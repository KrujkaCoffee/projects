import flet as ft
import components.calc_pneumatic_jet_back as calc_pneumatic_jet_back
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
_header_input_panel_btn_save_ref = ft.Ref[ft.Button]()

_input_column_tabels_ref = ft.Ref[ft.Column]()
_output_column_tabels_ref = ft.Ref[ft.Column]()

_desktop_row_ref = ft.Ref[ft.Row]()

_input_tabe_ref = ft.Ref[ft.DataTable]()
_output_tabe_ref = ft.Ref[ft.DataTable]()

NAME_MODULE = "pneumatic_jet"


def show_msgbox_err(e):
    # Проверяем доступ к странице
    CMF.msgbox(
        e,
        msg="Файл не был сохранен! Ошибка генерации",
        btn0_name="Закрыть",
        icon="WARNING",
        fontsize=14,
        title="Ошибка сохранения",
        time_life=3  # Автозакрытие через 5 секунд
    )

def apply_page_settings(page: ft.Page, MODULE:DTCLS.ModuleCfg):
    Data: DTCLS.Data_page = page.data
    route = page.route
    Data.Data_module = MODULE
    Data.Data_module.cust_data: calc_pneumatic_jet_back.Cust_module_params = calc_pneumatic_jet_back.Cust_module_params()
def gen_page(page):
    Data: DTCLS.Data_page = page.data

    def new_calc(e: ft.ControlEvent, default_vals_input: dict | None = None):
        Data: DTCLS.Data_page = e.page.data
        Data.Data_module.cust_data: calc_pneumatic_jet_back.Cust_module_params

        def fnc_onchange_tbl_input(e, *args):
            set_header_elems_visible(False)
            page.update()

        page: ft.Page = e.page

        # if not _desktop_column_ref.current:
        generate_desktop_row(page, rail)
        # _general_module_row_ref.current.controls.append(_desktop_column_ref.current)

        if _input_tabe_ref.current in _input_column_tabels_ref.current.controls:
            _input_column_tabels_ref.current.controls.clear()
        input_table_datatable, table_data = calc_pneumatic_jet_back.generate_input_data(fnc_onchange_tbl_input,
                                                                                 _input_tabe_ref,
                                                                                 default_vals_input)

        Data.Data_module.cust_data.input_tbl_editbl = table_data

        _input_column_tabels_ref.current.controls.append(input_table_datatable)
        DTCLS.Data_page.Data_module.status_bar.set_text()
        page.update()

    def generate_desktop_row(page: ft.Page, rail: ft.NavigationRail):
        Data: DTCLS.Data_page = page.data

        def add_rez_table(e: ft.ControlEvent):
            Data.Data_module.cust_data: calc_pneumatic_jet_back.Cust_module_params
            page = e.page
            btn_enabled = calc_pneumatic_jet_back.generate_rez_tbl(e, _input_tabe_ref.current,
                                                                                 _output_tabe_ref)
            table_data: CMF.Table_data = DTCLS.Data_page.Data_module.cust_data.output_tbl
            tbl_rez = table_data.table_view
            if tbl_rez == None:
                return
            if _output_column_tabels_ref.current.controls:
                _output_column_tabels_ref.current.controls.clear()
            _output_column_tabels_ref.current.controls.append(tbl_rez)
            set_header_elems_visible(btn_enabled)
            _header_input_panel_textfield_ref.current.value = calc_pneumatic_jet_back.get_name_new_calc(Data.Data_module.alias)

        def grab_new_table(e: ft.ControlEvent):
            dict_vals = calc_pneumatic_jet_back.get_vals_from_input_data_tbl(_input_tabe_ref.current)
            new_calc(e, dict_vals)

        def click_save_rez(e):
            Data: DTCLS.Data_page = e.page.data
            cfg_module: DTCLS.ModuleCfg = Data.Data_module
            name = _header_input_panel_textfield_ref.current.value
            rezult_data_for_save = calc_pneumatic_jet_back.generate_rezult_data_for_save(name, _input_tabe_ref.current,
                                                                                  _output_tabe_ref.current)
            rez = calc_pneumatic_jet_back.save_exel(rezult_data_for_save['input'], rezult_data_for_save['output'],
                                             rezult_data_for_save['name'], cfg_module.sub_dir,cfg_module.name)
            if not rez:
                show_msgbox_err(e)
                return
            else:
                if not calc_pneumatic_jet_back.save_in_db(e, name):
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
                alignment=ft.MainAxisAlignment.START,  # прижать всё к верху
                horizontal_alignment=ft.CrossAxisAlignment.START,  # прижать влево
                scroll=ft.ScrollMode.ALWAYS, expand=True,
                ref=_output_column_tabels_ref
            )
        ], scroll=ft.ScrollMode.ALWAYS, width=(Data.Data_vars.width - rail_width), height=Data.Data_vars.height,
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True, ref=_desktop_row_ref)

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
                                                           ref=_header_input_panel_textfield_ref),
                                              ft.Button(
                                                  'Сохранить',
                                                  ft.Icons.SAVE_AS,
                                                  on_click=click_save_rez,
                                                  style=ft.ButtonStyle(
                                                      shape=ft.RoundedRectangleBorder(radius=1),
                                                      # Радиус скругления в пикселях
                                                  ), height=50, width=150, ref=_header_input_panel_btn_save_ref
                                              )
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
                input_tbl, output_tbl = calc_pneumatic_jet_back.load_from_db_history_calc(e.page.data, s_num)

                data_tbl_input = CMF.generate_param_table(input_tbl, ref=_input_tabe_ref)
                data_tbl_output = CMF.generate_param_table(output_tbl, ref=_output_tabe_ref)
                generate_desktop_row(page, rail)
                _header_input_panel_textfield_ref.current.value = name
                _header_input_panel_textfield_ref.current.visible = True
                _header_input_panel_textfield_ref.current.disabled = True
                _input_column_tabels_ref.current.controls.append(data_tbl_input)
                _output_column_tabels_ref.current.controls.append(data_tbl_output)
                _btn_calc_ref.current.disabled = True
                _btn_grab_ref.current.visible = False
                page.update()

            tbl_data = calc_pneumatic_jet_back.make_history_tbl_data(e.page.data)
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

    statusBar = ft.Column([ft.Divider(height=1),
                           ft.Container(
                               ft.Text('', ref=_refStatusBarText))]
                          )

    dynamic_container = ft.Container(ft.Column(
        controls=[
        ],
        scroll=ft.ScrollMode.ALWAYS, expand=True, ref=_desktop_column_ref
    ), expand=True)
    status_container = ft.Container(content=statusBar,
                                    ref=_refStatusBar,
                                    height=100
                                    )
    # _general_module_row_ref.current = None
    # _desktop_column_ref.current = None

    # DTCLS.Data_page.Data_module.status_bar.set_text('123')

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


def set_header_elems_visible(val: bool = True):
    _header_input_panel_btn_save_ref.current.visible = val
    _header_input_panel_textfield_ref.current.visible = val


def set_header_elems_enabled(val: bool = True):
    _header_input_panel_btn_save_ref.current.disabled = not val
    _header_input_panel_textfield_ref.current.disabled = not val
