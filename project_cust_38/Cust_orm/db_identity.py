from __future__ import annotations

import os.path
import typing
from dataclasses import dataclass
import re
from typing import Any, Iterable

from project_cust_38 import Cust_Functions as F

if typing.TYPE_CHECKING:
    import project_cust_38.Cust_client_socket as CCS
else:
    CCS = F.LazyModule("project_cust_38.Cust_client_socket", namespace=globals(), global_name="CCS")

@dataclass(frozen=True)
class DbIdentity:
    canonical_key: str
    filename: str
    config_attr: str = ""
    aliases: tuple[str, ...] = ()

    @property
    def srv_name(self) -> str:
        return f"SRV:{self.filename}" if self.filename else ""

    def all_db_keys(self) -> tuple[str, ...]:
        values = [self.canonical_key]
        if self.config_attr:
            values.append(self.config_attr)
        if self.filename:
            values.extend((self.filename, DbKeyResolver._strip_db_suffix(self.filename)))
        values.extend(self.aliases)
        return DbKeyResolver._ordered_unique(value for value in values if value)

class DbKeyResolver:
    UNKNOWN_DB_KEY = "unknown_db"
    DEFAULT_SERVER_ROOT = "C:/DB_srv"

    KNOWN_IDENTITIES: tuple[DbIdentity, ...] = tuple()
    IDENTITY_BY_TOKEN: dict[str, DbIdentity] = dict()

    def __getattribute__(self, item):
        if item not in ("KNOWN_IDENTITIES", "IDENTITY_BY_TOKEN", "_identity_lookup", "fill_cls_attributes"):
            if (not object.__getattribute__(self, "KNOWN_IDENTITIES")
                    or not object.__getattribute__(self, "IDENTITY_BY_TOKEN")):
                identities = tuple(
                    DbIdentity(*self.make_db_identity(db.alias, db.attribute_name))
                for db in CCS.Servers)
                token = self._identity_lookup()
                type(self).fill_cls_attributes(identities, token)
        return object.__getattribute__(self, item)

    @classmethod
    def fill_cls_attributes(cls, identities, token):
        cls.KNOWN_IDENTITIES = identities
        cls.IDENTITY_BY_TOKEN = token

    def make_db_identity(self, alias: str, attribute_name: str) -> tuple[str, str, str]:
        no_db, ext = os.path.splitext(alias)
        return (no_db, alias, attribute_name)

    @staticmethod
    def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
        result: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            marker = value.casefold()
            if marker in seen:
                continue
            seen.add(marker)
            result.append(value)
        return tuple(result)

    @staticmethod
    def _strip_db_suffix(value: str) -> str:
        text = str(value or "").strip()
        return text[:-3] if text.casefold().endswith(".db") else text

    def _basename(self, value: Any) -> str:
        text = str(value or "").strip().strip('"').strip("'")
        if not text:
            return ""
        if text.upper().startswith("SRV:"):
            text = text.split(":", 1)[1]
        text = text.replace("\\", "/").rstrip("/")
        return text.rsplit("/", 1)[-1]

    def _normalized_token(self, value: Any) -> str:
        text = self._basename(value)
        return text.strip()


    def _identity_lookup(self) -> dict[str, DbIdentity]:
        result: dict[str, DbIdentity] = {}
        for identity in self.KNOWN_IDENTITIES:
            values = list(identity.all_db_keys())
            values.extend((identity.srv_name, f"{self.DEFAULT_SERVER_ROOT}/{identity.filename}"))
            for value in values:
                marker = self._normalized_token(value).casefold()
                if marker:
                    result[marker] = identity
                stem_marker = self._strip_db_suffix(self._normalized_token(value)).casefold()
                if stem_marker:
                    result[stem_marker] = identity
        return result

    def resolve_db_identity(self, value: Any) -> DbIdentity:
        token = self.normalized_token(value)
        if not token:
            return DbIdentity(self.UNKNOWN_DB_KEY, "")

        direct = self.IDENTITY_BY_TOKEN.get(token.casefold())
        if direct is not None:
            return direct

        stem = self._strip_db_suffix(token)
        direct = self.IDENTITY_BY_TOKEN.get(stem.casefold())
        if direct is not None:
            return direct

        canonical = stem or self.UNKNOWN_DB_KEY
        canonical = re.sub(r"\s+", "_", canonical).strip() or self.UNKNOWN_DB_KEY
        filename = token if token.casefold().endswith(".db") else f"{canonical}.db"
        return DbIdentity(canonical, filename)

    def canonical_db_key(self, value: Any) -> str:
        return self.resolve_db_identity(value).canonical_key

    def equivalent_db_keys(self, value: Any) -> tuple[str, ...]:
        return self.resolve_db_identity(value).all_db_keys()

    def make_table_key(self, db_key_or_path: Any, table_name: Any) -> str:
        table = str(table_name or "").strip()
        if not table:
            raise ValueError("table_name is empty")
        return f"{self.canonical_db_key(db_key_or_path)}.{table}"

    def split_table_key(self, table_key: Any) -> tuple[str, str]:
        text = str(table_key or "").strip()
        if "." not in text:
            return text, ""
        return tuple(text.split(".", 1))

    def equivalent_table_keys(self, db_key_or_path: Any, table_name: Any) -> tuple[str, ...]:
        table = str(table_name or "").strip()
        if not table:
            return ()
        return self._ordered_unique(f"{key}.{table}" for key in self.equivalent_db_keys(db_key_or_path))

    def equivalent_table_keys_from_key(self, table_key: Any) -> tuple[str, ...]:
        db_key, table_name = self.split_table_key(table_key)
        if not table_name:
            return (str(table_key or "").strip(),) if str(table_key or "").strip() else ()
        return self.equivalent_table_keys(db_key, table_name)

    def server_db_path(self, value: Any, root: str = None) -> str:
        if root is None:
            root = self.DEFAULT_SERVER_ROOT
        identity = self.resolve_db_identity(value)
        if not identity.filename:
            return ""
        return f"{str(root).rstrip('/\\')}/{identity.filename}"

    def srv_db_name(self, value: Any) -> str:
        identity = self.resolve_db_identity(value)
        return identity.srv_name

key_resolver = DbKeyResolver()



__all__ = [
    "DbIdentity",
    "key_resolver",
]
