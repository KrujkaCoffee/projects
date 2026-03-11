from __future__ import annotations
if __name__ == "__main__":
    quit()
from typing import  TYPE_CHECKING
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
from project_cust_38 import Cust_Functions as F
import project_cust_38.Cust_mes as CMS
if TYPE_CHECKING:
    from vipoln import mywindow
    from project_cust_38 import Cust_config as CFG
    import groups_manage as GRM

class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]

class data_app(SingletonMeta):
    app_self:mywindow = None
    # пользовательская конфигурация
    USER_CONFIG: CFG.User_config | None = None
    place: CFG.Place | None = None
    project: CFG.ProjectConfig | None = None
    APP_ARGS: dict | None = None
    production_shift: CMS.Production_shifts|None = None
    #modules
    table_nar: list[dict]|None = None
    gr_filter_nar: GRM.Filtr_nar|None = None
    gr_prgs_bar:CQT.Cust_progress_bar|None = None
    gr_groups_nar:CMS.Groups_nar|None = None