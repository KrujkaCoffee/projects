from __future__ import annotations

import logging
import mimetypes
import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs

from starlette.responses import Response

import Config.srv_config as SRVCFG
import components.modules as modules
import components.settings as SETGS
import data_class as DTCLS
import flet as ft
import flet.fastapi as flet_fastapi
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from flet import View

from auth_backend import MONTH_SECONDS, SESSION_COOKIE_NAME, SESSIONS, authenticate_windows_user
from middleware import SessionAuthMiddleware, current_auth_user

ver = 0.03

FLET_PATH = ""
FLET_PORT = SRVCFG.PORT
FLET_HOST = SRVCFG.HOST
IN_BROUSER = SRVCFG.IN_BROUSER

name_title = "MES app"
name = "Веб приложение МЕС"

LOGIN_PATH = f"/auth/login"
LOGOUT_PATH = f"/auth/logout"
AUTH_COOKIE_SECURE = socket.gethostname() not in ("POW18-08", "POW18-15")

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("application/wasm", ".wasm")

logging.basicConfig(level=logging.INFO)

os.environ.setdefault("FLET_ASSETS_DIR", str((Path(__file__).resolve().parent / "assets").resolve()))


def resolve_pathf_it_plan() -> str:
    if socket.gethostname() == "POW18-15":
        return r"C:\Python\Reiting_users\plan_it_form_b24(gen by reiting).pickle"
    return r"C:\srv_mes\srv_mes\plan_it_form_b24(gen by reiting).pickle"


PATHF_IT_PLAN = resolve_pathf_it_plan()


async def main(page: ft.Page):
    auth_user = current_auth_user.get() or {}
    auth_login = auth_user.get("login", "")
    page.session.store.set("auth_login", auth_login)
    DTCLS.Data_page.page = page
    DTCLS.Data_page.reload()
    page.data = cast(DTCLS.Data_page, DTCLS.Data_page)
    Data: DTCLS.Data_page = page.data

    page.title = name_title
    page.fonts = {
        "Roboto Mono": "RobotoMono-VariableFont_wght.ttf",
        "RobotoSlab": "RobotoSlab[wght].ttf",
    }
    async def on_click_logout(e):
        await e.page.launch_url("/auth/logout")

    async def on_range_change(e):
        if isinstance(e, ft.Page):
            page = e
        else:
            page = e.page
        page.views.clear()

        if e.route.startswith("/modules"):
            controls = await modules.load_module(page)
            if DTCLS.Data_page.Data_module.status_bar:
                DTCLS.Data_page.Data_module.status_bar.set_text()

            if controls:
                page.views.append(
                    View(
                        route=e.route,
                        controls=[controls],
                    )
                )
        else:
            _ref_settings = ft.Ref[ft.Column]()
            DTCLS.Data_page.Data_module.settingsRef = _ref_settings
            app_bar_actions = [
                ft.Container(
                    padding=10,
                    content=ft.Text(f"ver {ver}"),
                )
            ]
            if auth_login:
                app_bar_actions.extend([
                    ft.Container(
                        padding=10,
                        content=ft.Text(auth_login),
                    ),
                    ft.Container(
                        padding=10,
                        content=ft.TextButton("Выход", on_click=on_click_logout),
                    ),
                ])
            app_bar = ft.AppBar(
                leading_width=40,
                title=ft.Text(name),
                center_title=True,
                bgcolor=ft.Colors.INVERSE_PRIMARY,
                actions=app_bar_actions,
            )
            page.views.append(
                View(
                    route="/",
                    appbar=app_bar,
                    controls=[
                        modules.main_page(page, PATHF_IT_PLAN),
                        ft.Divider(height=1),
                        SETGS.LeftNavigationMenu(visible=False, ref=_ref_settings),
                    ],
                )
            )

        page.update()

    Data.Data_user.apply_theme_mode(page)
    Data.Data_user.apply_theme(page)

    page.on_error = lambda e: logging.info("Page error: %s", e.data)
    page.expand = True
    page.on_route_change = on_range_change

    await on_range_change(page)
    # await page.push_route(page.route or "/")



def sanitize_next_path(next_value: str | None) -> str:
    default = "/"
    if not next_value:
        return default
    value = next_value.strip()
    if not value.startswith("/"):
        return default
    if value.startswith("//"):
        return default
    if value.startswith("/auth"):
        return default
    return value



def render_login_page(next_url: str, error: str = "", preset_login: str = "sv.mes") -> str:
    error_block = f"<div class='error'>{error}</div>" if error else ""
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name_title} — вход</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f3f5f7;
      font-family: Arial, sans-serif;
    }}
    .card {{
      width: min(420px, calc(100vw - 32px));
      background: white;
      border-radius: 14px;
      padding: 24px;
      box-shadow: 0 10px 28px rgba(0, 0, 0, .08);
    }}
    h1 {{ margin: 0 0 10px; font-size: 24px; }}
    p {{ margin: 0 0 18px; color: #667085; }}
    label {{ display: block; margin: 12px 0 6px; font-weight: 600; }}
    input {{
      width: 100%;
      box-sizing: border-box;
      padding: 11px 12px;
      border: 1px solid #d0d5dd;
      border-radius: 10px;
      font-size: 15px;
    }}
    button {{
      width: 100%;
      margin-top: 18px;
      padding: 12px;
      border: 0;
      border-radius: 10px;
      background: #1f6feb;
      color: white;
      font-size: 15px;
      cursor: pointer;
    }}
    .error {{
      background: #fef3f2;
      border: 1px solid #fecdca;
      color: #b42318;
      border-radius: 10px;
      padding: 10px 12px;
      margin-bottom: 14px;
    }}
    .hint {{ font-size: 13px; color: #667085; margin-top: 10px; }}
  </style>
</head>
<body>
  <form class="card" method="post" action="{LOGIN_PATH}">
    <h1>Вход</h1>
    <p>Вводите логин <b>например i.ivanov</b>.</p>
    {error_block}
    <input type="hidden" name="next" value="{next_url}">
    <label for="login">Логин</label>
    <input id="login" name="login" value="{preset_login}" autocomplete="username" placeholder="Введите логин">
    <label for="password">Пароль</label>
    <input id="password" value="Adr1959967" name="password" type="password" autocomplete="current-password" placeholder="••••••••">
    <button type="submit">Войти</button>
    <div class="hint">Используйте логин вашей учетной записи windows</div>
  </form>
</body>
</html>"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await flet_fastapi.app_manager.start()
    yield
    await flet_fastapi.app_manager.shutdown()


root_app = FastAPI(lifespan=lifespan)


@root_app.get(LOGIN_PATH, response_class=Response)
async def login_page(request: Request) -> Response:
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    user = SESSIONS.get(sid)
    if user:
        next_url = sanitize_next_path(request.query_params.get("next"))
        return RedirectResponse(next_url, status_code=302)

    next_url = sanitize_next_path(request.query_params.get("next"))
    return HTMLResponse(render_login_page(next_url=next_url))


@root_app.post(LOGIN_PATH)
async def login_submit(
    login: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
) -> Response:
    next_url = sanitize_next_path(next)

    try:
        user, error_code = authenticate_windows_user(login, password)
    except ValueError as exc:
        return HTMLResponse(render_login_page(next_url=next_url, error=str(exc), preset_login=login), status_code=400)

    if user is None:
        return HTMLResponse(
            render_login_page(
                next_url=next_url,
                error=f"Неверный логин или пароль",
                preset_login=login,
            ),
            status_code=401,
        )

    sid = SESSIONS.create(user)
    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sid,
        max_age=MONTH_SECONDS,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@root_app.get(LOGOUT_PATH)
async def logout(request: Request) -> RedirectResponse:
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    SESSIONS.delete(sid)
    response = RedirectResponse(LOGIN_PATH, status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@root_app.get(f"/auth/me")
async def auth_me(request: Request):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    user = SESSIONS.get(sid, touch=False)
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}


root_app.mount("/", flet_fastapi.app(main, lambda _: _, assets_dir=r'C:\Users\A.A.Fedorov\MES\ideal_context\Transport\assets'))

app = SessionAuthMiddleware(root_app, login_path=LOGIN_PATH, public_prefixes=("/auth", "/assets"))


if __name__ == "__main__":
    print(f"http://{FLET_HOST}:{FLET_PORT}")
    print(f"http://mesinfo.powerz.ru:{FLET_PORT}")

    import uvicorn

    uvicorn.run(
        app,
        host=FLET_HOST,
        port=FLET_PORT,
        ws="wsproto",
        log_level="info",
    )
