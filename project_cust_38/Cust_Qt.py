import copy
import pathlib
import typing

import requests
import subprocess
from collections import namedtuple, defaultdict, deque
from dataclasses import dataclass, field
from functools import partial
from itertools import count
import inspect
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import QStyledItemDelegate, QMainWindow, QTableWidget, QHeaderView, QApplication, QTabWidget
from PyQt5.QtGui import QPixmap, QPen, QColor
from PyQt5.QtCore import Qt ,QObject, QEvent, QSignalBlocker
import project_cust_38.border_painter as CBPAINT
import project_cust_38.Cust_Functions as F
import os
import time
import sys
import linecache
import traceback
import re
import operator
import project_cust_38.Cust_Excel as CEX
import urllib

from isapi.samples.redirector_with_filter import Filter
from project_cust_38.Cust_Functions import num_col_by_name_in_hat_c

if __name__ == '__main__':
    exit()

from typing import Iterable, Any, Callable, NamedTuple
import ast
from datetime import datetime
from dateutil import parser


ERP_CSS = """
        QTableWidget {
            border: none; /* Убираем общий бордер */
            gridline-color: transparent;
        }
        
        QTableWidget::item {
            border-right: 0px solid rgb(254,254,254); /* Вертикальные границы ячеек белые */
            border-bottom: 1px solid rgb(230,230,230); /* Горизонтальные границы ячеек серые */
        }


        QTableWidget::item {
            background-color: rgb(254,254,254); /* Цвет выделенной ячейки */
           
        }
                    QTableWidget::item:selected {
            background-color: rgb(254,242,199); /* Цвет выделенной ячейки */
            border: 0px solid rgb(250,204,31); /* Темный контур для выделенной ячейки */
            color: rgb(40,40,40);
        }

        QTableWidget::item:selected:focus {
            background-color: rgb(243,230,143); /* Светло-желтый цвет для выделенной строки */
             border: 1px solid rgb(250,204,31); /* Темный контур для выделенной ячейки */
             color: rgb(40,40,40);
        }
        
        QHeaderView::section {
    background-color: rgb(242,242,242); /* Цвет фона заголовков */
    color: black; /* Цвет текста заголовков */
    border: 1px solid rgb(204,204,204);
}
                    """

class DataTypes:
    class BaseType:
        alias: str = ''
        params: list = []
        default: str = ''
        rgba: tuple[int] = (255, 255, 255, 0)

    class IntType:
        alias: str = 'int'
        params: list = ['Мин', 'Макс', 'Сумма', 'Количество']
        default: str = 'Сумма'
        rgba: tuple[int] = (173, 216, 230, int(255 / 6))

    class FloatType(IntType):
        alias: str = 'float'
        rgba: tuple[int] = (144, 238, 144, int(255 / 6))

    class StrType:
        alias: str = 'str'
        params: list = ['Первое', 'Последнее', 'Количество']
        default: str = 'Сумма'
        rgba: tuple[int] = (155, 216, 155, int(255 / 6))

    class DateType:
        alias: str = 'date'
        params: list = ['Мин', 'Макс', 'Мин/Макс']
        default: str = 'Мин/Макс'
        rgba: tuple[int] = (255, 255, 0, int(255 / 6))

    class DateTimeType(DateType):
        alias: str = 'datetime'
        rgba: tuple[int] = (240, 248, 255, int(255 / 6))

    types_params = {
        'int': IntType,
        'float': FloatType,
        'str': StrType,
        'date': DateType,
        'datetime': DateTimeType
    }

    def __getitem__(self, item):
        return self.types_params.get(item, self.BaseType)

    def is_date(self, value: Any) -> datetime | None:
        try:
            date = parser.parse(value)
            if date.year > 1900 and date.year < 2100:
                return date
        except (Exception, parser.ParserError, ValueError) as e:
            return

    def extract_dates(self, date_time_str, date_format) -> tuple[datetime, datetime] | tuple[None, None]:
        date_time_pattern = r"""^(?P<start>\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?)/(?P<stop>\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?)$"""
        match = re.match(date_time_pattern, date_time_str)
        if match:
            start = match.group('start')
            stop = match.group('stop')
            return datetime.strptime(start, date_format), datetime.strptime(stop, date_format)
        return None, None


class Grouper:
    def __init__(self, data: list[dict], group_columns: list[str], sum_columns: list[str], header_types: dict[str, DataTypes.BaseType],
                 additional_params) -> None:
        self.data = data
        self.groups = {}
        self.group_columns = group_columns
        self.sum_columns = sum_columns
        self.header_types = header_types
        self.additional_params = additional_params
        self.parse(data, group_columns, sum_columns, header_types)

    def parse(self, data, group_columns, sum_columns, header_types):
        for row in data:
            unique_key = tuple(row[key] for key in group_columns)
            if unique_key in self.groups:
                self.groups[unique_key].aggregate_row(row)
            else:
                self.groups[unique_key] = Group(row, group_columns, sum_columns, header_types, self.additional_params)

    def prepare_item(self, item: dict):
        result_item = {}
        retype_cols = set()
        for key, value in item.items():
            if key in self.additional_params and self.additional_params[key] == 'Мин/Макс':
                if '/' in value:
                    min_val, max_val = value.split('/')
                else:
                    min_val = max_val = value
                result_item.update({f'{key}(Мин)': min_val, f'{key}(Макс)': max_val})
                retype_cols.add(key)
            else:
                result_item[key] = value
        for column in retype_cols:
            if column in self.header_types:
                data_type = self.header_types.pop(column)
                self.header_types[f'{column}(Мин)'] = data_type
                self.header_types[f'{column}(Макс)'] = data_type
        return result_item

    def to_list(self):
        return [self.prepare_item(group.item) for key, group in self.groups.items()]


class Group:
    FORMATS = {
        'date': '%Y-%m-%d',
        'datetime': '%Y-%m-%d %H:%M:%S',
    }

    def __init__(self, row: dict, group_columns: list[str], sum_columns: list[str], header_types: dict[str, DataTypes.BaseType],
                 additional_params):
        self.data_types = DataTypes()
        self.group_columns = set(row.keys()).intersection(group_columns)
        self.sum_columns = set(row.keys()).intersection(sum_columns)
        self.header_types = header_types
        self.additional_params = additional_params
        self.item = {key: self.prepare_value(key, value) for key, value in row.items()}
        self.state_mutable = {key: False for key in self.item}

    def aggregate_row(self, row):
        cp_item = self.item.copy()
        for key in self.item:
            if key in self.sum_columns:
                param_key = self.additional_params.get(key)
                cp_item[key] = self.sum_values(cp_item[key], self.prepare_value(key, row[key]), self.header_types[key],
                                               param_key)
                self.state_mutable[key] = True
            elif row[key] != self.item[key]:
                self.state_mutable[key] = True
        self.item = cp_item

    def prepare_value(self, key, val):
        column_for_sum = self.sum_columns
        data_type = self.header_types[key]

        if key in column_for_sum:
            if key == '':
                return 0
            if data_type.alias in ('date', 'datetime'):
                if date_obj := self.data_types.is_date(val):
                    return date_obj.strftime('%Y-%m-%d %H:%M:%S')
                return ''
            if data_type.alias == 'str':
                if self.additional_params.get(key) == 'Количество':
                    return 0 if str(val).strip() == '' else 1
                return str(val)
            if data_type.alias in ('int', 'float'):
                try:
                    return float(val)
                except ValueError:
                    return 0
        return val

    def sum_values(self, val1, val2, data_type: DataTypes.BaseType, param_key: dict):
        try:
            if data_type.alias in ('datetime', 'date'):
                return self.sum_date(val1, val2, param_key, date_format=self.FORMATS.get(data_type.alias))
            if data_type.alias in ('str',):
                return self.sum_string(val1, val2, param_key)
            if data_type.alias in ('int', 'float'):
                return self.sum_numeric(val1, val2, param_key)
        except Exception as e:
            print(e)
        return 0

    def sum_numeric(self, val1, val2, params_key: str):
        prev_val_is_num = F.is_numeric(val1)
        target_val_is_num = F.is_numeric(val2)
        if not target_val_is_num:
            return val1
        if not prev_val_is_num:
            if target_val_is_num:
                return float(val2)
            return float()
        if params_key == 'Мин' :
            if float(val1) > float(val2):
                return float(val2)
        elif params_key == 'Макс' :
            if float(val1) < float(val2):
                return float(val2)
        elif params_key == 'Сумма':
            return float(val1) + float(val2)
        return 0

    def sum_string(self, val1, val2, params_key: dict):
        cleaned_prev_val = str(val1).strip()
        cleaned_target_val = str(val2).strip()
        if params_key == 'Первое':
            if cleaned_prev_val != '':
                return cleaned_prev_val
            else:
                return cleaned_target_val
        elif params_key == 'Последнее':
            if cleaned_target_val != '':
                return cleaned_target_val
        elif params_key == 'Количество':
            if not F.is_numeric(cleaned_prev_val):
                return 0 if cleaned_target_val == '' else 1
            return int(cleaned_prev_val) + 1
        return ''


    def sum_date(self, val1, val2, params_key: dict, date_format: str = '%Y-%m-%d'):
        old_date_obj = self.data_types.is_date(val1)
        current_date_obj = new_state = self.data_types.is_date(val2)
        if not current_date_obj:
            return val1
        if params_key == 'Мин/Макс':
            start, stop = self.data_types.extract_dates(val1, date_format)
            if start and stop:
                start = current_date_obj if start > current_date_obj else start
                stop = current_date_obj if stop < current_date_obj else stop
            else:
                if old_date_obj and current_date_obj:
                    start = current_date_obj if old_date_obj > current_date_obj else old_date_obj
                    stop = current_date_obj if old_date_obj < current_date_obj else old_date_obj
                else:
                    start = stop = current_date_obj
            return '/'.join((
                start.strftime(date_format),
                stop.strftime(date_format)
            ))
        if params_key == 'Мин':
            if old_date_obj:
                old_date_obj = datetime.strptime(val1, date_format)
                new_state = current_date_obj if old_date_obj > current_date_obj else old_date_obj
            return new_state.strftime(date_format)
        if params_key == 'Макс':
            if old_date_obj:
                old_date_obj = datetime.strptime(val1, date_format)
                new_state = current_date_obj if old_date_obj < current_date_obj else old_date_obj
            return new_state.strftime(date_format)
        return ''

    def __eq__(self, other):
        unique_key = tuple(self.item[key] for key in self.group_columns)
        return unique_key == other

    def __hash__(self):
        return hash(tuple(self.item[key] for key in self.group_columns))


class DataParser:
    def __init__(self, data: list[dict], add_params = None):
        self.data_types = DataTypes()
        self.add_params = add_params
        hat = self.unpack_header(data)
        self.header_types = self.get_hat_data_types(hat, data)
        self.header = hat
        self.body = self.clear_data(data)
        self.current_groups = None

    def make_fields_data_for_table(self, exclude_aggregated: bool = False, sum_cols = None, group_cols = None):
        if sum_cols is None or group_cols is None:
            sum_cols = self.dump_groups.sum_columns
            group_cols = self.dump_groups.group_columns
        return [
            {'Поля': head, 'Тип': data_type.alias, 'ВидСуммы': 'Первое', 'Видимость': ''}
            for head, data_type in self.header_types.items()
            if exclude_aggregated
               and head not in sum_cols
               and head not in group_cols
        ]

    def clear_data(self, data: list[dict]):
        return [row for row in data if any(row.values())]

    def unpack_header(self, data: list[dict]):
        if len(data) >= 1:
            return list(data[0].keys())

    def get_hat_data_types(self, header: list[str], body: list[list[str]]):
        data_types = {}
        types_factory = DataTypes()
        for idx, head in enumerate(header):
            types = defaultdict(int)
            for elem in body:
                value = elem[head]
                if str(value).strip():
                    data_type = self.calc_data_type(elem[head])
                    types[data_type] += 1
            if types:
                data_types[head] = types_factory[max(types, key=types.get)]
            else:
                data_types[head] = types_factory.BaseType
        return self.transform_types(data_types)

    def transform_types(self, types):
        transform = {'Количество': 'str'}
        if not isinstance(self.add_params, dict):
            return types
        cp_types = types.copy()
        for key, data_type in types.items():
            if key in self.add_params and self.add_params[key] in transform:
                new_type_key = transform[self.add_params[key]]
                cp_types[key] = self.data_types[new_type_key]
        return cp_types

    def calc_data_type(self, value: Any) -> str:
        value_type = '' if str(value).strip() == '' else 'str'
        try:
            converted_value = ast.literal_eval(str(value))
            return type(converted_value).__name__
        except (ValueError, SyntaxError) as e: ...
        if date_obj := self.data_types.is_date(value):
            type_object = 'datetime' if date_obj.hour or date_obj.minute or date_obj.second else 'date'
            return type_object
        return value_type

    def group_by_columns(self, group_by: list[str], sum_columns: list[str],
                         additional_params: dict[str, bool]) -> Grouper:
        header = self.header
        group_by = set(header).intersection(group_by)
        sum_columns = set(header).intersection(sum_columns)
        self.dump_groups = Grouper(self.body, group_by, sum_columns, self.header_types, additional_params)
        return self.dump_groups

    def reorder_dict(self, data: list[dict], keys: list[str]) -> list[dict]:
        result = []
        for item in data:
            item = item.copy()
            new_dict = {key: item[key] for key in keys if key in item}
            new_dict.update({key: item[key] for key in item if key not in keys})
            result.append(new_dict)
        return result

class HistoryStack:
    class StackElement(NamedTuple):
        data: list[dict]
        header_types: dict[str, DataTypes.BaseType]
        sum_elems: list[str]
        group_elems: list[str]
        fields_data: list[dict]
        grouper: Grouper | None
        visible_columns: list[str]

    def __init__(
            self,
            window: QtWidgets.QWidget,
            init_data: list[dict],
            fields_data: [list[dict]],
            header_types: dict[str, DataTypes.BaseType],
            visible_columns: list[str],
            stack_table: QtWidgets.QTableWidget,
            group_table: QtWidgets.QTableWidget,
            field_table: QtWidgets.QTableWidget,
            sum_table: QtWidgets.QTableWidget,
            data_table: QtWidgets.QTableWidget,
            name_edit_input: QtWidgets.QTableWidget,
            data_filter_table: QtWidgets.QTableWidget,
            data_sum_table: QtWidgets.QTableWidget,
            input_for_stack_name: QtWidgets.QLineEdit = None,
            decor_field_tbl: callable = None,
            decor_grouped_data: callable = None,
            fill_tbl_fields: callable = None,
            init_data_name: str = 'Заполнение',
    ) -> None:
        self.window = window
        self.__stack: dict[str, StackElement] = {}
        self.data_types = DataTypes()
        self.stack_table = stack_table
        self.stack_table.doubleClicked.connect(self.on_stack_elem_changed)
        self.input_for_stack_name = input_for_stack_name
        self.data_table = data_table
        self.data_filter_table = data_filter_table
        self.data_sum_table = data_sum_table
        self.field_table = field_table
        self.name_edit_input = name_edit_input
        self.init_data_name = init_data_name
        self.current_element_key = self.stack_name
        self.group_table = group_table
        self.sum_table = sum_table
        self.decor_field_tbl = decor_field_tbl
        self.decor_grouped_data = decor_grouped_data
        self.fill_tbl_fields = fill_tbl_fields
        self.stack_column_key = 'Название заполнения'
        self.add_block(init_data, header_types, [], [], fields_data, visible_columns)
        self.fill_stack_tbl()

    def clear_stack(self):
        self.sum_table.setRowCount(0)
        self.group_table.setRowCount(0)
        if len(self.__stack) > 1:
            first_key, first_value = next(iter(self.__stack.items())) # type: str, HistoryStack.StackElement
            self.__stack.clear()
            self.name_edit_input.setText('')
            self.add_block(
                data=first_value.data,
                header_types=first_value.header_types,
                sum_elems=first_value.sum_elems,
                group_elems=first_value.group_elems,
                fields_data=first_value.fields_data,
                visible_columns=first_value.visible_columns,
                grouper=first_value.grouper,
            )

    @property
    def stack_name(self):
        return f'{self.init_data_name} #{len(self.__stack) + 1}'

    def add_block(
            self,
            data: list[dict],
            header_types: dict[str, DataTypes.BaseType],
            sum_elems: list[str],
            group_elems: list[str],
            fields_data: list[dict],
            visible_columns: list[str],
            grouper: Grouper = None,
    ):
        stack_name = self.input_for_stack_name.text()
        if stack_name.strip() == '':
            stack_name = self.stack_name
        if stack_name in self.__stack and not msgboxgYN(f'Имя: {stack_name!r} уже содержится в списке групп перезаписать'):
            return

        self.__stack[stack_name] = self.StackElement(data, header_types, sum_elems, group_elems, fields_data, grouper, visible_columns)
        self.name_edit_input.setPlaceholderText(self.stack_name)
        self.fill_stack_tbl()
        last_index = len(self.__stack) - 1
        if last_index != -1:
            self.stack_table.clearSelection()
            self.stack_table.setCurrentCell(last_index, 0)
            self.on_stack_elem_changed()
            self.current_element_key = stack_name


    def drop_block(self, key: str):
        if bool(self.__stack.pop(key, None)):
            self.fill_stack_tbl()

    def list_elements(self):
        return list(self.__stack.keys())

    @property
    def current_data(self) -> StackElement:
        return self.__stack[self.current_element_key]

    def __getitem__(self, item) -> StackElement:
        return self.__stack.get(item)

    def __iter__(self):
        return iter(self.__stack.values())

    def on_stack_elem_changed(self, *args):
        col_num = num_col_by_name_c(self.stack_table, self.stack_column_key)
        cur_row = self.stack_table.currentRow()
        if cur_row != -1 and col_num is not None:
            cur_element = self.stack_table.item(cur_row, col_num).text()
            if self.current_element_key != cur_element:
                self.current_element_key = cur_element
                stack_element = self[cur_element]
                fill_wtabl(stack_element.data, self.data_table)
                fill_summ_tbl(self, self.data_sum_table, self.data_table, hidden_scroll=True)
                fill_filtr_c(self.window, self.data_filter_table, self.data_table)
                self.fill_tbl_fields(stack_element.fields_data, stack_element.visible_columns)
                if stack_element.group_elems:
                    processed_groups = [{'Поля': group} for group in stack_element.group_elems]
                    fill_wtabl(processed_groups, self.group_table)
                else:
                    self.group_table.setRowCount(0)
                if stack_element.sum_elems:
                    processed_sum = stack_element.sum_elems
                    fill_wtabl(processed_sum, self.sum_table)
                    if self.decor_field_tbl:
                        self.decor_field_tbl(self.sum_table)
                else:
                    self.sum_table.setRowCount(0)
                if isinstance(stack_element.grouper, Grouper):
                    self.decor_grouped_data(stack_element.grouper)

    def fill_stack_tbl(self):
        tbl = self.stack_table
        elements = self.list_elements()
        data = [{self.stack_column_key: elem} for elem in elements]
        fill_wtabl(data, tbl)


class Ui_Dialog(object):
    def setupUi(self, Dialog,msg):
        Dialog.setObjectName("Dialog")
        Dialog.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtWidgets.QLabel(Dialog)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_2.setFont(font)
        self.label_2.setPixmap(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)).pixmap(24,
                                                                                                              24))
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.lbl_img = QtWidgets.QLabel(Dialog)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.lbl_img.setFont(font)
        self.lbl_img.setObjectName("lbl_img")
        self.horizontalLayout.addWidget(self.lbl_img)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.tbl = QtWidgets.QTableWidget(Dialog)
        self.tbl.setObjectName("tbl")
        self.tbl.setColumnCount(0)
        self.tbl.setRowCount(0)
        self.verticalLayout.addWidget(self.tbl)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog,msg)
        self.buttonBox.accepted.connect(Dialog.accept)  # type: ignore
        self.buttonBox.rejected.connect(Dialog.reject)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog,msg):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        # self.label_2.setText(_translate("Dialog", "IMG"))
        self.lbl_img.setText(_translate("Dialog", msg))


       
class msgboxg_актуальноИлиНет(QtWidgets.QDialog):  # диалоговое окно
    def __init__(self, parent, msg):
        self.myparent = parent
        super(msgboxg_актуальноИлиНет, self).__init__()
        self.ui3 = Ui_Dialog()
        self.ui3.setupUi(self, msg)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle("Заголовок")
        self.ui3.buttonBox.accepted.connect(self.Yes)
        self.ui3.buttonBox.rejected.connect(self.No)
        # self.app_icons()
        returnValue = self.show()
        self.dragPos = QtCore.QPoint()
        load_css(self)
        load_icons(self, 24)
        return returnValue

    def closeEvent(self, event):
        print("X is clicked")
    def Yes(self):
        print('Yes')
    def No(self):
        print('No')


class LoadingBar(QtWidgets.QDialog):
    def __init__(self, stylesheets = None):
        super().__init__()
        self.setWindowTitle('Загрузка...')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.ui = self
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedSize(800, 150)

        self.label = QtWidgets.QLabel()
        self.label.setWordWrap(True)
        self.label.setFixedWidth(self.progress_bar.width())
        self.label.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        font = self.label.font()
        font.setPointSize(12)
        font.setItalic(True)
        self.label.setFont(font)
        
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.progress_bar, 1, QtCore.Qt.AlignVCenter)
        self.layout.addWidget(self.label, 1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.layout)
        QtWidgets.QApplication.processEvents()
        if stylesheets:
            self.setStyleSheet(stylesheets)
        self.setStyleSheet(self.styleSheet() + """
            QLabel {
                    border-width: 0px;
            }""")
        
def progress_decorator(fn):
    """
    При старте обернутой функции появляется окно загрузки
    Функции передается в аргумент объект hook_prog_bar с тремя методами
    * open открыть окно
    * close закрыть окно
    * set назначить новое состояние загрузки
    * text назначить сообщение под шкалой загрузки
    """
    Hook = namedtuple('Hook', 'open,close,set,text')
    parent: QtWidgets.QMainWindow | None = None
    loading_bar: LoadingBar | None = None
    stylesheets = None
    hook_prog_bar: Hook | None = None

    def run_func(*args, **kwargs):
        if parent:
            parent.hide()
        try:
            result = fn(*args, **kwargs, hook_prog_bar=hook_prog_bar)
        except TypeError as e:
            if e.args and "got an unexpected keyword argument 'hook_prog_bar'" in e.args[0]:
                result = fn(*args, **kwargs)
            else:
                raise e
        if parent:
            parent.setHidden(False)
        return result

    def ui_loader(fn):
        def wrap(*args, **kwargs):
            fn(*args, **kwargs)
            QtWidgets.QApplication.processEvents()
        return wrap

    def startLoading(*args, **kwargs):
        nonlocal loading_bar, hook_prog_bar, parent, stylesheets
        if args[0] and isinstance(args[0], QtWidgets.QMainWindow):
            parent = args[0]
            stylesheets = parent.styleSheet()

        loading_bar = LoadingBar(stylesheets)
        loading_bar.show()
        hook_prog_bar = Hook(
            ui_loader(loading_bar.show),
            ui_loader(loading_bar.hide),
            ui_loader(loading_bar.progress_bar.setValue),
            ui_loader(loading_bar.label.setText)
        )
        result = run_func(*args, **kwargs)
        loading_bar.hide()
        return result

    def wrap(*args, **kwargs):
        return startLoading(*args, **kwargs)

    return wrap

def freeze_mouse_wheel(obj:QtWidgets.QComboBox):
    def wheel_event(event):
        event.ignore()


    obj.wheelEvent = wheel_event
    obj.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        
def fill_list_combobx(self,cmb,list_rows,list_colors=[],list_tooltip=[], sep_col = ';',first_void = False,list_bold=[]):
    cmb.clear()
    model = cmb.model()

    for i in range(len(list_rows)):
        entry = QtGui.QStandardItem(list_rows[i])
        if list_colors:
            if i < len(list_colors):
                r = g= b = "254"
                if sep_col in list_colors[i]: 
                    r, g, b = list_colors[i].split(sep_col)
                color = QtGui.QColor.fromRgb(int(r), int(g), int(b))
                entry.setForeground(color)
        if i < len(list_bold):
            font = entry.font()
            font.setBold(list_bold[i])
            entry.setFont(font)
            if list_colors:
                entry.setForeground(color)
        model.appendRow(entry)
    for i in range(cmb.count()):
        if len(list_tooltip) == len(list_rows):
            cmb.setItemData(i, list_tooltip[i], QtCore.Qt.ToolTipRole)

    if first_void:
        model.insertRow(0,QtGui.QStandardItem(""))

    cmb.setMaxVisibleItems(len(list_rows))

def set_cell_editable(tbl:QtWidgets.QTableWidget, r:int, c:int, val:bool):
    if val:
        tbl.item(r,c).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        if tbl.cellWidget(r,c) != None:
            tbl.cellWidget(r,c).setEnabled(True)
    else:
        tbl.item(r, c).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        if tbl.cellWidget(r, c) != None:
            tbl.cellWidget(r, c).setEnabled(False)


def is_cell_editable(table: QTableWidget, row: int, column: int) -> bool:
    """
    Проверяет, является ли ячейка QTableWidget редактируемой.

    Args:
        table (QTableWidget): Таблица, в которой проверяется ячейка
        row (int): Номер строки
        column (int): Номер столбца

    Returns:
        bool: True если ячейка редактируема, False если нет или ячейка не существует
    """
    item = table.item(row, column)
    if item is None:
        return False

    return item.flags() & Qt.ItemIsEditable == Qt.ItemIsEditable


def valt(obj:object,name_col:str,row:int):
    nk = num_col_by_name_c(obj,name_col)
    return obj.item(row,nk).text()
    


def number_table_by_name_c(obj:QTabWidget,ima:str):
    for i in range(obj.count()):
        if obj.tabText(i) == ima:
            return i

def current_tab_name(obj):
    return obj.tabText(obj.currentIndex())


def get_selected_cells_coordinates(table: QTableWidget) -> list[tuple[int, int]]:
    """
    Возвращает координаты всех выбранных ячеек в QTableWidget.
    Учитывает множественное выделение с помощью Ctrl и Shift.

    Args:
        table: Экземпляр QTableWidget

    Returns:
        Список кортежей (row, column) выбранных ячеек
    """
    selected_cells = []

    # Получаем все диапазоны выделения
    selection_ranges = table.selectedRanges()

    for selection_range in selection_ranges:
        # Перебираем все ячейки в текущем диапазоне выделения
        for row in range(selection_range.topRow(), selection_range.bottomRow() + 1):
            for col in range(selection_range.leftColumn(), selection_range.rightColumn() + 1):
                selected_cells.append((row, col))

    return selected_cells


def number_selection_cell_by_row_and_column_c(tblw):
    for idx in tblw.selectionModel().selectedIndexes():
        row_number = idx.row()
        column_number = idx.column()
    return row_number,column_number

def convert_UI_into_PY_c():
    if F.is_frozen() == False:
        put = F.path_to_execut_file_c()
        files = F.list_of_files_c(put)
        for i in range(len(files[0][2])):
            if  files[0][2][i][-3:] == '.ui':
                py_file = files[0][0] + F.throw_out_extention_c(files[0][2][i]) + '.py'
                F.delete_file_c(py_file)
                fp = open(py_file, "w", encoding="utf-8")
                uic.compileUi(files[0][0] + files[0][2][i], fp, from_imports=True)
                fp.close()
    else:
        print('Фрозен')



def clear_tbl(tbl:QtWidgets.QTableWidget):
    tbl.blockSignals(True)
    tbl.clear()
    tbl.setRowCount(0)
    tbl.setColumnCount(0)
    tbl.blockSignals(False)


def blink_obj_c(self, chislo_mig, obj, msg, koef=0.3,icon = QtWidgets.QMessageBox.Information):
    """icon = NoIcon, Question, Information, Warning, Critical """
    msgbox(msg)
    if str(type(obj)) == "<class 'PyQt5.QtWidgets.QTableWidgetItem'>":
        old_col = obj.background()
        font = obj.font()

        # msgBox.setFont(font) #25.08.25
        for _ in range(0, chislo_mig):
            obj.setBackground(QtGui.QColor(255, 144, 144))
            time.sleep(koef)
            self.repaint()
            obj.setBackground(old_col)
            time.sleep(koef)
            self.repaint()
        obj.setFont(font)
        return 
    if obj is None:
        print('Cust_Qt.blink_obj_c аргумент obj is None')
        return
    tepm = obj.styleSheet()
    font = obj.font()
    for _ in range(0, chislo_mig):
        obj.setStyleSheet("background-color: rgb(255, 144, 144);")
        time.sleep(koef)
        
        self.repaint()
        obj.setStyleSheet(tepm)
        time.sleep(koef)
        self.repaint()
    obj.setFont(font)
    return

def migat(self, obj, i: int, j: int, n: int = 2,msg=None):
    if msg:
        msgbox(msg,time_life=2)
    for _ in range(n):
        add_color_wtab_c(obj, i, j, 150, 0, 0)
        self.repaint()
        time.sleep(0.5)
        add_color_wtab_c(obj, i, j, -150, 0, 0)
        self.repaint()
        time.sleep(0.5)


def migat_headers(self, obj: QTableWidget, columns: list[int], r: int, g: int, b: int, duration: int = 0.6, count: int = 2):
    def set_colors():
        old_bc = {}
        for col in columns:
            h_item = obj.horizontalHeaderItem(col)
            old_bc[col] = (h_item, h_item.background())
            h_item.setBackground(QtGui.QColor(r, g, b))
        return old_bc

    def reset_colors(headers):
        for col, (item, prev_background) in headers.items():
            item.setBackground(prev_background)
    for _ in range(count):
        headers = set_colors()
        self.repaint()
        time.sleep(duration)
        reset_colors(headers)
        self.repaint()
        time.sleep(duration)


def color_cell_wtable_c(wtabl, ima='', sod_text="", raven_text="", r=220, g=220, b=220, inventir=False):
    wtabl.blockSignals(True)
    r = int(r)
    g = int(g)
    b = int(b)
    try:
        if inventir == False:
            if ima != '':
                for j in range(wtabl.columnCount()):
                    if wtabl.horizontalHeaderItem(j).text() == ima:
                        for i in range(wtabl.rowCount()):
                            if sod_text == "" and raven_text == "":
                                if wtabl.item(i, j).text() == "":
                                    set_color_wtab_c(wtabl, i, j, r, g, b)
                            if sod_text != "":
                                if sod_text in wtabl.item(i, j).text():
                                    set_color_wtab_c(wtabl, i, j, r, g, b)
                            if raven_text != "":
                                if raven_text == wtabl.item(i, j).text():
                                    set_color_wtab_c(wtabl, i, j, r, g, b)
                            if sod_text == "*":
                                set_color_wtab_c(wtabl, i, j, r, g, b)
            else:
                for j in range(wtabl.columnCount()):
                    for i in range(wtabl.rowCount()):
                        if sod_text == "" and raven_text == "":
                            if wtabl.item(i, j).text() == "":
                                set_color_wtab_c(wtabl, i, j, r, g, b)
                        if sod_text != "":
                            if sod_text in wtabl.item(i, j).text():
                                set_color_wtab_c(wtabl, i, j, r, g, b)
                        if raven_text != "":
                            if raven_text == wtabl.item(i, j).text():
                                set_color_wtab_c(wtabl, i, j, r, g, b)
                        if sod_text == "*":
                            set_color_wtab_c(wtabl, i, j, r, g, b)
        else:
            for j in range(wtabl.columnCount()):
                for i in range(wtabl.rowCount()):
                    set_color_wtab_c(wtabl, i, j, r, g, b)
            r = 255
            g = 255
            b = 255
            if ima != '':
                for j in range(wtabl.columnCount()):
                    if wtabl.horizontalHeaderItem(j).text() == ima:
                        for i in range(wtabl.rowCount()):
                            if sod_text == "" and raven_text == "":
                                if wtabl.item(i, j).text() == "":
                                    set_color_wtab_c(wtabl, i, j, r, g, b)
                            if sod_text != "":
                                if sod_text in wtabl.item(i, j).text():
                                    set_color_wtab_c(wtabl, i, j, r, g, b)
                            if raven_text != "":
                                if raven_text == wtabl.item(i, j).text():
                                    set_color_wtab_c(wtabl, i, j, r, g, b)
                            if sod_text == "*":
                                set_color_wtab_c(wtabl, i, j, r, g, b)
            else:
                for j in range(wtabl.columnCount()):
                    for i in range(wtabl.rowCount()):
                        if sod_text == "" and raven_text == "":
                            if wtabl.item(i, j).text() == "":
                                set_color_wtab_c(wtabl, i, j, r, g, b)
                        if sod_text != "":
                            if sod_text in wtabl.item(i, j).text():
                                set_color_wtab_c(wtabl, i, j, r, g, b)
                        if raven_text != "":
                            if raven_text == wtabl.item(i, j).text():
                                set_color_wtab_c(wtabl, i, j, r, g, b)
                        if sod_text == "*":
                            set_color_wtab_c(wtabl, i, j, r, g, b)
    except:
        print('Ошибка color_cell_wtable_c')
    finally:
        wtabl.blockSignals(False)

def value_of_selection_row_by_column_c(wtabl, ima):
    if wtabl.currentRow() == -1:
        return False
    for i in range(wtabl.columnCount()):
        if wtabl.horizontalHeaderItem(i).text() == ima:
            return wtabl.item(wtabl.currentRow(), i).text()
    msgbox(f'Не найдена колонка {ima}')
    return False


def write_value_selection_row_by_column_c(wtabl, ima, text):
    if wtabl.currentRow() == -1:
        return False
    for i in range(wtabl.columnCount()):
        if wtabl.horizontalHeaderItem(i).text() == ima:
            wtabl.item(wtabl.currentRow(), i).setText(text)
            return
    return False

def select_range(tbl,i,j,i2='',j2=''):
    if i2 == '':
        i2 = i
    if j2 == '':
        j2 = j
    tbl.setStyleSheet(
        'selection-color: rgb(4, 4, 4);selection-background-color: rgb(' + str(100) + ', ' + str(100) + ', ' + str(100) + ')')
    tbl.setCurrentCell(i,j)
    tbl.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(i,j,i2,j2), True)
    positionCell = tbl.item(i, j)
    tbl.scrollToItem(positionCell)

def select_cell(tbl,i,j):
    #set_color_sort_cell_table_c(tbl)
    try:
        positionCell = tbl.item(i, j)
        tbl.scrollToItem(positionCell)
        tbl.setCurrentCell(i, j)
    except:
        pass

def num_col_by_name_c(obj, ima, not_found_val=None):
    if obj.metaObject().className() == 'QTreeWidget':
        for i in range(obj.columnCount()):
            if obj.headerItem().text(i) == ima:
                return i

    if obj.metaObject().className() == 'QTableWidget':
        for i in range(obj.columnCount()):
            if obj.horizontalHeaderItem(i) != None:
                if obj.horizontalHeaderItem(i).text() == ima:
                    return i


    return not_found_val

def set_val_tbl_by_name(tabl,row:int='',column_name:str='',val:str=''):
    if row == '':
        row = tabl.currentRow()
    for j in range(0, tabl.columnCount()):
        if tabl.horizontalHeaderItem(j) != None:
            name = tabl.horizontalHeaderItem(j).data(0)
            if name == column_name:
                tabl.item(row,j).setText(str(val))
                
def set_dict_line_form_tbl(tabl_bd:QTableWidget,row_data:dict,row:int =''):
    if row == '':
        row = tabl_bd.currentRow()
    for j in range(0, tabl_bd.columnCount()):
        if not tabl_bd.item(row, j) == None:
            if tabl_bd.horizontalHeaderItem(j) != None:
                nameHeader = tabl_bd.horizontalHeaderItem(j).data(0)
                if nameHeader in row_data:
                    tabl_bd.item(row, j).setText(row_data[nameHeader])
                    


def get_list_line_form_tbl(tabl_bd:QTableWidget) -> list:
    if tabl_bd.selectionMode() in (QTableWidget.SelectionMode.ExtendedSelection,
                                   QTableWidget.SelectionMode.ContiguousSelection,
                                   QTableWidget.SelectionMode.MultiSelection):
        # Получаем текущий стек вызовов
        stack_frames = inspect.stack()
        try:
            list_ich= [_.code_context for _ in stack_frames if 'currentItemChanged' in _.code_context[0]]
        except:
            list_ich = []
            print(f"unexpected error list_ich= [_.code_context for _ in stack_frames if 'currentItemChanged' in _.code_context[0]]")

        if len(list_ich):
            msgbox(f'Не применимо currentItemChanged и SelectionMode {tabl_bd.selectionMode()} в такой комбинации\nОбратиться к специалисту')
            list_rows = [tabl_bd.currentRow()]
        else:
            # Получаем все выбранные элементы
            selected_items = tabl_bd.selectedItems()
            # Получаем уникальные строки
            selected_rows = set()
            for item in selected_items:
                selected_rows.add(item.row())
            tabl_bd.currentRow()
            list_rows = sorted(selected_rows)
    else:
        list_rows = [tabl_bd.currentRow()]

    list_rez = []
    for num_row in list_rows:
        rez_dict= dict()
        for j in range(0, tabl_bd.columnCount()):
            text = ""
            if not tabl_bd.item(num_row,j) == None:
                text = tabl_bd.item(num_row, j).text()
            if tabl_bd.horizontalHeaderItem(j) != None:
                name = tabl_bd.horizontalHeaderItem(j).data(0)
                if name in rez_dict:
                    name = name + "_" +str(j)
                rez_dict[name] = text
            else:
                rez_dict[str(j)] = text
        list_rez.append(rez_dict)
    return list_rez


def get_dict_line_form_tbl(tabl_bd:QTableWidget,row='') -> dict:
    if row == '':
        row = tabl_bd.currentRow()
    if row == -1:
        return dict()
    rez_dict = dict()
    for j in range(0, tabl_bd.columnCount()):
        text = ""
        if not tabl_bd.item(row, j) == None:
            text = tabl_bd.item(row, j).text()
        if tabl_bd.horizontalHeaderItem(j) != None:
            name = tabl_bd.horizontalHeaderItem(j).data(0)
            if name in rez_dict:
                name = name + "_" + str(j)
            rez_dict[name] = text
        else:
            rez_dict[str(j)] = text
    return rez_dict

def set_color_sort_cell_table_c(obj, r=100, g=240, b=100, SelectionRow=True):
    obj.setSelectionBehavior(SelectionRow)
    obj.setStyleSheet(
        'selection-color: rgb(4, 4, 4);selection-background-color: rgb(' + str(r) + ', ' + str(g) + ', ' + str(b) + ')')


def set_color_of_obj_c(obj, r=240, g=240, b=240):
    obj.setStyleSheet('background: rgb(' + str(r) + ', ' + str(g) + ', ' + str(b) + ');')

    
    
def set_color_text_of_object_c(obj, r=240, g=240, b=240):
    obj.setStyleSheet('color: rgb(' + str(r) + ', ' + str(g) + ', ' + str(b) + ');')

def statusbar_text(self, text = '', font_size = 20, otstup = 8, text_color = 'black', bold = True, background_color = (255,255,255,255),text_align="right"):
    font_tip = 'normal'
    if bold:
        font_tip = 'bold'
    self.statusBar().setStyleSheet(
        f"QStatusBar {{padding: {otstup}px;background: rgba{background_color};color: {text_color};font-weight: {font_tip};text-align: {text_align};}}")
    self.statusBar().showMessage(text)
    
def list_from_cmb_c(obj):
    rez = []
    for i in range(obj.count()):
        rez.append(obj.itemText(i))
    return   rez
            
            
def list_from_wtabl_c(obj, sep='', hat_c=False, only_visible=False, rez_dict=False, only_visible_columns = False,only_current_row=False):
    spisok = []
    if obj == None:
        return []
    if rez_dict:
        hat_c = True
    if hat_c == True:
        s = []
        for j in range(0, obj.columnCount()):
            fl_column = True
            if only_visible_columns:
                if obj.isColumnHidden(j):
                    fl_column = False
            if fl_column:
                if obj.horizontalHeaderItem(j) != None:
                    s.append(obj.horizontalHeaderItem(j).data(0))
                else:
                    s.append('')
        if sep == '':
            spisok.append(s)
        else:
            spisok.append(sep.join(s))
    current_row = obj.currentRow()
    for i in range(0, obj.rowCount()):
        fl_write = True
        if only_visible:
            if obj.isRowHidden(i):
                fl_write = False
        if only_current_row:
            fl_write = False
            if i == current_row:
                fl_write = True
        if fl_write:
            s = []
            for j in range(0, obj.columnCount()):
                fl_column = True
                if only_visible_columns:
                    if obj.isColumnHidden(j):
                        fl_column = False
                if fl_column:
                    cell = obj.cellWidget(i, j) # 19.06.2025 (Извлечения вложенных таблиц)
                    if isinstance(cell, QtWidgets.QTableWidget):
                        s.append(list_from_wtabl_c(cell, sep, hat_c, only_visible, rez_dict, only_visible_columns, only_current_row))
                    elif obj.item(i, j) != None:
                        s.append(obj.item(i, j).data(0))
                    else:
                        s.append("")
            if sep == '':
                spisok.append(s)
            else:
                spisok.append(sep.join(s))
                
    if rez_dict:
        spisok = F.list_to_dict(spisok)
    return spisok


def font_size(obj, kol: int, size: int):
    font = QtGui.QFont()
    font.setPointSize(int(size))
    for i in range(0, obj.rowCount()):
        obj.item(i, kol).setFont(font)

def font_cell_size_format(obj, i: int, j: int, size: int = 0, bold: bool = False,underline: bool = False,italic: bool = False):
    obj.blockSignals(True)
    font = obj.item(i, j).font()
    if size:
        font.setPointSize(int(size))

    font.setBold(bold)
    font.setUnderline(underline)
    font.setItalic(italic)
    obj.item(i, j).setFont(font)
    obj.blockSignals(False)

def add_color_wtab(obj, i, j, r:int, g:int, b:int):
    if obj.item(i, j) == None:
        return
    izr = obj.item(i, j).background().color().red()
    izg = obj.item(i, j).background().color().green()
    izb = obj.item(i, j).background().color().blue()
    
    izr -=g
    izr -=b
    
    izg -=r
    izg -=b
    
    izb -=r
    izb -=g
    
    if izr < 0:
        izr = 255 - g
    if izg < 0:
        izg = 255 - g
    if izb < 0:
        izb = 255 - b
    obj.item(i, j).setBackground(QtGui.QColor(izr, izg, izb))

def add_color_wtab_c(obj, i, j, r, g, b):
    if obj.item(i, j) == None:
        return
    r = int(r)
    g = int(g)
    b = int(b)
    """    max_col = 0
    max_col = r if r > max_col else max_col
    max_col = g if g > max_col else max_col
    max_col = b if b > max_col else max_col
    
    r = max_col - r
    g = max_col - g
    b  =max_col - b"""
    
    izr = obj.item(i, j).background().color().red()
    izg = obj.item(i, j).background().color().green()
    izb = obj.item(i, j).background().color().blue()
    if izr == 0:
        izr = 255
    if izg == 0:
        izg = 255
    if izb == 0:
        izb = 255

    nr = izr - r
    if nr < 0:
        nr = 0
    if nr > 255:
        nr = 255
    ng = izg -g
    if ng < 0:
        ng = 0
    if ng > 255:
        ng = 255
    nb = izb - b
    if nb < 0:
        nb = 0
    if nb > 255:
        nb = 255
    obj.item(i, j).setBackground(QtGui.QColor(nr, ng, nb))


def set_color_wtab_c(obj, i, j, r, g, b,a=255):
    obj.blockSignals(True)
    r = int(r)
    g = int(g)
    b = int(b)
    obj.item(i, j).setBackground(QtGui.QColor(r, g, b, a))
    obj.blockSignals(False)

def set_color_header_wtab_horisontal_c(obj, j, r, g, b):
    obj.horizontalHeader().blockSignals(True)
    r = int(r)
    g = int(g)
    b = int(b)
    #obj.horizontalHeaderItem(j).setBackgroundColor(QtGui.QColor(r, g, b))
    item = obj.horizontalHeaderItem(j)
    if item == None:
        return 
    item.setBackground(QtGui.QColor(r, g, b))
    obj.setHorizontalHeaderItem(j, item)
    obj.horizontalHeader().blockSignals(False)
    
def set_color_header_wtab_vertical_c(obj, j, r, g, b):
    r = int(r)
    g = int(g)
    b = int(b)
    #obj.horizontalHeaderItem(j).setBackgroundColor(QtGui.QColor(r, g, b))
    item = obj.verticalHeaderItem(j)
    item.setBackground(QtGui.QColor(r, g, b))
    obj.setVerticalHeaderItem(j, item)

def set_color_text_header_wtab_horisontal_c(obj, j, r, g, b, size= 10, blod=False,):
    obj.horizontalHeader().blockSignals(True)
    r = int(r)
    g = int(g)
    b = int(b)
    fnt = QtGui.QFont()
    fnt.setPointSize(int(size))
    fnt.setBold(blod)
    #obj.horizontalHeaderItem(j).setBackgroundColor(QtGui.QColor(r, g, b))
    item = obj.horizontalHeaderItem(j)
    item.setForeground(QtGui.QColor(r, g, b))
    item.setFont(fnt)
    obj.setHorizontalHeaderItem(j, item)
    obj.horizontalHeader().blockSignals(False)
    
def set_color_text_header_wtab_vertical_c(obj, j, r, g, b, size= 10, blod=False,):
    obj.horizontalHeader().blockSignals(True)
    r = int(r)
    g = int(g)
    b = int(b)
    fnt = QtGui.QFont()
    fnt.setPointSize(int(size))
    fnt.setBold(blod)
    #obj.horizontalHeaderItem(j).setBackgroundColor(QtGui.QColor(r, g, b))
    item = obj.verticalHeaderItem(j)
    item.setForeground(QtGui.QColor(r, g, b))
    item.setFont(fnt)
    obj.setVerticalHeaderItem(j, item)
    obj.horizontalHeader().blockSignals(False)
    
def set_font_color_wtab_c(obj, i, j, r='', g='', b=''):
    obj.blockSignals(True)
    if r == '' or g == '' or b == '':
        pass
    else:
        r = int(r)
        g = int(g)
        b = int(b)
        obj.item(i, j).setForeground(QtGui.QColor(r, g, b))
    obj.blockSignals(False)

def set_color_row_wtab_c(obj, i, r, g, b):
    for j in range(obj.columnCount()):
        obj.item(i, j).setBackground(QtGui.QColor(r, g, b))

def highlight_tree_values_c(obj, kol, text, korr=0):
    flag_naid = False
    it = QtWidgets.QTreeWidgetItemIterator(obj)
    buf = None
    while it.value():
        if it.value().text(kol) == text or flag_naid == True:
            flag_naid = True
            if korr == -1:
                if buf == None:
                    obj.setCurrentItem(it.value())
                else:
                    obj.setCurrentItem(buf)
                return
            if korr == 0:
                obj.setCurrentItem(it.value())
                return
        if flag_naid == True:
            korr = korr - 1
        buf = it.value()
        it += 1

    return False


def highlight_tree_number_c(obj, nom):
    it = QtWidgets.QTreeWidgetItemIterator(obj)
    while it.value():
        nom -= 1
        if nom == 0:
            currentItem = it.value()
            obj.setCurrentItem(currentItem)
            return
        it += 1
    return False


def cells(x, y, obj):
    nom_dse = obj.model().index(x, y).data()
    return nom_dse


def fill_progress_c(self, wtabl, nom_kol_prog, hat_c=True, isp_summ=True, isp_poc=True,margin=0):
    """ if isp_summ == True , nom_kol_prog must have  max_summ|summ"""
    nach = 1 if hat_c == True else 0
    sp_rez = list_from_wtabl_c(wtabl, hat_c=True)
    if isp_summ == False:
        max = 0
        for i in range(nach, len(sp_rez)):
            if max < F.valm(sp_rez[i][nom_kol_prog]):
                max = F.valm(sp_rez[i][nom_kol_prog])
        for i in range(nach, len(sp_rez)):
            sp_rez[i][nom_kol_prog] = str(max) + "|" + str(sp_rez[i][nom_kol_prog])
        max+=1
        
    for i in range(nach, len(sp_rez)):
        # Создаем QProgressBar
        if nom_kol_prog < len(sp_rez[i]) and "|" in sp_rez[i][nom_kol_prog]:
            max_summ, summ = sp_rez[i][nom_kol_prog].split('|')
            max_summ = F.valm(max_summ)
            summ = F.valm(summ)
            progress = QtWidgets.QProgressBar()
            if max_summ == 0:
                proc = 0
            else:
                proc = round(summ / max_summ * 100,2)
            # Формат вывода: 10.50%
            if isp_poc == True:
                if proc > 100:
                    proc = 100
                progress.setMaximum(100)
                progress.setValue(int(proc))
                progress.setFormat(f'{proc}%')
                progress.setMinimum(0)
                
                r = 253 - proc * 2.5
                g = 0 + proc * 2.5
                progress.setStyleSheet("""QProgressBar {
                                        border: 2px solid grey;
                                        border-radius: 5px;
                                        text-align: center;
                                            }\n"""  
                                       
                                       "QProgressBar::chunk "
                                       "{"
                                       f"background-color: rgb({r}, {g}, 30);"
                                       "width: 20px;"
                                       f"margin: {margin}px;"
                                       "}")
            else:
                progress.setValue(int(proc))
                progress.setMinimum(0)
                progress.setMaximum(100)
                progress.setFormat(str(summ) + '/' + str(max_summ))
                r = 253 - proc * 2.5
                g = 0 + proc * 2.5
                progress.setStyleSheet("QProgressBar::chunk "
                                       "{"
                                       f"background-color: rgb({r}, {g}, 30);"
                                       "width: 10px;"
                                       f"margin: {margin}px;"
                                       "}")
            progress.setGeometry(200, 100, 200, 30)
            progress.setTextVisible(True)

            progress.setFont(QtGui.QFont('MS Shell Dlg 2', 16))
            progress.setAlignment(QtCore.Qt.AlignCenter)
            # cellinfo2 = QtWidgets.QTableWidgetItem(spisok_chasov[item])
            # self.ui.tableWidget_vibor_imeni_sla_nar.setItem(item, 0, cellinfo2)
            # Добавляем виджет в ячейку.
            wtabl.setCellWidget(i - 1, nom_kol_prog, progress)
            chislo = str(proc)
            cellinfo = QtWidgets.QTableWidgetItem(chislo)
            wtabl.setItem(i - 1, nom_kol_prog, cellinfo)
            wtabl.item(i - 1, nom_kol_prog).setText(sp_rez[i][nom_kol_prog])
            #print(sp_rez[i][nom_kol_prog])


def f_dialog_name(obj, text, putt, filtr, one=True):
    if putt == "":
        putt = os.path.expanduser('~')
    if one == True:
        ima = QtWidgets.QFileDialog.getOpenFileName(obj, text, putt, filtr)[0]
        ima = os.path.normpath(ima)
    else:
        ima = QtWidgets.QFileDialog.getOpenFileNames(obj, text, putt, filtr)[0]
        for i in range(len(ima)):
            ima[i] = os.path.normpath(ima[i])
    return ima


def f_dialog_save(obj, text, putt, filtr):
    """filtr = Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)"""
    ima = QtWidgets.QFileDialog.getSaveFileName(obj, text, putt, filtr)[0]
    ima = os.path.normpath(ima)
    return ima


def getDirectory(self, path):  # <-----
    path = os.path.normpath(path)
    dirlist = QtWidgets.QFileDialog.getExistingDirectory(self, "Выбрать папку", path)
    dirlist = os.path.normpath(dirlist)
    return dirlist

def tbl_set_val_wo_signal(tbl:QTableWidget,i:int,j:int,val):
    # Получаем указатель на данные элемента
    item = tbl.item(i, j)
    with QSignalBlocker(tbl):  # Контекстный менеджер
        item.setText(val)

def use_CSS_c(spis):
    tmp_dict = dict()
    rez = []
    try:
        for i in range(len(spis)):
            if spis[i] == '' or '{' in spis[i]:
                nach = i
                break
            if spis[i][0] == '$':
                tmp_dict[spis[i].split(' = ')[0]] = spis[i].split(' = ')[1].split(';')[0]

        for key in tmp_dict.keys():
            if '#' in tmp_dict[key]:
                tmp_dict[key] = f'rgb{F.hex_to_rgb(tmp_dict[key][1:])}'

        for i in range(nach,len(spis)):
            for key in tmp_dict.keys():
                spis[i] = spis[i].replace(key, tmp_dict[key])
            rez.append(spis[i])
    except:
        return ''
    return rez




def addline_w(item, i, j, slov):
    line = QtWidgets.QLineEdit()
    line.setStyle(item.style())
    # Создаём QCompleter, в который устанавливаем список, а также указатель на родителя
    completer = QtWidgets.QCompleter(slov, line)
    line.setCompleter(completer)
    item.setCellWidget(i, j, line)
    return


def add_table(item, i, j, spis_spiskov, set_editeble_col_nomera={}, visota = 10, show_horizontalHeader=True, show_verticalHeader=True):
    table = QtWidgets.QTableWidget()
    # table.setStyle(item.style())
    # Создаём QCompleter, в который устанавливаем список, а также указатель на родителя
    # completer = QtWidgets.QCompleter(spis_spiskov, table)
    # table.setCompleter(completer)
    table.setColumnCount(len(spis_spiskov[0]))
    table.setRowCount(len(spis_spiskov))
    for row in range(0, len(spis_spiskov)):
        for kol in range(0, len(spis_spiskov[row])):
            cellinfo = QtWidgets.QTableWidgetItem(str(spis_spiskov[row][kol]))
            if set_editeble_col_nomera != {'*'}:
                if kol not in set_editeble_col_nomera:
                    # Только для чтения
                    cellinfo.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            table.setItem(row, kol, cellinfo)
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setStretchLastSection(True)
            table.setRowHeight(row, visota)
            table.verticalHeader().setVisible(show_verticalHeader)
            table.horizontalHeader().setVisible(show_horizontalHeader)
    item.setCellWidget(i, j, table)
    return

def add_combobox(self = '', table = '', i=0, j=0, list=[], first_void=True,  conn_func = '', editable = False, name_flag = None):
    current_text = table.item(i,j).text()
    combo = QtWidgets.QComboBox()
    combo.wheelEvent = lambda event: None
    fl = False
    if conn_func != '':
        if self == '':
            if name_flag != None:
                combo.activated[str].connect(lambda text, row=i, col=j, flag=name_flag: conn_func(text,  row, col, flag))
            else:
                combo.activated[str].connect(lambda text, row=i, col=j, flag=name_flag: conn_func(text, row, col))
        else:
            if name_flag != None:
                combo.activated[str].connect(lambda text, self=self, row=i, col=j, flag=name_flag: conn_func(self, text,  row, col,flag))
            else:
                combo.activated[str].connect(
                    lambda text, self=self, row=i, col=j, flag=name_flag: conn_func(self, text, row, col))
    if first_void:
        combo.addItem("")
    if type(list) == type(dict()):
        _ = 0
        koef = 0
        if first_void:
            koef = 1
        for key in list:
            combo.addItem(key)
            combo.setItemData(_+koef, list[key], QtCore.Qt.ToolTipRole)
            if key == current_text:
                fl = True
            _+=1
    else:
        for item in list:
            combo.addItem(item)
            if item == current_text:
                fl = True
    table.setCellWidget(i, j, combo)
    if fl:
        combo.setCurrentText(current_text)
    if first_void:
        combo.setCurrentIndex(0)
    if editable:
        combo.setEditable(True)
    return combo #22.08.25


def add_check_box(table, i, j, trisate=False, val=False, conn_func_checked_row_col = '', self = '',enabled=True):
    check = QtWidgets.QCheckBox()
    check.setTristate(trisate)
    check.setChecked(val)
    check.setEnabled(enabled)
    if conn_func_checked_row_col != '':
        if self == '':
            check.clicked.connect(lambda checked, row=i, col=j: conn_func_checked_row_col(checked,row,col))
        else:
            check.clicked.connect(lambda checked, row=i, col=j: conn_func_checked_row_col(self,checked,row,col))
    table.setCellWidget(i, j, check)

    
def add_label_link(object_tbl, i,j, file, name,conn_func_label_link=None,parent_self=None):
    lbl = QtWidgets.QLabel()

    lbl.setOpenExternalLinks(True)
    lnk = urllib.parse.quote(f'{file}')
    linkTemplate = rf'<a href={lnk}>{name}</a>'
    lbl.setText(linkTemplate)
    lbl.setOpenExternalLinks(False)
    #alignment = object_tbl.item(i, j).textAlignment()
    lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter) 
    lbl.setAutoFillBackground(True)

    object_tbl.setCellWidget(i, j, lbl)
    if conn_func_label_link:
        if parent_self:
            lbl.linkActivated.connect(lambda: conn_func_label_link(lnk, i, j, name, file,parent_self))
        else:
            lbl.linkActivated.connect(lambda : conn_func_label_link(lnk, i,j,name,file))
    
def add_btn(item, i, j, text='', val=True, conn_func_checked_row_col = '', self = '',img_path='',height = '',fontsize='',cell_val=None):
    btn = QtWidgets.QPushButton()
    btn.setEnabled(val)
    btn.setText(text)
    if height != '':
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
    if conn_func_checked_row_col != '':
        if self == '':
            if cell_val:
                btn.clicked.connect(lambda checked, row=i, col=j: conn_func_checked_row_col(row,col,cell_val))
            else:
                btn.clicked.connect(lambda checked, row=i, col=j: conn_func_checked_row_col(row, col))
        else:
            if cell_val:
                btn.clicked.connect(lambda checked, row=i, col=j: conn_func_checked_row_col(self,row,col,cell_val))
            else:
                btn.clicked.connect(lambda checked, row=i, col=j: conn_func_checked_row_col(self, row, col))
    item.setCellWidget(i, j, btn)

class ClickedLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)

        self.clicked.emit()

def get_img_size(path):
    return  QPixmap(path).width() , QPixmap(path).height()

def add_image(item, i, j, path='', self = '',w = 16, h = 16,conn_func_click = None):
    lbl = ClickedLabel()
    fon = QPixmap(path)
    lbl.setFixedWidth(w)
    lbl.setFixedHeight(h)
    lbl.setFrameShape(QtWidgets.QFrame.Box)
    lbl.setFrameShadow(QtWidgets.QFrame.Raised)
    pixmap = fon.scaled(lbl.size(), Qt.KeepAspectRatio)
    lbl.setPixmap(pixmap)
    lbl.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
    lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    if conn_func_click:
        lbl.clicked.connect(lambda: conn_func_click( path,i, j))

    item.setCellWidget(i, j, lbl)

def add_label(item, i, j, text='', self = '',w = 16, h = 16):
    lbl = QtWidgets.QLabel()
    lbl.setFixedWidth(w)
    lbl.setFixedHeight(h)
    lbl.setText(text)
    item.setCellWidget(i, j, lbl)

class Delegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if ((1+index.row()) % 3 == 0): # Every third row
            painter.setPen(QPen(Qt.red, 3))
            painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())

        if ((1+index.column()) % 3 == 0): # Every third column
            painter.setPen(QPen(Qt.red, 3))
            painter.drawLine(option.rect.topRight(), option.rect.bottomRight())

def set_cell_editable(tbl, i, j, val:bool=True):
    tbl.blockSignals(True)
    cellinfo = tbl.item(i, j)
    if val:
        cellinfo.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        set_color_wtab_c(tbl, i , j, 250, 250, 250)
    else:
        cellinfo.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        set_color_wtab_c(tbl, i, j, 240, 240, 240)
    tbl.blockSignals(False)
    
def lbl_linkActivated(link, *args):
    try:
        link = urllib.parse.unquote(link) 
        if F.is_link_dir(link):
            if 'e1c://server' in link:
                prefix = fr'"%programfiles%\1cv8\common\1cestart.exe" '
                line = prefix + fr'/url "{link}"'
                try:
                    subprocess.call(line, shell=True)
                except:
                    F.copy_bufer(line)
                    CQT.msgbox(f'Скопировано в буфер\n{line}')
            else:
                F.run_file_os_c(link,normalize=False)
            return 
        if F.is_link_file(link):
            F.run_file_os_c(link)
    except:
        msgbox(f'Ошибка открытия пути')
        

class FillTableDelegator(QtWidgets.QStyledItemDelegate):
    def __init__(
            self,
            parent: QtWidgets.QTableWidget,
            colorful_edit = True,
            editable_col_nomera = set(),
            load_links = False
    ):
        super().__init__(parent)
        self.parent = parent
        self.prev_delegator = self.parent.itemDelegate()
        self.editable_col_nomera = editable_col_nomera
        self.colorful_edit = colorful_edit
        self.load_links = load_links

    def paint(self, painter: QtGui.QPainter, option, index: QtCore.QModelIndex):
        col = index.column()
        value = index.data()

        placeholder_text = '...'
        
        if self.colorful_edit:
            if col not in self.editable_col_nomera:
                rgb = (240, 240, 240)
            else:
                rgb = (250, 250, 250)
            if self.load_links and is_link_like(value):
                cell = self.parent.cellWidget(index.row(), col)
                if isinstance(cell, QtWidgets.QLabel):
                    cell.setStyleSheet(f'background-color:rgba{*rgb, 1};')
            option.backgroundBrush = QtGui.QBrush(QtGui.QColor(*rgb))
            painter.fillRect(option.rect, option.backgroundBrush)
            if not value and placeholder_text and is_cell_editable(self.parent,index.row(),col):  # Если данных нет
                # Сохраняем настройки пера
                old_pen = painter.pen()

                # Получаем текущий шрифт
                font = painter.font()

                # Уменьшаем размер (например, на 2 пункта)
                new_size = max(6, font.pointSize() - 4)  # Не меньше 6 пунктов
                font.setPointSize(new_size)

                # Устанавливаем новый шрифт
                painter.setFont(font)

                painter.setPen(QColor(190, 190, 190))  # Серый для плейсхолдера
                painter.drawText(option.rect, Qt.AlignCenter, placeholder_text)
                # Восстанавливаем перо

                painter.setPen(old_pen)

            else:
                pass
                # Стандартная отрисовка для непустых ячеек
                #if self.parent.styleSheet() != '':
                #    super().paint(painter, option, index)
        self.prev_delegator.paint(painter, option, index)

    def createEditor(self, parent, option, index):
        return self.prev_delegator.createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        return self.prev_delegator.setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        return self.prev_delegator.setModelData(editor, model, index)

def is_link_like(text: str):
    return F.is_link_like(text)


def fill_wtabl(dict_or_list, object, set_editeble_col_nomera={}, ogr_maxshir_kol=200,
                 min_width_col=20, height_row=30, colorful_edit = True, auto_type=True,head_column:int = None,
               hide_head_column:bool=False,hide_head_rows:bool=False,StretchLastSection=True,select_last_row=False,
               list_column_widths:list=[],save_column_sort_hh: bool = False, StretchLastRow=False,tbl_vidget:tuple|None=None,count_unhide_rows=5,
               selectionBehavior="SelectItems",count_rows_cell_max=1, load_links=False, conn_func_label_link=None,
               styleSheet=None,parent_self=None,sortingEnabled=False,selectionMode="ExtendedSelection"):

#16.07.25
    """
    
    :param dict_or_list: 
    :param object: 
    :param set_editeble_col_nomera: 
    :param ogr_maxshir_kol: 
    :param min_width_col: 
    :param height_row: 
    :param colorful_edit: 
    :param auto_type: 
    :param head_column: 
    :param hide_head_column: 
    :param hide_head_rows: 
    :param StretchLastSection: 
    :param select_last_row: 
    :param list_column_widths: 
    :param StretchLastRow: 
    :param tbl_vidget: 
    :param count_unhide_rows: 
    :param selectionBehavior: SelectItems|SelectRows|SelectColumns
    :param selectionMode:
            Число	Константа (SelectionMode)	Описание
            0	    NoSelection	                Выделение запрещено
            1	    SingleSelection	            Только один элемент (по умолчанию)
            2	    MultiSelection	            Множественный выбор (Ctrl+ЛКМ, но без Shift)
            3	    ExtendedSelection	        Расширенный выбор (как в проводнике — работает Shift и Ctrl)
            4	    ContiguousSelection	        Только смежные элементы (работает Shift, но не Ctrl)
    :return:
    """

    if dict_or_list == None or len(dict_or_list) == 0:
        return
    if isinstance(tbl_vidget,tuple):
        object_tbl = QtWidgets.QTableWidget()
        paret_item = object
    else:
        object_tbl = object
        paret_item = None
    clear_tbl(object_tbl) # 30.05.2025 по задаче (100054932 )
    object_tbl.reset()
    if isinstance(object_tbl, QtWidgets.QTableWidget):
        object_tbl.blockSignals(True)
        object_tbl.setUpdatesEnabled(False)
    object_tbl.horizontalHeader().blockSignals(True)
    object_tbl.horizontalHeader().setUpdatesEnabled(False)
    object_tbl.clear()
    object_tbl.setSelectionBehavior(eval(f'QtWidgets.QTableWidget.SelectionBehavior.{selectionBehavior}'))
    object_tbl.setSelectionMode(eval(f'QtWidgets.QTableWidget.SelectionMode.{selectionMode}'))
    tbl_object_name = object_tbl.objectName()
    if type(dict_or_list) == type(dict()):
        list_of_data = F.dict_of_dicts_to_list_of_lists(dict_or_list)
    if type(dict_or_list) == type(['']):
        if type(dict_or_list[0]) == type(dict()):
            list_of_data = F.list_of_dicts_to_list_of_lists(dict_or_list)  
        else:
            if not isinstance(dict_or_list[0],list):
                dict_or_list = [[_] for _ in dict_or_list]
            list_of_data = dict_or_list
            
    if set_editeble_col_nomera != '*':
        for _ in set_editeble_col_nomera:
            if type(_) != int:
                set_editeble_col_nomera = {F.num_col_by_name_in_hat_c(list_of_data, _) for _ in set_editeble_col_nomera}
                break
    else:
        set_editeble_col_nomera = set(range(len(list_of_data[0])))

    if styleSheet:
        object_tbl.setStyleSheet(styleSheet)
        
    object_tbl.setSortingEnabled(sortingEnabled)
    
    delegate = FillTableDelegator(object_tbl, colorful_edit, set_editeble_col_nomera, load_links)
    object_tbl.setItemDelegate(delegate)
    object_tbl.setColumnCount(len(list_of_data[0]))
    start_fill = 1
    if not hide_head_column:
        object_tbl.setRowCount(len(list_of_data) - 1)
        object_tbl.setHorizontalHeaderLabels(list_of_data[0])
    else:
        object_tbl.setRowCount(len(list_of_data))
        object_tbl.setHorizontalHeaderLabels(['' for _ in list_of_data[0]])
        start_fill = 0
    if head_column != None:
        object_tbl.setVerticalHeaderLabels([_[head_column] for _ in list_of_data[start_fill:]])
    for i in range(start_fill, len(list_of_data)):
        for j in range(len(list_of_data[i])):
            cellinfo = QtWidgets.QTableWidgetItem()
            text = list_of_data[i][j]   
            if isinstance(list_of_data[i][j],list) or isinstance(list_of_data[i][j],dict):  
                text = str(list_of_data[i][j])


            if auto_type:
                if F.is_numeric(list_of_data[i][j]):
                    if text == None:                        
                        cellinfo.setData(QtCore.Qt.DisplayRole,0)
                    else:
                        cellinfo.setData(QtCore.Qt.DisplayRole,F.valm(text))
                else:
                    if text == None:                        
                        cellinfo.setData(QtCore.Qt.DisplayRole,'')
                    else:
                        cellinfo.setText(str(text))
            else:
                if text == None:
                    cellinfo.setData(QtCore.Qt.DisplayRole, '')
                else:
                    cellinfo.setText(str(text))

            if j not in set_editeble_col_nomera:
                cellinfo.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            object_tbl.setItem(i-start_fill, j, cellinfo)
            
                        
            if load_links:
                if not conn_func_label_link:
                    conn_func_label_link = lbl_linkActivated
            # =================================links/files==============
                if is_link_like(text):
                    files = text.split(";")
                    if len(files) == 1:
                        file_str = files[0].lstrip('\n')
                        
                        if '|' in file_str:
                            file = file_str.split('|')[0]
                            name = '|'.join(file_str.split('|')[1:])
                        else:
                            file = file_str
                            name = file
                        if F.is_link_dir(file):

                            add_label_link(object_tbl,i - start_fill,j,file,name, conn_func_label_link=conn_func_label_link,parent_self=parent_self)

                        if F.is_link_file(file):
                            if not name:
                                name = F.get_name_file_from_path(file,extention=False)
                            text = file
                            if F.keep_extention_c(file) in ('.jpg', '.jpeg', '.bmp', '.png'):
                                size_w, size_h =get_img_size(file)
                                k = size_w/size_h
                                size_h_k = size_h//5
                                if size_h_k < height_row:
                                    size_h_k = height_row
                                if size_h_k > 240:
                                    size_h_k = 240
                                size_w_k = size_h_k*k
                                add_image(object_tbl,i - start_fill, j,file,"",F.round_up(size_w_k),F.round_up(size_h_k), conn_func_click=conn_func_label_link)

                                font_cell_size_format(object_tbl,i - start_fill, j,1)
                            else:
                                if not name: # add giperlink
                                    name = F.get_name_file_from_path(file)
                                
                                add_label_link(object_tbl, i - start_fill, j, file, name, conn_func_label_link=conn_func_label_link)


                    else:
                        if not hide_head_column:
                            files.insert(0,'Файлы')
                        text = files
                        list_of_data[i][j]= text
            # =================================links/files==============
                
            if isinstance(list_of_data[i][j],list) or isinstance(list_of_data[i][j],dict):
                fill_wtabl(list_of_data[i][j], object_tbl, set_editeble_col_nomera={}, ogr_maxshir_kol=ogr_maxshir_kol,
                               min_width_col=min_width_col, height_row=height_row, colorful_edit=colorful_edit, auto_type=auto_type,
                               head_column = head_column,
                               hide_head_column = hide_head_column, hide_head_rows = hide_head_rows, StretchLastSection=StretchLastSection,
                               select_last_row=select_last_row, list_column_widths = list_column_widths, 
                           StretchLastRow=StretchLastRow,tbl_vidget=(i-1,j),count_unhide_rows=count_unhide_rows,
                           selectionBehavior=selectionBehavior,count_rows_cell_max=count_rows_cell_max, load_links=load_links)
    object_tbl.horizontalHeader().setMinimumSectionSize(1)
    object_tbl.horizontalHeader().setDefaultSectionSize(20)
    object_tbl.verticalHeader().setMinimumSectionSize(1)
    object_tbl.verticalHeader().setDefaultSectionSize(20)
    
    #object_tbl.resizeColumnsToContents()
    
    object_tbl.horizontalHeader().setStretchLastSection(StretchLastSection)
    object_tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
    object_tbl.verticalHeader().setStretchLastSection(StretchLastRow)
    
    for i in range(0, object_tbl.columnCount() + 1):
        object_tbl.resizeColumnToContents(i)
        object_tbl.setColumnWidth(i, int(round(object_tbl.columnWidth(i)*1.15)))
        if object_tbl.columnWidth(i) > ogr_maxshir_kol:
            object_tbl.setColumnWidth(i, int(ogr_maxshir_kol))
        if object_tbl.columnWidth(i) < min_width_col:
            object_tbl.setColumnWidth(i, int(min_width_col))
        #object_tbl.setColumnHidden(i, False)
    if object_tbl.rowCount() > 0:
        for i in range(0, object_tbl.rowCount()):
            tbl_height = height_row
            for j in range(0, object_tbl.columnCount() + 1):
                crnt_tbl_height = height_row
                if object_tbl.cellWidget(i,j) != None:
                    if isinstance(object_tbl.cellWidget(i,j),QtWidgets.QTableWidget):
                        count_rows_child =   object_tbl.cellWidget(i,j).rowCount()
                        scroll_height = 2
                        if  object_tbl.cellWidget(i,j).horizontalScrollBar().isVisible():
                            scroll_height = object_tbl.cellWidget(i,j).horizontalScrollBar().height()
                        if count_rows_child > count_unhide_rows:
                            count_rows_child = count_unhide_rows
                        height_summ_childs = 0
                        for child_i in range(object_tbl.cellWidget(i,j).rowCount()):
                            height_summ_childs += (1+ object_tbl.cellWidget(i,j).rowHeight(child_i))
                        crnt_tbl_height = 2 + height_summ_childs   +  object_tbl.cellWidget(i,j).horizontalHeader().height()  + scroll_height
                    if isinstance(object_tbl.cellWidget(i,j),QtWidgets.QLabel):
                        crnt_tbl_height = object_tbl.cellWidget(i,j).height()
                if object_tbl.item(i,j) != None:
                    if '\n' in object_tbl.item(i,j).text():
                        count_rows = object_tbl.item(i,j).text().count('\n')+1
                        if count_rows_cell_max != -1 and count_rows > count_rows_cell_max:
                            count_rows = count_rows_cell_max
                        crnt_tbl_height = 2 + round(( object_tbl.item(i, j).font().pointSizeF() *2)) * (count_rows + 1 )
                if crnt_tbl_height > tbl_height:
                    tbl_height = crnt_tbl_height

            object_tbl.setRowHeight(i, int(tbl_height))

    if head_column != None:
        object_tbl.setColumnHidden(head_column,True)
    if hide_head_column:
        object_tbl.horizontalHeader().hide()
    if hide_head_rows:
        object_tbl.verticalHeader().hide()
        
    if isinstance(object_tbl,QtWidgets.QTableWidget):
        object_tbl.blockSignals(False)
        object_tbl.setUpdatesEnabled(True)

    object_tbl.horizontalHeader().blockSignals(False)
    object_tbl.horizontalHeader().setUpdatesEnabled(True)
    if select_last_row:
        lastIndex = object_tbl.rowCount() - 1
        item = object_tbl.item(lastIndex, 0)
        object_tbl.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtTop)
        object_tbl.selectRow(lastIndex)
    if list_column_widths:
        if len(list_column_widths) == object_tbl.columnCount():
            with QSignalBlocker(object_tbl.horizontalHeader()):
                for i in range(object_tbl.columnCount()):
                    object_tbl.setColumnWidth(i,int(list_column_widths[i]))
    if save_column_sort_hh and tbl_object_name:#16.07.25
        FillHorizontalHeaderSort(object_tbl)
    if paret_item == None:
        return object_tbl
    paret_item.setCellWidget(tbl_vidget[0], tbl_vidget[1], object_tbl)
    


def fill_combobox_in_table_c(tbl):
    for i in range(tbl.rowCount()):
        for j in range(tbl.columnCount()):
            if tbl.item(i, j).text() != '':
                if str(type(tbl.cellWidget(i, j))) == "<class 'PyQt5.QtWidgets.QComboBox'>":
                    tbl.cellWidget(i, j).setCurrentText(tbl.item(i, j).text())

def fill_wtabl_old_c(self, spisok, object, set_isp_nomera_col=0, set_editeble_col_nomera=0, spis_filtr_row_soder_item=(),
                 slovar_nkol_simv_iskl_row_pzf=(), ogr_maxshir_kol=200, isp_hat_c=False, separ='|', min_vis_row=30,
                 min_shir_col=30, max_vis_row=40,colorful_edit = True,select_last_row = False):
    object.blockSignals(True)
    try:
        if spisok == False or len(spisok)==0:
            return

        if type(spisok[0]) == type(dict()):
            hat_c = list(spisok[0].keys())
            if type(set_editeble_col_nomera) == type(set()):
                set_editeble_col_nomera = {hat_c.index(item) for item in set_editeble_col_nomera}
            if type(set_isp_nomera_col) == type(set()):
                set_isp_nomera_col = {hat_c.index(item) for item in set_isp_nomera_col}
            rez = [hat_c]
            for item in spisok:
                tmp = []
                for zagolovok in hat_c:
                    if zagolovok in item:
                        tmp.append(item[zagolovok])
                    else:
                        tmp.append('')
                rez.append(tmp)
            spisok = rez


        if set_isp_nomera_col == 0:
            if separ == '':
                set_isp_nomera_col = set(list(range(0, len(spisok[0]))))
            else:
                set_isp_nomera_col = set(list(range(0, len(spisok[0].split(separ)))))
        if set_editeble_col_nomera == 0:
            set_editeble_col_nomera = {}

        object.clear()
        Stroki_filt = list()
        if isp_hat_c == True:
            nach = 1
            Stroki_filt.append(spisok[0])
        else:
            nach = 0
        for line in range(nach, len(spisok)):
            if len(spis_filtr_row_soder_item) > 0:
                for item in spis_filtr_row_soder_item:
                    if item in spisok[line]:
                        Stroki_filt.append(spisok[line])
                        break
            else:
                Stroki_filt.append(spisok[line])
        if len(slovar_nkol_simv_iskl_row_pzf) > 0:
            nach_l = nach - 1
            for line in range(nach, len(Stroki_filt)):
                nach_l += 1
                if separ == '':
                    arr_line = Stroki_filt[nach_l]
                else:
                    arr_line = [x for x in Stroki_filt[nach_l].split(separ)]
                for item in slovar_nkol_simv_iskl_row_pzf.keys():
                    if slovar_nkol_simv_iskl_row_pzf[item] == '':
                        if len(arr_line[item]) == 0:
                            del Stroki_filt[nach_l]
                            nach_l -= 1
                            break
                    if slovar_nkol_simv_iskl_row_pzf[item] == '*':
                        if len(arr_line[item]) > 0:
                            del Stroki_filt[nach_l]
                            nach_l -= 1
                            break

                    if slovar_nkol_simv_iskl_row_pzf[item] != "" and slovar_nkol_simv_iskl_row_pzf[item] != "*" and \
                            slovar_nkol_simv_iskl_row_pzf[item] in arr_line[item]:
                        del Stroki_filt[nach_l]
                        nach_l -= 1
                        break

        isp_kol = set_isp_nomera_col
        hat_c = []
        # object.setColumnCount(FCN.max_kol(Stroki_filt))
        object.setColumnCount(len(isp_kol))
        if isp_hat_c == True:
            object.setRowCount(len(Stroki_filt) - 1)
        else:
            object.setRowCount(len(Stroki_filt))
        koef_hat_c = 0
        for line in range(0, len(Stroki_filt)):
            if len(hat_c) == 0 and isp_hat_c == True:
                koef_hat_c = 1
                if separ == "":
                    arr_hat_c = Stroki_filt[line]
                else:
                    arr_hat_c = [x.strip() for x in Stroki_filt[line].split(separ)]
                for i in range(0, len(arr_hat_c)):
                    if i in isp_kol:
                        hat_c.append(arr_hat_c[i])
                object.setHorizontalHeaderLabels(hat_c)
            else:
                if separ == "":
                    arr_line_temp = Stroki_filt[line]
                else:
                    arr_line_temp = [x.strip() for x in Stroki_filt[line].split(separ)]
                line_temp = []
                for i in range(0, len(arr_line_temp)):
                    if i in isp_kol:
                        line_temp.append(arr_line_temp[i])
                for kol in range(0, len(line_temp)):
                    cellinfo = QtWidgets.QTableWidgetItem(str(line_temp[kol]))
                    if set_editeble_col_nomera != {'*'}:
                        if kol not in set_editeble_col_nomera:
                            # Только для чтения
                            cellinfo.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    object.setItem(line - koef_hat_c, kol, cellinfo)
                    if kol not in set_editeble_col_nomera:
                        if colorful_edit:
                            add_color_wtab_c(object, line - koef_hat_c, kol, 15, 15, 15)
                        else:
                            add_color_wtab_c(object, line - koef_hat_c, kol, 5, 5, 5)
        object.horizontalHeader().setMinimumSectionSize(10)
        object.horizontalHeader().setDefaultSectionSize(20)
        object.verticalHeader().setMinimumSectionSize(10)
        object.verticalHeader().setDefaultSectionSize(20)
        object.resizeColumnsToContents()
        object.horizontalHeader().setStretchLastSection(True)
        object.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        for i in range(0, object.columnCount() + 1):
            if object.columnWidth(i) > ogr_maxshir_kol:
                object.setColumnWidth(i, ogr_maxshir_kol)
            if object.columnWidth(i) < min_shir_col:
                object.setColumnWidth(i, min_shir_col)
        if object.rowCount() > 0:
            height_shap = object.horizontalHeader().height() + 2 * object.rowCount()
            for i in range(0, object.rowCount()):
                height = (object.height() - height_shap) / (object.rowCount())
                if height > min_vis_row and height < max_vis_row:
                    object.setRowHeight(int(i), int(height))
                else:
                    if height < min_vis_row:
                        object.setRowHeight(i, min_vis_row)
                        height = min_vis_row
                    if height > max_vis_row:
                        object.setRowHeight(i, max_vis_row)
        if select_last_row:
            lastIndex = object.rowCount() - 1
            item = object.item(lastIndex, 0)
            object.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtTop)
            object.selectRow(lastIndex)

    except:
        print('ОШибка заполнения таблицы')
    finally:
        object.blockSignals(False)
        

def get_key_modifiers(self):
    QModifiers = QtWidgets.QApplication.keyboardModifiers()
    modifiers = []
    if (QModifiers & QtCore.Qt.ShiftModifier) == QtCore.Qt.ShiftModifier:
        modifiers.append('shift')
    if (QModifiers & QtCore.Qt.ControlModifier) == QtCore.Qt.ControlModifier:
        modifiers.append('control')
    if (QModifiers & QtCore.Qt.AltModifier) == QtCore.Qt.AltModifier:
        modifiers.append('alt')
    return modifiers

def focus_is_QTableWidget():
    if str(type(QtWidgets.QApplication.focusWidget())) == '<class \'PyQt5.QtWidgets.QTableWidget\'>':
        return True
    return False

def copy_bufer_table(tbl):
    spis = list_from_wtabl_c(tbl, sep='',hat_c=True,only_visible=True,only_visible_columns = True)
    F.copy_bufer_list(spis)

def refill_tbl_into_msgbox_get_table(self,tbl:QtWidgets.QTableWidget,msg='Информация'):
    msgboxg_get_table(self,msg=msg,dict_or_list =tbl,btn0_name='ОК',disable_btn1=True,load_summ=True,sortingEnabled=True)





def focus_obj_name():
    fwidget = QtWidgets.QApplication.focusWidget()
    if fwidget is not None:
        return QtWidgets.QApplication.focusWidget().objectName()
    else:
        if QtWidgets.QApplication.focusObject() is not None:
            return QtWidgets.QApplication.focusObject().objectName()
        else:
            None
    
    
def fill_vtable_c(window, obj, spisok, separ='|', isp_hat_c=False, ogr_maxshir_kol=200):
    sti = QtGui.QStandardItemModel(parent=window)

    if isp_hat_c == True:
        if separ == '':
            sti.setHorizontalHeaderLabels(spisok[0])
            for i in range(1, len(spisok)):
                sti.appendRow([QtGui.QStandardItem(x) for x in spisok[i]])
        else:
            sti.setHorizontalHeaderLabels(spisok[0].split(separ))
            for i in range(1, len(spisok)):
                sti.appendRow([QtGui.QStandardItem(x) for x in spisok[i].split(separ)])
    else:
        if separ == '':
            for i in range(0, len(spisok)):
                sti.appendRow([QtGui.QStandardItem(x) for x in spisok[i]])
        else:
            for i in range(0, len(spisok)):
                sti.appendRow([QtGui.QStandardItem(x) for x in spisok[i].split(separ)])

    obj.setModel(sti)
    obj.resizeColumnsToContents()
    if separ == '':
        for i in range(0, len(spisok[0]) + 1):
            if obj.columnWidth(i) > ogr_maxshir_kol:
                obj.setColumnWidth(i, ogr_maxshir_kol)
    else:
        for i in range(0, len(spisok[0].split(separ)) + 1):
            if obj.columnWidth(i) > ogr_maxshir_kol:
                obj.setColumnWidth(i, ogr_maxshir_kol)
                
def colors_into_tree_c(tree, text:list,nom_kol_find:int=0, r:int=11, g:int=11, b:int=11, a:int=255, nom_kol_colour = '*'):
    it = QtWidgets.QTreeWidgetItemIterator(tree)
    while it.value():
        currentItem = it.value()
        if currentItem.text(nom_kol_find) in text:
            if nom_kol_colour == "*":
                for _ in range(0, currentItem.columnCount()):
                    currentItem.setBackground(_, QtGui.QColor(r, g, b, a))
            else:
                currentItem.setBackground(nom_kol_colour, QtGui.QColor(r, g, b, a))
        it += 1

def list_from_tree_c(obj, hat_c = False):
    spisok_tree = []
    if hat_c:
        spis_hat_c = []
        for i in range(obj.columnCount()):
            spis_hat_c.append(obj.headerItem().text(i))
        spisok_tree.append(spis_hat_c)
    it = QtWidgets.QTreeWidgetItemIterator(obj)
    while it.value():
        currentItem = it.value()
        si = []
        for i in range(0, currentItem.columnCount()):
            si.append(currentItem.text(i))
        spisok_tree.append(si)
        it += 1
    return spisok_tree


def save_tree_state(tree_widget:QtWidgets.QTreeWidget):
    state_dict = {}

    def traverse(item):
        state_dict[item.text(0)] = item.isExpanded()
        for i in range(item.childCount()):
            traverse(item.child(i))

    for i in range(tree_widget.topLevelItemCount()):
        traverse(tree_widget.topLevelItem(i))

    return state_dict


def restore_tree_state(tree_widget:QtWidgets.QTreeWidget, state_dict:dict):
    def set_expanded(item):
        if item.text(0) in state_dict:
            if state_dict[item.text(0)]:
                item.setExpanded(True)
            else:
                item.setExpanded(False)
        for i in range(item.childCount()):
            set_expanded(item.child(i))

    for i in range(tree_widget.topLevelItemCount()):
        set_expanded(tree_widget.topLevelItem(i))
        
def fill_wtree_unique(tree:QtWidgets.QTreeWidget, list_dicts:list,  expand:bool = True,
                         min_width = 10):
    """
    list_of_dict.append({'Поле': k, 'Примечание': nick, '_lvl':0,'_Поле_tooltip':nick, '_Поле_gui':
            {'color_background':color_background, 'color_font':color_font, 'bold_font':bold_font, 'italic_font':italic_font,'size_font':size_font}
                             })
    :param tree: 
    :param list_dicts: 
    :param expand: 
    :param min_width: 
    :return: 
    """
    tree.blockSignals(True)
    dict_epand = save_tree_state(tree)

    def calc_row(item:dict)->list:
        clear_item = clear_dict(item)
        row = [_ for _ in clear_item.values()]

        tmp_dict_tooltip = dict()
        for key in item.keys():
            if key.startswith('_') and '_tooltip' in key:
                name_field = key.split('_')[1]
                tmp_dict_tooltip[name_field] = item[key]

        dict_tooltip = dict()
        for i, field in enumerate(clear_item.keys()):
            if field in tmp_dict_tooltip:
                dict_tooltip[i] = tmp_dict_tooltip[field]


        tmp_dict_gui = dict()
        for key in item.keys():
            if key.startswith('_') and '_gui' in key:
                name_field = key.split('_')[1]
                tmp_dict_gui[name_field] = item[key]

        dict_gui = dict()
        for i, field in enumerate(clear_item.keys()):
            if field in tmp_dict_gui:
                dict_gui[i] = tmp_dict_gui[field]

        return row, dict_tooltip, dict_gui

    def clear_dict(dict_cust):
        return {k: v for k, v in dict_cust.items() if not k.startswith('_')}

    tree.setColumnCount(len(clear_dict(list_dicts[0])))
    iter = 0
    for name in clear_dict(list_dicts[0]).keys():
        tree.headerItem().setText(iter,name)
        iter+=1

    tree.clear()
    def add_item(tree, data:dict, parent=None):
        row, tooltip_row, gui_row = calc_row(data)
        if parent:
            item_obj = QtWidgets.QTreeWidgetItem(parent, row)
        else:
            item_obj = QtWidgets.QTreeWidgetItem(tree, row)

        for i, tooltip in tooltip_row.items():
            if tooltip != '':
                item_obj.setToolTip(i, tooltip)


        for i, gui in gui_row.items():
            for key,val in gui.items():
                if val == None:
                    continue
                if key == 'color_font':
                    r, g, b = val.split(';')
                    color = QtGui.QColor.fromRgb(int(r), int(g), int(b))
                    item_obj.setForeground(i, color)
                if key == 'color_background':
                    r, g, b = val.split(';')
                    color = QtGui.QColor.fromRgb(int(r), int(g), int(b))
                    item_obj.setBackground(i, color)

                font = item_obj.font(i)
                if key == 'bold_font':
                    font.setBold(val)
                if key == 'italic_font':
                    font.setItalic(val)
                if key == 'size_font':
                    font.setPointSize(int(val))
                item_obj.setFont(i, font)
        if parent:
            parent.addChild(item_obj)
        else:
            tree.addTopLevelItem(item_obj)
        return item_obj

    dict_levels = dict()

    if isinstance(list_dicts,list):
        base_lvl = list_dicts[0]['_lvl']
        for item_data in list_dicts:
            lvl = item_data['_lvl']
            if lvl == base_lvl:
                current_item_tree = add_item(tree,item_data)
                dict_levels[lvl] = current_item_tree
            if lvl > base_lvl:
                current_item_tree = add_item(tree,item_data,dict_levels[lvl-1])
                dict_levels[lvl] = current_item_tree

    else:
        tree.blockSignals(False)
        return
    if expand:
        tree.expandAll()
    else:
        restore_tree_state(tree, dict_epand)
    if not load_column_widths('',tree,tmp_dir=qt_tmp_dir()):
        for i in range(len(clear_dict(list_dicts[0]))):
            tree.resizeColumnToContents(i)
            if tree.columnWidth(i) < min_width:
                tree.setColumnWidth(i,min_width)
    tree.blockSignals(False)

    

def load_icons(self:object,size:int=32):
    dir = F.sep().join([F.path_to_execut_file_c(), 'icons'])
    if F.existence_file_c(dir):
        try:
            if "ui" in self.__dict__:
                ui = self.ui
            elif "ui2" in self.__dict__:
                ui = self.ui2
            elif "ui3" in self.__dict__:
                ui = self.ui3
        except:
            return 
        for item in ui.__dict__:
            if str(type(ui.__dict__[item])) == "<class 'PyQt5.QtWidgets.QLabel'>":
                name_img = ''
                if F.existence_file_c(dir + F.sep() + item + '.png'):
                    name_img = dir + F.sep() + item + '.png'
                if F.existence_file_c(dir + F.sep() + item + '.ico'):
                    name_img = dir + F.sep() + item + '.ico'
                if F.existence_file_c(dir + F.sep() + item + '.svg'):
                    name_img = dir + F.sep() + item + '.svg'
                if F.existence_file_c(dir + F.sep() + item):
                    name_img = dir + F.sep() + item
                if name_img != '':
                    icon1 = QtGui.QPixmap(name_img)
                    eval(f'ui.{item}.setPixmap(icon1)')
                    eval(f'ui.{item}.setScaledContents(True)')
                    eval(f'ui.{item}.setFixedSize({size}, {size})')
                    eval(f'ui.{item}.setToolTip(self.ui.{item}.text())')
                    eval(f'ui.{item}.setText("")')

            if str(type(ui.__dict__[item])) == "<class 'PyQt5.QtWidgets.QPushButton'>":
                name_img = ''
                if F.existence_file_c(dir + F.sep() + item + '.png'):
                    name_img = dir + F.sep() + item + '.png'
                if F.existence_file_c(dir + F.sep() + item + '.ico'):
                    name_img = dir + F.sep() + item + '.ico'
                if F.existence_file_c(dir + F.sep() + item + '.svg'):
                    name_img = dir + F.sep() + item + '.svg'
                if F.existence_file_c(dir + F.sep() + item):
                    name_img = dir + F.sep() + item
                if name_img != '':

                    icon1 = QtGui.QIcon()
                    icon1.addPixmap(QtGui.QPixmap(name_img), QtGui.QIcon.Normal, QtGui.QIcon.Off)
                    eval(f'ui.{item}.setIcon(icon1)')
                    eval(f'ui.{item}.setIconSize(QtCore.QSize({size}, {size}))')
                    eval(f'ui.{item}.setToolTip(self.ui.{item}.text())')
                    eval(f'ui.{item}.setText("")')

            if str(type(ui.__dict__[item])) == "<class 'PyQt5.QtWidgets.QTabWidget'>":#tabwidget
                for child in ui.__dict__:
                    if str(type(ui.__dict__[child])) == "<class 'PyQt5.QtWidgets.QWidget'>":
                        if eval(f'ui.{item}.isAncestorOf(ui.{child})'):
                            i = eval(f'ui.{item}.indexOf(ui.{child})') 
                            name_img = ''
                            if F.existence_file_c(dir + F.sep() + child + '.png'):
                                name_img = dir + F.sep() + child + '.png'
                            if F.existence_file_c(dir + F.sep() + child + '.ico'):
                                name_img = dir + F.sep() + child + '.ico'
                            if F.existence_file_c(dir + F.sep() + child + '.svg'):
                                name_img = dir + F.sep() + child + '.svg'
                            if F.existence_file_c(dir + F.sep() + child):
                                name_img = dir + F.sep() + child
                            if name_img != '':
                                icon1 = QtGui.QIcon()
                                icon1.addPixmap(QtGui.QPixmap(name_img), QtGui.QIcon.Normal, QtGui.QIcon.Off)
                                eval(f'ui.{item}.setTabIcon({i}, icon1)')
            

def read_err(exc_traceback):
    if exc_traceback.tb_next == None:
        filename = exc_traceback.tb_frame.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, exc_traceback.tb_lineno, exc_traceback.tb_frame.f_globals).strip()
        return filename, exc_traceback.tb_lineno, line
    else:
        return read_err(exc_traceback.tb_next)


def load_css(self, add_menu: bool = True):
    try:
        theme_path =  F.sep().join([F.path_to_execut_file_c(), 'css'])
        config_theme_path = theme_path + F.sep() + 'current_theme_name.txt'
        if 'css_theme' in self.USER_CONFIG.__dict__:
            theme = self.USER_CONFIG.css_theme['Значение']
            apply_css_theme(self, theme_path + F.sep() + theme + '.qss')
        else:
            
            if F.existence_file_c(config_theme_path):
                theme = F.load_file(config_theme_path)
                apply_css_theme(self,theme)
            else:
                self.setStyleSheet(None)
    except:
        pass

def apply_css_theme(self,file_path_name):
    try:
        spis_korr = use_CSS_c(F.open_file_c(file_path_name))
        if spis_korr == '':
            self.setStyleSheet(None)
            return True
        self.setStyleSheet("".join(spis_korr))
        return True
    except:
        self.setStyleSheet(None)
        return False

def select_theme(*args):
    self = args[0][0]
    path_file_name = args[0][1]
    path = F.sep().join([F.path_to_execut_file_c(), 'css','current_theme_name.txt'])
    F.save_file(path,path_file_name)
    print(f'CSS:{path} сохранен путь темы {path_file_name}')
    rez  = apply_css_theme(self,path_file_name)
    if rez == False:
        try:
            F.delete_file_c(F.sep().join([F.path_to_execut_file_c(), 'css','current_theme_name.txt']))
        except:
            pass


def get_hover_row_col(self, tbl:QtWidgets.QTableWidget, event):
    """"#self.ui.tbl.setMouseTracking(True)
    #self.ui.tbl.mouseMoveEvent = self.func(): ... r, c =  get_hover_row_col"""
    row = 0
    column = 0
    y = event.pos().y()
    x = event.pos().x()
    left = 0
    rigth = 0
    hor = tbl.horizontalScrollBar().value()
    vert = tbl.verticalScrollBar().value()


    start = 0
    for column in range(tbl.columnCount()):
        if tbl.columnWidth(column) == 0:
            start +=1
        else:
            break
    start+= hor

    for column in range(start, tbl.columnCount()):
        rigth += tbl.columnWidth(column)
        if column >= tbl.columnCount() - 1:
            #print(f'Column {column + 1}')
            break
        if left <= x and x < rigth:
            #print(f'Column {column}')
            break
        left += tbl.columnWidth(column)


    up = 0
    down = 0

    start = 0
    for row in range(tbl.rowCount()):
        if tbl.rowHeight(row) == 0:
            start +=1
        else:
            break
    start+= vert

    for row in range(start, tbl.rowCount()):
        down += tbl.rowHeight(row)
        if row >= tbl.rowCount() - 1:
            #print(f'Row {row + 1}')
            break
        if up <= y and y < down:
            #print(f'Row {row}')
            break
        up += tbl.rowHeight(row)
    fl = False
    if 'hover_row' not in self.__dict__:
        self.hover_row = row
        fl = True
    else:
        if self.hover_row != row:
            fl = True
            self.hover_row = row
    if 'hover_column' not in self.__dict__:
        self.hover_column = column
        fl = True
    else:
        if self.hover_column != column:
            fl = True
            self.hover_column = column
    if fl:
        return row, column
    else:
        return None, None


def summ_selct_tbl(self,tbl):
    summ= 0
    sch = 1
    self.glob_kpl_summ_selct_tbl = f'                                         '
    try:
        #tbl = self.ui.tbl_kal_pl
        #col = tbl.currentColumn()
        #row = tbl.currentRow()
        summ = 0
        sch = 0
        for ix in tbl.selectedIndexes():
            #if col == ix.column():
            try:
                if F.is_numeric(ix.data()):
                    summ+=F.valm(ix.data())
                    sch+=1
            except:
                pass
        self.glob_kpl_summ_selct_tbl = f'                                         Сумма: {summ},  Среднее: {round(summ/sch,3)}'
    except:
        pass
    try:
        self.glob_kpl_summ_selct_tbl = f'                                         Сумма: {summ},  Среднее: {round(summ / sch,3)}'
    except:
        pass
    statusbar_text(self,self.glob_kpl_summ_selct_tbl)


def onerror(funcd):
    def wrapper(self, *args, **kwargs):
        try:
            rez = funcd(self, *args, **kwargs)
            return rez
        except Exception as ex:
            exc_type, exc_instance, exc_traceback = sys.exc_info()
            ver = '-'
            try:
                ver = self.versia
            except:
                pass
            list_trace = repr(traceback.extract_tb(exc_traceback)).split(',')
            # list_trace.reverse()
            counetr = 1
            for i in range(len(list_trace)):
                list_trace[i] = list_trace[i].replace('<FrameSummary', '') + ":"
                if i % 2 == 0:
                    list_trace[i] = f'Step {counetr}: ' + list_trace[i]
                    counetr += 1
                else:
                    sub_list_trace = list_trace[i].split()
                    list_trace[i] = f'''   fnc {sub_list_trace[3].replace('>', '')}\n        line {sub_list_trace[1]}\n'''
            tarcer = '\n'.join(list_trace)

            filename, lineno, line = read_err(exc_traceback)
            txt = (f'File:"{filename}\n    fnc {funcd.__name__}"\n        line {lineno}:\n{'\n'.join([f'            {_}' for _ in line.split('\n')])}\n '
                   f'unexpected error:\n   "{exc_instance}"\n'
                   f'===============FRAMES START===================\n'
                   f'{tarcer}\n'
                   f'===============FRAMES END===================\n\n')
            print(txt)
            arguments = '({pos}, {named})'.format(
                pos=', '.join(str(arg) for arg in (self, *args)),
                named=', '.join(f'{key}={val}' for key, val in kwargs.items())
            )
            line = [
                F.name_of_executable_file_c(),
                F.now(),
                ver,
                F.user_name(),
                F.computer_name(),
                filename,
                funcd.__name__,
                arguments,
                lineno,
                line,
                exc_instance,
                str(traceback.extract_tb(exc_traceback))
            ]
            add_error_line_in_debug_reestr(line)
            msgbox(txt, time_life=10, icon=QtWidgets.QMessageBox.Critical)
    return wrapper

def add_error_line_in_debug_reestr(line: list):
    if not F.is_debug():
        path = r'Z:\MES_setup\errors\debug.txt'
        with open(path, 'a+', encoding='utf8') as f:
            f.write('|'.join(str(column).replace('|', '%7C') for column in line) + '\n')

def add_err_to_debug(list, path):
    if F.existence_file_c(path) == False:
        F.save_file(path, [list])
    else:
        file_debug = F.open_file_c(path, utf8=True, separ='|')
        file_debug.append(list)
        F.save_file(path, file_debug)



def msgboxgYN(msg, btn0_name="Да", btn1_name="Нет", func_theme = '', icon = QtWidgets.QMessageBox.Question,fontsize=14,icon_str=None):
    """icon = NoIcon, Question, Information, Warning, Critical """
    if icon_str != None:
        icon = eval(f'QtWidgets.QMessageBox.{icon_str}')
    msgBox = QtWidgets.QMessageBox()
    # self.modal = 1
    msgBox.setIcon(icon)
    font = msgBox.font()
    font.setPointSize(int(fontsize))
    msgBox.setFont(font)
    msgBox.setText(msg)
    msgBox.setWindowTitle("Внимание!")
    # msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
    buttonoptionA = msgBox.addButton(btn0_name, QtWidgets.QMessageBox.YesRole)
    buttonoptionB = msgBox.addButton(btn1_name, QtWidgets.QMessageBox.AcceptRole)
    msgBox.setWindowModality(QtCore.Qt.ApplicationModal)
    # msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    # msgBox.setFocus()
    if func_theme != '':
        func_theme(msgBox)

    config_theme_path = F.sep().join([F.path_to_execut_file_c(), 'css', 'current_theme_name.txt'])
    if F.existence_file_c(config_theme_path):
        theme = F.load_file(config_theme_path)
        apply_css_theme(msgBox, theme)
    else:
        msgBox.setStyleSheet(None)

    returnValue = msgBox.exec()

    # msgBox.buttonClicked.connect(msgButtonClick)
    if returnValue == 0:
        return True
    return False

#def msg_dialog_box_get_table(self, msg, btn0_name="Да", btn1_name="Нет", func_theme = '', icon = QtWidgets.QMessageBox.Question):
#    self.msgboxg_get_table = None
#
#   self.w3 = msgboxg(self,msg)
#   
#    return 




def msgbox(msg, btn0_name="OK", func_theme = '', time_life = 0, icon = QtWidgets.QMessageBox.Information,fontsize=14,icon_str=None):
    """icon = NoIcon, Question, Information, Warning, Critical """
    if icon_str != None:
        icon = eval(f'QtWidgets.QMessageBox.{icon_str}')
    try:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(icon)
        msgBox.setText(msg)
        font = msgBox.font()
        font.setPointSize(int(fontsize))
        msgBox.setFont(font)
        msgBox.setWindowTitle("Внимание!")
        # msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)  # | QtWidgets.QMessageBox.Cancel)
        msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        msgBox.setWindowModality(QtCore.Qt.ApplicationModal)

        buttonoptionA = msgBox.addButton(btn0_name, QtWidgets.QMessageBox.YesRole)
        if time_life>0:
            QtCore.QTimer.singleShot(round(time_life*1000), lambda: msgBox.done(0))

        config_theme_path = F.sep().join([F.path_to_execut_file_c(), 'css', 'current_theme_name.txt'])
        if F.existence_file_c(config_theme_path):
            theme = F.load_file(config_theme_path)
            apply_css_theme(msgBox, theme)
        else:
            msgBox.setStyleSheet(None)

        returnValue = msgBox.exec()
        

        #msgBox.exec_()
        if func_theme != '':
            func_theme(msgBox)
    except:
        print(f'Ошибка вывода в  gui {msg}')



def _load_tbl(tbl:QtWidgets.QTableWidget,tblf:QtWidgets.QTableWidget,hidden_scrol=False,count_rows=1):
    QtWidgets.QApplication.processEvents()
    font = QtGui.QFont()
    font.setPointSize(8)
    tblf.verticalHeader().setFont(font)
    tblf.horizontalHeader().setFont(font)

    for i in range(tblf.columnCount()):
        tblf.setColumnWidth(i, tbl.columnWidth(i))
        if tbl.isColumnHidden(i):
            tblf.hideColumn(i)
        else:
            tblf.showColumn(i)
    non_zero_height = 0
    for i in range(tbl.rowCount()):
        if tbl.rowHeight(i)>0:
            non_zero_height = tbl.rowHeight(i)
            break
    if non_zero_height == 0:
        non_zero_height = 24
    tblf.setRowHeight(0, non_zero_height)
    tblf.setFixedHeight(non_zero_height *count_rows+ tblf.horizontalHeader().height() + 1)
    if hidden_scrol:
        tblf.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

        tbl.horizontalScrollBar().valueChanged.connect(
            tblf.horizontalScrollBar().setValue)
        tblf.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        tbl.horizontalHeader().sectionResized.connect(tblf.setColumnWidth)
        tblf.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

    tblf.verticalHeader().setFixedWidth(tbl.verticalHeader().width())

@progress_decorator
def get_answ_ai(promt,hook_prog_bar=None):#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
    hook_prog_bar.set(1)
    hook_prog_bar.text('Построение запроса')
    # Replace with your OpenRouter API key
    API_KEY = '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'
    API_URL = 'https://openrouter.ai/api/v1/chat/completions'

    # Define the headers for the API request
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    len(promt) / 1011  
    # Define the request payload (data)
    data = {
        "model": "deepseek/deepseek-chat:free",
        "messages": [{"role": "user", "content": promt}]
    }

    # Send the POST request to the DeepSeek API
    hook_prog_bar.set(5)
    hook_prog_bar.text('Анализ данных подождите...')
    response = requests.post(API_URL, json=data, headers=headers)
    hook_prog_bar.set(99)
    hook_prog_bar.text('Компоновка результата')
    # Check if the request was successful
    if response.status_code == 200:
        #print("API Response:", response.json())
        return response.status_code, response.json()['choices'][0]['message']['content']
    else:
        return response.status_code, f"Failed to fetch data from API. Status Code:{response.status_code}"

class Dialog_tbl(QtWidgets.QDialog):  # диалоговое окно
    def __init__(self, parent, msg:str, dict_or_list, btn0_name:str="Ввод",
                 btn1_name:str="Отмена", func_validate=None,
                 disable_btn0=False, disable_btn1=False, load_summ=False,
                 show_filtr=True, WindowTitle='Выбор варианта',
                 style_icon='SP_MessageBoxInformation', func_oform_tbl=None,
                 use_first_row_as_header=True, print_hat=True,
                 func_btn0=None, selection_from_tbl=False, ExtendedSelection=True, selectRows=False,
                 func_oform_filtr=None, load_links=False, conn_func_label_link=None, styleSheet=None, parent_self=None,
                 sortingEnabled=False, not_standart_close=False, save_column_sort_hh: bool = False):
        """        #SP_MessageBoxCritical
        #SP_MessageBoxInformation
        #SP_MessageBoxQuestion
        #SP_MessageBoxWarning"""
        from project_cust_38.dialog import Ui_Dialog
        super(Dialog_tbl, self).__init__()
        self.print_hat = print_hat
        self.parent_self = parent_self
        self.glob_selection_from_tbl = selection_from_tbl
        space = 10
        y_space = 15
        x_space = 55
        label_x_start = x_space
        label_y_start = space
        btn_height = 30

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.hide_widgets()
        self.ui.btn_add_res_field.clicked.connect(self.on_click_add_sum_fields)
        self.ui.btn_add_gr_field.clicked.connect(self.on_click_add_group_field)
        self.ui.btn_del_gr_field.clicked.connect(lambda *_: self.on_click_drop_field(self.ui.tbl_add_gr_field))
        self.ui.btn_del_res_field.clicked.connect(lambda *_: self.on_click_drop_field(self.ui.tbl_add_res_field))
        self.ui.btn_ok.clicked.connect(self.on_click_group_by)
        self.ui.btn_reset.clicked.connect(self.clear_add_field_tables)
        self.ui.cmb_action.addItems(['Файл',
                                     'Сохранить Exel как...',
                                     'Сохранить выдел. область Exel как...',
                                     'Сохранить выдел. область Exel как... TEST',
                                     'Компоновка',
                                     'Анализ таблицы'])
        self.ui.cmb_action.activated[int].connect(self.select_action)

        tbl = self.ui.tbl
        tblf = self.ui.tbl_filtr
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.myparent = parent

        self.ui.tbl.doubleClicked.connect(self.select_row)

        try:
            icon = QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(eval(f'QtWidgets.QStyle.{style_icon}')))
        except:
            icon = QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation))

        self.msgboxg_get_table = None
        self.ui.lbl_icon.setPixmap(icon.pixmap(24, 24))
        self.ui.lbl_text.setText(msg)
        ft = self.ui.lbl_text.font()
        ft.setPixelSize(18)
        self.ui.lbl_text.setFont(ft)
        self.ui.lbl_text.setWordWrap(True)

        colorful_edit = True
        if isinstance(dict_or_list, QtWidgets.QTableWidget):
            list_usefull_rows = [_ for _ in range(dict_or_list.rowCount()) if not dict_or_list.isRowHidden(_)]
            tbl.setSortingEnabled(sortingEnabled)
            tbl.setRowCount(len(list_usefull_rows))

            if dict_or_list.verticalHeaderItem(0):
                tbl.setVerticalHeaderLabels(
                    [dict_or_list.verticalHeaderItem(_).text() for _ in range(dict_or_list.rowCount()) if
                     _ in list_usefull_rows])
                for i, row in enumerate(list_usefull_rows):
                    tbl.verticalHeaderItem(i).setFont(dict_or_list.verticalHeaderItem(row).font())

            list_usefull_cols = [_ for _ in range(dict_or_list.columnCount()) if
                                 not dict_or_list.isColumnHidden(_) and dict_or_list.columnWidth(_) > 3]

            tbl.setColumnCount(len(list_usefull_cols))
            for i, column in enumerate(list_usefull_cols):
                tbl.setColumnWidth(i, dict_or_list.columnWidth(column))

            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
            if dict_or_list.horizontalHeaderItem(0):
                tbl.setHorizontalHeaderLabels([dict_or_list.horizontalHeaderItem(_).text() for _ in list_usefull_cols])
                for i, column in enumerate(list_usefull_cols):
                    tbl.horizontalHeaderItem(i).setFont(dict_or_list.horizontalHeaderItem(column).font())

            for i, row in enumerate(list_usefull_rows):

                tbl.setRowHeight(i, dict_or_list.rowHeight(row))

                for j, column in enumerate(list_usefull_cols):

                    item = dict_or_list.item(row, column)
                    if item is not None:
                        new_item = QtWidgets.QTableWidgetItem(item.text())
                        new_item.setFont(item.font())
                        new_item.setBackground(item.background())  # Копируем стиль
                        new_item.setForeground(item.foreground())
                        new_item.setFlags(item.flags())
                        tbl.setItem(i, j, new_item)
            if FillHorizontalHeaderSort.is_mutable(dict_or_list): # 16.07.25
                FillHorizontalHeaderSort(tbl)
        else:
            if not use_first_row_as_header:
                colorful_edit = False
                if isinstance(dict_or_list[0], dict):
                    #dict_or_list.insert(0, {k: str(i) for i, k in enumerate(dict_or_list[0].keys())})
                    pass
                else:
                    dict_or_list.insert(0, [str(i) for i, v in enumerate(dict_or_list[0])])
            fill_wtabl(dict_or_list, tbl, height_row=25, auto_type=False, colorful_edit=colorful_edit,
                       load_links=load_links, conn_func_label_link=conn_func_label_link,styleSheet=styleSheet,parent_self=parent_self,sortingEnabled=sortingEnabled,
                       save_column_sort_hh=save_column_sort_hh)
        if func_oform_tbl:
            if parent_self:
                func_oform_tbl(tbl,parent_self)
            else:
                func_oform_tbl(tbl)
        if selectRows:
            tbl.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectRows)
        else:
            tbl.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectItems)
        if ExtendedSelection:
            tbl.setSelectionMode(QtWidgets.QTableWidget.SelectionMode.ExtendedSelection)
        else:
            tbl.setSelectionMode(QtWidgets.QTableWidget.SelectionMode.SingleSelection)
        
        summ_width = 0
        for clmn in range(tbl.columnCount()):
            summ_width += (tbl.columnWidth(clmn) + 1)
        limit = 1920
        min_limit = 640
        width_dialog = summ_width + x_space + space
        if width_dialog > limit:
            width_dialog = limit
        if width_dialog < min_limit:
            width_dialog = min_limit
        self.setMinimumWidth(width_dialog)
        tbl.setToolTip(
            'F11 - полный экран')
        if show_filtr:
            hat_c = {tbl.horizontalHeaderItem(col).text(): "" for col in range(tbl.columnCount())}
            fill_wtabl([hat_c], tblf, height_row=25, auto_type=False,
                       set_editeble_col_nomera={_ for _ in range(tbl.columnCount())})
            _load_tbl(tbl, tblf, True)
            tblf.setToolTip(
                "фильтр по вхождению: \n* - любой символ\n! - не\n= - полное совпадение\n| - ИЛИ\n& - И\n'... - RegEx \nдаты: <24-11-11 & >24-11-01")
            if func_oform_filtr:
                if parent_self:
                    func_oform_filtr(tbl, tblf,parent_self)
                else:
                    func_oform_filtr(tbl, tblf)
        else:
            tblf.setHidden(True)

        self.ui.tbl_summ.setHidden(True)
        if load_summ:
            self.ui.tbl_summ.setHidden(False)
            fill_summ_tbl(self, self.ui.tbl_summ, tbl, hidden_scroll=True)
            _load_tbl(tbl, self.ui.tbl_summ, True)

        summ_tbl_height = 0
        for i in range(tbl.rowCount()):
            summ_tbl_height += tbl.rowHeight(i)
        if summ_tbl_height > 500:
            summ_tbl_height = 500

        self.setMinimumHeight(300 + summ_tbl_height)
        self.resize(width_dialog, 300 + summ_tbl_height)
        btn_width = int(round((self.width() / 2 - space * 2) / 2))
        # Устанавливаем политику размера
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.ui.lbl_text.setSizePolicy(size_policy)
        self.yes_btn = None
        if not disable_btn0:
            if not_standart_close:
                buttonoptionA = self.ui.buttonBox.addButton(btn0_name, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)
            else:
                buttonoptionA = self.ui.buttonBox.addButton(btn0_name, QtWidgets.QDialogButtonBox.ButtonRole.YesRole)
            buttonoptionA.setFixedHeight(30)
            buttonoptionA.setFixedWidth(btn_width)
            buttonoptionA.setAutoDefault(False)
            font = buttonoptionA.font()
            font.setPixelSize(14)
            buttonoptionA.setFont(font)
            self.yes_btn = buttonoptionA
            if func_btn0:
                # For ActionRole buttons, prevent dialog closing
                if not_standart_close:
                    #=============example===========
                    #if btn.text() == 'smth':
                    #    ...
                    #    dialog.accept()
                    #else:
                    #    dialog.reject()
                    #
                    # =============example===========

                    # Disconnect standard signals
                    self.ui.buttonBox.accepted.disconnect()
                    self.ui.buttonBox.rejected.disconnect()

                    # Connect custom handler
                    if parent_self:
                        self.ui.buttonBox.clicked.connect(lambda btn, dialog=self, t=tbl, p=parent_self: func_btn0(btn, dialog, t, p))# Dialog won't close unless you call accept()/reject()
                    else:
                        self.ui.buttonBox.clicked.connect(lambda btn, dialog=self, t=tbl: func_btn0(btn, dialog, t))# Dialog won't close unless you call accept()/reject()

                else:
                    if parent_self:
                        buttonoptionA.clicked.connect(lambda: func_btn0(tbl,parent_self))
                    else:
                        buttonoptionA.clicked.connect(lambda: func_btn0(tbl))
        if not disable_btn1:
            buttonoptionB = self.ui.buttonBox.addButton(btn1_name, QtWidgets.QDialogButtonBox.ButtonRole.NoRole)
            buttonoptionB.setFixedHeight(30)
            buttonoptionB.setFixedWidth(btn_width)
            buttonoptionB.setAutoDefault(False)
            font = buttonoptionB.font()
            font.setPixelSize(14)
            buttonoptionB.setFont(font)

        self.setWindowTitle(WindowTitle)
        # msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)

        self.setWindowModality(QtCore.Qt.ApplicationModal)
        # msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        # msgBox.setFocus()
        # load_css(self,add_menu=False)
        self.setStyleSheet(parent.styleSheet())
        load_icons(self, 24)
        self.oform_action()
        return

    def hide_widgets(self):
        self.ui.fr_figures.setHidden(True)
        self.ui.fr_groups.setHidden(True)

    def unpack_additional_params(self):
        tbl = self.ui.tbl_add_res_field
        params = {}
        nk_field = num_col_by_name_c(tbl, 'Поля')
        nk_type_sum = num_col_by_name_c(tbl, 'ВидСуммы')
        for row in range(tbl.rowCount()):
            field_item = tbl.item(row, nk_field)
            cmb_cell: QtWidgets.QComboBox = tbl.cellWidget(row, nk_type_sum)
            if isinstance(cmb_cell, QtWidgets.QComboBox) and field_item:
                type_sum = cmb_cell.currentText()
                field_name = field_item.text()
                params[field_name] = type_sum
        return params

    def unpack_visible_fields(self):
        tbl = self.ui.tbl_fields
        tbl_gr = self.ui.tbl_add_gr_field
        tbl_sum = self.ui.tbl_add_res_field
        col_visible = num_col_by_name_c(tbl, 'Видимость')
        col_field = num_col_by_name_c(tbl, 'Поля')
        result = [*self.unpack_fields(tbl_gr), *self.unpack_fields(tbl_sum)]
        if col_visible is not None and col_field is not None:
            for row in range(tbl.rowCount()):
                cell = tbl.cellWidget(row, col_visible)
                item = tbl.item(row, col_field)
                if isinstance(cell, QtWidgets.QCheckBox) and cell.isChecked():
                    result.append(item.text())
        return result

    def unpack_fields(self, tbl: QtWidgets.QTableWidget):
        result = []
        col_field = num_col_by_name_c(tbl, 'Поля')
        if col_field is not None:
            for row in range(tbl.rowCount()):
                result.append(tbl.item(row, col_field).text())
        return result

    @onerror
    def on_click_group_by(self, *args):
        row_groups = [group[0] for group in list_from_wtabl_c(self.ui.tbl_add_gr_field) if group]
        row_sums = [g_sum[0] for g_sum in list_from_wtabl_c(self.ui.tbl_add_res_field) if g_sum]
        if not row_groups and not row_sums:
            self.fill_main_tbl(self.stack.current_data.data)
        else:
            additional_fields_params = self.unpack_additional_params()
            actual_data = list_from_wtabl_c(self.ui.tbl, only_visible=True, rez_dict=True)
            self.data_parser = DataParser(actual_data, additional_fields_params)
            groups = self.data_parser.group_by_columns(row_groups, row_sums, additional_fields_params)
            result = groups.to_list()
            self.fill_main_tbl(result)
            self.decor_group_by_tbl(groups)
            msg = """
                Ячейки участвующие в суммировании/группировки помечены КУРСИВОМ И ПОДЧЕРКИВАНИЕМ
                Ячейки измененные путем группировки помечены ЖИРНЫМ ШРИФТОМ
            """
            self.ui.tbl.setToolTip(msg)

    def decor_group_by_tbl(self, groups: Grouper):
        tbl = self.ui.tbl
        sum_cols = list(groups.sum_columns)
        group_cols = list(groups.group_columns)
        header = [tbl.horizontalHeaderItem(col).text() for col in range(tbl.columnCount())]
        cleaning_sum_cols = set(header).intersection(sum_cols)
        cleaning_gr_cols = set(header).intersection(group_cols)
        for row_idx in range(tbl.rowCount()):
            unique_key = tuple(tbl.item(row_idx, num_col_by_name_c(tbl, col)).text() for col in cleaning_gr_cols)
            is_mutable_row = False
            if unique_key in groups.groups:
                group_object = groups.groups[unique_key]
                is_mutable_row = any(group_object.state_mutable.values())
            for col_idx in range(tbl.columnCount()):
                header_name = tbl.horizontalHeaderItem(col_idx).text()
                item = tbl.item(row_idx, col_idx)
                font = item.font()
                if header_name in cleaning_gr_cols or header_name in cleaning_sum_cols:
                    font.setItalic(True)
                    font.setUnderline(True)
                font.setBold(is_mutable_row)
                item.setFont(font)

    def clear_add_field_tables(self, *args):
        self.stack.clear_stack()

    def fill_main_tbl(self, data: list[dict]):
        tbl = self.ui.tbl
        new_columns = [key for key, val in self.data_parser.header_types.items()
                       if key not in self.data_parser.header
                       and key not in self.data_parser.dump_groups.sum_columns
                       and key not in self.data_parser.dump_groups.group_columns
                       ]
        self.data_parser.header = list(self.data_parser.header_types.keys())
        visible_columns = self.unpack_visible_fields() + new_columns
        filtered_data = [{key: val for key, val in row.items() if key in visible_columns} for row in data]
        lst_sums = list_from_wtabl_c(self.ui.tbl_add_res_field, rez_dict=True, only_visible=True)
        lst_groups = self.data_parser.dump_groups.group_columns
        data_types = self.data_parser.dump_groups.header_types
        fields_data = self.data_parser.make_fields_data_for_table(exclude_aggregated=True)
        self.fill_tbl_fields(fields_data, visible_columns)
        self.stack.add_block(
            data=filtered_data,
            header_types=data_types,
            sum_elems=lst_sums,
            group_elems=lst_groups,
            fields_data=fields_data,
            visible_columns=visible_columns,
            grouper=self.data_parser.dump_groups
        )
        fill_wtabl(filtered_data, tbl)
        fill_summ_tbl(self, self.ui.tbl_summ, tbl, hidden_scroll=True)
        fill_filtr_c(self, self.ui.tbl_filtr, tbl)

    def on_click_add_group_field(self, *args):
        cur_tbl = self.ui.tbl_add_gr_field
        tbl_fields = self.ui.tbl_fields
        cur_row = tbl_fields.currentRow()
        if cur_row == -1:
            return
        prev_tbl_items = list_from_wtabl_c(cur_tbl, rez_dict=True)
        cur_item = get_dict_line_form_tbl(tbl_fields, cur_row)

        prev_tbl_items.append({'Поля': cur_item.get('Поля')})
        tbl_fields.removeRow(cur_row)
        fill_wtabl(prev_tbl_items, cur_tbl)

    @onerror
    def on_click_drop_field(self, cur_tbl):
        tbl_field = self.ui.tbl_fields
        cur_row = cur_tbl.currentRow()
        if cur_row == -1:
            return
        col_field = num_col_by_name_c(tbl_field, 'Поля')
        if col_field is not None:
            new_field = valt(cur_tbl, 'Поля', cur_row)
            prev_lst = [tbl_field.item(row, col_field).text() for row in range(tbl_field.rowCount())] + [new_field]
            cur_tbl.removeRow(cur_row)
            sum_fields = [item.get('Поля') for item in list_from_wtabl_c(self.ui.tbl_add_res_field, rez_dict=True)]
            gr_fields = [item.get('Поля') for item in  list_from_wtabl_c(self.ui.tbl_add_gr_field, rez_dict=True)]
            fields = self.data_parser.make_fields_data_for_table(sum_cols=sum_fields, group_cols=gr_fields, exclude_aggregated=True)
            visible = self.unpack_visible_fields() + [new_field]
            self.fill_tbl_fields(fields, visible)

    @onerror
    def on_click_add_sum_fields(self, *args):
        cur_tbl = self.ui.tbl_add_res_field
        tbl_fields = self.ui.tbl_fields
        cur_row = tbl_fields.currentRow()
        if cur_row == -1:
            return
        lst_prev_values = list_from_wtabl_c(cur_tbl, rez_dict=True)
        col_field = num_col_by_name_c(tbl_fields, 'Поля')
        col_cur_sum = num_col_by_name_c(tbl_fields, 'ВидСуммы')
        col_cur_type = num_col_by_name_c(tbl_fields, 'Тип')
        if col_field is not None and col_cur_sum is not None and col_cur_type is not None:
            field = tbl_fields.item(cur_row, col_field).text()
            data_type_alias = tbl_fields.item(cur_row, col_cur_type).text()
            cur_sum = tbl_fields.item(cur_row, col_cur_sum).text()
            lst_prev_values.append({'Поля': field, 'Тип': data_type_alias, 'ВидСуммы': cur_sum})
            fill_wtabl(lst_prev_values, cur_tbl)
            self.decor_field_tbl(cur_tbl)
            tbl_fields.removeRow(cur_row)

    def decor_field_tbl(self, cur_tbl: QtWidgets.QTableWidget):
        col_cur_sum = num_col_by_name_c(cur_tbl, 'ВидСуммы')
        col_type = num_col_by_name_c(cur_tbl, 'Тип')
        for row in range(cur_tbl.rowCount()):
            data_type_alias = cur_tbl.item(row, col_type).text()
            data_type = DataTypes()[data_type_alias]
            if data_type.alias:
                cur_sum = cur_tbl.item(row, col_cur_sum).text()
                if not cur_sum or cur_sum not in data_type.params:
                    cur_tbl.item(row, col_cur_sum).setText(data_type.default)
                if col_cur_sum:
                    add_combobox(self=cur_tbl, table=cur_tbl, i=row, j=col_cur_sum, list=data_type.params,
                                 first_void=not bool(data_type.default), conn_func=self.on_cmb_sum_changed)
                rgb = data_type.rgba
                for col in range(cur_tbl.columnCount()):
                    set_color_wtab_c(cur_tbl, row, col, *rgb)

    def on_cmb_sum_changed(self, cur_tbl, text, row, col, *args):
        cur_tbl.item(row, col).setText(text)



    @onerror
    def select_action(self, i, *args):
        text = self.ui.cmb_action.itemText(i)
        self.ui.cmb_action.blockSignals(True)
        self.ui.cmb_action.setCurrentIndex(0)
        self.ui.cmb_action.blockSignals(False)
        if text == 'Сохранить Exel как...':
            rez = self.save_as_excel(self.ui.tbl)
        if text == 'Сохранить выдел. область Exel как...':
            list_rows = [_.row() for _ in self.ui.tbl.selectionModel().selectedIndexes()]
            list_columns = [_.column() for _ in self.ui.tbl.selectionModel().selectedIndexes()]
            if not len(list_rows) or not len(list_columns):
                msgbox(f'Диапазон не выбран')
                return
            rez = self.save_as_excel(self.ui.tbl, r1=min(list_rows), c1=min(list_columns), r2=max(list_rows),
                                     c2=max(list_columns))
        if text == 'Сохранить выдел. область Exel как... TEST':
            list_rows = [_.row() for _ in self.ui.tbl.selectionModel().selectedIndexes()]
            list_columns = [_.column() for _ in self.ui.tbl.selectionModel().selectedIndexes()]
            if not len(list_rows) or not len(list_columns):
                msgbox(f'Диапазон не выбран')
                return
            rez = self.save_as_excel_test(self.ui.tbl, r1=min(list_rows), c1=min(list_columns), r2=max(list_rows),
                                     c2=max(list_columns))
        if text == 'Компоновка':
            tbl = self.ui.tbl
            data = list_from_wtabl_c(tbl, rez_dict=True)
            self.data_parser = DataParser(data)
            self.ui.fr_groups.setVisible(True)
            fields = [
                {'Поля': head, 'Тип': data_type.alias, 'ВидСуммы': 'Первое', 'Видимость': ''}
                for head, data_type in self.data_parser.header_types.items()
            ]
            self.fill_tbl_fields(fields, self.data_parser.header_types.keys())
            visible_columns = self.unpack_visible_fields()
            self.stack = HistoryStack(
                # data
                window=self,
                init_data=self.data_parser.body,
                fields_data=fields,
                header_types=self.data_parser.header_types,
                visible_columns=visible_columns,
                # table_widgets
                stack_table=self.ui.tbl_stack_groups,
                data_table=self.ui.tbl,
                data_filter_table=self.ui.tbl_filtr,
                data_sum_table=self.ui.tbl_summ,
                field_table=self.ui.tbl_fields,
                sum_table=self.ui.tbl_add_res_field,
                decor_field_tbl=self.decor_field_tbl,
                name_edit_input=self.ui.le_name_group,
                # functions,
                group_table=self.ui.tbl_add_gr_field,
                input_for_stack_name=self.ui.le_name_group,
                fill_tbl_fields=self.fill_tbl_fields,
                decor_grouped_data=self.decor_group_by_tbl
            )
            for row in range(tbl.rowCount()):
                for col in range(tbl.columnCount()):
                    if item := tbl.item(row, col):
                        item.setBackground(QtGui.QColor(240, 240, 240))
                        item.setForeground(QtGui.QColor(15, 15, 15))
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.ui.tbl_fields.setSelectionMode(QTableWidget.SingleSelection)

        if text == 'Анализ таблицы':

            promt = f"""
            Можешь проверить таблицу на Сезонность и периодичность, Аномалии и выбросы,  и если это достоверно дать Прогнозирование. 
            Результат представь в виде сухих данных без вступлений, описаний, размышелний, предложений.
            пример ответа:
            1. Сезонность и периодичность:
                Факт, уд.т.: Значения сильно варьируются, но можно заметить, что в некоторые месяцы (например, апрель и декабрь) значения выше. 
                ...
                Внеплан, %: Значения варьируются, но нет явной сезонности.
            
            2. Аномалии и выбросы
                Факт, уд.т.: Высокие значения в апреле (125,65) и декабре (108,55).
                ...
                Освоено плановых, н-см.: Низкие значения в сентябре (581,25) и январе 2025 (600,93).
            3. Прогнозирование
                Факт, уд.т.: Возможен рост в конце года (на основе данных за декабрь).
                ...
            
              по следующей таблице: 
            """ + F.generate_exel_copy_notation_text(list_from_wtabl_c(self.ui.tbl,hat_c=True,only_visible=True,only_visible_columns=True))
            if len(promt) > (128000-1000)*2:
                msgbox(f'Размер таблицы слишком большой')
                return
            code, resp = get_answ_ai(promt)
            resp = [_.split('    ') for _ in resp.split('\n')]
            max_len = max([len(_) for _ in resp])
            for item in resp:
                for i in range(max_len - len(item)):
                    item.append('')
            
            if code == 200:
                msgboxg_get_table_ok_inf(self.myparent,"Анализ таблицы",resp,use_first_row_as_header=False)
            else:
                msgbox(f'Ошибка\n{resp}')

    def fill_tbl_fields(self, fields: list[dict], visible: list[str]):
        tbl_fields = self.ui.tbl_fields
        fill_wtabl(fields, tbl_fields, min_width_col=120)
        col_type, col_visible = num_col_by_name_c(tbl_fields, 'Тип'), num_col_by_name_c(tbl_fields, 'Видимость')
        col_field = num_col_by_name_c(tbl_fields, 'Поля')
        if col_type is not None and col_visible is not None and col_field is not None:
            for row in range(tbl_fields.rowCount()):
                cur_field = tbl_fields.item(row, col_field).text()
                value = cur_field in visible
                add_check_box(table=tbl_fields, i=row, j=col_visible, val=value)
                item_type = tbl_fields.item(row, col_type)
                cur_data_type = self.data_parser.data_types[item_type.text()]
                tbl_fields.item(row, col_type).setBackground(QColor(*cur_data_type.rgba))

    @onerror
    def save_as_excel(self, tbl, dir=None, file_name=None, r1=0, c1=0, r2=None, c2=None):

        if r2 == None:
            r2 = tbl.rowCount() - 1
        if c2 == None:
            c2 = tbl.columnCount() - 1

        if file_name == None:
            file_name = self.windowTitle() + ' от ' + F.now('%Y_%m_%d_%H%M')

        if dir == None:
            dir = F.dir_workdesc_c()

        ws_name = '1'
        putf = F.sep().join([dir, file_name])
        dirf = f_dialog_save(self, 'Выбрать файл', putf, '*.xlsx')
        if dirf == '.':
            return

        list_rows_height = [tbl.isRowHidden(_) for _ in range(tbl.rowCount())]
        list_col_weight = [tbl.isColumnHidden(_) for _ in range(tbl.columnCount())]

        for i in range(tbl.rowCount()):
            if i < r1 or i > r2:
                tbl.setRowHidden(i, True)
        for i in range(tbl.columnCount()):
            if i < c1 or i > c2:
                tbl.setColumnHidden(i, True)

        dir = F.sep().join(dirf.split(F.sep())[:-1])
        # self.setHidden(True)
        start_time = F.get_time_shtamp_c()
        count_rinted_cells = len([_ for _ in range(tbl.rowCount()) if not tbl.isRowHidden(_)]) * len(
            [_ for _ in range(tbl.columnCount()) if not tbl.isColumnHidden(_)])
        calced_time = 0.01 * count_rinted_cells
        if calced_time > 10:
            if not msgboxgYN(f'Выгрузка займет примерно {F.miutes_to_time(calced_time / 60)}\n Продолжить?'):
                return
        file_path = CEX.save_table_colour(tbl, dir, file_name, ws_name, print_hat_tbl=self.print_hat,
                                          wo_hide_rows_cols=True)
        delta = F.get_time_shtamp_c() - start_time
        print(delta)
        print(round(delta / count_rinted_cells, 4))
        self.setHidden(False)

        for i, v in enumerate(list_rows_height):
            tbl.setRowHidden(i, v)

        for i, v in enumerate(list_col_weight):
            tbl.setColumnHidden(i, v)
            if self.ui.tbl_filtr.columnCount() > i:
                self.ui.tbl_filtr.setColumnHidden(i, v)
                self.ui.tbl_filtr.setColumnWidth(i, tbl.columnWidth(i))
            if self.ui.tbl_summ.columnCount() > i:
                self.ui.tbl_summ.setColumnHidden(i, v)
                self.ui.tbl_summ.setColumnWidth(i, tbl.columnWidth(i))
        # .QApplication.processEvents()
        self.myparent.tmp_printout = False
        self.myparent.tmp_printout_dir = None
        if file_path:
            self.myparent.tmp_printout = True
            self.myparent.tmp_printout_dir = file_path
            F.run_file_os_c(file_path)
            return True
        return False

    @onerror
    def save_as_excel_test(self, tbl, dir=None, file_name=None, r1=0, c1=0, r2=None, c2=None):

        if r2 == None:
            r2 = tbl.rowCount() - 1
        if c2 == None:
            c2 = tbl.columnCount() - 1

        if file_name == None:
            file_name = self.windowTitle() + ' от ' + F.now('%Y_%m_%d_%H%M')

        if dir == None:
            dir = F.dir_workdesc_c()

        ws_name = '1'
        putf = F.sep().join([dir, file_name])
        dirf = f_dialog_save(self, 'Выбрать файл', putf, '*.xlsx')
        if dirf == '.':
            return

        list_rows_height = [tbl.isRowHidden(_) for _ in range(tbl.rowCount())]
        list_col_weight = [tbl.isColumnHidden(_) for _ in range(tbl.columnCount())]

        for i in range(tbl.rowCount()):
            if i < r1 or i > r2:
                tbl.setRowHidden(i, True)
        for i in range(tbl.columnCount()):
            if i < c1 or i > c2:
                tbl.setColumnHidden(i, True)

        dir = F.sep().join(dirf.split(F.sep())[:-1])
        # self.setHidden(True)
        start_time = F.get_time_shtamp_c()
        count_rinted_cells = len([_ for _ in range(tbl.rowCount()) if not tbl.isRowHidden(_)]) * len(
            [_ for _ in range(tbl.columnCount()) if not tbl.isColumnHidden(_)])
        file_path = CEX.save_table_colour_openpyxl(tbl, dir, file_name, ws_name, print_hat_tbl=self.print_hat,
                                          wo_hide_rows_cols=True)
        delta = F.get_time_shtamp_c() - start_time
        print(delta)
        print(round(delta / count_rinted_cells, 4))
        self.setHidden(False)

        for i, v in enumerate(list_rows_height):
            tbl.setRowHidden(i, v)

        for i, v in enumerate(list_col_weight):
            tbl.setColumnHidden(i, v)
            if self.ui.tbl_filtr.columnCount() > i:
                self.ui.tbl_filtr.setColumnHidden(i, v)
                self.ui.tbl_filtr.setColumnWidth(i, tbl.columnWidth(i))
            if self.ui.tbl_summ.columnCount() > i:
                self.ui.tbl_summ.setColumnHidden(i, v)
                self.ui.tbl_summ.setColumnWidth(i, tbl.columnWidth(i))
        # .QApplication.processEvents()
        self.myparent.tmp_printout = False
        self.myparent.tmp_printout_dir = None
        if file_path:
            self.myparent.tmp_printout = True
            self.myparent.tmp_printout_dir = file_path
            F.run_file_os_c(file_path)
            return True
        return False

    def select_row(self):
        if self.yes_btn != None and self.glob_selection_from_tbl:
            self.yes_btn.click()

    @onerror
    def oform_action(self):
        QtWidgets.QApplication.processEvents()
        back_dialog = ''
        back_dialog_2 = ''
        back_dialog_3 = ''
        if 'QMenu ' in self.myparent.styleSheet():
            back_dialog_color = ""
            list_attr = self.myparent.styleSheet().replace('\t', '').split('QMenu ')[-1].split('}')[0].split('{')[
                -1].split(';')
            for attr in list_attr:
                atr_fix = attr.strip()
                if atr_fix.startswith('background-color:'):
                    if '#' in atr_fix:
                        back_dialog_color = atr_fix.split('background-color:')[-1].split(')')[0]
                    else:
                        back_dialog_color = atr_fix.split('background-color:')[-1].split(')')[0] + ")"
                    break
            back_dialog = """background-color: """ + back_dialog_color + """;  /* Цвет фона */"""
            back_dialog_2 = """background: """ + back_dialog_color + """;"""
            back_dialog_3 = """selection-background-color: """ + back_dialog_color + """;"""
        else:
            palette = self.palette()
            back_dialog_color = palette.color(self.backgroundRole()).name()
            back_dialog = """background-color: """ + back_dialog_color + """;  /* Цвет фона */"""
            back_dialog_2 = """background: """ + back_dialog_color + """;"""
            back_dialog_3 = """selection-background-color: """ + back_dialog_color + """;"""
        font_dialog = ''
        if 'QMenuBar::item' in self.myparent.styleSheet():
            font_dialog_color = ''
            list_attr = \
                self.myparent.styleSheet().replace('\t', '').split('QMenuBar::item')[1].split('}')[0].split('{')[
                    -1].split(
                    ';')
            for attr in list_attr:
                atr_fix = attr.strip()
                if atr_fix.startswith('color:'):
                    if '#' in atr_fix:
                        font_dialog_color = atr_fix.split('color:')[-1].split(')')[0]
                    else:
                        font_dialog_color = atr_fix.split('color:')[-1].split(')')[0] + ")"
                    break
            if font_dialog_color != '':
                font_dialog = """color: """ + font_dialog_color + """;  /* Цвет текста */"""
        else:
            font_color = palette.color(self.foregroundRole()).name()
            font_dialog = """color: """ + font_color + """;  /* Цвет текста */""" + '\n'
        css_cmb = """
                    QComboBox {""" + font_dialog + """
                        border: none;  /* Убираем контур */
                        padding: 4px;  /* Добавляем отступ для улучшения внешнего вида */
                        """ + back_dialog + """
                    }
                    QComboBox::drop-down {
                        width: 0px;  /* Убираем стрелку */
                        border: none;  /* Убираем контур у стрелки */
                    }
                    QComboBox QAbstractItemView {

                          """ + back_dialog_2 + """
                          """ + back_dialog_3 + """
                        }
                """
        self.ui.cmb_action.setStyleSheet(css_cmb)

    def keyReleaseEvent(self, e):
        if self.ui.tbl_filtr.hasFocus():
            if e.key() == 16777220:
                apply_filtr_c(self, self.ui.tbl_filtr, self.ui.tbl)
                if not self.ui.tbl_summ.isHidden():
                    fill_summ_tbl(self, self.ui.tbl_summ, self.ui.tbl, hidden_scroll=True)
        if e.key() == 67 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if focus_is_QTableWidget():
                copy_bufer_table(QtWidgets.QApplication.focusWidget())
        if e.key() == QtCore.Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()


def show_fullscreen(app, self, val:bool=1):
    if val:
        self.showFullScreen()
    else:
        self.showMaximized()
        title_h = self.frameSize().height() - self.geometry().height()
        sys_h = app.primaryScreen().availableGeometry().height() - title_h  # QtWidgets.QDesktopWidget().screenGeometry().height()-75
        if self.height() > sys_h:
            self.setFixedHeight(sys_h)
                
def msgboxg_get_table(self, msg, dict_or_list, btn0_name="Ввод", btn1_name="Отмена", func_validate=None,*args,
                      disable_btn0=False,disable_btn1=False,load_summ=False,show_filtr=True,WindowTitle='Выбор варианта',
                      style_icon='SP_MessageBoxInformation',func_oform_tbl=None,use_first_row_as_header=True,
                      print_hat=True,func_btn0=None,selection_from_tbl=False,ExtendedSelection=True,
                      selectRows=False,func_oform_filtr=None,load_links=False, conn_func_label_link=None,
                      styleSheet=None,parent_self=None,sortingEnabled=False,yesNoMode=False,not_standart_close=False,
                      save_column_sort_hh: bool = False):
    self.__ansver_Dialog_tbl = None
    dialog_tbl = Dialog_tbl(self,msg, dict_or_list, btn0_name, btn1_name, func_validate,
                            disable_btn0=disable_btn0,disable_btn1=disable_btn1,load_summ=load_summ,
                            show_filtr=show_filtr,WindowTitle=WindowTitle,style_icon=style_icon,
                            func_oform_tbl=func_oform_tbl,use_first_row_as_header=use_first_row_as_header,
                            print_hat=print_hat,func_btn0=func_btn0,selection_from_tbl=selection_from_tbl,
                            ExtendedSelection=ExtendedSelection,selectRows=selectRows,
                            func_oform_filtr=func_oform_filtr,load_links=load_links,
                            conn_func_label_link=conn_func_label_link,styleSheet=styleSheet,parent_self=parent_self,
                            sortingEnabled=sortingEnabled,not_standart_close=not_standart_close,
                            save_column_sort_hh=save_column_sort_hh)

    returnValue = dialog_tbl.exec()
    if yesNoMode:
        return returnValue
    if returnValue == 1:
        if func_validate != None:
            dict_tbl = list_from_wtabl_c(dialog_tbl.ui.tbl, rez_dict=True)
            rez = func_validate(dict_tbl)
            return rez

        if ExtendedSelection:
            data_form_tbl = get_list_line_form_tbl(dialog_tbl.ui.tbl)
        else:
            data_form_tbl = get_dict_line_form_tbl(dialog_tbl.ui.tbl)
        return data_form_tbl
    return False

def msgboxg_get_table_ok_inf(self, msg, dict_or_list, btn0_name="OK", btn1_name="None", func_validate=None,*args, 
                             disable_btn0=False,disable_btn1=True,load_summ=False,show_filtr=True,WindowTitle='Информация',
                             style_icon='SP_MessageBoxInformation',func_oform_tbl=None,use_first_row_as_header=True,
                             print_hat=True,func_btn0=None,selection_from_tbl=False,ExtendedSelection=True,
                             selectRows=False,func_oform_filtr=None,load_links=False, conn_func_label_link=None,
                             styleSheet=None,parent_self=None,sortingEnabled=False, save_column_sort_hh: bool = False):
    self.__ansver_Dialog_tbl = None
    dialog_tbl = Dialog_tbl(self,msg, dict_or_list, btn0_name, btn1_name, func_validate,disable_btn0=disable_btn0,
                            disable_btn1=disable_btn1,load_summ=load_summ,show_filtr=show_filtr,WindowTitle=WindowTitle,
                            style_icon=style_icon,
                            func_oform_tbl=func_oform_tbl,use_first_row_as_header=use_first_row_as_header,
                            print_hat=print_hat,func_btn0=func_btn0,selection_from_tbl=selection_from_tbl,
                            ExtendedSelection=ExtendedSelection,selectRows=selectRows,func_oform_filtr=func_oform_filtr,
                            load_links=load_links, conn_func_label_link=conn_func_label_link,styleSheet=styleSheet,parent_self=parent_self,
                            sortingEnabled=sortingEnabled, save_column_sort_hh=save_column_sort_hh)
    returnValue = dialog_tbl.exec()
    return
#++20.05.25
def get_answer_dialog_table(parent, msg:str, dict_or_list, btn0_name:str="Ввод",
             btn1_name:str="Отмена", func_validate=None,
             disable_btn0=False, disable_btn1=False, load_summ=False,
             show_filtr=True, WindowTitle='Выбор варианта',
             style_icon='SP_MessageBoxInformation', func_oform_tbl=None,
             use_first_row_as_header=True, print_hat=True,
             func_btn0=None, selection_from_tbl=False, ExtendedSelection=True, selectRows=False,
             func_oform_filtr=None, load_links=False, conn_func_label_link=None, styleSheet=None, parent_self=None,
             sortingEnabled=False, not_standart_close=False,
             line_edit_default_value: str = '',
             on_confirm: callable = None,
             return_entire: bool = False,
             info_point_size: int = 15,
             save_column_sort_hh: bool = False
            ):
    """
    Поля дополняющие Dialog_tbl
        line_edit_default_value: str    | Стандартное значение в поле line_edit
        on_confirm: callable            | Функция исполняемая при попытке подтвердить значение клавишей <Enter>
        return_entire: bool             | Флаг вернуть все данные из таблицы
    Пример:

    Если on_confirm вернул True диалоговое окно закрывается
    def on_confirm(text, data):
        if text == 'Да' and len(data) > 2:
            return True
        if text == 'Нет':
            msgbox('А может всё-таки да?')
        return False
    text = get_answer_dialog_table(
        window,
        'Введите значение',
        data,
        on_confirm=on_confirm,
        line_edit_default_value='Нет'
    )
    2 Если определена on_validate, то результирующий текст из поля и данные из таблицы
        будут переданы в виде on_validate(text, data_table)
    """
    dialog = Dialog_tbl(
        parent, msg, dict_or_list, btn0_name,
        btn1_name, func_validate ,
        disable_btn0, disable_btn1, load_summ ,
        show_filtr , WindowTitle,
        style_icon, func_oform_tbl,
        use_first_row_as_header, print_hat,
        func_btn0, selection_from_tbl, ExtendedSelection, selectRows,
        func_oform_filtr, load_links, conn_func_label_link, styleSheet, parent_self,
        sortingEnabled, not_standart_close, save_column_sort_hh
    )
    dialog.ui.buttonBox.setHidden(True)
    font = QtGui.QFont()
    font.setPointSize(info_point_size)
    line_edit = QtWidgets.QLineEdit(line_edit_default_value)
    line_edit.setFont(font)
    dialog.ui.horizontalLayout.addWidget(line_edit)
    dialog.ui.horizontalLayout.setStretch(1, 1)
    dialog.ui.lbl_text.setWordWrap(True)

    def on_click_enter(self, *args, **kwargs):
        text = line_edit.text()
        data = list_from_wtabl_c(dialog.ui.tbl, rez_dict=True)  # 23.06.25
        if not on_confirm or on_confirm(text, data): #24.05.25
            return dialog.accept()

    def keyReleaseEvent(e: QtGui.QKeyEvent):
        if e.key() == QtCore.Qt.Key_Return:
            if on_confirm:
                text = line_edit.text()
                data = list_from_wtabl_c(dialog.ui.tbl, rez_dict=True) # 23.06.25
                if on_confirm(text, data):
                    dialog.accept()
            else:
                dialog.accept()
    dialog.keyReleaseEvent = keyReleaseEvent
    button_enter = QtWidgets.QPushButton(btn0_name)
    button_enter.setFont(font)
    button_enter.clicked.connect(on_click_enter)
    dialog.ui.horizontalLayout.addWidget(button_enter)
    returnValue = dialog.exec()
    if returnValue == 1:
        text = line_edit.text()
        if func_validate != None:
            dict_tbl = list_from_wtabl_c(dialog.ui.tbl, rez_dict=True)# 23.06.25
            rez = func_validate(text, dict_tbl)
            return text, rez
        if ExtendedSelection:
            data_form_tbl = get_list_line_form_tbl(dialog.ui.tbl)
        elif return_entire:
            data_form_tbl = list_from_wtabl_c(dialog.ui.tbl, rez_dict=True)# 23.06.25
        else:
            data_form_tbl = get_dict_line_form_tbl(dialog.ui.tbl)
        return text, data_form_tbl
    return False, False
#--20.05.25

@onerror
def apply_summ_с(tbl, sredn=False):
    rez_jur = list_from_wtabl_c(tbl)
    if not rez_jur:
        return 
    rez_summ = ['' for _ in rez_jur[0]]
    rez_sr = ['' for _ in rez_jur[0]]
    if len(rez_jur) > 1:
        for i in range(len(rez_jur[0])):
            summ = 0
            count = 0
            for j in range(len(rez_jur) - 1):
                if rez_jur[j][i] == '':
                    rez_jur[j][i] = 0
                if F.is_numeric(rez_jur[j][i]):
                    if tbl.isRowHidden(j) == False:
                        summ += F.valm(rez_jur[j][i])
                        count += 1
            if summ != 0:
                tbl.item(tbl.rowCount() - 1, i).setText(str(round(summ, 3)))
                if sredn:
                    try:
                        tbl.item(tbl.rowCount() - 2, i).setText(str(round(summ / (count - 1), 3)))
                    except:
                        print(f'Ошибка apply_c')
                        pass
            else:
                if sredn:
                    tbl.item(tbl.rowCount() - 2, i).setText('=AVERAGE=')

                tbl.item(tbl.rowCount() - 1, i).setText('=SUMM=')
    if sredn:
        tbl.setRowHidden(tbl.rowCount() - 2, False)
    tbl.setRowHidden(tbl.rowCount() - 1, False)

@onerror
def apply_filtr_c(self, tblf, tbl,save_data=True):
    tbl.blockSignals(True)
    def easy_filtr(filtr_word, val_word):
        if tbl.item(i, j) == None:
            return True

        if len(filtr_word) == 2 and filtr_word == '!*':  # ПУСТО
            if val_word == '' or val_word.lower() == 'none' or val_word == '0':
                pass
            else:
                return False

        else:
            if len(filtr_word) == 1 and filtr_word == '*':
                if val_word == '' or val_word.lower() == 'none' or val_word == '0':
                    return False

            else:
                if len(filtr[0][j]) > 1 and filtr_word[0] == '=':
                    filtr_word = filtr_word[1:]
                    if filtr_word.lower() != val_word:
                        return False

                else:
                    if len(filtr[0][j]) > 1 and filtr_word[0] == '!':
                        if len(filtr[0][j]) > 2 and filtr_word[1] == '=':
                            filtr_word = filtr_word[2:]
                            if filtr_word.lower() == val_word:
                                return False

                        else:
                            filtr_word = filtr_word[1:]
                            if filtr_word.lower() in val_word:
                                return False

                    else:
                        if '|' in filtr_word:
                            spis = filtr_word.split('|')
                            for usl in spis:

                                if usl in val_word:
                                    return True
                            return False
                        else:
                            if '&' in filtr_word:
                                spis = filtr_word.split('&')
                                for usl in spis:
                                    if usl not in val_word:
                                        return False

                            else:
                                if filtr_word.lower() not in val_word:
                                    return False
        return True

        # ====================================================
    KEYWORD_DATE_COMPARE = 'dt:'
    SET_SIGNS_FOR_DATE_COMPARE = {'>','<','=','&'}
    list_date_masks=["%Y-%m-%d %H:%M:%S",
                     "%Y-%m-%d",
                     "%d.%m.%Y",
                     "%d.%m.%Y %H:%M:%S",
                     "%y-%m-%d %H:%M:%S",
                     "%y-%m-%d",
                     "%Y-%m-%dT%H:%M:%S"
                     ]
    
    struck_save = dict()

    filtr = list_from_wtabl_c(tblf)
    for j in range(len(filtr[0])):
        filtr_word = filtr[0][j].strip()
        fl_date_compare = False
        if filtr_word != '' and filtr_word[0] in SET_SIGNS_FOR_DATE_COMPARE:
            fl_date_compare = True
            filtr_word_for_date = copy.copy(filtr_word)
            clear_filtr_word = copy.copy(filtr_word)
            for sign in SET_SIGNS_FOR_DATE_COMPARE:
                clear_filtr_word = clear_filtr_word.replace(sign, ' ')
            set_dates = set(clear_filtr_word.split())
            if '' in set_dates:
                set_dates.pop('')
            for date in set_dates:
                fl_date = False
                for mask in list_date_masks:
                    if F.is_date(date, mask):
                        filtr_word_for_date = filtr_word_for_date.replace(date, f'F.strtodate("{date}","{mask}")',1)
                        fl_date = True
                        break
                if not fl_date:
                    fl_date_compare = False
                    break
            if fl_date_compare:
                filtr[0][j] = KEYWORD_DATE_COMPARE + filtr_word_for_date
        
    for i in range(tbl.rowCount()):  # по строкам
        flag_ost = True
        for j in range(len(filtr[0])):  # по полям фильтра
            filtr_word = filtr[0][j].strip()
            if filtr_word != '':
                struck_save[tblf.horizontalHeaderItem(j).text()] = filtr[0][j].strip()
            val_word = ''
            if tbl.item(i, j) != None:
                val_word = tbl.item(i, j).text().strip().lower()
            if len(filtr_word) > 1 and "'" == filtr_word[0]:#ругулярки
                filtr_word = filtr_word[1:]
                flag_ost = re.match(fr'{filtr_word}', fr'{val_word}')
                if flag_ost == None:
                    flag_ost = False
            else:
                if filtr_word.startswith(KEYWORD_DATE_COMPARE):

                    fl_val_date = False
                    for mask in list_date_masks:
                        if F.is_date(val_word, mask):
                            val_date_word = f'F.strtodate("{val_word}","{mask}")'
                            fl_val_date=True
                            break
                    if not fl_val_date:
                        flag_ost = False
                    else:
                        flag_ost = True
                        list_filtr_dates = filtr_word.replace("=","==").replace(KEYWORD_DATE_COMPARE,'').split('&')
                        for filtr_date in list_filtr_dates:
                            if not eval(f'{val_date_word}{filtr_date}'):
                                flag_ost= False
                                break
                else:
                    filtr_word = filtr_word.lower()
                    flag_ost = easy_filtr(filtr_word, val_word)#текстовый
            if flag_ost == False:
                break
        if flag_ost:
            tbl.showRow(i)
        else:
            tbl.hideRow(i)
    tbl.blockSignals(False)
    def _save_tmp_stukt(data,name):
        puth_name = qt_tmp_dir() + os.sep + name + '.pickle'
        F.save_file_pickle(puth_name, data)
    if save_data: # saved_filter_
        put_value_in_filtr(struck_save, tblf, tbl)
        # _save_tmp_stukt(struck_save, "saved_filter_" + tblf.objectName())


@onerror
def fill_summ_tbl(self, tbls:QtWidgets.QTableWidget, tbl:QtWidgets.QTableWidget,
                  set_name_calc:(set|None) = None, hidden_scroll:bool = True,
                  calc_hidden_rows:bool= False,round_summ_digit:int = 2, average:bool=False):
    tbls.blockSignals(True)
    clear_tbl(tbls)
    if set_name_calc == None:
        set_name_calc = set()
        for i in range(tbl.columnCount()):
            if tbl.horizontalHeaderItem(i) != None:
                set_name_calc.add(tbl.horizontalHeaderItem(i).text())
            else:
                set_name_calc.add(str(i))

    base_dict_fields = dict()
    for i in range(tbl.columnCount()):
        summ_val = ''
        name = str(i)
        if tbl.horizontalHeaderItem(i) != None:
            name = tbl.horizontalHeaderItem(i).text()
        if name in set_name_calc:
            summ_val = 0
            val = 0
            for j in range(tbl.rowCount()):
                if not calc_hidden_rows:
                    if tbl.isRowHidden(j):
                        continue
                if tbl.item(j, i) != None and F.is_numeric(tbl.item(j, i).text()):
                    val = F.valm(tbl.item(j, i).text())
                    summ_val += val
            summ_val = str(round(summ_val, round_summ_digit))
        if tbl.horizontalHeaderItem(i) != None:
            base_dict_fields[tbl.horizontalHeaderItem(i).text()] = summ_val
        else:
            base_dict_fields[str(i)] = summ_val

    rez_data = [base_dict_fields]
    if average:
        count_row = 0
        for j in range(tbl.rowCount()):
            if not calc_hidden_rows:
                if tbl.isHidden():
                    continue
                count_row += 1
        base_dict_fields_aver = copy.deepcopy(base_dict_fields)
        for i in range(tbl.columnCount()):
            name = str(i)
            if tbl.horizontalHeaderItem(i) != None:
                name = tbl.horizontalHeaderItem(i).text()
            if name in set_name_calc:
                base_dict_fields_aver[name] = str(
                    round(F.valm(base_dict_fields_aver[name]) / count_row, round_summ_digit))
        rez_data.append(base_dict_fields_aver)

    fill_wtabl(rez_data, tbls, height_row=24)
    tbls.setVerticalHeaderLabels(['Сумма'])
    tbls.setToolTip(
        "СУММА")
    count_rows = 1
    if average:
        tbls.setVerticalHeaderLabels(['Сумма', 'Средн.'])
        tbls.setToolTip(
            "СУММА/СРЕДНЕЕ")
        tbls.setFixedHeight(
            round(tbl.rowHeight(0) * tbls.rowCount() + tbls.rowCount()))
        count_rows=2
    _load_tbl(tbl, tbls, hidden_scroll,count_rows)

    tbls.blockSignals(False)


@onerror
def fill_filtr_c(self, tblf:QtWidgets.QTableWidget, tbl:QtWidgets.QTableWidget, spis_znach='', hidden_scroll=False):

    tblf.blockSignals(True)
    # hat_c = {_:"" for _ in CQT.get_dict_line_form_tbl(tbl,0).keys()}
    hat_c = {tbl.horizontalHeaderItem(col).text(): "" for col in range(tbl.columnCount())}

    fl_auto_apply_filtr= False

    if spis_znach != '' and len(spis_znach) > 0:
        if type(spis_znach) == type(list()) and isinstance(hat_c, list):
            if len(spis_znach[0]) != len(hat_c[0]):
                print('fill_filtr_c не совпадение длин')
                return
            for i, key in enumerate(hat_c.keys()):
                hat_c[key] = spis_znach[0][i]
        if type(spis_znach) == type(list()) and isinstance(hat_c, dict):
            if len(spis_znach[0]) != len(hat_c):
                print('fill_filtr_c не совпадение длин')
                return
            for i, key in enumerate(hat_c.keys()):
                hat_c[key] = spis_znach[0][i]

        if type(spis_znach) == type(dict()):

            for key in spis_znach:
                if key in hat_c:
                    hat_c[key] = spis_znach[key]
    else:
        if 'USER_CONFIG' in self.__dict__ and self.USER_CONFIG.reset_tbl_filtrs['Значение'] == '0':
            hat_c = get_spis_znach_for_filtr(self,tblf,tbl)
        else:
            for j in range(tblf.columnCount()):
                tblf.item(0,j).setText('')
        fl_auto_apply_filtr = True
    ed = {_ for _ in range(len(hat_c))}
    fill_wtabl([hat_c], tblf, set_editeble_col_nomera=ed, auto_type=False)
    ConnectFilterKeyEvents(self, tbl, tblf)
    with QSignalBlocker(tblf.horizontalHeader()):
        tblf.setStyleSheet(tbl.styleSheet())
        with QSignalBlocker(tbl.horizontalHeader()):
            _load_tbl(tbl, tblf, hidden_scroll)
    # tblf.setRowHeight(0, tblf.height() - 35)
    key_shortcut_msg = (
        f'\n{"-" * 26}\n'
        '↑(Стрелка вверх) ↓(Стрелка вниз) — Вернуть прдыдущий фильтр\n'
        'Комбинация Shift + Delete — Отчистить фильтр'
    )
    tblf.setToolTip(
        "фильтр по вхождению: \n* - любой символ\n! - не\n= - полное совпадение\n| - ИЛИ\n& - И\n'... - RegEx \nдаты: <24-11-11 & >24-11-01"
        + key_shortcut_msg
    )
    tblf.blockSignals(False)
    if fl_auto_apply_filtr:
        apply_filtr_c(self,tblf,tbl)

class ConnectFilterKeyEvents:
    FILTER_TABLE_EVENTS_INITIALIZED_PROPERTY = 'FILTER_TABLE_EVENTS_INITIALIZED'
    TABLE_RELATION_PROPERTY = 'TABLE_RELATION_MARK'

    def __init__(self, window, tbl: QtWidgets.QTableWidget, tblf: QtWidgets.QTableWidget):
        self.window = window
        self.tbl: QtWidgets.QTableWidget = tbl
        self.tblf: QtWidgets.QTableWidget = tblf
        init_property = tblf.property(self.FILTER_TABLE_EVENTS_INITIALIZED_PROPERTY)
        if not init_property:
            tblf.keyReleaseEvent = self.keyReleaseEvent #17.07.25
            tblf.setProperty(self.FILTER_TABLE_EVENTS_INITIALIZED_PROPERTY, True)
            tbl.setProperty(self.TABLE_RELATION_PROPERTY, tblf.objectName())
        if FillHorizontalHeaderSort.is_mutable(tbl):
            FillHorizontalHeaderSort(table=tbl, filter_tbl=tblf)

    def apply_filter_state(self, new_state):
        self.tblf.clearSelection()
        cols = []
        if self.tblf.rowCount() == 1:
            for col in range(self.tblf.columnCount()):
                current_head = self.tblf.horizontalHeaderItem(col).text()
                new_value = str(new_state[current_head])
                self.tblf.item(0, col).setText(new_value)
                new_value.strip() and cols.append(col)
        migat_headers(self.window, self.tblf, cols, 255, 124, 115, count=1)

    def keyReleaseEvent(self, event):
        key_enter = QtGui.QKeyEvent(QtGui.QKeyEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            new_state = change_filter_state(event.key(), self.tblf, self.tbl)
            self.apply_filter_state(new_state)
        if event.key() == Qt.Key_Delete and event.modifiers() == (QtCore.Qt.ShiftModifier):
            for j in range(self.tblf.columnCount()):
                self.tblf.item(0, j).setText('')
            event = key_enter
        if hasattr(self.window, 'keyReleaseEvent'):
            return self.window.keyReleaseEvent(event)
        print(f'[ConnectFilterKeyEvents] Окно {self.window} не содержит метода keyReleaseEvent '
            f'чтобы делегировать эвент родительскому окну')

    @classmethod
    def get_filter_object_by_main_table(cls, table: QTableWidget):
        filter_table_name = table.property(cls.TABLE_RELATION_PROPERTY)
        active_window = QApplication.activeWindow()
        if not filter_table_name or not active_window:
            return
        return active_window.findChild(QtWidgets.QTableWidget, filter_table_name)

def qt_tmp_dir():
    ima_module = F.name_of_executable_file_c().split('.')[0]
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp'])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp']))
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module]))
    return os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])

StackState = namedtuple('StackState', 'data,current_num')

class FilterStack:
    def __init__(self, name_tbl_filtr: str, headers: list[str]):
        self.headers = headers
        self.name_tbl_filtr = name_tbl_filtr
        self.stack_data = []
        self.current_num = 0
        self.load_stack_sturct()

    def add_stack_element(self, new_elem: dict):
        last_row = self._unprepared_current_row()
        if new_elem != last_row:
            self.stack_data = [new_elem, *self.stack_data[self.current_num:10]]
            self.current_num = 0
            self._save_tmp_stukt()

    @classmethod
    def _load_tmp_stukt(cls, name_tbl_filtr, default_val=None):
        puth_name = qt_tmp_dir() + os.sep + name_tbl_filtr + '.pickle'
        if F.existence_file_c(puth_name) == True and os.path.getsize(puth_name) > 0:
            val = F.load_file_pickle(puth_name)
            return val
        return default_val

    def _save_tmp_stukt(self):
        puth_name = qt_tmp_dir() + os.sep + self.name_tbl_filtr + '.pickle'
        F.save_file_pickle(puth_name, StackState(data=self.stack_data, current_num=self.current_num))

    @property
    def template(self):
        return dict.fromkeys(self.headers, '')

    def load_stack_sturct(self):
        dumped_filters: StackState = self._load_tmp_stukt(self.name_tbl_filtr)
        if isinstance(dumped_filters, StackState):
            self.stack_data = dumped_filters.data
            self.current_num = dumped_filters.current_num

    def _unprepared_current_row(self):
        length_stack = len(self.stack_data)
        if length_stack <= self.current_num or self.current_num < 0:
            return self.template
        return self.stack_data[self.current_num]

    @property
    def current(self):
        filter_row = self._unprepared_current_row()
        prepared_row = self.template
        for head in self.headers:
            if head in filter_row:
                prepared_row[head] = filter_row[head]
        return prepared_row

    def _change_stack_level(self, operator_sub_add):
        new_state = operator_sub_add(self.current_num, 1)
        if len(self.stack_data) == 0:
            return self.template
        if new_state < len(self.stack_data) and new_state >= 0:
            self.current_num = new_state
            self._save_tmp_stukt()
            return self.current
        return self.current

    def up(self):
        return self._change_stack_level(operator.add)

    def down(self):
        return self._change_stack_level(operator.sub)



def change_filter_state(key: QtGui.QKeyEvent, tblf: QtWidgets.QTableWidget, tbl: QtWidgets.QTableWidget = None):
    name_tbl_filtr = "saved_filter_" + tblf.objectName()
    if tbl is None:
        tbl = tblf
    headers = [tbl.horizontalHeaderItem(i).text() for i in range(tbl.columnCount())]
    stack_instance = FilterStack(name_tbl_filtr, headers)
    if key == Qt.Key_Up:
        return stack_instance.up()
    if key == Qt.Key_Down:
        return stack_instance.down()


@onerror
def get_spis_znach_for_filtr(self,tblf:QtWidgets.QTableWidget,tbl:QtWidgets.QTableWidget=None, stack_num: int = None):
    name_tbl_filtr = "saved_filter_" + tblf.objectName()
    if tbl is None:
        tbl = tblf
    headers = [tbl.horizontalHeaderItem(i).text() for i in range(tbl.columnCount())]
    stack_instance = FilterStack(name_tbl_filtr, headers)
    return stack_instance.current


@onerror
def put_value_in_filtr(new_elem, tblf:QtWidgets.QTableWidget,tbl:QtWidgets.QTableWidget=None):
    name_tbl_filtr = "saved_filter_" + tblf.objectName()
    headers = [tbl.horizontalHeaderItem(i).text() for i in range(tbl.columnCount())]
    stack_instance = FilterStack(name_tbl_filtr, headers)
    stack_instance.add_stack_element(new_elem)



@onerror
def output_gant(self, fig, obj_browser, name_f='text', dir=None, *args):
    if dir == None:
        dir = F.sep().join((F.scfg('files_tmp'), 'charts'))
    html = fig.to_html()
    print('2.1')
    putf = F.sep().join((dir,f'{name_f}.html'))
    print(f'Saved: {putf}')
    print('2.2')
    with open(putf, 'w+', encoding="utf-8") as f:
        f.write(html)
    # rez = self.browser.setHtml(html)
    print('2.3')
    # self.ui.browser.setUrl(QtCore.QUrl(f"file://{putf.replace(F.sep(),'/')}"))
    obj_browser.setUrl(QtCore.QUrl(f"file:///{putf.replace(F.sep(), '/')}"))
    print('2.4')
    # print(rez)

@onerror
def on_section_resized(self,tmp_dir:str,*args):
    focus = QtWidgets.QApplication.focusWidget()

    if (isinstance(focus, QtWidgets.QTableWidget) or
            isinstance(focus, QtWidgets.QTreeWidget)
            or isinstance(focus, QtWidgets.QHeaderView)):
        if isinstance(focus, QtWidgets.QHeaderView):
            # Получаем родительский виджет (сам QTableWidget)
            tbl = focus.parentWidget()
            obj_name = tbl.objectName()
        else:
            tbl = focus
            obj_name = focus_obj_name()
        try:
            if args[1] % 5 != 0:
                return
        except:
            pass
        try:
            if tbl == None:
                print('Ошибка on_section_resized obj == None')
                return 
            spis_width = []
            for i in range(tbl.columnCount()):
                spis_width.append(tbl.columnWidth(i))
            if isinstance(obj_name, str):
                putf = tmp_dir + F.sep() + obj_name + "_column_widths.txt"
                F.save_file(putf, spis_width)
            else:
                print('Ошибка on_section_resized типа фокуса')
        except:
            print('on_section_resized Не сохранить параметры столбцов')

@onerror
def connect_to_resize(self,tmp_dir):
    for ui_name, ui in self.__dict__.items():
        if len(ui_name) < 4 and 'ui' in ui_name:
            for item in ui.__dict__:
                if isinstance(ui.__dict__[item],QtWidgets.QTableWidget):
                    table = ui.__dict__[item]
                    table.setToolTip('Ctrl+Shift+C - Копировать таблицу\nCtrl+Shift+P - Вывод доп.табличной формы')
                    header = table.horizontalHeader()

                    header.sectionResized.connect(lambda: on_section_resized(self,tmp_dir))
                if isinstance(ui.__dict__[item],QtWidgets.QTreeWidget):
                    table = ui.__dict__[item]
                    #table.setToolTip('Ctrl+Shift+C - Копировать таблицу\nCtrl+Shift+P - Вывод доп.табличной формы')
                    header = table.header()

                    header.sectionResized.connect(lambda: on_section_resized(self, tmp_dir))


@onerror
def load_column_widths(self='',tbl:QtWidgets.QTableWidget|QtWidgets.QTreeWidget=None,tmp_dir:str=''):
    tbl.blockSignals(True)
    spis_width = []
    putf = tmp_dir + F.sep() + tbl.objectName() + "_column_widths.txt"
    if F.existence_file_c(putf):
        spis_width = F.load_file(putf)
        if tbl.columnCount() == len(spis_width):
            for i in range(tbl.columnCount()):
                tbl.setColumnWidth(i, int(spis_width[i]))
    tbl.blockSignals(False)
    return spis_width


def tbl_encircle(tbl:QtWidgets.QTableWidget,r1=0,c1=0,r2=None,c2=None, thick_out: int = 4,
            thick_in: int = 1,
            horizontal_inline: bool = False,
            vertical_inline: bool = False,rgb='0;0;0',
                 rgb_in='5;5;5',line_style_in=Qt.SolidLine,line_style_out=Qt.SolidLine,):
    if r2 == None:
        r2 = tbl.rowCount()-1
    if c2 == None:
        c2 = tbl.columnCount()-1
    
    r,g,b =[int(_) for _ in rgb.split(';')]
    ri, gi, bi=[int(_) for _ in rgb_in.split(';')]
    border = CBPAINT.BorderPainter((r1,c1), (r2,c2), rgb_out=(r,g,b),thick_out=thick_out,
                                   thick_in=thick_in,
                                  rgb_in=(ri,gi,bi), line_style_in=line_style_in,line_style_out=line_style_out,
                                   horizontal_inline=horizontal_inline,vertical_inline=vertical_inline)
    tbl.setItemDelegate(border)
    return border

    
def is_tbl_cell_encircle(tbl):
    pass


class TableValidator(QStyledItemDelegate):
    """
    Класс проверки допустимости значений в редактируемых ячейках
    Пример использования:
    validator = TableValidator(fn_validator, self.table_widget)
    self.table_widget.setItemDelegate(validator)

    @param fn_validator функция, которой будет передано два аргумента
        str: шапка таблицы
        str: value
        на выходе функция должна вернуть bool значение (допускается/нет)
        если функция возвращает значение == False, то в ячейке таблицы остается старое значение
        если функция возвращает значения == True, то значение ячейки меняется
    """
    VALIDATOR_IS_UNPACKED_KEY = 'VALIDATOR_IS_UNPACKED_KEY'

    def __init__(self, fn_validator: Callable[[str, str, QtWidgets.QMainWindow], bool], parent: QtWidgets.QTableWidget, window: QtWidgets.QMainWindow) -> None:
        super().__init__(parent)
        self.parent = parent
        self.previous_value = None
        self.fn_validator = fn_validator
        self.window = window

    def updateEditorGeometry(self, QWidget, QStyleOptionViewItem, QModelIndex):#обход ячеек с виджетами
        if isinstance(QWidget, QtWidgets.QComboBox) and not hasattr(QWidget, self.VALIDATOR_IS_UNPACKED_KEY):
            setattr(QWidget, self.VALIDATOR_IS_UNPACKED_KEY, True)
            QWidget.currentIndexChanged.connect(lambda new_index: self.on_change_combo(new_index, QModelIndex.row(), QModelIndex.column()))
            QWidget.previous_value = QWidget.currentText()
        super().updateEditorGeometry(QWidget, QStyleOptionViewItem, QModelIndex)

    def on_change_combo(self, new_index, row, col, *args):#После выбора строки комбобока
        head_item = self.parent.horizontalHeaderItem(col)
        cell = self.parent.cellWidget(row, col)
        prev = cell.__dict__.get('previous_value')
        if head_item and isinstance(cell, QtWidgets.QComboBox) and prev != cell.currentText():
            header_text = head_item.text()
            if not self.fn_validator(header_text, cell.currentText(), self.window):
                cell.setCurrentText(prev)

    def setEditorData(self, editor, index):#После клика и До внесения данных
        self.previous_value = index.data()
        editor.setText(self.previous_value)

    @onerror
    def setModelData(self, editor, model, index):#После изменения содержимого ячейки
        value = editor.text()
        header = model.headerData(index.column(), Qt.Horizontal)
        if self.fn_validator(header, value, self.window):
            model.setData(index, value)
        else:
            model.setData(index, self.previous_value)

class RollBackUserChangesDelegator(QStyledItemDelegate):
    """
    Откат пользовательских изменений в таблице по нажатию клавиши Ctrl + Z
    Использование
    delegator = RollBackUserChangesDelegate(table_widget, window)
    table_widget.setItemDelegate(delegator)
    Где:
       table_widget = Объект QTableWidget
       window = Объект основного окна QMainWindow
    """
    def __init__(self, table_widget: QtWidgets.QTableWidget, window):
        self.table_widget = table_widget
        self.window = window
        self.prev_key_listener_func = None
        self.stack = []
        name = self.table_widget.objectName()
        mutable_mark = f'MUTABLE_KEY_RELEASES_MARK_{name}'
        if mutable_mark not in self.table_widget.__dict__:
            self.prev_key_listener_func = self.window.keyReleaseEvent
            self.window.keyReleaseEvent = self.keyReleaseEvent
            setattr(self.window, mutable_mark, True)
        super().__init__()

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        editor.setText(value)

    def setModelData(self, editor, model, index):
        value = editor.text()
        prev_val  = model.data(index)
        vertical = self.table_widget.horizontalScrollBar().value()
        horizontal = self.table_widget.verticalScrollBar().value()
        self.stack.append({
            'vertical': vertical,
            'horizontal': horizontal,
            'value': prev_val,
            'row': index.row(),
            'column': index.column()
        })
        model.setData(index, value, Qt.EditRole)

    def undo_red_tree(self) -> None:
        try:
            prev_state = self.stack.pop()
            vertical = prev_state['vertical']
            horizontal = prev_state['horizontal']
            value = prev_state['value']
            row = prev_state['row']
            column = prev_state['column']
            item = self.table_widget.item(row, column)
            if item is not None:
                item.setText(value)
            if vertical and horizontal:
                self.table_widget.setVerticalScrollBar(QtWidgets.QScrollBar(vertical))
                self.table_widget.setHorizontalScrollBar(QtWidgets.QScrollBar(horizontal))
        except Exception as e:
            print(e)

    def keyReleaseEvent(self, e):
        if e.key() == 90 and e.modifiers() == QtCore.Qt.ControlModifier:
            self.undo_red_tree()
        return self.prev_key_listener_func(e)

# 16.07.25 ++
class FillHorizontalHeaderSort(QtCore.QObject):
    """
    Сохранение позиции секций QTableWidget.HorizontalHeaderItem
    События:
        По событию фактического перемещения drag on drop колонки происходит сохранение состояния колонок в путь указанный
            в аргументе tmp_dir/имя объекта таблицы_sort_horizontal_header_columns.pickle
            если tmp_dir не задан формируется путь ${USER}/mes_tmp/{APP}/имя объекта таблицы_sort_horizontal_header_columns.pickle

    FillHorizontalHeaderSort(table_widget)
    """
    # Марки мутации объекта QTableWidget
    SIGNAL_PROPERTY = 'horizontal_header_section_moved_saver'

    # Курсоры
    hover_cursor: int = Qt.OpenHandCursor # Qt.PointingHandCursor # Курсор при наведении
    press_cursor: int = Qt.ClosedHandCursor                       # Курсор при клике

    def __init__(self,
                 table: QTableWidget,
                 filter_tbl: QTableWidget = None,
                 tmp_dir: str = None) -> None:
        super().__init__()
        self.table = table
        self.filter_tbl = filter_tbl
        self.tmp_dir = tmp_dir
        self.__mutable_table()
        self.fill_horizontal_header_sort()
        self.timer = QtCore.QTimer(self.table)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.check_mouse_state)
        self.is_focus = False

    @classmethod
    def is_mutable(cls, tbl: QtWidgets.QTableWidget):
        return tbl.property(cls.SIGNAL_PROPERTY)

    @property
    def tmp_path(self) -> pathlib.Path:
        if self.tmp_dir is None:
            executor, _ = F.name_of_executable_file_c().split('.')
            base_path = pathlib.Path().home() / 'mes_tmp' / executor
        else:
            base_path = pathlib.Path(self.tmp_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        filename = self.table.objectName() + "_sort_horizontal_header_columns.pickle"
        return base_path / filename

    def fill_horizontal_header_sort(self):
        data = self.__load_column_data()
        if data is None:
            return
        current_sections = self.get_horizontal_header_sections(self.table)
        filter_sections = self.get_horizontal_header_sections(self.filter_tbl)
        if not isinstance(current_sections, list) or len(current_sections) == 0:
            return
        tables_for_replace = []
        if set(current_sections) == set(data) and len(data) == len(current_sections):
            tables_for_replace.append(self.table)
        if isinstance(filter_sections, list) and set(filter_sections) == set(data) and len(data) == len(filter_sections):
            tables_for_replace.append(self.filter_tbl)
        for table in tables_for_replace:
            for target_index, column in enumerate(data):
                current_index = self.__current_logical_position(table, column)
                table.horizontalHeader().blockSignals(True)
                table.horizontalHeader().moveSection(current_index, target_index)
                table.horizontalHeader().repaint()
                table.horizontalHeader().blockSignals(False)

    def __current_logical_position(self, tbl: QtWidgets.QTableWidget, column_text: str) -> int:
        return next(
            col
            for col in range(tbl.columnCount())
            if tbl.horizontalHeaderItem(tbl.horizontalHeader().logicalIndex(col)).text() == column_text
        )

    def __mutable_table(self):
        is_mutable = self.table.property(self.SIGNAL_PROPERTY)
        if not is_mutable:
            self.table.setDragEnabled(True)
            self.table.setAcceptDrops(True)
            self.table.setDropIndicatorShown(True)
            self.table.setMouseTracking(True)
            self.table.setFocusPolicy(Qt.StrongFocus)
            self.table.horizontalHeader().setSectionsMovable(True)
            self.table.horizontalHeader().setFocusPolicy(Qt.StrongFocus)
            self.table.horizontalHeader().setSectionsClickable(True)
            self.table.horizontalHeader().setMouseTracking(True)
            self.table.horizontalHeader().installEventFilter(self)

            self.table.horizontalHeader().sectionMoved.connect(
                lambda struct_ind, old_ind, new_ind: self.__save_column_order(struct_ind, old_ind, new_ind)
            )
            self.table.horizontalHeader().sectionPressed.connect(self.__pressed_header)
            self.table.setProperty(self.SIGNAL_PROPERTY, True)

    def __save_column_order(self, logic_ind, old_ind, new_ind):
        headers = [
            self.table.horizontalHeaderItem(self.table.horizontalHeader().logicalIndex(i)).text()
            for i in range(self.table.columnCount())
        ]
        self.tmp_path.write_bytes(F.to_binary_pickle(headers))
        filter_table = ConnectFilterKeyEvents.get_filter_object_by_main_table(self.table)
        if filter_table:
            self.filter_tbl = filter_table
            filter_table.horizontalHeader().setUpdatesEnabled(False)
            filter_table.setUpdatesEnabled(False)

            for idx, column in enumerate(headers):
                current_index = self.__current_logical_position(filter_table, column)
                filter_table.horizontalHeader().blockSignals(True)
                filter_table.horizontalHeader().moveSection(current_index, idx)
                filter_table.horizontalHeader().blockSignals(False)
            filter_table.horizontalHeader().setUpdatesEnabled(True)
            filter_table.setUpdatesEnabled(True)

    def check_mouse_state(self, *args):
        buttons = QApplication.mouseButtons()
        if buttons & Qt.LeftButton:
            QApplication.setOverrideCursor(self.press_cursor)
            self.timer.start(200)
        else:
            QApplication.setOverrideCursor(self.hover_cursor)

    def __pressed_header(self, *args, **kwargs):
        QApplication.setOverrideCursor(self.press_cursor)
        self.timer.start(200)

    def __load_column_data(self):
        try:
            if self.tmp_path.exists():
                return F.from_binary_pickle(self.tmp_path.read_bytes())
        except (FileNotFoundError, EOFError):
            return

    def get_horizontal_header_sections(self, table: QtWidgets.QTableWidget):
        if table is None: return
        if table.columnCount() == 0:
            return
        places = [None] * table.columnCount()
        for col in range(table.columnCount()):
            places[table.horizontalHeader().logicalIndex(col)] = table.horizontalHeaderItem(col).text()
        return places

    def eventFilter(self, obj, event: QEvent):
        event_type = event.type()
        obj_cursor = obj.cursor().shape()
        if event_type == QEvent.CursorChange:
            QApplication.setOverrideCursor(obj_cursor)
        if event_type in (QEvent.Enter, QEvent.HoverEnter, QEvent.HoverMove) and obj_cursor == 0:
            if not QApplication.mouseButtons() & Qt.LeftButton:
                QApplication.setOverrideCursor(self.hover_cursor)
        if event.type() in (QEvent.HoverLeave, QEvent.Leave):
            self.timer.stop()
            QApplication.setOverrideCursor(Qt.ArrowCursor)
        return super().eventFilter(obj, event)

#21.08.25 ++

class InteractiveLabelInstance(QtCore.QObject):
    def __init__(self, table: QTableWidget, row: int,
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
        item = self.table.item(row, column)
        if item is None:
            return
        if not text:
            text = item.text()
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
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.label.setContentsMargins(5, 0, 5, 0)
        self.hlayout.addWidget(self.label, 1)

        self.buttons_widget = QtWidgets.QWidget()
        self.buttons_layout = QtWidgets.QHBoxLayout(self.buttons_widget)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(0)
        self.hlayout.addWidget(self.buttons_widget, 0)

        self.buttons = []

        item = QtWidgets.QTableWidgetItem(item.text())
        invisible_brush = QtGui.QBrush(QColor(0, 0, 0, 0))
        item.setForeground(invisible_brush)
        item.setBackground(QtGui.QBrush(QColor(0, 0, 0, 0)))
        self.table.setItem(self.row, self.column, item)

        self.table.setCellWidget(self.row, self.column, self.container)

        self._update_label_text()
        self._update_sizes()

        vh = self.table.verticalHeader()
        hh = self.table.horizontalHeader()
        self.destroyed_tasks = []
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

    def _apply_label_bg_style(self, qc: QColor):
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
        elided = fm.elidedText(self.full_text, Qt.ElideRight, available_px)
        # self.label.setText(elided)

    def _update_column_width_if_needed(self):
        fm = QtGui.QFontMetrics(self.label.font())
        desired_label_px = max(self.min_label_px, self._approx_label_width_px_by_chars())
        desired_total = desired_label_px + self._sum_buttons_width() + self.padding
        current = self.table.columnWidth(self.column)
        if current < desired_total:
            self.table.setColumnWidth(self.column, desired_total)

    def _update_sizes(self):
        self._update_button_sizes()
        self._update_label_text()
        self._update_column_width_if_needed()

    def _on_row_section_resized(self, logicalIndex, oldSize, newSize):
        if logicalIndex == self.row:
            self._update_sizes()

    def _on_column_section_resized(self, logicalIndex, oldSize, newSize):
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
        on_clicked
        * Если передано on_clicked(
            current_object: InteractiveLabelInstance # Для взаимодействия с виджетами table,label,buttons
            row: int,
            column: int,
            cell_val: Any Дополнительный объект (по совместимости с CQT.add_btn
        )
        """
        btn = QtWidgets.QPushButton(txt_button)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setToolTip(tooltip)
        btn.setFlat(True)
        if on_clicked is not None: #29.08.25
            if not self.parent_self:
                if cell_val:
                    btn.clicked.connect(lambda *args: on_clicked(self, self.row, self.column, cell_val))
                else:
                    btn.clicked.connect(lambda *args: on_clicked(self, self.row, self.column))
            else:
                if cell_val:
                    btn.clicked.connect(lambda *args: on_clicked(self, self.parent_self, self.row, self.column, cell_val))
                else:
                    btn.clicked.connect(lambda *args: on_clicked(self, self.parent_self, self.row, self.column))
        self.buttons_layout.addWidget(btn)
        self.buttons.append(btn)
        self._update_sizes()
        if img_path != '':
            self._update_img(img_path, btn)
        return btn

    def set_text(self, lbl_text: str):
        self.label.setText(lbl_text)
        self.full_text = lbl_text
        self._update_sizes()

def add_interactive_label(
        table: QTableWidget,
        row: int,
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
    inst = InteractiveLabelInstance(table, row, column, text,
                                    txt_cut=txt_cut,
                                    min_label_px=min_label_px,
                                    btn_width=btn_width,
                                    mark_not_changed_item=mark_not_changed_item,
                                    parent_self=parent_self)
    return inst


#+++29.08.25
class LinkDialog(QtWidgets.QDialog):
    def __init__(self, parent=None,
                 placeholder="http://srv-1c:8088/ERP/#e1cib/data/.../?ref=846800d861dd2b4a11ed131c12a92ef4",
                 validate_ref_func=None):
        super().__init__(parent)
        self.validate_ref_func = validate_ref_func
        self.setWindowTitle("Вставьте ссылку")
        self.setMinimumWidth(520)
        self.ref_value = None
        self._current_reply = None
        self.hint_label = QtWidgets.QLabel("Введите URL вида номенклатуры.\n"
                                 "Для этого необходимо:\n"
                                 "1. В 1С кликнуть правой кнопкой мыши по виду номенклатуры\n"
                                 "2. В контекстном меню выбрать пункт 'Получить ссылку'\n"
                                 "3. Данную ссылку вставить в поле ввода МЕС")
        self.hint_label.setWordWrap(True)

        self.url_edit = QtWidgets.QLineEdit()
        self.url_edit.setPlaceholderText(placeholder)
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.setMinimumHeight(28)
        self.url_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.info_label = QtWidgets.QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #333;")
        self.info_label.setMinimumHeight(36)

        self.cancel_btn = QtWidgets.QPushButton("Отмена")
        self.confirm_btn = QtWidgets.QPushButton("Подтвердить")
        self.confirm_btn.setEnabled(False)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addSpacerItem(QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.confirm_btn)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.hint_label)
        main_layout.addWidget(self.url_edit)
        main_layout.addWidget(self.info_label)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        self.url_edit.textEdited.connect(self.on_text_edited)
        self.url_edit.returnPressed.connect(self.on_return_pressed)
        self.cancel_btn.clicked.connect(self.reject)
        self.confirm_btn.clicked.connect(self.on_confirm)

        self.url_edit.setFocus()
        self.data = None

    def on_text_edited(self, text: str):
        text = text.strip()
        self.confirm_btn.setEnabled(False)
        self.info_label.setText("")
        self.ref_value = None

        if self._current_reply is not None:
            try:
                self._current_reply.abort()
            except Exception:
                pass
            self._current_reply = None

        if not text:
            return
        parsed = urllib.parse.urlparse(text)
        if parsed.scheme.lower() not in ("http", "https"):
            text = f"http://{text}"
            parsed = urllib.parse.urlparse(text)
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        ref_list = qs.get("ref")
        if not ref_list:
            frag = parsed.fragment or ""
            if "?" in frag:
                frag_query = frag.split("?", 1)[1]
                qs2 = urllib.parse.parse_qs(frag_query, keep_blank_values=True)
                ref_list = qs2.get("ref")
            else:
                qs2 = urllib.parse.parse_qs(frag, keep_blank_values=True)
                ref_list = qs2.get("ref")

        if not ref_list or not ref_list[0].strip():
            self.info_label.setText("Вставлен некорректный url")
            return
        ref_value = ref_list[0].strip()
        ref_key = F.restore_uuid_from_client_1C_reference(ref_value)
        if not ref_key:
            return
        if self.validate_ref_func is not None:
            self.data = self.validate_ref_func(self.info_label, ref_key)
            self.confirm_btn.setEnabled(bool(self.data))

    def on_return_pressed(self):
        if self.confirm_btn.isEnabled():
            self.on_confirm()

    def on_confirm(self):
        if self.data is None:
            return
        self.accept()
#----29.08.25