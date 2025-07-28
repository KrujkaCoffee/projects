from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFormLayout, QDialog, QHBoxLayout, QSpinBox, QComboBox

import utils
from utils import preparate_dict, error_message
from utils import check_int, get_val

from project_cust_38 import Cust_Qt as CQT


class CheckNewApplicationDialog(QDialog):
    def __init__(self, input_self, detail_di, sub_di, app_type, naryads):
        super().__init__(input_self)
        self.setWindowTitle("Проверка вводимых данных")
        # self.setBaseSize(500, 400)
        self.detail_di = detail_di
        self.app_type = app_type
        self.input_self = input_self
        self.new_app_types = utils.get_types_for_new_app()

        self.main_check_lt = QVBoxLayout()

        order_lt = QHBoxLayout()
        order_lt.addWidget(QLabel('Заказ на производство'))
        self.order = detail_di['production_order']

        order_lt.addWidget(QLabel(self.order))
        self.main_check_lt.addLayout(order_lt)

        nom_lt = QHBoxLayout()
        nom_lt.addWidget(QLabel('Номенклатура'))
        nom_lt.addWidget(QLabel(detail_di['name']))

        self.main_check_lt.addLayout(nom_lt)

        units = list(item['name'] for item in sub_di['units'])

        out_form_lt = QFormLayout()
        self.response_detail = QComboBox()
        self.response_detail.addItems(preparate_dict(self.new_app_types, 'response_detail', with_blanc=False))
        self.response_detail.setCurrentText('не выбран')
        out_form_lt.addRow('нужна ли ответная деталь', self.response_detail)
        self.detail_mark = QComboBox()
        self.detail_mark.addItems(preparate_dict(self.new_app_types, 'detail_mark', with_blanc=False))
        self.detail_mark.setCurrentText('не выбран')
        out_form_lt.addRow('нужна ли маркировка деталей', self.detail_mark)
        self.container_type = QComboBox()
        self.container_type.addItems(preparate_dict(self.new_app_types, 'container_type', with_blanc=False))
        self.container_type.setCurrentText('не выбран')
        out_form_lt.addRow('тип тары', self.container_type)
        self.pack_type = QComboBox()
        self.pack_type.addItems(preparate_dict(self.new_app_types, 'pack_type', with_blanc=False))
        self.pack_type.setCurrentText('не выбран')
        out_form_lt.addRow('тип упаковки', self.pack_type)
        self.raw_material = QComboBox()
        self.raw_material.addItems(preparate_dict(self.new_app_types, 'raw_material', with_blanc=False))
        self.raw_material.setCurrentText('не выбран')
        out_form_lt.addRow('материал', self.raw_material)
        self.main_check_lt.addLayout(out_form_lt)



        headers = ['Наименование', 'Номер_наряда', 'Операция', 'Опер_время', 'Опер_колво', 'Ед.изм']
        lst = [headers]

        table = QtWidgets.QTableWidget()
        self.table = table
        table.setHorizontalHeaderLabels(headers)

        self.main_check_lt.addWidget(table)
        for detail in detail_di['details']:
            operations = detail.get('operations')

            kw_head = {head: idx for idx, head in enumerate(headers)}
            for idx_row, (k, v) in enumerate(operations.items()):
                lst.append([k, detail['номер_наряда'], v[0], v[1], v[2], ''])
        CQT.fill_wtabl(lst, table, set_editeble_col_nomera=set(range(2, len(lst))))

        def on_select(self, text, row, col):
            self.table.item(row, col).setText(text)

        for row in range(table.rowCount()):
            CQT.add_combobox(self=self, table=table, i=row, j=kw_head.get('Ед.изм'), list=units, first_void=False,
                             conn_func=on_select)
            self.table.item(row, kw_head.get('Ед.изм')).setText(units[0])

        for detail in detail_di['details']:
            self.main_check_lt.addSpacing(30)
            form_lt1 = QFormLayout()
            # form_lt1.addRow("Примечание", QLineEdit(f"{detail['note']}"))
            self.base_detail_unit = QComboBox()
            self.base_detail_unit.addItems(units)
            self.base_detail_unit.setCurrentText('шт')

            quantity_unit_lt = QHBoxLayout()
            quantity_unit_lt.addWidget(self.base_detail_unit)
            quantity_le = QSpinBox()
            self.quantity_le = quantity_le
            quantity_le.setRange(1, 100)
            quantity_le.setValue(check_int(detail['quantity'], "количество изделий из базы"))
            quantity_unit_lt.addWidget(quantity_le)
            
            
            form_lt1.addRow("количество изделий из маршрутных карт\n(это число будет перемножено на количество в одном изделии)", quantity_unit_lt)

            self.main_check_lt.addLayout(form_lt1)
            self.num_naryads_lbl = '|'.join(str(nar) for nar in naryads)
            self.main_check_lt.addWidget(QLabel("           Операции на одно изделие"))
            form_lt2 = QFormLayout()

            # for k, v in operations.items():
            #     check_unit = QComboBox()
            #     check_unit.addItems(units.keys())
            #     check_unit.setCurrentText('шт')
            #     row_lt = QHBoxLayout()
            #     row_lt.addWidget(QLineEdit(f"{v[0]}"))
            #     dsb = QDoubleSpinBox()
            #     dsb.setDecimals(2)
            #     dsb.setMaximum(1000)
            #     dsb.setValue(check_float(v[1], 'количество изделий в базе'))
            #     row_lt.addWidget(dsb)
            #     sb = QSpinBox()
            #     sb.setValue(check_int(v[2], 'количество изделий в базе'))
            #     row_lt.addWidget(sb)
            #     row_lt.addWidget(check_unit)
            #     form_lt2.addRow(k, row_lt)

            self.main_check_lt.addLayout(form_lt2)
            

        row_buttons_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton(text='OK')
        ok_btn.clicked.connect(lambda _ : self.send_info(quantity_le.value()))
        cancel_btn = QtWidgets.QPushButton(text='Отменить')
        cancel_btn.clicked.connect(self.close)

        row_buttons_layout.addWidget(ok_btn)
        row_buttons_layout.addWidget(cancel_btn)
        
        self.main_check_lt.addLayout(row_buttons_layout)
        self.main_check_lt.addStretch(stretch=1)
        self.setLayout(self.main_check_lt)


    def send_info(self, quantity_le):
        is_ok = False
        di = {}
        lst = CQT.list_from_wtabl_c(self.table, rez_dict=True)

        di['unit'] = get_val(self.base_detail_unit)
        di['response_detail'] = utils.convert_to_bool(get_val(self.response_detail))
        di['detail_mark'] = utils.convert_to_bool(get_val(self.detail_mark))
        di['container_type'] = get_val(self.container_type)
        di['pack_type'] = get_val(self.pack_type)
        di['raw_material'] = get_val(self.raw_material)
        di['unit'] = get_val(self.base_detail_unit)
        di['quantity'] = get_val(self.quantity_le)
        # send_li = []
        
        # for index in range(self.main_check_lt.count()):
        #     form_lt = self.main_check_lt.itemAt(index)
        #     if form_lt and isinstance(form_lt, QFormLayout):
        #         lable_index = 0
        #         for row_count in range(form_lt.count()):
        #             label  = form_lt.itemAt(lable_index)
        #             h_box_lt = form_lt.itemAt(row_count)
        #
        #             if isinstance(h_box_lt, QHBoxLayout):
        #                 if h_box_lt.count() > 2:
        #                     lable_index += 2
        #                     inner_di = {}
        #                     inner_di['detail'] = get_val(label.widget())
        #                     pre_op = h_box_lt.itemAt(0)
        #                     inner_di['operation'] = get_val(pre_op.widget())
        #                     pre_time = h_box_lt.itemAt(1)
        #                     inner_di['time'] = get_val(pre_time.widget())
        #                     pre_q = h_box_lt.itemAt(2)
        #                     inner_di['quantity'] = get_val(pre_q.widget()) * quantity_le
        #                     pre_unit = h_box_lt.itemAt(3)
        #                     res = pre_unit.widget()
        #                     inner_di['unit'] = get_val(res)
        #
        #                     if inner_di['quantity'] != 0:
        #                         send_li.append(inner_di)
        #                         is_ok = True

        di['details'] = lst
        di['application_type'] = self.app_type
        di['order'] = self.order if self.order else "  "
        import refact
        import importlib
        importlib.reload(refact)
        refact.insert_application(di)
        # post_request('/outsouce/app_from_mkart', di)
        error_message("Заявка создана")
        # self.close()
        # self.input_self.get_applications()
        # self.input_self.close()



        
    # {'unit': 'шт', 'response_detail': 'не выбран', 'detail_mark': 'не выбран', 'container_type': 'не выбран', 'pack_type': 'не выбран', 'raw_material': 'не выбран', 'details': [{...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}], 'application_type_id': 1, 'order': 'ПУ00-000129 2401007'}    