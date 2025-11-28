from __future__ import annotations
import project_cust_38.Cust_odata_erp as ODAT
import project_cust_38.Cust_Functions as F
import os
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
from project_cust_38 import Cust_config as CFG
import project_cust_38.api_erp_commands as APIERP
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Union, ClassVar, get_type_hints, Any
import json
import re
import keyword

FL_LOAD_PROP = False
LAZY_METHOD_HUOURS = 300
if __name__ == '__main__':
    FL_LOAD_PROP = True
    LAZY_METHOD_HUOURS = 0.02


def __________attrs_nomen___________():
    pass
class base_attr():
    DICT_ALIASES = {
        'name':'Имя',
        'order':'Порядок',
        'code':'Код',
        'fullname':'Полное имя',
        'value_type': 'Вид',
        'group': 'Тип',
        'parent': 'Родитель'
    }

# --- СтавкиНДС ---
@dataclass
class NDS_rates(base_attr):
    name: str
    ref_key: str | None

# --- ВидыНоменклатуры ---
@dataclass
class VidNomem(base_attr):
    name: str
    parent: str
    group: bool
    ref_key: str | None

# --- ГруппаНоменклатуры ---
@dataclass
class GruopNomen(base_attr):
    name: str
    code: str
    parent: str
    group: bool
    ref_key: str | None

# --- ТипыНоменклатуры ---
@dataclass
class TypeNomen(base_attr):
    name: str
    order: int | None
    ref_key: str | None

# --- ВариантыОформленияПродажи ---
@dataclass
class SalesOptions(base_attr):
    name: str
    order: int | None
    ref_key: str | None

# --- ГруппыДоступаНоменклатуры ---
@dataclass
class AccessGroup(base_attr):
    name: str
    ref_key: str | None

# --- УпаковкиЕдиницыИзмерения ---
@dataclass
class PackagingUnits(base_attr):
    name: str
    code: str
    fullname: str
    ref_key: str | None

# --- ГруппыАналитическогоУчетаНоменклатуры ---
@dataclass
class NomenAnalysisGroups(base_attr):
    name: str
    parent: str
    group: bool
    ref_key: str | None

# --- ГруппыФинансовогоУчетаНоменклатуры ---
@dataclass
class FinancialAccountingGroup(base_attr):
    name: str
    parent: str
    value_type: str
    group: bool
    ref_key: str | None

def __________attrs____________():
    pass



# --- ПодразделениеДиспетчер ---
@dataclass
class Subdivision:
    name: str
    code: str

# --- РодительКод ---
@dataclass
class GroupRes:
    name: str | None = None
    code: str | None = None

@dataclass
class SourceOfTheHalffactoryReceipt:
    name: str | None = None
    code: str | None = None

    @classmethod
    def find_by_code(cls, code: str):
        req_text = f"""
                    ВЫБРАТЬ
                        РесурсныеСпецификации.Код КАК Код,
                        РесурсныеСпецификации.Наименование КАК Наименование
                    ИЗ
                        Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                    ГДЕ
                        РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
                         И РесурсныеСпецификации.Код = "{code}"
                    """
        key, data_rez = APIERP.get_wet_request(req_text, lazy_method_huours=LAZY_METHOD_HUOURS)
        if key != 200:
            raise ConnectionError(f'Ошибка получения данных РесурсныеСпецификации из ERP')

        if not data_rez['data']:
            raise ValueError(f'Не найдено РесурсныеСпецификации = `{code}` из ERP')

        Код = data_rez['data'][0]['Код']
        Наименование = data_rez['data'][0]['Наименование']
        return SourceOfTheHalffactoryReceipt( Наименование,Код)

# --- Материалы ---
@dataclass
class Material:
    КодНоменклатуры: str
    Количество: float
    СтатьяКалькуляции: ArticulationArticles
    СпособПолучения: MethodOfObtainingMaterialspecifications
    ИсточникПолученияПолуфабриката:SourceOfTheHalffactoryReceipt =  field(
        default_factory=SourceOfTheHalffactoryReceipt
    )

    def __post_init__(self):
        if self.СпособПолучения == MethodOfObtainingMaterialspecificationsData._hnt_произвести_по_спецификации_1:
            if self.ИсточникПолученияПолуфабриката == None:
                raise ValueError(f"ИсточникПолученияПолуфабриката не может быть None для СпособПолучения = произвести_по_спецификации")

# --- Трудозатраты ---
@dataclass
class LaborCost:
    ВидРабот: TypeOfWork
    Количество: Union[int, float]  # обычно минуты или часы


# --- Этап ---
@dataclass
class StageData:
    Подразделение: Subdivision
    Материалы: List[Material] = field(default_factory=list)
    Трудозатраты: List[LaborCost] = field(default_factory=list)
    ДлительностьМинут: int | float = 0

    def add_material(self, material: Material):
        self.Материалы.append(material)

    def add_labor(self, labor: LaborCost):
        self.Трудозатраты.append(labor)

    def __post_init__(self):
        if not (isinstance(self.ДлительностьМинут, int) or isinstance(self.ДлительностьМинут, float)):
            if not F.is_numeric(self.ДлительностьМинут):
                raise TypeError(f'ДлительностьМинут = `{self.ДлительностьМинут}` не число')
            self.ДлительностьМинут = F.valm(self.ДлительностьМинут)
        if self.ДлительностьМинут < 0:
            raise ValueError(f'ДлительностьМинут = `{self.ДлительностьМинут}` меньше нуля')


@dataclass
class Stage:
    НаименованиеЭтапа: str
    Данные: StageData


# --- Шапка ---

class ResourceHeader:
    def __init__(self, ОсновноеИзделиеКод: MainProduct,
                 ДатаНачала: str,
                 ДатаОкончания: str,
                 ПодразделениеДиспетчер: Subdivision,
                 РодительКод: GroupRes,
                 ВариантПодбораВДокументы: Variationsrespecificationdocuments,
                 СпособРаспределенияЗатратНаВыходныеИзделия: TheMethodOfAllocatingTheCostOfTheOutputProducts,
                 ТекущийПользователь: CurrentUser,
                 КоличествоУпаковок: int | float = 1,
                 Наименование: str | None = None,
                 ВыпускПроизвольнымиПорциями: bool = False,
                 ИмяБазы=CFG.Config.user_config.ERP_base_name['Значение'],
                 Описание: str = '',
                 Код: str | None = None  # для обновления = Код
                 ):
        '''

        :param ОсновноеИзделиеКод:
        :param Наименование:
        :param ДатаНачала:
        :param ДатаОкончания:
        :param ПодразделениеДиспетчер:
        :param РодительКод: Группа ресурсных спецификаций
        :param ВариантПодбораВДокументы:
        :param ВыпускПроизвольнымиПорциями:  Параметры производственного процесса-> Запуск
        :param ВыпускПроизвольнымиПорциями:
        :param ИмяБазы:
        :param ТекущийПользователь:
        :param Описание:
        :param Код:
        '''

        self.ОсновноеИзделиеКод: MainProduct = ОсновноеИзделиеКод
        if Наименование:
            self.Наименование: str = Наименование
        else:
            self.Наименование = self.ОсновноеИзделиеКод.Наименование
        self.ТекущийПользователь: CurrentUser = ТекущийПользователь
        self.ДатаНачала: str = ДатаНачала  # ДД.ММ.ГГГГ
        self.ДатаОкончания: str = ДатаОкончания
        self.Сохранять: bool = True
        self.ИмяБазы: str = ИмяБазы
        self.КоличествоУпаковок: int | float = КоличествоУпаковок
        self.КластерСерверов: str = self.get_claster()
        self.ПодразделениеДиспетчер: Subdivision = ПодразделениеДиспетчер
        self.ВыпускПроизвольнымиПорциями: bool = ВыпускПроизвольнымиПорциями
        self.РодительКод: GroupRes = РодительКод
        self.ВариантПодбораВДокументы: Variationsrespecificationdocuments = ВариантПодбораВДокументы
        self.СпособРаспределенияЗатрат: TheMethodOfAllocatingTheCostOfTheOutputProducts = СпособРаспределенияЗатратНаВыходныеИзделия
        self.Описание: Optional[str] = Описание
        self.Код: Optional[str] = Код  # для обновления = Код

        self.check_ОсновноеИзделиеКод()
        self.check_ТекущийПользователь()
        self.check_Даты()
        self.check_ОбновленияКод()

    def get_claster(self):
        claster = CSQ.custom_request_c(CFG.Config.project.db_users,
                                       f"""SELECT * FROM bases_ERP WHERE name = "{self.ИмяБазы}";""", rez_dict=True,
                                       one=True)
        return claster['КластерСерверов']

    def check_ОсновноеИзделиеКод(self):
        return self.check_КодНоменклатура(self.ОсновноеИзделиеКод.Код)

    def check_ОбновленияКод(self):
        if self.Код:
            return self.check_КодРесурсныеСпецификации(self.Код)

    def check_КодНоменклатура(self, Код):
        wet_req_text = f"""ВЫБРАТЬ
                        Номенклатура.Наименование КАК Наименование
                    ИЗ                
                        Справочник.Номенклатура КАК Номенклатура
                    ГДЕ
                        Номенклатура.Код = "{Код}";"""
        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            raise ConnectionError(f'Ошибка получения данных код ({key}) из ERP')
        if not data_rez['data']:
            raise ValueError(f'Не найдено изделие код ({Код}) из ERP')

    def check_КодРесурсныеСпецификации(self, Код):
        wet_req_text = f"""ВЫБРАТЬ
                        РесурсныеСпецификации.Наименование КАК Наименование
                    ИЗ                
                        Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                    ГДЕ
                        РесурсныеСпецификации.Код = "{Код}";"""
        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            raise ConnectionError(f'Ошибка получения данных код ({key}) из ERP')
        if not data_rez['data']:
            raise ValueError(f'Не найдено изделие код ({Код}) из ERP')

    def check_ТекущийПользователь(self):
        return True

    def check_Даты(self):
        self.check_Дата(self.ДатаНачала)
        self.check_Дата(self.ДатаОкончания)
        if F.strtodate(self.ДатаНачала, "%Y-%m-%d") >= F.strtodate(self.ДатаОкончания, "%Y-%m-%d"):
            raise ValueError(f'ДатаНачала >= ДатаОкончания')

    def check_Дата(self, Дата: str):
        if not F.is_date(Дата, "%Y-%m-%d"):
            raise ValueError(f'Дата {Дата} не формата "%Y-%m-%d"')


@dataclass
class MainProduct:
    Код: str
    Наименование: str
    ЕдИзм: str

    @classmethod
    def find_by_code(cls, code: str):
        req_text = f"""
                    ВЫБРАТЬ ПЕРВЫЕ 1
                        Номенклатура.Код КАК Код,
                        Номенклатура.Наименование КАК Наименование,
	                    Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмеренияНаименование
                    ИЗ
                        Справочник.Номенклатура КАК Номенклатура
                    ГДЕ
                        Номенклатура.Код = "{code}"
                    УПОРЯДОЧИТЬ ПО
                        Наименование
                    """
        key, data_rez = APIERP.get_wet_request(req_text, lazy_method_huours=LAZY_METHOD_HUOURS)
        if key != 200:
            raise ConnectionError(f'Ошибка получения данных Номенклатура из ERP')

        if not data_rez['data']:
            raise ValueError(f'Не найдено Номенклатура из ERP')

        Код = data_rez['data'][0]['Код']
        Наименование = data_rez['data'][0]['Наименование']
        ЕдИзм = data_rez['data'][0]['ЕдиницаИзмеренияНаименование']
        return MainProduct(Код, Наименование, ЕдИзм)

    @classmethod
    def find_by_name(cls, name: str):
        name = F.replace_forbidden_symbols_for_1c_sql(name) #27.07.25
        req_text = f"""
                        ВЫБРАТЬ ПЕРВЫЕ 1
                            Номенклатура.Код КАК Код,
                            Номенклатура.Наименование КАК Наименование,
    	                    Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмеренияНаименование
                        ИЗ
                            Справочник.Номенклатура КАК Номенклатура
                        ГДЕ
                            Номенклатура.Наименование = "{name}"
                        УПОРЯДОЧИТЬ ПО
                            Наименование
                        """
        key, data_rez = APIERP.get_wet_request(req_text, lazy_method_huours=LAZY_METHOD_HUOURS)
        if key != 200:
            raise ConnectionError(f'Ошибка получения данных Номенклатура из ERP')

        if not data_rez['data']:
            raise ValueError(f'Не найдено Номенклатура из ERP')

        Код = data_rez['data'][0]['Код']
        Наименование = data_rez['data'][0]['Наименование']
        ЕдИзм = data_rez['data'][0]['ЕдиницаИзмеренияНаименование']
        return MainProduct(Код, Наименование, ЕдИзм)

@dataclass
class Variationsrespecificationdocuments:
    name: str
    order: int | None
    ref_key: str | None

@dataclass
class TheMethodOfAllocatingTheCostOfTheOutputProducts:
    name: str
    order: int | None
    ref_key: str | None

@dataclass
class MethodOfObtainingMaterialspecifications:
    name: str
    order: int | None
    ref_key: str | None



@dataclass
class ArticulationArticles:
    name: str
    parent: str
    ref_key: str


@dataclass
class TypeOfWork:
    name: str
    code: str
    ref_key: str


class CurrentUser:
    def __init__(self, name: str):
        req_text = f"""
                ВЫБРАТЬ ПЕРВЫЕ 1
                    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Пользователи.Ссылка) КАК ref_key
                ИЗ
                    Справочник.Пользователи КАК Пользователи
                ГДЕ
                    Пользователи.Наименование = "{name}"
                """
        key, data_rez = APIERP.get_wet_request(req_text, lazy_method_huours=LAZY_METHOD_HUOURS)
        if key != 200:
            raise ConnectionError(f'Ошибка получения данных Пользователи из ERP')

        if not data_rez['data']:
            raise ValueError(f'Не найдено `{name}` из Пользователи ERP')

        self.name = name
        self.ref_key = data_rez['data'][0]['ref_key']



def ___________data____________():
    pass


def replace_for_pep(val: str) -> str:
    """
    Преобразует строку в валидное имя переменной по PEP 8.

    Параметры:
        val (str): Любая строка (например, из файла, базы данных и т. д.).

    Возвращает:
        str: Корректное имя переменной в snake_case.

    Примеры:
        >>> replace_for_pep("Ремонтный цех Производства")
        'remontnyy_ceh_proizvodstva'

        >>> replace_for_pep("123Invalid-Name!")
        '_123invalid_name'
    """
    # 1. Заменяем Unicode-символы (² → 2, ° → _ и т. д.)
    val = (
        val.strip()
        .replace("²", "2")  # Верхний индекс 2 → обычная 2
        .replace("³", "3")  # Верхний индекс 3 → обычная 3
        .replace("°", "_")  # Знак градуса → _
    )
    # Заменяем все НЕ-буквы и НЕ-цифры на "_"
    val = re.sub(r'[^\w]', '_', val.strip())

    # Удаляем повторяющиеся "_" и убираем "_" с концов
    val = re.sub(r'_+', '_', val).strip('_')

    # Если строка начинается с цифры, добавляем "_" в начало
    if val and val[0].isdigit():
        val = f"_{val}"

    # Переводим в нижний регистр
    val = val.lower()

    # Если результат — ключевое слово Python, добавляем "_" в конец
    if keyword.iskeyword(val):
        val = f"{val}_"

    # Если после всех преобразований строка пустая, возвращаем "_"
    return val or "_"

class ObjsData():
    NAME_ERP_OBJ = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.NAME_ERP_OBJ is None:
            raise TypeError(f"Класс {cls.__name__} должен переопределить NAME_ERP_OBJ")

    @classmethod
    def __find_by(cls, attr: str, attrname: str, default=ValueError):
        for k, item in cls.__dict__.items():
            if '_hnt' in k and getattr(item, attrname) == attr:
                return item
        if type(default) == type and issubclass(default, Exception): #26.08.25 (по задаче 100059257)
            raise ValueError(f'Не найдено {cls.NAME_ERP_OBJ} = `{attr}` из ERP')
        return default

    @classmethod
    def find_by_code(cls, code: str|None, default=ValueError):
        return cls.__find_by(code,'code',default)

    @classmethod
    def find_by_ref(cls, ref_key: str|None, default=ValueError):
        return cls.__find_by(ref_key, 'ref_key', default)

    @classmethod
    def find_by_name(cls, name: str|None, default=ValueError):
        return cls.__find_by(name,'name',default)

    @classmethod
    def _get_data_erp(cls, req_text: str):
        key, data_rez = APIERP.get_wet_request(req_text, lazy_method_huours=LAZY_METHOD_HUOURS)
        if key != 200:
            raise ConnectionError(f'Ошибка получения данных {NAME_ERP_OBJ} из ERP')
        if not data_rez['data']:
            raise ValueError(f'Не найдено {NAME_ERP_OBJ} из ERP')
        return data_rez['data']

    @classmethod
    def _fill_data(cls,data:list, sub_cls:type,sub_kwargs:dict ):
        name_sub_cls = sub_cls.__name__
        # Аннотации для подсказок типов (будет заполнено динамически)
        __annotations__: ClassVar[Dict[str, type]] = {}
        if FL_LOAD_PROP:
            print(f'')
            print(f'=====  свойства {name_sub_cls} ========')
        for item in data:
            prop_name = '_'.join( [str(_) for k, _ in item.items() if k not in ('ref_key')])
            prop_name = '_hnt_' + replace_for_pep(prop_name)
            kwargs = {k:item[v] for k,v in sub_kwargs.items()}
            prop_value = sub_cls(**kwargs)
            # Добавляем аннотацию типа для свойства
            SubdivisionsData.__annotations__[prop_name] = sub_cls
            # Устанавливаем значение свойства
            if FL_LOAD_PROP:
                print(f'{prop_name}: {name_sub_cls}')
            setattr(cls, prop_name, prop_value)
        if FL_LOAD_PROP:
            print(f'=====  свойства {name_sub_cls} ========')
            print(f'')
            print(f'')

    @classmethod
    def to_list(cls)->list[tuple]:
        pref = '_hnt_'
        return [(_[len(pref):], val) for _,val in cls.__dict__.items() if _.startswith(pref)]

# --- ПодразделениеДиспетчер ---

class SubdivisionsData(ObjsData):
    NAME_ERP_OBJ = 'СтруктураПредприятия'
    if 'свойства':
        pass
        _hnt_powerz_gmbh_00_000087: Subdivision
        _hnt_административно_хозяйственный_отдел_кбж_кбж_00_000153: Subdivision
        _hnt_административно_хозяйственный_отдел_келаст_управленческие_подразделения_келаст_00_000052: Subdivision
        _hnt_административно_хозяйственный_отдел_пауэрз_офис_пауэрз_00_000025: Subdivision
        _hnt_административно_хозяйственный_отдел_пкб_управленческие_подразделения_пкб_00_000019: Subdivision
        _hnt_административно_хозяйственный_отдел_таткуз_таткуз_00_000170: Subdivision
        _hnt_административно_хозяйственный_отдел_ук_хп_холдинг_пауэрз_ук_ооо_00_000174: Subdivision
        _hnt_ауп_тузукса_ъ_удалить_старое_00_000016: Subdivision
        _hnt_бухгалтерия_кбж_управленческие_подразделения_кбж_00_000111: Subdivision
        _hnt_бухгалтерия_келаст_управленческие_подразделения_келаст_00_000055: Subdivision
        _hnt_бухгалтерия_пауэрз_офис_пауэрз_00_000028: Subdivision
        _hnt_бухгалтерия_пкб_управленческие_подразделения_пкб_00_000146: Subdivision
        _hnt_бухгалтерия_таткуз_таткуз_00_000165: Subdivision
        _hnt_бухгалтерия_окбэм_пауэрз_управленческие_подразделения_окбэм_пауэрз_00_000143: Subdivision
        _hnt_дирекция_powerz_gmbh_00_000088: Subdivision
        _hnt_дирекция_кбж_кбж_00_000110: Subdivision
        _hnt_дирекция_келаст_управленческие_подразделения_келаст_00_000051: Subdivision
        _hnt_дирекция_пауэрз_офис_пауэрз_00_000024: Subdivision
        _hnt_дирекция_пкб_управленческие_подразделения_пкб_00_000018: Subdivision
        _hnt_дирекция_таткуз_таткуз_00_000167: Subdivision
        _hnt_дирекция_ук_хп_холдинг_пауэрз_ук_ооо_00_000152: Subdivision
        _hnt_дирекция_окбэм_пауэрз_управленческие_подразделения_окбэм_пауэрз_00_000107: Subdivision
        _hnt_заготовительный_цех_производства_пауэрз_производственные_подразделения_пауэрз_00_000044: Subdivision
        _hnt_кбж_00_000109: Subdivision
        _hnt_келаст_00_000050: Subdivision
        _hnt_коммерческие_подразделения_келаст_келаст_00_000127: Subdivision
        _hnt_коммерческие_подразделения_окбэм_пауэрз_окбэм_пауэрз_00_000134: Subdivision
        _hnt_конструкторский_отдел_келаст_производственные_подразделения_келаст_00_000060: Subdivision
        _hnt_конструкторский_отдел_пауэрз_производственные_подразделения_пауэрз_00_000038: Subdivision
        _hnt_конструкторский_отдел_пкб_производственные_подразделения_пкб_пауэрз_00_000020: Subdivision
        _hnt_конструкторский_отдел_таткуз_таткуз_00_000169: Subdivision
        _hnt_конструкторское_бюро_окбэм_пауэрз_производственные_подразделения_окбэм_пауэрз_00_000077: Subdivision
        _hnt_набивочный_цех_производства_келаст_цеха_келаст_00_000073: Subdivision
        _hnt_окбэм_пауэрз_00_000078: Subdivision
        _hnt_отдел_безопасности_келаст_управленческие_подразделения_келаст_00_000145: Subdivision
        _hnt_отдел_безопасности_пауэрз_офис_пауэрз_00_000144: Subdivision
        _hnt_отдел_внешнего_монтажа_и_сервиса_производства_пауэрз_офис_пауэрз_00_000048: Subdivision
        _hnt_отдел_внешнего_монтажа_производства_келаст_ъ_удалить_старое_00_000076: Subdivision
        _hnt_отдел_информационных_технологий_келаст_управленческие_подразделения_келаст_00_000057: Subdivision
        _hnt_отдел_информационных_технологий_пауэрз_офис_пауэрз_00_000030: Subdivision
        _hnt_отдел_капитального_строительства_и_ремонта_келаст_ъ_удалить_старое_00_000100: Subdivision
        _hnt_отдел_комплектации_келаст_цеха_келаст_00_000121: Subdivision
        _hnt_отдел_комплектации_пауэрз_производственные_подразделения_пауэрз_00_000119: Subdivision
        _hnt_отдел_логистики_gmbh_дирекция_00_000090: Subdivision
        _hnt_отдел_маркетинга_келаст_коммерческие_подразделения_келаст_00_000092: Subdivision
        _hnt_отдел_маркетинга_пауэрз_офис_пауэрз_00_000098: Subdivision
        _hnt_отдел_нв_пауэрз_офис_пауэрз_00_000033: Subdivision
        _hnt_отдел_охраны_труда_кбж_кбж_00_000159: Subdivision
        _hnt_отдел_охраны_труда_келаст_отдел_персонала_келаст_00_000097: Subdivision
        _hnt_отдел_охраны_труда_пауэрз_производственные_подразделения_пауэрз_00_000096: Subdivision
        _hnt_отдел_охраны_труда_таткуз_таткуз_00_000161: Subdivision
        _hnt_отдел_персонала_келаст_управленческие_подразделения_келаст_00_000054: Subdivision
        _hnt_отдел_персонала_пауэрз_офис_пауэрз_00_000027: Subdivision
        _hnt_отдел_персонала_таткуз_таткуз_00_000166: Subdivision
        _hnt_отдел_персонала_окбэм_пауэрз_управленческие_подразделения_окбэм_пауэрз_00_000108: Subdivision
        _hnt_отдел_по_управлению_качеством_пауэрз_офис_пауэрз_00_000039: Subdivision
        _hnt_отдел_продаж_келаст_коммерческие_подразделения_келаст_00_000061: Subdivision
        _hnt_отдел_продаж_пауэрз_офис_пауэрз_00_000122: Subdivision
        _hnt_отдел_продаж_таткуз_таткуз_00_000168: Subdivision
        _hnt_отдел_продаж_gmbh_дирекция_00_000091: Subdivision
        _hnt_отдел_продаж_быстросъемной_изоляции_келаст_коммерческие_подразделения_келаст_00_000062: Subdivision
        _hnt_отдел_продаж_газоочистного_оборудования_пауэрз_офис_пауэрз_00_000034: Subdivision
        _hnt_отдел_продаж_оборудования_пневмотранспорта_и_сажеобдувочных_аппаратов_пауэрз_офис_пауэрз_00_000035: Subdivision
        _hnt_отдел_проектных_продаж_окбэм_пауэрз_коммерческие_подразделения_окбэм_пауэрз_00_000101: Subdivision
        _hnt_отдел_складской_логистики_кбж_кбж_00_000156: Subdivision
        _hnt_отдел_складской_логистики_келаст_производственные_подразделения_келаст_00_000105: Subdivision
        _hnt_отдел_складской_логистики_пауэрз_производственные_подразделения_пауэрз_00_000103: Subdivision
        _hnt_отдел_складской_логистики_таткуз_таткуз_00_000172: Subdivision
        _hnt_отдел_снабжения_кбж_кбж_00_000158: Subdivision
        _hnt_отдел_снабжения_келаст_управленческие_подразделения_келаст_00_000058: Subdivision
        _hnt_отдел_снабжения_пауэрз_офис_пауэрз_00_000031: Subdivision
        _hnt_отдел_снабжения_таткуз_таткуз_00_000171: Subdivision
        _hnt_отдел_технического_контроля_келаст_производственные_подразделения_келаст_00_000075: Subdivision
        _hnt_отдел_технического_контроля_таткуз_таткуз_00_000173: Subdivision
        _hnt_отдел_технического_контроля_производства_пауэрз_производственные_подразделения_пауэрз_00_000047: Subdivision
        _hnt_отдел_транспортной_логистики_кбж_кбж_00_000154: Subdivision
        _hnt_отдел_транспортной_логистики_келаст_производственные_подразделения_келаст_00_000106: Subdivision
        _hnt_отдел_транспортной_логистики_пауэрз_производственные_подразделения_пауэрз_00_000104: Subdivision
        _hnt_отдел_транспортной_логистики_таткуз_таткуз_00_000162: Subdivision
        _hnt_отдел_управления_качеством_келаст_управленческие_подразделения_келаст_00_000059: Subdivision
        _hnt_отдел_управления_производства_кбж_кбж_00_000155: Subdivision
        _hnt_отдел_управления_производства_келаст_производственные_подразделения_келаст_00_000067: Subdivision
        _hnt_отдел_управления_производства_пауэрз_производственные_подразделения_пауэрз_00_000043: Subdivision
        _hnt_отдел_управления_производства_таткуз_таткуз_00_000163: Subdivision
        _hnt_отдел_экспорта_келаст_коммерческие_подразделения_келаст_00_000063: Subdivision
        _hnt_отдел_экспорта_пауэрз_офис_пауэрз_00_000032: Subdivision
        _hnt_отдел_экспорта_gmbh_дирекция_00_000089: Subdivision
        _hnt_офис_пауэрз_пауэрз_00_000124: Subdivision
        _hnt_пауэрз_00_000023: Subdivision
        _hnt_пкб_пауэрз_00_000022: Subdivision
        _hnt_планово_диспетчерский_отдел_производства_келаст_производственные_подразделения_келаст_00_000112: Subdivision
        _hnt_планово_диспетчерский_отдел_производства_пауэрз_производственные_подразделения_пауэрз_00_000049: Subdivision
        _hnt_проектный_отдел_пкб_производственные_подразделения_пкб_пауэрз_00_000021: Subdivision
        _hnt_производственные_подразделения_келаст_келаст_00_000129: Subdivision
        _hnt_производственные_подразделения_окбэм_пауэрз_окбэм_пауэрз_00_000136: Subdivision
        _hnt_производственные_подразделения_пауэрз_пауэрз_00_000125: Subdivision
        _hnt_производственные_подразделения_пкб_пауэрз_пкб_пауэрз_00_000133: Subdivision
        _hnt_ремонтный_цех_производства_келаст_производственные_подразделения_келаст_00_000120: Subdivision
        _hnt_ремонтный_цех_производства_пауэрз_производственные_подразделения_пауэрз_00_000094: Subdivision
        _hnt_сборочный_цех_производства_келаст_цеха_келаст_00_000148: Subdivision
        _hnt_сборочный_цех_производства_пауэрз_производственные_подразделения_пауэрз_00_000046: Subdivision
        _hnt_сталелитейный_цех_кбж_кбж_00_000157: Subdivision
        _hnt_сталелитейный_цех_таткуз_таткуз_00_000164: Subdivision
        _hnt_столярный_цех_производства_келаст_цеха_келаст_00_000074: Subdivision
        _hnt_таткуз_00_000160: Subdivision
        _hnt_технологический_отдел_производства_келаст_производственные_подразделения_келаст_00_000147: Subdivision
        _hnt_технологический_отдел_производства_пауэрз_производственные_подразделения_пауэрз_00_000102: Subdivision
        _hnt_управленческие_подразделения_кбж_кбж_00_000132: Subdivision
        _hnt_управленческие_подразделения_келаст_келаст_00_000128: Subdivision
        _hnt_управленческие_подразделения_окбэм_пауэрз_окбэм_пауэрз_00_000135: Subdivision
        _hnt_управленческие_подразделения_пкб_пкб_пауэрз_00_000131: Subdivision
        _hnt_финансово_экономический_отдел_келаст_управленческие_подразделения_келаст_00_000053: Subdivision
        _hnt_финансово_экономический_отдел_пауэрз_офис_пауэрз_00_000026: Subdivision
        _hnt_холдинг_пауэрз_ук_ооо_00_000151: Subdivision
        _hnt_цех_выпуска_готовой_продукции_производства_пауэрз_производственные_подразделения_пауэрз_00_000093: Subdivision
        _hnt_цех_гибких_вставок_производства_келаст_цеха_келаст_00_000150: Subdivision
        _hnt_цех_механической_обработки_производства_пауэрз_производственные_подразделения_пауэрз_00_000045: Subdivision
        _hnt_цеха_келаст_келаст_00_000130: Subdivision
        _hnt_цеха_пауэрз_ъ_удалить_старое_00_000042: Subdivision
        _hnt_швейный_цех_производства_келаст_цеха_келаст_00_000149: Subdivision
        _hnt_ъ_удалить_старое_00_000126: Subdivision
        _hnt_юридический_отдел_келаст_управленческие_подразделения_келаст_00_000056: Subdivision
        _hnt_юридический_отдел_пауэрз_офис_пауэрз_00_000029: Subdivision

    @classmethod
    def init_data(cls):
        СтруктураПредприятияНаименование = CFG.Config.place.Имя
        postfix = ''
        if СтруктураПредприятияНаименование:
            postfix = f'И СтруктураПредприятия.Наименование = "{СтруктураПредприятияНаименование}"'
        req_text = f"""
            ВЫБРАТЬ
        СтруктураПредприятия.Наименование КАК Наименование,
        СтруктураПредприятия.Родитель.Представление КАК РодительПредставление,
        СтруктураПредприятия.Код КАК Код
    ИЗ
        Справочник.СтруктураПредприятия КАК СтруктураПредприятия
    ГДЕ
        СтруктураПредприятия.ПометкаУдаления = ЛОЖЬ
        И СтруктураПредприятия.Родитель.Ссылка В ИЕРАРХИИ            (ВЫБРАТЬ ПЕРВЫЕ 1
                СтруктураПредприятия.Ссылка КАК Ссылка
            ИЗ
                Справочник.СтруктураПредприятия КАК СтруктураПредприятия
            ГДЕ
                СтруктураПредприятия.ПометкаУдаления = ЛОЖЬ
                {postfix}) 
    УПОРЯДОЧИТЬ ПО
        Наименование
        """

        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp,Subdivision,{'name':'Наименование','code':'Код'})


class GroupResData(ObjsData):
    NAME_ERP_OBJ = 'РесурсныеСпецификации'
    if 'свойства':
        pass
        _hnt_кзтт_стандарт_бси_кзх_00_053346: GroupRes
        _hnt_кзх_стандарт_бси_кзх_00_052294: GroupRes
        _hnt_бит_пауэрз_00_020880: GroupRes
        _hnt_пф_для_втулка_нажимная_сб_из_сырья_пф_производимые_в_процессе_00_020886: GroupRes
        _hnt_пф_для_клапана_из_сырья_пф_производимые_в_процессе_00_020882: GroupRes
        _hnt_пф_для_корпуса_из_сырья_пф_производимые_в_процессе_00_020883: GroupRes
        _hnt_пф_для_корпуса_уплотнения_сб_из_сырья_пф_производимые_в_процессе_00_020885: GroupRes
        _hnt_пф_для_створки_в_сборе_сб_из_сырья_пф_производимые_в_процессе_00_020884: GroupRes
        _hnt_пф_для_стрелки_в_сборе_сб_из_сырья_пф_производимые_в_процессе_00_020887: GroupRes
        _hnt_пф_для_швеллера_в_сборе_сб_из_сырья_пф_производимые_в_процессе_00_020888: GroupRes
        _hnt_пф_производимые_в_процессе_бит_00_020881: GroupRes
        _hnt__01_169_20_205_вс_обшивка_барабана_кмд_2503241_00_061844: GroupRes
        _hnt__02_169_20_206_вс_обшивка_расширителей_продувок_кмд_2503241_00_061886: GroupRes
        _hnt__03_169_20_207_вс_обшивка_теплого_ящика_кмд_2503241_00_061852: GroupRes
        _hnt__04_169_20_208_вс_кмд_2503241_00_062007: GroupRes
        _hnt__05_169_20_209_вс_детали_крепления_изоляции_теплого_ящика_кмд_2503241_00_061892: GroupRes
        _hnt__06_169_20_377_вс_детали_крепления_декоративной_обшивки_котла_и_твп_кмд_2503241_00_061916: GroupRes
        _hnt__07_169_20_385_вс_детали_декоративной_обшивки_горелок_и_сопел_кмд_2503241_00_062005: GroupRes
        _hnt__08_169_20_371_вс_эл_ты_крепления_обшивки_пылепроводов_кмд_2503241_00_061993: GroupRes
        _hnt__09_169_20_0925_вс_кмд_2503241_00_062009: GroupRes
        _hnt__10_169_20_331_вс_обшивка_мельниц_кмд_2503241_00_062008: GroupRes
        _hnt__1512122_перепродажа_системы_сухого_золоудаления_и_ком_ты_00_022255: GroupRes
        _hnt__2102107_покупные_проект_2102107_рудный_00_015401: GroupRes
        _hnt__2102107_производство_пауэрз_проект_2102107_рудный_00_015456: GroupRes
        _hnt_d100_гибкие_вставки_00_033561: GroupRes
        _hnt_d1000_гибкие_вставки_00_033588: GroupRes
        _hnt_d1120_гибкие_вставки_00_033593: GroupRes
        _hnt_d125_гибкие_вставки_00_033566: GroupRes
        _hnt_d1250_гибкие_вставки_00_033598: GroupRes
        _hnt_d1400_гибкие_вставки_00_033606: GroupRes
        _hnt_d160_гибкие_вставки_00_033571: GroupRes
        _hnt_d1600_гибкие_вставки_00_033614: GroupRes
        _hnt_d1800_гибкие_вставки_00_033620: GroupRes
        _hnt_d200_гибкие_вставки_00_033576: GroupRes
        _hnt_d2000_гибкие_вставки_00_033626: GroupRes
        _hnt_d225_гибкие_вставки_00_033342: GroupRes
        _hnt_d250_гибкие_вставки_00_033324: GroupRes
        _hnt_d280_гибкие_вставки_00_033310: GroupRes
        _hnt_d315_гибкие_вставки_00_033297: GroupRes
        _hnt_d355_гибкие_вставки_00_033283: GroupRes
        _hnt_d400_гибкие_вставки_00_033262: GroupRes
        _hnt_d450_гибкие_вставки_00_033242: GroupRes
        _hnt_d500_гибкие_вставки_00_033113: GroupRes
        _hnt_d560_гибкие_вставки_00_033212: GroupRes
        _hnt_d630_гибкие_вставки_00_033142: GroupRes
        _hnt_d710_гибкие_вставки_00_033139: GroupRes
        _hnt_d800_гибкие_вставки_00_033121: GroupRes
        _hnt_d900_гибкие_вставки_00_033583: GroupRes
        _hnt_аппарат_обдувки_перепродажа_аппараты_обдувки_00_045406: GroupRes
        _hnt_аппараты_обдувки_пауэрз_00_002090: GroupRes
        _hnt_бси_ресурсные_план_келаст_00_048708: GroupRes
        _hnt_бси_изоляция_рукавов_келаст_00_010279: GroupRes
        _hnt_бси_кзх_келаст_00_010280: GroupRes
        _hnt_бси_кип_келаст_00_010281: GroupRes
        _hnt_бси_палеты_келаст_00_010282: GroupRes
        _hnt_бси_рукава_келаст_00_010283: GroupRes
        _hnt_быстросъемная_изоляция_келаст_00_002087: GroupRes
        _hnt_газоходы_пауэрз_00_010290: GroupRes
        _hnt_газоходы_перепродажа_газоходы_00_046750: GroupRes
        _hnt_гибкие_вставки_келаст_00_032627: GroupRes
        _hnt_горелки_пауэрз_00_007550: GroupRes
        _hnt_детали_тара_и_упаковка_00_042543: GroupRes
        _hnt_закрытые_лента_для_гибких_вставок_00_047826: GroupRes
        _hnt_закрытые_рс_ао_аппараты_обдувки_00_060930: GroupRes
        _hnt_закрытые_рс_по_газоходам_газоходы_00_060933: GroupRes
        _hnt_закрытые_рс_по_горелкам_горелки_00_060934: GroupRes
        _hnt_закрытые_рс_по_клапанам_клапаны_00_060936: GroupRes
        _hnt_закрытые_рс_ссзу_системы_сухого_золоудаления_и_ком_ты_00_061184: GroupRes
        _hnt_испытания_келаст_00_051029: GroupRes
        _hnt_испытательный_цех_пауэрз_00_036776: GroupRes
        _hnt_клапаны_пауэрз_00_002091: GroupRes
        _hnt_кмд_системы_газоочистки_и_компоненты_00_022296: GroupRes
        _hnt_кмд_2503241_прочая_продукция_кмд_00_061843: GroupRes
        _hnt_компенсатор_композитный_келаст_00_034758: GroupRes
        _hnt_компенсатор_тканевый_келаст_00_002086: GroupRes
        _hnt_комплект_для_замыкания_келаст_00_047759: GroupRes
        _hnt_компоненты_систем_производимые_у_нас_системы_сухого_золоудаления_и_ком_ты_00_002628: GroupRes
        _hnt_коронки_рудтех_продакшн_00_005077: GroupRes
        _hnt_кт_ресурсные_план_келаст_00_053775: GroupRes
        _hnt_кт_ресурсные_ткп_келаст_00_059278: GroupRes
        _hnt_лента_для_гибких_вставок_келаст_00_031008: GroupRes
        _hnt_линзовые_компенсаторы_пауэрз_00_002092: GroupRes
        _hnt_литье_таткуз_00_058862: GroupRes
        _hnt_металлические_части_компенсаторов_для_ткп_металлоизделия_00_010876: GroupRes
        _hnt_металлоизделия_пауэрз_00_002093: GroupRes
        _hnt_модельная_оснастка_таткуз_келаст_00_057989: GroupRes
        _hnt_модельная_оснастка_таткуз_ремонт_келаст_00_060626: GroupRes
        _hnt_модельная_оснастка_таткуз_ткп_келаст_00_059339: GroupRes
        _hnt_монтаж_шефмонтаж_испытания_работы_не_редактировать_00_046090: GroupRes
        _hnt_не_использовать_работы_не_редактировать_00_002675: GroupRes
        _hnt_нзп_незавершенное_производство_келаст_00_056204: GroupRes
        _hnt_опоры_шпс_по_проектам_тара_и_упаковка_00_020732: GroupRes
        _hnt_павлова_пауэрз_00_022411: GroupRes
        _hnt_пауэрз_00_002084: GroupRes
        _hnt_пвс_1906147_производство_пауэрз_проект_пвс_1906147_00_012949: GroupRes
        _hnt_пвс_1906148_покупные_проект_пвс_1906148_00_015105: GroupRes
        _hnt_пвс_1906148_производство_пауэрз_проект_пвс_1906148_00_015106: GroupRes
        _hnt_пвс1906147_покупные_проект_пвс_1906147_00_012950: GroupRes
        _hnt_пкб_пауэрз_00_010488: GroupRes
        _hnt_поддоны_по_проектам_тара_и_упаковка_00_020733: GroupRes
        _hnt_поддоны_обычные_упаковка_типовая_00_020662: GroupRes
        _hnt_поддоны_усиленные_упаковка_типовая_00_020362: GroupRes
        _hnt_предварительные_рс_лента_для_гибких_вставок_00_059138: GroupRes
        _hnt_предварительные_рс_для_ссзу_системы_сухого_золоудаления_и_ком_ты_00_063434: GroupRes
        _hnt_предварительные_рс_на_аппараты_обдувки_для_ткп_аппараты_обдувки_00_007676: GroupRes
        _hnt_предварительные_рс_на_горелки_для_ткп_горелки_00_008119: GroupRes
        _hnt_предварительные_рс_на_клапаны_для_ткп_клапаны_00_007579: GroupRes
        _hnt_предварительные_рс_на_линзовые_компенсаторы_для_ткп_линзовые_компенсаторы_00_007677: GroupRes
        _hnt_предварительные_рс_на_шумоглушители_для_ткп_шумоглушители_00_007678: GroupRes
        _hnt_проект_2102107_рудный_системы_газоочистки_и_компоненты_00_015400: GroupRes
        _hnt_проект_пвс_1906147_системы_газоочистки_и_компоненты_00_012948: GroupRes
        _hnt_проект_пвс_1906148_системы_газоочистки_и_компоненты_00_015104: GroupRes
        _hnt_проектирование_пкб_пауэрз_00_010491: GroupRes
        _hnt_проектно_конструкторские_работы_работы_не_редактировать_00_040508: GroupRes
        _hnt_прочая_продукция_кмд_пауэрз_00_061842: GroupRes
        _hnt_прочая_продукция_келаста_келаст_00_002089: GroupRes
        _hnt_прочая_продукция_пауэрза_пауэрз_00_002096: GroupRes
        _hnt_работы_не_редактировать_00_002085: GroupRes
        _hnt_разборка_келаст_00_049368: GroupRes
        _hnt_разработка_аппаратов_обдувки_пкб_пауэрз_00_013039: GroupRes
        _hnt_разработка_горелок_пкб_пауэрз_00_010490: GroupRes
        _hnt_разработка_клапанов_пкб_пауэрз_00_010489: GroupRes
        _hnt_разработка_линзовых_компенсаторов_пкб_пауэрз_00_011704: GroupRes
        _hnt_разработка_проектной_и_рабочей_документации_работы_не_редактировать_00_016290: GroupRes
        _hnt_разработка_ркд_для_тканевый_компенсатор_келаст_00_040500: GroupRes
        _hnt_рем_комплект_келаст_00_047758: GroupRes
        _hnt_ремонт_келаст_00_047990: GroupRes
        _hnt_рудтех_продакшн_00_005076: GroupRes
        _hnt_рукавные_фильтры_системы_газоочистки_и_компоненты_00_058974: GroupRes
        _hnt_рукавные_фильтры_келаст_00_056181: GroupRes
        _hnt_рф_0_2411214_системы_газоочистки_и_компоненты_00_059411: GroupRes
        _hnt_системы_газоочистки_и_компоненты_пауэрз_00_010294: GroupRes
        _hnt_системы_сухого_золоудаления_и_ком_ты_пауэрз_00_002094: GroupRes
        _hnt_состовляющие_ящиков_упаковка_типовая_00_055832: GroupRes
        _hnt_ссзу_плановые_ресурсные_системы_сухого_золоудаления_и_ком_ты_00_010728: GroupRes
        _hnt_стенки_боковые_состовляющие_ящиков_00_055836: GroupRes
        _hnt_стенки_торцевые_состовляющие_ящиков_00_055835: GroupRes
        _hnt_тара_и_упаковка_келаст_00_002088: GroupRes
        _hnt_таткуз_00_058861: GroupRes
        _hnt_тестовые_рс_прочая_продукция_келаста_00_060213: GroupRes
        _hnt_технологическая_оснастка_келаст_00_055210: GroupRes
        _hnt_тканевый_компенсатор_кт_1507046_02_00_компенсатор_тканевый_00_048240: GroupRes
        _hnt_тканевый_компенсатор_кт_1507046_02_00_тест_компенсатор_тканевый_00_052219: GroupRes
        _hnt_упаковка_типовая_тара_и_упаковка_00_017175: GroupRes
        _hnt_ценообразование_00_050866: GroupRes
        _hnt_шумоглушители_пауэрз_00_002095: GroupRes
        _hnt_ящики_упаковка_типовая_00_020363: GroupRes
        _hnt_ящики_на_обычных_поддонах_упаковка_типовая_00_055831: GroupRes
        _hnt_ящики_на_усиленных_поддонах_упаковка_типовая_00_060430: GroupRes

    @classmethod
    def init_data(cls):
        req_text = f"""
            ВЫБРАТЬ
                РесурсныеСпецификации.Наименование КАК Наименование,
                РесурсныеСпецификации.Родитель.Представление КАК РодительПредставление,
                РесурсныеСпецификации.Код КАК Код
            ИЗ
                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
            ГДЕ
                РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
                И РесурсныеСпецификации.ЭтоГруппа = ИСТИНА
            
            УПОРЯДОЧИТЬ ПО
                Наименование
            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, Subdivision, {'name': 'Наименование', 'code': 'Код'})




class VariationsrespecificationdocumentsData(ObjsData):
    NAME_ERP_OBJ = 'ВариантыПодбораСпецификацииВДокументы'
    if 'свойства':
        pass
        _hnt_автоматически_по_приоритету_0: Variationsrespecificationdocuments
        _hnt_вручную_1: Variationsrespecificationdocuments

    @classmethod
    def init_data(cls):
        req_text = f"""
            ВЫБРАТЬ
    ПРЕДСТАВЛЕНИЕ(ВариантыПодбораСпецификацииВДокументы.Ссылка) КАК Наименование,
    ВариантыПодбораСпецификацииВДокументы.Порядок КАК Порядок,
	УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВариантыПодбораСпецификацииВДокументы.Ссылка) КАК ref_key
ИЗ
    Перечисление.ВариантыПодбораСпецификацииВДокументы КАК ВариантыПодбораСпецификацииВДокументы

            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, Variationsrespecificationdocuments, {'name': 'Наименование', 'order': 'Порядок', 'ref_key': 'ref_key'})



class TheMethodOfAllocatingTheCostOfTheOutputProductsData(ObjsData):
    NAME_ERP_OBJ = 'СпособыРаспределенияЗатратНаВыходныеИзделия'
    if 'свойства':
        pass
        _hnt_по_долям_стоимости_0: TheMethodOfAllocatingTheCostOfTheOutputProducts
        _hnt_по_плановой_стоимости_1: TheMethodOfAllocatingTheCostOfTheOutputProducts
        _hnt_по_весу_2: TheMethodOfAllocatingTheCostOfTheOutputProducts
        _hnt_по_объему_3: TheMethodOfAllocatingTheCostOfTheOutputProducts
        _hnt_по_количеству_4: TheMethodOfAllocatingTheCostOfTheOutputProducts

    @classmethod
    def init_data(cls):
        req_text = f"""
            ВЫБРАТЬ
    ПРЕДСТАВЛЕНИЕ(СпособыРаспределенияЗатратНаВыходныеИзделия.Ссылка) КАК Наименование,
    СпособыРаспределенияЗатратНаВыходныеИзделия.Порядок КАК Порядок,
	УНИКАЛЬНЫЙИДЕНТИФИКАТОР(СпособыРаспределенияЗатратНаВыходныеИзделия.Ссылка) КАК ref_key
ИЗ
    Перечисление.СпособыРаспределенияЗатратНаВыходныеИзделия КАК СпособыРаспределенияЗатратНаВыходныеИзделия

            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, TheMethodOfAllocatingTheCostOfTheOutputProducts, {'name': 'Наименование', 'order': 'Порядок', 'ref_key': 'ref_key'})





class MethodOfObtainingMaterialspecificationsData(ObjsData):
    NAME_ERP_OBJ = 'СпособыПолученияМатериаловВСпецификации'
    if 'свойства':
        pass
        _hnt_обеспечивать_0: MethodOfObtainingMaterialspecifications
        _hnt_произвести_по_спецификации_1: MethodOfObtainingMaterialspecifications
        _hnt_производится_на_этапе_2: MethodOfObtainingMaterialspecifications

    @classmethod
    def init_data(cls):
        req_text = f"""
            ВЫБРАТЬ
    ПРЕДСТАВЛЕНИЕ(СпособыПолученияМатериаловВСпецификации.Ссылка) КАК Наименование,
    СпособыПолученияМатериаловВСпецификации.Порядок КАК Порядок,
	УНИКАЛЬНЫЙИДЕНТИФИКАТОР(СпособыПолученияМатериаловВСпецификации.Ссылка) КАК ref_key
ИЗ
    Перечисление.СпособыПолученияМатериаловВСпецификации КАК СпособыПолученияМатериаловВСпецификации

            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, MethodOfObtainingMaterialspecifications, {'name': 'Наименование', 'order': 'Порядок', 'ref_key': 'ref_key'})





class TypeOfWorkData(ObjsData):
    NAME_ERP_OBJ = 'ВидыРаботСотрудников'
    if 'свойства':
        pass
        _hnt_не_используются_00_000019: TypeOfWork
        _hnt__2_16_9033_сварка_00_000058_пауэрз: TypeOfWork
        _hnt__2_22_4110_токарная_00_000056_пауэрз: TypeOfWork
        _hnt__2_8_9171_лазерная_резка_00_000057_пауэрз: TypeOfWork
        _hnt_гибка_устранение_недочётов_пауэрз_00_000023_устранение_недочётов: TypeOfWork
        _hnt_гибка_пауэрз_00_000021_пауэрз: TypeOfWork
        _hnt_гибка_металла_00_000079_новые_виды_работ: TypeOfWork
        _hnt_гравировка_келаст_00_000020_келаст: TypeOfWork
        _hnt_гравировка_пауэрз_00_000053_пауэрз: TypeOfWork
        _hnt_долбежка_пауэрз_00_000049_пауэрз: TypeOfWork
        _hnt_зачистка_устранение_недочётов_пауэрз_00_000024_устранение_недочётов: TypeOfWork
        _hnt_зачистка_пауэрз_00_000008_пауэрз: TypeOfWork
        _hnt_зачистка_поверхностей_00_000063_новые_виды_работ: TypeOfWork
        _hnt_изготовление_бси_набивка_1_разряда_келаст_00_000107_келаст: TypeOfWork
        _hnt_изготовление_бси_набивка_2_разряда_келаст_00_000108_келаст: TypeOfWork
        _hnt_изготовление_бси_1_разряда_келаст_00_000001_келаст: TypeOfWork
        _hnt_изготовление_бси_2_разряда_келаст_00_000097_келаст: TypeOfWork
        _hnt_изготовление_бси_3_разряда_келаст_00_000098_келаст: TypeOfWork
        _hnt_изготовление_бси_4_разряда_келаст_00_000099_келаст: TypeOfWork
        _hnt_изготовление_вкладыша_келаст_00_000002_келаст: TypeOfWork
        _hnt_изготовление_кт_келаст_00_000003_келаст: TypeOfWork
        _hnt_изготовление_кт_1_разряда_келаст_00_000100_келаст: TypeOfWork
        _hnt_изготовление_кт_2_разряда_келаст_00_000101_келаст: TypeOfWork
        _hnt_изготовление_кт_3_разряда_келаст_00_000102_келаст: TypeOfWork
        _hnt_изготовление_опор_и_подушек_келаст_00_000014_келаст: TypeOfWork
        _hnt_изготовление_тары_и_форм_2_разряда_келаст_00_000015_келаст: TypeOfWork
        _hnt_инженерно_конструкторские_работы_00_000083_келаст: TypeOfWork
        _hnt_инженерно_конструкторские_работы_2_категории_00_000084_келаст: TypeOfWork
        _hnt_инженерно_конструкторские_работы_3_категории_00_000085_келаст: TypeOfWork
        _hnt_келаст_00_000012: TypeOfWork
        _hnt_комплектование_зип_устранение_недочётов_пауэрз_00_000025_устранение_недочётов: TypeOfWork
        _hnt_комплектование_зип_пауэрз_00_000018_пауэрз: TypeOfWork
        _hnt_комплектовка_и_упаковка_келаст_00_000037_келаст: TypeOfWork
        _hnt_комплектовка_и_упаковка_1_категории_келаст_00_000103_келаст: TypeOfWork
        _hnt_комплектовка_и_упаковка_2_категории_келаст_00_000104_келаст: TypeOfWork
        _hnt_конструкторская_разработка_горелок_пкб_00_000040_пкб_пауэрз: TypeOfWork
        _hnt_конструкторская_разработка_горелок_пкб_00_000041_конструкторская_разработка_горелок_пкб: TypeOfWork
        _hnt_конструкторская_разработка_клапанов_пкб_00_000035_пкб_пауэрз: TypeOfWork
        _hnt_конструкторская_разработка_клапанов_пкб_00_000036_конструкторская_разработка_клапанов_пкб: TypeOfWork
        _hnt_конструкторская_разработка_линзовых_компенсаторов_пкб_00_000044_пкб_пауэрз: TypeOfWork
        _hnt_конструкторская_разработка_линзовых_компенсаторов_пкб_00_000045_конструкторская_разработка_линзовых_компенсаторов_пкб: TypeOfWork
        _hnt_лазерная_резка_устранение_недочётов_пауэрз_00_000026_устранение_недочётов: TypeOfWork
        _hnt_лазерная_резка_пауэрз_00_000005_пауэрз: TypeOfWork
        _hnt_литье_00_000096_таткуз: TypeOfWork
        _hnt_малярные_работы_00_000064_новые_виды_работ: TypeOfWork
        _hnt_монтажные_работы_3_разряда_келаст_00_000013_келаст: TypeOfWork
        _hnt_монтажные_работы_4_разряда_келаст_00_000105_келаст: TypeOfWork
        _hnt_новые_виды_работ_00_000060: TypeOfWork
        _hnt_обработка_на_токарно_карусельных_станках_00_000067_новые_виды_работ: TypeOfWork
        _hnt_окбэм_пауэрз_00_000089: TypeOfWork
        _hnt_окрашивание_пауэрз_00_000009_пауэрз: TypeOfWork
        _hnt_пауэрз_00_000011: TypeOfWork
        _hnt_перфорация_пауэрз_00_000051_пауэрз: TypeOfWork
        _hnt_пескоструйка_пауэрз_00_000050_пауэрз: TypeOfWork
        _hnt_пкб_пауэрз_00_000033: TypeOfWork
        _hnt_подготовка_к_малярным_работам_00_000081_новые_виды_работ: TypeOfWork
        _hnt_подготовка_поверхности_00_000080_новые_виды_работ: TypeOfWork
        _hnt_покраска_устранение_недочётов_пауэрз_00_000027_устранение_недочётов: TypeOfWork
        _hnt_проектирование_пкб_пауэрз_00_000032_проектирование_пкб_пауэрз: TypeOfWork
        _hnt_проектирование_пкб_пауэрз_00_000034_пкб_пауэрз: TypeOfWork
        _hnt_разработка_проекта_аппараты_обдувки_пауэрз_00_000111_пауэрз: TypeOfWork
        _hnt_разработка_проектной_и_рабочей_документации_окбэм_пауэрз_00_000090_окбэм_пауэрз: TypeOfWork
        _hnt_разработка_ркд_келаст_00_000031_келаст: TypeOfWork
        _hnt_разработка_ркд_пауэрз_00_000030_пауэрз: TypeOfWork
        _hnt_разработка_ркд_аппараты_обдувки_пкб_пауэрз_00_000042_пкб_пауэрз: TypeOfWork
        _hnt_разработка_ркд_аппараты_обдувки_пкб_пауэрз_00_000043_разработка_ркд_аппараты_обдувки_пкб_пауэрз: TypeOfWork
        _hnt_раскрой_1_разряда_келаст_00_000016_келаст: TypeOfWork
        _hnt_раскрой_2_разряда_келаст_00_000106_келаст: TypeOfWork
        _hnt_раскрой_оператор_фрезерного_станка_чпу_келаст_00_000091_келаст: TypeOfWork
        _hnt_резание_00_000061_новые_виды_работ: TypeOfWork
        _hnt_резка_пауэрз_00_000047_пауэрз: TypeOfWork
        _hnt_ремонтные_работы_келаст_00_000010_келаст: TypeOfWork
        _hnt_рубка_пауэрз_00_000052_пауэрз: TypeOfWork
        _hnt_сборка_сварка_устранение_недочётов_пауэрз_00_000028_устранение_недочётов: TypeOfWork
        _hnt_сборка_сварка_пауэрз_00_000007_пауэрз: TypeOfWork
        _hnt_сварочные_работы_келаст_00_000109_келаст: TypeOfWork
        _hnt_сварочные_работы_4_разряд_00_000072_новые_виды_работ: TypeOfWork
        _hnt_сварочные_работы_5_разряд_00_000076_новые_виды_работ: TypeOfWork
        _hnt_сварочные_работы_6_разряд_00_000077_новые_виды_работ: TypeOfWork
        _hnt_сверловка_пауэрз_00_000048_пауэрз: TypeOfWork
        _hnt_слесарно_сборочные_работы_00_000082_новые_виды_работ: TypeOfWork
        _hnt_слесарно_сборочные_работы_1_разряд_00_000073_новые_виды_работ: TypeOfWork
        _hnt_слесарно_сборочные_работы_2_разряд_00_000066_новые_виды_работ: TypeOfWork
        _hnt_слесарно_сборочные_работы_3_разряд_00_000075_новые_виды_работ: TypeOfWork
        _hnt_слесарь_00_000059_келаст: TypeOfWork
        _hnt_слксарно_сборочные_работы_вг_келаст_00_000110_келаст: TypeOfWork
        _hnt_таткуз_00_000092: TypeOfWork
        _hnt_токарка_фрезеровка_устранение_недочётов_пауэрз_00_000029_устранение_недочётов: TypeOfWork
        _hnt_токарка_фрезеровка_пауэрз_00_000017_пауэрз: TypeOfWork
        _hnt_токарная_обработка_00_000068_новые_виды_работ: TypeOfWork
        _hnt_токарная_обработка_расточка_00_000078_новые_виды_работ: TypeOfWork
        _hnt_точение_пауэрз_00_000055_пауэрз: TypeOfWork
        _hnt_упаковка_00_000088_новые_виды_работ: TypeOfWork
        _hnt_упаковка_пауэрз_00_000038_новые_виды_работ: TypeOfWork
        _hnt_упаковывание_00_000069_новые_виды_работ: TypeOfWork
        _hnt_устранение_недочётов_00_000022_пауэрз: TypeOfWork
        _hnt_формовка_00_000094_таткуз: TypeOfWork
        _hnt_фрезерование_00_000070_новые_виды_работ: TypeOfWork
        _hnt_фрезеровка_пауэрз_00_000054_пауэрз: TypeOfWork
        _hnt_футерование_печи_00_000093_таткуз: TypeOfWork
        _hnt_шеф_инженерные_работы_пауэрз_00_000086_новые_виды_работ: TypeOfWork

    @classmethod
    def init_data(cls):
        req_text = f"""
        ВЫБРАТЬ
            
            ВидыРаботСотрудников.Наименование КАК Наименование,
            ВидыРаботСотрудников.Код КАК Код,
            ВидыРаботСотрудников.Родитель.Представление КАК Родитель,
            УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыРаботСотрудников.Ссылка) КАК ref_key
        ИЗ
            Справочник.ВидыРаботСотрудников КАК ВидыРаботСотрудников
        ГДЕ
            ВидыРаботСотрудников.ПометкаУдаления = ЛОЖЬ

        УПОРЯДОЧИТЬ ПО
            Наименование
        """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, TypeOfWork, {'name': 'Наименование', 'code': 'Код', 'ref_key': 'ref_key'})




class ArticulationArticlesData(ObjsData):
    NAME_ERP_OBJ = 'СтатьиКалькуляции'
    if 'свойства':
        pass
        _hnt_основной_фот: ArticulationArticles
        _hnt_общепроизводственные_расходы: ArticulationArticles
        _hnt_материалы_прочие: ArticulationArticles
        _hnt_общехозяйственные_расходы: ArticulationArticles
        _hnt_услуги_текущего_ремонта: ArticulationArticles
        _hnt_транспортные_расходы_по_доставке: ArticulationArticles
        _hnt_материалы_дополнительные_производство: ArticulationArticles
        _hnt_материалы_основные_производство: ArticulationArticles
        _hnt_разработка_проектной_документации_производство: ArticulationArticles
        _hnt_услуги_переработчика_производство: ArticulationArticles
        _hnt_ремонтируемые_изделия_производство: ArticulationArticles
        _hnt_разбираемые_изделия_производство: ArticulationArticles
        _hnt_изготовление_комплектующих_производство: ArticulationArticles
        _hnt_качество_резки_материалы_невозвратные: ArticulationArticles
        _hnt_качество_гибки_материалы_невозвратные: ArticulationArticles
        _hnt_человеческий_фактор_материалы_невозвратные: ArticulationArticles
        _hnt_ошибка_при_сборке_материалы_невозвратные: ArticulationArticles
        _hnt_потеря_заготовок_материалы_невозвратные: ArticulationArticles
        _hnt_ошибки_документации_кд_материалы_невозвратные: ArticulationArticles
        _hnt_изменение_кд_доработка: ArticulationArticles
        _hnt_брак_резка_доработка: ArticulationArticles
        _hnt_брак_гибка_доработка: ArticulationArticles
        _hnt_недорез_приостановленного_проекта_доработка: ArticulationArticles
        _hnt_ошибка_csv_доработка: ArticulationArticles
        _hnt_утеря_доработка: ArticulationArticles
        _hnt_брак_сварка_доработка: ArticulationArticles
        _hnt_технологические_доработки_доработка: ArticulationArticles
        _hnt_брак_вальцовка_доработка: ArticulationArticles
        _hnt_ошибка_кд_доработка: ArticulationArticles
        _hnt_затраты_на_сырье_или_материалы_статьи_калькуляций_новые: ArticulationArticles
        _hnt_амортизация_зданий_производ_статьи_калькуляций_новые: ArticulationArticles
        _hnt_амортизация_оборудования_производ_статьи_калькуляций_новые: ArticulationArticles
        _hnt_амортизация_оргтехники_производ_статьи_калькуляций_новые: ArticulationArticles
        _hnt_документация_по_проекту_производ_статьи_калькуляций_новые: ArticulationArticles
        _hnt_налоги_от_заработной_платы_и_прочих_начислений_сотрудникам_производ_статьи_калькуляций_новые: ArticulationArticles
        _hnt_работы_услуги_сторонних_организаций_по_проекту_производ_статьи_калькуляций_новые: ArticulationArticles
        _hnt_упаковка_1_1_материалы: ArticulationArticles
        _hnt_услуги_сторонних_организаций_по_проекту_1_1_материалы: ArticulationArticles
        _hnt_сырье_1_1_материалы: ArticulationArticles
        _hnt_инструмент_1_1_материалы: ArticulationArticles
        _hnt_прочие_материалы_1_1_материалы: ArticulationArticles
        _hnt_потери_от_брака_1_1_материалы: ArticulationArticles
        _hnt_полуфабрикаты_производимые_в_процессе_1_1_материалы: ArticulationArticles
        _hnt_плата_за_загрязнение_окружающей_среды_экологический_сбор_1_1_материалы: ArticulationArticles
        _hnt_дизтопливо_1_2_гсм: ArticulationArticles
        _hnt_бензин_1_2_гсм: ArticulationArticles
        _hnt_прочие_горюче_смазочные_материалы_1_2_гсм: ArticulationArticles
        _hnt_запчасти_и_технические_жидкости_для_автомобилей_1_3_запасные_части: ArticulationArticles
        _hnt_запчасти_и_масла_для_оборудования_и_инструмента_1_3_запасные_части: ArticulationArticles
        _hnt_автошины_1_3_запасные_части: ArticulationArticles
        _hnt_комплектующие_для_орг_техники_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_средства_индивидуальной_защиты_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_техника_и_оборудование_быт_орг_видео_выставочное_и_др_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_инвентарь_в_т_ч_мебель_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_строительные_материалы_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_канц_товары_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_печатная_продукция_бланки_визитки_буклеты_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_хоз_средства_1_4_инвентарь_и_хоз_принадлежности: ArticulationArticles
        _hnt_электроэнергия_1_5_топливо_энергия: ArticulationArticles
        _hnt_теплоэнергия_1_5_топливо_энергия: ArticulationArticles
        _hnt_услуги_по_разгрузке_товара_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_услуги_по_доставке_товара_внешним_оператором_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_эксплуатационные_расходы_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_ремонт_основных_средств_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_аренда_транспортных_средств_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_аренда_зданий_помещений_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_аренда_оборудования_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_договоры_гпх_с_отчислениями_аутстаффинг_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_водоотведение_и_канализация_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_регулярный_ремонт_и_тех_обслуживание_ос_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_прочие_расходы_на_содержание_и_эксплуатацию_оборудования_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_прочие_расходы_на_охрану_труда_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_лизинговые_платежи_1_6_услуги_производственного_характера: ArticulationArticles
        _hnt_основной_фот_оплата_труда_и_страховые_взносы: ArticulationArticles
        _hnt_резерв_отпусков_оплата_труда_и_страховые_взносы: ArticulationArticles
        _hnt_страховые_взносы_оплата_труда_и_страховые_взносы: ArticulationArticles
        _hnt_актуализация_и_приобретение_документов_на_продукцию_информационное_обслуживание: ArticulationArticles
        _hnt_периодическая_печать_подписка_и_пр_информационное_обслуживание: ArticulationArticles
        _hnt_почта_dhl_письма_и_посылки_услуги_связи: ArticulationArticles
        _hnt_связь_услуги_связи: ArticulationArticles
        _hnt_прочие_расходы_будущих_периодов: ArticulationArticles
        _hnt_страхование_имущества_страхование: ArticulationArticles
        _hnt_страхование_сотрудников_страхование: ArticulationArticles
        _hnt_суточные_командировочные_расходы: ArticulationArticles
        _hnt_проживание_проездные_документы_и_пр_командировочные_расходы: ArticulationArticles
        _hnt_обучение_персонала_обучение_персонала: ArticulationArticles
        _hnt_дезинфекция_дезинсекция_прочие_услуги: ArticulationArticles
        _hnt_медосмотр_прочие_услуги: ArticulationArticles
        _hnt_лицензирование_прочие_услуги: ArticulationArticles
        _hnt_коммунальные_услуги_прочие_услуги: ArticulationArticles
        _hnt_поверка_и_колибровка_прочие_услуги: ArticulationArticles
        _hnt_уборка_пемещения_прочие_услуги: ArticulationArticles
        _hnt_подбор_персонала_прочие_услуги: ArticulationArticles
        _hnt_утилизация_прочие_услуги: ArticulationArticles
        _hnt_вывоз_бытовых_отходов_прочие_услуги: ArticulationArticles
        _hnt_услуги_таможенного_декларирования_прочие_услуги: ArticulationArticles
        _hnt_услуги_охраны_прочие_услуги: ArticulationArticles
        _hnt_прочие_услуги_прочие_услуги: ArticulationArticles
        _hnt_страхование_сотрудников_производственные_затраты_старое: ArticulationArticles
        _hnt_дорезка_старое: ArticulationArticles
        _hnt_документация_старое: ArticulationArticles
        _hnt_спецоснастка_старое: ArticulationArticles
        _hnt_энергоресурсы_старое: ArticulationArticles
        _hnt_отчисления_на_соцстрах_старое: ArticulationArticles
        _hnt_покупные_комплектующие_изделия_старое: ArticulationArticles
        _hnt_гибка_старое: ArticulationArticles
        _hnt_брак_старое: ArticulationArticles
        _hnt_страховые_взносы_фот_старое: ArticulationArticles
        _hnt_резка_старое: ArticulationArticles
        _hnt_возвратные_отходы_старое: ArticulationArticles
        _hnt_проектная_документация_старое: ArticulationArticles
        _hnt_транспортные_расходы_старое: ArticulationArticles
        _hnt_аренда_ос_старое: ArticulationArticles
        _hnt_амортизация_старое: ArticulationArticles
        _hnt_командировочные_расходы_старое: ArticulationArticles
        _hnt_разработка_кд_старое: ArticulationArticles
        _hnt_работы_услуги_стронних_организаций_старое: ArticulationArticles

    @classmethod
    def init_data(cls):
        req_text = f"""ВЫБРАТЬ
                СтатьиКалькуляции.Наименование КАК Наименование,
                УНИКАЛЬНЫЙИДЕНТИФИКАТОР(СтатьиКалькуляции.Ссылка) КАК ref_key,
                СтатьиКалькуляции.Родитель.Наименование КАК РодительПредставление
            ИЗ
                Справочник.СтатьиКалькуляции КАК СтатьиКалькуляции
            ГДЕ
                СтатьиКалькуляции.ЭтоГруппа = ЛОЖЬ
                И СтатьиКалькуляции.ПометкаУдаления = ЛОЖЬ"""
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, ArticulationArticles, {'name': 'Наименование', 'parent': 'РодительПредставление',
                                                        'ref_key': 'ref_key'})

def ___________data_nomen___________():
    pass



class NDS_ratesData(ObjsData):
    NAME_ERP_OBJ = 'СтавкиНДС'
    if 'свойства':
        _hnt__0: NDS_rates
        _hnt__10: NDS_rates
        _hnt__10_110: NDS_rates
        _hnt__15_25: NDS_rates
        _hnt__16_67: NDS_rates
        _hnt__18: NDS_rates
        _hnt__18_118: NDS_rates
        _hnt__20: NDS_rates
        _hnt__20_120: NDS_rates
        _hnt__5: NDS_rates
        _hnt__5_105: NDS_rates
        _hnt__7: NDS_rates
        _hnt__7_107: NDS_rates
        _hnt__9_09: NDS_rates
        _hnt_без_ндс: NDS_rates

    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
    СтавкиНДС.Наименование КАК Наименование,
    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(СтавкиНДС.Ссылка) КАК ref_key
ИЗ
    Справочник.СтавкиНДС КАК СтавкиНДС
 ГДЕ
            СтавкиНДС.ПометкаУдаления = ЛОЖЬ
        УПОРЯДОЧИТЬ ПО
            Наименование
            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, NDS_rates, {'name': 'Наименование', 'ref_key': 'ref_key'})



class VidNomemData(ObjsData):
    NAME_ERP_OBJ = 'ВидыНоменклатуры'
    if 'свойства':
        pass


    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
    ВидыНоменклатуры.Родитель.Наименование КАК РодительНаименование,
    ВидыНоменклатуры.Наименование КАК Наименование,
    ВидыНоменклатуры.ЭтоГруппа КАК ЭтоГруппа,
    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Ссылка) КАК ref_key
ИЗ
    Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
ГДЕ
    ВидыНоменклатуры.ЭтоГруппа = ЛОЖЬ
    И ВидыНоменклатуры.ПометкаУдаления = ЛОЖЬ
            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, VidNomem, {'name': 'Наименование', 'parent': 'РодительНаименование',
                                            'group': 'ЭтоГруппа', 'ref_key': 'ref_key'})


class TypeNomenData(ObjsData):
    NAME_ERP_OBJ = 'ТипыНоменклатуры'
    if 'свойства':
        _hnt_товар_0: TypeNomen
        _hnt_тара_1: TypeNomen
        _hnt_услуга_2: TypeNomen
        _hnt_работа_3: TypeNomen
        _hnt_набор_4: TypeNomen


    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
    ПРЕДСТАВЛЕНИЕ(ТипыНоменклатуры.Ссылка) КАК Наименование,
    ТипыНоменклатуры.Порядок КАК Порядок,
	УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ТипыНоменклатуры.Ссылка) КАК ref_key
ИЗ
    Перечисление.ТипыНоменклатуры КАК ТипыНоменклатуры
            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, TypeNomen, {'name': 'Наименование', 'order': 'Порядок', 'ref_key': 'ref_key'})


class AccessGroupData(ObjsData):
    NAME_ERP_OBJ = 'ГруппыДоступаНоменклатуры'
    if 'свойства':
        _hnt_газоочистка_круги: AccessGroup
        _hnt_газоочистка_листы: AccessGroup
        _hnt_газоочистка_насосы: AccessGroup
        _hnt_газоочистка_трубы: AccessGroup
        _hnt_гибкие_вставки: AccessGroup
        _hnt_гравировка: AccessGroup
        _hnt_детали_рес_спец: AccessGroup
        _hnt_детали_клапана: AccessGroup
        _hnt_дополнительно: AccessGroup
        _hnt_единая_номенклатура_материалов_для_ссзу_го: AccessGroup
        _hnt_запорная_арматура: AccessGroup
        _hnt_затворы_дисковые: AccessGroup
        _hnt_канцелярия: AccessGroup
        _hnt_клапаны_пауэрз: AccessGroup
        _hnt_краны: AccessGroup
        _hnt_манометр: AccessGroup
        _hnt_материалы: AccessGroup
        _hnt_материалы_полученные_от_давальцев: AccessGroup
        _hnt_материалы_болт: AccessGroup
        _hnt_материалы_винт: AccessGroup
        _hnt_материалы_гайка: AccessGroup
        _hnt_материалы_готовая_набивка: AccessGroup
        _hnt_материалы_грунт_эмали: AccessGroup
        _hnt_материалы_двутавр: AccessGroup
        _hnt_материалы_детали_трубопровода: AccessGroup
        _hnt_материалы_для_ткп: AccessGroup
        _hnt_материалы_древесные_материалы_10_01: AccessGroup
        _hnt_материалы_единая_номенклатура_конструкции_и_детали_10_02: AccessGroup
        _hnt_материалы_закаленное_стекло_смотровое: AccessGroup
        _hnt_материалы_заклёпки: AccessGroup
        _hnt_материалы_зубчатые_рейки: AccessGroup
        _hnt_материалы_квадрат: AccessGroup
        _hnt_материалы_компл_для_газоходов: AccessGroup
        _hnt_материалы_компл_для_проч_нест_обор: AccessGroup
        _hnt_материалы_компл_для_эмульгаторов: AccessGroup
        _hnt_материалы_круги: AccessGroup
        _hnt_материалы_листы: AccessGroup
        _hnt_материалы_масленки: AccessGroup
        _hnt_материалы_металлорукав: AccessGroup
        _hnt_материалы_нестандартные_детали_по_чертежам_на_заказ: AccessGroup
        _hnt_материалы_нестандартные_позиции: AccessGroup
        _hnt_материалы_пастообразные_материалы: AccessGroup
        _hnt_материалы_пиломатериал: AccessGroup
        _hnt_материалы_подшипники: AccessGroup
        _hnt_материалы_приводы: AccessGroup
        _hnt_материалы_прокладочный_материал: AccessGroup
        _hnt_материалы_пружина: AccessGroup
        _hnt_материалы_прутки: AccessGroup
        _hnt_материалы_свар_проволока: AccessGroup
        _hnt_материалы_стопорные_кольца: AccessGroup
        _hnt_материалы_тара_и_упаковка: AccessGroup
        _hnt_материалы_теплоизоляционный_материал: AccessGroup
        _hnt_материалы_труба_квадратная: AccessGroup
        _hnt_материалы_трубы: AccessGroup
        _hnt_материалы_уголок: AccessGroup
        _hnt_материалы_цепи: AccessGroup
        _hnt_материалы_шайба: AccessGroup
        _hnt_материалы_швеллер: AccessGroup
        _hnt_материалы_шестигранник: AccessGroup
        _hnt_материалы_шпилька: AccessGroup
        _hnt_материалы_шплинт: AccessGroup
        _hnt_материалы_шпонка: AccessGroup
        _hnt_материалы_электрика_10_01: AccessGroup
        _hnt_медосмотры: AccessGroup
        _hnt_номенклатура_для_бюджетирования: AccessGroup
        _hnt_обучение_по_охране_труда: AccessGroup
        _hnt_отдел_главного_технолога: AccessGroup
        _hnt_проведение_оценки_условий_труда_и_оценка_проф_рисков: AccessGroup
        _hnt_продукция_пауэрз: AccessGroup
        _hnt_продукция_пауэрз_для_эластика: AccessGroup
        _hnt_продукция_рудтех_продакшн: AccessGroup
        _hnt_продукция_эластик: AccessGroup
        _hnt_продукция_эластик_для_пауэрза: AccessGroup
        _hnt_продукция_эластик_кзх_стандарт: AccessGroup
        _hnt_продукция_виртуальная_номенклатура_ссзу: AccessGroup
        _hnt_прочие: AccessGroup
        _hnt_работы: AccessGroup
        _hnt_работы_новая_номенклатура: AccessGroup
        _hnt_работы_разработка_проектной_и_рабочей_документации: AccessGroup
        _hnt_расходники_расходные_материалы_для_сварочных_работ: AccessGroup
        _hnt_расходники_расходные_материалы_для_слесарных_работ: AccessGroup
        _hnt_расходники_расходные_материалы_для_станков_резки: AccessGroup
        _hnt_расходники_расходные_материалы_для_токарных_станков: AccessGroup
        _hnt_расходники_спецодежда: AccessGroup
        _hnt_расходные_материалы_для_малярного_участка_10_09: AccessGroup
        _hnt_расходные_материалы_для_складского_хозяйства_10_09: AccessGroup
        _hnt_ремонт_и_то_запчасти: AccessGroup
        _hnt_ремонтный_цех: AccessGroup
        _hnt_ссзу_рукавные_фильтры: AccessGroup
        _hnt_ссзу_шнек: AccessGroup
        _hnt_стандартные_приводые_механизмы_мэо_ф: AccessGroup
        _hnt_товары_powerz_gmbh_резиновые_компенсаторы: AccessGroup
        _hnt_услуги_новая_единая_номенклатура: AccessGroup
        _hnt_услуги_сторонних_организаций: AccessGroup
        _hnt_услуги_оказываемые_нами: AccessGroup
        _hnt_услуги_переработчики_для_ткп: AccessGroup
        _hnt_хомуты: AccessGroup

    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
    ГруппыДоступаНоменклатуры.Наименование КАК Наименование,
    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ГруппыДоступаНоменклатуры.Ссылка) КАК ref_key
ИЗ
    Справочник.ГруппыДоступаНоменклатуры КАК ГруппыДоступаНоменклатуры
 ГДЕ
            ГруппыДоступаНоменклатуры.ПометкаУдаления = ЛОЖЬ
        УПОРЯДОЧИТЬ ПО
            Наименование
            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, AccessGroup, {'name': 'Наименование', 'ref_key': 'ref_key'})



class GruopNomenData(ObjsData):
    NAME_ERP_OBJ = 'ГруппыДоступаНоменклатуры'
    if 'свойства':
        _hnt_черный_листовой_металлопрокат_00_00045064_true_none: GruopNomen
        _hnt_нержавеющий_металлопрокат_00_00065071_true_none: GruopNomen
        _hnt_ссзу_00_00072425_true_none: GruopNomen
        _hnt_го_00_00072426_true_none: GruopNomen
        _hnt_го_ссзу_00_00072427_true_none: GruopNomen

    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
    Номенклатура.Наименование КАК Наименование,
    Номенклатура.Код КАК Код,
    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Ссылка) КАК ref_key,
    Номенклатура.ЭтоГруппа КАК ЭтоГруппа,
    Номенклатура.Родитель.Код + " " + Номенклатура.Родитель.Наименование КАК Родитель
ИЗ
    Справочник.Номенклатура КАК Номенклатура
ГДЕ
    Номенклатура.ЭтоГруппа = ИСТИНА
    И Номенклатура.ПометкаУдаления = ЛОЖЬ            """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, GruopNomen, {
                                            'name': 'Наименование',
                                            'code': 'Код',
                                            'parent': 'Родитель',
                                            'group': 'ЭтоГруппа',
                                              'ref_key': 'ref_key'})


class SalesOptionsData(ObjsData):
    NAME_ERP_OBJ = 'ВариантыОформленияПродажи'
    if 'свойства':
        _hnt_реализация_товаров_и_услуг_0: SalesOptions
        _hnt_акт_выполненных_работ_1: SalesOptions
        _hnt_акт_на_передачу_прав_2: SalesOptions

    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
    ПРЕДСТАВЛЕНИЕ(ВариантыОформленияПродажи.Ссылка) КАК Наименование,
    ВариантыОформленияПродажи.Порядок КАК Порядок,
	УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВариантыОформленияПродажи.Ссылка) КАК ref_key
ИЗ
    Перечисление.ВариантыОформленияПродажи КАК ВариантыОформленияПродажи
        """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, SalesOptions, {'name': 'Наименование', 'order': 'Порядок', 'ref_key': 'ref_key'})


class PackagingUnitsData(ObjsData):
    NAME_ERP_OBJ = 'УпаковкиЕдиницыИзмерения'
    if 'свойства':
        _hnt__744_процент: PackagingUnits
        _hnt__281_f_градус_фаренгейта: PackagingUnits
        _hnt__280_с_градус_цельсия: PackagingUnits
        _hnt__732_10_пар_десять_пар: PackagingUnits
        _hnt__170_10_т3_килотонна: PackagingUnits
        _hnt__387_10_12_руб_триллион_рублей: PackagingUnits
        _hnt__801_10_12_шт_биллион_штук_европа_триллион_штук: PackagingUnits
        _hnt__388_10_15_руб_квадрильон_рублей: PackagingUnits
        _hnt__802_10_18_шт_квинтильон_штук_европа: PackagingUnits
        _hnt__973_10_3_автомоб_км_тысяча_автомобиле_километров: PackagingUnits
        _hnt__962_10_3_автомоб_мест_дн_тысяча_автомобиле_место_дней: PackagingUnits
        _hnt__960_10_3_автомоб_т_дн_тысяча_автомобиле_тонно_дней: PackagingUnits
        _hnt__961_10_3_автомоб_ч_тысяча_автомобиле_часов: PackagingUnits
        _hnt__952_10_3_ваг_маш_км_тысяча_вагоно_машино_километров: PackagingUnits
        _hnt__951_10_3_ваг_маш_ч_тысяча_вагоно_машино_часов: PackagingUnits
        _hnt__724_10_3_га_порц_тысяча_гектаров_порций: PackagingUnits
        _hnt__985_10_3_гол_тысяча_голов: PackagingUnits
        _hnt__980_10_3_доллар_тысяча_долларов: PackagingUnits
        _hnt__965_10_3_км_тысяча_километров: PackagingUnits
        _hnt__673_10_3_компл_тысяча_комплектов: PackagingUnits
        _hnt__981_10_3_корм_ед_тысяча_тонн_кормовых_единиц: PackagingUnits
        _hnt__986_10_3_краск_оттиск_тысяча_краско_оттисков: PackagingUnits
        _hnt__953_10_3_мест_км_тысяча_место_километров: PackagingUnits
        _hnt__479_10_3_набор_тысяча_наборов: PackagingUnits
        _hnt__709_10_3_ном_тысяча_номеров: PackagingUnits
        _hnt__958_10_3_пасс_миль_тысяча_пассажиро_миль: PackagingUnits
        _hnt__729_10_3_пач_тысяча_пачек: PackagingUnits
        _hnt__930_10_3_пласт_тысяча_пластин: PackagingUnits
        _hnt__956_10_3_поезд_км_тысяча_поездо_километров: PackagingUnits
        _hnt__955_10_3_поезд_ч_тысяча_поездо_часов: PackagingUnits
        _hnt__562_10_3_пряд_верет_тысяча_прядильных_веретен: PackagingUnits
        _hnt__563_10_3_пряд_мест_тысяча_прядильных_мест: PackagingUnits
        _hnt__761_10_3_стан_тысяча_станов: PackagingUnits
        _hnt__957_10_3_т_миль_тысяча_тонно_миль: PackagingUnits
        _hnt__966_10_3_тоннаж_рейс_тысяча_тоннаже_рейсов: PackagingUnits
        _hnt__974_10_3_тоннаж_сут_тысяча_тоннаже_сут: PackagingUnits
        _hnt__775_10_3_тюбик_тысяча_тюбиков: PackagingUnits
        _hnt__782_10_3_упак_тысяча_упаковок: PackagingUnits
        _hnt__776_10_3_усл_туб_тысяча_условных_тубов: PackagingUnits
        _hnt__207_10_3_ц_тысяча_центнеров: PackagingUnits
        _hnt__979_10_3_экз_тысяча_экземпляров: PackagingUnits
        _hnt__241_10_6_а_ч_миллион_ампер_часов: PackagingUnits
        _hnt__235_10_6_гкал_миллион_гигакалорий: PackagingUnits
        _hnt__557_10_6_гол_год_миллион_голов_в_год: PackagingUnits
        _hnt__120_10_6_дкл_миллион_декалитров: PackagingUnits
        _hnt__056_10_6_дм2_миллион_квадратных_дециметров: PackagingUnits
        _hnt__937_10_6_доз_миллион_доз: PackagingUnits
        _hnt__901_10_6_домхоз_миллион_домохозяйств: PackagingUnits
        _hnt__644_10_6_ед_миллион_единиц: PackagingUnits
        _hnt__544_10_6_ед_год_миллион_единиц_в_год: PackagingUnits
        _hnt__167_10_6_кар_миллион_каратов_метрических: PackagingUnits
        _hnt__242_10_6_кв_а_миллион_киловольт_ампер: PackagingUnits
        _hnt__982_10_6_корм_ед_миллион_тонн_кормовых_единиц: PackagingUnits
        _hnt__987_10_6_краск_оттиск_миллион_краско_оттисков: PackagingUnits
        _hnt__253_10_6_л_с_миллион_лошадиных_сил: PackagingUnits
        _hnt__949_10_6_лист_оттиск_миллион_листов_оттисков: PackagingUnits
        _hnt__057_10_6_м2_миллион_квадратных_метров: PackagingUnits
        _hnt__089_10_6_м2_2_мм_исч_миллион_квадратных_метров_в_двухмиллиметровом_исчислении: PackagingUnits
        _hnt__086_10_6_м2_жил_пл_миллион_квадратных_метров_жилой_площади: PackagingUnits
        _hnt__083_10_6_м2_общ_пл_миллион_квадратных_метров_общей_площади: PackagingUnits
        _hnt__159_10_6_м3_миллион_кубических_метров: PackagingUnits
        _hnt__125_10_6_м3_перераб_газа_миллион_кубических_метров_переработки_газа: PackagingUnits
        _hnt__838_10_6_пар_миллион_пар: PackagingUnits
        _hnt__424_10_6_пасс_км_миллион_пассажиро_километров: PackagingUnits
        _hnt__970_10_6_пасс_мест_миль_миллион_пассажиро_место_миль: PackagingUnits
        _hnt__968_10_6_пасс_миль_миллион_пассажиро_миль: PackagingUnits
        _hnt__129_10_6_пол_л_миллион_полулитров: PackagingUnits
        _hnt__385_10_6_руб_миллион_рублей: PackagingUnits
        _hnt__898_10_6_семей_миллион_семей: PackagingUnits
        _hnt__171_10_6_т_миллион_тонн: PackagingUnits
        _hnt__176_10_6_т_усл_топл_миллион_тонн_условного_топлива: PackagingUnits
        _hnt__451_10_6_т_км_миллион_тонно_километров: PackagingUnits
        _hnt__967_10_6_т_миль_миллион_тонно_миль: PackagingUnits
        _hnt__550_10_6_т_год_миллион_тонн_в_год: PackagingUnits
        _hnt__969_10_6_тоннаж_миль_миллион_тоннаже_миль: PackagingUnits
        _hnt__779_10_6_упак_миллион_упаковок: PackagingUnits
        _hnt__883_10_6_усл_банк_миллион_условных_банок: PackagingUnits
        _hnt__878_10_6_усл_ед_миллион_условных_единиц: PackagingUnits
        _hnt__895_10_6_усл_кирп_миллион_условных_кирпичей: PackagingUnits
        _hnt__886_10_6_усл_кус_миллион_условных_кусков: PackagingUnits
        _hnt__064_10_6_усл_м2_миллион_условных_квадратных_метров: PackagingUnits
        _hnt__988_10_6_усл_плит_миллион_условных_плиток: PackagingUnits
        _hnt__794_10_6_чел_миллион_человек: PackagingUnits
        _hnt__799_10_6_шт_миллион_штук: PackagingUnits
        _hnt__808_10_6_экз_миллион_экземпляров: PackagingUnits
        _hnt__249_10_9_квт_ч_миллиард_киловатт_часов: PackagingUnits
        _hnt__115_10_9_м3_миллиард_кубических_метров: PackagingUnits
        _hnt__386_10_9_руб_миллиард_рублей: PackagingUnits
        _hnt__800_10_9_шт_миллиард_штук: PackagingUnits
        _hnt__626_100_л_сто_листов: PackagingUnits
        _hnt__781_100_упак_сто_упаковок: PackagingUnits
        _hnt__797_100_шт_сто_штук: PackagingUnits
        _hnt__683_100_ящ_сто_ящиков: PackagingUnits
        _hnt__264_1000_а_ч_тысяча_ампер_часов: PackagingUnits
        _hnt__871_1000_ампул_тысяча_ампул: PackagingUnits
        _hnt__869_1000_бут_тысяча_бутылок: PackagingUnits
        _hnt__060_1000_га_тысяча_гектаров: PackagingUnits
        _hnt__234_1000_гкал_тысяча_гигакалорий: PackagingUnits
        _hnt__239_1000_гкал_ч_тысяча_гигакалорий_в_час: PackagingUnits
        _hnt__556_1000_гол_год_тысяча_голов_в_год: PackagingUnits
        _hnt__119_1000_дкл_тысяча_декалитров: PackagingUnits
        _hnt__054_1000_дм2_тысяча_квадратных_дециметров: PackagingUnits
        _hnt__640_1000_доз_тысяча_доз: PackagingUnits
        _hnt__900_1000_домхоз_тысяча_домохозяйств: PackagingUnits
        _hnt__643_1000_ед_тысяча_единиц: PackagingUnits
        _hnt__165_1000_кар_тысяча_каратов_метрических: PackagingUnits
        _hnt__250_1000_кв_а_р_тысяча_киловольт_ампер_реактивных: PackagingUnits
        _hnt__910_1000_кварт_тысяча_квартир: PackagingUnits
        _hnt__912_1000_коек_тысяча_коек: PackagingUnits
        _hnt__875_1000_кор_тысяча_коробок: PackagingUnits
        _hnt__559_1000_кур_несуш_тысяча_кур_несушек: PackagingUnits
        _hnt__130_1000_л_тысяча_литров: PackagingUnits
        _hnt__252_1000_л_с_тысяча_лошадиных_сил: PackagingUnits
        _hnt__058_1000_м2_тысяча_квадратных_метров: PackagingUnits
        _hnt__085_1000_м2_жил_пл_тысяча_квадратных_метров_жилой_площади: PackagingUnits
        _hnt__082_1000_м2_общ_пл_тысяча_квадратных_метров_общей_площади: PackagingUnits
        _hnt__088_1000_м2_уч_лаб_здан_тысяча_квадратных_метров_учебно_лабораторных_зданий: PackagingUnits
        _hnt__114_1000_м3_тысяча_кубических_метров: PackagingUnits
        _hnt__599_1000_м3_сут_тысяча_кубических_метров_в_сутки: PackagingUnits
        _hnt__699_1000_мест_тысяча_мест: PackagingUnits
        _hnt__837_1000_пар_тысяча_пар: PackagingUnits
        _hnt__548_1000_пар_смен_тысяча_пар_в_смену: PackagingUnits
        _hnt__423_1000_пасс_км_тысяча_пассажиро_километров: PackagingUnits
        _hnt__127_1000_плотн_м3_тысяча_плотных_кубических_метров: PackagingUnits
        _hnt__019_1000_пог_м_тысяча_погонных_метров: PackagingUnits
        _hnt__128_1000_пол_л_тысяча_полулитров: PackagingUnits
        _hnt__907_1000_посад_мест_тысяча_посадочных_мест: PackagingUnits
        _hnt__546_1000_посещ_смен_тысяча_посещений_в_смену: PackagingUnits
        _hnt__558_1000_птицемест_тысяча_птицемест: PackagingUnits
        _hnt__905_1000_раб_мест_тысяча_рабочих_мест: PackagingUnits
        _hnt__384_1000_руб_тысяча_рублей: PackagingUnits
        _hnt__751_1000_рул_тысяча_рулонов: PackagingUnits
        _hnt__897_1000_семей_тысяча_семей: PackagingUnits
        _hnt__169_1000_т_тысяча_тонн: PackagingUnits
        _hnt__177_1000_т_единовр_хран_тысяча_тонн_единовременного_хранения: PackagingUnits
        _hnt__561_1000_т_пар_ч_тысяча_тонн_пара_в_час: PackagingUnits
        _hnt__178_1000_т_перераб_тысяча_тонн_переработки: PackagingUnits
        _hnt__553_1000_т_перераб_сут_тысяча_тонн_переработки_в_сутки: PackagingUnits
        _hnt__175_1000_т_усл_топл_тысяча_тонн_условного_топлива: PackagingUnits
        _hnt__450_1000_т_км_тысяча_тонно_километров: PackagingUnits
        _hnt__538_1000_т_год_тысяча_тонн_в_год: PackagingUnits
        _hnt__537_1000_т_сез_тысяча_тонн_в_сезон: PackagingUnits
        _hnt__914_1000_том_книжн_фонд_тысяча_томов_книжного_фонда: PackagingUnits
        _hnt__874_1000_туб_тысяча_тубов: PackagingUnits
        _hnt__882_1000_усл_банк_тысяча_условных_банок: PackagingUnits
        _hnt__543_1000_усл_банк_смен_тысяча_условных_банок_в_смену: PackagingUnits
        _hnt__877_1000_усл_ед_тысяча_условных_единиц: PackagingUnits
        _hnt__890_1000_усл_кат_тысяча_условных_катушек: PackagingUnits
        _hnt__894_1000_усл_кирп_тысяча_условных_кирпичей: PackagingUnits
        _hnt__885_1000_усл_кус_тысяча_условных_кусков: PackagingUnits
        _hnt__048_1000_усл_м_тысяча_условных_метров: PackagingUnits
        _hnt__063_1000_усл_м2_тысяча_условных_квадратных_метров: PackagingUnits
        _hnt__124_1000_усл_м3_тысяча_условных_кубических_метров: PackagingUnits
        _hnt__892_1000_усл_плит_тысяча_условных_плиток: PackagingUnits
        _hnt__880_1000_усл_шт_тысяча_условных_штук: PackagingUnits
        _hnt__888_1000_усл_ящ_тысяча_условных_ящиков: PackagingUnits
        _hnt__903_1000_учен_мест_тысяча_ученических_мест: PackagingUnits
        _hnt__873_1000_флак_тысяча_флаконов: PackagingUnits
        _hnt__555_1000_ц_перераб_сут_тысяча_центнеров_переработки_в_сутки: PackagingUnits
        _hnt__793_1000_чел_тысяча_человек: PackagingUnits
        _hnt__541_1000_чел_дн_тысяча_человеко_дней: PackagingUnits
        _hnt__542_1000_чел_ч_тысяча_человеко_часов: PackagingUnits
        _hnt__730_20_два_десятка: PackagingUnits
        _hnt__288_k_кельвин: PackagingUnits
        _hnt__109_а_ар_100_м2: PackagingUnits
        _hnt__260_а_ампер: PackagingUnits
        _hnt__263_а_ч_ампер_час_3_6_ккл: PackagingUnits
        _hnt__513_авто_т_автотонна: PackagingUnits
        _hnt__959_автомоб_дн_автомобиле_день: PackagingUnits
        _hnt__870_ампул_ампула: PackagingUnits
        _hnt__301_ат_техническая_атмосфера_98066_5_па: PackagingUnits
        _hnt__300_атм_физическая_атмосфера_101325_па: PackagingUnits
        _hnt__255_байт_байт: PackagingUnits
        _hnt__309_бар_бар: PackagingUnits
        _hnt__254_бит_бит: PackagingUnits
        _hnt__323_бк_беккерель: PackagingUnits
        _hnt__616_боб_бобина: PackagingUnits
        _hnt__258_бод_бод: PackagingUnits
        _hnt__181_брт_брутто_регистровая_тонна_2_8316_м3: PackagingUnits
        _hnt__868_бут_бутылка: PackagingUnits
        _hnt__222_в_вольт: PackagingUnits
        _hnt__226_в_а_вольт_ампер: PackagingUnits
        _hnt__950_ваг_маш_дн_вагоно_машино_день: PackagingUnits
        _hnt__954_ваг_сут_вагоно_сутки: PackagingUnits
        _hnt__324_вб_вебер: PackagingUnits
        _hnt__212_вт_ватт: PackagingUnits
        _hnt__243_вт_ч_ватт_час: PackagingUnits
        _hnt__306_г_д_и_грамм_делящихся_изотопов: PackagingUnits
        _hnt__510_г_квт_ч_грамм_на_киловатт_час: PackagingUnits
        _hnt__366_г_лет_год: PackagingUnits
        _hnt__059_га_гектар: PackagingUnits
        _hnt__310_гб_гектобар: PackagingUnits
        _hnt__302_гбк_гигабеккерель: PackagingUnits
        _hnt__247_гвт_ч_гигаватт_час_миллион_киловатт_часов: PackagingUnits
        _hnt__160_гг_гектограмм: PackagingUnits
        _hnt__233_гкал_гигакалория: PackagingUnits
        _hnt__238_гкал_ч_гигакалория_в_час: PackagingUnits
        _hnt__122_гл_гектолитр: PackagingUnits
        _hnt__833_гл_100_спирта_гектолитр_чистого_100_спирта: PackagingUnits
        _hnt__287_гн_генри: PackagingUnits
        _hnt__836_гол_голова: PackagingUnits
        _hnt__163_грамм_г: PackagingUnits
        _hnt__290_гц_герц: PackagingUnits
        _hnt__515_дедвейт_т_дедвейт_тонна: PackagingUnits
        _hnt__361_дек_декада: PackagingUnits
        _hnt__368_деслет_десятилетие: PackagingUnits
        _hnt__271_дж_джоуль: PackagingUnits
        _hnt__116_дкл_декалитр: PackagingUnits
        _hnt__118_дл_децилитр: PackagingUnits
        _hnt__005_дм_дециметр: PackagingUnits
        _hnt__053_дм2_квадратный_дециметр: PackagingUnits
        _hnt__639_доз_доза: PackagingUnits
        _hnt__899_домхоз_домохозяйство: PackagingUnits
        _hnt__641_дюжина_дюжина_12_шт: PackagingUnits
        _hnt__733_дюжина_пар_дюжина_пар: PackagingUnits
        _hnt__737_дюжина_рул_дюжина_рулонов: PackagingUnits
        _hnt__780_дюжина_упак_дюжина_упаковок: PackagingUnits
        _hnt__740_дюжина_шт_дюжина_штук: PackagingUnits
        _hnt__039_дюйм_дюйм_25_4_мм: PackagingUnits
        _hnt__071_дюйм2_квадратный_дюйм_645_16_мм2: PackagingUnits
        _hnt__131_дюйм3_кубический_дюйм_16387_1_мм3: PackagingUnits
        _hnt__642_ед_единица: PackagingUnits
        _hnt__922_знак_знак: PackagingUnits
        _hnt_зуб_зуб: PackagingUnits
        _hnt__657_изд_изделие: PackagingUnits
        _hnt__236_кал_ч_калория_в_час: PackagingUnits
        _hnt__661_канал_канал: PackagingUnits
        _hnt__977_канал_км_канало_километр: PackagingUnits
        _hnt__978_канал_конц_канало_концы: PackagingUnits
        _hnt__162_кар_метрический_карат_1_карат_200_мг_2_0_0001_кг: PackagingUnits
        _hnt__312_кб_килобар: PackagingUnits
        _hnt__256_кбайт_килобайт: PackagingUnits
        _hnt__223_кв_киловольт: PackagingUnits
        _hnt__227_кв_а_киловольт_ампер: PackagingUnits
        _hnt__248_кв_а_р_киловольт_ампер_реактивный: PackagingUnits
        _hnt__230_квар_киловар: PackagingUnits
        _hnt__364_кварт_квартал: PackagingUnits
        _hnt__909_кварт_квартира: PackagingUnits
        _hnt__214_квт_киловатт: PackagingUnits
        _hnt__245_квт_ч_киловатт_час: PackagingUnits
        _hnt__166_кг_кг: PackagingUnits
        _hnt__8751_кг_кг: PackagingUnits
        _hnt_кг_вес_не_учит_в_ткп_килограмм_для_материалов_не_учитываемых_как_вес_в_ткп: PackagingUnits
        _hnt__845_кг_90_с_в_килограмм_90_го_сухого_вещества: PackagingUnits
        _hnt__841_кг_h_2_0_2_килограмм_пероксида_водорода: PackagingUnits
        _hnt__861_кг_n_килограмм_азота: PackagingUnits
        _hnt__863_кг_naoh_килограмм_гидроксида_натрия: PackagingUnits
        _hnt__867_кг_u_килограмм_урана: PackagingUnits
        _hnt__852_кг_к_2_о_килограмм_оксида_калия: PackagingUnits
        _hnt__859_кг_кон_килограмм_гидроксида_калия: PackagingUnits
        _hnt__865_кг_р_2_о_5_килограмм_пятиокиси_фосфора: PackagingUnits
        _hnt__511_кг_гкал_килограмм_на_гигакалорию: PackagingUnits
        _hnt__316_кг_м3_килограмм_на_кубический_метр: PackagingUnits
        _hnt__499_кг_с_килограмм_в_секунду: PackagingUnits
        _hnt__317_кг_см_2_килограмм_на_квадратный_сантиметр: PackagingUnits
        _hnt__291_кгц_килогерц: PackagingUnits
        _hnt__282_кд_кандела: PackagingUnits
        _hnt__273_кдж_килоджоуль: PackagingUnits
        _hnt__305_ки_кюри: PackagingUnits
        _hnt__232_ккал_килокалория: PackagingUnits
        _hnt__237_ккал_ч_килокалория_в_час: PackagingUnits
        _hnt__270_кл_кулон: PackagingUnits
        _hnt__349_кл_кг_кулон_на_килограмм: PackagingUnits
        _hnt__049_км_усл_труб_километр_условных_труб: PackagingUnits
        _hnt__008_км_1000_м_километр_тысяча_метров: PackagingUnits
        _hnt__333_км_ч_километр_в_час: PackagingUnits
        _hnt__061_км2_квадратный_километр: PackagingUnits
        _hnt__911_коек_койка: PackagingUnits
        _hnt__839_компл_комплект: PackagingUnits
        _hnt__971_корм_дн_кормо_день: PackagingUnits
        _hnt__8751_коробка_коробка: PackagingUnits
        _hnt__297_кпа_килопаскаль: PackagingUnits
        _hnt__820_креп_спирта_по_массе_крепость_спирта_по_массе: PackagingUnits
        _hnt__821_креп_спирта_по_объему_крепость_спирта_по_объему: PackagingUnits
        _hnt__831_л_100_спирта_литр_чистого_100_спирта: PackagingUnits
        _hnt__625_л_лист: PackagingUnits
        _hnt__918_л_авт_лист_авторский: PackagingUnits
        _hnt__920_л_печ_лист_печатный: PackagingUnits
        _hnt__251_л_с_лошадиная_сила: PackagingUnits
        _hnt__921_л_уч_изд_лист_учетно_издательский: PackagingUnits
        _hnt__112_литр_л: PackagingUnits
        _hnt__283_лк_люкс: PackagingUnits
        _hnt__284_лм_люмен: PackagingUnits
        _hnt__006_м_метр: PackagingUnits
        _hnt_м_метр: PackagingUnits
        _hnt__328_м_с_метр_в_секунду: PackagingUnits
        _hnt__335_м_с2_метр_на_секунду_в_квадрате: PackagingUnits
        _hnt__231_м_ч_метр_в_час: PackagingUnits
        _hnt__055_м2_квадратный_метр: PackagingUnits
        _hnt__084_м2_жил_пл_квадратный_метр_жилой_площади: PackagingUnits
        _hnt__081_м2_общ_пл_квадратный_метр_общей_площади: PackagingUnits
        _hnt__087_м2_уч_лаб_здан_квадратный_метр_учебно_лабораторных_зданий: PackagingUnits
        _hnt__113_м3_кубический_метр: PackagingUnits
        _hnt__596_м3_с_кубический_метр_в_секунду: PackagingUnits
        _hnt__598_м3_ч_кубический_метр_в_час: PackagingUnits
        _hnt__308_мб_миллибар: PackagingUnits
        _hnt__257_мбайт_мегабайт: PackagingUnits
        _hnt__228_мв_а_мегавольт_ампер_тысяча_киловольт_ампер: PackagingUnits
        _hnt__215_мвт_1000_квт_мегаватт_тысяча_киловатт: PackagingUnits
        _hnt_мвт_ч_мвт_ч: PackagingUnits
        _hnt__246_мвт_ч_1000_квт_ч_мегаватт_час_1000_киловатт_часов: PackagingUnits
        _hnt__161_мг_миллиграмм: PackagingUnits
        _hnt__292_мгц_мегагерц: PackagingUnits
        _hnt__362_мес_месяц: PackagingUnits
        _hnt__698_мест_место: PackagingUnits
        _hnt__6_метр_м: PackagingUnits
        _hnt__047_миля_морская_миля_1852_м: PackagingUnits
        _hnt__355_мин_минута: PackagingUnits
        _hnt__560_мин_заработн_плат_минимальная_заработная_плата: PackagingUnits
        _hnt__304_мки_милликюри: PackagingUnits
        _hnt__352_мкс_микросекунда: PackagingUnits
        _hnt__126_мл_мегалитр: PackagingUnits
        _hnt__353_млс_миллисекунда_эк: PackagingUnits
        _hnt__003_мм_миллиметр: PackagingUnits
        _hnt__009_мм_10_6_м_мегаметр_миллион_метров: PackagingUnits
        _hnt__337_мм_вод_ст_миллиметр_водяного_столба: PackagingUnits
        _hnt__338_мм_рт_ст_миллиметр_ртутного_столба: PackagingUnits
        _hnt__050_мм2_квадратный_миллиметр: PackagingUnits
        _hnt__110_мм3_кубический_миллиметр: PackagingUnits
        _hnt__298_мпа_мегапаскаль: PackagingUnits
        _hnt__289_н_ньютон: PackagingUnits
        _hnt__704_набор_набор: PackagingUnits
        _hnt__360_нед_неделя: PackagingUnits
        _hnt__908_ном_номер: PackagingUnits
        _hnt__331_об_мин_оборот_в_минуту: PackagingUnits
        _hnt__330_об_с_оборот_в_секунду: PackagingUnits
        _hnt__274_ом_ом: PackagingUnits
        _hnt__294_па_паскаль: PackagingUnits
        _hnt__715_пар_пара_2_шт: PackagingUnits
        _hnt__547_пар_смен_пара_в_смену: PackagingUnits
        _hnt__414_пасс_км_пассажиро_километр: PackagingUnits
        _hnt__421_пасс_мест_пассажирское_место_пассажирских_мест: PackagingUnits
        _hnt__991_пасс_миля_пассажиро_миля: PackagingUnits
        _hnt__427_пасс_поток_пассажиропоток: PackagingUnits
        _hnt__990_пасс_ч_пассажиров_в_час: PackagingUnits
        _hnt__121_плотн_м3_плотный_кубический_метр: PackagingUnits
        _hnt__018_пог_м_погонный_метр: PackagingUnits
        _hnt__365_полгода_полугодие: PackagingUnits
        _hnt__906_посад_мест_посадочное_место: PackagingUnits
        _hnt__545_посещ_смен_посещение_в_смену: PackagingUnits
        _hnt__734_посыл_посылка: PackagingUnits
        _hnt__963_привед_ч_приведенный_час: PackagingUnits
        _hnt__746_промилле_промилле_0_1_процента: PackagingUnits
        _hnt__904_раб_мест_рабочее_место: PackagingUnits
        _hnt_рабочие_дни_рабочие_дни: PackagingUnits
        _hnt__383_руб_рубль: PackagingUnits
        _hnt__736_рул_рулон: PackagingUnits
        _hnt_рулон_рулон: PackagingUnits
        _hnt__354_с_секунда: PackagingUnits
        _hnt__964_самолет_км_самолето_километр: PackagingUnits
        _hnt__173_сг_сантиграмм: PackagingUnits
        _hnt__840_секц_секция: PackagingUnits
        _hnt__896_семей_семья: PackagingUnits
        _hnt__924_символ_символ: PackagingUnits
        _hnt__923_слово_слово: PackagingUnits
        _hnt__004_см_сантиметр: PackagingUnits
        _hnt__296_см_сименс: PackagingUnits
        _hnt__339_см_вод_ст_сантиметр_водяного_столба: PackagingUnits
        _hnt__051_см2_квадратный_сантиметр: PackagingUnits
        _hnt__111_см3_мл_кубический_сантиметр_миллилитр: PackagingUnits
        _hnt__917_смен_смена: PackagingUnits
        _hnt__762_станц_станция: PackagingUnits
        _hnt__975_суго_сут_суго_сутки: PackagingUnits
        _hnt__983_суд_сут_судо_сутки: PackagingUnits
        _hnt__359_сут_дн_сутки: PackagingUnits
        _hnt__168_т_тонна_метрическая_тонна_1000_кг: PackagingUnits
        _hnt__847_т_90_с_в_тонна_90_го_сухого_вещества: PackagingUnits
        _hnt__185_т_грп_грузоподъемность_в_метрических_тоннах: PackagingUnits
        _hnt__533_т_пар_ч_тонна_пара_в_час: PackagingUnits
        _hnt__552_т_перераб_сут_тонна_переработки_в_сутки: PackagingUnits
        _hnt__172_т_усл_топл_тонна_условного_топлива: PackagingUnits
        _hnt__449_т_км_тонно_километр: PackagingUnits
        _hnt__512_т_ном_тонно_номер: PackagingUnits
        _hnt__516_т_танид_тонно_танид: PackagingUnits
        _hnt__514_т_тяги_тонна_тяги: PackagingUnits
        _hnt__536_т_смен_тонна_в_смену: PackagingUnits
        _hnt__535_т_сут_тонна_в_сутки: PackagingUnits
        _hnt__534_т_ч_тонна_в_час: PackagingUnits
        _hnt__313_тл_тесла: PackagingUnits
        _hnt__913_том_книжн_фонд_том_книжного_фонда: PackagingUnits
        _hnt__630_тыс_станд_усл_кирп_тысяча_стандартных_условных_кирпичей: PackagingUnits
        _hnt__798_тыс_шт_1000_шт_тысяча_штук: PackagingUnits
        _hnt__327_уз_узел_миля_ч: PackagingUnits
        _hnt__778_упак_упаковка: PackagingUnits
        _hnt__881_усл_банк_условная_банка: PackagingUnits
        _hnt__876_усл_ед_условная_единица: PackagingUnits
        _hnt__889_усл_кат_условная_катушка: PackagingUnits
        _hnt__893_усл_кирп_условный_кирпич: PackagingUnits
        _hnt__884_усл_кус_условный_кусок: PackagingUnits
        _hnt__020_усл_м_условный_метр: PackagingUnits
        _hnt__062_усл_м2_условный_квадратный_метр: PackagingUnits
        _hnt__123_усл_м3_условный_кубический_метр: PackagingUnits
        _hnt__891_усл_плит_условная_плитка: PackagingUnits
        _hnt__915_усл_рем_условный_ремонт: PackagingUnits
        _hnt__916_усл_рем_год_условный_ремонт_в_год: PackagingUnits
        _hnt__179_усл_т_условная_тонна_т: PackagingUnits
        _hnt__925_усл_труб_условная_труба: PackagingUnits
        _hnt__879_усл_шт_условная_штука: PackagingUnits
        _hnt__887_усл_ящ_условный_ящик: PackagingUnits
        _hnt__902_учен_мест_ученическое_место: PackagingUnits
        _hnt__314_ф_фарад: PackagingUnits
        _hnt__872_флак_флакон: PackagingUnits
        _hnt__041_фут_фут_0_3048_м: PackagingUnits
        _hnt__073_фут2_квадратный_фут_0_092903_м2: PackagingUnits
        _hnt__132_фут3_кубический_фут_0_02831685_м3: PackagingUnits
        _hnt__206_ц_центнер_метрический_100_кг_гектокилограмм_квинтал_метрический_децитонна: PackagingUnits
        _hnt__972_ц_корм_ед_центнер_кормовых_единиц: PackagingUnits
        _hnt__554_ц_перераб_сут_центнер_переработки_в_сутки: PackagingUnits
        _hnt__984_ц_га_центнеров_с_гектара: PackagingUnits
        _hnt__356_ч_час: PackagingUnits
        _hnt__735_часть_часть: PackagingUnits
        _hnt__792_чел_человек: PackagingUnits
        _hnt__540_чел_дн_человеко_день: PackagingUnits
        _hnt__539_чел_ч_человеко_час: PackagingUnits
        _hnt__522_чел_км2_человек_на_квадратный_километр: PackagingUnits
        _hnt__521_чел_м2_человек_на_квадратный_метр: PackagingUnits
        _hnt__989_чел_ч_человек_в_час: PackagingUnits
        _hnt_шт_шт: PackagingUnits
        _hnt__778_шт_штук: PackagingUnits
        _hnt__976_штук_в_20_футовом_эквиваленте_штук_в_20_футовом_эквиваленте_дфэ: PackagingUnits
        _hnt__796_штука_шт: PackagingUnits
        _hnt_штука_шт: PackagingUnits
        _hnt__745_элем_элемент: PackagingUnits
        _hnt__043_ярд_ярд_0_9144_м: PackagingUnits
        _hnt__075_ярд2_квадратный_ярд_0_8361274_м2: PackagingUnits
        _hnt__133_ярд3_кубический_ярд_0_764555_м3: PackagingUnits
        _hnt__810_яч_ячейка: PackagingUnits
        _hnt__812_ящ_ящик: PackagingUnits

    @classmethod
    def init_data(cls):
        req_text = f"""
            ВЫБРАТЬ РАЗЛИЧНЫЕ
                УНИКАЛЬНЫЙИДЕНТИФИКАТОР(УпаковкиЕдиницыИзмерения.Ссылка) КАК ref_key,
                УпаковкиЕдиницыИзмерения.Код КАК Код,
                УпаковкиЕдиницыИзмерения.Наименование КАК Наименование,
                УпаковкиЕдиницыИзмерения.НаименованиеПолное КАК НаименованиеПолное
            ИЗ
                Справочник.УпаковкиЕдиницыИзмерения КАК УпаковкиЕдиницыИзмерения
            ГДЕ
                УпаковкиЕдиницыИзмерения.ПометкаУдаления = ЛОЖЬ
                И УпаковкиЕдиницыИзмерения.НаименованиеПолное <> ""
            
            УПОРЯДОЧИТЬ ПО
                Наименование
        """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, PackagingUnits, {'name': 'Наименование',
                                                  'code': 'Код',
                                                  'fullname': 'НаименованиеПолное',
                                                    'ref_key': 'ref_key'})


class NomenAnalysisGroupsData(ObjsData):
    NAME_ERP_OBJ = 'ГруппыАналитическогоУчетаНоменклатуры'
    if 'свойства':
        _hnt_шумоглушители_продукция: NomenAnalysisGroups
        _hnt_тканевые_компенсаторы_продукция: NomenAnalysisGroups
        _hnt_аппараты_обдувки_продукция: NomenAnalysisGroups
        _hnt_быстросъемная_изоляция_продукция: NomenAnalysisGroups
        _hnt_материалы_прочие_материалы: NomenAnalysisGroups
        _hnt_материалы_основные_материалы: NomenAnalysisGroups
        _hnt_товары_товары: NomenAnalysisGroups
        _hnt_металлоизделия_продукция: NomenAnalysisGroups
        _hnt_системы_сухого_золоудаления_продукция: NomenAnalysisGroups
        _hnt_клапаны_продукция: NomenAnalysisGroups
        _hnt_услуги_оказываемые_нами_услуги: NomenAnalysisGroups
        _hnt_системы_продукция: NomenAnalysisGroups
        _hnt_услуги_сторонних_организаций_услуги: NomenAnalysisGroups
        _hnt_прочее_продукция: NomenAnalysisGroups
        _hnt_линзовые_компенсаторы_продукция: NomenAnalysisGroups
        _hnt_продукция_рудтех_продакшн_продукция: NomenAnalysisGroups
        _hnt_горелки_продукция: NomenAnalysisGroups
        _hnt_товары_продукция: NomenAnalysisGroups
        _hnt_канцелярия_материалы: NomenAnalysisGroups
        _hnt_полуфабрикаты_клапана_полуфабрикаты: NomenAnalysisGroups
        _hnt_гибкие_вставки_и_лента_продукция: NomenAnalysisGroups
        _hnt_испытательный_цех_продукция: NomenAnalysisGroups
        _hnt_полуфабрикаты_заготовки_полуфабрикаты: NomenAnalysisGroups
        _hnt_газоходы_продукция: NomenAnalysisGroups
        _hnt_полуфабрикаты_тканевого_компенсатора_полуфабрикаты: NomenAnalysisGroups
        _hnt_полуфабрикаты_быстросъёмной_изоляции_полуфабрикаты: NomenAnalysisGroups
        _hnt_средства_индивидуальной_защиты_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_теплоэнергия_1_5_топливо_энергия: NomenAnalysisGroups
        _hnt_инструмент_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_канцелярские_товары_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_представительские_расходы_none: NomenAnalysisGroups
        _hnt_печатная_и_сувенирная_продукция_бланки_визитки_буклеты_4_4_маркетинг_и_реклама: NomenAnalysisGroups
        _hnt_хоз_средства_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_инвентарь_в_т_ч_мебель_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_сырьё_деловой_отход_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_прочие_материалы_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_запчасти_и_масла_для_оборудования_и_инструмента_1_3_расходы_на_содержание_и_эксплуатацию_оборудования: NomenAnalysisGroups
        _hnt_упаковка_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_полуфабрикаты_шумоглушителей_продукция: NomenAnalysisGroups
        _hnt_бензин_1_2_гсм_и_запасные_части: NomenAnalysisGroups
        _hnt_дизтопливо_1_2_гсм_и_запасные_части: NomenAnalysisGroups
        _hnt_запчасти_и_технические_жидкости_для_автомобилей_1_2_гсм_и_запасные_части: NomenAnalysisGroups
        _hnt_регулярный_ремонт_и_тех_обслуживание_ос_1_2_гсм_и_запасные_части: NomenAnalysisGroups
        _hnt_автошины_1_2_гсм_и_запасные_части: NomenAnalysisGroups
        _hnt_техника_и_оборудование_быт_орг_видео_выставочное_и_др_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_строительные_материалы_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_прочие_расходные_материалы_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_основные_средства_none: NomenAnalysisGroups
        _hnt_комплектующие_и_запчасти_для_орг_техники_провода_элементы_сети_1_4_инвентарь_и_хоз_принадлежности: NomenAnalysisGroups
        _hnt_корпоративные_мероприятия_none: NomenAnalysisGroups
        _hnt_товары_для_перепродажи_тканевые_компенсаторы_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_листовой_металл_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_метизы_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_приводы_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_шестигранник_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_швеллер_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_прокат_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_трубы_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_прокладочный_материал_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_сырьё_лакокрасочные_материалы_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_товары_для_перепродажи_газоходы_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_товары_для_перепродажи_газоочистное_оборудование_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_услуги_сторонних_организаций_по_проекту_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_товары_для_перепродажи_ссзу_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_товары_для_перепродажи_ао_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_литье_продукция: NomenAnalysisGroups
        _hnt_рукава_фильтровальные_продукция: NomenAnalysisGroups
        _hnt_работы_по_проекту_1_1_материалы_и_работы: NomenAnalysisGroups
        _hnt_кмд_none: NomenAnalysisGroups

    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ГруппыАналитическогоУчетаНоменклатуры.Ссылка) КАК ref_key,
    ГруппыАналитическогоУчетаНоменклатуры.Наименование КАК Наименование,
    ГруппыАналитическогоУчетаНоменклатуры.Родитель.Представление КАК РодительПредставление,
    ГруппыАналитическогоУчетаНоменклатуры.ЭтоГруппа КАК ЭтоГруппа
ИЗ
    Справочник.ГруппыАналитическогоУчетаНоменклатуры КАК ГруппыАналитическогоУчетаНоменклатуры
ГДЕ
    ГруппыАналитическогоУчетаНоменклатуры.ЭтоГруппа = ЛОЖЬ
    И ГруппыАналитическогоУчетаНоменклатуры.ПометкаУдаления = ЛОЖЬ
        """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, NomenAnalysisGroups, {'name': 'Наименование',
                                                       'parent': 'РодительПредставление',
                                                       'group': 'ЭтоГруппа',
                                                    'ref_key': 'ref_key'})



class FinancialAccountingGroupData(ObjsData):
    NAME_ERP_OBJ = 'ГруппыФинансовогоУчетаНоменклатуры'
    if 'свойства':
        _hnt_продукция_собственного_производства_пауэрз_продукция_собственного_производства_пауэрз_перепродажа_через_келаст_таткуз_10_01_товары: FinancialAccountingGroup
        _hnt_материалы_сырье_и_материалы_10_01_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_келаст_продукция_собственного_производства_келаст_товары: FinancialAccountingGroup
        _hnt_товары_товары_на_складах_41_01_товары: FinancialAccountingGroup
        _hnt_услуги_услуги_через_90_товары: FinancialAccountingGroup
        _hnt_услуги_услуги_сторонних_организаций_товары: FinancialAccountingGroup
        _hnt_материалы_прочие_материалы_10_06_товары: FinancialAccountingGroup
        _hnt_материалы_топливо_10_03_товары: FinancialAccountingGroup
        _hnt_материалы_10_09_инвентарь_и_хозяйственные_принадлежности_товары: FinancialAccountingGroup
        _hnt_оборудование_оборудование_07_товары: FinancialAccountingGroup
        _hnt_материалы_спецодежда_на_складах_10_10_товары: FinancialAccountingGroup
        _hnt_материалы_строительные_материалы_10_08_товары: FinancialAccountingGroup
        _hnt_материалы_покупные_полуфабрикаты_и_комплектующие_изделия_конструкции_и_детали_10_02_товары: FinancialAccountingGroup
        _hnt_компоненты_ос_компоненты_основных_средств_08_04_1_ос: FinancialAccountingGroup
        _hnt_материалы_тара_и_тарные_материалы_10_04_товары: FinancialAccountingGroup
        _hnt_услуги_услуги_через_91_товары: FinancialAccountingGroup
        _hnt_материалы_10_05_запасные_части_товары: FinancialAccountingGroup
        _hnt_полуфабрикаты_полуфабрикаты_21_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_рудтех_продакшн_продукция_собственного_производства_рудтех_продакшн_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_келаст_продукция_собственного_производства_келаст_спецодежда_для_пауэрза_таткуза_10_10_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_пауэрз_продукция_собственного_производства_пауэрз_перепродажа_келаст_через_41_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_келаст_продукция_собственного_производства_келаст_тара_для_пауэрза_10_04_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_келаст_продукция_собственного_производства_келаст_прочие_материалы_для_пауэрза_таткуза_10_06_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_келаст_продукция_собственного_производства_келаст_инвентарь_для_пауэрза_10_09_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_келаст_продукция_собственного_производства_келаст_перепродажа_пауэрз_таткуз_через_41_товары: FinancialAccountingGroup
        _hnt_товары_товары_41_01_компоненты_ос_08_в_рудтех_продакшн_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_пауэрз_продукция_собственного_производства_пауэрз_компоненты_ос_келаст_через_08_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_пауэрз_продукция_собственного_производства_пауэрз_инвентарь_в_рудтехпродакшн_10_09_товары: FinancialAccountingGroup
        _hnt_товары_товары_41_01_компоненты_ос_08_в_пауэрз_отгрузка_через_91_сч_товары: FinancialAccountingGroup
        _hnt_материалы_материалы_основные_10_01_через_41_90_в_тузуксе_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_келаст_продукция_собственного_производства_келаст_инвентарь_для_рудтехпродакшн_10_09_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_пауэрз_продукция_собственного_производства_пауэрз_прочее_в_рудтехпродакшн_10_06_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_пауэрз_продукция_собственного_производства_пауэрз_ос_в_рудтехпродакшн_08_товары: FinancialAccountingGroup
        _hnt_товары_товары_41_01_компоненты_ос_08_в_келаст_отгрузка_через_90_сч_товары: FinancialAccountingGroup
        _hnt_материалы_тара_10_04_через_43_90_в_келасте_на_складах_гот_продукции_товары: FinancialAccountingGroup
        _hnt_товары_товары_41_01_компоненты_ос_08_в_хп_отгрузка_через_91_сч_товары: FinancialAccountingGroup
        _hnt_товары_товары_41_01_компоненты_ос_08_в_пауэрз_отгрузка_через_91_сч_без_искл_товары: FinancialAccountingGroup
        _hnt_товары_товары_41_01_отгрузка_через_91_сч_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_пауэрз_продукция_собственного_производства_пауэрз_перепродажа_келаст_таткуз_через_10_06_товары: FinancialAccountingGroup
        _hnt_товары_товары_41_01_компоненты_ос_08_в_ук_хп_отгрузка_через_90_сч_товары: FinancialAccountingGroup
        _hnt_продукция_собственного_производства_таткуз_продукция_собственного_производства_таткуз_товары: FinancialAccountingGroup

    @classmethod
    def init_data(cls):
        req_text = f"""
ВЫБРАТЬ
    УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ГруппыФинансовогоУчетаНоменклатуры.Ссылка) КАК ref_key,
    ГруппыФинансовогоУчетаНоменклатуры.Родитель.Представление КАК Родитель,

    ГруппыФинансовогоУчетаНоменклатуры.Наименование КАК Наименование,
    ГруппыФинансовогоУчетаНоменклатуры.ЭтоГруппа КАК ЭтоГруппа,

    ГруппыФинансовогоУчетаНоменклатуры.ВидЦенностиНДС КАК ВидЦенностиНДС
ИЗ
    Справочник.ГруппыФинансовогоУчетаНоменклатуры КАК ГруппыФинансовогоУчетаНоменклатуры
ГДЕ
    ГруппыФинансовогоУчетаНоменклатуры.ЭтоГруппа = ЛОЖЬ
    И ГруппыФинансовогоУчетаНоменклатуры.ПометкаУдаления = ЛОЖЬ
        """
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, FinancialAccountingGroup, {'name': 'Наименование',
                                                            'parent': 'Родитель',
                                                            'value_type': 'ВидЦенностиНДС',
                                                            'group': 'ЭтоГруппа',
                                                    'ref_key': 'ref_key'})


def ___________resource_specification____________():
    pass


@dataclass
class ResourceSpecificationInitData:
    # Инициализация данных
    SubdivisionsData.init_data()
    GroupResData.init_data()
    VariationsrespecificationdocumentsData.init_data()
    TheMethodOfAllocatingTheCostOfTheOutputProductsData.init_data()
    ArticulationArticlesData.init_data()
    MethodOfObtainingMaterialspecificationsData.init_data()
    TypeOfWorkData.init_data()


# --- Главный класс ---
@dataclass
class ResourceSpecification:
    hat: ResourceHeader
    stages: List[Stage] = field(default_factory=list)

    def add_stage(self, stage: Stage):
        self.stages.append(stage)

    def to_dict(self) -> dict:
        """Структура полностью совместимая с JSON для РесурсныхСпецификаций 1С"""
        rez = {
            "hat": {
                "ОсновноеИзделиеКод": self.hat.ОсновноеИзделиеКод.Код,
                "КоличествоУпаковок": self.hat.КоличествоУпаковок,
                "Наименование ресурсной": self.hat.Наименование,
                "ТекущийПользователь": self.hat.ТекущийПользователь.name,
                "НачалоДействия": F.dateStrToStr(self.hat.ДатаНачала,"%Y-%m-%d","%Y%m%d"),
                "КонецДействия": F.dateStrToStr(self.hat.ДатаОкончания,"%Y-%m-%d","%Y%m%d"),
                "Сохранять": self.hat.Сохранять,
                "ИмяБазы": self.hat.ИмяБазы,
                "КластерСерверов": self.hat.КластерСерверов,
                "ПодразделениеДиспетчер": self.hat.ПодразделениеДиспетчер.code,
                "ВыпускПроизвольнымиПорциями": self.hat.ВыпускПроизвольнымиПорциями,
                "РодительКод": self.hat.РодительКод.code,
                "ВариантПодбораВДокументы": self.hat.ВариантПодбораВДокументы.order,
                "СпособРаспределенияЗатратНаВыходныеИзделия": self.hat.СпособРаспределенияЗатрат.order,
                "Описание": self.hat.Описание,
                "Код": self.hat.Код
            },
            "data": [
                {
                    "Этап": stage.НаименованиеЭтапа,
                    "Данные": {
                        "Опер_наименование_подразделения": stage.Данные.Подразделение.name,
                        "Материалы": [
                            {
                                "Мат_код": m.КодНоменклатуры,
                                "Мат_норма": m.Количество,
                                "Материалы_Статья_калькуляции": m.СтатьяКалькуляции.name,
                                "Способы_получения_материала": m.СпособПолучения.order,
                                "ИсточникПолученияПолуфабриката": m.ИсточникПолученияПолуфабриката.code,
                            } for m in stage.Данные.Материалы
                        ],
                        "Трудозатраты": {
                            lc.ВидРабот.ref_key: lc.Количество
                            for lc in stage.Данные.Трудозатраты
                        },
                        "ДлительностьЭтапа": stage.Данные.ДлительностьМинут
                    }
                }
                for stage in self.stages
            ]
        }
        return rez

    def to_json(self, ensure_ascii=False, indent=2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)

    def send(self,msg=True,return_err=False) -> dict|bool|tuple[bool|list]:
        ERP_base_name = self.hat.ИмяБазы
        code, answ = APIERP.post_res_json(self.to_dict(), ERP_base_name)
        if code == 200:
            if return_err:
                return True, answ
            else:
                return answ
        else:
            if msg:
                CQT.msgbox(f'Ошибка создания ресурсной. Код {code}\n{answ["Ошибки"]}')
        if return_err:
            return False, answ["Ошибки"]
        else:
            return False


def ___________nomen____________():
    pass


@dataclass
class NomenclatureInitData:
    # Инициализация данных
    NDS_ratesData.init_data()
    TypeNomenData.init_data()
    VidNomemData.init_data()
    GruopNomenData.init_data()
    AccessGroupData.init_data()
    SalesOptionsData.init_data()
    PackagingUnitsData.init_data()
    NomenAnalysisGroupsData.init_data()
    FinancialAccountingGroupData.init_data()

class Nomenclature():
    def __init__(self,
            Наименование:  str = None,
            Артикул: None | str = None,
            ТипНоменклатуры:  TypeNomen = None,
            Группа: None | GruopNomen = None,
            ВидНоменклатуры: VidNomem = None,
            ВариантОформленияПродажи: SalesOptions = None,
            ГруппаДоступа:  AccessGroup = None,
            ЕдиницаИзмерения: PackagingUnits = None,
            ЕдиницаДляОтчетов:  PackagingUnits = None,
            СтавкаНДС:  NDS_rates = None,
            ГруппаАналитическогоУчета:  NomenAnalysisGroups = None,
            ГруппаФинансовогоУчета:  FinancialAccountingGroup = None,

                  ):
        self.Наименование:None|str = str(Наименование)
        self.Артикул:None|str = str(Артикул)
        self.ТипНоменклатуры:None|TypeNomen = ТипНоменклатуры
        self.Группа:None|GruopNomen = Группа
        self.ВидНоменклатуры:None|VidNomem = ВидНоменклатуры
        self.ТипНоменклатуры:None|TypeNomen = ТипНоменклатуры
        self.ВариантОформленияПродажи:None|SalesOptions = ВариантОформленияПродажи
        self.ГруппаДоступа:None|AccessGroup = ГруппаДоступа
        self.ЕдиницаИзмерения:None|PackagingUnits = ЕдиницаИзмерения
        self.ЕдиницаДляОтчетов:None|PackagingUnits = ЕдиницаДляОтчетов
        self.СтавкаНДС:None|NDS_rates = СтавкаНДС
        self.ГруппаАналитическогоУчета:None|NomenAnalysisGroups = ГруппаАналитическогоУчета
        self.ГруппаФинансовогоУчета:None|FinancialAccountingGroup = ГруппаФинансовогоУчета


    def check_data(self)->tuple[bool,list[str]]:
        list_err = []
        succ = True
        if len(self.Артикул) > 50:
            list_err.append(f'len(self.Артикул) > 50')
            succ = False
        if len(self.Наименование) > 150:
            list_err.append(f'len(self.Наименование) > 150')
            succ = False
        if len(self.Наименование.strip()) == '' :
            list_err.append(f'len(self.Наименование) == ""')
            succ = False
        if not isinstance(self.ТипНоменклатуры,TypeNomen):
            list_err.append(f'not isinstance(self.ТипНоменклатуры,TypeNomen)')
            succ = False
        if not isinstance(self.ВариантОформленияПродажи,SalesOptions):
            list_err.append(f'not isinstance(self.ВариантОформленияПродажи,SalesOptions)')
            succ = False
        if not isinstance(self.ГруппаДоступа,AccessGroup):
            list_err.append(f'not isinstance(self.ГруппаДоступа,AccessGroup)')
            succ = False
        if not isinstance(self.ЕдиницаИзмерения,PackagingUnits):
            list_err.append(f'not isinstance(self.ЕдиницаИзмерения,PackagingUnits)')
            succ = False
        if not isinstance(self.ЕдиницаДляОтчетов,PackagingUnits):
            list_err.append(f'not isinstance(self.ЕдиницаДляОтчетов,PackagingUnits)')
            succ = False
        if not isinstance(self.СтавкаНДС,NDS_rates):
            list_err.append(f'not isinstance(self.СтавкаНДС,NDS_rates)')
            succ = False
        if not isinstance(self.ГруппаАналитическогоУчета,NomenAnalysisGroups):
            list_err.append(f'not isinstance(self.ГруппаАналитическогоУчета,NomenAnalysisGroups)')
            succ = False
        if not isinstance(self.ГруппаФинансовогоУчета,FinancialAccountingGroup):
            list_err.append(f'not isinstance(self.ГруппаФинансовогоУчета,FinancialAccountingGroup)')
            succ = False
        if not isinstance(self.Группа, GruopNomen) and self.Группа is not None :
            list_err.append(f'not isinstance(self.Группа,GruopNomen)')
            succ = False
        if not isinstance(self.ВидНоменклатуры,VidNomem):
            list_err.append(f'not isinstance(self.ВидНоменклатуры,VidNomem)')
            succ = False
        return succ, list_err


    @CQT.onerror
    def create_nomen(self):
        """
                dict_nomen = {'Наименование': self.Наименование,
                      'Артикул': self.Артикул,
                      'ТипНоменклатуры': 'Товар',
                      'ВариантОформленияПродажи': 'РеализацияТоваровУслуг',
                      'ГруппаДоступа': 'Продукция Пауэрз для Эластика',
                      'ЕдиницаИзмерения': 'Штука',
                      'ЕдиницаДляОтчетов': 'Штука',

                      'СтавкаНДС': '20%',
                      'ГруппаАналитическогоУчета': 'Металлоизделия',
                      'ГруппаФинансовогоУчета': 'Продукция собственного производства (Пауэрз)',
                      }
        :return:
        """

        succ, data = self.check_data()#TODO init
        if not succ:
            return  False, data

        dict_nomen = {'Наименование': self.Наименование,
                      'ТипНоменклатуры': self.ТипНоменклатуры.order,
                      'ВариантОформленияПродажи': self.ВариантОформленияПродажи.order,
                      'ГруппаДоступа': self.ГруппаДоступа.ref_key,
                      'ЕдиницаИзмерения': self.ЕдиницаИзмерения.ref_key,
                      'ЕдиницаДляОтчетов': self.ЕдиницаДляОтчетов.ref_key,
                      'СтавкаНДС': self.СтавкаНДС.ref_key,
                      'ГруппаАналитическогоУчета': self.ГруппаАналитическогоУчета.ref_key,
                      'ГруппаФинансовогоУчета': self.ГруппаФинансовогоУчета.ref_key,
                      'ВидНоменклатуры': self.ВидНоменклатуры.ref_key,
                      'ГруппаФинансовогоУчета': self.ГруппаФинансовогоУчета.ref_key,
                      'ИспользованиеХарактеристик': 'НеИспользовать',
                      }
        if self.Артикул:
            dict_nomen['Артикул'] = self.Артикул
        if self.Группа:
            dict_nomen['Родитель'] =  self.Группа.ref_key
        

        code, data = APIERP.make_nomen(dict_nomen)
        if code != 200:
            return False, data
        new_cod = data["Код"]
        return True, data




def test_fnc():
    ПодразделениеДиспетчер = SubdivisionsData._hnt_производственные_подразделения_келаст_келаст_00_000129
    РодительКод = GroupResData._hnt_литье_таткуз_00_058862
    ВариантПодбораВДокументы = VariationsrespecificationdocumentsData._hnt_вручную_1
    СпособРаспределенияЗатратНаВыходныеИзделия = TheMethodOfAllocatingTheCostOfTheOutputProductsData._hnt_по_долям_стоимости_0
    # Шапка
    hat = ResourceHeader(
        ОсновноеИзделиеКод=MainProduct.find_by_code("00-00157077"),
        Наименование="Корпус насоса литой",
        ТекущийПользователь=CurrentUser(F.user_full_namre()),
        ДатаНачала="2025-08-14",
        ДатаОкончания="2025-08-21",
        ПодразделениеДиспетчер=ПодразделениеДиспетчер,
        РодительКод=РодительКод,
        ВариантПодбораВДокументы=ВариантПодбораВДокументы,
        Описание='',
        СпособРаспределенияЗатратНаВыходныеИзделия=СпособРаспределенияЗатратНаВыходныеИзделия
    )
    ОсновнойФОТ = ArticulationArticlesData._hnt_основной_фот
    СпособПолучения = MethodOfObtainingMaterialspecificationsData.find_by_ref("5c796eb7-92d0-494a-aad9-76cf7a28b3dd")
    СпособПолучения = MethodOfObtainingMaterialspecificationsData.find_by_name("Обеспечивать")

    # Этап
    Подразделение = SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
    stage_data = StageData(
        Подразделение=Подразделение,
        ДлительностьМинут='1440'
    )
    ИсточникПолученияПолуфабриката = SourceOfTheHalffactoryReceipt.find_by_code('00-058859')

    # Материалы
    mat1 = Material("M001", 5.0, ArticulationArticlesData.find_by_name('Сырье'), СпособПолучения, ИсточникПолученияПолуфабриката)
    mat2 = Material("M002", 0.2, ОсновнойФОТ, СпособПолучения)
    ВидРабот = TypeOfWorkData.find_by_name('формовка')
    # Трудозатраты
    labor = LaborCost(ВидРабот, 73)

    stage_data.add_material(mat1)
    stage_data.add_material(mat2)

    stage_data.add_labor(labor)

    stage = Stage("Литье", stage_data)

    # Итог
    spec = ResourceSpecification(hat)
    spec.add_stage(stage)

    print(spec.to_json())


if __name__ == '__main__':
    #test_fnc()
    pass