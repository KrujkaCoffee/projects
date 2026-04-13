from __future__ import annotations
if __name__ == "__main__":
    quit()
from typing import  TYPE_CHECKING
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
from project_cust_38 import Cust_Functions as F
import project_cust_38.Cust_mes as CMS
if TYPE_CHECKING:
    from arm_ww import mywindow
    import main_classes as CLSS
    import main_classes as MCL
    from project_cust_38 import Cust_config as CFG
class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]



class data_app(SingletonMeta):
    app_self:mywindow = None
    storages:MCL.Storages = None
    tbl_details:MCL.Details = None
    dateFiltr:MCL.DateFiltr = None
    # пользовательская конфигурация
    USER_CONFIG: CFG.User_config | None = None
    place: CFG.Place | None = None
    project: CFG.ProjectConfig | None = None
    APP_ARGS: dict | None = None
    lazy_time_munutes:int = 5
    params_doc:CLSS.Params_doc = None
    pline:CQT.Cust_plane_edit =None
