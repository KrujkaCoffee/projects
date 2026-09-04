import typing

if typing.TYPE_CHECKING:
    from PyQt5 import QtWidgets
    from project_cust_38.Cust_Qt import InteractiveLabelInstance

ParentTreeItemType = typing.TypeVar("ParentTreeItemType")
DroppedTreeItemType = typing.TypeVar("DroppedTreeItemType")

class ExtTreeWidget:
    """Расширенная версия QtWidgets.QTreeWidget
        --------------------------------------------------------------------------------------
        Параметры:
            @old_tree_instance: Заменяемый объект QTreeWidget
            @ui_instance: Объект self.ui на котором был инициализирован прежний QTreeWidget
        Структура классов с открытым интерфейсом
            - ExtTreeWidget  Класс дерева
            -- ExtTreeWidgetItem Класс строки
            --- ExtTreeWidgetCell Класс ячейки в строке
        Пример:
            self.ui.tree_base_tree = ExtTreeWidget(old_tree_instance=self.ui.tree_base_tree, ui_instance=self.ui)

        Хинт элементов:
            tree_table_widget: ExtTreeWidgetProtocol[ExtTreeWidget]
            item: ExtTreeWidgetItemProtocol[ExtTreeWidgetItem]
            cell: ExtTreeWidgetCellProtocol[ExtTreeWidgetCell]
    """
    def clear_table(self):
        """Отчистить таблицу"""

    def iter_rows(self) -> list[ExtTreeWidgetItem]:
        """Итератор объектов строк ExtTreeWidgetItem"""

    def get_dict_uid_is_expand(
            self
    ) -> dict :
        """Рекурсивно обходит дерево, начиная с itecem."""

    def get_item_cell_by_uuid(
            self,
            uuid:str
    ) -> ExtTreeWidgetCell | list[ExtTreeWidgetCell] | None:
        """
        Поиск элемента таблицы по uuid

        @uuid искомый uuid
        """
    def get_item_cell_by_value(
            self,
            value,
            column: int = None,
            many: bool = False
    ) -> ExtTreeWidgetCell | list[ExtTreeWidgetCell] | None:
        """Поиск элемента таблицы по значению
        -------------------------------------
        @value искомый текст
        @column Колонка для поиска (если None поиск по всем)
        @many Если True возврат всех совпадений/ Если False возврат первого совпадения
        """

    def fill_table(self,
                   dict_or_list: list[list] | list[dict] | dict[str, dict],
                   hide_horizontal_header: bool = False,
                   hide_root_decorations: bool = False,
                   min_col_width: int = None,
                   max_col_width: int = None,
                   stretch_last_column: bool = False,
                   min_row_height: int = 26,
                   max_row_height: int = 40,
                   resize_first_column_after_expand: bool = True,
                   nick_name_level: str = None,
                   nick_name_uuid: str = None,
                   one_root: bool = False,
                   odd_item_color: tuple[int, int, int] | str = None,
                   even_item_color: tuple[int, int, int] | str = None,
                   hover_indicator_color: tuple[int, int, int] | str = (0, 120, 215),
                   branch_icon_if_can_open: str = None,
                   branch_icon_if_can_close: str = None,
                   hover_item_color: tuple[int, int, int] | str = None,
                   selected_item_color: tuple[int, int, int] | str = None,
                   selection_mode: QtWidgets.QAbstractItemView.SelectionMode = QtWidgets.QAbstractItemView.SingleSelection,
                   selection_behavior: QtWidgets.QAbstractItemView.SelectionBehavior = QtWidgets.QAbstractItemView.SelectRows,
                   draggable: bool = True,
                   system_fields_prefix: str = '__',
                   on_drop_access: typing.Callable[[ParentTreeItemType, DroppedTreeItemType], None] = None,
                    on_header_resized=None,
                   ):
        """
        @dict_or_list Данные для размещения
        @nick_name_level Наименование колонки с уровнем
        @nick_name_uuid Наименование колонки с уникальным идентификатором (Если не найдена генерируется UUID v4)
        @one_root Допускает только один корневой элемент игнорируя остальные
        @selection_mode/selection_behavior: определяет режим выбора элемента в дереве
        @system_fields_prefix: Префикс служебных полей

        ## СТИЛИЗАЦИЯ
        @even_item_color/odd_item_color Цвет четного/нечетного элемента (Если None раскраска не происходит)
        @hover_indicator_color Цвет указателя hover на размещение элемента drag on drop
        @min_row_height / max_row_height: ограничение высоты строк
        @min_col_width / max_col_width: минимальная/максимальная ширина столбца
        @stretch_last_column: установить stretch последней колонки
        @hide_root_decorations: скрыть стрелку раскрытия у root
        @hide_horizontal_header: скрыть горизонтальный header
        @branch_icon_if_can_open: путь к иконке для кнопки для показа дочерних элементов ветки
        @branch_icon_if_can_close: путь к иконке для кнопки скрытия дочерних элементов ветки
        @hover_item_color: цвет строки при наведении
        @selected_item_color: цвет активной строки
        @resize_first_column_after_expand: Изменять размер первой колонки после раскрытия дочерних элементов
        """

    def dump_as_table(self, rez_dict: bool = False,
                      level_nickname: str = None,
                      uuid_nickname: str = None
                      ) -> list[dict] | list[list]:
        """Получить представление таблицы в структуре списка словарей/списков"""

    def dump_as_nested(
            self,
            children_key: str = 'children',
            uuid_key: str = 'uuid',
            system_props_key: str = 'system_props',
            level_key: str = 'level'
    ) -> list:
        """Получить представление структуры с вложенностью
        --------------------------------------------------
            @children_key: Ключ размещения вложенных объектов.
            @uuid_key: Ключ размещения уникального идентификатора строки.
            @level_key: Ключ размещение уровня вложенности.
            @system_props_key: Ключ размещения системных атрибутов
        """

    def num_column_by_name(self, name: str):
        """Индекс колонки по имени"""

    def insert_before(self, row: int = None, *values: dict[str, typing.Any], into: bool = False) -> list[ExtTreeWidgetItem]:
        """
        Вставить строку/строки перед указанной строкой
            Если @logical_index is None в начало структуры
            Если row is None и into True вкладывает элемент в корневой

        @logical_index индекс из виртуального представления без вложенностей
        @values значения для вставки (Для пустой строки достаточно передать пустого словаря/словарей
        @into Вставить в внутрь выделенного элемента
        -------------------------------------------------------------
        Пример:
            Одиочная вставка:
                logical_index = self.current_row
                insert_before(logical_index, {'Наименование': 'АСО-9999999.01', 'Количество': 44})
            Множественная вставка:
                logical_index = self.current_row
                insert_before(
                    logical_index,
                    {'Наименование': 'АСО-9999999.01', 'Количество': 44},
                    {'Наименование': 'АСО-9999999.02', 'Количество': 2},
                    {'Наименование': 'АСО-9999999.03', 'Количество': 3},
                )
            Либо:
                struct = [
                    {'Наименование': 'АСО-9999999.01', 'Количество': 44},
                    {'Наименование': 'АСО-9999999.02', 'Количество': 2},
                    {'Наименование': 'АСО-9999999.03', 'Количество': 3},
                ]
                insert_before(logical_index, *struct)
        """

    def insert_after(self, logical_index: int = None, *values: dict[str, typing.Any], into: bool = False
                     ) -> list[ExtTreeWidgetItem]:
        """Вставить строку/строки после указанной строкой
            Если @logical_index is None в конец структуры

        @logical_index индекс из виртуального представления без вложенностей
        @values значения для вставки (Для пустой строки достаточно передать пустого словаря/словарей
        @into Вставить в внутрь выделенного элемента
        -------------------------------------------------------------
        Пример:
            Одиочная вставка:
                logical_index = self.current_row
                insert_after(logical_index, {'Наименование': 'АСО-9999999.01', 'Количество': 44})
            Множественная вставка:
                logical_index = self.current_row
                insert_after(
                    logical_index,
                    {'Наименование': 'АСО-9999999.01', 'Количество': 44},
                    {'Наименование': 'АСО-9999999.02', 'Количество': 2},
                    {'Наименование': 'АСО-9999999.03', 'Количество': 3},
                )
            Либо:
                struct = [
                    {'Наименование': 'АСО-9999999.01', 'Количество': 44},
                    {'Наименование': 'АСО-9999999.02', 'Количество': 2},
                    {'Наименование': 'АСО-9999999.03', 'Количество': 3},
                ]
                insert_after(logical_index, *struct)
        """

    def currentItem(self) -> ExtTreeWidgetItem | None:
        """Получить текущий выделенный объект"""

    def current_row(self) -> int | None:
        """Получить индекс логической структуры
                или None если не найдено"""

    def get_item_by_logical_index(self, logical_index: int) -> ExtTreeWidgetItem | None:
        """Получить объект строки ExtTreeWidgetItem по логическому индексу"""

    def get_item_by_uuid(self, uuid: str) -> ExtTreeWidgetItem | None:
        """Получить элемент по уникальному идентификатору"""

    def remove_row(self, logical_index: int):
        """Удалить объект строки ExtTreeWidgetItem по логическому индексу"""

    def countRows(self) -> int:
        """Количество строк в таблице"""


class ExtTreeWidgetItem:
    @property
    def temp_data(self):
        """
        var = tree_item.temp_data
        Взять временное свойство
        -------------------------
        Назначить свойство
        tree_item.temp_data = {'any_data': 123}
        """

    @temp_data.setter
    def temp_data(self, value): ...

    def clear_children(self):
        """Удалить всех потомков у элемента"""

    def reload_row(self, new_value: dict) -> bool:
        """Перезаполнение строки указанными значениями
            @new_value Словарь со значениями ui/системными.

            @return True заполнение прошло корректно.
        """
    def expand_children(self, scroll_to_item: bool = True, select: bool = True):
        """Раскрыть все дочерние элементы текущего элемента"""

    def expand_parents(self, scroll_to_item: bool = True,select: bool =True):
        """Раскрыть все родительские элементы"""

    def get_system_field(self, field: str, default: typing.Any = None):
        """Получить все служебное поле текущей строки или @default"""

    def get_value_by_field(self, field: str, default: typing.Any = None) -> typing.Any:
        """Получить значение ячейки по имени колонки или @default"""

    def set_value_by_field(
            self, field: str, new_value: typing.Any,
            on_error: typing.Callable[[ExtTreeWidgetItem, Exception], None] = None
    ) -> None:
        """Вставить значение по имени поля
        ----------------------------------
        @field Имя поля
        @new_value Значение
        @on_error функция вызываемая при ошибке или отсутствия поля
            Принимающая параметры [@ExtTreeWidgetItem, @Exception]
        """

    def system_fields(self) -> dict[str, typing.Any]:
        """Получить все служебные поля текущей строки"""

    @property
    def uuid(self):
        """Получить уникальный идентификатор строки"""

    @uuid.setter
    def uuid(self, value): ...

    @property
    def level(self):
        """Получить уровень вложенности строки"""

    @level.setter
    def level(self): ...

    def iter_column_by_row(self) -> typing.Generator[ExtTreeWidgetCell, None, None]:
        """Получить генератор объектов колонок строки"""

    @property
    def current_index(self):
        """Текущее положение строки в виртуальной таблице"""

    def get_set_columns(self) -> set[str]: ...

    def to_dict(
            self,
            nick_name_level: str = 'Уровень',
            nick_name_uuid: str = 'UUID',
            include_system_fields: bool = True
    ) -> dict[str, typing.Any]: ...

    def add_combobox(self, column: int = 0, values: list | tuple = tuple(), first_void=True,
                     conn_func=None, editable: bool = False, name_flag: typing.Any = None,
                     additional_state: typing.Any = None
                     ) -> QtWidgets.QComboBox:
        """Добавить Combobox в ячейку строки
        ------------------------------------
        item.add_combobox(tree1.num_column_by_name('Код ERP'), conn_func=my_func, values=['a', 'b', 'c'], first_void=False)
        """

    def add_check_box(self, column, trisate=False, val=False, conn_func=None, additional_state=None, enabled=True
                      ) -> QtWidgets.QCheckBox:
        """
        Добавить QCheckBox в ячейку строки
        ----------------------------------
        item.add_check_box(
            tree1.num_column_by_name('Код ERP'),
            conn_func=my_func, additional_state={'Рандомная дата': datetime.now()}
        )"""

    def add_button(self, column, text='', val=True, conn_func=None, additional_state='',
                   img_path='', height: int = None, fontsize='', cell_val=None) -> QtWidgets.QPushButton:
        """Добавить QPushButton в ячейку строки
        ---------------------------------------
        item.add_button(tree1.num_column_by_name('Уровень'), conn_func=my_func)
        """

    def add_label_link(self, column: int, file, name, conn_func=None, parent_self=None):
        r"""
        Добавить кликабельную ссылку в ячейку строки
        -----------------------------------------------
        item.add_label_link(6, file=r'C:\Users\user\Work folders\Documents\2\test.txt', name='test_name', parent_self=tree1)
        """

    def set_row_style(self, *, foreground_color=None, background_color=None,
                      bold=None, italic=None, underline=None, strikeout=None,
                      font_family=None, font_size=None):
        """Задать стиль стиль к табличной строке
        ## Обязательные
        @item Элемент строки таблицы
        @column Колонка

        ## Опциональные
        @foreground_color Цвет строки
        @background_color Цвет фона
        @bold Жирность строки
        @italic Жирность строки
        @underline Подчеркнуть строку
        @font_family Задать объект QtGui.Font
        @font_size Размер строки

        ## Пример
        item.set_row_style(bold=True, background_color='#d9d899', italic=True)
        """

    def set_column_style(self, column, *, foreground_color=None, background_color=None,
                         bold: bool = None, italic: bool = None, underline: bool = None,
                         strikeout: bool = None, font_family=None, font_size=None):
        """Задать стиль ячейки таблицы
        ## Обязательные
        @item Элемент строки таблицы
        @column Колонка

        ## Опциональные
        @foreground_color Цвет строки
        @background_color Цвет фона
        @bold Жирность строки
        @italic Жирность строки
        @underline Подчеркнуть строку
        @font_family Задать объект QtGui.Font
        @font_size Размер строки

        ## Пример
        item.set_column_style(column=2, bold=True, background_color='#d9d899', underline=True)
        """

    def add_interactive_label(
            self,
            column: int,
            text: str = '',
            txt_cut: int = 15,
            min_label_px: int = 40,
            btn_width: int = 20,
            mark_not_changed_item: bool = True,
            parent_self: typing.Any = None
    ) -> InteractiveLabelInstance:
        """
        Пример использования
        widget = CQT.add_interactive_label(
            table=self.ui.tbl_pl_add_poz,               # Таблица для размещения label
            row=0,                                      # Строка таблицы
            column=nk_sort_c,                           # Колонка таблицы
            text=current_type_text,                     # Текст для label (Если не задан берется из ячейки QTableWidgetItem)
            txt_cut=14,                                 # До какого символа обрезать текст(Если не задан задается textWrapped)
            btn_width=25                                # Ширина кнопок
        )
        widget.add_button(
            txt_button='✏️',                            # Текст кнопки
            on_clicked=on_clicked,                      # Обработчик клика по кнопок
            tooltip='Редактировать',                    # tooltip кнопки
            img_path='btn_add_zamech'                   # Ссылка на изображение (Если задано без префикса диска C://,
                                                           то базовой папкой задается ./icons
        )

        widget.add_button(txt_button='x', on_clicked=print, tooltip='Удалить')
        widget.add_button(txt_button='...', on_clicked=print, tooltip='...', img_path='btn_add_zamech')
        """


class ExtTreeWidgetCell:
    tree: ExtTreeWidget
    row_item: ExtTreeWidgetItem
    column: int
    text: str
    level: int

    def set_text(self, new_value: str):
        """Задать новое значение ячейке"""
