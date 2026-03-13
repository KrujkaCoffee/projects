import flet as ft
import components.settings as SETGS
import project_cust_38.Cust_Functions as F
import components.plug_page as PLUG
import components.calc_pneumo as MCP
import components.calc_silencer as MCS
import components.calc_blower_zigel as MCBZ
import components.calc_pneumo_pkn as MCPPKN
import components.calc_airslide as MCA
import components.calc_pneumatic_jet as MCPj
import data_class as DTCLS

if __name__ == '__main__':
    quit()


modules = DTCLS.ModuleCfg()

modules.add_submodule(DTCLS.ModuleCfg("modules",
                              "/modules/modules",
                              'Модули',
                                      ft.Icons.WIDGETS,
                              'Выбор инструмента'))

modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("pneumatic_transport",
                              "/modules/pneumatic_transport_dev",
                              "ПО для расчета пневмотранспорта",
                                                             ft.Icons.AIR,
                              'Задача № 100050625'))

modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("pneumatic_transport_pkn",
                              "/modules/pneumatic_transport_pkn",
                              "ПО для расчета пневмотранспорта ПКН",
                                                             ft.Icons.AIR,
                              'Новый отдельный расчет по методике ПКН'))


modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("airslide",
                              "/modules/airslide",
                              "ПО для расчета аэрожелоба",
                                                             ft.Icons.AIRLINE_STOPS,
                              ''))
modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("pneumatic_jet",
                              "/modules/pneumatic_jet",
                              "ПО для расчета пневмотранспорта на базе струйного насоса",
                                                             ft.Icons.TORNADO,
                              ''))
modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("silencer",
                              "/modules/silencer",
                              "ПО для расчета шумоглушителей",
                                                             ft.Icons.VIBRATION,
                              ''))
modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg(
    "blower_zigel",
    "/modules/blower_zigel",
    "ПО для расчёта воздуходувки (метод Зигеля)",
    ft.Icons.AIR,
    ''
))
modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("vipoln",
                              "/modules/vipoln",
                              "Выполнение нарядов (планшетный вариант)",
                                                             ft.Icons.WORK_OUTLINE,
                              'Модуль "Выполнение" для планшета'))
modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("reports",
                              "/modules/reports",
                              "Отчеты",
                                                             ft.Icons.INSERT_CHART,
                              'Производственные отчеты'))
modules.sub_modules["modules"].add_submodule(DTCLS.ModuleCfg("guides",
                              "/modules/guides",
                              "Руководства",
                                                             ft.Icons.MENU_BOOK,
                              'Инструкции по работе с МЕС'))

modules.add_submodule(DTCLS.ModuleCfg("settings",
                              "/modules/settings",
                              'Настройки',
                                      ft.Icons.SETTINGS,
                              'Настройки'))
modules.sub_modules["settings"].add_submodule(DTCLS.ModuleCfg("decoration",
                              "/modules/decoration",
                              "Оформление",
                                                              ft.Icons.STYLE,
                              'Оформление'))

_ref_main = ft.Ref[ft.Row]()



def main_page(page, PATHF_IT_PLAN):
    data_it_plan = F.load_file_pickle(PATHF_IT_PLAN)
    list_plan = [_ for _ in data_it_plan if _['ТИП'] == 'Развитие процессов' and _['ПП'] == 'MES']
    list_completed = [_ for _ in list_plan if F.valm(_['ПРОЦЕНТ ВЫПОЛНЕНИЯ']) >= 1]
    list_intend = [_ for _ in list_plan if F.valm(_['ПРОЦЕНТ ВЫПОЛНЕНИЯ']) < 1]

    lv_completed = ft.ListView(spacing=10, padding=20, auto_scroll=True,expand=True)
    for item in list_completed:
        date = F.datetostr(F.strtodate(item['ДАТА ОКОНЧАНИЯ']), '%d.%m.%Y')
        lv_completed.controls.append(ft.Text(f"{date} {item['НАЗВАНИЕ ЗАДАЧИ']}"))

    lv_intend = ft.ListView(spacing=10, padding=20, auto_scroll=True,expand=True)
    for item in list_intend:
        num = item['НОМЕР']
        lv_intend.controls.append(ft.Text(f"№{num} {item['НАЗВАНИЕ ЗАДАЧИ']}"))
    column_completed = ft.Column(controls=[ft.Text(f"Обновления:"), lv_completed],
                                 expand=1,)
    column_intend = ft.Column(controls=[ft.Text(f"Текущие работы:"), lv_intend],
                              expand=1,)
    row_plan = ft.Row([column_completed, ft.VerticalDivider(width=2), column_intend],
                      spacing=20,  # Место для разделителя
                      expand=True,  # Растягиваем Row
                      )
    return ft.Column([menubar(), row_plan], ref=_ref_main, spacing=20,expand=True)


def menubar():
    def handle_menu_item_click(e):
        def clc_settings():
            if DTCLS.Data_page.Data_module.settingsRef.current and DTCLS.Data_page.Data_module.settingsRef.current.visible:
                DTCLS.Data_page.Data_module.settingsRef.current.visible = False
            else:
                DTCLS.Data_page.Data_module.settingsRef.current.visible = True
            DTCLS.Data_page.page.update()
        select = e.control
        select_name = select.content.value
        pg: ft.Page = e.page
        Data:DTCLS.Data_page = pg.data
        print(f"{F.now()}|{Data.Data_user.user_config.ip}|{Data.Data_user.user_config.bio.fio}|{e.control.content.value}")
        if select_name == 'Оформление':
            clc_settings()
            pg.update()
        try:
            module_data: DTCLS.Module_cfg = select.data
            if not module_data is select.data:
                module_data: DTCLS.ModuleCfg = select.data
        except:
            module_data: DTCLS.ModuleCfg = select.data
        if e.control.parent.content.value == 'Модули':
            pg.data.Data_module = module_data
            pg.go(module_data.route)

    def add_module(modules:dict):
        list_bars = []
        if not isinstance(modules, dict):
            return
        for module in modules.values():
            if not isinstance(module, DTCLS.ModuleCfg):
                return [module]

            if module.sub_modules:
                item = ft.SubmenuButton(
                    content=ft.Text(module.name),
                    # on_open=handle_on_open,
                    # on_close=handle_on_close,
                    # on_hover=handle_on_hover,
                    controls=add_module(module.sub_modules),
                    tooltip=module.tooltip,
                    data=module,
                    leading=ft.Icon(module.icon),
                )
            else:

                item = ft.MenuItemButton(
                    content=ft.Text(module.name),
                    leading=ft.Icon(module.icon),
                    data=module,
                    tooltip=module.tooltip,
                    on_click=handle_menu_item_click,
                )

            list_bars.append(item)
        return list_bars

    list_bars = add_module(modules.sub_modules)

    menubar = ft.MenuBar(
        expand=True,
        style=ft.MenuStyle(
            alignment=ft.Alignment.TOP_LEFT,
            # bgcolor=ft.Colors.RED_100,
            mouse_cursor={
                ft.ControlState.HOVERED: ft.MouseCursor.WAIT,
                ft.ControlState.DEFAULT: ft.MouseCursor.ZOOM_OUT,
            },
        ),
        controls=list_bars,
    )
    return ft.Row([menubar])


async def load_module(page: ft.Page):
    if page.route == ("/modules/pneumatic_transport_dev"):
        MCP.apply_page_settings(page,modules.get_module_by_route(page.route))
        return MCP.gen_page(page)
    if page.route == ("/modules/pneumatic_transport_pkn"):
        await MCPPKN.apply_page_settings(page,modules.get_module_by_route(page.route))
        return await MCPPKN.gen_page(page)
    if page.route == ("/modules/airslide"):
        MCA.apply_page_settings(page,modules.get_module_by_route(page.route))
        return MCA.gen_page(page)
    if page.route == ("/modules/pneumatic_jet"):
        MCPj.apply_page_settings(page,modules.get_module_by_route(page.route))
        return MCPj.gen_page(page)
    if page.route == ("/modules/silencer"):
        await MCS.apply_page_settings(page,modules.get_module_by_route(page.route))
        return MCS.gen_page(page)
    if page.route == ("/modules/blower_zigel"):
        await MCBZ.apply_page_settings(page,modules.get_module_by_route(page.route))
        return MCBZ.gen_page(page)

    return PLUG.gen_page(page)
