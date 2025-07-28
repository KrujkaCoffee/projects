from PyQt5 import QtWidgets

import refact
import utils
from utils import preparate_dict
from subdialogs.utils import check_input_values


class Rework(QtWidgets.QDialog):
    def __init__(self, application_num, response):
        super().__init__()
        self.application_num = application_num
        self.pre_application = response
        
        self.setWindowTitle(f"Внесение контроля доработки {self.application_num}")
        self.resize(227, 100)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.otk_control_label = QtWidgets.QLabel(text='Необходима доработка у поставщика')
        self.otk_control_combobox = QtWidgets.QComboBox()
        self.otk_control_combobox.addItems(preparate_dict(self.pre_application, 'to_control'))

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.otk_control_label)
        verticalLayout.addWidget(self.otk_control_combobox)
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
        di['to_control_id'] = check_input_values(self.otk_control_combobox, self.otk_control_label, self.pre_application['to_control'])
        
        app = refact.insert_rework_stage(app_id=self.application_num, rework=utils.get_val(self.otk_control_combobox))
        msg = 'Что-то пошло не так..'
        if app:
            msg = 'Создано'
        from project_cust_38 import Cust_Qt as CQT
        CQT.msgbox(msg)
        self.close()
        # post_request('/outsouce/set_rework', di)
