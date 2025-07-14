import flet as ft
import components.settings as SETGS
import project_cust_38.Cust_Functions as F
import components.plug_page as PLUG
import components.calc_pneumo as MCP
import components.calc_silencer as MCS
import components.calc_airslide as MCA
import components.calc_pneumatic_jet as MCPj
import data_class as DTCLS

DICT_MODULES = {'Модули':
                    {'icon': ft.Icons.WIDGETS,
                     'tooltip': 'Выбор инструмента',
                     '_subModules': {

                         "ПО для расчета пневмотранспорта":
                             {
                                 'icon': ft.Icons.AIR,
                                 'tooltip': 'Задача № 100050625',
                                 'data': DTCLS.Module_cfg("pneumatic_transport", "/modules/pneumatic_transport_dev")
                                 # {"alias": "pneumatic_transport", "route": "/modules/pneumatic_transport_dev"},

                             },
                         "ПО для расчета аэрожелоба":
                             {
                                 'icon': ft.Icons.AIRLINE_STOPS,
                                 'tooltip': '',
                                 'data': DTCLS.Module_cfg("airslide", "/modules/airslide")
                                 # {"alias": "pneumatic_transport", "route": "/modules/pneumatic_transport_dev"},

                             },
                         "ПО для расчета пневмотранспорта на базе струйного насоса":
                             {
                                 'icon': ft.Icons.TORNADO,
                                 'tooltip': '',
                                 'data': DTCLS.Module_cfg("pneumatic_jet", "/modules/pneumatic_jet")
                                 # {"alias": "pneumatic_transport", "route": "/modules/pneumatic_transport_dev"},

                             },
                        #F.existence_file_c("./assets/air_purifier_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")
                         "ПО для расчета шумоглушителей":
                             {
                                 'icon': ft.Icons.VIBRATION,
                                 'tooltip': '',
                                 'data': DTCLS.Module_cfg("silencer", "/modules/silencer")
                                 # {"alias": "pneumatic_transport", "route": "/modules/pneumatic_transport_dev"},

                             },
                         "Выполнение нарядов (планшетный вариант)":
                             {
                                 'icon': ft.Icons.WORK_OUTLINE,
                                 'tooltip': 'Модуль "Выполнение" для планшета',
                                 'data': DTCLS.Module_cfg("vipoln", "/modules/vipoln")
                                 # {"alias": "pneumatic_transport", "route": "/modules/pneumatic_transport_dev"},

                             },
                         "Отчеты":
                             {
                                 'icon': ft.Icons.INSERT_CHART,
                                 'tooltip': 'Производственные отчеты',
                                 'data': DTCLS.Module_cfg("reports", "/modules/reports")
                                 # {"alias": "pneumatic_transport", "route": "/modules/pneumatic_transport_dev"},

                             },
                        "Руководства":
                             {
                                 'icon': ft.Icons.MENU_BOOK,
                                 'tooltip': 'Инструкции по работе с МЕС',
                                 'data': DTCLS.Module_cfg("guides", "/modules/guides")
                                 # {"alias": "pneumatic_transport", "route": "/modules/pneumatic_transport_dev"},

                             },

                     },

                     },

                "Настройки":
                    {'icon': ft.Icons.SETTINGS,
                     'tooltip': 'Настройки',
                     '_subModules': {"Оформление": {
                            'icon': ft.Icons.STYLE              ,
                         'tooltip': 'Оформление',

                     }

                     }

                     },

                }

_ref_main = ft.Ref[ft.Row]()
_ref_settings = ft.Ref[ft.Column]()

DICT_MODULES_ROUTES = dict()


def add_ROUTES(struct: dict):
    if not isinstance(struct, dict):
        return [struct]
    for name, data_iter in struct.items():

        data = data_iter['data'] if 'data' in data_iter else None
        if data:
            DICT_MODULES_ROUTES[data.route] = data

        if '_subModules' in data_iter:
            add_ROUTES(data_iter['_subModules'])


add_ROUTES(DICT_MODULES)


def main_page(page, PATHF_IT_PLAN):
    data_it_plan = F.load_file_pickle(PATHF_IT_PLAN)
    list_plan = [_ for _ in data_it_plan if _['Тип'] == 'Развитие процессов' and _['ПП'] == 'MES']
    list_completed = [_ for _ in list_plan if F.valm(_['ПРОЦЕНТ ВЫПОЛНЕНИЯ']) >= 1]
    list_intend = [_ for _ in list_plan if F.valm(_['ПРОЦЕНТ ВЫПОЛНЕНИЯ']) < 1]

    lv_completed = ft.ListView(spacing=10, padding=20, auto_scroll=True, height=page.data.Data_vars.height - 200)
    for item in list_completed:
        date = F.datetostr(F.strtodate(item['ДАТА ОКОНЧАНИЯ']), '%d.%m.%Y')
        lv_completed.controls.append(ft.Text(f"{date} {item['НАЗВАНИЕ ЗАДАЧИ']}"))

    lv_intend = ft.ListView(spacing=10, padding=20, auto_scroll=True, height=page.data.Data_vars.height - 200)
    for item in list_intend:
        num = item['НОМЕР']
        lv_intend.controls.append(ft.Text(f"№{num} {item['НАЗВАНИЕ ЗАДАЧИ']}"))
    column_completed = ft.Column(controls=[ft.Text(f"Обновления:"), lv_completed],
                                 width=page.data.Data_vars.width / 2 - 20)
    column_intend = ft.Column(controls=[ft.Text(f"Текущие работы:"), lv_intend],
                              width=page.data.Data_vars.width / 2 - 20)
    row_plan = ft.Row([column_completed, ft.VerticalDivider(width=2), column_intend],
                      spacing=20,  # Место для разделителя
                      expand=True,  # Растягиваем Row
                      height=page.data.Data_vars.height - 200  # Фиксированная высота (опционально))
                      )
    return ft.Column([menubar(), row_plan], ref=_ref_main, spacing=20)


def menubar():
    def handle_menu_item_click(e):
        def clc_settings():
            if _ref_settings.current and _ref_settings.current.parent in _ref_main.current.controls:
                _ref_main.current.controls.remove(_ref_settings.current.parent)
            else:
                _ref_main.current.controls.append(SETGS.LeftNavigationMenu(visible=True, ref=_ref_settings))

        select = e.control
        select_name = select.content.value
        pg: ft.Page = e.page
        Data:DTCLS.Data_page = pg.data
        print(f"{F.now()}|{Data.Data_user.user_config.ip}|{Data.Data_user.user_config.bio.fio}|{e.control.content.value}")
        if select_name == 'Оформление':
            clc_settings()
            pg.update()
        module_data: DTCLS.Module_cfg = select.data
        if e.control.parent.content.value == 'Модули':
            pg.data.Data_module = module_data
            pg.go(module_data.route)

    def add_module(struct: dict):
        list_bars = []
        if not isinstance(struct, dict):
            return [struct]
        for name, data_iter in struct.items():
            icon = data_iter['icon'] if 'icon' in data_iter else None
            data = data_iter['data'] if 'data' in data_iter else None
            if data:
                DICT_MODULES_ROUTES[data.route] = data

            if '_subModules' in data_iter:

                item = ft.SubmenuButton(
                    content=ft.Text(name),
                    # on_open=handle_on_open,
                    # on_close=handle_on_close,
                    # on_hover=handle_on_hover,
                    controls=add_module(data_iter['_subModules']),
                    tooltip=data_iter['tooltip'],
                    data=data,
                    leading=ft.Icon(icon),
                )
            else:

                item = ft.MenuItemButton(
                    content=ft.Text(name),
                    leading=ft.Icon(icon),
                    data=data,
                    tooltip=data_iter['tooltip'],
                    on_click=handle_menu_item_click,
                )

            list_bars.append(item)
        return list_bars

    list_bars = add_module(DICT_MODULES)

    menubar = ft.MenuBar(
        expand=True,
        style=ft.MenuStyle(
            alignment=ft.alignment.top_left,
            # bgcolor=ft.Colors.RED_100,
            mouse_cursor={
                ft.ControlState.HOVERED: ft.MouseCursor.WAIT,
                ft.ControlState.DEFAULT: ft.MouseCursor.ZOOM_OUT,
            },
        ),
        controls=list_bars,
    )
    return ft.Row([menubar])





def load_module(page: ft.Page):
    if page.route == ("/modules/pneumatic_transport_dev"):
        MCP.apply_page_settings(page,DICT_MODULES_ROUTES)
        return MCP.gen_page(page)
    if page.route == ("/modules/airslide"):
        MCA.apply_page_settings(page,DICT_MODULES_ROUTES)
        return MCA.gen_page(page)
    if page.route == ("/modules/pneumatic_jet"):
        MCPj.apply_page_settings(page,DICT_MODULES_ROUTES)
        return MCPj.gen_page(page)
    #if page.route == ("/modules/silencer"):
    #    MCS.apply_page_settings(page)
    #    return MCS.gen_page(page)
    return PLUG.gen_page(page)
