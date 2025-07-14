import os
from typing import Self  # Только в Python 3.11+
import flet as ft
from typing import List, Dict
import socket
import data_class as DTCLS
from decimal import Decimal


# https://fonts.google.com/icons


class Field_params():
    def __init__(self, name: str, header: str = '', hidden: bool = False, editable: bool = False, width=100,
                 unique=False):
        self.name: str = name
        self.header: str = header
        self.hidden: bool = hidden
        self.editable: bool = editable
        self.width: int = width
        self.unique: bool = unique

    def __repr__(self):
        return f'cls Field_params, name = "{self.name}"'


class Cell_description():
    def __init__(self, min_max_list: tuple | list | None = None,
                 accuracy: int = 3, comment: str | None = None, data_type: type = str):

        if isinstance(min_max_list, tuple):
            if len(min_max_list) != 2:
                raise TypeError
            if type(min_max_list[0]) not in (float, int):
                raise TypeError
            if type(min_max_list[1]) not in (float, int):
                raise TypeError

        self.min_max_list = min_max_list  # если tuple то [0] - минимальное,[1] - максимальное, если list  то dropdown

        self.accuracy = accuracy  # точность после запятой
        self.comment = comment  #
        self.data_type = data_type

    def __repr__(self):
        return f'cls Cell_description, "{self.__dict__}"'


class _Cell_data():
    def __init__(self, val: int | float | str | None = None, description: Cell_description = Cell_description()):
        self.val: int | float | str = val
        self.description: Cell_description = description
        self.params_field: Field_params | None = None

    def __repr__(self):
        return f'cls Cell_data,  val = "{self.val}"'


class Row_data():
    def __init__(self):
        self.cells: List[_Cell_data] = []
        self._fields: Field_params | None = None

    def dict_cells(self) -> Dict[str, _Cell_data]:
        if self._fields == None:
            raise IndexError
        self._fields: list
        rez_dict = dict()
        for i in range(len(self._fields)):
            rez_dict[self._fields[i].name] = self.cells[i]
        return rez_dict

    def apply_new_vals(self, dict_unique_vals: dict, name_field: str):
        if name_field not in [_.params_field.name for _ in self.cells]:
            raise ValueError('name_field отсутствует в params_field')
        uniq_name = [_.val for _ in self.cells if _.params_field.unique][0]
        if uniq_name in dict_unique_vals:
            self.set_new_val(name_field, dict_unique_vals[uniq_name])
        return True

    def set_new_val(self, name_field, val):
        for cell in self.cells:
            if cell.params_field.name == name_field:
                cell.val = val
                break

    def append(self, val: float | int | str, desc: Cell_description):
        if type(val) is not desc.data_type:
            try:
                if desc.data_type is float:
                    val = float(val)
                if desc.data_type is int:
                    val = int(val)
                if desc.data_type is str:
                    val = str(val)
            except:
                raise TypeError
        self.cells.append(_Cell_data(val=val, description=desc))

    def __repr__(self):
        return f'cls Row_data, "{len(self.cells)}" cells'


class Table_data():
    def __init__(self, ):
        self.list_fields: List[Field_params] = []
        self._dict_params = dict()
        self.rows: list[Row_data] = []
        self._set_unique_vals = set()

    def set_vals_into_field(self, dict_vals: dict, name_filed: str):
        '''
        :param dict_vals: unique_field:new_val
        :param name_filed: name_filed = new_val
        :return:
        '''
        for rowData in self.rows:
            rowData.apply_new_vals(dict_vals, name_filed)

    def set_lock_vals(self, name_filed: str, lock: bool = True):
        for field in self.list_fields:
            if field.name == name_filed:
                field.editable = not lock

    def append_column_desc(self, name: str, header: str = '', hidden: bool = False, editable: bool = False, width=100,
                           unique=False):
        if name not in self._dict_params:
            item = Field_params(name, header, hidden, editable, width, unique)
            self.list_fields.append(item)
            self._dict_params[name] = item
        else:
            raise ValueError(f"Значение {name} не уникально")

    def get_param_by_name(self, name: str) -> Field_params:
        return self._dict_params[name]

    def _is_unique_determine(self) -> bool:
        count = sum([_.unique for _ in self.list_fields])
        if count == 1:
            return True
        return False

    def add_row(self, row: Row_data):
        if not self._is_unique_determine():
            raise InvalidUniqueError('Ошибка уникальности Field_params')

        if len(row.cells) != len(self.list_fields):
            raise IndexError
        for i, cell in enumerate(row.cells):
            cell.params_field = self.list_fields[i]
            row._fields = self.list_fields
            if cell.params_field.unique:
                if cell.val in self._set_unique_vals:
                    raise ValueError('Ошибка уникальности значения строки')
                else:
                    self._set_unique_vals.add(cell.val)

        self.rows.append(row)

    def __repr__(self):
        return f'cls Table_data, len(list_fields)="{len(self.list_fields)}" , len(rows)="{len(self.rows)}"'


class Input_param():
    def __init__(self, header: str, name: str, dimension: str = '', min_max_list: tuple | list = (0, 9999999),
                 default_val: int | float = 0, accuracy: int = 3, comment: str = ''):
        self.header = header  # строковое имя (поле таблицы)
        self.name = name  # уникальное название (поле таблицы)
        self.dimension = dimension  # единица измерения (поле таблицы)
        self.min_max_list = min_max_list  # если tuple то [0] - минимальное,[1] - максимальное, если list  то dropdown
        self.default_val = default_val  # значение по умолчанию
        self.accuracy = accuracy  # точность после запятой
        self.comment = comment  #

    def get(self, name_param):
        ans = None
        try:
            ans = eval(f'self.{name_param}')
        except:
            pass
        return ans

    def get_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class Module():  # TODO
    def __init__(self, icon: ft.Icons, tooltip: str, sub_module: Self = None):
        self.icon = icon
        self.tooltip = tooltip
        self.sub_module = sub_module
        ...


class InvalidUniqueError(ValueError):
    pass


def ip_to_hostname(ip_address):
    """
    Преобразует IP-адрес в доменное имя (hostname), если это возможно.

    Args:
        ip_address (str): IP-адрес (например, "192.168.1.1" или "127.0.0.1").

    Returns:
        str: Доменное имя или исходный IP, если разрешение не удалось.

    Raises:
        socket.herror: При ошибке разрешения имени.
    """
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except socket.herror:
        print(f"Не удалось разрешить IP '{ip_address}' в hostname.")
        return ip_address  # Возвращаем исходный IP, если имя не найдено
    except socket.error as e:
        print(f"Ошибка сети: {e}")
        return ip_address


def create_value_cell(cell_data: _Cell_data, visible: bool = True, width=None, fnc_onchange=None) -> ft.DataCell:
    width = 100 if width is None else width
    # """Создает ячейку значения в зависимости от типа параметра"""
    val = cell_data.val
    fnc_on_change = None
    # if fnc_onchange:
    #    fnc_on_change = lambda cell_data: fnc_onchange(cell_data)
    fnc_on_change = fnc_onchange
    if isinstance(cell_data.description.min_max_list, list):
        # Выпадающий список для параметров с множеством вариантов
        options = [ft.dropdown.Option(str(x)) for x in cell_data.description.min_max_list]

        return ft.DataCell(
            ft.Container(
                ft.Dropdown(
                    options=options,
                    value=str(val),
                    on_change=fnc_on_change,
                    tooltip=cell_data.description.comment,
                    border=ft.InputBorder.NONE,
                    width=width,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                ),
                width=width,  # Дублируем ширину у Container
            )
            , visible=visible
        )
    elif isinstance(cell_data.description.min_max_list, tuple):
        # Числовое поле с ограничениями
        min_val, max_val = cell_data.description.min_max_list
        tooltip = f"Допустимый диапазон: {min_val}...{max_val}"
        if cell_data.description.comment and len(cell_data.description.comment.strip()):
            tooltip = '\n'.join([f'{cell_data.description.comment}\n', f"Допустимый диапазон: {min_val}...{max_val}"])

        value = str(round(val, cell_data.description.accuracy))

        return ft.DataCell(
            ft.Container(
                ft.TextField(
                    value=value,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    input_filter=ft.InputFilter(r'^\d*\.?\d*$'),  # Только числа
                    on_change=fnc_on_change,
                    tooltip=tooltip,
                    border=ft.InputBorder.NONE,
                    width=width,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                ),
                width=width,  # Дублируем ширину у Container
            )
            , visible=visible
        )
    else:
        # Простое текстовое поле
        return ft.DataCell(
            ft.Container(
                ft.TextField(
                    value=str(val),
                    on_change=fnc_on_change,
                    border=ft.InputBorder.NONE,
                    tooltip=cell_data.description.comment,
                    width=width,  # Теперь должно работать
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                ),
                width=width,  # Дублируем ширину у Container
            )
            , visible=visible
        )


def generate_param_table(
        table_input_data: Table_data,
        bold_header=True,
        fnc_onchange=None,
        ref: ft.Ref[ft.DataTable] = None,
        selectedRows=False,
        selectedRowsfnc=None

) -> ft.DataTable:
    """
    Генерирует DataTable для списка параметров Input_param

    Args:
        data: Список объектов Input_param
        editable: Разрешить редактирование значений
        hidden_columns: Список имен колонок для скрытия (например, ['name'])

    Returns:
        Настроенный объект ft.DataTable
    """

    def selectedRowsfnc_dflt(e: ft.ControlEvent, add_fnc=None):
        page: ft.Page = e.page
        # Получаем данные строки
        row_index = e.control.data["row_index"]
        row_data = table_input_data.rows[row_index]
        if add_fnc:
            add_fnc(e, row_index, row_data)

    # Определяем видимые колонки
    font_weight = ft.FontWeight.NORMAL
    if bold_header:
        font_weight = ft.FontWeight.BOLD

    visible_columns = []
    for field in table_input_data.list_fields:
        header = field.header
        visible = not field.hidden
        if header:
            visible_columns.append(ft.DataColumn(ft.Text(header, weight=font_weight), visible=visible))

    # Создаем строки
    rows = []
    for i, row_data in enumerate(table_input_data.rows):
        list_cells = []
        for cell_data in row_data.cells:
            text = cell_data.val
            if cell_data.params_field.editable:
                value_cell = create_value_cell(cell_data, fnc_onchange=fnc_onchange, width=cell_data.params_field.width,
                                               visible=not cell_data.params_field.hidden)
                list_cells.append(value_cell)
            else:
                if cell_data.description.data_type is float:
                    text = Decimal(str(round(text, cell_data.description.accuracy)))
                list_cells.append(
                    ft.DataCell(
                        content=ft.Text(
                            text,
                            no_wrap=False,
                            width=cell_data.params_field.width
                        ),
                        visible=not cell_data.params_field.hidden
                    )
                )
        if selectedRows:
            rows.append(ft.DataRow(cells=list_cells,
                                   on_select_changed=lambda e, idx=i: selectedRowsfnc_dflt(e, selectedRowsfnc),
                                   data={"row_index": i}))
        else:
            rows.append(ft.DataRow(cells=list_cells,
                                   ))

    # if ref:
    #    if ref.current:
    #        ref.current = None

    new_table = ft.DataTable(
        columns=visible_columns,
        rows=rows,
        border=ft.border.all(1),

        vertical_lines=ft.border.BorderSide(1, color=ft.Colors.GREY_400),
        horizontal_lines=ft.border.BorderSide(1, color=ft.Colors.GREY_600),
        column_spacing=15,
        horizontal_margin=5,
        bgcolor=ft.Colors.SURFACE,
        ref=ref
    )
    return new_table


def datatable_to_dicts(table: ft.DataTable) -> list[dict]:
    """
    Преобразует DataTable в список словарей с поддержкой различных контролов.

    Args:
        table: Объект ft.DataTable

    Returns:
        Список словарей, где ключи - заголовки колонок,
        а значения - содержимое ячеек
    """
    if not table.columns or not table.rows:
        return []

    # Получаем названия колонок
    column_names = []
    for col in table.columns:
        if isinstance(col.label, ft.Text):
            column_names.append(col.label.value)
        else:
            column_names.append(f"Column_{len(column_names)}")

    # Извлекаем данные из строк
    result = []
    for row in table.rows:
        row_dict = {}
        for i, cell in enumerate(row.cells):
            if i >= len(column_names):
                break

            cell_value = ""
            if cell.content is not None:
                content = cell.content
                if isinstance(content, ft.Container):
                    content = content.content
                # Обработка разных типов контролов
                if isinstance(content, ft.Text):
                    cell_value = content.value
                elif isinstance(content, ft.TextField):
                    cell_value = content.value
                elif isinstance(content, ft.Dropdown):
                    cell_value = content.value
                elif isinstance(content, ft.Checkbox):
                    cell_value = content.value
                elif isinstance(content, ft.RadioGroup):
                    cell_value = content.value
                elif isinstance(content, ft.Slider):
                    cell_value = content.value
                elif isinstance(content, ft.Switch):
                    cell_value = content.value
                elif hasattr(content, "value"):
                    cell_value = str(content.value)
                else:
                    # Для сложных контролов пытаемся получить текстовое представление
                    try:
                        if isinstance(content, ft.Container):
                            if isinstance(content.content, ft.Text):
                                cell_value = content.content.value
                            else:
                                cell_value = str(content.content)
                        else:
                            cell_value = str(content)
                    except:
                        cell_value = ""
            if isinstance(cell_value, Decimal):
                cell_value = str(float(cell_value))
            row_dict[column_names[i]] = cell_value.strip() if isinstance(cell_value, str) else cell_value

        result.append(row_dict)

    return result


def msgboxgYN(
        e,
        msg: str,
        btn0_name: str = "Да",
        btn1_name: str = "Нет",
        func_theme=None,
        time_life: int = 0,
        icon: str = "INFO",
        fontsize: int = 14,
        icon_str: str = None,
        title: str = "Внимание!"
) -> bool:
    """Кастомное модальное окно с кнопками Да/Нет"""
    page = e.page
    result = [None]  # Используем список для изменения из вложенных функций

    # Удаляем предыдущий overlay, если есть
    if hasattr(page, 'modal_overlay_yn'):
        page.overlay.remove(page.modal_overlay_yn)

    # Определяем иконку
    icon_mapping = {
        "NOICON": None,
        "QUESTION": ft.icons.HELP_OUTLINE,
        "INFO": ft.icons.INFO_OUTLINE,
        "WARNING": ft.icons.WARNING_AMBER,
        "CRITICAL": ft.icons.ERROR_OUTLINE
    }

    if icon_str:
        icon = icon_str.upper()
    selected_icon = icon_mapping.get(icon.upper(), ft.icons.INFO_OUTLINE)

    # Определяем цвета
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    colors = {
        'bg': ft.colors.SURFACE_VARIANT if is_dark else ft.colors.WHITE,
        'text': ft.colors.ON_SURFACE_VARIANT if is_dark else ft.colors.BLACK,
        'divider': ft.colors.OUTLINE_VARIANT,
        'icon': ft.colors.BLUE_400 if is_dark else ft.colors.BLUE_600,
        'btn_yes': ft.colors.GREEN_400 if is_dark else ft.colors.GREEN_600,
        'btn_no': ft.colors.RED_400 if is_dark else ft.colors.RED_600
    }

    # Создаем содержимое окна
    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(selected_icon, color=colors['icon']) if selected_icon else ft.Container(),
                    ft.Text(title, weight=ft.FontWeight.BOLD, size=fontsize + 2, color=colors['text']),
                ],
                spacing=10
            ),
            ft.Divider(height=1, color=colors['divider']),
            ft.Text(msg, size=fontsize, color=colors['text']),
        ],
        spacing=15
    )

    # Функции обработки кнопок
    def set_result(res: bool):
        result[0] = res
        close_modal()

    # Создаем модальное окно
    modal_content = ft.Container(
        width=400,
        padding=20,
        border_radius=10,
        bgcolor=colors['bg'],
        border=ft.border.all(1, colors['divider']),
        content=ft.Column(
            controls=[
                content,
                ft.Row(
                    controls=[
                        ft.TextButton(
                            btn0_name,
                            on_click=lambda _: set_result(True),
                            style=ft.ButtonStyle(
                                color=colors['btn_yes'],
                                shape=ft.RoundedRectangleBorder(radius=5),
                                padding=ft.padding.symmetric(horizontal=20, vertical=8)
                            )
                        ),
                        ft.TextButton(
                            btn1_name,
                            on_click=lambda _: set_result(False),
                            style=ft.ButtonStyle(
                                color=colors['btn_no'],
                                shape=ft.RoundedRectangleBorder(radius=5),
                                padding=ft.padding.symmetric(horizontal=20, vertical=8)
                            )
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=10
                )
            ],
            spacing=20
        )
    )

    # Создаем overlay
    overlay = ft.Container(
        bgcolor=ft.colors.with_opacity(0.5, ft.colors.BLACK),
        content=ft.Stack(
            controls=[
                ft.Container(on_click=lambda e: set_result(False)),  # Клик вне окна = Нет
                ft.Column(
                    controls=[
                        ft.Container(expand=True),
                        ft.Row(
                            controls=[
                                ft.Container(expand=True),
                                modal_content,
                                ft.Container(expand=True),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(expand=True),
                    ],
                    expand=True
                )
            ],
            expand=True
        )
    )

    # Функция закрытия
    def close_modal():
        overlay.visible = False
        page.update()
        if func_theme:
            func_theme(overlay)

    # Добавляем overlay на страницу
    page.modal_overlay_yn = overlay
    page.overlay.append(overlay)
    page.update()

    # Автозакрытие
    if time_life > 0:
        def auto_close():
            import time
            time.sleep(time_life)
            if overlay.visible:
                set_result(False)  # При автозакрытии возвращаем False

        import threading
        threading.Thread(target=auto_close, daemon=True).start()

    # Ждем результата
    while result[0] is None:
        import time
        time.sleep(0.1)

    # Убираем overlay после получения результата
    page.overlay.remove(overlay)
    page.update()

    return result[0]


def msgbox(
        e,
        msg: str,
        btn0_name: str = "OK",
        func_theme=None,
        time_life: int = 0,
        icon: str = "INFO",
        fontsize: int = 14,
        icon_str: str = None,
        title: str = "Внимание!"
):
    """Кастомное модальное окно сообщения для Flet"""
    page = e.page

    # Удаляем предыдущий overlay, если есть
    if hasattr(page, 'modal_overlay'):
        page.overlay.remove(page.modal_overlay)

    # Определяем иконку
    icon_mapping = {
        "NOICON": None,
        "QUESTION": ft.icons.HELP_OUTLINE,
        "INFO": ft.icons.INFO_OUTLINE,
        "WARNING": ft.icons.WARNING_AMBER,
        "CRITICAL": ft.icons.ERROR_OUTLINE
    }

    if icon_str:
        icon = icon_str.upper()
    selected_icon = icon_mapping.get(icon.upper(), ft.icons.INFO_OUTLINE)

    # Определяем цвета
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    colors = {
        'bg': ft.colors.SURFACE_VARIANT if is_dark else ft.colors.WHITE,
        'text': ft.colors.ON_SURFACE_VARIANT if is_dark else ft.colors.BLACK,
        'divider': ft.colors.OUTLINE_VARIANT,
        'icon': ft.colors.BLUE_400 if is_dark else ft.colors.BLUE_600
    }

    # Создаем содержимое окна
    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(selected_icon, color=colors['icon']) if selected_icon else ft.Container(),
                    ft.Text(title, weight=ft.FontWeight.BOLD, size=fontsize + 2, color=colors['text']),
                ],
                spacing=10
            ),
            ft.Divider(height=1, color=colors['divider']),
            ft.Text(msg, size=fontsize, color=colors['text']),
        ],
        spacing=15
    )

    # Создаем модальное окно
    modal_content = ft.Container(
        width=400,
        padding=20,
        border_radius=10,
        bgcolor=colors['bg'],
        border=ft.border.all(1, colors['divider']),
        content=ft.Column(
            controls=[
                content,
                ft.Row(
                    controls=[
                        ft.TextButton(
                            btn0_name,
                            on_click=lambda _: close_modal(),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=5)
                            )
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END
                )
            ],
            spacing=20
        )
    )

    # Создаем новый overlay
    overlay = ft.Container(
        bgcolor=ft.colors.with_opacity(0.5, ft.colors.BLACK),
        content=ft.Stack(
            controls=[
                ft.Container(on_click=lambda e: close_modal()),  # Клик по затемнению
                ft.Column(
                    controls=[
                        ft.Container(expand=True),
                        ft.Row(
                            controls=[
                                ft.Container(expand=True),
                                modal_content,
                                ft.Container(expand=True),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(expand=True),
                    ],
                    expand=True
                )
            ],
            expand=True
        )
    )

    # Функция закрытия

    def close_modal():
        overlay.visible = False
        page.update()
        if func_theme:
            func_theme(overlay)
        # Не удаляем overlay здесь, чтобы можно было повторно использовать

    # Добавляем overlay на страницу
    page.modal_overlay = overlay
    page.overlay.append(overlay)
    page.update()

    # Автозакрытие
    if time_life > 0:
        def auto_close():
            import time
            time.sleep(time_life)
            if overlay.visible:
                close_modal()

        import threading
        threading.Thread(target=auto_close, daemon=True).start()

    return close_modal  # Возвращаем функцию для ручного закрытия


def dialog_save_file(e: ft.ControlEvent, pathf: str):
    file_name = pathf.split(os.sep)[-1]
    Data: DTCLS.Data_page = e.page.data
    port_api = Data.Data_vars.DOWNLOAD_TEMP_FILE
    download_url = '/'.join(
        ['http:/', f"{Data.Data_srv.ip}:{port_api}", 'hs/mes/download-temp', Data.Data_module.alias, file_name])
    e.page.launch_url(download_url)
    # https://flet.dev/docs/controls/filepicker/#save_file
