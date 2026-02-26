import contextvars

import flet as ft

import win32api
import win32security


current_win_user = contextvars.ContextVar("win_user", default="")


def user_from_iis_token_handle(token_handle_hex: str) -> str:
    """token_handle_hex берём из заголовка X-IIS-WindowsAuthToken."""
    token_handle_hex = (token_handle_hex or "").strip()
    if token_handle_hex.lower().startswith("0x"):
        token_handle_hex = token_handle_hex[2:]

    h = int(token_handle_hex, 16)
    try:
        sid = win32security.GetTokenInformation(h, win32security.TokenUser)[0]
        user, domain, _ = win32security.LookupAccountSid(None, sid)
        return f"{domain}\\{user}"
    finally:
        win32api.CloseHandle(h)


class IISWindowsUserMiddleware:
    """ASGI middleware: на каждом HTTP/WS запросе читает X-IIS-WindowsAuthToken
    и сохраняет user в contextvar на время обработки соединения.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = {}
        for k, v in scope.get("headers", []):
            headers[k.decode("latin1").lower()] = v.decode("latin1")

        token = headers.get("x-iis-windowsauthtoken", "")
        user = ""
        if token:
            try:
                user = user_from_iis_token_handle(token)
            except Exception:
                user = ""

        ctx = current_win_user.set(user)
        try:
            await self.app(scope, receive, send)
        finally:
            current_win_user.reset(ctx)



if __name__ == "__main__":
    async def main(page: ft.Page):
        user = current_win_user.get() or "unknown"

        page.session.set("win_user", user)

        page.add(
            ft.Text(f"Windows user: {user}")
        )
    _inner = ft.app(main, export_asgi_app=True, host='localhost', port=6000)
    app = IISWindowsUserMiddleware(_inner)

    # ft.run(main)
    # ft.app(target=main,
    #        host='localhost',
    #        )