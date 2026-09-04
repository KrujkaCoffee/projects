from __future__ import annotations

import enum
from collections import OrderedDict
import copy
import dataclasses
import datetime as _dt
import inspect
import json
import keyword
import typing
import types
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import project_cust_38.Cust_SQLite as CSQ


__all__ = [
    "OrmError",
    "DoesNotExist",
    "MultipleObjectsReturned",
    "Field",
    "IntField",
    "FloatField",
    "StrField",
    "BoolField",
    "DateTimeField",
    "BlobField",
    "JsonTextField",
    "ListTextField",
    "SmartRow",
    "SmartList",
    "QuerySetLite",
    "ObjectManager",
    "SaveResult",
    "BaseModel",
    "FieldRef",
    "TableRef",
    "RelationFieldPair",
    "RelationSpec",
    "Relationship",
    "GroupByTypes",
]


_EMPTY = object()
ModelT = typing.TypeVar("ModelT", bound="BaseModel")
HintT = typing.TypeVar("HintT")


class OrmError(Exception):
    """Базовое исключение."""


class DoesNotExist(OrmError):
    """Запись не найдена."""


class MultipleObjectsReturned(OrmError):
    """Найдено больше одной записи там, где ожидалась одна."""


class SmartRow(dict):
    """Словарь-строка, который помнит ORM-модель и умеет возвращаться обратно в модель."""

    def __init__(
        self,
        mapping: typing.Mapping[str, typing.Any] | None = None,
        *,
        _origin_qs: "QuerySetLite | None" = None,
        _origin_model: type["BaseModel"] | None = None,
        _key_mode: str = "python",
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
        _executor: "SqlExecutor | None" = None,
        _aliases: dict[str, str] | None = None,
    ) -> None:
        super().__init__(mapping or {})
        self._origin_qs = _origin_qs
        self._origin_model = _origin_model
        self._key_mode = _key_mode
        self._db = _db
        self._attach_dbs = _normalize_attach_dbs(_attach_dbs)
        self._executor = _executor
        self._aliases = dict(_aliases or {})

    @property
    def model_cls(self) -> type["BaseModel"] | None:
        return self._origin_model

    @property
    def key_mode(self) -> str:
        return self._key_mode

    def clone(self) -> "SmartRow":
        return SmartRow(
            dict(self),
            _origin_qs=self._origin_qs.clone() if self._origin_qs is not None else None,
            _origin_model=self._origin_model,
            _key_mode=self._key_mode,
            _db=self._db,
            _attach_dbs=self._attach_dbs,
            _executor=self._executor,
            _aliases=self._aliases,
        )

    def to_model(
        self,
        model_cls: type["BaseModel"] | None = None,
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: "SqlExecutor | None" = None,
        aliases: dict[str, str] | None = None,
    ) -> "BaseModel":
        model = model_cls or self._origin_model
        if model is None:
            raise OrmError("SmartRow не знает ORM-модель; передайте model_cls явно")
        return model.from_row(
            dict(self),
            db=self._db if db is None else db,
            attach_dbs=self._attach_dbs if attach_dbs is None else attach_dbs,
            executor=self._executor if executor is None else executor,
            aliases=self._aliases if aliases is None else aliases,
        )

    def to_dict(
        self,
        *,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        include_extra: bool = True,
    ) -> dict[str, typing.Any]:
        if self._origin_model is None:
            return dict(self)

        active_aliases = self._aliases if aliases is None else aliases
        model_cls = self._origin_model
        model = self.to_model(aliases=active_aliases)
        alias_map = model_cls.bind_aliases(active_aliases)

        result: dict[str, typing.Any] = {}
        used_fields: set[str] = set()
        extra_items: dict[str, typing.Any] = {}
        for raw_key, raw_value in self.items():
            field_name = model_cls.resolve_field_name(str(raw_key), aliases=active_aliases)
            if field_name in model_cls.__fields__:
                if field_name in used_fields:
                    continue
                used_fields.add(field_name)
                field = model_cls.__fields__[field_name]
                if by_aliases:
                    out_key = alias_map.get(field_name, field.db_column if by_db_columns else field_name)
                else:
                    out_key = field.db_column if by_db_columns else field_name
                result[out_key] = getattr(model, field_name)
            elif include_extra:
                extra_items[str(raw_key)] = raw_value
        if include_extra:
            result.update(extra_items)
        return result

    def by_aliases(self, aliases: dict[str, str] | None = None) -> "SmartRow":
        return SmartRow(
            self.to_dict(by_aliases=True, aliases=aliases),
            _origin_qs=self._origin_qs,
            _origin_model=self._origin_model,
            _key_mode="alias",
            _db=self._db,
            _attach_dbs=self._attach_dbs,
            _executor=self._executor,
            _aliases=self._aliases if aliases is None else aliases,
        )

    def by_db_columns(self) -> "SmartRow":
        return SmartRow(
            self.to_dict(by_db_columns=True),
            _origin_qs=self._origin_qs,
            _origin_model=self._origin_model,
            _key_mode="db",
            _db=self._db,
            _attach_dbs=self._attach_dbs,
            _executor=self._executor,
            _aliases=self._aliases,
        )

    def by_fields(self) -> "SmartRow":
        return SmartRow(
            self.to_dict(),
            _origin_qs=self._origin_qs,
            _origin_model=self._origin_model,
            _key_mode="python",
            _db=self._db,
            _attach_dbs=self._attach_dbs,
            _executor=self._executor,
            _aliases=self._aliases,
        )

class GroupByTypes(enum.Enum):
    LIST = 'list'       # Группировка по ключу {key: [values]}
    FIRST = 'first'     # По первому вхождению ключа {key: {value: 1}}
    LAST = 'last'       # По последнему вхождению ключа {key: {value: 1}}

class SmartList(list):
    """Список результатов, который помнит QuerySet/модель и умеет менять представление."""

    def __init__(
        self,
        iterable: Optional[Iterable[typing.Any]] = None,
        *,
        _origin_qs: "QuerySetLite | None" = None,
        _origin_model: type["BaseModel"] | None = None,
        _mutated: bool = False,
        _aliases: dict[str, str] | None = None,
    ):
        super().__init__(iterable or [])
        self._origin_qs = _origin_qs
        self._origin_model = _origin_model
        self._mutated = _mutated
        self._aliases = dict(_aliases or {})

    @classmethod
    def from_queryset(
        cls,
        qs: "QuerySetLite",
        *,
        by_aliases: bool = False,
        by_db_columns: bool = True,
        aliases: dict[str, str] | None = None,
    ) -> "SmartList":
        rows = qs._fetch_rows(one=False) or []
        items = [
            qs.model_cls.row_to_smartrow(
                row,
                by_aliases=by_aliases,
                by_db_columns=by_db_columns,
                aliases=aliases,
                db=qs.db,
                attach_dbs=qs.attach_dbs,
                executor=qs.executor,
                origin_qs=qs.clone(),
            )
            for row in rows
        ]
        return cls(items, _origin_qs=qs.clone(), _origin_model=qs.model_cls, _mutated=False, _aliases=aliases)

    @property
    def model_cls(self) -> type["BaseModel"] | None:
        return self._origin_model

    @property
    def is_mutated(self) -> bool:
        return bool(self._mutated)

    @property
    def can_restore_queryset(self) -> bool:
        return self._origin_qs is not None and not self._mutated

    def clone(self) -> "SmartList":
        return SmartList(
            list(self),
            _origin_qs=self._origin_qs.clone() if self._origin_qs is not None else None,
            _origin_model=self._origin_model,
            _mutated=self._mutated,
            _aliases=self._aliases,
        )

    def _mark_mutated(self):
        self._mutated = True

    def to_queryset(self) -> "QuerySetLite":
        if self._origin_qs is None:
            raise OrmError('SmartList не связан с QuerySetLite и не может быть восстановлен обратно')
        if self._mutated:
            raise OrmError('SmartList был изменен и не может быть безопасно преобразован обратно в QuerySetLite')
        return self._origin_qs.clone()

    def _as_smartrow(self, item: typing.Any, *, aliases: dict[str, str] | None = None) -> SmartRow:
        if isinstance(item, SmartRow):
            return item
        if isinstance(item, BaseModel):
            return item.to_smartrow(aliases=self._aliases if aliases is None else aliases)
        if isinstance(item, dict):
            return SmartRow(
                item,
                _origin_qs=self._origin_qs,
                _origin_model=self._origin_model,
                _key_mode="unknown",
                _db=getattr(self._origin_qs, 'db', None),
                _attach_dbs=getattr(self._origin_qs, 'attach_dbs', None),
                _executor=getattr(self._origin_qs, 'executor', None),
                _aliases=self._aliases if aliases is None else aliases,
            )
        raise TypeError(f"Нельзя преобразовать {type(item).__name__} в SmartRow")

    def to_models(
        self,
        model_cls: type["BaseModel"] | None = None,
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: "SqlExecutor | None" = None,
        aliases: dict[str, str] | None = None,
    ) -> "SmartList":
        model = model_cls or self._origin_model
        if model is None:
            raise OrmError("SmartList не знает ORM-модель; передайте model_cls явно")
        items = []
        for item in self:
            if isinstance(item, model):
                items.append(item)
            elif isinstance(item, BaseModel):
                items.append(model.from_row(item.to_dict(), db=db, attach_dbs=attach_dbs, executor=executor, aliases=aliases))
            else:
                items.append(self._as_smartrow(item, aliases=aliases).to_model(model, db=db, attach_dbs=attach_dbs, executor=executor, aliases=aliases))
        return SmartList(items, _origin_qs=self._origin_qs, _origin_model=model, _mutated=self._mutated, _aliases=aliases)

    def to_dicts(
        self,
        *,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        include_extra: bool = True,
    ) -> "SmartList":
        items = []
        for item in self:
            if isinstance(item, BaseModel):
                row = item.to_smartrow(
                    by_aliases=by_aliases,
                    by_db_columns=by_db_columns,
                    aliases=self._aliases if aliases is None else aliases,
                    include_extra=include_extra,
                )
            else:
                smart_row = self._as_smartrow(item, aliases=aliases)
                if by_aliases:
                    row = smart_row.by_aliases(self._aliases if aliases is None else aliases)
                elif by_db_columns:
                    row = smart_row.by_db_columns()
                else:
                    row = smart_row.by_fields()
            items.append(row)
        return SmartList(items, _origin_qs=self._origin_qs, _origin_model=self._origin_model, _mutated=self._mutated, _aliases=aliases)

    def by_aliases(self, aliases: dict[str, str] | None = None) -> "SmartList":
        return self.to_dicts(by_aliases=True, aliases=aliases)

    def by_db_columns(self) -> "SmartList":
        return self.to_dicts(by_db_columns=True)

    def by_fields(self) -> "SmartList":
        return self.to_dicts()

    def first(self, default: typing.Any = None) -> typing.Any:
        return self[0] if self else default

    def append(self, item):
        self._mark_mutated()
        return super().append(item)

    def extend(self, iterable):
        self._mark_mutated()
        return super().extend(iterable)

    def insert(self, index, item):
        self._mark_mutated()
        return super().insert(index, item)

    def pop(self, index=-1):
        self._mark_mutated()
        return super().pop(index)

    def remove(self, item):
        self._mark_mutated()
        return super().remove(item)

    def clear(self):
        self._mark_mutated()
        return super().clear()

    def sort(self, *args, **kwargs):
        self._mark_mutated()
        return super().sort(*args, **kwargs)

    def reverse(self):
        self._mark_mutated()
        return super().reverse()

    def __setitem__(self, key, value):
        self._mark_mutated()
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        self._mark_mutated()
        return super().__delitem__(key)

    @staticmethod
    def _ensure_dict(item: Any) -> dict:
        if isinstance(item, SmartRow):
            return item
        if isinstance(item, dict):
            return item
        if isinstance(item, BaseModel):
            return item.to_dict()
        raise TypeError(
            f"Ожидался dict/SmartRow/BaseModel, получено: {type(item).__name__}."
        )

    @staticmethod
    def _get_value(item: typing.Any, field: Union[str, Callable[[dict], Any]], default: Any = None) -> Any:
        if callable(field):
            return field(item)
        if isinstance(item, BaseModel):
            return getattr(item, field, default)
        if isinstance(item, dict):
            return item.get(field, default)
        return getattr(item, field, default)

    def group_by(
        self,
        field: Union[str, Callable[[dict], Any]],
        *,
        mode: GroupByTypes = GroupByTypes.LIST,
        item_filter: Optional[Callable[[dict], bool]] = None,
        default_key: Any = None,
    ) -> Dict[Any, Union[List[dict], dict, None]]:
        if not isinstance(mode, GroupByTypes):
            raise ValueError("mode должен быть типа Cust_orm.GroupByTypes")
        if mode == GroupByTypes.LIST:
            result: Dict[Any, List[dict]] = defaultdict(list)
        else:
            result: Dict[Any, dict] = {}
        for raw_item in self:
            item = raw_item
            if item_filter is not None and not item_filter(item):
                continue
            key = self._get_value(item, field, default=default_key)
            if mode == GroupByTypes.LIST:
                result[key].append(item)
            elif mode == GroupByTypes.FIRST:
                if key not in result:
                    result[key] = item
            elif mode == GroupByTypes.LAST:
                result[key] = item
        if mode == GroupByTypes.LIST:
            return dict(result)
        else:
            return SmartRow(result, _origin_model=self._origin_model, _origin_qs=self._origin_qs)

    def deploy_dict(
            self,
            field: Union[str, Field, Callable[[dict], Any]] = None,
            item_filter: Optional[Callable[[dict], bool]] = None
    ) -> Dict[Any, Union[List[dict], dict, None]]:
        """
        Параметры:
            field ключ группировки (например KroKases.id или 'id')
            item_filter функция фильтр, которой передается словарь текущей итерации

        Дефолтные параметры:
            field если не передан алгоритм попытается взять primary key

        Возврат:
            Структура {field: {val: 1, val: 2...}}
        """
        is_have_model = self._origin_model is not None
        if isinstance(field, Field):
            field = field.name
        if field is None:
            if is_have_model:
                field = self._origin_model.pk_name()
            else:
                raise ValueError('Ключ для deploy_by_dict не был передан')
        return self.group_by(field, item_filter=item_filter, mode=GroupByTypes.FIRST)

    def get_column_values(
        self,
        column: Union[str, Callable[[dict], Any]],
        *,
        item_filter: Optional[Callable[[dict], bool]] = None,
        converter: Optional[Callable[[Any], Any]] = None,
        skip_missing: bool = False,
        default: Any = None,
    ) -> List[Any]:
        result = []

        for raw_item in self:
            item = raw_item

            if item_filter is not None and not item_filter(item):
                continue

            if callable(column):
                value = column(item)
            else:
                if skip_missing and isinstance(item, dict) and column not in item:
                    continue
                value = self._get_value(item, column, default)

            if converter is not None:
                value = converter(value)

            result.append(value)

        return result

    def get_column_sum(
        self,
        column: Union[str, Callable[[dict], Any]],
        *,
        item_filter: Optional[Callable[[dict], bool]] = None,
        converter: Optional[Callable[[Any], Any]] = None,
        start: Any = 0,
        skip_none: bool = True,
    ) -> Any:
        total = start

        for value in self.get_column_values(
            column,
            item_filter=item_filter,
            converter=converter,
        ):
            if value is None and skip_none:
                continue
            total += value

        return total

    def sum_by(
        self,
        group_field: Union[str, Callable[[dict], Any]],
        sum_field: Union[str, Callable[[dict], Any]],
        *,
        item_filter: Optional[Callable[[dict], bool]] = None,
        converter: Optional[Callable[[Any], Any]] = None,
        start: Any = 0,
        default_key: Any = None,
        skip_none: bool = True,
    ) -> Dict[Any, Any]:
        result: Dict[Any, Any] = defaultdict(lambda: start)

        for raw_item in self:
            item = raw_item

            if item_filter is not None and not item_filter(item):
                continue

            key = self._get_value(item, group_field, default=default_key)
            value = self._get_value(item, sum_field)

            if converter is not None:
                value = converter(value)

            if value is None and skip_none:
                continue

            result[key] += value

        return dict(result)

    def left_join(
        self,
        other: Iterable[dict],
        left_on: Union[str, Callable[[dict], Any]],
        right_on: Union[str, Callable[[dict], Any]],
        *,
        how_many: str = "all",
        left_prefix: str = "",
        right_prefix: str = "r_",
        right_fields: Optional[Iterable[str]] = None,
        left_fields: Optional[Iterable[str]] = None,
        fill_none_for_missing_right: bool = False,
    ) -> "SmartList":
        if how_many not in {"all", "first", "last"}:
            raise ValueError("how_many должен быть 'all', 'first' или 'last'")

        right = SmartList(other)
        joined = SmartList()

        right_index = right.group_by(right_on, mode="list")

        for raw_left in self:
            left_item = self._ensure_dict(raw_left)
            left_key = self._get_value(left_item, left_on)
            matches = right_index.get(left_key, [])

            if not matches:
                merged = self._merge_dicts(
                    left_item,
                    None,
                    left_prefix=left_prefix,
                    right_prefix=right_prefix,
                    right_fields=right_fields,
                    left_fields=left_fields,
                )

                if fill_none_for_missing_right and right_fields is not None:
                    for field in right_fields:
                        key_name = f"{right_prefix}{field}"
                        if key_name in merged:
                            continue
                        merged[key_name] = None

                joined.append(merged)
                continue

            if how_many == "first":
                matches = matches[:1]
            elif how_many == "last":
                matches = matches[-1:]

            for match in matches:
                merged = self._merge_dicts(
                    left_item,
                    match,
                    left_prefix=left_prefix,
                    right_prefix=right_prefix,
                    right_fields=right_fields,
                    left_fields=left_fields,
                )
                joined.append(merged)

        return joined

    def right_join(
        self,
        other: Iterable[dict],
        left_on: Union[str, Callable[[dict], Any]],
        right_on: Union[str, Callable[[dict], Any]],
        *,
        how_many: str = "all",
        left_prefix: str = "l_",
        right_prefix: str = "",
        right_fields: Optional[Iterable[str]] = None,
        left_fields: Optional[Iterable[str]] = None,
        fill_none_for_missing_left: bool = False,
    ) -> "SmartList":
        other_list = SmartList(other)

        result = other_list.left_join(
            self,
            left_on=right_on,
            right_on=left_on,
            how_many=how_many,
            left_prefix=right_prefix,
            right_prefix=left_prefix,
            right_fields=left_fields,
            left_fields=right_fields,
            fill_none_for_missing_right=fill_none_for_missing_left,
        )
        return result


class SqlExecutor:

    def execute(
        self,
        bd: str,
        query: str,
        *,
        params: typing.Any = None,
        rez_dict: bool = False,
        one: bool = False,
        one_column: bool = False,
        attach_dbs: typing.Iterable[str] | str | None = (),
    ):
        if CSQ is None:
            raise RuntimeError(
                "Cust_SQLite недоступен. Передайте executor вручную либо запускайте внутри проекта."
            )

        kwargs = {
            "rez_dict": rez_dict,
            "one": one,
            "one_column": one_column,
            "attach_dbs": _normalize_attach_dbs(attach_dbs),
        }
        if params is None:
            return CSQ.custom_request_c(bd, query, **kwargs)

        normalized_params = _normalize_params(params)
        if _sql_has_returning(query):
            kwargs["list_of_lists_c"] = normalized_params
        else:
            kwargs["list_of_lists_c"] = [normalized_params]
        return CSQ.custom_request_c(bd, query, **kwargs)


_DEFAULT_EXECUTOR = SqlExecutor()


def set_default_executor(executor: SqlExecutor) -> None:
    global _DEFAULT_EXECUTOR
    _DEFAULT_EXECUTOR = executor


def get_default_executor() -> SqlExecutor:
    return _DEFAULT_EXECUTOR


@dataclasses.dataclass(frozen=True)
class SaveResult:
    """Результат сохранения одной ORM-сущности."""

    instance: "BaseModel"
    ok: bool
    created: bool = False
    updated: bool = False
    changed: bool = False
    matched: bool = False
    pk: typing.Any = None
    row: dict[str, typing.Any] | None = None
    dirty_fields: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.ok)


class ObjectManager(typing.Generic[ModelT, HintT]):
    """Менеджер операций над множеством ORM-объектов."""

    def __init__(self, model_cls: type[ModelT] | None = None) -> None:
        self.model_cls = model_cls

    def __get__(self, instance, owner: type[ModelT]) -> "ObjectManager[ModelT, HintT]":
        manager = copy.copy(self)
        manager.model_cls = owner
        manager._install_create_method()
        manager._install_update_method()
        return manager

    def _install_create_method(self) -> None:
        def create(
            *,
            _db: str | None = None,
            _attach_dbs: typing.Iterable[str] | str | None = None,
            _executor: SqlExecutor | None = None,
            **_kwargs,
        ) -> ModelT:
            return self._create(
                _db=_db,
                _attach_dbs=_attach_dbs,
                _executor=_executor,
                **_kwargs,
            )

        create.__name__ = "create"
        create.__qualname__ = f"{self.__class__.__name__}.create"
        create.__doc__ = "Создать объект модели, сохранить его и вернуть свежую ORM-сущность."
        try:
            create.__signature__ = self._create_signature()
        except Exception:
            pass
        self.create = create

    def _install_update_method(self) -> None:
        def update(
            pk: typing.Any,
            *,
            _db: str | None = None,
            _attach_dbs: typing.Iterable[str] | str | None = None,
            _executor: SqlExecutor | None = None,
            **_kwargs,
        ) -> SaveResult:
            return self._update(
                pk=pk,
                _db=_db,
                _attach_dbs=_attach_dbs,
                _executor=_executor,
                **_kwargs,
            )

        update.__name__ = "update"
        update.__qualname__ = f"{self.__class__.__name__}.update"
        update.__doc__ = "Обновить объект модели по первичному ключу и вернуть SaveResult."
        try:
            update.__signature__ = self._update_signature()
        except Exception:
            pass
        self.update = update

    def _create_signature(self) -> inspect.Signature:
        model_cls = self._ensure_model()
        annotations: dict[str, typing.Any] = {}
        for base in reversed(getattr(model_cls, "__mro__", ())):
            annotations.update(getattr(base, "__annotations__", {}) or {})
        params: list[inspect.Parameter] = [
            inspect.Parameter("_db", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=str | None),
            inspect.Parameter("_attach_dbs", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=typing.Any),
            inspect.Parameter("_executor", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=typing.Any),
        ]
        used_names = {param.name for param in params}
        for name, field in getattr(model_cls, "__fields__", {}).items():
            if not isinstance(name, str):
                continue
            if not name.isidentifier() or keyword.iskeyword(name) or name in used_names:
                continue
            default = None
            if field.default is not _EMPTY and not callable(field.default):
                try:
                    default = copy.deepcopy(field.default)
                except Exception:
                    default = None
            annotation = annotations.get(name, typing.Any)
            params.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )
            used_names.add(name)
        params.append(
            inspect.Parameter("_kwargs", inspect.Parameter.VAR_KEYWORD, annotation=typing.Any)
        )
        return inspect.Signature(params, return_annotation=model_cls)

    def _update_signature(self) -> inspect.Signature:
        model_cls = self._ensure_model()
        annotations: dict[str, typing.Any] = {}
        for base in reversed(getattr(model_cls, "__mro__", ())):
            annotations.update(getattr(base, "__annotations__", {}) or {})
        params: list[inspect.Parameter] = [
            inspect.Parameter("pk", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=typing.Any),
            inspect.Parameter("_db", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=str | None),
            inspect.Parameter("_attach_dbs", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=typing.Any),
            inspect.Parameter("_executor", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=typing.Any),
        ]
        used_names = {param.name for param in params}
        pk_name = model_cls.pk_name()
        for name, field in getattr(model_cls, "__fields__", {}).items():
            if not isinstance(name, str) or name == pk_name:
                continue
            if not name.isidentifier() or keyword.iskeyword(name) or name in used_names:
                continue
            default = None
            if field.default is not _EMPTY and not callable(field.default):
                try:
                    default = copy.deepcopy(field.default)
                except Exception:
                    default = None
            annotation = annotations.get(name, typing.Any)
            params.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )
            used_names.add(name)
        params.append(
            inspect.Parameter("_kwargs", inspect.Parameter.VAR_KEYWORD, annotation=typing.Any)
        )
        return inspect.Signature(params, return_annotation=SaveResult)

    def _ensure_model(self) -> type[ModelT]:
        if self.model_cls is None:
            raise OrmError("ObjectManager не привязан к модели")
        return self.model_cls

    def query(
        self,
        *,
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
        _executor: SqlExecutor | None = None,
    ) -> "QuerySetLite":
        return QuerySetLite(
            self._ensure_model(),
            db=_db,
            attach_dbs=_attach_dbs,
            executor=_executor,
        )

    def using(
        self,
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
    ) -> "QuerySetLite":
        return self.query(_db=_db, _attach_dbs=_attach_dbs)

    def with_executor(self, _executor: SqlExecutor) -> "QuerySetLite":
        return self.query(_executor=_executor)

    def filter(self, **_kwargs) -> "QuerySetLite":
        return self.query().filter(**_kwargs)

    def exclude(self, **_kwargs) -> "QuerySetLite":
        return self.query().exclude(**_kwargs)

    def where(self, sql: str, params: typing.Iterable[typing.Any] | None = None) -> "QuerySetLite":
        return self.query().where(sql, params=params)

    def order_by(self, *fields: str) -> "QuerySetLite":
        return self.query().order_by(*fields)

    def limit(self, value: int | None) -> "QuerySetLite":
        return self.query().limit(value)

    def all(
        self,
        *,
        model_as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
    ) -> "SmartList":
        return self.query().all(
            as_dict=model_as_dict,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    def as_smartlist(
        self,
        *,
        by_aliases: bool = False,
        by_db_columns: bool = True,
        aliases: dict[str, str] | None = None,
        **_kwargs,
    ) -> "SmartList":
        qs = self.query()
        if _kwargs:
            qs = qs.filter(**_kwargs)
        return qs.as_smartlist(
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    def values(
        self,
        *fields: str,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
    ) -> "SmartList":
        return self.query().values(
            *fields,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    def first(
        self,
        *,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        **_kwargs,
    ) -> ModelT | SmartRow | None:
        qs = self.query()
        if _kwargs:
            qs = qs.filter(**_kwargs)
        return qs.first(
            as_dict=as_dict,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    def get(
        self,
        pk: typing.Any = _EMPTY,
        *,
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
        _executor: SqlExecutor | None = None,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        **_kwargs,
    ) -> ModelT | SmartRow:
        model_cls = self._ensure_model()
        qs = self.query(_db=_db, _attach_dbs=_attach_dbs, _executor=_executor)
        if pk is not _EMPTY:
            _kwargs[model_cls.pk_name()] = pk
        return qs.get(
            as_dict=as_dict,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
            **_kwargs,
        )

    def count(self, **_kwargs) -> int:
        qs = self.query()
        if _kwargs:
            qs = qs.filter(**_kwargs)
        return qs.count()

    def _create(
        self,
        *,
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
        _executor: SqlExecutor | None = None,
        **_kwargs,
    ) -> ModelT:
        model_cls = self._ensure_model()
        obj = model_cls(_db=_db, _attach_dbs=_attach_dbs, _executor=_executor, **_kwargs)
        self.save_instance(obj, force_insert=True)
        return obj

    def _update(
        self,
        pk: typing.Any,
        *,
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
        _executor: SqlExecutor | None = None,
        **_kwargs,
    ) -> SaveResult:
        model_cls = self._ensure_model()
        unknown_fields = sorted(name for name in _kwargs if name not in model_cls.__fields__)
        if unknown_fields:
            raise OrmError(
                f"У модели {model_cls.__name__} нет полей для update: "
                f"{', '.join(repr(name) for name in unknown_fields)}"
            )

        pk_name = model_cls.pk_name()
        if pk_name in _kwargs:
            raise OrmError(
                f"Поле первичного ключа {pk_name!r} нельзя изменять через object_manager.update"
            )

        obj = self.get(
            pk=pk,
            _db=_db,
            _attach_dbs=_attach_dbs,
            _executor=_executor,
        )
        for name, value in _kwargs.items():
            setattr(obj, name, value)
        return self.save_instance_result(obj, update_fields=tuple(_kwargs))

    def save_instance(
        self,
        obj: ModelT,
        *,
        force_insert: bool = False,
        force_update: bool = False,
        update_fields: typing.Iterable[str] | None = None,
    ) -> bool:
        return bool(
            self.save_instance_result(
                obj,
                force_insert=force_insert,
                force_update=force_update,
                update_fields=update_fields,
            )
        )

    def save_instance_result(
        self,
        obj: ModelT,
        *,
        force_insert: bool = False,
        force_update: bool = False,
        update_fields: typing.Iterable[str] | None = None,
    ) -> SaveResult:
        obj._ensure_table_and_db()
        if force_insert and force_update:
            raise OrmError("force_insert и force_update одновременно использовать нельзя")

        should_insert = force_insert or not obj._persisted
        if should_insert:
            return self._insert_instance(obj)

        return self._update_instance(obj, update_fields=update_fields, force=force_update)

    def refresh_instance(self, obj: ModelT) -> ModelT:
        obj._ensure_table_and_db()
        fresh = obj.__class__.object_manager.get(
            pk=obj.pk,
            _db=obj._db,
            _attach_dbs=obj._attach_dbs,
            _executor=obj._executor,
        )
        obj._data = copy.deepcopy(fresh._data)
        obj._extra_data = copy.deepcopy(fresh._extra_data)
        obj._persisted = True
        obj._sync_original_data()
        return obj

    def delete_instance(self, obj: ModelT) -> bool:
        obj._ensure_table_and_db()
        pk_name = obj.pk_name()
        pk_value = getattr(obj, pk_name)
        if pk_value is None:
            raise OrmError("Нельзя удалить объект без первичного ключа")

        field = obj.get_field(pk_name)
        sql = f"DELETE FROM {obj.__table__} WHERE {field.db_column} = ?;"
        obj._executor.execute(
            obj._db,
            sql,
            params=[obj._prepare_db_value(pk_name, pk_value)],
            attach_dbs=obj._attach_dbs,
        )
        obj._persisted = False
        obj._original_db_data = {}
        return True

    def _insert_instance(self, obj: ModelT) -> SaveResult:
        columns: list[str] = []
        params: list[typing.Any] = []
        dirty_before = tuple(obj._dirty_fields)

        for name, field in obj.__fields__.items():
            value = obj._prepare_db_value(name, obj._data.get(name))
            if field.primary_key and value is None:
                continue
            columns.append(field.db_column)
            params.append(value)

        if not columns:
            raise OrmError(f"У модели {obj.__class__.__name__} нет данных для INSERT")

        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {obj.__table__} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *;"
        result = obj._executor.execute(
            obj._db,
            sql,
            params=params,
            attach_dbs=obj._attach_dbs,
            rez_dict=True,
            one=True,
        )
        row = self._returning_row(result)
        if row:
            obj._apply_db_row(row)
        obj._persisted = True
        obj._sync_original_data()
        return SaveResult(
            instance=obj,
            ok=True,
            created=True,
            updated=False,
            changed=True,
            matched=True,
            pk=obj.pk,
            row=row,
            dirty_fields=dirty_before,
        )

    def _update_instance(
        self,
        obj: ModelT,
        *,
        update_fields: typing.Iterable[str] | None,
        force: bool,
    ) -> SaveResult:
        pk_name = obj.pk_name()
        pk_value = getattr(obj, pk_name)
        if pk_value is None:
            raise OrmError("Нельзя обновить объект без первичного ключа")

        dirty_before = tuple(obj._dirty_fields)
        target_fields = list(update_fields) if update_fields is not None else list(dirty_before)
        target_fields = [name for name in target_fields if name != pk_name]

        if not target_fields and not force:
            return SaveResult(
                instance=obj,
                ok=False,
                created=False,
                updated=False,
                changed=False,
                matched=True,
                pk=obj.pk,
                row=None,
                dirty_fields=dirty_before,
            )

        if not target_fields and force:
            target_fields = [name for name in obj.__fields__ if name != pk_name]

        set_parts: list[str] = []
        params: list[typing.Any] = []
        for name in target_fields:
            field = obj.get_field(name)
            set_parts.append(f"{field.db_column} = ?")
            params.append(obj._prepare_db_value(name, obj._data.get(name)))

        if not set_parts:
            return SaveResult(
                instance=obj,
                ok=False,
                created=False,
                updated=False,
                changed=False,
                matched=True,
                pk=obj.pk,
                row=None,
                dirty_fields=dirty_before,
            )

        pk_field = obj.get_field(pk_name)
        params.append(obj._prepare_db_value(pk_name, pk_value))
        sql = f"UPDATE {obj.__table__} SET {', '.join(set_parts)} WHERE {pk_field.db_column} = ? RETURNING *;"
        result = obj._executor.execute(
            obj._db,
            sql,
            params=params,
            attach_dbs=obj._attach_dbs,
            rez_dict=True,
            one=True,
        )
        row = self._returning_row(result)
        if not row:
            return SaveResult(
                instance=obj,
                ok=False,
                created=False,
                updated=False,
                changed=bool(dirty_before),
                matched=False,
                pk=obj.pk,
                row=None,
                dirty_fields=dirty_before,
            )

        obj._apply_db_row(row)
        obj._persisted = True
        obj._sync_original_data()
        return SaveResult(
            instance=obj,
            ok=True,
            created=False,
            updated=True,
            changed=bool(dirty_before),
            matched=True,
            pk=obj.pk,
            row=row,
            dirty_fields=dirty_before,
        )

    @staticmethod
    def _returning_row(result: typing.Any) -> dict[str, typing.Any] | None:
        if isinstance(result, dict):
            return result or None
        if isinstance(result, list):
            if not result:
                return None
            first = result[0]
            if isinstance(first, dict):
                return first
        return None


class Field:
    """Базовое поле модели."""

    python_type: type | None = None

    def __init__(
        self,
        *,
        db_column: str | None = None,
        default: typing.Any = _EMPTY,
        nullable: bool = True,
        primary_key: bool = False,
        preserve_blank: bool = False,
    ) -> None:
        self.name: str | None = None
        self.model: type[BaseModel] | None = None
        self.db_column = db_column
        self.default = default
        self.nullable = nullable
        self.primary_key = primary_key
        self.preserve_blank = preserve_blank

    def clone(self) -> "Field":
        return copy.copy(self)

    def __set_name__(self, owner: type[BaseModel], name: str) -> None:
        self.bind(owner, name)

    def bind(self, owner: type[BaseModel], name: str) -> None:
        self.model = owner
        self.name = name
        if self.db_column is None:
            self.db_column = name

    def __get__(self, instance: BaseModel | None, owner: type[BaseModel]):
        if instance is None:
            return self
        return instance._data.get(self.name, self.get_default())

    def __set__(self, instance: BaseModel, value: typing.Any) -> None:
        instance._assign_field(self.name, value, from_db=False)

    def get_default(self) -> typing.Any:
        if self.default is _EMPTY:
            return None
        return self.default() if callable(self.default) else copy.deepcopy(self.default)

    def to_python(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        return value

    def to_db(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        return value

    @classmethod
    def from_annotation(cls, annotation: typing.Any, **kwargs) -> "Field":
        base = _unwrap_optional(annotation)
        mapping: dict[typing.Any, type[Field]] = {
            int: IntField,
            float: FloatField,
            str: StrField,
            bool: BoolField,
            bytes: BlobField,
            _dt.datetime: DateTimeField,
            _dt.date: DateTimeField,
        }
        field_cls = mapping.get(base, Field)
        return field_cls(**kwargs)


class IntField(Field):
    python_type = int

    def to_python(self, value: typing.Any) -> int | None | str:
        if value in (None, ""):
            return "" if value == "" and self.preserve_blank else None
        if isinstance(value, bool):
            return int(value)
        return int(value)

    def to_db(self, value: typing.Any) -> typing.Any:
        if value in (None, ""):
            return "" if value == "" and self.preserve_blank else None
        return int(value)


class FloatField(Field):
    python_type = float

    def to_python(self, value: typing.Any) -> float | None | str:
        if value in (None, ""):
            return "" if value == "" and self.preserve_blank else None
        return float(value)

    def to_db(self, value: typing.Any) -> typing.Any:
        if value in (None, ""):
            return "" if value == "" and self.preserve_blank else None
        return float(value)


class StrField(Field):
    python_type = str

    def to_python(self, value: typing.Any) -> str | None:
        if value is None:
            return None
        return str(value)

    def to_db(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        return str(value)


class BoolField(Field):
    python_type = bool

    TRUE_VALUES = {True, 1, "1", "true", "True", "да", "Да", "yes", "Yes"}
    FALSE_VALUES = {False, 0, "0", "false", "False", "нет", "Нет", "no", "No"}

    def to_python(self, value: typing.Any) -> bool | None:
        if value is None:
            return None
        if value in self.TRUE_VALUES:
            return True
        if value in self.FALSE_VALUES:
            return False
        return bool(value)

    def to_db(self, value: typing.Any) -> int | None:
        if value is None:
            return None
        return int(bool(value))


class DateTimeField(Field):
    python_type = _dt.datetime

    def to_python(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        if isinstance(value, (_dt.datetime, _dt.date)):
            return value
        return value

    def to_db(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        if isinstance(value, _dt.datetime):
            return value.isoformat(sep=" ")
        if isinstance(value, _dt.date):
            return value.isoformat()
        return value


class BlobField(Field):
    python_type = bytes

    def to_python(self, value: typing.Any) -> bytes | None:
        if value is None:
            return None
        if isinstance(value, memoryview):
            return value.tobytes()
        if isinstance(value, bytearray):
            return bytes(value)
        return value

    def to_db(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        if isinstance(value, bytearray):
            return bytes(value)
        return value


class JsonTextField(StrField):
    """Текстовое поле с json-объектом внутри."""

    def to_python(self, value: typing.Any) -> typing.Any:
        if value in (None, ""):
            return None
        if isinstance(value, (dict, list, tuple, int, float, bool)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return value

    def to_db(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)


class ListTextField(StrField):
    """Список, сериализуемый в строку через разделитель."""

    def __init__(self, *args, sep: str = "|", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sep = sep

    def to_python(self, value: typing.Any) -> list[typing.Any] | None:
        if value in (None, ""):
            return [] if value == "" else None
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return str(value).split(self.sep)

    def to_db(self, value: typing.Any) -> typing.Any:
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            return self.sep.join(str(item) for item in value)
        return str(value)


class QuerySetLite:
    def __init__(
        self,
        model_cls: type[ModelT],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        conditions: list[tuple[str, str, typing.Any, bool]] | None = None,
        orderings: list[str] | None = None,
        limit_value: int | None = None,
        where_sql: list[tuple[str, list[typing.Any]]] | None = None,
    ) -> None:
        self.model_cls = model_cls
        self.db = db if db is not None else model_cls.resolve_db()
        self.attach_dbs = _normalize_attach_dbs(
            attach_dbs if attach_dbs is not None else model_cls.resolve_attach_dbs()
        )
        self.executor = executor or get_default_executor()
        self._conditions = conditions[:] if conditions else []
        self._orderings = orderings[:] if orderings else []
        self._limit = limit_value
        self._where_sql = copy.deepcopy(where_sql) if where_sql else []

    def clone(self) -> "QuerySetLite":
        return QuerySetLite(
            self.model_cls,
            db=self.db,
            attach_dbs=self.attach_dbs,
            executor=self.executor,
            conditions=self._conditions,
            orderings=self._orderings,
            limit_value=self._limit,
            where_sql=self._where_sql,
        )

    def using(self, db: str | None = None, attach_dbs: typing.Iterable[str] | str | None = None) -> "QuerySetLite":
        clone = self.clone()
        if db is not None:
            clone.db = db
        if attach_dbs is not None:
            clone.attach_dbs = _normalize_attach_dbs(attach_dbs)
        return clone

    def with_executor(self, executor: SqlExecutor) -> "QuerySetLite":
        clone = self.clone()
        clone.executor = executor
        return clone

    def filter(self, **kwargs) -> "QuerySetLite":
        clone = self.clone()
        for key, value in kwargs.items():
            name, lookup = self._split_lookup(key)
            clone._validate_field(name)
            clone._conditions.append((name, lookup, value, False))
        return clone

    def exclude(self, **kwargs) -> "QuerySetLite":
        clone = self.clone()
        for key, value in kwargs.items():
            name, lookup = self._split_lookup(key)
            clone._validate_field(name)
            clone._conditions.append((name, lookup, value, True))
        return clone

    def where(self, sql: str, params: typing.Iterable[typing.Any] | None = None) -> "QuerySetLite":
        clone = self.clone()
        clone._where_sql.append((sql.strip(), list(params or [])))
        return clone

    def order_by(self, *fields: str) -> "QuerySetLite":
        clone = self.clone()
        for field_name in fields:
            if not field_name:
                continue
            raw_name = field_name[1:] if field_name.startswith("-") else field_name
            if raw_name != "pk":
                clone._validate_field(raw_name)
            clone._orderings.append(field_name)
        return clone

    def limit(self, value: int | None) -> "QuerySetLite":
        clone = self.clone()
        clone._limit = value
        return clone

    def _row_to_result(
        self,
        row: dict[str, typing.Any],
        *,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
    ) -> ModelT | SmartRow:
        if as_dict or by_aliases or by_db_columns:
            return self.model_cls.row_to_smartrow(
                row,
                by_aliases=by_aliases,
                by_db_columns=by_db_columns,
                aliases=aliases,
                db=self.db,
                attach_dbs=self.attach_dbs,
                executor=self.executor,
                origin_qs=self.clone(),
            )
        return self.model_cls.from_row(
            row,
            db=self.db,
            attach_dbs=self.attach_dbs,
            executor=self.executor,
            aliases=aliases,
        )

    def all(
        self,
        *,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
    ) -> SmartList:
        rows = self._fetch_rows(one=False) or []
        items = [
            self._row_to_result(
                row,
                as_dict=as_dict,
                by_aliases=by_aliases,
                by_db_columns=by_db_columns,
                aliases=aliases,
            )
            for row in rows
        ]
        return SmartList(items, _origin_qs=self.clone(), _origin_model=self.model_cls, _mutated=False, _aliases=aliases)

    def as_smartlist(
        self,
        *,
        by_aliases: bool = False,
        by_db_columns: bool = True,
        aliases: dict[str, str] | None = None,
    ) -> SmartList:
        return SmartList.from_queryset(
            self,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    def values(
        self,
        *fields: str,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
    ) -> SmartList:
        rows = self._fetch_rows(one=False) or []
        selected: list[SmartRow] = []
        resolved_fields = [self.model_cls.resolve_field_name(field, aliases=aliases) for field in fields]
        for row in rows:
            data = self.model_cls.normalize_row_keys(row, aliases=aliases, include_unknown=True)
            if resolved_fields:
                data = {field: data.get(field) for field in resolved_fields}
            smart_row = SmartRow(
                data,
                _origin_qs=self.clone(),
                _origin_model=self.model_cls,
                _key_mode="python",
                _db=self.db,
                _attach_dbs=self.attach_dbs,
                _executor=self.executor,
                _aliases=self.model_cls.bind_aliases(aliases),
            )
            if by_aliases:
                smart_row = smart_row.by_aliases(aliases)
            elif by_db_columns:
                smart_row = smart_row.by_db_columns()
            selected.append(smart_row)
        return SmartList(selected, _origin_qs=self.clone(), _origin_model=self.model_cls, _mutated=False, _aliases=aliases)

    def first(
        self,
        *,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
    ) -> ModelT | SmartRow | None:
        row = self.limit(1)._fetch_rows(one=True)
        if not row:
            return None
        return self._row_to_result(
            row,
            as_dict=as_dict,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    def get(
        self,
        *,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        **kwargs,
    ) -> ModelT | SmartRow:
        qs = self.filter(**kwargs) if kwargs else self
        rows = qs.limit(2)._fetch_rows(one=False)
        if not rows:
            raise self.model_cls.DoesNotExist(
                f"{self.model_cls.__name__} не найден по условиям {kwargs or 'без условий'}"
            )
        if len(rows) > 1:
            raise self.model_cls.MultipleObjectsReturned(
                f"{self.model_cls.__name__} вернул больше одной записи по условиям {kwargs}"
            )
        return qs._row_to_result(
            rows[0],
            as_dict=as_dict,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    def count(self) -> int:
        sql, params = self._build_select_sql(columns="COUNT(*) as cnt", for_count=True)
        row = self.executor.execute(
            self.db,
            sql,
            params=params,
            rez_dict=True,
            one=True,
            attach_dbs=self.attach_dbs,
        )
        if not row:
            return 0
        return int(row["cnt"])

    def _fetch_rows(self, *, one: bool) -> typing.Any:
        sql, params = self._build_select_sql()
        return self.executor.execute(
            self.db,
            sql,
            params=params,
            rez_dict=True,
            one=one,
            attach_dbs=self.attach_dbs,
        )

    def _build_select_sql(self, *, columns: str | None = None, for_count: bool = False) -> tuple[str, list[typing.Any]]:
        columns = columns or "*"
        sql = f"SELECT {columns} FROM {self.model_cls.__table__}"
        where_parts: list[str] = []
        params: list[typing.Any] = []

        for name, lookup, value, negated in self._conditions:
            field = self.model_cls.get_field(name)
            clause, clause_params = self._build_condition(field, lookup, value)
            if negated:
                clause = f"NOT ({clause})"
            where_parts.append(clause)
            params.extend(clause_params)

        for raw_sql, raw_params in self._where_sql:
            where_parts.append(f"({raw_sql})")
            params.extend(raw_params)

        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        if self._orderings and not for_count:
            chunks = []
            for item in self._orderings:
                descending = item.startswith("-")
                name = item[1:] if descending else item
                field = self.model_cls.get_field(name)
                chunks.append(f"{field.db_column} {'DESC' if descending else 'ASC'}")
            sql += " ORDER BY " + ", ".join(chunks)

        if self._limit is not None and not for_count:
            sql += f" LIMIT {int(self._limit)}"

        sql += ";"
        return sql, params

    def _build_condition(self, field: Field, lookup: str, value: typing.Any) -> tuple[str, list[typing.Any]]:
        column = field.db_column

        if lookup == "exact":
            if value is None:
                return f"{column} IS NULL", []
            return f"{column} = ?", [self.model_cls.prepare_db_value(field.name, value)]

        if lookup == "in":
            values = list(value or [])
            if not values:
                return "1 = 0", []
            placeholders = ", ".join("?" for _ in values)
            db_values = [self.model_cls.prepare_db_value(field.name, item) for item in values]
            return f"{column} IN ({placeholders})", db_values

        if lookup == "isnull":
            return (f"{column} IS NULL", []) if value else (f"{column} IS NOT NULL", [])

        if lookup in {"gt", "gte", "lt", "lte"}:
            op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
            return f"{column} {op_map[lookup]} ?", [self.model_cls.prepare_db_value(field.name, value)]

        if lookup in {"contains", "icontains"}:
            pattern = f"%{value}%"
            if lookup == "icontains":
                return f"LOWER({column}) LIKE LOWER(?)", [pattern]
            return f"{column} LIKE ?", [pattern]

        raise OrmError(f"Неподдерживаемый lookup: {lookup}")

    def _validate_field(self, name: str) -> None:
        self.model_cls.get_field(name)

    def _split_lookup(self, key: str) -> tuple[str, str]:
        if key == "pk":
            return self.model_cls.pk_name(), "exact"
        if "__" not in key:
            return key, "exact"
        name, lookup = key.rsplit("__", 1)
        if name == "pk":
            name = self.model_cls.pk_name()
        return name, lookup


class ModelMeta(type):
    """Собирает декларативные поля модели."""

    def __new__(mcls, name, bases, namespace, **kwargs):
        annotations: dict[str, typing.Any] = {}
        inherited_fields: OrderedDict[str, Field] = OrderedDict()

        for base in bases:
            annotations.update(getattr(base, "__annotations__", {}))
            for field_name, field in getattr(base, "__fields__", {}).items():
                inherited_fields[field_name] = field.clone()

        annotations.update(namespace.get("__annotations__", {}))

        new_namespace = dict(namespace)
        for field_name, field in inherited_fields.items():
            if field_name not in new_namespace:
                new_namespace[field_name] = field

        for field_name, annotation in annotations.items():
            if field_name.startswith("_"):
                continue
            attr = new_namespace.get(field_name, _EMPTY)
            if isinstance(attr, Field):
                continue
            if attr is _EMPTY:
                new_namespace[field_name] = Field.from_annotation(annotation)

        for attr_name, attr_value in list(new_namespace.items()):
            if attr_name.startswith("_"):
                continue
            if isinstance(attr_value, Field) and attr_name not in annotations:
                annotations[attr_name] = typing.Any

        cls = super().__new__(mcls, name, bases, new_namespace)

        fields: OrderedDict[str, Field] = OrderedDict()
        for base in bases:
            fields.update(getattr(base, "__fields__", {}))
        for attr_name in annotations:
            if attr_name.startswith("_"):
                continue
            attr_value = getattr(cls, attr_name, None)
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
        for attr_name, attr_value in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value

        cls.__fields__ = fields
        cls.__field_by_column__ = {field.db_column: name for name, field in fields.items()}

        relations: OrderedDict[str, typing.Any] = OrderedDict()
        for base in bases:
            relations.update(getattr(base, "__relations__", {}) or {})
        for attr_name, attr_value in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if getattr(attr_value, "__mes_relationship__", False):
                relations[attr_name] = attr_value
        cls.__relations__ = relations

        pk_name = getattr(cls, "__pk__", None)
        if pk_name is None:
            for field_name, field in fields.items():
                if field.primary_key:
                    pk_name = field_name
                    break
        if pk_name is None and "id" in fields:
            pk_name = "id"
        cls.__pk__ = pk_name

        if "object_manager" not in cls.__dict__:
            cls.object_manager = ObjectManager()

        cls.DoesNotExist = type(f"{name}DoesNotExist", (DoesNotExist,), {})
        cls.MultipleObjectsReturned = type(
            f"{name}MultipleObjectsReturned", (MultipleObjectsReturned,), {}
        )
        return cls


class BaseModel(typing.Generic[HintT], metaclass=ModelMeta):
    __abstract__ = True
    __table__: str | None = None
    # Static identity is deliberately separate from __db__. Reading relation
    # metadata must never call a DB/config-resolving callable.
    __db_key__: str = ''
    __canonical_db_key__: str = ''
    __table_key__: str = ''
    __db__: str | typing.Callable[[], str] | None = None
    __attach_dbs__: tuple[str, ...] | list[str] | str | None = ()
    __pk__: str | None = None
    ALIASES: dict[str, str] = {}

    object_manager = ObjectManager()

    def __init__(
        self,
        _persisted: bool = False,
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
        _executor: SqlExecutor | None = None,
        **_kwargs,
    ) -> None:
        self._data: dict[str, typing.Any] = {}
        self._extra_data: dict[str, typing.Any] = {}
        self._persisted = _persisted
        self._db = _db if _db is not None else self.resolve_db()
        self._attach_dbs = _normalize_attach_dbs(
            _attach_dbs if _attach_dbs is not None else self.resolve_attach_dbs()
        )
        self._executor = _executor or get_default_executor()
        self._original_db_data: dict[str, typing.Any] = {}

        for name, field in self.__fields__.items():
            self._data[name] = field.get_default()

        for key, value in _kwargs.items():
            if key in self.__fields__:
                self._assign_field(key, value, from_db=_persisted)
            elif key in self.__field_by_column__:
                self._assign_field(self.__field_by_column__[key], value, from_db=_persisted)
            else:
                self._extra_data[key] = value

        if _persisted:
            self._sync_original_data()

    def __repr__(self) -> str:
        pk_name = self.pk_name()
        pk_value = getattr(self, pk_name) if pk_name else None
        return f"<{self.__class__.__name__} pk={pk_value!r} persisted={self._persisted}>"

    @classmethod
    def resolve_db(cls) -> str | None:
        db = getattr(cls, "__db__", None)
        if callable(db):
            return db()
        return db

    @classmethod
    def resolve_attach_dbs(cls) -> tuple[str, ...]:
        return _normalize_attach_dbs(getattr(cls, "__attach_dbs__", ()))

    @classmethod
    def pk_name(cls) -> str:
        if not cls.__pk__:
            raise OrmError(f"У модели {cls.__name__} не определен __pk__")
        return cls.__pk__

    @property
    def pk(self) -> typing.Any:
        return getattr(self, self.pk_name())

    @classmethod
    def get_field(cls, name: str) -> Field:
        if name not in cls.__fields__:
            raise OrmError(f"У модели {cls.__name__} нет поля {name!r}")
        return cls.__fields__[name]

    @classmethod
    def get_relation(cls, name: str):
        if name not in getattr(cls, "__relations__", {}):
            raise OrmError(f"У модели {cls.__name__} нет связи {name!r}")
        return cls.__relations__[name]

    @classmethod
    def relation_specs(cls, *, strict: bool = True) -> dict[str, typing.Any]:
        """Return normalized relation metadata.

        Generated relations are part of the model contract. Silently returning a
        descriptor after a resolution error made schema audits look successful
        while runtime access failed later. ``strict=False`` remains available for
        legacy diagnostics, but normal callers fail closed.
        """
        result: dict[str, typing.Any] = {}
        for name, relation in (getattr(cls, "__relations__", {}) or {}).items():
            if hasattr(relation, "as_relation_spec") and callable(relation.as_relation_spec):
                try:
                    result[name] = relation.as_relation_spec(cls)
                    continue
                except Exception:
                    if strict:
                        raise
            result[name] = relation
        return result

    @classmethod
    def bind_aliases(cls, aliases: dict[str, str] | None = None) -> dict[str, str]:
        """Вернуть нормализованную карту python_field -> alias для модели."""
        raw_aliases: dict[str, str] = {}
        for attr_name in ("ALIASES", "__aliases__", "DICT_ALIASES"):
            value = getattr(cls, attr_name, None)
            if isinstance(value, dict):
                raw_aliases.update(value)
        if aliases:
            raw_aliases.update(aliases)

        result: dict[str, str] = {}
        for raw_key, raw_alias in raw_aliases.items():
            if raw_alias in (None, ""):
                continue
            key = str(raw_key)
            if key in cls.__fields__:
                field_name = key
            elif key in cls.__field_by_column__:
                field_name = cls.__field_by_column__[key]
            else:
                continue
            result[field_name] = str(raw_alias)
        return result

    @classmethod
    def alias_to_field_map(cls, aliases: dict[str, str] | None = None) -> dict[str, str]:
        return {alias: field_name for field_name, alias in cls.bind_aliases(aliases).items()}

    @classmethod
    def resolve_field_name(cls, key: str, aliases: dict[str, str] | None = None) -> str:
        key = str(key)
        if key in cls.__fields__:
            return key
        if key in cls.__field_by_column__:
            return cls.__field_by_column__[key]
        alias_map = cls.alias_to_field_map(aliases)
        if key in alias_map:
            return alias_map[key]
        return key

    @classmethod
    def normalize_row_keys(
        cls,
        row: dict[str, typing.Any],
        *,
        aliases: dict[str, str] | None = None,
        include_unknown: bool = True,
    ) -> dict[str, typing.Any]:
        result: dict[str, typing.Any] = {}
        for key, value in (row or {}).items():
            field_name = cls.resolve_field_name(str(key), aliases=aliases)
            if field_name in cls.__fields__:
                result[field_name] = value
            elif include_unknown:
                result[str(key)] = value
        return result

    @classmethod
    def row_to_smartrow(
        cls,
        row: dict[str, typing.Any],
        *,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        origin_qs: "QuerySetLite | None" = None,
    ) -> SmartRow:
        model = cls.from_row(row, db=db, attach_dbs=attach_dbs, executor=executor, aliases=aliases)
        key_mode = "python"
        if by_aliases:
            key_mode = "alias"
        elif by_db_columns:
            key_mode = "db"
        return SmartRow(
            model.to_dict(by_aliases=by_aliases, by_db_columns=by_db_columns, aliases=aliases),
            _origin_qs=origin_qs,
            _origin_model=cls,
            _key_mode=key_mode,
            _db=db,
            _attach_dbs=attach_dbs,
            _executor=executor,
            _aliases=cls.bind_aliases(aliases),
        )

    @classmethod
    def prepare_db_value(cls, field_name: str, value: typing.Any) -> typing.Any:
        field = cls.get_field(field_name)
        serializer = getattr(cls, f"serialize_{field_name}", None)
        if serializer and callable(serializer):
            value = serializer(value)
        return field.to_db(value)

    def _prepare_db_value(self, field_name: str, value: typing.Any) -> typing.Any:
        serializer = getattr(self, f"serialize_{field_name}", None)
        if serializer and callable(serializer):
            value = serializer(value)
        return self.get_field(field_name).to_db(value)

    def _assign_field(self, name: str, value: typing.Any, *, from_db: bool) -> None:
        field = self.get_field(name)
        if from_db:
            deserializer = getattr(self, f"deserialize_{name}", None)
            if deserializer and callable(deserializer):
                value = deserializer(value)
        else:
            cleaner = getattr(self, f"clean_{name}", None)
            if cleaner and callable(cleaner):
                value = cleaner(value)

        if value is None and field.default is not _EMPTY and not from_db:
            value = field.get_default()

        if value is None and not field.nullable and field.default is _EMPTY:
            raise ValueError(f"Поле {name} не допускает None")

        self._data[name] = field.to_python(value)

    def _current_db_snapshot(self) -> dict[str, typing.Any]:
        snapshot = {}
        for name in self.__fields__:
            snapshot[name] = self._prepare_db_value(name, self._data.get(name))
        return snapshot

    def _sync_original_data(self) -> None:
        self._original_db_data = self._current_db_snapshot()

    def _apply_db_row(self, row: dict[str, typing.Any]) -> None:
        for key, value in (row or {}).items():
            if key in self.__fields__:
                self._assign_field(key, value, from_db=True)
            elif key in self.__field_by_column__:
                self._assign_field(self.__field_by_column__[key], value, from_db=True)
            else:
                self._extra_data[key] = value

    @property
    def _dirty_fields(self) -> list[str]:
        current = self._current_db_snapshot()
        if not self._persisted:
            return [name for name, value in current.items() if value is not None]
        return [name for name, value in current.items() if self._original_db_data.get(name) != value]

    @property
    def dirty_fields(self) -> list[str]:
        return self._dirty_fields

    @classmethod
    def query(
        cls: type[ModelT],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
    ) -> QuerySetLite:
        return cls.object_manager.query(_db=db, _attach_dbs=attach_dbs, _executor=executor)

    @classmethod
    def filter(cls: type[ModelT], **kwargs) -> QuerySetLite:
        return cls.object_manager.filter(**kwargs)

    @classmethod
    def exclude(cls: type[ModelT], **kwargs) -> QuerySetLite:
        return cls.object_manager.exclude(**kwargs)

    @classmethod
    def where(cls: type[ModelT], sql: str, params: typing.Iterable[typing.Any] | None = None) -> QuerySetLite:
        return cls.object_manager.where(sql, params=params)

    @classmethod
    def order_by(cls: type[ModelT], *fields: str) -> QuerySetLite:
        return cls.object_manager.order_by(*fields)

    # @classmethod
    # def all(
    #     cls: type[ModelT],
    #     *,
    #     as_dict: bool = False,
    #     by_aliases: bool = False,
    #     by_db_columns: bool = False,
    #     aliases: dict[str, str] | None = None,
    # ) -> SmartList:
    #     return cls.object_manager.all(
    #         as_dict=as_dict,
    #         by_aliases=by_aliases,
    #         by_db_columns=by_db_columns,
    #         aliases=aliases,
    #     )

    # @classmethod
    # def as_smartlist(
    #     cls: type[ModelT],
    #     *,
    #     by_aliases: bool = False,
    #     by_db_columns: bool = True,
    #     aliases: dict[str, str] | None = None,
    #     **kwargs,
    # ) -> SmartList:
    #     return cls.object_manager.as_smartlist(
    #         by_aliases=by_aliases,
    #         by_db_columns=by_db_columns,
    #         aliases=aliases,
    #         **kwargs,
    #     )

    # @classmethod
    def values(
        cls: type[ModelT],
        *fields: str,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
    ) -> SmartList:
        return cls.object_manager.values(
            *fields,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
        )

    @classmethod
    def first(
        cls: type[ModelT],
        *,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        **kwargs,
    ) -> ModelT | SmartRow | None:
        return cls.object_manager.first(
            as_dict=as_dict,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
            **kwargs,
        )

    @classmethod
    def get(
        cls: type[ModelT],
        pk: typing.Any = _EMPTY,
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        as_dict: bool = False,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        **kwargs,
    ) -> ModelT | SmartRow:
        return cls.object_manager.get(
            pk=pk,
            _db=db,
            _attach_dbs=attach_dbs,
            _executor=executor,
            as_dict=as_dict,
            by_aliases=by_aliases,
            by_db_columns=by_db_columns,
            aliases=aliases,
            **kwargs,
        )

    @classmethod
    def count(cls: type[ModelT], **kwargs) -> int:
        return cls.object_manager.count(**kwargs)

    @classmethod
    def create(
        cls: type[ModelT],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        **_kwargs,
    ) -> ModelT:
        return cls.object_manager.create(
            _db=db,
            _attach_dbs=attach_dbs,
            _executor=executor,
            **_kwargs,
        )

    @classmethod
    def from_row(
        cls: type[ModelT],
        row: dict[str, typing.Any],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        aliases: dict[str, str] | None = None,
    ) -> ModelT:
        normalized_row = cls.normalize_row_keys(row, aliases=aliases, include_unknown=True)
        return cls(
            _persisted=True,
            _db=db,
            _attach_dbs=attach_dbs,
            _executor=executor,
            **normalized_row,
        )
    @classmethod
    def from_rows(
        cls: type[ModelT],
        rows: list[dict[str, typing.Any]],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        aliases: dict[str, str] | None = None,
    ) -> list[ModelT]:
        return SmartList([
            cls(
                _persisted=True,
                _db=db,
                _attach_dbs=attach_dbs,
                _executor=executor,
                **cls.normalize_row_keys(row, aliases=aliases, include_unknown=True),
            )
             for row in rows
        ], _origin_model=cls)

    def to_dict(
        self,
        *,
        by_db_columns: bool = False,
        by_aliases: bool = False,
        aliases: dict[str, str] | None = None,
        include_extra: bool = False,
    ) -> dict[str, typing.Any]:
        result = {}
        alias_map = self.bind_aliases(aliases)
        for name, field in self.__fields__.items():
            if by_aliases:
                key = alias_map.get(name, field.db_column if by_db_columns else name)
            else:
                key = field.db_column if by_db_columns else name
            result[key] = getattr(self, name)
        if include_extra:
            result.update(self._extra_data)
        return result

    def to_smartrow(
        self,
        *,
        by_aliases: bool = False,
        by_db_columns: bool = False,
        aliases: dict[str, str] | None = None,
        include_extra: bool = False,
        origin_qs: "QuerySetLite | None" = None,
    ) -> SmartRow:
        key_mode = "alias" if by_aliases else "db" if by_db_columns else "python"
        return SmartRow(
            self.to_dict(
                by_aliases=by_aliases,
                by_db_columns=by_db_columns,
                aliases=aliases,
                include_extra=include_extra,
            ),
            _origin_qs=origin_qs,
            _origin_model=self.__class__,
            _key_mode=key_mode,
            _db=self._db,
            _attach_dbs=self._attach_dbs,
            _executor=self._executor,
            _aliases=self.bind_aliases(aliases),
        )

    def clone(self: ModelT, *, reset_pk: bool = False) -> ModelT:
        data = self.to_dict()
        if reset_pk:
            data[self.pk_name()] = None
        return self.__class__(
            _persisted=False,
            _db=self._db,
            _attach_dbs=self._attach_dbs,
            _executor=self._executor,
            **data,
        )

    def save(
        self,
        *,
        force_insert: bool = False,
        force_update: bool = False,
        update_fields: typing.Iterable[str] | None = None,
    ) -> bool:
        return self.__class__.object_manager.save_instance(
            self,
            force_insert=force_insert,
            force_update=force_update,
            update_fields=update_fields,
        )

    def save_result(
        self,
        *,
        force_insert: bool = False,
        force_update: bool = False,
        update_fields: typing.Iterable[str] | None = None,
    ) -> SaveResult:
        return self.__class__.object_manager.save_instance_result(
            self,
            force_insert=force_insert,
            force_update=force_update,
            update_fields=update_fields,
        )

    def update(self, **kwargs) -> bool:
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.save(force_update=True)

    def refresh(self) -> "BaseModel":
        return self.__class__.object_manager.refresh_instance(self)

    def delete(self) -> bool:
        return self.__class__.object_manager.delete_instance(self)

    def _insert(self) -> bool:
        return bool(self.__class__.object_manager._insert_instance(self))

    def _update(self, *, update_fields: typing.Iterable[str] | None, force: bool) -> bool:
        return bool(
            self.__class__.object_manager._update_instance(
                self,
                update_fields=update_fields,
                force=force,
            )
        )

    def _ensure_table_and_db(self) -> None:
        if not self.__table__:
            raise OrmError(f"У модели {self.__class__.__name__} не задан __table__")
        if not self._db:
            raise OrmError(
                f"У модели {self.__class__.__name__} не задана база данных. "
                f"Передайте _db/db или определите __db__."
            )


def _sql_has_returning(query: str) -> bool:
    return " RETURNING " in f" {str(query or '').upper()} "


def _normalize_attach_dbs(value: typing.Iterable[str] | str | None) -> tuple[str, ...]:
    if value in (None, (), [], ""):
        return tuple()
    if isinstance(value, str):
        return (value,)
    return tuple(item for item in value if item)


def _normalize_params(params: typing.Any) -> typing.Any:
    """Приведение параметров к безопасному для custom_request_c виду."""
    if params is None:
        return [[]]
    if isinstance(params, tuple):
        return list(params)
    if isinstance(params, list):
        return params
    return [params]


def _unwrap_optional(annotation: typing.Any) -> typing.Any:
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


# Optional relation layer re-export. Kept at the end to avoid an import cycle:
# context_relations is ORM-agnostic and only duck-types Field/BaseModel objects.
try:  # production package path
    from project_cust_38.context_relations import (  # type: ignore
        FieldRef,
        TableRef,
        RelationFieldPair,
        RelationSpec,
        Relationship,
    )
except Exception:
    try:  # local isolated tests
        from context_relations import (  # type: ignore
            FieldRef,
            TableRef,
            RelationFieldPair,
            RelationSpec,
            Relationship,
        )
    except Exception:
        pass
