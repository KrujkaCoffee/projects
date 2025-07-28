from PyQt5 import QtWidgets

import refact
import utils
from utils import preparate_dict
from subdialogs.utils import check_input_values


class ToPost(QtWidgets.QDialog):
    def __init__(self, application_num, response):
        super().__init__()
        self.application_num = application_num
        self.pre_application = response

        self.setWindowTitle(f"Внесение контроля TO для заявки {self.application_num}")
        self.resize(227, 100)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.to_control_label = QtWidgets.QLabel(text='Контроль ТО')
        self.to_control_combobox = QtWidgets.QComboBox()
        w = preparate_dict(self.pre_application, 'to_control')
        self.to_control_combobox.addItems(preparate_dict(self.pre_application, 'to_control'))

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.to_control_label)
        verticalLayout.addWidget(self.to_control_combobox)
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
        di['to_control_id'] = check_input_values(self.to_control_combobox, self.to_control_label, self.pre_application['to_control'])
        if di['to_control_id']:
            # post_request('/outsouce/set_to', di)
            app = refact.insert_to_stage(app_id=self.application_num, to=utils.get_val(self.to_control_combobox))
            # post_request('/outsouce/set_to', di)\
            msg = 'Что-то пошло не так..'
            if app:
                msg = 'Создано'
            from project_cust_38 import Cust_Qt as CQT
            CQT.msgbox(msg)
            self.close()