from PyQt5 import QtWidgets, QtCore

import settings


def input_error(label, blanc=False):
    msg = QtWidgets.QMessageBox()
    if not blanc:
        msg.setWindowTitle("ошибка")
        stmt = 'Не верно: '
    else:
        msg.setWindowTitle("аутсорс")
        stmt = ''
    if isinstance(label, str):
        msg.setText(f'{stmt}{label}')
    else:
        msg.setText(f'{stmt}{label.text()}')
    msg.exec()



def get_value_from_full(li, val):
    for one_val_di in li:
        if one_val_di['name'] == val:
            return one_val_di['id']


def check_input_values(check_qobject, label, li=None):
    if isinstance(check_qobject, QtWidgets.QComboBox):
        value = check_qobject.currentText()
        if not value == settings.BLANC_VALUE:
            if li:
                return get_value_from_full(li, value)
            return value
            
    elif isinstance(check_qobject, QtWidgets.QTextEdit):
        value = check_qobject.toPlainText()
        if value and not value == settings.BLANC_VALUE:
            if li:
                return get_value_from_full(li, value)
            return value
            
    elif isinstance(check_qobject, QtWidgets.QSpinBox):
        value = check_qobject.value()
        if value:
            if li:
                return get_value_from_full(li, value)
            return value
        
    elif isinstance(check_qobject, QtWidgets.QDoubleSpinBox):
        value = check_qobject.value()
        if value:
            if li:
                return get_value_from_full(li, value)
            return value
        
    elif isinstance(check_qobject, QtWidgets.QDateEdit):
        value = check_qobject.dateTime()
        if value:
            if value > QtCore.QDateTime.currentDateTime():
                py_datetime = value.toPyDateTime()
                return py_datetime.strftime('%Y-%m-%d')
            
    input_error(label)