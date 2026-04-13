import flet as ft

import components.calc_blower_zigel_back as blower_back
import components.common_funcs as CMF
import data_class as DTCLS
import project_cust_38.Cust_emoji as Cust_emoji


DICT_BARS = {
    "leading": {
        "text": "Домой",
        "icon": ft.Icons.HOME,
        "selected_icon": ft.Icons.HOME_SHARP,
        "data": {"_ref": ft.Ref[ft.Text]()},
    },
    "destinations": {
        "Новый": {
            "icon": ft.Icons.CREATE,
            "selected_icon": ft.Icons.CREATE_SHARP,
            "disabled": True,
            "data": {"_ref": ft.Ref[ft.Text]()},
        },
        "История": {
            "icon": ft.Icons.ARCHIVE,
            "selected_icon": ft.Icons.ARCHIVE_SHARP,
            "disabled": True,
            "data": {"_ref": ft.Ref[ft.Text]()},
        },
    },
}


_btn_calc_ref = ft.Ref[ft.Button]()
_btn_grab_ref = ft.Ref[ft.Button]()
_btn_apply_material_ref = ft.Ref[ft.Button]()

_header_filtr_text_field_ref = ft.Ref[ft.TextField]()
_btn_search_ref = ft.Ref[ft.Button]()

_general_module_row_ref = ft.Ref[ft.Row]()
_desktop_column_ref = ft.Ref[ft.Column]()

_header_input_panel_textfield_ref = ft.Ref[ft.TextField]()
_header_input_panel_btn_save_ref = ft.Ref[ft.Control]()

_input_column_tabels_ref = ft.Ref[ft.Column]()
_output_column_tabels_ref = ft.Ref[ft.Column]()

_desktop_row_ref = ft.Ref[ft.Row]()

_input_tabe_ref = ft.Ref[ft.DataTable]()
_output_tabe_ref = ft.Ref[ft.DataTable]()


NAME_MODULE = "blower_zigel"


class DummyEvent:
    def __init__(self, page):
        self.page = page
        self.control = None
        self.name = "init"

async def apply_page_settings(page: ft.Page, MODULE: DTCLS.ModuleCfg):
    Data: DTCLS.Data_page = page.data
    Data.Data_module = MODULE
    Data.Data_module.cust_data = blower_back.Cust_module_params()


def save_word(e: ft.ControlEvent):
    Data: DTCLS.Data_page = e.page.data
    cfg_module: DTCLS.ModuleCfg = Data.Data_module
    name = (_header_input_panel_textfield_ref.current.value or "").strip()
    if not name:
        name = blower_back.get_name_new_calc()
        _header_input_panel_textfield_ref.current.value = name
    rezult_data_for_save = blower_back.generate_rezult_data_for_save(name, _input_tabe_ref.current,
                                                                            _output_tabe_ref.current)
    rez = blower_back.save_word(rezult_data_for_save['input'], rezult_data_for_save['output'],
                                       rezult_data_for_save['name'], cfg_module.sub_dir, cfg_module.name)
    if not rez:
        CMF.message_dialog(
            e.page,
            body_icon=ft.Icons.ERROR,
            title="Ошибка",
            message="Не удалось сохранить документ word"
        )
    else:
        if not blower_back.save_in_db(e, name):
            CMF.message_dialog(
                e.page,
                body_icon=ft.Icons.ERROR,
                title="Ошибка",
                message="Ошибка во время сохранения отчета в истории"
            )
            return e
        CMF.dialog_save_file(e, rez)
    return e

def gen_page(page: ft.Page | DummyEvent):
    Data: DTCLS.Data_page = page.data

    def new_calc(e: ft.ControlEvent | DummyEvent, default_vals_input: dict | None = None):
        Data: DTCLS.Data_page = e.page.data

        def fnc_onchange_tbl_input(e, *args):
            """Автоподстановка полей при выборе материала в выпадающем списке. """
            try:
                meta = getattr(e.control, 'data', None) or {}
                cell = meta.get('cell')
                if not cell or not getattr(cell, 'parent_row', None):
                    return
                row = cell.parent_row
                if row.table_header:
                    return
                uniq = row.dict_cells().get('name').val
                if uniq != 'material_name':
                    return

                input_vals = blower_back.get_vals_from_input_data_tbl(_input_tabe_ref.current)
                merged, note, ok = blower_back.apply_material_defaults(input_vals, overwrite=True)

                if ok:
                    Data.Data_module.cust_data.input_tbl_editbl.set_vals_into_field(merged, 'val')
                    Data.Data_module.status_bar.set_text(f"{str(Cust_emoji.EmojiMain.Статусы.info)} {note}")
                    _input_tabe_ref.current.update()
                else:
                    Data.Data_module.status_bar.set_text(f"{str(Cust_emoji.EmojiMain.Статусы.warning)} {note}")
                    e.page.update()
            except Exception as ex:
                Data.Data_module.status_bar.set_text(
                    f"{str(Cust_emoji.EmojiMain.Статусы.warning)} Ошибка автоподстановки по материалу: {ex}"
                )
                e.page.update()
            return

        generate_desktop_row(page, rail)

        if _input_tabe_ref.current in _input_column_tabels_ref.current.controls:
            _input_column_tabels_ref.current.controls.clear()

        def _on_manual_du_toggle(ev: ft.ControlEvent):
            enabled = bool(getattr(ev.control, "value", False))
            Data.Data_module.cust_data.manual_du_enabled = enabled
            blower_back.set_manual_du_inputs_enabled(Data.Data_module.cust_data.input_tbl_editbl, enabled)
            st = Cust_emoji.EmojiMain.Статусы.info if enabled else Cust_emoji.EmojiMain.Статусы.info
            Data.Data_module.status_bar.set_text(
                f"{str(st)} Режим: {'ручной подбор Ду' if enabled else 'автоподбор Ду'}"
            )
            e.page.update()

        manual_du_switch = ft.Switch(
            value=bool(getattr(Data.Data_module.cust_data, "manual_du_enabled", False)),
            on_change=_on_manual_du_toggle,
            tooltip="Вкл — ручной подбор Ду (поля доступны) / Выкл — автоподбор Ду",
        )

        group_header_controls = {
            blower_back.MANUAL_DU_GROUP_NAME: {
                blower_back.MANUAL_DU_TOGGLE_FIELD: manual_du_switch
            }
        }

        input_table, table_data = blower_back.generate_input_data(
            fnc_onchange_tbl_input,
            _input_tabe_ref,
            default_vals_input,
            group_header_controls=group_header_controls,
        )
        Data.Data_module.cust_data.input_tbl_editbl = table_data
        _input_column_tabels_ref.current.controls.append(input_table)

        blower_back.set_manual_du_inputs_enabled(
            Data.Data_module.cust_data.input_tbl_editbl,
            bool(getattr(Data.Data_module.cust_data, "manual_du_enabled", False)),
        )
        DTCLS.Data_page.Data_module.status_bar.set_text()
        page.update()

    def generate_desktop_row(page: ft.Page, rail: ft.NavigationRail):
        Data: DTCLS.Data_page = page.data

        def fnc_cell_click(e):
            meta = e.control.data
            cell: CMF._Cell_data = meta["cell"]
            row_data: CMF.Row_data = cell.parent_row
            tbl_data: CMF.Table_data = row_data.parent_table_data
            if row_data.table_header:
                tbl_data.toggle_group(None)
            else:
                tbl_data.toggle_group(cell.val)

        def add_rez_table(e: ft.ControlEvent):
            if not bool(getattr(Data.Data_module.cust_data, "manual_du_enabled", False)):
                input_vals = blower_back.get_vals_from_input_data_tbl(_input_tabe_ref.current)

                merged = dict(input_vals)
                if str(merged.get("material_name") or "").strip():
                    merged, _note_mat, _ok_mat = blower_back.apply_material_defaults(merged, overwrite=False)

                picked, note, ok = blower_back.auto_pick_yellow_inputs(merged, overwrite=True)

                try:
                    Data.Data_module.cust_data.input_tbl_editbl.set_vals_into_field(picked, "val")
                    blower_back.set_manual_du_inputs_enabled(Data.Data_module.cust_data.input_tbl_editbl, False)
                    _input_tabe_ref.current.update()
                except Exception:
                    pass

                if ok:
                    Data.Data_module.status_bar.set_text(f"{str(Cust_emoji.EmojiMain.Статусы.info)} {note}")
                else:
                    Data.Data_module.status_bar.set_text(f"{str(Cust_emoji.EmojiMain.Статусы.warning)} {note}")

            btn_enabled = blower_back.generate_rez_tbl(
                e, _input_tabe_ref.current, _output_tabe_ref, fnc_cell_click
            )
            table_data: CMF.Table_data = DTCLS.Data_page.Data_module.cust_data.output_tbl
            tbl_rez = table_data.table_view if table_data else None
            if tbl_rez is None:
                return
            if _output_column_tabels_ref.current.controls:
                _output_column_tabels_ref.current.controls.clear()
            _output_column_tabels_ref.current.controls.append(tbl_rez)
            _output_column_tabels_ref.current.update()
            set_header_elems_visible(bool(btn_enabled))

            input_vals = blower_back.get_vals_from_input_data_tbl(_input_tabe_ref.current)
            _header_input_panel_textfield_ref.current.value = blower_back.get_name_new_calc(input_vals)

        rail_width = rail.min_width
        if rail.width:
            rail_width = rail.width

        desktop_row = ft.Row(
            controls=[
                ft.Column(controls=[], scroll=ft.ScrollMode.ALWAYS, expand=True, ref=_input_column_tabels_ref),
                ft.VerticalDivider(width=2),
                ft.Column(
                    controls=[],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    scroll=ft.ScrollMode.ALWAYS,
                    expand=True,
                    ref=_output_column_tabels_ref,
                ),
            ],
            scroll=ft.ScrollMode.ALWAYS,
            height=page.height - 120,
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True,
            ref=_desktop_row_ref,
        )

        save_control = ft.Button(
            'Сохранить',
            ft.Icons.SAVE_AS,
            on_click=save_word,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=1),
            ), height=50, width=150, ref=_header_input_panel_btn_save_ref
        )

        header_input_panel = ft.Row(
            controls=[
                ft.VerticalDivider(thickness=0, width=200),
                ft.Button(
                    "Расчет",
                    ft.Icons.CALCULATE,
                    on_click=add_rez_table,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=1)),
                    height=50,
                    width=150,
                    ref=_btn_calc_ref,
                ),
                ft.TextField(
                    label="Название расчета",
                    hint_text="Введите текст",
                    width=500,
                    icon=ft.Icons.NOTE_ALT,
                    ref=_header_input_panel_textfield_ref,
                ),
                save_control,
            ],
            spacing=120,
        )

        set_header_elems_visible(False)

        _desktop_column_ref.current.controls.clear()
        _desktop_column_ref.current.controls = [
            ft.Container(content=header_input_panel, padding=ft.padding.only(top=10)),
            ft.Divider(height=1),
            desktop_row,
        ]

    def select_destination(e: ft.ControlEvent):
        def load_history_dest(e: ft.ControlEvent):
            def selectedRowsfnc(e: ft.ControlEvent, row_index: int, row_data: CMF.Row_data):
                s_num = int(row_data.dict_cells()["s_num"].val)
                name = row_data.dict_cells()["name"].val
                input_tbl, output_tbl = blower_back.load_from_db_history_calc(e.page.data, s_num)
                if not input_tbl or not output_tbl:
                    CMF.message_dialog(
                        e.page,
                        body_icon=ft.Icons.ERROR,
                        title="Ошибка",
                        message="Не удалось загрузить историю расчетов"
                    )
                    return
                data_tbl_input = CMF.generate_param_table(input_tbl, ref=_input_tabe_ref)

                data_tbl_output = CMF.Table_view(
                    output_tbl,
                    ref=_output_tabe_ref,
                    lazy_groups=True,
                    single_group_expand=False,
                )
                output_tbl.toggle_group(None)  # раскрыть все группы сразу

                Data.Data_module.cust_data.input_tbl_editbl = input_tbl
                Data.Data_module.cust_data.output_tbl = output_tbl

                generate_desktop_row(page, rail)

                _header_input_panel_textfield_ref.current.value = name
                _header_input_panel_textfield_ref.current.visible = True
                _header_input_panel_textfield_ref.current.disabled = True
                _input_column_tabels_ref.current.controls.append(data_tbl_input)
                _output_column_tabels_ref.current.controls.append(data_tbl_output)
                _btn_calc_ref.current.disabled = True
                page.update()

            tbl_data = blower_back.make_history_tbl_data(e.page.data)
            tbl_history = CMF.generate_param_table(
                tbl_data, selectedRowsfnc=selectedRowsfnc, selectedRows=True
            )

            _desktop_column_ref.current.controls.clear()

            def find_rez_table(e: ft.ControlEvent):
                Data.Data_module.cust_data.filtr_seach_history = _header_filtr_text_field_ref.current.value
                load_history_dest(e)

            header_input_panel = ft.Row(
                controls=[
                    ft.Button(
                        "Найти",
                        ft.Icons.CALCULATE,
                        on_click=find_rez_table,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=1)),
                        height=50,
                        width=150,
                        ref=_btn_search_ref,
                    ),
                    ft.TextField(
                        label="Название расчета",
                        hint_text="Введите текст",
                        width=500,
                        icon=ft.Icons.NOTE_ALT,
                        ref=_header_filtr_text_field_ref,
                    ),
                ],
                spacing=120,
            )

            _desktop_column_ref.current.controls = [header_input_panel, ft.Divider(), tbl_history]
            _desktop_column_ref.current.alignment = ft.MainAxisAlignment.START
            _desktop_column_ref.current.horizontal_alignment = ft.CrossAxisAlignment.START
            _desktop_column_ref.current.expand = True
            page.update()

        ind = e.control.selected_index
        selected_dist_name = list(DICT_BARS["destinations"].keys())[ind]
        if selected_dist_name == "История":
            load_history_dest(e)
        if selected_dist_name == "Новый":
            new_calc(e)

    rail = paint_rail(select_destination)

    _refStatusBar = ft.Ref[ft.Container]()
    _refStatusBarText = ft.Ref[ft.Text]()
    DTCLS.Data_page.Data_module.set_status_bar(_refStatusBar, _refStatusBarText)

    status_bar = ft.Column([ft.Divider(height=1), ft.Container(ft.Text("", ref=_refStatusBarText))])

    dynamic_container = ft.Container(
        ft.Column(controls=[], scroll=ft.ScrollMode.ALWAYS, expand=True, ref=_desktop_column_ref),
        expand=True,
    )
    status_container = ft.Container(content=status_bar, ref=_refStatusBar, height=100)

    new_calc(DummyEvent(page))

    return ft.Row(
        [
            rail,
            ft.VerticalDivider(width=1),
            ft.Column(controls=[dynamic_container, status_container], expand=True),
        ],
        expand=True,
        ref=_general_module_row_ref,
    )


def paint_rail(select_destination):
    def go_home(e):
        e.page.go("/")

    list_bars = []
    for name, module in DICT_BARS["destinations"].items():
        list_bars.append(
            ft.NavigationRailDestination(
                icon=ft.Icon(module["icon"]),
                selected_icon=ft.Icon(module["selected_icon"]),
                label=name,
            )
        )
    leading_data = DICT_BARS["leading"]
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=400,
        leading=ft.FloatingActionButton(
            icon=leading_data["icon"],
            content=leading_data["text"],
            on_click=lambda _: go_home(_),
        ),
        group_alignment=-0.9,
        destinations=list_bars,
        on_change=lambda e: select_destination(e),
    )
    return rail


def set_header_elems_visible(val: bool = True):
    if not _header_input_panel_btn_save_ref.current.visible == val:
        _header_input_panel_btn_save_ref.current.visible = val
        _header_input_panel_textfield_ref.current.visible = val
        return True
    return False
