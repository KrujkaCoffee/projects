from __future__ import annotations

import ctypes
import json
import os
import secrets
import threading
import time
from ctypes import wintypes

import project_cust_38.Cust_SQLite as CSQ
from project_cust_38.Cust_config import Config as CFG
from Config import srv_config

DEFAULT_DOMAIN = srv_config.DEFAULT_DOMAIN
SESSION_COOKIE_NAME = srv_config.SESSION_COOKIE_NAME
MONTH_SECONDS = srv_config.MONTH_SECONDS
SESSION_TTL_SECONDS = MONTH_SECONDS
DB_SESSION_TABLE = srv_config.DB_SESSION_TABLE
DB_SESSION_PATH = os.getenv("MES_AUTH_SESSION_DB", "SRV:db_flet.db")

LOGON32_LOGON_NETWORK = 3
LOGON32_PROVIDER_DEFAULT = 0

advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LogonUserW = advapi32.LogonUserW
LogonUserW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
]
LogonUserW.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL


def normalize_login(raw_login: str) -> tuple[str, str | None, str]:
    login = (raw_login or "").strip()
    if not login:
        raise ValueError("Неверный логин или пароль.")

    if "\\" in login:
        domain, username = login.split("\\", 1)
        domain = domain.strip()
        username = username.strip()
        if not domain or not username:
            raise ValueError("Неверный формат логина.")
        return username, domain, f"{domain}\\{username}"

    if "@" in login:
        return login, None, login.lower()

    if not DEFAULT_DOMAIN:
        raise ValueError("Не задан домен по умолчанию.")

    return login, DEFAULT_DOMAIN, f"{DEFAULT_DOMAIN}\\{login}"


def authenticate_windows_user(raw_login: str, password: str) -> tuple[dict | None, int | None]:
    username, domain, canonical_login = normalize_login(raw_login)

    token = wintypes.HANDLE()
    ok = LogonUserW(
        username,
        domain,
        password,
        LOGON32_LOGON_NETWORK,
        LOGON32_PROVIDER_DEFAULT,
        ctypes.byref(token),
    )
    if not ok:
        return None, ctypes.get_last_error()

    try:
        return {
            "login": canonical_login,
            "display_name": canonical_login,
            "source": "form",
        }, None
    finally:
        if token:
            CloseHandle(token)


class SessionStore:
    """Виртуальные сессии (хранение до перезагрузки сервера)"""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._items: dict[str, dict] = {}
        self._last_cleanup = 0.0

    def create(self, user: dict) -> str:
        sid = secrets.token_urlsafe(32)
        with self._lock:
            self._items[sid] = {
                "user": user,
                "expires_at": time.time() + self.ttl_seconds,
            }
        return sid

    def get(self, sid: str | None, touch: bool = True) -> dict | None:
        if not sid:
            return None

        now = time.time()
        with self._lock:
            item = self._items.get(sid)
            if not item:
                return None
            if item["expires_at"] <= now:
                self._items.pop(sid, None)
                return None
            if touch:
                item["expires_at"] = now + self.ttl_seconds
            return item["user"]

    def delete(self, sid: str | None) -> None:
        if not sid:
            return
        with self._lock:
            self._items.pop(sid, None)

    def cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup < 60:
            return
        with self._lock:
            expired = [sid for sid, item in self._items.items() if item["expires_at"] <= now]
            for sid in expired:
                self._items.pop(sid, None)
            self._last_cleanup = now


class DbSessionStore:
    """Интерфейс сессий через бд.
        Создать сессию -> получить id сессии
            create(user) -> sid
        Получить юзера по id сессии
            get(sid, touch=True) -> user | None
        Удалить сессию по id
            delete(sid) -> None
        Удалить устаревшие сессии
            cleanup() -> None
    """

    def __init__(
        self,
        db_path: str = DB_SESSION_PATH,
        table_name: str = DB_SESSION_TABLE,
        ttl_seconds: int = SESSION_TTL_SECONDS,
        cleanup_interval_seconds: int = 60,
    ) -> None:
        self.db_path = db_path
        self.table_name = table_name
        self.ttl_seconds = ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._lock = threading.RLock()
        self._last_cleanup = 0.0

    @staticmethod
    def _quote(value: str) -> str:
        return str(value).replace("'", "''")

    @staticmethod
    def _serialize_user(user: dict) -> str:
        return json.dumps(user, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _deserialize_user(raw: str | None) -> dict | None:
        if not raw:
            return None
        value = json.loads(raw)
        return value if isinstance(value, dict) else None

    def create(self, user: dict) -> str:
        self.cleanup()
        for _ in range(3):
            sid = secrets.token_urlsafe(32)
            now = time.time()
            expires_at = now + self.ttl_seconds
            try:
                ok = CSQ.custom_request_c(
                    self.db_path,
                    f"""
                    INSERT INTO {self.table_name} (
                        sid,
                        user_json,
                        created_at,
                        expires_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    list_of_lists_c=[[sid, self._serialize_user(user), now, expires_at, now]],
                )
            except Exception:
                ok = False
            if ok:
                return sid
        raise RuntimeError("Не удалось создать DB-сессию")

    def get(self, sid: str | None, touch: bool = True) -> dict | None:
        if not sid:
            return None

        now = time.time()
        sid_sql = self._quote(sid)

        with self._lock:
            row = CSQ.custom_request_c(
                self.db_path,
                f"""
                SELECT sid, user_json, created_at, expires_at, updated_at
                FROM {self.table_name}
                WHERE sid = '{sid_sql}'
                LIMIT 1;
                """,
                rez_dict=True,
                one=True,
            )
            if not row:
                return None

            expires_at = float(row.get("expires_at") or 0.0)
            if expires_at <= now:
                self.delete(sid)
                return None

            user = self._deserialize_user(row.get("user_json"))
            if user is None:
                self.delete(sid)
                return None

            if touch:
                new_expires_at = now + self.ttl_seconds
                CSQ.custom_request_c(
                    self.db_path,
                    f"""
                    UPDATE {self.table_name}
                    SET expires_at = ?,
                        updated_at = ?
                    WHERE sid = ?;
                    """,
                    list_of_lists_c=[new_expires_at, now, sid],
                )

            return user

    def delete(self, sid: str | None) -> None:
        if not sid:
            return
        sid_sql = self._quote(sid)
        with self._lock:
            CSQ.custom_request_c(
                self.db_path,
                f"DELETE FROM {self.table_name} WHERE sid = '{sid_sql}';",
            )

    def cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval_seconds:
            return
        with self._lock:
            CSQ.custom_request_c(
                self.db_path,
                f"DELETE FROM {self.table_name} WHERE expires_at <= {float(now)};",
            )
            self._last_cleanup = now


if srv_config.USE_DB_SESSION:
    SESSIONS = DbSessionStore(
        db_path=CFG.project.db_flet,
        table_name=DB_SESSION_TABLE,
        ttl_seconds=SESSION_TTL_SECONDS,
    )
else:
    SESSIONS = SessionStore(SESSION_TTL_SECONDS)
