# components/ext_report_native_menu.py
import flet as ft


def build_save_reports_menu(
    *,
    ref: ft.Ref | None = None,
    width: int = 150,
    height: int = 50,
    radius: int = 1,
    # callbacks:
    on_word=None,
    on_excel=None,
    on_tech_build=None,
    on_tech_settings=None,
):
    """
    Нативное меню сохранения:
      - Word (шаблон)
      - Excel
      - Технологический отчёт -> (Сформировать, Настройки)
    """

    def _safe_call(cb, e):
        if cb:
            cb(e)

    # Подменю "Технологический отчёт" (как на твоём скрине — стрелка и каскад вправо)
    tech_submenu = ft.SubmenuButton(
        leading=ft.Icon(ft.Icons.FACT_CHECK),
        content=ft.Text("Технологический отчёт"),
        # Для подменю обычно дефолтно уезжает вправо; стиль оставим минимальный
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

    # Главное меню “Сохранить”
    save_menu = ft.SubmenuButton(
        ref=ref,
        width=width,
        height=height,
        leading=ft.Icon(ft.Icons.SAVE_AS),
        content=ft.Text("Сохранить"),
        trailing=ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=radius)),
        # ВАЖНО:
        # alignment + alignment_offset позволяют "подвинуть" выпадающее меню.
        # Если хочешь, чтобы меню появлялось СПРАВА от кнопки — сдвигай по X примерно на ширину кнопки.
        menu_style=ft.MenuStyle(alignment=ft.Alignment.TOP_LEFT),
        alignment_offset=ft.Offset(width, 0),  # <-- стартово “справа”. Если не понравится — (0, 0) = ближе к кнопке.
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
            ft.MenuItemButton(),  # divider
            tech_submenu,
        ],
    )

    return save_menu
