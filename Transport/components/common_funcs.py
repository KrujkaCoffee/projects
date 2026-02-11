import copy
import os
from typing import Self  # Только в Python 3.11+
import flet as ft
from typing import List, Dict
import socket
import data_class as DTCLS
from decimal import Decimal
import json as JS
import project_cust_38.Cust_emoji as Cust_emoji
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
                 accuracy: int = 3, comment: str | None = None, data_type: type|str = str, default_val= None):
        if isinstance(data_type, str):
            data_type = self.str_to_type(data_type)
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
        self.default_val = default_val
        self.is_numeric = self.data_type in (float,int)

    def cast_type(self, val: str):

        """
        Преобразует строковое значение в указанный тип.

        Args:
            val (str): Строковое значение для преобразования
            type_val (type): Тип, в который нужно преобразовать значение

        Returns:
            Преобразованное значение указанного типа

        Raises:
            ValueError: Если преобразование невозможно
        """

        type_val = self.data_type

        if val is None or (isinstance(val, str) and val.lower() in ('none', 'null', '')):
            return None

        try:
            if type_val == bool:
                # Обработка булевых значений
                if isinstance(val, str):
                    val_lower = val.lower()
                    if val_lower in ('true', 'yes', '1', 'on'):
                        return True
                    elif val_lower in ('false', 'no', '0', 'off', ''):
                        return False
                return bool(val)

            elif type_val in (list, tuple, set):
                # Для коллекций пытаемся распарсить как JSON или разделить по запятым
                if isinstance(val, str):
                    try:
                        parsed = JS.loads(val)
                        if type_val == list:
                            return list(parsed)
                        elif type_val == tuple:
                            return tuple(parsed)
                        elif type_val == set:
                            return set(parsed)
                    except JS.JSONDecodeError:
                        # Если не JSON, пытаемся разделить по запятым
                        items = [item.strip() for item in val.split(',') if item.strip()]
                        if type_val == list:
                            return items
                        elif type_val == tuple:
                            return tuple(items)
                        elif type_val == set:
                            return set(items)

            elif type_val == dict:
                # Для словаря пытаемся распарсить как JSON
                if isinstance(val, str):
                    return JS.loads(val)

            # Для простых типов используем стандартное преобразование
            if type_val == float and isinstance(val,str):
                val = val.replace(',','.')

            return type_val(val)

        except (ValueError, TypeError) as e:
            raise ValueError(f"Не удалось преобразовать '{val}' в тип {type_val.__name__}: {e}")

    def str_to_type(self, data_type: str) -> type:
        """
        Преобразует строковое название типа в соответствующий тип Python.

        Args:
            data_type: Строка с названием типа (например, 'str', 'int', 'list')

        Returns:
            Соответствующий тип Python

        Raises:
            ValueError: Если тип не распознан
        """
        type_mapping = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'tuple': tuple,
            'dict': dict,
            'set': set,
            'none': type(None),
            'nonetype': type(None),
        }

        normalized_type = data_type.lower().strip()
        if normalized_type in type_mapping:
            return type_mapping[normalized_type]

        raise ValueError(f"Неизвестный тип: {data_type}")



    def __repr__(self):
        return f'cls Cell_description, "{self.__dict__}"'


class _Cell_data():
    def __init__(self, val: int | float | str | None = None, description: Cell_description = Cell_description()):
        if description.default_val == None:
            if description.data_type == str:
                description.default_val = ''
            if description.data_type == int:
                description.default_val = 0
            if description.data_type == float:
                description.default_val = 0.0
            if description.data_type == bool:
                description.default_val = False
        self.val: int | float | str = val
        self.description: Cell_description = description
        self.params_field: Field_params | None = None
        self.parent_row: Row_data | None = None

    # 🔑 ссылки на UI-элементы
        self.container_ref: ft.Ref[ft.Container] | None = None
        self.control_ref: ft.Ref[ft.Control] | None = None
        """
        cell_data.set_value("123")                 # поменять значение
        cell_data.set_bgcolor(ft.Colors.ERROR)     # подсветить ошибку
        cell_data.set_disabled(True)               # сделать поле недоступным
        """
    def on_focus(self,e:ft.ControlEvent):
        self.parent_row.current_cell = self

    def setFocus(self):
        self.control_ref.current.focus()
        self.parent_row.current_cell = self

    # --- Методы управления ячейкой ---
    def set_value_view(self, new_val):
        """Меняет значение в UI и в объекте"""
        self.val = new_val
        if self.control_ref and self.control_ref.current:
            # разные типы контролов (TextField, Dropdown, Text)
            if hasattr(self.control_ref.current, "value"):
                self.control_ref.current.value = str(new_val)
            else:
                self.control_ref.current.text = str(new_val)
            self.control_ref.current.update()

    def set_bgcolor_view(self, color):
        """Меняет фон ячейки"""
        if self.container_ref and self.container_ref.current:
            self.container_ref.current.bgcolor = color
            self.container_ref.current.update()

    def set_disabled_view(self, state: bool = True):
        """Блокирует или разблокирует ввод"""
        if self.control_ref and self.control_ref.current and hasattr(self.control_ref.current, "disabled"):
            self.control_ref.current.disabled = state
            self.control_ref.current.update()

    def set_text_color_view(self, color):
        """Меняет цвет текста в ячейке"""
        if self.control_ref and self.control_ref.current:
            # TextField / Dropdown → color
            if hasattr(self.control_ref.current, "color"):
                self.control_ref.current.color = color
            # Text → тоже есть color
            elif hasattr(self.control_ref.current, "text_style"):
                self.control_ref.current.text_style = ft.TextStyle(color=color)
            self.control_ref.current.update()


    def set_cell_height(self, height: int | None):
        """Меняет высоту ячейки"""
        if self.control_ref and self.control_ref.current:
            self.control_ref.current.height = height
            self.control_ref.current.update()

    def __repr__(self):
        if self.val is None:
            return 'cls Cell_data, val=None'

            # Проверяем тип данных из description
        if self.description.data_type in (int, float, bool):
            return f'cls Cell_data, val={self.val}'
        elif self.description.data_type is str:
            return f'cls Cell_data, val="{self.val}"'
        else:
            # fallback если тип неизвестен
            return f'cls Cell_data, val={repr(self.val)}'


class Row_data():
    def __init__(self,merge:bool=False):
        self.cells: List[_Cell_data] = []
        self.fields: Field_params | None = None
        self.merge:bool=merge
        self.group_name:str|None = None
        self.parent_table_data:Table_data | None = None
        self.table_header = False
        # 🔑 ссылки на UI-элементы
        self.sub_header_control_ref: ft.Ref[ft.Control] | None = None
        self.control_ref: ft.Ref[ft.Control] | None = None
        self.group_cell_text_ref: ft.Ref[ft.Text] | None = None
        self._current_cell: None|_Cell_data = None
    @property
    def current_cell(self):
        return self._current_cell

    @current_cell.setter
    def current_cell(self, val:_Cell_data):
        self._current_cell = val
        self.parent_table_data.current_row = self

    @property
    def is_visible(self):
        # В режиме ленивой генерации строк (lazy groups) строка может ещё не иметь UI-контрола
        if not self.control_ref or not self.control_ref.current:
            return False
        return self.control_ref.current.visible

    def setFocus(self,name_field):
        for cell in self.cells:
            if cell.params_field.name == name_field:
                cell.setFocus()


    def set_visible(self, visible: bool =True):
        """Скрывает или показывает строку через visible"""
        if self.control_ref and self.control_ref.current:
            # ⚡ обновляем только если реально изменилось
            if self.control_ref.current.visible != visible:
                self.control_ref.current.visible = visible

                # помечаем необходимость обновления
                if self.parent_table_data and hasattr(self.parent_table_data, "table_view"):
                    self.parent_table_data.table_view.fl_need_upd = True
    def dict_cells(self) -> Dict[str, _Cell_data]:
        if self.fields == None:
            raise IndexError
        self.fields: list
        rez_dict = dict()
        for i in range(len(self.fields)):
            rez_dict[self.fields[i].name] = self.cells[i]
        return rez_dict

    def apply_new_vals(self, dict_unique_vals: dict, name_field: str):
        if name_field not in [_.params_field.name for _ in self.cells]:
            raise ValueError('name_field отсутствует в params_field')
        uniq_name = [_.val for _ in self.cells if _.params_field.unique][0]
        if uniq_name in dict_unique_vals:
            self.set_new_val(name_field, dict_unique_vals[uniq_name])
        return True

    def get_val(self, name_field):
        for cell in self.cells:
            if cell.params_field.name == name_field:
                return cell.val


    def set_new_val(self, name_field, val):
        for cell in self.cells:
            if cell.params_field.name == name_field:
                cell.set_value_view(val)
                break

    # --- Доп. методы для управления через cell ---
    def set_cell_bgcolor(self, name_field: str, color):
        """Задать цвет фона ячейки"""
        for cell in self.cells:
            if cell.params_field.name == name_field:
                cell.set_bgcolor_view(color)
                break

    def set_cell_disabled(self, name_field: str, state: bool = True):
        """Задать доступность ячейки"""
        for cell in self.cells:
            if cell.params_field.name == name_field:
                cell.set_disabled_view(state)
                break


    def set_cell_text_color(self, name_field: str, color):
        """Задать цвет текста в ячейке"""
        for cell in self.cells:
            if cell.params_field.name == name_field:
                cell.set_text_color_view(color)
                break

    def set_row_height(self, height: int | None):
        """Установить высоту всем ячейкам строки"""
        for cell in self.cells:
            cell.set_cell_height(height)

    def style_cell(self, name_field: str, *, bgcolor=None, text_color=None, disabled=None, row_height=None, cell_height=None):
        """
        Универсальный метод: меняет стиль ячейки.
        Можно задать фон, цвет текста и доступность одной командой.
        """
        if row_height is not None:
            for cell in self.cells:
                cell.set_cell_height(row_height)


        for cell in self.cells:
            if cell.params_field.name == name_field:
                if bgcolor is not None:
                    cell.set_bgcolor_view(bgcolor)
                if text_color is not None:
                    cell.set_text_color_view(text_color)
                if disabled is not None:
                    cell.set_disabled_view(disabled)
                if cell_height is not None:
                    cell.set_cell_height(cell_height)
                break




    def set_default_val(self, name_field):
        for cell in self.cells:
            if cell.params_field.name == name_field:
                cell.set_value_view(cell.description.default_val)
                break

    def append(self, val: float | int | str, desc: Cell_description)->_Cell_data:
        if type(val) is not desc.data_type:
            try:
                if desc.data_type is float:
                    if val is None:
                        val = 0.0
                    else:
                        val = float(val)
                if desc.data_type is int:
                    if val is None:
                        val = 0
                    else:
                        val = int(val)
                if desc.data_type is str:
                    if val is None:
                        val = ''
                    else:
                        val = str(val)
            except:
                raise TypeError
        cell = _Cell_data(val=val, description=desc)
        cell.parent_row = self
        self.cells.append(cell)
        return cell

    def get_cell_unique(self) -> _Cell_data|None:
        for cell in self.cells:
            if cell.params_field.unique == True:
                return cell


    def __repr__(self):
        return f'cls Row_data, "{len(self.cells)}" cells'


class   Table_data():
    def __init__(self, ):
        self.list_fields: List[Field_params] = []
        self._dict_params = dict()
        self.rows: list[Row_data] = []
        self._set_unique_vals = set()
        self.table_view:Table_view|None = None
        self.name = None
        self.current_row:None|Row_data = None

    def calc_next_row(self)->Row_data|None:
        fl = True
        for row in self.rows:
            if not fl and not row.merge and row.is_visible :
                return row
            if row is self.current_row:
                fl = False
    def calc_previous_row(self)->Row_data|None:
        pr_row = None
        for row in self.rows:
            if row is self.current_row:
                return pr_row
            if not row.merge and row.is_visible:
                pr_row = row
    def set_focus_next_row(self):
        row = self.calc_next_row()
        if row is None:
            return
        name_field = self.current_row.current_cell.params_field.name
        row.setFocus(name_field)
    def set_focus_previous_row(self):
        row = self.calc_previous_row()
        if row is None:
            return
        name_field = self.current_row.current_cell.params_field.name
        row.setFocus(name_field)

    def hide_group(self,name:str|None=None,hide=True):

        def add_emoji(text,hide):
            text = text.replace(str(Cust_emoji.EmojiMain.Документы.plus), '')
            text = text.replace(str(Cust_emoji.EmojiMain.Документы.minus), '')
            if hide:
                return f'{Cust_emoji.EmojiMain.Документы.plus}{text}'
            else:
                return  f'{Cust_emoji.EmojiMain.Документы.minus}{text}'

        for row in self.rows:
            if row.table_header:
                text = row.group_cell_text_ref.current.value
                row.group_cell_text_ref.current.value = add_emoji(text, hide)
                continue
            if row.group_name == name or name == None:
                if row.merge:
                    if row.sub_header_control_ref:
                        row.sub_header_control_ref.current.visible = not hide

                    text = row.group_cell_text_ref.current.value
                    row.group_cell_text_ref.current.value = add_emoji(text,hide)

                else:
                    row.set_visible(not hide)


    def toggle_group(self,name:str|None=None):
        """Переключает раскрытие группы.
        Если таблица отрисована через Table_view с lazy_groups, делегируем управление ей
        (это позволяет вставлять/убирать строки вместо массового visible).
        """
        if (self.table_view is not None and hasattr(self.table_view, 'toggle_group_ui') and getattr(self.table_view, 'lazy_groups', False)):
            # UI-таблица сама решает, как эффективно раскрывать группы
            self.table_view.toggle_group_ui(name)
            return

        # Фолбэк: старое поведение через visible
        if self._is_all_rows_ih_group_visible(name):
            self.hide_group(name)
        else:
            self.hide_group(name,False)

    def _is_all_rows_ih_group_visible(self,name:str|None=None):
        for row in self.rows:
            if not row.merge:
                if row.group_name == name or name == None:
                    if not row.control_ref.current.visible:
                        return False
        return True

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
        if not self._is_unique_determine():
            raise InvalidUniqueError('Ошибка уникальности Field_params в Table_data')

    def get_param_by_name(self, name: str) -> Field_params:
        return self._dict_params[name]

    def get_unique_field_name(self):
        for field in self.list_fields:
            if field.unique:
                return field.hidden

    def get_row_by_unique_name(self, name_row:str)-> Row_data|None:
        for row in self.rows:
            if row.get_cell_unique().val == name_row:
                return row


    def _is_unique_determine(self) -> bool:
        count = sum([_.unique for _ in self.list_fields])
        if count == 1:
            return True
        return False

    def add_row(self, row: Row_data):
        if len(row.cells) != len(self.list_fields):
            raise IndexError

        for i, cell in enumerate(row.cells):
            cell.params_field = self.list_fields[i]

            if cell.params_field.unique:
                if cell.val in self._set_unique_vals:
                    raise ValueError(f'Ошибка уникальности значения строки `{cell.val}`')
                else:
                    self._set_unique_vals.add(cell.val)
        row.parent_table_data = self
        row.fields = self.list_fields
        self.rows.append(row)

    def add_group(self,unic_name:str,name_group:str):
        row = Row_data(merge=True)
        name = f'{unic_name}_{name_group}'
        row.group_name = name_group
        added = False
        for f in self.list_fields:
            if f.unique:
                cell = row.append(name,Cell_description())
            elif  not f.hidden and not added:
                cell =row.append(name_group, Cell_description())
                added = True
            else:
                cell =row.append('', Cell_description())
            cell.params_field = f
        row.parent_table_data = self
        row.fields = self.list_fields
        self.rows.append(row)


    def add_table_name(self,unic_name:str,table_name:str):

        for row in self.rows:
            if row.table_header:
                raise InvalidUniqueError(f'table_header already exists in TableData')

        row = Row_data(merge=True)
        name = f'{unic_name}_{table_name}'
        row.group_name = table_name
        added = False
        for f in self.list_fields:
            if f.unique:
                cell = row.append(name,Cell_description())
            elif  not f.hidden and not added:
                cell =row.append(table_name, Cell_description())
                added = True
            else:
                cell =row.append('', Cell_description())
            cell.params_field = f
        row.parent_table_data = self
        row.fields = self.list_fields
        row.table_header = True
        self.rows.insert(0,row)
        self.name = table_name

    # --- Новый метод ---
    def set_all_cells_disabled(self, disabled: bool = True):
        """
        Делает все ячейки таблицы доступными / недоступными
        через Row_data.set_cell_disabled().
        """

        if not self.rows:
            return

        for row in self.rows:   # проходим по Row_data
            for cell in row.cells:
                if cell.params_field.editable: # все ячейки внутри Row_data
                    row.set_cell_disabled(cell.params_field.name, disabled)
                    fl_pass = False
                    if cell.control_ref and cell.control_ref.current:
                        if hasattr(cell.control_ref.current, "color"):
                            if cell.control_ref.current.color == ft.Colors.TRANSPARENT:
                                fl_pass = True
                    if not fl_pass:
                        if disabled:
                            row.set_cell_text_color(cell.params_field.name,ft.Colors.SECONDARY)
                        else:
                            row.set_cell_text_color(cell.params_field.name,ft.Colors.ON_SURFACE)
        # --- Новый метод ---

    def sync_ui_to_data(self,field_name):
        """
        Копирует значения из UI (DataTable) в модель Table_data.
        Использует control_ref каждой ячейки (_Cell_data).
        """
        DTCLS.Data_page.Data_module.status_bar.set_text()
        if not self.rows:
            return
        for row in self.rows:  # Row_data
            for cell in row.cells:  # _Cell_data
                if cell.control_ref and cell.control_ref.current and cell.params_field.name == field_name:
                    ctrl = cell.control_ref.current
                    # Определяем значение в зависимости от типа контрола
                    if hasattr(ctrl, "value"):
                        val = ctrl.value
                    elif hasattr(ctrl, "text"):
                        val = ctrl.text
                    else:
                        val = None
                    try:
                        type_val = cell.description.cast_type(val)
                    except (ValueError, TypeError) as e:
                        DTCLS.Data_page.Data_module.status_bar.set_text(f'{Cust_emoji.EmojiMain.Статусы.alert} Ошибка в строке `{cell.parent_row.get_val("header")}`: {e}')
                        DTCLS.Data_page.page.update()
                        return
                    cell.val = cell.description.cast_type(val)
        return True
    def to_dict_by_unique(self) -> dict:
        """
        Преобразует данные таблицы в словарь:
        { уникальное_значение: {имя_поля: значение, ...}, ... }
        """
        result = {}
        for row in self.rows:
            row_dict = row.dict_cells()
            # ищем уникальное поле
            unique_cells = [c for c in row.cells if c.params_field and c.params_field.unique]
            if not unique_cells:
                raise ValueError("В строке нет уникального поля (unique=True)")

            unique_val = unique_cells[0].val
            result[unique_val] = {name: cell.val for name, cell in row_dict.items()}

        return result

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

class Table_view(ft.DataTable):
    def __init__(self,
            table_input_data: Table_data,
            bold_header=True,
            fnc_onchange=None,
            ref: ft.Ref[ft.DataTable] = None,
            selectedRows=False,
            selectedRowsfnc=None,
            fnc_on_click = None,
            lazy_groups: bool = False,
            single_group_expand: bool = False,


    ):
        print('INIT Table_view')
        self.table_data:Table_data = table_input_data
        self.lazy_groups: bool = bool(lazy_groups)
        self.single_group_expand: bool = bool(single_group_expand)
        # Ленивая логика раскрытия групп (решение 1) + режим "только одна раскрытая" (решение 2)
        self._expanded_groups: set[str] = set()
        self._group_order: list[str] = []
        self._group_rows_data: dict[str, list[Row_data]] = {}
        self._ui_table_header_row: ft.DataRow | None = None
        self._ui_group_header_rows: dict[str, ft.DataRow] = {}
        self._ui_subheader_rows: dict[str, ft.DataRow] = {}
        self._ui_data_rows_cache: dict[str, list[ft.DataRow]] = {}
        self._rowdata_by_group: dict[str, Row_data] = {}

        row_height = None
        def header_gen(obj_type=ft.DataColumn, empty=False) -> list:
            cells_columns = []
            fl_left_bord = False
            for field in table_input_data.list_fields:
                visible = not field.hidden
                left_bord = ft.Colors.TRANSPARENT
                if not fl_left_bord and visible:
                    fl_left_bord = True
                    left_bord = ft.Colors.OUTLINE_VARIANT

                header = field.header
                expand = True
                width = field.width
                if not visible:
                    width = 0
                    expand = False
                height = None
                content = ft.Text(header, weight=font_weight)
                border = ft.border.only(ft.BorderSide(1, left_bord),
                                        ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                        ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                        ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT))
                if field.unique:
                    empty = False
                if empty:
                    width = 0
                    height = 0
                    border = None
                    expand = False

                if header:
                    input_data = ft.Container(
                        content,
                        bgcolor=ft.Colors.TRANSPARENT,  # Цвет контейнера для акцента
                        padding=ft.padding.all(6),  # Отступы со всех сторон
                        border=border,
                        expand=expand,  # 🔑 растянуть по высоте строки
                        alignment=ft.Alignment.CENTER_LEFT,  # чтобы текст красиво встал
                        width=width,
                        height=height)

                    if obj_type == ft.DataColumn:
                        elem = ft.DataColumn(input_data, visible=visible)
                    else:
                        elem = ft.DataCell(input_data, visible=visible)
                    cells_columns.append(elem)
            return cells_columns

        def add_group(row_data,content_text,list_cells):
            if fnc_on_click:
                content_text = f'{content_text}'
            content_outed = False
            left_padding = 16
            if row_data.table_header:
                left_padding /=2
            for cell_data in row_data.cells:
                field = cell_data.params_field
                visible = True
                if not field.hidden and not content_outed:

                    group_cell_text_ref = ft.Ref[ft.Text]()

                    row_data.group_cell_text_ref =  group_cell_text_ref

                    merged_cell = ft.DataCell(
                        content=ft.Container(
                            content=ft.Text(
                                content_text,
                                no_wrap=False,
                                text_align=ft.TextAlign.LEFT,
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                color=ft.Colors.ON_SURFACE,# Автоматический цвет текста
                                ref=group_cell_text_ref
                            ),
                            height=row_height,
                            on_click=fnc_on_click,
                            data={"cell": cell_data},  # 🔑 привязка

                            alignment=ft.Alignment.CENTER_LEFT,

                            bgcolor=ft.Colors.TRANSPARENT,  # Цвет контейнера для акцента
                            padding=ft.padding.only(left_padding,4,4,4), # Отступы со всех сторон


                            border=ft.border.only(ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ),

                            expand=True,
                            width=field.width
                            # border_radius=ft.border_radius.all(4)
                        ),
                        visible=visible
                    )
                    list_cells.append(merged_cell)
                    content_outed = True
                else:
                    # Пустые ячейки с прозрачным фоном
                    expand = True
                    width = 0
                    if field.hidden:
                        width = 0
                        expand = False
                        visible = False
                    empty_cell = ft.DataCell(

                        content=ft.Container(

                            content=ft.Text(
                                '',
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                color=ft.Colors.TRANSPARENT  # Автоматический цвет текста
                            ),
                            height=row_height,
                            bgcolor=ft.Colors.TRANSPARENT,  # Прозрачный фон
                            border=ft.border.only(ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ),
                            expand=expand,
                            width=width
                        )
                        ,
                        visible=visible
                    )
                    list_cells.append(empty_cell)
            return list_cells

        font_weight = ft.FontWeight.NORMAL
        if bold_header:
            font_weight = ft.FontWeight.BOLD

        # --- Подготовка строителя обычной строки (используется в lazy-режиме при раскрытии группы) ---
        def _build_data_row(row_data: Row_data) -> ft.DataRow:
            list_cells: list[ft.DataCell] = []

            fl_left_bord = False
            for cell_data in row_data.cells:
                width = cell_data.params_field.width
                visible = True
                expand = True
                if cell_data.params_field.hidden:
                    width = 0
                    visible = False
                    expand = False

                if cell_data.params_field.editable:
                    value_cell = create_value_cell(
                        cell_data,
                        fnc_onchange=fnc_onchange,
                        width=cell_data.params_field.width,
                        visible=visible,
                        height=row_height
                    )
                    list_cells.append(value_cell)
                else:
                    text_val = cell_data.val
                    if cell_data.description.is_numeric:
                        try:
                            text_val = str(round(text_val, cell_data.description.accuracy))
                        except Exception:
                            text_val = str(text_val)

                    left_bord = ft.Colors.TRANSPARENT
                    if not fl_left_bord and visible:
                        fl_left_bord = True
                        left_bord = ft.Colors.OUTLINE_VARIANT

                    container_ref = ft.Ref[ft.Container]()
                    control_ref = ft.Ref[ft.Control]()
                    cell_data.container_ref = container_ref
                    cell_data.control_ref = control_ref

                    list_cells.append(
                        ft.DataCell(
                            content=ft.Container(
                                ref=container_ref,
                                content=ft.Text(
                                    str(text_val),
                                    ref=control_ref,
                                    no_wrap=False,
                                ),
                                height=row_height,
                                border=ft.border.only(
                                    ft.BorderSide(1, left_bord),
                                    ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                    ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                    ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                ),
                                padding=ft.padding.all(4),
                                width=width,
                                expand=expand,
                                alignment=ft.Alignment.CENTER_LEFT,
                            ),
                            visible=visible,
                        )
                    )

            row_control_ref = ft.Ref[ft.Control]()
            row_data.control_ref = row_control_ref

            on_select_changed = None
            data = None
            if selectedRows and not row_data.merge:
                on_select_changed = selectedRowsfnc
                data = {"row": row_data}

            return ft.DataRow(
                ref=row_control_ref,
                cells=list_cells,
                on_select_change=on_select_changed,
                data=data,
            )

        # Сохраняем, чтобы использовать при раскрытии групп (без повторного копипаста кода)
        self._build_data_row = _build_data_row

        def _build_subheader_row(row_data: Row_data) -> ft.DataRow:
            control_ref = ft.Ref[ft.Control]()
            row_data.sub_header_control_ref = control_ref
            return ft.DataRow(cells=header_gen(ft.DataCell), ref=control_ref)

        self._build_subheader_row = _build_subheader_row

        # -----------------------------
        # Построение строк таблицы
        # -----------------------------
        if self.lazy_groups:
            fl_were_header = False
            rows = []

            # 1) Собираем данные по группам, но UI строим ТОЛЬКО для заголовков групп
            for row_data in table_input_data.rows:
                if row_data.merge:
                    # Заголовок группы / таблицы
                    content_list = []
                    for cell_data in row_data.cells:
                        if cell_data.val and str(cell_data.val).strip() != '' and not cell_data.params_field.hidden:
                            content_list.append(str(cell_data.val))
                    content_text = ' '.join(content_list)

                    # По умолчанию все группы свернуты (плюсик)
                    content_text = self._emoji_group_text(content_text, expanded=False)

                    list_cells: list[ft.DataCell] = []
                    list_cells = add_group(row_data, content_text, list_cells)

                    row_control_ref = ft.Ref[ft.Control]()
                    row_data.control_ref = row_control_ref

                    ui_row = ft.DataRow(ref=row_control_ref, cells=list_cells)

                    if row_data.table_header:
                        self._ui_table_header_row = ui_row
                    else:
                        gname = row_data.group_name
                        if gname is None:
                            continue
                        self._group_order.append(gname)
                        self._rowdata_by_group[gname] = row_data
                        self._ui_group_header_rows[gname] = ui_row
                        fl_were_header = True
                else:
                    # Обычная строка: пока не создаем UI-строку, только складируем модель
                    gname = row_data.group_name
                    if gname is None:
                        gname = ""
                    self._group_rows_data.setdefault(gname, []).append(row_data)

            # 2) Начальное отображение: заголовок таблицы (если есть) + заголовки групп
            if self._ui_table_header_row is not None:
                rows.append(self._ui_table_header_row)
            for gname in self._group_order:
                rows.append(self._ui_group_header_rows[gname])

        else:
            fl_were_header = False
            rows = []
            for i, row_data in enumerate(table_input_data.rows):
                list_cells = []
                fl_need_header = False
                if row_data.merge:#Заголовок группы


                    content_list = []
                    # Ищем содержимое
                    for cell_data in row_data.cells:
                        if cell_data.val and str(cell_data.val).strip() != '' and not cell_data.params_field.hidden:
                            content_list.append(str(cell_data.val))

                    content_text = ' '.join(content_list)
                    fl_need_header = True
                    list_cells = add_group(row_data,content_text,list_cells)
                    if row_data.table_header:
                        fl_need_header = False

                else:# Обычная строка


                    fl_left_bord = False
                    for cell_data in row_data.cells:
                        width = cell_data.params_field.width
                        visible = True
                        expand = True
                        if cell_data.params_field.hidden:
                            width = 0
                            visible = False
                            expand = False

                        if cell_data.params_field.editable:
                            value_cell = create_value_cell(
                                cell_data,
                                fnc_onchange=fnc_onchange,
                                width=cell_data.params_field.width,
                                visible=visible,
                                height=row_height
                            )
                            list_cells.append(value_cell)
                        else:
                            text = cell_data.val
                            if cell_data.description.is_numeric:
                                text = str(round(text, cell_data.description.accuracy))

                            left_bord = ft.Colors.TRANSPARENT
                            if not fl_left_bord and visible:
                                fl_left_bord = True
                                left_bord = ft.Colors.OUTLINE_VARIANT

                            # 🔑 создаём рефы
                            container_ref = ft.Ref[ft.Container]()
                            control_ref = ft.Ref[ft.Control]()

                            # Обновляем cell_data, чтобы хранить ссылки
                            cell_data.container_ref = container_ref
                            cell_data.control_ref = control_ref

                            list_cells.append(
                                ft.DataCell(
                                    content=ft.Container(
                                        ref = container_ref,
                                        content=ft.Text(
                                            str(text),
                                            ref=control_ref,
                                            no_wrap=False,
                                        ),
                                        height=row_height,
                                        border=ft.border.only(ft.BorderSide(1, left_bord),
                                                              ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                                              ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                                              ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                                              ),
                                        padding=ft.padding.all(4),  # Отступы со всех сторон
                                        width=width,
                                        expand=expand,  # 🔑 растянуть по высоте строки
                                        alignment=ft.Alignment.CENTER_LEFT,  # чтобы текст красиво встал
                                    ),
                                    visible=visible,

                                )
                            )

                # 🔑 создаём рефы

                control_ref = ft.Ref[ft.Control]()

                # Обновляем cell_data, чтобы хранить ссылки

                row_data.control_ref = control_ref

                on_select_changed=None
                data = None

                if selectedRows and not row_data.merge:
                    on_select_changed = selectedRowsfnc
                    data = {"row": row_data}

                rows.append(ft.DataRow(
                        ref=control_ref,
                        cells=list_cells,
                        on_select_change=on_select_changed,
                        data=data,

                    ))

                if fl_need_header:
                    if row_data.merge:
                        # 🔑 создаём рефы

                        control_ref = ft.Ref[ft.Control]()

                        row_data.sub_header_control_ref = control_ref
                        rows.append(ft.DataRow(cells=header_gen(ft.DataCell),ref=control_ref,
                                               ))
                    fl_were_header = True


        heading_row_height = None
        if fl_were_header:
            heading_row_height = 0
        # [ [ j.visible for j in h.cells] for h in rows]
        # [ [ j.content.height for j in h.cells] for h in rows]
        super().__init__(
            columns=header_gen(empty=fl_were_header),
            data_row_min_height=0,
            heading_row_height=heading_row_height,
            rows=rows,
            border=ft.border.only(ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                  ft.BorderSide(1, ft.Colors.TRANSPARENT)),
            vertical_lines=ft.border.BorderSide(0, color=ft.Colors.TRANSPARENT),
            horizontal_lines=ft.border.BorderSide(0, color=ft.Colors.TRANSPARENT),  # Убираем горизонтальные линии
            column_spacing=0,  # Убираем промежутки между колонками
            horizontal_margin=0,
            divider_thickness=0.000001,  # 🔑 убираем горизонтальные разделители строк
            data_row_color=ft.Colors.SURFACE,  # 🔑 единый цвет для всех строк
            bgcolor=ft.Colors.SURFACE,
            ref=ref,
            expand=False,



        )
        table_input_data.table_view = self
        self.fl_need_upd: bool = False
        if table_input_data.name and fnc_on_click and (not self.lazy_groups):
            table_input_data.toggle_group(None)
        # В lazy-режиме группы уже стартуют свернутыми, ничего делать не нужно.
        DTCLS.Data_page.page.on_keyboard_event = self.on_key


    def on_key(self, e: ft.KeyboardEvent):
        #print("key:", e.key)
        #print(f'current_row {self.table_data.current_row.dict_cells()}')
        if e.key == 'Arrow Down':
            self.table_data.set_focus_next_row()
        if e.key == 'Arrow Up':
            self.table_data.set_focus_previous_row()





    # -----------------------------
    # Lazy groups (решение 1) + Single expand (решение 2)
    # -----------------------------
    def _strip_group_emoji(self, text: str) -> str:
        plus = str(Cust_emoji.EmojiMain.Документы.plus)
        minus = str(Cust_emoji.EmojiMain.Документы.minus)
        if text is None:
            return ""
        return str(text).replace(plus, "").replace(minus, "").strip()

    def _emoji_group_text(self, text: str, *, expanded: bool) -> str:
        base = self._strip_group_emoji(text)
        mark = str(Cust_emoji.EmojiMain.Документы.minus) if expanded else str(Cust_emoji.EmojiMain.Документы.plus)
        return f"{mark}{base}"

    def _set_group_header_expanded(self, group_name: str, expanded: bool):
        rd = self._rowdata_by_group.get(group_name)
        if rd is None:
            return
        if rd.group_cell_text_ref and rd.group_cell_text_ref.current:
            rd.group_cell_text_ref.current.value = self._emoji_group_text(rd.group_cell_text_ref.current.value, expanded=expanded)

    def _set_table_header_expanded(self, expanded: bool):
        # Находим row_data с table_header=True и обновляем его эмодзи
        for rd in self.table_data.rows:
            if getattr(rd, "table_header", False):
                if rd.group_cell_text_ref and rd.group_cell_text_ref.current:
                    rd.group_cell_text_ref.current.value = self._emoji_group_text(rd.group_cell_text_ref.current.value, expanded=expanded)
                break

    def _ensure_group_rows_cached(self, group_name: str):
        if group_name in self._ui_data_rows_cache:
            return
        rows_data = self._group_rows_data.get(group_name, [])
        self._ui_data_rows_cache[group_name] = [self._build_data_row(rd) for rd in rows_data]

    def _ensure_subheader_cached(self, group_name: str):
        if group_name in self._ui_subheader_rows:
            return
        rd = self._rowdata_by_group.get(group_name)
        if rd is None:
            return
        self._ui_subheader_rows[group_name] = self._build_subheader_row(rd)

    def _rebuild_lazy_rows(self):
        """Пересобирает список DataRow одним присваиванием (дешевле, чем дергать visible у тысяч строк)."""
        new_rows: list[ft.DataRow] = []
        if self._ui_table_header_row is not None:
            new_rows.append(self._ui_table_header_row)

        for g in self._group_order:
            new_rows.append(self._ui_group_header_rows[g])
            if g in self._expanded_groups:
                self._ensure_subheader_cached(g)
                self._ensure_group_rows_cached(g)
                sub = self._ui_subheader_rows.get(g)
                if sub is not None:
                    new_rows.append(sub)
                new_rows.extend(self._ui_data_rows_cache.get(g, []))

        self.rows.clear()
        self.rows.extend(new_rows)
        try:
            self.update()
        except Exception:
            pass

    def toggle_group_ui(self, name: str | None = None):
        """Эффективное раскрытие групп.
        - Решение 1: строки группы вставляются только при раскрытии (lazy).
        - Решение 2: при single_group_expand=True раскрыта может быть только одна группа.
        """
        if not self.lazy_groups:
            return  # в обычном режиме оставляем старую логику Table_data.hide_group()

        # Клик по заголовку таблицы: в single-режиме делаем только "свернуть всё"
        if name is None:
            if self._expanded_groups:
                for g in list(self._expanded_groups):
                    self._set_group_header_expanded(g, False)
                self._expanded_groups.clear()
                self._set_table_header_expanded(False)
                self._rebuild_lazy_rows()
            else:
                # Если single_group_expand выключен — можно раскрыть всё
                if not self.single_group_expand:
                    for g in self._group_order:
                        self._expanded_groups.add(g)
                        self._set_group_header_expanded(g, True)
                    self._set_table_header_expanded(True)
                    self._rebuild_lazy_rows()
            return

        group_name = str(name)

        # Свернуть, если уже раскрыто
        if group_name in self._expanded_groups:
            self._expanded_groups.discard(group_name)
            self._set_group_header_expanded(group_name, False)
            self._set_table_header_expanded(bool(self._expanded_groups))
            self._rebuild_lazy_rows()
            return

        # Раскрыть
        if self.single_group_expand and self._expanded_groups:
            for g in list(self._expanded_groups):
                self._set_group_header_expanded(g, False)
            self._expanded_groups.clear()

        self._expanded_groups.add(group_name)
        self._set_group_header_expanded(group_name, True)
        self._set_table_header_expanded(True)
        self._rebuild_lazy_rows()


    def update_view(self):
        """Обновляет отображение и сбрасывает флаг обновления.
        Важно: обновляем именно таблицу, а не всю страницу.
        """
        if self.fl_need_upd:
            try:
                self.update()
            except Exception:
                # Если таблица ещё не добавлена на страницу, update() может упасть
                pass
        self.fl_need_upd = False

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


def create_value_cell(cell_data: _Cell_data, visible: bool = True, width=None, height=None,
                      fnc_onchange=None
                      ) -> ft.DataCell:
    width = 100 if width is None else width

    width = 0 if not visible else width
    expand = False if width == 0 else True
    height = None if height is None else height
    # """Создает ячейку значения в зависимости от типа параметра"""
    val = cell_data.val


    # 🔑 создаём рефы
    container_ref = ft.Ref[ft.Container]()
    control_ref = ft.Ref[ft.Control]()

    # Обновляем cell_data, чтобы хранить ссылки
    cell_data.container_ref = container_ref
    cell_data.control_ref = control_ref


    # if fnc_onchange:
    #    fnc_on_change = lambda cell_data: fnc_onchange(cell_data)
    fnc_on_change = fnc_onchange
    if isinstance(cell_data.description.min_max_list, list):
        # Выпадающий список для параметров с множеством вариантов
        options = [ft.dropdown.Option(str(x)) for x in cell_data.description.min_max_list]

        return ft.DataCell(
                    ft.Container(
                        ref=container_ref,
                        bgcolor=ft.Colors.SECONDARY_CONTAINER,
                        margin=ft.margin.all(1),          # просвет для бордера
                        padding=ft.padding.symmetric(horizontal=12),  # имитируем padding как у TextField
                        content=ft.Dropdown(
                            ref=control_ref,
                            options=options,
                            value=str(val),
                            data={"cell": cell_data},  # 🔑 привязка
                            on_select=fnc_on_change,
                            on_focus=cell_data.on_focus,
                            tooltip=cell_data.description.comment,
                            border=ft.InputBorder.NONE,   # убираем рамку
                            width=width,
                            bgcolor=ft.Colors.SECONDARY_CONTAINER                  # фон контейнером
                        ),
                        width=width,
                        height=height
                    ),
                    visible=True,
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
                    ref=control_ref,
                    value=value,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    input_filter=ft.InputFilter(r'^\d*[.,]?\d*$'),  # Только числа
                    on_change=fnc_on_change,
                    on_focus=cell_data.on_focus,
                    tooltip=tooltip,
                    border=ft.InputBorder.NONE,
                    width=width,
                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                    data={"cell": cell_data},  # 🔑 привязка
                ),
                ref=container_ref,
                height=height,
                width=width,  # Дублируем ширину у Container
                margin=ft.margin.all(1),  # 🔑 оставить просвет для бордера


            )
            , visible=visible
        )
    else:
        # Простое текстовое поле
        return ft.DataCell(
            ft.Container(
                ft.TextField(
                    ref=control_ref,
                    value=str(val),
                    on_change=fnc_on_change,
                    on_focus=cell_data.on_focus,
                    border=ft.InputBorder.NONE,
                    tooltip=cell_data.description.comment,
                    width=width,  # Теперь должно работать
                    height= height,
                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                    data={"cell": cell_data},  # 🔑 привязка
                ),
                ref=container_ref,
                height=height,
                width=width,  # Дублируем ширину у Container
                margin=ft.margin.all(1),  # 🔑 оставить просвет для бордера

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
    def selectedRowsfnc_dflt(e: ft.ControlEvent, add_fnc=None):
        page: ft.Page = e.page
        row_index = e.control.data["row_index"]
        row_data = table_input_data.rows[row_index]
        if add_fnc:
            add_fnc(e, row_index, row_data)

    def header_gen(obj_type=ft.DataColumn, empty=False) -> list:
        cells_columns = []
        fl_left_bord = False
        for field in table_input_data.list_fields:
            visible = not field.hidden
            left_bord = ft.Colors.TRANSPARENT
            if not fl_left_bord and visible:
                fl_left_bord = True
                left_bord = ft.Colors.OUTLINE_VARIANT

            header = field.header

            width = field.width
            height = None
            content = ft.Text(header, weight=font_weight)
            border = ft.border.only(ft.BorderSide(1, left_bord),
                                    ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                    ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                    ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT))
            if empty:
                width = 0
                content = None
                height = 0
                border = None
            if header:
                input_data = ft.Container(
                    content,
                    bgcolor=ft.Colors.TRANSPARENT,  # Цвет контейнера для акцента
                    padding=ft.padding.all(6),  # Отступы со всех сторон
                    border=border,
                    expand=True,  # 🔑 растянуть по высоте строки
                    alignment=ft.alignment.center_left,  # чтобы текст красиво встал
                    width=width,
                    height=height)

                if obj_type == ft.DataColumn:
                    elem = ft.DataColumn(input_data, visible=visible)
                else:
                    elem = ft.DataCell(input_data, visible=visible)
                cells_columns.append(elem)
        return cells_columns

    font_weight = ft.FontWeight.NORMAL
    if bold_header:
        font_weight = ft.FontWeight.BOLD

    # Подсчитываем количество видимых колонок
    visible_columns_count = sum(1 for field in table_input_data.list_fields if not field.hidden)
    fl_were_header = False
    rows = []
    for i, row_data in enumerate(table_input_data.rows):
        list_cells = []
        fl_need_header = False
        if row_data.merge:
            content_found = False
            for j in range(visible_columns_count):
                if j == 0:
                    # Ищем содержимое
                    content_text = ""
                    for cell_data in row_data.cells:
                        if cell_data.val and str(cell_data.val).strip() != '' and not cell_data.params_field.hidden:
                            content_text = str(cell_data.val)
                            if cell_data.description.data_type is float:
                                content_text = str(
                                    Decimal(str(round(cell_data.val, cell_data.description.accuracy))))
                            break
                    fl_need_header = True

                    merged_cell = ft.DataCell(
                        content=ft.Container(
                            content=ft.Text(
                                content_text,
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                color=ft.Colors.ON_SURFACE  # Автоматический цвет текста
                            ),
                            alignment=ft.alignment.center,
                            bgcolor=ft.Colors.TRANSPARENT,  # Цвет контейнера для акцента
                            padding=12,
                            border=ft.border.only(ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ),

                            expand=True,
                            # border_radius=ft.border_radius.all(4)
                        )
                    )
                    list_cells.append(merged_cell)
                    content_found = True
                else:
                    # Пустые ячейки с прозрачным фоном
                    empty_cell = ft.DataCell(
                        content=ft.Container(
                            bgcolor=ft.Colors.TRANSPARENT,  # Прозрачный фон
                            border=ft.border.only(ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ft.BorderSide(1, ft.Colors.TRANSPARENT),
                                                  ),
                            expand=True
                        )
                    )
                    list_cells.append(empty_cell)

            if not content_found:
                # Запасной вариант
                for j in range(visible_columns_count):
                    if j == 0:
                        list_cells.append(ft.DataCell(ft.Text("Группа", weight=ft.FontWeight.BOLD)))
                    else:
                        list_cells.append(ft.DataCell(ft.Text("")))

        else:
            # Обычная строка
            visible_cells = [cell for cell in row_data.cells if not cell.params_field.hidden]
            fl_left_bord = False
            for cell_data in visible_cells:
                visible = True
                if cell_data.params_field.editable:
                    value_cell = create_value_cell(
                        cell_data,
                        fnc_onchange=fnc_onchange,
                        width=cell_data.params_field.width,
                        visible=visible,
                        row_data=row_data,
                        table_input_data=table_input_data,
                        ref_table=ref
                    )
                    list_cells.append(value_cell)
                else:
                    text = cell_data.val
                    if cell_data.description.data_type is float:
                        text = Decimal(str(round(text, cell_data.description.accuracy)))

                    left_bord = ft.Colors.TRANSPARENT
                    if not fl_left_bord and visible:
                        fl_left_bord = True
                        left_bord = ft.Colors.OUTLINE_VARIANT

                    list_cells.append(
                        ft.DataCell(
                            content=ft.Container(
                                content=ft.Text(
                                    str(text),
                                    no_wrap=False,
                                ),
                                border=ft.border.only(ft.BorderSide(1, left_bord),
                                                      ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                                      ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                                      ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                                                      ),
                                padding=ft.padding.all(4),  # Отступы со всех сторон
                                width=cell_data.params_field.width,
                                expand=True,  # 🔑 растянуть по высоте строки
                                alignment=ft.alignment.center_left,  # чтобы текст красиво встал
                            ),
                            visible=visible,

                        )
                    )

        # Выравниваем количество ячеек
        while len(list_cells) < visible_columns_count:
            list_cells.append(ft.DataCell(content=ft.Text(""), visible=True))
        list_cells = list_cells[:visible_columns_count]

        if selectedRows and not row_data.merge:
            rows.append(ft.DataRow(
                cells=list_cells,
                on_select_changed=lambda e, idx=i: selectedRowsfnc_dflt(e, selectedRowsfnc),
                data={"row_index": i}
            ))
        else:
            rows.append(ft.DataRow(cells=list_cells))

        if fl_need_header:
            if row_data.merge:
                rows.append(ft.DataRow(cells=header_gen(ft.DataCell)))
            fl_were_header = True
    heading_row_height = None
    if fl_were_header:
        heading_row_height = 0
    new_table = ft.DataTable(
        columns=header_gen(empty=fl_were_header),
        heading_row_height=heading_row_height,
        rows=rows,
        border=ft.border.only(ft.BorderSide(1, ft.Colors.TRANSPARENT),
                              ft.BorderSide(1, ft.Colors.TRANSPARENT),
                              ft.BorderSide(1, ft.Colors.TRANSPARENT),
                              ft.BorderSide(1, ft.Colors.TRANSPARENT)),
        vertical_lines=ft.border.BorderSide(0, color=ft.Colors.TRANSPARENT),
        horizontal_lines=ft.border.BorderSide(0, color=ft.Colors.TRANSPARENT),  # Убираем горизонтальные линии
        column_spacing=0,  # Убираем промежутки между колонками
        horizontal_margin=0,
        divider_thickness=0.000001,  # 🔑 убираем горизонтальные разделители строк
        data_row_color=ft.Colors.SURFACE,  # 🔑 единый цвет для всех строк
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
        obj = col.label
        if isinstance(obj, ft.Container):
            obj = obj.content
        if isinstance(obj, ft.Text):
            column_names.append(obj.value)
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
        "QUESTION": ft.Icons.HELP_OUTLINE,
        "INFO": ft.Icons.INFO_OUTLINE,
        "WARNING": ft.Icons.WARNING_AMBER,
        "CRITICAL": ft.Icons.ERROR_OUTLINE
    }

    if icon_str:
        icon = icon_str.upper()
    selected_icon = icon_mapping.get(icon.upper(), ft.Icons.INFO_OUTLINE)

    # Определяем цвета
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    colors = {
        'bg': ft.Colors.SURFACE_VARIANT if is_dark else ft.Colors.WHITE,
        'text': ft.Colors.ON_SURFACE_VARIANT if is_dark else ft.Colors.BLACK,
        'divider': ft.Colors.OUTLINE_VARIANT,
        'icon': ft.Colors.BLUE_400 if is_dark else ft.Colors.BLUE_600
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
        bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
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
    print(pathf)
    e.page.launch_url(download_url)
    # https://flet.dev/docs/controls/filepicker/#save_file
