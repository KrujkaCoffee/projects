import sys
from collections import defaultdict
from itertools import chain

from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QStyledItemDelegate
from PyQt5.QtGui import QPen, QColor, QPainter
from PyQt5.QtCore import Qt

"""

border = BorderPainter(top, bottom, left, right)
self.table.setItemDelegate(border)  # расширение хука paintEvent
border = BorderPainter(
    left_top=(2, 5), 
    right_bottom=(9, 9), 
    rgb_in=(200, 0, 0), 
    thick_out=6,
    highlight_hat=True  Задает границы ВВЕРХ ВНИЗ у текста отмеченного BOLD
    highlight_rows=[(6, 9)] Задает границы верх/низ, где 6 - это ВЕРХНЯЯ линия, а 9 НИЖНЯЯ
    highlight_cols=[(6, 9)] Задает границы лево/право, где 6 - это ЛЕВАЯ колонка линия, а 9 НИЖНЯЯ
)

ПАРАМЕТРЫ
    border.get_outside(row=2, col=2) # принимает строку и колонку и возвращает ВНЕШНИЕ границы для покраски
    border.color_out # объект цвета покраски внешних границ
    self.line_style_out Объект стиля внешней линии 
    self.thick_out толщина внешней линии
    
    
    border.get_insides(row=2, col=2) # принимает строку и колонку и возвращает ВНУТРЕННИЕ границы для покраски
    self.color_in # # объект цвета покраски внутренних границ
    self.line_style_in Объект стиля внутренней линии
    self.thick_out толщина внутренней линии
"""


class BorderPainter(QStyledItemDelegate):
    def __init__(
            self,
            left_top: tuple[int, int],
            right_bottom: tuple[int, int],
            thick_out: int = 4,
            thick_in: int = 1,
            rgb_out: tuple[int, int, int] = (0, 0, 0),
            rgb_in: tuple[int, int, int] = (0, 0, 0),
            line_style_out = Qt.SolidLine,
            line_style_in = Qt.SolidLine,
            horizontal_inline: bool = False,
            vertical_inline: bool = False,
            enabled:bool=True
    ):
        super().__init__()
        self.enabled = enabled

        self.left_top = left_top
        self.right_bottom = right_bottom
        self.thick_out = thick_out
        self.thick_in = thick_in
        self.color_out, self.color_in = QColor(*rgb_out), QColor(*rgb_in)
        self.pen_out = QPen(self.color_out, self.thick_out, line_style_out)
        self.line_style_out, self.line_style_in = line_style_out, line_style_in
        self.pen_in = QPen(self.color_in, self.thick_in, line_style_in)
        self.filled_top = set()
        self.filled_bottom = set()
        self.filled_left = set()
        self.filled_right = set()

        self.inside_right = set()
        self.inside_top = set()
        self._pens = []

        self.__init_coords = self.calc_coord(self.left_top, self.right_bottom, self.pen_out,
                                             horizontal_inline, vertical_inline)
        self.added_pen = None
        self.__dict__.update(**self.__init_coords)

    def update_border(self, table, left_top, right_bottom,
                      pen=None,
                      horizontal_inline=False,
                      vertical_inline=False,
                      repaint_by_row: bool = False):

        old_cells = (
                self.filled_top |
                self.filled_bottom |
                self.filled_left |
                self.filled_right |
                self.inside_top |
                self.inside_right
        )

        if pen is None:
            pen = self.pen_out

        self.filled_top.clear()
        self.filled_bottom.clear()
        self.filled_left.clear()
        self.filled_right.clear()
        self.inside_top.clear()
        self.inside_right.clear()
        self._pens.clear()

        coords = self.calc_coord(left_top, right_bottom, pen, horizontal_inline, vertical_inline)
        self.__dict__.update(**coords)

        new_cells = set().union(
            coords.get('filled_top', set()),
            coords.get('filled_bottom', set()),
            coords.get('filled_left', set()),
            coords.get('filled_right', set()),
            coords.get('inside_top', set()),
            coords.get('inside_right', set()),
        )

        cells_to_update = old_cells | new_cells

        if repaint_by_row:
            model = table.model()
            viewport = table.viewport()

            # Собираем строки для обновления (включая соседние для вертикальных линий)
            rows = {row for row, _ in cells_to_update}

            rows_with_neighbors = set()
            for row in rows:
                if 0 <= row < model.rowCount():
                    rows_with_neighbors.add(row)
                if 0 <= row - 1 < model.rowCount():
                    rows_with_neighbors.add(row - 1)
                if 0 <= row + 1 < model.rowCount():
                    rows_with_neighbors.add(row + 1)

            # Определяем видимые столбцы
            first_visible_col = table.columnAt(0)
            last_visible_col = table.columnAt(viewport.width() - 1)

            # Если таблица пустая или не отрисована - обновляем всё
            if first_visible_col == -1 or last_visible_col == -1:
                viewport.update()
                return

            for row in rows_with_neighbors:
                left_index = model.index(row, first_visible_col)
                right_index = model.index(row, last_visible_col)

                left_rect = table.visualRect(left_index)
                right_rect = table.visualRect(right_index)

                if not left_rect.isValid() or not right_rect.isValid():
                    continue

                row_rect = left_rect.united(right_rect)
                row_rect.adjust(-2, -2, 2, 2)  # Небольшой запас для границ

                viewport.update(row_rect)
        else:
            # Старый метод - обновляем отдельные ячейки
            for row, col in cells_to_update:
                index = table.model().index(row, col)
                if index.isValid():
                    rect = table.visualRect(index)
                    if rect.isValid():
                        rect.adjust(-1, -1, 1, 1)
                        table.viewport().update(rect)

    def set_colors(self,
                   rgb_out: tuple[int, int, int],
                   rgb_in: tuple[int, int, int]):

        self.color_out = QColor(*rgb_out)
        self.color_in = QColor(*rgb_in)

        self.pen_out = QPen(self.color_out, self.thick_out, self.line_style_out)
        self.pen_in = QPen(self.color_in, self.thick_in, self.line_style_in)

    def clear_borders(self,table:QTableWidget):

        old_cells = (
                self.filled_top |
                self.filled_bottom |
                self.filled_left |
                self.filled_right |
                self.inside_top |
                self.inside_right
        )



        self.filled_top.clear()
        self.filled_bottom.clear()
        self.filled_left.clear()
        self.filled_right.clear()
        self.inside_top.clear()
        self.inside_right.clear()
        self._pens.clear()

        self.enabled = False

        for row, col in old_cells:
            index = table.model().index(row, col)
            rect = table.visualRect(index)
            table.viewport().update(rect)

    def get_pen(self, row, col):
        pen = None
        for item in self._pens:
            cp = item.copy()
            cur_pen = cp.pop('pen')
            w = list(chain.from_iterable(cp.values()))
            if (row, col) in w:
                pen = cur_pen
        return pen

    def calc_coord(self, left_top, right_bottom, pen, hor, vert):
        ran_y = list(range(left_top[0], right_bottom[0] + 1))
        ran_x = list(range(left_top[1], right_bottom[1] + 1))
        result = defaultdict(set)
        for i in ran_y:
            for j in ran_x:
                is_min_y, is_max_y = min(ran_y) == i, max(ran_y) == i
                is_min_x, is_max_x = min(ran_x) == j, max(ran_x) == j
                if is_min_y:
                    result['filled_top'].add((i, j))
                if is_max_y:
                    result['filled_bottom'].add((i, j))
                if is_min_x:
                    result['filled_left'].add((i, j))
                if is_max_x:
                    result['filled_right'].add((i, j))
                if not is_min_y and hor:
                    result['inside_top'].add((i, j))
                if not is_max_x and vert:
                    result['inside_right'].add((i, j))
        result['pen'] = pen
        self._pens.append(result.copy())
        return result

    def __left(self, painter, option):
        painter.drawLine(option.rect.left(), option.rect.top(), option.rect.left(), option.rect.bottom())

    def __right(self, painter, option):
        painter.drawLine(option.rect.right(), option.rect.top(), option.rect.right(), option.rect.bottom())

    def __top(self, painter, option):
        painter.drawLine(option.rect.left(), option.rect.top(), option.rect.right(), option.rect.top())

    def __bottom(self, painter, option):
        painter.drawLine(option.rect.left(), option.rect.bottom(), option.rect.right(), option.rect.bottom())

    def get_outside(self, row, col):
        sides = {'top': self.filled_top, 'bottom': self.filled_bottom, 'left': self.filled_left, 'right': self.filled_right}
        found = []
        for name, side in sides.items():
            if (row, col) in side:
                found.append(name)
        return found

    def get_insides(self, row, col):
        sides = {'top': self.inside_top,'right': self.inside_right}
        found = []
        for name, side in sides.items():
            if (row, col) in side:
                found.append(name)
        return found

    def paint(self, painter, option, index):

        super().paint(painter, option, index)
        if self.enabled:
            painter.setRenderHint(QPainter.Antialiasing, True)
            found_out = self.get_outside(index.row(), index.column())
            found_in = self.get_insides(index.row(), index.column())
            if not found_out and not found_in:
                return
            pen = self.get_pen(index.row(), index.column())
            for side in sorted(found_in):
                painter.setPen(self.pen_in)
                getattr(self, f'_{self.__class__.__name__}__{side}')(painter, option)
            for side in found_out:
                if pen:
                    painter.setPen(pen)
                    getattr(self, f'_{self.__class__.__name__}__{side}')(painter, option)


    def get_min(self, lst, idx):
        try:
            srt = sorted(lst, key=lambda x: x[idx])
            return srt[0][idx]
        except Exception as e:
            print(e)

    def update_borders(self, coords: dict[str, set]):
        for key, value in coords.items():
            attr = getattr(self, key)
            if isinstance(attr, set):
                getattr(self, key).update(value)

    def add_corner_inside(
            self,
            left_top, right_bottom,
            thick: int = 2,
            rgb: tuple[int, int, int] = (0, 0, 0),
            line_style = Qt.SolidLine,
            horizontal_inline: bool = False,
            vertical_inline: bool = False
    ):
        color = QColor(*rgb)
        pen = QPen(color, thick, line_style)
        coords = self.calc_coord(left_top, right_bottom, pen, horizontal_inline, vertical_inline)
        init_coords = self.__init_coords

        min_left_out = sorted(init_coords['filled_left'])[0][1]
        min_left_inline = sorted(coords['filled_left'])[0][1]
        max_right_out = sorted(init_coords['filled_right'])[-1][1]
        max_right_inline = sorted(coords['filled_right'])[-1][1]
        min_top_out = sorted(init_coords['filled_top'])[0][0]
        min_top_inline = sorted(coords['filled_top'])[0][0]
        max_bottom_out = sorted(init_coords['filled_bottom'])[-1][0]
        max_bottom_inline = sorted(coords['filled_bottom'])[-1][0]

        if min_left_inline < min_left_out  and right_bottom[1] > self.left_top[1]:
            self.remove_out_intersections(coords, 'filled_left', min_left_out, max_right_out, is_x=True)
        if max_right_inline > max_right_out and right_bottom[1] < self.left_top[1]:
            self.remove_out_intersections(coords, 'filled_right', min_left_out, max_right_out, is_x=True)
        if min_top_inline < min_top_out and left_top[0] > self.right_bottom[0]:
            self.remove_out_intersections(coords, 'filled_top', min_top_out, max_bottom_out)
        if max_bottom_inline > max_bottom_out and left_top[0] < self.right_bottom[0]:
            self.remove_out_intersections(coords, 'filled_bottom', min_top_out, max_bottom_out)
        self.update_borders(coords)

    def remove_out_intersections(self, coords, key, min_val, max_val, is_x: bool = False):
        side_attr = getattr(self, key)
        for coord in coords[key]:
            if is_x:
                rang = side_attr.intersection([(coord[0], num) for num in range(min_val, max_val + 1)])
            else:
                rang = side_attr.intersection([(num, coord[1]) for num in range(min_val , max_val + 1)])
            for r in rang:
                side_attr.remove(r)


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.table = QTableWidget(100, 100)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.table)
        self.table.setHorizontalHeaderLabels([str(_) for _ in range(100)])
        self.table.setVerticalHeaderLabels([str(_) for _ in range(100)])

        for row in range(100):
            for col in range(100):
                item = QTableWidgetItem('бла бла бла')
                if row == 2 and col >= 5 and col <=9:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setText('заголовок')
                self.table.setItem(row, col, item)
        tbl = self.table
        border = BorderPainter(left_top=(3, 5), right_bottom=(9, 9), thick_out=3,
                               thick_in=3,rgb_out=(22,222,22),rgb_in=(122,222,122))
        # border = BorderPainter((0, 0), (3, tbl.columnCount() - 1))
        #border = BorderPainter((0, 0), (0, tbl.columnCount() - 1), thick_in=1,thick_out=2)
        #CQT.tbl_encircle(tbl, tbl.rowCount()-1, 0, tbl.rowCount()-1, tbl.columnCount() - 1)
        border.add_corner_inside((4, 4), (8, 8), thick=2)
        # border.add_corner_inside((4, 0), (4, tbl.columnCount() - 1), thick=2)
        #border.add_corner_inside((5, 0), (tbl.rowCount()-2, tbl.columnCount() - 1), thick=2,horizontal_inline=True,)
        #border.add_corner_inside((tbl.rowCount()-1, 0), (tbl.rowCount()-1, tbl.columnCount() - 1), thick=2)
        self.table.setItemDelegate(border)
        # border.add_corner_inside((1, 6), (10, 8))
        # border.add_corner_inside((3, 4), (8, 10), thick=4)
        # border.add_corner_inside((5, 6), (6, 7))

        self.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
