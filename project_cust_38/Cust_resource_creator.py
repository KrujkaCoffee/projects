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

    def send(self) -> dict|bool:
        ERP_base_name = self.hat.ИмяБазы
        code, answ = APIERP.post_res_json(self.to_dict(), ERP_base_name)
        if code == 200:
            return answ
        else:
            CQT.msgbox(f'Ошибка создания ресурсной. Код {code}\n{answ["Ошибки"]}')
        return False

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
        if issubclass(default, Exception):
            raise ValueError(f'Не найдено {cls.NAME_ERP_OBJ} = `{attr}` из ERP')
        return default

    @classmethod
    def find_by_code(cls, code: str, default=ValueError):
        return cls.__find_by(code,'code',default)

    @classmethod
    def find_by_ref(cls, ref_key: str, default=ValueError):
        return cls.__find_by(ref_key, 'ref_key', default)

    @classmethod
    def find_by_name(cls, name: str, default=ValueError):
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
                СтатьиКалькуляции.Родитель.Наименование КАК РодительПредставление
            ИЗ
                Справочник.СтатьиКалькуляции КАК СтатьиКалькуляции
            ГДЕ
                СтатьиКалькуляции.ЭтоГруппа = ЛОЖЬ
                И СтатьиКалькуляции.ПометкаУдаления = ЛОЖЬ"""
        data_erp = cls._get_data_erp(req_text)
        cls._fill_data(data_erp, ArticulationArticles, {'name': 'Наименование', 'parent': 'РодительПредставление'})




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


def test_fnc():
    ПодразделениеДиспетчер = SubdivisionsData._hnt_сталелитейный_цех_кбж_кбж_00_000157

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
    test_fnc()
