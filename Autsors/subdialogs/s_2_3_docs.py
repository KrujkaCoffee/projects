from PyQt5 import QtWidgets

import refact
import utils
from utils import preparate_dict
from subdialogs.utils import check_input_values

from project_cust_38 import Cust_Qt as CQT


class UpdDocs(QtWidgets.QDialog):
    def __init__(self, application_num, response):
        super().__init__()
        self.pre_application = response
        
        self.application_num = application_num
        self.setWindowTitle(f"Внесение данных по документам заявки №{application_num}")
        self.resize(227, 686)
        verticalLayout = QtWidgets.QVBoxLayout()
        self.provider_docs_label = QtWidgets.QLabel(text='Требуемые документы от поставщика')
        self.provider_docs_text = QtWidgets.QTextEdit()
        self.check_place_label = QtWidgets.QLabel(text='Место проведения входного контроля')
        self.check_place_combobox = QtWidgets.QComboBox()
        self.check_place_combobox.addItems(preparate_dict(self.pre_application, 'check_place'))
      
        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.provider_docs_label)
        verticalLayout.addWidget(self.provider_docs_text)
        verticalLayout.addWidget(self.check_place_label)
        verticalLayout.addWidget(self.check_place_combobox)
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
        di['provider_docs'] = check_input_values(self.provider_docs_text, self.provider_docs_label)
        di['check_place_id'] = check_input_values(self.check_place_combobox, self.check_place_label, self.pre_application['check_place'])
        app = refact.insert_add_docs_stage(
            app_id=self.application_num,
            provider_docs=check_input_values(self.provider_docs_text, self.provider_docs_label),
            check_place=utils.get_val(self.check_place_combobox)
        )
        msg = 'Что-то пошло не так..'
        if app:
            msg = 'Создано'
        CQT.msgbox(msg)
        self.close()
        self.close()