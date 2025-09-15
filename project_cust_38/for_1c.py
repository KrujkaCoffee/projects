import datetime
import json as JS
import pprint
import copy
import requests
import pickle
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Cust_odata_erp as ERP
import project_cust_38.Cust_SQLite as CSQ
from collections import defaultdict as ddict
import project_cust_38.Cust_mes as CMS
import api_srv_config
import hashlib
from dataclasses import dataclass
import pars as PRS
import project_cust_38.api_erp_commands as APIERP
print(f'{F.now()} == Загрузка_бюджетов===')
from typing import TYPE_CHECKING, Any, Callable
import logging
import sys
import io

if TYPE_CHECKING:
    from API_server import data_parse_prices

CHAT_FOR_DEBUGGER_BUDGETS = 'chat90757'


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def pretty_dict(d, indent=0):
    """Форматируем словарь для Б24, переносим элементы set на новые строки."""
    lines = []
    prefix = "—" * indent  # видимый отступ
    if isinstance(d, dict):
        for k, v in d.items():
            lines.append(f"{prefix}{k}:[BR]")
            lines.append(pretty_dict(v, indent + 1))
    elif isinstance(d, set) or isinstance(d, list) or isinstance(d, tuple):
        for item in d:  # сортируем для стабильного вывода
            lines.append(pretty_dict(item, indent + 1))
    else:
        lines.append(f"{prefix}{d}[BR]")
    return "".join(lines)


def log_prefix_decorator(
        event_name: str,
        target: str,
        *,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_b24: bool = True,
        b24_format: str = None,
        chat_id: str = CHAT_FOR_DEBUGGER_BUDGETS
):
    """
    Декоратор для логирования.

    event_name   : имя события
    target       : цель события
    enable_console : включить StreamHandler (консоль)
    enable_file    : включить FileHandler (лог в файл)
    enable_b24     : включить кастомный B24-хендлер
    b24_format     : формат строки для B24 (по умолчанию 'B24|event|target|message')
    chat_id        : куда слать сообщения в B24
    Логи только в консоль:

    @log_prefix_decorator("DEAL_CREATED", "clientX", enable_file=False, enable_b24=False)
    def create_deal():
        logger.info("Создана сделка")
    Логи только в файл + Б24:

    @log_prefix_decorator("DEAL_UPDATED", "clientY", enable_console=True)
    def update_deal():
        logger.info("Сделка обновлена")

    Только Б24 с кастомным форматом и другим chat_id:

    @log_prefix_decorator(
        "DEAL_DELETED",
        "clientZ",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id="chat99999"
    )
    def delete_deal():
        logger.warning("Сделка удалена")

    """

    class PostRequestHandler(logging.Handler):
        def __init__(self, chat_id: str):
            from project_cust_38 import Cust_b24 as CB24
            super().__init__()
            self.sender = CB24.B24Sender()
            self.chat_id = chat_id

        def handle(self, record):
            return super().handle(record)

        def emit(self, record):
            try:
                log_entry = self.format(record)
                self.sender.send_msg_by_chat_id(self.chat_id, log_entry)
            except Exception:
                import traceback
                sys.__stdout__.write(traceback.format_exc() + "\n")

    def decorator(func):
        def wrapper(*args, **kwargs):
            # локальные импорты для изоляции
            import logging
            import io
            import sys

            func_name = func.__name__

            # формат для консоли и файла
            default_formatter = logging.Formatter(
                f'{func_name} - {event_name} - {target} - %(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # формат для B24
            if b24_format:
                b24_formatter = logging.Formatter(b24_format, datefmt="%Y-%m-%d %H:%M")
            else:
                b24_formatter = logging.Formatter(
                    "B24|%(asctime)s|%(message)s",
                    datefmt="%Y-%m-%d %H:%M"
                )

            added_handlers = []

            # используем отдельный логгер для этой функции (чтобы управлять только его хендлерами)
            try:
                base_logger = logger  # если в модуле есть глобальный logger, берем его имя
            except NameError:
                base_logger = logging.getLogger(__name__)
            local_logger = logging.getLogger(f"{base_logger.name}.{func_name}")



            # helper: не добавлять дубликаты по разумным критериям
            def _has_similar_handler(new_h):
                for h in local_logger.handlers:
                    # PostRequestHandler: по типу и chat_id
                    if isinstance(new_h, PostRequestHandler) and isinstance(h, PostRequestHandler):
                        if getattr(h, "chat_id", None) == getattr(new_h, "chat_id", None):
                            return True
                    # FileHandler: по пути файла
                    if isinstance(new_h, logging.FileHandler) and isinstance(h, logging.FileHandler):
                        if getattr(h, "baseFilename", None) == getattr(new_h, "baseFilename", None):
                            return True
                    # StreamHandler: по потоку (stream)
                    if isinstance(new_h, logging.StreamHandler) and isinstance(h, logging.StreamHandler):
                        if getattr(h, "stream", None) == getattr(new_h, "stream", None):
                            return True
                return False

            # сохраняем состояние local_logger
            original_level = getattr(local_logger, "level", logging.NOTSET)
            # Если уровень не задан (NOTSET) либо выше INFO (например WARNING), понизим до INFO,
            # чтобы INFO-сообщения доходили до хендлеров.
            if original_level == logging.NOTSET or original_level > logging.INFO:
                local_logger.setLevel(logging.INFO)

            original_propagate = getattr(local_logger, "propagate", True)
            local_logger.propagate = False  # не поднимать к родителю (чтобы избежать дублирования)

            # --- добавляем хендлеры только если их нет ---
            if enable_console:
                out_handler = logging.StreamHandler(stream=sys.__stdout__)
                out_handler.setFormatter(default_formatter)
                out_handler.setLevel(logging.INFO)
                # проверяем только stream, чтобы не дублировать
                if not any(
                        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) == sys.__stdout__ for h in
                        local_logger.handlers):
                    local_logger.addHandler(out_handler)
                    added_handlers.append(out_handler)

            if enable_file:
                file_handler = logging.FileHandler('b24_deal_service.log', encoding='utf8')
                file_handler.setFormatter(default_formatter)
                file_handler.setLevel(logging.INFO)
                if not _has_similar_handler(file_handler):
                    local_logger.addHandler(file_handler)
                    added_handlers.append(file_handler)

            if enable_b24:
                b24_handler = PostRequestHandler(chat_id)
                b24_handler.setFormatter(b24_formatter)
                b24_handler.setLevel(logging.INFO)
                if not _has_similar_handler(b24_handler):
                    local_logger.addHandler(b24_handler)
                    added_handlers.append(b24_handler)

            #sys.__stdout__.write(f"DEBUG: local_logger.name={local_logger.name}\n")
            #sys.__stdout__.write(
            #    f"DEBUG: local_logger.level={local_logger.level} effective={local_logger.getEffectiveLevel()}\n")
            #for i, h in enumerate(local_logger.handlers):
            #    sys.__stdout__.write(
            #        f"DEBUG: handler[{i}]={type(h).__name__} level={h.level} fmt={getattr(getattr(h, 'formatter', None), '_fmt', None)} stream={getattr(h, 'stream', None)}\n")
            #sys.__stdout__.write(f"DEBUG: root.level={logging.getLogger().level}\n")

            # Перехват print() в logger — теперь логируем в local_logger
            class StreamToLogger:
                def __init__(self, logger_obj, level):
                    self.logger = logger_obj
                    self.level = level

                def write(self, buf):
                    buf = buf.replace('[BR]', '\n').rstrip('\n')  # сохраняем все строки как есть
                    if buf.strip():  # пропуск пустых сообщений
                        record = self.logger.makeRecord(
                            name=self.logger.name,
                            level=self.level,
                            fn='',
                            lno=0,
                            msg=buf,
                            args=None,
                            exc_info=None
                        )
                        for h in self.logger.handlers:
                            if self.level >= h.level:
                                h.emit(record)

                def flush(self):
                    pass

            old_stdout = sys.stdout
            sys.stdout = StreamToLogger(local_logger, logging.INFO)

            try:
                result = func(*args, **kwargs)
            finally:
                # восстанавливаем stdout
                sys.stdout = old_stdout
                # удаляем только те хендлеры, которые добавляли в этой обёртке
                for h in added_handlers:
                    try:
                        local_logger.removeHandler(h)
                    except Exception:
                        pass
                # восстанавливаем настройки logger'а
                local_logger.propagate = original_propagate
                try:
                    local_logger.setLevel(original_level)
                except Exception:
                    pass

            return result

        return wrapper

    return decorator

DATA_1С_VERSION = F.now()
TODAY = F.now("%Y-%m-%d")
NAME_OTKL_ZVP_SUMM = 'Ост., руб. по ст.ЗВП'
NAME_OTKL_BUDG_SUMM = 'Ост., руб. по ст.бюдж.'


def last_day(anyday):
    return F.datetostr(F.add_days(F.strtodate(anyday, "%Y-%m-%d"), time_delta=datetime.timedelta(days=-1)), "%Y-%m-%d")


def set_client_order_close_state(ERP_base: str, refKey_СделкиСКлиентами: str, state: str = None, close: bool = None,
                                 reason_lose: str = None):
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
        print(f'set_client_order_close_state err:state val')
        return 500

    m = ERP.OrdersComposit(ERP_base)

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
            if reason_lose not in dict_reasons:
                print(f'set_client_order_close_state err:reason_lose val')
                return 500
            else:
                reason_lose_key = dict_reasons[reason_lose]

    kod, data_order = m.get_response(doc_name=f"Catalog_СделкиСКлиентами(guid'{refKey_СделкиСКлиентами}')",
                                     wet_filtr=f"""?$filter=DeletionMark eq false &$top=100&$select=*""",
                                     with_cod=True)
    # if kod != 200:
    #    return kod
    # data_order[]

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


if __name__ == '__main__':

    quit()

LIST_MONTH_NAMES = ["Январь ",
                    "Февраль ",
                    "Март ",
                    "Апрель ",
                    "Май ",
                    "Июнь ",
                    "Июль ",
                    "Август ",
                    "Сентябрь ",
                    "Октябрь ",
                    "Ноябрь ",
                    "Декабрь ",
                    ]


class Fcns():


    @log_prefix_decorator(
        "",
        "",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id=CHAT_FOR_DEBUGGER_BUDGETS
    )
    @staticmethod
    def get_prices(DICT_NOMEN_NAMES):
        print(f'\n==== Объединение цен по номенклатуре из трех источников ====', )
        m = ERP.OrdersComposit()

        dict_type_price = F.deploy_dict_c(m.get_response(doc_name=fr"Catalog_ВидыЦен",
                                                         wet_filtr=f"?$filter=IsFolder eq false&$select= Ref_Key,Description",
                                                         lazy_method_huours=24), "Description")

        prices = m.get_response(doc_name=fr"InformationRegister_ЦеныНоменклатуры25_RecordType/SliceLast("
                                         fr"  Condition=(ВидЦены_Key eq guid'{dict_type_price['Закупочная цена']}' or ВидЦены_Key eq guid'{dict_type_price['Закупочная']}') and Цена gt 0)",
                                wet_filtr=f"?$select= Цена, Номенклатура_Key ", lazy_method_huours=0.25)

        prices_2 = m.get_response(doc_name=fr"InformationRegister_ЦеныНоменклатуры_RecordType/SliceLast("
                                           fr"  Condition= Цена gt 0)",
                                  wet_filtr=f"?$select= Цена, Номенклатура_Key ", lazy_method_huours=0.25)

        prices_3 = m.get_response(doc_name=fr"InformationRegister_ЦеныНоменклатурыПоставщиков_RecordType/SliceLast("
                                           fr"  Condition= Цена gt 0)",
                                  wet_filtr=f"?$select= Цена, Номенклатура_Key ", lazy_method_huours=0.25)

        list_prices = [prices, prices_2, prices_3]

        dict_prices = {}
        count_add = 0
        for_print = []
        for i, prices in enumerate(list_prices):
            tmp_dict_prices = F.deploy_dict_c(prices, 'Номенклатура_Key')
            for k, v in tmp_dict_prices.items():
                if k not in dict_prices:
                    dict_prices[k] = v
                    if i > 0:
                        count_add += 1
                        name = k
                        if k in DICT_NOMEN_NAMES:
                            name = DICT_NOMEN_NAMES[k]
                        for_print.append(f'Номенклатура: {name}  Цена: {dict_prices[k]}')
        print(pretty_dict(for_print))
        print(f'==== END  Объединение цен по номенклатуре из трех источников ====', end='\n\n')
        return dict_prices

    @log_prefix_decorator(
        "",
        "",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id=CHAT_FOR_DEBUGGER_BUDGETS
    )
    @staticmethod
    def init_dit_budgets():
        DIR_BUDGETS: str = api_srv_config.DIR_BUDGETS
        if not F.existence_file_c(DIR_BUDGETS):
            print(f'not existence_file_c {DIR_BUDGETS}')
            raise Exception

        return DIR_BUDGETS

    @staticmethod
    def get_data_odata(DIR_BUDGETS, name_file, doc_name, wet_filtr, m=None, name_save_file_pre=None):
        # =============LOAD_MIDDLE_DATE_DATA СтатьиРасходов================================================================
        if not name_save_file_pre:
            name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_file_{name_file}.pickle'
        else:
            if F.strtodate(name_save_file_pre, "%Y-%m-%d") < F.add_days(F.strtodate(TODAY, "%Y-%m-%d"),
                                                                        datetime.timedelta(-10)):
                return
            name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{name_save_file_pre}_file_{name_file}.pickle'
        if F.existence_file_c(name_save_file_dict_middle_data):
            if name_save_file_pre:
                pass
                # TODO SEND TO MSG B24 name_save_file_dict_middle_data
            DICT_data = F.load_file_pickle(name_save_file_dict_middle_data)
        else:
            code = 0
            if not name_save_file_pre:
                if m == None:
                    m = ERP.OrdersComposit()
                code, resp = m.get_response(doc_name=doc_name, wet_filtr=wet_filtr, with_cod=True)
                name_save_file_pre = TODAY
                # code = 500
            if not code == 200:

                DICT_data = Fcns.get_data_odata(DIR_BUDGETS, '', '',
                                                wet_filtr,
                                                m=m,
                                                name_save_file_pre=last_day(name_save_file_pre))
            else:
                DICT_data = resp
                F.save_file_pickle(name_save_file_dict_middle_data, DICT_data)
        if DICT_data == None and name_save_file_pre == None:
            pass
            # TODO SEND TO MSG B24 doc_name
        return DICT_data

    @staticmethod
    def calc_middle_data_СтатьиБюджетов(DIR_BUDGETS, m=None):
        # =============LOAD_MIDDLE_DATE_DATA СтатьиРасходов================================================================
        name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_file_dict_middle_data_СтатьяБюджетов.pickle'
        if F.existence_file_c(name_save_file_dict_middle_data):
            DICT_СТАТЬИБЮДЖЕТОВ = F.load_file_pickle(name_save_file_dict_middle_data)
        else:
            if m == None:
                m = ERP.OrdersComposit()
            DICT_СТАТЬИБЮДЖЕТОВ = F.deploy_dict_c(m.get_response(doc_name='Catalog_СтатьиБюджетов',
                                                                 wet_filtr=f"""?$filter=DeletionMark eq false&$select= Ref_Key, Description """),
                                                  'Ref_Key')
            F.save_file_pickle(name_save_file_dict_middle_data, DICT_СТАТЬИБЮДЖЕТОВ)
        return DICT_СТАТЬИБЮДЖЕТОВ

    @staticmethod
    def calc_middle_data_ОбъектыЭксплуатации(DIR_BUDGETS, m=None):
        # =============LOAD_MIDDLE_DATE_DATA СтатьиРасходов================================================================
        name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_file_dict_middle_data_ОбъектыЭксплуатации.pickle'
        if F.existence_file_c(name_save_file_dict_middle_data):
            DICT_ОбъектыЭксплуатации = F.load_file_pickle(name_save_file_dict_middle_data)
        else:
            if m == None:
                m = ERP.OrdersComposit()
            DICT_ОбъектыЭксплуатации = F.deploy_dict_c(m.get_response(doc_name='Catalog_ОбъектыЭксплуатации',
                                                                      wet_filtr=f"""?$filter=DeletionMark eq false&$select= Ref_Key, Description """),
                                                       'Ref_Key')
            F.save_file_pickle(name_save_file_dict_middle_data, DICT_ОбъектыЭксплуатации)
        return DICT_ОбъектыЭксплуатации

    @log_prefix_decorator(
        "LOAD_MIDDLE_DATE_DATA",
        "СтатьиРасходов",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id=CHAT_FOR_DEBUGGER_BUDGETS
    )
    @staticmethod
    def calc_middle_data_СтатьиРасходов(DIR_BUDGETS, m=None):
        # =============LOAD_MIDDLE_DATE_DATA СтатьиРасходов================================================================
        name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_file_dict_middle_data_СтатьиРасходов.pickle'
        get_from_srv = True
        if F.existence_file_c(name_save_file_dict_middle_data):
            DICT_PVH_СТАТЬИРАСХОДОВ, compliance_register_states_expenditure_and_budgets = F.load_file_pickle(
                name_save_file_dict_middle_data)
            get_from_srv = False
            if not len(DICT_PVH_СТАТЬИРАСХОДОВ) or not len(compliance_register_states_expenditure_and_budgets):
                get_from_srv = True
                print(
                    'Не удалось получить данные ChartOfCharacteristicTypes_СтатьиРасходов / InformationRegister_БИТ_СоответствиеСтатейРасходовИСтатейБюджетирования')
        if get_from_srv:
            if m == None:
                m = ERP.OrdersComposit()
            code, _resp = m.get_response(
                doc_name=fr"InformationRegister_БИТ_СоответствиеСтатейРасходовИСтатейБюджетирования/SliceLast()",
                wet_filtr=f"?$select=*", with_cod=True)
            if code != 200:
                print(f'ERR {_resp}')
                quit()

            compliance_register_states_expenditure_and_budgets = F.deploy_dict_c(_resp, 'СтатьяРасходов_Key')

            code, _resp = m.get_response(doc_name='ChartOfCharacteristicTypes_СтатьиРасходов',
                                         wet_filtr=f"""?$select= Ref_Key, Description """, with_cod=True)
            if code != 200:
                print(f'ERR {_resp}')
                raise Exception(resp)
                quit()
            DICT_PVH_СТАТЬИРАСХОДОВ = F.deploy_dict_c(_resp, 'Ref_Key')
            code, _resp = m.get_response(doc_name='ChartOfCharacteristicTypes_СтатьиАктивовПассивов',
                                         wet_filtr=f"""?$select= Ref_Key, Description""", with_cod=True)
            if code != 200:
                print(f'ERR {_resp}')
                quit()
            dict_pvh_СтатьиАктивовПассивов = F.deploy_dict_c(_resp, 'Ref_Key')

            for k, v in dict_pvh_СтатьиАктивовПассивов.items():
                DICT_PVH_СТАТЬИРАСХОДОВ[k] = v
            F.save_file_pickle(name_save_file_dict_middle_data,
                               (DICT_PVH_СТАТЬИРАСХОДОВ, compliance_register_states_expenditure_and_budgets))
        return DICT_PVH_СТАТЬИРАСХОДОВ, compliance_register_states_expenditure_and_budgets

    @staticmethod
    def calc_middle_data_kat_expl(DIR_BUDGETS, m):
        # =============LOAD_MIDDLE_DATE_DATA kat_expl================================================================
        name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_file_dict_middle_data_kat_expl.pickle'
        if F.existence_file_c(name_save_file_dict_middle_data):
            DICT_LIST_KAT_EXPL = F.load_file_pickle(name_save_file_dict_middle_data)
        else:
            if m == None:
                m = ERP.OrdersComposit()

            list_kat_expl = m.get_response(doc_name='Catalog_КатегорииЭксплуатации',
                                           wet_filtr=f"""?$filter=DeletionMark eq false &$select= Ref_Key,Description""")
            DICT_LIST_KAT_EXPL = F.deploy_dict_c(list_kat_expl, 'Ref_Key')

            F.save_file_pickle(name_save_file_dict_middle_data, DICT_LIST_KAT_EXPL)
        return DICT_LIST_KAT_EXPL

    @staticmethod
    def calc_middle_data_list_CFO(DIR_BUDGETS, direction_key, m):
        # =============LOAD_MIDDLE_DATE_DATA kat_expl================================================================
        name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_{direction_key}_file_dict_middle_data_list_CFO.pickle'
        if F.existence_file_c(name_save_file_dict_middle_data):
            list_CFO = F.load_file_pickle(name_save_file_dict_middle_data)
        else:
            if m == None:
                m = ERP.OrdersComposit()

            list_CFO = m.get_response(doc_name='Catalog_СтруктураПредприятия',
                                      wet_filtr=f"""?$filter=DeletionMark eq false and Code eq '{direction_key}'&$select= Ref_Key,Description""")
            F.save_file_pickle(name_save_file_dict_middle_data, list_CFO)
        return list_CFO

    @staticmethod
    def calc_middle_data_full_dict_CFO(DIR_BUDGETS, m):
        # =============LOAD_MIDDLE_DATE_DATA kat_expl================================================================
        name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_full_file_dict_middle_data_list_CFO.pickle'
        if F.existence_file_c(name_save_file_dict_middle_data):
            dict_CFO = F.load_file_pickle(name_save_file_dict_middle_data)
        else:
            if m == None:
                m = ERP.OrdersComposit()

            dict_CFO = F.deploy_dict_c(m.get_response(doc_name='Catalog_СтруктураПредприятия',
                                                      wet_filtr=f"""?$filter=DeletionMark eq false &$select= Ref_Key,Description"""),
                                       'Ref_Key')

            F.save_file_pickle(name_save_file_dict_middle_data, dict_CFO)
        return dict_CFO

    @staticmethod
    def calc_middle_data_list_budgets(DIR_BUDGETS, DICT_СТАТЬИБЮДЖЕТОВ, DICT_ПОКАЗАТЕЛИБЮДЖЕТОВ, dict_CFO,
                                      Catalog_ОбъектыЭксплуатации, m=None):

        name_save_file_dict_middle_data = DIR_BUDGETS + F.sep() + f'{TODAY}_file_dict_middle_data_list_budgets.pickle'
        if F.existence_file_c(name_save_file_dict_middle_data):
            budgets = F.load_file_pickle(name_save_file_dict_middle_data)
        else:
            if m == None:
                m = ERP.OrdersComposit()
            budgets = m.get_response(doc_name='Document_ЭкземплярБюджета?$expand=Подразделение,ВидБюджета',
                                     wet_filtr=f"""&$filter=DeletionMark eq false and Статус eq 'Утвержден' 
                                      and Сценарий_Key eq guid'7871a890-edb6-11e4-92f1-0050568b35ac'&$select=
                                      ВидБюджета/Description,Подразделение/Description,Number,Date, 
                                      Организация_Key,Подразделение_Key,НачалоПериода,Комментарий, 
                                      АналитикаСтатейБюджетов/ИдентификаторСтроки, АналитикаСтатейБюджетов/СтатьяБюджетов, АналитикаСтатейБюджетов/Аналитика1, АналитикаСтатейБюджетов/Аналитика2, 
                                      ОборотыПоСтатьямБюджетов/ИдентификаторСтроки, ОборотыПоСтатьямБюджетов/ПериодПланирования, ОборотыПоСтатьямБюджетов/Сумма""")  # Утвержден, Бюджеты подразделений (год)
            for budget in budgets:  # ЭкземплярБюджета Утвержден, Бюджеты подразделений (год)
                date_budget = F.strtodate(budget['НачалоПериода'], "%Y-%m-%dT00:00:00")
                year_str = F.datetostr(date_budget, "%Y")
                АналитикаСтатейБюджетов = F.deploy_dict_c(budget['АналитикаСтатейБюджетов'], 'ИдентификаторСтроки')
                ОборотыПоСтатьямБюджетов = budget['ОборотыПоСтатьямБюджетов']
                budget['year_str'] = year_str
                state_by_month = dict()

                for k, v in АналитикаСтатейБюджетов.items():
                    name = 'X3'
                    podr = 'na'
                    obj_expl = ''

                    if v['СтатьяБюджетов'] in DICT_СТАТЬИБЮДЖЕТОВ:
                        name = DICT_СТАТЬИБЮДЖЕТОВ[v['СтатьяБюджетов']]
                    if v['СтатьяБюджетов'] in DICT_ПОКАЗАТЕЛИБЮДЖЕТОВ:
                        name = DICT_ПОКАЗАТЕЛИБЮДЖЕТОВ[v['СтатьяБюджетов']]

                    if name not in state_by_month:
                        state_by_month[name] = Fcns.get_shabl_month(year_str, 0)

                    v['Description'] = name

                    if v['Аналитика1'] in dict_CFO:
                        podr = dict_CFO[v['Аналитика1']]
                    v['CFO'] = podr

                    if v['Аналитика2'] in Catalog_ОбъектыЭксплуатации:
                        obj_expl = Catalog_ОбъектыЭксплуатации[v['Аналитика2']]
                    v['obj_expl'] = obj_expl
                    for vol_state in ОборотыПоСтатьямБюджетов:
                        if k == vol_state['ИдентификаторСтроки']:
                            period = vol_state['ПериодПланирования']
                            founds = vol_state['Сумма']
                            if F.is_date(period, "%Y-%m-%dT%H:%M:%S"):
                                month_str = F.month_rus_from_date(period, "%Y-%m-%dT%H:%M:%S", False) + F.datetostr(
                                    F.strtodate(period, "%Y-%m-%dT%H:%M:%S"), " %Y г.")
                                if month_str not in state_by_month[name]:
                                    state_by_month[name][month_str] = 0
                                state_by_month[name][month_str] += founds
                                state_by_month[name][month_str] = round(state_by_month[name][month_str], 2)
                budget['АналитикаСтатейБюджетов'] = АналитикаСтатейБюджетов
                budget['state_by_month'] = state_by_month

            F.save_file_pickle(name_save_file_dict_middle_data, budgets)
        return budgets

    @log_prefix_decorator(
        "Загрузка_бюджетов",
        "",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id=CHAT_FOR_DEBUGGER_BUDGETS
    )
    @staticmethod
    def load_budgets_prices(budgets):
        DICT_BUDGETS_PRICES_YEAR = dict()
        for budget in budgets:
            date_budget = F.strtodate(budget['НачалоПериода'], "%Y-%m-%dT00:00:00")
            year_str = F.datetostr(date_budget, "%Y")
            if year_str not in DICT_BUDGETS_PRICES_YEAR:
                DICT_BUDGETS_PRICES_YEAR[year_str] = dict()
            if 'ВидБюджета' not in budget:
                print("'ВидБюджета' not in budget")
                return
            if 'Description' not in budget['ВидБюджета']:
                print("'Description' not in budget['ВидБюджета']")
                return
            if 'state_by_month' not in budget:
                print("'state_by_month' not in budget")
                return
            bud_podr = '$'.join([budget['ВидБюджета']['Description'], budget['Подразделение']['Description']])
            DICT_BUDGETS_PRICES_YEAR[year_str][bud_podr] = budget['state_by_month']
        print(f'{F.now()} == Загрузка_бюджетов ОК===')
        return DICT_BUDGETS_PRICES_YEAR

    @log_prefix_decorator(
        "",
        "",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id=CHAT_FOR_DEBUGGER_BUDGETS
    )
    @staticmethod
    def load_budgets_states(DICT_СТАТЬИБЮДЖЕТОВ, budgets, DICT_PVH_СТАТЬИРАСХОДОВ,
                            compliance_register_states_expenditure_and_budgets):
        set_err = set()
        DICT_СТАТЬИБЮДЖЕТОВ = DICT_СТАТЬИБЮДЖЕТОВ
        budgets = budgets
        DICT_PVH_СТАТЬИРАСХОДОВ = DICT_PVH_СТАТЬИРАСХОДОВ
        DICT_BUDGETS_STATES = dict()
        counter_na = 1
        set_state_budgets_refs = set()
        dict_missing_state_budgets_refs = dict()

        compliance_state_budgets_state_expenditure = F.list_of_lists_to_dict_of_dicts(
            F.dict_of_dicts_to_list_of_lists(
                compliance_register_states_expenditure_and_budgets, 'СтатьяРасходов_Key'),
            'СтатьяБюджетирования_Key')

        for budget in budgets:
            # set_states = {_['СтатьяБюджетов'] for _ in budget['АналитикаСтатейБюджетов']}
            set_state_budgets_refs = {_['СтатьяБюджетов'] for _ in budget['АналитикаСтатейБюджетов'].values()}
            set_missing_state_budgets_refs = {DICT_СТАТЬИБЮДЖЕТОВ[_] for _ in set_state_budgets_refs if
                                              _ not in compliance_state_budgets_state_expenditure}
            if len(set_missing_state_budgets_refs):
                if budget['year_str'] not in dict_missing_state_budgets_refs:
                    dict_missing_state_budgets_refs[budget['year_str']] = dict()
                if budget['ВидБюджета']['Description'] not in dict_missing_state_budgets_refs[budget['year_str']]:
                    dict_missing_state_budgets_refs[budget['year_str']][
                        budget['ВидБюджета']['Description']] = set_missing_state_budgets_refs

            podr = budget['Подразделение']['Description']
            for state_b in budget['state_by_month']:

                set_state_r = {st_r for st_r, vals in compliance_register_states_expenditure_and_budgets.items() if
                               vals['СтатьяБюджетирования_Key'] in DICT_СТАТЬИБЮДЖЕТОВ and DICT_СТАТЬИБЮДЖЕТОВ[
                                   vals['СтатьяБюджетирования_Key']] == state_b}
                for state_r in set_state_r:
                    if podr not in DICT_BUDGETS_STATES:
                        DICT_BUDGETS_STATES[podr] = dict()
                    if state_r in DICT_PVH_СТАТЬИРАСХОДОВ:
                        state_r = DICT_PVH_СТАТЬИРАСХОДОВ[state_r]
                    DICT_BUDGETS_STATES[podr][state_r] = {"СтатьяВБюджете": state_b,
                                                          "Бюджет": budget['ВидБюджета']['Description']
                                                          }

            for key_state, state in DICT_PVH_СТАТЬИРАСХОДОВ.items():
                # key_podr_state = "$".join([budget['Подразделение']['Description'], state])
                # state_budget = f'n/a_{counter_na}'
                if key_state in compliance_register_states_expenditure_and_budgets:
                    pass
                    # state_budget_Key = compliance_register_states_expenditure_and_budgets[key_state]['СтатьяБюджетирования_Key']
                    # if state_budget_Key in set_states:
                    # if state_budget_Key in DICT_СТАТЬИБЮДЖЕТОВ:
                    #    state_budget = DICT_СТАТЬИБЮДЖЕТОВ[state_budget_Key]
                    # DICT_BUDGETS_STATES[key_podr_state] = {"СтатьяВБюджете": state_budget,
                    #                                           "Бюджет": budget['ВидБюджета']['Description']
                    #                                           }

                else:
                    set_err.add(state)
                pass

        if len(dict_missing_state_budgets_refs):

            #pprint.pprint(dict_missing_state_budgets_refs)
            print(f'не найдены в БИТ_СоответствиеСтатейРасходовИСтатейБюджетирования статьи бюджетов:\n' + pretty_dict(dict_missing_state_budgets_refs))
            # F.save_file('Не заполненные статьи бюджетов в СоответствиеСтатейРасходовИСтатейБюджетирования.txt', list_missing_state_budgets_refs,
            #            sep='\t')
        else:
            print('Все статьи бюджетов в СоответствиеСтатейРасходовИСтатейБюджетирования заполнены')
        return DICT_BUDGETS_STATES

    @log_prefix_decorator(
        "не заполненные статьи расходов",
        "",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id=CHAT_FOR_DEBUGGER_BUDGETS
    )
    @staticmethod
    def calc_not_fill_states_expenditure(m, DICT_PVH_СТАТЬИРАСХОДОВ,
                                         compliance_register_states_expenditure_and_budgets, BUDGETS):
        list_years_str = list(
            {F.datetostr(F.strtodate(_['НачалоПериода'], "%Y-%m-%dT%H:%M:%S"), '%Y') for _ in BUDGETS})
        dict_expenditures = dict()

        def calc_by_year(year, dict_expenditures):

            dict_znvp = F.deploy_dict_c(
                m.get_response(doc_name='Document_ЗаказНаВнутреннееПотребление?$expand=Подразделение',
                               wet_filtr=f"&$filter=DeletionMark eq false and year(ДатаОтгрузки) eq {year} "
                                         f"&$select= Number, Ref_Key, Статус, ДатаОтгрузки, Подразделение/Description, "
                                         f"ХозяйственнаяОперация, Товары/КатегорияЭксплуатации_Key, "
                                         f"Товары/СтатьяРасходов,  Товары/Количество,  Товары/Номенклатура_Key, "
                                         f"Товары/ДатаОтгрузки, Товары/Отменено"),
                'Ref_Key')
            if not dict_znvp:
                print(
                    f'Ошибка получения данных OData Document_ЗаказНаВнутреннееПотребление')

                return False
            for znvp in dict_znvp.values():
                for product in znvp['Товары']:
                    state_zvp = product['СтатьяРасходов']
                    state_zvp_name = 'None'
                    if product['СтатьяРасходов'] in DICT_PVH_СТАТЬИРАСХОДОВ:
                        state_zvp_name = DICT_PVH_СТАТЬИРАСХОДОВ[state_zvp]
                    # ===========Корректровка ТЗ от 14.01.2025
                    # if znvp['ХозяйственнаяОперация'] == 'ПередачаВЭксплуатацию':
                    #    state_zvp = product['КатегорияЭксплуатации_Key']
                    #    if product['КатегорияЭксплуатации_Key'] in DICT_LIST_KAT_EXPL:
                    #        state_zvp_name = DICT_LIST_KAT_EXPL[state_zvp]
                    # =======================================
                    if state_zvp not in compliance_register_states_expenditure_and_budgets:
                        podr = None
                        if znvp['Подразделение'] != None and 'Description' in znvp['Подразделение']:
                            podr = znvp['Подразделение']['Description']
                        if year not in dict_expenditures:
                            dict_expenditures[year] = set()
                        dict_expenditures[year].add(f"{podr}: '{state_zvp_name}'")

        for year in list_years_str:
            calc_by_year(year, dict_expenditures)

        if dict_expenditures:

            #@pprint.pprint(dict_expenditures, width=800)
            print(
                f'При анализе ЗаказНаВнутреннееПотребление - не заполненные статьи расходов в СоответствиеСтатейРасходовИСтатейБюджетирования:\n' + pretty_dict(dict_expenditures))
            # F.save_file('Не заполненные статьи расходов в СоответствиеСтатейРасходовИСтатейБюджетирования.txt',list_exp,sep='\t')
        else:
            print('Все статьи расходов в СоответствиеСтатейРасходовИСтатейБюджетирования заполенены')
        return

    @staticmethod
    def get_shabl_month(year: str, default_val={}):
        list_month_str = [_.lower() + year + " г." for _ in LIST_MONTH_NAMES]
        return {k: copy.deepcopy(default_val) for k in list_month_str}


@dataclass
class Data_1с:


    code,  nomen_names  = APIERP.get_wet_request(f'''ВЫБРАТЬ
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Ссылка)) КАК Ref,
        Номенклатура.Код + " " + Номенклатура.Наименование КАК Descr
    ИЗ
        Справочник.Номенклатура КАК Номенклатура''', lazy_method_huours=2)
    if code != 200:
        print(f'Ошибка получения данных из 1С')
    DICT_NOMEN_NAMES = F.deploy_dict_c(nomen_names['data'],'Ref')

    print(f'\n======================= INIT Data_1с ======================\n')
    DICT_PRICES = Fcns.get_prices(DICT_NOMEN_NAMES)

    DIR_BUDGETS = Fcns.init_dit_budgets()
    SAVE_FILE_PATH_NAME: str = DIR_BUDGETS + F.sep() + 'budgets.pickle'
    SAVE_FILE_BUDGETS_NAME: str = 'budgets.pickle'
    m = ERP.OrdersComposit()
    ПОКАЗАТЕЛИБЮДЖЕТОВ = Fcns.get_data_odata(DIR_BUDGETS,
                                             'middle_data_ПоказателиБюджетов',
                                             'Catalog_ПоказателиБюджетов',
                                             f"""?$filter=DeletionMark eq false&$select=Description, Ref_Key """,
                                             m)
    if ПОКАЗАТЕЛИБЮДЖЕТОВ == None:
        quit()
    DICT_ПОКАЗАТЕЛИБЮДЖЕТОВ = F.deploy_dict_c(ПОКАЗАТЕЛИБЮДЖЕТОВ, 'Ref_Key')
    DICT_СТАТЬИБЮДЖЕТОВ = Fcns.calc_middle_data_СтатьиБюджетов(DIR_BUDGETS, m)

    Catalog_ОбъектыЭксплуатации = Fcns.calc_middle_data_ОбъектыЭксплуатации(DIR_BUDGETS, m)
    dict_CFO = Fcns.calc_middle_data_full_dict_CFO(DIR_BUDGETS, m)
    BUDGETS = Fcns.calc_middle_data_list_budgets(DIR_BUDGETS, DICT_СТАТЬИБЮДЖЕТОВ, DICT_ПОКАЗАТЕЛИБЮДЖЕТОВ, dict_CFO,
                                                 Catalog_ОбъектыЭксплуатации, m)
    DICT_BUDGETS_PRICES = Fcns.load_budgets_prices(BUDGETS)

    if DICT_BUDGETS_PRICES == None:
        quit()

    DICT_PVH_СТАТЬИРАСХОДОВ, compliance_register_states_expenditure_and_budgets = Fcns.calc_middle_data_СтатьиРасходов(
        DIR_BUDGETS, m)
    # DICT_LIST_KAT_EXPL = Fcns.calc_middle_data_kat_expl(DIR_BUDGETS, m)

    DICT_BUDGETS_STATES = Fcns.load_budgets_states(DICT_СТАТЬИБЮДЖЕТОВ, BUDGETS, DICT_PVH_СТАТЬИРАСХОДОВ,
                                                   compliance_register_states_expenditure_and_budgets)

    Fcns.calc_not_fill_states_expenditure(m, DICT_PVH_СТАТЬИРАСХОДОВ,
                                          compliance_register_states_expenditure_and_budgets, BUDGETS)




def get_znvp(key_CFO: str, year: str, m=None):
    if m == None:
        m = ERP.OrdersComposit()
    dict_znvp = F.deploy_dict_c(m.get_response(doc_name='Document_ЗаказНаВнутреннееПотребление',
                                               wet_filtr=f"?$filter=DeletionMark eq false and year(ДатаОтгрузки) eq {year} "
                                                         f"and БитЦФО_Key eq guid'{key_CFO}'&$select= Number, Ref_Key, Статус, ДатаОтгрузки, "
                                                         f"ХозяйственнаяОперация, Товары/КатегорияЭксплуатации_Key, "
                                                         f"Товары/СтатьяРасходов,  Товары/Количество,  Товары/Номенклатура_Key, "
                                                         f"Товары/ДатаОтгрузки, Товары/Отменено",
                                               lazy_method_huours=0.25),
                                'Ref_Key')
    return dict_znvp

@log_prefix_decorator(
    "",
    "",
    enable_console=True,
    enable_file=False,
    enable_b24=True,
    b24_format="[%(asctime)s] %(message)s",
    chat_id=CHAT_FOR_DEBUGGER_BUDGETS
)
def eval_1c_budgetzvp_v1(data):
    print(f'\n=== START eval_1c_budgetzvp_v1 ===')

    @log_prefix_decorator(
        "",
        "",
        enable_console=True,
        enable_file=False,
        enable_b24=True,
        b24_format="[%(asctime)s] %(message)s",
        chat_id=CHAT_FOR_DEBUGGER_BUDGETS
    )
    def add_znvp_list_year(dict_znvp_years, year, list_err, m=None):

        def get_budget_and_state(name_CFO, state_zvp):
            if state_zvp not in Data_1с.DICT_BUDGETS_STATES[name_CFO]:
                return None, None
            budget = Data_1с.DICT_BUDGETS_STATES[name_CFO][state_zvp]['Бюджет']
            state_budget = Data_1с.DICT_BUDGETS_STATES[name_CFO][state_zvp]['СтатьяВБюджете']
            return budget, state_budget

        def month_str_to_month(month_str):
            num = F.date_from_month_rus(month_str.split()[0], False)
            str_num = '0' * (2 - len(str(num))) + str(num)
            return str_num

        list_znvp_data =[]
        if year not in dict_znvp_years:
            print(f'\n=== START add_znvp_list_year year: {year}===')
            if name_CFO not in Data_1с.DICT_BUDGETS_STATES:
                return

            dict_znvp_tmp = dict()
            dict_znvp = get_znvp(key_CFO, year, m)
            for znvp in dict_znvp.values():
                set_err = set()
                for product in znvp['Товары']:
                    if product['Отменено']:
                        continue
                    price_tch = 0
                    if product['Номенклатура_Key'] in dict_prices:
                        price_tch = dict_prices[product['Номенклатура_Key']]
                    else:
                        name_nomen = product['Номенклатура_Key']
                        data_nomen = CSQ.custom_request_c(F.scfg('nomenklatura_erp'),
                                                          f"""SELECT Код, Наименование 
                                                          FROM nomen WHERE Ref_Key == "{product['Номенклатура_Key']}" LIMIT 1""",
                                                          rez_dict=True)
                        if data_nomen == None or data_nomen == False or len(data_nomen) == 0:
                            data_nomen = m.get_response(doc_name='Catalog_Номенклатура',
                                                        wet_filtr=f"""?$filter=Ref_Key eq guid'{product['Номенклатура_Key']}'&$select= Code, Description""")
                            if data_nomen == None or data_nomen == False or len(data_nomen) == 0:
                                pass
                            else:
                                name_nomen = data_nomen[0]
                        else:
                            name_nomen = data_nomen[0]
                        list_err.append(
                            f"ЗНВП № {znvp['Number']} не обработан, т.к. не найден {name_nomen} в ПоследнихЦенах/ЦеныНоменклатуры25/ЦенахПоставщиков, стоимость принята 0")
                        print(f"ЗНВП № {znvp['Number']} не обработан, т.к. не найден {name_nomen} в ПоследнихЦенах/ЦеныНоменклатуры25/ЦенахПоставщиков, стоимость принята 0")
                    summ_price = price_tch * product['Количество']

                    state_zvp = product['СтатьяРасходов']
                    if product['СтатьяРасходов'] in DICT_PVH_СТАТЬИРАСХОДОВ:
                        state_zvp = DICT_PVH_СТАТЬИРАСХОДОВ[product['СтатьяРасходов']]
                    # =============14.01.2025 корректировка ТЗ
                    # if znvp['ХозяйственнаяОперация'] == 'ПередачаВЭксплуатацию':
                    #    state_zvp = product['КатегорияЭксплуатации_Key']
                    #    if product['КатегорияЭксплуатации_Key'] in DICT_LIST_KAT_EXPL:
                    #        state_zvp = DICT_LIST_KAT_EXPL[product['КатегорияЭксплуатации_Key']]
                    # =====================================================
                    date_dt = F.strtodate(product['ДатаОтгрузки'], "%Y-%m-%dT%H:%M:%S")
                    year_product = F.datetostr(date_dt, '%Y')
                    month = F.datetostr(date_dt, '%m')
                    month_str = F.month_rus_from_date(znvp['ДатаОтгрузки'], "%Y-%m-%dT%H:%M:%S",
                                                      False) + F.datetostr(
                        F.strtodate(znvp['ДатаОтгрузки'], "%Y-%m-%dT%H:%M:%S"), " %Y г.")
                    budget, state_budget = get_budget_and_state(name_CFO, state_zvp)
                    if budget == None:
                        msg = f"ЗНВП № {znvp['Number']} не обработан, т.к. не найдены для `{name_CFO}` статья ЗВП `{state_zvp}` в бюджетах. Стоимость принята 0"
                        
                        set_err.add(
                            msg)
                        continue

                    if (budget, state_budget) not in dict_znvp_tmp:
                        dict_znvp_tmp[(budget, state_budget)] = dict()

                    if month not in dict_znvp_tmp[(budget, state_budget)]:
                        dict_znvp_tmp[(budget, state_budget)][month] = 0
                    dict_znvp_tmp[(budget, state_budget)][month] += summ_price
                    znvp_data_result = {'ЦФО':name_CFO, 'Бюджет':budget, 'Статья бюджета': state_budget, 'Месяц': month, 'ЗНВП':znvp['Number'], 'Сумм.Цена':str(summ_price)}
                    list_znvp_data.append( '|'.join([f'{k}:{v}' for k,v in znvp_data_result.items()]))
                    #print('|'.join([name_CFO, budget, state_budget, month, znvp['Number'], str(summ_price)]))

                    #
                    # if year_product not in dict_znvp_years:
                    #    dict_znvp_years[year] = dict()
                    # if month not in dict_znvp_years[year]:
                    #    dict_znvp_years[year][month] = dict()
                    # if state_zvp not in dict_znvp_years[year][month]:
                    #    dict_znvp_years[year][month][state_zvp] = dict()
                    #    
                    #    budget, state_budget, limit = calc_budget(state_zvp, name_CFO, month_str, year_product)
                    #    dict_znvp_years[year][month][state_zvp]['info'] = {"budget": budget,
                    #                                                       "state_budget": state_budget,
                    #                                                       "limit": limit}
                    #    dict_znvp_years[year][month][state_zvp]['summ_price'] = 0
                    # dict_znvp_years[year][month][state_zvp]['summ_price'] += summ_price
                for elem in set_err:
                    list_err.append(elem)
                    print(elem)
            def get_prices_from_dict_znvp_tmp(dict_znvp_tmp, budget, state_budget, month):
                if (budget, state_budget) in dict_znvp_tmp:
                    if month in dict_znvp_tmp[(budget, state_budget)]:
                        return dict_znvp_tmp[(budget, state_budget)][month]
                return 0

            for state_zvp in Data_1с.DICT_BUDGETS_STATES[name_CFO].keys():
                budget, state_budget = get_budget_and_state(name_CFO, state_zvp)
                if budget == None:
                    list_err.append(
                        f"Не найдены для `{name_CFO}` статья ЗВП `{state_zvp}`. стоимость принята 0")
                    continue
                budget_cfo = "$".join([budget, name_CFO])

                if year in Data_1с.DICT_BUDGETS_PRICES:
                    if budget_cfo in Data_1с.DICT_BUDGETS_PRICES[year]:
                        if state_budget in Data_1с.DICT_BUDGETS_PRICES[year][budget_cfo]:
                            for month_str in Data_1с.DICT_BUDGETS_PRICES[year][budget_cfo][state_budget]:
                                month = month_str_to_month(month_str)
                                if year not in dict_znvp_years:
                                    dict_znvp_years[year] = dict()
                                if month not in dict_znvp_years[year]:
                                    dict_znvp_years[year][month] = dict()
                                if state_zvp not in dict_znvp_years[year][month]:
                                    dict_znvp_years[year][month][state_zvp] = dict()
                                limit = Data_1с.DICT_BUDGETS_PRICES[year][budget_cfo][state_budget][month_str]
                                limit = limit - get_prices_from_dict_znvp_tmp(dict_znvp_tmp, budget, state_budget,
                                                                              month)
                                dict_znvp_years[year][month][state_zvp]['info'] = {"budget": budget,
                                                                                   "state_budget": state_budget,
                                                                                   "limit": limit}
                                # dict_znvp_years[year][month][state_zvp]['summ_price'] = 0
            if list_znvp_data:
                print('Учет ЗНВП:\n' + pretty_dict(list_znvp_data))
            else:
                print('ЗНВП Не найдены')
            print(f'\n=== END add_znvp_list_year year: {year}===')
        return dict_znvp_years, list_err

    def group_expenditures(data):
        result = {}

        for item in data:
            # Формируем ключ как кортеж из month и state_expenditure
            key = (item['month'], item['state_expenditure'])

            # Если ключа еще нет в словаре, создаем пустой список
            if key not in result:
                result[key] = []

            # Добавляем kod_row в список
            result[key].append(item['kod_row'])

        return result

    dict_znvp_years = dict()
    m = ERP.OrdersComposit()
    rez = []
    dict_prices = Data_1с.DICT_PRICES

    list_CFO = Fcns.calc_middle_data_list_CFO(Data_1с.DIR_BUDGETS, data.direction_key, m)

    key_CFO = list_CFO[0]['Ref_Key']
    name_CFO = list_CFO[0]['Description']

    DICT_PVH_СТАТЬИРАСХОДОВ = Data_1с.DICT_PVH_СТАТЬИРАСХОДОВ
    set_postfix = set()
    list_err = []
    data_list_month_grouped = group_expenditures(data.list_month)
    for month, product in data_list_month_grouped.keys():
        year = F.datetostr(F.strtodate(month, "%m.%Y"), "%Y")
        if year not in Data_1с.DICT_BUDGETS_PRICES:
            set_postfix.add(f'Бюджеты на {year} год не обнаружены')
        dict_znvp_years, list_err = add_znvp_list_year(dict_znvp_years, year, list_err, m)
        dict_znvp_years, list_err = add_znvp_list_year(dict_znvp_years, str(int(year) + 1), list_err, m)

    for product in data.list_month:
        budget_name = 'Не обнаружен в бюджетах'
        year_delta = 0
        month_delta = 0
        year_product = F.datetostr(F.strtodate(product['month'], "%m.%Y"), "%Y")
        month_product = F.datetostr(F.strtodate(product['month'], "%m.%Y"), "%m")
        state_expenditure = product['state_expenditure']

        budget_name = f'"{state_expenditure}" Не обнаружен в бюджетах {name_CFO}'
        summ_waste = 0
        fl = False
        if year_product in dict_znvp_years:
            for month, data_month in dict_znvp_years[year_product].items():
                for state, data_state in data_month.items():
                    if state == state_expenditure:
                        year_delta += data_state['info']['limit']
                        # year_delta -= data_state['summ_price']
                        if month == month_product:
                            fl = True
                            budget_name = data_state['info']['budget']
                            month_delta += data_state['info']['limit']
                            # month_delta -= data_state['summ_price']

        if fl:
            msg = ''
        rez.append(
            {'КодСтроки': product['kod_row'], 'Остаток': round(month_delta, 2), 'ОстатокГод': round(year_delta, 2),
             'Сообщить': '/'.join(list(set_postfix)),
             "Бюджет": budget_name})
    print(f'\n=== END eval_1c_budgetzvp_v1 ===')
    return rez, list_err


def eval_1c_budget_v1(data):
    return eval_budget(data.direction_key, str(data.year), data.month)


def calc_budget(state, cfo, month_str, year, add_info=''):
    budget = 'Вне бюджета'
    state_budget = f'Не найдена {add_info} (Статья расходов `{state}` в БИТ_СоответствиеСтатейРасходовИСтатейБюджетирования)'
    limit = 0
    if cfo in Data_1с.DICT_BUDGETS_STATES:
        if state in Data_1с.DICT_BUDGETS_STATES[cfo]:
            budget = Data_1с.DICT_BUDGETS_STATES[cfo][state]['Бюджет']
            state_budget = Data_1с.DICT_BUDGETS_STATES[cfo][state]['СтатьяВБюджете']
            if year in Data_1с.DICT_BUDGETS_PRICES:
                budget_cfo = "$".join([budget, cfo])
                if budget_cfo in Data_1с.DICT_BUDGETS_PRICES[year]:
                    if state_budget in Data_1с.DICT_BUDGETS_PRICES[year][budget_cfo]:
                        if month_str in Data_1с.DICT_BUDGETS_PRICES[year][budget_cfo][state_budget]:
                            limit = Data_1с.DICT_BUDGETS_PRICES[year][budget_cfo][state_budget][month_str]
    return budget, state_budget, limit

@log_prefix_decorator(
    "",
    "",
    enable_console=True,
    enable_file=False,
    enable_b24=True,
    b24_format="[%(asctime)s] %(message)s",
    chat_id=CHAT_FOR_DEBUGGER_BUDGETS
)
def eval_budget(direction_key, year: str, data_month: str = None, dict_prices=None, dict_znvp=None):
    def calc_rez_data(dict_data, date=None):
        rez_data = []
        for budget, state_zvp_dict in dict_data.items():
            for state_zvp, state_data in state_zvp_dict.items():
                tmp_dict = ddict(int, {'Бюджет': budget, 'Статья в ЗВП': state_zvp,
                                       'Статья бюджета': state_data['Статья бюджета']})
                for month, types_summ in state_data.items():
                    if date == None or month == date:
                        if isinstance(types_summ, dict):
                            for k, v in types_summ.items():
                                if F.is_numeric(v):
                                    tmp_dict[k] += round(v, 2)
                                else:
                                    tmp_dict[k] = v
                            if date != None:
                                break
                rez_data.append(tmp_dict)
        return rez_data

    def calc_dict_data(dict_znvp, name_CFO, shabl_month, month_str_erp, year):
        # summ_summ = 0
        dict_data = dict()
        list_znvp_wo_prices = []
        dict_otkl_summ = dict()
        for znvp_key, znvp in dict_znvp.items():
            print(f'calc_dict_data - znvp_key: {znvp_key}')
            for s_num, product in enumerate(znvp['Товары']):
                month_str = F.month_rus_from_date(product['ДатаОтгрузки'], "%Y-%m-%dT%H:%M:%S", False) + F.datetostr(
                    F.strtodate(product['ДатаОтгрузки'], "%Y-%m-%dT%H:%M:%S"), " %Y г.")
                if month_str_erp != None and month_str_erp != month_str:
                    continue
                if product['Отменено']:
                    continue
                price_tch = 0
                if product['Номенклатура_Key'] in dict_prices:
                    price_tch = dict_prices[product['Номенклатура_Key']]
                else:
                    print(f"не найден {product['Номенклатура_Key']} в ценах")
                    list_znvp_wo_prices.append([
                        f"Цена не найдена: {znvp['Number']} ", product['Номенклатура_Key']])

                summ_price = price_tch * product['Количество']

                state_zvp = product['СтатьяРасходов']
                if product['СтатьяРасходов'] in DICT_PVH_СТАТЬИРАСХОДОВ:
                    state_zvp = DICT_PVH_СТАТЬИРАСХОДОВ[product['СтатьяРасходов']]
                # =======================корректировка ТЗ от 14.01.2025
                # if znvp['ХозяйственнаяОперация'] == 'ПередачаВЭксплуатацию':
                #    state_zvp = product['КатегорияЭксплуатации_Key']
                #    if product['КатегорияЭксплуатации_Key'] in DICT_LIST_KAT_EXPL:
                #        state_zvp = DICT_LIST_KAT_EXPL[product['КатегорияЭксплуатации_Key']]
                # =================================================================
                budget, state_budget, limit = calc_budget(state_zvp, name_CFO, month_str, year,
                                                          add_info=f"в ЗНВП {znvp['Number']}/строка {s_num + 1}")

                if budget not in dict_otkl_summ:
                    dict_otkl_summ[budget] = dict()
                if state_budget not in dict_otkl_summ[budget]:
                    dict_otkl_summ[budget][state_budget] = dict()
                if month_str not in dict_otkl_summ[budget][state_budget]:
                    dict_otkl_summ[budget][state_budget][month_str] = limit

                if budget not in dict_data:
                    dict_data[budget] = dict()

                if state_zvp not in dict_data[budget]:
                    dict_data[budget][state_zvp] = copy.deepcopy(shabl_month)
                    dict_data[budget][state_zvp]['Статья бюджета'] = state_budget

                dict_data[budget][state_zvp][month_str]['Утв. сумма статьи бюджета, руб.'] = limit
                dict_data[budget][state_zvp][month_str][NAME_OTKL_BUDG_SUMM] = 0
                dict_data[budget][state_zvp][month_str][znvp['Статус'] + ", руб."] += summ_price
                if znvp['Статус'] in ['Закрыт', "КВыполнению"]:
                    dict_data[budget][state_zvp][month_str]['Всего утв., руб.'] += summ_price
                summ_zvp_price = dict_data[budget][state_zvp][month_str]['Всего утв., руб.']
                dict_data[budget][state_zvp][month_str][NAME_OTKL_ZVP_SUMM] = limit - summ_zvp_price

                dict_otkl_summ[budget][state_budget][month_str] -= summ_price

                # summ_summ += summ_price
                # print('|'.join([tag, znvp_key, state_zvp, znvp['Статус'] + ", руб.", str(summ_price)]))
        # print(summ_summ)
        for k, v in dict_data.items():
            if not k in dict_otkl_summ:
                continue
            for k_zvp, v_zvp in v.items():
                state_budget = v_zvp['Статья бюджета']
                if state_budget not in dict_otkl_summ[k]:
                    continue
                for k_month, v_month in v_zvp.items():
                    if isinstance(v_month, dict):
                        if k_month not in dict_otkl_summ[k][state_budget]:
                            continue
                        v_month[NAME_OTKL_BUDG_SUMM] = dict_otkl_summ[k][state_budget][k_month]
        return dict_data, list_znvp_wo_prices

    m = ERP.OrdersComposit()

    DICT_PVH_СТАТЬИРАСХОДОВ = Data_1с.DICT_PVH_СТАТЬИРАСХОДОВ

    list_CFO = Fcns.calc_middle_data_list_CFO(Data_1с.DIR_BUDGETS, direction_key, m)
    if dict_prices == None:
        dict_prices = Data_1с.DICT_PRICES

    key_CFO = list_CFO[0]['Ref_Key']
    name_CFO = list_CFO[0]['Description']
    if dict_znvp == None:
        dict_znvp = get_znvp(key_CFO, year, m)

    dict_shabl = {_ + ", руб.": 0 for _ in set([_['Статус'] for _ in dict_znvp.values()])}
    dict_shabl['Всего утв., руб.'] = 0
    dict_shabl['Утв. сумма статьи бюджета, руб.'] = 0
    dict_shabl[NAME_OTKL_ZVP_SUMM] = 0

    shabl_month = Fcns.get_shabl_month(year)
    shabl_month = {k: copy.deepcopy(dict_shabl) for k in shabl_month.keys()}
    if data_month == None:
        month_str_erp = None
    else:
        month_str_erp = f"{data_month} {year} г.".lower()

    dict_data, list_znvp_wo_prices = calc_dict_data(dict_znvp, name_CFO, shabl_month, month_str_erp, year)

    dict_ref = {_[-1]: _[-1] for _ in list_znvp_wo_prices}
    for ref in dict_ref.keys():
        code, data_nomen = m.get_response(doc_name='Catalog_Номенклатура',
                                          wet_filtr=f"""?$filter=Ref_Key eq guid'{ref}'&$select= Code, Description""",
                                          with_cod=True)
        if code == 200:
            dict_ref[ref] = data_nomen[0]['Description']

    rez_data = calc_rez_data(dict_data, month_str_erp)

    if len(rez_data):
        for znvp_wo_prices in list_znvp_wo_prices:
            tmp_item = {_: '' for _ in copy.deepcopy(rez_data[0]).keys()}
            tmp_item['Бюджет'] = f"{znvp_wo_prices[0]}({dict_ref[znvp_wo_prices[1]]})"
            rez_data.append(tmp_item)
    return rez_data


def eval_1c_parse_prices_v1(data):
    answ = PRS.run_parse(data.data_nomens)
    return answ


def get_file(data):
    list_err = []
    data_resp = []
    for path in data:
        file_blob = None
        if F.existence_file_c(path.path_file):
            file_blob = F.load_file_convert_to_binary(path.path_file, True)
        data_resp.append({path.path_file: file_blob})
    return data_resp, list_err


def update_drawback_journal(deal_id: int | str, data: dict, queue: str = 'bitrix24.Неудача.ОбновлениеСтатуса'):
    list_err = None
    file_db = F.scfg('files')

    def check_data_existing(cur_hash: str):
        res = CSQ.custom_request_c(file_db, f'SELECT id FROM exchange WHERE key = {cur_hash!r}', hat_c=False)
        if not isinstance(res, list):
            raise Exception(f'[B24-HANDLER]Ошибка при проверке ключа {queue!r}')
        return not bool(res)

    hash_data = hashlib.sha256(f'{deal_id}|{data}'.encode('utf8')).hexdigest()
    if check_data_existing(hash_data):
        b_data = pickle.dumps(data)
        kwargs = {'key': hash_data, 'queue': queue, 'data': b_data}
        keys = ', '.join(kwargs.keys())
        values_eq = ', '.join('?' for _ in kwargs)
        values = list(kwargs.values())
        result = CSQ.custom_request_c(
            F.scfg('files'),
            f'INSERT INTO exchange({keys}) VALUES ({values_eq})',
            list_of_lists_c=[values]
        )
        if result == False:
            raise Exception('[B24-HANDLER]Не удалось сохранить данные неудачной попытки')
    return None, list_err
