import flet as ft
import components.calc_silencer_back as calc_silencer_back
import components.common_funcs as CMF
import data_class as DTCLS
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_emoji as Cust_emoji
from typing import Any

from components.tech_report_excel import build_tech_report_xlsx
from components.tech_report_settings_dialog import open_tech_report_settings_dialog

DICT_BARS = {"leading": {'text': 'Домой',
                         'icon': ft.Icons.HOME,
                         'selected_icon': ft.Icons.HOME_SHARP,
                         'data': {
                             '_ref': ft.Ref[ft.Text]()
                         }
                         },
             "destinations": {
                            "Новый":
                                 {'icon': ft.Icons.CREATE,
                                  'selected_icon': ft.Icons.CREATE_SHARP,
                                    'disabled' : True,
                                  'data': {
                                      '_ref': ft.Ref[ft.Text]()
                                  }
                                  },
                            "История":
                                 {'icon': ft.Icons.ARCHIVE,
                                  'selected_icon': ft.Icons.ARCHIVE_SHARP,
                                    'disabled' : True,
                                  'data': {
                                      '_ref': ft.Ref[ft.Text]()
                                  }
                                  },


                         }
             }
_btn_calc_ref = ft.Ref[ft.Button]()
_btn_grab_ref = ft.Ref[ft.Button]()

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

NAME_MODULE = "silencer"


def show_msgbox_err(e):
    CMF.msgbox(
        e,
        msg="Файл не был сохранен! Ошибка генерации",
        btn0_name="Закрыть",
        icon="WARNING",
        fontsize=14,
        title="Ошибка сохранения",
        time_life=3
    )

async def apply_page_settings(page: ft.Page,MODULE:DTCLS.ModuleCfg):
    Data: DTCLS.Data_page = page.data
    Data.Data_module = MODULE
    Data.Data_module.cust_data: calc_silencer_back.Cust_module_params = calc_silencer_back.Cust_module_params()

    try:
        storage_key = f"tech_report_cfg::{MODULE.alias}"
        client_storage = ft.SharedPreferences()
        stored = await client_storage.get(storage_key)
        if isinstance(stored, str):
            try:
                import json

                stored = json.loads(stored)
            except Exception:
                stored = None
        if isinstance(stored, dict):
            setattr(Data.Data_module.cust_data, "tech_report_cfg", stored)
    except Exception:
        pass


def _client_storage_set_safe(page: ft.Page, key: str, value: Any) -> None:
    async def _do():
        try:
            client_storage = ft.SharedPreferences()
            import json

            stored = json.dumps(value)
            await client_storage.set(key, stored)
        except Exception as e:
            print(e)
            pass
    page.run_task(_do)


def _client_storage_remove_safe(page: ft.Page, key: str) -> None:
    async def _do():
        try:
            client_storage = ft.SharedPreferences()
            await client_storage.remove(key)
        except Exception:
            pass
    page.run_task(_do)


def _save_word(e: ft.ControlEvent):
    Data: DTCLS.Data_page = e.page.data
    cfg_module = Data.Data_module
    name = _header_input_panel_textfield_ref.current.value

    rezult_data_for_save = calc_silencer_back.generate_rezult_data_for_save(
        name, _input_tabe_ref.current, _output_tabe_ref.current
    )
    rez = calc_silencer_back.save_exel(
        rezult_data_for_save["input"],
        rezult_data_for_save["output"],
        rezult_data_for_save["name"],
        cfg_module.sub_dir,
        cfg_module.name,
    )
    if not rez:
        show_msgbox_err(e)
        return

    if not calc_silencer_back.save_in_db(e, name):
        return

    CMF.dialog_save_file(e, rez)

def _save_excel(e: ft.ControlEvent):
    DTCLS.Data_page.Data_module.status_bar.set_text(
        f"{str(Cust_emoji.EmojiMain.Статусы.info)} Excel-отчёт пока в разработке"
    )
    e.page.update()

def _tech_build(e: ft.ControlEvent):
    if build_tech_report_xlsx is None:
        DTCLS.Data_page.Data_module.status_bar.set_text(
            f"{str(Cust_emoji.EmojiMain.Статусы.warning)} Модуль tech-отчёта не подключен"
        )
        e.page.update()
        return

    Data: DTCLS.Data_page = e.page.data
    cfg_module = Data.Data_module
    name = (_header_input_panel_textfield_ref.current.value or "tech_report").strip()

    input_rows = CMF.datatable_to_dicts(_input_tabe_ref.current)

    calculated, errors, success = calc_silencer_back.prepare_calc_new_data(input_rows, Data)
    if calculated is None:
        show_msgbox_err(e)
        return

    cfg = getattr(cfg_module.cust_data, "tech_report_cfg", None) or {}

    path = build_tech_report_xlsx(
        report_name=name,
        input_rows=input_rows,
        calculated=calculated,
        output_params=calc_silencer_back.OUTPUT_PARAMS,
        errors=errors,
        save_dir=cfg_module.sub_dir,
        module_alias=cfg_module.alias,
        cfg_raw=cfg,
    )
    if not path:
        show_msgbox_err(e)
        return

    calc_silencer_back.save_in_db(e, name)
    CMF.dialog_save_file(e, path)


def _tech_settings(e: ft.ControlEvent):
    Data: DTCLS.Data_page = e.page.data
    cfg = getattr(Data.Data_module.cust_data, "tech_report_cfg", None)
    if not isinstance(cfg, dict):
        cfg = {
          "transpose_enabled": True,
          "transpose_num_prefixes": ["ak_srednegeometricheskaya_chastota_gc"],
          "transpose_numfix": ["ak_srednegeometricheskaya_chastota_gc||14"],
          "transpose_tag_bases": ["pressure", "diameter"],
        }

    def _on_save(new_cfg: dict):
        setattr(Data.Data_module.cust_data, "tech_report_cfg", new_cfg)
        try:
            storage_key = f"tech_report_cfg::{Data.Data_module.alias}"
            persist = bool(new_cfg.get("persist", True))
            if persist:
                _client_storage_set_safe(e.page, storage_key, new_cfg)
            else:
                _client_storage_remove_safe(e.page, storage_key)
        except Exception:
            pass
        try:
            sb = DTCLS.Data_page.Data_module.status_bar
            sb.set_text("Настройки технологического отчёта сохранены")
            # обновляем только статусбар (без page.update!)
            if getattr(sb, "_refConteiner", None) and sb._refConteiner.current:
                sb._refConteiner.current.update()
            if getattr(sb, "_refStatusBarText", None) and sb._refStatusBarText.current:
                sb._refStatusBarText.current.update()
        except Exception:
            pass

    open_tech_report_settings_dialog(
        e.page,
        output_params=calc_silencer_back.OUTPUT_PARAMS,
        cfg=cfg,
        on_save=_on_save,
    )

def gen_page(page):
    Data: DTCLS.Data_page = page.data

    def new_calc(e: ft.ControlEvent, default_vals_input: dict | None = None):
        Data: DTCLS.Data_page = e.page.data
        Data.Data_module.cust_data: calc_silencer_back.Cust_module_params


        def apply_oforml(table_data:CMF.Table_data):
            for row_data in table_data.rows:
                for cell in row_data.cells:
                    if row_data.get_cell_unique().val == 'kolichestvo_kasset' and cell.params_field.name == 'val':
                         calc_silencer_back.oform_kolichestvo_kasset(cell,cell.val)

                    if row_data.get_cell_unique().val == 'kolichestvo_stupenej_drosselirovaniya_sht' and cell.params_field.name == 'val':
                        calc_silencer_back.oform_kolichestvo_stupenej_drosselirovaniya_sht(cell,cell.val)

                    if row_data.get_cell_unique().val == 'edinica_rashoda' and cell.params_field.name == 'val':
                        calc_silencer_back.oform_edinica_rashoda(cell,cell.val)
            # table_data.table_view.update_view()


        def fnc_onchange_tbl_input(e, *args):
            meta = e.control.data
            cell:CMF._Cell_data = meta['cell']
            row_data: CMF.Row_data = cell.parent_row
            old_val = cell.val
            new_val = e.data

            new_val = cell.description.cast_type(new_val)

            if row_data.get_cell_unique().val == 'kolichestvo_kasset' and cell.params_field.name == 'val':
                calc_silencer_back.oform_kolichestvo_kasset(cell, new_val)
            if row_data.get_cell_unique().val == 'kolichestvo_stupenej_drosselirovaniya_sht' and cell.params_field.name == 'val':
                calc_silencer_back.oform_kolichestvo_stupenej_drosselirovaniya_sht(cell, new_val)
            if row_data.get_cell_unique().val == 'edinica_rashoda' and cell.params_field.name == 'val':
                calc_silencer_back.oform_edinica_rashoda(cell, new_val)

            # if set_header_elems_visible(False) or table_data.table_view.fl_need_upd:
            #     table_data.table_view.update_view()

        page: ft.Page = e.page

        # if not _desktop_column_ref.current:
        generate_desktop_row(page, rail)
        # _general_module_row_ref.current.controls.append(_desktop_column_ref.current)

        if _input_tabe_ref.current in _input_column_tabels_ref.current.controls:
            _input_column_tabels_ref.current.controls.clear()
        input_table_datatable, table_data = calc_silencer_back.generate_input_data(fnc_onchange_tbl_input,
                                                                                 _input_tabe_ref,
                                                                                 default_vals_input)

        Data.Data_module.cust_data.input_tbl_editbl = table_data

        _input_column_tabels_ref.current.controls.append(input_table_datatable)
        DTCLS.Data_page.Data_module.status_bar.set_text()
        page.update()
        apply_oforml(table_data)

    def generate_desktop_row(page: ft.Page, rail: ft.NavigationRail):
        Data: DTCLS.Data_page = page.data

        def fnc_cell_click(e):
            def scroll_to_row(table_ref: ft.Ref[ft.DataTable], row_index: int):
                if table_ref.current:
                    # Получаем контейнер строки
                    row = table_ref.current.rows[row_index]
                    if hasattr(row, "ref") and row.ref and row.ref.current:
                        row.ref.current.scroll_into_view(
                            alignment=0.1,  # куда позиционировать (0.0 – верх, 1.0 – низ)
                            duration=300  # анимация
                        )
            meta = e.control.data
            cell: CMF._Cell_data = meta['cell']
            row_data: CMF.Row_data = cell.parent_row
            tbl_data: CMF.Table_data = row_data.parent_table_data
            if row_data.table_header:
                tbl_data.toggle_group(None)
            else:
                tbl_data.toggle_group(cell.val)


        def add_rez_table(e: ft.ControlEvent):
            Data.Data_module.cust_data: calc_silencer_back.Cust_module_params
            page = e.page
            btn_enabled = calc_silencer_back.generate_rez_tbl(e, _input_tabe_ref.current,
                                                                                 _output_tabe_ref,fnc_cell_click)
            table_data:CMF.Table_data = DTCLS.Data_page.Data_module.cust_data.output_tbl
            tbl_rez = table_data.table_view
            if tbl_rez == None:
                return
            if _output_column_tabels_ref.current.controls:
                _output_column_tabels_ref.current.controls.clear()
            _output_column_tabels_ref.current.controls.append(tbl_rez)
            _output_column_tabels_ref.current.update()
            set_header_elems_visible(btn_enabled)
            input_vals = calc_silencer_back.get_vals_from_input_data_tbl(_input_tabe_ref.current)
            _header_input_panel_textfield_ref.current.value = calc_silencer_back.get_name_new_calc(input_vals)
            #DTCLS.Data_page.Data_module.status_bar.set_text('Успешно рассчитано')


        def grab_new_table(e: ft.ControlEvent):
            dict_vals = calc_silencer_back.get_vals_from_input_data_tbl(_input_tabe_ref.current)
            new_calc(e, dict_vals)

        def click_save_rez(e):
            DTCLS.Data_page.Data_module.status_bar.set_text(f'{str(Cust_emoji.EmojiMain.Статусы.info)} Отчет не доделан, сохранение отключено')
            DTCLS.Data_page.page.update()
            return
            Data: DTCLS.Data_page = e.page.data
            cfg_module: DTCLS.Module_cfg = Data.Data_module
            name = _header_input_panel_textfield_ref.current.value
            rezult_data_for_save = calc_silencer_back.generate_rezult_data_for_save(name, _input_tabe_ref.current,
                                                                                  _output_tabe_ref.current)
            rez = calc_silencer_back.save_exel(rezult_data_for_save['input'], rezult_data_for_save['output'],
                                             rezult_data_for_save['name'], cfg_module.sub_dir,cfg_module.name)
            if not rez:
                show_msgbox_err(e)
                return
            else:
                if not calc_silencer_back.save_in_db(e, name):
                    return
                CMF.dialog_save_file(e, rez)
                return

        rail_width = rail.min_width
        if rail.width:
            rail_width = rail.width

        desktop_row = ft.Row(controls=[
            ft.Column(
                controls=[],
                scroll=ft.ScrollMode.ALWAYS, expand=True, ref=_input_column_tabels_ref
            )
            ,
            ft.VerticalDivider(width=2),
            ft.Column(
                controls=[],
                # alignment=ft.MainAxisAlignment.START,  # прижать всё к верху
                horizontal_alignment=ft.CrossAxisAlignment.START,  # прижать влево
                scroll=ft.ScrollMode.ALWAYS, expand=True,
                ref=_output_column_tabels_ref
            )
        ], scroll=ft.ScrollMode.ALWAYS, width=(Data.Data_vars.width - rail_width), height=Data.Data_vars.height,
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True, ref=_desktop_row_ref)


        save_control = CMF.build_save_reports_menu(
            ref=_header_input_panel_btn_save_ref,
            width=150,
            height=50,
            radius=1,
            on_word=_save_word,
            on_excel=_save_excel,
            on_tech_build=_tech_build,
            on_tech_settings=_tech_settings,
        )

        header_input_panel = ft.Row(controls=[ft.VerticalDivider(thickness=0, width=200),
                                              ft.Button(
                                                  'Правка',
                                                  ft.Icons.MODE_EDIT,
                                                  on_click=grab_new_table,
                                                  style=ft.ButtonStyle(
                                                      shape=ft.RoundedRectangleBorder(radius=1),
                                                      # Радиус скругления в пикселях
                                                  ), height=50, width=150, ref=_btn_grab_ref, visible=False
                                              ),
                                              ft.Button(
                                                  'Расчет',
                                                  ft.Icons.CALCULATE,
                                                  on_click=add_rez_table,
                                                  style=ft.ButtonStyle(
                                                      shape=ft.RoundedRectangleBorder(radius=1),
                                                      # Радиус скругления в пикселях
                                                  ), height=50, width=150, ref=_btn_calc_ref
                                              ),
                                              ft.TextField(label="Название расчета", hint_text="Введите текст",
                                                           width=500,
                                                           icon=ft.Icons.NOTE_ALT,
                                                           ref=_header_input_panel_textfield_ref), save_control
                                              # ft.Button(
                                              #     'Сохранить',
                                              #     ft.Icons.SAVE_AS,
                                              #     on_click=click_save_rez,
                                              #     style=ft.ButtonStyle(
                                              #         shape=ft.RoundedRectangleBorder(radius=1),
                                              #         # Радиус скругления в пикселях
                                              #     ), height=50, width=150, ref=_header_input_panel_btn_save_ref
                                              # )
                                              ], spacing=120
                                    )

        set_header_elems_visible(False)

        _desktop_column_ref.current.controls.clear()
        _desktop_column_ref.current.controls = [
            ft.Container(
                content=header_input_panel,
                padding=ft.padding.only(top=10)  # Отступ снизу
            ),

            ft.Divider(height=1),
            desktop_row
        ]

        return

    def select_destination(e: ft.ControlEvent):
        def load_history_dest(e: ft.ControlEvent):
            def selectedRowsfnc(e: ft.ControlEvent, row_index: int, row_data: CMF.Row_data):
                s_num = int(row_data.dict_cells()['s_num'].val)
                name = row_data.dict_cells()['name'].val
                input_tbl, output_tbl = calc_silencer_back.load_from_db_history_calc(e.page.data, s_num)
                data_tbl_input = CMF.generate_param_table(input_tbl, ref=_input_tabe_ref)
                data_tbl_output = CMF.generate_param_table(output_tbl, ref=_output_tabe_ref)
                generate_desktop_row(page, rail)
                _header_input_panel_textfield_ref.current.value = name
                _header_input_panel_textfield_ref.current.visible = True
                _header_input_panel_textfield_ref.current.disabled = True
                _input_column_tabels_ref.current.controls.append(data_tbl_input)
                _output_column_tabels_ref.current.controls.append(data_tbl_output)
                _btn_calc_ref.current.disabled = True
                _btn_grab_ref.current.visible = True
                page.update()

            tbl_data = calc_silencer_back.make_history_tbl_data(e.page.data)
            tbl_history = CMF.generate_param_table(tbl_data, selectedRowsfnc=selectedRowsfnc, selectedRows=True)

            _desktop_column_ref.current.controls.clear()

            def find_rez_table(e:ft.ControlEvent):
                Data.Data_module.cust_data.filtr_seach_history = _header_filtr_text_field_ref.current.value
                load_history_dest(e)


            header_input_panel = ft.Row(controls=[
                                                  ft.Button(
                                                      'Найти',
                                                      ft.Icons.CALCULATE,
                                                      on_click=find_rez_table,
                                                      style=ft.ButtonStyle(
                                                          shape=ft.RoundedRectangleBorder(radius=1),
                                                          # Радиус скругления в пикселях
                                                      ), height=50, width=150, ref=_btn_search_ref
                                                  ),
                                                  ft.TextField(label="Название расчета", hint_text="Введите текст",
                                                               width=500,
                                                               icon=ft.Icons.NOTE_ALT,
                                                               ref=_header_filtr_text_field_ref),

                                                  ], spacing=120
                                        )

            _desktop_column_ref.current.controls = [ header_input_panel,ft.Divider(),
                tbl_history
            ]
            _desktop_column_ref.current.alignment=ft.MainAxisAlignment.START
            _desktop_column_ref.current.horizontal_alignment=ft.CrossAxisAlignment.START
            _desktop_column_ref.current.expand=True

            page.update()


        ind = e.control.selected_index
        selected_dist_name = list(DICT_BARS['destinations'].keys())[ind]
        if selected_dist_name == 'История':
            load_history_dest(e)

        if selected_dist_name == 'Новый':
            new_calc(e)

    rail = paint_rail(select_destination)

    _refStatusBar = ft.Ref[ft.Container]()
    _refStatusBarText = ft.Ref[ft.Text]()
    DTCLS.Data_page.Data_module.set_status_bar(_refStatusBar, _refStatusBarText)

    status_bar = ft.Column(
        [
            ft.Divider(height=1),
            ft.Container(ft.Text("", ref=_refStatusBarText)),
        ]
    )

    dynamic_container = ft.Container(ft.Column(
        controls=[
        ],
        scroll=ft.ScrollMode.ALWAYS, expand=True, ref=_desktop_column_ref
    ), expand=True)
    status_container = ft.Container(content=status_bar,
                                    ref=_refStatusBar,
                                    height=100
                                    )
    # _general_module_row_ref.current = None
    # _desktop_column_ref.current = None

    return ft.Row([
        rail,
        ft.VerticalDivider(width=1),
        ft.Column(
            controls=[dynamic_container,
                      status_container
                      ],
            expand=True
        )

    ],
        # vertical_alignment= ft.CrossAxisAlignment.START,
        # width=(Data.Data_vars.width),
        # height=Data.Data_vars.height,
        expand=True,
        ref=_general_module_row_ref
    )


def paint_rail(select_destination):
    def go_home(e):
        e.page.go('/')


    list_bars = []
    for name, module in DICT_BARS['destinations'].items():
        list_bars.append(ft.NavigationRailDestination(icon=ft.Icon(module['icon']),
                                                      selected_icon=ft.Icon(module['selected_icon']),
                                                      label=name
                                                      ))
    leading_data = DICT_BARS['leading']
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=400,
        leading=ft.FloatingActionButton(icon=leading_data['icon'],
                                        content=leading_data['text'],
                                        on_click=lambda _: go_home(_)),
        group_alignment=-0.9,
        destinations=list_bars,
        on_change=lambda e: select_destination(e),  # e.control.selected_index
    )
    return rail


def set_header_elems_visible(val: bool = True): #todo нужен ли ререндер
    if not _header_input_panel_btn_save_ref.current.visible == val:
        _header_input_panel_btn_save_ref.current.visible = val
        _header_input_panel_textfield_ref.current.visible = val
        return True
    return False


def set_header_elems_enabled(val: bool = True): #todo нужен ли ререндер
    if  _header_input_panel_btn_save_ref.current.disabled == val:
        _header_input_panel_btn_save_ref.current.disabled = not val
        _header_input_panel_textfield_ref.current.disabled = not val
        return True
    return False

