import pathlib
import sys
import json

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QEvent, Qt, QObject
from PyQt5.QtGui import QCursor
# from PyQt5.QtGui import QCursor, QPalette
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, \
    QMessageBox, QStyledItemDelegate

from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_Qt as CQT


class HeaderHoverFilter(QObject):
    def __init__(self, header):
        super().__init__(header)

    def eventFilter(self, obj, event: QEvent):
        if not QApplication.mouseButtons() & Qt.LeftButton:
            QApplication.setOverrideCursor(Qt.PointingHandCursor)
        if event.type() == QEvent.HoverLeave:
            QApplication.setOverrideCursor(Qt.ArrowCursor)
        return super().eventFilter(obj, event)


class TableWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.table = QTableWidget(7, 5)
        self.table.setHorizontalHeaderLabels(['Column 1', 'Column 2', 'Column 3', 'col 4', 'col 5'])
        self.table.setMouseTracking(True)
        self.table.setRowCount(5)
        CQT.FillHorizontalHeaderSort(self.table)
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)


class FillHorizontalHeaderSort:
    """
    Сохранение позиции секций QTableWidget.HorizontalHeaderItem
    События:
        По событию фактического перемещения drag on drop колонки происходит сохранение состояния колонок в путь указанный
            в аргументе tmp_dir/имя объекта таблицы_sort_horizontal_header_columns.pickle
            если tmp_dir не задан формируется путь ${USER}/mes_tmp/{APP}/имя объекта таблицы_sort_horizontal_header_columns.pickle

    FillHorizontalHeaderSort(table_widget)
    """
    def __init__(self, table: QTableWidget, tmp_dir: str = None):
        self.table = table
        self.tmp_dir = tmp_dir
        self.signal_property = 'horizontal_header_section_moved_saver'
        self.__mutable_table()
        self.fill_horizontal_header_sort()

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
        current_sections = self.get_horizontal_header_sections()
        if not isinstance(current_sections, list) or len(current_sections) == 0:
            return
        if set(current_sections) != set(data) or len(data) != len(current_sections):
            print('[fill_horizontal_header_sort] Количество колонок изменилось, значение порядка из кэша не будет применено')
            return
        for target_index, column in enumerate(data):
            current_index = current_sections.index(column)
            if current_sections[target_index] != column:
                self.table.horizontalHeader().moveSection(current_index, target_index)
                current_sections[target_index], current_sections[current_index] = current_sections[current_index], current_sections[target_index]

    def __mutable_table(self):
        is_mutable = self.table.property(self.signal_property)
        if not is_mutable:
            self.table.setDragEnabled(True)
            self.table.setAcceptDrops(True)
            self.table.setDropIndicatorShown(True)
            self.table.horizontalHeader().setSectionsMovable(True)
            self.table.horizontalHeader().sectionMoved.connect(
                lambda struct_ind, old_ind, new_ind: self.__save_column_order(struct_ind, old_ind, new_ind)
            )
            self.table.horizontalHeader().sectionPressed.connect(self.__pressed_header)
            self.table.setProperty(self.signal_property, True)


    def __save_column_order(self, _, old_ind, new_ind):
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        headers[new_ind], headers[old_ind] = headers[old_ind], headers[new_ind]
        self.tmp_path.write_bytes(F.to_binary_pickle(headers))

    def __pressed_header(self, *args, **kwargs):
        self.table.horizontalHeader().setCursor(Qt.ClosedHandCursor)


    def __load_column_data(self):
        try:
            if self.tmp_path.exists():
                return F.from_binary_pickle(self.tmp_path.read_bytes())
        except (FileNotFoundError, EOFError):
            return

    def get_horizontal_header_sections(self):
        if self.table.columnCount() == 0:
            return
        return [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TableWidget()
    window.resize(400, 300)
    window.show()
    sys.exit(app.exec_())
