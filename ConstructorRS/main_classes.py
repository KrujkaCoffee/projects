from __future__ import annotations


from typing import  TYPE_CHECKING
from dataclasses import dataclass
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
from project_cust_38 import Cust_config as CFG
import project_cust_38.Cust_docs as CDCS
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.Cust_tree_widget as CTREE
import project_cust_38.Cust_resource_creator as CRES
import uuid
import dataClass
from PyQt5 import QtWidgets
from functools import partial
from dataClass import data_app as DTCLS
if TYPE_CHECKING:
    from dataClass import data_app as DTCLS
    from constr_rc import mywindow as mywindow

class Base_cls():
    _UNSERIALIZABLE_ATTRS = {'_lock_recalc'}
    _lock_recalc = False
    def _export(self):

        if self.__class__.__name__ == 'CrResBody':
            pass
        result = {}

        # Словарь кастомных обработчиков для специфичных типов
        CUSTOM_HANDLERS = {
            #'datetime': lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x),
            #'date': lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x),
            #'time': lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x),
            #'decimal': lambda x: float(x) if hasattr(x, '__float__') else str(x),
        }

        def process_value(value):
            """Рекурсивно обрабатывает значение для экспорта"""
            # Базовые типы
            if isinstance(value, (int, float, str, bool, type(None), bytes, bytearray)):
                return value

            # Объекты с методом _export
            if hasattr(value, '_export'):
                return value._export()

            # Проверка кастомных обработчиков
            type_name = type(value).__name__.lower()
            if type_name in CUSTOM_HANDLERS:
                return CUSTOM_HANDLERS[type_name](value)

            # Списки
            if isinstance(value, list):
                return [process_item(item) for item in value]

            # Кортежи
            if isinstance(value, tuple):
                return tuple(process_item(item) for item in value)

            # Множества
            if isinstance(value, set):
                return {process_item(item) for item in value}

            # Словари
            if isinstance(value, dict):
                return {process_item(key): process_item(val) for key, val in value.items()}

            # NumPy массивы (если используется numpy)
            if hasattr(value, 'tolist') and hasattr(value, 'dtype'):
                return value.tolist()

            # Pandas объекты (если используется pandas)
            if hasattr(value, 'to_dict'):
                return value.to_dict()

            # Если дошли сюда - возвращаем как есть
            #print(f'{self.__class__.__name__}: значение типа {type(value).__name__} не обработано')
            return value

        def process_item(item):
            """Обрабатывает один элемент с перехватом исключений"""
            try:
                return process_value(item)
            except Exception as e:
                print(f'Ошибка при обработке элемента {type(item).__name__}: {e}')
                return item

        for name, attr in self.__dict__.items():
            if attr is self or name in self._UNSERIALIZABLE_ATTRS:
                continue

            try:
                result[name] = process_value(attr)
            except Exception as e:
                print(f'Ошибка при обработке атрибута {name}: {e}')
                result[name] = attr

        return result

    @classmethod
    def _import(cls, data, parent=None):
        """
        Восстанавливает объект из данных экспорта

        :param data: данные экспорта (словарь)
        :param parent: родительский объект (если есть)
        :return: восстановленный объект
        """
        # Создаем новый экземпляр класса
        obj = cls.__new__(cls)
        obj._lock_recalc = True

        # Устанавливаем родителя
        obj.parent = parent
        # Обрабатываем данные и устанавливаем атрибуты
        for name, value in data.items():
            # Пропускаем служебные поля и несериализуемые атрибуты
            if name in cls._UNSERIALIZABLE_ATTRS:
                continue

            # Обрабатываем значение в зависимости от его типа
            processed_value = cls._process_import_value(value, obj, name)

            # Устанавливаем атрибут
            setattr(obj, name, processed_value)



        # Вызываем пост-обработку если есть такой метод
        if hasattr(obj, '_post_import'):
            obj._post_import()
        obj._lock_recalc = False
        return obj

    @classmethod
    def _process_import_value(cls, value, current_obj=None, attr_name=None):
        """
        Рекурсивно обрабатывает значение при импорте
        """
        # Базовые типы
        if isinstance(value, (int, float, str, bool, type(None), bytes, bytearray)):
            return value

        # Списки - специальная обработка для списков объектов
        if isinstance(value, list):
            processed_list = []
            for item in value:
                # Проверяем, не является ли элемент словарем с информацией о классе
                if isinstance(item, dict) and '_class' in item and '_data' in item:
                    processed_item = cls._recreate_object_from_export(item, current_obj, attr_name)
                elif isinstance(item, dict) and 'code_mes' in item:
                    # Специальная обработка для EtapTreeDoc
                    try:
                        processed_item = EtapTreeDoc._import(item, current_obj)
                    except Exception as e:
                        print(f"Ошибка создания EtapTreeDoc: {e}")
                        processed_item = item
                else:
                    processed_item = cls._process_import_item(item, current_obj, attr_name)
                processed_list.append(processed_item)
            return processed_list

        # Кортежи
        if isinstance(value, tuple):
            return tuple(cls._process_import_item(item, current_obj, attr_name) for item in value)

        # Множества
        if isinstance(value, set):
            return {cls._process_import_item(item, current_obj, attr_name) for item in value}

        # Словари
        if isinstance(value, dict):
            # Проверяем, не является ли это экспортированным объектом
            if '_class' in value and '_data' in value:
                return cls._recreate_object_from_export(value, current_obj, attr_name)
            return {cls._process_import_item(k, current_obj, attr_name):
                        cls._process_import_item(v, current_obj, attr_name) for k, v in value.items()}

        return value
    @classmethod
    def _process_import_item(cls, item, current_obj=None, attr_name=None):
        """
        Обрабатывает один элемент с обработкой исключений
        """
        try:
            return cls._process_import_value(item, current_obj, attr_name)
        except Exception as e:
            print(f"Ошибка обработки элемента {type(item).__name__}: {e}")
            return item

    @classmethod
    def _recreate_object_from_export(cls, data, current_obj=None, attr_name=None):
        """
        Создает объект из данных с информацией о классе
        """
        if '_class' in data and '_data' in data:
            class_name = data['_class']
            obj_data = data['_data']

            # Ищем класс в текущем модуле и импортируемых модулях
            target_class = cls._find_class_by_name(class_name)

            if target_class and hasattr(target_class, '_import'):
                return target_class._import(obj_data, current_obj)
            elif target_class:
                # Для классов без метода _import создаем простой объект
                obj = target_class.__new__(target_class)
                for name, value in obj_data.items():
                    setattr(obj, name, value)
                return obj

        return data

    @classmethod
    def _find_class_by_name(cls, class_name):
        """
        Ищет класс по имени в доступных модулях
        """
        import sys
        import inspect

        # Проверяем текущий модуль
        current_module = sys.modules[__name__]
        if hasattr(current_module, class_name):
            return getattr(current_module, class_name)

        # Проверяем другие импортируемые модули
        modules_to_check = [
            'dataClass',
            'project_cust_38.Cust_resource_creator',
            # добавьте другие нужные модули
        ]

        for module_name in modules_to_check:
            try:
                module = __import__(module_name, fromlist=[class_name])
                if hasattr(module, class_name):
                    return getattr(module, class_name)
            except (ImportError, AttributeError):
                continue

        print(f"Класс {class_name} не найден")
        return None

    def _post_import(self):
        """
        Метод для пост-обработки после импорта
        Может быть переопределен в дочерних классах
        """
        # Восстанавливаем связи, которые не могли быть сериализованы
        pass


class Gui_page():
    def __init__(self, page, tbl, parent:Gui_tb):
        self.parent: Gui_tb = parent
        self.page:QtWidgets.QWidget = page
        self.tbl:QtWidgets.QTableWidget = tbl
        self.ind:int = self.parent._get_index_by_widget(self.page)
        self.text:str = self.parent.tb.itemText(self.ind)
        self.name:str = self.page.objectName()
    def clear(self):
        CQT.clear_tbl(self.tbl)

    def set_page_active(self):
        self.parent.tb.setCurrentIndex(self.ind)

    def set_text(self,txt:str):
        self.parent.tb.setItemText(self.ind,txt)


    def hide(self,val:bool=True):
        if  val:
            self.set_text('')
        else:
            self.set_text(self.text)


class Gui_tb():
    def __init__(self):
        self._app_self = DTCLS.app_self
        self._ui = self._app_self.ui
        self.tb:QtWidgets.QToolBox = self._ui.tb_elem
        self.pg_cards1c:Gui_page = Gui_page( self._ui.pg_cards1c, self._ui.tbl_card_nomen, self)
        self.pg_dse_attr:Gui_page  =Gui_page(  self._ui.pg_dse_attr,self._ui.tbl_cr_dse, self)
        self.pg_res_attr:Gui_page  =Gui_page(  self._ui.pg_res_attr,self._ui.tbl_cr_res, self)
        self.pg_etaps:Gui_page  =Gui_page(  self._ui.pg_etaps,self._ui.tbl_cr_etaps_res, self)
        self.dict_pgs:dict[int,Gui_page] = self._get_pgs()


    def _get_pgs(self)->dict[int,Gui_page]:
        res = dict()
        for name, attr in F.get_all_attrs_with_properties(self).items():
            if name.startswith('pg_'):
                attr:Gui_page
                res[attr.ind] = attr

        return res
    def _get_index_by_widget(self, widget:QtWidgets.QWidget):
        toolbox = self.tb
        """Получить индекс страницы по заголовку"""
        for i in range(toolbox.count()):
            if toolbox.widget(i) is widget:
                return i
        return -1  # если не найдено

    def _clear_all(self):
        for name, attr in F.get_all_attrs_with_properties(self).items():
            if name.startswith('pg_'):
                attr.clear()
                attr.hide(False)
        CQT.clear_tbl(self._ui.tbl_current_elem)
    def select_elem(self):
        self._clear_all()
        if DTCLS.current_elem.type_doc == TypesDoc.dse:
            self.pg_res_attr.hide()
            self.pg_etaps.hide()
            self.pg_dse_attr.set_page_active()
            self.tb.setDisabled(False)
        if DTCLS.current_elem.type_doc == TypesDoc.trd:
            self.pg_res_attr.hide()
            self.pg_dse_attr.hide()
            self.pg_etaps.hide()
            self.pg_cards1c.hide()
            self.tb.setDisabled(True)
        if DTCLS.current_elem.type_doc == TypesDoc.res:
            self.pg_res_attr.set_page_active()
            self.tb.setDisabled(False)
        if DTCLS.current_elem.type_doc == TypesDoc.none:
            self.pg_res_attr.hide()
            self.pg_dse_attr.hide()
            self.pg_etaps.hide()
            self.pg_cards1c.hide()
            self.tb.setDisabled(True)
        DTCLS.current_elem.fill_tables_dse_res()

    def select_import(self):
        self.pg_cards1c.set_page_active()
    @staticmethod
    def clear_current_elem():
        DTCLS.current_elem = None


    @staticmethod
    def toggle_select():
        self = DTCLS.app_self
        if self.ui.fr_select.isHidden():
            self.ui.fr_select.setHidden(False)
            self.ui.fr_left.setHidden(True)
        else:
            self.ui.fr_select.setHidden(True)
            self.ui.fr_left.setHidden(False)
            CQT.clear_tbl(self.ui.tbl_select)

    def get_page(self,ind:int)->Gui_page:
        return self.dict_pgs[ind]

class Stages_order:
    _DICT_STAGES = CSQ.custom_request_c(CFG.Config.project.db_dse, f"""SELECT * 
                  FROM constr_rs_order_stages;
                """, rez_dict=True)
    _DICT_STAGES_BY_NUM = F.deploy_dict_c(_DICT_STAGES, 's_num')
    _DICT_STAGES_BY_NAME = F.deploy_dict_c(_DICT_STAGES, 'name')

    def __init__(self, snum: int, *args):
        self.snum = snum
        self.name = Stages_order._DICT_STAGES_BY_NUM[self.snum]['name']
        self.description = Stages_order._DICT_STAGES_BY_NUM[self.snum]['description']
        self.percent = Stages_order._DICT_STAGES_BY_NUM[self.snum]['percent']

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Stages_order('{self.snum}', '{self.name}', '{self.description}', '{self.percent}')"


@dataclass(frozen=True)
class TypeDoc():
    name: str
    user_name: str
    path_conf_1c: str
    path_parent_conf_1c: str
    emo: CEMOJ.EmojiItem
    def __str__(self) -> str:
        return str(self.emo)

class TypesDoc():
    none: TypeDoc = TypeDoc('none','Не определено','','',CEMOJ.EmojiMain.СтатусыПроизводства.uncertain)
    dse: TypeDoc  = TypeDoc('dse','ДСЕ','Справочники.Номенклатура','Справочники.ВидыНоменклатуры',CEMOJ.EmojiMain.ОперацииПроизводства.dse)
    res: TypeDoc  = TypeDoc('res','Ресурсн.','Справочники.РесурсныеСпецификации','Справочники.РесурсныеСпецификации',CEMOJ.EmojiMain.ОперацииПроизводства.res)
    trd: TypeDoc  = TypeDoc('trd','Труды','','',CEMOJ.EmojiMain.ОперацииПроизводства.trd)
    osn_izd: TypeDoc  = TypeDoc('osn_izd','Осн.Изд.','','',CEMOJ.EmojiMain.ОборудованиеИнструменты.label)
    @staticmethod
    def calc_type_by_tch( СпособПолучения)->TypeDoc:
        if СпособПолучения == 'Произвести по спецификации':
            return TypesDoc.res
        else:
            return TypesDoc.dse

    @classmethod
    def list_types(cls)->list[TypeDoc]:
        return [v for k, v in vars(cls).items() if not k.startswith('__') and isinstance(v,TypeDoc)]
class BaseOrder():
    DICT_ALIASES = {
        "iD_card": "id_card_docs",
        "шифрИзделия_card": "product_code_card_docs",
        "номерПроекта_card": "project_number_card_docs",
        "номерПозиции_card": "position_number_card_docs",
        "наименование_card": "card_name_card_docs",
        "датаСоздания_card": "card_date_create_card_docs",
        "названиеВарианта_card": "card_variant_card_docs",
        "ссылкаДокс_card": "link_card_docs",
        "iD_proc": "id_processes_tkp_proc_docs",
        "ответственный_proc": "responsible_proc_docs",
        "комментарий_proc": "comment_proc_docs",
        "наименование_proc": "tkp_name_proc_docs",
        "этап_proc": "stage_proc_docs",
        "исполнитель_proc": "executor_proc_docs",
        "датаЗапуска_proc": "start_date_proc_docs",
        "статус_proc": "status_proc_docs",
        "желаемаяДата_proc": "wish_date_proc_docs",
        "кодРС_proc": "res_code_proc_docs",
        "ссылкаДокс_proc": "link_proc_docs",
        "uuiD_proc": "UID",

    }
    SET_EXCLUDED_FIELDS = {
        'wish_date_proc_docs', "res_code_proc_docs"}
class OrderDocs(BaseOrder):
    SET_DATE_FIELDS = {'card_date_create_card_docs','start_date_proc_docs'}
    def __init__(self,item:CDCS.ProcessTkp):

        self.id_card_docs: int | None = None
        self.product_code_card_docs: str | None = None
        self.project_number_card_docs: str | None = None
        self.position_number_card_docs: str | None = None
        self.card_name_card_docs: str | None = None
        self.card_date_create_card_docs: str | None = None
        self.card_variant_card_docs: str | None = None
        self.link_card_docs: str | None = None
        self.id_processes_tkp_proc_docs: int | None = None
        self.responsible_proc_docs: str | None = None
        self.comment_proc_docs: str | None = None
        self.tkp_name_proc_docs: str | None = None
        self.stage_proc_docs: str | None = None
        self.executor_proc_docs: str | None = None
        self.start_date_proc_docs: str | None = None
        self.status_proc_docs: str | None = None
        self.link_proc_docs: str | None = None
        self.UID: str | None = None

        for k, v in item._asdict().items():
            if k in self.DICT_ALIASES and self.DICT_ALIASES[k] not in self.SET_EXCLUDED_FIELDS:
                k = self.DICT_ALIASES[k]
                if k in self.SET_DATE_FIELDS:
                    if v:
                        v = F.dateStrToStr(v,format_out="%d.%m.%Y",onerror=v)
                exec(f'self.{k} = v')
                #type_val = str(type(v)).replace("<class '",'').replace("'>",'')
                #print(f'self.{k}:{type_val}|None = None')

        if self.link_card_docs:
            self.id_card_docs = '|'.join([self.link_card_docs, str(self.id_card_docs)])
        self.link_proc_docs = '|'.join([self.link_proc_docs, str(self.id_processes_tkp_proc_docs)])
    def get_process(self)->Process:
        process = Process(self.UID)
        return process
    def get_dict(self):
        return F.get_all_attrs_with_properties(self)


class OrdersDocs(BaseOrder):
    def __init__(self):

        self._db = CFG.Config.project.db_dse
        self.list_folders = None
        self.dict_orders_docs:dict[str,OrderDocs] = dict()

    def list_orders_docs(self)->list[dict]:
        result = []
        for v in self.dict_orders_docs.values():
            result.append(v.get_dict())
        return result
    def load_folders(self):
        with CDCS.TFlexTkpProcessClient() as client:
            key, data = client.get_tkp_folders()
            self.list_folders = data
    def get_data(self, UUID: str, active_process: bool,LIMIT_SECS:int=300)->list[dict]:
        if UUID == None:
            raise ValueError(f'UUID folder_uuid_lst is None')
        try:
            data_cache = CMS.load_tmp_stukt(f"constr_rs_orders_{UUID}{active_process}", False)
        except:
            data_cache = None
        fl_load_from_srv = True
        if data_cache:
            delta = (F.now('') - F.strtodate(data_cache['date'])).seconds
            if delta < LIMIT_SECS:
                fl_load_from_srv = False
        if fl_load_from_srv:
            with CDCS.TFlexTkpProcessClient() as client:
                key, data = client.get_process_tkp(folder_uuid_lst=[UUID], active_process=active_process)
            if not key == 200:
                CQT.msgbox(f'Ошибка получения данных из DOCs код {key}')
                data = data_cache['data']
            else:
                CMS.save_tmp_stukt({"data": data, "date": F.now()}, f"constr_rs_orders_{UUID}")
        else:
            data = data_cache['data']
        return data
    def load_process(self, UUID: str, active_process: bool):
        wet_data = self.get_data(UUID,active_process,LIMIT_SECS=300)


        for i, item in enumerate(wet_data):
            new_item = OrderDocs(item)

            self.dict_orders_docs[new_item.UID] = new_item

        list_mes = CSQ.custom_request_c(self._db, f"""SELECT s_num_docs 
                         FROM constr_rs_orders;
                       """, one_column=True, hat_c=False)
        set_orders_mes = set(list_mes)

        list_keys = ['s_num_docs', 'num_proc']
        list_vals = []
        for uid, docs_order in self.dict_orders_docs.items():
            if uid not in set_orders_mes:
                list_vals.append([uid, docs_order.id_processes_tkp_proc_docs])
        if list_vals:
            result = CSQ.custom_request_c(self._db,
                                          f"""Insert INTO constr_rs_orders ({CSQ.prepare_list_to_tuple(list_keys)}) VALUES ({CSQ.questions_for_mask(list_keys)})""",
                                          list_of_lists_c=list_vals)
            if not result:
                CQT.msgbox(f'Ошибка объединения с DOCs')
                return



class Erp_res():
    def __init__(self,doc_or_ref:TreeDoc|str):
        if isinstance(doc_or_ref,str):
            self.ref:str = doc_or_ref
        else:
            self.ref:str = doc_or_ref.ref

    def list_res(self):
        pass

    def get_tch_mat(self)->list[dict]:
        text = """
                    ВЫБРАТЬ
                    РесурсныеСпецификацииМатериалыИУслуги.НомерСтроки КАК N,
                    "" КАК Тип,
                    РесурсныеСпецификацииМатериалыИУслуги.Номенклатура КАК Номенклатура,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Ссылка)) КАК ref, 
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.ВидНоменклатуры.Ссылка)) КАК ref_parent,
                    РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Код КАК Код,
                    РесурсныеСпецификацииМатериалыИУслуги.Характеристика КАК Характеристика,

                    РесурсныеСпецификацииМатериалыИУслуги.КоличествоУпаковок КАК Количество,
                    РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдИзм,
                    РесурсныеСпецификацииМатериалыИУслуги.СпособПолученияМатериала КАК СпособПолучения,
                    РесурсныеСпецификацииМатериалыИУслуги.Этап.Наименование КАК ЭтапНаименование,
                    РесурсныеСпецификацииМатериалыИУслуги.ИсточникПолученияПолуфабриката КАК Источник,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификацииМатериалыИУслуги.СтатьяКалькуляции)) КАК СтатьяКалькуляции_ref,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификацииМатериалыИУслуги.ИсточникПолученияПолуфабриката)) КАК ref_res,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификацииМатериалыИУслуги.СпособПолученияМатериала)) КАК СпособПолученияМатериала_ref
                    ИЗ
                        Справочник.РесурсныеСпецификации.МатериалыИУслуги КАК РесурсныеСпецификацииМатериалыИУслуги
                    ГДЕ
                        РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Ссылка = &Ссылка

                    УПОРЯДОЧИТЬ ПО
                        НомерСтроки
                                            """
        refs = APIERP.Refs_wet(text)
        ref_obj = APIERP.Ref_wet('Ссылка', TypesDoc.res.path_conf_1c, self.ref)
        refs.add_ref(ref_obj)
        if (tch := APIERP.get_wet_request_result(text=text, refs=refs,
                                                 msg_err=f'{TypesDoc.res.user_name} не найдены TЧ')) is None:
            return []
        return  tch

    def get_tch_trdz(self)->list[dict]:
        text = """
                ВЫБРАТЬ
                    РесурсныеСпецификацииТрудозатраты.НомерСтроки КАК N,
                    "" КАК Тип,
                    РесурсныеСпецификацииТрудозатраты.ВидРабот КАК ВидРабот,
                    РесурсныеСпецификацииТрудозатраты.ВидРабот.Код КАК Код,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификацииТрудозатраты.ВидРабот.Ссылка)) КАК ref, 
                    РесурсныеСпецификацииТрудозатраты.Этап.Наименование КАК ЭтапНаименование, 
                    РесурсныеСпецификацииТрудозатраты.Количество КАК Количество,
                    РесурсныеСпецификацииТрудозатраты.ВидРабот.ЕдиницаИзмерения КАК ЕдИзм
                ИЗ
                    Справочник.РесурсныеСпецификации.Трудозатраты КАК РесурсныеСпецификацииТрудозатраты
                ГДЕ
                    РесурсныеСпецификацииТрудозатраты.Ссылка.Ссылка = &Ссылка

                УПОРЯДОЧИТЬ ПО
                    РесурсныеСпецификацииТрудозатраты.НомерСтроки
                                """
        refs = APIERP.Refs_wet(text)
        ref_obj = APIERP.Ref_wet('Ссылка', TypesDoc.res.path_conf_1c, self.ref)
        refs.add_ref(ref_obj)
        trdz = APIERP.get_wet_request_result(text=text, refs=refs,msg_err=None)
        if trdz is None:
            return []
        return  trdz

class Process():

    def __init__(self,s_num_docs:str):
        self.num_proc: int|None = None
        self.documents_link: str|None = None
        self.name_nomen_for_res_product: str|None = None
        self.order_stage: int|Stages_order|None = None
        self.res_blob: bytes|None = None
        self.res_product: str|None = None
        self.s_num: int|None = None
        self.s_num_docs: str|None = None
        self.tree_res: TreeRes|None = None

        data = CSQ.custom_request_c( CFG.Config.project.db_dse, f"""SELECT * FROM constr_rs_orders WHERE s_num_docs = '{s_num_docs}';""",rez_dict=True,one=True)
        for key in data.keys():
            exec(f'self.{key.replace(".","_")} = data[key]')
        self.order_stage = Stages_order(self.order_stage)
        if self.res_blob:
            self.res_blob = F.from_binary_pickle(self.res_blob)
        self.order:OrderDocs = self.load_order()
    def __str__(self):
        return (f'{self.num_proc} {self.order.card_name_card_docs}'
                f' {self.order.product_code_card_docs}.{self.order.project_number_card_docs}'
                f'.{self.order.position_number_card_docs}')
    @classmethod
    def update_view(cls,uid_folder_docs=None):
        if uid_folder_docs is None:
            uid_folder_docs = DTCLS.current_folder_docs.uuid
        if uid_folder_docs is None:
            return
        orders = OrdersDocs()
        orders.load_process(uid_folder_docs, not DTCLS.app_self.ui.chk_wo_not_active_prcss.isChecked())
        DTCLS.dict_orders_docs = orders.dict_orders_docs
        resp = CSQ.custom_request_c(CFG.Config.project.db_dse, f"""SELECT 

            order_stage,
            documents_link,
            name_nomen_for_res_product,
            res_product,
            s_num_docs 
                              FROM constr_rs_orders WHERE s_num_docs in ({','.join([f'"{_}"' for _ in orders.dict_orders_docs.keys()])}) ;
                            """, rez_dict=True)
        data = F.left_join(resp, orders.list_orders_docs(), "s_num_docs", "UID", delete_key="UID")

        tbl = DTCLS.app_self.ui.tbl_list_orders
        CQT.set_color_sort_cell_table_c(tbl)

        selected_ind = tbl.currentIndex()
        data = DTCLS.PARAMS_FIELDS_DB.apply_alias_list(data)

        def fnc_clear_res(self, s_num_docs:str):
            print(f"\n=== ВЫЗОВ fnc_clear_res ===")
            print(f"Параметр s_num_docs: {s_num_docs}")

            # Добавляем трассировку
            import traceback
            print("Стек вызовов в fnc_clear_res:")
            for line in traceback.format_stack()[-10:]:
                print(f"  {line.strip()}")

            # Оригинальный код функции
            order: OrderDocs = DTCLS.dict_orders_docs[s_num_docs]
            process: Process = order.get_process()
            process.clear_res()
            # Проверяем, не вызывает ли что-то обновление таблицы
            print("=== ПРОВЕРКА ПОСЛЕ ВЫПОЛНЕНИЯ ===")

            # Если функция что-то делает с таблицей, добавьте принты



        @CQT.onerror
        def fncContextMenu(self: mywindow, tbl: QtWidgets.QTableWidget, row: int, col: int,
                           menu_builder: CQT.ContextMenuBuilder):
            print("CONTEXT OPEN CALLED")
            menu_builder.add_submenu(f" {CEMOJ.EmojiMain.ОперацииПроизводства.res.symbol} Ресурсная    ")


            s_num_docs = CQT.get_dict_line_form_tbl(tbl,row)['s_num_docs']
            fnc = partial(fnc_clear_res, self, s_num_docs)
            menu_builder.add_menu(f'{CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol} открепить', fnc)

            menu_builder.end_submenu()
        CQT.fill_wtabl(data, tbl, load_links=True, selectionBehavior='SelectRows', selectionMode='SingleSelection',
                       sortingEnabled=True, list_column_widths=CMS.load_column_widths(DTCLS.app_self, tbl),
                       save_column_sort_hh=True, auto_type=True,fncContextMenu=fncContextMenu)
        cls.oform_tbl(data)
        CMS.fill_filtr_c(DTCLS.app_self, DTCLS.app_self.ui.tbl_list_orders_filtr, tbl, hidden_scroll=True)

    def save_res(self):
        DTCLS.current_process.res_product = DTCLS.current_process.tree_res.get_root().code.code
        DTCLS.current_process.res_blob = F.to_binary_pickle(DTCLS.tree_data_manager.generate_tree_lite())
        DTCLS.current_process.name_nomen_for_res_product = DTCLS.current_process.tree_res.get_root().cr_res_data.schema.ОсновноеИзделиеКод
        DTCLS.current_process.save()  # при записи в БД обновить ТЧ
    def clear_res(self):
        DTCLS.current_process.res_product = None
        DTCLS.current_process.res_blob = None
        DTCLS.current_process.name_nomen_for_res_product = None
        DTCLS.current_process.save()
        DTCLS.treeNavigator.clear_table()
        DTCLS.gui_qt.clear_current_elem()
        DTCLS.gui_qt._clear_all()
    @staticmethod
    def oform_tbl( data: list[dict]):
        dict_states = {
            '': 0,
            'Отменён': 0,
            'Завершён': 100,
            'В очереди': 30,
            'В работе': 55,
            'Новый': 14
        }
        tbl = DTCLS.app_self.ui.tbl_list_orders
        nf_state_docs = CQT.num_col_by_name_c(tbl, 'Cтатус в\nDocs')
        nf_state_mes = CQT.num_col_by_name_c(tbl, 'Стадия ТКП')

        for i in range(tbl.rowCount()):
            if nf_state_docs is not None:
                state: str = tbl.item(i, nf_state_docs).text()
                percent = dict_states.get(state, 0)
                if state not in dict_states:
                    print(f"'{state}':0,")
                clr = CMS.Color_tbl(percent)
                CQT.set_color_wtab_c(tbl, i, nf_state_docs, clr.r, clr.g, clr.b)
            if nf_state_mes is not None:
                state: Stages_order = Stages_order(data[i]['Стадия ТКП'])
                clr = CMS.Color_tbl(state.percent)
                CQT.set_color_wtab_c(tbl, i, nf_state_mes, clr.r, clr.g, clr.b)
                CQT.setCustData(tbl.item(i, nf_state_mes), state)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 's_num_docs'), True)
        # tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,'res_blob'),True)

    def save(self):
        data = CSQ.custom_request_c(CFG.Config.project.db_dse,
                                    f"""SELECT * FROM constr_rs_orders WHERE s_num_docs = '{self.s_num_docs}';""",
                                    rez_dict=True, one=True)
        names_to_save= []
        vals_to_save= []
        for key, val in data.items():
            name = key.replace(".", "_")
            if hasattr(self,name):
                val_attr = getattr(self,name)
                if name == 'res_blob':
                    val_attr = F.to_binary_pickle(val_attr)
                if name == 'order_stage':
                    val_attr = val_attr.snum
                if val_attr  != val:
                    names_to_save.append(key)
                    vals_to_save.append(val_attr)

        if names_to_save:
            if not CSQ.custom_request_c(
                CFG.Config.project.db_dse,f"""UPDATE constr_rs_orders SET  ({CSQ.prepare_list_to_tuple(names_to_save)})
                    = ({CSQ.questions_for_mask(names_to_save)}) WHERE s_num_docs = '{self.s_num_docs}';""" , list_of_lists_c=[vals_to_save]
            ):
                CQT.msgbox(f'Ошибка сохранения в МЕС {str(self)}')
                return

        self.update_view()


    def load_order(self):
        uid = self.s_num_docs
        return DTCLS.dict_orders_docs[uid]

    def setCurrentProcess(self,data_cls:type[dataClass.data_app]):
        data_cls.current_process = self
        num = 'не выбран'
        if data_cls.current_process:
            num = str(data_cls.current_process)
        data_cls.app_self.ui.lbl_current_proj.setText(f'Текущий процесс: {num}')

    def clear(self):
        self.num_proc: int | None = None
        self.documents_link: str | None = None
        self.name_nomen_for_res_product: str | None = None
        self.order_stage: int | Stages_order | None = None
        self.res_blob: bytes | None = None
        self.res_product: str | None = None
        self.s_num: int | None = None
        self.s_num_docs: str | None = None
        self.tree_res: TreeRes | None = None


class Code(Base_cls):
    _UNSERIALIZABLE_ATTRS = {'parent','_lock_recalc'}
    def __init__(self, parent:TreeDoc, code: str=None, is_exists_doc:bool|None=None, check_code:bool = True):
        self._forced_check:bool = True if is_exists_doc is None else False
        self.is_exists = None
        self.parent: TreeDoc = parent
        self._check_code:bool = check_code
        self.code: str | None = code
        if self._forced_check and self._check_code:
            self.update_exists()
        else:
            self.is_exists: bool | None = is_exists_doc
        self._check_code = True

    def __str__(self):
        res_nomen_code_descr = ''
        if self.parent.type_doc == TypesDoc.res:
            res_nomen_code_descr = TypesDoc.osn_izd.emo.symbol
            if self.parent.cr_res_data:
                code_nomen = self.parent.cr_res_data.schema.ОсновноеИзделиеКод
                if code_nomen and code_nomen.startswith('00-'):
                    res_nomen_code_descr = ''

        if self.is_exists:
            return f'{CEMOJ.EmojiMain.СтатусыПроизводства.success.symbol}{self.code}{res_nomen_code_descr}'
        else:
            if self.parent._filled_bodyHat_erp_export:
                return f'{CEMOJ.EmojiMain.Документы.soon.symbol}{res_nomen_code_descr}'
            else:
                return f'{CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol}'

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if self._lock_recalc:
            return
        if name == 'code' or name == 'type_doc':
            if getattr(self, 'code',False) and getattr(self, 'type_doc',False) and self._forced_check and self._check_code:
                self.is_exists = self.calc_is_exists()
        if getattr(self, 'parent', None):
            self.parent.update_attr_into_gui_obj('code')


    def update_exists(self):
        self.is_exists: bool | None = self.calc_is_exists()

    def val_for_edit(self):
        return self.code
    def calc_is_exists(self)->bool:
        if self.parent.type_doc == TypesDoc.trd:
            return True

        text = None
        if self.code is None or self.code == '':
            return False
        if self.parent.type_doc == TypesDoc.res:
            text = f""" 
                ВЫБРАТЬ
                    РесурсныеСпецификации.Код КАК Код
                ИЗ
                    Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                ГДЕ
                    РесурсныеСпецификации.Код = "{self.code}";
                                        """
        elif self.parent.type_doc == TypesDoc.dse:
            text = f""" 
                            ВЫБРАТЬ
                                Номенклатура.Код КАК Код
                            ИЗ
                                Справочник.Номенклатура КАК Номенклатура
                            ГДЕ
                                Номенклатура.Код = "{self.code}";
                                                    """

        if text:
            key, res = APIERP.get_wet_request(text=text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')
                return False
            if not res['data']:
                return False
            else:
                return True
        return False
    def clear(self):
        self.code = None
        self.is_exists = False
        self.parent.update('code')




class EtapTreeDoc(Base_cls):
    ALIASES = {'name':'Имя',
               'code_mes': 'Код',
               'code_podrazd': 'Подразделение код',
               'minutes': 'Минут',

               }
    _UNSERIALIZABLE_ATTRS = {'parent','_lock_recalc'}
    def __init__(self,code_mes:int,parent:TreeDoc|None):
        self._inited = False
        if code_mes not in DTCLS.DICT_ETAPS:
            if F.is_numeric(code_mes):
                msg = f'Код этапа "{code_mes}" не найден в БД для {CFG.Config.place.Имя}\nПроверить Опции->Организация'
                CQT.msgbox(msg)
                return
            raise ValueError(f'code_mes not in DTCLS.DICT_ETAPS')
        self._mes_row = DTCLS.DICT_ETAPS[code_mes]
        self.code_mes: int | None = code_mes
        self.name:str|None = self._mes_row['name']
        self.code_podrazd:str|None = None
        self.minutes:int|float|None = None
        self.parent:TreeDoc = parent
        self._inited = True

    @classmethod
    def _import(cls, data, parent=None):
        """
        Специфичный импорт для EtapTreeDoc
        """
        if isinstance(data, dict):
            # Если данные в формате полного экспорта
            code_mes = data.get('code_mes')
            if code_mes is None:
                return None

            obj = cls.__new__(cls)
            obj._inited = True

            # Восстанавливаем основные атрибуты
            obj.code_mes = code_mes
            obj.name = data.get('name')
            obj.code_podrazd = data.get('code_podrazd')
            obj.minutes = data.get('minutes')
            obj.parent = parent

            # Восстанавливаем _mes_row
            if '_mes_row' in data:
                obj._mes_row = data['_mes_row']
            else:
                # Ищем в DTCLS.DICT_ETAPS
                if code_mes in DTCLS.DICT_ETAPS:
                    obj._mes_row = DTCLS.DICT_ETAPS[code_mes]
                else:
                    print(f"Предупреждение: код этапа {code_mes} не найден в DTCLS.DICT_ETAPS")
                    obj._inited = False
            obj._lock_recalc = False
            return obj

        else:
            # Если данные - просто code_mes (число)
            return cls(data, parent)

    def apply_aliases(self,k:str):
        if k in self.ALIASES:
            return self.ALIASES[k]
        return k
    def get_dict(self):
        EXCLUDE_FIELDS = 'parent'
        return  {self.apply_aliases(k):v for k,v in  self.__dict__.items() if not k.startswith(("_", "__")) and k not in EXCLUDE_FIELDS}

    def copy_params(self,from_obj:EtapTreeDoc|None):
        if from_obj == None:
            return
        self.code_mes = from_obj.code_mes
        self._mes_row = from_obj._mes_row
        self.code_podrazd = from_obj.code_podrazd
        self.minutes = from_obj.minutes
        self.name = from_obj.name
    def __str__(self):
        return f'{self.name}'

class TreeDoc(Base_cls):
    ALIASES = {
        'type_doc': 'Тип',
        'name': 'Наименование',
        'code': 'Код',
        'count': 'КолВо',
        'changed': 'Изменен',
        'belongs_to_etap': 'Этап',
        'parent': 'Родитель'
    }

    NOT_HIDDEN_FIELDS = {
        'type_doc',
        'name',
        'code',
        'count',
        'changed',
        'belongs_to_etap',
    }

    EDITABLE_VIEW_ATTRS = {'count','name'}
    ATTRS_FOR_CHANGED_ITEM = {'code','name'}
    ATTRS_FOR_CHANGED_PARENT = {'code','name','count'}
    ROOT_NON_EDITABLE_VIEW_ATTRS= {'count'}

    _UNSERIALIZABLE_ATTRS = {
            '_me',
            '_gui_obj',
            'parent',
            '_TreeDoc__dict_attrs_properties',
            'parent','_lock_recalc'
        }

    _UNSET = object()
    def __init__(self,
                 tree:TreeRes,
                 type_doc:TypeDoc,
                 gui_obj: CTREE.ExtTreeWidgetItem|None,
                 name: str = None,
                 code: str=None,
                 ref: str = None,
                 count: float|None = 0,
                 level_index:int=0,
                 ref_struct_parent: str|None = None,
                 uid_parent: str = None,
                 check_code:bool = True
                 ):
        if not F.is_numeric(count) and count is not  None:
            raise TypeError(f'not F.is_numeric(count)')
        if isinstance(count,str):
            count = F.valm(count)
        self._gui_obj: CTREE.ExtTreeWidgetItem | None = gui_obj
        self._uid_parent: str | None = uid_parent
        self.type_doc: TypeDoc = TypesDoc.res if self.is_root() else type_doc
        self.name: str|None = name
        self._code: Code | None = Code(self, code,check_code=check_code)
        self._ref: str|None = ref
        self._filled_bodyHat_erp_export: bool = False

        self._changed: bool = False
        self._uid: str = str(uuid.uuid4())
        self._level_index: int = level_index
        self._ref_struct_parent: str|None = ref_struct_parent

        self.parent: TreeRes | None = tree
        self._count: float | None = 1 if self.is_root() else count
        self._me = self
        self.level_gui = 0
        self.__dict_attrs_properties = F.get_class_properties(self)

        self._belongs_to_etap:EtapTreeDoc|None = None
        self._cr_res_data:CrResData|None = None
        self._cr_dse_data:CrDseData|None = None
        if self.type_doc == TypesDoc.res:
            self._cr_res_data:CrResData = CrResData(self)
            self._cr_dse_data: CrDseData = CrDseData(self)
        if self.type_doc == TypesDoc.dse:
            self._cr_dse_data:CrDseData = CrDseData(self)
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if self._lock_recalc:
            return
        self.update(name,value)

    @classmethod
    def _import(cls, data, parent=None):
        """
        Специфичный импорт для TreeDoc
        """
        # Создаем базовый объект
        obj = super()._import(data, parent)
        obj._lock_recalc = True
        # Восстанавливаем специальные атрибуты
        if '_old_uid' in data:
            obj._old_uid = data['_old_uid']

        # Инициализируем свойства
        obj.__dict_attrs_properties = F.get_class_properties(obj)
        obj._me = obj
        # Теперь создаем Code с правильными параметрами
        code_value:dict = data.get('_code')
        code_is_exists:bool = data.get('_code.is_exists', None)
        obj._code = Code(obj, code_value['code'], is_exists_doc=code_is_exists, check_code=False)

        # Восстанавливаем связанные объекты
        if '_cr_res_data' in data and data['_cr_res_data'] is not None:
            obj._cr_res_data = CrResData._import(data['_cr_res_data'], obj)

        if '_cr_dse_data' in data and data['_cr_dse_data'] is not None:
            obj._cr_dse_data = CrDseData._import(data['_cr_dse_data'], obj)

        if '_belongs_to_etap' in data and data['_belongs_to_etap'] is not None:
            obj._belongs_to_etap = EtapTreeDoc._import(data['_belongs_to_etap'], obj)
        obj._lock_recalc = False
        return obj

    def _export(self):
        result = {
            'parent': None,
            '_gui_obj': None,
        }

        # Словарь кастомных обработчиков для специфичных типов
        CUSTOM_HANDLERS = {
            # 'datetime': lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x),
            # 'date': lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x),
            # 'time': lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x),
            # 'decimal': lambda x: float(x) if hasattr(x, '__float__') else str(x),
        }

        def process_value(value):
            """Рекурсивно обрабатывает значение для экспорта"""
            # Базовые типы
            if isinstance(value, (int, float, str, bool, type(None), bytes, bytearray)):
                return value

            # Объекты с методом _export
            if hasattr(value, '_export'):
                return value._export()

            # Проверка кастомных обработчиков
            type_name = type(value).__name__.lower()
            if type_name in CUSTOM_HANDLERS:
                return CUSTOM_HANDLERS[type_name](value)

            # Списки
            if isinstance(value, list):
                return [process_item(item) for item in value]

            # Кортежи
            if isinstance(value, tuple):
                return tuple(process_item(item) for item in value)

            # Множества
            if isinstance(value, set):
                return {process_item(item) for item in value}

            # Словари
            if isinstance(value, dict):
                return {process_item(key): process_item(val) for key, val in value.items()}

            # NumPy массивы (если используется numpy)
            if hasattr(value, 'tolist') and hasattr(value, 'dtype'):
                return value.tolist()

            # Pandas объекты (если используется pandas)
            if hasattr(value, 'to_dict'):
                return value.to_dict()

            # Если дошли сюда - возвращаем как есть
            #print(f'{self.__class__.__name__}: значение типа {type(value).__name__} не обработано')
            return value

        def process_item(item):
            """Обрабатывает один элемент с перехватом исключений"""
            try:
                return process_value(item)
            except Exception as e:
                print(f'Ошибка при обработке элемента {type(item).__name__}: {e}')
                return item

        for name, attr in self.__dict__.items():
            if attr is self or name in self._UNSERIALIZABLE_ATTRS:
                continue

            try:
                result[name] = process_value(attr)
            except Exception as e:
                print(f'Ошибка при обработке атрибута {name}: {e}')
                result[name] = attr

        #if name in ('_cr_res_data', '_belongs_to_etap', '_cr_dse_data'):
        #    if attr is not None:
        #        if name == '_cr_res_data':
        #            attr = self._cr_res_data.gen_params_for_save()
        #        if name == '_cr_dse_data':
        #            attr = self._cr_dse_data.gen_params_for_save()
        #        if name == '_belongs_to_etap':
        #            attr = attr.code_mes


        result['_old_uid'] = self.uid
        result['_code.is_exists'] = self._code.is_exists
        return result




    def recalc_filled_bodyHat_erp_export(self):
        if self.type_doc == TypesDoc.res:
            if self._cr_res_data is not  None and self._cr_dse_data is not None:
                self._filled_bodyHat_erp_export = self._cr_res_data._check_res_filled() and self._cr_dse_data._check_dse_filled()
        if self.type_doc == TypesDoc.dse:
            if self._cr_dse_data is not None:
                self._filled_bodyHat_erp_export = self._cr_dse_data._check_dse_filled()
    def get_childs(self)->set[TreeDoc]:
        tree = self.parent
        return tree.get_childs(self.uid)

    def make_doc_erp(self)->tuple[bool, list[str]]:
        suc:bool = False
        errs:list[str] = []
        if self.type_doc == TypesDoc.res:
            if self.cr_res_data.schema.ref_output_dse == None:
                suc, errs = self._make_dse_erp(output_izd=True)
                return suc, errs
            else:
                if not self.code.is_exists:
                    suc, errs = self._make_res_erp()
        if self.type_doc == TypesDoc.dse:
            suc, errs = self._make_dse_erp()
        return suc , errs

    def _make_res_erp(self):
        suc, errs = self._cr_res_data.export_to_1c()
        if suc:
            self._set_new_code_into_doc(errs)
        return suc, errs
    def _make_dse_erp(self,output_izd:bool=False):
        suc, errs = self._cr_dse_data.export_to_1c()
        if suc:
            self._set_new_code_into_doc(errs,output_izd=output_izd)
        return suc, errs

    def _set_new_code_into_doc(self, data:dict , output_izd:bool=False):
        ref: str | None = data['RefKey']
        if output_izd:
            self._cr_res_data.schema.ref_output_dse = ref
            code: str | None = data['Код']
            self._cr_res_data.schema.ОсновноеИзделиеКод  = code
        else:
            self.ref = ref
        self.code = self.code
        if self.ref:
            self.reload_erp()


    def recalc_filled_bodyHat(self):
        if self.type_doc == TypesDoc.res:
            self._cr_res_data.schema.get_vals_from_parent()
            self._cr_res_data._recalc_docRes_filled()
            self._cr_dse_data._recalc_hat_filled()
        if self.type_doc == TypesDoc.dse:
            self._cr_dse_data._recalc_hat_filled()

    def update_doc_ready_state(self):
        if self.type_doc == TypesDoc.res:
            if self._cr_res_data is None:
                return
            self._cr_res_data.update_doc_ready_state()
            self._cr_dse_data.update_doc_ready_state()
            return
        if self.type_doc == TypesDoc.dse:
            if self._cr_dse_data is None:
                return
            self._cr_dse_data.update_doc_ready_state()
            return

    def fill_tables_dse_res(self):
        if self.type_doc == TypesDoc.res:
            self._cr_res_data.fill_tables()
            self._cr_dse_data.fill_tables()
        if self.type_doc == TypesDoc.dse:
            self._cr_dse_data.fill_tables()

    @property
    def nesting_level(self) -> int:
        level = 0
        parent_uid = self._uid_parent
        while parent_uid is not None:
            parent_obj = self.parent.find_by_uid(parent_uid)
            parent_uid = parent_obj._uid_parent
            level += 1
        return level


    @property
    def count(self) -> int|float|None:
        return self._count

    @count.setter
    def count(self, val: int|str|None | int):
        if val is None:
            self._count = None
            return
        if isinstance(val, str):
            self._count = F.valm(val)
            return
        if isinstance(val, (int,float)):
            self._count = val
            return
        raise TypeError(f'count.setter')

    @property
    def belongs_to_etap(self) -> EtapTreeDoc:
        return self._belongs_to_etap

    @belongs_to_etap.setter
    def belongs_to_etap(self, val: EtapTreeDoc | int):
        if isinstance(val, EtapTreeDoc):
            self._belongs_to_etap = val
            return
        self._belongs_to_etap = EtapTreeDoc(val,self)

    @property
    def me(self)->TreeDoc:
        return self

    @me.setter
    def me(self, val):
        return


    @property
    def code(self)-> Code:
        return self._code
    @code.setter
    def code(self, val: Code|str):
        if isinstance(val,Code):
            self._code = val
        elif isinstance(val,str):
            if self._code is None:
                raise AttributeError(f'code is None')
            else:
                self._code.code = val
        else:
            raise TypeError(f'code Type is not Code|str')
    @property
    def gui_obj(self)->CTREE.ExtTreeWidgetItem:
        return self._gui_obj
    @gui_obj.setter
    def gui_obj(self, val: CTREE.ExtTreeWidgetItem):
        self._gui_obj = val

    @property
    def level_index(self)->int:
        return self._level_index
    @level_index.setter
    def level_index(self, val: int):
        self._level_index = val
    @property
    def changed(self)->str:
        return  CEMOJ.EmojiMain.СтатусыПроизводства.warning.symbol  if self._changed else ''
    @changed.setter
    def changed(self,val:bool):
        self._changed = val
    @property
    def uid(self)->str:
        return self._uid
    @uid.setter
    def uid(self,val:str):
        self._uid= val

    @property
    def ref(self)->str:
        return self._ref
    @ref.setter
    def ref(self,val:str):
        self._ref= val

    @property
    def ref_struct_parent(self)->str:
        return self._ref_struct_parent
    @ref_struct_parent.setter
    def ref_struct_parent(self,val:str):
        self._ref_struct_parent= val

    @property
    def uid_parent(self)->str:
        return self._uid_parent
    @uid_parent.setter
    def uid_parent(self,val:str):
        self._uid_parent= val

    @property
    def cr_res_data(self)->CrResData:
        return self._cr_res_data
    @property
    def cr_dse_data(self)->CrDseData:
        return self._cr_dse_data



    def is_name_res_exists_in_nomen_erp(self)->dict:
        name = self.name
        if name is not None and len(name):

            text = f"""
                        ВЫБРАТЬ
                        Номенклатура.Код КАК Код,
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Ссылка)) КАК ref
                    ИЗ
                        Справочник.Номенклатура КАК Номенклатура
                    ГДЕ
                        Номенклатура.Наименование = "{name}" 
                        И Номенклатура.ПометкаУдаления = ЛОЖЬ
                        """

            key, res = APIERP.get_wet_request(text=text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')
                return dict()
            if not res['data']:
                return dict()
            else:
                return res['data'][0]
        return dict()

    def is_nomen_name_exists_erp(self,name:str=None)->bool:
        if name is None:
            name = self.name
        if name is not None and len(name):
            text = None
            if self.type_doc == TypesDoc.dse:
                text = f"""
                            ВЫБРАТЬ
                            Номенклатура.Код КАК Код
                        ИЗ
                            Справочник.Номенклатура КАК Номенклатура
                        ГДЕ
                            Номенклатура.Наименование = "{name}" 
                            И Номенклатура.ПометкаУдаления = ЛОЖЬ
                        """
            if self.type_doc == TypesDoc.res:
                text = f"""
                           ВЫБРАТЬ
                           РесурсныеСпецификации.Код КАК Код
                       ИЗ
                           Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                       ГДЕ
                           РесурсныеСпецификации.Наименование = "{name}" 
                           И РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
                       """
            if text is None:
                return False
            key, res = APIERP.get_wet_request(text=text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')
                return True
            if not res['data']:
                return False
            else:
                return True
        return False
    def is_code_exists_erp(self)->bool:
        self.code.update_exists()
        return self.code.is_exists



    def set_select_gui(self):
        item = self.gui_obj
        self.parent.tree_gui.setCurrentItem(item)
        item.setSelected(True)
        self.parent.tree_gui.scrollToItem(item)
        # вручную эмитируем сигнал, если нужно поведение клика
        index = self.parent.tree_gui.indexFromItem(item)
        self.parent.tree_gui.clicked.emit(index)


    def get_parent(self)->None|TreeDoc:
        if self.uid_parent is None:
            return None
        return self.parent.find_by_uid(self.uid_parent)
    def еrror_name(self):
        row = ''
        if self.name:
            row += f'Имя:{self.name}'
        if self.code.code:
            row += f'Код:{self.code.code}'
        if not row:
            if self.is_root():
                row += f'Корневой узел'
            else:
                parent = self.get_parent()
                if parent:
                    if parent.is_root():
                        row += f'Входящий в корневой узел, строка {self._level_index+1}'
                    else:
                        if parent.name or parent.code.code:
                            row += f'Входящий в: {parent.name}({parent.code.code}) строка {self._level_index+1}'
        if self.uid and not row:
            row += f'uid:{self.uid}'

        return row



    def calc_plan_for_1c_export(self)->list[dict]:
        list_reg = []
        for uid, row in self.parent.tree_rows.items():
            if row.changed:
                list_reg.append({'uid':row.uid,
                                 'Тип':row.type_doc.user_name,
                                 ' ':row.type_doc.emo,
                                 'Наименование':row.gui_str(),
                                 'Действие':'Создать',
                                 'Результат':'',
                                 'Код':'',
                                 'Несоответствия':''})
            if row.type_doc == TypesDoc.res:
                if row.cr_res_data.schema.ref_output_dse == None:
                    list_reg.append({'uid':row.uid,
                                     'Тип': TypesDoc.osn_izd.user_name,
                                     ' ': TypesDoc.osn_izd.emo,
                                     'Наименование':row.cr_dse_data,
                                     'Действие':'Создать',
                                     'Результат':'',
                                     'Код':'',
                                     'Несоответствия':''})
        return list_reg

    def check_ready_for_1c_export(self,list_err:ErrorsTreeDoc|None=None)->tuple[bool,ErrorsTreeDoc]:
        if list_err is None:
            errors = ErrorsTreeDoc()
        else:
            errors = list_err
        success = True
        childs = self.parent.get_childs(self.uid)
        for child in childs:
            suc_chld, errs_result = child.check_ready_for_1c_export(errors)
            if not suc_chld:
                success = False

        if self.type_doc == TypesDoc.none:
            errors.add_err(self, f'не выбран тип элемента')
        else:
            if self.changed:
                if not self._filled_bodyHat_erp_export :
                    success = False
                    errors.add_err(self, f'не готов для выгрузки')
                    if not self._cr_res_data is None:
                        if not self._cr_res_data.body_filled:
                            errors.add_err(self, f'не заполнены параметры этапов')
                        if not self._cr_res_data.hat_filled:
                            errors.add_err(self, f'не заполнены РЕС атрибуты')
                            for attr in self._cr_res_data.schema.get_not_filled_attrs():
                                errors.add_err(self, f'    не заполнен {attr}')
                    if not self._cr_dse_data is None:
                        if not self._cr_dse_data.hat_filled:
                            errors.add_err(self, f'не заполнены ДСЕ основные атрибуты')
                            for attr in self._cr_dse_data.get_not_filled_attrs():
                                errors.add_err(self, f'    не заполнен {attr}')
                        if not self._cr_dse_data.body_filled:
                            errors.add_err(self, f'не заполнены ДСЕ атрибуты')
                            for attr in self._cr_dse_data.body.get_unfilled_atts():
                                errors.add_err(self, f'    не заполнен {attr}')
                else:
                    if self.is_nomen_name_exists_erp():
                        success = False
                        errors.add_err(self, f'Наименование уже существует в 1с')
            else:
                if not self.is_code_exists_erp():
                    success = False
                    errors.add_err(self, f'Код не существует в 1с')
            if not self.is_root() and self.belongs_to_etap is None:
                errors.add_err(self, f'не выбран этап')
            # ===========check poki filtr by code depatment=====================
            if self.cr_res_data is not None:
                for name_etap, etap in self.cr_res_data.generate_dict_etaps().items():
                    code = etap['Опер_код_подразделения']
                    if not CRES.SubdivisionsData.find_by_code(code,False):
                        success = False
                        errors.add_err(self, f'Не найден для {CFG.Config.place.Имя} код подразделения {code} для этапа {name_etap}')

            #===========Find nomen by name=====================
            if self.cr_res_data is not None and self.cr_res_data.schema.ОсновноеИзделиеКод == "":
                nomen_data = self.is_name_res_exists_in_nomen_erp()
                if nomen_data:
                    code = nomen_data['Код']
                    ref = nomen_data['ref']
                    if CQT.msgboxgYN(f'Номенклатура с наименованием \n"{self.name}"\n уже существует.\n'
                               f'Применить ее, не создавая новую?'):
                        self.cr_res_data.schema.ОсновноеИзделиеКод = code
                        self.cr_res_data.schema.ref_output_dse = ref
                        self.recalc_filled_bodyHat_erp_export()

                    else:
                        success = False
                        errors.add_err(self, f'Номенклатура с наименованием "{self.name}" уже существует.')


        return success, errors
    def update_gui_cr_res_data(self):
        self.update_attr_into_gui_obj('_cr_res_data')
    def new_body_res(self)->CrResBody:
        self._cr_res_data.body = CrResBody(self._cr_res_data)
        return self._cr_res_data.body

    def alias(self,attr:str):
        if attr in self.ALIASES:
            return  self.ALIASES[attr]
        return attr
    def update_attr_into_gui_obj(self,attr:str):
        if getattr(self, 'gui_obj', None):
            attr_al = self.alias(attr)
            if attr_al not in self.gui_obj.get_set_columns():
                return
            gui_obj = self.gui_obj.get_value_by_field(attr_al)
            if getattr(self, attr, self._UNSET) is self._UNSET:
                attr_val = None
            else:
                attr_val = str(getattr(self,attr))
            if attr_val != gui_obj:
                self.gui_obj.set_value_by_field(attr_al, attr_val)


    def update(self, name=None,value = _UNSET):
        if value is self.__class__._UNSET:
            value = getattr(self,name)
        if hasattr(self,'gui_obj') and self.gui_obj is not None:
            fl_upd_gui = True

            if name in self.__dict_attrs_properties:
                return
            if name in ('_filled_bodyHat_erp_export'):
                return
            name_oform, value_oform = self._oform_for_gui(name, value)
            if not DTCLS.view_hidden_fields:
                if name not in self.NOT_HIDDEN_FIELDS and name not in self.parent.HIDDEN_FIELDS:
                    fl_upd_gui = False

            if fl_upd_gui and name_oform in self.gui_obj.get_set_columns():
                self.gui_obj.set_value_by_field(name_oform, value_oform,) #

            if DTCLS.current_elem and self._cr_res_data is not None:
                self._cr_res_data.schema.set_value_by_field(name_oform, value_oform)
                self._cr_res_data._recalc_docRes_filled()
                #self._cr_res_data.schema.get_not_filled_attrs()


            if DTCLS.current_elem and self._cr_dse_data is not None:
                self._cr_dse_data.set_value_by_field(name_oform, value_oform)
                self._cr_dse_data._recalc_filled()
            self.update_doc_ready_state()
            self.update_attr_into_gui_obj('me')
            if name == 'type_doc':
                self.reload_cr_res_data()
            parent = self.get_parent()
            if parent:
                if parent._cr_res_data is not None:
                    parent._cr_res_data.body.calc_filled_body()
                    parent._cr_res_data.schema.calc_filled_ready()
                    parent._cr_dse_data._recalc_filled()


    def reload_cr_res_data(self):
        self._cr_res_data = None
        if self.type_doc == TypesDoc.res:
            self._cr_res_data: CrResData = CrResData(self)
            self._cr_dse_data: CrDseData = CrDseData(self)
        if self.type_doc == TypesDoc.dse:
            self._cr_dse_data: CrDseData = CrDseData(self)

    def is_requires_erp_creation(self):
        return not self._code.is_exists and self.type_doc != TypesDoc.none

    def is_root(self):
        return self.uid_parent is None

    def is_knot(self):
        if self.parent.count_childs(self.uid):
            return True
        return False

    def set_change(self):
        self.changed = True
        self._code.clear()
        self.ref = None

    def reacalc_is_not_change_docs(self,doc:None|TreeDoc=None)->bool:
        tree = self.parent
        if doc is None:
            doc = tree.get_root()
        chge = True
        if not self._code.is_exists or self.ref is None:
            chge = False

        for child in doc.get_childs():
            if not self.reacalc_is_not_change_docs(child):
                chge = False
        self.changed = chge
        return chge


    def set_parent_change(self,uid_item:str):
        obj  = self.parent.find_by_uid(uid_item)
        if obj.uid_parent is None:
            return
        par_obj = obj.get_parent()
        if not par_obj:
            return
        if par_obj._code is not None and par_obj._code != '':
            par_obj.set_change()

        self.set_parent_change(uid_item=par_obj.uid)

    def _reload_dse_body(self,ref, type_dse='', СтатьяКалькуляции_ref=None, СпособПолученияМатериала_ref=None) -> dict | None:

        if not DTCLS.use_cache_params:
            self._cr_dse_data.body.reset()

        if ref is  None:
            return
        text_dse = """      ВЫБРАТЬ
                                    Номенклатура.Наименование КАК Наименование,
                                    Номенклатура.Код КАК Код,
                                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ВидНоменклатуры.Ссылка)) КАК ref_parent,
                                    Номенклатура.Артикул КАК Артикул,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ТипНоменклатуры) КАК ТипНоменклатуры,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ГруппаДоступа) КАК ГруппаДоступа,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ВидНоменклатуры) КАК ВидНоменклатуры,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ВариантОформленияПродажи) КАК ВариантОформленияПродажи,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Родитель) КАК Группа,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ЕдиницаИзмерения) КАК ЕдиницаИзмерения,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ЕдиницаДляОтчетов) КАК ЕдиницаДляОтчетов,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.СтавкаНДС) КАК СтавкаНДС,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ГруппаАналитическогоУчета) КАК ГруппаАналитическогоУчета,
                                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ГруппаФинансовогоУчета) КАК ГруппаФинансовогоУчета
                                ИЗ
                                    Справочник.Номенклатура КАК Номенклатура
                                ГДЕ
                                    Номенклатура.Ссылка = &Ссылка
                                    """  #

        refs = APIERP.Refs_wet(text_dse)
        ref_obj = APIERP.Ref_wet('Ссылка', TypesDoc.dse.path_conf_1c,
                                 ref)

        refs.add_ref(ref_obj)
        key, res = APIERP.get_wet_request(text=text_dse, refs=refs)
        if key != 200:
            CQT.msgbox(f'Ошибка получения данных из ЕРП')
            return
        if not res['data']:
            CQT.msgbox(f'ДСЕ {type_dse} для {ref} не найдены')
            return
        data = res['data'][0]
        self._cr_dse_data.body.Артикул = data['Артикул']
        self._cr_dse_data.body.ТипНоменклатуры = data['ТипНоменклатуры']
        self._cr_dse_data.body.Группа = data['Группа']
        self._cr_dse_data.body.ВидНоменклатуры = data['ВидНоменклатуры']
        self._cr_dse_data.body.ВариантОформленияПродажи = data['ВариантОформленияПродажи']
        self._cr_dse_data.body.ГруппаДоступа = data['ГруппаДоступа']
        self._cr_dse_data.body.ЕдиницаИзмерения = data['ЕдиницаИзмерения']
        self._cr_dse_data.body.ЕдиницаДляОтчетов = data['ЕдиницаДляОтчетов']
        self._cr_dse_data.body.СтавкаНДС = data['СтавкаНДС']
        self._cr_dse_data.body.ГруппаАналитическогоУчета = data['ГруппаАналитическогоУчета']
        self._cr_dse_data.body.ГруппаФинансовогоУчета = data['ГруппаФинансовогоУчета']
        if СпособПолученияМатериала_ref:
            self._cr_dse_data.body.СпособПолучения = СпособПолученияМатериала_ref
        if СтатьяКалькуляции_ref:
            self._cr_dse_data.body.СтатьяКалькуляции = СтатьяКалькуляции_ref
        return data

    def reload_erp(self,recurse:bool=True,autocall:bool=False)->list[TreeDoc]|None: #00-063145
        print(f'reload_erp {self.name}')
        text = ''
        tch = None
        trdz = None
        new_rows = []
        etaps_erp = []
        DICT_ETAPS_BY_NAME = F.deploy_dict_c(DTCLS.LIST_ETAPS, 'name')

        data = None
        if self.type_doc == TypesDoc.dse:
            data = self._reload_dse_body(self.ref)
        elif self.type_doc == TypesDoc.res:

            res_obj = Erp_res(self)
            tch = res_obj.get_tch_mat()
            trdz = res_obj.get_tch_trdz()


            text = f"""
                    ВЫБРАТЬ
                        
                        ЭтапыПроизводства.Наименование КАК Наименование,
                        ЭтапыПроизводства.Подразделение.Код КАК ПодразделениеКод,
                        ЭтапыПроизводства.ДлительностьЭтапа КАК ДлительностьЭтапа,
                        ЭтапыПроизводства.ЕдиницаИзмеренияДлительностиЭтапа КАК ЕдиницаИзмеренияДлительностиЭтапа
                        
                    ИЗ
                        Справочник.ЭтапыПроизводства КАК ЭтапыПроизводства
                    ГДЕ
                        ЭтапыПроизводства.Владелец.Ссылка = &Ссылка
                    """
            refs = APIERP.Refs_wet(text)
            ref_obj = APIERP.Ref_wet('Ссылка', self.type_doc.path_conf_1c, self._ref)

            refs.add_ref(ref_obj)
            if (etaps_erp:= APIERP.get_wet_request_result(text=text, refs=refs,
                                                msg_err=f'{self.type_doc.user_name} не найдены этапы')) is None:
                return

            text = """     ВЫБРАТЬ
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Родитель.Ссылка)) КАК ref_parent,
                    РесурсныеСпецификации.ОсновноеИзделиеНоменклатура.Ссылка.Код КАК ОсновноеИзделиеКод,
                    РесурсныеСпецификации.Родитель.Код КАК РодительКод,
                    РесурсныеСпецификации.НачалоДействия КАК НачалоДействия,
                    РесурсныеСпецификации.КонецДействия КАК КонецДействия,
                    РесурсныеСпецификации.Описание КАК Описание,
                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.ОсновноеИзделиеНоменклатура.Ссылка) КАК ОсновноеИзделиеНоменклатура_ref,
                    РесурсныеСпецификации.Код КАК Код,
                    РесурсныеСпецификации.Наименование КАК Наименование
                ИЗ
                    Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                ГДЕ
                    РесурсныеСпецификации.Ссылка = &Ссылка
                              """

            refs = APIERP.Refs_wet(text)
            ref_obj = APIERP.Ref_wet('Ссылка', self.type_doc.path_conf_1c, self._ref)
            refs.add_ref(ref_obj)

            if (data:= APIERP.get_wet_request_result(text=text, refs=refs,
                            msg_err=f'{self.type_doc.user_name} для {self._ref} не найдены')) is None:
                return
            data = data[0]
        if data is None:
            return
        #------------main part--------------------------
        self.name = data['Наименование']
        self.code = Code(self, data['Код'], is_exists_doc= True)
        self._ref_struct_parent = data['ref_parent']
        self.changed = False

        if not autocall:
            self.set_parent_change(uid_item=self.uid)  # set_change

        if self.type_doc == TypesDoc.res:
            contains_stages = self.new_body_res()
            for etap_data in etaps_erp:
                if etap_data['Наименование'] in DICT_ETAPS_BY_NAME:
                    s_num_etap = DICT_ETAPS_BY_NAME[etap_data['Наименование']]['s_num']
                    contains_stages.set_podr(s_num_etap,etap_data['ПодразделениеКод'])
                    contains_stages.set_minutes(s_num_etap,etap_data['ДлительностьЭтапа'])
                else:
                    print(f" err {etap_data['Наименование']} not in DICT_ETAPS_BY_NAME")

            self._cr_res_data.schema.ref_output_dse = data['ОсновноеИзделиеНоменклатура_ref']
            self._cr_res_data.schema.ОсновноеИзделиеКод = data['ОсновноеИзделиеКод']


            self._cr_res_data.schema.ГруппаКод = data['РодительКод']
            self._cr_res_data.schema.НачалоДействияРесурсной = (
                F.dateStrToStr(data['НачалоДействия'],format_out="%d.%m.%Y",onerror=None))
            self._cr_res_data.schema.КонецДействияРесурсной = F.dateStrToStr(data['КонецДействия'],
                                                                             format_out="%d.%m.%Y",onerror=None)
            self._cr_res_data.schema.Описание = data['Описание']

            # -------DSE OUTPUT========
            if self._cr_res_data.schema.ref_output_dse:
                self._reload_dse_body(self._cr_res_data.schema.ref_output_dse, 'DSE OUTPUT')
            # ---------------------------------

            self.update_gui_cr_res_data()




            childs = self.parent.get_childs(self.uid) #  delete_children
            for child in childs:
                self.parent.delete_row(child.uid)
            tmp_indx = 0
            if tch :
                for row_tch in tch:
                    data_row_tch = self.parent.insert_row_after(self.uid,into=True) # update_gui

                    data_row_tch.type_doc =  TypesDoc.calc_type_by_tch(row_tch['СпособПолучения'])
                    data_row_tch.name = row_tch['Номенклатура']
                    data_row_tch.code = Code(data_row_tch, code=row_tch['Код'], is_exists_doc=True)
                    if row_tch['СпособПолученияМатериала_ref'] == DTCLS.Method_Obtain_Mat_Create_res.ref_key:
                        data_row_tch.ref =  row_tch['ref_res']
                        data_row_tch._cr_res_data.schema.ref_output_dse = row_tch['ref']
                    else:
                        data_row_tch.ref =  row_tch['ref']
                    data_row_tch.count = F.valm(row_tch['Количество'])
                    data_row_tch.changed = False

                    data_row_tch.level_index = tmp_indx
                    tmp_indx+=1
                    data_row_tch.ref_struct_parent =  row_tch['ref_parent']
                    data_row_tch.uid_parent =  self.uid


                    name_etap_mes = row_tch['ЭтапНаименование']
                    if name_etap_mes in DICT_ETAPS_BY_NAME:
                        code_etap_mes = DICT_ETAPS_BY_NAME[name_etap_mes]['s_num']
                        data_row_tch.belongs_to_etap = EtapTreeDoc(code_etap_mes, self)
                    else:
                        print(f'err {name_etap_mes} not in DICT_ETAPS_BY_NAME')
                    data_row_tch.update_doc_ready_state()
                    new_rows.append(data_row_tch)

                    data_row_tch._cr_dse_data.body.СтатьяКалькуляции = row_tch['СтатьяКалькуляции_ref']
                    data_row_tch._cr_dse_data.body.СпособПолучения = row_tch['СпособПолученияМатериала_ref']

                    if recurse:
                        data_row_tch.reload_erp(autocall=True)

            if trdz:
                for row_tch in trdz:
                    data_row_tch = self.parent.insert_row_after(self.uid, into=True)  # update_gui

                    data_row_tch.type_doc = TypesDoc.trd
                    data_row_tch.name = row_tch['ВидРабот']
                    data_row_tch.code = Code(data_row_tch, code=row_tch['Код'], is_exists_doc=True)

                    data_row_tch.ref = row_tch['ref']
                    data_row_tch.count = F.valm(row_tch['Количество'])
                    data_row_tch.changed = False

                    data_row_tch.level_index = tmp_indx
                    tmp_indx += 1
                    data_row_tch.uid_parent = self.uid


                    name_etap_mes = row_tch['ЭтапНаименование']
                    if name_etap_mes in DICT_ETAPS_BY_NAME:
                        code_etap_mes = DICT_ETAPS_BY_NAME[name_etap_mes]['s_num']
                        data_row_tch.belongs_to_etap = EtapTreeDoc(code_etap_mes, self)
                    else:
                        print(f'err {name_etap_mes} not in DICT_ETAPS_BY_NAME')
                        self.set_change()
                    data_row_tch.update_doc_ready_state()

                    new_rows.append(data_row_tch)

        self.parent.update_levels()
        return new_rows

    def _oform_for_gui(self,name,val):
        if name == 'changed':
            val = self.changed
        name = self.alias(name)
        if val is None:
            val = ''
        if (isinstance(val, int) or isinstance(val, float)) and not isinstance(val, bool):
            pass
        elif isinstance(val, bool):
            val = 'Да' if val else 'Нет'
        else:
            val = str(val)
        return name,val

    def get_dict(self):
        res = dict()
        iter=0
        for attr, attr_v in F.get_all_attrs_with_properties(self,prefer_properties=True).items():
            k, v = self._oform_for_gui(attr, attr_v)
            if not DTCLS.view_hidden_fields:
                if attr not in self.NOT_HIDDEN_FIELDS and attr not in self.parent.HIDDEN_FIELDS:
                    continue
            res[k] = v
            iter+=1
        return res

    def get_vert_dict(self):
        res = []
        for name,v in F.get_all_attrs_with_properties(self,prefer_properties=True).items():
            izm = CEMOJ.EmojiMain.ОборудованиеИнструменты.lock.symbol
            if name in self.EDITABLE_VIEW_ATTRS:
                izm = CEMOJ.EmojiMain.Документы.pencil_note.symbol
                try:
                    if v is not None and not isinstance(v, (str, int, float, bool)):
                        v = v.val_for_edit()
                except:
                    print(f'editable_view_attr {name} not have val_for_edit')
            k, v = self._oform_for_gui(name, v)
            if not DTCLS.view_hidden_fields:
                if name not in self.NOT_HIDDEN_FIELDS and name not in self.parent.HIDDEN_FIELDS:
                    continue
            res.append({'name':name,'Параметр':k,'Изм.':izm,'Значение':str(v)})
        return res

    def clear(self):
        self.type_doc = TypesDoc.none
        self.name = None
        self.code = Code(self, is_exists_doc=False)
        self.count = 1 if self.is_root() else 0
        self.ref = None
        self.changed: bool = False
        self.ref_struct_parent = None
        gui_obj:CTREE.ExtTreeWidgetItem =  self.gui_obj
        if self._cr_dse_data:
            self._cr_dse_data.clear()
        if self._cr_res_data:
            self._cr_res_data.clear()
        for k,v in self.get_dict().items():
            if k == 'uid':
                continue
            gui_obj.set_value_by_field(k,v)

    def setCurrentElem(self,data_cls:type[dataClass.data_app]):
        data_cls.current_elem = self
        num = 'не выбран'
        if data_cls.current_elem:
            num = str(data_cls.current_elem)
        data_cls.app_self.ui.lbl_current_elem.setText(f'Текущий элемент: {num}')


    def __str__(self):
        return f'{self.uid[:3]+ "-" +self.uid[-3:]} {self.type_doc} {self.changed}{self.name}({self._code})-{self.count} шт.'
    def gui_str(self):
        return f'{self.type_doc} {self.changed}{self.name}({self._code})-{self.count} шт.'

class TreeDataManager:
    """
    менеджер сохранения/загрузки данных
    """
    def __init__(self,tree:TreeRes):
        self.tree:TreeRes = tree
        self.tmp_path = F.sep().join([CMS.tmp_dir(), 'tmp_save'])
        self.tree_new:TreeRes|None = None


    def _copy_res(self) -> TreeRes:
        copy_tree = self.tree.__class__(None, None)
        dict_rows = dict()
        for k, v in self.tree.tree_rows.items():
            dict_rows[k] = self._copy_doc(v)
        copy_tree.tree_rows = dict_rows
        return copy_tree


    def _copy_doc(self,v:TreeDoc)->TreeDoc:
        copy_tree: TreeRes = v.parent
        debug = False
        if debug:
            path = F.path_to_execut_file_c(False)
            file_name = f'test_pickle'
            puthf = F.sep().join([path, file_name])

        obj = v.__class__(copy_tree,v.type_doc,None,v.name,v._code.code,v._ref,v.count,
                             v._level_index,v._ref_struct_parent,v._uid_parent)
        for name, attr in v.__dict__.items():
            if name in('parent', '_gui_obj'):
                continue
            if isinstance(attr, (CTREE.ExtTreeWidgetItem, CTREE.ExtTreeWidget)):
                print(name)
            if name == '_code':
                attr = Code(obj,v._code.code,v._code.is_exists)
            if name in ( '_me'):
                attr = obj
            if name in ( '_level_index','level_gui'):
                pass
            if name in ( '_cr_res_data','_belongs_to_etap','_cr_dse_data'):
                if attr is not None:
                    attr.parent = obj

            obj.__setattr__(name,attr)
            if debug:
                try:
                    F.save_file_pickle(puthf,obj)
                except:
                    print(name)
        obj._old_uid = v.uid
        return obj

    @CQT.onerror
    def save_tree(self, puthf: str=None, *args):
        current_tree = self.tree
        save_needs = dict()
        selected_uid = current_tree.current_row().uid
        dict_expand = current_tree.tree_gui.get_dict_uid_is_expand()
        tree_tmp = self._copy_res()
        for k, v in tree_tmp.tree_rows.items():
            uuid = k
            save_needs[uuid] = {'gui_index': None,
                                'is_expand': dict_expand[v._old_uid],
                                'current_row': uuid == selected_uid}

        data = {'ver': 1, 'tree': tree_tmp, 'needs': save_needs}
        if puthf is None:
            puthf = self.tmp_path
        F.save_file_pickle(puthf, data)
        print('save file success')

    #------------lite-------------------------------------

    @CQT.onerror
    def generate_tree_lite(self, *args)->dict:
        current_tree = self.tree
        save_needs = dict()
        selected_uid = current_tree.current_row().uid
        dict_expand = current_tree.tree_gui.get_dict_uid_is_expand()

        tree_tmp = current_tree._export()
        for k, v in tree_tmp.items():
            uuid = k
            save_needs[uuid] = {'gui_index': None,
                                'is_expand': dict_expand[v['_old_uid']],
                                'current_row': uuid == selected_uid}

        data = {'ver': 2, 'tree': tree_tmp, 'needs': save_needs}
        return data
    @CQT.onerror
    def save_tree_lite(self, puthf: str=None, *args):
        data = self.generate_tree_lite()
        if puthf is None:
            puthf = self.tmp_path
        F.save_file_pickle(puthf, data)
        print(f'save lite file success puthf:{puthf}')
        return

    def _toggle_tree_gui(self, off=True):
        # Отключаем графику и сигналы
        tree: QtWidgets.QTreeWidget|CTREE.ExtTreeWidget = DTCLS.treeNavigator
        if off:
            tree.setUpdatesEnabled(False)  # отключаем перерисовку
            tree.blockSignals(True)  # блокируем сигналы

        else:
            tree.blockSignals(False)
            tree.setUpdatesEnabled(True)  # включаем перерисовку обратно
            tree.repaint()  # принудительно перерисовать



    def _make_tree_from_dict(self,data_dict:dict)->TreeRes|None:
        copy_tree = TreeRes(None, None)
        dict_rows = dict()
        for k, v in data_dict.items():
            doc = TreeDoc._import(v,copy_tree)
            #doc = self._make_doc_from_dict(copy_tree,v,check_code=False)
            if doc is None:
                return
            dict_rows[k] = doc
        copy_tree.tree_rows = dict_rows
        return copy_tree

    def _parse_tree_from_data(self,data)-> TreeRes|None:
        if data['ver'] == 1:
            tree: TreeRes = data['tree']
        elif data['ver'] == 2:
            tree: TreeRes = self._make_tree_from_dict(data['tree'])  #------------lite-------------------------------------
        else:
           return None
        return tree

    def _gen_objs(self,tree:TreeRes, save_needs:dict):
        for uid, row in tree.tree_rows.items():
            if uid in save_needs:
                if save_needs[uid]['is_expand']:
                    row.gui_obj.expand_children(scroll_to_item=False, select=False)
                if save_needs[uid]['current_row']:
                    row.set_select_gui()

    def load_tree(self,puthf:str=None):
        if puthf is None:
            puthf = self.tmp_path
        data = F.load_file_pickle(puthf)
        print('load_data')
        self.tree_new = self._parse_tree_from_data(data)
        if self.tree_new is None:
            self._toggle_tree_gui(False)
            return



        if DTCLS.current_process is not None:
            DTCLS.current_process.tree_res.clear()

        DTCLS.current_process.tree_res = self.tree_new
        self.tree_new.tree_gui = DTCLS.treeNavigator
        #self._toggle_tree_gui()
        print('fill_gui')
        self.tree_new.fill_gui()
        self.tree_new.united_gui()
        print('_gen_objs')

        self._gen_objs( self.tree_new,data['needs'])

        #self._toggle_tree_gui(False)

class TreeRes():
    HIDDEN_FIELDS = {'level_gui','uid','level_index','uid_parent'}
    def __init__(self,tree_gui:CTREE.ExtTreeWidget|None ,tree_data:dict[str,TreeDoc]|None=None):
        self.tree_gui:CTREE.ExtTreeWidget|None = tree_gui
        self.tree_rows:dict[str,TreeDoc]|None =tree_data
        if self.tree_gui is not None:
            self._new_rows()
        if self.tree_rows is not  None:
            self.get_root().set_select_gui()
    def __str__(self):
        result = ''
        root = self.get_root()
        result = f'{root.name} {str(root.code)}'
        return result
    def _export(self) -> dict:
        dict_rows = dict()
        for k, v in self.tree_rows.items():
            dict_rows[k] = v._export()
        return dict_rows

    def reset(self):
        self.__init__(self.tree_gui)
    def clearCurrentElem(self,data_cls:type[dataClass.data_app]):
        data_cls.current_elem = None
        num = 'не выбран'
        data_cls.app_self.ui.lbl_current_elem.setText(f'Текущий элемент: {num}')

    def sorted_docs_by_level(self)->list[TreeDoc]:
        sorted_docs = list(sorted(self.tree_rows.values(), key=lambda d: d.nesting_level,reverse=True))
        return sorted_docs

    def save(self,dialog=True):
        path = None
        if dialog:
            pass
        DTCLS.tree_data_manager.save_tree_lite(path)


    def load(self,dialog=True):
        path = None
        if dialog:
            pass
        DTCLS.tree_data_manager.load_tree(path)

    def delete_item(self,uid:str)->bool:
        result = True
        childs = self.get_childs(uid)
        for chld in childs:
            if not self.delete_item(chld.uid):
                result = False
        if not self.tree_rows.pop(uid,False):
            result = False
        return result



    def get_root(self)->TreeDoc:
        for doc in self.tree_rows.values():
            if doc.is_root():
                return doc
        raise AttributeError(f'{self.__class__.__name__}: root is not existence')

    def on_drDr(self,new_parent:CTREE.ExtTreeWidgetItem, DroppedTreeItemType:CTREE.ExtTreeWidgetItem):
        """DragDrop event"""

        current_row = DTCLS.current_process.tree_res.find_by_uid(DroppedTreeItemType.uuid)
        old_parent_uid = current_row.uid_parent
        old_parent_row = current_row.parent.find_by_uid(old_parent_uid)
        current_row.gui_obj = DroppedTreeItemType
        new_parent_row:TreeDoc|None = None
        if new_parent:
            new_parent_uid  = new_parent.uuid
            new_parent_row = new_parent.temp_data
            if new_parent_row.type_doc != TypesDoc.res:
                new_parent_row.type_doc = TypesDoc.res
        else:
            new_parent_uid  = None
        current_row.uid_parent = new_parent_uid
        current_row.gui_obj.temp_data = current_row
        DTCLS.current_process.tree_res.update_levels()
        #current_row.level_index = ParentTreeItemType.indexOfChild(DroppedTreeItemType)
        if old_parent_uid != new_parent_uid:
            current_row.set_parent_change(current_row.uid)
            if new_parent_row:
                new_parent_row.type_doc = TypesDoc.res
                new_parent_row.recalc_filled_bodyHat()
            old_parent_row.recalc_filled_bodyHat()

    def update_levels(self):
        for doc in self.tree_rows.values():
            parent = doc.gui_obj.parent()
            if parent is None:
                doc.level_index = 0
            else:
                doc.level_index = doc.gui_obj.parent().indexOfChild(doc.gui_obj)
            doc.level_gui = doc.gui_obj.level

    def clear(self):
        self.tree_rows = dict()
        self.tree_gui.clear_table()
        DTCLS.tree_data_manager = None


    def count(self):
        return len(self.tree_rows)

    def _sort_by_parent_and_index(self,data) -> list[dict]:
        items: list[dict] = data
        """Сортирует элементы по uid_parent и level_index внутри каждой группы"""

        # Создаем словарь детей для каждого родителя
        children_by_parent = {}
        for item in items:
            parent_uid = item.get('uid_parent', '')
            if parent_uid not in children_by_parent:
                children_by_parent[parent_uid] = []
            children_by_parent[parent_uid].append(item)

        # Сортируем детей каждого родителя по level_index
        for parent_uid in children_by_parent:
            children_by_parent[parent_uid].sort(key=lambda x: x.get('level_index', 0))

        # Рекурсивная функция для обхода дерева
        def get_sorted_tree(parent_uid=''):
            result = []
            if parent_uid in children_by_parent:
                for child in children_by_parent[parent_uid]:
                    result.append(child)
                    # Рекурсивно добавляем детей этого ребенка
                    result.extend(get_sorted_tree(child['uid']))
            return result

        return get_sorted_tree()
    def united_gui(self):
        nick_name_uuid = 'uid'
        for gui_obj in self.tree_gui.iter_rows():  # tree.tree_gui.dump_as_table(rez_dict=True)
            for uid, row in self.tree_rows.items():
                if row.uid == gui_obj.to_dict(nick_name_uuid=nick_name_uuid)[nick_name_uuid]:
                    row.gui_obj = gui_obj
                    gui_obj.temp_data = row
                    break


    def fill_gui(self):
        sorted_data = self.dict_data()
        self.tree_gui.fill_table(
            sorted_data,
            min_row_height=26,
            hide_horizontal_header=False,
            min_col_width=80,
            stretch_last_column=True,
            nick_name_level='level_gui',
            nick_name_uuid='uid',
            odd_item_color='#ffffff',
            even_item_color='#f0f8ff',
            hover_indicator_color=(233, 233, 111),
            # branch_icon_if_can_close='./Mkarti/icons/1.ico',
            selected_item_color='#bfbfbf',
            hover_item_color="#d8dee3",
            on_drop_access=self.on_drDr,
            one_root=True,
            on_header_resized = CQT.on_section_resized_tree

            )
        CMS.load_column_widths(self, self.tree_gui)
        CQT.FillHorizontalHeaderSort(self.tree_gui)
        for field in self.HIDDEN_FIELDS:
            num = CQT.num_col_by_name_c(self.tree_gui,field)
            if num:
                if not DTCLS.view_hidden_fields:
                    self.tree_gui.setColumnHidden(num,True)
                else:
                    self.tree_gui.setColumnHidden(num, False)

        DTCLS.tree_data_manager = TreeDataManager(self)

    def current_row(self)->TreeDoc:
        current_row:CTREE.ExtTreeWidgetItem|None = self.tree_gui.currentItem()
        if current_row:
            return current_row.temp_data

    def find_by_uid(self,uid:str)->TreeDoc:
        if uid not in self.tree_rows:
            raise ValueError (f'find_by_uid uid {uid} not found')
        return self.tree_rows[uid]

    def find_by_ref(self,ref:str)->list[TreeDoc]:
        result = []
        for item in self.tree_rows.values():
            if item.ref == ref:
                result.append(item)
        return result

    def dict_data(self)->list[dict]:
        data = [self.dict_from_doc(_) for _ in self.tree_rows.values()]
        return  self._sort_by_parent_and_index(data)

    def _new_rows(self, type_doc:TypeDoc=TypesDoc.none, level_index:int=0):
        doc = self._new_row(None, type_doc,  uid_parent=None)
        uid = doc.uid
        self.tree_rows = {uid: doc}
        self.fill_gui()
        for gui_obj in self.tree_gui.iter_rows():
            doc.gui_obj = gui_obj
            gui_obj.temp_data = doc
            break
        return

    def _new_row(self,
                 gui_obj: CTREE.ExtTreeWidgetItem|None,
                 type_doc: TypeDoc = TypesDoc.none,
                 name: str = '',
                 code: str=None,
                 ref: str = None,
                 count: float|None = 0,
                 level_index:int=0,
                 ref_struct_parent: str|None = None,
                 uid_parent: str = None):
        if not F.is_numeric(count) and count is not  None:
            raise TypeError(f'not F.is_numeric(count)')
        if isinstance(count,str):
            count = F.valm(count)
        return TreeDoc(self, type_doc, gui_obj,  name=name,code=code, ref = ref, count=count,ref_struct_parent=ref_struct_parent,
                       uid_parent=uid_parent, level_index=level_index)

    def delete_row(self, uid: str):
        row = self.find_by_uid(uid)

        if not row:
            return
        if self.delete_item(uid):
            self.tree_gui.remove_row(row.gui_obj.current_index)
            return True
        else:
            #TODO дописать восстановление таблицы и дерева из за ошибки()
            return False
    def insert_row_after(self, uid:str,
                         type_doc: TypeDoc = TypesDoc.none,
                         name: str = '',
                         code: str = None,
                         ref: str = None,
                         count: float | None = 0,
                         ref_struct_parent: str | None = None,
                         level_index: int|None=None,into=False)-> TreeDoc:

        if uid not in self.tree_rows:
            raise ValueError(f'insert_row uid {uid} not found')
        row_after: TreeDoc = self.tree_rows[uid]
        if row_after.uid_parent is None:
            into = True

        if into:
            last_child = self.get_last_child(uid)
            if last_child:
                row_after: TreeDoc = last_child
                uid_parent = row_after.uid_parent
                gui_index = row_after.gui_obj.current_index
                into = False
            else:
                row_after: TreeDoc = self.tree_rows[uid]
                uid_parent = uid
                gui_index = row_after.gui_obj.current_index

        else:
            row_after: TreeDoc = self.tree_rows[uid]
            uid_parent = row_after.uid_parent
            gui_index = row_after.gui_obj.current_index

        if level_index is None:
            if not self.count_childs(uid_parent):
                level_index = 0
            else:
                level_index = gui_index
                for chld in self.get_childs(uid_parent):
                    if chld.level_index >= level_index:
                        chld.level_index += 1

        else:
            brothers = self.get_childs(uid_parent)
            for bro in brothers:
                if bro.level_index >= level_index:
                    bro.level_index += 1
        if not F.is_numeric(count) and count is not  None:
            raise TypeError(f'not F.is_numeric(count)')
        if isinstance(count,str):
            count = F.valm(count)
        new_row = self._new_row(None, type_doc, name=name,code=code,ref=ref,count=count,level_index=level_index,
                                ref_struct_parent=ref_struct_parent,uid_parent=uid_parent)


        gui_obj:CTREE.ExtTreeWidgetItem = self.tree_gui.insert_after(gui_index,
                                                                    new_row.get_dict(),into=into)[0]
        new_row.gui_obj = gui_obj
        gui_obj.temp_data = new_row
        self.tree_rows[new_row.uid] = new_row
        new_row.parent = self
        return new_row

    def dict_from_doc(self,doc:TreeDoc):
        return doc.get_dict()

    def get_childs(self,uid:str)->set[TreeDoc]:
        tree_rows:dict[str,TreeDoc] = self.tree_rows
        if tree_rows is None:
            return set()
        return set([_ for _ in tree_rows.values() if _.uid_parent == uid])

    def count_childs(self, uid: str) -> int:
        tree_rows: dict[str, TreeDoc] = self.tree_rows
        return sum(1 for _ in tree_rows.values() if _.uid_parent == uid)
    def get_last_child(self,uid:str)->TreeDoc|None:
        broths: set[TreeDoc] = self.get_childs(uid)
        max_lvl = -1
        max_bro = None
        for bro in broths:
            if bro.level_index > max_lvl:
                max_lvl = bro.level_index
                max_bro = bro
        return max_bro

    def get_first_child(self, uid: str) -> TreeDoc | None:
        broths: set[TreeDoc] = self.get_childs(uid)
        min_lvl = float('inf')
        min_bro = None
        for bro in broths:
            if bro.level_index < min_lvl:
                min_lvl = bro.level_index
                min_bro = bro
        return min_bro


class CrResBody(Base_cls):
    _UNSERIALIZABLE_ATTRS = {'parent','_lock_recalc'}
    def __init__(self,parent:CrResData):
        self.parent:CrResData = parent
        self.params_etaps_cache = [EtapTreeDoc(_,None) for _ in DTCLS.DICT_ETAPS.keys()]
        try:
            self.parent.schema.body = self
        except:
            pass
        self.calc_filled_body()

    @classmethod
    def _import(cls, data, parent=None):
        """
        Специфичный импорт для CrResBody
        """
        obj = cls.__new__(cls)
        obj._lock_recalc = True
        obj.parent = parent

        # Восстанавливаем params_etaps_cache
        if 'params_etaps_cache' in data and data['params_etaps_cache'] is not None:
            obj.params_etaps_cache = cls._restore_params_etaps_cache(data['params_etaps_cache'], obj)
        else:
            # Создаем по умолчанию если нет в данных
            obj.params_etaps_cache = [EtapTreeDoc(_, None) for _ in DTCLS.DICT_ETAPS.keys()]

        # Восстанавливаем другие атрибуты
        for name, value in data.items():
            if name == 'params_etaps_cache':
                continue  # Уже обработали
            if hasattr(obj, name):
                setattr(obj, name, value)

        obj._lock_recalc = False
        return obj

    @classmethod
    def _restore_params_etaps_cache(cls, data, parent_obj):
        """
        Восстанавливает params_etaps_cache из данных экспорта
        """
        restored_etaps = []

        for etap_data in data:
            if isinstance(etap_data, dict):
                # Создаем EtapTreeDoc из данных
                code_mes = etap_data.get('code_mes')
                if code_mes is not None:
                    # Создаем объект EtapTreeDoc
                    etap_obj = EtapTreeDoc(code_mes, parent_obj.parent.parent)  # parent_obj.parent.parent = TreeDoc

                    # Восстанавливаем остальные атрибуты
                    etap_obj.code_podrazd = etap_data.get('code_podrazd')
                    etap_obj.minutes = etap_data.get('minutes')
                    etap_obj.name = etap_data.get('name')

                    # Восстанавливаем _mes_row если есть
                    if '_mes_row' in etap_data:
                        etap_obj._mes_row = etap_data['_mes_row']

                    restored_etaps.append(etap_obj)
            else:
                # Если данные в старом формате (просто code_mes)
                restored_etaps.append(EtapTreeDoc(etap_data, parent_obj.parent.parent))

        return restored_etaps

    def gen_params_for_save(self):
        rez = []
        for etap in self.params_etaps_cache:
            rez.append({
                '_mes_row':etap._mes_row,
                'code_mes':etap.code_mes,
                'name':etap.name,
                'code_podrazd':etap.code_podrazd,
                'minutes':etap.minutes,
                        })
        return rez


    @staticmethod
    def fit_name_to_length(name:str,len_name:int)->str:
        middlefix= '...'

        if len(name) > len_name:
            len_name = len_name - len(middlefix)
            left_len = len_name//2
            rigt_len = len_name - left_len
            name = f'{name[:left_len]}{middlefix}{name[-rigt_len:]}'
            return name
        return name
    def __str__(self):
        return '|'.join([ f'{self.fit_name_to_length(_.name,11)} {_.code_podrazd} {_.minutes}'
                          for _ in self.params_etaps_cache if _.code_podrazd is not None])
    def set_podr(self,s_num:int,code:str):
        if not isinstance(s_num,int):
            raise TypeError(f'set_podr err type s_num')
        etap = self._get_from_cache(s_num)
        if etap is None:
            return
        etap.code_podrazd = code
        self.calc_filled_body()

    def set_minutes(self ,s_num:int,minutes:int|float):
        if not isinstance(s_num,int):
            raise TypeError(f'set_minutes err type s_num')
        etap = self._get_from_cache(s_num)
        if etap is None:
            return
        etap.minutes = minutes
        self.calc_filled_body()
    def calc_list_etaps(self):
        doc = self.parent.parent
        childs = doc.parent.get_childs(doc.uid)
        set_cods = set()
        filtred_etaps = []
        for child in childs:

            if child.belongs_to_etap is None:
                continue
            set_cods.add(child.belongs_to_etap.code_mes)

        for etap in self.params_etaps_cache:
            if etap.code_mes in set_cods:
                filtred_etaps.append(etap)
        sorted_list = sorted(list(filtred_etaps), key=lambda x: x.code_mes)
        return sorted_list


    def _get_from_cache(self,s_num):
        for etap in self.params_etaps_cache:
            if etap.code_mes == s_num:
                return etap


    def fill_table(self,tbl:CQT.QTableWidget):
        def fnc_oform_tbl(tbl:CQT.QTableWidget,parent_self:mywindow):
            pass
        @CQT.onerror
        def fnc_select_podr(lblself: CQT.InteractiveLabelInstance, self: mywindow, row, col,data:tuple[CrResData,int] , *args):
            list_podr = DTCLS.LIST_PODRAZD
            cr_res_data, code_etap = data
            result = None
            if list_podr:
                result = CQT.msgboxg_get_table(self, f'Выбор подразделения', list_podr, "Выбор",
                                               styleSheet=CQT.ERP_CSS, ExtendedSelection=False,
                                               selectRows=True, selection_from_tbl=True, func_oform_tbl=fnc_oform_tbl,
                                               parent_self=DTCLS.app_self)

            if result:
                with CQT.table_updating(tbl):
                    code_podr = result['Код']
                    tbl.item(row, col).setText(code_podr)
                    lblself.set_text(code_podr)
                cr_res_data.body.set_podr(code_etap,code_podr)
            pass
        

        with CQT.table_updating(tbl):
            data_for_tbl = [_.get_dict() for _ in self.calc_list_etaps()]
            CQT.fill_wtabl(data_for_tbl, tbl, selectionMode='SingleSelection', styleSheet=CQT.ERP_CSS,
                           set_editeble_col_nomera={'Минут'})

            CQT.load_column_widths(DTCLS.app_self, tbl, CMS.tmp_dir())
            nf_podr = CQT.num_col_by_name_c(tbl,'Подразделение код')
            nf_code_etap = CQT.num_col_by_name_c(tbl,'Код')
            for i in range(tbl.rowCount()):
                code_etap = int(tbl.item(i, nf_code_etap).text())
                widg = CQT.add_interactive_label(tbl, i, nf_podr, tbl.item(i, nf_podr).text(),
                                                 parent_self=DTCLS.app_self)
                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбор',
                                fnc_select_podr,
                                cell_val = (self.parent, code_etap), img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                     'icons', 'btn_select']))


    def calc_filled_body(self):
        self.parent.body_filled = self._check_filled_body()
    def _check_filled_body(self):
        etaps = self.calc_list_etaps()
        if not etaps:
            return False
        for etap in etaps:
            if etap.code_podrazd is None:
                return False
            if etap.minutes is None:
                return False
        return True

    def calc_dict_etaps(self)->dict[str,dict[str,any]]:
        result_dict = dict()
        for etap in self.calc_list_etaps():
            mats = dict()
            trdz = dict()
            for chld in self.parent.parent.get_childs():
                if chld.belongs_to_etap.name == etap.name:
                    Способы_получения_материала = 'Обеспечивать'
                    Способы_получения_материала = 'Покупной'
                    Материалы_Статья_калькуляции = 'Сырье'
                    Материалы_Статья_калькуляции = 'Вспомогательные материалы'
                    Материалы_Статья_калькуляции = 'Возвратные отходы'
                    if chld.type_doc == TypesDoc.dse:
                        Материалы_Статья_калькуляции = None
                        Способы_получения_материала = None
                        if chld.cr_dse_data.body.СтатьяКалькуляции:
                            Материалы_Статья_калькуляции = chld.cr_dse_data.body.СтатьяКалькуляции.ref_key
                        if chld.cr_dse_data.body.СпособПолучения:
                            Способы_получения_материала = chld.cr_dse_data.body.СпособПолучения.ref_key
                        if Материалы_Статья_калькуляции is None:
                            raise ValueError(f'Материалы_Статья_калькуляции не указано')
                        if Способы_получения_материала is None:
                            raise ValueError(f'Способы_получения_материала не указано')
                        #if pki == '1':
                        #    Способы_получения_материала = "Покупной"
                        if (chld.ref in mats
                                and mats[chld.ref]["Материалы_Статья_калькуляции"] == Материалы_Статья_калькуляции
                                and mats[chld.ref]["Способы_получения_материала"] == Способы_получения_материала
                                    ):
                            mats[chld.ref]["Мат_норма"] += chld.count
                        else:
                            mats[chld.ref] = {
                                "Мат_код": chld.code.code,
                                "Мат_наименование": chld.name,
                                'ЕдиницаИзмерения': chld.cr_dse_data.body.ЕдиницаИзмерения.ref_key,
                                "Мат_норма": chld.count,
                                "Материалы_Статья_калькуляции": Материалы_Статья_калькуляции,
                                "Способы_получения_материала": Способы_получения_материала,
                                                    }

                    if chld.type_doc == TypesDoc.res:
                        mats[chld.ref] = {
                            "Мат_код": chld.cr_res_data.schema.ОсновноеИзделиеКод,
                            "Мат_наименование": chld.name,
                            'ЕдиницаИзмерения': '0fb9aa6f-e02d-11ed-847d-00d861dd2b4a',#{'code': '796 ', 'fullname': 'шт', 'name': 'Штука', 'ref_key': '0fb9aa6f-e02d-11ed-847d-00d861dd2b4a'}
                            'КодИсточник': chld.code.code,
                            "Мат_норма": chld.count,
                            "Материалы_Статья_калькуляции": "Полуфабрикаты производимые в процессе",
                            "Способы_получения_материала": "Произвести по спецификации",
                        }
                    if chld.type_doc == TypesDoc.trd:
                        if chld.ref not in trdz:
                            trdz[chld.ref] = 0
                        trdz[chld.ref] += chld.count
            result_dict[etap.name]= {"Опер_код_подразделения":etap.code_podrazd,
                                     "ДлительностьМинут":etap.minutes,
                                     "Материалы":mats,
                                     "Трудозатраты":trdz
                                     }
        return result_dict

class CrResParams(Base_cls):
    connector = {'Наименование':'НаименованиеРесурсной',
                 'КолВо':'count'}
    schema = {
        "ОсновноеИзделиеКод": {"type": "tbl", "descr": "Основное изделие код"},
        "ГруппаКод": {"type": "tbl", "descr": "Группа код"},
        "НаименованиеРесурсной": {"type": "str", "descr": "Наименование РС"},
        "НачалоДействияРесурсной": {"type": "date", "descr": "Начало действия РС"},
        "КонецДействияРесурсной": {"type": "date", "descr": "Конец действия РС"},
        "Описание": {"type": "text", "descr": "Описание"},
    }
    NOT_NECCESARY_FILL = {'Описание','_is_exists_all_attrs','ref_output_dse','ОсновноеИзделиеКод'}
    CACHED_ATTRIBUTES = {'ОсновноеИзделиеКод','ГруппаКод'}
    FORMAT_DATE = "%d.%m.%Y"
    _UNSERIALIZABLE_ATTRS = {'parent','schema','_lock_recalc'}
    def __init__(self,parent:CrResData):
        self._is_exists_all_attrs = False
        self.parent:CrResData = parent
        self.ref_output_dse: None | str = None
        self.ОсновноеИзделиеКод: str | None = None
        self.ГруппаКод: str|None = None
        self.НаименованиеРесурсной: str|None = None
        self.НачалоДействияРесурсной: str|None = F.now(self.FORMAT_DATE)
        self.КонецДействияРесурсной: str|None = F.dateStrToStr(
                F.add_days(F.strtodate(self.НачалоДействияРесурсной,self.FORMAT_DATE),F.timedelta(14))
                ,format_out=self.FORMAT_DATE)
        self.Описание: str|None = None
        self.count: int|float|None = None

        self._is_exists_all_attrs = True
        self.get_vals_from_parent()

        if DTCLS.use_cache_params:
            for k in self.__dict__.keys():
                if not k.startswith('_'):
                    cached_val = self._load_cache_attr(k)
                    if cached_val is not None:
                        setattr(self, k, cached_val)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if self._lock_recalc:
            return
        if getattr(self,'_is_exists_all_attrs',None):
            self.calc_filled_ready()
        if key == 'ОсновноеИзделиеКод':
            self.reload_params_ОсновноеИзделиеКод()


    def gen_params_for_save(self)->dict:
        EXPORT_FIELDS = {
        'ref_output_dse',
        'ОсновноеИзделиеКод',
        'ГруппаКод',
        'НаименованиеРесурсной',
        'НачалоДействияРесурсной',
        'КонецДействияРесурсной',
        'Описание',
        'count',
        }
        res = {}
        for k, v in F.get_all_attrs_with_properties(self).items():
            if k in EXPORT_FIELDS:
                res[k]=v
        return res
    def reload_params_ОсновноеИзделиеКод(self):
        code = self.ОсновноеИзделиеКод
        doc = self.parent.parent

        if doc._cr_res_data is None:
            return
        doc._reload_dse_body(doc._cr_res_data.schema.ref_output_dse,
                                            'DSE OUTPUT')
        doc.code = doc.code
        doc._cr_dse_data.fill_tables()

    def get_vals_from_parent(self):
        for field,val in  F.get_all_attrs_with_properties(self.parent.parent).items():
            field = self.parent.parent.alias(field)
            if field in self.connector:
                field = self.connector[field]
            if field in self.__dict__:
                setattr(self, field, val)
        self.calc_filled_ready()

    def set_value_by_field(self, field: str, new_value, refill_tbl = True):
        if field in self.connector:
            field = self.connector[field]
        if field in self.__dict__:
            setattr(self,field,new_value)
            self._cache_attr(field,new_value)
            self.calc_filled_ready()
            if refill_tbl:
                self._fill_table_from_schema(DTCLS.app_self.ui.tbl_cr_res)
    def _name_for_cache(self,attr:str):
        return f'cache_CrResParams_' + attr
    def _cache_attr(self,attr:str,val):
        if attr in self.CACHED_ATTRIBUTES and val is not None:
            CMS.save_tmp_stukt(val,self._name_for_cache(attr))
    def _load_cache_attr(self,attr:str):
        if attr in self.CACHED_ATTRIBUTES:
            return CMS.load_tmp_stukt(self._name_for_cache(attr),None)
    def save_attr_cache(self,attr:str):
        if attr not in self.CACHED_ATTRIBUTES:
            return
        val = getattr(self,attr)
        self._cache_attr(attr,val)

    def calc_filled_ready(self):
        self.parent.hat_filled = self._check_filled_hat()

    def get_not_filled_attrs(self)->list[str]:
        res = list()
        for k, v in self.__dict__.items():
            if k in self._UNSERIALIZABLE_ATTRS:
                continue
            if k not in self.NOT_NECCESARY_FILL:
                if v is None or v in ('',0,0.0):
                    res.append(k)
        return res

    def _check_filled_hat(self):
        if self.get_not_filled_attrs():
            return False
        return True
    def get_list(self):
        return  {k:v for k,v in self.__dict__.items() if not k.startswith('_')}

    def _fill_table_from_schema(self,tbl:CQT.QTableWidget):
        values_attr: dict | None = self.get_list()
        @CQT.onerror
        def fnc_clear_code(lblself:CQT.InteractiveLabelInstance,self:mywindow, row, col,key,*args):

            if key == 'ГруппаКод':
                pass

            if key == 'ОсновноеИзделиеКод':

                if not DTCLS.use_cache_params:

                    CQT.msgboxgYN(f'Кеширование параметров выключено. Сохранить ДСЕ атрибуты для основного изделия?')
                    self.ui.chk_use_cache_params.setChecked(True)

                DTCLS.current_elem._cr_res_data.schema.ref_output_dse = None
            tbl.item(row, col).setText('')
            lblself.set_text('')


        @CQT.onerror
        def fnc_select_val(lblself:CQT.InteractiveLabelInstance,self:mywindow, row, col,key,*args):
            list_data = []
            result = dict()
            fnc_oform_tbl = None
            if key == 'ГруппаКод':
                list_GroupResData = CRES.GroupResData().to_list()
                list_data = [{'':CEMOJ.EmojiMain.Документы.folder.symbol , 'Код': _[1].code, 'Наименование': _[1].name}
                             for _ in list_GroupResData]

            if key in ('НачалоДействияРесурсной','КонецДействияРесурсной'):
                ans , dates = CQT.get_data_dialog_choose(self,f'Выбор {key}','Выбрать',format_dates="%d.%m.%Y")
                if not  ans:
                    return
                result['Код'] = dates['date_from']

            if key == 'ОсновноеИзделиеКод':

                def fnc_oform_tbl(tbl:CQT.QTableWidget,parent_self:mywindow):
                    fnc_oform_tbl_select_dse(tbl)

                tree: CTREE.ExtTreeWidget = self.ui.tree_add_dse
                current_видНоменклатуры = tree.currentItem()
                if current_видНоменклатуры is None:
                    DTCLS.app_self.ui.tabw_add_erp.setCurrentIndex(
                        CQT.number_table_by_name_c(DTCLS.app_self.ui.tabw_add_erp,
                                                   'ДСЕ'))
                    CQT.blink_widget_border(DTCLS.app_self.ui.tree_add_dse, msg= f'Не выбран вид номенклатуры')
                    return
                data = current_видНоменклатуры.to_dict()
                Ref_видНоменклатуры  = data['Ref']
                видНоменклатурыНаименование  = data['Наименование']
                list_data =  get_list_nomen(Ref_видНоменклатуры, TypesDoc.dse, видНоменклатурыНаименование)
                if list_data is not None:
                    list_data = oform_НаУдаление(list_data['data'])


            if list_data:
                result = CQT.msgboxg_get_table(self, f'Выбор {key}', list_data, "Выбор",
                                           styleSheet=CQT.ERP_CSS, ExtendedSelection=False,
                                           selectRows=True, selection_from_tbl=True,func_oform_tbl=fnc_oform_tbl,
                                               parent_self=DTCLS.app_self)

            if result:
                if key == 'ОсновноеИзделиеКод':
                    DTCLS.current_elem._cr_res_data.schema.ref_output_dse = result['Ref']
                lblself.set_text(result['Код'])
                tbl.item(row,col).setText(result['Код'])


        schema = self.schema
        with CQT.table_updating(tbl):
            CQT.clear_tbl(tbl)
            data_for_tbl= []

            for row, (key, meta) in enumerate(schema.items()):
                val = ''
                if key in values_attr:
                    val = values_attr[key]
                if key == 'НаименованиеРесурсной':
                    if DTCLS.current_elem:
                        val = DTCLS.current_elem.name
                data_for_tbl.append({'name':key, 'Параметр': meta["descr"], 'Значение': val})
            CQT.fill_wtabl(data_for_tbl,tbl,selectionMode='SingleSelection',styleSheet=CQT.ERP_CSS,
                           set_editeble_col_nomera={2})
            if not DTCLS.view_hidden_fields:
                tbl.setColumnHidden(0,True)

            for row, (key, meta) in enumerate(schema.items()):
                if meta["type"] == "str":
                    if key == 'НаименованиеРесурсной':
                        CQT.set_cell_editable(tbl,row,2,False)

                elif meta["type"] == "text":
                    pass
                elif meta["type"] == "int":
                    pass

                elif meta["type"] == "date":
                    widg = CQT.add_interactive_label(tbl, row, 2, tbl.item(row, 2).text(),
                                                     parent_self=DTCLS.app_self)
                    widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбор',
                                    fnc_select_val,
                                    cell_val=key, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                         'icons', 'btn_select']))
                elif meta["type"] == "combo":
                    list_txt = []
                    list_data = []
                    if key == 'ГруппаКод':
                        list_GroupResData = CRES.GroupResData().to_list()
                        list_txt = [_[0] for _ in list_GroupResData]
                        list_data = [_[1] for _ in list_GroupResData]

                    CQT.add_combobox(DTCLS.app_self,tbl,row,2,list_txt,first_void=False,
                                     list_data=list_data, return_data=True )
                elif meta["type"] == "tbl":

                    widg = CQT.add_interactive_label(tbl, row,2, tbl.item(row,2).text(),
                                                     parent_self=DTCLS.app_self)
                    widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбор',
                                        fnc_select_val,
                                        cell_val=key,img_path=  F.sep().join([F.path_to_execut_file_c(),
                                                                              'icons','btn_select']) )
                    widg.add_button(CEMOJ.EmojiMain.Статусы.error.symbol, 'Очистить', on_clicked=fnc_clear_code,
                                    cell_val=key)



        CQT.load_column_widths(self, tbl, CMS.tmp_dir())
class CrResData(Base_cls):
    _UNSERIALIZABLE_ATTRS = {'parent','_lock_recalc'}
    def __init__(self,parent:TreeDoc):
        self._is_exists_all_attrs = False
        self.parent:TreeDoc = parent
        self.schema:CrResParams = CrResParams(self)
        self.body:CrResBody = CrResBody(self)
        self.hat_filled:bool = False
        self.body_filled:bool = False
        self._is_exists_all_attrs = True
    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if self._lock_recalc:
            return
        if getattr(self, '_is_exists_all_attrs', None):
            if key in ('hat_filled','body_filled'):
                self._calc_docRes_filled()

    @classmethod
    def _import(cls, data, parent=None):
        obj = cls.__new__(cls)
        obj._lock_recalc = True
        obj.parent = parent

        # Восстанавливаем schema
        if 'schema' in data and data['schema'] is not None:
            obj.schema = CrResParams._import(data['schema'], obj)
        else:
            obj.schema = CrResParams(obj)

        # Восстанавливаем body
        if 'body' in data and data['body'] is not None:
            obj.body = CrResBody._import(data['body'], obj)
        else:
            obj.body = CrResBody(obj)

        # Восстанавливаем флаги
        obj.hat_filled = data.get('hat_filled', False)
        obj.body_filled = data.get('body_filled', False)

        # Устанавливаем связь schema.body если нужно
        if hasattr(obj.schema, 'body'):
            obj.schema.body = obj.body
        obj._lock_recalc = False
        return obj

    def gen_params_for_save(self)->dict:
        return {'body':self.body.gen_params_for_save(),'hat':self.schema.gen_params_for_save()}

    def clear(self):
        self.__init__(self.parent)
    def _recalc_docRes_filled(self):
        self.schema.calc_filled_ready()
        self.body.calc_filled_body()

    def fill_tables(self):
        if self.body is not None:
            self.body.fill_table(DTCLS.app_self.ui.tbl_cr_etaps_res)
        if self.schema is not None:
            self.schema._fill_table_from_schema(DTCLS.app_self.ui.tbl_cr_res)

    def update_doc_ready_state(self):
        self._calc_docRes_filled()

    def _calc_docRes_filled(self):
        res_filled= self._check_res_filled()
        if res_filled != self.parent._filled_bodyHat_erp_export:
            self.parent.recalc_filled_bodyHat_erp_export()
            self.parent.update_attr_into_gui_obj('code')

    def _check_res_filled(self):
        return self.hat_filled and self.body_filled

    def generate_dict_etaps(self)->dict[str,dict[str,any]]:
        result_dict = self.body.calc_dict_etaps()
        return  result_dict
    def export_to_1c(self)->tuple[bool, dict]:
        hat = self.schema
        dict_etaps = self.generate_dict_etaps()
        main_izd = CRES.MainProduct.find_by_code(hat.ОсновноеИзделиеКод)
        obj = self.generate_obj( main_izd,
                                hat.ГруппаКод,
                                hat.НаименованиеРесурсной,
                                hat.НачалоДействияРесурсной,
                                hat.КонецДействияРесурсной,
                                hat.Описание,
                                dict_etaps,
                                )
        print(obj.to_dict())
        print()
        succ, data = obj.send(msg=False,return_err=True)
        return succ, data
    def generate_obj(self,
                     ОсновноеИзделиеКод:CRES.MainProduct,
                     ГруппаКод,
                     НаименованиеРесурсной,
                     НачалоДействияРесурсной,
                     КонецДействияРесурсной,
                     Описание,
                     dict_etaps:dict,
                     code_old_res=None,)->CRES.ResourceSpecification:
        """
        :param ОсновноеИзделиеКод:
        :param ГруппаКод:
        :param НаименованиеРесурсной:
        :param НачалоДействияРесурсной:
        :param КонецДействияРесурсной:
        :param Описание:
        :param dict_etaps:
            dict_etaps = {
                        "Этап 1": {  # ключ — имя или код этапа
                            ""Опер_код_подразделения": "00-222",
                            "ДлительностьМинут": 120,  # число
                            "Материалы": {
                                "mat_001": {  # ключ — идентификатор материала (произвольный)
                                    "Мат_код": "M001",  # код материала
                                    "Мат_наименование": "Сталь 20",
                                    "Мат_норма": 12.5,  # норма расхода
                                    "Материалы_Статья_калькуляции": "Основные материалы",
                                    "Способы_получения_материала": "Покупной"
                                },
                                "mat_002": {
                                    "Мат_код": "M002",
                                    "Мат_наименование": "Электрод УОНИ-13/55",
                                    "Мат_норма": 0.5,
                                    "Материалы_Статья_калькуляции": "Вспомогательные материалы",
                                    "Способы_получения_материала": "Покупной"
                                },
                            },
                            "Трудозатраты": {
                                "ref_001": 2.5,  # ключ — ссылка на вид работ (ref), значение — количество (часы, человеко-часы и т.п.)
                                "ref_002": 1.0
                            }
                        },
                        "Этап 2": {
                            "Опер_код_подразделения": "00-222",
                            "ДлительностьМинут": 60,
                            "Материалы": {
                                "mat_003": {
                                    "Мат_код": "M003",
                                    "Мат_наименование": "Болт М6",
                                    "Мат_норма": 10,
                                    "Материалы_Статья_калькуляции": "Крепеж",
                                    "Способы_получения_материала": "Покупной"
                                }
                            },
                            "Трудозатраты": {
                                "ref_003": 3.0
                            }
                        }
                    }
        :param code_old_res:
        :return:
        """


        СпособРаспределенияЗатратНаВыходныеИзделия = CRES.TheMethodOfAllocatingTheCostOfTheOutputProductsData._hnt_по_долям_стоимости_0
        РодительКод = CRES.GroupResData.find_by_code(ГруппаКод, CRES.GroupRes())
        ПодразделениеДиспетчер = None
        ВариантПодбораВДокументы = None
        if CFG.Config.place.poki == 0:
            ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_автоматически_по_приоритету_0
            ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_планово_диспетчерский_отдел_производства_пауэрз_производственные_подразделения_пауэрз_00_000049
        if CFG.Config.place.poki == 1:
            ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_планово_диспетчерский_отдел_производства_келаст_производственные_подразделения_келаст_00_000112
            ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_вручную_1
        if CFG.Config.place.poki == 3:
            ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
            ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_вручную_1
        if ВариантПодбораВДокументы is None:
            raise ValueError('ВариантПодбораВДокументы')
        # Шапка
        hat = CRES.ResourceHeader(
            ОсновноеИзделиеКод=ОсновноеИзделиеКод,
            КоличествоУпаковок=1,
            Наименование=НаименованиеРесурсной,
            ТекущийПользователь=CRES.CurrentUser(F.user_full_namre()),
            ДатаНачала=F.dateStrToStr(НачалоДействияРесурсной),
            ДатаОкончания=F.dateStrToStr(КонецДействияРесурсной),
            ПодразделениеДиспетчер=ПодразделениеДиспетчер,
            РодительКод=РодительКод,
            ВариантПодбораВДокументы=ВариантПодбораВДокументы,
            Описание=Описание,
            СпособРаспределенияЗатратНаВыходныеИзделия=СпособРаспределенияЗатратНаВыходныеИзделия,
            Код=code_old_res
        )

        spec = CRES.ResourceSpecification(hat)

        for k, v in dict_etaps.items():
            if len(v['Материалы']) or len(v['Трудозатраты']):
                # Этап
                Подразделение = CRES.SubdivisionsData.find_by_code(v['Опер_код_подразделения'])
                stage_data = CRES.StageData(
                    Подразделение=Подразделение,
                    ДлительностьМинут= v['ДлительностьМинут']
                )
                for mat in v['Материалы'].values():
                    if mat['Мат_норма']:
                        ИсточникПолученияПолуфабриката = CRES.field(default_factory=CRES.SourceOfTheHalffactoryReceipt)
                        if 'КодИсточник' in mat:
                            ИсточникПолученияПолуфабриката = CRES.SourceOfTheHalffactoryReceipt.find_by_code(mat['КодИсточник'])
                        if F.is_unique_identifier(mat['Материалы_Статья_калькуляции']):
                            Материалы_Статья_калькуляции = CRES.ArticulationArticlesData.find_by_ref(mat['Материалы_Статья_калькуляции'])
                        else:
                            Материалы_Статья_калькуляции = CRES.ArticulationArticlesData.find_by_name(mat['Материалы_Статья_калькуляции'])
                        if F.is_unique_identifier(mat['Способы_получения_материала']):
                            Способы_получения_материала = CRES.MethodOfObtainingMaterialspecificationsData.find_by_ref(mat['Способы_получения_материала'])
                        else:
                            Способы_получения_материала = CRES.MethodOfObtainingMaterialspecificationsData.find_by_name(mat['Способы_получения_материала'])
                        if 'КодИсточник' in mat:
                            ИсточникПолученияПолуфабриката = CRES.SourceOfTheHalffactoryReceipt.find_by_code(mat['КодИсточник'])
                            CRESMateria = CRES.Material(
                                mat['Мат_код'],
                                mat['Мат_норма'],
                                Материалы_Статья_калькуляции,
                                Способы_получения_материала,
                                ИсточникПолученияПолуфабриката)
                        else:
                            CRESMateria = CRES.Material(
                                mat['Мат_код'],
                                mat['Мат_норма'],
                                Материалы_Статья_калькуляции,
                                Способы_получения_материала )
                        stage_data.add_material(CRESMateria)
                    else:
                        CQT.msgbox(
                            f'В `{v["Опер_наименование_подразделения"]}` пропущен материал \n`{mat["Мат_наименование"]}`\nт.к. кол-во = 0')

                trs = v['Трудозатраты']
                for key, tr in trs.items():
                    if tr:
                        stage_data.add_labor(CRES.LaborCost(
                            CRES.TypeOfWorkData.find_by_ref(key),
                            tr)
                        )
                    else:
                        CQT.msgbox(
                            f'В `{v["Опер_наименование_подразделения"]}` пропущен вид работ \n`{DTCLS.DICT_VID_RAB_BY_REF[key]["Список"]}`\nт.к. кол-во = 0')

                spec.add_stage(CRES.Stage(k, stage_data))


        return spec


class CrDseBody(Base_cls):
    CACHED_ATTRIBUTES = {
        'ТипНоменклатуры',
        'Группа',
        'ВидНоменклатуры',
        'ВариантОформленияПродажи',
        'ГруппаДоступа',
        'ЕдиницаИзмерения',
        'ЕдиницаДляОтчетов',
        'СтавкаНДС',
        'ГруппаАналитическогоУчета',
        'ГруппаФинансовогоУчета',
        'СпособПолучения',
        'СтатьяКалькуляции',
    }
    SET_USER_FILLED_ATTRS = {
        'Артикул',
        'ТипНоменклатуры',
        'Группа',
        'ВидНоменклатуры',
        'ВариантОформленияПродажи',
        'ГруппаДоступа',
        'ЕдиницаИзмерения',
        'ЕдиницаДляОтчетов',
        'СтавкаНДС',
        'ГруппаАналитическогоУчета',
        'ГруппаФинансовогоУчета',
        'СпособПолучения',
        'СтатьяКалькуляции',
    }
    DICT_ALIASES = {

    }
    SET_EXPORT_ATTRS = {
        'Артикул',
        'ТипНоменклатуры',
        'Группа',
        'ВидНоменклатуры',
        'ВариантОформленияПродажи',
        'ГруппаДоступа',
        'ЕдиницаИзмерения',
        'ЕдиницаДляОтчетов',
        'СтавкаНДС',
        'ГруппаАналитическогоУчета',
        'ГруппаФинансовогоУчета',
        'СпособПолучения',
        'СтатьяКалькуляции',
    }
    SET_FREE_FIELDS = {'Артикул'}
    SET_SELECTABLE_FIELDS = {
        'ТипНоменклатуры',
        'Группа',
        'ВидНоменклатуры',
        'ВариантОформленияПродажи',
        'ГруппаДоступа',
        'ЕдиницаИзмерения',
        'ЕдиницаДляОтчетов',
        'СтавкаНДС',
        'ГруппаАналитическогоУчета',
        'ГруппаФинансовогоУчета',
        'СпособПолучения',
        'СтатьяКалькуляции',
    }
    SET_OPTIONAL_FIELDS = {'Артикул','Группа','ГруппаАналитическогоУчета','ГруппаФинансовогоУчета'}
    SET_ROOT_OPTIONAL_FIELDS = {'Артикул','Группа','СпособПолучения','СтатьяКалькуляции'}
    SET_ROOT_HIDDEN_FIELDS = {'СпособПолучения','СтатьяКалькуляции'}

    _UNSERIALIZABLE_ATTRS = {'parent','_lock_recalc'}
    def __init__(self, parent: CrDseData):

        self.parent: CrDseData = parent
        self.Артикул:str = ''
        self._ТипНоменклатуры:None|CRES.TypeNomen = None
        self._Группа:None|CRES.TypeNomen = None
        self._ВидНоменклатуры:None|CRES.TypeNomen = None
        self._ВариантОформленияПродажи:None|CRES.SalesOptions = None
        self._ГруппаДоступа:None|CRES.AccessGroup = None
        self._ЕдиницаИзмерения:None|CRES.PackagingUnits = None
        self._ЕдиницаДляОтчетов:None|CRES.PackagingUnits = None
        self._СтавкаНДС:None|CRES.NDS_rates = None
        self._ГруппаАналитическогоУчета:None|CRES.NomenAnalysisGroups= None
        self._ГруппаФинансовогоУчета:None|CRES.FinancialAccountingGroup = None
        self._СпособПолучения:None|CRES.MethodOfObtainingMaterialspecifications = None
        self._СтатьяКалькуляции:None|CRES.ArticulationArticles = None

        self._is_exists_all_attrs = True
        self._fill_data_from_parent()

        if DTCLS.use_cache_params:
            for attr in F.get_all_attrs_with_properties(self,prefer_properties=True):
                if attr not in self.CACHED_ATTRIBUTES:
                    continue
                cached_val = self._load_cache_attr(attr)
                if cached_val is not None:
                    setattr(self, attr, cached_val)
        self.calc_filled_body()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if self._lock_recalc:
            return
        if getattr(self,'_is_exists_all_attrs',None):
            self.calc_filled_body()
    def __str__(self):
        name = ''
        if self._ВидНоменклатуры is not None:
            name = f'({self._ВидНоменклатуры.name})'
        return f'{self.Артикул}{name}'



    def gen_params_for_save(self) -> dict:
        res = {}
        for k,v in F.get_all_attrs_with_properties(self).items():
            if k in self.SET_EXPORT_ATTRS:
                if hasattr(v,'ref_key'):
                    res[k] = v.ref_key
                else:
                    res[k] = v
        return res

    @property
    def ВидНоменклатуры(self) -> None|CRES.VidNomem:
        return self._ВидНоменклатуры
    @ВидНоменклатуры.setter
    def ВидНоменклатуры(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ВидНоменклатуры = CRES.VidNomemData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ВидНоменклатуры')
    @property
    def Группа(self) -> None|CRES.GruopNomen:
        return self._Группа
    @Группа.setter
    def Группа(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._Группа = CRES.GruopNomenData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err Группа')
    @property
    def ТипНоменклатуры(self) -> None|CRES.TypeNomen:
        return self._ТипНоменклатуры
    @ТипНоменклатуры.setter
    def ТипНоменклатуры(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ТипНоменклатуры = CRES.TypeNomenData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ТипНоменклатуры')

    @property
    def ВариантОформленияПродажи(self) -> None|CRES.SalesOptions:
        return self._ВариантОформленияПродажи
    @ВариантОформленияПродажи.setter
    def ВариантОформленияПродажи(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ВариантОформленияПродажи = CRES.SalesOptionsData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ВариантОформленияПродажи')

    @property
    def ГруппаДоступа(self) -> None | CRES.AccessGroup:
        return self._ГруппаДоступа
    @ГруппаДоступа.setter
    def ГруппаДоступа(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ГруппаДоступа = CRES.AccessGroupData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ГруппаДоступа')

    @property
    def ЕдиницаИзмерения(self) -> None | CRES.PackagingUnits:
        return self._ЕдиницаИзмерения
    @ЕдиницаИзмерения.setter
    def ЕдиницаИзмерения(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ЕдиницаИзмерения = CRES.PackagingUnitsData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ЕдиницаИзмерения')

    @property
    def ЕдиницаДляОтчетов(self) -> None | CRES.PackagingUnits:
        return self._ЕдиницаДляОтчетов
    @ЕдиницаДляОтчетов.setter
    def ЕдиницаДляОтчетов(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ЕдиницаДляОтчетов = CRES.PackagingUnitsData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ЕдиницаДляОтчетов')


    @property
    def СтавкаНДС(self) -> None | CRES.NDS_rates:
        return self._СтавкаНДС
    @СтавкаНДС.setter
    def СтавкаНДС(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._СтавкаНДС = CRES.NDS_ratesData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err СтавкаНДС')
    @property
    def ГруппаАналитическогоУчета(self) -> None | CRES.NomenAnalysisGroups:
        return self._ГруппаАналитическогоУчета
    @ГруппаАналитическогоУчета.setter
    def ГруппаАналитическогоУчета(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ГруппаАналитическогоУчета = CRES.NomenAnalysisGroupsData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ГруппаАналитическогоУчета')

    @property
    def ГруппаФинансовогоУчета(self) -> None | CRES.FinancialAccountingGroup:
        return self._ГруппаФинансовогоУчета
    @ГруппаФинансовогоУчета.setter
    def ГруппаФинансовогоУчета(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._ГруппаФинансовогоУчета = CRES.FinancialAccountingGroupData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err ГруппаФинансовогоУчета')

    @property
    def СпособПолучения(self) -> None | CRES.MethodOfObtainingMaterialspecifications:
        return self._СпособПолучения
    @СпособПолучения.setter
    def СпособПолучения(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._СпособПолучения = CRES.MethodOfObtainingMaterialspecificationsData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err СпособПолучения')

    @property
    def СтатьяКалькуляции(self) -> None | CRES.ArticulationArticles:
        return self._СтатьяКалькуляции
    @СтатьяКалькуляции.setter
    def СтатьяКалькуляции(self, ref: str):
        if F.is_unique_identifier(ref) or ref is None:
            self._СтатьяКалькуляции = CRES.ArticulationArticlesData.find_by_ref(ref,None)
        else:
            raise ValueError(f'ref err СтатьяКалькуляции')
    def reset(self):
        СпособПолучения = None
        СтатьяКалькуляции = None
        if self.СпособПолучения:
            СпособПолучения = self.СпособПолучения.ref_key
        if self.СтатьяКалькуляции:
            СтатьяКалькуляции = self.СтатьяКалькуляции.ref_key
        self.__init__(self.parent)
        if СпособПолучения:
            self.СпособПолучения = СпособПолучения
        if СтатьяКалькуляции:
            self.СтатьяКалькуляции = СтатьяКалькуляции

    def get_alias(self,attr:str)->str:
        if attr in self.DICT_ALIASES:
            return self.DICT_ALIASES[attr]
        return attr



    def get_unfilled_atts(self)->list[str]:
        result = list()
        for attr in F.get_all_attrs_with_properties(self,prefer_properties=True):
            if attr in self.SET_EXPORT_ATTRS:
                val = getattr(self,attr)
                if val is None and attr not in self.SET_OPTIONAL_FIELDS:
                    if self.parent.parent.is_root():
                        if attr not in self.SET_ROOT_OPTIONAL_FIELDS:
                            result.append(attr)
                    else:
                        result.append(attr)
        return result
    def save_attr_cache(self,attr:str):
        if attr not in self.CACHED_ATTRIBUTES:
            return
        val = getattr(self,attr)
        if val is not None:
            if not isinstance(val,str):
                val = getattr(val,'ref_key')
        self._cache_attr(attr,val)
    def _name_for_cache(self,attr:str):
        return f'cache_CrDseBodyParams_' + attr
    def _cache_attr(self,attr:str,val):
        if attr in self.CACHED_ATTRIBUTES:
            CMS.save_tmp_stukt(val,self._name_for_cache(attr))
    def _load_cache_attr(self,attr:str):
        if attr in self.CACHED_ATTRIBUTES:
            return CMS.load_tmp_stukt(self._name_for_cache(attr),None)

    def fill_table(self):

        def fnc_clear_val(lblself:CQT.InteractiveLabelInstance,self:mywindow, row, col,name_attr,*args):
            tbl.item(row, nf['Значение']).setText('')
            tbl.item(row, nf['ref_key']).setText('')
            lblself.set_text('')

        def fnc_select_val(lblself:CQT.InteractiveLabelInstance,self:mywindow, row, col,name_attr,*args):
            list_data = []
            result = dict()

            def fnc_oform_tbl(tbl_: CQT.QTableWidget, parent_self: mywindow):
                nf = CQT.nums_col_by_name_dict(tbl_)
                if not DTCLS.view_hidden_fields:
                    tbl_.setColumnHidden(nf['ref_key'], True)

            if name_attr == 'ТипНоменклатуры':
                list_data = [_[1].__dict__ for _ in CRES.TypeNomenData.to_list()]

            if name_attr == 'Группа':
                list_data = [_[1].__dict__ for _ in CRES.GruopNomenData.to_list()]

            if name_attr == 'ВидНоменклатуры':
                list_data = [_[1].__dict__ for _ in CRES.VidNomemData.to_list()]

            if name_attr == 'ВариантОформленияПродажи':
                list_data = [_[1].__dict__ for _ in CRES.SalesOptionsData.to_list()]

            if name_attr == 'ГруппаДоступа':
                list_data = [_[1].__dict__ for _ in CRES.AccessGroupData.to_list()]

            if name_attr == 'ЕдиницаИзмерения':
                list_data = [_[1].__dict__ for _ in CRES.PackagingUnitsData.to_list()]

            if name_attr == 'ЕдиницаДляОтчетов':
                list_data = [_[1].__dict__ for _ in CRES.PackagingUnitsData.to_list()]

            if name_attr == 'СтавкаНДС':
                list_data = [_[1].__dict__ for _ in CRES.NDS_ratesData.to_list()]

            if name_attr == 'ГруппаАналитическогоУчета':
                list_data = [_[1].__dict__ for _ in CRES.NomenAnalysisGroupsData.to_list()]

            if name_attr == 'ГруппаФинансовогоУчета':
                list_data = [_[1].__dict__ for _ in CRES.FinancialAccountingGroupData.to_list()]

            if name_attr == 'СпособПолучения':
                list_data = [_[1].__dict__ for _ in CRES.MethodOfObtainingMaterialspecificationsData.to_list()]
                list_data = [_ for  _ in list_data if _['name'] != 'Произвести по спецификации']

            if name_attr == 'СтатьяКалькуляции':
                list_data = [_[1].__dict__ for _ in CRES.ArticulationArticlesData.to_list()]


            fl_is_group_exists = False
            for i in range(len(list_data)):
                if 'group' in list_data[i]:
                    fl_is_group_exists = True
                    if list_data[i]['group']:
                        list_data[i]['group'] = CEMOJ.EmojiMain.Документы.folder_closed.symbol
                    else:
                        list_data[i]['group'] = CEMOJ.EmojiMain.Документы.document.symbol
            if fl_is_group_exists:
                list_data = F.move_key_in_dicts(list_data,'group',0)
            if list_data:
                result = CQT.msgboxg_get_table(self, f'Выбор {name_attr}', list_data, "Выбор",
                                           styleSheet=CQT.ERP_CSS, ExtendedSelection=False,
                                           selectRows=True, selection_from_tbl=True,func_oform_tbl=fnc_oform_tbl,
                                               parent_self=DTCLS.app_self,aliases_header=CRES.TypeNomen.DICT_ALIASES
                                               )

            if result:
                tbl.item(row,nf['Значение']).setText(result['name'])
                tbl.item(row,nf['ref_key']).setText(result['ref_key'])
                lblself.set_text(result['name'])

        tbl = DTCLS.app_self.ui.tbl_cr_dse
        with CQT.table_updating(tbl):
            list_data_dse = self.get_list_attrs()
            CQT.fill_wtabl(list_data_dse, tbl, selectionMode='SingleSelection', styleSheet=CQT.ERP_CSS,
                           set_editeble_col_nomera={2})
            nf = CQT.nums_col_by_name_dict(tbl)
            CQT.load_column_widths(DTCLS.app_self, tbl, CMS.tmp_dir())
            if not DTCLS.view_hidden_fields:
                tbl.setColumnHidden(nf['name'],True)
                tbl.setColumnHidden(nf['ref_key'],True)


            for i in range(tbl.rowCount()):
                name_attr = tbl.item(i,nf['name']).text()
                text_val = tbl.item(i, nf['Значение']).text()
                if name_attr in self.SET_SELECTABLE_FIELDS:
                    widg = CQT.add_interactive_label(tbl, i, 2, text_val,
                                                     parent_self=DTCLS.app_self)
                    widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбор',
                                    fnc_select_val,
                                    cell_val=name_attr, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                         'icons', 'btn_select']))

                    widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol, 'Очистить',
                                    fnc_clear_val,
                                    cell_val=name_attr)


        CQT.load_column_widths(self, tbl, CMS.tmp_dir())

    def get_list_attrs(self):
        result = list()
        for attr in F.get_all_attrs_with_properties(self,False,True):
            if attr in self.SET_USER_FILLED_ATTRS:
                val = getattr(self,attr)
                val_str = val
                val_ref = None
                if isinstance(val,(
                        CRES.NDS_rates,
                        CRES.GruopNomen,
                        CRES.VidNomem,
                        CRES.TypeNomen,
                        CRES.SalesOptions,
                        CRES.AccessGroup,
                        CRES.PackagingUnits,
                        CRES.NomenAnalysisGroups,
                        CRES.FinancialAccountingGroup,
                        CRES.MethodOfObtainingMaterialspecifications,
                        CRES.ArticulationArticles,
                                   )):
                    val_str = val.name
                    val_ref = val.ref_key
                attr_alias = self.get_alias(attr)
                if self.parent.parent.is_root():
                    if attr in self.SET_ROOT_HIDDEN_FIELDS:
                        continue
                result.append({'name': attr, 'Параметр': attr_alias, 'Значение': val_str, 'ref_key': val_ref} )
        return result

    def _fill_data_from_parent(self):
        pass

    def calc_filled_body(self):
        self.parent.body_filled = self._check_filled_body()

    def _check_filled_body(self):
        if self.get_unfilled_atts():
            return False
        return True



class CrDseData(Base_cls):
    connector = {'КолВо':'count',
                 'Наименование':'name'}
    NECCESARY_FILL = {'name','count'}
    _UNSERIALIZABLE_ATTRS = {'parent','_lock_recalc'}
    def __init__(self,parent:TreeDoc):

        self.parent:TreeDoc = parent
        self.name:str|None = None
        self.count:int|float|None = None
        self.hat_filled:bool = False
        self.body_filled: bool = False
        self.body:CrDseBody = CrDseBody(self)

        self.get_vals_from_parent()
        self._recalc_hat_filled()
    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if self._lock_recalc:
            return
        if key in ('hat_filled','body_filled'):
            self._calc_docDse_filled()
    def __str__(self):
        return f'{self.name} {self.body}'

    @classmethod
    def _import(cls, data, parent=None):
        obj = cls.__new__(cls)
        obj._lock_recalc = True
        obj.parent = parent

        obj.name = data.get('name')
        obj.count = data.get('count')
        obj.hat_filled = data.get('hat_filled', False)
        obj.body_filled = data.get('body_filled', False)

        if 'body' in data:
            obj.body = CrDseBody._import(data['body'], obj)
        obj._lock_recalc = False
        return obj
    def gen_params_for_save(self) -> dict:
        return {'body': self.body.gen_params_for_save(), 'hat': {'name':self.name,'count':self.count}}

    def clear(self):
        self.__init__(self.parent)

    def fill_tables(self):
        self.body.fill_table()

    def export_to_1c(self)->tuple[bool, dict]:
        obj = CRES.Nomenclature(self.body.parent.parent.name,
                                self.body.Артикул,
                                self.body.ТипНоменклатуры,
                                self.body.Группа,
                                self.body.ВидНоменклатуры,
                                self.body.ВариантОформленияПродажи,
                                self.body.ГруппаДоступа,
                                self.body.ЕдиницаИзмерения,
                                self.body.ЕдиницаДляОтчетов,
                                self.body.СтавкаНДС,
                                self.body.ГруппаАналитическогоУчета,
                                self.body.ГруппаФинансовогоУчета
                                )
        succ, data = obj.create_nomen()
        return succ, data
    def get_vals_from_parent(self):
        for field,val in list(F.get_all_attrs_with_properties(self.parent).items()):
            field = self.parent.alias(field)
            if field in self.connector:
                field = self.connector[field]
            if field in self.__dict__:
                setattr(self, field, val)
        self._recalc_hat_filled()


    def set_value_by_field(self, field: str, new_value):
        if field in self.connector:
            field = self.connector[field]
        if field in self.__dict__:
            setattr(self,field,new_value)
            self._recalc_hat_filled()

    def get_not_filled_attrs(self)->list[str]:
        res = list()
        for k, v in self.__dict__.items():
            if k in self._UNSERIALIZABLE_ATTRS:
                continue
            if k in self.NECCESARY_FILL:
                if v is None or v in ('', 0, 0.0):
                    res.append(self.apply_aliases(k))
        return res

    def apply_aliases(self,attr:str)->str:
        for k,v in self.connector.items():
            if v == attr:
                return k
        return attr

    def _calc_filled_ready(self):
        if self.get_not_filled_attrs():
            return False
        return True
    def _recalc_hat_filled(self):
        self.hat_filled = self._calc_filled_ready()
    def _recalc_body_filled(self):
        self.body.calc_filled_body()

    def _recalc_filled(self):
        self._recalc_hat_filled()
        self._recalc_body_filled()

    def _check_dse_filled(self):
        return self.hat_filled and self.body_filled


    def _calc_docDse_filled(self):
        res_ready = self._check_dse_filled()
        if res_ready != self.parent._filled_bodyHat_erp_export:
            self.parent.recalc_filled_bodyHat_erp_export()
            self.parent.update_attr_into_gui_obj('code')

    def update_doc_ready_state(self):
        self._calc_docDse_filled()

class ErrorsTreeDoc():
    def __init__(self):
        self.list_errs = []
    def add_err(self, doc:TreeDoc,text:str):
        self.list_errs.append({'Элемент':doc.еrror_name(),'Значение':text})



def fnc_oform_tbl_select_dse(tbl:CQT.QTableWidget):
    tbl.hideColumn(CQT.num_col_by_name_c(tbl,'Ref'))
def oform_НаУдаление(items):
    for i in items:
        if i['НаУдаление']:
            i['НаУдаление'] = CEMOJ.EmojiMain.Статусы.error.symbol
        else:
            i['НаУдаление'] = ''
        if i['Тип'] == True:
            i['Тип'] = CEMOJ.EmojiMain.ДокументыДанные.folder.symbol
        else:
            i['Тип'] = CEMOJ.EmojiMain.ДокументыДанные.document.symbol
    return items
def get_list_nomen(ref:str,obj_type:TypeDoc,Наименование:str)->None|dict:
    text = """
                            ВЫБРАТЬ
                            "" КАК Тип,
                            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Ссылка)) КАК Ref,
                                Номенклатура.ПометкаУдаления КАК НаУдаление,
                                Номенклатура.Код КАК Код,
                                Номенклатура.Артикул КАК Артикул,
                                Номенклатура.Наименование КАК Наименование
                            ИЗ
                                Справочник.Номенклатура КАК Номенклатура
                            ГДЕ
                                Номенклатура.ВидНоменклатуры.Ссылка = &Ссылка
                    """

    refs = APIERP.Refs_wet(text)
    ref_obj = APIERP.Ref_wet('Ссылка', obj_type.path_parent_conf_1c, ref)

    refs.add_ref(ref_obj)
    key, res = APIERP.get_wet_request(text=text, refs=refs)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных из ЕРП')
        return
    if not res['data']:
        CQT.msgbox(f'{obj_type.user_name} для {Наименование} не найдены')
        return
    return res
