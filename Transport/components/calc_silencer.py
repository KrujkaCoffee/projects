import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import flet as ft

import components.calc_silencer_back as calc_silencer_back
import components.common_funcs as CMF
import data_class as DTCLS

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_emoji as Cust_emoji
from project_cust_38 import Cust_SQLite as CSQ
from components.tech_report_excel import build_tech_report_xlsx
from components.tech_report_settings_dialog import open_tech_report_settings_dialog

try:
    from components.silencer_chart_report import build_silencer_report
except Exception:
    build_silencer_report = None

try:
    from components.silencer_report_pdf import build_silencer_report_pdf
except Exception:
    build_silencer_report_pdf = None

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
NAME_MODULE = "silencer"


class DummyEvent:
    """Минимальное событие для первичной отрисовки экрана ввода."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.control = None


@dataclass
class SilencerPageRefs:
    """Все изменяемые UI-ссылки одной страницы расчёта."""

    btn_calc: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Button]())
    btn_grab: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Button]())
    btn_report: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Button]())
    header_filter: ft.Ref = field(default_factory=lambda: ft.Ref[ft.TextField]())
    btn_search: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Button]())
    general_module_row: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Row]())
    desktop_column: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Column]())
    calculation_name: ft.Ref = field(default_factory=lambda: ft.Ref[ft.TextField]())
    save_button: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Control]())
    input_column: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Column]())
    output_column: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Column]())
    desktop_row: ft.Ref = field(default_factory=lambda: ft.Ref[ft.Row]())
    input_table: ft.Ref = field(default_factory=lambda: ft.Ref[ft.DataTable]())
    output_table: ft.Ref = field(default_factory=lambda: ft.Ref[ft.DataTable]())


def _page_refs(page: ft.Page) -> SilencerPageRefs:
    module_data = page.data.Data_module.cust_data
    refs = getattr(module_data, 'ui_refs', None)
    if not isinstance(refs, SilencerPageRefs):
        refs = SilencerPageRefs()
        module_data.ui_refs = refs
    return refs


def _draft_storage_key(Data: DTCLS.Data_page, module_alias: str) -> str:
    owner = Data.Data_user.login or Data.Data_user.ip or 'anonymous'
    return f"transport_draft::{owner}::{module_alias}"


def _schedule_draft_save(page: ft.Page, input_values: dict[str, Any]) -> None:
    module_data = page.data.Data_module.cust_data
    module_data.draft_revision = int(getattr(module_data, 'draft_revision', 0)) + 1
    revision = module_data.draft_revision
    storage_key = module_data.draft_storage_key
    payload = {
        'schema_version': 1,
        'module': NAME_MODULE,
        'inputs': input_values,
    }

    async def _save_after_debounce():
        await asyncio.sleep(0.75)
        if revision != getattr(module_data, 'draft_revision', 0):
            return
        try:
            await ft.SharedPreferences().set(
                storage_key,
                json.dumps(payload, ensure_ascii=False),
            )
        except Exception as exc:
            print(f'Не удалось сохранить черновик Transport: {exc}')

    page.run_task(_save_after_debounce)


def _clear_draft(page: ft.Page) -> None:
    module_data = page.data.Data_module.cust_data
    module_data.draft_revision = int(getattr(module_data, 'draft_revision', 0)) + 1
    _client_storage_remove_safe(page, module_data.draft_storage_key)




async def apply_page_settings(page: ft.Page,MODULE:DTCLS.ModuleCfg):
    Data: DTCLS.Data_page = page.data
    Data.Data_module = MODULE
    Data.Data_module.cust_data: calc_silencer_back.Cust_module_params = calc_silencer_back.Cust_module_params()
    Data.Data_module.cust_data.ui_refs = SilencerPageRefs()
    Data.Data_module.cust_data.draft_revision = 0
    Data.Data_module.cust_data.draft_storage_key = _draft_storage_key(Data, MODULE.alias)
    Data.Data_module.cust_data.pending_draft = None

    try:
        storage_key = f"tech_report_cfg::{MODULE.alias}"
        client_storage = ft.SharedPreferences()
        stored = await client_storage.get(storage_key)
        if isinstance(stored, str):
            try:
                stored = json.loads(stored)
            except Exception:
                stored = None
        if isinstance(stored, dict):
            setattr(Data.Data_module.cust_data, "tech_report_cfg", stored)
    except Exception:
        pass

    try:
        stored_draft = await ft.SharedPreferences().get(Data.Data_module.cust_data.draft_storage_key)
        if isinstance(stored_draft, str):
            stored_draft = json.loads(stored_draft)
        if (
            isinstance(stored_draft, dict)
            and stored_draft.get('schema_version') == 1
            and isinstance(stored_draft.get('inputs'), dict)
        ):
            Data.Data_module.cust_data.pending_draft = stored_draft['inputs']
    except Exception:
        pass


def _client_storage_set_safe(page: ft.Page, key: str, value: Any) -> None:
    async def _do():
        try:
            client_storage = ft.SharedPreferences()
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
    refs = _page_refs(e.page)
    cfg_module = Data.Data_module
    name = refs.calculation_name.current.value

    rezult_data_for_save = calc_silencer_back.generate_rezult_data_for_save(
        name, refs.input_table.current, refs.output_table.current
    )
    rez = calc_silencer_back.save_exel(
        rezult_data_for_save["input"],
        rezult_data_for_save["output"],
        rezult_data_for_save["name"],
        cfg_module.sub_dir,
        cfg_module.name,
    )
    if not rez:
        CMF.message_dialog(
            e.page,
            body_icon=ft.Icons.ERROR,
            title="Ошибка",
            message="Не удалось сохранить документ word"
        )
        return

    # if not calc_silencer_back.save_in_db(e, name):
    #     return

    CMF.dialog_save_file(e, rez)

def _save_excel(e: ft.ControlEvent):
    Data: DTCLS.Data_page = e.page.data
    Data.Data_module.status_bar.set_text(
        f"{str(Cust_emoji.EmojiMain.Статусы.info)} Excel-отчёт пока в разработке"
    )
    e.page.update()

def _tech_build(e: ft.ControlEvent):
    Data: DTCLS.Data_page = e.page.data
    refs = _page_refs(e.page)
    if build_tech_report_xlsx is None:
        Data.Data_module.status_bar.set_text(
            f"{str(Cust_emoji.EmojiMain.Статусы.warning)} Модуль tech-отчёта не подключен"
        )
        e.page.update()
        return

    cfg_module = Data.Data_module
    name = (refs.calculation_name.current.value or "tech_report").strip()

    input_rows = CMF.datatable_to_dicts(refs.input_table.current)

    calculated, errors, success = calc_silencer_back.prepare_calc_new_data(input_rows, Data)
    if calculated is None:
        CMF.message_dialog(
            e.page,
            body_icon=ft.Icons.ERROR,
            title="Ошибка",
            message="Произошла критическая ошибка во время расчетов"
        )
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
        CMF.message_dialog(
            e.page,
            body_icon=ft.Icons.ERROR,
            title="Ошибка",
            message="Не удалось сохранить excel"
        )
        return

    if calc_silencer_back.save_in_db(e, name):
        _clear_draft(e.page)
    CMF.dialog_save_file(e, path)


async def _tech_settings(e: ft.ControlEvent):
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
            sb = Data.Data_module.status_bar
            sb.set_text("Настройки технологического отчёта сохранены")
            # обновляем только статусбар (без page.update!)
            if getattr(sb, "_refConteiner", None) and sb._refConteiner.current:
                sb._refConteiner.current.update()
            if getattr(sb, "_refStatusBarText", None) and sb._refStatusBarText.current:
                sb._refStatusBarText.current.update()
        except Exception:
            pass

    await open_tech_report_settings_dialog(
        e.page,
        output_params=calc_silencer_back.OUTPUT_PARAMS,
        cfg=cfg,
        on_save=_on_save,
    )

def _save_in_db(e: ft.ControlEvent):
    Data: DTCLS.Data_page = e.page.data
    refs = _page_refs(e.page)
    module_data: calc_silencer_back.Cust_module_params = Data.Data_module.cust_data

    input_tbl = getattr(module_data, "input_tbl_editbl", None)
    output_tbl = getattr(module_data, "output_tbl", None)
    if input_tbl is None or output_tbl is None:
        CMF.message_dialog(
            e.page,
            title="Сохранение невозможно",
            message="Сначала выполните расчёт.",
            body_icon=ft.Icons.WARNING,
        )
        return False
    if input_tbl.sync_ui_to_data('val') is False:
        return False

    name = (refs.calculation_name.current.value or '').strip()
    row = [
        F.now(),
        name,
        Data.Data_user.login,
        calc_silencer_back.build_history_blob(input_tbl, output_tbl),
    ]
    try:
        status = CSQ.custom_request_c(
            Data.Data_user.db_flet,
            "INSERT INTO silencer_history (date, name, login, data) VALUES (?, ?, ?, ?)",
            list_of_lists_c=[row],
        )
        if status:
            _clear_draft(e.page)
            CMF.message_dialog(
                e.page,
                title="Успешно сохранено",
                title_size=20,
                body_icon_color="green",
                body_icon=ft.Icons.CHECK_CIRCLE,
                btn_ok_text="Отлично"
            )
        else:
            CMF.message_dialog(
                e.page,
                title="Ошибка",
                message=f"Не удалось сохранить {Data.Data_module.name} в истории расчетов",
                body_icon=ft.Icons.ERROR,
                btn_ok_text="Ок"
            )
        return bool(status)
    except Exception as exc:
        CMF.message_dialog(
            e.page,
            title="Ошибка",
            message=f"Не удалось сохранить расчёт в истории: {exc}",
            body_icon=ft.Icons.ERROR,
        )
        return False

async def gen_page(page):
    Data: DTCLS.Data_page = page.data
    refs = _page_refs(page)

    def new_calc(e: ft.ControlEvent, default_vals_input: dict | None = None):
        Data: DTCLS.Data_page = e.page.data
        Data.Data_module.cust_data: calc_silencer_back.Cust_module_params
        restored_draft = False
        if default_vals_input is None:
            pending_draft = getattr(Data.Data_module.cust_data, 'pending_draft', None)
            if isinstance(pending_draft, dict):
                default_vals_input = pending_draft
                Data.Data_module.cust_data.pending_draft = None
                restored_draft = True

        def fnc_onchange_tbl_input(e, *args):
            meta = e.control.data
            cell:CMF._Cell_data = meta['cell']
            row_data: CMF.Row_data = cell.parent_row
            param_name = row_data.get_cell_unique().val
            new_val = e.data
            new_val = cell.description.cast_type(new_val)
            if (
                new_val == ''
                and cell.description.is_numeric
                and param_name in calc_silencer_back.BLANK_ZERO_INPUT_NAMES
            ):
                new_val = cell.description.data_type(0)
            cell.val = new_val

            if param_name == 'kolichestvo_kasset' and cell.params_field.name == 'val':
                calc_silencer_back.oform_kolichestvo_kasset(cell, new_val)
            if param_name == 'kolichestvo_stupenej_drosselirovaniya_sht' and cell.params_field.name == 'val':
                calc_silencer_back.oform_kolichestvo_stupenej_drosselirovaniya_sht(cell, new_val)
            if param_name == 'edinica_rashoda' and cell.params_field.name == 'val':
                calc_silencer_back.oform_edinica_rashoda(cell, new_val)

            try:
                Data.Data_module.cust_data.last_calculated = None
                Data.Data_module.cust_data.last_calc_errors = []
            except Exception:
                pass
            values_by_row = Data.Data_module.cust_data.input_tbl_editbl.to_dict_by_unique()
            _schedule_draft_save(
                e.page,
                {
                    name: values['val']
                    for name, values in values_by_row.items()
                    if name in calc_silencer_back.INPUT_PARAM_NAMES
                },
            )
            set_header_elems_visible(refs, False)

        page: ft.Page = e.page

        generate_desktop_row(page, rail)

        if refs.input_table.current in refs.input_column.current.controls:
            refs.input_column.current.controls.clear()
        input_table_datatable, table_data = calc_silencer_back.generate_input_data(fnc_onchange_tbl_input,
                                                                                 refs.input_table,
                                                                                 default_vals_input,
                                                                                 page=page)

        Data.Data_module.cust_data.input_tbl_editbl = table_data
        Data.Data_module.cust_data.last_calculated = None
        Data.Data_module.cust_data.last_input_vals = None
        Data.Data_module.cust_data.last_calc_errors = []

        refs.input_column.current.controls.append(input_table_datatable)
        if restored_draft:
            Data.Data_module.status_bar.set_text(
                f"{str(Cust_emoji.EmojiMain.Статусы.info)} Черновик восстановлен"
            )
        else:
            Data.Data_module.status_bar.set_text()
        # page.update()
        # apply_oforml(table_data)

    def generate_desktop_row(page: ft.Page, rail: ft.NavigationRail):
        Data: DTCLS.Data_page = page.data

        def fnc_cell_click(e):
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
            btn_enabled = calc_silencer_back.generate_rez_tbl(
                e,
                refs.input_table.current,
                refs.output_table,
                fnc_cell_click,
            )
            table_data: CMF.Table_data | None = Data.Data_module.cust_data.output_tbl
            if table_data is None:
                return
            try:
                input_vals = calc_silencer_back.get_vals_from_input_data_tbl(refs.input_table.current)
                Data.Data_module.cust_data.last_input_vals = input_vals
            except Exception:
                input_vals = {}
            tbl_rez = table_data.table_view
            if tbl_rez == None:
                return
            if refs.output_column.current.controls:
                refs.output_column.current.controls.clear()
            refs.output_column.current.controls.append(tbl_rez)
            refs.output_column.current.update()
            set_header_elems_visible(refs, bool(btn_enabled))
            refs.calculation_name.current.value = calc_silencer_back.get_name_new_calc(input_vals)


        def show_chart_report(e: ft.ControlEvent):
            if refs.input_table.current is None:
                Data.Data_module.status_bar.set_text(
                    f"{str(Cust_emoji.EmojiMain.Статусы.warning)} Сначала выполните расчёт"
                )
                e.page.update()
                return

            input_vals = getattr(Data.Data_module.cust_data, "last_input_vals", None)
            if not isinstance(input_vals, dict):
                try:
                    input_vals = calc_silencer_back.get_vals_from_input_data_tbl(refs.input_table.current)
                except Exception:
                    input_vals = {}

            calculated = getattr(Data.Data_module.cust_data, "last_calculated", None)
            if not isinstance(calculated, dict):
                input_rows = CMF.datatable_to_dicts(refs.input_table.current)
                calculated, errors, _success = calc_silencer_back.prepare_calc_new_data(input_rows, Data)
                if calculated is None:
                    CMF.message_dialog(
                        e.page,
                        body_icon=ft.Icons.ERROR,
                        title="Ошибка",
                        message="Не удалось подготовить данные для отчёта"
                    )
                    return
                Data.Data_module.cust_data.last_calculated = calculated
                Data.Data_module.cust_data.last_calc_errors = errors

            if build_silencer_report is None:
                Data.Data_module.status_bar.set_text(
                    f"{str(Cust_emoji.EmojiMain.Статусы.warning)} Модуль графического отчёта не подключен"
                )
                e.page.update()
                return

            back_controls = list(refs.desktop_column.current.controls)
            back_keyboard_handler = e.page.on_keyboard_event

            def back_to_calc(_e: ft.ControlEvent):
                _e.page.on_keyboard_event = back_keyboard_handler
                refs.desktop_column.current.controls = back_controls
                refs.desktop_column.current.update()

            def print_pdf(print_e: ft.ControlEvent):
                if build_silencer_report_pdf is None:
                    Data.Data_module.status_bar.set_text(
                        f"{str(Cust_emoji.EmojiMain.Статусы.warning)} Модуль PDF-отчёта не подключен"
                    )
                    print_e.page.update()
                    return

                btn = getattr(print_e, "control", None)
                try:
                    if btn is not None and hasattr(btn, "disabled"):
                        btn.disabled = True
                        btn.update()
                except Exception:
                    pass

                Data.Data_module.status_bar.set_text(
                    f"{str(Cust_emoji.EmojiMain.Статусы.info)} Формирую PDF-отчёт..."
                )
                print_e.page.update()

                async def _task():
                    await asyncio.sleep(0)
                    try:
                        report_name = ""
                        try:
                            report_name = (refs.calculation_name.current.value or "").strip()
                        except Exception:
                            report_name = ""
                        if not report_name:
                            report_name = str(input_vals.get("nazvanie_proekta") or "silencer_report")

                        path = build_silencer_report_pdf(
                            report_name=report_name,
                            calculated=calculated,
                            input_values=input_vals,
                            save_dir=Data.Data_module.sub_dir,
                        )
                        if not path:
                            raise RuntimeError("Не удалось сформировать PDF-отчёт")

                        Data.Data_module.status_bar.set_text(
                            f"{str(Cust_emoji.EmojiMain.Статусы.success)} PDF-отчёт сформирован"
                        )
                        CMF.dialog_save_file(print_e, path)
                    except Exception as ex:
                        Data.Data_module.status_bar.set_text(
                            f"{str(Cust_emoji.EmojiMain.Статусы.warning)} Ошибка формирования PDF-отчёта: {ex}"
                        )
                        CMF.message_dialog(
                            print_e.page,
                            body_icon=ft.Icons.ERROR,
                            title="Ошибка",
                            message=f"Не удалось сформировать PDF-отчёт: {ex}",
                        )
                    finally:
                        try:
                            if btn is not None and hasattr(btn, "disabled"):
                                btn.disabled = False
                                btn.update()
                        except Exception:
                            pass
                        try:
                            print_e.page.update()
                        except Exception:
                            pass

                print_e.page.run_task(_task)

            report_panel = build_silencer_report(
                calculated=calculated,
                input_values=input_vals,
                on_back=back_to_calc,
                on_print_pdf=print_pdf,
            )

            e.page.on_keyboard_event = None
            refs.desktop_column.current.controls = [report_panel]
            refs.desktop_column.current.alignment = ft.MainAxisAlignment.START
            refs.desktop_column.current.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
            refs.desktop_column.current.update()

            _refStatusBar.current.visible = False
            _refStatusBar.current.update()


        def grab_new_table(e: ft.ControlEvent):
            dict_vals = calc_silencer_back.get_vals_from_input_data_tbl(refs.input_table.current)
            new_calc(e, dict_vals)

        desktop_row = ft.Row(controls=[
            ft.Column(
                controls=[],
                scroll=ft.ScrollMode.ALWAYS, expand=True, ref=refs.input_column
            )
            ,
            ft.VerticalDivider(width=2),
            ft.Column(
                controls=[],
                horizontal_alignment=ft.CrossAxisAlignment.START,  # прижать влево
                scroll=ft.ScrollMode.ALWAYS, expand=True,
                ref=refs.output_column
            )
        ], scroll=ft.ScrollMode.ALWAYS,
            vertical_alignment=ft.CrossAxisAlignment.START,
            height=page.height - 120,
            expand=True, ref=refs.desktop_row)


        save_control = CMF.build_save_reports_menu(
            ref=refs.save_button,
            width=150,
            height=50,
            radius=1,
            on_word=_save_word,
            on_excel=_save_excel,
            on_tech_build=_tech_build,
            on_tech_settings=_tech_settings,
            on_db=_save_in_db
        )

        header_input_panel = ft.Row(controls=[ft.VerticalDivider(thickness=0, width=200),
                                              ft.Button(
                                                  'Правка',
                                                  ft.Icons.MODE_EDIT,
                                                  on_click=grab_new_table,
                                                  style=ft.ButtonStyle(
                                                      shape=ft.RoundedRectangleBorder(radius=1),
                                                      # Радиус скругления в пикселях
                                                  ), height=50, width=150, ref=refs.btn_grab, visible=False
                                              ),
                                              ft.Button(
                                                  'Расчет',
                                                  ft.Icons.CALCULATE,
                                                  on_click=add_rez_table,
                                                  style=ft.ButtonStyle(
                                                      shape=ft.RoundedRectangleBorder(radius=1),
                                                      # Радиус скругления в пикселях
                                                  ), height=50, width=150, ref=refs.btn_calc
                                              ),
                                              ft.Button(
                                                  '📊 График',
                                                  ft.Icons.INSERT_CHART,
                                                  on_click=show_chart_report,
                                                  style=ft.ButtonStyle(
                                                      shape=ft.RoundedRectangleBorder(radius=1),
                                                  ), height=50, width=170, ref=refs.btn_report, visible=False
                                              ),
                                              ft.TextField(label="Название расчета", hint_text="Введите текст",
                                                           width=500,
                                                           icon=ft.Icons.NOTE_ALT,
                                                           ref=refs.calculation_name), save_control
                                              ], spacing=120
                                    )

        set_header_elems_visible(refs, False)

        refs.desktop_column.current.controls.clear()
        refs.desktop_column.current.controls = [
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
            e.page.on_keyboard_event = None

            def selectedRowsfnc(e: ft.ControlEvent, row_index: int, row_data: CMF.Row_data):
                s_num = int(row_data.dict_cells()["s_num"].val)
                name = row_data.dict_cells()["name"].val
                try:
                    loaded = calc_silencer_back.load_from_db_history_calc(e.page.data, s_num)
                except Exception as exc:
                    CMF.message_dialog(
                        e.page,
                        title="Ошибка",
                        message=f"Не удалось прочитать расчёт из истории: {exc}",
                        body_icon=ft.Icons.ERROR,
                    )
                    return
                if not loaded:
                    CMF.message_dialog(
                        e.page,
                        title="Ошибка",
                        message="Расчёт не найден в истории.",
                        body_icon=ft.Icons.ERROR,
                    )
                    return
                input_tbl, output_tbl = loaded

                data_tbl_output = CMF.Table_view(
                    output_tbl,
                    ref=refs.output_table,
                    lazy_groups=True,
                    single_group_expand=False,
                )
                preferred_group = 'Уровень звукового давления на расстоянии 1 м. от ШГ, дБ'
                if preferred_group in getattr(data_tbl_output, '_group_order', []):
                    data_tbl_output.toggle_group_ui(preferred_group)
                elif getattr(data_tbl_output, '_group_order', []):
                    data_tbl_output.toggle_group_ui(data_tbl_output._group_order[0])

                for field in input_tbl.list_fields:
                    field.editable = False
                data_tbl_input = CMF.Table_view(
                    input_tbl,
                    ref=refs.input_table,
                )
                Data.Data_module.cust_data.input_tbl_editbl = input_tbl
                Data.Data_module.cust_data.output_tbl = output_tbl

                generate_desktop_row(page, rail)

                refs.calculation_name.current.value = name
                refs.calculation_name.current.visible = True
                refs.calculation_name.current.disabled = True
                refs.input_column.current.controls.append(data_tbl_input)
                refs.output_column.current.controls.append(data_tbl_output)
                refs.btn_calc.current.disabled = True
                data_rows = sum(
                    not row.merge and not row.table_header for row in output_tbl.rows
                )
                groups = len({
                    row.group_name
                    for row in output_tbl.rows
                    if row.group_name and row.merge and not row.table_header
                })
                Data.Data_module.status_bar.set_text(
                    f"{str(Cust_emoji.EmojiMain.Статусы.success)} Загружено: {data_rows} параметров, {groups} групп"
                )
                e.page.update()

            tbl_data = calc_silencer_back.make_history_tbl_data(e.page.data)
            tbl_history = CMF.generate_param_table(tbl_data, selectedRowsfnc=selectedRowsfnc, selectedRows=True)

            refs.desktop_column.current.controls.clear()

            def find_rez_table(e:ft.ControlEvent):
                Data.Data_module.cust_data.filtr_seach_history = refs.header_filter.current.value
                load_history_dest(e)


            header_input_panel = ft.Row(controls=[
                                                  ft.Button(
                                                      'Найти',
                                                      ft.Icons.CALCULATE,
                                                      on_click=find_rez_table,
                                                      style=ft.ButtonStyle(
                                                          shape=ft.RoundedRectangleBorder(radius=1),
                                                          # Радиус скругления в пикселях
                                                      ), height=50, width=150, ref=refs.btn_search
                                                  ),
                                                  ft.TextField(label="Название расчета", hint_text="Введите текст",
                                                               width=500,
                                                               icon=ft.Icons.NOTE_ALT,
                                                               ref=refs.header_filter),

                                                  ], spacing=120
                                        )

            refs.desktop_column.current.controls = [ header_input_panel,ft.Divider(),
                tbl_history
            ]
            refs.desktop_column.current.alignment=ft.MainAxisAlignment.START
            refs.desktop_column.current.horizontal_alignment=ft.CrossAxisAlignment.START
            refs.desktop_column.current.expand=True

        ind = e.control.selected_index
        selected_dist_name = list(DICT_BARS['destinations'].keys())[ind]
        if selected_dist_name == 'История':
            load_history_dest(e)

        if selected_dist_name == 'Новый':
            new_calc(e)

    rail = paint_rail(select_destination)

    _refStatusBar = ft.Ref[ft.Container]()
    _refStatusBarText = ft.Ref[ft.Text]()
    Data.Data_module.set_status_bar(_refStatusBar, _refStatusBarText)

    status_bar = ft.Column(
        [
            ft.Divider(height=1),
            ft.Container(ft.Text("", ref=_refStatusBarText)),
        ]
    )

    dynamic_container = ft.Container(ft.Column(
        controls=[
        ],
        scroll=ft.ScrollMode.ALWAYS, expand=True, ref=refs.desktop_column
    ), expand=True)
    status_container = ft.Container(content=status_bar,
                                    ref=_refStatusBar,
                                    height=100
                                    )
    # selected_index сам по себе не вызывает on_change. Без явной
    # инициализации экран оставался пустым, а сохранённый черновик не читался.
    new_calc(DummyEvent(page))

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
        expand=True,
        ref=refs.general_module_row
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


def set_header_elems_visible(refs: SilencerPageRefs, val: bool = True):
    changed = False
    if refs.save_button.current and refs.save_button.current.visible != val:
        refs.save_button.current.visible = val
        changed = True
    if refs.calculation_name.current and refs.calculation_name.current.visible != val:
        refs.calculation_name.current.visible = val
        changed = True
    if refs.btn_report.current and refs.btn_report.current.visible != val:
        refs.btn_report.current.visible = val
        changed = True
    return changed


def set_header_elems_enabled(refs: SilencerPageRefs, val: bool = True):
    changed = False
    if refs.save_button.current and refs.save_button.current.disabled == val:
        refs.save_button.current.disabled = not val
        changed = True
    if refs.calculation_name.current and refs.calculation_name.current.disabled == val:
        refs.calculation_name.current.disabled = not val
        changed = True
    if refs.btn_report.current and refs.btn_report.current.disabled == val:
        refs.btn_report.current.disabled = not val
        changed = True
    return changed
