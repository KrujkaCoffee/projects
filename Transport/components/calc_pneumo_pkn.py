from __future__ import annotations

import asyncio
import os
from typing import Any

import flet as ft

import components.calc_pneumo_pkn_back as calc_pneumo_pkn_back
import components.common_funcs as CMF
import data_class as DTCLS


DICT_BARS = {
    "leading": {
        "text": "Домой",
        "icon": ft.Icons.HOME,
        "selected_icon": ft.Icons.HOME_SHARP,
    },
    "destinations": {
        "Новый": {
            "icon": ft.Icons.CREATE,
            "selected_icon": ft.Icons.CREATE_SHARP,
        },
        "История":
            {'icon': ft.Icons.ARCHIVE,
             'selected_icon': ft.Icons.ARCHIVE_SHARP,
             'disabled': True,
             'data': {
                 '_ref': ft.Ref[ft.Text]()
             }
             },
    },
}

_general_module_row_ref = ft.Ref[ft.Row]()
_desktop_column_ref = ft.Ref[ft.Column]()
_input_column_tabels_ref = ft.Ref[ft.Column]()
_output_column_tabels_ref = ft.Ref[ft.Column]()
_input_tabe_ref = ft.Ref[ft.DataTable]()
_output_tabe_ref = ft.Ref[ft.DataTable]()

_header_input_panel_textfield_ref = ft.Ref[ft.TextField]()
_header_input_panel_btn_save_ref = ft.Ref[ft.Button]()

_btn_calc_ref = ft.Ref[ft.Button]()
_btn_reset_ref = ft.Ref[ft.Button]()
_btn_grab_ref = ft.Ref[ft.Button]()

_hint_details_ref = ft.Ref[ft.Container]()
_hint_toggle_icon_ref = ft.Ref[ft.Icon]()
_hint_toggle_caption_ref = ft.Ref[ft.Text]()

_header_filtr_text_field_ref = ft.Ref[ft.TextField]()
_btn_search_ref = ft.Ref[ft.Button]()

_HINT_IMAGE_SRC = "pneumo_pkn_hint.png"


async def apply_page_settings(page: ft.Page, MODULE: DTCLS.ModuleCfg):
    Data: DTCLS.Data_page = page.data
    Data.Data_module = MODULE
    Data.Data_module.cust_data = calc_pneumo_pkn_back.Cust_module_params()


def _set_status(message: str | None = None) -> None:
    status_bar = DTCLS.Data_page.Data_module.status_bar
    if status_bar:
        status_bar.set_text(message)


def _status_message_from_errors(errors: list[dict], *, success: bool) -> str | None:
    if errors:
        headers = ", ".join(err.get("header", "") for err in errors[:4] if err.get("header"))
        suffix = "" if len(errors) <= 4 else f" и ещё {len(errors) - 4}"
        if headers:
            return f"Ошибки расчёта: {headers}{suffix}"
        return f"Ошибки расчёта: {len(errors)}"
    if success:
        return "Расчёт обновлён"
    return None


def paint_rail(select_destination):
    def go_home(e: ft.ControlEvent):
        e.page.go("/")

    destinations = []
    for name, meta in DICT_BARS["destinations"].items():
        destinations.append(
            ft.NavigationRailDestination(
                icon=ft.Icon(meta["icon"]),
                selected_icon=ft.Icon(meta["selected_icon"]),
                label=name,
            )
        )

    leading_data = DICT_BARS["leading"]
    return ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=220,
        leading=ft.FloatingActionButton(
            icon=leading_data["icon"],
            content=leading_data["text"],
            on_click=lambda e: go_home(e),
        ),
        group_alignment=-0.9,
        destinations=destinations,
        on_change=select_destination,
    )


async def gen_page(page: ft.Page):
    Data: DTCLS.Data_page = page.data
    hint_state = {"open": False}

    async def load_history_dest(e: ft.ControlEvent):
        def selectedRowsfnc(e: ft.ControlEvent, row_index: int, row_data: CMF.Row_data):
            s_num = int(row_data.dict_cells()['s_num'].val)
            name = row_data.dict_cells()['name'].val
            input_tbl, output_tbl = calc_pneumo_pkn_back.load_from_db_history_calc(e.page.data, s_num)
            if not input_tbl or not output_tbl:
                CMF.message_dialog(
                    e.page,
                    body_icon=ft.Icons.ERROR,
                    title="Ошибка",
                    message="Не удалось загрузить историю"
                )
                return

            input_tbl_view = CMF.generate_param_table(input_tbl, ref=_input_tabe_ref, fnc_onchange=fnc_onchange_tbl_input)
            output_tbl_view = CMF.generate_param_table(output_tbl, ref=_output_tabe_ref)

            Data.Data_module.cust_data.input_tbl_editbl = input_tbl
            Data.Data_module.cust_data.output_tbl = output_tbl
            show_calc_screen(input_tbl_view, output_tbl_view)

            # apply_input_styles(input_tbl)
            _header_input_panel_textfield_ref.current.value = name
            _header_input_panel_textfield_ref.current.visible = True
            _header_input_panel_textfield_ref.current.disabled = True
            if _header_input_panel_btn_save_ref.current is not None:
                _header_input_panel_btn_save_ref.current.disabled = True
            _btn_calc_ref.current.disabled = True
            _set_status("Открыт расчёт из истории")
            # page.update()

        tbl_data = calc_pneumo_pkn_back.make_history_tbl_data(e.page.data)
        tbl_history = CMF.generate_param_table(tbl_data, selectedRowsfnc=selectedRowsfnc, selectedRows=True)

        _desktop_column_ref.current.controls.clear()

        async def find_rez_table(e: ft.ControlEvent):
            Data.Data_module.cust_data.filtr_seach_history = _header_filtr_text_field_ref.current.value
            await load_history_dest(e)

        header_input_panel = ft.Row(controls=[
            ft.Button(
                'Найти',
                ft.Icons.CALCULATE,
                on_click=find_rez_table,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=1),
                ), height=50, width=150, ref=_btn_search_ref
            ),
            ft.TextField(label="Название расчета", hint_text="Введите текст",
                         width=500,
                         icon=ft.Icons.NOTE_ALT,
                         ref=_header_filtr_text_field_ref),

        ], spacing=120
        )

        _desktop_column_ref.current.controls = [header_input_panel, ft.Divider(),
                                                tbl_history
                                                ]
        _desktop_column_ref.current.alignment = ft.MainAxisAlignment.START
        _desktop_column_ref.current.horizontal_alignment = ft.CrossAxisAlignment.START
        _desktop_column_ref.current.expand = True
        page.update()

    def fnc_onchange_tbl_input(e, *args):
        _ = args
        meta = getattr(e.control, "data", {}) or {}
        cell = meta.get("cell")
        if cell is not None:
            try:
                cell.val = cell.description.cast_type(e.data)
            except Exception:
                pass
        _set_status()

    def fnc_cell_click(e):
        meta = getattr(e.control, "data", {}) or {}
        cell = meta.get("cell")
        if cell is None:
            return
        row_data = cell.parent_row
        table_data = row_data.parent_table_data
        if row_data.table_header:
            table_data.toggle_group(None)
        else:
            table_data.toggle_group(cell.val)

    def apply_input_styles(table_data):
        for row in table_data.rows:
            if row.merge or row.table_header:
                continue
            unique_cell = row.get_cell_unique()
            if unique_cell is None:
                continue
            name = unique_cell.val
            meta = calc_pneumo_pkn_back.INPUT_PARAMS_BY_NAME.get(name, {})
            is_editable = bool(meta.get("editable", True))
            if is_editable:
                row.style_cell(
                    "val",
                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                    text_color=ft.Colors.ON_SURFACE,
                    disabled=False,
                    row_height=50,
                )
            else:
                row.style_cell(
                    "val",
                    bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                    text_color=ft.Colors.SECONDARY,
                    disabled=True,
                    row_height=50,
                )

    async def apply_input_styles_later(table_data):
        await asyncio.sleep(0)
        try:
            apply_input_styles(table_data)
            page.update()
        except Exception:
            pass

    def build_controls(default_vals_input: dict | None = None):
        input_table_control, table_data = calc_pneumo_pkn_back.generate_input_data(
            fnc_onchange_tbl_input,
            _input_tabe_ref,
            default_vals_input,
        )
        Data.Data_module.cust_data.input_tbl_editbl = table_data
        return input_table_control, table_data

    def save_word(e: ft.ControlEvent):
        Data: DTCLS.Data_page = e.page.data
        cfg_module: DTCLS.ModuleCfg = Data.Data_module
        name = (_header_input_panel_textfield_ref.current.value or "").strip()
        if not name:
            name = calc_pneumo_pkn_back.get_name_new_calc()
            _header_input_panel_textfield_ref.current.value = name
        rezult_data_for_save = calc_pneumo_pkn_back.generate_rezult_data_for_save(name, _input_tabe_ref.current,
                                                                         _output_tabe_ref.current)
        rez = calc_pneumo_pkn_back.save_word(rezult_data_for_save['input'], rezult_data_for_save['output'],
                                    rezult_data_for_save['name'], cfg_module.sub_dir, cfg_module.name)
        if not rez:
            CMF.message_dialog(
                e.page,
                body_icon=ft.Icons.ERROR,
                title="Ошибка",
                message="Не удалось сохранить документ word"
            )
            return
        else:
            if not calc_pneumo_pkn_back.save_in_db(e, name):
                CMF.message_dialog(
                    e.page,
                    title="Ошибка",
                    body_icon=ft.Icons.ERROR,
                    message="Не удалось сохранить расчет в истории",
                )
                return
            CMF.dialog_save_file(e, rez)
            return

    def sync_hint_section() -> None:
        is_open = bool(hint_state["open"])

        if _hint_details_ref.current is not None:
            _hint_details_ref.current.visible = is_open and hint_image_exists()
            try:
                _hint_details_ref.current.update()
            except Exception:
                pass

        if _hint_toggle_icon_ref.current is not None:
            _hint_toggle_icon_ref.current.name = (
                ft.Icons.EXPAND_LESS if is_open else ft.Icons.EXPAND_MORE
            )
            try:
                _hint_toggle_icon_ref.current.update()
            except Exception:
                pass

        if _hint_toggle_caption_ref.current is not None:
            _hint_toggle_caption_ref.current.value = "Скрыть" if is_open else "Показать"
            try:
                _hint_toggle_caption_ref.current.update()
            except Exception:
                pass
    def hint_image_exists() -> bool:
        return os.path.exists(os.path.join("assets", _HINT_IMAGE_SRC)) or os.path.exists(_HINT_IMAGE_SRC)

    def get_hint_preview_height() -> int:
        height = getattr(Data.Data_vars, "height", 800) or 800
        return int(min(max(height * 0.45, 260), 560))

    def toggle_hint(e: ft.ControlEvent | None = None):
        _ = e
        if not hint_image_exists():
            _set_status("Файл подсказки не найден")
            page.update()
            return

        hint_state["open"] = not hint_state["open"]
        sync_hint_section()

    def build_hint_section() -> ft.Control:

        details = ft.Container(
            ref=_hint_details_ref,
            visible=hint_state["open"] and hint_image_exists(),
            padding=ft.padding.only(top=6),
            content=ft.Column(
                controls=[
                    ft.Container(
                        height=get_hint_preview_height(),
                        padding=8,
                        border_radius=8,
                        bgcolor=ft.Colors.SURFACE,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Image(
                            src=_HINT_IMAGE_SRC,
                            fit=ft.BoxFit.CONTAIN,
                            expand=True,
                        ),
                    ),
                ],
                spacing=8,
            ),
        )

        return ft.Container(
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            content=ft.Column(
                controls=[
                    ft.Container(
                        on_click=toggle_hint,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.HELP_OUTLINE, color=ft.Colors.PRIMARY),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            "График выбора весовой концентрации",
                                            weight=ft.FontWeight.BOLD,
                                            expand=True,
                                        ),

                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Text(
                                    "Показать",
                                    ref=_hint_toggle_caption_ref,
                                    size=12,
                                    color=ft.Colors.SECONDARY,
                                ),
                                ft.Icon(
                                    ft.Icons.EXPAND_MORE,
                                    ref=_hint_toggle_icon_ref,
                                    color=ft.Colors.SECONDARY,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        expand=True,
                    ),
                    details,
                ],
                spacing=6,
                expand=True,
            ),
            expand=True,
        )

    def show_calc_screen(input_control, output_control=None):
        if _input_column_tabels_ref.current is not None:
            _input_column_tabels_ref.current.controls.clear()
            _input_column_tabels_ref.current.controls.extend([build_hint_section(), input_control])

        if _output_column_tabels_ref.current is not None:
            _output_column_tabels_ref.current.controls.clear()
            if output_control is not None:
                _output_column_tabels_ref.current.controls.append(output_control)

        if _desktop_column_ref.current is not None:
            _desktop_column_ref.current.controls = [
                ft.Container(content=header_row, padding=ft.padding.only(top=10, right=10)),
                ft.Divider(height=1),
                ft.Row(
                    controls=[
                        left_column,
                        ft.VerticalDivider(width=2),
                        right_column,
                    ],
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ]
            _desktop_column_ref.current.expand = True
            _desktop_column_ref.current.alignment = ft.MainAxisAlignment.START
            _desktop_column_ref.current.horizontal_alignment = ft.CrossAxisAlignment.START

    async def reset_module(e: ft.ControlEvent | None = None):
        hint_state["open"] = False
        input_control, table_data = build_controls()
        Data.Data_module.cust_data.output_tbl = None
        show_calc_screen(input_control)
        await apply_input_styles_later(table_data)
        if _header_input_panel_textfield_ref.current is not None:
            _header_input_panel_textfield_ref.current.value = calc_pneumo_pkn_back.get_name_new_calc()
            _header_input_panel_textfield_ref.current.visible = False
            _header_input_panel_textfield_ref.current.disabled = False

        if _header_input_panel_btn_save_ref.current is not None:
            _header_input_panel_btn_save_ref.current.visible = False
        if _btn_calc_ref.current is not None:
            _btn_calc_ref.current.disabled = False
        _set_status()
        if e is not None:
            page.update()

    def calculate_module(e: ft.ControlEvent):
        calculated, errors, success = calc_pneumo_pkn_back.prepare_calc_new_data(None, e.page.data)
        if success:
            calculated = calc_pneumo_pkn_back.clean_result(calculated)
        if calculated is None:
            return

        table_data = Data.Data_module.cust_data.input_tbl_editbl
        calc_pneumo_pkn_back.apply_calculated_to_input_table(table_data, calculated)
        apply_input_styles(table_data)

        if calculated:
            output_tbl_data = calc_pneumo_pkn_back.make_res_tbl(calculated, _output_tabe_ref, fnc_cell_click)
        else:
            output_tbl_data = calc_pneumo_pkn_back.make_err_tbl(errors, _output_tabe_ref)

        Data.Data_module.cust_data.output_tbl = output_tbl_data

        if _output_column_tabels_ref.current is not None:
            if _output_column_tabels_ref.current.controls:
                _output_column_tabels_ref.current.controls.clear()

            _output_column_tabels_ref.current.controls.append(output_tbl_data.table_view)
            _output_column_tabels_ref.current.update()
            output_tbl_data.toggle_group(None)
        if _header_input_panel_btn_save_ref.current is not None:
            _header_input_panel_btn_save_ref.current.visible = True
        if _header_input_panel_textfield_ref.current is not None:
            _header_input_panel_textfield_ref.current.visible = True
            _header_input_panel_textfield_ref.current.content = calc_pneumo_pkn_back.get_name_new_calc()
        _set_status(_status_message_from_errors(errors, success=success))
        e.page.update()

    async def select_destination(e: ft.ControlEvent):
        selected_name = list(DICT_BARS["destinations"].keys())[e.control.selected_index]
        if selected_name == "Новый":
            await reset_module(e)
        if selected_name == 'История':
            await load_history_dest(e)
        e.page.update()

    rail = paint_rail(select_destination)

    _ref_status_bar = ft.Ref[ft.Container]()
    _ref_status_text = ft.Ref[ft.Text]()
    DTCLS.Data_page.Data_module.set_status_bar(_ref_status_bar, _ref_status_text)

    initial_input_control, initial_table_data = build_controls()

    await apply_input_styles_later(initial_table_data)

    header_row = ft.Row(
        controls=[
            ft.VerticalDivider(thickness=0, width=200),
            ft.Button(
                content="Расчет",
                icon=ft.Icons.CALCULATE,
                on_click=calculate_module,
                ref=_btn_calc_ref,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=1)),
                height=46,
                width=150,
            ),
            ft.TextField(label="Название расчета", hint_text="Введите текст",
                width=500,
                value=calc_pneumo_pkn_back.get_name_new_calc(),
                icon=ft.Icons.NOTE_ALT,
                visible=False,
                ref=_header_input_panel_textfield_ref),
            ft.Button(
              'Сохранить',
              ft.Icons.SAVE_AS,
              on_click=save_word,
                visible=False,
              style=ft.ButtonStyle(
                  shape=ft.RoundedRectangleBorder(radius=1),
              ), height=50, width=150, ref=_header_input_panel_btn_save_ref
            )

        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=120,
        wrap=True,
    )

    left_column = ft.Column(
        controls=[
            build_hint_section(),
            initial_input_control,
        ],
        ref=_input_column_tabels_ref,
        expand=False,
        scroll=ft.ScrollMode.ALWAYS,
    )

    right_column = ft.Column(
        controls=[],
        ref=_output_column_tabels_ref,
        expand=False,
        scroll=ft.ScrollMode.ALWAYS,
    )

    status_bar = ft.Column(
        [
            ft.Divider(height=1),
            ft.Container(ft.Text("", ref=_ref_status_text)),
        ]
    )
    status_container = ft.Container(content=status_bar, ref=_ref_status_bar, height=90)

    dynamic_column = ft.Column(
        controls=[
            ft.Container(content=header_row, padding=ft.padding.only(top=10, right=10)),
            ft.Divider(height=1),
            ft.Row(
                controls=[
                    left_column,
                    ft.VerticalDivider(width=2),
                    right_column,
                ],
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        expand=True,
        ref=_desktop_column_ref,
    )

    return ft.Row(
        controls=[
            rail,
            ft.VerticalDivider(width=1),
            ft.Column(
                controls=[
                    dynamic_column,
                    status_container,
                ],
                expand=True,
            ),
        ],
        expand=True,
        ref=_general_module_row_ref,
    )

