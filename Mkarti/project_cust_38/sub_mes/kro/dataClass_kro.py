from __future__ import annotations

import datetime

if __name__ == "__main__":
    quit()

from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_SQLite as CSQ
from typing import  TYPE_CHECKING
from project_cust_38 import dynamic_db_models as DDM
from project_cust_38 import Cust_orm as CORM
if TYPE_CHECKING:
    from project_cust_38.Cust_mes import Emploee_usr
    from project_cust_38.sub_mes.kro.manage_kro import (Kros, Kro, Krowindow, Result_states, States_agreement,
                                                        Agreement, Regime, Alerts)
    from project_cust_38.dynamic_db_models.orm_models import KroCauses as orm_KroCauses
    from project_cust_38.dynamic_db_models.orm_models import Подразделения as orm_Подразделения
    from project_cust_38.dynamic_db_models.orm_models import ФизическиеЛица as orm_ФизическиеЛица
    from project_cust_38.dynamic_db_models.orm_models import КадроваяИстория as orm_КадроваяИстория

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
    DICT_KroCauses: dict[int, orm_KroCauses] | None = None
    DICT_КадроваяИстория_by_ref: dict[str, orm_КадроваяИстория] | None = None

class data_manage_kro(SingletonMeta):
    kros: Kros|None = None
    alerts: Alerts|None = None
    regime: Regime|None = None
    current_main_elem:str|None=None
    current_kro_o:Kro|None=None
    current_agreement_o:Agreement|None=None
    self_ui:Krowindow|None = None
    filter_mk:list|int|None = None
    result_states:Result_states|None = None
    states_agreement:States_agreement|None = None
    agreements_list:list[Agreement]|None= None


class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    CONFIG:CFG.Config = CFG.Config
    app_self: mywindow | None = None
    module_manage_kro: data_manage_kro | None = data_manage_kro
    ReferenceStore:ReferenceStore = ReferenceStore()

    @classmethod
    def load_data_main(cls):
        cls.ReferenceStore.DICT_KroCauses = DDM.KroCauses().object_manager.all().deploy_dict(
            DDM.KroCauses.pk_name())
        cls.ReferenceStore.DICT_Подразделения_by_ref = DDM.Подразделения.object_manager.all().deploy_dict(
            DDM.Подразделения.Подразделение_Key)
        cls.ReferenceStore.DICT_ФизическиеЛица_by_ref = DDM.ФизическиеЛица.object_manager.all().deploy_dict(
            DDM.ФизическиеЛица.ФизическоеЛицо_Key)
        cls.ReferenceStore.DICT_КадроваяИстория_by_ref = DDM.КадроваяИстория.object_manager.all().group_by(
            DDM.КадроваяИстория.ФизическоеЛицо_Key.name, mode= CORM.GroupByTypes.LAST )
    @classmethod
    def init_data(cls):
        cls.load_data_main()