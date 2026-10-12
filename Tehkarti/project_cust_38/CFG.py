import os
import typing
from collections import UserString
import dataclasses

__all__ = [
    'Servers',
    'IP',
    'IS_SERVER'
]

# IP = '192.168.50.208'# AG local
IP = 'mesinfo.powerz.ru'# server domain  ip = '192.168.50.44'# server
# IP = '192.168.17.149'# AF local
IS_SERVER = os.environ.get('MES_IS_SERVER')

@dataclasses.dataclass
class CFG:
    # -------------------------------------------------------------------------
    # Общие настройки
    # -------------------------------------------------------------------------
    Stile = 'windowsvista,Fusion,Windows'
    company = 'Powerz'
    limit_k = '3'
    limit_o = '10'
    limit_p = '5'
    ogran_shir = '190'
    blok_pr_norm = '1'

    # -------------------------------------------------------------------------
    # общие каталоги
    # -------------------------------------------------------------------------
    setup = 'Z:\\MES_setup'
    dir_list_prog = 'Z:\\MES_setup'
    BDact = 'Z:\\Data'
    BD_selector = 'Z:\\Data'
    data_f = 'Z:\\Data'
    mag = 'Z:\\Data'
    db_dse = 'Z:\\Data'
    DB_staff_placement = 'Z:\\Data'

    # -------------------------------------------------------------------------
    # Маршрутные карты
    # -------------------------------------------------------------------------
    mk_data = 'Z:\\Data\\MKart\\data'
    bd_mk = 'Z:\\Data\\MKart\\data'
    Mk = 'Z:\\Data\\MKart\\data'

    # -------------------------------------------------------------------------
    # Техкарты
    # -------------------------------------------------------------------------
    add_docs = 'Z:\\Data\\TehKart\\Data\\docs'
    pickle = 'Z:\\Data\\TehKart\\Data\\docs'
    cash = 'Z:\\Data\\TehKart\\Data\\bin'
    oper = 'Z:\\Data\\TehKart\\Data\\bin'
    liter = 'Z:\\Data\\TehKart\\Data\\bin'
    bd_prof = 'Z:\\Data\\TehKart\\Data\\bin'
    vivod_tk = 'Z:\\Data\\TehKart\\Vivod'
    td = 'Z:\\Data\\TehKart\\MES_инструкции'

    # -------------------------------------------------------------------------
    # Создание / выполнение
    # -------------------------------------------------------------------------
    Riba = 'Z:\\Data\\Выполнение\\Data'
    Opoveshenie = 'Z:\\Data\\Выполнение\\Data'
    Etapi = 'Z:\\Data\\Создание\\Data'
    Filtr_rab = 'Z:\\Data\\Создание\\Data'
    FiltrEmpDel = 'Z:\\Data\\Создание\\Data'
    FiltrEmp = 'Z:\\Data\\Создание\\Data'
    Opovesh = 'Z:\\Data\\Создание\\Data'
    FiltrEmp_vypolnenie = 'Z:\\Data\\Выполнение\\Data'
    Opovesh_vypolnenie = 'Z:\\Data\\Выполнение\\Data'


    BD_Proect = 'Z:\\Data\\бд_проекты'
    Puti_pr = 'O:\\Производство Powerz'
    employee = 'O:\\Журналы и графики\\Ведомости для передачи'
    ko_ii = 'O:\\Журналы и графики\\КРО\\Журнал учета КРО форма ПЗ-СТО-12 Ф-04.xlsx'
    defolt_fold = 'O:\\Производство Powerz\\Отдел технолога\\ТД'

    # -------------------------------------------------------------------------
    # ОТК / POB
    # -------------------------------------------------------------------------
    foto_brak = 'Z:\\Data\\POB\\Config\\docs'
    foto_brak_test = 'Z:\\Data\\Тест БотОТК\\Config\\docs'

    # -------------------------------------------------------------------------
    # Viewer / CSV
    # -------------------------------------------------------------------------
    files_tmp = 'Z:\\Data\\viewer'
    BD_vo = 'Z:\\Data\\CSV'

    # -------------------------------------------------------------------------
    # Серверные БД
    # -------------------------------------------------------------------------
    nomenklatura_erp = 'SRV:DB_nomenklatura_erp.db' # todo перенести
    BD_dse = 'SRV:BD_dse.db'
    DB_invest = 'SRV:DB_invest.db'
    db_resxml = 'SRV:BD_resxml.db'
    DB_kplan = 'SRV:DB_kplan.db'
    BD_users = 'SRV:BD_users.db'
    Users = 'SRV:BD_users.db'
    files = 'SRV:BD_files.db'
    BD_files = 'SRV:BD_files.db'
    Naryad = 'SRV:Naryad.db'


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


