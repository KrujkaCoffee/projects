import argparse
import dataclasses
import typing

from cfg_types import _ServerItem, _ClassDict

__all__ = [
    "NetworkPaths"
]

@dataclasses.dataclass
class NetworkPaths(typing.Dict):
    Stile = 'windowsvista,Fusion,Windows'

    add_docs = 'Z:\\ProdSoft\\Data\\TehKart\\Data\\docs;Z:\\Data\\TehKart\\Data\\docs'
    mk_data = 'Z:\\ProdSoft\\Data\\MKart\\data;Z:\\Data\\MKart\\data'
    BD_Proect = 'Z:\\ProdSoft\\Data\\бд_проекты;Z:\\Data\\бд_проекты'
    foto_brak = 'Z:\\ProdSoft\\Data\\POB\\Config\\docs;Z:\\Data\\POB\\Config\\docs'
    Puti_pr = 'O:\\Производство Powerz'
    setup = 'Z:\\ProdSoft\\MES_setup;Z:\\MES_setup'
    BDact = 'Z:\\ProdSoft\\Data;Z:\\Data'
    BD_selector =  'Z:\\ProdSoft\\Data;Z:\\Data'
    cash = 'Z:\\ProdSoft\\Data\\TehKart\\Data\\bin;Z:\\Data\\TehKart\\Data\\bin'
    oper = 'Z:\\ProdSoft\\Data\\TehKart\\Data\\bin;Z:\\Data\\TehKart\\Data\\bin'
    DB_staff_placement = 'Z:\\ProdSoft\\Data;Z:\\Data'

    nomenklatura_erp = 'SRV:DB_nomenklatura_erp.db'
    BD_dse = 'SRV:BD_dse.db'
    DB_invest = 'SRV:DB_invest.db'
    db_resxml = 'SRV:BD_resxml.db'
    DB_kplan = 'SRV:DB_kplan.db'
    BD_users = 'SRV:BD_users.db'
    files =  'SRV:BD_files.db'
    Naryad = 'SRV:Naryad.db'

@dataclasses.dataclass(frozen=True, slots=True)
class ApplicationArguments:
    parser = argparse.ArgumentParser(description='Аргументы приложения', allow_abbrev=False)
    parser.add_argument('--user_mode', '--UserMode', '-UserMode', dest='UserMode',
                         nargs='?', const=True,
                         default=None,
                         type=str,
                         metavar='BOOL_OR_DATE',
                         help='Пользовательский режим дата ГГГГ-ММ-ДД',
                         )
    parser.add_argument(
        '--organization', '--Organization', '-Organization',
        dest='Organization',
        default=None,
        metavar='NAME',
        help='Наименование организации',
    )
    parser.add_argument(
        '--erp_base_name', '--ERP_base_name', '-ERP_base_name',
        dest='ERP_base_name',
        default=None,
        metavar='NAME',
        help='Имя базы 1С:ERP',
    )
    parser.add_argument(
        '--do_base', '--do_base_name', '--DO_base_name', '-DO_base_name',
        dest='DO_base_name',
        default=None,
        metavar='NAME',
        help='Имя базы 1С:Документооборот',
    )

    # Преднастройки
    UserMode: bool | str | None = None
    Organization: str | None = None
    ERP_base_name: str | None = None
    DO_base_name: str | None = None


class DBServers(metaclass=_ClassDict):
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