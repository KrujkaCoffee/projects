from __future__ import annotations

"""Pure database/table identity helpers for MES.

This module MUST stay import-side-effect free.  In particular it must not import
CFG, Cust_config, Cust_client_socket, Cust_SQLite, context_admin or any GUI
module.  It is safe to import from server cache/invalidation code and from
schema generation code.

Canonical policy
----------------
The stable ``db_key`` is the physical SQLite file stem:
``Naryad``, ``DB_kplan``, ``BD_users`` ... .  Historic configuration attribute
names such as ``db_naryad`` remain accepted aliases, but are never used for new
rows.  Existing administrative rows are not renamed automatically; callers
must resolve aliases against the database and either reuse the single existing
row or stop on a conflict.
"""

from dataclasses import dataclass
import re
from typing import Any, Iterable


UNKNOWN_DB_KEY = "unknown_db"
DEFAULT_SERVER_ROOT = "C:/DB_srv"


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
        """Values that may historically occur in ``admin_physical_tables.db_key``."""
        values = [self.canonical_key]
        if self.config_attr:
            values.append(self.config_attr)
        if self.filename:
            values.extend((self.filename, _strip_db_suffix(self.filename)))
        values.extend(self.aliases)
        return _ordered_unique(value for value in values if value)


_KNOWN_IDENTITIES: tuple[DbIdentity, ...] = (
    DbIdentity("Naryad", "Naryad.db", "db_naryad"),
    DbIdentity("BD_dse", "BD_dse.db", "db_dse"),
    DbIdentity("BD_resxml", "BD_resxml.db", "db_resxml"),
    DbIdentity("BD_files", "BD_files.db", "db_files"),
    DbIdentity("DB_kplan", "DB_kplan.db", "db_kplan"),
    DbIdentity("BD_users", "BD_users.db", "db_users"),
    DbIdentity("DB_nomenklatura_erp", "DB_nomenklatura_erp.db", "db_nomen"),
    DbIdentity("db_flet", "db_flet.db", "db_flet"),
    DbIdentity("DB_xl_formulas", "DB_xl_formulas.db", "xl_formulas"),
)


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


def _strip_db_suffix(value: str) -> str:
    text = str(value or "").strip()
    return text[:-3] if text.casefold().endswith(".db") else text


def _basename(value: Any) -> str:
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        return ""
    if text.upper().startswith("SRV:"):
        text = text.split(":", 1)[1]
    text = text.replace("\\", "/").rstrip("/")
    return text.rsplit("/", 1)[-1]


def _normalized_token(value: Any) -> str:
    text = _basename(value)
    return text.strip()


def _identity_lookup() -> dict[str, DbIdentity]:
    result: dict[str, DbIdentity] = {}
    for identity in _KNOWN_IDENTITIES:
        values = list(identity.all_db_keys())
        values.extend((identity.srv_name, f"{DEFAULT_SERVER_ROOT}/{identity.filename}"))
        for value in values:
            marker = _normalized_token(value).casefold()
            if marker:
                result[marker] = identity
            stem_marker = _strip_db_suffix(_normalized_token(value)).casefold()
            if stem_marker:
                result[stem_marker] = identity
    return result


_IDENTITY_BY_TOKEN = _identity_lookup()


def resolve_db_identity(value: Any) -> DbIdentity:
    """Return a canonical identity without importing any MES runtime module."""
    token = _normalized_token(value)
    if not token:
        return DbIdentity(UNKNOWN_DB_KEY, "")

    direct = _IDENTITY_BY_TOKEN.get(token.casefold())
    if direct is not None:
        return direct

    stem = _strip_db_suffix(token)
    direct = _IDENTITY_BY_TOKEN.get(stem.casefold())
    if direct is not None:
        return direct

    # Unknown databases still receive a deterministic file-stem identity.
    canonical = stem or UNKNOWN_DB_KEY
    canonical = re.sub(r"\s+", "_", canonical).strip() or UNKNOWN_DB_KEY
    filename = token if token.casefold().endswith(".db") else f"{canonical}.db"
    return DbIdentity(canonical, filename)


def canonical_db_key(value: Any) -> str:
    return resolve_db_identity(value).canonical_key


def equivalent_db_keys(value: Any) -> tuple[str, ...]:
    return resolve_db_identity(value).all_db_keys()


def make_table_key(db_key_or_path: Any, table_name: Any) -> str:
    table = str(table_name or "").strip()
    if not table:
        raise ValueError("table_name is empty")
    return f"{canonical_db_key(db_key_or_path)}.{table}"


def split_table_key(table_key: Any) -> tuple[str, str]:
    text = str(table_key or "").strip()
    if "." not in text:
        return text, ""
    return tuple(text.split(".", 1))  # type: ignore[return-value]


def equivalent_table_keys(db_key_or_path: Any, table_name: Any) -> tuple[str, ...]:
    table = str(table_name or "").strip()
    if not table:
        return ()
    return _ordered_unique(f"{key}.{table}" for key in equivalent_db_keys(db_key_or_path))


def equivalent_table_keys_from_key(table_key: Any) -> tuple[str, ...]:
    db_key, table_name = split_table_key(table_key)
    if not table_name:
        return (str(table_key or "").strip(),) if str(table_key or "").strip() else ()
    return equivalent_table_keys(db_key, table_name)


def server_db_path(value: Any, root: str = DEFAULT_SERVER_ROOT) -> str:
    identity = resolve_db_identity(value)
    if not identity.filename:
        return ""
    return f"{str(root).rstrip('/\\')}/{identity.filename}"


def srv_db_name(value: Any) -> str:
    identity = resolve_db_identity(value)
    return identity.srv_name


__all__ = [
    "DbIdentity",
    "UNKNOWN_DB_KEY",
    "DEFAULT_SERVER_ROOT",
    "resolve_db_identity",
    "canonical_db_key",
    "equivalent_db_keys",
    "make_table_key",
    "split_table_key",
    "equivalent_table_keys",
    "equivalent_table_keys_from_key",
    "server_db_path",
    "srv_db_name",
]
