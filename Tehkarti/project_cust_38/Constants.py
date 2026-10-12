import os
import typing
from collections import UserString
import dataclasses

__all__ = [
    'Servers',
]





@dataclasses.dataclass
class CFG:
    # IP = '192.168.50.208'# AG local
    IP = 'mesinfo.powerz.ru'  # server domain  ip = '192.168.50.44'# server
    # IP = '192.168.17.149'# AF local

    IS_SERVER = os.environ.get('MES_IS_SERVER')
    # -------------------------------------------------------------------------
    # Общие настройки
    # -------------------------------------------------------------------------
    Stile: str = 'windowsvista,Fusion,Windows'
    company: str = 'Powerz'
    limit_k: str = '3'
    limit_o: str = '10'
    limit_p: str = '5'
    ogran_shir: str = '190'
    blok_pr_norm: str = '1'

    # -------------------------------------------------------------------------
    # общие каталоги
    # -------------------------------------------------------------------------
    setup: str = 'Z:\\MES_setup'
    dir_list_prog: str = 'Z:\\MES_setup'
    BDact: str = 'Z:\\Data'
    BD_selector: str = 'Z:\\Data'
    data_f: str = 'Z:\\Data'
    mag: str = 'Z:\\Data'
    db_dse: str = 'Z:\\Data'
    DB_staff_placement: str = 'Z:\\Data'

    # -------------------------------------------------------------------------
    # Маршрутные карты
    # -------------------------------------------------------------------------
    mk_data: str = 'Z:\\Data\\MKart\\data'
    bd_mk: str = 'Z:\\Data\\MKart\\data'
    Mk: str = 'Z:\\Data\\MKart\\data'

    # -------------------------------------------------------------------------
    # Техкарты
    # -------------------------------------------------------------------------
    add_docs: str = 'Z:\\Data\\TehKart\\Data\\docs'
    pickle: str = 'Z:\\Data\\TehKart\\Data\\docs'
    cash: str = 'Z:\\Data\\TehKart\\Data\\bin'
    oper: str = 'Z:\\Data\\TehKart\\Data\\bin'
    liter: str = 'Z:\\Data\\TehKart\\Data\\bin'
    bd_prof: str = 'Z:\\Data\\TehKart\\Data\\bin'
    vivod_tk: str = 'Z:\\Data\\TehKart\\Vivod'
    td: str = 'Z:\\Data\\TehKart\\MES_инструкции'

    # -------------------------------------------------------------------------
    # Создание / выполнение
    # -------------------------------------------------------------------------
    Riba: str = 'Z:\\Data\\Выполнение\\Data'
    Opoveshenie: str = 'Z:\\Data\\Выполнение\\Data'
    Etapi: str = 'Z:\\Data\\Создание\\Data'
    Filtr_rab: str = 'Z:\\Data\\Создание\\Data'
    FiltrEmpDel: str = 'Z:\\Data\\Создание\\Data'
    FiltrEmp: str = 'Z:\\Data\\Создание\\Data'
    Opovesh: str = 'Z:\\Data\\Создание\\Data'
    FiltrEmp_vypolnenie: str = 'Z:\\Data\\Выполнение\\Data'
    Opovesh_vypolnenie: str = 'Z:\\Data\\Выполнение\\Data'


    BD_Proect: str = 'Z:\\Data\\бд_проекты'
    Puti_pr: str = 'O:\\Производство Powerz'
    employee: str = 'O:\\Журналы и графики\\Ведомости для передачи'
    ko_ii: str = 'O:\\Журналы и графики\\КРО\\Журнал учета КРО форма ПЗ-СТО-12 Ф-04.xlsx'
    defolt_fold: str = 'O:\\Производство Powerz\\Отдел технолога\\ТД'

    # -------------------------------------------------------------------------
    # ОТК / POB
    # -------------------------------------------------------------------------
    foto_brak: str = 'Z:\\Data\\POB\\Config\\docs'
    foto_brak_test: str = 'Z:\\Data\\Тест БотОТК\\Config\\docs'

    # -------------------------------------------------------------------------
    # Viewer / CSV
    # -------------------------------------------------------------------------
    files_tmp: str = 'Z:\\Data\\viewer'
    BD_vo: str = 'Z:\\Data\\CSV'

    # -------------------------------------------------------------------------
    # Серверные БД
    # -------------------------------------------------------------------------
    nomenklatura_erp: str = 'SRV:DB_nomenklatura_erp.db' # todo перенести
    BD_dse: str = 'SRV:BD_dse.db'
    DB_invest: str = 'SRV:DB_invest.db'
    db_resxml: str = 'SRV:BD_resxml.db'
    DB_kplan: str = 'SRV:DB_kplan.db'
    BD_users: str = 'SRV:BD_users.db'
    Users: str = 'SRV:BD_users.db'
    files: str = 'SRV:BD_files.db'
    BD_files: str = 'SRV:BD_files.db'
    Naryad: str = 'SRV:Naryad.db'


class _ServerItem(UserString):
    alias: str                                  # "Naryad.db"
    absolute_path: str                          # "C://DB_srv//Naryad.db"
    port: typing.Union[int, str, None] = None   # 20002

    def __init__(self, alias: str, absolute_path: str = '', port: typing.Union[int, str, None] = None):
        super().__init__(f'SRV:{alias}')
        self.alias = alias
        self.absolute_path = absolute_path
        self.port = port
        self.attribute_name = None


class _ClassDict(type):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if "__annotations__" in dct:
            annotations = dct["__annotations__"]
        else :
            import annotationlib
            annotate = annotationlib.get_annotate_from_class_namespace(dct)
            annotationlib.get_annotate_from_class_namespace(dct)
            annotations = annotationlib.call_annotate_function(
                annotate,
                format=annotationlib.Format.STRING,
            )
        cls._declared_attrs = {
            k: dct.get(k)
            for k in annotations
        }
        cls.__by_alias = {}
        cls.__iter = []
        cls.__by_name = {}
        for name, attr in cls._declared_attrs.items():
            if isinstance(attr, _ServerItem):
                cls.__by_alias[attr.alias] = attr
                cls.__iter.append(attr)
                attr.attribute_name = name
            cls.__by_name[name] = attr

    def __getitem__(cls, item):
        return cls.__by_alias.get(item) or cls.__by_name.get(item)

    def __iter__(self) -> typing.Iterator[_ServerItem]:
        return iter(self.__iter)


class Servers(metaclass=_ClassDict):

    db_naryad: _ServerItem = _ServerItem(alias='Naryad.db', absolute_path='C://DB_srv//Naryad.db', port=20002)
    db_dse: _ServerItem = _ServerItem(alias='BD_dse.db', absolute_path='C://DB_srv//BD_dse.db', port=20003)
    db_resxml: _ServerItem = _ServerItem(alias='BD_resxml.db', absolute_path='C://DB_srv//BD_resxml.db', port=20005)
    db_files: _ServerItem = _ServerItem(alias='BD_files.db', absolute_path='C://DB_srv//BD_files.db', port=20006)
    db_kplan: _ServerItem = _ServerItem(alias='DB_kplan.db', absolute_path='C://DB_srv//DB_kplan.db', port=20007)
    db_users: _ServerItem = _ServerItem(alias='BD_users.db', absolute_path='C://DB_srv//BD_users.db', port=20009)
    db_nomen: _ServerItem = _ServerItem(alias='DB_nomenklatura_erp.db', absolute_path='C://DB_srv//DB_nomenklatura_erp.db', port=20010)
    db_flet: _ServerItem = _ServerItem(alias='db_flet.db', absolute_path='C://DB_srv//db_flet.db', port=20014)

    xl_formulas: _ServerItem = _ServerItem(alias='DB_xl_formulas.db', port=20012)
    mes_api: _ServerItem = _ServerItem(alias='MES_api', port=20011)


CFG = CFG() # Замена глобального имени класса


