"""Виртуальные регистры состояния MES в одном production-модуле.

Модуль import-safe: обычный import не загружает CFG, Cust_SQLite,
context_admin, generated ORM models и не обращается к БД. Инфраструктура
поднимается лениво только при build/get и первом фактическом запросе.

Архитектурное объединение выполнено намеренно: production-развёртывание MES
требует одного файла вместо package registers/*.py.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import importlib
import json
import keyword
import pathlib
import re
import sqlite3
import threading
from collections import OrderedDict
from types import ModuleType
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Mapping,
    Protocol,
    Sequence,
    TypeVar,
    TypedDict,
    cast,
)



# ==============================================================================
# ОШИБКИ
# ==============================================================================

class RegisterError(Exception):
    """Базовая ошибка подсистемы регистров."""


class RegisterDeclarationError(RegisterError):
    """Декларация регистра противоречива или не поддерживается текущим runtime."""


class RegisterQueryError(RegisterError):
    """Публичный запрос к регистру сформирован некорректно."""


class RegisterDataError(RegisterError):
    """Источник регистра содержит данные, которые нельзя трактовать однозначно."""


class RegisterCardinalityError(RegisterDataError):
    """Relation, объявленная как one-shaped, размножила строку регистра."""


class RegisterSourceUnavailable(RegisterError):
    """Источник регистра или SQL executor недоступен."""


# ==============================================================================
# МЕТАДАННЫЕ ДЕКЛАРАЦИЙ
# ==============================================================================

_HIDDEN_PREFIX = "__register_"


def quote_ident(value: str) -> str:
    """Кавычки SQLite identifier. Значения этим методом не экранируются."""
    return '"' + str(value).replace('"', '""') + '"'




@dataclasses.dataclass(frozen=True)
class ModelIdentity:
    """Точная identity generated ORM без исправления и нормализации ключей."""

    model: Any
    table_name: str
    table_key: str
    db_key: str
    pk_name: str


@dataclasses.dataclass(frozen=True)
class FieldRef:
    model: Any
    python_name: str
    db_column: str

    @property
    def identity(self) -> tuple[int, str, str]:
        return id(self.model), self.python_name, self.db_column


@dataclasses.dataclass(frozen=True)
class KeyField:
    public_name: str
    field: FieldRef


@dataclasses.dataclass(frozen=True)
class OutputField:
    field: Any
    output_name: str


@dataclasses.dataclass(frozen=True)
class DirectOutput:
    field: FieldRef
    output_name: str


@dataclasses.dataclass(frozen=True)
class RegisterDefinition:
    code: str
    title: str
    source: ModelIdentity
    keys: tuple[KeyField, ...]
    period: FieldRef
    outputs: tuple[Any, ...]
    tie_breakers: tuple[FieldRef, ...]
    strict_dates: bool = True
    notes: str = ""
    content_hash: str = ""

    @property
    def version(self) -> str:
        return self.content_hash[:12]


def named(field: Any, as_: str) -> OutputField:
    """Задать понятное имя прямому полю в результате регистра."""
    output_name = _clean_output_name(as_)
    return OutputField(field=field, output_name=output_name)


def _clean_output_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise RegisterDeclarationError("Имя выходного поля не может быть пустым")
    if text.startswith(_HIDDEN_PREFIX):
        raise RegisterDeclarationError(
            f"Префикс {_HIDDEN_PREFIX!r} зарезервирован runtime регистров"
        )
    return text


def _clean_public_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise RegisterDeclarationError("Публичное имя ключа не может быть пустым")
    if not text.isidentifier() or keyword.iskeyword(text):
        raise RegisterDeclarationError(
            f"Публичное имя ключа {text!r} должно быть корректным Python identifier"
        )
    if text.startswith("_"):
        raise RegisterDeclarationError(
            f"Публичное имя ключа {text!r} не должно начинаться с '_'"
        )
    return text


def resolve_model_identity(model: Any) -> ModelIdentity:
    """Прочитать точную identity ORM-модели.

    Stage 2.1 сознательно не исправляет и не нормализует ключи. Generated ORM
    обязана содержать однородную пару::

        __db_key__ = "Naryad"
        __table_key__ = "Naryad.naryad"

    Путь/``SRV:`` здесь не вычисляется: production executor получает
    физическую БД из ``CSQ.Servers`` только при фактическом запросе.
    """
    if not isinstance(model, type):
        raise RegisterDeclarationError(
            f"source должен быть ORM-классом, получено {model!r}"
        )

    table_name = str(getattr(model, "__table__", "") or "").strip()
    db_key = str(getattr(model, "__db_key__", "") or "").strip()
    table_key = str(getattr(model, "__table_key__", "") or "").strip()

    if not table_name:
        raise RegisterDeclarationError(
            f"ORM-модель {getattr(model, '__name__', model)!r} не содержит __table__"
        )
    if not db_key:
        raise RegisterDeclarationError(
            f"ORM-модель {getattr(model, '__name__', model)!r} не содержит точный __db_key__"
        )
    if not table_key:
        raise RegisterDeclarationError(
            f"ORM-модель {getattr(model, '__name__', model)!r} не содержит точный __table_key__"
        )

    expected_table_key = f"{db_key}.{table_name}"
    if table_key != expected_table_key:
        raise RegisterDeclarationError(
            f"Неконсистентная identity модели {getattr(model, '__name__', model)!r}: "
            f"__table_key__={table_key!r}, ожидается {expected_table_key!r}. "
            "Автоматическая нормализация запрещена."
        )


    pk_name = ""
    pk_getter = getattr(model, "pk_name", None)
    if callable(pk_getter):
        try:
            pk_name = str(pk_getter() or "")
        except Exception:
            pk_name = ""
    pk_name = pk_name or str(getattr(model, "__pk__", "") or "")
    if not pk_name:
        fields = getattr(model, "__fields__", {}) or {}
        for field_name, field in fields.items():
            if bool(getattr(field, "primary_key", False)):
                pk_name = str(field_name)
                break
    if not pk_name:
        raise RegisterDeclarationError(
            f"У модели {getattr(model, '__name__', model)!r} не найден первичный ключ; "
            "для регистра состояния нужен стабильный tie-breaker"
        )

    return ModelIdentity(
        model=model,
        table_name=table_name,
        table_key=table_key,
        db_key=db_key,
        pk_name=pk_name,
    )


def resolve_field(field: Any, *, expected_model: Any | None = None) -> FieldRef:
    if isinstance(field, str):
        raise RegisterDeclarationError(
            f"Строковая ссылка на поле {field!r} запрещена в публичной декларации регистра; "
            "передайте generated ORM field"
        )
    python_name = str(getattr(field, "name", "") or "").strip()
    db_column = str(getattr(field, "db_column", "") or python_name).strip()
    model = getattr(field, "model", None)
    if not python_name or not db_column or model is None:
        raise RegisterDeclarationError(
            f"Объект {field!r} не похож на связанное ORM-поле "
            "(нужны name, db_column и model)"
        )
    if expected_model is not None and model is not expected_model:
        expected_table = getattr(expected_model, "__table_key__", getattr(expected_model, "__name__", expected_model))
        actual_table = getattr(model, "__table_key__", getattr(model, "__name__", model))
        raise RegisterDeclarationError(
            f"Поле {python_name!r} принадлежит {actual_table!r}, ожидалась модель {expected_table!r}"
        )
    return FieldRef(model=model, python_name=python_name, db_column=db_column)


def resolve_keys(key: Any, *, source_model: Any) -> tuple[KeyField, ...]:
    if isinstance(key, Mapping):
        items = list(key.items())
    elif isinstance(key, (list, tuple)):
        items = [(None, item) for item in key]
    else:
        items = [(None, key)]
    if not items:
        raise RegisterDeclarationError("StateRegister требует хотя бы один ключ сущности")
    result: list[KeyField] = []
    seen_public: set[str] = set()
    seen_fields: set[tuple[int, str, str]] = set()
    for public_name, field in items:
        ref = resolve_field(field, expected_model=source_model)
        public = _clean_public_name(public_name if public_name is not None else ref.python_name)
        if public in seen_public:
            raise RegisterDeclarationError(f"Публичный ключ {public!r} объявлен повторно")
        if ref.identity in seen_fields:
            raise RegisterDeclarationError(f"Поле ключа {ref.python_name!r} объявлено повторно")
        seen_public.add(public)
        seen_fields.add(ref.identity)
        result.append(KeyField(public_name=public, field=ref))
    return tuple(result)


def resolve_outputs(fields: Iterable[Any], *, source_model: Any) -> tuple[Any, ...]:
    result: list[Any] = []
    output_names: set[str] = set()
    for item in tuple(fields or ()):
        if isinstance(item, OutputField):
            ref = resolve_field(item.field, expected_model=source_model)
            output_name = _clean_output_name(item.output_name)
            normalized: Any = DirectOutput(field=ref, output_name=output_name)
        elif _is_relation_projection(item):
            # Полная проверка relation откладывается до SQL compiler: там уже
            # разрешается target model и field_pairs. Здесь достаточно убедиться,
            # что projection не является строковой заглушкой.
            normalized = item
            projection_names = _projection_output_names(item)
            for name in projection_names:
                clean = _clean_output_name(name)
                if clean in output_names:
                    raise RegisterDeclarationError(f"Выходное поле {clean!r} объявлено повторно")
                output_names.add(clean)
            result.append(normalized)
            continue
        else:
            ref = resolve_field(item, expected_model=source_model)
            output_name = ref.python_name
            normalized = DirectOutput(field=ref, output_name=output_name)
        if normalized.output_name in output_names:
            raise RegisterDeclarationError(
                f"Выходное поле {normalized.output_name!r} объявлено повторно"
            )
        output_names.add(normalized.output_name)
        result.append(normalized)
    if not result:
        raise RegisterDeclarationError(
            "StateRegister требует явный fields=(...); скрытый SELECT * не используется"
        )
    return tuple(result)


def _is_relation_projection(value: Any) -> bool:
    return (
        hasattr(value, "relationship")
        and hasattr(value, "fields")
        and hasattr(value, "aliases")
    )


def _projection_output_names(projection: Any) -> tuple[str, ...]:
    fields = tuple(getattr(projection, "fields", ()) or ())
    aliases = tuple(getattr(projection, "aliases", ()) or ())
    prefix = str(getattr(projection, "prefix", "") or "").strip()
    rel = getattr(projection, "relationship", None)
    rel_name = str(getattr(rel, "name", "") or "relation")
    if aliases:
        if len(aliases) != len(fields):
            raise RegisterDeclarationError(
                "Число aliases в relation projection не совпадает с числом полей"
            )
        return tuple(str(item) for item in aliases)
    result = []
    for field in fields:
        ref = resolve_field(field)
        result.append(f"{prefix or rel_name}.{ref.python_name}")
    return tuple(result)


def resolve_tie_breakers(
    value: Iterable[Any] | Any | None,
    *,
    source: ModelIdentity,
) -> tuple[FieldRef, ...]:
    if value is None:
        pk_field = getattr(source.model, source.pk_name, None)
        if pk_field is None:
            pk_field = (getattr(source.model, "__fields__", {}) or {}).get(source.pk_name)
        refs = (resolve_field(pk_field, expected_model=source.model),)
    else:
        items = value if isinstance(value, (list, tuple)) else (value,)
        refs = tuple(resolve_field(item, expected_model=source.model) for item in items)
    if not refs:
        raise RegisterDeclarationError("Нужен хотя бы один стабильный tie-breaker")
    return refs


def build_definition(
    *,
    code: str,
    title: str,
    source_model: Any,
    key: Any,
    period: Any,
    fields: Iterable[Any],
    tie_breaker: Iterable[Any] | Any | None = None,
    strict_dates: bool = True,
    notes: str = "",
) -> RegisterDefinition:
    code = str(code or "").strip()
    if not code or not code.isidentifier() or keyword.iskeyword(code) or code.startswith("_"):
        raise RegisterDeclarationError(
            f"Код регистра {code!r} должен быть публичным Python identifier"
        )
    source = resolve_model_identity(source_model)
    keys = resolve_keys(key, source_model=source.model)
    period_ref = resolve_field(period, expected_model=source.model)
    outputs = resolve_outputs(fields, source_model=source.model)
    tie_breakers = resolve_tie_breakers(tie_breaker, source=source)
    definition = RegisterDefinition(
        code=code,
        title=str(title or code).strip(),
        source=source,
        keys=keys,
        period=period_ref,
        outputs=outputs,
        tie_breakers=tie_breakers,
        strict_dates=bool(strict_dates),
        notes=str(notes or ""),
    )
    payload = definition_manifest(definition, include_hash=False)
    content_hash = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return dataclasses.replace(definition, content_hash=content_hash)


def _relation_manifest(definition: RegisterDefinition, projection: Any) -> dict[str, Any]:
    relationship = getattr(projection, "relationship", None)
    if relationship is None or not callable(getattr(relationship, "as_relation_spec", None)):
        raise RegisterDeclarationError(
            f"Объект {projection!r} не является Relationship.select(...) projection"
        )
    spec = relationship.as_relation_spec(owner=definition.source.model).normalized()
    target_model = getattr(spec, "target_model", None)
    if target_model is None:
        target_model = getattr(getattr(spec, "target_table", None), "model", None)
    target = resolve_model_identity(target_model)
    selected_fields = [
        resolve_field(field, expected_model=target.model)
        for field in tuple(getattr(projection, "fields", ()) or ())
    ]
    output_names = list(_projection_output_names(projection))
    pairs = []
    for pair in spec.resolved_pairs():
        pairs.append({
            "left_field": pair.left_field.field_name,
            "left_db_column": pair.left_field.db_column or pair.left_field.field_name,
            "right_field": pair.right_field.field_name,
            "right_db_column": pair.right_field.db_column or pair.right_field.field_name,
            "role": str(pair.role or "direct"),
            "operator": str(pair.operator or "="),
            "pair_join_type": str(pair.pair_join_type or ""),
        })
    return {
        "kind": "relation",
        "relation": str(getattr(relationship, "name", "") or spec.relation_name or ""),
        "relation_key": str(spec.relation_key or ""),
        "source_table_key": definition.source.table_key,
        "target_table_key": target.table_key,
        "target_db_key": target.db_key,
        "cardinality": str(spec.cardinality or ""),
        "join_type": str(spec.join_type or ""),
        "missing_policy": str(spec.missing_policy or ""),
        "on_many": str(getattr(spec, "on_many", "") or ""),
        "pairs": pairs,
        "fields": [item.python_name for item in selected_fields],
        "db_columns": [item.db_column for item in selected_fields],
        "outputs": output_names,
        "aliases": list(getattr(projection, "aliases", ()) or ()),
        "prefix": str(getattr(projection, "prefix", "") or ""),
        "required": bool(getattr(projection, "required", False)),
    }


def definition_manifest(definition: RegisterDefinition, *, include_hash: bool = True) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    dependencies = [definition.source.table_key]
    for item in definition.outputs:
        if isinstance(item, DirectOutput):
            outputs.append({
                "kind": "field",
                "field": item.field.python_name,
                "db_column": item.field.db_column,
                "output": item.output_name,
            })
        else:
            relation_data = _relation_manifest(definition, item)
            outputs.append(relation_data)
            target_key = str(relation_data.get("target_table_key") or "")
            if target_key and target_key not in dependencies:
                dependencies.append(target_key)
    result = {
        "code": definition.code,
        "title": definition.title,
        "source": {
            "table_key": definition.source.table_key,
            "db_key": definition.source.db_key,
            "table_name": definition.source.table_name,
        },
        "keys": [
            {
                "public_name": item.public_name,
                "field": item.field.python_name,
                "db_column": item.field.db_column,
            }
            for item in definition.keys
        ],
        "period": {
            "field": definition.period.python_name,
            "db_column": definition.period.db_column,
        },
        "tie_breakers": [
            {"field": item.python_name, "db_column": item.db_column}
            for item in definition.tie_breakers
        ],
        "outputs": outputs,
        "dependencies": dependencies,
        "strict_dates": definition.strict_dates,
        "notes": definition.notes,
    }
    if include_hash:
        result["content_hash"] = definition.content_hash
        result["version"] = definition.version
    return result


def _safe_relation_key(relationship: Any) -> str:
    getter = getattr(relationship, "relation_key", None)
    if callable(getter):
        try:
            return str(getter() or "")
        except Exception:
            return ""
    return str(getattr(relationship, "_relation_key_override", "") or "")


def parse_moment(value: Any, *, parameter: str = "date") -> _dt.datetime:
    if isinstance(value, _dt.datetime):
        result = value
    elif isinstance(value, _dt.date):
        result = _dt.datetime.combine(value, _dt.time.min)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise RegisterQueryError(f"Параметр {parameter!r} не может быть пустым")
        try:
            result = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RegisterQueryError(
                f"Параметр {parameter!r} должен быть ISO-датой/датой-временем, получено {value!r}"
            ) from exc
    else:
        raise RegisterQueryError(
            f"Параметр {parameter!r} должен быть date/datetime/ISO str, получено {type(value).__name__}"
        )
    if result.tzinfo is not None and result.utcoffset() is not None:
        raise RegisterQueryError(
            f"Параметр {parameter!r} содержит timezone, а MES-источники хранят локальное naive-время"
        )
    return result.replace(tzinfo=None)


def moment_to_sql(value: _dt.datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")


def parse_key_arguments(
    definition: RegisterDefinition,
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
) -> OrderedDict[str, Any]:
    key_names = [item.public_name for item in definition.keys]
    if len(args) > len(key_names):
        raise RegisterQueryError(
            f"Регистр {definition.code!r} ожидает {len(key_names)} ключ(а/ей), получено {len(args)}"
        )
    result: OrderedDict[str, Any] = OrderedDict()
    for index, value in enumerate(args):
        result[key_names[index]] = value
    unknown = set(kwargs) - set(key_names)
    if unknown:
        raise RegisterQueryError(
            f"Неизвестные ключи регистра {definition.code!r}: {sorted(unknown)!r}; "
            f"ожидаются {key_names!r}"
        )
    for name in key_names:
        if name in kwargs:
            if name in result:
                raise RegisterQueryError(f"Ключ {name!r} передан и позиционно, и по имени")
            result[name] = kwargs[name]
    missing = [name for name in key_names if name not in result]
    if missing:
        raise RegisterQueryError(
            f"Не заданы ключи регистра {definition.code!r}: {missing!r}"
        )
    return result


# ==============================================================================
# ИСПОЛНИТЕЛИ SQL
# ==============================================================================

class RegisterExecutor(Protocol):
    def fetch_all(
        self,
        db: str,
        sql: str,
        params: Sequence[Any] = (),
        *,
        attach_dbs: Sequence[str] = (),
    ) -> list[dict[str, Any]]:
        ...


def _strip_sql_literals_and_comments(sql: str) -> str:
    """Оставить только исполняемые токены SQL.

    Значения/quoted identifiers заменяются пробелами, чтобы слово DELETE внутри
    строки или имени поля не считалось оператором. Функция не является общим SQL
    parser; она намеренно консервативна для SQL, который генерирует register core.
    """
    text = str(sql or "")
    out: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        nxt = text[index + 1] if index + 1 < length else ""
        if char == "-" and nxt == "-":
            out.extend("  ")
            index += 2
            while index < length and text[index] not in "\r\n":
                out.append(" ")
                index += 1
            continue
        if char == "/" and nxt == "*":
            out.extend("  ")
            index += 2
            while index < length:
                if text[index] == "*" and index + 1 < length and text[index + 1] == "/":
                    out.extend("  ")
                    index += 2
                    break
                out.append(" ")
                index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            out.append(" ")
            index += 1
            while index < length:
                out.append(" ")
                if text[index] == quote:
                    if index + 1 < length and text[index + 1] == quote:
                        out.append(" ")
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if char == "[":
            out.append(" ")
            index += 1
            while index < length:
                out.append(" ")
                if text[index] == "]":
                    index += 1
                    break
                index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _ensure_readonly_sql(sql: str) -> None:
    cleaned = _strip_sql_literals_and_comments(sql).strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    if ";" in cleaned:
        raise RegisterQueryError("Runtime регистров запрещает несколько SQL statements")
    head = cleaned.split(None, 1)[0].upper() if cleaned else ""
    if head not in {"SELECT", "WITH", "EXPLAIN"}:
        raise RegisterQueryError(
            f"Runtime регистров выполняет только read-only SQL, получено начало {head!r}"
        )
    tokens = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", cleaned.upper()))
    forbidden = {
        "INSERT", "UPDATE", "DELETE", "REPLACE", "UPSERT",
        "CREATE", "DROP", "ALTER", "TRUNCATE",
        "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX", "ANALYZE",
        "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE",
        "LOAD_EXTENSION",
    }
    found = sorted(tokens.intersection(forbidden))
    if found:
        raise RegisterQueryError(
            f"Runtime регистров отклонил потенциально изменяющий SQL: {found!r}"
        )


def _normalize_rows(result: Any, *, source: str) -> list[dict[str, Any]]:
    if result in (None, False):
        raise RegisterSourceUnavailable(
            f"Источник {source!r} не вернул данные для read-only запроса регистра"
        )
    if not isinstance(result, list):
        raise RegisterSourceUnavailable(
            f"Источник {source!r} вернул неожиданный тип {type(result).__name__}; ожидался list[Mapping]"
        )
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(result):
        if not isinstance(row, Mapping):
            raise RegisterSourceUnavailable(
                f"Источник {source!r} вернул строку #{index} типа {type(row).__name__}; "
                "ожидался Mapping"
            )
        rows.append(dict(row))
    return rows


class MesSqlExecutor:
    """Production adapter поверх ``Cust_SQLite.custom_request_c``.

    На вход принимает только точные ``db_key`` generated ORM. Физический
    ``_ServerItem`` берётся по точному имени ``<db_key>.db`` из единого реестра
    ``CSQ.Servers``. В старых сборках имя реестра ``CSQ.DB_NAMES`` поддержано
    лишь как API-совместимый alias; перебора вариантов и нормализации ключей нет.
    """

    def __init__(
        self,
        custom_request: Callable[..., Any] | None = None,
        servers: Any | None = None,
    ) -> None:
        self._custom_request = custom_request
        self._servers = servers
        self._csq_module: ModuleType | None = None

    def _load_csq(self) -> ModuleType:
        if self._csq_module is not None:
            return self._csq_module
        try:
            module = importlib.import_module("project_cust_38.Cust_SQLite")
        except Exception as exc:
            raise RegisterSourceUnavailable(
                "Не удалось лениво загрузить project_cust_38.Cust_SQLite"
            ) from exc
        self._csq_module = module
        return module

    def _request(self) -> Callable[..., Any]:
        if self._custom_request is not None:
            return self._custom_request
        module = self._load_csq()
        try:
            fn = getattr(module, "custom_request_c")
        except AttributeError as exc:
            raise RegisterSourceUnavailable(
                "В project_cust_38.Cust_SQLite отсутствует custom_request_c"
            ) from exc
        self._custom_request = fn
        return fn

    def _server_registry(self):
        if self._servers is not None:
            return self._servers
        module = self._load_csq()
        registry = getattr(module, "Servers", None)
        if registry is None:
            registry = getattr(module, "DB_NAMES", None)
        if registry is None:
            raise RegisterSourceUnavailable(
                "Cust_SQLite не экспортирует единый реестр Servers/DB_NAMES"
            )
        self._servers = registry
        return registry

    def _server(self, db_key: str):
        key = str(db_key or "").strip()
        if not key or "." in key or key.upper().startswith("SRV:"):
            raise RegisterSourceUnavailable(
                f"Ожидался точный db_key generated ORM, получено {db_key!r}"
            )
        alias = f"{key}.db"
        try:
            server = self._server_registry()[alias]
        except Exception as exc:
            raise RegisterSourceUnavailable(
                f"CSQ.Servers не содержит точную БД {alias!r} для db_key={key!r}"
            ) from exc
        if server is None:
            raise RegisterSourceUnavailable(
                f"CSQ.Servers не содержит точную БД {alias!r} для db_key={key!r}"
            )
        declared_alias = str(getattr(server, "alias", alias) or alias)
        if declared_alias != alias:
            raise RegisterSourceUnavailable(
                f"CSQ.Servers вернул {declared_alias!r} вместо ожидаемой {alias!r}"
            )
        return server

    def fetch_all(
        self,
        db: str,
        sql: str,
        params: Sequence[Any] = (),
        *,
        attach_dbs: Sequence[str] = (),
    ) -> list[dict[str, Any]]:
        _ensure_readonly_sql(sql)
        fn = self._request()
        main_server = self._server(db)
        attach_servers = tuple(self._server(item) for item in tuple(attach_dbs or ()))
        packed_params = [list(params)] if params else [[]]
        try:
            result = fn(
                main_server,
                sql,
                list_of_lists_c=packed_params,
                rez_dict=True,
                hat_c=False,
                one=False,
                attach_dbs=attach_servers,
            )
        except Exception as exc:
            raise RegisterSourceUnavailable(
                f"Ошибка чтения регистра из db_key={db!r}: {type(exc).__name__}: {exc}"
            ) from exc
        return _normalize_rows(result, source=db)


class CallableExecutor:
    """Адаптер для тестов/внешнего транспорта."""

    def __init__(self, fn: Callable[..., Any]) -> None:
        if not callable(fn):
            raise TypeError("CallableExecutor требует callable")
        self.fn = fn

    def fetch_all(
        self,
        db: str,
        sql: str,
        params: Sequence[Any] = (),
        *,
        attach_dbs: Sequence[str] = (),
    ) -> list[dict[str, Any]]:
        _ensure_readonly_sql(sql)
        try:
            result = self.fn(db=db, sql=sql, params=tuple(params), attach_dbs=tuple(attach_dbs))
        except Exception as exc:
            raise RegisterSourceUnavailable(
                f"Callable executor завершился ошибкой для {db!r}: {type(exc).__name__}: {exc}"
            ) from exc
        return _normalize_rows(result, source=db or "callable")




class SqliteExecutor:
    """Прямой read-only SQLite executor для тестов и shadow-сравнения.

    ``db_paths`` — явная карта точных ``db_key -> файл``. Никакого поиска по
    ``SRV:``, basename, legacy alias или каталогу не выполняется.
    """

    def __init__(
        self,
        db_paths: Mapping[str, str | pathlib.Path],
        *,
        trace: list[dict[str, Any]] | None = None,
    ) -> None:
        if not isinstance(db_paths, Mapping) or not db_paths:
            raise RegisterSourceUnavailable(
                "SqliteExecutor требует непустую точную карту db_paths={db_key: file}"
            )
        self.db_paths = {
            str(key).strip(): pathlib.Path(value)
            for key, value in db_paths.items()
        }
        if any(not key for key in self.db_paths):
            raise RegisterSourceUnavailable("SqliteExecutor получил пустой db_key")
        self.trace = trace

    def _path(self, db_key: str) -> pathlib.Path:
        key = str(db_key or "").strip()
        if key not in self.db_paths:
            raise RegisterSourceUnavailable(
                f"SqliteExecutor не содержит точный db_key {key!r}; "
                f"доступны {sorted(self.db_paths)!r}"
            )
        path = self.db_paths[key]
        if not path.is_file():
            raise RegisterSourceUnavailable(
                f"SQLite-файл для db_key={key!r} не найден: {str(path)!r}"
            )
        return path

    @staticmethod
    def _uri(path: pathlib.Path) -> str:
        return path.resolve().as_uri() + "?mode=ro"

    def fetch_all(
        self,
        db: str,
        sql: str,
        params: Sequence[Any] = (),
        *,
        attach_dbs: Sequence[str] = (),
    ) -> list[dict[str, Any]]:
        _ensure_readonly_sql(sql)
        main_path = self._path(db)
        if self.trace is not None:
            self.trace.append({
                "db": db,
                "sql": sql,
                "params": tuple(params),
                "attach_dbs": tuple(attach_dbs),
            })

        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(self._uri(main_path), uri=True, timeout=4)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only = ON")
            used_aliases: set[str] = {"main", "temp", str(db)}
            for attach_key in tuple(attach_dbs or ()):
                attach_key = str(attach_key)
                attach_path = self._path(attach_key)
                if attach_key in used_aliases:
                    if attach_path.resolve() == main_path.resolve():
                        continue
                    raise RegisterSourceUnavailable(
                        f"Конфликт SQLite attach alias {attach_key!r}"
                    )
                used_aliases.add(attach_key)
                conn.execute(
                    f"ATTACH DATABASE ? AS {quote_ident(attach_key)}",
                    (self._uri(attach_path),),
                )
            cursor = conn.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            raise RegisterSourceUnavailable(
                f"SQLite read-only запрос регистра завершился ошибкой: {exc}"
            ) from exc
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass


def default_executor() -> RegisterExecutor:
    return MesSqlExecutor()


# ==============================================================================
# SQL-КОМПИЛЯТОР
# ==============================================================================

@dataclasses.dataclass(frozen=True)
class RequiredMarker:
    alias: str
    relation_name: str


@dataclasses.dataclass(frozen=True)
class QueryPlan:
    operation: str
    db: str
    sql: str
    params: tuple[Any, ...]
    attach_dbs: tuple[str, ...]
    output_names: tuple[str, ...]
    source_identity_aliases: tuple[str, ...]
    required_markers: tuple[RequiredMarker, ...] = ()


@dataclasses.dataclass(frozen=True)
class _SelectPlan:
    select_sql: tuple[str, ...]
    join_sql: tuple[str, ...]
    attach_dbs: tuple[str, ...]
    output_names: tuple[str, ...]
    source_identity_aliases: tuple[str, ...]
    required_markers: tuple[RequiredMarker, ...]


class RegisterSqlCompiler:
    """Компилирует только виртуальные регистры состояния для SQLite/MES SRV."""

    def compile_date_guard(
        self,
        definition: RegisterDefinition,
        *,
        key_values: Mapping[str, Any] | None = None,
    ) -> QueryPlan:
        predicates, params = self._key_predicates(definition, key_values or {})
        period_sql = f'src.{quote_ident(definition.period.db_column)}'
        invalid = (
            f'({period_sql} IS NULL OR '
            f'trim(CAST({period_sql} AS TEXT)) = \'\' OR '
            f'julianday({period_sql}) IS NULL OR '
            f'date({period_sql}) <> substr(trim(CAST({period_sql} AS TEXT)), 1, 10))'
        )
        predicates.append(invalid)
        tie_parts = [
            f'src.{quote_ident(field.db_column)} AS {quote_ident(f"__register_source_{idx}")}'
            for idx, field in enumerate(definition.tie_breakers)
        ]
        tie_parts.append(f'{period_sql} AS {quote_ident("__register_bad_period")}')
        sql = (
            'SELECT\n    '
            + ',\n    '.join(tie_parts)
            + f'\nFROM {quote_ident(definition.source.table_name)} AS src'
            + ('\nWHERE ' + ' AND '.join(predicates) if predicates else '')
            + '\nLIMIT 1'
        )
        return QueryPlan(
            operation='date_guard',
            db=definition.source.db_key,
            sql=sql,
            params=tuple(params),
            attach_dbs=(),
            output_names=(),
            source_identity_aliases=tuple(
                f'__register_source_{idx}' for idx in range(len(definition.tie_breakers))
            ),
        )

    def compile_at(
        self,
        definition: RegisterDefinition,
        *,
        key_values: Mapping[str, Any],
        moment_sql: str,
    ) -> QueryPlan:
        predicates, params = self._key_predicates(definition, key_values)
        period = f'src.{quote_ident(definition.period.db_column)}'
        predicates.append(f'julianday({period}) <= julianday(?)')
        params.append(moment_sql)
        order_sql = self._descending_state_order(definition, alias='src')
        source_cte = (
            'source_state AS (\n'
            f'    SELECT src.*\n'
            f'    FROM {quote_ident(definition.source.table_name)} AS src\n'
            f'    WHERE {" AND ".join(predicates)}\n'
            f'    ORDER BY {order_sql}\n'
            '    LIMIT 1\n'
            ')'
        )
        return self._compile_from_source_cte(
            definition,
            operation='at',
            source_ctes=(source_cte,),
            params=params,
            final_order='',
        )

    def compile_history(
        self,
        definition: RegisterDefinition,
        *,
        key_values: Mapping[str, Any],
        from_sql: str | None = None,
        to_sql: str | None = None,
    ) -> QueryPlan:
        predicates, params = self._key_predicates(definition, key_values)
        period = f'src.{quote_ident(definition.period.db_column)}'
        if from_sql is not None:
            predicates.append(f'julianday({period}) >= julianday(?)')
            params.append(from_sql)
        if to_sql is not None:
            predicates.append(f'julianday({period}) <= julianday(?)')
            params.append(to_sql)
        source_cte = (
            'source_state AS (\n'
            '    SELECT src.*\n'
            f'    FROM {quote_ident(definition.source.table_name)} AS src'
            + (f'\n    WHERE {" AND ".join(predicates)}' if predicates else '')
            + '\n)'
        )
        return self._compile_from_source_cte(
            definition,
            operation='history',
            source_ctes=(source_cte,),
            params=params,
            final_order=self._ascending_state_order(definition, alias='src'),
        )

    def compile_all_at(
        self,
        definition: RegisterDefinition,
        *,
        moment_sql: str,
    ) -> QueryPlan:
        partition = ', '.join(
            f'src.{quote_ident(key.field.db_column)}' for key in definition.keys
        )
        period = f'src.{quote_ident(definition.period.db_column)}'
        order = self._descending_state_order(definition, alias='src')
        ranked = (
            'ranked_source AS (\n'
            '    SELECT\n'
            '        src.*,\n'
            f'        ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY {order}) '
            f'AS {quote_ident("__register_rank")}\n'
            f'    FROM {quote_ident(definition.source.table_name)} AS src\n'
            f'    WHERE julianday({period}) <= julianday(?)\n'
            ')'
        )
        chosen = (
            'source_state AS (\n'
            '    SELECT *\n'
            '    FROM ranked_source\n'
            f'    WHERE {quote_ident("__register_rank")} = 1\n'
            ')'
        )
        final_order = ', '.join(
            f'src.{quote_ident(key.field.db_column)} ASC' for key in definition.keys
        )
        return self._compile_from_source_cte(
            definition,
            operation='all_at',
            source_ctes=(ranked, chosen),
            params=[moment_sql],
            final_order=final_order,
        )

    def _compile_from_source_cte(
        self,
        definition: RegisterDefinition,
        *,
        operation: str,
        source_ctes: Sequence[str],
        params: Sequence[Any],
        final_order: str,
    ) -> QueryPlan:
        select_plan = self._select_and_relations(definition)
        sql = (
            'WITH ' + ',\n'.join(source_ctes)
            + '\nSELECT\n    '
            + ',\n    '.join(select_plan.select_sql)
            + '\nFROM source_state AS src'
        )
        if select_plan.join_sql:
            sql += '\n' + '\n'.join(select_plan.join_sql)
        if final_order:
            sql += '\nORDER BY ' + final_order
        return QueryPlan(
            operation=operation,
            db=definition.source.db_key,
            sql=sql,
            params=tuple(params),
            attach_dbs=select_plan.attach_dbs,
            output_names=select_plan.output_names,
            source_identity_aliases=select_plan.source_identity_aliases,
            required_markers=select_plan.required_markers,
        )

    def _select_and_relations(self, definition: RegisterDefinition) -> _SelectPlan:
        select_parts: list[str] = []
        joins: list[str] = []
        attach_dbs: list[str] = []
        output_names: list[str] = []
        output_seen: set[str] = set()
        required_markers: list[RequiredMarker] = []

        for item in definition.outputs:
            if isinstance(item, DirectOutput):
                self._append_select(
                    select_parts,
                    output_names,
                    output_seen,
                    f'src.{quote_ident(item.field.db_column)}',
                    item.output_name,
                )
                continue
            relation_select, relation_join, relation_attach, relation_outputs, marker = (
                self._compile_relation_projection(definition, item, index=len(joins))
            )
            joins.append(relation_join)
            for db in relation_attach:
                if db not in attach_dbs:
                    attach_dbs.append(db)
            for expression, output_name in relation_select:
                self._append_select(
                    select_parts,
                    output_names,
                    output_seen,
                    expression,
                    output_name,
                )
            if marker is not None:
                select_parts.append(
                    f'{marker[0]} AS {quote_ident(marker[1].alias)}'
                )
                required_markers.append(marker[1])

        source_identity_aliases: list[str] = []
        for index, field in enumerate(definition.tie_breakers):
            alias = f'__register_source_{index}'
            source_identity_aliases.append(alias)
            select_parts.append(
                f'src.{quote_ident(field.db_column)} AS {quote_ident(alias)}'
            )
        select_parts.append(
            f'src.{quote_ident(definition.period.db_column)} '
            f'AS {quote_ident("__register_period_raw")}'
        )

        return _SelectPlan(
            select_sql=tuple(select_parts),
            join_sql=tuple(joins),
            attach_dbs=tuple(attach_dbs),
            output_names=tuple(output_names),
            source_identity_aliases=tuple(source_identity_aliases),
            required_markers=tuple(required_markers),
        )

    @staticmethod
    def _append_select(
        select_parts: list[str],
        output_names: list[str],
        output_seen: set[str],
        expression: str,
        output_name: str,
    ) -> None:
        if output_name in output_seen:
            raise RegisterDeclarationError(f'Выходное поле {output_name!r} объявлено повторно')
        output_seen.add(output_name)
        output_names.append(output_name)
        select_parts.append(f'{expression} AS {quote_ident(output_name)}')

    def _compile_relation_projection(
        self,
        definition: RegisterDefinition,
        projection: Any,
        *,
        index: int,
    ) -> tuple[
        list[tuple[str, str]],
        str,
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, RequiredMarker] | None,
    ]:
        relationship = getattr(projection, 'relationship', None)
        if relationship is None or not callable(getattr(relationship, 'as_relation_spec', None)):
            raise RegisterDeclarationError(
                f'Объект {projection!r} не является Relationship.select(...) projection'
            )
        owner = getattr(relationship, 'owner', None)
        if owner is not definition.source.model:
            raise RegisterDeclarationError(
                f'Relation {getattr(relationship, "name", "")!r} не принадлежит source модели '
                f'{getattr(definition.source.model, "__name__", definition.source.model)!r}'
            )
        spec = relationship.as_relation_spec(owner=definition.source.model).normalized()
        cardinality = str(spec.cardinality or '').lower()
        if cardinality not in {'one_to_one', 'many_to_one'}:
            raise RegisterDeclarationError(
                f'Регистр {definition.code!r}: relation {spec.relation_key!r} имеет '
                f'cardinality={cardinality!r}. На Stage 2 разрешены только one_to_one/many_to_one; '
                'для коллекций позже появятся явные collect/explode.'
            )
        missing_policy = str(spec.missing_policy or 'none').lower().strip()
        if missing_policy not in {'none', 'raise', 'drop'}:
            raise RegisterDeclarationError(
                f'Регистр {definition.code!r}: missing_policy={missing_policy!r} '
                'не имеет однозначной SQL-семантики для one-shaped relation'
            )
        declared_join_type = str(spec.join_type or 'LEFT JOIN').upper().strip()
        if declared_join_type not in {'LEFT JOIN', 'INNER JOIN'}:
            raise RegisterDeclarationError(
                f'Регистр {definition.code!r}: join_type={declared_join_type!r} не поддержан'
            )
        required = bool(getattr(projection, 'required', False)) or missing_policy == 'raise'
        # Для raise нужен LEFT JOIN + post-check marker. INNER JOIN скрыл бы
        # отсутствие relation как будто исходного состояния не существует.
        if required:
            join_type = 'LEFT JOIN'
        elif missing_policy == 'drop':
            join_type = 'INNER JOIN'
        else:
            join_type = declared_join_type
        on_many = str(getattr(spec, 'on_many', 'error') or 'error').lower()
        if on_many != 'error':
            raise RegisterDeclarationError(
                f'Регистр {definition.code!r}: SQL relation требует on_many="error", '
                f'получено {on_many!r}; first/last без явного порядка недетерминированы.'
            )
        target_model = getattr(spec, 'target_model', None)
        if target_model is None:
            target_model = getattr(getattr(spec, 'target_table', None), 'model', None)
        target = resolve_model_identity(target_model)
        alias = f'rel_{index}'
        target_ref = quote_ident(target.table_name)
        attach: list[str] = []
        source_db_key = definition.source.db_key
        target_db_key = target.db_key
        if target_db_key and target_db_key != source_db_key:
            target_ref = f'{quote_ident(target_db_key)}.{quote_ident(target.table_name)}'
            attach.append(target.db_key)

        on_parts: list[str] = []
        for pair in spec.resolved_pairs():
            role = str(pair.role or 'direct')
            operator = str(pair.operator or '=')
            pair_join_type = str(pair.pair_join_type or '')
            if role != 'direct' or operator != '=' or pair_join_type:
                raise RegisterDeclarationError(
                    f'Регистр {definition.code!r}: relation {spec.relation_key!r} поддерживает '
                    'только direct field_pairs, operator="=" и пустой pair_join_type'
                )
            on_parts.append(
                f'{quote_ident(alias)}.{quote_ident(pair.right_field.db_column or pair.right_field.field_name)} '
                f'= src.{quote_ident(pair.left_field.db_column or pair.left_field.field_name)}'
            )
        if not on_parts:
            raise RegisterDeclarationError(
                f'Relation {spec.relation_key!r} не содержит исполнимых direct field_pairs'
            )
        join = f'{join_type} {target_ref} AS {quote_ident(alias)} ON ' + ' AND '.join(on_parts)

        fields = tuple(getattr(projection, 'fields', ()) or ())
        aliases = tuple(getattr(projection, 'aliases', ()) or ())
        prefix = str(getattr(projection, 'prefix', '') or '').strip()
        relation_name = str(getattr(relationship, 'name', '') or spec.relation_name or 'relation')
        if aliases and len(aliases) != len(fields):
            raise RegisterDeclarationError(
                f'Relation projection {relation_name!r}: aliases и fields разной длины'
            )
        select: list[tuple[str, str]] = []
        output_names: list[str] = []
        for field_index, field in enumerate(fields):
            ref = resolve_field(field, expected_model=target.model)
            if aliases:
                output_name = str(aliases[field_index])
            else:
                output_name = f'{prefix or relation_name}.{ref.python_name}'
            output_names.append(output_name)
            select.append((
                f'{quote_ident(alias)}.{quote_ident(ref.db_column)}',
                output_name,
            ))

        marker = None
        if required:
            marker_field = getattr(target.model, target.pk_name, None)
            if marker_field is None:
                marker_field = (getattr(target.model, '__fields__', {}) or {}).get(target.pk_name)
            marker_ref = resolve_field(marker_field, expected_model=target.model)
            marker_alias = f'__register_rel_{index}_marker'
            marker = (
                f'{quote_ident(alias)}.{quote_ident(marker_ref.db_column)}',
                RequiredMarker(alias=marker_alias, relation_name=relation_name),
            )
        return select, join, tuple(attach), tuple(output_names), marker

    @staticmethod
    def _key_predicates(
        definition: RegisterDefinition,
        key_values: Mapping[str, Any],
    ) -> tuple[list[str], list[Any]]:
        predicates: list[str] = []
        params: list[Any] = []
        for key in definition.keys:
            if key.public_name not in key_values:
                continue
            value = key_values[key.public_name]
            column = f'src.{quote_ident(key.field.db_column)}'
            if value is None:
                predicates.append(f'{column} IS NULL')
            else:
                predicates.append(f'{column} = ?')
                params.append(value)
        return predicates, params

    @staticmethod
    def _descending_state_order(definition: RegisterDefinition, *, alias: str) -> str:
        period = f'{alias}.{quote_ident(definition.period.db_column)}'
        parts = [f'julianday({period}) DESC']
        parts.extend(
            f'{alias}.{quote_ident(field.db_column)} DESC'
            for field in definition.tie_breakers
        )
        return ', '.join(parts)

    @staticmethod
    def _ascending_state_order(definition: RegisterDefinition, *, alias: str) -> str:
        period = f'{alias}.{quote_ident(definition.period.db_column)}'
        parts = [f'julianday({period}) ASC']
        parts.extend(
            f'{alias}.{quote_ident(field.db_column)} ASC'
            for field in definition.tie_breakers
        )
        return ', '.join(parts)


# ==============================================================================
# RUNTIME
# ==============================================================================

RowT = TypeVar("RowT", bound=Mapping[str, Any])


class RegisterRow(dict):
    """Строка регистра: обычный dict с безопасным attribute-access для удобства."""

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def copy(self) -> "RegisterRow":
        return RegisterRow(self)


class RegisterRows(list[RegisterRow]):
    """Fallback, если SmartList недоступен в изолированном контуре."""

    def as_dicts(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self]


def _smart_rows(rows: Sequence[RegisterRow]):
    try:
        module = importlib.import_module("project_cust_38.Cust_orm")
        smart_list = getattr(module, "SmartList")
        return smart_list(list(rows))
    except Exception:
        return RegisterRows(rows)


class BoundStateRegister(Generic[RowT]):
    def __init__(
        self,
        definition: RegisterDefinition,
        *,
        executor: RegisterExecutor,
        clock,
        compiler: RegisterSqlCompiler | None = None,
    ) -> None:
        self.definition = definition
        self.executor = executor
        self.clock = clock
        self.compiler = compiler or RegisterSqlCompiler()

    @property
    def code(self) -> str:
        return self.definition.code

    @property
    def title(self) -> str:
        return self.definition.title

    def manifest(self) -> dict[str, Any]:
        return definition_manifest(self.definition)

    def current(self, *key_values: Any, **keys: Any) -> RowT | None:
        """Состояние сущности на текущий локальный момент."""
        return self.at(*key_values, date=self.clock(), **keys)

    def at(self, *args: Any, date: Any = None, **keys: Any) -> RowT | None:
        """Состояние одной сущности на дату.

        Один ключ:
            register.at(employee_ref, date)

        Составной ключ:
            register.at(order_id, employee, date)
            register.at(order_id=..., employee=..., date=...)
        """
        args = list(args)
        expected = len(self.definition.keys)
        if date is None and len(args) == expected + 1:
            date = args.pop()
        if date is None:
            raise RegisterQueryError(
                f"register.{self.code}.at(...) требует параметр date"
            )
        key_map = parse_key_arguments(self.definition, args, keys)
        moment = parse_moment(date, parameter="date")
        self._guard_dates(key_map)
        plan = self.compiler.compile_at(
            self.definition,
            key_values=key_map,
            moment_sql=moment_to_sql(moment),
        )
        rows = self._execute(plan)
        if not rows:
            return None
        if len(rows) != 1:
            raise RegisterCardinalityError(
                f"Регистр {self.code!r} ожидал одно состояние, получено {len(rows)}"
            )
        return cast(RowT, rows[0])

    def history(
        self,
        *key_values: Any,
        from_: Any = None,
        to: Any = None,
        **keys: Any,
    ) -> list[RowT]:
        """История одной сущности в возрастающем порядке периода и PK."""
        key_map = parse_key_arguments(self.definition, key_values, keys)
        from_dt = parse_moment(from_, parameter="from_") if from_ is not None else None
        to_dt = parse_moment(to, parameter="to") if to is not None else None
        if from_dt is not None and to_dt is not None and from_dt > to_dt:
            raise RegisterQueryError("from_ не может быть позже to")
        self._guard_dates(key_map)
        plan = self.compiler.compile_history(
            self.definition,
            key_values=key_map,
            from_sql=moment_to_sql(from_dt) if from_dt is not None else None,
            to_sql=moment_to_sql(to_dt) if to_dt is not None else None,
        )
        return cast(list[RowT], _smart_rows(self._execute(plan)))

    def all_current(self) -> list[RowT]:
        """Текущее состояние всех сущностей."""
        return self.all_at(self.clock())

    def all_at(self, date: Any) -> list[RowT]:
        """Срез последних по всем сущностям на дату."""
        moment = parse_moment(date, parameter="date")
        self._guard_dates({})
        plan = self.compiler.compile_all_at(
            self.definition,
            moment_sql=moment_to_sql(moment),
        )
        return cast(list[RowT], _smart_rows(self._execute(plan)))

    def preview_at(self, *args: Any, date: Any = None, **keys: Any) -> QueryPlan:
        """Read-only preview SQL для тестов и будущей admin-panel."""
        args = list(args)
        expected = len(self.definition.keys)
        if date is None and len(args) == expected + 1:
            date = args.pop()
        if date is None:
            raise RegisterQueryError("preview_at требует date")
        key_map = parse_key_arguments(self.definition, args, keys)
        moment = parse_moment(date, parameter="date")
        return self.compiler.compile_at(
            self.definition,
            key_values=key_map,
            moment_sql=moment_to_sql(moment),
        )

    def preview_history(
        self,
        *key_values: Any,
        from_: Any = None,
        to: Any = None,
        **keys: Any,
    ) -> QueryPlan:
        key_map = parse_key_arguments(self.definition, key_values, keys)
        from_dt = parse_moment(from_, parameter="from_") if from_ is not None else None
        to_dt = parse_moment(to, parameter="to") if to is not None else None
        if from_dt is not None and to_dt is not None and from_dt > to_dt:
            raise RegisterQueryError("from_ не может быть позже to")
        return self.compiler.compile_history(
            self.definition,
            key_values=key_map,
            from_sql=moment_to_sql(from_dt) if from_dt else None,
            to_sql=moment_to_sql(to_dt) if to_dt else None,
        )

    def preview_all_at(self, date: Any) -> QueryPlan:
        moment = parse_moment(date, parameter="date")
        return self.compiler.compile_all_at(
            self.definition,
            moment_sql=moment_to_sql(moment),
        )

    def _guard_dates(self, key_map: Mapping[str, Any]) -> None:
        if not self.definition.strict_dates:
            return
        plan = self.compiler.compile_date_guard(
            self.definition,
            key_values=key_map,
        )
        bad = self.executor.fetch_all(
            plan.db,
            plan.sql,
            plan.params,
            attach_dbs=plan.attach_dbs,
        )
        if bad:
            row = bad[0]
            identity = tuple(
                row.get(alias) for alias in plan.source_identity_aliases
            )
            raise RegisterDataError(
                f"Регистр {self.code!r}: источник {self.definition.source.table_key!r} "
                f"содержит некорректный период {row.get('__register_bad_period')!r}; "
                f"source_identity={identity!r}"
            )

    def _execute(self, plan: QueryPlan) -> list[RegisterRow]:
        raw_rows = self.executor.fetch_all(
            plan.db,
            plan.sql,
            plan.params,
            attach_dbs=plan.attach_dbs,
        )
        seen_source: set[tuple[Any, ...]] = set()
        result: list[RegisterRow] = []
        for raw in raw_rows:
            identity = tuple(raw.get(alias) for alias in plan.source_identity_aliases)
            if identity in seen_source:
                raise RegisterCardinalityError(
                    f"Регистр {self.code!r}: relation размножила строку источника "
                    f"source_identity={identity!r}. one_to_many/дубликат one-to-one запрещён."
                )
            seen_source.add(identity)
            for marker in plan.required_markers:
                if raw.get(marker.alias) is None:
                    raise RegisterDataError(
                        f"Регистр {self.code!r}: обязательная relation "
                        f"{marker.relation_name!r} не найдена для source_identity={identity!r}"
                    )
            result.append(RegisterRow({name: raw.get(name) for name in plan.output_names}))
        return result


# ==============================================================================
# КАТАЛОГ И ДЕКЛАРАЦИИ
# ==============================================================================

class StateRegister:
    """Кодовая декларация виртуального регистра состояния.

    Обязательные понятия public API:
        source — ORM-модель истории;
        key    — ключ сущности;
        period — момент начала действия записи;
        fields — возвращаемые поля.
    """

    def __init__(
        self,
        *,
        source: Any,
        key: Any,
        period: Any,
        fields: Iterable[Any],
        title: str = "",
        tie_breaker: Iterable[Any] | Any | None = None,
        strict_dates: bool = True,
        notes: str = "",
    ) -> None:
        self.source = source
        self.key = key
        self.period = period
        self.fields = tuple(fields or ())
        self.title = str(title or "")
        self.tie_breaker = tie_breaker
        self.strict_dates = bool(strict_dates)
        self.notes = str(notes or "")
        self._code = ""

    def __set_name__(self, owner, name: str) -> None:
        self._set_code(name)

    def __get__(self, instance: "RegisterCatalog | None", owner=None):
        if instance is None:
            return self
        return instance._bind(self)

    @property
    def code(self) -> str:
        return self._code

    def _set_code(self, code: str) -> None:
        code = str(code or "").strip()
        if self._code and self._code != code:
            raise RegisterDeclarationError(
                f"Одна декларация StateRegister не может иметь два кода: {self._code!r}, {code!r}"
            )
        self._code = code

    def definition(self) -> RegisterDefinition:
        if not self._code:
            raise RegisterDeclarationError(
                "StateRegister не получил имя. Объявите его атрибутом RegisterCatalog "
                "или передайте через declarations={code: register}."
            )
        # Definition is deliberately rebuilt for each catalog binding. Generated
        # models may be reloaded by a maintenance process, and caching a previous
        # db_key/table_key here would silently bind a new catalog to stale metadata. The catalog itself caches the already-bound runtime object.
        return build_definition(
            code=self._code,
            title=self.title or self._code,
            source_model=self.source,
            key=self.key,
            period=self.period,
            fields=self.fields,
            tie_breaker=self.tie_breaker,
            strict_dates=self.strict_dates,
            notes=self.notes,
        )

    def manifest(self) -> dict[str, Any]:
        return definition_manifest(self.definition())


class RegisterCatalog:
    def __init__(
        self,
        *,
        declarations: Mapping[str, StateRegister] | None = None,
        executor: RegisterExecutor | None = None,
        clock=None,
        compiler: RegisterSqlCompiler | None = None,
    ) -> None:
        self._executor = executor or default_executor()
        self._clock = clock or _dt.datetime.now
        self._compiler = compiler or RegisterSqlCompiler()
        self._declarations: OrderedDict[str, StateRegister] = OrderedDict()
        self._definitions: OrderedDict[str, RegisterDefinition] = OrderedDict()
        self._bound: dict[str, BoundStateRegister] = {}

        for code, declaration in self._class_declarations().items():
            self._register_declaration(code, declaration)
        for code, declaration in dict(declarations or {}).items():
            self._register_declaration(code, declaration)

    @classmethod
    def _class_declarations(cls) -> OrderedDict[str, StateRegister]:
        result: OrderedDict[str, StateRegister] = OrderedDict()
        for base in reversed(cls.__mro__):
            for name, value in base.__dict__.items():
                if isinstance(value, StateRegister):
                    result[name] = value
        return result

    def _register_declaration(self, code: str, declaration: StateRegister) -> None:
        if not isinstance(declaration, StateRegister):
            raise RegisterDeclarationError(
                f"declarations[{code!r}] должен быть StateRegister"
            )
        declaration._set_code(code)
        if code in self._declarations:
            if self._declarations[code] is not declaration:
                raise RegisterDeclarationError(f"Регистр {code!r} объявлен повторно")
            return
        # Каталог фиксирует нормализованный контракт один раз. Глобальная
        # декларация не кэширует db_key/table_key identity между разными каталогами,
        # но уже созданный runtime не меняется при случайной перезагрузке модели.
        definition = declaration.definition()
        self._declarations[code] = declaration
        self._definitions[code] = definition

    def _bind(self, declaration: StateRegister) -> BoundStateRegister:
        definition = self._definitions[declaration.code]
        bound = self._bound.get(definition.code)
        if bound is None:
            bound = BoundStateRegister(
                definition,
                executor=self._executor,
                clock=self._clock,
                compiler=self._compiler,
            )
            self._bound[definition.code] = bound
        return bound

    def __getattr__(self, item: str):
        declarations = self.__dict__.get("_declarations", {})
        if item in declarations:
            return self._bind(declarations[item])
        raise AttributeError(item)

    def get(self, code: str) -> BoundStateRegister:
        try:
            declaration = self._declarations[code]
        except KeyError as exc:
            raise KeyError(
                f"Регистр {code!r} не объявлен; доступны {list(self._declarations)!r}"
            ) from exc
        return self._bind(declaration)

    def codes(self) -> tuple[str, ...]:
        return tuple(self._declarations)

    def manifest(self) -> dict[str, Any]:
        return {
            "format": "mes-register-catalog/2",
            "registers": [
                definition_manifest(definition)
                for definition in self._definitions.values()
            ],
        }

    def validate(self) -> tuple[RegisterDefinition, ...]:
        return tuple(self._definitions.values())


# ==============================================================================
# СТАРТОВЫЕ РЕГИСТРЫ MES
# ==============================================================================

_DEFAULT_MODELS_MODULE = "project_cust_38.dynamic_db_models.orm_models"


_LOCK = threading.RLock()


_DEFAULT_CATALOG: "MesRegisterCatalog | None" = None


class EmployeeStateRow(TypedDict):
    id: int
    ФизическоеЛицо_Key: str | None
    Должность_Key: str | None
    Подразделение_Key: str | None
    Период: str
    Организация_Key: str | None
    Событие: str | None
    Сотрудник_Key: str | None


class CompetenceStateRow(TypedDict):
    s_num: int
    id_comp: int | None
    id_user: str | None
    value: int
    created_at: str | None


class WorkOrderStateRow(TypedDict):
    Пномер: int
    Дата: str | None
    Штамп: float | None
    Номер_наряда: int | None
    ФИО: str | None
    Подытог: float | None
    Подытог_нормы: float | str | None
    Статус: str | None
    Примечание: str | None
    Ном_заверш: int | None
    Дата_выгрузки_ЕРП: str | None
    ФИО_выгрузки_ЕРП: str | None
    Минут_выгружено_ЕРП: float | None
    base_ERP: int | None


class MesRegisterCatalog(RegisterCatalog):
    """Типизированный публичный каталог стартовых регистров MES."""

    @property
    def employee(self) -> BoundStateRegister[EmployeeStateRow]:
        return cast(BoundStateRegister[EmployeeStateRow], self.get("employee"))

    @property
    def competence(self) -> BoundStateRegister[CompetenceStateRow]:
        return cast(BoundStateRegister[CompetenceStateRow], self.get("competence"))

    @property
    def work_order(self) -> BoundStateRegister[WorkOrderStateRow]:
        return cast(BoundStateRegister[WorkOrderStateRow], self.get("work_order"))


def _load_models_module(value: str | ModuleType | None) -> ModuleType:
    if isinstance(value, ModuleType):
        return value
    module_name = str(value or _DEFAULT_MODELS_MODULE)
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        raise RegisterDeclarationError(
            f"Не удалось импортировать generated ORM models {module_name!r}. "
            "Сначала атомарно сгенерируйте dynamic_db_models из принятого Stage 1."
        ) from exc


def _iter_models(module: ModuleType):
    # Generated модуль иногда может экспортировать тот же класс дополнительным
    # alias-именем. Это не identity-конфликт: конфликтом считаются только два
    # разных класса для одного точного table_key.
    seen: set[int] = set()
    for value in vars(module).values():
        if not isinstance(value, type) or not getattr(value, "__table__", None):
            continue
        marker = id(value)
        if marker in seen:
            continue
        seen.add(marker)
        yield value




def _models_by_table_key(module: ModuleType) -> dict[str, type]:
    """Построить точный индекс generated ORM по ``__table_key__``."""
    result: dict[str, type] = {}
    for model in _iter_models(module):
        identity = resolve_model_identity(model)
        previous = result.get(identity.table_key)
        if previous is not None and previous is not model:
            raise RegisterDeclarationError(
                f"Generated ORM содержит два разных класса с table_key={identity.table_key!r}: "
                f"{getattr(previous, '__name__', previous)!r} и "
                f"{getattr(model, '__name__', model)!r}"
            )
        result[identity.table_key] = model
    return result


def _require_model(models: Mapping[str, type], table_key: str) -> type:
    exact_key = str(table_key or "").strip()
    try:
        return models[exact_key]
    except KeyError as exc:
        raise RegisterDeclarationError(
            f"Generated ORM не содержит точную модель {exact_key!r}; "
            f"доступно {len(models)} table_key"
        ) from exc


def build_mes_registers(
    *,
    models_module: str | ModuleType | None = None,
    executor=None,
    clock=None,
) -> MesRegisterCatalog:
    """Построить независимый каталог из generated ORM Stage 1."""
    models_module_obj = _load_models_module(models_module)
    models = _models_by_table_key(models_module_obj)

    employee_state = _require_model(models, "BD_users.КадроваяИстория")
    competence_values = _require_model(models, "BD_users.competence_vals")
    work_log = _require_model(models, "Naryad.jurnal")

    # После явного lazy-import декларации используют сами ORM descriptors,
    # а не строковые имена полей. Строки остаются только в bootstrap-поиске
    # физической модели по точному table_key.
    EmployeeHistory = employee_state
    CompetenceValues = competence_values
    WorkLog = work_log

    employee = StateRegister(
        title="Кадровое состояние сотрудника",
        source=EmployeeHistory,
        key={"employee_ref": EmployeeHistory.ФизическоеЛицо_Key},
        period=EmployeeHistory.Период,
        fields=(
            EmployeeHistory.id,
            EmployeeHistory.ФизическоеЛицо_Key,
            EmployeeHistory.Должность_Key,
            EmployeeHistory.Подразделение_Key,
            EmployeeHistory.Период,
            EmployeeHistory.Организация_Key,
            EmployeeHistory.Событие,
            EmployeeHistory.Сотрудник_Key,
        ),
        notes=(
            "Срез кадровой истории. Стабильный выбор при одинаковом Период: "
            "ORDER BY Период DESC, id DESC."
        ),
    )

    competence = StateRegister(
        title="Состояние компетенции сотрудника",
        source=CompetenceValues,
        key={
            "employee_ref": CompetenceValues.id_user,
            "competence_id": CompetenceValues.id_comp,
        },
        period=CompetenceValues.created_at,
        fields=(
            CompetenceValues.s_num,
            CompetenceValues.id_comp,
            CompetenceValues.id_user,
            CompetenceValues.value,
            CompetenceValues.created_at,
        ),
        notes="Последняя оценка конкретной компетенции сотрудника на дату.",
    )

    work_order = StateRegister(
        title="Состояние исполнения наряда сотрудником",
        source=WorkLog,
        key={
            "order_id": WorkLog.Номер_наряда,
            "employee": WorkLog.ФИО,
        },
        period=WorkLog.Дата,
        fields=(
            WorkLog.Пномер,
            WorkLog.Дата,
            WorkLog.Штамп,
            WorkLog.Номер_наряда,
            WorkLog.ФИО,
            WorkLog.Подытог,
            WorkLog.Подытог_нормы,
            WorkLog.Статус,
            WorkLog.Примечание,
            WorkLog.Ном_заверш,
            WorkLog.Дата_выгрузки_ЕРП,
            WorkLog.ФИО_выгрузки_ЕРП,
            WorkLog.Минут_выгружено_ЕРП,
            WorkLog.base_ERP,
        ),
        notes=(
            "Последнее событие jurnal по паре Номер_наряда + ФИО. "
            "Не заменяет расчёт пар Начат/Завершен и суммирование выработки."
        ),
    )

    return MesRegisterCatalog(
        declarations={
            "employee": employee,
            "competence": competence,
            "work_order": work_order,
        },
        executor=executor,
        clock=clock,
    )


def get_mes_registers(
    *,
    reset: bool = False,
    models_module: str | ModuleType | None = None,
    executor=None,
    clock=None,
) -> MesRegisterCatalog:
    """Получить каталог.

    При передаче custom models/executor/clock возвращается отдельный экземпляр.
    Default-каталог лениво создаётся один раз и не вызывает SQL до первого запроса.
    """
    global _DEFAULT_CATALOG
    custom = models_module is not None or executor is not None or clock is not None
    if custom:
        return build_mes_registers(
            models_module=models_module,
            executor=executor,
            clock=clock,
        )
    with _LOCK:
        if reset or _DEFAULT_CATALOG is None:
            _DEFAULT_CATALOG = build_mes_registers()
        return _DEFAULT_CATALOG


__all__ = [
    "RegisterCatalog",
    "StateRegister",
    "BoundStateRegister",
    "RegisterRow",
    "RegisterRows",
    "RegisterExecutor",
    "MesSqlExecutor",
    "SqliteExecutor",
    "CallableExecutor",
    "RegisterSqlCompiler",
    "QueryPlan",
    "named",
    "RegisterError",
    "RegisterDeclarationError",
    "RegisterQueryError",
    "RegisterDataError",
    "RegisterCardinalityError",
    "RegisterSourceUnavailable",
    "EmployeeStateRow",
    "CompetenceStateRow",
    "WorkOrderStateRow",
    "MesRegisterCatalog",
    "build_mes_registers",
    "get_mes_registers",
]
