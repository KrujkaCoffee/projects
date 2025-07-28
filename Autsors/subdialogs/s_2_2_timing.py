from PyQt5 import QtWidgets, QtCore

import refact
import utils
from utils import preparate_dict
from subdialogs.utils import check_input_values, input_error

from project_cust_38 import Cust_Qt as CQT


class UpdTiming(QtWidgets.QDialog):
    def __init__(self, application_num, response):
        super().__init__()
        self.application_num = application_num
        self.pre_application = response

        self.setWindowTitle(f"Внесение сроков заявки {self.application_num}")
        self.resize(227, 386)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.need_date_label = QtWidgets.QLabel(text='Необходимая дата для ответа (проработка 3-5 дней)')
        self.need_date = QtWidgets.QDateEdit()
        self.need_date.setDate(QtCore.QDate.currentDate())
        self.need_date.date()
        self.need_date.setCalendarPopup(True)
        self.delivery_date_label = QtWidgets.QLabel(text='Необходимая дата поставки на склад')
        self.delivery_date = QtWidgets.QDateEdit()
        self.delivery_date.setDate(QtCore.QDate.currentDate())
        self.delivery_date.setCalendarPopup(True)
        self.ready_date_label = QtWidgets.QLabel(text='Дата готовности заготовки к передаче')
        self.ready_date = QtWidgets.QDateEdit()
        self.ready_date.setDate(QtCore.QDate.currentDate())
        self.ready_date.setCalendarPopup(True)
        self.type_material_label = QtWidgets.QLabel(text='Использование сырья')
        self.type_material_combobox = QtWidgets.QComboBox()
        self.type_material_combobox.addItems(preparate_dict(self.pre_application, 'type_material'))

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.need_date_label)
        verticalLayout.addWidget(self.need_date)
        verticalLayout.addWidget(self.ready_date_label)
        verticalLayout.addWidget(self.ready_date)
        verticalLayout.addWidget(self.delivery_date_label)
        verticalLayout.addWidget(self.delivery_date)
        verticalLayout.addWidget(self.type_material_label)
        verticalLayout.addWidget(self.type_material_combobox)
        verticalLayout.addWidget(self.easy_notify)

        buttonsLayout = QtWidgets.QHBoxLayout()
        btn_create = QtWidgets.QPushButton(text='Сохранить')
        btn_create.clicked.connect(self.save_application)
        btn_cancel = QtWidgets.QPushButton(text='Отменить')
        btn_cancel.clicked.connect(self.close)
        buttonsLayout.addWidget(btn_create)
        buttonsLayout.addWidget(btn_cancel)
        verticalLayout.addStretch(stretch=1)
        verticalLayout.addLayout(buttonsLayout)
        self.setLayout(verticalLayout)


    def save_application(self):
        di = {}
        di['is_notify'] = self.easy_notify.isChecked()
        di['application_num'] = self.application_num
        di['need_date'] = check_input_values(self.need_date, self.need_date_label)
        di['delivery_date'] = check_input_values(self.delivery_date, self.delivery_date_label)
        di['ready_date'] = check_input_values(self.ready_date, self.ready_date_label)
        di['type_material_id'] = check_input_values(self.type_material_combobox, self.type_material_label, self.pre_application['type_material'])

        res_date_check = self.check_dates()
        app = refact.insert_add_time_stage(
            app_id=self.application_num,
            need_date=check_input_values(self.need_date, self.need_date_label),
            delivery_date=check_input_values(self.delivery_date, self.delivery_date_label),
            ready_date=check_input_values(self.ready_date, self.ready_date_label),
            type_material=utils.get_val(self.type_material_combobox)
        )
        msg = 'Что-то пошло не так..'
        if app:
            msg = 'Создано'
        CQT.msgbox(msg)
        # post_request('/outsouce/set_timings_st', di)
        self.close()

    def check_dates(self):
        response_befor_delevery = False
        ready_befor_delivery = False

        if self.ready_date.dateTime().toPyDateTime() < self.delivery_date.dateTime().toPyDateTime():
            ready_befor_delivery = True

        if self.need_date.dateTime().toPyDateTime() < self.delivery_date.dateTime().toPyDateTime():
            response_befor_delevery = True
        
        if not ready_befor_delivery:
            input_error('Дата готовности заготовок всегда должна быть раньше даты поставки на склад', blanc=True)
        
        if not response_befor_delevery:
            input_error('Дата ответа всегда должна быть раньше даты поставки на склад', blanc=True)

        if response_befor_delevery and ready_befor_delivery:
            return True
