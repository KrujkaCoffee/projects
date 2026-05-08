from __future__ import annotations

from typing import Any, Iterable

from project_cust_38 import context_admin as CADM
from project_cust_38 import context_schema_generator as CSG
from project_cust_38 import srv_sql_cache as SQLCACHE
from project_cust_38 import context_registers as CREG


__all__ = ['ContextAdminService']


class ContextAdminService:
    def __init__(self, repo: CADM.ContextAdminRepo | None = None,
                 cache: SQLCACHE.FileRequestCache | None = None,
                 register_repo: CREG.RegisterAdminRepo | None = None):
        self.repo = repo or CADM.ContextAdminRepo()
        self.cache = cache or SQLCACHE.FileRequestCache()
        self.register_repo = register_repo

    def bootstrap_db(self, db_path: str, table_names=None, skip_tables=None, include_fields: bool = True,
                     schema_enabled: bool = True, cache_enabled: bool = True, is_enabled: bool = True,
                     cache_lifetime_min: int = 120, notes: str = '') -> dict[str, Any]:
        table_keys = self.repo.bootstrap_tables_from_db(
            db_path=db_path,
            table_names=table_names,
            include_fields=include_fields,
            schema_enabled=1 if schema_enabled else 0,
            cache_enabled=1 if cache_enabled else 0,
            is_enabled=1 if is_enabled else 0,
            cache_lifetime_min=cache_lifetime_min,
            notes=notes,
            skip_tables=skip_tables,
        )
        return {
            'db_path': db_path,
            'table_keys': table_keys,
            'count': len([item for item in table_keys if item]),
        }

    def bootstrap_table(self, db_path: str, table_name: str, include_fields: bool = True,
                        schema_enabled: bool = True, cache_enabled: bool = True, is_enabled: bool = True,
                        cache_lifetime_min: int = 120, notes: str = '') -> dict[str, Any]:
        table_key = self.repo.bootstrap_physical_table(
            db_path=db_path,
            table_name=table_name,
            include_fields=include_fields,
            schema_enabled=1 if schema_enabled else 0,
            cache_enabled=1 if cache_enabled else 0,
            is_enabled=1 if is_enabled else 0,
            cache_lifetime_min=cache_lifetime_min,
            notes=notes,
        )
        fields = self.repo.get_table_fields(table_key=table_key, include_disabled=True) if table_key else []
        return {
            'db_path': db_path,
            'table_name': table_name,
            'table_key': table_key,
            'field_count': len(fields),
        }

    def preview_schema_diff(self, output_dir=None) -> dict[str, Any]:
        return CSG.preview_schema_diff(output_dir=output_dir)

    def apply_schema_generation(self, output_dir=None, debug: bool = False, force: bool = False) -> dict[str, Any]:
        diff = self.preview_schema_diff(output_dir=output_dir)
        if diff.get('has_breaking_changes') and not force:
            return {
                'applied': False,
                'reason': 'breaking_changes',
                'diff': diff,
            }
        result = CSG.generate_schema_artifacts(output_dir=output_dir, debug=debug)
        return {
            'applied': True,
            'diff': diff,
            **result,
        }

    def latest_manifest(self) -> dict[str, Any] | None:
        return self.repo.latest_manifest()

    def list_registered_tables(self) -> list[dict[str, Any]]:
        return self.repo.get_physical_tables()

    def list_table_fields(self, table_key: str | None = None) -> list[dict[str, Any]]:
        return self.repo.get_table_fields(table_key=table_key, include_disabled=True)

    def clear_server_cache(self) -> dict[str, Any]:
        self.cache.clear()
        return {
            'ok': True,
            'cache_dir': str(self.cache.cache_dir),
        }

    def invalidate_tables(self, table_names: Iterable[str], notes: str = 'ui_admin') -> dict[str, Any]:
        details = self.cache.invalidate_by_table_names(table_names, notes=notes, return_details=True)
        return details or {'ok': False, 'table_names': [], 'table_keys': []}

    def list_register_types(self) -> dict[str, Any]:
        return {
            'storage_kinds': CREG.RegisterTypes.StorageKind.rows(),
            'register_kinds': CREG.RegisterTypes.RegisterKind.rows(),
            'refresh_policies': CREG.RegisterTypes.RefreshPolicy.rows(),
            'source_kinds': CREG.RegisterTypes.SourceKind.rows(),
        }

    def _ensure_register_repo(self) -> CREG.RegisterAdminRepo:
        if self.register_repo is None:
            self.register_repo = CREG.RegisterAdminRepo()
        return self.register_repo

    def register_spec(self, **kwargs) -> dict[str, Any]:
        repo = self._ensure_register_repo()
        spec = CREG.RegisterSpec(**kwargs).normalized()
        ok = repo.upsert_spec(spec)
        return {
            'ok': bool(ok),
            'spec': spec.to_dict(),
        }

    def list_register_specs(self, enabled: bool | None = None) -> list[dict[str, Any]]:
        repo = self._ensure_register_repo()
        normalized_enabled = None if enabled is None else (1 if enabled else 0)
        return [spec.to_dict() for spec in repo.list_specs(enabled=normalized_enabled)]

    def get_register_spec(self, code: str) -> dict[str, Any] | None:
        repo = self._ensure_register_repo()
        spec = repo.get_spec(code)
        return spec.to_dict() if spec else None

    def resolve_virtual_register(self, code: str, rows, *, as_of=None) -> list[dict[str, Any]]:
        repo = self._ensure_register_repo()
        spec = repo.get_spec(code)
        if spec is None:
            raise ValueError(f'Регистр {code!r} не найден')
        if spec.storage_kind != CREG.RegisterTypes.StorageKind.VIRTUAL.value:
            raise ValueError(f'Регистр {code!r} не является виртуальным')
        return CREG.RegisterRuntime.resolve(spec, rows, as_of=as_of)
