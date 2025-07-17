import project_cust_38.Cust_Functions as F
from dataclasses import dataclass
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS

import project_cust_38.Cust_config as USRCNF

@dataclass
class Data_plan:
    @staticmethod
    def GET_DICT_INFO_FIELDS_KPL(db_kplan):

        _INFO_FIELDS_KPL = CSQ.custom_request_c(db_kplan, f"""SELECT case when table_kpl = '' then name else  table_kpl 
     || "." || name end as name, nickname, hand_editable, edit_rules_str_digit_date, users_rule, 
        rule_mode_1_disabled,hide FROM info_fields_kpl;""", rez_dict=True)
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

    db_kplan = F.bdcfg('DB_kplan')
    db_invest = F.bdcfg('DB_invest')
    db_state = F.bdcfg('DB_staff_placement')
    bd_naryad = F.bdcfg('Naryad')
    db_users = F.bdcfg('BD_users')
    db_nomen = F.bdcfg('nomenklatura_erp')

    PLACE = USRCNF.Config.place
    # ======= KAL PLAN======================
    NAPR_DEYAT = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM napravl_deyat WHERE state_on_off = 1 and poki == {PLACE.poki} OR poki is NULL""", rez_dict=True)
    DICT_NAPR_DEYAT = F.deploy_dict_c(NAPR_DEYAT, 'Пномер')
    DICT_NAPR_DEYAT_NAME = F.deploy_dict_c(NAPR_DEYAT, 'Имя')
    DICT_NAPR_DEYAT_PSDNAME = F.deploy_dict_c(NAPR_DEYAT, 'Псевдоним')
    from Setup import result
    # VID_PO_NAPR = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM виды_по_напр""", rez_dict=True)
    VID_PO_NAPR = result
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


    LIST_NAPRAVLENIE = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM napravlenie""", rez_dict=True)

    DICT_NAPRAVLENIE = F.deploy_dict_c(LIST_NAPRAVLENIE, 'Пномер')
    DICT_NAPRAVLENIE_BY_NAME = F.deploy_dict_c(LIST_NAPRAVLENIE, 'name')

    DICT_CLD = CMS.DICT_CLD_KPLAN(db_kplan)
    DICT_PODR = F.deploy_dict_c(CSQ.custom_request_c(db_kplan, """SELECT * FROM podrazdel""", rez_dict=True), 'Имя')
    DICT_PODR_POKI = {k:v for k,v in  DICT_PODR.items() if (v['poki'] is None or v['poki'] == USRCNF.Config.place.poki)}
    STATUS_NORM = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM status_norm""", rez_dict=True)
    DICT_STATUS_NORM = F.deploy_dict_c(STATUS_NORM, 'Код')
    DICT_STATUS_NORM_NAME = F.deploy_dict_c(STATUS_NORM, 'Имя')
    DICT_DOLGN_ETAP = F.deploy_dict_c(CSQ.custom_request_c(bd_naryad, f"""
    SELECT * FROM dolgn_etap""", rez_dict=True),"Должность")
    ETAPS_NAME = CSQ.custom_request_c(bd_naryad, f"""
           SELECT * FROM etaps WHERE poki == {PLACE.poki};""", rez_dict=True)
    DICT_ETAPS_NAME = F.deploy_dict_c(ETAPS_NAME,"name")
    DICT_ETAPS_VID_NAME = F.deploy_dict_c(ETAPS_NAME, "имя_в_виды_по_напр")
    DICT_EMPLOEE_FULL_WITH_DEL = CMS.dict_emploee_full_with_del(db_users)

    DICT_INFO_FIELDS_KPL = GET_DICT_INFO_FIELDS_KPL(db_kplan)

    DICT_REPLACE_BY_DAYS = dict()

    DICT_GROUP_VID_RAB_FOR_PLAN = F.deploy_dict_c(CSQ.custom_request_c(db_users, f'''SELECT * FROM group_vid_rab_for_plan WHERE composite = 0;''',rez_dict=True), 'name')
    LIST_VID_NOMEN =  CSQ.custom_request_c(db_nomen, f'''SELECT * FROM ВидыНоменклатуры;''',rez_dict=True)
    DICT_VID_NOMEN = F.deploy_dict_c(LIST_VID_NOMEN,'name')
    DICT_VID_NOMEN_NUM = F.deploy_dict_c(LIST_VID_NOMEN, 's_num')
    DICT_COMPOSITE_PODRAZD =  calc_composite_plan_group(db_kplan,db_users,PLACE,DICT_GROUP_VID_RAB_FOR_PLAN)
    DICT_GROUP_PODR_VID_RAB_FOR_PLAN = F.deploy_dict_c(CSQ.custom_request_c(db_kplan, """SELECT 
       podrazdel.Пномер,
       podrazdel.Имя,
       podrazdel.Имя_поля,
       podrazdel.Имя_первичного_поля,
       podrazdel.Имя_начала_этапа,
       podrazdel.Имя_конца_этапа,
       podrazdel.Порядок,
       podrazdel.Группа_для_расч_норм_и_ганта,
       podrazdel.Это_группа_сборки,
       podrazdel.Цвет,
       podrazdel.Наименование,
       podrazdel.mnts_plan_names as "podrazdel_mnts_plan_names",
       podrazdel.icon_flet,
       podrazdel.Наименование_СТО,
       podrazdel.Сокращ_наименование,
       podrazdel.Наименование_ЕРП,
       podrazdel.Наименование_rab_c,
       podrazdel.Имя_начала_этапа_факт,
       podrazdel.Имя_конца_этапа_факт,
       podrazdel.poki,
       podrazdel.statistic_deficit_emploers_time_percent,
       group_vid_rab_for_plan.name,
       REPLACE(group_vid_rab_for_plan.name, 'Нчас_', 'Фчас_') as name_fact,
       group_vid_rab_for_plan.nick_name,
       group_vid_rab_for_plan.color,
       group_vid_rab_for_plan.sort,
       group_vid_rab_for_plan.mnts_plan_names,
       group_vid_rab_for_plan.name_field_obespech,
       group_vid_rab_for_plan.composite,
       group_vid_rab_for_plan.estimated,
       group_vid_rab_for_plan.koef_estimate,
       group_vid_rab_for_plan.num_podr
     FROM 
    group_vid_rab_for_plan INNER JOIN 
    podrazdel ON group_vid_rab_for_plan.num_podr == podrazdel.Пномер""", rez_dict=True, attach_dbs=db_users), 'name')