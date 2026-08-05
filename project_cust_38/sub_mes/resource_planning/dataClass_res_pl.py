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
    from  PyQt5.QtWidgets import QFrame
    from project_cust_38.sub_mes.resource_planning.manage_res_pl import (Plwindow,)
    from project_cust_38.sub_mes.resource_planning.clses import  (ShablonsRes,ShablonsEve,Type_entity,SubjectPl,
                                                                  Info,Resources,Events,Crosses,UserConfigSubPlan,
                                                                  CustomTypes)

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
    DICT_КадроваяИстория_by_ref: dict[str, orm_КадроваяИстория] | None = None

class data_manage_sub_app(SingletonMeta):
    sub_self:Plwindow|None = None
    subj_pl:SubjectPl|None = None
    fr_ev:QFrame|None = None
    fr_res:QFrame|None = None
    current_settings_mode:Type_entity|None = None
    shablons_res:ShablonsRes = None
    shablons_eve:ShablonsEve = None
    info_o: Info = None
    resources:Resources  = None
    events:Events  = None
    current_focus_type:str = None
    tmp_overlay = None
    crosses: Crosses = None
    filtr_cross_by_res: int|None = None
    filtr_cross_by_eve: int|None = None
    user_config_sub_plan: UserConfigSubPlan = None
    custom_types: CustomTypes = None

class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    CONFIG:CFG.Config = CFG.Config
    app_self: Plwindow | None = None
    curren_frame = None
    module_manage_sub_app: data_manage_sub_app | None = data_manage_sub_app
    ReferenceStore:ReferenceStore = ReferenceStore()



    @classmethod
    def load_data_main(cls):
        cls.ReferenceStore.DICT_Подразделения_by_ref = DDM.Подразделения.object_manager.all().deploy_dict(
            DDM.Подразделения.Подразделение_Key)
        cls.ReferenceStore.DICT_ФизическиеЛица_by_ref = DDM.ФизическиеЛица.object_manager.all().deploy_dict(
            DDM.ФизическиеЛица.ФизическоеЛицо_Key)
        cls.ReferenceStore.DICT_КадроваяИстория_by_ref = DDM.КадроваяИстория.object_manager.all().group_by(
            DDM.КадроваяИстория.ФизическоеЛицо_Key.name, mode= CORM.GroupByTypes.LAST )
    @classmethod
    def init_data(cls):
        pass
        #cls.load_data_main()