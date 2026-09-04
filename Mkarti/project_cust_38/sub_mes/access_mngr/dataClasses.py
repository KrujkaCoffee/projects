from __future__ import annotations

import datetime

if __name__ == "__main__":
    quit()

from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import dynamic_db_models as DDM
from project_cust_38 import Cust_orm as CORM

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main_mngr import CentralWindown

    from project_cust_38.dynamic_db_models.orm_models import Подразделения as orm_Подразделения
    from project_cust_38.dynamic_db_models.orm_models import ФизическиеЛица as orm_ФизическиеЛица
    from project_cust_38.dynamic_db_models.orm_models import КадроваяИстория as orm_КадроваяИстория
    from project_cust_38.Cust_mes import ManagerAccess


class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]


class ReferenceStore():
    DICT_Подразделения_by_ref: dict[str, orm_Подразделения] | None = None
    DICT_ФизическиеЛица_by_ref: dict[str, orm_ФизическиеЛица] | None = None
    DICT_КадроваяИстория_by_ref: dict[str, orm_КадроваяИстория] | None = None

    @classmethod
    def load_data_reference(cls):
        cls.DICT_Подразделения_by_ref = DDM.Подразделения.object_manager.all().deploy_dict(
            DDM.Подразделения.Подразделение_Key)
        cls.DICT_ФизическиеЛица_by_ref = DDM.ФизическиеЛица.object_manager.all().deploy_dict(
            DDM.ФизическиеЛица.ФизическоеЛицо_Key)
        cls.DICT_КадроваяИстория_by_ref = DDM.КадроваяИстория.object_manager.all().group_by(
            DDM.КадроваяИстория.ФизическоеЛицо_Key.name, mode=CORM.GroupByTypes.LAST)


class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    CONFIG: CFG.Config = CFG.Config
    sub_self: CentralWindown = None
    app_self = None
    mngr_acess:ManagerAccess = None
    filtred_r:str = None
    filtred_u:tuple[int,str] = None


    @classmethod
    def init_data(cls):
        pass
