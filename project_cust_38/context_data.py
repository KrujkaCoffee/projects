from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import importlib
import importlib.util
import inspect
import json
import pathlib
import sqlite3
import threading
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

from project_cust_38 import Cust_config as CFG  # type: ignore
import project_cust_38.Cust_SQLite as CSQ  # type: ignore
from project_cust_38 import context_admin as CADM  # type: ignore


__all__ = [
    'Attr',
    'DbAttr',
    'CallableAttr',
    'HttpAttr',
    'RuntimeRegistry',
    'BoundAttr',
    'CacheEntry',
    'LoadResult',
    'SchemaBundle',
    'ContextData',
    'GLOBAL_RUNTIME_REGISTRY',
    'register_runtime_attr',
    'resolve_cfg_db',
    'infer_payload_schema',
]


_DEFAULT_CACHE_LIFETIME_MIN = 120


def _local_now() -> str:
    return _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str, separators=(',', ':'))


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return '{' + key + '}'


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _normalize_path(value: Any) -> str:
    if value in (None, ''):
        return ''
    text = str(value).strip().strip('"').strip("'")
    if not text:
        return ''
    return str(pathlib.Path(text))


def _normalize_attach_dbs(value: Iterable[str] | str | None) -> tuple[str, ...]:
    if value in (None, '', ()):
        return ()
    if isinstance(value, str):
        return (value,)
    result = []
    for item in value:
        if item not in (None, ''):
            result.append(str(item))
    return tuple(result)


def _normalize_params_for_local(params: Any) -> Any:
    if params is None:
        return ()
    if isinstance(params, Mapping):
        return dict(params)
    if isinstance(params, tuple):
        return params
    if isinstance(params, list):
        if not params:
            return ()
        if len(params) == 1 and isinstance(params[0], (list, tuple, Mapping)):
            inner = params[0]
            if isinstance(inner, Mapping):
                return dict(inner)
            return tuple(inner)
        if params and all(not isinstance(item, (list, tuple, Mapping)) for item in params):
            return tuple(params)
        return tuple(params)
    return (params,)


def _normalize_params_for_csq(params: Any) -> list[Any]:
    if params is None:
        return [[]]
    if isinstance(params, Mapping):
        return [dict(params)]
    if isinstance(params, tuple):
        return list(params)
    if isinstance(params, list):
        return params if params else [[]]
    return [params]


def _parse_dt(value: Any) -> _dt.datetime | None:
    if value in (None, ''):
        return None
    if isinstance(value, _dt.datetime):
        return value
    text = str(value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return _dt.datetime.strptime(text, fmt)
        except Exception:
            pass
    try:
        return _dt.datetime.fromisoformat(text)
    except Exception:
        return None


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, pathlib.Path):
        return str(value)
    return repr(value)


def _call_factory(factory: Any, context: 'ContextData', **kwargs) -> Any:
    if not callable(factory):
        return factory
    attempts: list[tuple[tuple[Any, ...], dict[str, Any]]] = [
        ((context,), dict(kwargs)),
        ((), dict(kwargs)),
        ((context,), {}),
        ((), {}),
    ]
    last_error: Exception | None = None
    for args, kkwargs in attempts:
        try:
            return factory(*args, **kkwargs)
        except TypeError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    return factory()


def resolve_cfg_db(db_key_or_path: str | None) -> str | None:
    """Возвращает путь к БД по alias из CFG.Config.project либо возвращает вход как есть."""
    if db_key_or_path in (None, ''):
        return None
    value = str(db_key_or_path)
    project = getattr(getattr(CFG, 'Config', None), 'project', None)
    if project is not None and hasattr(project, value):
        try:
            resolved = getattr(project, value)
            if isinstance(resolved, str) and resolved:
                return resolved
        except Exception:
            pass
    return value


def _module_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


@dataclass
class SchemaBundle:
    manifest: dict[str, Any] = field(default_factory=dict)
    table_hints: dict[str, Any] = field(default_factory=dict)
    source_hints: dict[str, Any] = field(default_factory=dict)
    origin: str = ''

    @property
    def artifact_version(self) -> str:
        return str(self.manifest.get('artifact_version') or '')

    @property
    def generated_at_utc(self) -> str:
        return str(self.manifest.get('generated_at_utc') or '')


@dataclass
class CacheEntry:
    key: str
    attr_name: str
    source_code: str
    variant_fingerprint: str
    value: Any
    loaded_at: str
    dependency_fingerprint: str = ''
    schema: dict[str, Any] = field(default_factory=dict)
    source_hint: dict[str, Any] = field(default_factory=dict)
    table_hint: dict[str, Any] = field(default_factory=dict)
    resolved_args: dict[str, Any] = field(default_factory=dict)
    cache_enabled: bool = True
    cache_lifetime_min: int = _DEFAULT_CACHE_LIFETIME_MIN
    stale_after_dt: str | None = None


@dataclass
class LoadResult:
    value: Any
    cache_hit: bool
    cache_key: str
    source_code: str
    variant_fingerprint: str
    dependency_fingerprint: str
    schema: dict[str, Any]
    source_hint: dict[str, Any]
    table_hint: dict[str, Any]
    resolved_args: dict[str, Any]
    loaded_at: str


class RuntimeRegistry:
    """Runtime-реестр Attr-объектов.

    Не является владельцем истины о schema/source metadata,
    а только индексом runtime loaders.
    """

    def __init__(self) -> None:
        self._attrs: dict[str, Attr] = {}

    def register(self, name: str, attr: 'Attr', *, replace: bool = True) -> 'Attr':
        if not replace and name in self._attrs:
            raise KeyError(f'Attr {name!r} уже зарегистрирован')
        self._attrs[name] = attr
        if not attr.attr_name:
            attr.attr_name = name
        return attr

    def get(self, name: str) -> 'Attr | None':
        return self._attrs.get(name)

    def items(self):
        return self._attrs.items()

    def keys(self):
        return self._attrs.keys()

    def values(self):
        return self._attrs.values()

    def has(self, name: str) -> bool:
        return name in self._attrs

    def copy(self) -> 'RuntimeRegistry':
        other = RuntimeRegistry()
        other._attrs = dict(self._attrs)
        return other


GLOBAL_RUNTIME_REGISTRY = RuntimeRegistry()


def register_runtime_attr(name: str, attr: 'Attr', *, replace: bool = True) -> 'Attr':
    return GLOBAL_RUNTIME_REGISTRY.register(name, attr, replace=replace)


class BoundAttr:
    def __init__(self, context: 'ContextData', name: str):
        self.context = context
        self.name = name

    @property
    def attr(self) -> 'Attr':
        attr = self.context.registry.get(self.name)
        if attr is None:
            raise KeyError(f'Attr {self.name!r} не найден в runtime registry')
        return attr

    def get(self, *args, with_meta: bool = False, force_refresh: bool = False, verify_freshness: bool = True, **kwargs):
        if args:
            raise TypeError('Используйте только именованные аргументы resolved args')
        return self.context.get(self.name, with_meta=with_meta, force_refresh=force_refresh, verify_freshness=verify_freshness, **kwargs)

    def meta(self, **kwargs) -> LoadResult:
        result = self.context.get(self.name, with_meta=True, **kwargs)
        assert isinstance(result, LoadResult)
        return result

    def invalidate(self) -> None:
        self.context.invalidate_source(self.attr.resolved_source_code())

    def __call__(self, **kwargs):
        return self.get(**kwargs)


class Attr:
    """Базовый runtime loader.

    runtime-слой, который:
    - знает, как получить данные;
    - умеет использовать admin metadata для freshness/invalidation;
    - умеет опираться на shipped schema artifacts.
    """

    source_kind = 'runtime'

    def __init__(
        self,
        *,
        source_code: str | None = None,
        source_key: str | None = None,
        cache_enabled: bool | None = None,
        schema_enabled: bool | None = None,
        cache_lifetime_min: int | None = None,
        stale_after_dt: str | None = None,
        base_table_key: str | None = None,
        schema_source_table_key: str | None = None,
        source_tables: Sequence[str] | None = None,
        fallback_schema: Mapping[str, Any] | None = None,
        default: Any = None,
        notes: str = '',
        auto_register_source: bool = True,
        postprocess: Callable[..., Any] | None = None,
    ) -> None:
        self.attr_name: str | None = None
        self.source_code = source_code or source_key
        self.source_key = self.source_code  # deprecated alias for compatibility
        self.cache_enabled = cache_enabled
        self.schema_enabled = schema_enabled
        self.cache_lifetime_min = cache_lifetime_min
        self.stale_after_dt = stale_after_dt
        self.base_table_key = base_table_key
        self.schema_source_table_key = schema_source_table_key or base_table_key
        self.source_tables = tuple(source_tables or ())
        self.fallback_schema = dict(fallback_schema or {})
        self.default = default
        self.notes = notes or ''
        self.auto_register_source = bool(auto_register_source)
        self.postprocess = postprocess

    def __set_name__(self, owner, name: str) -> None:
        self.attr_name = name

    def __get__(self, instance: 'ContextData | None', owner=None):
        if instance is None:
            return self
        return instance.get(self.attr_name or self.resolved_source_code())

    def resolved_source_code(self) -> str:
        return str(self.source_code or self.attr_name or self.__class__.__name__)

    def resolve_runtime_args(self, context: 'ContextData', **kwargs) -> dict[str, Any]:
        return dict(kwargs)

    def build_variant_payload(self, context: 'ContextData', *, resolved_args: Mapping[str, Any], runtime_extras: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(resolved_args)
        if runtime_extras:
            payload.update(dict(runtime_extras))
        return {str(k): _to_jsonable(v) for k, v in payload.items()}

    def preview_runtime_extras(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> dict[str, Any]:
        return {}

    def variant_fingerprint(self, context: 'ContextData', *, resolved_args: Mapping[str, Any], runtime_extras: Mapping[str, Any] | None = None) -> str:
        payload = {
            'source_code': self.resolved_source_code(),
            'source_kind': self.source_kind,
            'resolved_args': self.build_variant_payload(context, resolved_args=resolved_args, runtime_extras=runtime_extras),
        }
        return _sha256_text(_json_dumps(payload))

    def ensure_admin_source(self, context: 'ContextData') -> None:
        context.ensure_source_registered(self)

    def compute_source_schema(self, context: 'ContextData', *, payload: Any = None) -> dict[str, Any]:
        schema = context.get_source_schema(self.attr_name or self.resolved_source_code(), payload=payload)
        if not schema and self.fallback_schema:
            schema = dict(self.fallback_schema)
        return schema

    def materialize(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
        value = self.load_value(context, resolved_args=resolved_args)
        if self.postprocess is not None:
            value = _call_factory(self.postprocess, context, value=value, **dict(resolved_args))
        return value, {}

    def load_value(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> Any:
        raise NotImplementedError


class DbAttr(Attr):
    source_kind = 'sql'

    def __init__(
        self,
        *,
        db: str | Callable[..., str | None] | None = None,
        db_key: str | None = None,
        sql: str | Callable[..., str] | None = None,
        sql_template: str | Callable[..., str] | None = None,
        params: Any = None,
        attach_dbs: Iterable[str] | str | Callable[..., Iterable[str] | str | None] | None = None,
        rez_dict: bool = True,
        one: bool = False,
        one_column: bool = False,
        hat_c: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.db_key = db_key
        self.sql = sql
        self.sql_template = sql_template
        self.params = params
        self.attach_dbs = attach_dbs
        self.rez_dict = rez_dict
        self.one = one
        self.one_column = one_column
        self.hat_c = hat_c

    def resolve_db(self, context: 'ContextData', **resolved_args) -> str:
        db_value = self.db if self.db is not None else self.db_key
        db_value = _call_factory(db_value, context, **resolved_args)
        resolved = resolve_cfg_db(db_value)
        if not resolved:
            raise RuntimeError(f'Для source {self.resolved_source_code()!r} не удалось определить db/db_key')
        return str(resolved)

    def resolve_sql(self, context: 'ContextData', **resolved_args) -> str:
        if self.sql is not None:
            if callable(self.sql):
                return str(_call_factory(self.sql, context, **resolved_args))
            return str(self.sql)
        if self.sql_template is None:
            raise RuntimeError(f'Для source {self.resolved_source_code()!r} не задан sql/sql_template')
        template = self.sql_template
        if callable(template):
            return str(_call_factory(template, context, **resolved_args))
        return str(template).format_map(_SafeFormatDict(**{k: str(v) for k, v in resolved_args.items()}))

    def resolve_params(self, context: 'ContextData', **resolved_args) -> Any:
        return _call_factory(self.params, context, **resolved_args)

    def resolve_attach_dbs(self, context: 'ContextData', **resolved_args) -> tuple[str, ...]:
        resolved = _call_factory(self.attach_dbs, context, **resolved_args)
        attach_dbs = _normalize_attach_dbs(resolved)
        return tuple(filter(None, (resolve_cfg_db(item) for item in attach_dbs)))

    def preview_runtime_extras(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> dict[str, Any]:
        sql_text = self.resolve_sql(context, **dict(resolved_args))
        params = self.resolve_params(context, **dict(resolved_args))
        db = self.resolve_db(context, **dict(resolved_args))
        attach_dbs = self.resolve_attach_dbs(context, **dict(resolved_args))
        return {
            '_db': db,
            '_sql': sql_text,
            '_params': _to_jsonable(params),
            '_attach_dbs': list(attach_dbs),
        }

    def materialize(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
        runtime_extras = self.preview_runtime_extras(context, resolved_args=resolved_args)
        sql_text = str(runtime_extras.get('_sql') or '')
        params = runtime_extras.get('_params')
        # В execute_sql нужен исходный объект params
        raw_params = self.resolve_params(context, **dict(resolved_args))
        db = str(runtime_extras.get('_db') or '')
        attach_dbs = tuple(runtime_extras.get('_attach_dbs') or ())
        value = context.execute_sql(
            db=db,
            sql=sql_text,
            params=raw_params,
            rez_dict=self.rez_dict,
            one=self.one,
            one_column=self.one_column,
            hat_c=self.hat_c,
            attach_dbs=attach_dbs,
        )
        if self.postprocess is not None:
            value = _call_factory(self.postprocess, context, value=value, **dict(resolved_args))
        runtime_extras['_params'] = _to_jsonable(raw_params)
        return value, runtime_extras

    def load_value(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> Any:
        value, _ = self.materialize(context, resolved_args=resolved_args)
        return value


class CallableAttr(Attr):
    source_kind = 'callable'

    def __init__(self, loader: Callable[..., Any], *, schema_loader: Callable[..., Mapping[str, Any]] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.loader = loader
        self.schema_loader = schema_loader

    def materialize(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
        value = _call_factory(self.loader, context, **dict(resolved_args))
        if self.postprocess is not None:
            value = _call_factory(self.postprocess, context, value=value, **dict(resolved_args))
        return value, {}

    def load_value(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> Any:
        value, _ = self.materialize(context, resolved_args=resolved_args)
        return value

    def compute_source_schema(self, context: 'ContextData', *, payload: Any = None) -> dict[str, Any]:
        if self.schema_loader is not None:
            try:
                schema = _call_factory(self.schema_loader, context, payload=payload)
                if isinstance(schema, Mapping):
                    return dict(schema)
            except Exception:
                pass
        return super().compute_source_schema(context, payload=payload)


class HttpAttr(Attr):
    source_kind = 'http'

    def __init__(
        self,
        *,
        url: str | Callable[..., str],
        method: str = 'GET',
        params: Any = None,
        json_body: Any = None,
        data: Any = None,
        headers: Any = None,
        timeout: float = 15.0,
        response_adapter: Callable[..., Any] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url
        self.method = method.upper().strip() or 'GET'
        self.params = params
        self.json_body = json_body
        self.data = data
        self.headers = headers
        self.timeout = timeout
        self.response_adapter = response_adapter

    def preview_runtime_extras(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> dict[str, Any]:
        return {
            '_url': str(_call_factory(self.url, context, **dict(resolved_args))),
            '_method': self.method,
            '_params': _to_jsonable(_call_factory(self.params, context, **dict(resolved_args))),
        }

    def materialize(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
        import requests

        runtime_extras = self.preview_runtime_extras(context, resolved_args=resolved_args)
        url = str(runtime_extras['_url'])
        params = _call_factory(self.params, context, **dict(resolved_args))
        json_body = _call_factory(self.json_body, context, **dict(resolved_args))
        data = _call_factory(self.data, context, **dict(resolved_args))
        headers = _call_factory(self.headers, context, **dict(resolved_args)) or {}
        response = requests.request(
            method=self.method,
            url=url,
            params=params,
            json=json_body,
            data=data,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        value: Any
        if self.response_adapter is not None:
            value = _call_factory(self.response_adapter, context, response=response, **dict(resolved_args))
        else:
            ctype = response.headers.get('Content-Type', '')
            if 'json' in ctype.lower():
                value = response.json()
            else:
                value = response.text
        if self.postprocess is not None:
            value = _call_factory(self.postprocess, context, value=value, **dict(resolved_args))
        runtime_extras['_params'] = _to_jsonable(params)
        return value, runtime_extras

    def load_value(self, context: 'ContextData', *, resolved_args: Mapping[str, Any]) -> Any:
        value, _ = self.materialize(context, resolved_args=resolved_args)
        return value


class ContextData:
    """Runtime core для data access.

    Порядок источников схемы:
    1. shipped generated artifacts (`generated_schemas`)
    2. admin metadata (`db_files`)
    3. payload inference fallback
    """

    def __init__(
        self,
        *,
        db_files: str | None = None,
        shipped_schema_dir: str | pathlib.Path | None = None,
        registry: RuntimeRegistry | None = None,
        use_global_registry: bool = False,
        auto_load_artifacts: bool = True,
        executor: Callable[..., Any] | None = None,
    ) -> None:
        self.db_files = _normalize_path(db_files) or self._resolve_default_db_files()
        self.registry = RuntimeRegistry()
        self._lock = threading.RLock()
        self._cache: dict[str, CacheEntry] = {}
        self._executor = executor
        self._schema_bundle = SchemaBundle()
        self._shipped_schema_dir = pathlib.Path(shipped_schema_dir).resolve() if shipped_schema_dir else None
        self._source_row_cache: dict[str, dict[str, Any] | None] = {}
        self._table_row_cache: dict[str, dict[str, Any] | None] = {}
        self._table_fields_cache: dict[str, list[dict[str, Any]]] = {}
        self._admin_repo = self._create_admin_repo()

        if use_global_registry:
            for name, attr in GLOBAL_RUNTIME_REGISTRY.items():
                self.registry.register(name, attr)
        if registry is not None:
            for name, attr in registry.items():
                self.registry.register(name, attr)
        self._register_declared_attrs()
        if auto_load_artifacts:
            self.reload_schema_artifacts()

    # ---------- bootstrap / config ----------
    def _resolve_default_db_files(self) -> str:
        if CADM is not None:
            try:
                return str(CADM.resolve_default_db_files())  # type: ignore[attr-defined]
            except Exception:
                pass
        project = getattr(getattr(CFG, 'Config', None), 'project', None)
        if project is not None:
            db_files = getattr(project, 'db_files', None)
            if db_files:
                return str(db_files)
        return ''

    def _create_admin_repo(self):
        if CADM is None or not self.db_files:
            return None
        try:
            return CADM.ensure_admin_schema(self.db_files)
        except Exception:
            return None

    def cfg_db(self, key: str) -> str | None:
        return resolve_cfg_db(key)

    def _register_declared_attrs(self) -> None:
        for cls in reversed(self.__class__.mro()):
            for name, value in cls.__dict__.items():
                if isinstance(value, Attr):
                    self.registry.register(name, value)

    def register_attr(self, name: str, attr: Attr, *, replace: bool = True) -> Attr:
        return self.registry.register(name, attr, replace=replace)

    def register_db_attr(self, name: str, **kwargs) -> DbAttr:
        return self.register_attr(name, DbAttr(**kwargs))  # type: ignore[return-value]

    def register_callable_attr(self, name: str, loader: Callable[..., Any], **kwargs) -> CallableAttr:
        return self.register_attr(name, CallableAttr(loader, **kwargs))  # type: ignore[return-value]

    def register_http_attr(self, name: str, **kwargs) -> HttpAttr:
        return self.register_attr(name, HttpAttr(**kwargs))  # type: ignore[return-value]

    def bind(self, name: str) -> BoundAttr:
        return BoundAttr(self, name)

    def __getattr__(self, name: str):
        if self.registry.has(name):
            return self.get(name)
        raise AttributeError(name)

    # ---------- schema loading ----------
    def _candidate_schema_dirs(self) -> list[pathlib.Path]:
        result: list[pathlib.Path] = []
        if self._shipped_schema_dir is not None:
            result.append(self._shipped_schema_dir)
        result.append(_module_root() / 'generated_schemas')
        result.append(pathlib.Path.cwd() / 'project_cust_38' / 'generated_schemas')
        result.append(pathlib.Path.cwd() / 'generated_schemas')
        seen = set()
        unique: list[pathlib.Path] = []
        for path in result:
            path = path.resolve()
            if str(path) not in seen:
                seen.add(str(path))
                unique.append(path)
        return unique

    def _load_module_from_path(self, module_name: str, path: pathlib.Path) -> types.ModuleType:
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            raise ImportError(f'Не удалось создать spec для {path}')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[call-arg]
        return mod

    def _load_shipped_bundle(self) -> SchemaBundle:
        bundle = SchemaBundle()
        # 1. package import
        package_names = (
            'project_cust_38.generated_schemas',
            'generated_schemas',
        )
        for package_name in package_names:
            try:
                pkg = importlib.import_module(package_name)
                manifest = getattr(pkg, 'MANIFEST', {})
                table_hints = getattr(pkg, 'TABLE_HINTS', {})
                source_hints = getattr(pkg, 'SOURCE_HINTS', {})
                if isinstance(manifest, Mapping) and (table_hints or source_hints):
                    return SchemaBundle(
                        manifest=dict(manifest),
                        table_hints=dict(table_hints),
                        source_hints=dict(source_hints),
                        origin=f'package:{package_name}',
                    )
            except Exception:
                pass

        # 2. direct file path
        for schema_dir in self._candidate_schema_dirs():
            if not schema_dir.exists():
                continue
            manifest_path = schema_dir / 'schema_manifest.py'
            table_path = schema_dir / 'table_hints.py'
            source_path = schema_dir / 'source_hints.py'
            if not (manifest_path.exists() and table_path.exists() and source_path.exists()):
                continue
            try:
                manifest_mod = self._load_module_from_path('_ctx_schema_manifest', manifest_path)
                table_mod = self._load_module_from_path('_ctx_table_hints', table_path)
                source_mod = self._load_module_from_path('_ctx_source_hints', source_path)
                manifest = getattr(manifest_mod, 'MANIFEST', {})
                table_hints = getattr(table_mod, 'TABLE_HINTS', {})
                source_hints = getattr(source_mod, 'SOURCE_HINTS', {})
                return SchemaBundle(
                    manifest=dict(manifest or {}),
                    table_hints=dict(table_hints or {}),
                    source_hints=dict(source_hints or {}),
                    origin=f'path:{schema_dir}',
                )
            except Exception:
                continue
        return bundle

    def reload_schema_artifacts(self) -> SchemaBundle:
        self._schema_bundle = self._load_shipped_bundle()
        self._source_row_cache.clear()
        self._table_row_cache.clear()
        self._table_fields_cache.clear()
        return self._schema_bundle

    @property
    def schema_bundle(self) -> SchemaBundle:
        return self._schema_bundle

    @property
    def artifact_manifest(self) -> dict[str, Any]:
        return dict(self._schema_bundle.manifest)

    @property
    def artifact_version(self) -> str:
        return self._schema_bundle.artifact_version

    # ---------- admin metadata ----------
    @property
    def admin_repo(self):
        return self._admin_repo

    def _admin_source_row(self, source_code: str) -> dict[str, Any] | None:
        if source_code not in self._source_row_cache:
            row = None
            if self.admin_repo is not None and CADM is not None:
                try:
                    row = CSQ.custom_request_c(
                        self.db_files,
                        f"SELECT * FROM {CADM.ADMIN_TABLES['sources']} WHERE source_code = {self.source_code!r}",
                        hat_c=False,
                        one=True
                        # rez_dict=True,
                        # [source_code],
                    )

                except Exception:
                    row = None
            self._source_row_cache[source_code] = row
        return self._source_row_cache[source_code]

    def _admin_source_tables(self, source_code: str) -> list[str]:
        if self.admin_repo is None:
            return []
        try:
            rows = self.admin_repo.get_source_tables(source_code)
            return [row['table_key'] for row in rows]
        except Exception:
            return []

    def _admin_table_row(self, table_key: str) -> dict[str, Any] | None:
        if table_key not in self._table_row_cache:
            row = None
            if self.admin_repo is not None and CADM is not None:
                try:
                    row = CSQ.custom_request_c(
                        self.db_files,
                        f"SELECT * FROM {CADM.ADMIN_TABLES['physical_tables']} WHERE table_key = {table_key!r} LIMIT 1",
                        hat_c=False,
                        list_of_lists_c=[table_key],
                        one=True
                    )

                except Exception:
                    row = None
            self._table_row_cache[table_key] = row
        return self._table_row_cache[table_key]

    def _admin_table_fields(self, table_key: str) -> list[dict[str, Any]]:
        if table_key not in self._table_fields_cache:
            rows: list[dict[str, Any]] = []
            if self.admin_repo is not None:
                try:
                    rows = self.admin_repo.get_table_fields(table_key, include_disabled=False)
                except Exception:
                    rows = []
            self._table_fields_cache[table_key] = rows
        return self._table_fields_cache[table_key]

    def table_hint(self, table_key: str | None) -> dict[str, Any]:
        if not table_key:
            return {}
        shipped = self._schema_bundle.table_hints.get(table_key)
        if isinstance(shipped, Mapping):
            payload = dict(shipped)
            payload.setdefault('table_key', table_key)
            return payload
        row = self._admin_table_row(table_key)
        if not row:
            return {}
        fields = self._admin_table_fields(table_key)
        return {
            'table_key': table_key,
            'db_key': row.get('db_key'),
            'table_name': row.get('table_name'),
            'schema_enabled': row.get('schema_enabled', 1),
            'cache_enabled': row.get('cache_enabled', 1),
            'cache_lifetime_min': row.get('cache_lifetime_min', _DEFAULT_CACHE_LIFETIME_MIN),
            'validity_mark': row.get('validity_mark', ''),
            'fields': fields,
            'origin': 'admin-db',
        }

    def source_hint(self, source_code: str | None) -> dict[str, Any]:
        if not source_code:
            return {}
        shipped = self._schema_bundle.source_hints.get(source_code)
        result: dict[str, Any] = {}
        if isinstance(shipped, Mapping):
            result.update(dict(shipped))
            result.setdefault('origin', 'shipped-artifact')
        row = self._admin_source_row(source_code)
        if row:
            result.setdefault('source_kind', row.get('source_kind', 'sql'))
            result.setdefault('base_table_key', row.get('base_table_key'))
            result.setdefault('schema_source_table_key', row.get('schema_source_table_key'))
            result['cache_enabled'] = row.get('cache_enabled', result.get('cache_enabled', 1))
            result['schema_enabled'] = row.get('schema_enabled', result.get('schema_enabled', 1))
            result['cache_lifetime_min'] = row.get('cache_lifetime_min', result.get('cache_lifetime_min', _DEFAULT_CACHE_LIFETIME_MIN))
            result['stale_after_dt'] = row.get('stale_after_dt', result.get('stale_after_dt'))
            result['validity_mark'] = row.get('validity_mark', result.get('validity_mark', ''))
            result['invalidated_at'] = row.get('invalidated_at', result.get('invalidated_at'))
            result.setdefault('dependencies', self._admin_source_tables(source_code))
            if 'origin' not in result:
                result['origin'] = 'admin-db'
        if not result:
            attr = self.registry.get(source_code)
            if attr is not None:
                deps = list(attr.source_tables)
                result = {
                    'source_kind': attr.source_kind,
                    'base_table_key': attr.base_table_key,
                    'schema_source_table_key': attr.schema_source_table_key,
                    'cache_enabled': 1 if attr.cache_enabled is not False else 0,
                    'schema_enabled': 0 if attr.schema_enabled is None else int(bool(attr.schema_enabled)),
                    'cache_lifetime_min': attr.cache_lifetime_min or _DEFAULT_CACHE_LIFETIME_MIN,
                    'dependencies': deps,
                    'origin': 'runtime-fallback',
                }
        return result

    def get_source_schema(self, name_or_source: str, *, payload: Any = None) -> dict[str, Any]:
        attr = self.registry.get(name_or_source)
        source_code = attr.resolved_source_code() if attr is not None else name_or_source
        source_hint = self.source_hint(source_code)
        schema_table_key = source_hint.get('schema_source_table_key') or source_hint.get('base_table_key')
        table_hint = self.table_hint(schema_table_key)
        fields = table_hint.get('fields') if isinstance(table_hint, Mapping) else None
        inferred = False
        if not fields and payload is not None:
            inferred = True
            fields = infer_payload_schema(payload).get('fields', [])
        return {
            'source_code': source_code,
            'source_kind': source_hint.get('source_kind', attr.source_kind if attr is not None else 'runtime'),
            'base_table_key': source_hint.get('base_table_key'),
            'schema_source_table_key': schema_table_key,
            'dependencies': list(source_hint.get('dependencies') or []),
            'fields': list(fields or []),
            'source_hint': dict(source_hint),
            'table_hint': dict(table_hint or {}),
            'artifact_version': self.artifact_version,
            'generated_at_utc': self._schema_bundle.generated_at_utc,
            'inferred_from_payload': inferred,
        }

    # ---------- cache / invalidation ----------
    def _cache_key(self, source_code: str, variant_fingerprint: str) -> str:
        return f'{source_code}::{variant_fingerprint}'

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def inspect_cache(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    'key': entry.key,
                    'attr_name': entry.attr_name,
                    'source_code': entry.source_code,
                    'variant_fingerprint': entry.variant_fingerprint,
                    'loaded_at': entry.loaded_at,
                    'dependency_fingerprint': entry.dependency_fingerprint,
                    'cache_enabled': entry.cache_enabled,
                    'cache_lifetime_min': entry.cache_lifetime_min,
                    'stale_after_dt': entry.stale_after_dt,
                }
                for entry in self._cache.values()
            ]

    def invalidate_source(self, source_code: str) -> None:
        with self._lock:
            keys = [key for key, entry in self._cache.items() if entry.source_code == source_code]
            for key in keys:
                self._cache.pop(key, None)

    def invalidate_table(self, table_key: str) -> None:
        with self._lock:
            keys = []
            for key, entry in self._cache.items():
                schema = entry.schema or {}
                deps = schema.get('dependencies') or []
                if table_key in deps or entry.table_hint.get('table_key') == table_key:
                    keys.append(key)
            for key in keys:
                self._cache.pop(key, None)

    def _soft_expired(self, entry: CacheEntry) -> bool:
        loaded_at = _parse_dt(entry.loaded_at)
        if loaded_at is None:
            return True
        lifetime = int(entry.cache_lifetime_min or _DEFAULT_CACHE_LIFETIME_MIN)
        if lifetime > 0 and _dt.datetime.now() >= loaded_at + _dt.timedelta(minutes=lifetime):
            return True
        stale_dt = _parse_dt(entry.stale_after_dt)
        if stale_dt is not None and _dt.datetime.now() >= stale_dt:
            return True
        return False

    def _hard_invalidated(self, entry: CacheEntry) -> bool:
        if self.admin_repo is None:
            return False
        source_code = entry.source_code
        if not source_code:
            return False
        try:
            current_dep_fp = self.admin_repo.build_dependency_fingerprint(source_code)
        except Exception:
            current_dep_fp = ''
        if entry.dependency_fingerprint and current_dep_fp and entry.dependency_fingerprint != current_dep_fp:
            return True
        source_row = self._admin_source_row(source_code)
        invalidated_at = _parse_dt((source_row or {}).get('invalidated_at'))
        loaded_at = _parse_dt(entry.loaded_at)
        if invalidated_at is not None and loaded_at is not None and invalidated_at >= loaded_at:
            return True
        return False

    def _should_refresh(self, entry: CacheEntry | None, *, force_refresh: bool, verify_freshness: bool, cache_enabled: bool) -> bool:
        if force_refresh or entry is None:
            return True
        if not cache_enabled:
            return True
        if not verify_freshness:
            return False
        if self._hard_invalidated(entry):
            return True
        if self._soft_expired(entry):
            return True
        return False

    # ---------- admin registration ----------
    def ensure_source_registered(self, attr: Attr) -> None:
        if self.admin_repo is None or not attr.auto_register_source:
            return
        source_code = attr.resolved_source_code()
        existing = self._admin_source_row(source_code)
        if existing is None:
            try:
                self.admin_repo.register_source(
                    source_code=source_code,
                    source_kind=attr.source_kind,
                    base_table_key=attr.base_table_key,
                    schema_source_table_key=attr.schema_source_table_key,
                    schema_enabled=0 if attr.schema_enabled is None else int(bool(attr.schema_enabled)),
                    cache_enabled=1 if attr.cache_enabled is not False else 0,
                    cache_lifetime_min=attr.cache_lifetime_min or _DEFAULT_CACHE_LIFETIME_MIN,
                    stale_after_dt=attr.stale_after_dt,
                    notes=attr.notes or 'auto-registered by context_data runtime',
                )
                self._source_row_cache.pop(source_code, None)
            except Exception:
                return
        deps = list(dict.fromkeys([*attr.source_tables, *(self._admin_source_tables(source_code) or [])]))
        for table_key in deps:
            try:
                self.admin_repo.bind_source_table(source_code=source_code, table_key=table_key)
            except Exception:
                continue

    def _register_variant(self, attr: Attr, *, source_code: str, variant_fingerprint: str, dependency_fingerprint: str, runtime_extras: Mapping[str, Any], resolved_args: Mapping[str, Any]) -> None:
        if self.admin_repo is None:
            return
        sql_text = ''
        sql_template = ''
        if isinstance(attr, DbAttr):
            sql_text = str(runtime_extras.get('_sql') or '')
            sql_template = str(attr.sql_template or '') if attr.sql_template is not None else ''
        try:
            self.admin_repo.register_source_variant(
                source_code=source_code,
                sql_text=sql_text,
                sql_template=sql_template,
                resolved_args={**attr.build_variant_payload(self, resolved_args=resolved_args, runtime_extras=runtime_extras)},
                variant_fingerprint=variant_fingerprint,
                dependency_fingerprint=dependency_fingerprint,
                last_used_at=_local_now(),
                last_refresh_at=_local_now(),
                last_verified_at=_local_now(),
                notes=attr.notes,
            )
        except Exception:
            return

    def _touch_variant(self, source_code: str, variant_fingerprint: str, *, refresh: bool = False, verified: bool = True) -> None:
        if self.admin_repo is None:
            return
        try:
            self.admin_repo.touch_source_variant(
                source_code=source_code,
                variant_fingerprint=variant_fingerprint,
                touch_used=True,
                touch_refresh=refresh,
                touch_verified=verified,
            )
        except Exception:
            return

    # ---------- runtime loading ----------
    def get(self, name_or_attr: str | Attr, *, with_meta: bool = False, force_refresh: bool = False, verify_freshness: bool = True, **kwargs):
        attr: Attr
        attr_name: str
        if isinstance(name_or_attr, Attr):
            attr = name_or_attr
            attr_name = attr.attr_name or attr.resolved_source_code()
        else:
            attr_name = str(name_or_attr)
            attr = self.registry.get(attr_name)
            if attr is None:
                raise KeyError(f'Attr {attr_name!r} не найден')

        source_code = attr.resolved_source_code()
        resolved_args = attr.resolve_runtime_args(self, **kwargs)
        attr.ensure_admin_source(self)
        source_hint = self.source_hint(source_code)
        cache_enabled = bool(source_hint.get('cache_enabled', 1 if attr.cache_enabled is not False else 0))
        cache_lifetime_min = int(source_hint.get('cache_lifetime_min') or attr.cache_lifetime_min or _DEFAULT_CACHE_LIFETIME_MIN)
        stale_after_dt = attr.stale_after_dt or source_hint.get('stale_after_dt')

        preview_extras = attr.preview_runtime_extras(self, resolved_args=resolved_args)
        variant_fingerprint = attr.variant_fingerprint(self, resolved_args=resolved_args, runtime_extras=preview_extras)
        cache_key = self._cache_key(source_code, variant_fingerprint)
        with self._lock:
            entry = self._cache.get(cache_key)

        if not self._should_refresh(entry, force_refresh=force_refresh, verify_freshness=verify_freshness, cache_enabled=cache_enabled):
            self._touch_variant(source_code, entry.variant_fingerprint, refresh=False, verified=True)
            result = LoadResult(
                value=entry.value,
                cache_hit=True,
                cache_key=entry.key,
                source_code=entry.source_code,
                variant_fingerprint=entry.variant_fingerprint,
                dependency_fingerprint=entry.dependency_fingerprint,
                schema=copy.deepcopy(entry.schema),
                source_hint=copy.deepcopy(entry.source_hint),
                table_hint=copy.deepcopy(entry.table_hint),
                resolved_args=copy.deepcopy(entry.resolved_args),
                loaded_at=entry.loaded_at,
            )
            return result if with_meta else entry.value

        value, runtime_extras = attr.materialize(self, resolved_args=resolved_args)
        # second pass: stable fingerprint that also includes resolved SQL/HTTP/runtime extras
        variant_fingerprint = attr.variant_fingerprint(self, resolved_args=resolved_args, runtime_extras=runtime_extras)
        cache_key = self._cache_key(source_code, variant_fingerprint)
        try:
            dependency_fingerprint = self.admin_repo.build_dependency_fingerprint(source_code) if self.admin_repo is not None else ''
        except Exception:
            dependency_fingerprint = ''
        schema = attr.compute_source_schema(self, payload=value)
        table_hint = dict(schema.get('table_hint') or {})
        source_hint = dict(schema.get('source_hint') or source_hint)

        entry = CacheEntry(
            key=cache_key,
            attr_name=attr_name,
            source_code=source_code,
            variant_fingerprint=variant_fingerprint,
            value=value,
            loaded_at=_local_now(),
            dependency_fingerprint=dependency_fingerprint,
            schema=schema,
            source_hint=source_hint,
            table_hint=table_hint,
            resolved_args={**{k: _to_jsonable(v) for k, v in resolved_args.items()}, **{k: _to_jsonable(v) for k, v in runtime_extras.items()}},
            cache_enabled=cache_enabled,
            cache_lifetime_min=cache_lifetime_min,
            stale_after_dt=stale_after_dt,
        )
        if cache_enabled:
            with self._lock:
                self._cache[cache_key] = entry
        self._register_variant(
            attr,
            source_code=source_code,
            variant_fingerprint=variant_fingerprint,
            dependency_fingerprint=dependency_fingerprint,
            runtime_extras=runtime_extras,
            resolved_args=resolved_args,
        )
        self._touch_variant(source_code, variant_fingerprint, refresh=True, verified=True)
        result = LoadResult(
            value=value,
            cache_hit=False,
            cache_key=cache_key,
            source_code=source_code,
            variant_fingerprint=variant_fingerprint,
            dependency_fingerprint=dependency_fingerprint,
            schema=copy.deepcopy(schema),
            source_hint=copy.deepcopy(source_hint),
            table_hint=copy.deepcopy(table_hint),
            resolved_args=copy.deepcopy(entry.resolved_args),
            loaded_at=entry.loaded_at,
        )
        return result if with_meta else value

    def preload(self, *names: str, force_refresh: bool = False) -> dict[str, Any]:
        result = {}
        for name in names:
            result[name] = self.get(name, force_refresh=force_refresh)
        return result

    # ---------- SQL execution ----------
    def execute_sql(
        self,
        *,
        db: str,
        sql: str,
        params: Any = None,
        rez_dict: bool = False,
        one: bool = False,
        one_column: bool = False,
        hat_c: bool = False,
        attach_dbs: Iterable[str] | str | None = None,
    ) -> Any:
        if self._executor is not None:
            return self._executor(
                db=db,
                sql=sql,
                params=params,
                rez_dict=rez_dict,
                one=one,
                one_column=one_column,
                hat_c=hat_c,
                attach_dbs=attach_dbs,
            )

        db = str(resolve_cfg_db(db) or db)
        attach_dbs = tuple(filter(None, (resolve_cfg_db(item) for item in _normalize_attach_dbs(attach_dbs))))
        if db.startswith('SRV:') and CSQ is not None:
            list_of_lists_c = _normalize_params_for_csq(params)
            return CSQ.custom_request_c(
                db,
                sql,
                rez_dict=rez_dict,
                one=one,
                one_column=one_column,
                hat_c=hat_c,
                list_of_lists_c=list_of_lists_c,
                attach_dbs=attach_dbs,
            )
        return self._execute_sqlite_local( # для тестов
            db=db,
            sql=sql,
            params=params,
            rez_dict=rez_dict,
            one=one,
            one_column=one_column,
            hat_c=hat_c,
            attach_dbs=attach_dbs,
        )

    def _execute_sqlite_local(
        self,
        *,
        db: str,
        sql: str,
        params: Any,
        rez_dict: bool,
        one: bool,
        one_column: bool,
        hat_c: bool,
        attach_dbs: Sequence[str],
    ) -> Any:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            for attach_db in attach_dbs:
                attach_db = str(attach_db)
                alias = pathlib.Path(attach_db).stem.replace('-', '_').replace(' ', '_')
                cur.execute(f'ATTACH DATABASE ? AS {alias}', (attach_db,))
            normalized_params = _normalize_params_for_local(params)
            sql_type = str(sql).strip().split(None, 1)[0].upper() if str(sql).strip() else ''
            if isinstance(normalized_params, Mapping):
                cur.execute(sql, normalized_params)
            else:
                if normalized_params in ((), [], None):
                    cur.execute(sql)
                else:
                    cur.execute(sql, normalized_params)

            if sql_type in {'SELECT', 'WITH', 'PRAGMA', 'EXPLAIN'}:
                rows = cur.fetchone() if one else cur.fetchall()
                if rez_dict:
                    if one:
                        return dict(rows) if rows is not None else {}
                    return [dict(row) for row in rows]
                if one:
                    if rows is None:
                        result: list[Any] = []
                    else:
                        result = [list(rows)]
                else:
                    result = [list(row) for row in rows]
                    if hat_c:
                        cols = [col[0] for col in cur.description]
                        result.insert(0, cols)
                if one_column:
                    result = [item[0] for item in result]
                    if one:
                        return result[0] if result else None
                return result

            conn.commit()
            if cur.description is not None:
                rows = cur.fetchone() if one else cur.fetchall()
                if rez_dict:
                    if one:
                        return dict(rows) if rows is not None else {}
                    return [dict(row) for row in rows]
                if one:
                    return [list(rows)] if rows is not None else []
                return [list(row) for row in rows]
            return True
        finally:
            try:
                conn.close()
            except Exception:
                pass


def infer_payload_schema(payload: Any) -> dict[str, Any]:
    """Fallback-инференс по payload, когда admin/shipped schema недоступны."""
    def _guess_type(value: Any) -> str:
        if value is None:
            return 'NoneType'
        if isinstance(value, bool):
            return 'bool'
        if isinstance(value, int) and not isinstance(value, bool):
            return 'int'
        if isinstance(value, float):
            return 'float'
        if isinstance(value, bytes):
            return 'bytes'
        if isinstance(value, Mapping):
            return 'dict'
        if isinstance(value, (list, tuple, set)):
            return 'list'
        return type(value).__name__

    fields: list[dict[str, Any]] = []
    sample_kind = _guess_type(payload)

    if isinstance(payload, Mapping):
        for idx, (key, value) in enumerate(payload.items()):
            fields.append({
                'field_name': str(key),
                'python_name': str(key),
                'db_type': _guess_type(value),
                'nullable': 1 if value is None else 0,
                'is_pk': 0,
                'label': str(key),
                'sort_order': idx,
                'include_in_schema': 1,
                'orm_field_class': '',
                'widget_hint': '',
                'form_hint': '',
            })
    elif isinstance(payload, list) and payload and all(isinstance(item, Mapping) for item in payload):
        ordered_keys: list[str] = []
        for item in payload:
            for key in item.keys():
                skey = str(key)
                if skey not in ordered_keys:
                    ordered_keys.append(skey)
        for idx, key in enumerate(ordered_keys):
            values = [item.get(key) for item in payload if isinstance(item, Mapping)]
            non_null = next((val for val in values if val is not None), None)
            fields.append({
                'field_name': key,
                'python_name': key,
                'db_type': _guess_type(non_null),
                'nullable': 0 if all(val is not None for val in values) else 1,
                'is_pk': 0,
                'label': key,
                'sort_order': idx,
                'include_in_schema': 1,
                'orm_field_class': '',
                'widget_hint': '',
                'form_hint': '',
            })
        sample_kind = 'list[dict]'
    elif isinstance(payload, list):
        fields = [{
            'field_name': 'value',
            'python_name': 'value',
            'db_type': _guess_type(payload[0]) if payload else 'Any',
            'nullable': 1 if any(item is None for item in payload) else 0,
            'is_pk': 0,
            'label': 'value',
            'sort_order': 0,
            'include_in_schema': 1,
            'orm_field_class': '',
            'widget_hint': '',
            'form_hint': '',
        }]
        sample_kind = 'list'
    else:
        fields = [{
            'field_name': 'value',
            'python_name': 'value',
            'db_type': _guess_type(payload),
            'nullable': 1 if payload is None else 0,
            'is_pk': 0,
            'label': 'value',
            'sort_order': 0,
            'include_in_schema': 1,
            'orm_field_class': '',
            'widget_hint': '',
            'form_hint': '',
        }]

    return {
        'sample_kind': sample_kind,
        'fields': fields,
        'inferred_from_payload': True,
        'generated_at_utc': _utc_now(),
    }
