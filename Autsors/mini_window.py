from typing import TYPE_CHECKING
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QDialog, QLabel

if TYPE_CHECKING:
    from Outsourcing import ObjBranch

class MiniTablePopup(QDialog):
    def __init__(self, parent, cur_obj: 'ObjBranch', on_checked):
        super().__init__(parent)
        self.cur_obj = cur_obj
        self.on_checked = on_checked
        self.label = QLabel('Выделите нужны поля')
        self.setGeometry(100, 100, 200, 200)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.table = QtWidgets.QTableWidget(len(cur_obj.fields), 2)
        self.table.setHorizontalHeaderLabels(["Поле", "✓"])
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        for idx, (field, is_checked) in enumerate(self.cur_obj.fields.items()):
            self.table.setItem(idx, 0, QtWidgets.QTableWidgetItem(field))
            checkbox = QtWidgets.QCheckBox()
            checkbox.setChecked(is_checked)
            checkbox.stateChanged.connect(self.chk_state_changed(idx))
            self.checkbox = checkbox
            self.table.setCellWidget(idx, 1, checkbox)

        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        self.setLayout(layout)

    def chk_state_changed(self, row: int):
        def wrap(checked):
            key = self.table.item(row, 0) and self.table.item(row, 0).text()
            if key:
                self.cur_obj.fields = {**self.cur_obj.fields, key: checked}
            self.on_checked()
        return wrap

class CustomComboBox(QPushButton):
    def __init__(self, cur_obj: 'ObjBranch', on_checked):
        super().__init__()
        self.clicked.connect(self.show_list)
        self.setText("Выделите поля")
        self.on_checked = on_checked
        self.cur_obj = cur_obj

    def show_list(self, *args):
        if not self.cur_obj.fields:
            return
        dialog = MiniTablePopup(self, self.cur_obj, self.on_checked)
        dialog.setModal(True)
        button_pos = QtGui.QCursor.pos()
        dialog.move(button_pos)
        dialog.exec_()
