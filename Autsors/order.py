import copy
from datetime import datetime
from dataclasses import dataclass, field, asdict

from PyQt5 import QtWidgets, QtGui, QtCore
import requests

from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_odata_erp as COE
from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_Qt as CQT



class NotFoundRequiredParameterForERP(Exception): ...


def make_client_1c_reference(ref_key: str) -> str:
    ref_splitted = ref_key.split('-')
    return ''.join((ref_splitted[3], ref_splitted[4], ref_splitted[2], ref_splitted[1], ref_splitted[0]))

def make_reference_on_erp_entity(domain: str, base_name: str, nomen_endpoint: str, ref_key_odata: str):
    prepared_ref_key = make_client_1c_reference(ref_key_odata)
    return f'e1c://server/{domain}/{base_name}#e1cib/data/{nomen_endpoint}?ref={prepared_ref_key}'


class Property1C:
    __SELECT_TEMPLATE = '$select={kw}'
    __FILTER_TEMPLATE = '$filter={kw}'
    __FORMAT = '$format=json'

    __URL_POSTFIX = '/odata/standard.odata/'

    def __init__(self, *, select, doc_name: str, alias: str, **kwargs):
        self.__filter = self.make_filter_params_by_key_words(kwargs)
        self.__select = self.make_select_params_by_key_words(select)
        self.base_url = 'http://srv-1c:8088'
        # self.base_url = CFG.Config.project.ERB_BASE_URL
        self.doc_name = doc_name
        self.base_name = 'ERP'
        self.alias = alias
        # self.base_name = CFG.usr

        self.url = self.make_url()
        self.Description = ''
        self.Ref_Key = ''
        self.request_data()
        self.gui_reference = self.make_gui_reference()

    def request_data(self):
        import requests
        response = requests.get(self.url, auth=('OdataZNP', 'znp'))
        if response.ok and 'application/json' in response.headers['Content-Type']:
            converted_data = response.json()
            if 'value' in converted_data:
                for item in converted_data['value']:
                    for key, value in item.items():
                        self.__dict__[key] = value
                    return

    def make_url(self):
        lst_params = (self.__select, self.__filter, self.__FORMAT)
        params = '&'.join(param for param in lst_params if param)
        return f'{self.base_url}/{self.base_name}/{self.__URL_POSTFIX}/{self.doc_name}?{params}'

    def make_select_params_by_key_words(self, select: list[str]):
        if not isinstance(select, (list, tuple)) or len(select) == 0:
            return ''
        return self.__SELECT_TEMPLATE.format(kw=','.join(key for key in select))

    def prepare_value(self, key, value):
        if key == 'Ref_Key':
            return f'guid{value!r}'
        return repr(value)

    def make_filter_params_by_key_words(self, key_words: dict):
        if not isinstance(key_words, dict) or len(key_words) == 0:
            return ''
        return self.__FILTER_TEMPLATE.format(kw=','.join(f'{key} eq {self.prepare_value(key, value)}' for key, value in key_words.items()))

    def make_gui_reference(self):
        ...

@dataclass
class BaseOrder:
    ЖелаемаяДатаПоступления: str
    Подразделение_Key: str = "b7f31b2d-2297-11eb-8453-b42e99cc2e43"
    Автор_Key: str = "070496bf-10bb-11ec-8460-00d861dd2b4a"

    # Автор_Type: str = "StandardODATA.Catalog_Пользователи"
    Статус: str = "НеСогласован"
    Приоритет_Key: str = "e566b370-019f-11e7-80c0-4ccc6a67082d"
    Организация_Key: str = field(init=False)
    Партнер_Key: str =  "92ed7c6a-47e6-11ea-842b-00d861129db6"
    Контрагент_Key: str =  "ac2dcf99-47e6-11ea-842b-00d861129db6"
    Договор_Key: str =  "d71917c7-47e6-11ea-842b-00d861129db6"

    НалогообложениеНДС: str = "ПродажаОблагаетсяНДС"
    ЗакупкаПодДеятельность: str = "ПродажаОблагаетсяНДС"

    Комментарий: str = ""
    ДополнительнаяИнформация: str = ""
    Менеджер_Key: str = "070496bf-10bb-11ec-8460-00d861dd2b4a"
    Валюта_Key: str = "cf2a82f0-019f-11e7-80c0-4ccc6a67082d"

    # _preview: dict = field(init=False, repr=False)


    def __post_init__(self):
        self.Организация_Key = Property1C(
            select=('Description', 'Ref_Key'),
            doc_name='Catalog_Организации',
            alias='Организация',
            Ref_Key=CFG.Config.place.Организация_Key
        )

        if self.Организация_Key is None:
            raise NotFoundRequiredParameterForERP()

    def as_dict(self):
        dirt_data = asdict(self)
        body = {}
        for key_main, value in dirt_data.items():
            cleaned_value = value
            if isinstance(value, Property1C):
                cleaned_value = value.Ref_Key
            if isinstance(value, list):
                cleaned_value = []
                for item in value:
                    cur_dic = {}
                    for key, val in item.items():
                        if isinstance(val, Property1C):
                            val = val.Ref_Key
                        cur_dic[key] = val
                    cleaned_value.append(cur_dic)
            body[key_main] = cleaned_value
        return body

@dataclass
class OrderSupplier(BaseOrder):
    Date: str = field(init=False)
    ХозяйственнаяОперация: str = "ЗакупкаУПоставщика"
    ГруппаФинансовогоУчета_Key: str = "bd2de41a-4603-11e7-80c2-4ccc6a67082d"

    МаксимальныйКодСтроки: str = "4"
    ОбъектРасчетов_Key: str = "6d1f4361-097d-11f0-a3ad-30e1716be59f"

    Склад_Key: str = "1a4f5d38-fb17-11e9-80e9-4ccc6a67082d"

    Соглашение_Key: str = "16c4f97b-1a4e-11ee-84a1-00d861dd2b4a"
    # Автор_Key: str = "57ff083e-6439-11ee-84c4-00d861dd2b4a"
    ПоступлениеОднойДатой: bool = True
    ПорядокРасчетов: str = "ПоЗаказам"
    СпособДоставки: str = "СиламиПоставщикаДоНашегоСклада"

    Товары: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.Date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    def append_Товары(
            self,
            Номенклатура_Key: str = "fe9d5f44-aaf0-11ef-85cb-00d861dd2b4a",
            Характеристика_Key: str = "00000000-0000-0000-0000-000000000000",
            Упаковка_Key: str = "00000000-0000-0000-0000-000000000000",
            Количество: int | float = 2
    ):
        count = str(len(self.Товары) + 1)
        self.Товары.append({
            "Номенклатура_Key": Номенклатура_Key,
            "Характеристика_Key": Характеристика_Key,
            "Упаковка_Key": Упаковка_Key,
            "КоличествоУпаковок": Количество,
            "Количество": Количество,
            "LineNumber": count,
            "КодСтроки": count,
            "Цена": 1,
            "Сумма": 1,
            "Склад_Key": self.Склад_Key,
            "СтавкаНДС_Key": "5e490d31-e68d-11ed-8482-00d861dd2b4a",
        })

@dataclass
class OrderRecycler(BaseOrder):
    ХозяйственнаяОперация: str = 'ПроизводствоУПереработчика2_5'
    ГруппировкаЗатрат: str = "БезГруппировки"
    # УслугиПоПереработке: str =  "УказываютсяВЗаказеОтчете"
    СпособДоставки: str = "Самовывоз"
    Назначение_Key: str = "eab8e737-dc9a-11ef-85ff-00d861dd2b4a"
    НазначениеПередачи_Key: str = "eab8e737-dc9a-11ef-85ff-00d861dd2b4a"
    МаксимальныйНомерГруппыЗатрат: str = "1"
    СкладПродукции_Key: str = Property1C(Ref_Key="84c6c4d4-298f-11e7-80c0-4ccc6a67082d", select=('Description', 'Ref_Key'), doc_name='Catalog_Склады', alias='СкладПродукции') # http://srv-1c:8088/ERP/odata/standard.odata/Catalog_Склады?$format=json&$filter=Ref_Key%20eq%20guid%271a4f5d38-fb17-11e9-80e9-4ccc6a67082d%27
    СкладМатериалов_Key: str = Property1C(Ref_Key="84c6c4d4-298f-11e7-80c0-4ccc6a67082d", select=('Description', 'Ref_Key'), doc_name='Catalog_Склады', alias='СкладМатериалов') # http://srv-1c:8088/ERP/odata/standard.odata/Catalog_Склады?$format=json&$filter=Ref_Key%20eq%20guid%271a4f5d38-fb17-11e9-80e9-4ccc6a67082d%27

    ПорядокРасчетов: str = "ПоЗаказам"
    ГруппаФинансовогоУчета_Key: str = "bc077c89-e4c0-11e7-80cd-4ccc6a67082d"
    ФормаОплаты: str = "Безналичная"
    ОбъектРасчетов_Key: str = "2538590a-dd6b-11ef-8600-00d861dd2b4a"
    СпособРаспределенияЗатратНаВыходныеИзделия: str = "ПоДолямСтоимости"
    ВариантПриемкиТоваров: str = "РазделенаТолькоПоНакладным"

    ВыходныеИзделия: list = field(default_factory=list)
    ОбеспечениеМатериаламиИРаботами: list = field(default_factory=list)
    Услуги: list = field(default_factory=list)

    def __post_init__(self):
        # self.ЖелаемаяДатаПоступления = '2025-05-05'
        # self.Организация_Key = 'd01c313c-114f-11e7-80c0-4ccc6a67082d'
        super().__post_init__()
        if self.ЖелаемаяДатаПоступления:
            date_obj = datetime.strptime(self.ЖелаемаяДатаПоступления, '%Y-%m-%d')
            self.ЖелаемаяДатаПоступления = date_obj.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            raise Exception

    def append_ВыходныеИзделия(
            self,
            Номенклатура_Key: str = '9186ec97-d186-11ef-85f7-00d861dd2b4a',
            Количество: int | float = 4

    ):
        row_code = str(len(self.ВыходныеИзделия) + 1)
        self.ВыходныеИзделия.append({
            'LineNumber': row_code,
            'Номенклатура_Key': Номенклатура_Key,
            'КоличествоУпаковок': Количество,
            'Количество': Количество,
            "ДоляСтоимости": 50,
            "Получатель": self.СкладПродукции_Key,
            "Получатель_Type": "StandardODATA.Catalog_Склады",
            "КодСтроки": row_code,
            "НомерГруппыЗатрат": "1"
        })

    def append_ОбеспечениеМатериаламиИРаботами(
            self,
            Номенклатура_Key: str = '66a64d5a-a0b4-11ef-85c3-00d861dd2b4a',
            Количество: int | float = 883.125

    ):
        row_pk = str(len(self.ОбеспечениеМатериаламиИРаботами) + 1)
        self.ОбеспечениеМатериаламиИРаботами.append({
            'LineNumber': row_pk,
            'Номенклатура_Key': Номенклатура_Key,
            'КоличествоУпаковок': Количество,
            'Количество': Количество,
            "СтатусУказанияСерий": 0,
            "Упаковка_Key": "00000000-0000-0000-0000-000000000000",
            "ВариантОбеспечения": "КОбеспечению",
            "Склад_Key": self.СкладМатериалов_Key,
            "ДатаОтгрузки": "0001-01-01T00:00:00",
            "СрокПоставки": "0",
            "СтатьяКалькуляции_Key": "62dd9c47-4227-11ec-8463-00d861dd2b4a",
            "НомерГруппыЗатрат": "1",
            "КодСтроки": row_pk,
            "КлючСвязиНабор": "00000000-0000-0000-0000-000000000000"
        })

    def append_Услуги(
            self,
            Номенклатура_Key: str = '37d95399-0568-11f0-a3a8-30e1716be59f',
            Количество: int | float = 4,
            Характеристика_Key: str = "9acd8a3a-0569-11f0-a3a8-30e1716be59f"
    ):
        row_pk = str(len(self.Услуги) + 1)
        self.Услуги.append({
            'LineNumber': row_pk,
            'Номенклатура_Key': Номенклатура_Key,
            'Количество': Количество,
            "Характеристика_Key": Характеристика_Key,
            "СтавкаНДС_Key": "5e490d31-e68d-11ed-8482-00d861dd2b4a",
            "СтатьяКалькуляции_Key": "62dd9c47-4227-11ec-8463-00d861dd2b4a",
            "НомерГруппыЗатрат": "1",
            "КодСтроки": row_pk,
        })



class OrderERP:
    def __init__(self, *, erp_base_name: str, window = None):
        self.client = COE.OrdersComposit(erp_base_name)
        self.nomen_cache = {}
        self.window = window

    def get_order_services(self):
        debug = '05c2c56b-0567-11f0-a3a8-30e1716be59f'
        response = self.client.get_response(
            'Catalog_ХарактеристикиНоменклатуры',
            wet_filtr=f'?$select=Ref_Key,Description&$filter=ВидНоменклатуры_Key eq guid{debug!r}'
        )
        return response

    def find_ERP_nomen_by_nn(self, name: str):
        response = self.client.get_response(
            'Catalog_Номенклатура',
            wet_filtr=f'?$filter=substringof({name!r}, Description)&$select=Ref_Key,Description,ЕдиницаИзмерения_Key,Code'
        )
        return response

    def find_ERP_nomen_by_code(self, code: str):
        return self.client.get_response(
            'Catalog_Номенклатура',
            wet_filtr=f'?$filter=Code eq {code!r}&$top=1&$select=Ref_Key,Description,ЕдиницаИзмерения_Key,Code'
        )

    def create_nomen(self, name: str, ЕдиницаИзмерения_Key: str = 'dd2c9714-019f-11e7-80c0-4ccc6a67082d'):
        data = {
            "Description": name,
            "ВидНоменклатуры_Key": "e3548d04-3c27-11ee-84b4-00d861dd2b4a",
            "ГруппаДоступа_Key": "84132460-8936-11ea-8438-00d861c603dc",
            "ИспользованиеХарактеристик": "НеИспользовать",
            "ГруппаФинансовогоУчета_Key": "e615b90d-4aae-11e8-80d0-4ccc6a67082d",
            "СтавкаНДС_Key": "5e490d31-e68d-11ed-8482-00d861dd2b4a",

            "ЕдиницаИзмерения_Key": ЕдиницаИзмерения_Key,
            "ГруппаАналитическогоУчета_Key": "c46b6037-0585-11e8-80cd-4ccc6a67082d",
            "ВладелецТоварныхКатегорий_Key": "12a92ef4-131c-11ed-8468-00d861dd2b4a",
        }

        headers = self.client.headers
        url = self.client.get_url(doc_name='Catalog_Номенклатура', patch=True)
        try:
            response = requests.post(url, json=data, headers=headers, auth=(self.client.user, self.client.pswd),)
            cod = response.status_code
            response = response.json()
            if 'odata.error' in response:
                return cod, response['odata.error']['message']['value']
        except (
        requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.JSONDecodeError):
            print(f'{F.now()} not connect ERP')
            return 0, None
        return cod, response


    def department_by_individual_id(self, individual_id: str):
        return self.client.get_response(
            'Catalog_Пользователи',
            wet_filtr=f"?$filter=ФизическоеЛицо_Key eq guid{individual_id!r}"
        )

    def mark_author(self, ref_key: str, document_type: str, author_uuid: str):
        doc_name = f'{document_type}(guid{ref_key!r})'
        if document_type == 'Document_ЗаказПоставщику':
            data = {'Автор_Key': author_uuid}
        else:
            data = {
                'Автор_Key': author_uuid,
                'Автор_Type': "StandardODATA.Catalog_Пользователи"
            }
        self.client.params = data
        response = self.client.patch_responce(doc_name=doc_name)
        self.client.params = {}
        return response

    def on_click_create_nomen(self, row: int, col: int, tbl: QtWidgets.QTableWidget, *args, **kwargs):
        nk_nn = CQT.num_col_by_name_c(tbl, 'Номенклатурный номер')
        nk_code = CQT.num_col_by_name_c(tbl, 'Код')
        nk_action = CQT.num_col_by_name_c(tbl, 'Действие')
        nn = tbl.item(row, nk_nn).text()
        code, nomen = self.create_nomen(nn)
        if code != 201:
            return CQT.msgbox(f'Произошла ошибка при добавлении номенклатуры с обозначением: {nn!r}')
        tbl.item(row, nk_code).setText(nomen['Code'])
        tbl.removeCellWidget(row, nk_action)


    def on_click_select_nomen(self, nomen_lst, row: int, col: int, tbl: QtWidgets.QTableWidget, *args, **kwargs):
        result = CQT.msgboxg_get_table(tbl, dict_or_list=nomen_lst, msg='Выберите строку номенклатуры', ExtendedSelection=False)
        if not result: return
        nk_nn = CQT.num_col_by_name_c(tbl, 'Номенклатурный номер')
        nk_code = CQT.num_col_by_name_c(tbl, 'Код')
        nk_ref_key = CQT.num_col_by_name_c(tbl, 'Ref_Key')
        tbl.item(row, nk_code).setText(result['Code'])
        tbl.item(row, nk_nn).setText(result['Description'])
        tbl.item(row, nk_ref_key).setText(result['Ref_Key'])

    def oform_sub_preview_table(self, tbl: QtWidgets.QTableWidget):
        spec_columns = {
            tbl.hideColumn(column)
            for column in range(tbl.columnCount())
            if tbl.horizontalHeaderItem(column).text() in ('Ref_Key', 'Характеристика_Key')
        }
        for row in range(tbl.rowCount()):
            for col in range(tbl.columnCount()):
                if tbl.columnWidth(col) < 80:
                    tbl.setColumnWidth(col, 80)
                item = tbl.item(row, col)
                value = item.text()
                split_value = value.split('|')
                if len(split_value) == 2:
                    if split_value[0] == '<btn>':
                        CQT.add_btn(tbl, row, col, split_value[1], conn_func_checked_row_col=self.on_click_create_nomen, cell_val=tbl)
                    if split_value[0] == '<combo>':
                        nk_nn = CQT.num_col_by_name_c(tbl, 'Номенклатурный номер')
                        nn = tbl.item(row, nk_nn).text()
                        nomen_lst = self.nomen_cache.get(nn)
                        CQT.add_btn(tbl, row, col, split_value[1], conn_func_checked_row_col=self.on_click_select_nomen, cell_val=tbl, self=nomen_lst)



    def oform_preview_table(self, tbl: QtWidgets.QTableWidget):
        tbl.setMinimumWidth(1260)
        tbl.setMinimumHeight(780)
        font = QtGui.QFont()
        font.setPointSize(8)
        tbl.setFont(font)
        spec_columns = {
            tbl.hideColumn(column)
            for column in range(tbl.columnCount())
            if tbl.horizontalHeaderItem(column).text().endswith('_1c')
        }
        tbl.setStyleSheet(CQT.ERP_CSS)
        for row in range(tbl.rowCount()):
            for col in range(tbl.columnCount()):
                cell = tbl.cellWidget(row, col)
                if isinstance(cell, QtWidgets.QTableWidget):

                    if cell.rowCount() > 0:
                        # scroll_height = cell.horizontalScrollBar().height()
                        # head_height = cell.horizontalHeader().height()
                        # first_row_heigh = cell.rowHeight(0)
                        # tbl.setRowHeight(row, head_height + scroll_height + first_row_heigh)
                        self.oform_sub_preview_table(cell)
                        # cell.setMinimumHeight(scroll_height + head_height + 10)


    def validate_user_preview_changes(self, data):
        cp_data = copy.deepcopy(data)
        for idx, item in enumerate(data):
            if item['Значение_1c'] == 'list':
                lst = item['Значение']
                field = item['Поле']
                if isinstance(lst, list):
                    for item in lst:
                        if 'Ref_Key' in item and item['Ref_Key'] == '':
                            return
                cp_data[idx]['Значение'] = lst
        return cp_data

    def unpack_user_changes_in_object(self, result, order_object: OrderRecycler | OrderSupplier):
        for item in result:
            key = item['Поле']
            value = item['Значение']
            if value == '[]':
                continue
            match key:
                case 'Товары':
                    for nomen in value:
                        order_object.append_Товары(
                            Номенклатура_Key=nomen['Ref_Key'],
                            Количество=nomen['Количество']
                        )
                case 'ОбеспечениеМатериаламиИРаботами':
                    for nomen in value:
                        order_object.append_ОбеспечениеМатериаламиИРаботами(
                            Номенклатура_Key=nomen['Ref_Key'],
                            Количество=nomen['Количество']
                        )
                case 'ВыходныеИзделия':
                    for nomen in value:
                        order_object.append_ВыходныеИзделия(
                            Номенклатура_Key=nomen['Ref_Key'],
                            Количество=nomen['Количество']
                        )
                case 'Услуги':
                    for nomen in value:
                        order_object.append_Услуги(
                            Количество=nomen['Количество'],
                            Характеристика_Key=nomen['Характеристика_Key']
                        )
        return order_object

    def prepare_data_for_send(self, main_data: dict[str, str | int], nomen_lst: list[dict], doc_name: str, docs: list[list]):
        # Этап 1 составление объекта-представления документа с основными данными
        if doc_name == 'Document_ЗаказПоставщику':
            data_order_obj = OrderSupplier(**main_data)
        if doc_name == 'Document_ЗаказПереработчику2_5':
            data_order_obj = OrderRecycler(**main_data)
        # Этап 2 Получение данных для пользовательского редактирования
        data_order = asdict(data_order_obj)
        data = self.get_document_view_for_preview(
            docs=docs,
            doc_name=doc_name,
            lst_dse=nomen_lst,
            dic_main_info=data_order
        )
        # Этап 3 Получение пользовательских изменений
        # 3.1 Функция оформления основной таблицы А.) скрывает колонки Б.) Выравнивает размерность вложенных таблиц
        # 3.1 Функция оформления побочной таблицы А.) скрывает колонки Б.) Размещает виджеты в местах, где пользователь должен уточнить информацию
        # 3.2 Функция валидации А.) возвращает False если уточняющая информация не была заполнена
        result = CQT.msgboxg_get_table(self.window,
                                       'Предпросмотр данных', dict_or_list=data,
                                       btn0_name='Принять',
                                       func_validate=self.validate_user_preview_changes, func_oform_tbl=self.oform_preview_table, show_filtr=False)
        if result:
            # Этап 3 Распаковка пользовательских изменений в объект документа
            obj = self.unpack_user_changes_in_object(result, data_order_obj)
            # Этап 4 Распаковка тела для запроса и отправка на создание
            return obj.as_dict()

    def create_order(self, docs: list[list], doc_name: str, data_for_order, nomen_dse):
        prepared_data = self.prepare_data_for_send(docs=docs, doc_name=doc_name, nomen_lst=nomen_dse, main_data=data_for_order)
        if not prepared_data:
            return None, None
        self.client.params = prepared_data
        response = self.client.post_responce(doc_name=doc_name)
        self.client.params = {}
        return response

    def get_document(self, doc_name: str, ref_key: str, fields: list[str] = None):
        select = ''
        if fields is not None:
            select = '?$select=%s' % ','.join(fields)
        return self.client.get_response(f'{doc_name}(guid{ref_key!r})', wet_filtr=select, with_cod=True)

    def mark_remove_order(self, ref_key: str, doc_name: str, mark: bool):
        self.client.params = {"DeletionMark": mark}
        response = self.client.patch_responce(f'{doc_name}(guid{ref_key!r})')
        self.client.params = {}
        return response

    def make_tbl_row_by_nomen_description(self, description: str, count: int):
        nomen = self.find_ERP_nomen_by_nn(description)
        if len(nomen) == 0:
            return {
                'Номенклатурный номер': description,
                'Код': '',
                'Количество': count,
                'Действие': '<btn>|Создать',
                'Инфо': 'Номенклатура с данным обозначением не найдена',
                'Ref_Key': ''
            }
        elif len(nomen) == 1:
            return {
                'Номенклатурный номер': description,
                'Код': nomen[0]["Code"],
                'Количество': count,
                'Действие': '',
                'Инфо': 'Найдено',
                'Ref_Key': nomen[0]['Ref_Key']
            }
        else:
            self.nomen_cache[description] = nomen
            return {
                'Номенклатурный номер': description,
                'Код': '',
                'Количество': count,
                'Действие': '<combo>|Выберите номенклатуру',
                'Инфо': 'Найдено несколько номенклатур с данным обозначением',
                'Ref_Key': ''
            }

    def get_document_view_for_preview(self, docs: list[dict], doc_name: str, lst_dse, dic_main_info):
        services = self.get_order_services()
        services_by_name = F.deploy_dict_c(services, 'Description')
        nomen_izd = []
        nomen_mats = []
        nomen_services = []
        for dse in lst_dse:
            nn = dse['Номенклатурный_номер']
            # nomen = self.find_ERP_nomen_by_nn(nn)
            nomen_izd.append(self.make_tbl_row_by_nomen_description(nn, dse['Количество']))
            mats = [mat for oper in dse['_Операция'] for mat in oper['Материалы']]
            for mat in mats:
                mat_code = mat['Мат_код']
                mat_count = mat['Мат_норма']
                mat_erp = self.find_ERP_nomen_by_code(mat_code)
                if mat_erp:
                    # nomen_mats.append(mat_erp[0]['Description'], mat_count)
                    nomen_mats.append({
                        'Номенклатурный номер': mat_erp[0]['Description'],
                        'Код': mat_erp[0]['Code'],
                        'Количество': mat_count,
                        'Ref_Key': mat_erp[0]['Ref_Key']
                    })
            nomen_services.append({
                'Ref_Key': '37d95399-0568-11f0-a3a8-30e1716be59f',
                'Наименование': 'Работы сторонних организаций',
                'Характеристика': dse.get('Услуга'),
                'Характеристика_Key': services_by_name.get(dse.get('Услуга')),
                'Количество': dse['Количество']
            })
        if doc_name == 'Document_ЗаказПереработчику2_5':
            additional_info = [
                {'Поле': 'ВыходныеИзделия', 'Значение': nomen_izd, 'Поле_1c': '', 'Значение_1c': 'list'},
                {'Поле': 'ОбеспечениеМатериаламиИРаботами', 'Значение': nomen_mats, 'Поле_1c': '', 'Значение_1c': 'list'},
                {'Поле': 'Услуги', 'Значение': nomen_services, 'Поле_1c': '', 'Значение_1c': 'list'},
            ]
            preview_keys = [
                'Статус',
                'Организация_Key',
                'ЖелаемаяДатаПоступления',
                'СкладПродукции_Key',
                'СкладМатериалов_Key',
                'Комментарий',
                'ДополнительнаяИнформация'
            ]
        elif doc_name == 'Document_ЗаказПоставщику':
            additional_info = [
                {'Поле': 'Товары', 'Значение': nomen_izd, 'Поле_1c': '', 'Значение_1c': 'list'},
            ]
            preview_keys = [
                'Статус',
                'Организация_Key',
                'ЖелаемаяДатаПоступления',
                'Склад_Key',
                'Комментарий',
                'ДополнительнаяИнформация'
            ]
        else:
            raise Exception("Не удалось вычислить тип документа")

        main_info = []
        for key in preview_keys:
            alias = key
            value = dic_main_info[key]
            ref_key = dic_main_info[key]
            if isinstance(value, Property1C):
                alias = value.alias
                ref_key = value.Ref_Key
                value = value.Description
            main_info.append({
                'Поле': alias,
                'Поле_1c': key,
                'Значение': value,
                'Значение_1c': ref_key
            })
        if len(docs) == 1:
            docs = []
        additional_info.append({
            'Поле': 'Прикрепленные файлы', 'Значение': docs, 'Значение_1c': 'list'
        })
        # for key, value in dic_main_info.items():
        #     main_info.append({'Поле': key, 'Значение': value})

        return [*main_info, *additional_info]


if __name__ == '__main__':
    data_for_order_test = {'Автор_Key': 'f3762eb1-5a2c-11ef-8581-00d861dd2b4a', 'ДополнительнаяИнформация': '',
                           'ЖелаемаяДатаПоступления': '2025-06-18', 'Комментарий': '',
                           'Менеджер_Key': 'f3762eb1-5a2c-11ef-8581-00d861dd2b4a',
                           'Подразделение_Key': 'b0f6c17d-2297-11eb-8453-b42e99cc2e43'}
    doc_name_test = 'Document_ЗаказПереработчику2_5'
    nomen_dse_test = [{'_Операция': [
        {'_Материал': [], 'Закрыто,шт.': 0, 'Материалы': [], 'Опер_КОИД': 1, 'Опер_КР': 1, 'Опер_РЦ_код': '020201',
         'Опер_РЦ_наименование': 'ПДО ПЗ', 'Опер_Тпз': 200.0, 'Опер_Тшт': 0, 'Опер_Тшт_ед': 0,
         'Опер_вспомогательная': 0, 'Опер_документы': [], 'Опер_инстумент': [], 'Опер_код': '5000',
         'Опер_наименование': 'Термическая обработка', 'Опер_наименование_подразделения': '', 'Опер_номер': '035',
         'Опер_оборудование_код': '', 'Опер_оборудование_наименование': 'Аутсорс', 'Опер_оснастка': [],
         'Опер_профессия_код': '12837', 'Опер_профессия_наименование': 'Комплектовщик', 'Освоено,шт.': 12,
         'Переходы': [], 'Этап': 'Вспомогательная'}], 'dreva_kod': '1.10.0.0', 'Документы': '['']', 'Код ERP': '',
                       'Код_ERP': '', 'Количество': '12', 'Количество_ед': '1', 'Мат_кд': '83.29///',
                       'Наименование': 'Первая ступень дросселирования', 'Номенклатурный_номер': 'ШПС.2404156.01.01',
                       'Номерпп': '26', 'ОперациПоНаряду': '035$Термическая обработка', 'ПКИ': '0', 'Параметрика': '{}',
                       'Прим': '', 'Способы_получения_материала': 'Произвести по основной спецификации',
                       'Ссылка': 'docs://srv-docs.powerz.ru:21361/OpenPropertiesInNewWindow/?refId=403&objID=14547',
                       'Уровень': '1', 'Услуга': 'работы по гибке деталей'}]
    order_instance = OrderERP(erp_base_name='ERP_MES2')

    data_order = order_instance.check_validate(data_for_order_test, doc_name_test, nomen_dse_test)
    order_instance.get_nomen_for_preview_recycler(
        nomen_dse_test,
        data_order
    )
    print(data_order)