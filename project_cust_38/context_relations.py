# -*- coding: utf-8 -*-
"""Declarative relationship/enrichment layer for MES context registers.

This module is intentionally independent from the concrete ORM implementation.
It accepts normal strings as before, but also accepts ORM-like Field objects
(`name`, `db_column`, `model`) and model classes (`__table__`, `__fields__`).

Main responsibilities:
    * describe table-to-table relationships separately from register fields;
    * resolve Field objects into stable FieldRef/TableRef metadata;
    * provide lazy Relationship descriptor for ORM models;
    * enrich rows in memory before RegisterRuntime;
    * generate SQL SELECT/JOIN fragments for virtual registers and reports;
    * serialize RelationSpec into the admin metadata tables agreed for stage 1.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from enum import Enum
import inspect
import re
import sys
import types
import typing
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence


__all__ = [
    'RelationError',
    'RelationMissingError',
    'RelationCardinalityError',
    'RelationJoinType',
    'RelationCardinality',
    'RelationShape',
    'MissingPolicy',
    'OnManyPolicy',
    'SelectMode',
    'JoinType',
    'Cardinality',
    'OnMany',
    'FieldRef',
    'TableRef',
    'RelationFieldPair',
    'ResolvedRelationFieldPair',
    'RelationSpec',
    'RelationRef',
    'RegisterStageSpec',
    'RelationRegistry',
    'RelationResolver',
    'EnrichmentStage',
    'SqlPlan',
    'SQLRelationCompiler',
    'Relationship',
    'resolve_table_ref',
    'resolve_field_ref',
    'field_name',
    'field_db_column',
    'quote_ident',
    'relation_to_admin_records',
    'relation_from_admin_records',
    'relation_from_state_field',
    'register_stage_from_legacy_state_fields',
]


class RelationError(Exception):
    """Base relation-stage exception."""


class RelationMissingError(RelationError):
    """Required related object was not found."""


class RelationCardinalityError(RelationError):
    """A one-shaped relation returned several rows."""


class RelationJoinType(str, Enum):
    LEFT = 'LEFT JOIN'
    INNER = 'INNER JOIN'


# Backwards-compatible alias used by the first prototype/tests.
JoinType = RelationJoinType


class RelationCardinality(str, Enum):
    ONE_TO_ONE = 'one_to_one'
    MANY_TO_ONE = 'many_to_one'
    ONE_TO_MANY = 'one_to_many'
    MANY_TO_MANY = 'many_to_many'


class Cardinality(str, Enum):
    """Compatibility shape enum from the prototype: one/many."""

    ONE = 'one'
    MANY = 'many'


class RelationShape(str, Enum):
    ONE = 'one'
    MANY = 'many'


class MissingPolicy(str, Enum):
    NONE = 'none'          # lazy: None; SQL/enrichment: LEFT behavior
    EMPTY = 'empty'        # lazy: [];   SQL/enrichment: LEFT behavior
    RAISE = 'raise'        # lazy/enrichment: raise; SQL: usually INNER/post-check
    DROP = 'drop'          # SQL/enrichment: INNER behavior / skip row
    DEFAULT = 'default'    # lazy/enrichment: default_factory


class OnManyPolicy(str, Enum):
    ERROR = 'error'
    FIRST = 'first'
    LAST = 'last'
    LIST = 'list'


# Backwards-compatible alias used by the first prototype/tests.
OnMany = OnManyPolicy


class SelectMode(str, Enum):
    ONLY = 'only'
    ALL = 'all'
    NONE = 'none'


_ALLOWED_JOIN_TYPES = {item.value for item in RelationJoinType}
_FORBIDDEN_STAGE_JOINS = {'RIGHT', 'RIGHT JOIN', 'RIGHT OUTER JOIN', 'FULL', 'FULL JOIN', 'FULL OUTER JOIN'}
_ALLOWED_CARDINALITIES = {item.value for item in RelationCardinality} | {item.value for item in Cardinality}
_ALLOWED_MISSING = {item.value for item in MissingPolicy}
_ALLOWED_ON_MANY = {item.value for item in OnManyPolicy}
_ALLOWED_SELECT_MODES = {item.value for item in SelectMode}


FieldLike = Any
TableLike = Any


def _clean_text(value: Any) -> str:
    return str(value or '').strip()


def _safe_alias(value: Any, default: str = 'rel') -> str:
    text = _clean_text(value) or default
    text = re.sub(r'\W+', '_', text, flags=re.UNICODE).strip('_')
    if not text:
        text = default
    if text[0].isdigit():
        text = '_' + text
    return text


def quote_ident(value: Any) -> str:
    return '"' + str(value or '').replace('"', '""') + '"'


def _db_alias(db_name: Any) -> str:
    text = _clean_text(db_name)
    if not text:
        return ''
    if text.startswith('SRV:'):
        text = text.split('SRV:', 1)[-1]
    text = text.replace('\\', '/').rstrip('/')
    text = text.split('/')[-1]
    if '.' in text:
        text = text.rsplit('.', 1)[0]
    return _safe_alias(text, 'db')


def _normalize_join_type(value: Any, *, missing_policy: str | None = None) -> str:
    if value in (None, ''):
        if missing_policy in (MissingPolicy.DROP.value, MissingPolicy.RAISE.value):
            return RelationJoinType.INNER.value
        return RelationJoinType.LEFT.value
    text = _clean_text(value).upper()
    if text in ('LEFT', 'LEFT OUTER'):
        text = RelationJoinType.LEFT.value
    elif text in ('INNER', 'JOIN'):
        text = RelationJoinType.INNER.value
    if text in _FORBIDDEN_STAGE_JOINS:
        raise RelationError(
            f'{text} специально не поддержан в RelationSpec stage 1: у регистра должен быть ведущий источник. '
            'Для сверок/отчётов используйте ручной source_sql.'
        )
    if text not in _ALLOWED_JOIN_TYPES:
        raise RelationError(f'Некорректный join_type={value!r}. Разрешено: {sorted(_ALLOWED_JOIN_TYPES)}')
    return text


def _normalize_choice(value: Any, allowed: set[str], default: str, *, upper: bool = False) -> str:
    text = _clean_text(value) or default
    text = text.upper() if upper else text.lower()
    if text not in allowed:
        raise RelationError(f'Некорректное значение {value!r}. Разрешено: {sorted(allowed)}')
    return text


def _shape_from_cardinality(value: Any) -> str:
    text = _clean_text(value).lower()
    if text in (Cardinality.MANY.value, RelationCardinality.ONE_TO_MANY.value, RelationCardinality.MANY_TO_MANY.value):
        return RelationShape.MANY.value
    return RelationShape.ONE.value


def _normalize_cardinality(value: Any, *, inferred_shape: str | None = None) -> str:
    text = _clean_text(value).lower()
    if not text:
        if inferred_shape == RelationShape.MANY.value:
            return RelationCardinality.ONE_TO_MANY.value
        return RelationCardinality.MANY_TO_ONE.value
    if text == Cardinality.ONE.value:
        return RelationCardinality.MANY_TO_ONE.value
    if text == Cardinality.MANY.value:
        return RelationCardinality.ONE_TO_MANY.value
    if text not in _ALLOWED_CARDINALITIES:
        raise RelationError(f'Некорректная cardinality={value!r}. Разрешено: {sorted(_ALLOWED_CARDINALITIES)}')
    return text


def _normalize_missing(value: Any, *, shape: str | None = None, optional: bool | None = None) -> str:
    if value not in (None, ''):
        return _normalize_choice(value, _ALLOWED_MISSING, MissingPolicy.NONE.value)
    if shape == RelationShape.MANY.value:
        return MissingPolicy.EMPTY.value
    if optional is False:
        return MissingPolicy.RAISE.value
    return MissingPolicy.NONE.value


def _is_orm_field(value: Any) -> bool:
    return hasattr(value, 'db_column') and hasattr(value, 'name')


def _is_model_cls(value: Any) -> bool:
    return isinstance(value, type) and (hasattr(value, '__fields__') or hasattr(value, '__table__'))


def _accepts_keyword(callable_obj: Any, keyword_name: str) -> bool:
    """Return whether a callable accepts a keyword without executing it.

    Relation loading must not catch a broad ``TypeError`` and then repeat the
    query: the first call may already have reached the database and failed from
    inside user/runtime code.  Signature inspection lets us preserve legacy
    target models without a dangerous double execution.
    """
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        # BaseModel's public contract accepts executor. Unknown callables are
        # treated as modern; a genuine TypeError must be allowed to surface.
        return True
    if keyword_name in signature.parameters:
        parameter = signature.parameters[keyword_name]
        return parameter.kind in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    return any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _resolve_model_reference(value: Any, *, owner: Any = None, required: bool = True) -> Any:
    """Resolve a forward model reference without importing MES runtime modules.

    Generated models live in one module and may reference a class declared
    later in that module.  A string/class/lambda is therefore sufficient; no
    import of CFG, CMS or context_admin is needed.
    """
    if _is_model_cls(value):
        return value

    candidate = value
    if isinstance(value, str):
        module = sys.modules.get(getattr(owner, '__module__', '')) if owner is not None else None
        candidate = getattr(module, value, None) if module is not None else None
        if not _is_model_cls(candidate) and module is not None:
            # Also accept a stable table_key string for hand-written models.
            for item in vars(module).values():
                if not _is_model_cls(item):
                    continue
                if value in {
                    getattr(item, '__name__', ''),
                    getattr(item, '__table_key__', ''),
                }:
                    candidate = item
                    break
    elif callable(value):
        candidate = value()

    if _is_model_cls(candidate):
        return candidate
    if required:
        raise RelationError(f'Не удалось разрешить target_model={value!r} для owner={owner!r}')
    return None


def _model_db_key(model: Any) -> str:
    if model is None:
        return ''
    explicit = getattr(model, '__db_key__', None) or getattr(model, '__database_key__', None)
    if explicit:
        return str(explicit)
    db = getattr(model, '__db__', None)
    if isinstance(db, str):
        return _db_alias(db)
    # Do not eagerly call __db__ callables here: in the project they may touch
    # runtime config. A stable table key can still be provided via __table_key__.
    return ''


@dataclass(frozen=True)
class TableRef:
    """Stable reference to a physical/admin table or ORM model table."""

    table_key: str = ''
    table_name: str = ''
    db_key: str = ''
    db_path: str = ''
    model: Any = None

    @property
    def sql_name(self) -> str:
        return self.table_name or self.table_key.split('.')[-1]

    def __str__(self) -> str:
        return self.sql_name

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return other in {self.table_name, self.table_key, self.sql_name}
        return super().__eq__(other)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            'table_key': self.table_key,
            'table_name': self.table_name,
            'db_key': self.db_key,
            'db_path': self.db_path,
        }


@dataclass(frozen=True)
class FieldRef:
    """Resolved field metadata accepted by relations/register specs."""

    field_name: str
    db_column: str = ''
    python_name: str = ''
    table_key: str = ''
    table_name: str = ''
    db_key: str = ''
    model: Any = None
    field: Any = None

    @property
    def name(self) -> str:
        return self.field_name

    def to_jsonable(self) -> dict[str, Any]:
        return {
            'table_key': self.table_key,
            'table_name': self.table_name,
            'field_name': self.field_name,
            'db_column': self.db_column or self.field_name,
            'python_name': self.python_name or self.field_name,
            'db_key': self.db_key,
        }


def resolve_table_ref(value: TableLike = None, *, db_key: str | None = None, table_name: str | None = None,
                      db_path: str | None = None, model: Any = None) -> TableRef:
    if isinstance(value, TableRef):
        return value
    if value is None and model is not None:
        value = model
    if _is_model_cls(value):
        table = _clean_text(getattr(value, '__table__', ''))
        key = _clean_text(getattr(value, '__table_key__', ''))
        m_db_key = _model_db_key(value)
        if not key and table:
            key = f'{m_db_key or "unknown_db"}.{table}'
        return TableRef(
            table_key=key,
            table_name=table,
            db_key=m_db_key,
            db_path='',
            model=value,
        )
    if isinstance(value, Mapping):
        return TableRef(
            table_key=_clean_text(value.get('table_key')),
            table_name=_clean_text(value.get('table_name') or table_name),
            db_key=_clean_text(value.get('db_key') or db_key),
            db_path=_clean_text(value.get('db_path') or db_path),
            model=value.get('model'),
        )
    text = _clean_text(value or table_name)
    if not text:
        return TableRef(db_key=_clean_text(db_key), db_path=_clean_text(db_path), model=model)
    if '.' in text and not table_name:
        inferred_db_key, inferred_table = text.rsplit('.', 1)
        return TableRef(table_key=text, table_name=inferred_table, db_key=_clean_text(db_key) or inferred_db_key,
                        db_path=_clean_text(db_path), model=model)
    key = f'{_clean_text(db_key) or "unknown_db"}.{text}' if text else ''
    return TableRef(table_key=key, table_name=text, db_key=_clean_text(db_key), db_path=_clean_text(db_path), model=model)


def resolve_field_ref(value: FieldLike, *, model: Any = None, table: TableLike = None) -> FieldRef:
    if isinstance(value, FieldRef):
        return value
    table_ref = resolve_table_ref(table if table is not None else model)
    if _is_orm_field(value):
        field_model = getattr(value, 'model', None) or model
        if field_model is not None:
            table_ref = resolve_table_ref(field_model)
        raw_name = getattr(value, 'name', None) or getattr(value, 'db_column', None)
        db_column = getattr(value, 'db_column', None) or raw_name
        if not raw_name:
            raise RelationError(f'ORM Field {value!r} ещё не привязан к модели: нет .name/.db_column')
        return FieldRef(
            field_name=str(raw_name),
            db_column=str(db_column or raw_name),
            python_name=str(raw_name),
            table_key=table_ref.table_key,
            table_name=table_ref.table_name,
            db_key=table_ref.db_key,
            model=field_model,
            field=value,
        )
    text = _clean_text(value)
    if not text:
        raise RelationError('Пустая ссылка на поле')
    active_model = model or table_ref.model
    if active_model is not None and hasattr(active_model, '__fields__'):
        fields = getattr(active_model, '__fields__', {}) or {}
        by_column = getattr(active_model, '__field_by_column__', {}) or {}
        if text in fields:
            fld = fields[text]
            return resolve_field_ref(fld, model=active_model)
        if text in by_column:
            py_name = by_column[text]
            fld = fields[py_name]
            return resolve_field_ref(fld, model=active_model)
        raise RelationError(f'Поле {text!r} не найдено в модели {getattr(active_model, "__name__", active_model)!r}')
    return FieldRef(
        field_name=text,
        db_column=text,
        python_name=text,
        table_key=table_ref.table_key,
        table_name=table_ref.table_name,
        db_key=table_ref.db_key,
        model=active_model,
    )


def field_name(value: FieldLike) -> str:
    return resolve_field_ref(value).field_name


def field_db_column(value: FieldLike) -> str:
    ref = resolve_field_ref(value)
    return ref.db_column or ref.field_name


def _get_value(row: Any, ref_or_name: FieldLike, default: Any = None) -> Any:
    try:
        ref = resolve_field_ref(ref_or_name)
        names = [ref.field_name, ref.db_column]
    except Exception:
        names = [_clean_text(ref_or_name)]
    names = [name for idx, name in enumerate(names) if name and name not in names[:idx]]
    if isinstance(row, Mapping):
        for name in names:
            if name in row:
                return row.get(name)
        return default
    for name in names:
        if hasattr(row, name):
            return getattr(row, name)
    return default


def _as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    if isinstance(row, Mapping):
        return dict(row)
    if hasattr(row, 'to_dict') and callable(row.to_dict):
        return dict(row.to_dict())
    if hasattr(row, 'to_smartrow') and callable(row.to_smartrow):
        return dict(row.to_smartrow())
    if hasattr(row, '__dict__'):
        return {key: value for key, value in vars(row).items() if not key.startswith('_')}
    raise TypeError(f'Не удалось преобразовать строку {type(row).__name__} в dict')


def _iter_dict_rows(rows: Iterable[Any] | None) -> list[dict[str, Any]]:
    return [_as_dict(row) for row in (rows or ())]


@dataclass(frozen=True)
class RelationFieldPair:
    left_field: FieldLike
    right_field: FieldLike
    left_table: TableLike | None = None
    right_table: TableLike | None = None
    role: str = 'direct'
    operator: str = '='
    pair_join_type: str = ''

    def resolve(self, *, source_table: TableLike = None, target_table: TableLike = None) -> 'ResolvedRelationFieldPair':
        left_table = self.left_table if self.left_table is not None else source_table
        right_table = self.right_table if self.right_table is not None else target_table
        return ResolvedRelationFieldPair(
            left_field=resolve_field_ref(self.left_field, table=left_table),
            right_field=resolve_field_ref(self.right_field, table=right_table),
            left_table=resolve_table_ref(left_table),
            right_table=resolve_table_ref(right_table),
            role=_clean_text(self.role) or 'direct',
            operator=_clean_text(self.operator) or '=',
            pair_join_type=_clean_text(self.pair_join_type),
        )


@dataclass(frozen=True)
class ResolvedRelationFieldPair:
    left_field: FieldRef
    right_field: FieldRef
    left_table: TableRef
    right_table: TableRef
    role: str = 'direct'
    operator: str = '='
    pair_join_type: str = ''


@dataclass(frozen=True)
class RelationSpec:
    """Declarative table/model relationship for stage 1.

    The class keeps compatibility with the previous prototype (`name`,
    `local_field`, `remote_field`, `target_table`) and also supports the
    normalized metadata design (`relation_key`, table refs and field_pairs).
    """

    # compatibility / identity
    name: str = ''
    relation_key: str = ''
    relation_name: str = ''

    # tables/models
    source_table: TableLike | None = None
    target_table: TableLike | None = None
    target_model: Any = None
    source_db: str | None = None
    target_db: str | None = None

    # one-pair shortcut, kept for ergonomic declarations
    local_field: FieldLike | None = None
    remote_field: FieldLike | None = 'Пномер'
    field_pairs: tuple[RelationFieldPair, ...] = ()

    # semantics
    cardinality: str = RelationCardinality.MANY_TO_ONE.value
    shape: str = ''
    join_type: str = ''
    missing_policy: str = MissingPolicy.NONE.value
    on_many: str = OnManyPolicy.ERROR.value
    on_many_policy: str = ''

    # output/enrichment
    select_mode: str = SelectMode.ONLY.value
    select_fields: tuple[FieldLike, ...] = ()
    select_prefix: str = ''
    alias: str = ''
    fill_missing_selected: bool = True
    join_on_sql: str = ''
    notes: str = ''

    def normalized(self) -> 'RelationSpec':
        key = _clean_text(self.relation_key or self.name or self.relation_name)
        rel_name = _clean_text(self.relation_name or self.name or (key.rsplit('.', 1)[-1] if key else ''))
        if not key and rel_name:
            key = rel_name
        if not rel_name and key:
            rel_name = key.rsplit('.', 1)[-1]
        if not key:
            raise RelationError('RelationSpec требует relation_key/name')

        src_table = resolve_table_ref(self.source_table, db_key=_db_alias(self.source_db), db_path=self.source_db)
        target_like = self.target_model if self.target_model is not None else self.target_table
        target_table = resolve_table_ref(target_like, db_key=_db_alias(self.target_db), db_path=self.target_db)
        if self.target_db and not target_table.db_path:
            target_table = replace(target_table, db_path=str(self.target_db), db_key=target_table.db_key or _db_alias(self.target_db))

        inferred_shape = self.shape or None
        card = _normalize_cardinality(self.cardinality, inferred_shape=inferred_shape)
        shape = _normalize_choice(self.shape, {item.value for item in RelationShape}, _shape_from_cardinality(card)) if self.shape else _shape_from_cardinality(card)
        missing = _normalize_missing(self.missing_policy, shape=shape)
        join_type = _normalize_join_type(self.join_type, missing_policy=missing)
        select_mode = _normalize_choice(self.select_mode, _ALLOWED_SELECT_MODES, SelectMode.ONLY.value)
        on_many = _normalize_choice(self.on_many_policy or self.on_many, _ALLOWED_ON_MANY, OnManyPolicy.ERROR.value)

        pairs = tuple(self.field_pairs or ())
        if not pairs and self.local_field not in (None, ''):
            pairs = (RelationFieldPair(self.local_field, self.remote_field or 'Пномер'),)
        if not pairs and not self.join_on_sql:
            raise RelationError(f'RelationSpec({key!r}) требует field_pairs/local_field или join_on_sql')

        normalized_pairs: list[RelationFieldPair] = []
        for pair in pairs:
            if not isinstance(pair, RelationFieldPair):
                raise RelationError(f'field_pairs должен содержать RelationFieldPair, получено {pair!r}')
            # Validate now; keep original pair values for later model-aware resolution.
            pair.resolve(source_table=src_table, target_table=target_table)
            normalized_pairs.append(pair)

        selected = tuple(item for item in (self.select_fields or ()) if item not in (None, ''))
        if select_mode == SelectMode.ONLY.value and not selected:
            # For pure relationship/lazy descriptors select_fields may be empty. It
            # only matters for row enrichment / SQL compiler, where a clearer error
            # will be raised if selected output is requested.
            selected = tuple()

        first_pair = normalized_pairs[0] if normalized_pairs else None
        local = first_pair.left_field if first_pair else self.local_field
        remote = first_pair.right_field if first_pair else self.remote_field
        local_name = resolve_field_ref(local, table=src_table).field_name if local not in (None, '') else ''
        remote_name = resolve_field_ref(remote, table=target_table).field_name if remote not in (None, '') else ''

        return replace(
            self,
            name=rel_name,
            relation_key=key,
            relation_name=rel_name,
            source_table=src_table,
            target_table=target_table,
            target_model=target_table.model or self.target_model,
            target_db=target_table.db_path or self.target_db,
            source_db=src_table.db_path or self.source_db,
            local_field=local_name,
            remote_field=remote_name or 'Пномер',
            field_pairs=tuple(normalized_pairs),
            cardinality=card,
            shape=shape,
            missing_policy=missing,
            join_type=join_type,
            on_many=on_many,
            on_many_policy=on_many,
            select_mode=select_mode,
            select_fields=selected,
            select_prefix=_clean_text(self.select_prefix),
            alias=_safe_alias(self.alias, rel_name or key),
            join_on_sql=_clean_text(self.join_on_sql),
            notes=_clean_text(self.notes),
        )

    @property
    def output_prefix(self) -> str:
        spec = self.normalized()
        return spec.select_prefix or spec.relation_name or spec.name

    @property
    def dependency_key(self) -> str:
        spec = self.normalized()
        table_ref = resolve_table_ref(spec.target_table)
        if table_ref.table_key:
            return table_ref.table_key
        if table_ref.table_name:
            return f'{table_ref.db_key or _db_alias(spec.target_db) or "source_db"}.{table_ref.table_name}'
        return ''

    def resolved_pairs(self) -> tuple[ResolvedRelationFieldPair, ...]:
        spec = self.normalized()
        return tuple(pair.resolve(source_table=spec.source_table, target_table=spec.target_table) for pair in spec.field_pairs)


@dataclass(frozen=True)
class RelationRef:
    name: str
    fields: tuple[FieldLike, ...] = ()
    prefix: str = ''
    mode: str = ''
    required: bool = False
    explode: bool = False

    def apply_to(self, spec: RelationSpec) -> RelationSpec:
        kwargs: dict[str, Any] = {}
        if self.fields:
            kwargs['select_fields'] = tuple(self.fields)
            kwargs['select_mode'] = SelectMode.ONLY.value
        if self.prefix:
            kwargs['select_prefix'] = self.prefix
        if self.mode:
            kwargs['select_mode'] = self.mode
        if self.required:
            kwargs['missing_policy'] = MissingPolicy.DROP.value
            kwargs['join_type'] = RelationJoinType.INNER.value
        return replace(spec, **kwargs).normalized()


@dataclass(frozen=True)
class RegisterStageSpec:
    code: str
    relation_refs: tuple[str | RelationRef | RelationSpec, ...] = ()
    dependency_table_keys: tuple[str, ...] = ()


class RelationRegistry:
    def __init__(self, relations: Iterable[RelationSpec] | None = None) -> None:
        self._items: dict[str, RelationSpec] = {}
        for relation in relations or ():
            self.register(relation)

    def register(self, relation: RelationSpec) -> RelationSpec:
        spec = relation.normalized()
        if spec.relation_key in self._items:
            raise RelationError(f'Связь {spec.relation_key!r} уже зарегистрирована')
        self._items[spec.relation_key] = spec
        if spec.name and spec.name not in self._items:
            self._items[spec.name] = spec
        return spec

    def replace(self, relation: RelationSpec) -> RelationSpec:
        spec = relation.normalized()
        self._items[spec.relation_key] = spec
        if spec.name:
            self._items[spec.name] = spec
        return spec

    def get(self, name: str) -> RelationSpec:
        try:
            return self._items[str(name)]
        except KeyError as exc:
            raise RelationError(f'Связь {name!r} не зарегистрирована') from exc

    def resolve(self, item: str | RelationRef | RelationSpec) -> RelationSpec:
        if isinstance(item, RelationSpec):
            return item.normalized()
        if isinstance(item, RelationRef):
            return item.apply_to(self.get(item.name))
        return self.get(str(item)).normalized()

    def dependency_keys(self, refs: Iterable[str | RelationRef | RelationSpec]) -> tuple[str, ...]:
        result: list[str] = []
        for ref_item in refs:
            dep = self.resolve(ref_item).dependency_key
            if dep and dep not in result:
                result.append(dep)
        return tuple(result)

    def as_dict(self) -> dict[str, RelationSpec]:
        return dict(self._items)


class RelationResolver:
    """In-memory row enrichment stage."""

    def __init__(self, registry: RelationRegistry | None = None) -> None:
        self.registry = registry or RelationRegistry()

    def apply(
        self,
        rows: Iterable[Any],
        relations: Sequence[str | RelationRef | RelationSpec],
        *,
        right_data: Mapping[str, Iterable[Any]] | None = None,
        loader: Callable[[RelationSpec], Iterable[Any]] | None = None,
    ) -> list[dict[str, Any]]:
        result = _iter_dict_rows(rows)
        for relation_item in relations:
            spec = self.registry.resolve(relation_item)
            right_rows = self._load_right_rows(spec, right_data=right_data, loader=loader)
            result = self._apply_one(result, spec, right_rows)
        return result

    @staticmethod
    def _load_right_rows(
        spec: RelationSpec,
        *,
        right_data: Mapping[str, Iterable[Any]] | None,
        loader: Callable[[RelationSpec], Iterable[Any]] | None,
    ) -> list[dict[str, Any]]:
        keys = [spec.relation_key, spec.name, spec.relation_name]
        if right_data:
            for key in keys:
                if key and key in right_data:
                    return _iter_dict_rows(right_data[key])
        if loader is not None:
            return _iter_dict_rows(loader(spec))
        raise RelationError(
            f'Для связи {spec.relation_key!r} не переданы right_data/loader. '
            'SQL и транспорт остаются вне stage 1.'
        )

    def _key_for_left(self, row: Mapping[str, Any], pairs: tuple[ResolvedRelationFieldPair, ...]) -> tuple[Any, ...]:
        return tuple(_get_value(row, pair.left_field) for pair in pairs if pair.role == 'direct')

    def _key_for_right(self, row: Mapping[str, Any], pairs: tuple[ResolvedRelationFieldPair, ...]) -> tuple[Any, ...]:
        return tuple(_get_value(row, pair.right_field) for pair in pairs if pair.role == 'direct')

    def _apply_one(self, left_rows: list[dict[str, Any]], spec: RelationSpec, right_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        spec = spec.normalized()
        pairs = spec.resolved_pairs()
        direct_pairs = tuple(pair for pair in pairs if pair.role == 'direct')
        if not direct_pairs and not spec.join_on_sql:
            raise RelationError(f'In-memory enrichment для {spec.relation_key!r} требует direct field_pairs')

        index: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for right in right_rows:
            index[self._key_for_right(right, direct_pairs)].append(right)

        result: list[dict[str, Any]] = []
        for left in left_rows:
            local_key = self._key_for_left(left, direct_pairs)
            matches = index.get(local_key, [])
            if not matches:
                if spec.missing_policy == MissingPolicy.DROP.value or spec.join_type == RelationJoinType.INNER.value:
                    continue
                if spec.missing_policy == MissingPolicy.RAISE.value:
                    raise RelationMissingError(f'Связь {spec.relation_key!r}: объект для ключа {local_key!r} не найден')
                merged = dict(left)
                self._merge_missing(merged, spec)
                result.append(merged)
                continue
            result.extend(self._merge_matches(left, spec, matches))
        return result

    def _merge_matches(self, left: dict[str, Any], spec: RelationSpec, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if spec.shape == RelationShape.ONE.value:
            if len(matches) > 1:
                if spec.on_many == OnManyPolicy.ERROR.value:
                    raise RelationCardinalityError(
                        f'Связь {spec.relation_key!r} объявлена как one, но найдено {len(matches)} строк справа.'
                    )
                if spec.on_many == OnManyPolicy.FIRST.value:
                    matches = matches[:1]
                elif spec.on_many == OnManyPolicy.LAST.value:
                    matches = matches[-1:]
                elif spec.on_many == OnManyPolicy.LIST.value:
                    merged = dict(left)
                    self._merge_list(merged, spec, matches)
                    return [merged]
            merged = dict(left)
            self._merge_one(merged, spec, matches[0])
            return [merged]
        merged = dict(left)
        self._merge_list(merged, spec, matches)
        return [merged]

    def _selected_payload(self, spec: RelationSpec, right: dict[str, Any]) -> dict[str, Any]:
        if spec.select_mode == SelectMode.NONE.value:
            return {}
        target_model = resolve_table_ref(spec.target_table).model or spec.target_model
        if spec.select_mode == SelectMode.ALL.value:
            return dict(right)
        if not spec.select_fields:
            raise RelationError(f'RelationSpec({spec.relation_key!r}) select_mode="only" требует select_fields для enrichment')
        payload: dict[str, Any] = {}
        for item in spec.select_fields:
            ref = resolve_field_ref(item, model=target_model)
            payload[ref.field_name] = _get_value(right, ref)
        return payload

    def _merge_one(self, left: MutableMapping[str, Any], spec: RelationSpec, right: dict[str, Any]) -> None:
        prefix = spec.output_prefix
        for out_field, value in self._selected_payload(spec, right).items():
            left[f'{prefix}.{out_field}' if prefix else out_field] = value

    def _merge_list(self, left: MutableMapping[str, Any], spec: RelationSpec, matches: list[dict[str, Any]]) -> None:
        prefix = spec.output_prefix
        left[f'{prefix}[]'] = [self._selected_payload(spec, right) for right in matches]

    def _merge_missing(self, left: MutableMapping[str, Any], spec: RelationSpec) -> None:
        if spec.select_mode == SelectMode.NONE.value or not spec.fill_missing_selected:
            return
        prefix = spec.output_prefix
        if spec.shape == RelationShape.MANY.value or spec.missing_policy == MissingPolicy.EMPTY.value:
            left[f'{prefix}[]'] = []
            return
        if spec.select_mode == SelectMode.ONLY.value:
            target_model = resolve_table_ref(spec.target_table).model or spec.target_model
            for item in spec.select_fields:
                ref = resolve_field_ref(item, model=target_model)
                left[f'{prefix}.{ref.field_name}' if prefix else ref.field_name] = None


class EnrichmentStage:
    def __init__(self, registry: RelationRegistry | None = None) -> None:
        self.registry = registry or RelationRegistry()
        self.resolver = RelationResolver(self.registry)

    def apply(
        self,
        rows: Iterable[Any],
        spec: RegisterStageSpec,
        *,
        right_data: Mapping[str, Iterable[Any]] | None = None,
        loader: Callable[[RelationSpec], Iterable[Any]] | None = None,
    ) -> list[dict[str, Any]]:
        return self.resolver.apply(rows, spec.relation_refs, right_data=right_data, loader=loader)

    def dependency_table_keys(self, spec: RegisterStageSpec) -> tuple[str, ...]:
        result = list(spec.dependency_table_keys or ())
        for key in self.registry.dependency_keys(spec.relation_refs):
            if key not in result:
                result.append(key)
        return tuple(result)


@dataclass(frozen=True)
class SqlPlan:
    sql: str
    select_sql: str
    join_sql: str
    attach_dbs: tuple[str, ...] = ()
    dependency_table_keys: tuple[str, ...] = ()


class SQLRelationCompiler:
    def __init__(self, registry: RelationRegistry | None = None) -> None:
        self.registry = registry or RelationRegistry()

    def compile_select(
        self,
        *,
        source_table: TableLike | None = None,
        source_model: Any = None,
        source_sql: str | None = None,
        source_db: str | None = None,
        source_fields: Sequence[FieldLike] = (),
        relations: Sequence[str | RelationRef | RelationSpec] = (),
        source_alias: str = 'src',
        where_sql: str = '',
        order_by_sql: str = '',
        limit: int | str | None = None,
    ) -> SqlPlan:
        if not source_table and source_model is None and not source_sql:
            raise RelationError('compile_select требует source_table/source_model или source_sql')
        src_ref = resolve_table_ref(source_model if source_model is not None else source_table, db_key=_db_alias(source_db), db_path=source_db)
        if source_model is not None:
            source_table = source_model

        select_parts: list[str] = []
        join_parts: list[str] = []
        attach_dbs: list[str] = []
        dependency_keys: list[str] = []
        output_names: set[str] = set()

        def add_select(expression: str, output_name: str) -> None:
            if output_name in output_names:
                return
            output_names.add(output_name)
            select_parts.append(f'{expression} AS {quote_ident(output_name)}')

        for field_item in source_fields:
            ref = resolve_field_ref(field_item, table=src_ref)
            add_select(f'{source_alias}.{quote_ident(ref.db_column or ref.field_name)}', ref.field_name)
        if not source_fields:
            select_parts.append(f'{source_alias}.*')

        for relation_item in relations:
            spec = self.registry.resolve(relation_item)
            spec = spec.normalized()
            target_ref = resolve_table_ref(spec.target_table)
            if not target_ref.sql_name:
                raise RelationError(f'Для SQL-компиляции связи {spec.relation_key!r} нужен target_table/target_model')
            alias = spec.alias
            table_ref_sql = quote_ident(target_ref.sql_name)
            rel_db_path = target_ref.db_path or spec.target_db
            if rel_db_path and source_db and str(rel_db_path) != str(source_db):
                if rel_db_path not in attach_dbs:
                    attach_dbs.append(str(rel_db_path))
                db_alias = target_ref.db_key or _db_alias(rel_db_path)
                if db_alias:
                    table_ref_sql = f'{db_alias}.{quote_ident(target_ref.sql_name)}'

            if spec.join_on_sql:
                on_sql = spec.join_on_sql
            else:
                on_parts: list[str] = []
                for pair in spec.resolved_pairs():
                    if pair.role != 'direct':
                        raise RelationError(
                            f'SQLRelationCompiler пока поддерживает direct field_pairs; роль {pair.role!r} '
                            f'для {spec.relation_key!r} лучше компилировать отдельным source_sql.'
                        )
                    op = pair.operator or '='
                    on_parts.append(
                        f'{alias}.{quote_ident(pair.right_field.db_column or pair.right_field.field_name)} '
                        f'{op} {source_alias}.{quote_ident(pair.left_field.db_column or pair.left_field.field_name)}'
                    )
                on_sql = ' AND '.join(on_parts)
            join_parts.append(f'{spec.join_type} {table_ref_sql} AS {alias} ON {on_sql}')

            if spec.select_mode == SelectMode.NONE.value:
                continue
            if spec.select_mode == SelectMode.ALL.value:
                raise RelationError(f'RelationSpec({spec.relation_key!r}) select_mode="all" не поддержан SQL-компилятором без схемы')
            if not spec.select_fields:
                continue
            prefix = spec.output_prefix
            target_model = target_ref.model or spec.target_model
            for field_item in spec.select_fields:
                ref = resolve_field_ref(field_item, model=target_model, table=target_ref)
                add_select(f'{alias}.{quote_ident(ref.db_column or ref.field_name)}', f'{prefix}.{ref.field_name}' if prefix else ref.field_name)

            dep = spec.dependency_key
            if dep and dep not in dependency_keys:
                dependency_keys.append(dep)

        if source_sql:
            from_sql = f'({_clean_text(source_sql).rstrip(";")}) AS {source_alias}'
        else:
            from_sql = f'{quote_ident(src_ref.sql_name or str(source_table))} AS {source_alias}'

        sql = 'SELECT\n    ' + ',\n    '.join(select_parts) + f'\nFROM {from_sql}'
        if join_parts:
            sql += '\n' + '\n'.join(join_parts)
        if where_sql:
            sql += f'\nWHERE {where_sql.strip()}'
        if order_by_sql:
            sql += f'\nORDER BY {order_by_sql.strip()}'
        if limit not in (None, ''):
            sql += f'\nLIMIT {limit}'
        return SqlPlan(
            sql=sql,
            select_sql=',\n    '.join(select_parts),
            join_sql='\n'.join(join_parts),
            attach_dbs=tuple(attach_dbs),
            dependency_table_keys=tuple(dependency_keys),
        )


def _annotation_shape(annotation: Any) -> tuple[str | None, bool | None, Any]:
    """Return (shape, optional, item_type) inferred from annotation."""
    if annotation is None:
        return None, None, None
    if isinstance(annotation, str):
        text = annotation.replace('typing.', '').replace(' ', '')
        lower = text.lower()
        optional = '|none' in lower or 'none|' in lower or lower.startswith('optional[') or ',nonetype' in lower
        if lower.startswith(('list[', 'tuple[', 'set[', 'sequence[', 'iterable[')):
            return RelationShape.MANY.value, True, Any
        return RelationShape.ONE.value, optional if optional else False, Any
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin in (list, tuple, set, Sequence, Iterable):
        return RelationShape.MANY.value, True, args[0] if args else Any
    if origin in (typing.Union, types.UnionType):
        non_none = [arg for arg in args if arg is not type(None)]
        optional = len(non_none) != len(args)
        if len(non_none) == 1:
            nested_shape, _, nested_type = _annotation_shape(non_none[0])
            return nested_shape or RelationShape.ONE.value, optional, nested_type or non_none[0]
        return RelationShape.ONE.value, optional, non_none[0] if non_none else Any
    return RelationShape.ONE.value, False, annotation


class Relationship:
    """Lazy ORM-like relationship descriptor.

    Minimal declaration:

        mk: MkModel | None = Relationship(
            MkModel,
            local_field=Номер_мк,
            remote_field=MkModel.Пномер,
        )

    The descriptor only stores metadata and lazy-loading behavior. Query JOINs are
    generated by RelationSpec/SQLRelationCompiler so many-relations do not
    accidentally multiply register movement rows.
    """

    __mes_relationship__ = True

    def __init__(
        self,
        target_model: Any = None,
        *,
        relation_key: str = '',
        local_field: FieldLike | None = None,
        remote_field: FieldLike | None = 'pk',
        field_pairs: tuple[RelationFieldPair, ...] = (),
        cardinality: str | None = None,
        shape: str | None = None,
        missing: str | None = None,
        missing_policy: str | None = None,
        join_type: str | None = None,
        on_many: str = OnManyPolicy.ERROR.value,
        through: Any = None,
        through_local_field: FieldLike | None = None,
        through_remote_field: FieldLike | None = None,
        select_fields: tuple[FieldLike, ...] = (),
        select_prefix: str = '',
        notes: str = '',
        loader: Callable[[Any, Any, 'Relationship'], Any] | None = None,
        default_factory: Callable[[], Any] | None = None,
        cache: bool = True,
        none_values: tuple[Any, ...] = (None, '', 0, '-'),
    ) -> None:
        self.target_model = target_model
        self._relation_key_override = _clean_text(relation_key)
        self.local_field = local_field
        self.remote_field = remote_field
        self.field_pairs = tuple(field_pairs or ())
        self.cardinality = cardinality
        self.shape = shape
        self.missing_policy = missing_policy if missing_policy is not None else missing
        self.join_type = join_type
        self.on_many = on_many
        self.through = through
        self.through_local_field = through_local_field
        self.through_remote_field = through_remote_field
        self.select_fields = tuple(select_fields or ())
        self.select_prefix = select_prefix
        self.notes = _clean_text(notes)
        self.loader = loader
        self.default_factory = default_factory
        self.cache = cache
        self.none_values = none_values
        self.name = ''
        self.owner = None
        self._resolved_target_model = None
        self._inferred_shape: str | None = None
        self._inferred_optional: bool | None = None

    def __set_name__(self, owner: Any, name: str) -> None:
        self.name = name
        self.owner = owner
        ann = getattr(owner, '__annotations__', {}).get(name)
        try:
            ann = typing.get_type_hints(owner).get(name, ann)
        except Exception:
            pass
        self._inferred_shape, self._inferred_optional, _ = _annotation_shape(ann)
        # Keep the owner's relation registry in descriptor form; ModelMeta in Cust_orm
        # may replace this with RelationSpec records later, but this works for plain classes.
        relations = dict(getattr(owner, '__relations__', {}) or {})
        relations[name] = self
        try:
            setattr(owner, '__relations__', relations)
        except Exception:
            pass

    @property
    def resolved_shape(self) -> str:
        if self.shape:
            return _normalize_choice(self.shape, {item.value for item in RelationShape}, RelationShape.ONE.value)
        if self._inferred_shape:
            return self._inferred_shape
        return _shape_from_cardinality(self.cardinality or RelationCardinality.MANY_TO_ONE.value)

    @property
    def resolved_cardinality(self) -> str:
        return _normalize_cardinality(self.cardinality, inferred_shape=self.resolved_shape)

    @property
    def resolved_missing_policy(self) -> str:
        return _normalize_missing(self.missing_policy, shape=self.resolved_shape, optional=self._inferred_optional)

    @property
    def resolved_join_type(self) -> str:
        return _normalize_join_type(self.join_type, missing_policy=self.resolved_missing_policy)

    def resolve_target_model(self, *, required: bool = True) -> Any:
        if _is_model_cls(self._resolved_target_model):
            return self._resolved_target_model
        target = _resolve_model_reference(self.target_model, owner=self.owner, required=required)
        if _is_model_cls(target):
            self._resolved_target_model = target
        return target

    def as_relation_spec(self, owner: Any = None) -> RelationSpec:
        source_model = owner or self.owner
        pairs = self.field_pairs
        if not pairs and self.local_field not in (None, ''):
            pairs = (RelationFieldPair(self.local_field, self.remote_field or 'pk'),)
        # Resolve 'pk' remote shorthand against target model.
        fixed_pairs: list[RelationFieldPair] = []
        target = self.resolve_target_model()
        for pair in pairs:
            right = pair.right_field
            if right in ('pk', '__pk__') and target is not None and hasattr(target, 'pk_name'):
                try:
                    right = getattr(target, target.pk_name())
                except Exception:
                    right = getattr(target, getattr(target, '__pk__', ''), right)
            fixed_pairs.append(replace(pair, right_field=right))
        return RelationSpec(
            name=self.name,
            relation_key=self.relation_key(source_model),
            relation_name=self.name,
            source_table=source_model,
            target_table=target,
            target_model=target,
            field_pairs=tuple(fixed_pairs),
            local_field=self.local_field,
            remote_field=self.remote_field,
            cardinality=self.resolved_cardinality,
            shape=self.resolved_shape,
            missing_policy=self.resolved_missing_policy,
            join_type=self.resolved_join_type,
            on_many=self.on_many,
            select_fields=self.select_fields,
            select_prefix=self.select_prefix or self.name,
            notes=self.notes,
        ).normalized()

    def relation_key(self, owner: Any = None) -> str:
        if self._relation_key_override:
            return self._relation_key_override
        src = resolve_table_ref(owner or self.owner)
        return f'{src.table_key}.{self.name}' if src.table_key else self.name

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        if instance is None:
            return self
        target, lookup, cache_value = self._build_lookup(instance)
        local_values = cache_value if isinstance(cache_value, tuple) else (cache_value,)
        if any(value in self.none_values for value in local_values):
            return self._missing_value(cache_value)

        cache_attr = f'_relationship_cache_{self.name}'
        cache_key_attr = f'_relationship_cache_key_{self.name}'
        if self.cache and getattr(instance, cache_key_attr, object()) == cache_value:
            return getattr(instance, cache_attr, None)

        result = self._load(instance, target=target, lookup=lookup, cache_value=cache_value)
        if result in (None, []):
            if self.resolved_missing_policy == MissingPolicy.RAISE.value:
                raise RelationMissingError(f'Связь {self.name!r}: объект для ключа {cache_value!r} не найден')
            if self.resolved_missing_policy in (MissingPolicy.EMPTY.value, MissingPolicy.DEFAULT.value):
                result = self._missing_value(cache_value)
        if self.cache:
            setattr(instance, cache_key_attr, cache_value)
            setattr(instance, cache_attr, result)
        return result

    def _build_lookup(self, instance: Any) -> tuple[Any, dict[str, Any], Any]:
        target = self.resolve_target_model(required=self.loader is None)
        if self.resolved_cardinality == RelationCardinality.MANY_TO_MANY.value and self.loader is None:
            raise RelationError(
                f'Relationship({self.name}) many_to_many требует явный loader/through-runtime; '
                'декларация through сама по себе ещё не исполняется.'
            )

        raw_pairs = tuple(self.field_pairs or ())
        if not raw_pairs:
            if self.local_field in (None, ''):
                raise RelationError(f'Relationship({self.name}) требует local_field или field_pairs')
            raw_pairs = (RelationFieldPair(self.local_field, self.remote_field or 'pk'),)

        lookup: dict[str, Any] = {}
        local_values: list[Any] = []
        for pair in raw_pairs:
            role = _clean_text(pair.role) or 'direct'
            if role != 'direct':
                continue
            operator = _clean_text(pair.operator) or '='
            if operator != '=':
                raise RelationError(
                    f'Relationship({self.name}) lazy-loader поддерживает только operator="="; '
                    f'получено {operator!r}'
                )
            local_ref = resolve_field_ref(pair.left_field, model=self.owner)
            value = _get_value(instance, local_ref)
            local_values.append(value)
            if target is None:
                # A custom loader owns remote resolution; retain only a stable
                # cache key and do not require target metadata.
                continue
            right_field = pair.right_field
            if right_field in ('pk', '__pk__'):
                right_field = target.pk_name() if hasattr(target, 'pk_name') else getattr(target, '__pk__', 'pk')
            remote_ref = resolve_field_ref(right_field, model=target)
            remote_name = remote_ref.field_name
            if remote_name in lookup:
                raise RelationError(
                    f'Relationship({self.name}) содержит несколько direct-пар для '
                    f'одного удалённого поля {remote_name!r}; условие неоднозначно'
                )
            lookup[remote_name] = value

        if not local_values:
            raise RelationError(f'Relationship({self.name}) не содержит direct field_pairs')
        cache_value: Any = local_values[0] if len(local_values) == 1 else tuple(local_values)
        return target, lookup, cache_value

    def _missing_value(self, local_value: Any) -> Any:
        policy = self.resolved_missing_policy
        if policy == MissingPolicy.EMPTY.value:
            return []
        if policy == MissingPolicy.DEFAULT.value:
            return self.default_factory() if self.default_factory else None
        if policy == MissingPolicy.RAISE.value:
            raise RelationMissingError(f'Связь {self.name!r}: пустой локальный ключ {local_value!r}')
        return None

    def _load(self, instance: Any, *, target: Any, lookup: dict[str, Any], cache_value: Any) -> Any:
        if self.loader is not None:
            return self.loader(instance, cache_value, self)

        # The source instance may live in another SQLite database. Reusing
        # instance._db here silently redirected cross-database relationships to
        # the wrong file. The target model owns its DB; only a custom executor is
        # shared so tests/transports remain injectable.
        executor = getattr(instance, '_executor', None)
        try:
            pk_name = target.pk_name() if hasattr(target, 'pk_name') else getattr(target, '__pk__', None)
        except Exception:
            pk_name = getattr(target, '__pk__', None)
        if (
                self.resolved_shape == RelationShape.ONE.value
                and len(lookup) == 1
                and pk_name
                and pk_name in lookup
                and hasattr(target, 'get')
        ):
            get_kwargs = {'pk': lookup[pk_name]}
            if executor is not None and _accepts_keyword(target.get, 'executor'):
                get_kwargs['executor'] = executor
            try:
                return target.get(**get_kwargs)
            except Exception as exc:
                does_not_exist = getattr(target, 'DoesNotExist', None)
                if isinstance(does_not_exist, type) and isinstance(exc, does_not_exist):
                    return None
                raise

        if hasattr(target, 'query'):
            query_kwargs = {}
            if executor is not None and _accepts_keyword(target.query, 'executor'):
                query_kwargs['executor'] = executor
            qs = target.query(**query_kwargs).filter(**lookup)
        elif hasattr(target, 'filter'):
            qs = target.filter(**lookup)
        else:
            qs = None

        if self.resolved_shape == RelationShape.MANY.value:
            if qs is None:
                return []
            if hasattr(qs, 'all'):
                return qs.all()
            return list(qs)

        if qs is not None:
            rows: list[Any] | None = None
            if hasattr(qs, 'limit') and hasattr(qs, 'all'):
                rows = list(qs.limit(2).all())
            elif hasattr(qs, 'all'):
                rows = list(qs.all())
            elif isinstance(qs, (list, tuple)):
                rows = list(qs)
            if rows is not None:
                if not rows:
                    return None
                if len(rows) == 1:
                    return rows[0]
                policy = _normalize_choice(self.on_many, _ALLOWED_ON_MANY, OnManyPolicy.ERROR.value)
                if policy == OnManyPolicy.FIRST.value:
                    return rows[0]
                if policy == OnManyPolicy.LAST.value:
                    return rows[-1]
                if policy == OnManyPolicy.LIST.value:
                    return rows
                raise RelationCardinalityError(
                    f'Relationship({self.name}) ожидал одну строку, получено {len(rows)} для {lookup!r}'
                )
            if hasattr(qs, 'first'):
                return qs.first()
        raise RelationError(f'Не умею загрузить relationship {self.name!r} через target_model={target!r}')


# ----- Admin metadata helpers -------------------------------------------------


def relation_to_admin_records(spec: RelationSpec) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec = spec.normalized()
    source = resolve_table_ref(spec.source_table)
    target = resolve_table_ref(spec.target_table)
    header = {
        'relation_key': spec.relation_key,
        'relation_name': spec.relation_name,
        'source_table_key': source.table_key,
        'target_table_key': target.table_key,
        'cardinality': spec.cardinality,
        'join_type': spec.join_type,
        'missing_policy': spec.missing_policy,
        'on_many_policy': spec.on_many,
        'select_prefix': spec.select_prefix,
        'is_enabled': 1,
        'is_generated': 0,
        'notes': spec.notes,
    }
    pairs: list[dict[str, Any]] = []
    for idx, pair in enumerate(spec.resolved_pairs()):
        pairs.append({
            'relation_key': spec.relation_key,
            'pair_no': idx,
            'left_table_key': pair.left_table.table_key or pair.left_field.table_key,
            'left_field_name': pair.left_field.db_column or pair.left_field.field_name,
            'right_table_key': pair.right_table.table_key or pair.right_field.table_key,
            'right_field_name': pair.right_field.db_column or pair.right_field.field_name,
            'role': pair.role,
            'operator': pair.operator,
            'pair_join_type': pair.pair_join_type,
        })
    return header, pairs


def relation_from_admin_records(header: Mapping[str, Any], pairs: Iterable[Mapping[str, Any]]) -> RelationSpec:
    field_pairs = []
    for row in sorted(list(pairs or ()), key=lambda item: int(item.get('pair_no', 0) or 0)):
        field_pairs.append(RelationFieldPair(
            left_field=str(row.get('left_field_name') or ''),
            right_field=str(row.get('right_field_name') or ''),
            left_table=str(row.get('left_table_key') or ''),
            right_table=str(row.get('right_table_key') or ''),
            role=str(row.get('role') or 'direct'),
            operator=str(row.get('operator') or '='),
            pair_join_type=str(row.get('pair_join_type') or ''),
        ))
    return RelationSpec(
        relation_key=str(header.get('relation_key') or ''),
        relation_name=str(header.get('relation_name') or ''),
        source_table=str(header.get('source_table_key') or ''),
        target_table=str(header.get('target_table_key') or ''),
        cardinality=str(header.get('cardinality') or RelationCardinality.MANY_TO_ONE.value),
        shape=str(header.get('shape') or ''),
        join_type=str(header.get('join_type') or ''),
        missing_policy=str(header.get('missing_policy') or MissingPolicy.NONE.value),
        on_many=str(header.get('on_many_policy') or OnManyPolicy.ERROR.value),
        select_prefix=str(header.get('select_prefix') or ''),
        field_pairs=tuple(field_pairs),
        notes=str(header.get('notes') or ''),
    ).normalized()


# ----- Legacy bridges ---------------------------------------------------------


def relation_from_state_field(state_field: Any, *, name: str | None = None) -> RelationSpec | None:
    if isinstance(state_field, Mapping):
        getter = state_field.get
    else:
        getter = lambda key, default=None: getattr(state_field, key, default)

    join_table = getter('join_table')
    if not join_table:
        return None
    field_name_value = getter('field_name', '')
    relation_name = name or _safe_alias(f'{field_name(field_name_value)}_{join_table}', str(join_table))
    return RelationSpec(
        name=relation_name,
        local_field=field_name_value,
        remote_field=str(getter('field_for_join', '') or 'Пномер'),
        target_table=str(join_table),
        target_db=getter('db_name'),
        join_type=str(getter('join_type', RelationJoinType.LEFT.value) or RelationJoinType.LEFT.value),
        select_mode=str(getter('join_mode', SelectMode.ALL.value) or SelectMode.ALL.value),
        select_fields=tuple(getter('select_fields', ()) or ()),
        select_prefix=str(getter('select_prefix', '') or str(join_table)),
        alias=str(getter('join_alias', '') or ''),
        join_on_sql=str(getter('join_on_sql', '') or ''),
    ).normalized()


def register_stage_from_legacy_state_fields(
    *,
    code: str,
    state_fields: Iterable[Any],
    registry: RelationRegistry | None = None,
    dependency_table_keys: Iterable[str] = (),
) -> RegisterStageSpec:
    active_registry = registry or RelationRegistry()
    refs: list[RelationRef] = []
    for item in state_fields or ():
        relation = relation_from_state_field(item)
        if relation is None:
            continue
        active_registry.replace(relation)
        refs.append(RelationRef(relation.relation_key))
    return RegisterStageSpec(
        code=code,
        relation_refs=tuple(refs),
        dependency_table_keys=tuple(str(key) for key in dependency_table_keys),
    )
