import flet as ft


def build_save_reports_menu(
    *,
    ref: ft.Ref | None = None,
    width: int = 200,
    height: int = 50,
    radius: int = 1,
    # callbacks:
    on_word=None,
    on_excel=None,
    on_tech_build=None,
    on_tech_settings=None,
):
    """Нативное меню сохранения:"""

    def _safe_call(cb, e):
        if cb:
            cb(e)

    tech_submenu = ft.SubmenuButton(
        leading=ft.Icon(ft.Icons.FACT_CHECK),
        content=ft.Text("Технологический отчёт"),
        controls=[
            ft.MenuItemButton(
                leading=ft.Icon(ft.Icons.PLAY_ARROW),
                content=ft.Text("Сформировать"),
                on_click=lambda e: _safe_call(on_tech_build, e),
            ),
            ft.MenuItemButton(
                leading=ft.Icon(ft.Icons.SETTINGS),
                content=ft.Text("Настройки…"),
                on_click=lambda e: _safe_call(on_tech_settings, e),
            ),
        ],
    )

    save_menu = ft.SubmenuButton(
        ref=ref,
        # width=width,
        height=height,
        leading=ft.Icon(ft.Icons.SAVE_AS),
        content=ft.Text("Сохранить"),
        trailing=ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=radius)),
        menu_style=ft.MenuStyle(alignment=ft.Alignment.TOP_LEFT),
        alignment_offset=ft.Offset(width, 0),
        controls=[
            ft.MenuItemButton(
                leading=ft.Icon(ft.Icons.DESCRIPTION),
                content=ft.Text("Word (шаблон)"),
                on_click=lambda e: _safe_call(on_word, e),
            ),
            ft.MenuItemButton(
                leading=ft.Icon(ft.Icons.GRID_ON),
                content=ft.Text("Excel"),
                on_click=lambda e: _safe_call(on_excel, e),
            ),
            ft.MenuItemButton(),
            tech_submenu,
        ],
    )

    return save_menu
