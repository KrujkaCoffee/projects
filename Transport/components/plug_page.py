import flet as ft

import components.common_funcs as CMF
import data_class as DTCLS

DICT_BARS = {"leading": {'text': 'Домой',
                         'icon': ft.Icons.HOME,
                         'selected_icon': ft.Icons.HOME_SHARP,
                         'data': {
                             '_ref': ft.Ref[ft.Text]()
                                }

                         },

             "destinations": {
                 "":
                     {'icon': ft.Icons.POWER_OFF,
                      'selected_icon': ft.Icons.POWER_OFF_SHARP,
                      'disabled' : True,
                      'data': {
                          '_ref': ft.Ref[ft.Text]()
                      }
                      },
             }
             }

_general_module_row_ref = ft.Ref[ft.Row]()
_desktop_column_ref = ft.Ref[ft.Column]()

def paint_rail(select_destination):
    def leading_click(e: ft.ControlEvent):
        e.page.go('/')

    list_bars = []
    for name, module in DICT_BARS['destinations'].items():
        list_bars.append(ft.NavigationRailDestination(icon=ft.Icon(module['icon']),
                                                      selected_icon=ft.Icon(module['selected_icon']),
                                                      label=name,
                                                      disabled=module['disabled']
                                                      ))

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=400,
        leading=ft.FloatingActionButton(icon=DICT_BARS['leading']['icon'],

                                        content=DICT_BARS['leading']['text'], on_click=lambda _: leading_click(_)
                                        ),
        group_alignment=-0.9,
        destinations=list_bars,
        on_change=lambda e: select_destination(e),  # e.control.selected_index
    )
    return rail


def gen_page(page):
    Data: DTCLS.Data_page = page.data

    def generate_desktop_row(page: ft.Page, rail: ft.NavigationRail):
        Data: DTCLS.Data_page = page.data

        return

    def select_destination(e: ft.ControlEvent):
        ind = e.control.selected_index
        if list(DICT_BARS.keys())[ind] == '':
            page.update()





    rail = paint_rail(select_destination)

    _general_module_row_ref.current = None
    _desktop_column_ref.current = None
    return ft.Row([
        rail,
        ft.VerticalDivider(width=1),
        ft.Column(
            controls=[ft.Icon(ft.Icons.CONSTRUCTION,size=150),
                ft.Text(f'Модуль в разработке',size=50)
            ],
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment= ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ALWAYS, expand=True, ref=_desktop_column_ref
        )

    ], expand=True
        , width=(Data.Data_vars.width),
        height=Data.Data_vars.height,
        ref=_general_module_row_ref
    )