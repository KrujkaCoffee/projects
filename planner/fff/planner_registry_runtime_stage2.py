from __future__ import annotations

import dataclasses
import inspect
import logging
import math
import os
import re
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

try:
    from . import planner_registry_stage2 as registry
except ImportError:
    import planner_registry_stage2 as registry


logger = logging.getLogger(__name__)


class PlannerPoolError(registry.PlannerRepositoryError):
    """Пул не смог безопасно выдать или вернуть соединение."""


class PlannerRuntimeError(registry.PlannerRegistryError):
    """Интеграционный контур planner registry не завершил операцию."""


class PlannerBootstrapError(registry.PlannerRegistryError):
    """Первичная регистрация не может быть применена без ручного решения."""


@dataclass(frozen=True)
class PlannerPoolSettings:
    min_size: int = 0
    max_size: int = 4
    max_waiting: int = 8
    acquire_timeout_sec: float = 5.0
    max_idle_sec: float = 60.0
    max_lifetime_sec: float = 900.0
    reconnect_timeout_sec: float = 10.0
    connect_timeout_sec: float = 5.0
    statement_timeout_ms: int = 15_000
    lock_timeout_ms: int = 3_000
    idle_in_transaction_timeout_ms: int = 10_000
    application_name: str = "mes_planner_registry"
    keep_idle_connections: bool = True
    check_on_checkout: bool = True
    num_workers: int = 1

    def validate(self) -> None:
        if self.min_size < 0:
            raise PlannerPoolError("min_size не может быть отрицательным.")
        if self.max_size < 1:
            raise PlannerPoolError("max_size должен быть не меньше 1.")
        if self.min_size > self.max_size:
            raise PlannerPoolError("min_size не может быть больше max_size.")
        if not self.keep_idle_connections and self.min_size != 0:
            raise PlannerPoolError(
                "Для NullConnectionPool min_size должен быть равен 0."
            )
        if self.max_waiting < 1:
            raise PlannerPoolError(
                "max_waiting должен быть ограничен положительным числом."
            )
        for caption, value in (
            ("acquire_timeout_sec", self.acquire_timeout_sec),
            ("max_idle_sec", self.max_idle_sec),
            ("max_lifetime_sec", self.max_lifetime_sec),
            ("reconnect_timeout_sec", self.reconnect_timeout_sec),
            ("connect_timeout_sec", self.connect_timeout_sec),
        ):
            if value <= 0:
                raise PlannerPoolError(f"{caption} должен быть больше нуля.")
        for caption, value in (
            ("statement_timeout_ms", self.statement_timeout_ms),
            ("lock_timeout_ms", self.lock_timeout_ms),
            (
                "idle_in_transaction_timeout_ms",
                self.idle_in_transaction_timeout_ms,
            ),
        ):
            if value <= 0:
                raise PlannerPoolError(f"{caption} должен быть больше нуля.")
        if self.num_workers < 1:
            raise PlannerPoolError("num_workers должен быть не меньше 1.")
        if not self.application_name.strip():
            raise PlannerPoolError("application_name не должен быть пустым.")

    def connection_kwargs(self) -> dict[str, Any]:
        options = " ".join(
            (
                f"-c statement_timeout={int(self.statement_timeout_ms)}",
                f"-c lock_timeout={int(self.lock_timeout_ms)}",
                "-c idle_in_transaction_session_timeout="
                f"{int(self.idle_in_transaction_timeout_ms)}",
            )
        )
        return {
            "autocommit": False,
            "connect_timeout": max(1, int(math.ceil(self.connect_timeout_sec))),
            "application_name": self.application_name,
            "options": options,
        }


class _PooledConnectionLease:
    def __init__(
        self,
        owner: "PsycopgPlannerPool",
        pool: Any,
        connection: Any,
    ) -> None:
        self._owner = owner
        self._pool = pool
        self._connection = connection
        self._closed = False
        self._lock = threading.Lock()

    @property
    def autocommit(self) -> Any:
        return getattr(self._connection, "autocommit", None)

    @autocommit.setter
    def autocommit(self, value: Any) -> None:
        self._connection.autocommit = value

    def cursor(self, *args: Any, **kwargs: Any) -> Any:
        return self._connection.cursor(*args, **kwargs)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._owner._return_connection(self._pool, self._connection)

    def __enter__(self) -> "_PooledConnectionLease":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc is not None:
            try:
                self.rollback()
            except Exception as rollback_exc:
                if hasattr(exc, "add_note"):
                    exc.add_note(
                        f"Дополнительно не удалось выполнить rollback: {rollback_exc}"
                    )
        try:
            self.close()
        except Exception as close_exc:
            if exc is not None and hasattr(exc, "add_note"):
                exc.add_note(
                    f"Дополнительно не удалось вернуть connection в pool: {close_exc}"
                )
            elif exc is None:
                raise
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


class PsycopgPlannerPool:
    def __init__(
        self,
        conninfo: str | Callable[[], str],
        settings: PlannerPoolSettings | None = None,
        *,
        pool_class: type | None = None,
    ) -> None:
        self.conninfo = conninfo
        self.settings = settings or PlannerPoolSettings()
        self.settings.validate()
        self._pool_class = pool_class
        self._pool: Any | None = None
        self._native_checkout_check = False
        self._lock = threading.RLock()

    def open(self, *, verify: bool = True) -> None:
        with self._lock:
            if self._pool is not None:
                return
            pool_class = self._pool_class or self._load_pool_class()
            conninfo = self._pool_conninfo(pool_class)

            constructor_kwargs: dict[str, Any] = {
                "conninfo": conninfo,
                "kwargs": self.settings.connection_kwargs(),
                "min_size": self.settings.min_size,
                "max_size": self.settings.max_size,
                "open": False,
                "timeout": self.settings.acquire_timeout_sec,
                "max_waiting": self.settings.max_waiting,
                "max_lifetime": self.settings.max_lifetime_sec,
                "max_idle": self.settings.max_idle_sec,
                "reconnect_timeout": self.settings.reconnect_timeout_sec,
                "num_workers": self.settings.num_workers,
                "name": self.settings.application_name,
            }
            native_check = getattr(pool_class, "check_connection", None)
            if self.settings.check_on_checkout and callable(native_check):
                if self._accepts_keyword(pool_class, "check"):
                    constructor_kwargs["check"] = native_check
                    self._native_checkout_check = True

            pool = pool_class(**constructor_kwargs)
            try:
                pool.open()
                self._pool = pool
                if verify:
                    self.probe()
            except Exception as exc:
                self._pool = None
                try:
                    pool.close()
                except Exception:
                    pass
                raise PlannerPoolError(
                    f"Пул PostgreSQL не прошёл стартовую проверку: {exc}"
                ) from exc

    def close(self) -> None:
        with self._lock:
            pool = self._pool
            self._pool = None
        if pool is None:
            return
        try:
            pool.close()
        except Exception as exc:
            raise PlannerPoolError(f"Не удалось закрыть пул PostgreSQL: {exc}") from exc

    def get_connection(self) -> _PooledConnectionLease:
        pool = self._require_pool()
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                connection = pool.getconn(timeout=self.settings.acquire_timeout_sec)
            except Exception as exc:
                raise PlannerPoolError(
                    "Пул PostgreSQL не выдал соединение за "
                    f"{self.settings.acquire_timeout_sec:g} сек.: {exc}"
                ) from exc
            if not self.settings.check_on_checkout or self._native_checkout_check:
                return _PooledConnectionLease(self, pool, connection)
            try:
                self._check_raw_connection(connection)
                return _PooledConnectionLease(self, pool, connection)
            except Exception as exc:
                last_error = exc
                self._discard_failed_checkout(pool, connection, exc)
                if attempt == 0:
                    continue
        raise PlannerPoolError(
            f"Пул дважды выдал нерабочее соединение: {last_error}"
        ) from last_error

    def connection_factory(self) -> _PooledConnectionLease:
        return self.get_connection()

    def probe(self) -> None:
        connection = self.get_connection()
        cursor = None
        operation_error: BaseException | None = None
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if row is None:
                raise PlannerPoolError("PostgreSQL не вернул результат SELECT 1.")
            connection.rollback()
        except PlannerPoolError as exc:
            operation_error = exc
            raise
        except Exception as exc:
            try:
                connection.rollback()
            except Exception:
                pass
            operation_error = PlannerPoolError(
                f"Проверка соединения PostgreSQL завершилась ошибкой: {exc}"
            )
            raise operation_error from exc
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            try:
                connection.close()
            except Exception as close_exc:
                message = (
                    f"Не удалось вернуть connection стартовой проверки: {close_exc}"
                )
                if operation_error is not None and hasattr(operation_error, "add_note"):
                    operation_error.add_note(message)
                elif operation_error is None:
                    raise PlannerPoolError(message) from close_exc

    def stats(self) -> dict[str, Any]:
        pool = self._require_pool()
        getter = getattr(pool, "get_stats", None)
        return dict(getter() or {}) if callable(getter) else {}

    def __enter__(self) -> "PsycopgPlannerPool":
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.close()
        return False

    def _return_connection(self, pool: Any, connection: Any) -> None:
        cleanup_error: Exception | None = None
        if self._transaction_needs_rollback(connection):
            try:
                connection.rollback()
            except Exception as exc:
                cleanup_error = exc
        try:
            pool.putconn(connection)
        except Exception as exc:
            if cleanup_error is None:
                cleanup_error = exc
        if cleanup_error is not None:
            raise PlannerPoolError(
                f"Соединение не удалось безопасно вернуть в пул: {cleanup_error}"
            ) from cleanup_error

    def _require_pool(self) -> Any:
        with self._lock:
            if self._pool is None:
                raise PlannerPoolError(
                    "Пул PostgreSQL не открыт. Сначала вызовите open()."
                )
            return self._pool

    def _load_pool_class(self) -> type:
        try:
            import psycopg_pool
        except ImportError as exc:
            raise PlannerPoolError(
                "Не найден psycopg_pool. Установите psycopg-pool в MES-интерпретатор."
            ) from exc
        if self.settings.keep_idle_connections:
            return psycopg_pool.ConnectionPool
        return psycopg_pool.NullConnectionPool

    def _pool_conninfo(
        self,
        pool_class: type,
    ) -> str | Callable[[], str]:
        if not callable(self.conninfo):
            value = str(self.conninfo or "").strip()
            if not value:
                raise PlannerPoolError("Не передана строка подключения PostgreSQL.")
            return value

        provider = self.conninfo

        def checked_provider() -> str:
            try:
                value = str(provider() or "").strip()
            except Exception as exc:
                raise PlannerPoolError(
                    f"Функция conninfo завершилась ошибкой: {exc}"
                ) from exc
            if not value:
                raise PlannerPoolError(
                    "Функция conninfo вернула пустую строку подключения PostgreSQL."
                )
            return value

        if self._supports_callable_conninfo(pool_class):
            return checked_provider
        return checked_provider()

    @staticmethod
    def _supports_callable_conninfo(pool_class: type) -> bool:
        explicit = getattr(
            pool_class,
            "_planner_supports_callable_conninfo",
            None,
        )
        if explicit is not None:
            return bool(explicit)

        module_name = str(getattr(pool_class, "__module__", ""))
        if not module_name.startswith("psycopg_pool"):
            return False
        try:
            import psycopg_pool
        except ImportError:
            return False
        match = re.match(r"^(\d+)\.(\d+)", str(psycopg_pool.__version__))
        if match is None:
            return False
        return tuple(map(int, match.groups())) >= (3, 3)

    @staticmethod
    def _discard_failed_checkout(
        pool: Any,
        connection: Any,
        check_error: BaseException,
    ) -> None:
        cleanup_errors: list[str] = []
        try:
            connection.close()
        except Exception as exc:
            cleanup_errors.append(f"close: {exc}")
        try:
            pool.putconn(connection)
        except Exception as exc:
            cleanup_errors.append(f"putconn: {exc}")
        if cleanup_errors:
            error = PlannerPoolError(
                "Нерабочее соединение не удалось исключить из пула: "
                + "; ".join(cleanup_errors)
            )
            if hasattr(error, "add_note"):
                error.add_note(f"Исходная ошибка проверки: {check_error}")
            raise error from check_error

    @staticmethod
    def _accepts_keyword(callable_obj: Any, name: str) -> bool:
        try:
            signature = inspect.signature(callable_obj)
        except (TypeError, ValueError):
            return False
        if name in signature.parameters:
            return True
        return any(
            item.kind is inspect.Parameter.VAR_KEYWORD
            for item in signature.parameters.values()
        )

    @staticmethod
    def _transaction_needs_rollback(connection: Any) -> bool:
        info = getattr(connection, "info", None)
        status = getattr(info, "transaction_status", None)
        if status is None:
            return True
        name = str(getattr(status, "name", status)).upper()
        if name == "IDLE" or status == 0:
            return False
        if name in {"UNKNOWN", "BAD"}:
            return False
        return True

    @staticmethod
    def _check_raw_connection(connection: Any) -> None:
        cursor = connection.cursor()
        operation_error: BaseException | None = None
        try:
            cursor.execute("SELECT 1")
            if cursor.fetchone() is None:
                raise PlannerPoolError("Проверка соединения не вернула SELECT 1.")
            connection.rollback()
        except BaseException as exc:
            operation_error = exc
            _rollback_without_masking(connection, exc)
            raise
        finally:
            try:
                cursor.close()
            except Exception as close_exc:
                message = f"Не удалось закрыть check-cursor: {close_exc}"
                if operation_error is not None and hasattr(operation_error, "add_note"):
                    operation_error.add_note(message)
                elif operation_error is None:
                    raise PlannerPoolError(message) from close_exc


class PostgresAdminCatalogReader:
    _queries = (
        (
            "tables",
            "SELECT * FROM public.admin_physical_tables "
            "ORDER BY db_key, table_name, table_key",
        ),
        (
            "fields",
            "SELECT * FROM public.admin_table_fields "
            "ORDER BY table_key, sort_order, field_name",
        ),
        (
            "relations",
            "SELECT * FROM public.admin_table_relations "
            "ORDER BY source_table_key, relation_name, relation_key",
        ),
        (
            "pairs",
            "SELECT * FROM public.admin_relation_field_pairs "
            "ORDER BY relation_key, pair_no",
        ),
    )

    def __init__(
        self,
        connection_factory: Callable[[], Any],
        *,
        disconnect_checker: Callable[[BaseException], bool] | None = None,
    ) -> None:
        self.connection_factory = connection_factory
        self.disconnect_checker = disconnect_checker or is_psycopg_disconnect_error

    def load(self) -> registry.AdminCatalog:
        for attempt in range(2):
            try:
                return self._load_once()
            except registry.PlannerCatalogError:
                raise
            except BaseException as exc:
                if attempt == 0 and self.disconnect_checker(exc):
                    logger.warning(
                        "Чтение admin-каталога повторяется один раз после обрыва соединения."
                    )
                    continue
                if isinstance(exc, registry.PlannerRegistryError):
                    raise
                raise registry.PlannerRepositoryError(
                    f"Не удалось прочитать единый снимок admin-каталога: {exc}"
                ) from exc
        raise AssertionError("Недостижимая ветка повторного чтения каталога.")

    def _load_once(self) -> registry.AdminCatalog:
        connection = self.connection_factory()
        if connection is None:
            raise PlannerPoolError("Фабрика не вернула PostgreSQL-соединение.")
        cursor = None
        rows: dict[str, list[dict[str, Any]]] = {}
        operation_error: BaseException | None = None
        try:
            if getattr(connection, "autocommit", None) is not None:
                connection.autocommit = False
            cursor = connection.cursor()
            cursor.execute(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
            )
            for key, sql in self._queries:
                cursor.execute(sql)
                rows[key] = _fetch_dict_rows(cursor)
            connection.rollback()
        except BaseException as exc:
            operation_error = exc
            _rollback_without_masking(connection, exc)
            raise
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            try:
                connection.close()
            except Exception as close_exc:
                message = (
                    f"Не удалось освободить connection чтения каталога: {close_exc}"
                )
                if operation_error is not None and hasattr(operation_error, "add_note"):
                    operation_error.add_note(message)
                elif operation_error is None:
                    raise PlannerPoolError(message) from close_exc
        return registry.AdminCatalog.from_rows(
            rows["tables"],
            rows["fields"],
            rows["relations"],
            rows["pairs"],
        )


class PlannerSchemaInstaller:
    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.connection_factory = connection_factory

    def install(self) -> int:
        statements = _split_sql_statements(registry.POSTGRES_MIGRATION_SQL)
        connection = self.connection_factory()
        if connection is None:
            raise PlannerPoolError("Фабрика не вернула PostgreSQL-соединение.")
        cursor = None
        commit_started = False
        operation_error: BaseException | None = None
        try:
            if getattr(connection, "autocommit", None) is not None:
                connection.autocommit = False
            cursor = connection.cursor()
            for statement in statements:
                cursor.execute(statement)
            commit_started = True
            connection.commit()
            return len(statements)
        except BaseException as exc:
            if commit_started:
                operation_error = registry.PlannerCommitOutcomeUnknown(
                    "PostgreSQL не подтвердил COMMIT миграции planner.*. "
                    "Не запускайте миграцию повторно до проверки схемы."
                )
                raise operation_error from exc
            operation_error = exc
            _rollback_without_masking(connection, exc)
            if isinstance(exc, registry.PlannerRegistryError):
                raise
            raise PlannerRuntimeError(
                f"Миграция planner.* отменена: {exc}"
            ) from exc
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            try:
                connection.close()
            except Exception as close_exc:
                message = f"Не удалось освободить соединение миграции: {close_exc}"
                if operation_error is not None and hasattr(operation_error, "add_note"):
                    operation_error.add_note(message)
                elif operation_error is None:
                    raise PlannerPoolError(message) from close_exc


@dataclass(frozen=True)
class CatalogHealthIssue:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class CatalogHealthReport:
    table_count: int
    field_count: int
    relation_count: int
    pair_count: int
    issues: tuple[CatalogHealthIssue, ...] = ()

    @property
    def has_errors(self) -> bool:
        return any(item.level == "error" for item in self.issues)

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def inspect_catalog(catalog: registry.AdminCatalog) -> CatalogHealthReport:
    issues: list[CatalogHealthIssue] = []
    identity_groups: dict[str, list[registry.AdminTable]] = {}
    for table in catalog.tables.values():
        identity_groups.setdefault(table.table_key.casefold(), []).append(table)
    collisions = [items for items in identity_groups.values() if len(items) > 1]
    ambiguous = [
        items
        for items in collisions
        if sum(int(item.schema_enabled) for item in items) != 1
    ]
    if collisions:
        issues.append(
            CatalogHealthIssue(
                level="warning",
                code="casefold_table_identity",
                message=(
                    f"Обнаружено {len(collisions)} групп table_key, различающихся регистром. "
                    "Модуль не нормализует их автоматически."
                ),
            )
        )
    if ambiguous:
        issues.append(
            CatalogHealthIssue(
                level="error",
                code="ambiguous_schema_table_identity",
                message=(
                    f"В {len(ambiguous)} группах нельзя выбрать единственную "
                    "schema_enabled таблицу."
                ),
            )
        )
    without_pairs = [
        item.relation_key
        for item in catalog.relations.values()
        if item.is_enabled and not item.field_pairs
    ]
    if without_pairs:
        issues.append(
            CatalogHealthIssue(
                level="warning",
                code="relation_without_pairs",
                message=(
                    "Активные relations без пар полей: " + ", ".join(without_pairs)
                ),
            )
        )
    return CatalogHealthReport(
        table_count=len(catalog.tables),
        field_count=len(catalog.fields),
        relation_count=len(catalog.relations),
        pair_count=sum(len(item.field_pairs) for item in catalog.relations.values()),
        issues=tuple(issues),
    )


@dataclass(frozen=True)
class InitialSeedDefinition:
    configs: tuple[registry.PlannerSourceConfig, ...]
    warnings: tuple[str, ...] = ()


def build_initial_seed(catalog: registry.AdminCatalog) -> InitialSeedDefinition:
    _require_catalog_fields(
        catalog,
        "DB_kplan.podrazdel",
        ("Пномер", "Имя", "Цвет"),
    )
    _require_catalog_fields(
        catalog,
        "Naryad.mk",
        ("Пномер", "Номенклатура", "Тип", "Дата", "Дата_завершения"),
    )

    resource_key = "gant.resource.podrazdel"
    event_key = "gant.event.mk"
    resource = registry.PlannerSourceConfig(
        source=registry.PlannerSource(
            source_key=resource_key,
            subject_code="gant",
            table_key="DB_kplan.podrazdel",
            caption="Подразделения",
            identity_field_name="Пномер",
            sort_order=10,
        ),
        roles=(registry.SourceRole.RESOURCE,),
        requisites=(
            registry.PlannerRequisite(
                requisite_key=f"{resource_key}.req.name",
                source_key=resource_key,
                field_name="Имя",
                caption="Имя",
                semantic_role=registry.SemanticRole.LABEL,
                sort_order=10,
            ),
            registry.PlannerRequisite(
                requisite_key=f"{resource_key}.req.color",
                source_key=resource_key,
                field_name="Цвет",
                caption="Цвет",
                semantic_role=registry.SemanticRole.COLOR,
                sort_order=20,
            ),
        ),
        presentations=(
            registry.PlannerPresentation(
                presentation_key=f"{resource_key}.view.default",
                source_key=resource_key,
                source_field_name="Пномер",
                result_table_key="DB_kplan.podrazdel",
                result_field_name="Имя",
                caption="Имя подразделения",
                is_default=True,
            ),
        ),
    )

    event_presentations: list[registry.PlannerPresentation] = [
        registry.PlannerPresentation(
            presentation_key=f"{event_key}.view.default",
            source_key=event_key,
            source_field_name="Пномер",
            result_table_key="Naryad.mk",
            result_field_name="Номенклатура",
            caption="Номенклатура МК",
            is_default=True,
            sort_order=10,
        )
    ]
    warnings: list[str] = []
    type_relation = _find_scalar_relation(
        catalog,
        source_table_key="Naryad.mk",
        source_field_name="Тип",
        target_result_field="Имя",
    )
    if type_relation is None:
        reverse_relations = [
            item.relation_key
            for item in catalog.relations.values()
            if item.target_table_key == "Naryad.mk"
            and any(pair.right_field_name == "Тип" for pair in item.field_pairs)
        ]
        suffix = (
            " Обнаружена только обратная связь: " + ", ".join(reverse_relations) + "."
            if reverse_relations
            else ""
        )
        warnings.append(
            "Presentation Тип МК → Имя не добавлено: нет корректной исходящей "
            "many_to_one/one_to_one relation от Naryad.mk.Тип." + suffix
        )
    else:
        target_table_key, relation_key = type_relation
        event_presentations.append(
            registry.PlannerPresentation(
                presentation_key=f"{event_key}.view.type",
                source_key=event_key,
                source_field_name="Тип",
                result_table_key=target_table_key,
                result_field_name="Имя",
                caption="Имя типа МК",
                relation_steps=(relation_key,),
                sort_order=20,
            )
        )

    event = registry.PlannerSourceConfig(
        source=registry.PlannerSource(
            source_key=event_key,
            subject_code="gant",
            table_key="Naryad.mk",
            caption="Маршрутные карты",
            identity_field_name="Пномер",
            sort_order=20,
        ),
        roles=(registry.SourceRole.EVENT,),
        requisites=(
            registry.PlannerRequisite(
                requisite_key=f"{event_key}.req.name",
                source_key=event_key,
                field_name="Номенклатура",
                caption="Номенклатура",
                semantic_role=registry.SemanticRole.LABEL,
                sort_order=10,
            ),
            registry.PlannerRequisite(
                requisite_key=f"{event_key}.req.type",
                source_key=event_key,
                field_name="Тип",
                caption="Тип МК",
                sort_order=20,
            ),
            registry.PlannerRequisite(
                requisite_key=f"{event_key}.req.start",
                source_key=event_key,
                field_name="Дата",
                caption="Дата начала",
                semantic_role=registry.SemanticRole.START,
                sort_order=30,
            ),
            registry.PlannerRequisite(
                requisite_key=f"{event_key}.req.end",
                source_key=event_key,
                field_name="Дата_завершения",
                caption="Дата завершения",
                semantic_role=registry.SemanticRole.END,
                sort_order=40,
            ),
        ),
        presentations=tuple(event_presentations),
    )
    return InitialSeedDefinition(configs=(resource, event), warnings=tuple(warnings))


@dataclass(frozen=True)
class BootstrapResult:
    planned: tuple[str, ...] = ()
    created: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    dry_run: bool = True


class PlannerRegistryBootstrapper:
    def __init__(self, service: registry.PlannerRegistryService) -> None:
        self.service = service

    def apply(
        self,
        definition: InitialSeedDefinition,
        *,
        dry_run: bool = True,
        replace_existing: bool = False,
    ) -> BootstrapResult:
        existing = {
            item.source.source_key: item for item in self.service.list_configs()
        }
        table_owners = {
            (item.source.subject_code, item.source.table_key): item.source.source_key
            for item in existing.values()
        }
        planned: list[registry.PlannerSourceConfig] = []
        skipped: list[str] = []
        warnings = list(definition.warnings)

        for config in definition.configs:
            source_key = config.source.source_key
            current = existing.get(source_key)
            if current is not None and not replace_existing:
                skipped.append(source_key)
                if current != config:
                    warnings.append(
                        f"{source_key!r} уже существует и не был перезаписан."
                    )
                continue
            owner = table_owners.get(
                (config.source.subject_code, config.source.table_key)
            )
            if owner is not None and owner != source_key:
                raise PlannerBootstrapError(
                    f"Таблица {config.source.table_key!r} уже принадлежит {owner!r}."
                )
            self.service.validator.validate(config)
            planned.append(config)

        if not dry_run and planned:
            self.service.save_configs(planned)
        keys = tuple(item.source.source_key for item in planned)
        return BootstrapResult(
            planned=keys,
            created=() if dry_run else keys,
            skipped=tuple(skipped),
            warnings=tuple(warnings),
            dry_run=dry_run,
        )


@dataclass
class PlannerRegistryRuntime:
    pool: PsycopgPlannerPool
    catalog: registry.AdminCatalog
    repository: registry.CustOrmPlannerRegistryRepository
    service: registry.PlannerRegistryService
    disconnect_checker: Callable[[BaseException], bool] = field(
        default_factory=lambda: is_psycopg_disconnect_error,
        repr=False,
    )

    @classmethod
    def connect(
        cls,
        conninfo: str | Callable[[], str],
        *,
        pool_settings: PlannerPoolSettings | None = None,
        corm_module: Any | None = None,
        pool_class: type | None = None,
        disconnect_checker: Callable[[BaseException], bool] | None = None,
    ) -> "PlannerRegistryRuntime":
        checker = disconnect_checker or is_psycopg_disconnect_error
        pool = PsycopgPlannerPool(
            conninfo,
            settings=pool_settings,
            pool_class=pool_class,
        )
        pool.open()
        try:
            catalog = PostgresAdminCatalogReader(
                pool.connection_factory,
                disconnect_checker=checker,
            ).load()
            repository = registry.CustOrmPlannerRegistryRepository(
                connection_factory=pool.connection_factory,
                corm_module=corm_module,
                close_connection=True,
                planner_schema=registry.PLANNER_SCHEMA,
            )
            service = registry.PlannerRegistryService(catalog, repository)
            return cls(
                pool=pool,
                catalog=catalog,
                repository=repository,
                service=service,
                disconnect_checker=checker,
            )
        except BaseException as exc:
            try:
                pool.close()
            except Exception as close_exc:
                if hasattr(exc, "add_note"):
                    exc.add_note(
                        f"Дополнительно не удалось закрыть pool: {close_exc}"
                    )
            raise

    def install_schema(self) -> int:
        return PlannerSchemaInstaller(self.pool.connection_factory).install()

    def reload_catalog(self) -> registry.AdminCatalog:
        catalog = PostgresAdminCatalogReader(
            self.pool.connection_factory,
            disconnect_checker=self.disconnect_checker,
        ).load()
        self.catalog = catalog
        self.service = registry.PlannerRegistryService(catalog, self.repository)
        return catalog

    def list_sources(
        self,
        subject_code: str | None = None,
        *,
        role: registry.SourceRole | str | None = None,
    ) -> list[registry.PlannerSourceConfig]:
        items = self._read_with_one_disconnect_retry(
            lambda: self.service.list_configs(subject_code)
        )
        if role is None:
            return items
        normalized_role = (
            role if isinstance(role, registry.SourceRole) else registry.SourceRole(role)
        )
        return [item for item in items if normalized_role in item.roles]

    def get_source(self, source_key: str) -> registry.PlannerSourceConfig | None:
        return self._read_with_one_disconnect_retry(
            lambda: self.service.get_config(source_key)
        )

    def save_source(self, config: registry.PlannerSourceConfig) -> None:
        self.service.save_config(config)

    def save_sources(self, configs: Sequence[registry.PlannerSourceConfig]) -> None:
        self.service.save_configs(configs)

    def delete_source(self, source_key: str) -> None:
        self.service.delete_config(source_key)

    def initial_seed(
        self,
        *,
        dry_run: bool = True,
        replace_existing: bool = False,
    ) -> BootstrapResult:
        definition = build_initial_seed(self.catalog)
        return PlannerRegistryBootstrapper(self.service).apply(
            definition,
            dry_run=dry_run,
            replace_existing=replace_existing,
        )

    def available_tables(
        self,
        *,
        schema_enabled_only: bool = True,
    ) -> tuple[registry.AdminTable, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.catalog.tables.values()
                    if not schema_enabled_only or item.schema_enabled
                ),
                key=lambda item: (item.db_key, item.table_name, item.table_key),
            )
        )

    def available_fields(self, table_key: str) -> tuple[registry.AdminField, ...]:
        return self.catalog.table_fields(table_key)

    def available_relations(
        self,
        table_key: str,
    ) -> tuple[registry.AdminRelation, ...]:
        return self.catalog.outgoing_relations(table_key)

    def catalog_bundle(self) -> dict[str, Any]:
        relations = []
        pairs = []
        for relation in self.catalog.relations.values():
            relation_data = dataclasses.asdict(relation)
            relation_data.pop("field_pairs", None)
            relations.append(relation_data)
            pairs.extend(dataclasses.asdict(item) for item in relation.field_pairs)
        return {
            "tables": [
                dataclasses.asdict(item) for item in self.catalog.tables.values()
            ],
            "fields": [
                dataclasses.asdict(item) for item in self.catalog.fields.values()
            ],
            "relations": relations,
            "pairs": pairs,
        }

    def health(self) -> dict[str, Any]:
        return {
            "catalog": inspect_catalog(self.catalog).as_dict(),
            "pool": self.pool.stats(),
        }

    def close(self) -> None:
        self.pool.close()

    def __enter__(self) -> "PlannerRegistryRuntime":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        try:
            self.close()
        except Exception as close_exc:
            if exc is not None and hasattr(exc, "add_note"):
                exc.add_note(
                    f"Дополнительно не удалось закрыть runtime pool: {close_exc}"
                )
            elif exc is None:
                raise
        return False

    def _read_with_one_disconnect_retry(self, operation: Callable[[], Any]) -> Any:
        for attempt in range(2):
            try:
                return operation()
            except BaseException as exc:
                if attempt == 0 and self.disconnect_checker(exc):
                    logger.warning(
                        "Read-only запрос planner registry повторяется один раз после обрыва."
                    )
                    continue
                raise
        raise AssertionError("Недостижимая ветка повторного чтения.")


def is_psycopg_disconnect_error(error: BaseException) -> bool:
    try:
        import psycopg
    except ImportError:
        return False
    disconnect_types = tuple(
        item
        for item in (
            getattr(psycopg, "OperationalError", None),
            getattr(psycopg, "InterfaceError", None),
        )
        if isinstance(item, type)
    )
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if disconnect_types and isinstance(current, disconnect_types):
            return True
        current = current.__cause__ or current.__context__
    return False


def _fetch_dict_rows(cursor: Any) -> list[dict[str, Any]]:
    rows = cursor.fetchall() or []
    if not rows:
        return []
    if isinstance(rows[0], Mapping):
        return [dict(item) for item in rows]
    names = []
    for column in cursor.description or ():
        name = getattr(column, "name", None)
        if name is None:
            name = column[0]
        names.append(str(name))
    return [dict(zip(names, item)) for item in rows]


def _rollback_without_masking(connection: Any, original_error: BaseException) -> None:
    try:
        connection.rollback()
    except Exception as rollback_exc:
        if hasattr(original_error, "add_note"):
            original_error.add_note(
                f"Дополнительно не удалось выполнить rollback: {rollback_exc}"
            )


def _split_sql_statements(sql: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(sql):
        char = sql[index]
        if quote is not None:
            buffer.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    buffer.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
        elif char in {"'", '"'}:
            quote = char
            buffer.append(char)
        elif char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer.clear()
        else:
            buffer.append(char)
        index += 1
    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return tuple(statements)


def _require_catalog_fields(
    catalog: registry.AdminCatalog,
    table_key: str,
    field_names: Iterable[str],
) -> None:
    table = catalog.tables.get(table_key)
    if table is None:
        raise PlannerBootstrapError(
            f"Для первичного seed отсутствует таблица {table_key!r}."
        )
    if not table.schema_enabled:
        raise PlannerBootstrapError(
            f"Таблица {table_key!r} не включена в schema-каталог."
        )
    missing = [
        name for name in field_names if (table_key, name) not in catalog.fields
    ]
    if missing:
        raise PlannerBootstrapError(
            f"Для {table_key!r} отсутствуют поля seed: {', '.join(missing)}."
        )


def _find_scalar_relation(
    catalog: registry.AdminCatalog,
    *,
    source_table_key: str,
    source_field_name: str,
    target_result_field: str,
) -> tuple[str, str] | None:
    matches: list[tuple[str, str]] = []
    for relation in catalog.outgoing_relations(source_table_key):
        if relation.cardinality not in {"many_to_one", "one_to_one"}:
            continue
        target_table = catalog.tables.get(relation.target_table_key)
        if target_table is None or not target_table.schema_enabled:
            continue
        if not relation.field_pairs:
            continue
        if not any(
            item.left_table_key == source_table_key
            and item.left_field_name == source_field_name
            and item.operator == "="
            for item in relation.field_pairs
        ):
            continue
        if (relation.target_table_key, target_result_field) not in catalog.fields:
            continue
        matches.append((relation.target_table_key, relation.relation_key))
    if len(matches) > 1:
        raise PlannerBootstrapError(
            f"Для {source_table_key}.{source_field_name} найдено несколько relations: "
            + ", ".join(item[1] for item in matches)
        )
    return matches[0] if matches else None


def config_to_dict(config: registry.PlannerSourceConfig) -> dict[str, Any]:
    return {
        "source": dataclasses.asdict(config.source),
        "roles": [item.value for item in config.roles],
        "requisites": [
            {
                **dataclasses.asdict(item),
                "semantic_role": item.semantic_role.value,
            }
            for item in config.requisites
        ],
        "presentations": [
            {
                **dataclasses.asdict(item),
                "presentation_kind": item.kind.value,
            }
            for item in config.presentations
        ],
    }


def _run_demo() -> int:
    try:
        from PyQt5 import QtWidgets
    except ImportError:
        print(
            "PyQt5 не найден. Запустите runtime-стенд в MES-интерпретаторе с PyQt5.15.",
            file=sys.stderr,
        )
        return 2

    class RuntimeWindow(QtWidgets.QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.runtime: PlannerRegistryRuntime | None = None
            self.setWindowTitle("Planner registry — PostgreSQL runtime test")
            self.resize(980, 680)
            layout = QtWidgets.QVBoxLayout(self)

            form = QtWidgets.QFormLayout()
            self.conninfo = QtWidgets.QLineEdit(
                os.getenv("MES_PLANNER_PG_DSN", "")
            )
            self.conninfo.setPlaceholderText(
                "postgresql://user:password@host:5432/database"
            )
            self.conninfo.setEchoMode(QtWidgets.QLineEdit.Password)
            form.addRow("PostgreSQL DSN:", self.conninfo)
            layout.addLayout(form)

            buttons = QtWidgets.QHBoxLayout()
            for caption, callback in (
                ("Подключить и прочитать каталог", self.open_runtime),
                ("Установить planner.*", self.install_schema),
                ("Предпросмотр seed", self.preview_seed),
                ("Применить seed", self.apply_seed),
                ("Показать регистрации", self.show_sources),
                ("Статистика пула", self.show_stats),
            ):
                button = QtWidgets.QPushButton(caption)
                button.clicked.connect(callback)
                buttons.addWidget(button)
            layout.addLayout(buttons)

            self.output = QtWidgets.QPlainTextEdit()
            self.output.setReadOnly(True)
            layout.addWidget(self.output)

        def append(self, text: str) -> None:
            self.output.appendPlainText(text)

        def require_runtime(self) -> PlannerRegistryRuntime:
            if self.runtime is None:
                raise PlannerRuntimeError(
                    "Сначала подключите runtime к PostgreSQL."
                )
            return self.runtime

        def open_runtime(self) -> None:
            try:
                if self.runtime is not None:
                    self.runtime.close()
                self.runtime = PlannerRegistryRuntime.connect(
                    self.conninfo.text().strip()
                )
                report = inspect_catalog(self.runtime.catalog)
                self.append(
                    "Каталог прочитан: "
                    f"tables={report.table_count}, fields={report.field_count}, "
                    f"relations={report.relation_count}, pairs={report.pair_count}."
                )
                for issue in report.issues:
                    self.append(f"[{issue.level}] {issue.message}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка подключения", str(exc))

        def install_schema(self) -> None:
            try:
                runtime = self.require_runtime()
                answer = QtWidgets.QMessageBox.question(
                    self,
                    "Подтверждение",
                    "Создать или проверить пять таблиц в схеме planner?",
                )
                if answer != QtWidgets.QMessageBox.Yes:
                    return
                count = runtime.install_schema()
                self.append(f"Миграция выполнена: SQL statements={count}.")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка миграции", str(exc))

        def preview_seed(self) -> None:
            try:
                result = self.require_runtime().initial_seed(dry_run=True)
                self.append(f"Seed planned={list(result.planned)}")
                self.append(f"Seed skipped={list(result.skipped)}")
                for warning in result.warnings:
                    self.append(f"[warning] {warning}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка seed", str(exc))

        def apply_seed(self) -> None:
            try:
                runtime = self.require_runtime()
                answer = QtWidgets.QMessageBox.question(
                    self,
                    "Подтверждение записи",
                    "Добавить только отсутствующие стартовые регистрации?",
                )
                if answer != QtWidgets.QMessageBox.Yes:
                    return
                result = runtime.initial_seed(dry_run=False)
                self.append(f"Seed created={list(result.created)}")
                self.append(f"Seed skipped={list(result.skipped)}")
                for warning in result.warnings:
                    self.append(f"[warning] {warning}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка seed", str(exc))

        def show_sources(self) -> None:
            try:
                items = self.require_runtime().list_sources("gant")
                if not items:
                    self.append("Регистрации gant отсутствуют.")
                for item in items:
                    roles = ", ".join(role.value for role in item.roles)
                    self.append(
                        f"{item.source.source_key}: {item.source.table_key} [{roles}]"
                    )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка чтения", str(exc))

        def show_stats(self) -> None:
            try:
                self.append(str(self.require_runtime().health()))
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка статистики", str(exc))

        def closeEvent(self, event) -> None:
            if self.runtime is not None:
                try:
                    self.runtime.close()
                except Exception:
                    pass
            super().closeEvent(event)

    application = QtWidgets.QApplication(sys.argv)
    window = RuntimeWindow()
    window.show()
    return application.exec_()


if __name__ == "__main__":
    raise SystemExit(_run_demo())
