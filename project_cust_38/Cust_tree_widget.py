import copy
import json
import pickle
import os
import sys
import typing
import pathlib
import logging
import uuid

from urllib.parse import quote

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor

from project_cust_38 import Cust_Functions as F


logger = logging.getLogger(__name__)


def copy_base_widget_attributes(src: QtWidgets.QWidget, dst: QtWidgets.QWidget) -> None:
    dst.setObjectName(src.objectName())
    dst.setEnabled(src.isEnabled())
    dst.setVisible(src.isVisible())
    dst.setGeometry(src.geometry())
    dst.setMinimumSize(src.minimumSize())
    dst.setMaximumSize(src.maximumSize())
    dst.setSizePolicy(src.sizePolicy())
    dst.setFont(src.font())
    dst.setStyleSheet(src.styleSheet())
    dst.setToolTip(src.toolTip())
    dst.setWhatsThis(src.whatsThis())
    dst.setFocusPolicy(src.focusPolicy())
    dst.setLayoutDirection(src.layoutDirection())


def _copy_qtree_props(src: QtWidgets.QTreeWidget, dst: QtWidgets.QTreeWidget) -> None:
    try:
        dst.setSelectionMode(src.selectionMode())
        dst.setSelectionBehavior(src.selectionBehavior())
        dst.setSortingEnabled(src.isSortingEnabled())
        dst.setEditTriggers(src.editTriggers())
        # dst.setDragEnabled(src.dragEnabled())
        # dst.setAcceptDrops(src.acceptDrops())
        # dst.setDragDropMode(src.dragDropMode())
    except Exception:
        logger.debug("Behavior properties copy failed", exc_info=True)
    try:
        dst.setUniformRowHeights(src.uniformRowHeights())
        dst.setRootIsDecorated(src.rootIsDecorated())
        dst.setItemsExpandable(src.itemsExpandable())
        dst.setAllColumnsShowFocus(src.allColumnsShowFocus())
    except Exception:
        pass


def _find_widget_index_in_layout(layout: QtWidgets.QLayout, widget: QtWidgets.QWidget) -> int:
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is None:
            continue
        w = item.widget()
        if w is widget:
            return i
    return -1


def replace_qtree(
        old_tree: QtWidgets.QTreeWidget,
        new_tree: QtWidgets.QTreeWidget,
        ui_instance
) -> QtWidgets.QTreeWidget:
    parent = old_tree.parent()
    attr_name = old_tree.objectName()
    setattr(ui_instance, attr_name, new_tree)
    copy_base_widget_attributes(old_tree, new_tree)
    try:
        _copy_qtree_props(old_tree, new_tree)
    except Exception:
        logger.exception('Ошибка при попытке копирования базовых атрибутов QTreeWidget')

    if isinstance(parent, QtWidgets.QSplitter):
        idx = parent.indexOf(old_tree)
        parent.insertWidget(idx, new_tree)
        old_tree.setParent(None)
        old_tree.deleteLater()
        logger.info(f'{attr_name!r} с родительским виджетом QSplitter успешно заменен')
        return new_tree

    if isinstance(parent, QtWidgets.QTabWidget):
        tab_widget: QtWidgets.QTabWidget = parent
        idx = tab_widget.indexOf(old_tree)
        tab_text = tab_widget.tabText(idx)
        tab_icon = tab_widget.tabIcon(idx)
        tab_tooltip = tab_widget.tabToolTip(idx)
        tab_widget.removeTab(idx)
        tab_widget.insertTab(idx, new_tree, tab_icon, tab_text)
        tab_widget.setTabToolTip(idx, tab_tooltip)
        old_tree.setParent(None)
        old_tree.deleteLater()
        logger.info(f'{attr_name!r} с родительским виджетом QTabWidget успешно заменен')
        return new_tree

    if isinstance(parent, QtWidgets.QStackedWidget):
        stack: QtWidgets.QStackedWidget = parent
        idx = stack.indexOf(old_tree)
        stack.removeWidget(old_tree)
        stack.insertWidget(idx, new_tree)
        old_tree.setParent(None)
        old_tree.deleteLater()
        logger.info(f'{attr_name!r} с родительским виджетом QStackedWidget успешно заменен')
        return new_tree

    if isinstance(parent, QtWidgets.QScrollArea):
        scroll: QtWidgets.QScrollArea = parent
        if scroll.widget() is old_tree:
            scroll.takeWidget()
            scroll.setWidget(new_tree)
            old_tree.setParent(None)
            old_tree.deleteLater()
            logger.info(f'{attr_name!r} с родительским виджетом QScrollArea успешно заменен')
            return new_tree

    if parent is not None:
        layout = parent.layout()
        if layout is not None:
            idx = _find_widget_index_in_layout(layout, old_tree)
            if idx >= 0:
                layout.insertWidget(idx, new_tree)
                layout.removeWidget(old_tree)
                old_tree.setParent(None)
                old_tree.deleteLater()
                logger.info(f'{attr_name!r} с родительским виджетом {type(parent).__name__} с индексом {idx} успешно заменен')
                return new_tree

    if parent is not None:
        new_tree.setParent(parent)
        new_tree.setGeometry(old_tree.geometry())
        old_tree.hide()
        logger.info(f'{attr_name!r} с родительским виджетом {type(parent).__name__} успешно заменен')
        return new_tree

    new_tree.show()
    old_tree.hide()
    logger.info(f'{attr_name!r} родительский виджет не найден')
    return new_tree



class InteractiveLabelInstance(QtCore.QObject):
    def __init__(self, table: QtWidgets.QTableWidget, row: int,
                 column: int,
                 text: str,
                 txt_cut: int = 15,
                 min_label_px: int = 40,
                 btn_width=20,
                 mark_not_changed_item: bool = True,
                 parent_self: typing.Any = None
        ) -> None:
        super().__init__()
        self.mark_not_changed_item = mark_not_changed_item
        self.parent_self = parent_self
        self.table = table
        self.row = row
        self.column = column
        if not text:
            text = self.item_text # 01.10.25
        self.full_text = text
        self.txt_cut = txt_cut
        self.min_label_px = min_label_px
        self.padding = 4
        self.btn_width = btn_width

        self.container = QtWidgets.QWidget()
        self.container.setAutoFillBackground(True)

        self.hlayout = QtWidgets.QHBoxLayout(self.container)
        self.hlayout.setContentsMargins(0, 0, 0, 0)
        self.hlayout.setSpacing(0)

        self.label = QtWidgets.QLabel(text)
        # self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft) # 01.10.25
        self.label.setContentsMargins(5, 0, 5, 0)
        self.hlayout.addWidget(self.label, 1)

        self.buttons_widget = QtWidgets.QWidget()
        self.buttons_layout = QtWidgets.QHBoxLayout(self.buttons_widget)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(0)
        self.hlayout.addWidget(self.buttons_widget, 0)

        self.buttons = []
        item = self.cell_item # 01.10.25
        self.set_cell_widget(item)
        self._update_label_text()
        self._update_sizes()
        self.destroyed_tasks = []
        if isinstance(table, QtWidgets.QTableWidget): # 01.10.25
            vh = self.table.verticalHeader()
            hh = self.table.horizontalHeader()
            try:
                vh.sectionResized.connect(self._on_row_section_resized)
                self.destroyed_tasks.append((vh.sectionResized, self._on_row_section_resized))
            except Exception:
                pass
            try:
                hh.sectionResized.connect(self._on_column_section_resized)
                self.destroyed_tasks.append((hh.sectionResized, self._on_column_section_resized))
            except Exception:
                pass
        palette = self.container.palette()
        qcolor = palette.color(self.container.backgroundRole())
        self._apply_label_bg_style(qcolor)
        self._init_label_color_state()
        self.label.destroyed.connect(self.on_destroyed)

    @property
    def cell_item(self):
        if isinstance(self.table, QtWidgets.QTreeWidget):
            return self.table.iter_rows()[self.row]
        else:
            return self.table.item(self.row, self.column)

    def set_cell_widget(self, item):
        invisible_brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))

        if isinstance(self.table, QtWidgets.QTreeWidget):
            invisible_brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
            item.setForeground(self.column, invisible_brush)
            item.setBackground(self.column, invisible_brush)
            self.table.setItemWidget(item, self.column, self.container)
        if isinstance(self.table, QtWidgets.QTableWidget):
            item.setForeground(invisible_brush)
            item.setBackground(invisible_brush)
            self.table.setCellWidget(self.row, self.column, self.container)

    @property
    def item_text(self) -> str:
        current_item = self.cell_item
        if current_item:
            return current_item.text()
        return ''

    def on_destroyed(self, *args):
        while self.destroyed_tasks:
            task, func = self.destroyed_tasks.pop(0)
            task.disconnect(func)

    def _init_label_color_state(self):
        if self.mark_not_changed_item:
            self.label.setStyleSheet("color: gray;")
            prev_method = self.label.setText
            self.label.setText = lambda text: self._on_label_text_edit(text, prev_method)

    def _on_label_text_edit(self, text, prev, *args):
        try:
            if self.full_text != text:
                self.label.setStyleSheet(f"color: {self.text_color}")
            prev(text)
        except Exception as e:
            ...

    def _apply_label_bg_style(self, qc: QtGui.QColor):
        r, g, b, _ = qc.getRgb()
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        text_color = '#ffffff' if luminance < 128 else '#000000'
        self.text_color = text_color
        bg_hex = qc.name()
        style = f"background-color: {bg_hex}; color: {text_color};"
        self.label.setStyleSheet(style)
        p = self.container.palette()
        p.setColor(self.container.backgroundRole(), qc)
        self.container.setPalette(p)

    def _approx_label_width_px_by_chars(self):
        fm = QtGui.QFontMetrics(self.label.font())
        if self.txt_cut <= 0:
            return self.min_label_px
        avg = fm.averageCharWidth()
        return int(avg * self.txt_cut + fm.horizontalAdvance('..'))

    def _sum_buttons_width(self):
        if not self.buttons:
            return 0
        size = self._button_size_for_current_row()
        total = 0
        total += size * len(self.buttons)
        return total

    def _button_size_for_current_row(self):
        row_h = self.table.rowHeight(self.row)
        size = max(16, max(1, row_h))
        return size

    def _update_button_sizes(self):
        try:
            size = self._button_size_for_current_row()
            for btn in self.buttons: # type: QtWidgets.QPushButton
                btn.setFixedSize(QtCore.QSize(size, size))
                h = self._button_size_for_current_row()
                btn.setFixedSize(QtCore.QSize(self.btn_width, h))
                btn.setFlat(True)
        except Exception as e:
            ...


    def _update_label_text(self):
        fm = QtGui.QFontMetrics(self.label.font())
        buttons_px = self._sum_buttons_width()
        col_width = self.table.columnWidth(self.column)
        available_px = max(self.min_label_px, col_width - buttons_px - self.padding)
        if available_px <= 0:
            available_px = self._approx_label_width_px_by_chars()

    def _update_column_width_if_needed(self):
        desired_label_px = max(self.min_label_px, self._approx_label_width_px_by_chars())
        desired_total = desired_label_px + self._sum_buttons_width() + self.padding
        current = self.table.columnWidth(self.column)
        if current < desired_total:
            self.table.setColumnWidth(self.column, desired_total)

    def _update_sizes(self):
        self._update_button_sizes()
        self._update_label_text()
        self._update_column_width_if_needed()

    def _on_row_section_resized(self, logicalIndex, *args):
        if logicalIndex == self.row:
            self._update_sizes()

    def _on_column_section_resized(self, logicalIndex, *args):
        if logicalIndex == self.column:
            self._update_label_text()

    def _update_img(self, img_path: str, btn: QtWidgets.QPushButton):
        dir = F.sep().join([F.path_to_execut_file_c(), 'icons'])
        path_obj = pathlib.Path(img_path)
        if not path_obj.drive:
            path_obj = pathlib.Path(dir) / path_obj
        if path_obj.exists():
            icon1 = QtGui.QIcon()
            icon1.addPixmap(QtGui.QPixmap(str(path_obj.absolute())), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            btn.setIcon(icon1)
            btn.setToolTip(btn.text())
            btn.setText('')
            h = self._button_size_for_current_row()
            inset_w = max(1, self.btn_width - 4)
            inset_h = max(1, h - 4)
            btn.setIconSize(QtCore.QSize(inset_w, inset_h))


    def add_button(self, txt_button: str = '', tooltip: str ='' ,
                   on_clicked=None,
                   img_path: str = '',
                   cell_val: typing.Any = None,
        ):
        """
        on_clicked (lblself:CQT.InteractiveLabelInstance,self, row, col)
        * Если передано on_clicked(
            current_object: InteractiveLabelInstance # Для взаимодействия с виджетами table,label,buttons
            row: int,
            column: int,
            cell_val: Any Дополнительный объект (по совместимости с CQT.add_btn
        )
        """
        btn = QtWidgets.QPushButton(txt_button)
        btn.setFocusPolicy(QtCore.Qt.NoFocus) #01.10.25
        btn.setToolTip(tooltip)
        btn.setFlat(True)
        if on_clicked is not None: #29.08.25
            column_item = ExtTreeWidgetColumn(
                tree=self.cell_item.treeWidget(),
                item=self.cell_item,
                column=self.column
            )
            if not self.parent_self:
                if cell_val:
                    btn.clicked.connect(lambda *args: on_clicked(self, column_item, cell_val))
                else:
                    btn.clicked.connect(lambda *args: on_clicked(self, column_item))
            else:
                if cell_val:
                    btn.clicked.connect(lambda *args: on_clicked(self, self.parent_self,column_item, cell_val))
                else:
                    btn.clicked.connect(lambda *args: on_clicked(self, self.parent_self, column_item))
        self.buttons_layout.addWidget(btn)
        self.buttons.append(btn)
        if isinstance(self.table, QtWidgets.QTableWidget): #01.10.25
            self._update_sizes()
        if img_path != '':
            self._update_img(img_path, btn)
        return btn

    def set_text(self, lbl_text: str):
        self.label.setText(lbl_text)
        self.full_text = lbl_text
        self._update_sizes()


class BaseTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    LEVEL_ROLE = Qt.UserRole + 1
    UUID_ROLE = Qt.UserRole + 2
    SYSTEM_FIELDS_ROLE = Qt.UserRole + 3

    def __init__(self, texts, level: int = 0, object_uuid: str | None = None, system_data: dict = None):
        super().__init__([str(i) for i in texts])
        self.__init_system_fields(system_data)
        self.level = level
        if object_uuid is None:
            object_uuid = str(uuid.uuid4())

        self.uuid = object_uuid
        self.background_changed = set()

    def __init_system_fields(self, system_data: dict = None):
        if not isinstance(system_data, dict):
            system_data = {}
        self.setData(0, self.SYSTEM_FIELDS_ROLE, system_data)

    def treeWidget(self) -> "ExtTreeWidget":
        return super().treeWidget()

    def _reload_props(self, new_value: dict) -> bool:
        if not isinstance(new_value, dict):
            logger.debug('ExtTreeWidgetItem.reload_row: Некорректный тип значения для заполнения')
            return False
        tree = self.treeWidget()
        header = tree.headerItem()
        data = prepare_data_for_fill([new_value], tree.nick_name_uuid, tree.nick_name_level,
                                     tree.system_fields_prefix)
        if not data:
            logger.debug('ExtTreeWidgetItem.reload_row: Не удалось подготовить строку к вставке')
            return False
        for row_data in data:
            for column in range(self.treeWidget().columnCount()):
                head_name = header.text(column)
                if tree.nick_name_level and tree.nick_name_level == head_name:
                    continue
                old_value = self.text(column)
                new_value = row_data.user_data.get(head_name, None)
                if new_value is None:
                    continue
                if str(old_value) != str(new_value):
                    self.setText(column, str(new_value))
            sys_fields = self.system_fields
            sys_fields.update(row_data.system_data)
            self.system_fields = sys_fields
            return True
        return False


class ExtTreeWidgetItem(BaseTreeWidgetItem):

    def reload_row(self, new_value: dict) -> bool:
        """Перезаполнение строки указанными значениями
            @new_value Словарь со значениями ui/системными.

            @return True заполнение прошло корректно.
        """
        return self._reload_props(new_value)

    def expand_parents(self, scroll_to_item: bool = True):
        """Раскрыть все родительские элементы"""
        cr_tree = self.treeWidget()
        parent = self.parent()
        while parent:
            parent.setExpanded(True)
            parent = parent.parent()
        if scroll_to_item:
            cr_tree.scrollToItem(self)
        cr_tree.setFocus()
        self.setSelected(True)

    def get_system_field(self, field: str, default: typing.Any = None):
        """Получить все служебное поле текущей строки или @default"""
        props = self.data(0, self.SYSTEM_FIELDS_ROLE)
        return props.get(field, default)

    def get_value_by_field(self, field: str, default: typing.Any = None) -> typing.Any:
        """Получить значение ячейки по имени колонки или @default"""
        row_data = self.to_dict()
        if not isinstance(row_data, dict):
            return
        return row_data.get(field, default)

    @property
    def system_fields(self) -> dict[str, typing.Any]:
        """Получить все служебные поля текущей строки"""
        return self.data(0, self.SYSTEM_FIELDS_ROLE)

    @system_fields.setter
    def system_fields(self, new_val):
        prev_state = self.system_fields
        if not isinstance(prev_state, dict):
            prev_state = {}
        if not isinstance(new_val, dict):
            return
        prev_state.update(new_val)
        self.setData(0, self.SYSTEM_FIELDS_ROLE, prev_state)

    @property
    def uuid(self):
        """Получить уникальный идентификатор строки"""
        return self.data(0, self.UUID_ROLE)

    @uuid.setter
    def uuid(self, value):
        self.setData(0, self.UUID_ROLE, value)

    @property
    def level(self):
        """Получить уровень вложенности строки"""
        v = self.data(0, ExtTreeWidgetItem.LEVEL_ROLE)
        return int(v) if v is not None else 0

    @level.setter
    def level(self, lvl: int):
        super().setData(0, ExtTreeWidgetItem.LEVEL_ROLE, int(lvl))

    def iter_column_by_row(self) -> typing.Generator["ExtTreeWidgetColumn", None, None]:
        """Получить генератор объектов колонок строки"""
        for column in range(self.columnCount()):
            yield ExtTreeWidgetColumn(
                tree=self.treeWidget(),
                item=self,
                column=column
            )

    @property
    def current_index(self):
        """Текущее положение строки в виртуальной таблице"""
        rows = self.treeWidget().iter_rows()
        for i, it in enumerate(rows):
            if it is self:
                return i

    def to_dict(
            self,
            nick_name_level: str = 'Уровень',
            nick_name_uuid: str = 'UUID',
            include_system_fields: bool = True
    ) -> dict[str, typing.Any]:
        header_item = self.treeWidget().headerItem()
        user_data = {
            header_item.text(column): self.text(column)
            for column in range(self.columnCount())
        }
        if include_system_fields:
            system_fields = self.system_fields
            if isinstance(system_fields, dict):
                user_data.update(system_fields)
        user_data[nick_name_level] = self.level
        user_data[nick_name_uuid] = self.uuid
        return user_data

    def add_combobox(
            self,
            column=0,
            values: list | tuple=tuple(),
            first_void=True,
            conn_func=None,
            editable=False,
            name_flag=None,
            additional_state: typing.Any = None
    ):
        current_text = self.text(column)
        combo = QtWidgets.QComboBox()
        combo.wheelEvent = lambda event: None
        fl = False
        if conn_func is not None:
            column_item = ExtTreeWidgetColumn(
                tree=self.treeWidget(),
                item=self,
                column=column
            )
            if additional_state == '':
                if name_flag != None:
                    combo.activated[str].connect(
                        lambda text: conn_func(text, self.treeWidget(), column_item, name_flag, additional_state))
                else:
                    combo.activated[str].connect(lambda text: conn_func(text, self.treeWidget(), column_item, name_flag, additional_state))
            else:
                if name_flag != None:
                    combo.activated[str].connect(
                        lambda text: conn_func(self, text, self.treeWidget(), column_item, name_flag))
                else:
                    combo.activated[str].connect(
                        lambda text: conn_func(self, text, self.treeWidget(), column_item))
        if first_void:
            combo.addItem("")
        if isinstance(values, dict):
            _ = 0
            koef = 0
            if first_void:
                koef = 1
            for key in values:
                combo.addItem(key)
                combo.setItemData(_ + koef, values[key], QtCore.Qt.ToolTipRole)
                if key == current_text:
                    fl = True
                _ += 1
        else:
            for item in values:
                combo.addItem(item)
                if item == current_text:
                    fl = True
        self.treeWidget().setItemWidget(self, column, combo)
        if fl:
            combo.setCurrentText(current_text)
        if first_void:
            combo.setCurrentIndex(0)
        if editable:
            combo.setEditable(True)
        return combo

    def add_check_box(self, column, trisate=False, val=False, conn_func=None, additional_state = None, enabled=True):
        check = QtWidgets.QCheckBox()
        check.setTristate(trisate)
        check.setChecked(val)
        check.setEnabled(enabled)
        if conn_func is not None:
            column_item = ExtTreeWidgetColumn(
                tree=self.treeWidget(),
                item=self,
                column=column
            )
            if additional_state is None:
                check.clicked.connect(lambda checked: conn_func(checked, column_item))
            else:
                check.clicked.connect(lambda checked: conn_func(additional_state, checked, column_item))
        self.treeWidget().setItemWidget(self, column, check)

    def add_button(self, column, text='', val=True, conn_func = None, additional_state = '',img_path='',height: int = None,fontsize='',cell_val=None):
        btn = QtWidgets.QPushButton()
        btn.setEnabled(val)
        btn.setText(text)
        if height is not None:
            btn.setFixedHeight(height)
        if img_path != '':
            if F.existence_file_c(img_path):
                icon1 = QtGui.QIcon()
                icon1.addPixmap(QtGui.QPixmap(img_path), QtGui.QIcon.Normal, QtGui.QIcon.Off)
                btn.setIcon(icon1)
                btn.setIconSize(QtCore.QSize(btn.height(), btn.height()))
                btn.setToolTip(btn.text())
                btn.setText('')
        if fontsize != '':
            font = btn.font()
            font.setPointSize(int(fontsize))
            btn.setFont(font)
        if conn_func is not None:
            column_item = ExtTreeWidgetColumn(
                tree=self.treeWidget(),
                item=self,
                column=column
            )
            if additional_state == '':
                if cell_val:
                    btn.clicked.connect(lambda checked: conn_func(column_item,cell_val))
                else:
                    btn.clicked.connect(lambda checked: conn_func(column_item))
            else:
                if cell_val:
                    btn.clicked.connect(lambda checked: conn_func(additional_state, column_item, cell_val))
                else:
                    btn.clicked.connect(lambda checked: conn_func(additional_state, column_item))
        self.treeWidget().setItemWidget(self, column, btn)

    def add_label_link(
            self,
            column: int,
            file,
            name,
            conn_func=None,
            parent_self=None
    ):
        lbl = QtWidgets.QLabel()

        lbl.setOpenExternalLinks(True)
        lnk = quote(f'{file}')
        link_template = rf'<a href={lnk}>{name}</a>'
        lbl.setText(link_template)
        lbl.setOpenExternalLinks(False)
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl.setAutoFillBackground(True)
        self.treeWidget().setItemWidget(self, column, lbl)
        if conn_func:
            if parent_self:
                lbl.linkActivated.connect(lambda: conn_func(lnk, column, name, file, parent_self))
            else:
                lbl.linkActivated.connect(lambda: conn_func(lnk, column, name, file))

    def set_row_style(self, *,
                      foreground_color=None,
                      background_color=None,
                      bold=None, italic=None, underline=None, strikeout=None,
                      font_family=None, font_size=None):
        """
        Задать стиль стиль к табличной строке

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

        """
        if item is None:
            return

        fg = self.treeWidget().make_qcolor(foreground_color)
        bg = self.treeWidget().make_qcolor(background_color)

        cols = self.columnCount()
        base_font = item.font(0) if cols > 0 else self.font()

        for col in range(cols):
            if fg is not None:
                item.setForeground(col, QtGui.QBrush(fg))
            if bg is not None:
                item.background_changed.add(col)
                item.setBackground(col, QtGui.QBrush(bg))
            if any(p is not None for p in (bold, italic, underline, strikeout, font_family, font_size)):
                cur_font = item.font(col) or base_font
                new_font = self.treeWidget().apply_font_modifications(cur_font, bold=bold, italic=italic,
                                                     underline=underline, strikeout=strikeout,
                                                     family=font_family, size=font_size)
                item.setFont(col, new_font)

    def set_column_style(self, column, *,
                         foreground_color=None,
                         background_color=None,
                         bold: bool = None,
                         italic: bool = None,
                         underline: bool = None,
                         strikeout: bool = None,
                         font_family=None,
                         font_size=None):
        """
        Задать стиль ячейки таблицы

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
        """

        if item is None:
            return
        if column < 0 or column >= self.columnCount():
            return
        item.background_changed.add(column)

        fg = self.treeWidget().make_qcolor(foreground_color)
        bg = self.treeWidget().make_qcolor(background_color)

        if fg is not None:
            item.setForeground(column, QtGui.QBrush(fg))
        if bg is not None:
            item.setBackground(column, QtGui.QBrush(bg))

        if any(p is not None for p in (bold, italic, underline, strikeout, font_family, font_size)):
            cur_font = item.font(column) or item.font(0) or self.font()
            new_font = self.treeWidget().apply_font_modifications(cur_font, bold=bold, italic=italic,
                                                 underline=underline, strikeout=strikeout,
                                                 family=font_family, size=font_size)
            item.setFont(column, new_font)

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
            on_clicked=on_clicked,                      # Обработчик клика по кнопк
            tooltip='Редактировать',                    # tooltip кнопки
            img_path='btn_add_zamech'                   # Ссылка на изображение (Если задано без префикса диска C://,
                                                           то базовой папкой задается ./icons
        )

        widget.add_button(txt_button='x', on_clicked=print, tooltip='Удалить')
        widget.add_button(txt_button='...', on_clicked=print, tooltip='...', img_path='btn_add_zamech')
        """
        inst = InteractiveLabelInstance(self.treeWidget(), self.current_index, column, text,
                                        txt_cut=txt_cut,
                                        min_label_px=min_label_px,
                                        btn_width=btn_width,
                                        mark_not_changed_item=mark_not_changed_item,
                                        parent_self=parent_self)
        return inst

class ExtTreeWidgetColumn:
    def __init__(self, tree, item: ExtTreeWidgetItem, column: int):
        self.tree = tree
        self.row_item = item
        self.column = column
        self.text = item.text(column)
        self.level = self.row_item.level

    def set_text(self, new_value):
        self.row_item.setText(self.column, new_value)

from dataclasses import dataclass
from collections import UserList

@dataclass
class RowData:
    system_data: dict
    user_data: dict
    level: int | None
    uuid_: str | None

TableRowType = typing.TypeVar('TableRowType', bound=RowData)

class TableData(UserList[TableRowType], typing.Generic[TableRowType]):
    @property
    def user_headers(self):
        if len(self) < 1:
            return None
        first_elem: TableRowType = self.data[0]
        user_row = first_elem.user_data
        if isinstance(user_row, dict):
            return list(user_row.keys())
        if isinstance(user_row, list):
            return user_row
        return None

def prepare_data_for_fill(data, nick_name_uuid: str, nick_name_level: str, property_prefix: str = '__'):
    data_for_fill = TableData()
    if not isinstance(data, (list, tuple)):
        return
    if len(data) < 1:
        return

    match data:
        case [first, *others] if isinstance(first, dict):
            data_to_dict = data
        case [first, *others] if isinstance(first, (list, tuple)):
            data_to_dict = F.list_of_lists_to_list_of_dicts(list(data))
        case _:
            return

    for row_idx, item in enumerate(data_to_dict):
        property_ = {}
        row_data = {}
        level = 0
        uuid_ = None
        for key, val in item.items():
            if key == nick_name_level:
                level = val
            if key == nick_name_uuid:
                uuid_ = val
            elif key.startswith(property_prefix):
                property_[key] = val
            else:
                row_data[key] = val
        data_for_fill.append(
            RowData(system_data=property_, user_data=row_data, level=level, uuid_=uuid_)
        )
    return data_for_fill



class BaseTreeWidget(QtWidgets.QTreeWidget):
    MIME_TYPE = 'application/x-ExtTreeWidgetItem'
    def __init__(self, old_tree_instance: QtWidgets.QTreeWidget, ui_instance: object):
        super().__init__()

        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setAnimated(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(self.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(self.SingleSelection)

        self.min_row_height = None
        self.max_row_height = None
        self.width_first_column = None
        self.min_col_width = None
        self.max_col_width = None
        self.stretch_last_column = None

        self.hover_indicator_color = None
        self._indicator_item = None
        self._indicator_pos = None
        self._hover_expand_timer = None
        self._last_hover_item = None
        self.remove_on_drop = True
        self._odd_color = None
        self._even_color = None
        self.nick_name_level = None
        self.nick_name_uuid = None
        self.expanded.connect(self.__on_expand)
        self.__post_init__(old_tree_instance, ui_instance)
        self.header().setStretchLastSection(True)
        self.property_manager = None
        self.system_fields_prefix = None

    def __post_init__(self, old_tree_instance, ui_instance):
        replace_qtree(old_tree=old_tree_instance, new_tree=self, ui_instance=ui_instance)
        self.show()

    def _prepare_text_for_item(self, text: dict | list):
        if isinstance(text, dict):
            texts = []
            for col in range(self.columnCount()):
                current_header = self.headerItem().text(col)
                texts.append(text.get(current_header, ''))
            return texts
        if isinstance(text, list):
            return [str(t) for t in text]
        return []

    def make_qcolor(self, x: tuple[int, int, int] | str):
        if x is None:
            return None
        if isinstance(x, QColor):
            return x
        return QtGui.QColor(x)

    def apply_font_modifications(self, base_font: QtGui.QFont, bold=None, italic=None,
                                  underline=None, strikeout=None,
                                  family=None, size=None) -> QtGui.QFont:
        f = QtGui.QFont(base_font)  # копия
        if bold is not None:
            f.setBold(bool(bold))
        if italic is not None:
            f.setItalic(bool(italic))
        if underline is not None:
            f.setUnderline(bool(underline))
        if strikeout is not None:
            f.setStrikeOut(bool(strikeout))
        if family is not None:
            f.setFamily(str(family))
        if size is not None:
            f.setPointSize(int(size))
        return f

    def install_branch_and_selection_icons(self,
                                           open_icon_path: str = "",
                                           closed_icon_path: str = "",
                                           selected_item_color: str | tuple[int, int, int] = "",
                                           hover_item_color: str | tuple[int, int, int] = "",
                                           ):

        def calc_color(color: str | tuple[int, int, int]) -> typing.Optional[str]:
            match color:
                case (r, g, b):
                    return f"rgba({r}, {g}, {b})"
                case str(hex_color):
                    return hex_color
                case _:
                    return None

        stylesheet = ""
        if hover_color := calc_color(hover_item_color):
            stylesheet += f"QTreeView::item:hover {{ background: {hover_color}; }}"
        if open_icon_path and os.path.exists(open_icon_path):
            stylesheet += f"""QTreeView::branch:open:has-children {{image: url({open_icon_path});}}"""
        if closed_icon_path and os.path.exists(closed_icon_path):
            stylesheet += f"""QTreeView::branch:closed:has-children {{image: url({closed_icon_path});}}"""
        if selected_color := calc_color(selected_item_color):
            stylesheet += f"""QTreeView::item:selected {{ background: {selected_color}; }}"""
        if stylesheet:
            self.setStyleSheet(stylesheet)

    def mimeData(self, items):
        def node_to_dict(node: QtWidgets.QTreeWidgetItem | None):
            if isinstance(node, ExtTreeWidgetItem):
                return {
                    'texts': node.to_dict(),
                    'level': int(node.data(0, ExtTreeWidgetItem.LEVEL_ROLE) or 0),
                    'children': [node_to_dict(node.child(i)) for i in range(node.childCount())],
                    'uuid': node.uuid,
                    'system_props': node.system_fields
                }
            else:
                return {
                    'texts': [node.text(c) for c in range(self.columnCount())],
                    'level': int(node.data(0, ExtTreeWidgetItem.LEVEL_ROLE) or 0),
                    'children': [node_to_dict(node.child(i)) for i in range(node.childCount())],
                    'uuid': None,
                    'system_props': None
                }


        data = [node_to_dict(it) for it in items]
        md = QtCore.QMimeData()
        # md.setData(ExtTreeWidget.MIME_TYPE, QtCore.QByteArray(json.dumps(data).encode('utf-8')))
        md.setData(ExtTreeWidget.MIME_TYPE, QtCore.QByteArray(pickle.dumps(data)))
        md.setData((ExtTreeWidget.MIME_TYPE + '/remove'), QtCore.QByteArray(b'1' if self.remove_on_drop else b'0'))
        return md

    def _create_items_from_serialized(self, data, parent_level_base: int = None):
        def create_node(nd, base_level):
            texts = []
            droped_text = nd.get('texts', [])
            uuid_ = nd.get('uuid')
            system_props = nd.get('system_props')
            if isinstance(droped_text, dict):
                for col in range(self.columnCount()):
                    current_header = self.headerItem().text(col)
                    texts.append(droped_text.get(current_header, ''))

            else:
                texts = [str(t) for t in nd.get('texts', [])]
            rel_lvl = nd.get('level', 0)
            new_level = base_level + rel_lvl if base_level is not None else rel_lvl
            headers = [self.headerItem().text(col) for col in range(self.columnCount())]
            struct = [headers, texts]
            if self.nick_name_level:
                column_level = F.num_col_by_name_in_hat_c(struct, self.nick_name_level)
                if column_level < len(texts):
                    texts[column_level] = new_level
            item = ExtTreeWidgetItem(texts, new_level, object_uuid=uuid_, system_data=system_props)
            for ch in nd.get('children', []):
                item.addChild(create_node(ch, base_level))
            if self.min_row_height is not None:
                for c in range(self.columnCount()):
                    item.setSizeHint(c, QtCore.QSize(item.sizeHint(c).width() if item.sizeHint(c) else 0,
                                                     self.min_row_height))
            return item

        items = []
        for nd in data:
            base = 0 if parent_level_base is None else parent_level_base
            items.append(create_node(nd, base if parent_level_base is not None else None))
        return items

    def restruct_level_by_item(self, items: list[ExtTreeWidgetItem]):
        if not items:
            return
        view_level = False
        level_column = None
        if self.nick_name_level:
            for col in range(self.columnCount()):
                if self.headerItem().text(col) == self.nick_name_level:
                    level_column = col
                    view_level = True
        for item in items:
            cnt = 0
            parent = item.parent()
            while parent:
                parent = parent.parent()
                cnt += 1
            item.level = cnt
            if view_level:
                item.setText(level_column, str(cnt))
            children = [item.child(ind) for ind in range(item.childCount())]
            self.restruct_level_by_item(children)


    def dropEvent(self, event):
        mime = event.mimeData()
        if not mime.hasFormat(ExtTreeWidget.MIME_TYPE):
            event.ignore()
            return

        raw = bytes(mime.data(ExtTreeWidget.MIME_TYPE))
        # data = json.loads(raw.decode('utf-8'))
        data = pickle.loads(raw)
        target_item = self.itemAt(event.pos())
        cr_item = self.currentItem()
        if cr_item == target_item and cr_item is not None:
            self._clear_indicator()
            self._cancel_expand_timer()
            return

        if target_item is None:
            new_items = self._create_items_from_serialized(data, parent_level_base=None)
            for ni in new_items:
                self.addTopLevelItem(ni)
            event.acceptProposedAction()
            self._clear_indicator()
            self._cancel_expand_timer()
            self.restruct_level_by_item(new_items)
            return

        target_rect = self.visualItemRect(target_item)
        if target_rect.isNull():
            new_items = self._create_items_from_serialized(data, parent_level_base=None)
            for ni in new_items:
                self.addTopLevelItem(ni)
            event.acceptProposedAction()
            self._clear_indicator()
            self._cancel_expand_timer()
            self.restruct_level_by_item(new_items)
            return

        y = event.pos().y()
        height = target_rect.height()
        threshold = height * 0.35 #todo ?вынести в константу
        top_th = target_rect.top() + threshold
        bottom_th = target_rect.bottom() - threshold

        if y < top_th: # todo ?вынести логику определения режима вставки в отдельную функцию
            mode = 'before'
        elif y > bottom_th:
            mode = 'after'
        else:
            mode = 'into'

        if mode == 'into':
            parent_level = int(target_item.data(0, ExtTreeWidgetItem.LEVEL_ROLE) or 0) + 1
        else:
            parent_level = int(target_item.data(0, ExtTreeWidgetItem.LEVEL_ROLE) or 0)

        new_items = self._create_items_from_serialized(data, parent_level)


        def insert_items_as_siblings(parent, start_index):
            idx = start_index
            for ni in new_items:
                if parent is None:
                    self.insertTopLevelItem(idx, ni)
                else:
                    parent.insertChild(idx, ni)
                idx += 1

        if mode == 'into':
            target_item.setExpanded(True)
            for ni in new_items:
                target_item.addChild(ni)
        else:
            parent = target_item.parent()
            if parent is None:
                target_index = self.indexOfTopLevelItem(target_item)
            else:
                target_index = parent.indexOfChild(target_item)

            if mode == 'before':
                start_index = target_index
            else:
                start_index = target_index + 1

            insert_items_as_siblings(parent, start_index)

        event.acceptProposedAction()
        self._clear_indicator()
        self._cancel_expand_timer()
        self.restruct_level_by_item(new_items)

    def _last_visible_item(self):
        """Возвращает последний топ-левел элемент, который видим (или None)."""
        count = self.topLevelItemCount()
        if count == 0:
            return None
        return self.topLevelItem(count - 1)

    def _set_indicator(self, item, pos_flag):
        """Сохраняем индикатор и перерисовываем view."""
        changed = (item != self._indicator_item) or (pos_flag != self._indicator_pos)
        if changed:
            self._indicator_item = item
            self._indicator_pos = pos_flag
            self.viewport().update()

        self._last_hover_item = item

    def _clear_indicator(self):
        if self._indicator_item is not None or self._indicator_pos is not None:
            self._indicator_item = None
            self._indicator_pos = None
            self.viewport().update()
        self._last_hover_item = None

    def _cancel_expand_timer(self):
        if self._hover_expand_timer and self._hover_expand_timer.isActive():
            self._hover_expand_timer.stop()
        self._hover_expand_timer = None

    def _handle_hover_expand(self):
        self._cancel_expand_timer()
        if self._indicator_item and self._indicator_pos == 'on':
            if self._indicator_item.childCount() > 0 and not self._indicator_item.isExpanded():
                self._hover_expand_timer = QTimer(self)
                self._hover_expand_timer.setSingleShot(True)
                self._hover_expand_timer.setInterval(700)
                self._hover_expand_timer.timeout.connect(self._on_expand_timeout) # type: ignore
                self._hover_expand_timer.start()

    def _on_expand_timeout(self):
        if self._last_hover_item and not self._last_hover_item.isExpanded():
            self._last_hover_item.setExpanded(True)
        self._hover_expand_timer = None

    def paintEvent(self, event):
        super().paintEvent(event)
        color = None
        if isinstance(self.hover_indicator_color, tuple) and len(self.hover_indicator_color) == 3:
            color = QtGui.QColor(*self.hover_indicator_color)
        elif isinstance(self.hover_indicator_color, str):
            color = QtGui.QColor(self.hover_indicator_color)
        else:
            return
        if color is None:
            return

        if not self._indicator_item or not self._indicator_pos:
            return

        rect = self.visualItemRect(self._indicator_item)
        if rect.isNull():
            return

        painter = QPainter(self.viewport())
        blue = color
        pen = QtGui.QPen(blue)
        pen.setWidth(2)
        painter.setPen(pen)

        if self._indicator_pos == 'on':
            fill_color = QColor(0, 120, 215, 60)
            painter.fillRect(rect.adjusted(1, 1, -1, -1), fill_color)
        else:
            if self._indicator_pos == 'above':
                y = rect.top()
            else:
                y = rect.bottom()

            left = 2
            right = self.viewport().width() - 2
            painter.drawLine(left, y, right, y)

            radius = 6
            painter.setBrush(blue)
            painter.drawEllipse(QPoint(left + radius, y), radius, radius)

        painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(ExtTreeWidget.MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(ExtTreeWidget.MIME_TYPE):
            event.ignore()
            return
        pos = event.pos()
        item = self.itemAt(pos)

        if item is None:
            last = self._last_visible_item()
            if last is not None:
                rect = self.visualItemRect(last)
                if pos.y() < rect.top():
                    self._set_indicator(last, 'above')
                else:
                    self._set_indicator(last, 'below')
            else:
                self._clear_indicator()
        else:
            rect = self.visualItemRect(item)
            third = rect.height() / 3.0
            y = pos.y() - rect.top()
            if y < third:
                self._set_indicator(item, 'above')
            elif y > rect.height() - third:
                self._set_indicator(item, 'below')
            else:
                self._set_indicator(item, 'on')

        self._handle_hover_expand()

        event.accept()

    def dragLeaveEvent(self, event):
        self._clear_indicator()
        self._cancel_expand_timer()
        super().dragLeaveEvent(event)

    def normalize_row_heights(self):
        if not self.min_row_height and not self.max_row_height:
            return
        fm = self.fontMetrics()
        col_count = self.columnCount()
        viewport_w = self.viewport().width()
        def compute_height_for_item(item):
            max_text_h = 0
            for col in range(col_count):
                text = item.text(col) or ""
                if not text:
                    continue
                col_w = max(10, self.columnWidth(col))
                rect = fm.boundingRect(0, 0, col_w, 10000, Qt.TextWordWrap, text)
                max_text_h = max(max_text_h, rect.height())

            if max_text_h == 0:
                max_text_h = fm.height()

            padding = 8
            desired = max_text_h + padding

            desired = max(self.min_row_height, min(self.max_row_height, desired))
            return desired

        root = self.invisibleRootItem()
        stack = [root]
        while stack:
            parent = stack.pop()
            for i in range(parent.childCount()):
                it = parent.child(i)
                h = compute_height_for_item(it)
                it.setSizeHint(0, QtCore.QSize(-1, h))
                stack.append(it)

    def _set_row_height(self, item):
        if self.min_row_height is not None:
            for c in range(self.columnCount()):
                item.setSizeHint(c, QtCore.QSize(item.sizeHint(c).width() if item.sizeHint(c) else 0, self.min_row_height))

    def _apply_column_constraints(self, min_col_width, max_col_width, stretch_last_column):
        header = self.header()


        if stretch_last_column is not None:
            header.setStretchLastSection(bool(stretch_last_column))
        for c in range(self.columnCount()):
            w = self.columnWidth(c)
            if min_col_width is not None and w < min_col_width:
                self.setColumnWidth(c, min_col_width)
            if max_col_width is not None and w > max_col_width:
                self.setColumnWidth(c, max_col_width)

    def mimeTypes(self):
        return [ExtTreeWidget.MIME_TYPE]

    def iter_items_preorder(self):
        for i in range(self.topLevelItemCount()):
            yield from self._iter_subtree(self.topLevelItem(i))

    def _iter_subtree(self, item: QtWidgets.QTreeWidgetItem):
        yield item
        for i in range(item.childCount()):
            yield from self._iter_subtree(item.child(i))

    def apply_alternate_colors(self):
        index = 0
        if not self._even_color and not self._odd_color:
            return
        def walk(parent = None):
            nonlocal index
            count = parent.childCount() if parent else self.topLevelItemCount()
            for i in range(count):
                item = parent.child(i) if parent else self.topLevelItem(i) # type: ExtTreeWidgetItem
                color = self._even_color if (index % 2 == 0) else self._odd_color
                brush = QtGui.QBrush(color)
                for col in range(self.columnCount()):
                    if col not in item.background_changed:
                        item.setBackground(col, brush)
                index += 1
                if item.childCount() > 0 and item.isExpanded():
                    walk(item)
        walk()

    def __on_expand(self, index: QtCore.QModelIndex, *args, **kwargs):
        item: ExtTreeWidgetItem = self.itemFromIndex(index)
        style = self.style()
        base_padding = 14
        if self.width_first_column and self.resize_first_column_after_expand:
            current_width = self.columnWidth(0)
            new_width = style.pixelMetric(QtWidgets.QStyle.PM_LayoutLeftMargin) * item.level + base_padding + self.width_first_column
            if current_width < new_width:
                self.setColumnWidth(0, new_width)
        self.apply_alternate_colors()

    def set_row_colors(self, odd_color, even_color):
        if None in (odd_color, even_color):
            return
        if isinstance(odd_color, str):
            odd_color = QtGui.QColor(odd_color)
        if isinstance(even_color, str):
            even_color = QtGui.QColor(even_color)
        self._odd_color = odd_color
        self._even_color = even_color
        self.apply_alternate_colors()

    def _prepare_data_for_user_insert1(self, data: list[dict], level: int = 0, children = None):

        if children is None:
            children = []
        data = prepare_data_for_fill(data, nick_name_level=self.nick_name_level, nick_name_uuid=self.nick_name_uuid)

        return [
            {
                'texts': item.user_data,
                'level': item.level,
                'children': children,
                'uuid': item.uuid_,
                'system_props': item.system_data}
            for item in data
        ]
    def _prepare_data_for_user_insert(self, data: list[dict],
                                      parent_instance: ExtTreeWidgetItem = None,
                                      into: bool = False,
                                      after: bool = False
                                      ):

        table_data = prepare_data_for_fill(data, nick_name_level=self.nick_name_level, nick_name_uuid=self.nick_name_uuid)
        if parent_instance is None:
            parents = { -1: None }
        else:
            parents = {}
        ui_index = None
        prev_lvl = None
        delta = 0

        for row_idx, row_data in enumerate(table_data): # type: RowData
            if ui_index is not None and prev_lvl is not None and prev_lvl == row_data.level and not after:
                ui_index += 1
            else:
                ui_index = None
            if row_idx == 0 and parent_instance is not None:
                delta = parent_instance.level - row_data.level
                if into:
                    delta += 1
                    parents[parent_instance.level] = parent_instance
                else:
                    parent_of_parent: ExtTreeWidgetItem = parent_instance.parent()
                    if parent_of_parent is None:
                        ui_index = self.indexOfTopLevelItem(parent_instance)
                        parents[-1] = None
                    else:
                        ui_index = parent_of_parent.indexOfChild(parent_instance)
                        parent_instance = parent_of_parent
                        parents[parent_of_parent.level] = parent_of_parent

            lvl = row_data.level + delta
            if lvl is None:
                lvl = 0
            data_for_fill = self._prepare_text_for_item(row_data.user_data)
            item = ExtTreeWidgetItem(data_for_fill, lvl, object_uuid=row_data.uuid_, system_data=row_data.system_data)
            if ui_index is not None:
                ui_index = ui_index + int(after)
            if into and not after:
                ui_index = 0
            if self.min_row_height is not None:
                for c in range(self.columnCount()):
                    item.setSizeHint(c, QtCore.QSize(item.sizeHint(c).width() if item.sizeHint(c) else 0, self.min_row_height))
            if lvl == 0:
                if ui_index is not None:
                    self.insertTopLevelItem(ui_index, item)
                else:
                    # if root_placed and self.one_root:
                    #     continue
                    # root_placed = True
                    self.addTopLevelItem(item)
                parents[0] = item
            else:
                parent = parents.get(lvl-1)
                if parent is None:
                    candidate_level = lvl-1
                    while candidate_level >= 0 and parents.get(candidate_level) is None:
                        candidate_level -= 1
                    parent: ExtTreeWidgetItem = parents.get(candidate_level)
                if parent is None:
                    if ui_index is not None:
                        self.insertTopLevelItem(ui_index, item)
                    else:
                        self.addTopLevelItem(item)
                else:
                    if ui_index is not None:
                        parent.insertChild(ui_index, item)
                    else:
                        parent.addChild(item)
                parents[lvl] = item
            prev_lvl = row_data.level
            # ui_index = None
        if parent_instance is not None:
            return self.restruct_level_by_item([parent_instance])
        return self.restruct_level_by_item(self._rows_generator())

    def _clear_table(self):
        self.clear()
        self.property_manager = None

    def _rows_generator(self) -> typing.Generator[ExtTreeWidgetItem, None, None]:
        def recurse(parent_item):
            for i in range(parent_item.childCount()):
                ch = parent_item.child(i)
                yield ch
                yield from recurse(ch)
        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            yield top
            yield from recurse(top)

class ExtTreeWidget(BaseTreeWidget):
    """
        Расширенная версия QtWidgets.QTreeWidget
        --------------------------------------------------------------------------------------
        Параметры:
            @old_tree_instance: Заменяемый объект QTreeWidget
            @ui_instance: Объект self.ui на котором был инициализирован прежний QTreeWidget
        Структура классов с открытым интерфейсом
            - ExtTreeWidget  Класс дерева
            -- ExtTreeWidgetItem Класс строки
            --- ExtTreeWidgetColumn Класс ячейки в строке
        Пример:
            ExtTreeWidget(old_tree_instance=self.ui.tree_base_tree, ui_instance=self.ui)
    """
    def iter_rows(self) -> list[ExtTreeWidgetItem]:
        out = []
        def recurse(parent_item):
            for i in range(parent_item.childCount()):
                ch = parent_item.child(i)
                out.append(ch)
                recurse(ch)
        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            out.append(top)
            recurse(top)
        return out

    def get_item_by_value(
            self,
            value,
            column: int = None,
            many: bool = False
    ) -> ExtTreeWidgetColumn | list[ExtTreeWidgetColumn] | None:
        """
        Поиск элемента таблицы по значению

        @value искомый текст
        @column Колонка для поиска (если None поиск по всем)
        @many Если True возврат всех совпадений/ Если False возврат первого совпадения
        """
        elements = []
        for item in self.iter_rows(): # type: ExtTreeWidgetItem
            if column is not None:
                if str(item.text(column)).strip() == str(value).strip():
                    elements.append(
                        ExtTreeWidgetColumn(tree=self,item=item,column=column
                        )
                    )
            else:
                for col in range(item.columnCount()):
                    if str(item.text(col)).strip() == str(value).strip():
                        elements.append(
                            ExtTreeWidgetColumn(tree=self, item=item, column=col
                            )
                        )
        if not elements:
            return None
        if many:
            return elements
        return elements[0]


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
        system_fields_prefix: str = '__'
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
        @resize_first_column_after_expand: Изменять размер первой колонки после раскрытия дочерних элентов
        """
        self._clear_table()
        self.setSelectionMode(selection_mode)
        self.setSelectionBehavior(selection_behavior)
        if draggable:
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setAnimated(True)
            self.setDropIndicatorShown(False)
        self.min_col_width = min_col_width
        self.max_col_width = max_col_width
        self.stretch_last_column = stretch_last_column
        self.min_row_height = min_row_height
        self.max_row_height = max_row_height
        self.nick_name_level = nick_name_level
        self.nick_name_uuid = nick_name_uuid
        self.hover_indicator_color = hover_indicator_color
        self.system_fields_prefix = system_fields_prefix
        self.resize_first_column_after_expand = resize_first_column_after_expand

        self.install_branch_and_selection_icons(
            branch_icon_if_can_open,
            branch_icon_if_can_close,
            selected_item_color,
            hover_item_color,
        )
        header = None
        list_of_data = []

        if type(dict_or_list) == type(dict()):
            list_of_data = F.dict_of_dicts_to_list_of_lists(dict_or_list)
        if type(dict_or_list) == type(['']):
            if type(dict_or_list[0]) == type(dict()):
                list_of_data = F.list_of_dicts_to_list_of_lists(dict_or_list)
            else:
                if not isinstance(dict_or_list[0], list):
                    dict_or_list = [[_] for _ in dict_or_list]
                list_of_data = dict_or_list

        cp_data = copy.deepcopy(list_of_data)
        table_data: TableData = prepare_data_for_fill(cp_data, nick_name_uuid, nick_name_level,
                                                      property_prefix=system_fields_prefix)
        if hide_horizontal_header:
            self.header().hide()
        else:
            header = table_data.user_headers
            self.setHeaderLabels(header)
            self.header().show()
            self.width_first_column = self.columnWidth(0)
        self.setRootIsDecorated(not hide_root_decorations)

        headers = [self.headerItem().text(c) for c in range(self.columnCount())]

        parents = { -1: None }

        def fill_empty_places(struct: list[list], length: int):
            cp_struct = copy.deepcopy(struct)
            for idx, item in enumerate(struct):
                if len(item) < length:
                    cp_struct[idx].extend([''] * (length - len(item)))
            return cp_struct

        root_placed = False

        for row_idx, row_data in enumerate(table_data): # type: RowData
            lvl = row_data.level
            if lvl is None:
                lvl = 0
            data_for_fill = self._prepare_text_for_item(row_data.user_data)
            item = ExtTreeWidgetItem(data_for_fill, lvl, object_uuid=row_data.uuid_, system_data=row_data.system_data)
            if min_row_height is not None:
                for c in range(self.columnCount()):
                    item.setSizeHint(c, QtCore.QSize(item.sizeHint(c).width() if item.sizeHint(c) else 0, min_row_height))
            if lvl == 0:
                if root_placed and one_root:
                    continue
                root_placed = True
                self.addTopLevelItem(item)
                parents[0] = item
            else:
                parent = parents.get(lvl-1)
                if parent is None:
                    candidate_level = lvl-1
                    while candidate_level >= 0 and parents.get(candidate_level) is None:
                        candidate_level -= 1
                    parent = parents.get(candidate_level)
                if parent is None:
                    self.addTopLevelItem(item)
                else:
                    parent.addChild(item)
                parents[lvl] = item

        self._apply_column_constraints(min_col_width, max_col_width, stretch_last_column)

        if max_row_height is not None:
            for it in self.iter_items_preorder():
                for c in range(self.columnCount()):
                    sh = it.sizeHint(c)
                    if sh is not None and sh.height() > max_row_height:
                        it.setSizeHint(c, QtCore.QSize(sh.width(), max_row_height))

        self.set_row_colors(odd_item_color, even_item_color)
        self.normalize_row_heights()

    def dump_as_table(self, rez_dict: bool = False,
                      level_nickname: str = None,
                      uuid_nickname: str = None
        ) -> list[dict] | list[list]:
        if level_nickname is None:
            level_nickname = self.nick_name_level if self.nick_name_level else 'Уровень'
        if uuid_nickname is None:
            uuid_nickname = self.nick_name_uuid if self.nick_name_uuid else 'UUID'
        rows = []
        for it in self.iter_items_preorder(): # type: ExtTreeWidgetItem
            rows.append(it.to_dict(nick_name_uuid=uuid_nickname, nick_name_level=level_nickname))
        if not rez_dict:
            return F.list_of_dicts_to_list_of_lists(rows)
        return rows

    def dump_as_nested(
            self,
            children_key: str = 'children',
            uuid_key: str = 'uuid',
            system_props_key: str = 'system_props',
            level_key: str = 'level'
    ) -> list:
        """
        Получить представление структуры с вложенностью
        -----------------------------------------------------------------
            @children_key: Ключ размещения вложенных объектов.
            @uuid_key: Ключ размещения уникального идентификатора строки.
            @level_key: Ключ размещение уровня вложенности.
            @system_props_key: Ключ размещения системных атрибутов
        """
        def build_node(it: ExtTreeWidgetItem):
            data = {self.headerItem().text(c): it.text(c) for c in range(self.columnCount())}
            node = {
                'data': data,
                system_props_key: it.system_fields,
                uuid_key: it.uuid,
                level_key: int(it.data(0, ExtTreeWidgetItem.LEVEL_ROLE) or 0),
                children_key: []
            }
            for i in range(it.childCount()):
                node[children_key].append(build_node(it.child(i)))
            return node

        out = []
        for i in range(self.topLevelItemCount()):
            out.append(build_node(self.topLevelItem(i)))
        return out

    def num_column_by_name(self, name: str):
        """
            Индекс колонки по имени
        """
        header_item = self.headerItem()
        for column in range(self.columnCount()):
            if header_item.text(column) == name:
                return column
        return None

    def insert_before(self, row: int = None, *values: dict[str, typing.Any], into: bool = False):
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
        if row is not None:
            prev_item = self.get_item_by_logical_index(row)
            if prev_item is None:
                return
            return self._prepare_data_for_user_insert(values, prev_item, into=into)
        return self._prepare_data_for_user_insert(values, None, into=True)


    def insert_after(self, logical_index: int = None, *values: dict[str, typing.Any], into: bool = False):
        """
        Вставить строку/строки после указанной строкой
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
        if logical_index is not None:
            prev_item = self.get_item_by_logical_index(logical_index)
            if prev_item is None:
                return
            return self._prepare_data_for_user_insert(values, prev_item, into=into, after=True)
        return self._prepare_data_for_user_insert(values, None, into=True, after=True)


    def currentItem(self) -> ExtTreeWidgetItem | None:
        """Получить текущий выделенный объект"""
        return super().currentItem()

    @property
    def current_row(self) -> int | None:
        """Получить индекс логической структуры
                или None если не найдено"""
        item = self.currentItem()
        if item:
            return item.current_index
        return None

    def get_item_by_logical_index(self, logical_index: int) -> ExtTreeWidgetItem | None:
        """Получить объект строки ExtTreeWidgetItem по логическому индексу"""
        rows = self.iter_rows()
        if len(rows) < int(logical_index):
            logger.info(f'Элемент с индексом {logical_index} не найден!')
            return None
        return rows[int(logical_index)]

    def get_item_by_uuid(self, uuid: str) -> ExtTreeWidgetItem | None:
        generator = (item for item in self._rows_generator() if item.uuid == uuid)
        return next(generator, None)

    def remove_row(self, logical_index: int):
        """Удалить объект строки ExtTreeWidgetItem по логическому индексу"""
        item = self.get_item_by_logical_index(logical_index)
        if not item:
            return
        parent = item.parent()
        parent.removeChild(item)

    def countRows(self) -> int:
        rows = self.iter_rows()
        return len(rows)


if __name__ == '__main__':
    """
        Структура классов с открытым интерфейсом
        - ExtTreeWidget  Класс дерева
        -- ExtTreeWidgetItem Класс строки
        --- ExtTreeWidgetColumn Класс ячейки в строке
    """


    from project_cust_38 import Cust_SQLite as CSQ
    from project_cust_38 import Cust_config as CFG


    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    w = QtWidgets.QWidget(window)
    w.setWindowTitle('Древо')
    w.resize(1360, 768)
    window.resize(1360, 768)
    layout = QtWidgets.QHBoxLayout(w)
    old_tree_1 = QtWidgets.QTreeWidget()
    old_tree_2 = QtWidgets.QTreeWidget()


    tree1 = ExtTreeWidget(old_tree_1, ui_instance=window)
    tree2 = ExtTreeWidget(old_tree_2, ui_instance=window)
    data2 = CSQ.custom_request_c(
        CFG.Config.project.db_resxml,
        'SELECT data FROM res WHERE Номер_мк = 5310',
        rez_dict=True,
        one=True
    )
    data = pickle.loads(data2['data'])
    import datetime
    # TODO СТИЛИЗАЦИЯ
    data_for_table_2 = [
        {'Наименование': 'Т1_Элемент 1', 'Доп колонка': 'фыв', 'Уровень': 0,
             '__test': 'qwe',
             '__pickle': data2['data'],
             '__datetime': datetime.datetime.now()
         },
        {'Наименование': 'Т1__элемент 1', 'Доп колонка': 'йцу', 'Уровень': 1},
        {'Наименование': 'Т1___элемент 1', 'Доп колонка': 'йцупп', 'Уровень': 2},
        {'Наименование': 'Т1_Элемент 2', 'Доп колонка': 'ар', 'Уровень': 0},
        {'Наименование': 'Т1__элемент 1', 'Доп колонка': 'варвар', 'Уровень': 1},
        {'Наименование': 'Т1__элемент 1', 'Доп колонка': 'варвар', 'Уровень': 2},
        {'Наименование': 'Т1__элемент 1', 'Доп колонка': 'варвар', 'Уровень': 3},
        {'Наименование': 'Эмуляция сломанного слота', 'Уровень': 2},
    ]
    tree1.fill_table(#TODO ЗАПОЛНЕНИЕ
        data,
        min_row_height=26,
        hide_horizontal_header=False,
        min_col_width=80,
        stretch_last_column=True,
        nick_name_level='Уровень',
        # nick_name_uuid='Наименование',
        odd_item_color='#ffffff',
        even_item_color='#f0f8ff',
        hover_indicator_color=(233, 233, 111),
        # branch_icon_if_can_close='./Mkarti/icons/1.ico',
        hover_item_color="#91916a"
    )
    tree2.fill_table(data_for_table_2, hide_horizontal_header=False, min_col_width=80, stretch_last_column=True,
                               nick_name_level='Уровень')

    def my_func(*args, **kwargs):
        print()

    for row_item in tree1.iter_rows(): # ИТЕРАЦИЯ СТРОК ПО Y
        print(row_item.to_dict()) #  каждую строку из ui можно конвертировать в dict
        for column_item in row_item.iter_column_by_row():  # ИТЕРАЦИЯ КОЛОНОК ПО X СТРОКИ
            print(column_item.text) # Доступ к тексту ячейки

    item = tree1.iter_rows()[2]

    # Добавление комбобокса
    item.add_combobox(tree1.num_column_by_name('Код ERP'), conn_func=my_func, values=['a', 'b', 'c'], first_void=False)

    # Добавление
    item.add_label_link(6, file=r'C:\Users\A.A.Fedorov\Work folders\Documents\2\test.txt', name='test_name', parent_self=tree1)

    # Добавление чекбокса
    item.add_check_box(3, conn_func=my_func)

    #  Добавление кнопки
    item.add_button(tree1.num_column_by_name('Уровень'), conn_func=my_func)
    column_count_ed = tree1.num_column_by_name('Количеств_ед')
    tree1.iter_rows()[3].set_column_style(column=2, bold=True, background_color='red')

    # Добавление интерактивного лэйбла
    i_l = tree1.iter_rows()[0].add_interactive_label(
        2,
        'Тест'
    )
    i_l.add_button('B', on_clicked=my_func)
    i_l.add_button('A', on_clicked=my_func)

    # Поиск элементов по имени
    a = tree1.get_item_by_value('АСО.400000И', many=True)

    count = 0
    variants = [
        [{'Наименование': 'qweqwe'}, {'Наименование': 'qweqwe2'}, {'Наименование': 'qweqwe3'}], # Без уровня
        [{'Уровень': 1, 'Наименование': f'Test : {count}'},
                           {'Уровень': 3, 'Наименование': f'Test : {count + 1}'},
                           {'Уровень': 4, 'Наименование': f'Test : {count + 2}'},
                           {'Уровень': 5, 'Наименование': f'Test : {count + 3}'},
                           {'Уровень': 6, 'Наименование': f'Test : {count + 4}'},
                           {'Уровень': 3, 'Наименование': f'Test : {count + 5}'},
                           {'Уровень': 2, 'Наименование': f'Test : {count + 6}'}], # С разрывом
        [{'Уровень': 3, 'Наименование': f'Test : {count}'},
                           {'Уровень': 3, 'Наименование': f'Test : {count + 1}'},
                           {'Уровень': 4, 'Наименование': f'Test : {count + 2}'},
                           {'Уровень': 5, 'Наименование': f'Test : {count + 3}'},
                           {'Уровень': 6, 'Наименование': f'Test : {count + 4}'},
                           {'Уровень': 3, 'Наименование': f'Test : {count + 5}'},
                           {'Уровень': 2, 'Наименование': f'Test : {count + 6}'},] # С высоким урвнем старта и двойной вложенностью в середине

    ]

    btn_dump = QtWidgets.QPushButton('дамп')
    btn_ctrl_shift_p = QtWidgets.QPushButton('Ctrl shift p')
    btn_insert_before = QtWidgets.QPushButton('Вставить перед')
    btn_insert_after = QtWidgets.QPushButton('Вставить после')
    btn_get_uuid = QtWidgets.QPushButton('Выдать UUID элемента')
    expand_parents = QtWidgets.QPushButton('Раскрыть родителей')
    reload_row = QtWidgets.QPushButton('Замена строки')
    btn_get_uuid.setFocusPolicy(QtCore.Qt.StrongFocus)

    line_edit = QtWidgets.QLineEdit()
    label_uuid = QtWidgets.QLabel()
    check_uuid = QtWidgets.QCheckBox()
    combo = QtWidgets.QComboBox()
    combo_variants = QtWidgets.QComboBox()

    def on_dump(*args, **kwargs):
        table = __get_current_table()
        dump = table.dump_as_table(rez_dict=True) # Дамп списком
        dump2 = table.dump_as_nested() # Дамп с вложенностями

    def insert_before(window, tree, line, *args, **kwargs):
        idx = line.text()
        tree_name = combo.currentText()
        table = globals().get(tree_name)
        if not idx:
            idx = table.current_row
        var = variants[int(combo_variants.currentText())]

        table.insert_before(idx,  *var, into=check_uuid.isChecked())

    def __get_current_table():
        tree_name = combo.currentText()
        return globals().get(tree_name)

    count = 0
    def insert_after(window, tree, *args, **kwargs):
        global count
        table = __get_current_table()
        idx = table.current_row
        count += 1
        var = variants[int(combo_variants.currentText())]
        table.insert_after(idx, *var, into=check_uuid.isChecked())


    btn_dump.clicked.connect(on_dump)
    from project_cust_38 import Cust_Qt as CQT
    def on_ctrl_shift_p(window, table):
        CQT.msgboxg_get_table(window, msg='test', dict_or_list=table.dump_as_table(rez_dict=True),
                              btn0_name='ОК', disable_btn1=True, load_summ=True,
                          sortingEnabled=True)

    def on_click_get_uuid(window, table, label, check):
        if check.isChecked():
            table = tree2
        item = table.currentItem()

        if not item:
            return
        uu = item.uuid
        label.setText(item.uuid)

    def on_click_expand_parents(window, table, label, check):
        row = line_edit.text()
        item = tree1.get_item_by_logical_index(row)
        item.expand_parents()
    def on_click_reload(*args):
        global count
        row = line_edit.text()
        table = __get_current_table()
        item = table.get_item_by_logical_index(row)
        count += 1
        item.reload_row({'Наименование': f'test{count}', '__sys_col': 'Рандомная строка'.encode('utf8'), '__sys_date': datetime.datetime.now()})

    btn_dump.clicked.connect(on_dump)
    btn_ctrl_shift_p.clicked.connect(lambda: on_ctrl_shift_p(window, tree1))
    btn_insert_before.clicked.connect(lambda: insert_before(window, tree1, line_edit))
    btn_insert_after.clicked.connect(lambda: insert_after(window, tree1))
    btn_get_uuid.clicked.connect(lambda: on_click_get_uuid(window, tree1, label_uuid, check_uuid))
    expand_parents.clicked.connect(lambda: on_click_expand_parents(window, tree1, label_uuid, check_uuid))
    reload_row.clicked.connect(on_click_reload)

    combo.addItems(['tree1', 'tree2'])
    combo_variants.addItems(list(str(num) for num in range(len(variants))))

    vl = QtWidgets.QVBoxLayout()
    vl.addWidget(combo)
    vl.addWidget(combo_variants)
    layout.addWidget(tree1, 3)
    layout.addWidget(tree2, 3)
    layout.addLayout(vl, 1)
    vl.addWidget(btn_dump)
    vl.addWidget(btn_ctrl_shift_p)
    vl.addWidget(reload_row)

    # test btn insert before
    layout_insert_before = QtWidgets.QHBoxLayout()
    vl.addLayout(layout_insert_before)
    layout_insert_before.addWidget(btn_insert_before)
    layout_insert_before.addWidget(line_edit)

    layout_get_uuid = QtWidgets.QHBoxLayout()
    vl.addLayout(layout_get_uuid)
    layout_get_uuid.addWidget(btn_get_uuid)
    layout_get_uuid.addWidget(label_uuid)
    layout_get_uuid.addWidget(check_uuid)

    vl.addWidget(expand_parents)

    vl.addWidget(btn_insert_after)
    window.show()
    sys.exit(app.exec_())
