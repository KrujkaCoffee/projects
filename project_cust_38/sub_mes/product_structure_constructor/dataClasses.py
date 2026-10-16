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
    from main_constructor import CentralWindown,StartMode
    from sub_classes import SpecSchema, TypesNomenclature, OpenedFile, OrdersDocs
    from project_cust_38.dynamic_db_models.orm_models import Подразделения as orm_Подразделения
    from project_cust_38.dynamic_db_models.orm_models import ФизическиеЛица as orm_ФизическиеЛица
    from project_cust_38.dynamic_db_models.orm_models import КадроваяИстория as orm_КадроваяИстория
    from project_cust_38.dynamic_db_models.orm_models import Nomen as orm_Номенклатура


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
    DICT_Номенклатура_by_code: dict[str, orm_Номенклатура] | None = None

    @classmethod
    def load_data_reference(cls):
        #cls.DICT_Подразделения_by_ref = DDM.Подразделения.object_manager.all().deploy_dict(
        #    DDM.Подразделения.Подразделение_Key)
        cls.DICT_ФизическиеЛица_by_ref = DDM.ФизическиеЛица.object_manager.all().deploy_dict(
            DDM.ФизическиеЛица.ФизическоеЛицо_Key)
        #cls.DICT_КадроваяИстория_by_ref = DDM.КадроваяИстория.object_manager.all().group_by(
        #    DDM.КадроваяИстория.ФизическоеЛицо_Key.name, mode=CORM.GroupByTypes.LAST)
        #cls.DICT_Номенклатура_by_code = DDM.Nomen.object_manager.filter(На_удаление=0,Вид__in=()).all().group_by(
        #   DDM.Nomen.Код.name, mode=CORM.GroupByTypes.LAST)
        pass


class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    CONFIG: CFG.Config = CFG.Config
    sub_self: CentralWindown = None
    app_self = None
    spec_schema:SpecSchema = None
    types_nomenclature:TypesNomenclature = None
    opened_file_path:OpenedFile = None
    orders_docs:OrdersDocs = None
    mode: StartMode = None
    @classmethod
    def init_data(cls):
        pass
