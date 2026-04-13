from __future__ import annotations

import logging
import mimetypes
import os
import socket
from contextlib import asynccontextmanager
from typing import cast

from starlette.responses import Response

import Config.srv_config as SRVCFG
import components.modules as modules
import components.settings as SETGS
import data_class as DTCLS
import flet as ft
import flet.fastapi as flet_fastapi
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from flet import View

from Config import srv_config
from auth_backend import MONTH_SECONDS, SESSION_COOKIE_NAME, SESSIONS, authenticate_windows_user
from middleware import SessionAuthMiddleware, current_auth_user

ver = 0.03

FLET_PATH = ""
FLET_PORT = SRVCFG.PORT
FLET_HOST = SRVCFG.HOST
IN_BROUSER = SRVCFG.IN_BROUSER

name_title = "MES app"
name = "Веб приложение МЕС"

AUTH_PREFIX = "/auth"
LOGIN_PATH = f"{AUTH_PREFIX}/login"
LOGOUT_PATH = f"{AUTH_PREFIX}/logout"

TEMPLATES = Jinja2Templates(directory=srv_config.TEMPLATES_DIR)

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("application/wasm", ".wasm")

logging.basicConfig(level=logging.INFO)
os.environ.setdefault("FLET_ASSETS_DIR", srv_config.ASSERT_PATH)


def resolve_pathf_it_plan() -> str:
    if socket.gethostname() == "POW18-15":
        return r"C:\Python\Reiting_users\plan_it_form_b24(gen by reiting).pickle"
    return r"C:\srv_mes\srv_mes\plan_it_form_b24(gen by reiting).pickle"


PATHF_IT_PLAN = resolve_pathf_it_plan()


async def main(page: ft.Page):
    print(f'RELOAD =================== {page}')

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

    async def on_click_logout(e: ft.ControlEvent):
        await e.page.launch_url(LOGOUT_PATH)

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
                app_bar_actions.extend(
                    [
                        ft.Container(
                            padding=10,
                            content=ft.Text(auth_login),
                        ),
                        ft.Container(
                            padding=10,
                            content=ft.TextButton("Выход", on_click=on_click_logout),
                        ),
                    ]
                )
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
    if value.startswith(AUTH_PREFIX):
        return default
    return value


def render_login_page(
    request: Request,
    next_url: str,
    error: str = "",
    preset_login: str = "",
):
    return TEMPLATES.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "page_title": name_title,
            "form_action": LOGIN_PATH,
            "next_url": next_url,
            "error": error,
            "preset_login": preset_login,
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await flet_fastapi.app_manager.start()
    yield
    await flet_fastapi.app_manager.shutdown()


root_app = FastAPI(lifespan=lifespan)


@root_app.get(LOGIN_PATH)
async def login_page(request: Request):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    user = SESSIONS.get(sid)
    if user:
        next_url = sanitize_next_path(request.query_params.get("next"))
        return RedirectResponse(next_url, status_code=302)

    next_url = sanitize_next_path(request.query_params.get("next"))
    return render_login_page(request, next_url=next_url)


@root_app.post(LOGIN_PATH)
async def login_submit(
    request: Request,
    login: str = Form(default=""),
    password: str = Form(default=""),
    next: str = Form("/"),
) -> Response:
    next_url = sanitize_next_path(next)

    try:
        user, error_code = authenticate_windows_user(login, password)
    except ValueError as exc:
        return render_login_page(request, next_url=next_url, error=str(exc), preset_login=login)

    if user is None:
        _ = error_code
        return render_login_page(
            request,
            next_url=next_url,
            error="Неверный логин или пароль",
            preset_login=login,
        )

    sid = SESSIONS.create(user)
    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sid,
        max_age=MONTH_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return response


@root_app.get(LOGOUT_PATH)
async def logout(request: Request):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    SESSIONS.delete(sid)
    response = RedirectResponse(LOGIN_PATH, status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@root_app.get(f"{AUTH_PREFIX}/me")
async def auth_me(request: Request):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    user = SESSIONS.get(sid, touch=False)
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}


root_app.mount("/", flet_fastapi.app(main, lambda _: _, assets_dir=srv_config.ASSERT_PATH))

app = SessionAuthMiddleware(root_app, login_path=LOGIN_PATH, public_prefixes=(
        "/auth",
        "/assets",
        "/manifest.json",
        "/icons",
        "/favicon",
        "/apple-touch-icon"
))


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
