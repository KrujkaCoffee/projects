from PyQt5 import QtWidgets, QtCore

import connectors_1c
import refact

from project_cust_38 import Cust_Qt as CQT


class OrderPost(QtWidgets.QDialog):
    def __init__(self, application_num):
        super().__init__()
        self.application_num = application_num

        self.setWindowTitle(f"Внесение номера заказа для заявки {self.application_num}")
        self.resize(227, 100)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.provider_rbtn = QtWidgets.QRadioButton(text='заказ поставщику')
        self.provider_rbtn.setChecked(True)
        self.recicler_rbtn = QtWidgets.QRadioButton(text='заказ переработчику')
        get_orders_btn = QtWidgets.QPushButton('Получить')
        get_orders_btn.clicked.connect(self.get_orders)

        self.order_combo = QtWidgets.QComboBox()

        self.order_combo.setEditable(True)
        self.order_combo.lineEdit().returnPressed.connect(self.searchOrder)
        self.order_combo.addItems([])

        verticalLayout.addWidget(self.provider_rbtn)
        verticalLayout.addWidget(self.recicler_rbtn)
        verticalLayout.addWidget(get_orders_btn)
        verticalLayout.addWidget(self.order_combo)

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")
        verticalLayout.addWidget(self.easy_notify)

        buttonsLayout = QtWidgets.QHBoxLayout()
        btn_create = QtWidgets.QPushButton(text='Сохранить')
        btn_create.clicked.connect(self.save_application)
        btn_cancel = QtWidgets.QPushButton(text='Отменить')
        btn_cancel.clicked.connect(self.close)
        buttonsLayout.addWidget(btn_create)
        buttonsLayout.addWidget(btn_cancel)

        verticalLayout.addLayout(buttonsLayout)
        self.setLayout(verticalLayout)

    def searchOrder(self):
        text = self.order_combo.currentText()
        index = self.order_combo.findText(text, flags=QtCore.Qt.MatchFlag.MatchContains )
        if index != -1:
            self.order_combo.setCurrentIndex(index)
            self.order_combo.lineEdit().setSelection(len(text), len(self.order_combo.currentText()))

    def save_application(self):
        di = {}
        di['is_notify'] = self.easy_notify.isChecked()
        di['application_num'] = self.application_num
        di['provider_order'] = self.order_combo.currentText()
        app = refact.insert_provider_order_stage(
            app_id=self.application_num,
            provider_order=self.order_combo.currentText()
        )
        msg = 'Что-то пошло не так..'
        if app:
            msg = 'Создано'
        CQT.msgbox(msg)
        self.close()
        # if di['provider_order']:
        #     post_request('/outsouce/provider_order', di)
        #     self.close()

    def get_orders(self):
        di = {}
        di['application_num'] = self.application_num
        if self.provider_rbtn.isChecked():
            res = connectors_1c.get_provider_orders()
            # res = post_request('/outsouce/get_provider_orders', di)
        else:
            res = connectors_1c.get_provider_orders()

            # res = post_request('/outsouce/get_recicler_orders', di)

        self.order_combo.addItems(res)