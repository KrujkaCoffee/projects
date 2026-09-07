from __future__ import annotations
from typing import  TYPE_CHECKING
import project_cust_38.Cust_docs as CDCS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Functions as F
from project_cust_38.Cust_tree_widget import ExtTreeWidget
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_resource_creator as CRES
import project_cust_38.Cust_mes as CMS
if TYPE_CHECKING:
    from constr_rc import mywindow
    import main_classes as CLSS

class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]

def calc_dict_vid_rab_by_ref(bd_users):
    custom_request_c = f'''SELECT * FROM professions INNER JOIN vid_rab_po_dolg 
           ON vid_rab_po_dolg.Вид_работ = professions.вид_работ,
            group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan WHERE Вкл = 1 and group_vid_rab_for_plan.composite = 0'''
    return F.deploy_dict_c(CSQ.custom_request_c(bd_users, custom_request_c, rez_dict=True),'ref_Key_erp')

def load_vids_rab():
    return CSQ.custom_request_c(CFG.Config.project.db_users, f"""SELECT 
    Пномер, 
    Вид_работ, 
    Руб_мин, 
    group_for_plan, 
    group_for_plan_f, 
    group_for_plan_start_f, 
    group_for_plan_end_f, 
    group_for_plan_start, 
    group_for_plan_end, 
    name_tbl, 
    ERP_name, 
    ref_Key_erp, 
    Родитель, 
    DeletionMark FROM  vid_rab_po_dolg WHERE Родитель == "{CFG.Config.place.РодительВидаРабот}"; """, rez_dict=True)
def load_porazd():
    text = f"""ВЫБРАТЬ
        СтруктураПредприятия.Наименование КАК Наименование,
        СтруктураПредприятия.Родитель.Представление КАК РодительПредставление,
        СтруктураПредприятия.Код КАК Код
    ИЗ
        Справочник.СтруктураПредприятия КАК СтруктураПредприятия
    ГДЕ
        СтруктураПредприятия.ПометкаУдаления = ЛОЖЬ
        И СтруктураПредприятия.Родитель.Ссылка В ИЕРАРХИИ            (ВЫБРАТЬ ПЕРВЫЕ 1
                СтруктураПредприятия.Ссылка КАК Ссылка
            ИЗ
                Справочник.СтруктураПредприятия КАК СтруктураПредприятия
            ГДЕ
                СтруктураПредприятия.ПометкаУдаления = ЛОЖЬ
                И СтруктураПредприятия.Наименование = "{CFG.Config.place.Имя}") 
    УПОРЯДОЧИТЬ ПО
        Наименование"""
    key, res = APIERP.get_wet_request(text=text, lazy_method_huours=24)
    if key != 200:
        raise ConnectionError(f'Ошибка получения данных из ЕРП')
    if not res['data']:
        raise ValueError(f'Подразделения пусто')
    return res['data']

def load_etaps():
    return CSQ.custom_request_c(CFG.Config.project.db_naryad, f"""SELECT s_num,
       name,
       color,
       mnts_join,
       ДляЕРП,
       poki,
       имя_в_виды_по_напр,
       Опер_код_рц_для_ткп_стат,
       Опер_профессия_код_для_ткп_стат,
       Опер_код_для_ткп_стат,
       sopost_etapov_vo,
       порядокДляРС 
  FROM etaps WHERE poki == {CFG.Config.place.poki} order by порядокДляРС; """, rez_dict=True)

class data_app(SingletonMeta):
    if CFG.Config.place.poki == None:
        raise ImportError(f'CFG.Config.place not init')
    current_folder_docs: CDCS.FolderTkp |None = None
    dict_orders_docs: dict[str,CLSS.OrderDocs] |None = None
    current_process: CLSS.Process|None = None
    current_elem: CLSS.TreeDoc|None = None
    app_self: mywindow|None = None
    treeNavigator: ExtTreeWidget|None = None
    tree_data_manager: CLSS.TreeDataManager|None = None
    res_stucture: list[dict]|None = None
    dse_stucture: list[dict]|None = None
    view_hidden_fields: bool|None = False
    use_cache_params: bool|None = False
    gui_qt: CLSS.Gui_tb | None = None
    _old_val_cell = None
    DICT_VID_RAB_BY_REF:dict[dict] = calc_dict_vid_rab_by_ref(CFG.Config.project.db_users)
    LIST_VID_RAB:list[dict] = load_vids_rab()
    LIST_ETAPS:list[dict] = load_etaps()
    LIST_PODRAZD:list[dict] = load_porazd()
    DICT_ETAPS:dict[int, dict] = F.deploy_dict_c(LIST_ETAPS,'s_num')
    DICT_PODRAZD:dict[int, dict] = F.deploy_dict_c(LIST_PODRAZD,'Код')
    Method_Obtain_Mat_Create_res:CRES.MethodOfObtainingMaterialspecifications =\
        CRES.MethodOfObtainingMaterialspecificationsData.find_by_name('Произвести по спецификации')
    PARAMS_FIELDS_DB = CMS.DocumentedVariables('constr_rs')

    @classmethod
    def check_is_tree_accessed(cls):
        if cls.current_process is None:
            CQT.msgbox(f'Не выбран процесс')
            return False
        if cls.current_process.tree_res is None:
            CQT.msgbox(f'Не создано дерево РС')
            return False
        return True
    def __setattr__(self, name, value):
        if name == 'current_process':
            self.current_elem = None
        super().__setattr__(name, value)
