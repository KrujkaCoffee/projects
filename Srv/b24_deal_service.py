import base64
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
from functools import reduce
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('deal_service_error.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

from project_cust_38 import Cust_SQLite as CSQ
import project_cust_38.Cust_odata_erp as ERP
import project_cust_38.Cust_b24 as CB24
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Functions as F

def log_prefix_decorator(event_name: str, target: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            original_level = logger.level
            class InfoFormatter(logging.Formatter):
                def format(self, record):
                    record.msg = f"{event_name} | {record.msg}"
                    return super().format(record)
            func_name = func.__name__
            formatter = InfoFormatter(f'%(asctime)s | {func_name} | %(message)s', datefmt='%Y-%m-%d %H:%M')
            file_handler = logging.FileHandler('b24_deal_service.log', encoding='utf8')
            out_handler = logging.StreamHandler()
            file_handler.setFormatter(formatter)
            out_handler.setFormatter(formatter)
            prev_handlers = logger.handlers.copy()
            logger.handlers = [out_handler, file_handler]
            try:
                old_value = kwargs.get('old_val')
                new_value = kwargs.get('new_val')
                source = kwargs.get('source')
                object_name = kwargs.get('object_name')
                result = func(*args, **kwargs)
                if result:
                    logging.info(f'{object_name!r} | Из: {source!r} | В {target!r} | Было: {old_value!r} | Стало: {new_value!r}')
            finally:
                logger.handlers = prev_handlers
                logger.setLevel(original_level)
            return result
        return wrapper
    return decorator


"""
            "ID": "13361",
            "TITLE": "1812109-24.5",
            "TYPE_ID": "SALE",
            "STAGE_ID": "C1:1", # ID Статуса сделки (entityId=DEAL_STAGE_1)
            "IS_MANUAL_OPPORTUNITY": "N",
            "COMPANY_ID": "4512",
            "CONTACT_ID": "8254",
            "BEGINDATE": "2024-11-29T03:00:00+03:00",
            "CLOSEDATE": "2024-12-06T03:00:00+03:00",
            "CREATED_BY_ID": "2871", # ID cоздателя сделки
            "MODIFY_BY_ID": "3076", # ID пользователя совершившего последнее обновление
            "DATE_CREATE": "2024-11-29T13:11:41+03:00",
            "DATE_MODIFY": "2024-12-17T18:24:29+03:00",
            "OPENED": "Y",
            "CLOSED": "N",
            "COMMENTS": "ТЕСТОВАЯ СДЕЛКА НЕ УДАЛЯТЬ.\n",
            "MOVED_BY_ID": "3076",  
            "MOVED_TIME": "2024-12-17T18:24:29+03:00",
"""

from unittest.mock import patch

patch('project_cust_38.Cust_config.AppConfig')
patch('project_cust_38.Cust_config.User_config')


TEST_CHAT = 'chat78766'


## ================ ENUMS =================

class B24MeasureAttributes(enum.Enum):
    CODE = "CODE"
    MEASURE_TITLE = 'MEASURE_TITLE'


## ================ MODELS =================



def concat_url(*args):
    form = lambda a, b: '%s/%s' % (a.strip('/'), b.strip('/'))
    return reduce(form, args)

def find_match( text: str, dic: dict[str, str]):
    """Совершает поиск левенштейна указанной @string строки в указанному списке @lst"""
    closest_match = difflib.get_close_matches(text, dic, n=1, cutoff=0.9)
    if closest_match:
        return dic[closest_match[0]]
    else:
        return None

class CRM:
    BASE_URL = 'https://bitrix24.kelast.ru/rest/3342/'
    TOKEN = 'zmoegng9gl0gp5gm'

    DEAL_ONE = 'crm.deal.get'
    DEAL_MORE = 'crm.deal.list'
    DEAL_UPDATE = 'crm.deal.update'
    DEAL_STATUS_MORE = 'crm.status.entity.items'  # ?entityId=DEAL_STAGE_1

    def __init__(self):
        self.url = concat_url(self.BASE_URL, self.TOKEN)

    def find_status(self):
        ...

    def deal_status_all(self):
        response = requests.get(
            concat_url(self.url, self.DEAL_STATUS_MORE),
            params={'entityId': 'DEAL_STAGE_1'}
        )
        return response.json()

    def deal_one(self, deal_id: int | str = 13361):
        response = requests.get(
            url=concat_url(self.url, self.DEAL_ONE),
            params={'ID': deal_id},
            headers={'Content-Type': 'application/json'}
        )
        return response.json()

    def deal_list(self, credentials: dict = None):
        response = requests.post(
            url=concat_url(self.url, self.DEAL_MORE),
            headers={'Content-Type': 'application/json', "Accept": "application/json"},
            json=credentials
        )
        return response.json()

    def deal_update(
            self,
            deal_id: int = 13361,
            credentials: dict[str, str] = {'FIELDS': {'STAGE_ID': 'C1:1'}}
    ):
        response = requests.post(
            url=concat_url(self.url, self.DEAL_UPDATE),
            params={'id': deal_id},
            json=credentials,
            headers={'Content-Type': 'application/json'}
        )
        reg = 'Ошибка! Сделка с таким названием (2304050-26.1) уже существует!'
        return response.ok

crm = CRM()
db_files = F.scfg('files')
nomenklatura_erp = F.scfg('nomenklatura_erp')
ERP_SRV = 'ERP'

PREFIX_LOG = '\n' + ('=' * 26)
ENV_LAST_UPDATE_TIME = 'EXCHANGE_LAST_UPDATE'
ITER_INTERVAL = 180
INTERVAL_DAYS = 14

status_key = 'STAGE_ID'
closed_key = 'CLOSED'
ref_key_pk = 'UF_CRM_1712643377'


def set_client_order_close_state(
        ERP_base: str,
        refKey_СделкиСКлиентами: str,
        state: str=None,
        close: bool=None,
        reason_lose: str=None
):

    """ https://bitrix24.kelast.ru/~PJs23
            В документе "Сделка с клиентом" автоматически устанавливается галка в чек-бокс Закрыта (Скриншот 23).
        e1cib/data/Справочник.СделкиСКлиентами?ref=856800d861dd2b4a11ef3548c3fbc558
        state : ВРаботе/Выиграна/Проиграна
        close : True/False
        reason_lose : None/False/ Catalog_ПричиныПроигрышаСделок_keys (Проигрыш конкуренту
        Неплатёжеспособность клиента
        Тендер был фиктивным
        Длительный срок поставки
        Мониторинг цен будующих закупок
        Высокая стоимость
        Отмена закупки по неизвестным причинам
        Несоответствие ТЗ
        Перекуп в открытой закупке
        Неактуальная)
    """
    SET_STATES = {None, 'ВРаботе', 'Выиграна', 'Проиграна'}

    if state not in SET_STATES:
        logging.error('set_client_order_close_state err:state val')
        return 500

    m = ERP.OrdersComposit(ERP_base)
    ERP.OrdersComposit.params = {}
    reason_lose_key = None
    if not reason_lose == None:
        if reason_lose == False:
            reason_lose_key = '00000000-0000-0000-0000-000000000000'
        else:
            kod, list_resaons = m.get_response(doc_name=f'Catalog_ПричиныПроигрышаСделок',
                                               wet_filtr=f"""?$filter=DeletionMark eq false &$top=100&$select=Description,Ref_Key""",
                                               with_cod=True)
            if kod != 200:
                return kod
            dict_reasons = F.deploy_dict_c(list_resaons, 'Description')
            reason_lose_key = find_match(reason_lose, dict_reasons)
            if reason_lose_key:
                key_reason_lose = 'ПричинаПроигрышаСделки_Key'
                deal_1c = m.get_response(f"Catalog_СделкиСКлиентами(guid'{refKey_СделкиСКлиентами}')",
                                         wet_filtr=f'?$select={key_reason_lose}')
                if not deal_1c:
                    return 200
                if deal_1c[key_reason_lose] == reason_lose_key:
                    return 200
            if not reason_lose_key:
                logging.error(f'set_client_order_close_state Не удалось обновить: "{refKey_СделкиСКлиентами}" Причина сделки: "{reason_lose}" не найдена в ERP')
                return 500
    #kod , data_order =  m.get_response(doc_name=f"Catalog_СделкиСКлиентами(guid'{refKey_СделкиСКлиентами}')",
    #                   wet_filtr=f"""?$filter=DeletionMark eq false &$top=100&$select=Закрыта,Статус,ПричинаПроигрышаСделки_Key""",
    #                   with_cod=True)
    #if kod != 200:
    #    return kod
    #data_order[]
    if close != None:
        m.params['Закрыта'] = close
    if state != None:
        m.params['Статус'] = state
    if reason_lose_key != None:
        m.params['ПричинаПроигрышаСделки_Key'] = reason_lose_key
    if len(m.params):
        kod, data_order = m.patch_responce(doc_name=f"Catalog_СделкиСКлиентами(guid'{refKey_СделкиСКлиентами}')")
        return kod
    return 200

def current_iso_date():
    tz = timezone(timedelta(hours=3))
    current_time = datetime.now(tz)
    return current_time.isoformat()

class B24Bucket:
    SELECT_DEAL_FIELDS = (
        "UF_CRM_1712927868",        # Плановая дата () : str ISO DATETIME
        "OPPORTUNITY",              # Сумма (9999) : float:2f
        "STAGE_ID",                 # ID стадии (C1:NEW) : str
        'UF_CRM_1737711083528',     # ТипТКП (Компенсаторы) : str
        'UF_CRM_1737727925',        # Организация (Пауэрз) : str
        'UF_CRM_1712643377',        # Ref_Key сделки 1с () : str
        'CLOSED' ,
        'DATE_MODIFY'# Статус завершена ("0", "1") : str
    )                               # Поля сделки хранимые в ведре

    LAST_MODIFY_KEY = 'DEALS_LAST_MODIFY' # Ключ последнего изменения в ведре
    LAST_DEALS_LIST_KEY = 'DEALS_LIST_BY_ID' # Ключ последнего изменения в ведре

    def __init__(self):
        self.__deals_list = None
        self.DEALS_last_modify = None
        self.set_id_modified = set()
        self.deals: dict[str, dict] = self.get_dict_deals_by_id()

    def check_deals_keys(self) -> bool:
        for deal_id, deal_value in self.__deals_list.items():
            if set(self.SELECT_DEAL_FIELDS).issubset(deal_value.keys()):
                return True
            return False
        return False

    def get_dict_deals_by_id(self):
        bucket_data = get_config_data('./deal_bucket.pickle')
        self.DEALS_last_modify = bucket_data.get(self.LAST_MODIFY_KEY)
        self.__deals_list = bucket_data.get(self.LAST_DEALS_LIST_KEY)
        now = current_iso_date()
        if not self.__deals_list or not self.DEALS_last_modify:
            self.__deals_list = self.dict_deals_by_id(self.get_all_deals())
            self.set_id_modified = set(self.__deals_list.keys())
        if not self.check_deals_keys():
            self.__deals_list = self.dict_deals_by_id(self.get_all_deals())
            self.set_id_modified = set(self.__deals_list.keys())
        if self.DEALS_last_modify:
            last_updates = self.get_last_updates()
            for item in last_updates:
                deal_id = item['ID']
                self.set_id_modified.add(deal_id)
                self.__deals_list[str(deal_id)] = item
        self.DEALS_last_modify = now
        put_config_data(self.LAST_MODIFY_KEY, self.DEALS_last_modify, filename='./deal_bucket.pickle')
        put_config_data(self.LAST_DEALS_LIST_KEY, self.__deals_list, filename='./deal_bucket.pickle')
        return self.__deals_list

    def dict_deals_by_id(self, deals):
        data_b24 = {}
        for item_b24 in deals:
            data_b24[item_b24['ID']] = item_b24
        return data_b24

    def get_last_updates(self):
        last_modify = self.DEALS_last_modify
        credentials = {
            "SELECT": list(self.SELECT_DEAL_FIELDS),
            "FILTER": {">=DATE_MODIFY": last_modify}
        }
        result_b24 = []
        next_vals = '0'
        while not next_vals is None:
            credentials['start'] = next_vals
            last_deals = crm.deal_list(credentials)
            result_b24.extend(last_deals['result'])
            next_vals = last_deals.get('next')
        return result_b24

    def get_all_deals(self):
        result_b24 = []
        credentials = {
            "SELECT": list(self.SELECT_DEAL_FIELDS),
        }
        next_vals = '0'
        while not next_vals is None:
            credentials['start'] = next_vals
            last_deals = crm.deal_list(credentials)
            result_b24.extend(last_deals['result'])
            next_vals = last_deals.get('next')
        return result_b24

class Bucket1C:
    KEY_1C_LAST_MODIFY_ZK_KP_DATA = 'LAST_MODIFY_ZK_KP_MARK_DATA' # Ключ последнего изменения в ведре
    KEY_1C_LAST_MODIFY_ZK_KP_MARK = 'LAST_MODIFY_ZK_KP_MARK_KEY' # Ключ последнего изменения в ведре
    def __init__(self):
        self.__zk_kp_deals_list = None
        self.ZK_KP_DEALS_mark = None
        self.zk_kp_deal_id_modified = set()
        self.zk_kp_deal_data = self.fill_deals_with_relationships()

    def get_last_mark(self, items: list[dict], key_name: str = 'МаксВерсияДанных'):
        last_mark = ''
        for item in items:
            mark = item[key_name]
            if mark is None:
                continue
            if not last_mark:
                last_mark = mark
                continue
            try:
                num = decode_1c_data_version_attribute(mark)
                num_prev = decode_1c_data_version_attribute(last_mark)
            except Exception as e:
                print()
            if num > num_prev:
                last_mark = mark
        return last_mark

    def get_deals_by_relation_zk_kp(self, data_version: str = ''):
        commerc_mark = commerc_ssilc = zk_mark = kp_version = zk_version = ''
        if data_version:
            kp_version = f'И КоммерческоеПредложениеКлиенту.ВерсияДанных >= "{data_version}"'
            zk_version = f'И ЗаказКлиента.ВерсияДанных >= "{data_version}"'
            commerc_mark = f'И КоммерческоеПредложениеКлиенту.ВерсияДанных >= "{data_version}"'
            commerc_ssilc = f'И КоммерческоеПредложениеКлиентуТовары.Ссылка.ВерсияДанных >= "{data_version}"'
            zk_mark = f'И ЗаказКлиента.ВерсияДанных >= "{data_version}"'
        query_1 = f"""
        ВЫБРАТЬ
            МАКСИМУМ(КоммерческоеПредложениеКлиенту.Дата) КАК Дата,
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК СделкаПБ24_id_bitrix
        ПОМЕСТИТЬ ВТ_КППоДатеУник
        ИЗ
            Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
        ГДЕ
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix > 0
            И КоммерческоеПредложениеКлиенту.СуммаДокумента > 0
            И КоммерческоеПредложениеКлиенту.ПометкаУдаления = ЛОЖЬ
            И КоммерческоеПредложениеКлиенту.Проведен = ИСТИНА
            {commerc_mark}

        СГРУППИРОВАТЬ ПО
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
            МАКСИМУМ(КоммерческоеПредложениеКлиентуТовары.СрокПоставки) КАК СрокПоставки,
            КоммерческоеПредложениеКлиентуТовары.Ссылка КАК Ссылка
        ПОМЕСТИТЬ ВТ_ДатыИзКП
        ИЗ
            Документ.КоммерческоеПредложениеКлиенту.Товары КАК КоммерческоеПредложениеКлиентуТовары
        ГДЕ
            КоммерческоеПредложениеКлиентуТовары.Ссылка.Сделка.ПБ24_id_bitrix > 0
            И КоммерческоеПредложениеКлиентуТовары.Ссылка.СуммаДокумента > 0
            И КоммерческоеПредложениеКлиентуТовары.Ссылка.ПометкаУдаления = ЛОЖЬ
            И КоммерческоеПредложениеКлиентуТовары.Ссылка.Проведен = ИСТИНА
            И КоммерческоеПредложениеКлиентуТовары.Ссылка.ВариантУказанияСрокаПоставки = ЗНАЧЕНИЕ(Перечисление.ВариантыСроковПоставкиКоммерческихПредложений.УказываетсяНаОпределеннуюДату)
            {commerc_ssilc}

        СГРУППИРОВАТЬ ПО
            КоммерческоеПредложениеКлиентуТовары.Ссылка
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
            ЗаказКлиента.Ссылка КАК Ссылка,
            ЗаказКлиента.НеОтгружатьЧастями КАК НеОтгружатьЧастями
        ПОМЕСТИТЬ ВТ_ЗКОтбор
        ИЗ
            Документ.ЗаказКлиента КАК ЗаказКлиента
        ГДЕ
            ЗаказКлиента.Сделка.ПБ24_id_bitrix > 0
            И ЗаказКлиента.ПометкаУдаления = ЛОЖЬ
            И ЗаказКлиента.Проведен = ИСТИНА
            {zk_mark}
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
            ЗаказКлиента.Ссылка КАК Ссылка,
            ЗаказКлиента.ДатаОтгрузки КАК ДатаОтгрузки,
            ЗаказКлиента.НеОтгружатьЧастями КАК НеОтгружатьЧастями
        ПОМЕСТИТЬ ВТ_ЗКСоед
        ИЗ
            ВТ_ЗКОтбор КАК ВТ_ЗКОтбор
                ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказКлиента КАК ЗаказКлиента
                ПО ВТ_ЗКОтбор.Ссылка = ЗаказКлиента.Ссылка
        ГДЕ
            ЗаказКлиента.НеОтгружатьЧастями = ИСТИНА

        ОБЪЕДИНИТЬ ВСЕ

        ВЫБРАТЬ
            ЗаказКлиентаТовары.Ссылка.Ссылка,
            МАКСИМУМ(ЗаказКлиентаТовары.ДатаОтгрузки),
            ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями
        ИЗ
            ВТ_ЗКОтбор КАК ВТ_ЗКОтбор
                ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказКлиента.Товары КАК ЗаказКлиентаТовары
                ПО ВТ_ЗКОтбор.Ссылка = ЗаказКлиентаТовары.Ссылка
        ГДЕ
            ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями = ЛОЖЬ

        СГРУППИРОВАТЬ ПО
            ЗаказКлиентаТовары.Ссылка.Ссылка,
            ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
            СУММА(ВТ_ЗКСоед.Ссылка.СуммаДокумента) КАК СуммаЗК,
            МАКСИМУМ(ВТ_ЗКСоед.ДатаОтгрузки) КАК ДатаОтгрузкиЗК,
            ВТ_ЗКСоед.Ссылка.Сделка.ПБ24_id_bitrix КАК СсылкаСделкаПБ24_id_bitrixЗК,
            МАКСИМУМ(ВТ_ЗКСоед.Ссылка.ВерсияДанных) КАК ВерсияДанныхЗК
        ПОМЕСТИТЬ ВТ_ЗКГр
        ИЗ
            ВТ_ЗКСоед КАК ВТ_ЗКСоед

        СГРУППИРОВАТЬ ПО
            ВТ_ЗКСоед.Ссылка.Сделка.ПБ24_id_bitrix
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
        КоммерческоеПредложениеКлиенту.Статус КАК Статус,
            КоммерческоеПредложениеКлиенту.Ссылка КАК Ссылка,
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК ID,
            КоммерческоеПредложениеКлиенту.Сделка.Ссылка КАК СделкаСсылка,
            КоммерческоеПредложениеКлиенту.ВерсияДанных КАК ВерсияДанныхКП,
            КоммерческоеПредложениеКлиенту.СуммаДокумента КАК СуммаДокументаКП,
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_СтадияБ24.Код КАК СделкаПБ24_СтадияБ24Код,
            ВТ_ДатыИзКП.СрокПоставки КАК СрокПоставкиПоКП,
            ВТ_ЗКГр.СуммаЗК КАК СуммаЗК,
            ВТ_ЗКГр.ДатаОтгрузкиЗК КАК ДатаОтгрузкиЗК,
            ВТ_ЗКГр.ВерсияДанныхЗК КАК ВерсияДанныхЗК,
            ВЫБОР
                КОГДА ЕСТЬNULL(ВТ_ЗКГр.ВерсияДанныхЗК, КоммерческоеПредложениеКлиенту.ВерсияДанных) > КоммерческоеПредложениеКлиенту.ВерсияДанных
                    ТОГДА ЕСТЬNULL(ВТ_ЗКГр.ВерсияДанныхЗК, КоммерческоеПредложениеКлиенту.ВерсияДанных)
                ИНАЧЕ КоммерческоеПредложениеКлиенту.ВерсияДанных
            КОНЕЦ КАК МаксВерсияДанных
        ИЗ
            ВТ_КППоДатеУник КАК ВТ_КППоДатеУник
                ЛЕВОЕ СОЕДИНЕНИЕ Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
                    ЛЕВОЕ СОЕДИНЕНИЕ ВТ_ДатыИзКП КАК ВТ_ДатыИзКП
                    ПО (ВТ_ДатыИзКП.Ссылка = КоммерческоеПредложениеКлиенту.Ссылка)
                ПО (ВТ_КППоДатеУник.Дата = КоммерческоеПредложениеКлиенту.Дата)
                    И (ВТ_КППоДатеУник.СделкаПБ24_id_bitrix = КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix)
                ЛЕВОЕ СОЕДИНЕНИЕ ВТ_ЗКГр КАК ВТ_ЗКГр
                ПО (ВТ_ЗКГр.СсылкаСделкаПБ24_id_bitrixЗК = КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix)

        СГРУППИРОВАТЬ ПО
            КоммерческоеПредложениеКлиенту.Ссылка,
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix,
            КоммерческоеПредложениеКлиенту.СуммаДокумента,
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_СтадияБ24.Код,
            ВТ_ДатыИзКП.СрокПоставки,
            ВТ_ЗКГр.СуммаЗК,
            ВТ_ЗКГр.ДатаОтгрузкиЗК,
            ВТ_ЗКГр.ВерсияДанныхЗК,
            КоммерческоеПредложениеКлиенту.ВерсияДанных

        УПОРЯДОЧИТЬ ПО
            МаксВерсияДанных ASC
        """
        query = f"""

        ВЫБРАТЬ
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК СделкаПБ24_id_bitrix
        ПОМЕСТИТЬ ВТ_фильтр_сделок
        ИЗ
        	Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
        ГДЕ
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix > 0
        	И КоммерческоеПредложениеКлиенту.СуммаДокумента > 0
        	И КоммерческоеПредложениеКлиенту.ПометкаУдаления = ЛОЖЬ
        	И КоммерческоеПредложениеКлиенту.Проведен = ИСТИНА
        	{kp_version}

        СГРУППИРОВАТЬ ПО
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix

        ОБЪЕДИНИТЬ ВСЕ

        ВЫБРАТЬ
        	ЗаказКлиента.Сделка.ПБ24_id_bitrix
        ИЗ
        	Документ.ЗаказКлиента КАК ЗаказКлиента
        ГДЕ
        	ЗаказКлиента.Сделка.ПБ24_id_bitrix > 0
        	И ЗаказКлиента.ПометкаУдаления = ЛОЖЬ
        	И ЗаказКлиента.Проведен = ИСТИНА
        	{zk_version}
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ РАЗЛИЧНЫЕ
        	ВТ_фильтр_сделок.СделкаПБ24_id_bitrix КАК СделкаПБ24_id_bitrix
        ПОМЕСТИТЬ ВТ_фильтр_сделок_Гр
        ИЗ
        	ВТ_фильтр_сделок КАК ВТ_фильтр_сделок
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
        	МАКСИМУМ(КоммерческоеПредложениеКлиенту.Дата) КАК Дата,
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК СделкаПБ24_id_bitrix
        ПОМЕСТИТЬ ВТ_КППоДатеУник
        ИЗ
        	ВТ_фильтр_сделок_Гр КАК ВТ_фильтр_сделок_Гр
        		ЛЕВОЕ СОЕДИНЕНИЕ Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
        		ПО ВТ_фильтр_сделок_Гр.СделкаПБ24_id_bitrix = КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix

        СГРУППИРОВАТЬ ПО
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
        	МАКСИМУМ(КоммерческоеПредложениеКлиентуТовары.СрокПоставки) КАК СрокПоставки,
        	КоммерческоеПредложениеКлиентуТовары.Ссылка КАК Ссылка
        ПОМЕСТИТЬ ВТ_ДатыИзКП
        ИЗ
        	ВТ_фильтр_сделок_Гр КАК ВТ_фильтр_сделок_Гр
        		ЛЕВОЕ СОЕДИНЕНИЕ Документ.КоммерческоеПредложениеКлиенту.Товары КАК КоммерческоеПредложениеКлиентуТовары
        		ПО (КоммерческоеПредложениеКлиентуТовары.Ссылка.Сделка.ПБ24_id_bitrix = ВТ_фильтр_сделок_Гр.СделкаПБ24_id_bitrix)
        ГДЕ
        	КоммерческоеПредложениеКлиентуТовары.Ссылка.ВариантУказанияСрокаПоставки = ЗНАЧЕНИЕ(Перечисление.ВариантыСроковПоставкиКоммерческихПредложений.УказываетсяНаОпределеннуюДату)

        СГРУППИРОВАТЬ ПО
        	КоммерческоеПредложениеКлиентуТовары.Ссылка
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
        	ЗаказКлиента.Ссылка КАК Ссылка,
        	ЗаказКлиента.НеОтгружатьЧастями КАК НеОтгружатьЧастями
        ПОМЕСТИТЬ ВТ_ЗКОтбор
        ИЗ
        	ВТ_фильтр_сделок_Гр КАК ВТ_фильтр_сделок_Гр
        		ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказКлиента КАК ЗаказКлиента
        		ПО (ЗаказКлиента.Сделка.ПБ24_id_bitrix = ВТ_фильтр_сделок_Гр.СделкаПБ24_id_bitrix)
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
        	ЗаказКлиента.Ссылка КАК Ссылка,
        	ЗаказКлиента.ДатаОтгрузки КАК ДатаОтгрузки,
        	ЗаказКлиента.НеОтгружатьЧастями КАК НеОтгружатьЧастями
        ПОМЕСТИТЬ ВТ_ЗКСоед
        ИЗ
        	ВТ_ЗКОтбор КАК ВТ_ЗКОтбор
        		ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказКлиента КАК ЗаказКлиента
        		ПО ВТ_ЗКОтбор.Ссылка = ЗаказКлиента.Ссылка
        ГДЕ
        	ЗаказКлиента.НеОтгружатьЧастями = ИСТИНА

        ОБЪЕДИНИТЬ ВСЕ

        ВЫБРАТЬ
        	ЗаказКлиентаТовары.Ссылка.Ссылка,
        	МАКСИМУМ(ЗаказКлиентаТовары.ДатаОтгрузки),
        	ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями
        ИЗ
        	ВТ_ЗКОтбор КАК ВТ_ЗКОтбор
        		ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказКлиента.Товары КАК ЗаказКлиентаТовары
        		ПО ВТ_ЗКОтбор.Ссылка = ЗаказКлиентаТовары.Ссылка
        ГДЕ
        	ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями = ЛОЖЬ

        СГРУППИРОВАТЬ ПО
        	ЗаказКлиентаТовары.Ссылка.Ссылка,
        	ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
        	СУММА(ВТ_ЗКСоед.Ссылка.СуммаДокумента) КАК СуммаЗК,
        	МАКСИМУМ(ВТ_ЗКСоед.ДатаОтгрузки) КАК ДатаОтгрузкиЗК,
        	ВТ_ЗКСоед.Ссылка.Сделка.ПБ24_id_bitrix КАК СсылкаСделкаПБ24_id_bitrixЗК,
        	МАКСИМУМ(ВТ_ЗКСоед.Ссылка.ВерсияДанных) КАК ВерсияДанныхЗК
        ПОМЕСТИТЬ ВТ_ЗКГр
        ИЗ
        	ВТ_ЗКСоед КАК ВТ_ЗКСоед

        СГРУППИРОВАТЬ ПО
        	ВТ_ЗКСоед.Ссылка.Сделка.ПБ24_id_bitrix
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
        	КоммерческоеПредложениеКлиенту.Ссылка КАК Ссылка,
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК ID,
        	КоммерческоеПредложениеКлиенту.Сделка.Ссылка КАК СделкаСсылка,
        	КоммерческоеПредложениеКлиенту.ВерсияДанных КАК ВерсияДанныхКП,
        	КоммерческоеПредложениеКлиенту.СуммаДокумента КАК СуммаДокументаКП,
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_СтадияБ24.Код КАК СделкаПБ24_СтадияБ24Код,
        	ВТ_ДатыИзКП.СрокПоставки КАК СрокПоставкиПоКП,
            ЕСТЬNULL(ВТ_ЗКГр.СуммаЗК, 0) КАК СуммаЗК,
        	ВТ_ЗКГр.ДатаОтгрузкиЗК КАК ДатаОтгрузкиЗК,
        	ВТ_ЗКГр.ВерсияДанныхЗК КАК ВерсияДанныхЗК,
        	ВЫБОР
        		КОГДА ЕСТЬNULL(ВТ_ЗКГр.ВерсияДанныхЗК, КоммерческоеПредложениеКлиенту.ВерсияДанных) > КоммерческоеПредложениеКлиенту.ВерсияДанных
        			ТОГДА ЕСТЬNULL(ВТ_ЗКГр.ВерсияДанныхЗК, КоммерческоеПредложениеКлиенту.ВерсияДанных)
        		ИНАЧЕ КоммерческоеПредложениеКлиенту.ВерсияДанных
        	КОНЕЦ КАК МаксВерсияДанных,
        	КоммерческоеПредложениеКлиенту.Сделка.Закрыта КАК СделкаЗакрыта
        ИЗ
        	ВТ_КППоДатеУник КАК ВТ_КППоДатеУник
        		ЛЕВОЕ СОЕДИНЕНИЕ Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
        			ЛЕВОЕ СОЕДИНЕНИЕ ВТ_ДатыИзКП КАК ВТ_ДатыИзКП
        			ПО (ВТ_ДатыИзКП.Ссылка = КоммерческоеПредложениеКлиенту.Ссылка)
        		ПО (ВТ_КППоДатеУник.Дата = КоммерческоеПредложениеКлиенту.Дата)
        			И (ВТ_КППоДатеУник.СделкаПБ24_id_bitrix = КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix)
        		ЛЕВОЕ СОЕДИНЕНИЕ ВТ_ЗКГр КАК ВТ_ЗКГр
        		ПО (ВТ_ЗКГр.СсылкаСделкаПБ24_id_bitrixЗК = КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix)

        СГРУППИРОВАТЬ ПО
        	КоммерческоеПредложениеКлиенту.Ссылка,
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix,
        	КоммерческоеПредложениеКлиенту.СуммаДокумента,
        	КоммерческоеПредложениеКлиенту.Сделка.ПБ24_СтадияБ24.Код,
        	ВТ_ДатыИзКП.СрокПоставки,
        	ВТ_ЗКГр.СуммаЗК,
        	ВТ_ЗКГр.ДатаОтгрузкиЗК,
        	ВТ_ЗКГр.ВерсияДанныхЗК,
        	КоммерческоеПредложениеКлиенту.ВерсияДанных,
        	КоммерческоеПредложениеКлиенту.Сделка.Ссылка,
        	КоммерческоеПредложениеКлиенту.Сделка.Закрыта

        УПОРЯДОЧИТЬ ПО
        	МаксВерсияДанных УБЫВ
        """
        code, response = AEC.get_wet_request(text=query)
        return response

    def fill_deals_with_relationships(self):
        bucket_data = get_config_data('./deal_bucket.pickle')
        self.ZK_KP_DEALS_mark = bucket_data.get(self.KEY_1C_LAST_MODIFY_ZK_KP_MARK)
        self.__zk_kp_deals_list = bucket_data.get(self.KEY_1C_LAST_MODIFY_ZK_KP_DATA)
        if not self.__zk_kp_deals_list:
            self.__zk_kp_deals_list = self.dict_deals_by_id(self.get_deals_by_relation_zk_kp()['data'])
            self.zk_kp_deal_id_modified = set(self.__zk_kp_deals_list.keys())
        if not self.ZK_KP_DEALS_mark and self.__zk_kp_deals_list:
            self.ZK_KP_DEALS_mark = self.get_last_mark(self.__zk_kp_deals_list.values())
        # if not self.check_deals_keys(): # TODO если ключи не совпадают пересобрать выборку
        #     self.__deals_list = self.dict_deals_by_id(self.get_all_deals())
        if self.ZK_KP_DEALS_mark:
            last_updates = self.get_deals_by_relation_zk_kp(self.ZK_KP_DEALS_mark)
            for item in last_updates['data']:
                deal_id = item['ID']
                if str(deal_id) not in self.__zk_kp_deals_list:
                    self.__zk_kp_deals_list[str(deal_id)] = item
                    self.zk_kp_deal_id_modified.add(deal_id)
                    continue

                for key, val in item.items():
                    if val not in ('', '0', None):
                        self.__zk_kp_deals_list[str(deal_id)][key] = val
                self.zk_kp_deal_id_modified.add(deal_id)
        put_config_data(self.KEY_1C_LAST_MODIFY_ZK_KP_MARK, self.ZK_KP_DEALS_mark, filename='./deal_bucket.pickle')
        put_config_data(self.KEY_1C_LAST_MODIFY_ZK_KP_DATA, self.__zk_kp_deals_list, filename='./deal_bucket.pickle')
        return self.__zk_kp_deals_list

    def dict_deals_by_id(self, deals):
        data_b24 = {}
        for item_b24 in deals:
            data_b24[str(item_b24['ID'])] = item_b24
        return data_b24


def last_update_time_from_env(update: bool = False):
    var = os.environ.get(ENV_LAST_UPDATE_TIME)
    if var is None:
        delta = 1 if update else INTERVAL_DAYS
        current_datetime = datetime.now() - timedelta(days=delta)
        formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M")
        os.environ[ENV_LAST_UPDATE_TIME] = formatted_datetime
    else:
        formatted_datetime = var
    return formatted_datetime

def deal_values(queue: str, bucket: B24Bucket):
    make_deal_key = lambda deal: f'{deal["ID"]}|{deal["STAGE_ID"]}'
    data_for_update = {}
    for deal_id in bucket.set_id_modified:
        deal = bucket.deals.get(str(deal_id))
        if deal['CLOSED'] == "Y":
            deal_id = deal.get('ID')
            deal_stage = deal.get('STAGE_ID')
            deal_last_modify = deal.get('DATE_MODIFY')
            data_for_update[f'{deal_id}|{deal_stage}|{deal_last_modify}'] = deal
    return data_for_update



def action_deal_close(task: dict[str, str]) -> bool:
    status = 'ВРаботе'
    status_b24 = task[status_key]
    task_id = task['ID']

    ref_key = get_deal_ref_key(task_id)
    if not ref_key:
        logging.info(f'Не найден ref_key сделки номер {task_id}')
        return True

    logging.info(f'{PREFIX_LOG}\nОбработка сделки номер {task_id} с Ref_Key: {ref_key}')
    if len(status_b24.split(':')) > 1:
        letter, num = status_b24.split(':')
    else:
        letter = 'C'
        num = status_b24
    status_full_name = False
    if num == 'NEW':
        return True
    if num == 'WON':
        status = 'Выиграна'
    elif num == 'LOSE' or int(num) >= 9:
        status = 'Проиграна'
        status_list = F.deploy_dict_c(crm.deal_status_all()['result'], 'STATUS_ID')
        if dic := status_list.get(status_b24):
            status_full_name = dic.get('NAME')
    resp = set_client_order_close_state(
        ERP_SRV,
        ref_key, # ref_key
        state=status,
        close=True,
        reason_lose=status_full_name
    )
    logging.info(f'Обработка завершена с статусом {resp}')
    return resp == 200


def action_end_deal_status(task) -> bool:
    if closed_key in task and task[closed_key] == 'Y':
        return action_deal_close(task)

def bad_attempt_upgrade_values():
    response = CSQ.custom_request_c(
        db_files,
        'SELECT * FROM exchange WHERE finished = 0',
        rez_dict=True
    )
    if isinstance(response, list):
        return response
    return []

def action_for_bad_attempt_upgrade(task):
    deal_id = task.get('ID')
    if deal_id is not None:
        return crm.deal_update(deal_id, task)


def get_deal_ref_key(deal_id: str | int) -> str:
    result = crm.deal_one(deal_id)
    if 'result' in result and ref_key_pk in result['result']:
        return result['result'][ref_key_pk]


class Client1c:
    def __init__(self):
        from project_cust_38 import Cust_odata_erp as COE
        self.client = COE.OrdersComposit(srv_name='ERP')

    def get_data_version_mark_by_ref_key_deal(self, ref_key: str):
        code, resp = self.client.get_response(
            doc_name=f'Catalog_СделкиСКлиентами(guid{ref_key!r})',
            wet_filtr=f"?$select=DataVersion",
            with_cod=True
        )
        if code == 200:
            return resp
    def get_last_deals(self, mark: str = 'AAAAAAPiQ70=',
                       select: list[str] = ('ТКП_Тип_Key', 'ВидНоменклатуры/Description', 'Организация/Description', 'Сделка/Ref_Key',
                                            'Сделка/ПБ24_id_bitrix', 'Сделка/DataVersion', 'Сделка/ПБ24_СтадияБ24_Key', 'Сделка/Description')
                       ):
        query = """
        ВЫБРАТЬ
            ПЕРВЫЕ 9000
            КоммерческоеПредложениеКлиенту.ТКП_Тип.Наименование КАК ТКП_ТипНаименование,
            КоммерческоеПредложениеКлиенту.Организация.Наименование КАК ОрганизацияНаименование,
            УНИКАЛЬНЫЙИДЕНТИФИКАТОР(КоммерческоеПредложениеКлиенту.Сделка.Ссылка) КАК СделкаСсылка,
            КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК СделкаПБ24_id_bitrix,
            КоммерческоеПредложениеКлиенту.Сделка.ВерсияДанных КАК СделкаВерсияДанных,
            УНИКАЛЬНЫЙИДЕНТИФИКАТОР(КоммерческоеПредложениеКлиенту.Сделка.ПБ24_СтадияБ24.Ссылка) КАК СделкаПБ24_СтадияБ24Ссылка,
            КоммерческоеПредложениеКлиенту.Сделка.Наименование КАК СделкаНаименование
        ИЗ
            Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
        УПОРЯДОЧИТЬ ПО СделкаВерсияДанных УБЫВ"""

        code, data = AEC.get_wet_request(query)


        # order_by = '$orderby=Сделка/DataVersion asc'
        # filtr = '&$filter=DeletionMark eq false'
        # if mark:
        #     filtr = f'&$filter=DataVersion ge {mark!r} and DeletionMark eq false'
        # code, resp = self.client.get_response(
        #     doc_name='Document_КоммерческоеПредложениеКлиенту',
        #     wet_filtr=f"?$select={select}{filtr}&$expand=ВидНоменклатуры,Организация,Сделка&{order_by}",
        #     with_cod=True
        # )

        if code == 200:
            return data['data']

    def get_deal_by_ref(self, ref_key,
                       select: list[str] = ['ВидНоменклатуры/Description', 'Организация/Description', 'Сделка/Ref_Key',
                                            'Сделка/ПБ24_id_bitrix', 'Сделка/DataVersion', 'Сделка/Description',
                                            'Сделка/ПБ24_СтадияБ24_Key']
                       ):
        select = ','.join(select)
        filter = f'$filter=Сделка_Key eq guid{ref_key!r}'
        expand = f'$expand=ВидНоменклатуры,Организация,Сделка'
        code, resp = self.client.get_response(
            doc_name=f'Document_КоммерческоеПредложениеКлиенту',
            wet_filtr=f"?$select={select}&{expand}&{filter}",
            with_cod=True
        )
        if code == 200:
            return resp
        print()

    def update_deal_stage(self, deal_id: int = 14449, deal_stage: str = ''):
        url = f'http://srv-1c:8088/ERP/ru_RU/hs/SDE/Sdelka/?id_bitrix={deal_id}'
        response = requests.patch(url=url, json={'stage': deal_stage}, auth=(self.client.user, self.client.pswd))
        return response.json()

client = Client1c()


def get_val_for_update_organization_and_type_tkp(set_parsed_refs: set[str], bucket: B24Bucket):
    logging.info(f'[get_val_for_update_organization_and_type_tkp] Получение значений конец найдено: {len(bucket.set_id_modified)}')
    data = {}
    data_b24 = bucket.deals
    for b24_id in bucket.set_id_modified:
        item = data_b24.get(str(b24_id))
        ref_key = item['UF_CRM_1712643377']
        if ref_key not in set_parsed_refs:
            if ref_key is None:
                continue
            deal = client.get_deal_by_ref(ref_key)
            if deal == []:
                continue
            type_tkp_1c = None
            if isinstance(deal[0]['ВидНоменклатуры'], dict):
                type_tkp_1c = deal[0]['ВидНоменклатуры']['Description']
            data[f'{b24_id}'] = {
                'organization_b24': item['UF_CRM_1737727925'],
                'type_tkp_b24': item['UF_CRM_1737711083528'],
                'stage_id_b24': item['STAGE_ID'],
                'type_tkp_1c': type_tkp_1c,
                'organization_1c': deal[0]['Организация']['Description'],
                'ref_stage_1c': deal[0]['Сделка']['ПБ24_СтадияБ24_Key'],
                'description': deal[0]['Сделка']['Description'],
                'b24_id': b24_id,
                'current_mark': deal[0]['Сделка']['DataVersion'],
                'ref_key_deal': deal[0]['Сделка']['Ref_Key'],
            }
    return data

def accumulate_response(deals: list[dict]): # STAGE 1.2 Фильтрация данных
    """
    1. Выборка deals должна быть по orderby DataVersion asc (от младшего к старшему)
    2. При итерации повторяющие сделки накладываются на младшую по ключу Ref_Key_1c: last_deal_idx
    3. Возвращается генератор сделок входящие в выборку последних уникальных индексов
    """
    unique_keys = {}
    for cur_row_idx, item in enumerate(deals):
        if item['Сделка'] is None:
            continue
        ref_key_deal = item['Сделка']['Ref_Key']
        unique_keys[ref_key_deal] = cur_row_idx
    unique_last_values = tuple(unique_keys.values())
    return (deal for idx, deal in enumerate(deals) if idx in unique_last_values)

def get_deal_values_by_data_version_mark(queue: str, bucket: B24Bucket):
    data_version = get_last_data_version(queue)
    response_1c = client.get_last_deals(mark=data_version)
    # response_1c = accumulate_response(response_1c)
    data_b24 = bucket.deals
    last_mark = data_version
    ref_story = set()
    data = {}
    for comm in response_1c:
        if not comm['ТКП_ТипНаименование']:
            continue
        if not comm['ОрганизацияНаименование']:
            continue
        type_tkp = comm['ТКП_ТипНаименование']
        organization = comm['ОрганизацияНаименование']
        ref_stage_1c = comm['СделкаПБ24_СтадияБ24Ссылка']
        description = comm['СделкаНаименование']

        current_mark = comm['СделкаВерсияДанных']
        ref_key_deal = comm['СделкаСсылка']

        b24_id = comm['СделкаПБ24_id_bitrix']
        if str(b24_id) == '0':
            continue
        # deal = crm.deal_one(b24_id)['result']
        deal = data_b24.get(str(b24_id))
        if not deal:
            continue
        b24_type_tkp = deal['UF_CRM_1737711083528']
        b24_stage_id = deal['STAGE_ID']
        b24_organization = deal['UF_CRM_1737727925']
        data[f'{b24_id}'] = {
            'type_tkp_1c': type_tkp,
            'organization_1c': organization,
            'ref_stage_1c': ref_stage_1c,
            'description': description,

            'current_mark': current_mark,
            'ref_key_deal': ref_key_deal,
            'type_tkp_b24': b24_type_tkp,
            'stage_id_b24': b24_stage_id,
            'organization_b24':b24_organization,
            'b24_id': b24_id,
        }
        ref_story.add(ref_key_deal)
        try:
            if not last_mark or F.decode_1c_data_version_attribute(last_mark) < F.decode_1c_data_version_attribute(current_mark):
                last_mark = current_mark
                put_last_data_version(queue=queue, data_version=last_mark)
        except Exception as e:
            print(e)
    data.update(get_val_for_update_organization_and_type_tkp(ref_story, bucket))
    return data

def task_logger(task_name: str):
    def wrap_fn(fn):
        def execute(task, *args, **kwargs):
            break_line = '=' * 36
            # logging.info(break_line)
            # logging.info(f'[{fn.__name__}][{task_name}]Начало обработки события')
            # task_credentials = '\n\t'.join(f'{key}: {val}' for key, val in task.items())
            # logging.info(f'{task_credentials}')
            result = fn(task, *args, **kwargs)
            is_success_str = 'Удачно' if result else 'Неудачно'
            # logging.info(f'[{fn.__name__}][{task_name}]Конец обработки {is_success_str!r}')
            # logging.info(break_line)
            return result
        return execute
    return wrap_fn

def update_inconsistencies_b24(
        b24_id: int | str,
        type_tkp_b24: str,
        type_tkp_1c: str,
        organization_b24: str,
        organization_1c: str,
        description: str
):
    credentials = {}
    if type_tkp_b24 != type_tkp_1c:
        logging.info(f'Сделка: {description!r} с id: {b24_id}| Несоответствие поля "Тип ТКП"| Значение 1С: {type_tkp_1c!r}| Значение Б24: {type_tkp_b24!r} ')
        credentials['UF_CRM_1737711083528'] = type_tkp_1c
    if organization_b24 != organization_1c:
        logging.info(f'Сделка: {description!r} с id: {b24_id}| Несоответствие поля "Организация"| Значение 1С: {organization_1c!r}| Значение Б24: {organization_b24!r} ')
        credentials['UF_CRM_1737727925'] = organization_1c
    if not credentials:
        return True
    else:
        logging.info(f'[update_inconsistencies_b24] Сделка {b24_id} найдены несоответсвия {credentials}')
        response = crm.deal_update(b24_id, {
            'FIELDS': credentials
        })
        return response
RESULT_STAGES = {

}
def update_inconsistencies_1c(b24_id: int | str, ref_stage_1c: str, stage_id_b24: str):
    stages = {
        'C1:NEW': 'dd7a619b-da6f-11ef-85fe-00d861dd2b4a',
        'C1:1': '7e0b0e9e-da6f-11ef-85fe-00d861dd2b4a',
        'C1:2': 'b097e9d1-da6f-11ef-85fe-00d861dd2b4a',
        'C1:3': 'b828ddf3-da6f-11ef-85fe-00d861dd2b4a',
        'C1:5': 'c49ce3d2-da6f-11ef-85fe-00d861dd2b4a',
        'C1:6': 'c49ce503-da6f-11ef-85fe-00d861dd2b4a',
        'C1:7': 'cadbb8d5-da6f-11ef-85fe-00d861dd2b4a',
        'C1:8': 'd110c2d0-da6f-11ef-85fe-00d861dd2b4a',
        'C1:9': 'd74c39d5-da6f-11ef-85fe-00d861dd2b4a',
        'C1:WON': 'e3c3c5b8-da6f-11ef-85fe-00d861dd2b4a',
        'C1:10': '84036069-da6f-11ef-85fe-00d861dd2b4a',
        'C1:11': '89fd5eb4-da6f-11ef-85fe-00d861dd2b4a',
        'C1:15': 'a9a7e7df-da6f-11ef-85fe-00d861dd2b4a',
        'C1:LOSE': 'd74c39e5-da6f-11ef-85fe-00d861dd2b4a',
    }
    ref_stage = stages.get(stage_id_b24, '')
    try:
        if ref_stage == '' or ref_stage != ref_stage_1c:
            response_update_stage = client.update_deal_stage(b24_id, stage_id_b24)
            if response_update_stage['КодСостояния'] in (200, 404):
                logging.info(f'[update_inconsistencies_1c] [deal_id={b24_id}] Обновление прошло успешно новая стадия {stage_id_b24}')
                return True
            else:
                logging.info(f'[update_inconsistencies_1c] [deal_id={b24_id}] Неудалось установить стадию {stage_id_b24}')
        else:
            return True
    except Exception as e:
        return False


@task_logger('Синхронизация полей сделки 1С->Б24(Организация, ТипТКП) Б24->1С (Стадия)')
def update_organization_and_type_tkp(task: dict):
    organization_b24 = task['organization_b24']
    type_tkp_b24 = task['type_tkp_b24']
    stage_id_b24 = task['stage_id_b24']
    type_tkp_1c = task['type_tkp_1c']
    organization_1c = task['organization_1c']
    ref_stage_1c = task['ref_stage_1c']
    b24_id = task['b24_id']
    description = task['description']
    resp_b24 = update_inconsistencies_b24(
        b24_id=b24_id,
        type_tkp_b24=type_tkp_b24,
        type_tkp_1c=type_tkp_1c,
        organization_b24=organization_b24,
        organization_1c=organization_1c,
        description=description
    )
    # resp_1c = update_inconsistencies_1c(b24_id=b24_id, ref_stage_1c=ref_stage_1c, stage_id_b24=stage_id_b24)
    return resp_b24 # and resp_1c

from project_cust_38 import api_erp_commands as AEC


def get_config_data(filename: str = './deal_config.pickle'):
    try:
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return {}
def get_last_data_version(queue: str):
    data_version = ''
    try:
        data = get_config_data()
        unchecked_value = data[queue]
        check = F.decode_1c_data_version_attribute(data_version)
        data_version = unchecked_value
    except Exception: ...
    return data_version

def put_config_data(key, data, filename: str = 'now'):
    prev_data = get_config_data(filename=filename)
    with open(filename, 'wb+') as f:
        try:
            prev_data[key] = data
            pickle.dump(prev_data, f)
        except Exception: ...

def put_last_data_version(queue: str, data_version: str):
    data = get_config_data()
    with open('./deal_config.pickle', 'wb+') as f:
        try:
            check = F.decode_1c_data_version_attribute(data_version)
            data[queue] = data_version
            pickle.dump(data, f)
        except Exception: ...

def get_last_changes_date_and_sum_ZK_TKP(queue: str, bucket: B24Bucket):
    # data_version = get_last_data_version(queue=queue)
    # commerc_mark = commerc_ssilc = zk_mark = ''
    # data_version = ''
    # if data_version:
    #     commerc_mark = f'И КоммерческоеПредложениеКлиенту.ВерсияДанных >= "{data_version}"'
    #     commerc_ssilc = f'И КоммерческоеПредложениеКлиентуТовары.Ссылка.ВерсияДанных >= "{data_version}"'
    #     zk_mark = f'И ЗаказКлиента.ВерсияДанных >= "{data_version}"'
    # query = f"""
    # ВЫБРАТЬ
    #     МАКСИМУМ(КоммерческоеПредложениеКлиенту.Дата) КАК Дата,
    #     КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК СделкаПБ24_id_bitrix
    # ПОМЕСТИТЬ ВТ_КППоДатеУник
    # ИЗ
    #     Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
    # ГДЕ
    #     КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix > 0
    #     И КоммерческоеПредложениеКлиенту.СуммаДокумента > 0
    #     И КоммерческоеПредложениеКлиенту.ПометкаУдаления = ЛОЖЬ
    #     И КоммерческоеПредложениеКлиенту.Проведен = ИСТИНА
    #     {commerc_mark}
    #
    # СГРУППИРОВАТЬ ПО
    #     КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix
    # ;
    #
    # ////////////////////////////////////////////////////////////////////////////////
    # ВЫБРАТЬ
    #     МАКСИМУМ(КоммерческоеПредложениеКлиентуТовары.СрокПоставки) КАК СрокПоставки,
    #     КоммерческоеПредложениеКлиентуТовары.Ссылка КАК Ссылка
    # ПОМЕСТИТЬ ВТ_ДатыИзКП
    # ИЗ
    #     Документ.КоммерческоеПредложениеКлиенту.Товары КАК КоммерческоеПредложениеКлиентуТовары
    # ГДЕ
    #     КоммерческоеПредложениеКлиентуТовары.Ссылка.Сделка.ПБ24_id_bitrix > 0
    #     И КоммерческоеПредложениеКлиентуТовары.Ссылка.СуммаДокумента > 0
    #     И КоммерческоеПредложениеКлиентуТовары.Ссылка.ПометкаУдаления = ЛОЖЬ
    #     И КоммерческоеПредложениеКлиентуТовары.Ссылка.Проведен = ИСТИНА
    #     И КоммерческоеПредложениеКлиентуТовары.Ссылка.ВариантУказанияСрокаПоставки = ЗНАЧЕНИЕ(Перечисление.ВариантыСроковПоставкиКоммерческихПредложений.УказываетсяНаОпределеннуюДату)
    #     {commerc_ssilc}
    #
    # СГРУППИРОВАТЬ ПО
    #     КоммерческоеПредложениеКлиентуТовары.Ссылка
    # ;
    #
    # ////////////////////////////////////////////////////////////////////////////////
    # ВЫБРАТЬ
    #     ЗаказКлиента.Ссылка КАК Ссылка,
    #     ЗаказКлиента.НеОтгружатьЧастями КАК НеОтгружатьЧастями
    # ПОМЕСТИТЬ ВТ_ЗКОтбор
    # ИЗ
    #     Документ.ЗаказКлиента КАК ЗаказКлиента
    # ГДЕ
    #     ЗаказКлиента.Сделка.ПБ24_id_bitrix > 0
    #     И ЗаказКлиента.ПометкаУдаления = ЛОЖЬ
    #     И ЗаказКлиента.Проведен = ИСТИНА
    #     {zk_mark}
    # ;
    #
    # ////////////////////////////////////////////////////////////////////////////////
    # ВЫБРАТЬ
    #     ЗаказКлиента.Ссылка КАК Ссылка,
    #     ЗаказКлиента.ДатаОтгрузки КАК ДатаОтгрузки,
    #     ЗаказКлиента.НеОтгружатьЧастями КАК НеОтгружатьЧастями
    # ПОМЕСТИТЬ ВТ_ЗКСоед
    # ИЗ
    #     ВТ_ЗКОтбор КАК ВТ_ЗКОтбор
    #         ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказКлиента КАК ЗаказКлиента
    #         ПО ВТ_ЗКОтбор.Ссылка = ЗаказКлиента.Ссылка
    # ГДЕ
    #     ЗаказКлиента.НеОтгружатьЧастями = ИСТИНА
    #
    # ОБЪЕДИНИТЬ ВСЕ
    #
    # ВЫБРАТЬ
    #     ЗаказКлиентаТовары.Ссылка.Ссылка,
    #     МАКСИМУМ(ЗаказКлиентаТовары.ДатаОтгрузки),
    #     ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями
    # ИЗ
    #     ВТ_ЗКОтбор КАК ВТ_ЗКОтбор
    #         ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказКлиента.Товары КАК ЗаказКлиентаТовары
    #         ПО ВТ_ЗКОтбор.Ссылка = ЗаказКлиентаТовары.Ссылка
    # ГДЕ
    #     ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями = ЛОЖЬ
    #
    # СГРУППИРОВАТЬ ПО
    #     ЗаказКлиентаТовары.Ссылка.Ссылка,
    #     ЗаказКлиентаТовары.Ссылка.НеОтгружатьЧастями
    # ;
    #
    # ////////////////////////////////////////////////////////////////////////////////
    # ВЫБРАТЬ
    #     СУММА(ВТ_ЗКСоед.Ссылка.СуммаДокумента) КАК СуммаЗК,
    #     МАКСИМУМ(ВТ_ЗКСоед.ДатаОтгрузки) КАК ДатаОтгрузкиЗК,
    #     ВТ_ЗКСоед.Ссылка.Сделка.ПБ24_id_bitrix КАК СсылкаСделкаПБ24_id_bitrixЗК,
    #     МАКСИМУМ(ВТ_ЗКСоед.Ссылка.ВерсияДанных) КАК ВерсияДанныхЗК
    # ПОМЕСТИТЬ ВТ_ЗКГр
    # ИЗ
    #     ВТ_ЗКСоед КАК ВТ_ЗКСоед
    #
    # СГРУППИРОВАТЬ ПО
    #     ВТ_ЗКСоед.Ссылка.Сделка.ПБ24_id_bitrix
    # ;
    #
    # ////////////////////////////////////////////////////////////////////////////////
    # ВЫБРАТЬ
    # КоммерческоеПредложениеКлиенту.Статус КАК Статус,
    #     КоммерческоеПредложениеКлиенту.Ссылка КАК Ссылка,
    #     КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix КАК ID,
    #     КоммерческоеПредложениеКлиенту.Сделка.Ссылка КАК СделкаСсылка,
    #     КоммерческоеПредложениеКлиенту.ВерсияДанных КАК ВерсияДанныхКП,
    #     КоммерческоеПредложениеКлиенту.СуммаДокумента КАК СуммаДокументаКП,
    #     КоммерческоеПредложениеКлиенту.Сделка.ПБ24_СтадияБ24.Код КАК СделкаПБ24_СтадияБ24Код,
    #     ВТ_ДатыИзКП.СрокПоставки КАК СрокПоставкиПоКП,
    #     ВТ_ЗКГр.СуммаЗК КАК СуммаЗК,
    #     ВТ_ЗКГр.ДатаОтгрузкиЗК КАК ДатаОтгрузкиЗК,
    #     ВТ_ЗКГр.ВерсияДанныхЗК КАК ВерсияДанныхЗК,
    #     ВЫБОР
    #         КОГДА ЕСТЬNULL(ВТ_ЗКГр.ВерсияДанныхЗК, КоммерческоеПредложениеКлиенту.ВерсияДанных) > КоммерческоеПредложениеКлиенту.ВерсияДанных
    #             ТОГДА ЕСТЬNULL(ВТ_ЗКГр.ВерсияДанныхЗК, КоммерческоеПредложениеКлиенту.ВерсияДанных)
    #         ИНАЧЕ КоммерческоеПредложениеКлиенту.ВерсияДанных
    #     КОНЕЦ КАК МаксВерсияДанных
    # ИЗ
    #     ВТ_КППоДатеУник КАК ВТ_КППоДатеУник
    #         ЛЕВОЕ СОЕДИНЕНИЕ Документ.КоммерческоеПредложениеКлиенту КАК КоммерческоеПредложениеКлиенту
    #             ЛЕВОЕ СОЕДИНЕНИЕ ВТ_ДатыИзКП КАК ВТ_ДатыИзКП
    #             ПО (ВТ_ДатыИзКП.Ссылка = КоммерческоеПредложениеКлиенту.Ссылка)
    #         ПО (ВТ_КППоДатеУник.Дата = КоммерческоеПредложениеКлиенту.Дата)
    #             И (ВТ_КППоДатеУник.СделкаПБ24_id_bitrix = КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix)
    #         ЛЕВОЕ СОЕДИНЕНИЕ ВТ_ЗКГр КАК ВТ_ЗКГр
    #         ПО (ВТ_ЗКГр.СсылкаСделкаПБ24_id_bitrixЗК = КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix)
    #
    # СГРУППИРОВАТЬ ПО
    #     КоммерческоеПредложениеКлиенту.Ссылка,
    #     КоммерческоеПредложениеКлиенту.Сделка.ПБ24_id_bitrix,
    #     КоммерческоеПредложениеКлиенту.СуммаДокумента,
    #     КоммерческоеПредложениеКлиенту.Сделка.ПБ24_СтадияБ24.Код,
    #     ВТ_ДатыИзКП.СрокПоставки,
    #     ВТ_ЗКГр.СуммаЗК,
    #     ВТ_ЗКГр.ДатаОтгрузкиЗК,
    #     ВТ_ЗКГр.ВерсияДанныхЗК,
    #     КоммерческоеПредложениеКлиенту.ВерсияДанных
    #
    # УПОРЯДОЧИТЬ ПО
    #     МаксВерсияДанных ASC
    # """
    # last_mark = data_version
    # code, response = AEC.get_wet_request(text=query)
    data = {}
    data_b24 = bucket.deals
    bucket_1c = Bucket1C()
    zk_kp_data = bucket_1c.zk_kp_deal_data
    for b24_id in bucket_1c.zk_kp_deal_id_modified:
        item = zk_kp_data[str(b24_id)]

        description = item['СделкаСсылка']
        kp_version = item['ВерсияДанныхКП']
        if F.valm(item['СуммаДокументаКП']):
            kp_sum = float(F.valm(item['СуммаДокументаКП']))
        else:
            kp_sum = None
        kp_date = item['СрокПоставкиПоКП']

        zk_version = item['ВерсияДанныхЗК']
        if F.valm(item['СуммаЗК']):
            zk_sum = float(F.valm(item['СуммаЗК']))
        else:
            zk_sum = None
        zk_shipment_date = item['ДатаОтгрузкиЗК']
        deal_b24 = data_b24.get(str(b24_id))
        if not deal_b24:
            continue
        b24_shipment_date = deal_b24['UF_CRM_1712927868']
        b24_sum = float(F.valm(deal_b24['OPPORTUNITY']))
        b24_stage_id = deal_b24['STAGE_ID']
        b24_stage_in_1c = item['СделкаПБ24_СтадияБ24Код']
        data[f"{b24_id}"] = {
            'БитриксID': b24_id,
            'Б24_ДатаОтгрузки': b24_shipment_date,
            'Б24_СуммаДокумента': b24_sum,
            'Б24_Наименование': description,
            'Б24_Стадия': b24_stage_id,
            'Сделка_Стадия': b24_stage_in_1c,

            'КП_ВерсияДокумента': kp_version,
            'КП_СуммаДокумента': kp_sum,
            'КП_СрокПоставкиПоКП': kp_date,

            'ЗК_ВерсияДокумента': zk_version,
            'ЗК_ДатаОтгрузки': zk_shipment_date,
            'ЗК_СуммаДокумента': zk_sum,
        }
    return data


def update_date_and_sum_ZK_TKP(task: dict):
    null_date = '01.01.0001 0:00:00'
    STAGE_NEW_DEAL = 'C1:NEW'
    """
    Выборка фильтр:
    1. СуммаДокумента > 0
    2. Проведен
    3. Присутсвует id_bitrx24
    4. Не имеет статус ("Черновик", "Отменен")

    Ветвление:
    1. Если есть СуммаДокумента у (зк, кп) ставим статус = Выставлено ткп если ниже
    2. Если есть заказ клиента и его сумма н равна сумме Б24 -> обновить атрибут Б24
    2.1 Если нету заказа клиента и сумма кп не равна сумме Б24 -> обновить атрибут Б24
    3. Если у максимальной даты товаров ЗК есть дата и она не равна нулевой 
    3.1 Если у Б24 не выставлена дата или она не равна максимальной дате товара в ЗК -> обновить атрибут Б24
    4. Если нету ЗК и есть дата в КП -> обновить атрибут Б24
    """
    match task:
        case {
            'БитриксID': b24_id,
            'Б24_ДатаОтгрузки': b24_shipment_date,
            'Б24_СуммаДокумента': b24_sum,
            'Б24_Наименование': description,
            'Б24_Стадия': b24_stage_id,

            'КП_ВерсияДокумента': kp_version,
            'КП_СуммаДокумента': kp_sum,
            'КП_СрокПоставкиПоКП': kp_date,

            'ЗК_ВерсияДокумента': zk_version,
            'ЗК_ДатаОтгрузки': zk_shipment_date,
            'ЗК_СуммаДокумента': zk_sum,
        }:
            # Для лога
            zk_source = '1С.Document_ЗаказКлиента'
            kp_source = '1С.Document_КоммерческоеПредложениеКлиенту'

            # if (zk_sum or kp_sum) and b24_stage_id == STAGE_NEW_DEAL:
            #     update_stage_b24_on_date_1c(b24_id=b24_id, old_val=b24_stage_id, new_val='C1:1', source=kp_source,
            #                                 object_name=description)
            if zk_version and zk_sum:
                if zk_sum != b24_sum:
                    update_sum_b24_on_date_1c(b24_id=b24_id, new_val=zk_sum, old_val=b24_sum, source=zk_source,
                                              object_name=description)
            else:
                if kp_sum != b24_sum:
                    update_sum_b24_on_date_1c(b24_id=b24_id, new_val=kp_sum, old_val=b24_sum, source=kp_source,
                                              object_name=description)

            if zk_shipment_date and zk_shipment_date != null_date:
                if not b24_shipment_date:
                    if F.is_date(zk_shipment_date, '%d.%m.%Y %H:%M:%S'):
                        date_obj_1c = datetime.strptime(zk_shipment_date, '%d.%m.%Y %H:%M:%S')
                    elif F.is_date(zk_shipment_date, '%Y-%m-%dT%H:%M:%S'):
                        date_obj_1c = datetime.strptime(zk_shipment_date, '%Y-%m-%dT%H:%M:%S')
                    else:
                        return False
                    date_for_update_b24 = date_obj_1c.isoformat()
                    update_date_b24_on_date_1c(b24_id=b24_id, new_val=date_for_update_b24, old_val=b24_shipment_date,
                                               source=zk_source, object_name=description)
                else:
                    date_obj_b24 = datetime.strptime(b24_shipment_date, '%Y-%m-%dT%H:%M:%S%z')
                    if F.is_date(zk_shipment_date, '%d.%m.%Y %H:%M:%S'):
                        date_obj_1c = datetime.strptime(zk_shipment_date, '%d.%m.%Y %H:%M:%S')
                    elif F.is_date(zk_shipment_date, '%Y-%m-%dT%H:%M:%S'):
                        date_obj_1c = datetime.strptime(zk_shipment_date, '%Y-%m-%dT%H:%M:%S')
                    else:
                        return False
                    if date_obj_b24.date() != date_obj_1c.date():
                        date_for_update_b24 = date_obj_1c.isoformat()
                        update_date_b24_on_date_1c(b24_id=b24_id, new_val=date_for_update_b24,
                                                   old_val=b24_shipment_date, source=zk_source, object_name=description)
            else:
                if kp_date == null_date:
                    return True
                if not b24_shipment_date and kp_date:
                    if F.is_date(zk_shipment_date, '%d.%m.%Y %H:%M:%S'):
                        date_obj_1c = datetime.strptime(zk_shipment_date, '%d.%m.%Y %H:%M:%S')
                    elif F.is_date(zk_shipment_date, '%Y-%m-%dT%H:%M:%S'):
                        date_obj_1c = datetime.strptime(zk_shipment_date, '%Y-%m-%dT%H:%M:%S')
                    else:
                        return False
                    date_obj_b24 = datetime.strptime(b24_shipment_date, '%Y-%m-%dT%H:%M:%S%z')
                    if date_obj_b24.date() != date_obj_1c.date():
                        date_for_update_b24 = date_obj_1c.isoformat()
                        update_date_b24_on_date_1c(b24_id=b24_id, new_val=date_for_update_b24,
                                                   old_val=b24_shipment_date, source=kp_source, object_name=description)
            return True
    return False


@log_prefix_decorator(event_name='Обновление даты Б24', target='Битрикс24.Сделка.ПлановыйСрокРеализации')
def update_date_b24_on_date_1c(*, b24_id: int | str, new_val: str, old_val: str, source: str, object_name: str) -> bool:
    credentials = {'FIELDS': {'UF_CRM_1712927868': new_val}}
    return crm.deal_update(b24_id, credentials)

@log_prefix_decorator(event_name='Обновление суммы Б24', target='Битрикс24.Сделка.Сумма')
def update_sum_b24_on_date_1c(*, b24_id: int | str, new_val: str, old_val: str, source: str, object_name: str) -> bool:
    credentials = {'FIELDS': {'OPPORTUNITY': new_val}}
    return crm.deal_update(b24_id, credentials)

@log_prefix_decorator(event_name='Обновление стадии Б24', target='Битрикс24.Сделка.СтадияСделки')
def update_stage_b24_on_date_1c(*, b24_id: int | str, old_val: str, new_val: str, source: str, object_name: str) -> bool:
    credentials = {'FIELDS': {'STAGE_ID': new_val}}
    return crm.deal_update(b24_id, credentials)

from enum import Enum

class EntityType(Enum):
    ENTITY_TYPE_ID_ORDER_SUPPLIER = 1072        # 1104
    ENTITY_TYPE_ID_DELIVERY_ORDER = 1076        # 1108
    ENTITY_TYPE_ID_DELIVERY_ORDER_PACK = 1090

    OWNER_TYPE = 'T430'

    class Test(Enum):
        ENTITY_TYPE_ID_ORDER_SUPPLIER = 1104        # 1104
        ENTITY_TYPE_ID_DELIVERY_ORDER = 1108        # 1108
        ENTITY_TYPE_ID_DELIVERY_ORDER_PACK = 1126

        OWNER_TYPE = 'T450'

class CRMOrders:
    BASE_URL: str = None

    cache_type_packs = {}

    def __init__(self, is_test: bool = False):
        if is_test:
            self.BASE_URL = 'https://dev.bitrix24.kelast.ru/rest/2585/6tq57vcv71ou03r9/'
        else:
            self.BASE_URL = 'https://bitrix24.kelast.ru/rest/3342/zmoegng9gl0gp5gm/'

        self.nomenclature_crm = RecursiveResponse(is_test=is_test)

    def create_order(self, body, entity_type: EntityType | EntityType.Test) -> Optional[dict]:
        credentials = {
            'entityTypeId': entity_type.value,
            'fields': body
        }
        response = requests.post(f'{self.BASE_URL}crm.item.add', json=credentials)
        new_elem = response.json()
        match new_elem:
            case {'result': {'item': item}}:
                return item
        return None

    def get_product_rows_by_order_id(self, order_id: int):
        credentials = {
            'filter': {'=ownerType' : EntityType.OWNER_TYPE.value, '=ownerId': order_id}
        }
        response = requests.post(f'{self.BASE_URL}crm.item.productrow.list', json=credentials)
        return response.json()


    def get_order_by_xml_id(self, ref_key: str, entity_type: EntityType | EntityType.Test, addition: dict = None):
        if not isinstance(addition, dict):
            addition = {}
        credentials = {
            'entityTypeId': entity_type.value,
            'filter': {'xmlId': ref_key, **addition},
        }
        response = requests.post(f'{self.BASE_URL}crm.item.list', json=credentials)
        data = response.json()
        match data:
            case {'result': {'items': [first_item, *any_items]}}:
                return first_item
        return None

    def delete_item(self, item_id: int | str, entity_type: EntityType | EntityType.Test):
        credentials = {
            'entityTypeId': entity_type.value,
            'id': item_id,
        }
        response = requests.post(f'{self.BASE_URL}crm.item.delete', json=credentials)
        data = response.json()
        match data:
            case {'result': []}:
                return True
        return None

    def is_int(self, val):
        try:
            val = float(val)
            return True
        except Exception:
            ...
        return False

    def mutable_delivery_order(self, prepared_data):
        import datetime
        # is_filled = False
        # if prepared_data["ufCrm18PackingType"] and prepared_data["ufCrm18CountSpots"]:
        #     is_filled = True
        ref_key = prepared_data['xmlId']

        auth = ('OdataZNP', 'znp')
        document = 'Document_Д_РаспоряжениеНаДоставку'
        format_ = '?$format=json'
        filter_ = f'&$filter=Ref_Key eq guid{ref_key!r}'
        expand_ = '&$expand=КонтактноеЛицоГрузоотправителя'
        response = requests.get(
            url=f'http://srv-1c:8088/ERP/odata/standard.odata/{document}{format_}{filter_}{expand_}',
            auth=auth
        )
        data = response.json()
        match data:
            case {'value': [first_value, *any_values]}:
                if first_value['КонтактноеЛицоГрузоотправителя_Type'] == 'Edm.String':
                    name = first_value['КонтактноеЛицоГрузоотправителя']
                else:
                    name = first_value['КонтактноеЛицоГрузоотправителя_Expanded']['Description']
                tel = first_value['НомерКонтактногоЛицаГО']
                contact = f'{name}, {tel}'
                unique_number = first_value['Number']
                date = datetime.datetime.fromisoformat(first_value['Date'])
                date_str = date.strftime('%d.%m.%Y')
                title = f'{unique_number} от {date_str}'
                # if is_filled:
                #     prepared_data['title'] = title
                #     prepared_data['ufCrm18ShipperContact'] = contact
                #     return prepared_data
                # PART 2
                filter_ = f'&$filter=Товары/any(x: x/Распоряжение_Key eq guid{ref_key!r})'
                document = 'Document_Д_Упаковка'
                response = requests.get(
                    url=f'http://srv-1c:8088/ERP/odata/standard.odata/{document}{format_}{filter_}',
                    auth=auth
                )
                data_pack = response.json()
                nomens = []
                gabars = []
                pack_types = []
                count_places = 0
                weight_b = 0
                weight_n = 0
                volume = 0
                for pack_obj in data_pack['value']:
                    if not pack_obj['DeletionMark']:
                        for nomen in pack_obj['Товары']:
                            num_pack = nomen['НомерУпаковки']
                            if nomen['Распоряжение_Key'] != ref_key:
                                continue
                            if num_pack == 0:
                                continue
                            if nomen['КоличествоУпаковок'] == '0':
                                continue
                            ref_nomen = nomen['Номенклатура_Key']
                            document = 'Catalog_Номенклатура'
                            guid = f'(guid{ref_nomen!r})'
                            select_ = '&$select=Description'
                            response = requests.get(
                                url=f'http://srv-1c:8088/ERP/odata/standard.odata/{document}{guid}{format_}{select_}',
                                auth=auth
                            )
                            data = response.json()
                            nomens.append(data['Description'])
                            for pack in pack_obj['Упаковки']:
                                if num_pack == pack['НомерУпаковки']:
                                    if pack['ВидУпаковки_Key'] == 'a1eca979-b83d-11ed-8478-00d861dd2b4a':
                                        continue
                                    if pack['Габариты'].strip():
                                        gabars.append(pack['Габариты'])
                                    count_places += 1
                                    weight_b += pack['ВесБрутто']
                                    weight_n += pack['ВесНетто']
                                    volume += pack['Объем']

                                    select_ = '&$select=Description'
                                    guid = f'(guid{ref_nomen!r})'

                                    pack_type_ref = pack['ВидУпаковки_Key']
                                    if pack_type_ref not in self.cache_type_packs:
                                        document = 'Catalog_Д_ВидыУпаковки'
                                        guid = f'(guid{pack_type_ref!r})'
                                        select_ = '&$select=Description'
                                        response = requests.get(
                                            url=f'http://srv-1c:8088/ERP/odata/standard.odata/{document}{guid}{format_}{select_}',
                                            auth=auth
                                        )
                                        response = response.json()
                                        self.cache_type_packs[pack_type_ref] = response['Description']
                                    pack_types.append(self.cache_type_packs[pack_type_ref])
                form = {
                    'title': title,
                    'ufCrm18CountSpots': count_places,
                    'ufCrm18DimensionsSpots': ', '.join(gabars),
                    'ufCrm18Volume': round(volume, 3),
                    'ufCrm18NetWeigth': round(weight_n, 1),
                    'ufCrm18GrossWeight': round(weight_b, 1),
                    'ufCrm18ShipperContact': contact,
                    'ufCrm18PackingType': ', '.join(pack_types)
                }
                msg = []
                def compare(val, val2):
                    is_numeric = False
                    try:
                        float(val)
                        float(val2)
                        is_numeric = True
                    except Exception:
                        is_numeric = False
                    if is_numeric and int(val) == int(val2):
                        return True
                    return str(val) == str(val2)


                for key, value in prepared_data.items():
                    if not value:
                        continue
                    if key in form and not compare(value, form[key]):
                        msg.append(f'Несоответствие ключа: {key!r} Значение из тригера: {value} Значение из постобработки {form[key]}')
                from project_cust_38 import Cust_b24 as B24
                message = '[B]Распоряжение на доставку тест обработки[/B]\n' + '\n'.join(msg)

                B24.B24Sender().send_msg_by_chat_id('chat85751', message)
                prepared_data.update(form)
            case _:
                print('НЕ НАЙДЕНО')
        return prepared_data
    def get_changed_values(self, original_item: dict, target_item: dict):
        update_fields = {}
        if 'is_test' in original_item:
            original_item.pop('is_test')
        # original_item = self.mutable_delivery_order(prepared_data=original_item)
        for key, val in original_item.items():
            prev_val = target_item[key]
            if self.is_int(prev_val) and self.is_int(val):
                if float(prev_val) != float(val):
                    update_fields[key] = val
            else:
                if str(prev_val) != str(val):
                    update_fields[key] = str(val)
        return update_fields

    def check_apply_update(self, fields_for_update, response_data: dict) -> bool:
        not_updated_fields = set()
        match response_data:
            case {'result': {'item': new_item}}:
                if 'is_test' in new_item:
                    new_item.pop('is_test')
                if 'is_test' in fields_for_update:
                    fields_for_update.pop('is_test')
                for key, new_val in fields_for_update.items():

                    target_val = new_item[key]
                    if not new_val and not target_val:
                        continue
                    if self.is_int(target_val) and self.is_int(new_val):
                        if float(target_val) != float(new_val):
                            not_updated_fields.add(key)
                        else:
                            continue
                    else:
                        if str(target_val) != str(new_val):
                            not_updated_fields.add(key)
                        else:
                            continue

                    if target_val != new_val:
                        not_updated_fields.add(key)
            case _:
                return False
        return not bool(not_updated_fields)

    def update_order_fields(self, order_id: int, fields: dict[str, Any], entity_type: EntityType.Test | EntityType):
        response = requests.post(f'{self.BASE_URL}crm.item.update', json={
            'entityTypeId': entity_type.value,
            'id': order_id,
            'fields': fields
        })
        updated_data = response.json()
        return self.check_apply_update(fields, updated_data)

    def get_product_pos(self, ref_key: str, block: int = 27):
        url = f'{self.BASE_URL}catalog.product.list?iblockId={block}'
        response = requests.post(url, json={
            'select': ['iblockId', 'id', 'name', 'iblockSectionId', 'xmlId', 'property458'],
            'filter': {
                'xmlId': ref_key,
                'iblockId': block,
            }
        })
        data = response.json()
        match data:
            case {'result': {'products': [first_product, *_]}}:
                return first_product
        return False

    def create_product_pos(self, ref_key: str, description: str, ratio: float | str, measure: str):
        url = f'{self.BASE_URL}catalog.product.add?iblockId=27'
        measure_id = self.nomenclature_crm.get_measure_by_name(measure)
        response = requests.post(url, json={
            'fields': {
                'name': description,
                'iblockId': 27,
                'xmlId': ref_key,
                'measure': measure_id,
                'property458': {'value': ratio}
            }
        })
        data = response.json()
        match data:
            case {'result': {'element': item}}:
                return item
        return False

    def update_table_product_rows(self, order_id: int, rows: list[dict[str, Any]], source_products: list):
        url = f'{self.BASE_URL}crm.item.productrow.set?iblockId=27'
        response = requests.post(url, json={
            'ownerType' : EntityType.OWNER_TYPE.value,
            'ownerId': order_id,
            'productRows': rows
        })
        response_data = response.json()
        match response_data:
            case {'result': {'productRows': products}} if len(products) == len(source_products):
                return True
        return False

    def get_measure(self, measure: str, find_by: B24MeasureAttributes = B24MeasureAttributes.MEASURE_TITLE):
        body = {
            "filter": {find_by.value: measure}
        }
        response = requests.post(f'{self.BASE_URL}/crm.measure.list', json=body)
        if not response.ok:
            return None
        data = response.json()
        match data:
            case {'result': [{"ID": id_measure}, *others]}:
                return id_measure
        return None

    def sync_order_products(self, order_id, source_products):
        data_for_post = []
        for idx, row in enumerate(source_products):
            ref_key = row['Ref_Key']
            nomen_measure = row.get('measure_code_nomen', '')
            product = self.get_product_pos(ref_key)
            if not product:
                product = self.create_product_pos(
                    description=row['description'],
                    ref_key=row['Ref_Key'],
                    ratio=row['ratio_for_report'],
                    measure=nomen_measure
                )
                if not product:
                    return False
            measure_name = row.get('measure_code_pos')
            if measure_name == 'NULL':
                measure_name = nomen_measure

            measure_id = self.nomenclature_crm.get_measure_code_by_name(measure_name)
            data_for_post.append({
                'productId': product['id'],
                'quantity': row['count'],
                'price': row['price'],
                'measureCode': measure_id,
                "sort": idx,
                'property458': {'value': row['ratio_for_report']}
            })
        return self.update_table_product_rows(order_id, data_for_post, source_products)

def update_delivery_order_attributes(task: dict):
    crm_client = CRMOrders()
    if 'xmlId' not in task:
        return
    order = crm_client.get_order_by_xml_id(task['xmlId'], entity_type=EntityType.ENTITY_TYPE_ID_DELIVERY_ORDER)
    if 'ufCrm18Shipper2' in task:
        task['ufCrm18Shipper'] = task.pop('ufCrm18Shipper2')
    if 'ufCrm18ShippingAddress2' in task:
        task['ufCrm18ShippingAddress'] = task.pop('ufCrm18ShippingAddress2')
    if order is None:
        # task = crm_client.mutable_delivery_order(task)
        return crm_client.create_order(task, EntityType.ENTITY_TYPE_ID_DELIVERY_ORDER)
    changes = crm_client.get_changed_values(task, order)
    if not changes:
        return True
    return crm_client.update_order_fields(order['id'], changes, entity_type=EntityType.ENTITY_TYPE_ID_DELIVERY_ORDER)


def update_order_supplier_attributes(task):
    crm_client = CRMOrders()
    description = task['description']
    ref_key = task['Ref_Key']
    deletion_mark = task['DeletionMark']
    order = crm_client.get_order_by_xml_id(task['Ref_Key'], entity_type=EntityType.ENTITY_TYPE_ID_ORDER_SUPPLIER)
    if not order:
        order = crm_client.create_order(body={'title': description, 'xmlId': ref_key}, entity_type=EntityType.ENTITY_TYPE_ID_ORDER_SUPPLIER)
    products_1c = task['products']
    order_id = order['id']
    crm_client.update_order_fields(order_id, {'ufCrm_17_DELETED_1C': deletion_mark}, entity_type=EntityType.ENTITY_TYPE_ID_ORDER_SUPPLIER)
    return crm_client.sync_order_products(order_id, products_1c)


class DependenciesNomenclature:
    def __init__(self):
        self.list_nomen_types = CSQ.custom_request_c(
            CFG.Config.project.db_nomen,
            f'SELECT name, Ref_Key, ЕстьПараметры FROM ВидыНоменклатуры',
            rez_dict=True
        )
        self.dict_nomen_types_by_ref = F.deploy_dict_c(self.list_nomen_types, 'Ref_Key')


def current_iso_date():
    tz = timezone(timedelta(hours=3))
    current_time = datetime.now(tz)
    return current_time.isoformat()

def get_config_data(filename: str = './deal_config.pickle'):
    try:
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return {}

def put_config_data(key, data, filename: str = 'now'):
    prev_data = get_config_data(filename=filename)
    with open(filename, 'wb+') as f:
        try:
            prev_data[key] = data
            pickle.dump(prev_data, f)
        except Exception as e:
            print(e)

import dataclasses

@dataclasses.dataclass
class RelationAttribute:
    name_b24: Any
    name_1c: Any


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

import typing
ServiceName = typing.TypeVar('ServiceName', bound=str)

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

def update_delivery_order_pack_attributes(task: Task):
    entity_type = EntityType
    if task.is_test:
        entity_type = EntityType.Test
        return True
    crm_client = CRMOrders(is_test=task.is_test)
    credentials = task.credentials
    ref_key = credentials['xmlId']
    title = credentials['title']
    delivery_order_ref = credentials.pop('parent_ref')
    deletion_mark = credentials.pop('deletion_mark')

    delivery_order = crm_client.get_order_by_xml_id(delivery_order_ref, entity_type=entity_type.ENTITY_TYPE_ID_DELIVERY_ORDER)
    if not delivery_order: # Если распоряжения на доставку с указанным ref_key не существует
        logger.info(f'Упаковка: {title!r} Не создана по причине отсутствия распоряжения')
        return False
    pack_table_row = crm_client.get_order_by_xml_id(
        ref_key=ref_key,
        entity_type=entity_type.ENTITY_TYPE_ID_DELIVERY_ORDER_PACK,
        addition={'ufCrm21Number': credentials['ufCrm21Number']}
    )
    if task.is_test:
        credentials['parentId1108'] = delivery_order['id']
    else:
        credentials['parentId1076'] = delivery_order['id'] # Заполняем id родительского распоряжения
    if not pack_table_row:
        if deletion_mark:
            return True
        item = crm_client.create_order(body=credentials, entity_type=entity_type.ENTITY_TYPE_ID_DELIVERY_ORDER_PACK)
        return not bool(crm_client.get_changed_values(credentials, item))
    else:
        order_id = pack_table_row['id']
        if deletion_mark:
            return crm_client.delete_item(order_id, entity_type=entity_type.ENTITY_TYPE_ID_DELIVERY_ORDER_PACK)
        return crm_client.update_order_fields(order_id, credentials, entity_type=entity_type.ENTITY_TYPE_ID_DELIVERY_ORDER_PACK)

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

            resp = CSQ.custom_request_c(
                CFG.Config.project.db_nomen,
                f'SELECT Ref_Key FROM nomen WHERE Ref_Key = {ref_key!r}',
                one=True,
                rez_dict=True
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
                        ref_key
                        ]
                result = CSQ.custom_request_c(nomenklatura_erp, f"""INSERT INTO nomen (
                        Код
                        ,Артикул
                        ,Наименование
                        ,ЕдиницаИзмерения
                        ,На_удаление
                        ,Дата_изменения
                        ,СхемаОбеспечения
                        ,Закупочная_цена
                        ,Вид_Ref_Key
                        ,Вид,
                        Ref_Key) VALUES ({','.join('?' * len(body))})""", list_of_lists_c=[body])
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
                    type_name
                ]
                result = CSQ.custom_request_c(nomenklatura_erp, f"""UPDATE nomen 
                    SET Код = ?,
                        Артикул = ?,
                        Наименование = ?,
                        ЕдиницаИзмерения = ?,
                        На_удаление = ?,
                        Дата_изменения = ?,
                        СхемаОбеспечения = ?,
                        Вид_Ref_Key = ?,
                        Закупочная_цена = ?,
                        Вид = ? WHERE Ref_Key = {ref_key!r}""", list_of_lists_c=body)
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



def send_message(pk: int, service_status: bytes | None, is_accepted: bool):
    try:
        if is_accepted:
            data: MessageStatus = pickle.loads(service_status)


    except Exception as e:
        print(f'Ошибка в функции: {send_message!r}; {e}')
    ...

def unpack_message_status(message_status: bytes) -> Optional[MessageStatus]:
    try:
        data = pickle.loads(message_status)
        if isinstance(data, MessageStatus):
            return data
    except Exception as e: ...
    return None



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

def update_deal_status(task: Task):
    deal_id = task.credentials['id']
    crm = CRM()
    deal_obj = crm.deal_one(deal_id)['result']
    previous_stage = deal_obj['STAGE_ID']
    new_stage = task.credentials['status_code']
    #optional
    organization = task.credentials.get('UF_CRM_1737727925')
    type_tkp = task.credentials.get('UF_CRM_1737711083528')

    forced = task.credentials.get('forced', False)
    body = {'STAGE_ID': new_stage}

    if not forced:
        statuses = crm.deal_status_all()
        previous_rank = new_rank = None
        for status in statuses['result']:
            split_code = status['STATUS_ID'].rsplit(':')[-1]
            prev_stage_code = previous_stage.rsplit(':')[-1]
            new_stage_code = new_stage.rsplit(':')[-1]
            if split_code == prev_stage_code:
                previous_rank = status['SORT']
            if split_code == new_stage_code:
                new_rank = status['SORT']
        if new_rank <= previous_rank:
            logger.info(f'Сделка: {deal_id} | Завршено: True | Причина: Текущий статус выше или равен')
            body.pop('STAGE_ID')
        if task.is_test:
            return crm.deal_update(deal_id=13361, credentials={
                'FIELDS': {'STAGE_ID': new_stage}
            })
    # else:
    #     try:
    #         erp_base = 'ERP_MES1' if task.is_test else 'ERP'
    #         if deal_obj[closed_key] == 'Y':
    #             ref_key = deal_obj['UF_CRM_1712643377']
    #             set_client_order_close_state(erp_base, ref_key, 'ВРаботе', False, False)
    #     except Exception as e:
    #         print(e, f'Ошибка при завершении сделки 1С IS_TEST: {task.is_test}')
    if organization:
        body['UF_CRM_1737727925'] = str(organization)
    if type_tkp:
        body['UF_CRM_1737711083528'] = str(type_tkp)
    if not body:
        return True

    result = crm.deal_update(deal_id=deal_id, credentials={
        'FIELDS': body
    })
    logger.info(f'Сделка: {deal_id} | Завршено: {result} | Новый: {new_stage} | Предыдущий: {previous_stage}')
    return result


def checking_positions_for_closed_mk(task: Task) -> bool:
    znpr_ref = task.credentials['Ref_Key']
    znpr_num = task.credentials['Number']

    query_find_kpl = f"""
        SELECT НомПл 
        FROM пл_оуп
        INNER JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП
        INNER JOIN plan ON plan.Пномер = пл_оуп.НомПл
        WHERE знпр.№ERP = {znpr_num!r} AND знпр.Ref_Key_py = {znpr_ref!r} AND plan.Статус != 4
    """
    kpl_items = CSQ.custom_request_c(
        CFG.Config.project.db_kplan,
        query_find_kpl,
        one_column=True,
        rez_dict=True)
    if not isinstance(kpl_items, list):
        return False
    pk_kpl = [kpl for kpl in kpl_items]
    kpl_nums = ','.join(str(i) for i in pk_kpl)

    list_if_status = CSQ.custom_request_c(
        CFG.Config.project.db_naryad,
        f"""SELECT Пномер, НомКплан as "КПЛ", Статус FROM mk
        WHERE НомКплан IN ({kpl_nums}) AND Статус != 'НаУдаление';""",
        rez_dict=True)
    list_open_mk = []
    for item in list_if_status:
        if item['Дата_завершения'] == "":
            list_open_mk.append(item)
    if list_open_mk:
        mk_quot = "\n>> ".join(str(mk) for mk in list_open_mk)
        message_template = f"""
        По {znpr_num} создан документ "Передача продукции из производства"
        Статус "Завершена" не был применен к номерам КПЛ ({kpl_nums}) из-за незакрытых МК
        [B]Необходимо закрыть следующие МК[/B]
        {mk_quot}
        """
        is_done = False
    else:
        mk_quot = "\n>> ".join(str(mk) for mk in list_open_mk)
        message_template = f"""
        По {znpr_num} создан документ "Передача продукции из производства"
        Статус "Завершена" не был применен к номерам КПЛ ({kpl_nums}) из-за незакрытых МК
        [B]Необходимо закрыть следующие МК[/B]
        {mk_quot}
        """
        is_done = True
        for pnum in pk_kpl:
            CSQ.custom_request_c(
                CFG.Config.project.db_kplan,
                f"""UPDATE plan SET Статус = 4 WHERE Пномер = {pnum}""")
    sender = CB24.B24Sender()
    result = sender.send_msg_table(
       title=message_template,
       horizontal=True,
       lst_of_lists=list_open_mk,
       chat_id=task.chat_id)
    return is_done

def update_status_mes(task: Task):
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

commands = {
    'bitrix24.Сделка.Завершение': {
        'producer': deal_values,
        'consumer': action_end_deal_status,
        'check': True,
        'chat_id': None,
        'interval': 60 * 3 - 1,
        'new_task_format': False,
        'services': None

    },
    'bitrix24.Сделка.ОбновлениеТипТКП/Организация': {
        'producer': get_deal_values_by_data_version_mark,
        'consumer': update_organization_and_type_tkp,
        'check': True,
        'chat_id': None,
        'interval': 60 * 60 * 2,
        'new_task_format': False,
        'services': None
    },
    'bitrix24.Сделка.ОбновлениеПлановойДаты/Суммы': {
        'producer': get_last_changes_date_and_sum_ZK_TKP,
        'consumer': update_date_and_sum_ZK_TKP,
        'check': True,
        'chat_id': None,
        'interval': 60 * 5,
        'new_task_format': False,
        'services': None
    },
    'bitrix24.ЗаказПоставщику.СинхронизацияЗаказа/ТабличнойЧасти': { # https://bitrix24.kelast.ru/company/personal/user/3076/tasks/task/view/100056637/?MID=888366#com888366
        'producer': None,
        'consumer': update_order_supplier_attributes,
        'check': True,
        'chat_id': None,
        'interval': 60 * 3 - 1,
        'new_task_format': False,
        'services': None
    },
    'bitrix24.РаспоряжениеНаДоставку.СинхронизацияТабличнойЧасти': { # https://bitrix24.kelast.ru/company/personal/user/3076/tasks/task/view/100056997/
        'producer': None,
        'consumer': update_delivery_order_attributes,
        'check': True,
        'chat_id': None,
        'interval': 60 * 3 - 1,
        'new_task_format': False,
        'services': None
    },
    "bitrix24.РаспоряжениеНаДоставку/Упаковка.СинхронизацияТабличнойЧастиУпаковки": { # https://bitrix24.kelast.ru/company/personal/user/3076/tasks/task/view/100059053/
        'producer': None,
        'consumer': update_delivery_order_pack_attributes,
        'check': True,
        'chat_id': None,
        'interval': 60 * 3 - 1,
        'new_task_format': True,
        'services': None
    },
    "bitrix24.Сделка/ОбновлениеСтатуса": {
        # https://bitrix24.kelast.ru/company/personal/user/3076/tasks/task/view/100059053/
        'producer': None,
        'consumer': update_deal_status,
        'check': True,
        'chat_id': None,
        'interval': 60 * 3 - 1,
        'new_task_format': True,
        'services': None
    },
    'MES.Номенклатура/СинхронизацияПолей': {
        'producer': None,
        'consumer': update_nomenclature,
        'check': True,
        'chat_id': 'chat59299',
        'interval': 60 * 1 - 1,
        'new_task_format': True,
        'services': {
            'MES': sync_nomen_mes,
            'Bitrix24': sync_nomen_b24,
            'DOCs': sync_nomen_tflex_docs
        }
    },

}
# commands = {
#     'bitrix24.Сделка.ОбновлениеТипТКП/Организация': {
#         'producer': get_deal_values_by_data_version_mark,
#         'consumer': update_organization_and_type_tkp,
#         'check': True,
#         'chat_id': None,
#         'interval': 60 * 60 * 2,
#         'new_task_format': False,
#         'services': None
#     },
# }
# commands = {
#     "bitrix24.РаспоряжениеНаДоставку/Упаковка.СинхронизацияТабличнойЧастиУпаковки": {
#         # https://bitrix24.kelast.ru/company/personal/user/3076/tasks/task/view/100059053/
#         'producer': None,
#         'consumer': update_delivery_order_pack_attributes,
#         'check': True,
#         'chat_id': None,
#         'interval': 60 * 3 - 1,
#         'new_task_format': True,
#         'services': None
#     },
# }
# commands = {
#     'bitrix24.ЗаказПоставщику.СинхронизацияЗаказа/ТабличнойЧасти': { # https://bitrix24.kelast.ru/company/personal/user/3076/tasks/task/view/100056637/?MID=888366#com888366
#         'producer': None,
#         'consumer': update_order_supplier_attributes,
#         'check': True,
#         'chat_id': None,
#         'interval': 60 * 3 - 1,
#         'new_task_format': False,
#         'services': None
#     },
    # 'MES.Номенклатура/СинхронизацияПолей': {
    #     'producer': None,
    #     'consumer': update_nomenclature,
    #     'check': True,
    #     'chat_id': 'chat59299',
    #     'interval': 60 * 3 - 1,
    #     'new_task_format': True,
    #     'services': {
    #         'MES': sync_nomen_mes,
    #         'Bitrix24': sync_nomen_b24,
    #         'TFLEX.Docs': sync_nomen_tflex_docs
    #     }
    # },
    # "MES.plan/ОбновлениеСтатусаПозиции": {
    #     # https://bitrix24.kelast.ru/company/personal/user/3076/tasks/task/view/100059053/
    #     'producer': None,
    #     'consumer': checking_positions_for_closed_mk,
    #     'check': True,
    #     'chat_id': None,
    #     'interval': 60 * 60 * 24,
    #     'new_task_format': True,
    #     'services': None
    # },
# }


def check_commands():
    return
    for queue,  (producer, consumer, check, chat_id, interval, new_task_format, services) in commands.items():
        fn1, fn2 = commands[queue][producer], commands[queue][consumer]
        sing2 = inspect.signature(fn2)
        if fn1 is not None and not callable(fn1):
            raise Exception(f'[{queue}]Значение у задачи ключа {producer} не функция')
        if fn2 is not None and not callable(fn2):
            raise Exception(f'[{queue}]Значение у задачи ключа {consumer} не функция')
        # if len(sing2.parameters) != 1:
        #     raise Exception(f'[{queue}] Ключ {consumer} принимает 1 параметр')

def check_new_actions(new: dict, old: dict):
    for key, value in new.items():
        if key in old:
            json_old = pickle.loads(old[key]['data'])
            if json_old != value:
                pk = old[key]['id']
                CSQ.custom_request_c(db_files, f'DELETE FROM exchange WHERE id = {pk}')
                yield key, value
        else:
            yield key, value

def check_values():
    logging.info('Поиск новых событий...')
    for queue, (fn_info, fn_handle, check, chat_id, interval, new_task_format, services) in commands.items():
        if commands[queue][fn_info] is None:
            continue
        interval_value = commands[queue][interval]
        previous_time = os.environ.get(queue)
        now = int(time.time())
        if previous_time is None or (now - int(previous_time)) >= interval_value:
            os.environ[queue] = str(now)
        else:
            return
        if not commands[queue][check]:
            continue
        logging.info(f'[{queue}]Проверка событий')
        bucket = B24Bucket()
        last_actions = commands[queue][fn_info](queue, bucket)
        search_keys = ', '.join(repr(key) for key in last_actions.keys())
        response = CSQ.custom_request_c(
            db_files,
            f'SELECT key, data, id FROM exchange WHERE queue = {queue!r} AND key IN ({search_keys})',
            rez_dict=True,
            hat_c=False
        )
        if isinstance(response, list):
            response = F.deploy_dict_c(response, 'key')
            body = []
            for key, item in check_new_actions(last_actions, response):
                body.append([key, queue, pickle.dumps(item)])
            logging.info(f'[{queue}]Найдено новых событий: {len(body)}')
            if body:
                is_done = CSQ.custom_request_c(
                    db_files,
                    'INSERT INTO exchange(key, queue, data) '
                    'VALUES (?, ?, ?)',
                    list_of_lists_c=body
                )
                msg =  f'[{queue}]События успешно сохранены' if is_done else f'[{queue}]Не удалось сохранить события'
                logging.info(msg)


def handle_tasks():
    logging.info('Выполнение накопленных событий...')
    for queue, (fn_info, fn_handle, check, chat_key, interval, new_task_format, services_key) in commands.items():
        logging.info(f'[{queue}]Старт обработки')
        query = f'SELECT * FROM exchange WHERE queue = {queue!r} AND finished IN ("", 0) OR finished IS NULL'
        last_tasks = CSQ.custom_request_c(db_files, query, rez_dict=True)
        stat = {'y': 0, 'n': 0}
        is_new_task_format = commands[queue][new_task_format]
        chat_id = commands[queue][chat_key]
        used_tasks = set()
        if isinstance(last_tasks, list):
            if last_tasks:
                result = {}
                for task in last_tasks:
                    pk = task.get('id')
                    service_status = task.get('message_status')
                    is_test = task.get('is_test')
                    chat_accepted = bool(task.get('chat_accepted'))
                    services = commands[queue][services_key]
                    try:
                        data = pickle.loads(task['data'])
                        if is_new_task_format:
                            data = Task(
                                pk=pk,
                                credentials=data,
                                services=services,
                                chat_id=chat_id,
                                message_status=unpack_message_status(service_status),
                                chat_accepted=chat_accepted,
                                is_test=is_test
                            )
                            try:
                                if data in used_tasks:
                                    result[pk] = True
                                    continue
                                used_tasks.add(data)
                            except Exception as e:
                                logger.error(f'Ошибка при хэшировании задачи: {e}', exc_info=e, stack_info=True)
                        cp_data = copy.deepcopy(data)
                        cp_data2 = copy.deepcopy(data)
                        finished = commands[queue][fn_handle](cp_data)
                        if not finished:
                            finished = commands[queue][fn_handle](cp_data2)
                    except Exception as e:
                        logging.error('Ошибка выполнения задачи', exc_info=e, stack_info=True)
                        finished = False
                    result[pk] = finished
                    stat['y' if finished else 'n'] += 1
                body = []
                if all(result.values()):
                    last_update_time_from_env(update=True)
                for pk, is_finished in result.items():
                    body.append([is_finished, pk])
                query = f'UPDATE exchange SET finished = ? WHERE id = ?'
                is_done = CSQ.custom_request_c(db_files, query, rez_dict=True, list_of_lists_c=body)
                if is_done:
                    logging.info(f"[{queue}]Обработка прошла успешно, обработано: \nУдачно: {stat['y']}\nНеудачно: {stat['n']}{PREFIX_LOG}\n\n")
            else:
                logging.info(f'[{queue}]Новых задач не найдено')


def main():
    try:
        check_commands()
        check_values()
        handle_tasks()
    except KeyboardInterrupt as e:
        logging.info('Перезагрузка...')
        sys.exit(0)
    except Exception as e:
        logging.error('Ошибка в цикле событий', exc_info=e, stack_info=True)
        sys.exit(1)
    time.sleep(ITER_INTERVAL)
    sys.exit(1)


def decode_1c_data_version_attribute(base64_string: str):
    """Декодировать атрибут DataVersion 1С в число"""
    import base64
    decoded_bytes = base64.b64decode(base64_string)
    result_integer = int.from_bytes(decoded_bytes, byteorder='big')
    return result_integer



### TODO END


if __name__ == '__main__':
    while True:
        main()

