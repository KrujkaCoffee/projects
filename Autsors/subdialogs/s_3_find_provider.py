from PyQt5 import QtWidgets, QtCore

import refact
from subdialogs.utils import check_input_values

from project_cust_38 import Cust_Qt as CQT


class UpdProvider(QtWidgets.QDialog):
    def __init__(self, application_num, response):
        super().__init__()
        self.pre_application = response
        
        self.application_num = application_num
        self.setWindowTitle(f"Внесение поставщиков {self.application_num}")
        self.setFixedSize(330, 360)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.provider_label = QtWidgets.QLabel(text='Поставщик')
        self.provider_combobox = QtWidgets.QComboBox()
        for item in self.pre_application:
            self.provider_combobox.addItem(item['name'], item['Ref_Key'])
        self.provider_combobox.setEditable(True)
        self.provider_combobox.lineEdit().returnPressed.connect(self.searchProvider)
        
        self.rovider_redy_date_label = QtWidgets.QLabel(text='Сроки готовности от поставщика')
        self.rovider_redy_date = QtWidgets.QDateEdit()
        self.rovider_redy_date.setDate(QtCore.QDate.currentDate())
        self.rovider_redy_date.setCalendarPopup(True)
        self.provider_note_label = QtWidgets.QLabel(text='Причечание')
        self.provider_note_text = QtWidgets.QTextEdit() 

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.provider_label)
        verticalLayout.addWidget(self.provider_combobox)
        verticalLayout.addWidget(self.rovider_redy_date_label)
        verticalLayout.addWidget(self.rovider_redy_date)
        verticalLayout.addWidget(self.easy_notify)
        verticalLayout.addWidget(self.provider_note_label)
        verticalLayout.addWidget(self.provider_note_text)

        # upd_providers_label = QtWidgets.QLabel('Если не нашли нужного поставщика:')
        # self.upd_providers_btn = QtWidgets.QPushButton(text='обновить базу')
        # self.upd_providers_btn.clicked.connect(self.upd_providers)
        # verticalLayout.addWidget(upd_providers_label)
        # verticalLayout.addWidget(self.upd_providers_btn)

        buttonsLayout = QtWidgets.QHBoxLayout()
        btn_create = QtWidgets.QPushButton(text='Сохранить')
        btn_create.clicked.connect(self.save_application)
        btn_reject = QtWidgets.QPushButton(text='Отклонить')
        btn_reject.clicked.connect(self.reject_application)
        btn_cancel = QtWidgets.QPushButton(text='Отменить')
        btn_cancel.clicked.connect(self.close)
        buttonsLayout.addWidget(btn_create)
        buttonsLayout.addWidget(btn_reject)
        buttonsLayout.addWidget(btn_cancel)

        verticalLayout.addLayout(buttonsLayout)
        self.setLayout(verticalLayout)


    def searchProvider(self):
        text = self.provider_combobox.currentText()
        index = self.provider_combobox.findText(text, flags=QtCore.Qt.MatchFlag.MatchContains )
        if index != -1:
            self.provider_combobox.setCurrentIndex(index)
            self.provider_combobox.lineEdit().setSelection(len(text), len(self.provider_combobox.currentText()))


    def save_application(self):
        di = {}
        di['is_notify'] = self.easy_notify.isChecked()
        di['application_num'] = self.application_num
        app = refact.insert_find_providers_stage(
            app_id=self.application_num,
            provider_redy_date=check_input_values(self.rovider_redy_date, self.rovider_redy_date_label),
            provider=self.provider_combobox.currentText(),
            note=self.provider_note_text.toPlainText(),
            ref_key=self.provider_combobox.currentData()
        )
        msg = 'Что-то пошло не так..'
        if app:
            msg = 'Создано'
        CQT.msgbox(msg)
        self.close()

        # if di['provider_id'] and di['provider_redy_date']:
        #     post_request('/outsouce/set_providers', di)
        #     self.close()


    def reject_application(self):
        di = {}
        di['application_num'] = self.application_num
        # post_request('/outsouce/reject_app', di) TODO статус = отмена
        self.close()


    def upd_providers(self):
        # get_request('/outsouce/upd_partners_from_1c', is_realy_get=True)
        self.upd_providers_btn.setDisabled(True)
        self.close()
