import difflib
import os
import pickle
import logging
import inspect
import time
from functools import reduce
from datetime import datetime, timedelta, timezone

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
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_b24 as CB24


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
        return response.ok

crm = CRM()
db_files = F.scfg('files')
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
        'CLOSED'                   # Статус завершена ("0", "1") : str
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
            if not last_mark:
                last_mark = mark
                continue
            num = decode_1c_data_version_attribute(mark)
            num_prev = decode_1c_data_version_attribute(last_mark)
            if num > num_prev:
                last_mark = mark
        return last_mark

    def get_deals_by_relation_zk_kp(self, data_version: str = ''):
        commerc_mark = commerc_ssilc = zk_mark = ''
        if data_version:
            commerc_mark = f'И КоммерческоеПредложениеКлиенту.ВерсияДанных >= "{data_version}"'
            commerc_ssilc = f'И КоммерческоеПредложениеКлиентуТовары.Ссылка.ВерсияДанных >= "{data_version}"'
            zk_mark = f'И ЗаказКлиента.ВерсияДанных >= "{data_version}"'
        query = f"""
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


def prepare_keys(data, *keys) -> dict:
    result = {}
    for item in data:
        exchange_key = '|'.join(value for key, value in item.items() if key in keys)
        result[exchange_key] = item
    return result

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
            data_for_update[make_deal_key(deal)] = deal
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
                       select: list[str] = ['ВидНоменклатуры/Description', 'Организация/Description', 'Сделка/Ref_Key',
                                            'Сделка/ПБ24_id_bitrix', 'Сделка/DataVersion', 'Сделка/ПБ24_СтадияБ24_Key', 'Сделка/Description']
                       ):
        select = ','.join(select)

        order_by = '$orderby=Сделка/DataVersion asc'
        filtr = ''
        if mark:
            filtr = f'&$filter=DataVersion ge {mark!r}'
        code, resp = self.client.get_response(
            doc_name='Document_КоммерческоеПредложениеКлиенту',
            wet_filtr=f"?$select={select}{filtr}&$expand=ВидНоменклатуры,Организация,Сделка&{order_by}",
            with_cod=True
        )
        if code == 200:
            return resp

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


def current_iso_date():
    tz = timezone(timedelta(hours=3))
    current_time = datetime.now(tz)
    return current_time.isoformat()


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
import logging

def get_deal_values_by_data_version_mark(queue: str, bucket: B24Bucket):
    data_version = get_last_data_version(queue)
    response_1c = client.get_last_deals(mark=data_version)
    response_1c = accumulate_response(response_1c)
    data_b24 = bucket.deals
    last_mark = data_version
    ref_story = set()
    data = {}
    for comm in response_1c:
        if comm['ВидНоменклатуры'] is None:
            continue
        if comm['Организация'] is None:
            continue
        type_tkp = comm['ВидНоменклатуры']['Description']
        organization = comm['Организация']['Description']
        ref_stage_1c = comm['Сделка']['ПБ24_СтадияБ24_Key']
        description = comm['Сделка']['Description']

        current_mark = comm['Сделка']['DataVersion']
        ref_key_deal = comm['Сделка']['Ref_Key']

        b24_id = comm['Сделка']['ПБ24_id_bitrix']
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
    resp_1c = update_inconsistencies_1c(b24_id=b24_id, ref_stage_1c=ref_stage_1c, stage_id_b24=stage_id_b24)
    return resp_b24 and resp_1c

from project_cust_38 import api_erp_commands as AEC


def get_config_data(filename: str = './deal_config.pickle'):
    try:
        with open(filename, 'rb') as f:
            import pickle
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
        import pickle
        try:
            prev_data[key] = data
            pickle.dump(prev_data, f)
        except Exception: ...

def put_last_data_version(queue: str, data_version: str):
    data = get_config_data()
    with open('./deal_config.pickle', 'wb+') as f:
        import pickle
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
        kp_sum = float(F.valm(item['СуммаДокументаКП']))
        kp_date = item['СрокПоставкиПоКП']

        zk_version = item['ВерсияДанныхЗК']
        zk_sum = float(F.valm(item['СуммаЗК']))
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

            if (zk_sum or kp_sum) and b24_stage_id == STAGE_NEW_DEAL:
                update_stage_b24_on_date_1c(b24_id=b24_id, old_val=b24_stage_id, new_val='C1:1', source=kp_source,
                                            object_name=description)
            if zk_version:
                if zk_sum != b24_sum:
                    update_sum_b24_on_date_1c(b24_id=b24_id, new_val=zk_sum, old_val=b24_sum, source=zk_source,
                                              object_name=description)
            else:
                if kp_sum != b24_sum:
                    update_sum_b24_on_date_1c(b24_id=b24_id, new_val=kp_sum, old_val=b24_sum, source=kp_source,
                                              object_name=description)

            if zk_shipment_date and zk_shipment_date != null_date:
                if not b24_shipment_date:
                    date_obj_1c = datetime.strptime(zk_shipment_date, '%d.%m.%Y %H:%M:%S')
                    date_for_update_b24 = date_obj_1c.isoformat()
                    update_date_b24_on_date_1c(b24_id=b24_id, new_val=date_for_update_b24, old_val=b24_shipment_date,
                                               source=zk_source, object_name=description)
                else:
                    date_obj_b24 = datetime.strptime(b24_shipment_date, '%Y-%m-%dT%H:%M:%S%z')
                    date_obj_1c = datetime.strptime(zk_shipment_date, '%d.%m.%Y %H:%M:%S')
                    if date_obj_b24 != date_obj_1c:
                        date_for_update_b24 = date_obj_1c.isoformat()
                        update_date_b24_on_date_1c(b24_id=b24_id, new_val=date_for_update_b24,
                                                   old_val=b24_shipment_date, source=zk_source, object_name=description)
            else:
                if kp_date == null_date:
                    return True
                if not b24_shipment_date and kp_date:
                    date_obj_1c = datetime.strptime(kp_date, '%d.%m.%Y %H:%M:%S')
                    date_obj_b24 = datetime.strptime(b24_shipment_date, '%Y-%m-%dT%H:%M:%S%z')
                    if date_obj_b24 != date_obj_1c:
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


commands = {
    'bitrix24.Сделка.Завершение': {
        'producer': deal_values,
        'consumer': action_end_deal_status,
        'check': True,
        'interval': 60 * 3 - 1

    },
    'bitrix24.Сделка.ОбновлениеТипТКП/Организация': {
        'producer': get_deal_values_by_data_version_mark,
        'consumer': update_organization_and_type_tkp,
        'check': True,
        'interval': 60 * 60 * 2
    },
    'bitrix24.Сделка.ОбновлениеПлановойДаты/Суммы': {
        'producer': get_last_changes_date_and_sum_ZK_TKP,
        'consumer': update_date_and_sum_ZK_TKP,
        'check': True,
        'interval': 60 * 5
    },
    # 'bitrix24.Неудача.ОбновлениеСтатуса': {
    #     'producer': None,
    #     'consumer': action_for_bad_attempt_upgrade,
    #     'check': False,
    #     'interval': 60 * 3 - 1
    #
    # },
}

def check_commands():
    for queue, (producer, consumer, check, interval) in commands.items():
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
    for queue, (fn_info, fn_handle, check, interval) in commands.items():
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
    for queue, (fn_info, fn_handle, check, interval) in commands.items():
        logging.info(f'[{queue}]Старт обработки')
        query = f'SELECT * FROM exchange WHERE queue = {queue!r} AND finished IN ("", 0) OR finished IS NULL'
        last_tasks = CSQ.custom_request_c(db_files, query, rez_dict=True)
        stat = {'y': 0, 'n': 0}
        if isinstance(last_tasks, list):
            if last_tasks:
                result = {}
                for task in last_tasks:
                    pk = task.get('id')
                    try:
                        data = pickle.loads(task['data'])
                        finished = commands[queue][fn_handle](data)
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
    except Exception as e:
        logging.error('Ошибка в цикле событий', exc_info=e, stack_info=True)
    time.sleep(ITER_INTERVAL)


def decode_1c_data_version_attribute(base64_string: str):
    """Декодировать атрибут DataVersion 1С в число"""
    import base64
    decoded_bytes = base64.b64decode(base64_string)
    result_integer = int.from_bytes(decoded_bytes, byteorder='big')
    return result_integer




if __name__ == '__main__':
    while True:
        main()


