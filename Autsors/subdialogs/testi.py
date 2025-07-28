import sys
from typing import Callable
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QDialog, QLabel

class MiniTablePopup(QDialog):
    def __init__(self, parent, cur_obj: str, fields: dict[str, bool], on_checked: Callable[[str, dict[str, bool]], None]):
        super().__init__(parent)
        self.fields = fields
        self.on_checked = on_checked
        self.label = QLabel('Выделите нужны поля')
        self.setWindowTitle("Мини-таблица")
        self.setGeometry(100, 100, 200, 200)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.table = QtWidgets.QTableWidget(len(fields), 2)
        self.table.setHorizontalHeaderLabels(["Поле", "✓"])
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        for idx, (field, is_checked) in enumerate(fields.items()):
            self.table.setItem(idx, 0, QtWidgets.QTableWidgetItem(field))
            checkbox = QtWidgets.QCheckBox()
            checkbox.setChecked(is_checked)
            checkbox.stateChanged.connect(self.chk_state_changed(idx, cur_obj))
            self.table.setCellWidget(idx, 1, checkbox)

        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def chk_state_changed(self, row: int, cur_obj: str):
        def wrap(checked):
            key = self.table.item(row, 0) and self.table.item(row, 0).text()
            if key:
                self.fields[key] = checked
            self.on_checked(cur_obj, self.fields)
        return wrap

class CustomComboBox(QPushButton):
    def __init__(self, cur_obj: str, get_fields_func: Callable[..., dict[str, str]], on_checked):
        super().__init__()
        self.clicked.connect(self.show_list)
        self.setText("Выделите поля")
        self.get_fields_func = get_fields_func
        self.on_checked = on_checked
        self.cur_obj = cur_obj

    def show_list(self, *args):
        fields = self.get_fields_func(self.cur_obj) if callable(self.get_fields_func) else self.get_fields_func
        if not fields:
            return
        dialog = MiniTablePopup(self, self.cur_obj, fields, self.on_checked)
        dialog.setModal(True)
        button_pos = QtGui.QCursor.pos()
        dialog.move(button_pos)
        dialog.exec_() 

def handler(dic):
    print()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    items = {"Item 1": True, "Item 2": True, "Item 3": True, "Item 4": True}
    combo_box = CustomComboBox(lambda: items, handler)
    combo_box.setWindowTitle("Custom ComboBox")
    combo_box.resize(200, 150)
    combo_box.show()

    sys.exit(app.exec_())
