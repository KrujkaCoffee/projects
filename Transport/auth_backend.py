from __future__ import annotations

import ctypes
import os
import secrets
import threading
import time
from ctypes import wintypes

DEFAULT_DOMAIN = os.getenv("MES_AUTH_DEFAULT_DOMAIN", "POWERZ")
SESSION_COOKIE_NAME = "mes_auth_sid"
MONTH_SECONDS = 60 * 60 * 24 * 30
SESSION_TTL_SECONDS = MONTH_SECONDS

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
        raise ValueError("Введите логин.")

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
    """In-memory sessions."""

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


SESSIONS = SessionStore(SESSION_TTL_SECONDS)
