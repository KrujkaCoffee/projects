from __future__ import annotations

import contextvars
from http.cookies import SimpleCookie
from urllib.parse import quote

from auth_backend import SESSION_COOKIE_NAME, SESSIONS

current_auth_user = contextvars.ContextVar("auth_user", default=None)


class SessionAuthMiddleware:
    def __init__(self, app, login_path: str = "/auth/login", public_prefixes: tuple[str, ...] = ("/auth",)):
        self.app = app
        self.login_path = login_path
        self.public_prefixes = public_prefixes

    async def __call__(self, scope, receive, send):
        scope_type = scope.get("type")
        if scope_type not in {"http", "websocket", "lifespan"}:
            await self.app(scope, receive, send)
            return

        if scope_type == "lifespan":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "") or "/"

        if self._is_public_path(path):
            await self.app(scope, receive, send)
            return

        sid = self._parse_cookie(scope, SESSION_COOKIE_NAME)
        user = SESSIONS.get(sid)

        if not user:
            if scope_type == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return

            method = (scope.get("method") or "GET").upper()
            if method in {"GET", "HEAD"}:
                next_url = self._build_next_url(scope)
                location = f"{self.login_path}?next={quote(next_url, safe='/?:=&')}"
                await send(
                    {
                        "type": "http.response.start",
                        "status": 302,
                        "headers": [(b"location", location.encode("utf-8"))],
                    }
                )
                await send({"type": "http.response.body", "body": b""})
                return

            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": b"Authentication required"})
            return

        scope.setdefault("state", {})
        scope["state"]["auth_user"] = user
        scope["state"]["auth_sid"] = sid

        ctx = current_auth_user.set(user)
        try:
            await self.app(scope, receive, send)
        finally:
            current_auth_user.reset(ctx)

    def _is_public_path(self, path: str) -> bool:
        for prefix in self.public_prefixes:
            normalized = prefix.rstrip("/")
            if path == normalized or path.startswith(normalized + "/"):
                return True
        return False

    @staticmethod
    def _parse_cookie(scope, name: str) -> str | None:
        raw_cookie = None
        for key, value in scope.get("headers", []):
            if key == b"cookie":
                raw_cookie = value.decode("utf-8", "ignore")
                break

        if not raw_cookie:
            return None

        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        morsel = cookie.get(name)
        return morsel.value if morsel else None

    @staticmethod
    def _build_next_url(scope) -> str:
        path = scope.get("path", "/") or "/"
        query_string = scope.get("query_string", b"").decode("utf-8", "ignore")
        if query_string:
            return f"{path}?{query_string}"
        return path
