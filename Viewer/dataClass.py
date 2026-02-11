from __future__ import annotations

import datetime

if __name__ == "__main__":
    quit()

from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_SQLite as CSQ
from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from Viewer import mywindow
    from project_cust_38.competence_matrix import Competencies
    from project_cust_38.Cust_mes import Emploee_usr
    from reports_of_personal import Rules
    from reports_of_personal import Events
    from reports_of_personal import Regime
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
    current_user: Emploee_usr | None = None
    creator_user: Emploee_usr | None = None
    current_user_events: Events | None = None
    regime: Regime | None = None
    date_start_report:datetime.datetime| None = None
    date_end_report:datetime.datetime| None = None
class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    app_self: mywindow | None = None
    _old_val_cell = None
    obj_Competencies:Competencies|None = None
    empl_obj: Emploee_usr | None = None
    module_repots_of_personal: data_repots_of_personal | None = data_repots_of_personal
