from PyQt5 import QtCore, QtWidgets

import refact
import utils
from utils import preparate_dict
from subdialogs.utils import check_input_values
from utils import error_message
from subdialogs.s_11_check_new_app_dialog import CheckNewApplicationDialog

from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_Functions as F


class NewApplicationDialog(QtWidgets.QDialog):
    def __init__(self, response, get_applications):
        super().__init__()
        self.setWindowTitle("Новая заявка")
        self.setFixedSize(800, 786)
        self.get_applications = get_applications
        verticalLayout = QtWidgets.QVBoxLayout()
        self.orders = None
        self.need_wo = None
        self.right_row_num = 0
        self.pre_application = response
        self.label_app_type = QtWidgets.QLabel(text='Тип заявки')
        self.comboBox_app_type = QtWidgets.QComboBox()
        self.comboBox_app_type.addItems(preparate_dict(self.pre_application, 'application_types'))
        self.label_order = QtWidgets.QLabel(text='Заказ на производство')
        self.comboBox_order = QtWidgets.QComboBox()
        self.comboBox_order.setToolTip('Удаляем все полностью(и пробелы тоже) и вводим часть того номера который помним нажимаем Enter')
        self.comboBox_order.addItems(preparate_dict(self.pre_application, 'orders'))
        self.comboBox_order.setEditable(True)
        self.comboBox_order.lineEdit().returnPressed.connect(self.searchComboBox)
        
        self.label_material = QtWidgets.QLabel(text='Материал')
        self.comboBox_materials = QtWidgets.QComboBox()
        self.comboBox_materials.addItems(preparate_dict(self.pre_application, 'materials'))
        self.comboBox_materials.setEditable(True)
        self.comboBox_materials.lineEdit().returnPressed.connect(self.searchMaterials)

        self.label_unit = QtWidgets.QLabel(text='Единицы измерения')
        self.comboBox_unit = QtWidgets.QComboBox()
        self.comboBox_unit.addItems(preparate_dict(self.pre_application, 'units'))
        self.label_quantity = QtWidgets.QLabel(text='Количество')
        self.spinbox_quantity = QtWidgets.QSpinBox()
        self.spinbox_quantity.setMaximum(10000)
        self.detail_for_plan = QtWidgets.QLabel(text='Наименование детали по чертежу')
        self.text_detail_for_plan = QtWidgets.QTextEdit()
        self.label_second_material = QtWidgets.QLabel(text='Материал/материалы\n(если не указано в чертеже)')
        self.text_second_material = QtWidgets.QTextEdit()
        self.label_detail = QtWidgets.QLabel(text='Маркировка деталей')
        self.comboBox_detail = QtWidgets.QComboBox()
        self.comboBox_detail.addItems(preparate_dict(self.pre_application, 'detail_marks'))
        self.label_note = QtWidgets.QLabel(text='Примечание')
        self.text_note = QtWidgets.QTextEdit()

        self.easy_notify = QtWidgets.QCheckBox(text="оповещение в битрикс")
        verticalLayout.addWidget(self.label_app_type)
        verticalLayout.addWidget(self.comboBox_app_type)
        
        
        self.tabs = QtWidgets.QTabWidget() 
        with_order_tab = QtWidgets.QWidget()  # c заказом на производство
        self.with_order_layout = QtWidgets.QVBoxLayout()
        get_order_btn = QtWidgets.QPushButton(text='Получить заказы на производство')
        get_order_btn.clicked.connect(self.get_orders)

        self.orders_spin = QtWidgets.QComboBox()
        self.orders_spin.setEditable(True)
        view_order_label = QtWidgets.QPushButton(text='Получить наряды по заказу на производство')
        view_order_label.clicked.connect(self.get_wo_per_order)

        self.with_order_layout.addWidget(get_order_btn)
        self.with_order_layout.addWidget(self.orders_spin)
        self.with_order_layout.addWidget(view_order_label)

        self.with_order_layout.addStretch(stretch=1)
        with_order_tab.setLayout(self.with_order_layout)
        
        without_wo_tab = QtWidgets.QWidget()  # без наряда
        with_out_order = QtWidgets.QVBoxLayout()
        with_out_order.addWidget(self.label_order)
        with_out_order.addWidget(self.comboBox_order)
        with_out_order.addWidget(self.label_material)
        with_out_order.addWidget(self.comboBox_materials)
        with_out_order.addWidget(self.label_unit)
        with_out_order.addWidget(self.comboBox_unit)
        with_out_order.addWidget(self.label_quantity)
        with_out_order.addWidget(self.spinbox_quantity)
        with_out_order.addWidget(self.detail_for_plan)
        with_out_order.addWidget(self.text_detail_for_plan)
        with_out_order.addWidget(self.label_second_material)
        with_out_order.addWidget(self.text_second_material)
        with_out_order.addWidget(self.label_detail)
        with_out_order.addWidget(self.comboBox_detail)
        with_out_order.addWidget(self.label_note)
        with_out_order.addWidget(self.text_note)
        without_wo_tab.setLayout(with_out_order)


        with_wo_tab = QtWidgets.QWidget()
        with_wo_lt = QtWidgets.QVBoxLayout()
        with_wo_all_orders_btn = QtWidgets.QPushButton("Получить все незавершенные наряды с пометкой на аутсорс")
        with_wo_all_orders_btn.clicked.connect(self.get_wo_autsorce)
        with_wo_lt.addWidget(with_wo_all_orders_btn)
        

        

        with_wo_lt.addStretch(stretch=1)

        with_wo_tab.setLayout(with_wo_lt)
        


        self.tabs.addTab(with_order_tab, 'Из заказов на прозиводство')
        self.tabs.addTab(with_wo_tab, 'Из наряда на аутсорс')
        self.tabs.addTab(without_wo_tab, 'Без наряда')
        self.tabs.currentChanged.connect(self.changeMainTabs)

        verticalLayout.addWidget(self.tabs)
        verticalLayout.addWidget(self.init_choose_lt())
        verticalLayout.addWidget(self.easy_notify)

        buttonsLayout = QtWidgets.QHBoxLayout()
        btn_create = QtWidgets.QPushButton(text='Создать заявку', default=False, autoDefault=False)
        btn_create.setStatusTip('Заявка будет создана в базе')
        btn_create.clicked.connect(self.save_application)
        btn_cancel = QtWidgets.QPushButton(text='Отменить', default=False, autoDefault=False)
        btn_cancel.setStatusTip('Данных этой заявки не сохранится')
        btn_cancel.clicked.connect(self.close)
        buttonsLayout.addWidget(btn_create)
        buttonsLayout.addWidget(btn_cancel)


        verticalLayout.addLayout(buttonsLayout)
        # verticalLayout.addWidget(self.init_choose_lt())
        self.setLayout(verticalLayout)


    def changeMainTabs(self, index):
        print(index)
        if self.tabs.currentIndex()<2:
            self.base_choose_wdt.setVisible(True)
        else:
            self.base_choose_wdt.setVisible(False)


    def save_application(self):
        
        if self.tabs.currentIndex() < 2:  # c нарядом
            application = {}
            cur_order = self.orders_spin.currentText()
            application['production_order'] = cur_order
            naryads = []
            for num in range(self.right_elems.count()):
                # orders.append(cur_order)

                raw_wo = self.right_elems.item(num).text()
                wo_num = int(raw_wo.split(' ')[0])
                naryads.append(wo_num)
                wo = self.need_wo.get(wo_num)
                application['name'] = wo.get('Номенклатура')

                detail = {}
                detail['note'] = wo.get('Примечание') + wo.get('Задание')
                detail['quantity'] = wo.get('Количество')
                detail['номер_наряда'] = wo_num

                operations = {}
                if '|' in wo['Операции']:
                    pre_op = wo['Операции'].split('|')
                    pre_dse = wo['ДСЕ'].split('|')
                    pre_dse = [dse.replace("$", ' ') for dse in pre_dse]
                    operations_li = [val.split('$')[1] for val in pre_op]
                    operations_time = wo.get('Опер_время')
                    if operations_time:
                        operations_time = operations_time.split('|')

                    operations_quantity = wo.get('Опер_колво')
                    if operations_quantity:
                        operations_quantity = operations_quantity.split('|')
                    for index in range(len(operations_li)):
                        operations[pre_dse[index]] = (operations_li[index], float(operations_time[index] if operations_time else 0), int(operations_quantity[index] if operations_quantity else 0))
                else:
                    sub_res = wo['Операции'].split('$')[1]
                    sub_dse = wo['ДСЕ'].replace('$', ' ')
                    operations[sub_dse] = (sub_res, wo.get('Опер_время'), wo.get('Опер_колво'))

                detail['operations'] = operations
                if not application.get('details'):
                    application['details'] = []
                application['details'].append(detail)

            if application:
                if self.comboBox_app_type.currentText() == ' ':
                    error_message('не задан тип заявки')
                elif self.right_elems.count() == 0:
                    error_message('не добавлены заявки')
                else:
                    cd = CheckNewApplicationDialog(self, application, self.pre_application, self.comboBox_app_type.currentText(), naryads)
                    cd.exec()

        else:  # без наряда
            di = {}
            # оповещение битрикс
            di['is_notify'] = self.easy_notify.isChecked()
            # Тип заявки application_types
            di['application_type_id'] = check_input_values(self.comboBox_app_type, self.label_app_type, self.pre_application['application_types'])
            # чекбокс заказов на производство "Номер_проекта Номерзаказа"
            di['production_order'] = check_input_values(self.comboBox_order, self.label_order, self.pre_application['orders'])

            di['matherial_id'] = check_input_values(self.comboBox_materials, self.label_material, self.pre_application['materials'])
            # di['unit_id'] = check_input_values(self.comboBox_unit, self.label_unit, self.pre_application['units'])
            di['unit'] = utils.get_val(self.comboBox_unit)
            di['quantity'] = check_input_values(self.spinbox_quantity, self.label_quantity)
            di['matherial_not_plan'] = None if self.text_second_material.toPlainText() == '' else self.text_second_material.toPlainText()
            di['detail_mark'] = utils.convert_to_bool(utils.get_val(self.comboBox_unit))
            di['note'] = None if self.text_note.toPlainText() == '' else self.text_note.toPlainText()
            di['detail_for_plan'] = None if self.text_detail_for_plan.toPlainText() == '' else self.text_detail_for_plan.toPlainText()

            if di['application_type_id'] and di['production_order'] and di['matherial_id'] and di['unit'] and di['quantity']:
                refact.insert_application(di)


    def searchComboBox(self):
        text = self.comboBox_order.currentText()
        index = self.comboBox_order.findText(text, flags=QtCore.Qt.MatchFlag.MatchContains )
        if index != -1:
            self.comboBox_order.setCurrentIndex(index)
            self.comboBox_order.lineEdit().setSelection(len(text), len(self.comboBox_order.currentText()))

    def searchMaterials(self):
        text = self.comboBox_materials.currentText()
        index = self.comboBox_materials.findText(text, flags=QtCore.Qt.MatchFlag.MatchContains )
        if index != -1:
            self.comboBox_materials.setCurrentIndex(index)
            self.comboBox_materials.lineEdit().setSelection(len(text), len(self.comboBox_materials.currentText()))

    def searchOrders(self):
        text = self.orders_spin.currentText()
        index = self.orders_spin.findText(text, flags=QtCore.Qt.MatchFlag.MatchContains )
        if index != -1:
            self.orders_spin.setCurrentIndex(index)
            self.orders_spin.lineEdit().setSelection(len(text), len(self.orders_spin.currentText()))


    def get_orders(self):
        stmt = """SELECT printf('%s %s', Номер_проекта, Номер_заказа) as конк_заказ_проект, mk.* FROM mk ORDER BY Пномер DESC"""
        res = CSQ.custom_request_c(F.scfg('Naryad'), stmt, rez_dict=True)
        if res:
            self.orders = F.deploy_dict_c(res, 'конк_заказ_проект')
            self.orders_spin.addItems(self.orders.keys())

    def get_wo_per_order(self):
        checked_text = self.orders_spin.currentText()
        if not self.orders:
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle("ошибка")
            msg.setText(f'Получите наряды {checked_text}')

        elif not self.orders.get(checked_text):
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle("ошибка")
            msg.setText(f'введено неверноне название номеглатуры {checked_text}')
            msg.exec()
        else:
            nomenglature_name = check_input_values(self.orders_spin, "не задан номенклатурный номер")
            num = self.orders.get(nomenglature_name)['Пномер']
            stmt = f"""
                SELECT mk.Номенклатура, mk.Вес, mk.Количество, 
                    mk.Номенклатура, naryad.Задание, naryad.ДСЕ, 
                    naryad.Операции, naryad.Опер_время, naryad.Опер_колво, 
                    naryad.Номер_мк, naryad.Примечание, naryad.Пномер  
                FROM naryad 
                join mk on mk.Пномер=naryad.Номер_мк 
                WHERE naryad.Номер_мк={num}"""
            res = F.deploy_dict_c(CSQ.custom_request_c(F.scfg('Naryad'), stmt, rez_dict=True), 'Пномер')
            if res:
                if self.need_wo:
                    self.need_wo.update(res)
                else:
                    self.need_wo = res
                self.work_choose_lt()
            # {'707': {'Задание': 'Шумоглушитель ШПС.2203029.03 (1 шт.) - 77 мин.    ; СТО-ОП7-1-2021; ПЗ-И-001; № ОП6; LF    025 Контроль(формы и расположения поверхностей)LF        Контроль ОТК, установить клеймо контролера ОТК, по результату приемочного контроляLFLF', 'ДСЕ': 'Шумоглушитель$ШПС.2203029.03', 'Операции': '025$Контроль(формы и расположения поверхностей)'}}
    
    def get_wo_autsorce(self):
        stmt = """
            SELECT 
                naryad.Пномер, naryad.Задание, naryad.ДСЕ, 
                mk.Номенклатура, 
                naryad.Операции, naryad.Номер_мк, naryad.Примечание 
            FROM naryad 
            join jurnal on jurnal.Номер_наряда=naryad.Пномер 
            join mk on mk.Пномер=naryad.Номер_мк 
            WHERE Аутсорсинг=1 and not jurnal.Статус=='Завершен'
            """
        res = F.deploy_dict_c(CSQ.custom_request_c(F.scfg('Naryad'), stmt, rez_dict=True), 'Пномер')
        if res:
            if self.need_wo:
                self.need_wo.update(res)
            else:
                self.need_wo = res
            self.work_choose_lt()
        

    def init_choose_lt(self):
        self.base_choose_wdt = QtWidgets.QWidget()
        self.base_choose_wdt.setFixedHeight(300)
        self.base_choose_lt = QtWidgets.QVBoxLayout()
        # self.souce_choose_lt = QtWidgets.QVBoxLayout()
        # self.dist_choose_lt = QtWidgets.QVBoxLayout()
        self.between_btns_lt = QtWidgets.QVBoxLayout()
        
        naming_lt = QtWidgets.QHBoxLayout()
        naming_lt.addWidget(QtWidgets.QLabel("Исходные наряды"), alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        naming_lt.addWidget(QtWidgets.QLabel("Наряды уходящие в заявку"), alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.left_elems = QtWidgets.QListWidget(self)
        self.right_elems = QtWidgets.QListWidget(self)
        self.left_elems.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)     # - DragDrop, + InternalMove
        self.right_elems.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DropOnly)

        
        self.choose_li = QtWidgets.QHBoxLayout()
        self.choose_li.addWidget(self.left_elems)
        self.choose_li.addWidget(self.right_elems)
        
        to_right_btn = QtWidgets.QPushButton("Добавить в заявку")
        # to_right_btn.setFixedSize(180, 30)
        to_right_btn.clicked.connect(self.to_right_clicked)
        

        clean_left_btn = QtWidgets.QPushButton("Очистить исходные")
        # clean_left_btn.setFixedSize(180, 30)
        clean_left_btn.clicked.connect(self.left_elems.clear)


        clean_right_btn = QtWidgets.QPushButton("Очистить в заявке")
        # clean_right_btn.setFixedSize(180, 30)
        clean_right_btn.clicked.connect(self.right_elems.clear)
        
        

        self.base_choose_lt.addLayout(naming_lt)
        self.base_choose_lt.addLayout(self.choose_li)

        wo_buttons_lt = QtWidgets.QHBoxLayout()
        wo_buttons_lt.addWidget(clean_left_btn)

        wo_buttons_lt.addWidget(clean_left_btn,  alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        wo_buttons_lt.addWidget(to_right_btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        wo_buttons_lt.addWidget(clean_right_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        # wo_buttons_lt.setStretchFactor(clean_left_btn, 1)
        # wo_buttons_lt.setStretchFactor(to_right_btn, 1)
        # wo_buttons_lt.setStretchFactor(clean_right_btn, 1)





        self.base_choose_lt.addLayout(wo_buttons_lt)

        self.base_choose_wdt.setLayout(self.base_choose_lt)
        return self.base_choose_wdt

    def to_right_clicked(self):
        item = self.left_elems.currentItem()
        if item:
            self.right_elems.insertItem(self.right_row_num, item.text())
            self.right_row_num += 1

    def work_choose_lt(self):
        self.row_num = 0
        for wo_num, di in self.need_wo.items():
            self.left_elems.insertItem(self.row_num, f"{wo_num} {di['Задание']}")
            self.row_num += 1

    # def mouseDoubleClickEvent(self, a0: QMouseEvent | None) -> None:
    #     print(a0)
    #     return super().mouseDoubleClickEvent(a0)
    # # def clean_left_application(self):
    #     self.left_elems.clear()

        # {'32438': {'Задание': 'Экран КТ.2303006.01.04 (1 шт.) - 17.5 мин.    ; СТО-ОП7-1-2021; ПЗ-И-001; № ОП6; ТТПС; ; LF    045 Контроль(формы и расположения поверхностей)LF        Согласно требованиям ТИПОВОГО ТЕХНОЛОГИЧЕСКОГО ПРОЦЕССА ТТПС – МП-М01/М02/М11-КО п. 12; Контроль ОТК - контроль зачистных работ, установить клеймо контролера ОТК, по результату приемочного контроляLFLFФланец прижимной КТ.2303006.01.03 (2 шт.) - 13.56 мин.    ; СТО-ОП7-1-2021; ПЗ-И-001; № ОП6; ТТПС; ; LF    045 Контроль(формы и расположения поверхностей)LF        Согласно требованиям ТИПОВОГО ТЕХНОЛОГИЧЕСКОГО ПРОЦЕССА ТТПС – МП-М01/М02/М11-КО п. 12; Контроль ОТК - контроль зачистных работ, установить клеймо контролера ОТК, по результату приемочного контроляLFLFПатрубок КТ.2303006.01.02 (1 шт.) - 20.2 мин.    ; СТО-ОП7-1-2021; ПЗ-И-001; № ОП6; ТТПС; ; LF    045 Контроль(формы и расположения поверхностей)LF        Согласно требованиям ТИПОВОГО ТЕХНОЛОГИЧЕСКОГО ПРОЦЕССА ТТПС – МП-М01/М02/М11-КО п. 12; Контроль ОТК - контроль зачистных работ, установить клеймо контролера ОТК, по результату приемочного контроляLFLF', 'ДСЕ': 'Экран$КТ.2303006.01.04|Фланец прижимной$КТ.2303006.01.03|Патрубок$КТ.2303006.01.02', 'Операции': '045$Контроль(формы и расположения поверхностей)|045$Контроль(формы и расположения поверхностей)|045$Контроль(формы и расположения поверхностей)', 'Номер_мк': 2952}}
# class DragAndDropListWidget(QListWidget):
#     def __init__(self, parent=None):
#         super(DragAndDropListWidget, self).__init__(parent)
#         self.setAcceptDrops(True)
#         self.setDragEnabled(True)
#         self.setDropIndicatorShown(True)

#     def startDrag(self, index):
#         item = self.takeItem(index.row())
#         drag = QDrag(self)
#         mime = QMimeData()
#         mime.setText(item.text())
#         drag.setMimeData(mime)
#         drag.exec(Qt.CopyAction)

#     def dragEnterEvent(self, event):
#         if event.mimeData().hasText():
#             event.acceptProposedAction()
#         else:
#             event.ignore()

#     def dropEvent(self, event):
#         position = event.pos()
#         item = QListWidgetItem(event.mimeData().text())
#         self.insertItem(position.row(), item)