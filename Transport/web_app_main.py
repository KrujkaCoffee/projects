import mimetypes
import logging

import Config.srv_config as SRVCFG
import flet as ft
from flet import View
import socket
import data_class as DTCLS
import components.modules as modules
import components.settings as SETGS
from middleware import IISWindowsUserMiddleware

from typing import cast

ver = 0.02

FLET_PATH = ''
FLET_PORT = SRVCFG.PORT
FLET_HOST = SRVCFG.HOST

IN_BROUSER = SRVCFG.IN_BROUSER

name_title = "MES app"
name = "Веб приложение МЕС"

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("application/wasm", ".wasm")

logging.basicConfig(level=logging.INFO)

async def main(page: ft.Page):
    DTCLS.Data_page.page = page
    DTCLS.Data_page.reload()
    page.data = cast(DTCLS.Data_page, DTCLS.Data_page)
    Data: DTCLS.Data_page = page.data


    page.title = name_title
    page.fonts = {
        "Roboto Mono": "RobotoMono-VariableFont_wght.ttf",
        "RobotoSlab": "RobotoSlab[wght].ttf",

    }

    # img_path =  os.sep.join(['assets','favicon-16x16.png'])
    # if not F.existence_file_c(img_path):
    #    quit()
    # page.favicon = img_path

    async def on_range_change(e):
        if isinstance(e, ft.Page):
            page = e
        else:
            page = e.page
        page.views.clear()

        if e.route.startswith('/modules'):
            controls = await modules.load_module(page)
            if DTCLS.Data_page.Data_module.status_bar:
                DTCLS.Data_page.Data_module.status_bar.set_text()

            if controls:
                page.views.append(
                    View(
                        route=e.route, controls=[controls]
                    )
                )
        else:
            _ref_settings = ft.Ref[ft.Column]()
            DTCLS.Data_page.Data_module.settingsRef = _ref_settings
            app_bar = ft.AppBar(
                # leading=ft.Container(padding=5,
                #                     content=ft.Image(src= os.sep.join(['assets','logo.png']))),
                leading_width=40,
                title=ft.Text(name),
                center_title=True,
                bgcolor=ft.Colors.INVERSE_PRIMARY,
                actions=[
                    ft.Container(
                        padding=10, content=ft.Text(f"ver {ver}")
                    )
                ],
            )
            page.views.append(
                View(
                    route="/",
                    appbar=app_bar,
                    controls=[modules.main_page(page, PATHF_IT_PLAN), ft.Divider(height=1),
                     SETGS.LeftNavigationMenu(visible=False, ref=_ref_settings)]
                    ,

                )
            )

        page.update()

    Data.Data_user.apply_theme_mode(page)
    Data.Data_user.apply_theme(page)

    page.on_error = lambda e: logging.info("Page error:", e.data)

    page.expand = True

    async def update_size(e):
        local_storage = ft.SharedPreferences()
        width = await local_storage.get("window_width")
        height = await local_storage.get("window_height")
        Data.Data_vars.width = width or 800
        Data.Data_vars.height = height or 600

    page.on_resize = update_size
    page.on_route_change = on_range_change
    await on_range_change(page)
    await page.push_route("/")


if __name__ == "__main__":
    if socket.gethostname() == 'POW18-15':  # a.belyakov
        PATHF_IT_PLAN = fr'C:\Python\Reiting_users\plan_it_form_b24(gen by reiting).pickle'
        if IN_BROUSER:
            print(f'http://{FLET_HOST}:{FLET_PORT}')

            ft.app(name=FLET_PATH, target=main, view=None, port=FLET_PORT, host=FLET_HOST, assets_dir="assets")
        else:
            ft.app(name=FLET_PATH, target=main)
    elif socket.gethostname() == 'POW18-08':
        PATHF_IT_PLAN = fr'C:\srv_mes\srv_mes\plan_it_form_b24(gen by reiting).pickle'
        print(f'http://{FLET_HOST}:{FLET_PORT}')
        print(f'http://mesinfo.powerz.ru:{FLET_PORT}') # SRVmes 'http://mesinfo.powerz.ru:20000/'
        learn_app = ft.run(name=FLET_PATH, main=main, view=ft.AppView.WEB_BROWSER, port=FLET_PORT,
               host='localhost')
        app = IISWindowsUserMiddleware(learn_app)

    else:
        PATHF_IT_PLAN = fr'C:\srv_mes\srv_mes\plan_it_form_b24(gen by reiting).pickle'
        print(f'http://{FLET_HOST}:{FLET_PORT}')
        print(f'http://mesinfo.powerz.ru:{FLET_PORT}') # SRVmes 'http://mesinfo.powerz.ru:20000/'
        learn_app = ft.run(name=FLET_PATH, main=main, view=ft.AppView.WEB_BROWSER, port=FLET_PORT,
               host='0.0.0.0', export_asgi_app=True)
        app = IISWindowsUserMiddleware(learn_app)
