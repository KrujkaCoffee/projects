from PyQt5 import QtWidgets, QtCore

import connectors_1c
import refact
from subdialogs.s_2_1_materials import UpdMaterials
from subdialogs.s_2_2_timing import UpdTiming
from subdialogs.s_2_3_docs import UpdDocs
from subdialogs.s_3_find_provider import UpdProvider
from subdialogs.s_4_agreement import Agreement
from subdialogs.s_5_order_after_agree import OrderPost
from subdialogs.s_6_otk import OtkPost
from subdialogs.s_7_to import ToPost
from subdialogs.s_8_rework import Rework
from subdialogs.s_9_fact_ready_date import FactReadyDate
from subdialogs.s_10_fact_provider_ready_date import FactProviderReadyDate
from utils import create_excel, create_pdf, strip_list


class OneApp(QtWidgets.QDialog):
    def __init__(self, app_data, parent):
        super().__init__()
        self.journal = refact.get_journal(app_data['number'])
        self.parent_widget = parent
        self.app_data = app_data
        self.setMinimumSize(QtCore.QSize(900, 800))
        main_layout = QtWidgets.QHBoxLayout()
        btn_layout = QtWidgets.QVBoxLayout()
        excel_btn = QtWidgets.QPushButton('Выгрузить в Excel')
        excel_btn.clicked.connect(lambda: create_excel(parent, self.app_data, check_hidden=False))
        pdf_btn = QtWidgets.QPushButton('Выгрузить в Pdf')
        pdf_btn.clicked.connect(lambda: create_pdf(self, is_one_app=self.app_data, is_for_provider=False))
        fact_redy_date_btn = QtWidgets.QPushButton(text='Фактическая дата готовности')
        fact_redy_date_btn.clicked.connect(self.fact_ready_date)
        fact_provider_redy_date_btn = QtWidgets.QPushButton(text='Фактическая дата готовности от поставщика')
        fact_provider_redy_date_btn.clicked.connect(self.fact_provider_ready_date)
        # load_erp_files = QtWidgets.QPushButton('Сохранить файлы из к заявке из ERP(пока не реализовано)')

        btn_layout.addWidget(excel_btn)
        btn_layout.addWidget(pdf_btn)
        btn_layout.addWidget(fact_redy_date_btn)
        btn_layout.addWidget(fact_provider_redy_date_btn)
        # btn_layout.addWidget(load_erp_files)

        # if self.app_data.get("stage") == 'Указание документов, сроков и материалов':
        self.add_materials = QtWidgets.QPushButton(text='Добавить материалы')
        self.add_materials.clicked.connect(self.upd_materials)
        btn_layout.addWidget(self.add_materials)

        self.add_timing = QtWidgets.QPushButton(text='Внесение данных по срокам')
        self.add_timing.clicked.connect(self.upd_timing)
        btn_layout.addWidget(self.add_timing)

        self.add_docs = QtWidgets.QPushButton(text='Внесение данных по документам')
        self.add_docs.clicked.connect(self.upd_docs)
        btn_layout.addWidget(self.add_docs)

        # if self.app_data.get('stage_timing'):
        #     self.add_timing.setEnabled(False)

        # if self.app_data.get('stage_docs'):
        #     self.add_docs.setEnabled(False)
                

        if self.app_data.get("stage") == 'Поиск поставщика':
            self.add_provider = QtWidgets.QPushButton(text='Внесение данных поставщика')
            self.add_provider.clicked.connect(self.upd_provider)
            btn_layout.addWidget(self.add_provider)


        elif self.app_data.get("stage") == 'Согласование':
            self.add_agreement = QtWidgets.QPushButton(text='Согласование')
            self.add_agreement.clicked.connect(self.upd_agreement)
            btn_layout.addWidget(self.add_agreement)

            

        elif self.app_data.get("stage") == 'Размещение заказа поставщику':
            self.add_provider_order = QtWidgets.QPushButton(text='Размещение заказа поставщику')
            self.add_provider_order.clicked.connect(self.upd_provider_order)
            btn_layout.addWidget(self.add_provider_order)


        elif self.app_data.get("stage") == 'Приемка ОТК':
            self.add_acceptance = QtWidgets.QPushButton(text='Внесение статуса приемки ОТК')
            self.add_acceptance.clicked.connect(self.upd_acceptance)
            btn_layout.addWidget(self.add_acceptance)


        elif self.app_data.get("stage") == 'Приемка ТО':
            self.add_to_acceptance = QtWidgets.QPushButton(text='Внесение статуса приемки ТО')
            self.add_to_acceptance.clicked.connect(self.upd_to)
            btn_layout.addWidget(self.add_to_acceptance)


        elif self.app_data.get("stage") == 'Доработка':
            self.rework = QtWidgets.QPushButton(text='Внесение статуса доработки')
            self.rework.clicked.connect(self.upd_rework)
            btn_layout.addWidget(self.rework)
            if self.app_data.get('rework_status'):
                self.rework.setEnabled(False)

            btn_layout.addStretch(stretch=1)


        self.app_number = self.app_data['number']

        right_layout = QtWidgets.QVBoxLayout()

        # if self.app_data:
        self.setWindowTitle(f"заявка номер {self.app_number}")
        right_layout.addWidget(QtWidgets.QLabel(text=f'Заявка № {self.app_data["number"]} от {self.app_data["creation_date"]}'))
        right_layout.addWidget(QtWidgets.QLabel(text=f'Текущая стадия {self.app_data["stage"]}'))
        right_layout.addWidget(QtWidgets.QLabel(text=f'Текущий статус {self.app_data["status"]}'))

        # стадия создания заявки
        right_layout.addWidget(QtWidgets.QLabel(text=f'Тип заявки {self.app_data["application_type"]}'))
        right_layout.addWidget(QtWidgets.QLabel(text=f'Требуется ли маркировка деталей {self.app_data["detail_mark"]}'))
        right_layout.addWidget(QtWidgets.QLabel(text=f'Заказ номер {self.app_data["production_order"]}'))
        if self.app_data["matherial_not_plan"]:
            right_layout.addWidget(QtWidgets.QLabel(text=f'Материал {self.app_data["matherial"]}({self.app_data["matherial_not_plan"]}) {self.app_data["quantity"] if self.app_data["quantity"] else ""} '))  # {self.app_data["unit"]}
        else:
            right_layout.addWidget(QtWidgets.QLabel(text=f'Материал {self.app_data["matherial"]} {self.app_data["quantity"] if self.app_data["quantity"] else ""}'))  #  {self.app_data["unit"]}
        btn_layout.addWidget(QtWidgets.QLabel(text=f'Создатель заявки: {self.app_data["applicant"]}'))
        if self.app_data["note_new_app"]:
            right_layout.addWidget(QtWidgets.QLabel(text=f'Заметки {self.app_data["note_new_app"]}'))
        right_layout.addWidget(QtWidgets.QLabel(text=f'Дата создания заявки {strip_list(self.app_data["creation_date"])}'))

        if self.app_data.get('stage_materials'):
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Внесение материалов: {strip_list(self.app_data["add_material_creation_date"])}  {strip_list(self.app_data["add_material_user"], is_date=False)}'))

        if action := self.journal.get('Внесение сроков'):
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Внесение сроков: {action['created_at']} {action['ФИО']}'))

        if action := self.journal.get('Внесение документов'):
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Внесение документов {action['created_at']} {action['ФИО']}'))

        if action := self.journal.get('Указание информации о поставщике'):
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Указание информации о поставщике {action['created_at']} {action['ФИО']}'))


        if ref_key := self.app_data.get('st_provider/Ref_Key'):
            right_layout.addWidget(QtWidgets.QLabel(text=f'Поставщик {parent.DICT_PARTNERS[ref_key]['name']}'))
            # right_layout.addWidget(QtWidgets.QLabel(text=f'Контакты поставщика {self.app_data["provider_contact"]}'))
            # btn_layout.addWidget(QtWidgets.QLabel(text=f'Закупщик {self.app_data["byer"]}'))


        if action := self.journal.get('Согласование'):
            right_layout.addWidget(QtWidgets.QLabel(text=f'Согласование {strip_list(self.app_data["agree_stage_creation_date"])} {self.app_data["agree"]}'))
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Согласовавший поставщика {action['created_at']} {action['ФИО']}'))


        if action := self.journal.get('Внесение статуса ОТК'):
            right_layout.addWidget(QtWidgets.QLabel(text=f'Требуется ли контроль ОТК {self.app_data["otk_control"]}'))
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Внесение статуса ОТК  {action['created_at']} {action['ФИО']}'))

        if action := self.journal.get('Внесение статуса ТО'):
            right_layout.addWidget(QtWidgets.QLabel(text=f'Требуется ли контроль ТО {self.app_data["to_control"]}'))
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Внесение статуса ТО  {action['created_at']} {action['ФИО']}'))

        if action := self.journal.get('Внесение статуса переработки'):
            right_layout.addWidget(QtWidgets.QLabel(text=f'Требуется ли контроль переработки {self.app_data["rework_control"]}'))
            btn_layout.addWidget(QtWidgets.QLabel(text=f'Внесение статуса переработки  {action['created_at']} {action['ФИО']}'))

        btn_layout.addStretch(stretch=1)
        right_layout.addStretch(stretch=1)
        main_layout.addLayout(btn_layout, 1)
        main_layout.addLayout(right_layout, 3)
        self.setLayout(main_layout)
    

    def upd_materials(self):
        response = refact.get_materials_st()
        if response:
            dlg = UpdMaterials(self.app_number, response)
            dlg.exec()
            di = {}
            di['app_num'] = self.app_number
            # TODO пытается взять свежую версию
            self.parent_widget.refresh_applications(self.app_number)

    def upd_timing(self):
        response = {'type_material': [{'id': 1, 'name': 'Давальческое'}, {'id': 2, 'name': 'Поставщика'}]}
        if response:
            dlg = UpdTiming(self.app_number, response)
            dlg.exec()
            di = {}
            di['app_num'] = self.app_number
            self.parent_widget.refresh_applications(self.app_number)


    def upd_docs(self):
        response = {'check_place': [{'id': 1, 'name': 'На стороне исполнителя'}, {'id': 2, 'name': 'На территории заказчика'}]}
        if response:
            dlg = UpdDocs(self.app_number, response)
            dlg.exec()
            di = {}
            di['app_num'] = self.app_number
            self.parent_widget.refresh_applications(self.app_number)

    def upd_provider(self):
        response = connectors_1c.get_partners_from_1s()
        if response:
            dlg = UpdProvider(self.app_number, response)
            dlg.exec()
            self.parent_widget.refresh_applications(self.app_number)

    def upd_agreement(self):
        response = {'agreements': [{'id': 1, 'name': 'Да'}, {'id': 2, 'name': 'Нет'}, {'id': 3, 'name': 'не выбран'}]}
        if response:
            dlg = Agreement(self.app_number, response)
            dlg.exec()
            self.parent_widget.refresh_applications(self.app_number)

    def upd_provider_order(self):
        dlg = OrderPost(application_num=self.app_number)
        dlg.exec()
        self.parent_widget.refresh_applications(self.app_number)

    def upd_acceptance(self):
        response = [{'id': 1, 'name': 'Да'}, {'id': 2, 'name': 'Нет'}, {'id': 3, 'name': 'С замечаниями'}]
        dlg = OtkPost(self.app_number, response)
        dlg.exec()
        self.parent_widget.refresh_applications(self.app_number)

    def upd_rework(self):
        response = {'to_control': [{'id': 1, 'name': 'Да'}, {'id': 2, 'name': 'Нет'}, {'id': 3, 'name': 'не выбран'}]}
        if response:
            dlg = Rework(self.app_number, response)
            dlg.exec()
            self.parent_widget.refresh_applications(self.app_number)

    def upd_to(self):
        response = {'to_control': [
            {'id': 1, 'name': 'Да'},
            {'id': 2, 'name': 'Нет'},
            {'id': 3, 'name': 'С замечаниями'},
            {'id': 4, 'name': 'Не нужен'},
            {'id': 5, 'name': 'Доработка поставщиком'}
        ]}
        dlg = ToPost(self.app_number, response)
        dlg.exec()
        self.parent_widget.refresh_applications(self.app_number)

    def fact_ready_date(self):
        dlg = FactReadyDate(self.app_number)
        dlg.exec()



    def fact_provider_ready_date(self):
        dlg = FactProviderReadyDate(self.app_number)
        dlg.exec()

