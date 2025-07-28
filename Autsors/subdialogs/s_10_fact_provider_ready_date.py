from PyQt5 import QtWidgets, QtCore

import refact
from subdialogs.utils import check_input_values
from project_cust_38 import Cust_Qt as CQT


class FactProviderReadyDate(QtWidgets.QDialog):
    def __init__(self, application_num):
        super().__init__()
        self.application_num = application_num     
 
        self.setWindowTitle(f"Внесение контроля доработки {self.application_num}")
        self.resize(227, 100)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.need_date_label = QtWidgets.QLabel(text='выберите дату')
        self.need_date = QtWidgets.QDateEdit()
        self.need_date.setDate(QtCore.QDate.currentDate())
        self.need_date.date()
        self.need_date.setCalendarPopup(True)

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.need_date)
        verticalLayout.addWidget(self.easy_notify)
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


    def save_application(self):
        di = {}
        di['is_notify'] = self.easy_notify.isChecked()
        di['application_num'] = self.application_num
        di['fact_provider_ready_date'] = check_input_values(self.need_date, self.need_date_label)
        
        if di['fact_provider_ready_date']:
            result = refact.update_fact_provider_ready_date(self.application_num, check_input_values(self.need_date, self.need_date_label))
            if result:
                CQT.msgbox('Удачно')
            else:
                CQT.msgbox('Не удалось отредактировать дату')
            # post_request('/outsouce/set_fact_provider_ready_date', di)
            self.close()