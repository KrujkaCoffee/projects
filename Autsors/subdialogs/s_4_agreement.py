from PyQt5 import QtWidgets

import refact
import utils
from utils import preparate_dict

from project_cust_38 import Cust_Qt as CQT


class Agreement(QtWidgets.QDialog):
    def __init__(self, application_num, response):
        super().__init__()
        self.pre_application = response
        
        # self.pre_application = post_request('/outsouce/get_agreements')
        self.pre_application = {'agreements': [{'id': 1, 'name': 'Да'}, {'id': 2, 'name': 'Нет'}, {'id': 3, 'name': 'не выбран'}]}

        self.application_num = application_num
        self.setWindowTitle(f"Внесение сроков заявки {self.application_num}")
        self.resize(227, 100)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.check_ok_label = QtWidgets.QLabel(text='цена и сроки устраивают?')
        self.check_ok_combobox = QtWidgets.QComboBox()
        self.check_ok_combobox.addItems(preparate_dict(self.pre_application, 'agreements'))

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.check_ok_label)
        verticalLayout.addWidget(self.check_ok_combobox)
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
        # di['agree_id'] = check_input_values(self.check_ok_combobox, self.check_ok_label, self.pre_application['agreements'])
        di['agree'] = utils.get_val(self.check_ok_combobox)
        app = refact.insert_agreement_stage(
            app_id=self.application_num,
            agree=utils.convert_to_bool(utils.get_val(self.check_ok_combobox))
        )
        msg = 'Что-то пошло не так..'
        if app:
            msg = 'Создано'
        CQT.msgbox(msg)
        self.close()

        # if di['agree_id']:
        #     post_request('/outsouce/set_agreements', di)
        #     self.close()
