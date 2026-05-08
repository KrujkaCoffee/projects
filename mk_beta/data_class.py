from __future__ import annotations
import project_cust_38.Cust_Functions as F
from dataclasses import dataclass
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import datetime
import project_cust_38.Cust_config as USRCNF
from typing import TYPE_CHECKING
import project_cust_38.border_painter as BORDERP
if TYPE_CHECKING:
    from MKart import mywindow
    import kal_plan as KPL
    import gui_kal_plan as GPL
    from PyQt5 import QtWebEngineWidgets
class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]




@dataclass
class Data_plan(SingletonMeta):

    @staticmethod
    def get_groups_vid_rab_for_plan():
        data = CSQ.custom_request_c(USRCNF.Config.project.db_users,f"""SELECT 
        group_vid_rab_for_plan.* , group_vid_rab_for_plan_vs_etap.etap_id, 
            group_vid_rab_for_plan_vs_etap.koef FROM group_vid_rab_for_plan 
            INNER JOIN group_vid_rab_for_plan_vs_etap ON 
            group_vid_rab_for_plan_vs_etap.group_vid_rab == group_vid_rab_for_plan.name""",rez_dict=True)
        return CMS.Groups_vid_rab_for_plan(data)
    @staticmethod
    def GET_DICT_INFO_FIELDS_KPL(db_kplan):

        _INFO_FIELDS_KPL = CSQ.custom_request_c(db_kplan, f"""SELECT case when table_kpl = '' then name else  table_kpl 
     || "." || name end as name, nickname, hand_editable, edit_rules_str_digit_date, users_rule, 
        rule_mode_1_disabled,hide, is_system FROM info_fields_kpl;""", rez_dict=True) #10.11.25
        for item in _INFO_FIELDS_KPL:
            if item['name'].startswith('.'):
                item['name'] = item['name'][1:]
        DICT_INFO_FIELDS_KPL = F.deploy_dict_c(_INFO_FIELDS_KPL, 'name')

        return  DICT_INFO_FIELDS_KPL

    @staticmethod
    def calc_composite_plan_group(db_kplan,db_users,PLACE,DICT_GROUP_VID_RAB_FOR_PLAN):

        list_composites_podr = CSQ.custom_request_c(db_kplan,
                             f"""SELECT * FROM podrazdel WHERE Имя_поля LIKE '%;%' and poki == {PLACE.poki};""",
                             rez_dict=True)
        list_composites_group = CSQ.custom_request_c(db_users,
                             f"""SELECT * FROM group_vid_rab_for_plan WHERE composite = 1;""",
                             rez_dict=True)

        result_dict = dict()
        for item in list_composites_podr:
            comp_fields = item['Имя_поля'].split(';')
            main_comp_field_name = comp_fields[0]
            list_input_fields = comp_fields[1:]
            dict_input_fields = dict()
            name_field_froup = '.'.join([item['Имя'],main_comp_field_name])
            nick_name = False
            sort = 0
            for gr in list_composites_group:
                if gr['name'] == name_field_froup:
                    nick_name = gr['nick_name']
                    sort = gr['sort']
                    break
            if not nick_name:
                continue

            for input_field in list_input_fields:
                name_field_froup = '.'.join([item['Имя'], input_field])
                for gr_name, gr in DICT_GROUP_VID_RAB_FOR_PLAN.items():
                    if gr_name == name_field_froup:
                        dict_input_fields[input_field] = gr['nick_name']
                        break

            result_dict[nick_name] = {'name':item['Имя'],
                                      'sort':sort,
                'main_comp_field_name': main_comp_field_name,
                                        'dict_input_fields' : dict_input_fields
                                                        }

        return  result_dict

    app_self:mywindow|None = None
    PROJECT = USRCNF.Config.project
    PLACE = USRCNF.Config.place
    USER_CONFIG = USRCNF.Config.user_config
    db_kplan = PROJECT.db_kplan
    db_invest = F.bdcfg('DB_invest')
    db_state = F.bdcfg('DB_staff_placement')
    bd_naryad = PROJECT.db_naryad
    db_users = PROJECT.db_users
    db_nomen = PROJECT.db_nomen
    db_resxml = PROJECT.db_resxml
    db_fiels = PROJECT.db_files


    # ======= KAL PLAN======================
    #----------flags--------------------------
    current_id_poz_kpl:int|None=None
    current_gant:CMS.Gant|None = None
    current_vol_gant:CMS.Gant|None = None
    EDIT_TABEL_MODE:bool|None = None
    edit_tabel_current_month:str|None = None
    SETTINGS_PL_MODE:bool|None = None
    ADD_POZ_MODE:bool|None = None
    EDIT_POZ_MODE:bool|None = None
    DICT_INFO_FIELDS_KPL = GET_DICT_INFO_FIELDS_KPL(db_kplan)
    GROUPS_VID_RAB_FOR_PLAN:CMS.Groups_vid_rab_for_plan = get_groups_vid_rab_for_plan()
    CHECK_FIELD_RULES:None|KPL.Check_field_rules = None
    FIELDS_DB_INFO:None|CMS.Fields_db_info = None
    current_podr_for_edit: str | None = None
    DICT_ITERS_FOR_CHECK_FIELDS:dict | None = None
    LIST_FOR_HAT_GANT:list[str]|None = None
    MOUSE_MOVING_BLOCK_GANT:KPL.Gant_handler|None = None

    #---------------gant_borders-------------
    tbl_gant_local_border:BORDERP.BorderPainter = BORDERP.BorderPainter(
                            left_top=(0, 0), right_bottom=(0, 0),
                                thick_out=7,
                               thick_in=0,rgb_out=(22,122,22),rgb_in=(122,222,122),enabled=False)

    tbl_gant_context_border:BORDERP.BorderPainter = BORDERP.BorderPainter(
                            left_top=(0, 0), right_bottom=(0, 0),
                                thick_out=7,
                               thick_in=0,rgb_out=(22,222,22),rgb_in=(122,222,122),enabled=False)

    #---------------------------------------
    BROWSER_GR_PAD_MOSH:QtWebEngineWidgets.QWebEngineView|None = None
    BROWSER_DIAGRAM_SUMM:QtWebEngineWidgets.QWebEngineView|None = None

    NAPR_DEYAT = CMS.calc_napr_deyat(PLACE.poki)
    DICT_NAPR_DEYAT = F.deploy_dict_c(NAPR_DEYAT, 'Пномер')
    DICT_NAPR_DEYAT_NAME = F.deploy_dict_c(NAPR_DEYAT, 'Имя')
    DICT_NAPR_DEYAT_PSDNAME = F.deploy_dict_c(NAPR_DEYAT, 'Псевдоним')
    # VID_PO_NAPR = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM виды_по_напр""", rez_dict=True)
    VID_PO_NAPR = CMS.TypesWorkingByDirections().get_old_view_response() # DB_kplan.виды_по_направлению 18.07.25
    DICT_VID_PO_NAPR = F.deploy_dict_c(VID_PO_NAPR, 'Пномер')
    DICT_VID_PO_NAPR_NAME = F.deploy_dict_c(VID_PO_NAPR, 'Имя')
    STATUS_POZ =        CSQ.custom_request_c(db_kplan, f"""SELECT * FROM status_poz""", rez_dict=True)
    DICT_STATUS_POZ = F.deploy_dict_c(STATUS_POZ, 'Пномер')
    DICT_STATUS_POZ_NAME = F.deploy_dict_c(STATUS_POZ, 'Имя')
    STATUS_ETAPI_ERP =        CSQ.custom_request_c(db_kplan, f"""SELECT * FROM status_etapi_erp""", rez_dict=True)
    DICT_STATUS_ETAPI_ERP = F.deploy_dict_c(STATUS_ETAPI_ERP, 'Пномер')
    DICT_STATUS_ETAPI_ERP_NAME = F.deploy_dict_c(STATUS_ETAPI_ERP, 'Имя')
    DICT_STATUS_TARA_FULL = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM status_tara""", rez_dict=True)
    DICT_STATUS_TARA_NAME = F.deploy_dict_c(DICT_STATUS_TARA_FULL, 'name')
    DICT_STATUS_TARA_NUM = F.deploy_dict_c(DICT_STATUS_TARA_FULL, 's_num')
    DICT_BASES_ERP = F.deploy_dict_c(CSQ.custom_request_c(db_users, f"""SELECT * FROM bases_ERP""", rez_dict=True),
                                      'name')


    LIST_NAPRAVLENIE = CMS.calc_dict_napravlenie()
    DICT_NAPRAVLENIE = F.deploy_dict_c(LIST_NAPRAVLENIE, 'Пномер')
    DICT_NAPRAVLENIE_BY_NAME = F.deploy_dict_c(LIST_NAPRAVLENIE, 'name')
    DICT_CLD = CMS.DICT_CLD_KPLAN(db_kplan)
    LIST_PODR = CMS.calc_dict_podr()
    DICT_PODR = F.deploy_dict_c(LIST_PODR, 'Имя')
    DICT_PODR_BY_ID = F.deploy_dict_c(LIST_PODR, 'Пномер')
    DICT_PODR_POKI = {k:v for k,v in  DICT_PODR.items() if (v['poki'] is None or USRCNF.Config.place.poki == v['poki'] )}
    STATUS_NORM = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM status_norm""", rez_dict=True)
    DICT_STATUS_NORM = F.deploy_dict_c(STATUS_NORM, 'Код')
    DICT_STATUS_NORM_NAME = F.deploy_dict_c(STATUS_NORM, 'Имя')
    DICT_DOLGN_ETAP = F.deploy_dict_c(CSQ.custom_request_c(bd_naryad, f"""
    SELECT * FROM dolgn_etap""", rez_dict=True),"Должность")
    ETAPS_NAME = CSQ.custom_request_c(bd_naryad, f"""
           SELECT * FROM etaps WHERE poki == {PLACE.poki} order by порядокДляРС;""", rez_dict=True)
    DICT_ETAPS_NAME = F.deploy_dict_c(ETAPS_NAME,"name")
    DICT_ETAPS_VID_NAME = F.deploy_dict_c(ETAPS_NAME, "имя_в_виды_по_напр")
    DICT_EMPLOEE_FULL_WITH_DEL = CMS.dict_emploee_full_with_del(db_users)


    list_dict_from_db:None|list[dict] = None
    dict_dict_from_db:None|dict[dict] = None
    DICT_REPLACE_BY_DAYS = dict()

    DICT_GROUP_VID_RAB_FOR_PLAN = F.deploy_dict_c(CSQ.custom_request_c(db_users, f'''SELECT * FROM group_vid_rab_for_plan WHERE composite = 0;''',rez_dict=True), 'name')
    LIST_VID_NOMEN =  CSQ.custom_request_c(db_nomen, f'''SELECT * FROM ВидыНоменклатуры;''',rez_dict=True)
    DICT_VID_NOMEN = F.deploy_dict_c(LIST_VID_NOMEN,'name')
    DICT_VID_NOMEN_NUM = F.deploy_dict_c(LIST_VID_NOMEN, 's_num')
    DICT_COMPOSITE_PODRAZD =  calc_composite_plan_group(db_kplan,db_users,PLACE,DICT_GROUP_VID_RAB_FOR_PLAN)
    LIST_GROUP_VID_RAB_FOR_PLAN_VS_ETAP = CSQ.custom_request_c(db_users, f'''SELECT *
     FROM group_vid_rab_for_plan_vs_etap 
    INNER JOIN etaps ON etaps.s_num == group_vid_rab_for_plan_vs_etap.etap_id;''', rez_dict=True,attach_dbs=bd_naryad)
    DICT_GROUP_PODR_VID_RAB_FOR_PLAN = CMS.calc_dict_group_podr_vid_rab_for_plan()
