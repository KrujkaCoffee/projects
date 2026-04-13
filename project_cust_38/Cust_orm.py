from __future__ import annotations

from collections import OrderedDict
import copy
import datetime as _dt
import json
import typing

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
    "QuerySetLite",
    "BaseModel",
]


_EMPTY = object()
T = typing.TypeVar("T", bound="BaseModel")


class OrmError(Exception):
    """Базовое исключение."""


class DoesNotExist(OrmError):
    """Запись не найдена."""


class MultipleObjectsReturned(OrmError):
    """Найдено больше одной записи там, где ожидалась одна."""


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

        kwargs["list_of_lists_c"] = _normalize_params(params)
        return CSQ.custom_request_c(bd, query, **kwargs)


_DEFAULT_EXECUTOR = SqlExecutor()


def set_default_executor(executor: SqlExecutor) -> None:
    global _DEFAULT_EXECUTOR
    _DEFAULT_EXECUTOR = executor


def get_default_executor() -> SqlExecutor:
    return _DEFAULT_EXECUTOR


class Manager:
    """Минимальный аналог Django objects manager."""

    def __get__(self, instance, owner: type[BaseModel]) -> "QuerySetLite":
        return QuerySetLite(owner)


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
        # В проекте много дат хранится строками; на Stage 1 не форсируем парсинг.
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
    """Облегченный query builder."""

    def __init__(
        self,
        model_cls: type[T],
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

    def all(self) -> list[T]:
        rows = self._fetch_rows(one=False)
        return [self.model_cls.from_row(row, db=self.db, attach_dbs=self.attach_dbs, executor=self.executor) for row in rows]

    def first(self) -> T | None:
        row = self.limit(1)._fetch_rows(one=True)
        if not row:
            return None
        return self.model_cls.from_row(row, db=self.db, attach_dbs=self.attach_dbs, executor=self.executor)

    def get(self, **kwargs) -> T:
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
        return self.model_cls.from_row(rows[0], db=self.db, attach_dbs=self.attach_dbs, executor=self.executor)

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

        pk_name = getattr(cls, "__pk__", None)
        if pk_name is None:
            for field_name, field in fields.items():
                if field.primary_key:
                    pk_name = field_name
                    break
        if pk_name is None and "id" in fields:
            pk_name = "id"
        cls.__pk__ = pk_name

        if "objects" not in cls.__dict__:
            cls.objects = Manager()

        cls.DoesNotExist = type(f"{name}DoesNotExist", (DoesNotExist,), {})
        cls.MultipleObjectsReturned = type(
            f"{name}MultipleObjectsReturned", (MultipleObjectsReturned,), {}
        )
        return cls


class BaseModel(metaclass=ModelMeta):
    __abstract__ = True
    __table__: str | None = None
    __db__: str | typing.Callable[[], str] | None = None
    __attach_dbs__: tuple[str, ...] | list[str] | str | None = ()
    __pk__: str | None = None

    objects = Manager()

    def __init__(
        self,
        _persisted: bool = False,
        _db: str | None = None,
        _attach_dbs: typing.Iterable[str] | str | None = None,
        _executor: SqlExecutor | None = None,
        **kwargs,
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

        for key, value in kwargs.items():
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

    @property
    def dirty_fields(self) -> list[str]:
        current = self._current_db_snapshot()
        if not self._persisted:
            return [name for name, value in current.items() if value is not None]
        return [name for name, value in current.items() if self._original_db_data.get(name) != value]

    @classmethod
    def query(
        cls: type[T],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
    ) -> QuerySetLite:
        return QuerySetLite(cls, db=db, attach_dbs=attach_dbs, executor=executor)

    @classmethod
    def filter(cls: type[T], **kwargs) -> QuerySetLite:
        return cls.query().filter(**kwargs)

    @classmethod
    def all(cls: type[T]) -> list[T]:
        return cls.query().all()

    @classmethod
    def first(cls: type[T], **kwargs) -> T | None:
        qs = cls.query()
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs.first()

    @classmethod
    def get(
        cls: type[T],
        pk: typing.Any = _EMPTY,
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        **kwargs,
    ) -> T:
        qs = cls.query(db=db, attach_dbs=attach_dbs, executor=executor)
        if pk is not _EMPTY:
            kwargs[cls.pk_name()] = pk
        return qs.get(**kwargs)

    @classmethod
    def create(
        cls: type[T],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
        **kwargs: typing.TypedDict[T.__dict__],
    ) -> T:
        obj = cls(_db=db, _attach_dbs=attach_dbs, _executor=executor, **kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    def from_row(
        cls: type[T],
        row: dict[str, typing.Any],
        *,
        db: str | None = None,
        attach_dbs: typing.Iterable[str] | str | None = None,
        executor: SqlExecutor | None = None,
    ) -> T:
        return cls(
            _persisted=True,
            _db=db,
            _attach_dbs=attach_dbs,
            _executor=executor,
            **row,
        )

    def to_dict(self, *, by_db_columns: bool = False, include_extra: bool = False) -> dict[str, typing.Any]:
        result = {}
        for name, field in self.__fields__.items():
            key = field.db_column if by_db_columns else name
            result[key] = getattr(self, name)
        if include_extra:
            result.update(self._extra_data)
        return result

    def clone(self: T, *, reset_pk: bool = False) -> T:
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
        self._ensure_table_and_db()
        if force_insert and force_update:
            raise OrmError("force_insert и force_update одновременно использовать нельзя")

        should_insert = force_insert or not self._persisted
        if should_insert:
            return self._insert()

        return self._update(update_fields=update_fields, force=force_update)

    def update(self, **kwargs) -> bool:
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.save(force_update=True)

    def refresh(self) -> "BaseModel":
        self._ensure_table_and_db()
        fresh = self.__class__.get(
            pk=self.pk,
            db=self._db,
            attach_dbs=self._attach_dbs,
            executor=self._executor,
        )
        self._data = copy.deepcopy(fresh._data)
        self._extra_data = copy.deepcopy(fresh._extra_data)
        self._persisted = True
        self._sync_original_data()
        return self

    def delete(self) -> bool:
        self._ensure_table_and_db()
        pk_name = self.pk_name()
        pk_value = getattr(self, pk_name)
        if pk_value is None:
            raise OrmError("Нельзя удалить объект без первичного ключа")

        field = self.get_field(pk_name)
        sql = f"DELETE FROM {self.__table__} WHERE {field.db_column} = ?;"
        self._executor.execute(
            self._db,
            sql,
            params=[self._prepare_db_value(pk_name, pk_value)],
            attach_dbs=self._attach_dbs,
        )
        self._persisted = False
        self._original_db_data = {}
        return True

    def _insert(self) -> bool:
        columns: list[str] = []
        params: list[typing.Any] = []

        for name, field in self.__fields__.items():
            value = self._prepare_db_value(name, self._data.get(name))
            if field.primary_key and value is None:
                continue
            columns.append(field.db_column)
            params.append(value)

        if not columns:
            raise OrmError(f"У модели {self.__class__.__name__} нет данных для INSERT")

        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {self.__table__} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *;"
        result = self._executor.execute(self._db, sql, params=params, attach_dbs=self._attach_dbs, rez_dict=True)
        self._persisted = True
        self._sync_original_data()
        return True

    def _update(self, *, update_fields: typing.Iterable[str] | None, force: bool) -> bool:
        pk_name = self.pk_name()
        pk_value = getattr(self, pk_name)
        if pk_value is None:
            raise OrmError("Нельзя обновить объект без первичного ключа")

        target_fields = list(update_fields) if update_fields is not None else self.dirty_fields
        target_fields = [name for name in target_fields if name != pk_name]

        if not target_fields and not force:
            return False

        if not target_fields and force:
            target_fields = [name for name in self.__fields__ if name != pk_name]

        set_parts: list[str] = []
        params: list[typing.Any] = []
        for name in target_fields:
            field = self.get_field(name)
            set_parts.append(f"{field.db_column} = ?")
            params.append(self._prepare_db_value(name, self._data.get(name)))

        if not set_parts:
            return False

        pk_field = self.get_field(pk_name)
        params.append(self._prepare_db_value(pk_name, pk_value))
        sql = f"UPDATE {self.__table__} SET {', '.join(set_parts)} WHERE {pk_field.db_column} = ?;"
        self._executor.execute(self._db, sql, params=[params], attach_dbs=self._attach_dbs)
        self._persisted = True
        self._sync_original_data()
        return True

    def _ensure_table_and_db(self) -> None:
        if not self.__table__:
            raise OrmError(f"У модели {self.__class__.__name__} не задан __table__")
        if not self._db:
            raise OrmError(
                f"У модели {self.__class__.__name__} не задана база данных. "
                f"Передайте _db/db или определите __db__."
            )


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
    if origin is typing.Union:
        args = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation
