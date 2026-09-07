from __future__ import annotations

import datetime

if __name__ == "__main__":
    quit()

from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import dynamic_db_models as DDM
from project_cust_38 import Cust_orm as CORM

from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from Viewer import mywindow
    from project_cust_38.competence_matrix import Competencies
    from project_cust_38.Cust_mes import Emploee_usr
    from reports_of_personal import Rules
    from reports_of_personal import Events
    from reports_of_personal import Regime
    from project_cust_38.dynamic_db_models.orm_models import Подразделения as orm_Подразделения
    from project_cust_38.dynamic_db_models.orm_models import ФизическиеЛица as orm_ФизическиеЛица
    from project_cust_38.dynamic_db_models.orm_models import КадроваяИстория as orm_КадроваяИстория
    from project_cust_38.Cust_mes import Jurnal_nar

class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]

def load_user_report_periods():
    periods = CSQ.custom_request_c(CFG.Config.project.db_users,f"""SELECT id,
           name,
           date_time_liter,
           priority
      FROM user_report_periods;
    """,rez_dict=True)
    return periods
def load_user_report_doc_types():
    doc_types = CSQ.custom_request_c(CFG.Config.project.db_users,f"""SELECT id,
       name,
       file_extension
  FROM user_report_doc_types;
    """,rez_dict=True)
    return doc_types


class data_repots_of_personal(SingletonMeta):
    user_report_periods: list[dict] | None = load_user_report_periods()
    user_report_doc_types: list[dict] | None = load_user_report_doc_types()
    user_report_rules: Rules | None = None
    selected_user: Emploee_usr | None = None
    creator_user: Emploee_usr | None = None
    selected_user_events: Events | None = None
    regime: Regime | None = None
    date_start_report:datetime.datetime| None = None
    date_end_report:datetime.datetime| None = None

class data_arm_oper(SingletonMeta):
    #===============ARM_OPER_PR========================================
    current_row_jurnal:dict = None
    current_jur_obj:Jurnal_nar = None

class ReferenceStore():
    DICT_Подразделения_by_ref: dict[str, orm_Подразделения] | None = None
    DICT_ФизическиеЛица_by_ref: dict[str, orm_ФизическиеЛица] | None = None
    DICT_КадроваяИстория_by_ref: dict[str, orm_КадроваяИстория] | None = None
    DICT_ФизическиеЛица_by_FIO: dict[str, orm_ФизическиеЛица] | None = None


class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    CONFIG:CFG.Config = CFG.Config
    app_self: mywindow | None = None
    _old_val_cell = None
    obj_Competencies:Competencies|None = None
    empl_obj: Emploee_usr | None = None
    module_repots_of_personal: data_repots_of_personal | None = data_repots_of_personal

    module_arm_oper: data_arm_oper | None = data_arm_oper
    ReferenceStore: ReferenceStore = ReferenceStore()

    @classmethod
    def load_data_main(cls):
        cls.ReferenceStore.DICT_Подразделения_by_ref = DDM.Подразделения.object_manager.all().deploy_dict(
            DDM.Подразделения.Подразделение_Key)
        cls.ReferenceStore.DICT_ФизическиеЛица_by_ref = DDM.ФизическиеЛица.object_manager.all().deploy_dict(
            DDM.ФизическиеЛица.ФизическоеЛицо_Key)
        cls.ReferenceStore.DICT_КадроваяИстория_by_ref = DDM.КадроваяИстория.object_manager.all().group_by(
            DDM.КадроваяИстория.ФизическоеЛицо_Key.name, mode= CORM.GroupByTypes.LAST )
        cls.ReferenceStore.DICT_ФизическиеЛица_by_FIO = DDM.ФизическиеЛица.object_manager.all().deploy_dict(
            DDM.ФизическиеЛица.Наименование)