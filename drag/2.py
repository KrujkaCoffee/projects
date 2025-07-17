import json
import sys

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QWidget, QTableWidget


class TableWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget(5, 3)
        self.table.setHorizontalHeaderLabels(['Column 1', 'Column 2', 'Column 3'])
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)

        self.save_button = QPushButton("Сохранить порядок")
        self.save_button.clicked.connect(self.save_column_order)

        self.load_button = QPushButton("Загрузить порядок")
        self.load_button.clicked.connect(self.load_column_order)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.save_button)
        layout.addWidget(self.load_button)
        self.setLayout(layout)

    def save_column_order(self):
        order = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        with open('column_order.json', 'w') as f:
            json.dump(order, f)
        print("Порядок колонок сохранен:", order)

    def load_column_order(self):
        try:
            with open('column_order.json', 'r') as f:
                order = json.load(f)
            print("Загруженный порядок колонок:", order)
            self.reorder_columns(order)
        except FileNotFoundError:
            print("Файл с порядком колонок не найден.")

    def reorder_columns(self, order):
        current_labels = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        new_order_indices = [current_labels.index(col) for col in order if col in current_labels]
        self.table.setColumnHidden(0, True)
        for index in new_order_indices:
            self.table.setColumnHidden(index, False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TableWidget()
    window.show()
    sys.exit(app.exec_())
