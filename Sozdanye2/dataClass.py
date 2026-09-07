from __future__ import annotations
if __name__ == "__main__":
    quit()

from project_cust_38 import Cust_config as CFG
from typing import  TYPE_CHECKING
from project_cust_38 import dynamic_db_models as DDM
from project_cust_38.dynamic_db_models.orm_models import Подразделения as Подразделения_orm
if TYPE_CHECKING:
    from Sozdanie import mywindow
    from project_cust_38.competence_matrix import Competencies
    from project_cust_38.Cust_mes import Emploee_usr
    from project_cust_38.Cust_mes import Compositions

class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]


class Main_module():
    DICT_Подразделения_by_ref:dict[int,Подразделения_orm]|None = None
class data_app(SingletonMeta):


    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    app_self: mywindow | None = None
    _old_val_cell = None
    obj_Competencies:Competencies|None = None
    main_module:Main_module|None = Main_module()
    empl_obj:Emploee_usr|None = None
    PLACE:CFG.Place = CFG.Config.place
    PROJECT:CFG.ProjectConfig = CFG.Config.project
    USER_CONFIG:CFG.User_config = CFG.Config.user_config
    APP:CFG.AppConfig = CFG.Config.app
    APP_ARGS:dict = CFG.Config.app_args
    #======COMPOZITIONS=============
    compositions: Compositions|None = None


    @classmethod
    def load_data_main(cls):
        cls.main_module.DICT_Подразделения_by_ref = DDM.Подразделения().object_manager.all().deploy_dict(DDM.Подразделения.Подразделение_Key)
        pass

    @classmethod
    def init_data(cls):
        cls.load_data_main()