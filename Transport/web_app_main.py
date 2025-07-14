import flet as ft
from flet import View
import socket
import data_class as DTCLS
import components.modules as modules
import Config.srv_config as SRVCFG
from typing import cast

ver = 0.01

FLET_PATH = ''  # or 'ui/path'
FLET_PORT = SRVCFG.PORT
FLET_HOST = SRVCFG.HOST

IN_BROUSER = SRVCFG.IN_BROUSER

name_title = "MES app"
name = "Веб приложение МЕС"


def main(page: ft.Page):
    page.data = cast(DTCLS.Data_page, DTCLS.Data_page(page))
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

    def route_change(e):
        if isinstance(e, ft.Page):
            page = e
        else:
            page = e.page
        #print("Route change:", e.route)
        page.views.clear()

        if e.route.startswith('/modules'):
            controls = modules.load_module(page)
            if controls:
                page.views.append(
                    View(
                        e.route, [
                            controls
                        ]
                    )
                )
        else:

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
                    "/",
                    [app_bar, modules.main_page(page, PATHF_IT_PLAN), ft.Divider(height=1)],
                    spacing=100,

                )
            )

        page.update()

    Data.Data_user.apply_theme_mode(page)
    Data.Data_user.apply_theme(page)

    # page.theme_mode = ft.ThemeMode.LIGHT
    page.on_error = lambda e: print("Page error:", e.data)

    # route_change(page)

    page.spacing = 100
    page.expand = True

    #print(f"Initial route: {page.route}")

    def update_size(e):
        # Для веба: используем контейнер с expand=True
        width = page.client_storage.get("window_width", 800)
        height = page.client_storage.get("window_height", 600)
        Data.Data_vars.width = width
        Data.Data_vars.height = height

    page.on_resize = update_size
    page.on_route_change = route_change

    page.go(page.route)


if __name__ == "__main__":
    PATHF_IT_PLAN = fr'.\plan_it_form_b24(gen by reiting).pickle'

    ft.app(name=FLET_PATH, target=main)
    #
    # if socket.gethostname() == 'POW18-15':  # a.belyakov
    #     PATHF_IT_PLAN = fr'C:\Python\Reiting_users\plan_it_form_b24(gen by reiting).pickle'
    #     if IN_BROUSER:
    #         print(f'http://{FLET_HOST}:{FLET_PORT}')
    #         ft.app(name=FLET_PATH, target=main, view=None, port=FLET_PORT, host=FLET_HOST, assets_dir="assets")
    #     else:
    #         ft.app(name=FLET_PATH, target=main)
    #
    # else:
    #     PATHF_IT_PLAN = fr'C:\srv_mes\srv_mes\plan_it_form_b24(gen by reiting).pickle'
    #     print(f'http://{FLET_HOST}:{FLET_PORT}')
    #     print(f'http://mesinfo.powerz.ru:{FLET_PORT}')
    #     ft.app(name=FLET_PATH, target=main, view=ft.WEB_BROWSER, port=FLET_PORT,
    #            host='0.0.0.0')  # SRVmes 'http://mesinfo.powerz.ru:20000/'
