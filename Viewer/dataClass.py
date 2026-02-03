from __future__ import annotations
if __name__ == "__main__":
    quit()

from project_cust_38 import Cust_config as CFG
from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from Viewer import mywindow
    from project_cust_38.competence_matrix import Competencies
    from project_cust_38.Cust_mes import Emploee_usr
class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]


class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    app_self: mywindow | None = None
    _old_val_cell = None
    obj_Competencies:Competencies|None = None
    empl_obj: Emploee_usr | None = None