from PyQt5 import QtCore, QtWidgets

import refact
import utils
from utils import preparate_dict
from subdialogs.utils import check_input_values


class UpdMaterials(QtWidgets.QDialog):
    def __init__(self, application_num, response):
        super().__init__()

        self.pre_application = response

        self.application_num = application_num
        self.setWindowTitle(f"Внесение материалов заявки {application_num}")
        self.setFixedSize(350, 586)
        verticalLayout = QtWidgets.QVBoxLayout()

        self.material_for_quantity_label = QtWidgets.QLabel(text='Материал норма, кг. на кол-во')
        self.material_for_quantity_combobox = QtWidgets.QDoubleSpinBox()
        self.operation_label = QtWidgets.QLabel(text='Операция')
        self.operation_combobox = QtWidgets.QComboBox()
        self.operation_combobox.addItems(preparate_dict(self.pre_application, 'operations'))
        self.response_detail_label = QtWidgets.QLabel(text='Требуется ли предоставление ответной детали?')
        self.response_detail_combobox = QtWidgets.QComboBox()
        self.response_detail_combobox.addItems(preparate_dict(self.pre_application, 'response_detail'))
        self.time_norm_label = QtWidgets.QLabel(text='Нормы времени по операции на количество, Мин')
        self.time_norm_combobox = QtWidgets.QSpinBox()
        self.time_norm_combobox.setMaximum(1000)
        self.type_workpiece_label = QtWidgets.QLabel(text='Вид заготвки (сортамент полуфабрикат)') 
        self.type_workpiece_combo = QtWidgets.QComboBox()
        self.type_workpiece_combo.addItems(preparate_dict(self.pre_application, 'workpiece'))
        self.type_workpiece_combo.setEditable(True)
        self.type_workpiece_combo.lineEdit().returnPressed.connect(self.search_workpice)
        self.pack_type_label = QtWidgets.QLabel(text='Виды упаковки')
        self.pack_type_combobox = QtWidgets.QComboBox()
        self.pack_type_combobox.addItems(preparate_dict(self.pre_application, 'pack_type'))
        self.container_type_label = QtWidgets.QLabel(text='Виды тары')
        self.container_type_combobox = QtWidgets.QComboBox()
        self.container_type_combobox.addItems(preparate_dict(self.pre_application, 'container_type'))
        self.to_check_label = QtWidgets.QLabel(text='Нужен ли ТО контроль')
        self.to_check_combo = QtWidgets.QComboBox()
        self.to_check_combo.addItems(['Да', 'Нет'])

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")

        verticalLayout.addWidget(self.material_for_quantity_label)
        verticalLayout.addWidget(self.material_for_quantity_combobox)
        verticalLayout.addWidget(self.operation_label)
        verticalLayout.addWidget(self.operation_combobox)
        verticalLayout.addWidget(self.response_detail_label)
        verticalLayout.addWidget(self.response_detail_combobox)
        verticalLayout.addWidget(self.time_norm_label)
        verticalLayout.addWidget(self.time_norm_combobox)
        verticalLayout.addWidget(self.type_workpiece_label)
        verticalLayout.addWidget(self.type_workpiece_combo)
        verticalLayout.addWidget(self.pack_type_label)
        verticalLayout.addWidget(self.pack_type_combobox)
        verticalLayout.addWidget(self.container_type_label)
        verticalLayout.addWidget(self.container_type_combobox)
        verticalLayout.addWidget(self.to_check_label)
        verticalLayout.addWidget(self.to_check_combo)
        verticalLayout.addWidget(self.easy_notify)
        verticalLayout.addStretch(stretch=1)

        buttonsLayout = QtWidgets.QHBoxLayout()
        btn_create = QtWidgets.QPushButton(text='Сохранить')
        btn_create.clicked.connect(self.save)
        btn_cancel = QtWidgets.QPushButton(text='Отменить')
        btn_cancel.clicked.connect(self.close)
        buttonsLayout.addWidget(btn_create)
        buttonsLayout.addWidget(btn_cancel)

        verticalLayout.addLayout(buttonsLayout)
        self.setLayout(verticalLayout)


    def save(self):
        di = {}
        di['is_notify'] = self.easy_notify.isChecked()
        di['application_num'] = self.application_num
        di['quantity'] = check_input_values(self.material_for_quantity_combobox, self.material_for_quantity_label)
        di['operation'] = utils.get_val(self.operation_combobox)
        di['response_detail'] = utils.convert_to_bool(utils.get_val(self.response_detail_combobox))
        di['time'] = check_input_values(self.time_norm_combobox, self.time_norm_label)
        di['detail'] = utils.get_val(self.type_workpiece_combo)
        di['pack_type'] = utils.get_val(self.pack_type_combobox)
        di['container_type'] = utils.get_val(self.container_type_combobox)
        di['to_check'] = check_input_values(self.to_check_combo, self.to_check_label)
        # post_request('/outsouce/set_material_st', di)
        refact.insert_material_to_out(
            app=self.application_num,
            container_type=utils.get_val(self.container_type_combobox),
            pack_type=utils.get_val(self.pack_type_combobox),
            respons_detail=utils.convert_to_bool(utils.get_val(self.response_detail_combobox)),
            # detail=check_input_values(self.type_workpiece_combo, self.type_workpiece_label, self.pre_application['workpiece']),
            detail=di,
        )
        self.close()
          
    def search_workpice(self):
        text = self.type_workpiece_combo.currentText()
        index = self.type_workpiece_combo.findText(text, flags=QtCore.Qt.MatchFlag.MatchContains )
        if index != -1:
            self.type_workpiece_combo.setCurrentIndex(index)
            self.type_workpiece_combo.lineEdit().setSelection(len(text), len(self.type_workpiece_combo.currentText()))