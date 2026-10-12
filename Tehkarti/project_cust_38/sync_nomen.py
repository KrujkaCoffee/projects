import collections
import difflib
import enum
import os
import pickle
import copy
import logging
import json
import inspect
import time
import hashlib
import base64
import typing
from functools import reduce
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from enum import Enum
import dataclasses
import sys

import requests

from project_cust_38 import Cust_SQLite as CSQ
import project_cust_38.Cust_odata_erp as ERP
import project_cust_38.Cust_b24 as CB24
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Functions as F
from unittest.mock import patch
from project_cust_38.nomenklatura import ExpensiveChecker as NOMENEXCH

logger = logging.getLogger(__name__)

ServiceName = typing.TypeVar('ServiceName', bound=str)

TEST_CHAT = 'chat78766'


class B24MeasureAttributes(enum.Enum):
    CODE = "CODE"
    MEASURE_TITLE = 'MEASURE_TITLE'


class DependenciesNomenclature:
    def __init__(self):
        self.list_nomen_types = CSQ.custom_request_c(
            CFG.Config.project.db_nomen,
            f'SELECT name, Ref_Key, ЕстьПараметры FROM ВидыНоменклатуры',
            rez_dict=True,
        )
        self.dict_nomen_types_by_ref = F.deploy_dict_c(self.list_nomen_types, 'Ref_Key')


class RecursiveResponse:


    def __init__(self, is_test: bool):
        self.B24_BASE_URL = 'https://bitrix24.kelast.ru/rest/3342/zmoegng9gl0gp5gm'
        if is_test:
            self.B24_BASE_URL = 'https://dev.bitrix24.kelast.ru/rest/2585/6tq57vcv71ou03r9'

        self.measure_by_cut_name = {}
        self.measure_by_title = {}
        self.get_all_measure()

    def get_measure_by_name(self, measure_name: str) -> Optional[int]:
        if measure_name in self.measure_by_cut_name:
            return self.measure_by_cut_name[measure_name]['ID']
        if measure_name in self.measure_by_title:
            return self.measure_by_title[measure_name]['ID']

    def get_measure_code_by_name(self, measure_name: str) -> Optional[int]:
        if measure_name in self.measure_by_cut_name:
            return self.measure_by_cut_name[measure_name]['CODE']
        if measure_name in self.measure_by_title:
            return self.measure_by_title[measure_name]['CODE']

    def get_all_measure(self):
        result = {}
        next_vals = '0'
        credentials = {}
        while not next_vals is None:
            credentials['start'] = next_vals
            last_deals = self.measure_list(credentials)
            for measure_item in last_deals['result']:
                self.measure_by_cut_name[measure_item['SYMBOL_RUS']] = measure_item
                self.measure_by_title[measure_item['MEASURE_TITLE']] = measure_item
            next_vals = last_deals.get('next')
        return result

    def measure_list(self, body: dict):
        url = f'{self.B24_BASE_URL}/crm.measure.list'
        response = requests.post(url, json=body)
        data = response.json()
        return data

    def get_section_b24_by_id(self, section_id):
        url = f'{self.B24_BASE_URL}/catalog.section.get?id={section_id}'
        response = requests.post(url, json={'filter': {'active': 'Y', 'iblockId': 27, 'id': section_id}})
        data = response.json()
        return data['result']['section']

    def get_section_b24_by_xml_id(self, xml_id):
        url = f'{self.B24_BASE_URL}/catalog.section.list'
        response = requests.post(url, json={'filter': {'active': 'Y', 'iblockId': 27, 'xmlId': xml_id}})
        data = response.json()
        match data:
            case {'result': {'section': [section, *args]}}:
                return section

    def get_children_sections_b24_by_parent_id(self, idx: int, start: str):
        url = f'{self.B24_BASE_URL}/catalog.section.list?start={start}'
        response = requests.post(url, json={'filter': {'active': 'Y', 'iblockId': 27, 'iblockSectionId': idx}, 'start': start})
        data = response.json()
        return data

    def get_full_result(self, pk, fn):
        result_b24 = []
        next_vals = '0'
        while not next_vals is None:
            page = fn(idx=pk, start=next_vals)
            result_b24.extend(page['result']['sections'])
            next_vals = page.get('next')
        return result_b24

    def get_product_by_section_id_b24(self, section_id: int, start: int):
        url = f'{self.B24_BASE_URL}/catalog.product.list?iblockId=27&start={start}'
        response = requests.post(url, json={
            'select': ['iblockId', 'id', 'name', 'iblockSectionId', 'xmlId', 'property454', 'property453'],
            'filter': {
                'iblockSectionId': section_id,
                'iblockId': 27,
            }
        })
        data = response.json()
        return data['result']['products']

    def get_product_by_name_b24(self, name: int):
        url = f'{self.B24_BASE_URL}/catalog.product.list?iblockId=27'
        response = requests.post(url, json={
            'select': ['iblockId', 'id', 'name', 'iblockSectionId', 'xmlId', 'property454', 'property453'],
            'filter': {
                'name': name,
                'iblockId': 27,
                'property453': False
            }
        })
        data = response.json()
        return data['result']['products']

    def get_product_by_xml_id(self, xmlId: int):
        url = f'{self.B24_BASE_URL}/catalog.product.list?iblockId=27'
        response = requests.post(url, json={
            'select': ['iblockId', 'id', 'name', 'iblockSectionId', 'xmlId', 'property454', 'property453'],
            'filter': {
                'xmlId': xmlId,
                'iblockId': 27,
                'property453': False
            }
        })
        data = response.json()
        match data:
            case {'result': {'products': [product, *args]}}:
                return product
        # return data['result']['products']

    def create_productby_b24(self, name: str, category_id: int, ref_key_1c: str, mass_per_unit: float, measure: str):
        print('создан', name, category_id, ref_key_1c)
        url = f'{self.B24_BASE_URL}/catalog.product.add'
        measure_id = self.get_measure(measure, find_by=B24MeasureAttributes.MEASURE_TITLE)
        response = requests.post(url, json={
            'fields': {
                'name': name,
                'iblockId': 27,
                'property453': False,
                'iblockSectionId': category_id,
                'xmlId': ref_key_1c,
                'measure': measure_id,
                'property454': {'value': mass_per_unit}
            }
        })
        data = response.json()
        return data['result']['element']

    def get_measure(self, measure: str, find_by: B24MeasureAttributes = B24MeasureAttributes.MEASURE_TITLE):
        body = {
            "filter": {find_by.value: measure}
        }
        response = requests.post(f'{self.B24_BASE_URL}/crm.measure.list', json=body)
        if not response.ok:
            return None
        data = response.json()
        match data:
            case {'result': [{"ID": id_measure}, *others]}:
                return id_measure
        return None

    def update_productby_b24(self, product_id: int, name: str, category_id: int, ref_key_1c: str, mass_per_unit: float, measure: str):
        print('обновлен', name, product_id, category_id, ref_key_1c)
        url = f'{self.B24_BASE_URL}/catalog.product.update?id={product_id}'
        # measure_id = self.get_measure(measure, find_by=B24MeasureAttributes.MEASURE_TITLE)
        measure_id = self.get_measure_by_name(measure)

        response = requests.post(url, json={
            'id': product_id,
            'fields': {
                'name': name,
                'iblockId': 27,
                'property453': {'value': False},
                'iblockSectionId': category_id,
                'xmlId': ref_key_1c,
                'property454': {'value': mass_per_unit},
                'measure': measure_id
            }
        })
        data = response.json()
        return data['result']['element']

    def delete_productby_b24(self, product_id):
        url = f'{self.B24_BASE_URL}/catalog.product.delete?id={product_id}'
        response = requests.post(url, json={
            'id': product_id,
        })
        return response.status_code

    def mark_delete_productby_b24(self, product_id):
        url = f'{self.B24_BASE_URL}/catalog.product.update?id={product_id}'
        response = requests.post(url, json={
            'id': product_id,
            'fields': {
                'property453': {'value': True},
            }
        })
        data = response.json()
        return data['result']['element']

    def get_children_by_array_id(self, array_id: set[int]):
        new_ids = set()
        for pk in array_id:
            # elems = self.get_children_sections_b24_by_parent_id(pk)
            elems = self.get_full_result(pk, self.get_children_sections_b24_by_parent_id)
            for elem in elems:
                # products = self.get_full_result(elem['id'], self.get_product_by_section_id_b24)
                # self.data.extend(products)
                self.b24_data.setdefault(elem['name'].strip(), list()).append(elem)
                self.b24_data_by_id[elem['id']] = elem
                new_ids.add(elem['id'])
        if new_ids:
            return self.get_children_by_array_id(new_ids)

    def get_section_1c_by_parent_ref(self, ref_key: str):
        additional = '$expand=Parent&$select=Description,Ref_Key,Parent/Ref_Key,Parent/Description'
        url = self.BASE_URL_1C + f'?$filter=Parent_Key eq guid{ref_key!r} and DeletionMark eq false&$format=json&{additional}'
        response = requests.get(url, auth=self.auth_1c)
        data = response.json()
        return data['value']

    def get_section_1c_by_ref(self, ref_key: str):
        additional = '$expand=Parent&$select=Description,Ref_Key,Parent/Ref_Key,Parent/Description'
        url = self.BASE_URL_1C + f'?$filter=Ref_Key eq guid{ref_key!r} and DeletionMark eq false&$format=json&{additional}'
        response = requests.get(url, auth=self.auth_1c)
        data = response.json()
        return data['value']

    def get_section_1c_by_name(self, name: str):
        additional = '$expand=Parent&$select=Description,Ref_Key,Parent/Ref_Key,Parent/Description'
        url = self.BASE_URL_1C + f'?$filter=Description eq {name!r} and DeletionMark eq false&$format=json&{additional}'
        response = requests.get(url, auth=self.auth_1c)
        data = response.json()
        return data['value']


    def update_b24_xml(self, b24_id, new_ref, name, *, parent_id: int):
        url = f'{self.B24_BASE_URL}/catalog.section.update?iblockId=27&id={b24_id}'
        response = requests.post(url, json={'id': b24_id, 'iblockId': 27, 'fields': {'xmlId': new_ref, 'iblockId': 27, 'name': name, 'iblockSectionId': parent_id}})
        data = response.json()
        return data['result']['section']

    def create_category_b24(self, description: str, ref_key: str, parent_id: int):
        url = f'{self.B24_BASE_URL}/catalog.section.add'
        response = requests.post(url, json={'fields': {'name': description, 'xmlId': ref_key, 'iblockId': 27, 'iblockSectionId': parent_id}})
        data = response.json()
        match data:
            case {'result': {'section': section}}:
                return section
        # return data['result']['section']

    def find_parent_by_name_b24(self, name: str):
        url = f'{self.B24_BASE_URL}/catalog.section.list'
        response = requests.post(url, json={'filter': {'active': 'Y', 'iblockId': 27, 'name': name}})
        data = response.json()
        return data['result']['sections']

    def get_nomen_by_vid_ref(self, ref_key: str):
        select = '$select=Description,Ref_Key,КоэффициентЕдиницыДляОтчетов'
        url = f'{self.BASE_URL_1C_NOMEN}?$filter=ВидНоменклатуры_Key eq guid{ref_key!r} and DeletionMark eq false&$format=json&{select}'
        response = requests.get(url, auth=self.auth_1c)
        data = response.json()['value']
        return data


class Emoji:
    error = '❗'
    success = '🟢'
    pending = '⏳'
    unnecessary = '🟡'

    def is_success(self, status):
        return status in (ServiceStatus.success, ServiceStatus.unnecessary)


class ServiceStatus(typing.NamedTuple):
    emoji: str
    status_code: int
    is_success: bool
    description: str


class MessageStatus(typing.NamedTuple):
    services: dict[ServiceName, ServiceStatus]
    message_id: Optional[int]


@dataclasses.dataclass
class Task:
    pk: int  # Идентификатор задачи
    credentials: dict  # Данные с которыми работают хэндлеры
    services: dict[str, typing.Callable]  # Сервисы, для которых доставляются данные

    chat_id: str  # Чат оповещения о состоянии задачи
    message_status: MessageStatus  # Данные о доставке оповещения
    chat_accepted: bool  # Флаг отправлено ли сообщение в чат

    is_test: bool = False

    def __hash__(self):
        def _encode_struct(obj):
            if isinstance(obj, dict):
                return {k: _encode_struct(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [_encode_struct(v) for v in obj]
            elif isinstance(obj, (set, frozenset)):
                return sorted([_encode_struct(v) for v in obj], key=lambda x: str(x))
            elif isinstance(obj, bytes):
                return base64.b64encode(obj).decode("ascii")
            else:
                return obj

        struct = _encode_struct(self.credentials)
        serialized = json.dumps(
            struct,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).digest()
        return hash((self.pk, digest))


def sync_nomen_b24(task: Task):
    if task.is_test:
        return 204
    b24_nomen_client = RecursiveResponse(is_test=task.is_test)
    match task.credentials:
        case {
            'Код': code,
            'Артикул': article_number,
            'Наименование': nomen_name,
            'ЕдиницаИзмерения': unit_of_measurement,
            'На_удаление': is_delete,
            'СхемаОбеспечения': provision_schema,
            'Ref_Key': ref_key,
            'Вид_Ref_Key': type_ref_key,
            'Вид': type_name,
            'Закупочная_цена': price,
            'types_tree': hierarchy_nomen_types,
            'unit_code': unit_code,
            'unit_ratio': unit_ratio
        }:
            if hierarchy_nomen_types is None:
                hierarchy_nomen_types = ''
            nomen_b24 = b24_nomen_client.get_product_by_xml_id(ref_key)
            set_types = set(hierarchy_nomen_types.split(';'))
            set_types.add(type_ref_key)
            need_types = {
                'cecbbe44-9f30-11ea-8440-00d861129db6',
                '12ce209b-a327-11e9-80e4-4ccc6a67082d',
                'c6784f84-c9e8-11e7-80cb-4ccc6a67082d',
                '0501665b-c9f6-11e7-80cb-4ccc6a67082d',
            }
            if not set_types.intersection(need_types):
                return 204
            section_b24 = b24_nomen_client.get_section_b24_by_xml_id(type_ref_key)
            if section_b24 is None:
                section_b24 = b24_nomen_client.create_category_b24(type_name, type_ref_key, None)
                if not section_b24:
                    return 500
            if is_delete and not nomen_b24:
                return 204
            if nomen_b24 is None:
                nomen_b24 = b24_nomen_client.create_productby_b24(
                    nomen_name,
                    section_b24['id'],
                    ref_key,
                    unit_ratio,
                    measure=unit_of_measurement
                )
                if nomen_b24:
                    return 201
            elif is_delete:
                return b24_nomen_client.delete_productby_b24(nomen_b24['id'])
            else:
                product = b24_nomen_client.update_productby_b24(
                    product_id=nomen_b24['id'],
                    name=nomen_name,
                    category_id=section_b24['id'],
                    ref_key_1c=ref_key,
                    mass_per_unit=unit_ratio,
                    measure=unit_of_measurement
                )
                return 200 if product else 500
            return 500


def sync_nomen_mes(task):
    def calc_expensive(name:str)->int:
        exp_check = NOMENEXCH()
        return F.valm(exp_check.is_expensive_nomen(name))

    if task.is_test:
        return 200
    match task.credentials:
        case {
            'Код': code,
            'Артикул': article_number,
            'Наименование': nomen_name,
            'ЕдиницаИзмерения': unit_of_measurement,
            'На_удаление': is_delete,
            'СхемаОбеспечения': provision_schema,
            'Ref_Key': ref_key,
            'Вид_Ref_Key': type_ref_key,
            'Вид': type_name,
            'Закупочная_цена': price
        }:
            depends = DependenciesNomenclature()

            if type_ref_key not in depends.dict_nomen_types_by_ref:
                return 204
            expensive = calc_expensive(nomen_name)
            resp = CSQ.custom_request_c(
                CFG.Config.project.db_nomen,
                f'SELECT Ref_Key FROM nomen WHERE Ref_Key = {ref_key!r}',
                one=True,
                rez_dict=True,
            )
            if not resp: # Создать

                body = [code,
                        article_number,
                        nomen_name,
                        unit_of_measurement,
                        is_delete,
                        F.now(),
                        provision_schema,
                        price,
                        type_ref_key,
                        type_name,
                        ref_key,
                        expensive
                        ]
                result = CSQ.custom_request_c(CFG.Config.project.db_nomen, f"""INSERT INTO nomen (
                        Код
                        ,Артикул
                        ,Наименование
                        ,ЕдиницаИзмерения
                        ,На_удаление
                        ,Дата_изменения
                        ,СхемаОбеспечения
                        ,Закупочная_цена
                        ,Вид_Ref_Key
                        ,Вид
                        ,Ref_Key
                        ,expensive) VALUES ({','.join('?' * len(body))})""", list_of_lists_c=[body])
                return 201 if result else 500
            else:

                body = [ # Редактировать
                    code,
                    article_number,
                    nomen_name,
                    unit_of_measurement,
                    is_delete,
                    F.now(),
                    provision_schema,
                    type_ref_key,
                    price,
                    type_name,
                    expensive
                ]
                result = CSQ.custom_request_c(CFG.Config.project.db_nomen, f"""UPDATE nomen 
                    SET Код = ?,
                        Артикул = ?,
                        Наименование = ?,
                        ЕдиницаИзмерения = ?,
                        На_удаление = ?,
                        Дата_изменения = ?,
                        СхемаОбеспечения = ?,
                        Вид_Ref_Key = ?,
                        Закупочная_цена = ?,
                        Вид = ?,
                        expensive = ? WHERE Ref_Key = {ref_key!r}""", list_of_lists_c=body)
                return 200 if result else 500

    return 500

def sync_nomen_tflex_docs(task: Task):
    return 204
    if task.is_test:
        try:
            a = requests.post('http://192.168.14.69:5226/NomenFromOneEs',
                         json=task.credentials, timeout=5)
            return a.status_code

        except Exception as e:
            ...
    return 204





def create_status_by_code(status_code: int):
    match status_code:
        case 204:
            emoji = Emoji.unnecessary
            description = 'Отклонено'
            is_success = True
        case 201:
            emoji = Emoji.success
            description = 'Создано'
            is_success = True
        case 200:
            emoji = Emoji.success
            description = 'Обновлено'
            is_success = True
        case _:
            emoji = Emoji.error
            description = 'Ошибка'
            is_success = False
    return ServiceStatus(emoji, status_code, is_success, description=description)

def send_nomen_message(
        nomen_name: str,
        code: str,
        type_name: str,
        mark: str,
        mark_delete: bool,
        ref_key: str,
        current_status: dict[str, ServiceStatus], chat_id: str, exchange_id: int, message_id: int = None):
    title = f"ДОБАВЛЕНО" if not mark_delete else 'На удаление'
    message_template = f"""
[B]{title}[/B]
>> Наименование: {nomen_name}
>> КОД: {code}
>> ВИД: {type_name}
>> АРТИКУЛ: {mark}
>> Ref_Key: {ref_key}
    """
    # msg = message_template.format(title=title, nomen_name=nomen_name, type_name=type_name, mark=mark, ref_key=ref_key)
    table = []
    statuses = []
    for service, status in current_status.items():
        table.append({'Сервис': service,
                      'Статус': status.emoji,
                      'Код состояния': status.status_code,
                      'Описание': status.description})
        statuses.append(status.status_code)

    if message_id is None and all(status == 204 for status in statuses):
        return True
    sender = CB24.B24Sender()
    result = sender.send_msg_table(table,
                                    title=message_template,
                                    horizontal=True,
                                    chat_id=chat_id,
                                    message_id=message_id)
    if message_id is None and isinstance(result, int):
        message_id = result
        if all(status == 204 for status in statuses):
            return sender.send_msg_by_chat_id(chat_id=chat_id, msg='', message_id=message_id)
    if result:
        if all(status == 204 for status in statuses):
            return True
        is_written = CSQ.custom_request_c(
            CFG.Config.project.db_files,
            'UPDATE exchange SET chat_accepted = 1, message_status = ?  WHERE id = ?',
                             list_of_lists_c=[
                                 pickle.dumps(MessageStatus(message_id=message_id, services=current_status)),
                                 exchange_id
                             ])
        if not is_written:
            return sender.send_msg_by_chat_id(chat_id=chat_id, message_id=message_id, msg='')


def update_nomenclature(task: Task):
    # credentials: Nomenclature
    default_status = ServiceStatus(Emoji.pending, 205, is_success=False, description='Не обработан')
    current_status = dict.fromkeys(
        task.services.keys(),
        default_status
    )
    if task.message_status and task.message_status.services:
        current_status = task.message_status.services

    for service, func in task.services.items():
        status = current_status.get(service, default_status)
        if not status.is_success:
            try:
                code = func(task)
                current_status[service] = create_status_by_code(code)
            except Exception as e:
                print(e) # todo error log
    data = task.credentials
    message_id = None
    if isinstance(task.message_status, MessageStatus) and task.message_status.message_id:
        message_id = task.message_status.message_id

    chat_id = task.chat_id
    if task.is_test:
        chat_id = TEST_CHAT
    send_nomen_message(
        nomen_name=data['Наименование'],
        code=data['Код'],
        type_name=data['Вид'],
        mark=data['Артикул'],
        ref_key=data['Ref_Key'],
        mark_delete=data['На_удаление'],
        current_status=current_status,
        chat_id=chat_id,
        exchange_id=task.pk,
        message_id=message_id
    )
    return all(status.is_success for status in current_status.values())
