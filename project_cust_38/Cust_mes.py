from __future__ import annotations

import dataclasses
import logging
import datetime
import pathlib
import pprint
import re

import asyncio
import typing
from builtins import ValueError
from itertools import accumulate
from collections import defaultdict, OrderedDict
import project_cust_38.Cust_odata_erp as ODAT
import project_cust_38.Cust_Functions as F
import os
import project_cust_38.Cust_SQLite as CSQ
from PyQt5 import QtWidgets, QtGui, QtCore
import sys
import project_cust_38.Cust_Qt as CQT
import hashlib
from project_cust_38 import Cust_config as CFG
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Cust_virbotka as VIR
import project_cust_38.xml_v_drevo as XML
import project_cust_38.report_ci as report_ci
import project_cust_38.Cust_docs as CDOCS
import project_cust_38.Cust_storage as CSTORE
from project_cust_38 import Cust_progressBar as CPB
import copy
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import subprocess
import winreg
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_emoji as CEMOJ
try:
    from project_cust_38.isdayoff_cust import ProdCalendar
except:
    print(f'isdayoff err import')
try:
    import project_cust_38.Erp_connector_plan as ERP
    import project_cust_38.Cust_b24 as CB24
    from project_cust_38 import Cust_xl_formul as CXLF
except:
    print(f'Erp_connector_plan err import')
    print(f'Cust_b24 err import')
    pass
import project_cust_38.operacii as operacii
#exclude import calculate_vo 11.11.25
FOLDER_CLOSED = f'{CEMOJ.EmojiMain.ДокументыДанные.folder_closed.symbol}{CEMOJ.EmojiMain.ДокументыДанные.plus_circled.symbol}'
FOLDER_OPEN = f'{CEMOJ.EmojiMain.ДокументыДанные.folder.symbol}{CEMOJ.EmojiMain.ДокументыДанные.minus_circled.symbol}'
DOC_EMOJI = f'    {CEMOJ.EmojiMain.ДокументыДанные.document.symbol}'




class Tabels_erp():
    def __init__(self,ERP_base_name):
        self._m = ODAT.OrdersComposit(ERP_base_name)
        self.list_tab_headers:list[Tabel] = []

        self.dict_sotr = F.deploy_dict_c(self._m.get_response('Catalog_Сотрудники',
                             f"""?$filter=DeletionMark eq false 
                                                    &$select=Ref_Key, Description"""),"Ref_Key")
        self.dict_vid_time = F.deploy_dict_c(self._m.get_response('Catalog_ВидыИспользованияРабочегоВремени',
                             f"""?$filter=DeletionMark eq false 
                                                    &$select=Ref_Key, Description, БуквенныйКод"""),"Ref_Key")
        return

    def get_list_tab_headers(self):
        data_tabs = self._m.get_response('Document_ТабельУчетаРабочегоВремени?$expand=Подразделение',
                                   f"""&$filter=DeletionMark eq false and Подразделение_Key ne guid'00000000-0000-0000-0000-000000000000'
                                    &$select=Ref_Key, Комментарий, Number,ПериодРегистрации,Подразделение/Description""")
        for item in data_tabs:
            item['Подразделение'] = item['Подразделение']['Description']
            item['ПериодРегистрации'] = F.strtodate(item['ПериодРегистрации'],"%Y-%m-%dT%H:%M:%S")
            self.list_tab_headers.append(Tabel(self._m,self.dict_sotr,self.dict_vid_time, item))


class Tabel():
    def __init__(self,m:ODAT.OrdersComposit,dict_sotr:dict,dict_vid_time:dict, header:dict):
        self._m = m
        self.Ref_Key:str = header['Ref_Key']
        self.Комментарий:str = header['Комментарий']
        self.Number:str = header['Number']
        self.ПериодРегистрации:datetime.datetime = header['ПериодРегистрации']
        self.Подразделение:str = header['Подразделение']
        self.data = None
        self.dict_sotr = dict_sotr
        self.dict_vid_time = dict_vid_time
        pass

    def load_data(self):
        tmp_data = self._m.get_response('Document_ТабельУчетаРабочегоВремени',
                             f"""?$filter=DeletionMark eq false and Ref_Key eq guid'{self.Ref_Key}'
                                            &$select=ДанныеОВремени""")
        def name_vid_time_str(item:dict):
            return f'{item["Description"]}({item["БуквенныйКод"]})'


        def calc_vid_time(item):
            dict_num_vid_time = dict()

            for item_name, item_dat in item.items():
                item_name:str = item_name
                for field in USE_FIELDS:
                    if item_name.startswith(field):
                        num = F.valm(item_name.replace('_Key', '').split(field)[-1])
                        if num not in dict_num_vid_time:
                            dict_num_vid_time[num] = dict()
                        if item_dat in self.dict_vid_time:
                            item_dat = name_vid_time_str(self.dict_vid_time[item_dat])
                        dict_num_vid_time[num][field] = item_dat
            for num in dict_num_vid_time:
                if 'ВидВремени' in dict_num_vid_time[num]:
                    val = 0
                    if 'Часов' in dict_num_vid_time[num]:
                        val = dict_num_vid_time[num]['Часов']
                    dict_num_vid_time[num] = {dict_num_vid_time[num]['ВидВремени']:val}
            return dict_num_vid_time

        USE_FIELDS = ('Часов','ВидВремени')
        rez_dict = dict()
        data_days:list = tmp_data[0]['ДанныеОВремени']
        setErr = set()
        shabl_vid_time = {name_vid_time_str(v):0 for v in self.dict_vid_time.values()}

        for item in data_days:
            if self.dict_sotr[item['Сотрудник_Key']] not in rez_dict:
                rez_dict[self.dict_sotr[item['Сотрудник_Key']]] = {'data':dict(),'dict_summ': copy.deepcopy(shabl_vid_time)}

            dict_vid_time = calc_vid_time(item)
            for num in dict_vid_time.keys():
                if num not in rez_dict[self.dict_sotr[item['Сотрудник_Key']]]['data']:
                    rez_dict[self.dict_sotr[item['Сотрудник_Key']]]['data'][num] = dict()
                item_vid:dict = dict_vid_time[num]
                for k , v in item_vid.items():
                    rez_dict[self.dict_sotr[item['Сотрудник_Key']]]['data'][num][k] = v


        for user, item in rez_dict.items():
            for day, data_day in item['data'].items():
                for vid, time in data_day.items():
                    if vid == '00000000-0000-0000-0000-000000000000':
                        continue
                    if vid not in item['dict_summ']:
                        setErr.add(f'Несоответствие типа времени в табеле {vid}')
                        item['dict_summ'][vid] = 0
                    item['dict_summ'][vid] += time

        self.data = rez_dict
        if setErr:
            print(setErr)




class Logs():
    def __init__(self,db_files:str):
        self.db = db_files

    def get_history(self,row:int,column_name:str,obj_name:str=None):
        name_tbl, name_field = column_name.split('.')
        if obj_name == None:
            obj_name = self._generate_obj_name()
        res = CSQ.custom_request_c(self.db,f"""SELECT user,datetime_change,new_val FROM journal_log 
         INNER JOIN objects_jur ON objects_jur.s_num == journal_log.obj WHERE objects_jur.name =="{obj_name}" AND 
          journal_log.row == {row} AND journal_log.column_name == "{name_field}";""",rez_dict=True)
        return  res


    def add_note(self,row:int,column_name:str,val:str,name_tbl=None):
        self.obj_name = self._generate_obj_name(name_tbl)
        self.row = row
        self.column_name = column_name
        self.val = str(val)
        self.obj_s_num = None
        self.check_obj()

        add_row = [self.obj_s_num,self.row,self.column_name,F.curr_user_c(),F.now(),self.val]
        CSQ.custom_request_c(self.db,f"""INSERT INTO journal_log (
        obj, 
        row, 
        column_name, 
        user, 
        datetime_change, 
        new_val 
        )
                              VALUES ({CSQ.questions_for_mask(add_row)});""",list_of_lists_c=[add_row])

    def _generate_obj_name(self,name_tbl=None):
        if name_tbl == None:
            name_tbl = str(CQT.focus_obj_name())
        name = os.path.abspath(sys.modules['__main__'].__file__).split(os.sep)[-1].replace('.py',
                                                                                    '') + "$" + name_tbl
        return name

    def get_dict_obj(self):
        dict_obj = F.deploy_dict_c(CSQ.custom_request_c(self.db,f"""SELECT s_num, name FROM objects_jur;""",rez_dict=True),"name")
        return dict_obj

    def check_obj(self):
        dict_obj = self.get_dict_obj()
        if self.obj_name not in dict_obj:
            self._add_obj_db()
        else:
            self.obj_s_num = dict_obj[self.obj_name]

    def _add_obj_db(self):
        CSQ.custom_request_c(self.db,f"""INSERT INTO objects_jur (name)
                              VALUES (?);""",list_of_lists_c=[[self.obj_name]])
        data_resp = CSQ.custom_request_c(self.db, f"""SELECT s_num FROM objects_jur WHERE name = "{self.obj_name}";""", rez_dict=True,one=True)
        self.obj_s_num = data_resp['s_num']




class Color_tbl():
    DICT_COLOR = {0 : "248;105;107",
    10 : "249;131;112",
    20 : "250;157;117",
    30 : "252;183;122",
    40 : "253;209;127",
    50 : "255;235;132",
    60 : "224;227;131",
    70 : "193;218;129",
    80 : "162;208;127",
    90 : "131;199;125",
    100 : "99;190;123",
    }
    DICT_COLOR_DARK = {
        0: "198;55;57",  # Более насыщенный красный
        10: "209;81;62",  # Теплый оранжево-красный
        20: "220;107;67",  # Насыщенный оранжевый
        30: "212;133;72",  # Золотисто-оранжевый
        40: "203;159;77",  # Светло-оранжевый
        50: "205;185;82",  # Желто-оранжевый
        60: "174;177;81",  # Оливково-желтый
        70: "143;168;79",  # Желто-зеленый
        80: "112;158;77",  # Светло-зеленый
        90: "81;149;75",  # Средне-зеленый
        100: "49;140;73",  # Насыщенный зеленый
    }
    def __init__(self,val:float|int,revers=False,dark_mode=False):
        DICT_COLOR = Color_tbl.DICT_COLOR
        if dark_mode:
            DICT_COLOR = Color_tbl.DICT_COLOR_DARK

        self.r, self.g, self.b = DICT_COLOR[100].split(';')

        if revers:
            dict_color = {(100-k):v for k,v in dict(reversed(DICT_COLOR.items())).items()}
        else:
            dict_color = copy.deepcopy(DICT_COLOR)
        for key, color in dict_color.items():
            if key >= val:
                self.r,self.g,self.b =color.split(';')
                break
        self.r = int(self.r)
        self.g = int(self.g)
        self.b = int(self.b)
        self.rgb = [self.r,self.g,self.b]

class Emploee_usr():
    def __init__(self,fio:str,user_db:str):
        if F.is_unique_identifier(fio):
            data = CSQ.custom_request_c(user_db, f"""SELECT * FROM employee WHERE ID_ФизЛица == "{fio}";""", rez_dict=True)
        else:
            data = CSQ.custom_request_c(user_db,f"""SELECT * FROM employee WHERE ФИО == "{fio}";""",rez_dict =True)
        if len(data) == 0:
            raise Exception('не найден ФИО в БД')
        self.user_db = user_db
        self.ФИО = None

        self.Пномер = None
        self.Должность = None
        self.Статус = None
        self.Подразделение = None
        self.Режим = None
        self.Компания = None
        self.ID_ФизЛица = None
        self.ВидЗанятости = None
        self.ДатаИзмененияДолжности = None
        self.history = []

        for record in data:
            if record['Статус'] == 'Работа':
                for key in record.keys():
                    exec(f'self.{key.replace(".", "_")} = record[key]')
        for item in data:
            self.history.append(item)

    def is_dismissed_now(self,dolgn,date=None):
        user_frame = dict()
        for item in self.history[-1:-1:-1]:
            if item['Должность'] == dolgn:
                user_frame = item
                break
        if len(user_frame) == 0:
            raise Exception('не найдена должность для ФИО в БД')

        if item['Статус'] == 'Увольнение':
            list_states = CSQ.custom_request_c(self.user_db, f"""SELECT s_num, user_id, state, date FROM 
             employee_registr WHERE user_id == "{item['ID_ФизЛица']}" AND state == 10;""",rez_dict=True)
            if date != None:
                if F.strtodate(date) >= list_states[-1]['date']:
                    list_states[-1]['date']
                else:
                    False
            else:
                return list_states[-1]['date']
        else:
            return False



class Emploee_spread_db():

    def __init__(self):
        pass

    def update_fiz_users(self):
        text = """
        ВЫБРАТЬ
            ФизическиеЛица.Фамилия КАК Фамилия,
            ФизическиеЛица.Имя КАК Имя,
            ФизическиеЛица.Отчество КАК Отчество,
            ПРЕДСТАВЛЕНИЕ(ФизическиеЛица.Пол.Ссылка) КАК Пол,
            ФизическиеЛица.ПометкаУдаления КАК ПометкаУдаления,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ФизическиеЛица.Родитель.Ссылка))  КАК Родитель_key,
            ФизическиеЛица.ЭтоГруппа КАК ЭтоГруппа,
            Наименование КАК Наименование,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ФизическиеЛица.Ссылка)) КАК ФизическоеЛицо_Key
        ИЗ
            Справочник.ФизическиеЛица КАК ФизическиеЛица
        ГДЕ
            ФизическиеЛица.ПометкаУдаления = ЛОЖЬ
        """
        succ, data_1C = APIERP.get_wet_request(text)
        if succ != 200:
            print(f'update_fiz_users err data_1C')
            return
        data_1C = F.deploy_dict_c(data_1C['data'],'ФизическоеЛицо_Key',keep_key=True)


        data_mes = CSQ.custom_request_c(CFG.Config.project.db_users,f"""SELECT * 
                                                                                      FROM ФизическоеЛица;
                                                                                    """,rez_dict=True)
        if data_mes is None or data_mes == False:
            print(f'update_fiz_users err data_mes')
            return
        data_mes = F.deploy_dict_c(data_mes,'ФизическоеЛицо_Key',keep_key=True)
        
        dict_add = dict()
        dict_edit = dict()


        def add_edit(ref,k,v):
            if ref not in dict_edit:
                dict_edit[ref] = dict()
            dict_edit[ref][k] = v

        for ref, vals_1c in data_1C.items():
            if ref not in data_mes:
                dict_add[ref] = vals_1c
                continue
            vals_mes = data_mes[ref]
            for k,v in vals_1c.items():
                if k not in vals_mes:
                    print(f'update_fiz_users err attr {k}')
                    return
                v_mes = vals_mes[k]
                if v != v_mes:
                    add_edit(ref,k,v)

        for ref, vals_mes in data_mes.items():
            if vals_mes['ПометкаУдаления'] == 1:
                continue
            if ref not in data_1C:
                add_edit(ref,'ПометкаУдаления',True)
                continue

        if dict_edit:
            for ref, dict_vals in dict_edit.items():
                list_k = list(dict_vals.keys())
                list_v = list(dict_vals.values())
                CSQ.custom_request_c(CFG.Config.project.db_users, f"""
                        UPDATE ФизическоеЛица 
                SET  ({','.join(list_k)})
                    = ({CSQ.questions_for_mask(list_k)})
                            WHERE ФизическоеЛицо_Key == "{ref}" ;""", list_of_lists_c=[list_v])
                print(f'ФизическоеЛицо_Key == "{ref}" vals({list_v})')
        if dict_add:
            fields = [list(dict_vals.keys()) for dict_vals in dict_add.values()]
            fields = fields[0]
            list_of_lists = [list(dict_vals.values()) for dict_vals in dict_add.values()]
            CSQ.custom_request_c(CFG.Config.project.db_users, f"""INSERT INTO ФизическоеЛица
                              ({','.join(fields)}) 
                              VALUES ({CSQ.questions_for_mask(fields)});""", list_of_lists_c=list_of_lists)
        
        
        

class Emploee_db():
    URI = fr'{CFG.Config.project.ERB_BASE_URL}/ERP/hs/SDE/Staff/'
    def __init__(self, db):
        self.db = db


        self.DICT_EMPLOYEE_REGISTR_STATES =\
            F.deploy_dict_c(CSQ.custom_request_c(self.db,f"""
            SELECT * FROM employee_registr_states;""",rez_dict=True),'name')

    def _add_registr_note(self,id:str,state:str):
        if state not in self.DICT_EMPLOYEE_REGISTR_STATES:
            print(f'ERROR _add_registr_note  {state} not in self.DICT_EMPLOYEE_REGISTR_STATES')
            return False
        state = self.DICT_EMPLOYEE_REGISTR_STATES[state]
        CSQ.custom_request_c(self.db,f"""INSERT INTO employee_registr (user_id,    state, 
         date) VALUES (?,?,?);""",list_of_lists_c=[[id,state,F.now("%Y-%m-%d")]])
        return True

    def update_db(self,db_naryad,write):
        def add_abstract(spis_empolee):
            spis_empolee.append({
                'ФИОПолные': '',
                'ID_ФизЛица': '',
                'Подразделение': '',
                'Должность': '',
                'ГрафикРаботы': '',
                'ВидЗанятости': '',
                'Состояние': '',
                'Организация': '',
                'ДатаИзмененияДолжности': '',
            }
            )
            spis_empolee.append({
                'ФИОПолные': '-',
                'ID_ФизЛица': '',
                'Подразделение': '-',
                'Должность': '-',
                'ГрафикРаботы': 'Абстракт',
                'ВидЗанятости': '',
                'Состояние': '',
                'Организация': '',
                'ДатаИзмененияДолжности': '',
            }
            )
            spis_empolee.append({
                'ФИОПолные': '+',
                'ID_ФизЛица': '',
                'Подразделение': '+',
                'Должность': '+',
                'ГрафикРаботы': 'Абстракт',
                'ВидЗанятости': '',
                'Состояние': '',
                'Организация': '',
                'ДатаИзмененияДолжности': '',
            }
            )
            return spis_empolee
        def prepare_params(fio,dolg,date):

            if F.is_date(date,"%Y-%m-%dT%H:%M:%SZ"):
                date = F.datetostr(F.strtodate(date,"%Y-%m-%dT%H:%M:%SZ"),"%Y-%m-%d")
            fio = fio.strip()
            dolg = dolg.replace('.', '').replace('  ', ' ').strip()
            return fio, dolg,date

        list_changes = []
        empolee_base = self._get_data_from_1c()
        #empolee_base = F.load_file_pickle('empolee_base.pickle')

        set_state = set()
        for item in empolee_base:
            set_state.add(item['Состояние'])

        put_db = self.db
        if empolee_base == None:
            print(f'{F.now()} Не получить данные из 1с')
            return
        #F.save_file_pickle('empolee_base.pickle',empolee_base)
        #F.delete_file_c('empolee_base.pickle')
        dict_organiztions = F.deploy_dict_c(CSQ.custom_request_c(db_naryad,f"""SELECT * FROM places""",rez_dict=True),"Имя")
        spis_empolee = [_ for _ in empolee_base if _['Организация'] in  list(dict_organiztions.keys()) ]

        if spis_empolee == []:
            print(f'{F.now()} Не найдены сотрудники из 1с')
            return

        spis_empolee = add_abstract(spis_empolee)
        # |_| вакант = нет
        # - не нужен = нет
        # + не нужен = есть

        print('employee обновление')
        users_db = CSQ.custom_request_c(put_db, '''SELECT * FROM employee WHERE Статус != "Увольнение"''', rez_dict=True)
        spis_add = []
        spis_edit = []

        # ================= проверка на увольнение(нет фио в списке)
        for i in range(1, len(users_db)):
            fl_naid = False
            if users_db[i]['Режим'] == 'Абстракт':
                continue
            for user in spis_empolee:
                fio, dolg,date = prepare_params(user['ФИОПолные'], user['Должность'],user['ДатаИзмененияДолжности'])
                if users_db[i]['ID_ФизЛица'] == user['ID_ФизЛица'] and users_db[i]['Должность'] == dolg:
                    fl_naid = True
                    break
            if fl_naid == False:
                list_changes.append(f"{users_db[i]['ФИО']} {users_db[i]['Должность']} уволен")
                if write:
                    CSQ.custom_request_c(put_db,
                                         f'''UPDATE employee SET (Статус,ДатаИзмененияДолжности) 
                                         = ("Увольнение","{F.now("%Y-%m-%d")}") WHERE Пномер = {users_db[i]['Пномер']} ''')
                    if not self._add_registr_note(users_db[i]['ID_ФизЛица'],"Увольнение"):
                        return
        if len(list_changes) == 0:
            print('Увольнение не найдены')
        # ==================== проверка на устройство(нет фио в бд)
        for user in spis_empolee:
            fio, dolg,date = prepare_params(user['ФИОПолные'], user['Должность'],user['ДатаИзмененияДолжности'])
            podr = user['Подразделение']
            fl_naid = False
            gender = user['ID_ФизЛица'] #28.11.2025
            for user_db in users_db:
                if user_db['ФИО'] != 'Абстракт' and dolg == user_db['Должность'] and fio == user_db['ФИО'] and user_db['Компания'] == "":
                    if user_db['ID_ФизЛица'] == '':
                        user_db['ID_ФизЛица'] = user['ID_ФизЛица']
                        user_db['Компания'] = user['Организация']
                        CSQ.custom_request_c(self.db, f"""UPDATE employee SET (ID_ФизЛица,Компания) = 
                        ("{user['ID_ФизЛица']}","{user['Организация']}") WHERE Пномер={user_db['Пномер']};""")
                    else:
                        user_db['Компания'] = user['Организация']
                        CSQ.custom_request_c(self.db,f"""UPDATE employee SET (Компания) = 
                    ("{user['Организация']}") WHERE Пномер={user_db['Пномер']};""")

                if user['ID_ФизЛица'] == user_db['ID_ФизЛица'] and dolg == user_db['Должность'] and user_db['Статус'] != 'Увольнение':
                    fl_naid = True
                    break
            if fl_naid == False:
                spis_add.append([fio, dolg,user['Состояние'],user['Подразделение'],user['ГрафикРаботы'],
                                 user['Организация'],user['ID_ФизЛица'],user['ВидЗанятости'],date,gender])
                list_changes.append(f'Добавлен {user}')
        if len(list_changes) == 0:
            print('Новые сотрудники не найдены')

        if write:
            if len(spis_add) > 0:
                custom_request_c = f"""INSERT INTO employee
                                                          ( ФИО,
                                                            Должность,
                                                            Статус,
                                                            Подразделение,
                                                            Режим,
                                                            Компания,
                                                            ID_ФизЛица,
                                                            ВидЗанятости,
                                                            ДатаИзмененияДолжности,
                                                            gender)
                                                          VALUES ({CSQ.questions_for_mask(['' for _ in range(len(spis_add[0]))])});"""
                CSQ.custom_request_c(put_db, custom_request_c, list_of_lists_c=spis_add)
            for item in spis_add:
                if not self._add_registr_note(item[6], item[2]):
                    return
        # ==================== проверка на режим и подразделение
        for user in spis_empolee:
            fio, dolg,date = prepare_params(user['ФИОПолные'], user['Должность'],user['ДатаИзмененияДолжности'])
            pass
            for user_db in users_db:
                if user_db['Статус'] == 'Увольнение' or user_db['Режим'] == 'Абстракт':
                    continue
                if user['ID_ФизЛица'] == user_db['ID_ФизЛица'] and dolg == user_db['Должность']:
                    if write:
                        if user['Подразделение'] != user_db['Подразделение']:
                            CSQ.custom_request_c(put_db,
                                                 f"""UPDATE employee SET Подразделение = "{user['Подразделение']}"
                                                     WHERE Пномер = {user_db['Пномер']}""")
                        if user['Состояние'] != user_db['Статус']:
                            CSQ.custom_request_c(put_db,
                                                 f"""UPDATE employee SET Статус = "{user['Состояние']}"
                                                                            WHERE Пномер = {user_db['Пномер']}""")
                            if not  self._add_registr_note(user['ID_ФизЛица'],user['Состояние']):
                                return
                        if user['ГрафикРаботы'] != user_db['Режим']:
                            CSQ.custom_request_c(put_db,
                                                 f"""UPDATE employee SET Режим = "{user['ГрафикРаботы']}" 
                                                     WHERE Пномер = {user_db['Пномер']}""")
                        if user['ВидЗанятости'] != user_db['ВидЗанятости']:
                            CSQ.custom_request_c(put_db,
                                                 f"""UPDATE employee SET 
                                                    (ВидЗанятости) = (?) 
                                                     WHERE Пномер = {user_db['Пномер']}""",
                                                 list_of_lists_c=[[user['ВидЗанятости']]])
                    else:
                        if user['Подразделение'] != user_db['Подразделение']:
                            list_changes.append(f"{fio} Подразд. Было {user_db['Подразделение']}     Стало {user['Подразделение']}")
                        if user['ГрафикРаботы'] != user_db['Режим']:
                            list_changes.append(f"{fio} Режим. Было {user_db['Режим']}     Стало {user['ГрафикРаботы']}")
                        if user['ВидЗанятости'] != user_db['ВидЗанятости']:
                            list_changes.append(f"{fio} ВидЗанятости. Было {user_db['ВидЗанятости']}     Стало {user['ВидЗанятости']}")
                    break
        if len(list_changes) == 0:
            print('Изменения состояйний не обнаружено')
        if not write:
            #print(pprint.pformat(list_changes))
            return list_changes
        else:
            print(pprint.pformat(list_changes))
            list_from_empl = CSQ.custom_request_c(put_db,
                                                  f"""SELECT DISTINCT Должность, Подразделение, Компания FROM 
                                        employee WHERE Компания != '' and Подразделение not in ("+","-")""",
                                                  rez_dict=True)
            list_from_etaps = CSQ.custom_request_c(db_naryad,
                                                   f"""SELECT DISTINCT Должность, 
                                                   Подразделение, Производство FROM dolgn_etap """,
                                                   rez_dict=True)
            list_add = []
            for item in list_from_empl:
                fl_naid = False
                for item_et in list_from_etaps:
                    if (item['Должность'] == item_et['Должность'] and item['Подразделение'] == item_et['Подразделение']
                            and item['Компания'] == item_et['Производство']):
                        fl_naid = True
                        break
                if fl_naid == False:
                    list_add.append([item['Должность'], item['Подразделение'], item['Компания']])
            if len(list_add) > 0:
                CSQ.custom_request_c(db_naryad, f"""INSERT INTO dolgn_etap
                                      (Должность, Подразделение,Производство)
                                      VALUES (?, ?, ?);""", list_of_lists_c=list_add)
            return
    @classmethod
    def get_info_user(cls,fio:str):
        try:
            import requests
        except:
            print('_get_data_from_1c err не устанволен requests')
        session = requests.Session()
        user = 'Obmen_proizv'
        password = 'nE6zamap'
        postfix = f'?Организация=Пауэрз&ФИОПолные={fio}'
        try:
            response = requests.get(Emploee_db.URI + fio, auth=(user, password))
            list_of_dicts = eval(F.convert_binary_to_data(response.content))
            return list_of_dicts
        except:
            pass

    def _get_data_from_1c(self):
        try:
            import requests
        except:
            print('_get_data_from_1c err не устанволен requests')
        session = requests.Session()
        user = 'Obmen_proizv'
        password = 'nE6zamap'
        try:
            response = requests.get(self.URI, auth=(user, password))
            list_of_dicts = eval(F.convert_binary_to_data(response.content))
            return list_of_dicts
        except:
            pass

    def get_gender(self, ref_key_phys: str):
        """Возвращает пол человека по uuid физ лица
            :ref_key_phys  uuid физ лица
        """
        client = ODAT.OrdersComposit()
        code, response = client.get_response(
            f'Catalog_ФизическиеЛица(guid{ref_key_phys!r})',
            wet_filtr='$select=Пол',
            with_cod=True
        )
        if code != 200:
            return
        return response['Пол']


class File_db():
    def __init__(self,db,table_name):
        self.db = db
        self.table_name = table_name

    def add_file(self,path_f):
        pass

    def open_file(self,s_nom):
        pass

#++ 06.06.2025 (по задаче 100055177 )
def get_db_rows_pl_etaps(pnom_or_pnoms: int | list[int]):
    db_kplan = CFG.Config.project.db_kplan
    where = f'WHERE Пномер == %s' % str(pnom_or_pnoms)
    one = True
    if isinstance(pnom_or_pnoms, list):
        if len(pnom_or_pnoms) == 0:
            where = ''
        else:
            joined_pks = CSQ.prepare_list_to_tuple(pnom_or_pnoms)
            where = f'WHERE Пномер in ({joined_pks})'
        one = False
    request = f"""
                                SELECT plan.Пномер, plan.Пдата_зав_вспом, plan.Пдата_нач_вспом, 
                                  пл_заг.ПДата_зав_заг, пл_заг.ПДата_нач_заг,
                                  пл_мех.Пдата_зав_мехобр, пл_мех.Пдата_нач_мехобр,
                                  пл_сб.Пдата_зав_сб, пл_сб.Пдата_нач_сб,
                                  пл_покр.Пдата_зав_покр, пл_покр.Пдата_нач_покр,
                                  пл_компл.ПДата_зав_комплект_упаковки,  пл_компл.ПДата_нач_комплект_упаковки,
                                  пл_отк.Пдата_зав_контр,  пл_отк.Пдата_нач_контр,
                                   пл_топ.Пдата_зав_ТД,  пл_топ.Пдата_нач_ТД,
                                   пл_чпу.ПДата_зав_чпу,  пл_чпу.ПДата_нач_чпу,


                                    пл_топ.Пдата_нач_ТД AS "пл_топ.Пдата_нач_ТД", 
                                    пл_топ.Пдата_зав_ТД AS "пл_топ.Пдата_зав_ТД",
                                    plan.Пдата_зав_вспом AS "plan.Пдата_зав_вспом", 
                                    plan.Пдата_нач_вспом AS "plan.Пдата_нач_вспом",  
                                    пл_заг.ПДата_зав_заг AS "пл_заг.ПДата_зав_заг",  
                                    пл_заг.ПДата_нач_заг AS "пл_заг.ПДата_нач_заг", 
                                    пл_мех.Пдата_зав_мехобр AS "пл_мех.Пдата_зав_мехобр", 
                                    пл_мех.Пдата_нач_мехобр AS "пл_мех.Пдата_нач_мехобр", 
                                    пл_сб.Пдата_зав_сб AS "пл_сб.Пдата_зав_сб", 
                                    пл_сб.Пдата_нач_сб AS "пл_сб.Пдата_нач_сб", 
                                    пл_покр.Пдата_зав_покр AS "пл_покр.Пдата_зав_покр", 
                                    пл_покр.Пдата_нач_покр AS "пл_покр.Пдата_нач_покр", 
                                    пл_компл.ПДата_зав_комплект_упаковки AS "пл_компл.ПДата_зав_комплект_упаковки",  
                                    пл_компл.ПДата_нач_комплект_упаковки AS "пл_компл.ПДата_нач_комплект_упаковки",
                                    пл_отк.Пдата_зав_контр AS "пл_отк.Пдата_зав_контр",  
                                    пл_отк.Пдата_нач_контр AS "пл_отк.Пдата_нач_контр",
                                    пл_чпу.ПДата_нач_чпу AS "пл_чпу.ПДата_нач_чпу",

                                    пл_сб.Нчас_слсб AS "пл_сб.Нчас_слсб",
                                    пл_сб.Фчас_слсб AS "пл_сб.Фчас_слсб",
                                    пл_сб.Нчас_св AS "пл_сб.Нчас_св",
                                    пл_сб.Фчас_св AS "пл_сб.Фчас_св",
                                    пл_сб.Нчас_зач AS "пл_сб.Нчас_зач",
                                    пл_сб.Фчас_зач AS "пл_сб.Фчас_зач",

                                    пл_топ.Фдата_нач_ТД AS "пл_топ.Фдата_нач_ТД", 
                                    пл_топ.Фдата_зав_ТД AS "пл_топ.Фдата_зав_ТД",
                                    plan.Фдата_зав_вспом AS "plan.Фдата_зав_вспом", 
                                    plan.Фдата_нач_вспом AS "plan.Фдата_нач_вспом",  
                                    пл_заг.ФДата_зав_заг AS "пл_заг.ФДата_зав_заг", 
                                    пл_заг.ФДата_нач_заг AS "пл_заг.ФДата_нач_заг", 
                                    пл_мех.Фдата_зав_мехобр AS "пл_мех.Фдата_зав_мехобр", 
                                    пл_мех.Фдата_нач_мехобр AS "пл_мех.Фдата_нач_мехобр", 
                                    пл_сб.Фдата_зав_сб AS "пл_сб.Фдата_зав_сб", 
                                    пл_сб.Фдата_нач_сб AS "пл_сб.Фдата_нач_сб", 
                                    пл_покр.Фдата_зав_покр AS "пл_покр.Фдата_зав_покр", 
                                    пл_покр.Фдата_нач_покр AS "пл_покр.Фдата_нач_покр", 
                                    пл_компл.ФДата_зав_комплект_упаковки AS "пл_компл.ФДата_зав_комплект_упаковки", 
                                    пл_компл.ФДата_нач_комплект_упаковки AS "пл_компл.ФДата_нач_комплект_упаковки", 
                                    пл_отк.Фдата_зав_контр AS "пл_отк.Фдата_зав_контр", 
                                    пл_отк.Фдата_нач_контр AS "пл_отк.Фдата_нач_контр", 
                                    пл_чпу.ФДата_нач_чпу AS "пл_чпу.ФДата_нач_чпу", 
                                    пл_чпу.ФДата_зав_чпу AS "пл_чпу.ФДата_зав_чпу", 

                                    пл_топ.Нчас_ТД AS "пл_топ.Нчас_ТД", 
                                    пл_топ.Фчас_ТД AS "пл_топ.Фчас_ТД", 
                                    пл_заг.Нчас_заг AS "пл_заг.Нчас_заг", 
                                    пл_заг.Фчас_заг AS "пл_заг.Фчас_заг", 
                                    пл_мех.Нчас_мехобр AS "пл_мех.Нчас_мехобр", 
                                    пл_мех.Фчас_мехобр AS "пл_мех.Фчас_мехобр", 
                                    пл_сб.Нчас_сб AS "пл_сб.Нчас_сб", 
                                    пл_сб.Фчас_сб AS "пл_сб.Фчас_сб", 
                                    пл_покр.Нчас_покр AS "пл_покр.Нчас_покр", 
                                    пл_покр.Фчас_покр AS "пл_покр.Фчас_покр", 
                                    пл_компл.Нчас_упаковки AS "пл_компл.Нчас_упаковки", 
                                    пл_компл.Фчас_упаковки AS "пл_компл.Фчас_упаковки", 
                                    пл_отк.Нчас_контр AS "пл_отк.Нчас_контр", 
                                    пл_отк.Фчас_контр AS "пл_отк.Фчас_контр", 
                                    plan.Нчас_вспом AS "plan.Нчас_вспом", 
                                    plan.Фчас_вспом AS "plan.Фчас_вспом",
                                    пл_чпу.Фчас_чпу AS "пл_чпу.Фчас_чпу",

                                    пл_рскр.Нчас_рскр AS "пл_рскр.Нчас_рскр", 
                                    пл_оснтк.Нчас_оснтк AS "пл_оснтк.Нчас_оснтк", 
                                    пл_швк.Нчас_швк AS "пл_швк.Нчас_швк", 
                                    пл_сбтк.Нчас_сбтк AS "пл_сбтк.Нчас_сбтк", 
                                    пл_сбмл.Нчас_сбмл AS "пл_сбмл.Нчас_сбмл", 
                                    пл_нбвк.Нчас_нбвк AS "пл_нбвк.Нчас_нбвк", 
                                    пл_свг.Нчас_свг AS "пл_свг.Нчас_свг", 
                                    пл_сббси.Нчас_сббси AS "пл_сббси.Нчас_сббси", 
                                    пл_упквк.Нчас_упквк AS "пл_упквк.Нчас_упквк", 
                                    пл_кмпл.Нчас_кмпл AS "пл_кмпл.Нчас_кмпл", 
                                    пл_откк.Нчас_откк AS "пл_откк.Нчас_откк", 
                                    пл_чпу.Нчас_чпу AS "пл_чпу.Нчас_чпу", 

                                    пл_рскр.Фчас_рскр AS "пл_рскр.Фчас_рскр", 
                                    пл_оснтк.Фчас_оснтк AS "пл_оснтк.Фчас_оснтк", 
                                    пл_швк.Фчас_швк AS "пл_швк.Фчас_швк", 
                                    пл_сбтк.Фчас_сбтк AS "пл_сбтк.Фчас_сбтк", 
                                    пл_сбмл.Фчас_сбмл AS "пл_сбмл.Фчас_сбмл", 
                                    пл_нбвк.Фчас_нбвк AS "пл_нбвк.Фчас_нбвк", 
                                    пл_свг.Фчас_свг AS "пл_свг.Фчас_свг", 
                                    пл_сббси.Фчас_сббси AS "пл_сббси.Фчас_сббси", 
                                    пл_упквк.Фчас_упквк AS "пл_упквк.Фчас_упквк", 
                                    пл_кмпл.Фчас_кмпл AS "пл_кмпл.Фчас_кмпл", 
                                    пл_откк.Фчас_откк AS "пл_откк.Фчас_откк", 

                                    пл_рскр.ПДата_нач_рскр AS "пл_рскр.ПДата_нач_рскр", 
                                    пл_оснтк.ПДата_нач_оснтк AS "пл_оснтк.ПДата_нач_оснтк", 
                                    пл_швк.ПДата_нач_швк AS "пл_швк.ПДата_нач_швк", 
                                    пл_сбтк.ПДата_нач_сбтк AS "пл_сбтк.ПДата_нач_сбтк", 
                                    пл_сбмл.ПДата_нач_сбмл AS "пл_сбмл.ПДата_нач_сбмл", 
                                    пл_нбвк.ПДата_нач_нбвк AS "пл_нбвк.ПДата_нач_нбвк", 
                                    пл_свг.ПДата_нач_свг AS "пл_свг.ПДата_нач_свг", 
                                    пл_сббси.ПДата_нач_сббси AS "пл_сббси.ПДата_нач_сббси", 
                                    пл_упквк.ПДата_нач_упквк AS "пл_упквк.ПДата_нач_упквк", 
                                    пл_кмпл.ПДата_нач_кмпл AS "пл_кмпл.ПДата_нач_кмпл", 
                                    пл_откк.ПДата_нач_откк AS "пл_откк.ПДата_нач_откк", 

                                    пл_рскр.ПДата_зав_рскр AS "пл_рскр.ПДата_зав_рскр", 
                                    пл_оснтк.ПДата_зав_оснтк AS "пл_оснтк.ПДата_зав_оснтк", 
                                    пл_швк.ПДата_зав_швк AS "пл_швк.ПДата_зав_швк", 
                                    пл_сбтк.ПДата_зав_сбтк AS "пл_сбтк.ПДата_зав_сбтк", 
                                    пл_сбмл.ПДата_зав_сбмл AS "пл_сбмл.ПДата_зав_сбмл", 
                                    пл_нбвк.ПДата_зав_нбвк AS "пл_нбвк.ПДата_зав_нбвк", 
                                    пл_свг.ПДата_зав_свг AS "пл_свг.ПДата_зав_свг", 
                                    пл_сббси.ПДата_зав_сббси AS "пл_сббси.ПДата_зав_сббси", 
                                    пл_упквк.ПДата_зав_упквк AS "пл_упквк.ПДата_зав_упквк", 
                                    пл_кмпл.ПДата_зав_кмпл AS "пл_кмпл.ПДата_зав_кмпл", 
                                    пл_откк.ПДата_зав_откк AS "пл_откк.ПДата_зав_откк", 
                                    пл_чпу.ПДата_зав_чпу AS "пл_чпу.ПДата_зав_чпу", 

                                    пл_рскр.ФДата_нач_рскр AS "пл_рскр.ФДата_нач_рскр", 
                                    пл_оснтк.ФДата_нач_оснтк AS "пл_оснтк.ФДата_нач_оснтк", 
                                    пл_швк.ФДата_нач_швк AS "пл_швк.ФДата_нач_швк", 
                                    пл_сбтк.ФДата_нач_сбтк AS "пл_сбтк.ФДата_нач_сбтк", 
                                    пл_сбмл.ФДата_нач_сбмл AS "пл_сбмл.ФДата_нач_сбмл", 
                                    пл_нбвк.ФДата_нач_нбвк AS "пл_нбвк.ФДата_нач_нбвк", 
                                    пл_свг.ФДата_нач_свг AS "пл_свг.ФДата_нач_свг", 
                                    пл_сббси.ФДата_нач_сббси AS "пл_сббси.ФДата_нач_сббси", 
                                    пл_упквк.ФДата_нач_упквк AS "пл_упквк.ФДата_нач_упквк", 
                                    пл_кмпл.ФДата_нач_кмпл AS "пл_кмпл.ФДата_нач_кмпл", 
                                    пл_откк.ФДата_нач_откк AS "пл_откк.ФДата_нач_откк", 

                                    пл_рскр.ФДата_зав_рскр AS "пл_рскр.ФДата_зав_рскр", 
                                    пл_оснтк.ФДата_зав_оснтк AS "пл_оснтк.ФДата_зав_оснтк", 
                                    пл_швк.ФДата_зав_швк AS "пл_швк.ФДата_зав_швк", 
                                    пл_сбтк.ФДата_зав_сбтк AS "пл_сбтк.ФДата_зав_сбтк", 
                                    пл_сбмл.ФДата_зав_сбмл AS "пл_сбмл.ФДата_зав_сбмл", 
                                    пл_нбвк.ФДата_зав_нбвк AS "пл_нбвк.ФДата_зав_нбвк", 
                                    пл_свг.ФДата_зав_свг AS "пл_свг.ФДата_зав_свг", 
                                    пл_сббси.ФДата_зав_сббси AS "пл_сббси.ФДата_зав_сббси", 
                                    пл_упквк.ФДата_зав_упквк AS "пл_упквк.ФДата_зав_упквк", 
                                    пл_кмпл.ФДата_зав_кмпл AS "пл_кмпл.ФДата_зав_кмпл", 
                                    пл_откк.ФДата_зав_откк AS "пл_откк.ФДата_зав_откк",

                                    пл_заг.Дата_обесп_заг AS "пл_заг.Дата_обесп_заг",
                                    пл_компл.Дата_обесп_компл AS "пл_компл.Дата_обесп_компл",
                                    пл_сб.Дата_обесп_сб AS "пл_сб.Дата_обесп_сб",
                                    пл_покр.Дата_обесп_покр AS "пл_покр.Дата_обесп_покр",
                                    пл_мех.Дата_обесп_мех AS "пл_мех.Дата_обесп_мех",
                                    пл_отк.Дата_обесп_отк AS "пл_отк.Дата_обесп_отк",
                                    пл_рскр.Дата_обесп_рскр AS "пл_рскр.Дата_обесп_рскр",
                                    пл_оснтк.Дата_обесп_оснтк AS "пл_оснтк.Дата_обесп_оснтк",
                                    пл_швк.Дата_обесп_швк AS "пл_швк.Дата_обесп_швк",
                                    пл_сбтк.Дата_обесп_сбтк AS "пл_сбтк.Дата_обесп_сбтк",
                                    пл_сбмл.Дата_обесп_сбмл AS "пл_сбмл.Дата_обесп_сбмл",
                                    пл_нбвк.Дата_обесп_нбвк AS "пл_нбвк.Дата_обесп_нбвк",
                                    пл_свг.Дата_обесп_свг AS "пл_свг.Дата_обесп_свг",
                                    пл_сббси.Дата_обесп_сббси AS "пл_сббси.Дата_обесп_сббси",
                                    пл_упквк.Дата_обесп_упквк AS "пл_упквк.Дата_обесп_упквк",
                                    пл_кмпл.Дата_обесп_кмпл AS "пл_кмпл.Дата_обесп_кмпл",
                                    пл_откк.Дата_обесп_откк AS "пл_откк.Дата_обесп_откк",
                                    пл_чпу.Дата_обесп_чпу AS "пл_чпу.Дата_обесп_чпу"



                                 FROM plan INNER JOIN  
                                 пл_топ  ON plan.Пномер == пл_топ.НомПл,
                                пл_заг  ON plan.Пномер == пл_заг.НомПл,
                                пл_мех  ON plan.Пномер == пл_мех.НомПл,
                                пл_сб  ON plan.Пномер == пл_сб.НомПл,
                                пл_покр  ON plan.Пномер == пл_покр.НомПл,
                                пл_компл  ON plan.Пномер == пл_компл.НомПл, 
                                пл_отк  ON plan.Пномер == пл_отк.НомПл, 
                                пл_рскр ON пл_рскр.НомПл = plan.Пномер,
                                пл_оснтк ON пл_оснтк.НомПл = plan.Пномер,
                                пл_швк ON пл_швк.НомПл = plan.Пномер,
                                пл_сбтк ON пл_сбтк.НомПл = plan.Пномер,
                                пл_сбмл ON пл_сбмл.НомПл = plan.Пномер,
                                пл_нбвк ON пл_нбвк.НомПл = plan.Пномер,
                                пл_свг ON пл_свг.НомПл = plan.Пномер,
                                пл_сббси ON пл_сббси.НомПл = plan.Пномер,
                                пл_упквк ON пл_упквк.НомПл = plan.Пномер,
                                пл_кмпл ON пл_кмпл.НомПл = plan.Пномер,
                                пл_откк ON пл_откк.НомПл = plan.Пномер,
                                пл_чпу ON пл_чпу.НомПл = plan.Пномер

                                {where};""" #22.10.25
    return CSQ.custom_request_c(db_kplan, request, rez_dict=True, one=one)
# --06.06.2025 (по задаче 100055177 )

class Pozitions():
    def __init__(self,p_noms:list,db_kpl,db_naryad,db_resxml,db_users,parent_self=None, load_loacal_graf=False,
                 load_day_plan=False):
        if p_noms == []:
            postfix_pnoms = ''
            postfix_pnoms_dates = ''
        else:
            postfix_pnoms = f''' WHERE plan.Пномер in ({CSQ.prepare_list_to_tuple(p_noms)})'''
            postfix_pnoms_dates = f""" 
                          WHERE Пномер in ({CSQ.prepare_list_to_tuple(p_noms)})"""

        postfix_local_graf = ''
        postfix_day_plan = ''
        if load_loacal_graf:
            postfix_local_graf = f', plan.local_graf'
        if load_day_plan:
            postfix_day_plan = f', plan.fact_jurnal_blolb_data'
        request = f"""
                SELECT 
                plan.Пномер,
                plan.Дата_внесения, 
                plan.Позиция, 
                plan.Направление_деятельности, 
                plan.Статус, 
                plan.Статус_норм, 
                plan.Фдата_получения_КД, 
                plan.МК, 
                plan.Нчас_заявка_мат, 
                plan.Пдата_нач_заявка_мат, 
                plan.Пдата_зав_заявка_мат, 
                plan.Фчас_заявка_мат, 
                plan.Фдата_нач_заявка_мат, 
                plan.Фдата_зав_заявка_мат, 
                plan.Нчас_заявка_аутсорс, 
                plan.Пдата_нач_заявка_аутсорс, 
                plan.Пдата_зав_заявка_аутсорс, 
                plan.Фчас_заявка_аутсорс, 
                plan.Фдата_нач_заявка_аутсорс, 
                plan.Фдата_зав_заявка_аутсорс, 
                plan.Нчас_вспом, 
                plan.Пдата_нач_вспом, 
                plan.Пдата_зав_вспом, 
                plan.Фчас_вспом, 
                plan.Фдата_нач_вспом, 
                plan.Фдата_зав_вспом, 
                plan.Фчас_доп_раб, 
                знпр.Этапы_ЕРП, 
                plan.Готовность_ПУ, 
                plan.Постановка_в_план, 
                plan.Примечание, 
                plan.Приоритет{postfix_local_graf}{postfix_day_plan} 

                 FROM plan INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер,
                 знпр ON знпр.s_num = пл_оуп.Пномер_ЗП {postfix_pnoms}
                ;"""
        rows = CSQ.custom_request_c(db_kpl, request, rez_dict=True) # 06.06.2025 (по задаче 100055177 )

        # request = f"""
        #                   SELECT plan.Пдата_зав_вспом, plan.Пдата_нач_вспом,
        #                     пл_заг.ПДата_зав_заг, пл_заг.ПДата_нач_заг,
        #                     пл_мех.Пдата_зав_мехобр, пл_мех.Пдата_нач_мехобр,
        #                     пл_сб.Пдата_зав_сб, пл_сб.Пдата_нач_сб,
        #                     пл_покр.Пдата_зав_покр, пл_покр.Пдата_нач_покр,
        #                     пл_компл.ПДата_зав_комплект_упаковки,  пл_компл.ПДата_нач_комплект_упаковки
        #                    FROM plan INNER JOIN
        #                   пл_заг  ON plan.Пномер == пл_заг.НомПл,
        #                   пл_мех  ON plan.Пномер == пл_мех.НомПл,
        #                   пл_сб  ON plan.Пномер == пл_сб.НомПл,
        #                   пл_покр  ON plan.Пномер == пл_покр.НомПл,
        #                   пл_компл  ON plan.Пномер == пл_компл.НомПл {postfix_pnoms_dates};"""
        data_etaps = F.deploy_dict_c(get_db_rows_pl_etaps(p_noms), 'Пномер')

        # rows_dates_etaps = CSQ.custom_request_c(db_kpl, request, rez_dict=True)
        self.parent_self = parent_self
        self.dict_pozs:dict[int,Pozition] = dict()
        for i, item in enumerate(rows):
            row_dates_etaps= data_etaps.get(item['Пномер'])
            self.dict_pozs[item['Пномер']] =  Pozition(item,db_kpl,db_naryad,db_resxml,db_users,self.parent_self, row_dates_etaps= row_dates_etaps)
    
    def load_kpl_table(self,name_table):


        request = f""" 
                                SELECT * FROM {name_table} 
                                WHERE НомПл in ({CSQ.prepare_list_to_tuple(list(self.dict_pozs.keys()))});"""
        
        rows = CSQ.custom_request_c(CFG.Config.project.db_kplan, request, rez_dict=True)
        if name_table == 'пл_оуп':
            request = f"""
                    SELECT * FROM 
                    знпр 
                    WHERE знпр.s_num in ({CSQ.prepare_list_to_tuple([_['Пномер_ЗП'] for _ in rows])});"""
            rows_оуп = CSQ.custom_request_c(CFG.Config.project.db_kplan, request, rez_dict=True)
            row_оуп_zero = CSQ.dict_zero_val_row(CFG.Config.project.db_kplan, 'знпр')

        for num_poz, poz in self.dict_pozs.items():
            poz.dict_tables[name_table] = dict()
            row = None
            for row_iter in rows:
                if row_iter['НомПл'] == num_poz:
                    row = row_iter
            if row is None:
                raise ValueError(f'Pozitions: load_kpl_table row is None')

            for key in row.keys():
                exec(f'poz.dict_tables["{name_table}"]["{key.replace(".", "_")}"] = row[key]')

            if name_table == 'пл_оуп':
                row_оуп = None
                for row_iter_оуп in rows_оуп:
                    if row_iter_оуп['s_num'] == row['Пномер_ЗП']:
                        row_оуп = row_iter_оуп

                if row_iter_оуп is None:
                    row_оуп = row_оуп_zero
                else:
                    for key in row_оуп.keys():
                        field = key.replace(".", "_")
                        if field in poz.dict_tables[name_table]:
                            poz.dict_tables[name_table][f'{field}_base'] = poz.dict_tables[name_table][field]
                        exec(f'poz.dict_tables["{name_table}"]["{field}"] = row_оуп[key]')

class Pozition():
    def __init__(self,p_nom_or_row_preload,db_kpl=None,db_naryad=None,db_resxml=None,db_users=None,parent_self=None,
                 load_loacal_graf=False,row_dates_etaps=None,load_day_plan=False):
        if p_nom_or_row_preload is None:
            raise ValueError(f'Pozition init-> p_nom_or_row_preload is None')
        if db_kpl == None:
            db_kpl = CFG.Config.project.db_kplan
        if db_naryad == None:
            db_naryad = CFG.Config.project.db_naryad
        if db_resxml == None:
            db_resxml = CFG.Config.project.db_resxml
        if db_users == None:
            db_users = CFG.Config.project.db_users
        def get_data_etaps(Пномер): # 06.06.2025 (по задаче 100055177 )
            ADDITIONAL_FIELDS = {
                "пл_сб.Нчас_слсб",
                "пл_сб.Фчас_слсб",
                "пл_сб.Нчас_св",
                "пл_сб.Фчас_св",
                "пл_сб.Нчас_зач",
                "пл_сб.Фчас_зач", }
            if isinstance(Пномер,int):
                resp = get_db_rows_pl_etaps(Пномер)
            # if isinstance(Пномер,int):
            #
            #
            #     request = f"""
            #                                 SELECT plan.Пдата_зав_вспом, plan.Пдата_нач_вспом,
            #                                   пл_заг.ПДата_зав_заг, пл_заг.ПДата_нач_заг,
            #                                   пл_мех.Пдата_зав_мехобр, пл_мех.Пдата_нач_мехобр,
            #                                   пл_сб.Пдата_зав_сб, пл_сб.Пдата_нач_сб,
            #                                   пл_покр.Пдата_зав_покр, пл_покр.Пдата_нач_покр,
            #                                   пл_компл.ПДата_зав_комплект_упаковки,  пл_компл.ПДата_нач_комплект_упаковки,
            #                                   пл_отк.Пдата_зав_контр,  пл_отк.Пдата_нач_контр,
            #                                    пл_топ.Пдата_зав_ТД,  пл_топ.Пдата_нач_ТД,
            #
            #
            #                                     пл_топ.Пдата_нач_ТД AS "пл_топ.Пдата_нач_ТД",
            #                                     пл_топ.Пдата_зав_ТД AS "пл_топ.Пдата_зав_ТД",
            #                                     plan.Пдата_зав_вспом AS "plan.Пдата_зав_вспом",
            #                                     plan.Пдата_нач_вспом AS "plan.Пдата_нач_вспом",
            #                                     пл_заг.ПДата_зав_заг AS "пл_заг.ПДата_зав_заг",
            #                                     пл_заг.ПДата_нач_заг AS "пл_заг.ПДата_нач_заг",
            #                                     пл_мех.Пдата_зав_мехобр AS "пл_мех.Пдата_зав_мехобр",
            #                                     пл_мех.Пдата_нач_мехобр AS "пл_мех.Пдата_нач_мехобр",
            #                                     пл_сб.Пдата_зав_сб AS "пл_сб.Пдата_зав_сб",
            #                                     пл_сб.Пдата_нач_сб AS "пл_сб.Пдата_нач_сб",
            #                                     пл_покр.Пдата_зав_покр AS "пл_покр.Пдата_зав_покр",
            #                                     пл_покр.Пдата_нач_покр AS "пл_покр.Пдата_нач_покр",
            #                                     пл_компл.ПДата_зав_комплект_упаковки AS "пл_компл.ПДата_зав_комплект_упаковки",
            #                                     пл_компл.ПДата_нач_комплект_упаковки AS "пл_компл.ПДата_нач_комплект_упаковки",
            #                                     пл_отк.Пдата_зав_контр AS "пл_отк.Пдата_зав_контр",
            #                                     пл_отк.Пдата_нач_контр AS "пл_отк.Пдата_нач_контр",
            #
            #                                     пл_сб.Нчас_слсб AS "пл_сб.Нчас_слсб",
            #                                     пл_сб.Фчас_слсб AS "пл_сб.Фчас_слсб",
            #                                     пл_сб.Нчас_св AS "пл_сб.Нчас_св",
            #                                     пл_сб.Фчас_св AS "пл_сб.Фчас_св",
            #                                     пл_сб.Нчас_зач AS "пл_сб.Нчас_зач",
            #                                     пл_сб.Фчас_зач AS "пл_сб.Фчас_зач",
            #
            #                                     пл_топ.Фдата_нач_ТД AS "пл_топ.Фдата_нач_ТД",
            #                                     пл_топ.Фдата_зав_ТД AS "пл_топ.Фдата_зав_ТД",
            #                                     plan.Фдата_зав_вспом AS "plan.Фдата_зав_вспом",
            #                                     plan.Фдата_нач_вспом AS "plan.Фдата_нач_вспом",
            #                                     пл_заг.ФДата_зав_заг AS "пл_заг.ФДата_зав_заг",
            #                                     пл_заг.ФДата_нач_заг AS "пл_заг.ФДата_нач_заг",
            #                                     пл_мех.Фдата_зав_мехобр AS "пл_мех.Фдата_зав_мехобр",
            #                                     пл_мех.Фдата_нач_мехобр AS "пл_мех.Фдата_нач_мехобр",
            #                                     пл_сб.Фдата_зав_сб AS "пл_сб.Фдата_зав_сб",
            #                                     пл_сб.Фдата_нач_сб AS "пл_сб.Фдата_нач_сб",
            #                                     пл_покр.Фдата_зав_покр AS "пл_покр.Фдата_зав_покр",
            #                                     пл_покр.Фдата_нач_покр AS "пл_покр.Фдата_нач_покр",
            #                                     пл_компл.ФДата_зав_комплект_упаковки AS "пл_компл.ФДата_зав_комплект_упаковки",
            #                                     пл_компл.ФДата_нач_комплект_упаковки AS "пл_компл.ФДата_нач_комплект_упаковки",
            #                                     пл_отк.Фдата_зав_контр AS "пл_отк.Фдата_зав_контр",
            #                                     пл_отк.Фдата_нач_контр AS "пл_отк.Фдата_нач_контр",
            #
            #                                     пл_топ.Нчас_ТД AS "пл_топ.Нчас_ТД",
            #                                     пл_топ.Фчас_ТД AS "пл_топ.Фчас_ТД",
            #                                     пл_заг.Нчас_заг AS "пл_заг.Нчас_заг",
            #                                     пл_заг.Фчас_заг AS "пл_заг.Фчас_заг",
            #                                     пл_мех.Нчас_мехобр AS "пл_мех.Нчас_мехобр",
            #                                     пл_мех.Фчас_мехобр AS "пл_мех.Фчас_мехобр",
            #                                     пл_сб.Нчас_сб AS "пл_сб.Нчас_сб",
            #                                     пл_сб.Фчас_сб AS "пл_сб.Фчас_сб",
            #                                     пл_покр.Нчас_покр AS "пл_покр.Нчас_покр",
            #                                     пл_покр.Фчас_покр AS "пл_покр.Фчас_покр",
            #                                     пл_компл.Нчас_упаковки AS "пл_компл.Нчас_упаковки",
            #                                     пл_компл.Фчас_упаковки AS "пл_компл.Фчас_упаковки",
            #                                     пл_отк.Нчас_контр AS "пл_отк.Нчас_контр",
            #                                     пл_отк.Фчас_контр AS "пл_отк.Фчас_контр",
            #                                     plan.Нчас_вспом AS "plan.Нчас_вспом",
            #                                     plan.Фчас_вспом AS "plan.Фчас_вспом",
            #
            #                                     пл_рскр.Нчас_рскр AS "пл_рскр.Нчас_рскр",
            #                                     пл_оснтк.Нчас_оснтк AS "пл_оснтк.Нчас_оснтк",
            #                                     пл_швк.Нчас_швк AS "пл_швк.Нчас_швк",
            #                                     пл_сбтк.Нчас_сбтк AS "пл_сбтк.Нчас_сбтк",
            #                                     пл_сбмл.Нчас_сбмл AS "пл_сбмл.Нчас_сбмл",
            #                                     пл_нбвк.Нчас_нбвк AS "пл_нбвк.Нчас_нбвк",
            #                                     пл_свг.Нчас_свг AS "пл_свг.Нчас_свг",
            #                                     пл_сббси.Нчас_сббси AS "пл_сббси.Нчас_сббси",
            #                                     пл_упквк.Нчас_упквк AS "пл_упквк.Нчас_упквк",
            #                                     пл_кмпл.Нчас_кмпл AS "пл_кмпл.Нчас_кмпл",
            #                                     пл_откк.Нчас_откк AS "пл_откк.Нчас_откк",
            #
            #                                     пл_рскр.Фчас_рскр AS "пл_рскр.Фчас_рскр",
            #                                     пл_оснтк.Фчас_оснтк AS "пл_оснтк.Фчас_оснтк",
            #                                     пл_швк.Фчас_швк AS "пл_швк.Фчас_швк",
            #                                     пл_сбтк.Фчас_сбтк AS "пл_сбтк.Фчас_сбтк",
            #                                     пл_сбмл.Фчас_сбмл AS "пл_сбмл.Фчас_сбмл",
            #                                     пл_нбвк.Фчас_нбвк AS "пл_нбвк.Фчас_нбвк",
            #                                     пл_свг.Фчас_свг AS "пл_свг.Фчас_свг",
            #                                     пл_сббси.Фчас_сббси AS "пл_сббси.Фчас_сббси",
            #                                     пл_упквк.Фчас_упквк AS "пл_упквк.Фчас_упквк",
            #                                     пл_кмпл.Фчас_кмпл AS "пл_кмпл.Фчас_кмпл",
            #                                     пл_откк.Фчас_откк AS "пл_откк.Фчас_откк",
            #
            #                                     пл_рскр.ПДата_нач_рскр AS "пл_рскр.ПДата_нач_рскр",
            #                                     пл_оснтк.ПДата_нач_оснтк AS "пл_оснтк.ПДата_нач_оснтк",
            #                                     пл_швк.ПДата_нач_швк AS "пл_швк.ПДата_нач_швк",
            #                                     пл_сбтк.ПДата_нач_сбтк AS "пл_сбтк.ПДата_нач_сбтк",
            #                                     пл_сбмл.ПДата_нач_сбмл AS "пл_сбмл.ПДата_нач_сбмл",
            #                                     пл_нбвк.ПДата_нач_нбвк AS "пл_нбвк.ПДата_нач_нбвк",
            #                                     пл_свг.ПДата_нач_свг AS "пл_свг.ПДата_нач_свг",
            #                                     пл_сббси.ПДата_нач_сббси AS "пл_сббси.ПДата_нач_сббси",
            #                                     пл_упквк.ПДата_нач_упквк AS "пл_упквк.ПДата_нач_упквк",
            #                                     пл_кмпл.ПДата_нач_кмпл AS "пл_кмпл.ПДата_нач_кмпл",
            #                                     пл_откк.ПДата_нач_откк AS "пл_откк.ПДата_нач_откк",
            #
            #                                     пл_рскр.ПДата_зав_рскр AS "пл_рскр.ПДата_зав_рскр",
            #                                     пл_оснтк.ПДата_зав_оснтк AS "пл_оснтк.ПДата_зав_оснтк",
            #                                     пл_швк.ПДата_зав_швк AS "пл_швк.ПДата_зав_швк",
            #                                     пл_сбтк.ПДата_зав_сбтк AS "пл_сбтк.ПДата_зав_сбтк",
            #                                     пл_сбмл.ПДата_зав_сбмл AS "пл_сбмл.ПДата_зав_сбмл",
            #                                     пл_нбвк.ПДата_зав_нбвк AS "пл_нбвк.ПДата_зав_нбвк",
            #                                     пл_свг.ПДата_зав_свг AS "пл_свг.ПДата_зав_свг",
            #                                     пл_сббси.ПДата_зав_сббси AS "пл_сббси.ПДата_зав_сббси",
            #                                     пл_упквк.ПДата_зав_упквк AS "пл_упквк.ПДата_зав_упквк",
            #                                     пл_кмпл.ПДата_зав_кмпл AS "пл_кмпл.ПДата_зав_кмпл",
            #                                     пл_откк.ПДата_зав_откк AS "пл_откк.ПДата_зав_откк",
            #
            #                                     пл_рскр.ФДата_нач_рскр AS "пл_рскр.ФДата_нач_рскр",
            #                                     пл_оснтк.ФДата_нач_оснтк AS "пл_оснтк.ФДата_нач_оснтк",
            #                                     пл_швк.ФДата_нач_швк AS "пл_швк.ФДата_нач_швк",
            #                                     пл_сбтк.ФДата_нач_сбтк AS "пл_сбтк.ФДата_нач_сбтк",
            #                                     пл_сбмл.ФДата_нач_сбмл AS "пл_сбмл.ФДата_нач_сбмл",
            #                                     пл_нбвк.ФДата_нач_нбвк AS "пл_нбвк.ФДата_нач_нбвк",
            #                                     пл_свг.ФДата_нач_свг AS "пл_свг.ФДата_нач_свг",
            #                                     пл_сббси.ФДата_нач_сббси AS "пл_сббси.ФДата_нач_сббси",
            #                                     пл_упквк.ФДата_нач_упквк AS "пл_упквк.ФДата_нач_упквк",
            #                                     пл_кмпл.ФДата_нач_кмпл AS "пл_кмпл.ФДата_нач_кмпл",
            #                                     пл_откк.ФДата_нач_откк AS "пл_откк.ФДата_нач_откк",
            #
            #                                     пл_рскр.ФДата_зав_рскр AS "пл_рскр.ФДата_зав_рскр",
            #                                     пл_оснтк.ФДата_зав_оснтк AS "пл_оснтк.ФДата_зав_оснтк",
            #                                     пл_швк.ФДата_зав_швк AS "пл_швк.ФДата_зав_швк",
            #                                     пл_сбтк.ФДата_зав_сбтк AS "пл_сбтк.ФДата_зав_сбтк",
            #                                     пл_сбмл.ФДата_зав_сбмл AS "пл_сбмл.ФДата_зав_сбмл",
            #                                     пл_нбвк.ФДата_зав_нбвк AS "пл_нбвк.ФДата_зав_нбвк",
            #                                     пл_свг.ФДата_зав_свг AS "пл_свг.ФДата_зав_свг",
            #                                     пл_сббси.ФДата_зав_сббси AS "пл_сббси.ФДата_зав_сббси",
            #                                     пл_упквк.ФДата_зав_упквк AS "пл_упквк.ФДата_зав_упквк",
            #                                     пл_кмпл.ФДата_зав_кмпл AS "пл_кмпл.ФДата_зав_кмпл",
            #                                     пл_откк.ФДата_зав_откк AS "пл_откк.ФДата_зав_откк",
            #
            #                                     пл_заг.Дата_обесп_заг AS "пл_заг.Дата_обесп_заг",
            #                                     пл_компл.Дата_обесп_компл AS "пл_компл.Дата_обесп_компл",
            #                                     пл_сб.Дата_обесп_сб AS "пл_сб.Дата_обесп_сб",
            #                                     пл_покр.Дата_обесп_покр AS "пл_покр.Дата_обесп_покр",
            #                                     пл_мех.Дата_обесп_мех AS "пл_мех.Дата_обесп_мех",
            #                                     пл_отк.Дата_обесп_отк AS "пл_отк.Дата_обесп_отк",
            #                                     пл_рскр.Дата_обесп_рскр AS "пл_рскр.Дата_обесп_рскр",
            #                                     пл_оснтк.Дата_обесп_оснтк AS "пл_оснтк.Дата_обесп_оснтк",
            #                                     пл_швк.Дата_обесп_швк AS "пл_швк.Дата_обесп_швк",
            #                                     пл_сбтк.Дата_обесп_сбтк AS "пл_сбтк.Дата_обесп_сбтк",
            #                                     пл_сбмл.Дата_обесп_сбмл AS "пл_сбмл.Дата_обесп_сбмл",
            #                                     пл_нбвк.Дата_обесп_нбвк AS "пл_нбвк.Дата_обесп_нбвк",
            #                                     пл_свг.Дата_обесп_свг AS "пл_свг.Дата_обесп_свг",
            #                                     пл_сббси.Дата_обесп_сббси AS "пл_сббси.Дата_обесп_сббси",
            #                                     пл_упквк.Дата_обесп_упквк AS "пл_упквк.Дата_обесп_упквк",
            #                                     пл_кмпл.Дата_обесп_кмпл AS "пл_кмпл.Дата_обесп_кмпл",
            #                                     пл_откк.Дата_обесп_откк AS "пл_откк.Дата_обесп_откк"
            #
            #
            #
            #                                  FROM plan INNER JOIN
            #                                  пл_топ  ON plan.Пномер == пл_топ.НомПл,
            #                                 пл_заг  ON plan.Пномер == пл_заг.НомПл,
            #                                 пл_мех  ON plan.Пномер == пл_мех.НомПл,
            #                                 пл_сб  ON plan.Пномер == пл_сб.НомПл,
            #                                 пл_покр  ON plan.Пномер == пл_покр.НомПл,
            #                                 пл_компл  ON plan.Пномер == пл_компл.НомПл,
            #                                 пл_отк  ON plan.Пномер == пл_отк.НомПл,
            #                                 пл_рскр ON пл_рскр.НомПл = plan.Пномер,
            #                                 пл_оснтк ON пл_оснтк.НомПл = plan.Пномер,
            #                                 пл_швк ON пл_швк.НомПл = plan.Пномер,
            #                                 пл_сбтк ON пл_сбтк.НомПл = plan.Пномер,
            #                                 пл_сбмл ON пл_сбмл.НомПл = plan.Пномер,
            #                                 пл_нбвк ON пл_нбвк.НомПл = plan.Пномер,
            #                                 пл_свг ON пл_свг.НомПл = plan.Пномер,
            #                                 пл_сббси ON пл_сббси.НомПл = plan.Пномер,
            #                                 пл_упквк ON пл_упквк.НомПл = plan.Пномер,
            #                                 пл_кмпл ON пл_кмпл.НомПл = plan.Пномер,
            #                                 пл_откк ON пл_откк.НомПл = plan.Пномер
            #
            #                                 WHERE Пномер == {Пномер};"""
            #     resp = CSQ.custom_request_c(self.db, request, rez_dict=True)[0]

            else:
                resp = row_dates_etaps
            row_dates_etap = {k: v for k, v in resp.items() if 'пдата_' in k.lower() and '.' not in k}
            row_dates_etap_fact = {k: v for k, v in resp.items() if 'фдата_' in k.lower()}
            row_dates_etap_plan = {k: v for k, v in resp.items() if 'пдата_' in k.lower() and '.' in k}
            row_time_etap = {k: v for k, v in resp.items() if
                             'час_' in k.lower() and k not in ADDITIONAL_FIELDS}
            row_time_add_etap = {k: v for k, v in resp.items() if
                             'час_' in k.lower() and k in ADDITIONAL_FIELDS}
            row_dates_supply = {k: v for k, v in resp.items() if 'дата_обесп' in k.lower() and '.' in k}
            return row_dates_etap,row_time_etap,row_dates_etap_fact,row_dates_etap_plan,row_time_add_etap,row_dates_supply
        self.parent_self = parent_self
        self.db = db_kpl
        self.db_naryad = db_naryad
        self.db_resxml = db_resxml
        self.db_users = db_users

        self.Пномер = None
        self.Дата_внесения = None
        self.Позиция = None
        self.Направление_деятельности = None
        self.Статус = None
        self.Статус_норм = None
        self.Фдата_получения_КД = None
        self.МК = None
        self.Нчас_заявка_мат = None
        self.Пдата_нач_заявка_мат = None
        self.Пдата_зав_заявка_мат = None
        self.Фчас_заявка_мат = None
        self.Фдата_нач_заявка_мат = None
        self.Фдата_зав_заявка_мат = None
        self.Нчас_заявка_аутсорс = None
        self.Пдата_нач_заявка_аутсорс = None
        self.Пдата_зав_заявка_аутсорс = None
        self.Фчас_заявка_аутсорс = None
        self.Фдата_нач_заявка_аутсорс = None
        self.Фдата_зав_заявка_аутсорс = None
        self.Нчас_вспом = None
        self.Пдата_нач_вспом = None
        self.Пдата_зав_вспом = None
        self.Фчас_вспом = None
        self.Фдата_нач_вспом = None
        self.Фдата_зав_вспом = None
        self.Фчас_доп_раб = None
        self.Этапы_ЕРП = None
        self.Готовность_ПУ = None
        self.Постановка_в_план = None
        self.Примечание = None
        self.Приоритет = None
        self.local_graf = None
        self.fact_jurnal_blolb_data = None
        if F.is_numeric(p_nom_or_row_preload):
            p_nom_or_row_preload = int(p_nom_or_row_preload)
        if not isinstance(p_nom_or_row_preload,int) :
            if row_dates_etaps == None:
                row_dates_etap,row_time_etap,row_dates_etap_fact,row_dates_etap_plan,row_time_add_etap,row_dates_supply = get_data_etaps(p_nom_or_row_preload.Пномер)
            row = p_nom_or_row_preload
            row_dates_etap = row_dates_etaps
        else:
            p_nom = p_nom_or_row_preload
            postfix_local_graf= ''
            postfix_day_plan = ''
            if load_loacal_graf:
                postfix_local_graf = f', plan.local_graf'
            if load_day_plan:
                postfix_day_plan = f', plan.fact_jurnal_blolb_data'
            request = f"""
                            SELECT 
                            plan.Пномер,
                            plan.Дата_внесения, 
                            plan.Позиция, 
                            plan.Направление_деятельности, 
                            plan.Статус, 
                            plan.Статус_норм, 
                            plan.Фдата_получения_КД, 
                            plan.МК, 
                            plan.Нчас_заявка_мат, 
                            plan.Пдата_нач_заявка_мат, 
                            plan.Пдата_зав_заявка_мат, 
                            plan.Фчас_заявка_мат, 
                            plan.Фдата_нач_заявка_мат, 
                            plan.Фдата_зав_заявка_мат, 
                            plan.Нчас_заявка_аутсорс, 
                            plan.Пдата_нач_заявка_аутсорс, 
                            plan.Пдата_зав_заявка_аутсорс, 
                            plan.Фчас_заявка_аутсорс, 
                            plan.Фдата_нач_заявка_аутсорс, 
                            plan.Фдата_зав_заявка_аутсорс, 
                            plan.Нчас_вспом, 
                            plan.Пдата_нач_вспом, 
                            plan.Пдата_зав_вспом, 
                            plan.Фчас_вспом, 
                            plan.Фдата_нач_вспом, 
                            plan.Фдата_зав_вспом, 
                            plan.Фчас_доп_раб, 
                            знпр.Этапы_ЕРП, 
                            plan.Готовность_ПУ, 
                            plan.Постановка_в_план, 
                            plan.Примечание, 
                            plan.Приоритет{postfix_local_graf}{postfix_day_plan} 

                             FROM plan INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер,
                             знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
            WHERE plan.Пномер == {p_nom};"""
            row = CSQ.custom_request_c(db_kpl,request,rez_dict=True)
            if len(row) == 0:
                print(f'Pozition Остутвет в БД кпл {p_nom}')
                return
            row = row[0]


        self.dict_tables = dict()
        self.row = row
        for key in row.keys():
            exec(f'self.{key.replace(".","_")} = row[key]')

        row_dates_etap, row_time_etap,row_dates_etap_fact,row_dates_etap_plan,row_time_add_etap,row_dates_supply = get_data_etaps(p_nom_or_row_preload)


        self.max_date = ''
        self.min_date = ''
        max_date = F.strtodate('2001-01-01', "%Y-%m-%d")
        min_date = F.strtodate('2201-01-01', "%Y-%m-%d")


        def apply_min_max(min,max, date, mask):
            if F.is_date(date,mask):
                if F.strtodate(date,mask)>max_date:
                    max = F.strtodate(date,mask)

                if F.strtodate(date,mask)<min_date:
                    min = F.strtodate(date,mask)
            return min,max

        for data in row_dates_etap.values():
            min_date,max_date = apply_min_max(min_date,max_date, data, "%Y-%m-%d")
        for data in row_dates_etap_fact.values():
            min_date, max_date = apply_min_max(min_date, max_date, data, "%Y-%m-%d")
        for data in row_dates_etap_plan.values():
            min_date, max_date = apply_min_max(min_date, max_date, data, "%Y-%m-%d")
        for data in row_dates_supply.values():
            min_date, max_date = apply_min_max(min_date, max_date, data, "%Y-%m-%d")
        if self.fact_jurnal_blolb_data:
            self.fact_jurnal_data = F.from_binary_pickle(self.fact_jurnal_blolb_data)
            for etap in self.fact_jurnal_data:
                for data in etap:
                    min_date,max_date = apply_min_max(min_date,max_date, data, "%d\n%m\n%y")


        self.max_date = F.datetostr(max_date,'%d.%m.%Y')
        self.min_date = F.datetostr(min_date,'%d.%m.%Y')

        self.row_dates_etap = row_dates_etap
        self.row_time_etap = row_time_etap
        self.row_dates_etap_fact = row_dates_etap_fact
        self.row_dates_etap_plan = row_dates_etap_plan
        self.row_time_add_etap = row_time_add_etap
        self.row_dates_supply = row_dates_supply


    def update_dates_supply(self,dict_dates:dict[str:datetime.datetime]):
       return self.update_row_etaps(dict_dates)


    @staticmethod
    def set_flag_recalc_dates(db_kplan:str,num_poz:int,val:int):
        CSQ.custom_request_c(db_kplan,f"""UPDATE plan SET (Потребность_пересч_сроков) = ({val}) WHERE Пномер = {num_poz};""")


    def get_napravl(self):
        rez = CSQ.custom_request_c(self.db,f"""SELECT * FROM napravl_deyat INNER JOIN 
        napravlenie ON napravl_deyat.Направление = napravlenie.Пномер WHERE napravl_deyat.Пномер 
         = {self.Направление_деятельности} and napravl_deyat.poki == {CFG.Config.place.poki}""",rez_dict=True)[0]
        return rez

    def get_plan_etaps_dates(self):

        rez = {'Лазерная резка':{'нач':self.row_dates_etap['ПДата_нач_заг'],'зав':self.row_dates_etap['ПДата_зав_заг']},
                'Токарка+фрезеровка':{'нач':self.row_dates_etap['Пдата_нач_мехобр'],'зав':self.row_dates_etap['Пдата_зав_мехобр']},
                'Сборка+сварка':{'нач':self.row_dates_etap['Пдата_нач_сб'],'зав':self.row_dates_etap['Пдата_зав_сб']},
                'Зачистка':{'нач':self.row_dates_etap['Пдата_нач_сб'],'зав':self.row_dates_etap['Пдата_зав_сб']},
                'Вспомогательная':{'нач':self.row_dates_etap['Пдата_нач_вспом'],'зав':self.row_dates_etap['Пдата_зав_вспом']},
                'Покраска':{'нач':self.row_dates_etap['Пдата_нач_покр'],'зав':self.row_dates_etap['Пдата_зав_покр']},
                'Подготовка монтажного комплекта':{'нач':self.row_dates_etap['ПДата_нач_комплект_упаковки'],'зав':self.row_dates_etap['ПДата_зав_комплект_упаковки']},
                'Упаковка и комплектование ЗИП':{'нач':self.row_dates_etap['ПДата_нач_комплект_упаковки'],'зав':self.row_dates_etap['ПДата_зав_комплект_упаковки']},
                'Шеф-монтаж':{'нач':self.row_dates_etap['ПДата_нач_комплект_упаковки'],'зав':self.row_dates_etap['ПДата_зав_комплект_упаковки']},
        }


        return rez

    def get_erp_data(self, last_days=0):
        m = ERP.OrdersComposit()
        # m.get_orders(last_days=2)  # find_me="Статус eq 'КПроизводству'"
        self.load_kpl_table('пл_оуп')
        year = F.datetostr(F.strtodate(self.dict_tables['пл_оуп']['Дата_заявки_на_произв'],"%Y-%m-%d"),"%Y")
        orders = m.get_orders(number=self.dict_tables['пл_оуп']['№ERP'],year = year)
        for order_name, v in orders.items():
            #print(order_name)
            nomenglatures = m.get_nomenglature_order(order_name)
        if self.dict_tables['пл_оуп']['№ERP'] in orders:
            return orders[self.dict_tables['пл_оуп']['№ERP']]
        else:
            return

    @classmethod
    def get_erp_data_last_days(cls,last_days=30):
        m = ERP.OrdersComposit()
        # m.get_orders(last_days=2)  # find_me="Статус eq 'КПроизводству'"
        orders = m.get_orders(last_days=last_days)
        for order_name, v in orders.items():
            #print(order_name)
            nomenglatures = m.get_nomenglature_order(order_name)
        return orders

    @classmethod
    def get_erp_data_py(cls,py):
        m = ERP.OrdersComposit()
        # m.get_orders(last_days=2)  # find_me="Статус eq 'КПроизводству'"
        orders = m.get_orders(number=py)
        for order_name, v in orders.items():
            #print(order_name)
            nomenglatures = m.get_nomenglature_order(order_name)
        return orders


    def load_kpl_table(self,name_table):

        request = f"""
                SELECT * FROM {name_table} 
                WHERE НомПл == {self.Пномер};"""
        row = CSQ.custom_request_c(self.db, request, rez_dict=True)[0]
        self.dict_tables[name_table] = dict()
        for key in row.keys():
            exec(f'self.dict_tables["{name_table}"]["{key.replace(".", "_")}"] = row[key]')
        if name_table == 'пл_оуп':
            if self.dict_tables[name_table]['Пномер_ЗП']:
                request = f"""
                                SELECT * FROM знпр 
                                WHERE s_num == {self.dict_tables[name_table]['Пномер_ЗП']};"""
                row = CSQ.custom_request_c(self.db, request, rez_dict=True)[0]


            else:
                row = CSQ.dict_zero_val_row(self.db,'знпр')
            for key in row.keys():
                field = key.replace(".", "_")
                if field in self.dict_tables[name_table]:
                    self.dict_tables[name_table][f'{field}_base'] = self.dict_tables[name_table][field]
                exec(f'self.dict_tables["{name_table}"]["{field}"] = row[key]')
    def get_list_link_mk(self):
        list_mk = CSQ.custom_request_c(self.db_naryad,f"""SELECT Пномер FROM mk 
         WHERE НомКплан == {self.Пномер} AND Дата_завершения == "" AND На_удал == 0;""",hat_c=False,one_column=True)
        return list_mk

    def get_norm_by_range_dates(self, start_date_obj, end_date_obj,LIST_PROFESSIONS,mode='left_right')->dict:
        dict_tbl_name_to_nick = {'план_'+k['name_tbl']:k['nick_name'] for k in LIST_PROFESSIONS}
        dict_from_cld = dict()
        data_cld = F.from_binary_pickle(self.local_graf)[0]
        if mode == 'after_right':
            for day in data_cld['data'].keys():
                if  day > end_date_obj:
                    for podr in data_cld['data'][day]['podr']:
                        podr_data = data_cld['data'][day]['podr'][podr]
                        if isinstance(podr_data, list) and 'план_' in podr:
                            if podr not in dict_from_cld:
                                dict_from_cld[podr] = 0
                            for item in podr_data:
                                dict_from_cld[podr] += item['Время_час']
        if mode == 'right':
            for day in data_cld['data'].keys():
                if  day <= end_date_obj:
                    for podr in data_cld['data'][day]['podr']:
                        podr_data = data_cld['data'][day]['podr'][podr]
                        if isinstance(podr_data, list) and 'план_' in podr:
                            if podr not in dict_from_cld:
                                dict_from_cld[podr] = 0
                            for item in podr_data:
                                dict_from_cld[podr] += item['Время_час']
        if mode == 'left_right':
            for day in data_cld['data'].keys():
                if day >= start_date_obj and day <= end_date_obj:
                    for podr in data_cld['data'][day]['podr']:
                        podr_data = data_cld['data'][day]['podr'][podr]
                        if isinstance(podr_data,list) and 'план_' in podr:
                            if podr not in dict_from_cld:
                                dict_from_cld[podr] = 0
                            for item in podr_data:
                                dict_from_cld[podr]+=item['Время_час']

        result_minutes = dict()
        for podr , val in dict_from_cld.items():
            if podr in dict_tbl_name_to_nick:
                nick_name = dict_tbl_name_to_nick[podr]
                if nick_name in ('Сборка_н_см','Сварка_н_см','Зачистка_н_см'):
                    summ_sb = self.row_time_etap['пл_сб.Нчас_сб']
                    part_sv = 0
                    part_sl = 0
                    part_zch = 0
                    if summ_sb >0:
                        part_sv = self.row_time_add_etap['пл_сб.Нчас_св'] * val / summ_sb
                        part_sl = self.row_time_add_etap['пл_сб.Нчас_слсб'] * val / summ_sb
                        part_zch = self.row_time_add_etap['пл_сб.Нчас_зач'] * val / summ_sb
                    if 'Сварка_н_см' not in result_minutes:
                        result_minutes['Сварка_н_см'] = 0
                    if 'Сборка_н_см' not in result_minutes:
                        result_minutes['Сборка_н_см'] = 0
                    if 'Зачистка_н_см' not in result_minutes:
                        result_minutes['Зачистка_н_см'] = 0
                    result_minutes['Сварка_н_см'] += part_sv * 60
                    result_minutes['Сборка_н_см'] += part_sl * 60
                    result_minutes['Зачистка_н_см'] += part_zch * 60
                else:
                    if nick_name not in result_minutes:
                        result_minutes[nick_name] = 0
                    result_minutes[nick_name] += val*60
        return result_minutes

    @CQT.onerror
    def calc_osvoeno(self,DICT_PROFESSIONS,DICT_OP_NAME,koef_vneplana=1,koef_pogr_norm=1):
        #вфбрать все марушрутки
        list_mk = self.get_list_link_mk()
            #разложить их на сумму по этапам норма и освоено
        #dict_professions(self,self.db_users)
        if len(list_mk) == 0:
            return f'Не найдено ни одной МК для  позиции {self.Пномер}, МК возможно завершена, тогда нужно сменить статус позиции'
        #dict_opers(pself,self.db_naryad)

        dict_vid_rab = {DICT_PROFESSIONS[_]['nick_name']:{'Норма_н_см':0,'Заверш_н_см':0,'sort':DICT_PROFESSIONS[_]['sort']} for _ in  DICT_PROFESSIONS.keys()}
        dict_vid_rab = dict(sorted(dict_vid_rab.items(), key=lambda item: item[1]['sort']))
        for key in dict_vid_rab.keys():
            dict_vid_rab[key].pop('sort')
        print(f"Пномер|Наименование|Опер_номер"
              f"Опер_наименование|vid_rab_nick|add_all_time|add_zav_time|count_dse|zaversh")
        for item in list_mk:
            mk = Marshrut_cards(item,self.db_naryad,self.db_resxml)
            for dse in mk.res:
                count_dse = dse['Количество']

                for oper in dse['Операции']:
                    if oper['Опер_профессия_код'] not in DICT_PROFESSIONS:
                        print(f"{oper['Опер_профессия_код']} not in DICT_PROFESSIONS")
                        continue

                    vid_rab_nick = DICT_PROFESSIONS[oper['Опер_профессия_код']]['nick_name']
                    kr = 1
                    if oper['Опер_наименование'] in DICT_OP_NAME:
                        kr = DICT_OP_NAME[oper['Опер_наименование']]['kr_default']
                    koef_posta = 1
                    if kr == 2:
                        koef_posta = 1 / 0.7

                    koef_vneplana_tmp = 1

                    if DICT_PROFESSIONS[oper['Опер_профессия_код']]['name'] in ('пл_сб.Нчас_слсб', 'пл_сб.Нчас_св', 'пл_сб.Нчас_зач'):
                        koef_vneplana_tmp = koef_vneplana

                    zaversh = 0
                    if 'Закрыто,шт.' in oper:
                        zaversh = oper['Закрыто,шт.']

                    add_time = ((oper['Опер_Тпз'] + oper['Опер_Тшт'] * koef_posta) * koef_vneplana_tmp * koef_pogr_norm)
                    dict_vid_rab[vid_rab_nick]['Норма_н_см'] += add_time
                    #print(f'{mk.Пномер}|{dse['Наименование']}{dse['Номенклатурный_номер']}|{oper['Опер_номер']} '
                    #      f'{oper['Опер_наименование']}|{vid_rab_nick}|{round(add_time,2)}|{dict_vid_rab[vid_rab_nick]['Норма_н_см']}')
                    add_zav_time = 0
                    if zaversh > 0 and count_dse > 0:
                        add_zav_time= (oper['Опер_Тпз'] + oper['Опер_Тшт_ед']) * zaversh
                        dict_vid_rab[vid_rab_nick]['Заверш_н_см'] += add_zav_time
                    print(f"{mk.Пномер}|{dse['Наименование']}{dse['Номенклатурный_номер']}|{oper['Опер_номер']} "
                              f"{oper['Опер_наименование']}|{vid_rab_nick}|{add_time}|{round(add_zav_time, 2)}|{count_dse}|{zaversh}")
        count_izd = self.dict_tables['пл_оуп']['Количество']
        for item in dict_vid_rab.keys():
            dict_vid_rab[item]['Остаток_н_см'] = round( dict_vid_rab[item]['Норма_н_см'] - dict_vid_rab[item]['Заверш_н_см'],2)
            if dict_vid_rab[item]['Остаток_н_см'] < 0:
                dict_vid_rab[item]['Остаток_н_см'] = 0

            dict_vid_rab[item]['Остаток_шт'] = 0

            if dict_vid_rab[item]['Норма_н_см'] > 0:
                dict_vid_rab[item]['Остаток_шт'] = round(count_izd - dict_vid_rab[item]['Заверш_н_см'] / dict_vid_rab[item][
                    'Норма_н_см'] * count_izd,2)
                if dict_vid_rab[item]['Остаток_шт'] < 0:
                    dict_vid_rab[item]['Остаток_шт'] = 0
                dict_vid_rab[item]['Норма_н_см'] = round(dict_vid_rab[item]['Норма_н_см'], 2)

            dict_vid_rab[item]['Заверш_н_см']  = round(dict_vid_rab[item]['Заверш_н_см']/480,2)
            dict_vid_rab[item]['Остаток_н_см'] = round(dict_vid_rab[item]['Остаток_н_см'] / 480, 2)
            dict_vid_rab[item]['Норма_н_см'] = round(dict_vid_rab[item]['Норма_н_см'] / 480, 2)

        self.dict_vid_rab = dict_vid_rab
        self.dict_vid_rab_tmp = copy.deepcopy(dict_vid_rab)

    def check_date_res(self,selection_res:Materials_erp_arm):
        list_res = CSQ.custom_request_c(self.db,f"""SELECT  
            s_num, 
            active, 
            file_name, 
            num_kpl, 
            date_version, 
            user, 
            primech, 
            ИдентификаторВерсииРесурсной FROM versions_res_mat WHERE num_kpl = {self.Пномер}""",rez_dict=True)
        set_dates = F.sort_by_column_c(list(set([(_['date_version']) for _ in list_res])),0,False,True,hat_c=False)
        if F.strtodate(selection_res.date_ver) < F.strtodate(set_dates[0]):
            CQT.msgbox(f'Дата выбранной ресурсной не является самой последней')
            return False
        return True


    def check_summ_orders_mat(self,s_num_new_res):
        list_docs = CSQ.custom_request_c(self.db,f"""SELECT * from orders_res_mat WHERE pozition == {self.Пномер} and state = 2""",rez_dict=True)
        dict_docs = dict()
        for doc in list_docs:
            data = F.from_binary_pickle(F.unpack_byte_file(doc['data']))
            for etap in data.keys():
                if etap not in dict_docs:
                    dict_docs[etap] = dict()
                for kod in data[etap].keys():
                    if kod not in dict_docs[etap]:
                        dict_docs[etap][kod] = {'Количество':0}

                    dict_docs[etap][kod]['Количество']+=data[etap][kod]

        active_res = CSQ.custom_request_c(self.db,f"""SELECT * FROM versions_res_mat WHERE s_num = {s_num_new_res}""",one=True,rez_dict=True)
        data = F.from_binary_pickle(F.unpack_byte_file(active_res['data']))
        list_errors = []
        if set(dict_docs.keys()) != set(data.keys()):
            list_errors.append(f'Не соответствует Этапы  : {dict_docs.keys()} и {data.keys()}')
            CQT.msgbox(pprint.pformat(list_errors))
            return False
        for etap in dict_docs.keys():
            if set(dict_docs[etap].keys()) != set(data[etap].keys()):
                list_errors.append(f'Не соответствует в {etap} Коды  : {dict_docs[etap].keys()} и {data[etap].keys()} ')
                CQT.msgbox(pprint.pformat(list_errors))
                return False

            for key in dict_docs[etap].keys():
                if round(dict_docs[etap][key]['Количество'], 8)  != round(data[etap][key]['Количество'], 8):
                    list_errors.append(f'Не соответствует в {etap}  {key}  : {dict_docs[etap][key]} и {data[etap][key]} ')


        if len(list_errors)>0:
            CQT.msgbox('Выбранная ресурсная не соответсвует сумме материалов по проведенным заявкам:\n\n' + pprint.pformat(list_errors))
            return False
        return True

    def set_new_active_res(self,new_ver_res:int):
        CSQ.custom_request_c(self.db,f"""UPDATE пл_топ SET ВерсияРесурсной = {new_ver_res} WHERE НомПл = {self.Пномер}""")

    def set_new_type_by_direction(self, new_type: int): #21.07.25
        CSQ.custom_request_c(self.db,f"""
            UPDATE пл_топ 
            SET Вид = {new_type} 
            WHERE НомПл = {self.Пномер}
            RETURNING *
        """, rez_dict=True)
        self.load_kpl_table('пл_топ')

    def get_unicue_fild_name(self,name_table):
        if name_table == 'plan':
            return 'Пномер'
        else:
            return 'НомПл'

    def update_znpr(self):
        
        fl = False
        if 'пл_оуп' not in self.dict_tables:
            return fl
        
        dict_for_update:dict = self.dict_tables['пл_оуп']
        DICT_FIELDS_SHABL = CSQ.dict_types_tbl(self.db,'знпр')
        data_znpr:dict = CSQ.custom_request_c(self.db,f"""SELECT * FROM знпр WHERE s_num == {dict_for_update['s_num']};""",rez_dict=True,one=True)
        list_fields = []
        list_vals = []
        for field, type_val in DICT_FIELDS_SHABL.items():
            if field in dict_for_update:
                if type(dict_for_update[field]) == type(data_znpr[field]):
                    if dict_for_update[field] != data_znpr[field]:
                        list_fields.append(field)
                        list_vals.append(dict_for_update[field])
                else:
                    raise TypeError(f'update_znpr: field {field} type not match')
        if list_fields:
            
            str_fields = ', '.join(list_fields)
            
            fl = CSQ.custom_request_c(self.db,
                                 f"""UPDATE знпр SET ({str_fields}) =
                                  ({CSQ.questions_for_mask(list_fields)}) 
                                  WHERE s_num == {dict_for_update['s_num']}""",list_of_lists_c=[list_vals])
        return fl
            
    def update_row_etaps(self,new_row_dates_etap:dict):
        list_name_fields = []
        list_dates = []
        dict_for_update = dict()
        for k,v in new_row_dates_etap.items():
            if k in self.row_time_etap:
                if v != self.row_time_etap[k]:
                    name_tbl, field = k.split(".")
                    if name_tbl not in dict_for_update:
                        dict_for_update[name_tbl] = [[],[]]
                    dict_for_update[name_tbl][0].append(field)
                    dict_for_update[name_tbl][1].append(str(v))
            if k in self.row_time_add_etap:
                if v != self.row_time_add_etap[k]:
                    name_tbl, field = k.split(".")
                    if name_tbl not in dict_for_update:
                        dict_for_update[name_tbl] = [[],[]]
                    dict_for_update[name_tbl][0].append(field)
                    dict_for_update[name_tbl][1].append(str(v))
            if k in self.row_dates_etap_fact:
                if v != self.row_dates_etap_fact[k]:
                    name_tbl, field = k.split(".")
                    if name_tbl not in dict_for_update:
                        dict_for_update[name_tbl] = [[],[]]
                    dict_for_update[name_tbl][0].append(field)
                    dict_for_update[name_tbl][1].append(f'"{v}"')
            if k in self.row_dates_etap_plan:
                if v != self.row_dates_etap_plan[k]:
                    name_tbl, field = k.split(".")
                    if name_tbl not in dict_for_update:
                        dict_for_update[name_tbl] = [[],[]]
                    dict_for_update[name_tbl][0].append(field)
                    dict_for_update[name_tbl][1].append(f'"{v}"')
            if k in self.row_dates_supply:
                if v != self.row_dates_supply[k]:
                    name_tbl, field = k.split(".")
                    if name_tbl not in dict_for_update:
                        dict_for_update[name_tbl] = [[],[]]
                    dict_for_update[name_tbl][0].append(field)
                    dict_for_update[name_tbl][1].append(f'"{v}"')
        fl = False
        for tbl in dict_for_update.keys():
            if len(dict_for_update[tbl]):
                fl = True
                str_fields = ', '.join(dict_for_update[tbl][0])
                str_vals = ', '.join(dict_for_update[tbl][1])
                unicue_field = self.get_unicue_fild_name(tbl)
                CSQ.custom_request_c(self.db,f"""UPDATE {tbl} SET ({str_fields}) = ({str_vals}) WHERE {unicue_field} = {self.Пномер}""")
        if fl:
            return dict_for_update
        return fl

    def get_state_poz_name(self):
        rez =  CSQ.custom_request_c(self.db,f"""SELECT Имя from status_poz WHERE Пномер = {self.Статус}""",one_column=True,one=True,hat_c=False)
        if rez == None or rez == False:
            return rez
        return rez #11.11.25

    def update_day_plan_etap_jurnal(self, data:dict, clear_upd = False):
        if clear_upd: #18.09.2025 от Моренко
            old_dict = None #self.get_day_plan_etap_jurnal() 02.09.2025 от Моренко
        else:
            old_dict = self.get_day_plan_etap_jurnal()
        if old_dict == None or old_dict == False:
            old_dict = data
        else:
            for k,v in data.items():
                old_dict[k] = v

        blob= F.to_binary_pickle(old_dict)
        CSQ.custom_request_c(self.db,f"""UPDATE plan SET fact_jurnal_blolb_data = ? 
         WHERE Пномер == ?""",list_of_lists_c=[[blob,self.Пномер]])

    def get_day_plan_etap_jurnal(self):
        if self.fact_jurnal_blolb_data == None:
            data = CSQ.custom_request_c(self.db,f"""SELECT fact_jurnal_blolb_data FROM 
             plan WHERE Пномер == ?""",list_of_lists_c=[self.Пномер],one=True,one_column=True,hat_c=False)
            if data == None or data == False:
                return False
            self.fact_jurnal_blolb_data = data #11.11.25
        if self.fact_jurnal_blolb_data == None or self.fact_jurnal_blolb_data== '':
            return defaultdict(defaultdict)
        else:
            return F.from_binary_pickle(self.fact_jurnal_blolb_data)


    def recalc_get_day_plan_as_fact(self, pl_name,f_name):
        dict_days = self.get_day_plan_etap_jurnal()
        if f_name not in dict_days:
            return False
        name_time_etap = pl_name.replace('план_','')
        if name_time_etap not in self.parent_self.Data_plan.DICT_PODR:
            return False
        name_field_time = name_time_etap + '.' + self.parent_self.Data_plan.DICT_PODR[name_time_etap]['Имя_поля'].split(';')[0]
        name_field_end = name_time_etap + '.' + self.parent_self.Data_plan.DICT_PODR[name_time_etap]['Имя_конца_этапа'].split(';')[0]
        name_field_start = name_time_etap + '.' + self.parent_self.Data_plan.DICT_PODR[name_time_etap]['Имя_начала_этапа'].split(';')[0]
        name_field_end_fact = name_time_etap + '.' + \
                           self.parent_self.Data_plan.DICT_PODR[name_time_etap]['Имя_конца_этапа_факт'].split(';')[0]
        dict_days[pl_name] = dict()
        dict_days_tmp = copy.deepcopy(dict_days)
        summ_fact = sum(dict_days[f_name].values())
        le_date_or_num :QtWidgets.QLineEdit = self.parent_self.ui.le_plan_day_edit_recalc_hour_per_day
        date_or_num = le_date_or_num.text().strip().replace('\t','').replace('\n','')
        set_masks_date = {"%d.%m.%Y","%d.%m.%y","%Y-%m-%d","%y-%m-%d",}
        if self.row_dates_etap_plan[name_field_start] == '':
            CQT.msgbox(f'Пдата начала {name_field_start} не указана')
            return
        pull_time = copy.deepcopy(self.row_time_etap[name_field_time]) * 60
        if not F.is_numeric(date_or_num):
            date_target = None
            for mask in set_masks_date:
                if F.is_date(date_or_num,mask):
                    date_target_data  = F.strtodate(date_or_num,mask)
                    if date_target_data < F.strtodate(self.row_dates_etap_plan[name_field_start]):
                        CQT.msgbox(f'Целевая дата не может быть меньше чем Пдата начала')
                        return
                    if date_target_data < F.now(''):
                        CQT.msgbox(f'Целевая дата не может быть меньше чем сегодня')
                        return
                    date_target = F.datetostr(date_target_data,"%d\n%m\n%y")
                    break
            if date_target == None:
                CQT.blink_obj_c(self.parent_self,1,le_date_or_num,'Не число и не дата')
                return False



            remains_time = pull_time - summ_fact

            if len(dict_days[f_name]) >0:
                last_date_fact =F.datetostr(max([F.strtodate(_,"%d\n%m\n%y") for _ in dict_days[f_name].keys()]),"%d\n%m\n%y")
            else:
                last_date_fact = F.datetostr(F.strtodate(self.row_dates_etap_fact[name_field_end_fact]), "%d\n%m\n%y")
            count_days_before = 0
            fl_find_day_last = False
            cld = copy.deepcopy(self.parent_self.Data_plan.DICT_CLD)
            for day, vals in cld.items():
                day_gui = F.datetostr(day, "%d\n%m\n%y")

                if fl_find_day_last and vals['Выходные'] == 0 and day > F.now(''):
                    count_days_before +=1
                if fl_find_day_last == False and  day_gui == last_date_fact:
                    fl_find_day_last = True
                if date_target == day_gui:
                    break
            if count_days_before == 0:
                date_target_str = F.datetostr(F.strtodate( date_target,"%d\n%m\n%y"),"%d.%m.%Y")
                CQT.msgbox(f'Не удалось посчитать дни  до {date_target_str}')
                return
            date_or_num = round(remains_time/count_days_before/60,3)
            pull_time = date_or_num * 60 * count_days_before + summ_fact



        average = F.valm(date_or_num)*60
        if average < 1:
            CQT.blink_obj_c(self.parent_self, 1, le_date_or_num, 'Не может быть меньше 0.0167')
            return False

        #if len(dict_days[f_name]) > 0:
        #    average = summ_fact / len(dict_days[f_name])
        #delta = summ_fact - self.row_time_etap[name_field_time]

        summ_plan = 0
        cld = copy.deepcopy(self.parent_self.Data_plan.DICT_CLD)

        new_last_date = self.row_dates_etap_plan[name_field_end]
        new_first_date = ''

        for day, vals in cld.items():
            day_gui = F.datetostr(day,"%d\n%m\n%y")
            plan = 0
            if pull_time == 0:
                break
            if len(dict_days_tmp[f_name]) == 0:
                if vals['Выходные'] == 0 and day >= F.strtodate(self.row_dates_etap_plan[name_field_start]) and day > F.now(''):
                    plan = average
            else:
                if day_gui in dict_days_tmp[f_name]:
                    plan = dict_days_tmp[f_name][day_gui]
                    dict_days_tmp[f_name].pop(day_gui)
            if plan <= 0.02:
                continue

            if round(pull_time - plan,2) <= 0:
                plan = pull_time
            pull_time -= plan
            cld[day]['план'] = plan
            cld[day]['day_gui'] = day_gui


        for day, vals in cld.items():
            if 'day_gui' in vals:
                dict_days[pl_name][vals['day_gui']] = round(vals['план'],2)
                new_last_date = F.datetostr(day, "%Y-%m-%d")
                if new_first_date == '':
                    new_first_date = F.datetostr(day, "%Y-%m-%d")

        fl = False
        new_tbl = copy.deepcopy(self.row_dates_etap_plan)
        if new_last_date != self.row_dates_etap_plan[name_field_end]:
            new_tbl[name_field_end] = new_last_date
            fl=True
        if new_first_date != self.row_dates_etap_plan[name_field_start]:
            new_tbl[name_field_start] = new_first_date
            fl = True
        if fl:
            self.update_row_etaps(new_tbl)
        self.update_day_plan_etap_jurnal(dict_days,clear_upd=True)
        return dict_days

class Techkards():
    UNRECALC_MARK = '='
    db_dse = None
    def __init__(self,nn_or_snum:str|int,db_dse:str, nom_mk:int = '',path_docs='',
                 db_nomen='', # не используется
                 fix_mat=False,
            DICT_OP_NAME: dict = None,
            DICT_PROFESSIONS: dict = None #31.07.25
        ):
        poki = CFG.Config.place.poki
        self.DICT_OP_NAME = self.DICT_KOD_OPER = None
        if DICT_OP_NAME is None:
            print(f'class Techkards: DICT_OP_NAME = None')
            config = CFG.Config.project #10.04.25
            list_operations = CSQ.custom_request_c(config.db_naryad, f"""SELECT * FROM operacii WHERE poki == {poki}""",rez_dict=True)
            DICT_OP_NAME = F.deploy_dict_c(list_operations,'name')
        self.DICT_KOD_OPER = {oper_name: creds['kod'] for oper_name, creds in DICT_OP_NAME.items()} #20.11.25
        self.fix_mat = fix_mat
        self.fl_fix = False

        self.DICT_PROFESSIONS = DICT_PROFESSIONS
        if DICT_PROFESSIONS is None:
            print(f'class Techkards: DICT_PROFESSIONS = None')
            dict_professions(self, db_users=CFG.Config.project.db_users)

        Techkards.db_dse = db_dse
        fl_fix = False
        if isinstance(nn_or_snum, str):
            self.dse = CSQ.custom_request_c(db_dse,f"""SELECT * FROM dse WHERE Номенклатурный_номер = "{nn_or_snum}" and poki = {poki};""",rez_dict=True) #07.04.25
        elif isinstance(nn_or_snum, int):
            self.dse = CSQ.custom_request_c(db_dse, f"""SELECT * FROM dse WHERE Пномер = {nn_or_snum};""",
                                            rez_dict=True)
        else:
            raise ValueError

        if self.dse == None or self.dse == False or self.dse == []:
            print(f'Не найдена {nn_or_snum} в БД')
            return None
        self.dse = self.dse[0]
        nn = self.dse['Номенклатурный_номер']
        self.tk = None
        if nom_mk == '':
            if path_docs == "":
                path_docs = F.scfg('add_docs')
            putf = path_docs + os.sep + self.dse['Номер_техкарты'] + "_" + nn + '.pickle'
        else:
            if path_docs == "":
                path_docs = CFG.Config.project.mk_temp_folder #31.07.25
            putf = path_docs + os.sep + nom_mk + os.sep + self.dse['Номер_техкарты'] + '_' + nn + '.pickle'
        self.putf = putf
        self.nom_mk = nom_mk
        self.path_docs = path_docs
        self.xl_formulas = CXLF.XlFormula()
        if not F.existence_file_c(putf):
            print(f'Не найден файл {putf}')
            return
        sp_tk = F.open_file_c(putf, False, "|", pickl=True)
        bodys = []

        for i in range(10,len(sp_tk)):
            if int(sp_tk[i][20]) == 0:
                opers = []
                for j in range(i+1,len(sp_tk)):
                    if int(sp_tk[j][20]) < 1:
                        break
                    if int(sp_tk[j][20]) == 1:
                        if sp_tk[j][0] not in DICT_OP_NAME:
                            CQT.msgbox(
                                f"{nn} Операция ``{sp_tk[j][0]}`` не найдена в БД для {CFG.Config.user_config.Organization['Значение']}")
                            return
                        mats = self.unpack_materials(sp_tk[j][10].split("{"))
                        # for _ in sp_tk[j][10].split("{"):
                        #     if _ == '':
                        #         break
                        #     if len(_.split("$")) == 3:
                        #         ed_izm = ''
                        #         if db_nomen == '':
                        #             print(f'error load edizm, need db_nomen')
                        #             return None
                        #         dict_ed_izm = CSQ.custom_request_c(db_nomen,f"""SELECT * FROM nomen WHERE Код = "{_.split("$")[0]}"; """,rez_dict=True)
                        #         if len(dict_ed_izm) >0:
                        #             ed_izm = dict_ed_izm[0]['ЕдиницаИзмерения']
                        #         mats.append( {"cod":_.split("$")[0],"naimen":_.split("$")[1],"ed_izm":ed_izm,"norma":F.valm(_.split("$")[2])} )
                        #         if self.fix_mat:
                        #             self.fl_fix=True
                        #
                        #     else:
                        #         try:
                        #             mats.append( {"cod":_.split("$")[0],"naimen":_.split("$")[1],"ed_izm":_.split("$")[2],"norma":F.valm(_.split("$")[3])} )
                        #         except:
                        #             print(f'error load mats')

                        perehs = []
                        for k in range(j + 1, len(sp_tk)):
                            if int(sp_tk[k][20]) < 2:
                                break
                            if int(sp_tk[k][20]) == 2:
                                if sp_tk[j][16] == '':
                                    params_dict = dict()
                                else:
                                    params_dict = eval(sp_tk[j][16])
                                pereh = {"name_ver": sp_tk[k][0],
                                'doc_mark': sp_tk[k][1],
                                'doc_card': sp_tk[k][13].split("$"),
                                #'doc': sp_tk[k][15],
                                's_name': sp_tk[k][2],
                                's_name_full': sp_tk[k][3],
                                #'rab_centr': sp_tk[k][4],


                                't_sht': F.valm(sp_tk[k][7]),
                                 'params': sp_tk[k][14].split("$"),
                                'prisposobs': sp_tk[k][11].split("$"),
                                'instrums': sp_tk[k][12].split("$"),
                                'params_dict': params_dict,
                                'lvl': int(sp_tk[k][20]),


                                }
                                perehs.append(pereh)

                        if sp_tk[j][16] == '':
                            params_dict = dict()
                        else:
                            params_dict = eval(sp_tk[j][16])
                        if self.check_val_on_unrecalcitrant_mark(sp_tk[j][7]):
                            t_sht = sp_tk[j][7]
                        else:
                            t_sht = F.valm(sp_tk[j][7])
                        if self.check_val_on_unrecalcitrant_mark(sp_tk[j][6]):
                            t_pz = sp_tk[j][6]
                        else:
                            t_pz = F.valm(sp_tk[j][6])

                        if sp_tk[j][8] not in self.DICT_PROFESSIONS:
                            CQT.msgbox(f'Некорректный код профессии необходимо править техкарту: {nn}')
                            return
                        oper = {"cod": DICT_OP_NAME[sp_tk[j][0]]['kod'],
                                "name_ver": sp_tk[j][0],
                                'doc_mark': sp_tk[j][1],
                                'doc_card': sp_tk[j][13].split("$"),
                                'doc': sp_tk[j][15],
                                's_name': sp_tk[j][2],
                                's_name_full': sp_tk[j][3],
                                'rab_centr': sp_tk[j][4],
                                'oborudovanie': sp_tk[j][5],
                                't_pz': t_pz,
                                't_sht': t_sht,
                                'profession': sp_tk[j][8],
                                'kr': F.valm(sp_tk[j][9]),
                                'materials': mats,
                                'koid': F.valm(sp_tk[j][11]),
                                'params': sp_tk[j][14].split("$"),
                                'params_dict': params_dict,
                                'lvl': int(sp_tk[j][20]),
                                'perehs': perehs
                                }

                        opers.append(oper)

                tk = {"name_ver": sp_tk[i][0],
                          'doc_mark': sp_tk[i][1],
                          'doc_card': sp_tk[i][13].split("$"),
                          'doc': sp_tk[i][15],
                          's_name': sp_tk[i][2],
                          's_name_full': sp_tk[i][3],

                          'date': sp_tk[i][5],
                          'razrabotal': sp_tk[i][6],
                          'primech': sp_tk[i][7],
                          'params': sp_tk[i][14],
                          'lvl': int(sp_tk[i][20]),
                          'opers': opers
                          }
                bodys.append(tk)
        self.tk = {'hat': {'dse_name':sp_tk[0][0],
                           'tk_name':sp_tk[1][0],
                            'litera':sp_tk[2][0],
                           'razrabotal_name':sp_tk[3][0],
                           'razrabotal_date': sp_tk[4][0],
                           'proveril_name': sp_tk[5][0],
                           'normiroval_name': sp_tk[6][0],
                           'metrolog_exsp_name': sp_tk[7][0],
                           'normokontrol': sp_tk[8][0],
                           'primechanie': sp_tk[9][0],

                           },
                   'bodys':bodys}
        self.sp_tk = sp_tk
        if self.fix_mat and self.fl_fix:
            self.save_tk()

    def check_tk(self) -> str | None: #03.09.25
        """
        Проверка техкарты на доступность атрибутов для последующего парсинга
        """
        nn = self.dse["Номенклатурный_номер"]
        if self.tk is None:
            return f'Не найдена {nn!r}'
        if isinstance(self.tk, dict) and not self.tk.get('bodys'):
            return f'Техкарта {nn!r} не содержит операций'

    def recalc_materials(self, strict: bool = False) -> list[str]: #24.11.25
        """
        Пересчет норм материалов на операцию заложенных в db_nomenclature.complex_filtr
        @strict показывать все ошибки (для дебага)
        """
        messages = []
        nn = self.dse["Номенклатурный_номер"]
        if error := self.check_tk():
            return [error]
        for i, tk in enumerate(self.tk['bodys']):
            for j, oper in enumerate(tk['opers']):
                oper_name = oper["name_ver"]
                params = prepareed_params = oper['params_dict']
                if isinstance(params, dict):
                    prepareed_params = F.list_of_dicts_to_list_of_lists([params])
                if not isinstance(prepareed_params, list):
                    oper_name = oper["name_ver"]
                    print(f'ДСЕ: {nn} Строка: {i} Операции: {oper_name!r} некорректный тип параметров')
                    messages.append(f'ДСЕ: {nn} Строка: {i} Операции: {oper_name!r} некорректный тип параметров')
                    continue
                try:
                    recalced_mats_str = operacii.materiali(self, oper['name_ver'], prepareed_params)
                    if recalced_mats_str is None: # Операция не найдена в функции materiali
                        continue
                except Exception as e:
                    msg = f"Ошибка при расчёте материалов к операции: {oper_name} дсе: {nn}'"
                    print(f'[Techkards.recalced_mats] {msg}')
                    if strict:
                        messages.append(msg)
                    continue
                oper['materials'] = self.unpack_materials(recalced_mats_str.split('{'))
                recalced_mats = self.unpack_materials(recalced_mats_str.split('{'))#21.11.25
                if recalced_mats:
                    oper['materials'] = recalced_mats
                # for new_mat in recalced_mats:
                #     replace_idx = None
                #     for idx, old_mat in enumerate(orig_mats):
                #         if new_mat['cod'] == old_mat['cod']:
                #             replace_idx = idx
                #             break
                #     if replace_idx is not None:
                #         orig_mats[replace_idx] = new_mat.copy()
                #     else:
                #         orig_mats.append(new_mat)
                # oper['materials'] = orig_mats
        return messages

    def unpack_materials(self, splited_row: list[str]):
        db_nomen = CFG.Config.project.db_nomen
        mats = []
        for _ in splited_row:
            if _ == '':
                break
            if len(_.split("$")) == 3:
                ed_izm = ''
                dict_ed_izm = CSQ.custom_request_c(db_nomen,
                                                   f"""SELECT * FROM nomen WHERE Код = "{_.split("$")[0]}"; """,
                                                   rez_dict=True)
                if len(dict_ed_izm) > 0:
                    ed_izm = dict_ed_izm[0]['ЕдиницаИзмерения']
                mats.append({"cod": _.split("$")[0], "naimen": _.split("$")[1], "ed_izm": ed_izm,
                             "norma": F.valm(_.split("$")[2])})
                if self.fix_mat:
                    self.fl_fix = True

            else:
                try:
                    mats.append({"cod": _.split("$")[0], "naimen": _.split("$")[1], "ed_izm": _.split("$")[2],
                                 "norma": F.valm(_.split("$")[3])})
                except:
                    print(f'error load mats')
        return mats

    def check_code_profession(self, code: str): #10.04.25
        config = CFG.Config
        query = f"SELECT COUNT(*) as Количество FROM professions WHERE код = {code!r} AND poki = {config.place.poki}"
        response = CSQ.custom_request_c(
            config.project.db_users,
            query,
            rez_dict=True,
            one=True
        )
        return isinstance(response, dict) and response.get('Количество') >= 1

    def _spis_parametrov_na_perehod(self, oper: str, spis_op: list):
        rez = []
        for i in range(len(spis_op)):
            if spis_op[i][0] == oper and len(spis_op[i]) > 2:
                spis_per = spis_op[i][2].split(';')
                for j in range(len(spis_per)):
                    rez.append(spis_per[j])
                break
        return rez

    def recalc_opers(self,list_opers_name=[],DICT_OPERS=None):
        list_errors = []
        list_edit = []
        if list_opers_name == []:
            list_opers_name = list(DICT_OPERS.keys())
        dict_tpz = {k:DICT_OPERS[k]['Tpz'] for k in DICT_OPERS.keys()}
        for oper_recalc in list_opers_name:
            for i,tk in enumerate(self.tk['bodys']):
                for j,oper in enumerate(tk['opers']):
                    if oper['name_ver'] not in list_opers_name:  # 09.06.2025 (по задаче 100055272 )
                        self.tk['bodys'][i]['opers'][j]['t_sht'] = self.clean_unrecalc_mark(oper['t_sht'])
                        self.tk['bodys'][i]['opers'][j]['t_pz'] = self.clean_unrecalc_mark(oper['t_pz'])
                    if oper['name_ver'] == oper_recalc:
                        if self.check_val_on_unrecalcitrant_mark(oper['t_sht']):
                            self.tk['bodys'][i]['opers'][j]['t_sht'] = self.clean_unrecalc_mark(oper['t_sht'])
                            self.tk['bodys'][i]['opers'][j]['t_pz'] = self.clean_unrecalc_mark(oper['t_pz'])
                            continue
                        time_pereh_summ = 0
                        time_oper_pz = dict_tpz[oper['name_ver']]
                        for k, pereh in enumerate(oper['perehs']):
                            tsht_pereh = 0
                            try:
                                tsht_pereh = operacii.vremya_tsht_perehodi(oper['name_ver'],pereh['name_ver'],
                                                          pereh['params_dict'],oper['params_dict'])
                                if tsht_pereh is None: #07.04.25
                                    tsht_pereh = F.valm(pereh['t_sht'])
                                    list_edit.append(f'Переход: {pereh["name_ver"]} не был пересчитан из-за отсутствия формулы(Выставлено время из техкарты)({tsht_pereh})')
                            except Exception as e:
                                list_errors.append(
                                    f"{self.dse['Номенклатурный_номер']} ошибка расчета перехода: {oper['name_ver']!r}.{pereh['name_ver']!r} {oper['params']}")

                            time_pereh_summ+= tsht_pereh
                            if tsht_pereh == 0:
                                self.tk['bodys'][i]['opers'][j]['perehs'][k]['t_sht'] = ''
                        try:
                            time_oper = operacii.vremya_tsht(oper['name_ver'],oper['params_dict'])
                            if time_oper is None: #07.04.25
                                time_oper = F.valm(oper['t_sht'])
                                list_edit.append(
                                    f'Операция: {oper["name_ver"]} не была пересчитана из-за отсутствия формулы(Выставлено время из техкарты)({time_oper})')
                        except Exception as e:
                            list_errors.append(f"{self.dse['Номенклатурный_номер']} ошибка расчета {oper['s_name']} {oper['name_ver']} {oper['params']}")
                            continue
                        if time_oper == None:
                            list_errors.append(f"{self.dse['Номенклатурный_номер']} пустые параметры в операции {oper['s_name']} {oper['name_ver']} {oper['params']}")
                            continue
                        if type(time_oper) == tuple:
                            time_oper, time_oper_pz = time_oper
                        if time_oper == 0:
                            stalo_tsht = time_pereh_summ
                        else:
                            stalo_tsht = time_oper
                        if stalo_tsht == 0 and self.xl_formulas.check_strict_calc(operation=oper['name_ver']): #15.04.25
                            list_errors.append(
                                'Операция с обязательным пересчетом "[{s_num}]{oper}" вернула 0 тшт'.format(
                                    oper=oper['name_ver'],
                                    s_num=oper['s_name']
                                ))
                        if stalo_tsht != self.tk['bodys'][i]['opers'][j]['t_sht']:
                            msg =  (f"{oper['name_ver']}: Тшт= было {self.tk['bodys'][i]['opers'][j]['t_sht']}  / стало {stalo_tsht}")
                            print(msg)
                            list_edit.append(msg)
                        if time_oper_pz != self.tk['bodys'][i]['opers'][j]['t_pz']:
                            msg = ( f"{oper['name_ver']}: Тшт= было {self.tk['bodys'][i]['opers'][j]['t_pz']}   / стало {time_oper_pz}")
                            print(msg )
                            list_edit.append(msg)
                        self.tk['bodys'][i]['opers'][j]['t_sht'] = F.valm(stalo_tsht) # 03.04.25
                        self.tk['bodys'][i]['opers'][j]['t_pz'] = F.valm(time_oper_pz)

            if len(list_errors) >0:
                return list_errors, list_edit
        return None, list_edit

    def check_val_on_unrecalcitrant_mark(self, val):
        return str(val).startswith(self.UNRECALC_MARK)

    def clean_unrecalc_mark(self, val):
        cleaned_value = str(val).lstrip(self.UNRECALC_MARK)
        if not F.is_numeric(cleaned_value):
            return 0
        return float(str(val).lstrip(self.UNRECALC_MARK))

    def get_oper(self,nom_oper:str):
        if not self.tk['bodys'] or not self.tk['bodys'][0]: #30.07.25
            return None
        for oper in self.tk['bodys'][0]['opers']:
            if oper['s_name'] == nom_oper:
                return oper

    def get_attached_operation_files(self, num_oper: str, allowed_ext: list[str] = None):
        oper = self.get_oper(num_oper)
        tk_name = self.dse['Номер_техкарты']
        if not isinstance(oper['doc'], str) or not oper['doc'].strip():
            return []
        reestr_files = CSQ.custom_request_c(CFG.Config.project.db_files, f"""
            SELECT t_kards.file_name
            FROM t_kards
            LEFT JOIN names ON t_kards.file_name = names.name
            WHERE t_kards.t_kard_name = {tk_name!r}""", one_column=True, hat_c=False)
        filenames = []
        for filename in oper['doc'].split('%20'):
            if not filename.strip() or filename not in reestr_files:
                continue
            name, ext = os.path.splitext(filename)
            if allowed_ext and ext not in allowed_ext:
                continue
            filenames.append(filename)
        return filenames

    def _update_params_oper(self,DICT_OPERS):
        def fix_sv(params,params_db):
            if len(params_db) == len(params) +1:
                params.append('1')
            return params
        for tk in self.tk['bodys']:
            for oper in tk['opers']:
                mark_ignore_params = self.check_val_on_unrecalcitrant_mark(oper['t_sht']) or self.check_val_on_unrecalcitrant_mark(oper['t_pz'])
                if mark_ignore_params:
                    continue
                params_db = []
                if self.xl_formulas.check_op(oper['name_ver'], True):
                    params_db = []
                    for key in self.xl_formulas.get_op_params(oper['name_ver']):
                        params_db.append(key)
                elif oper['name_ver'] in operacii.Data_oper_norm.DICT_OPERS_CALC:
                    params_db = []
                    if CFG.Config.place.poki == 0:
                        for key in operacii.Data_oper_norm.DICT_OPERS_CALC[oper['name_ver']].keys():
                            params_db.append(key)
                    if oper['name_ver'] == 'Сварка':
                        oper['params']= fix_sv(oper['params'],params_db)
                else:
                    if oper['name_ver'] in DICT_OPERS:
                        if DICT_OPERS[oper['name_ver']]['Vars']:
                            params_db = [_.split(':')[0] for _ in DICT_OPERS[oper['name_ver']]['Vars'].split(';')]
                if len(params_db)>0:
                    if len(params_db) == len(oper['params']):
                        oper['params_dict'] =  F.list_of_lists_to_list_of_dicts([params_db,
                                                                                 oper['params']])[0]
                    else:
                        oper['t_sht'] = 0
                        oper['t_pz'] = 0
                        oper['params'] = []
                        oper['params_dict'] = dict()

                for pereh in oper['perehs']:
                    pereh_path = self.xl_formulas.get_pereh_txt_path(oper_name=oper['name_ver']) # Путь к txt с учетом poki
                    # if F.existence_file_c(F.scfg('cash') + os.sep + oper['name_ver'] + ".txt"):
                    if F.existence_file_c(pereh_path):
                        spis_pereh = F.open_file_c(pereh_path, False, "|")
                        if self.xl_formulas.check_per(oper['name_ver'], pereh['name_ver'], True):
                            params_names = self.xl_formulas.get_per_params(oper['name_ver'], pereh['name_ver'])
                        else:
                            params_names = self._spis_parametrov_na_perehod(pereh['name_ver'],spis_pereh)
                        if len(params_names) > 0:
                            if len(params_names) == len(pereh['params']):
                                pereh['params_dict'] = F.list_of_lists_to_list_of_dicts([params_names,
                                                                                 pereh['params']])[0]
                            else:
                                pereh['t_sht'] = 0
                                pereh['params'] = []
                                pereh['params_dict'] = dict()


    def save_tk(self, nom_mk:int = '',path_docs='',save_into_mk=False):
        if nom_mk=='':
            nom_mk = self.nom_mk
        if save_into_mk:
            if self.nom_mk == '':
                print(f' Techkards save_tk не заполнена nom_mk')
                return False
        if path_docs == '':
            path_docs = self.path_docs

        data_list = [[self.tk['hat']['dse_name']],
                     [self.tk['hat']['tk_name']],
                     [self.tk['hat']['litera']],
                     [self.tk['hat']['razrabotal_name']],
                     [self.tk['hat']['razrabotal_date']],
                     [self.tk['hat']['proveril_name']],
                     [self.tk['hat']['normiroval_name']],
                     [self.tk['hat']['metrolog_exsp_name']],
                     [self.tk['hat']['normokontrol']],
                     [self.tk['hat']['primechanie']],
                     ]
        for i in range(len(data_list)):
            if data_list[i] != self.sp_tk[i]:
                print(f' {self.sp_tk[i]} {data_list[i]}')


        i= 10
        for tk in self.tk['bodys']:
            tmp = [tk['name_ver'],tk['doc_mark'],tk['s_name'],tk['s_name_full'],'',tk['date'],
                              tk['razrabotal'],tk['primech'],'','','','','',"$".join(tk['doc_card']),
                              "$".join(tk['params']),tk['doc'],'','','','',str(tk['lvl'])]
            data_list.append(tmp)
            for j in range(len(self.sp_tk[i])):
                if self.sp_tk[i][j] != tmp[j]:
                    #print(f' {self.sp_tk[i][j]} {tmp[j]}')
                    pass
            i+=1
            for oper in tk['opers']:

                tmp_list_mat = []
                for line_mat in oper['materials']:
                    line =  "$".join([line_mat['cod'],line_mat['naimen'],line_mat['ed_izm'],'{:.8f}'.format(round(line_mat['norma'], 8))] )
                    tmp_list_mat.append(line)
                mats = "{".join(tmp_list_mat)

                tmp = [oper['name_ver'], oper['doc_mark'], oper['s_name'], oper['s_name_full'], oper['rab_centr'],
                 oper['oborudovanie'],
                 str(oper['t_pz']), str(oper['t_sht']), oper['profession'], str(oper['kr']), mats, str(oper['koid']), '',
                 "$".join(oper['doc_card']),
                 "$".join(oper['params']), oper['doc'], oper['params_dict'], '', '', '', str(oper['lvl'])]
                data_list.append(tmp)
                for j in range(len(self.sp_tk[i])):
                    if self.sp_tk[i][j] != tmp[j]:
                        #print(f' {self.sp_tk[i][j]} {tmp[j]}')
                        pass
                i += 1
                for pereh in oper['perehs']:
                    tmp = [pereh['name_ver'],pereh['doc_mark'],pereh['s_name'],pereh['s_name_full'],'','','',
                                      str(pereh['t_sht']),'','','', "$".join(pereh['prisposobs']),"$".join(pereh['instrums']),
                              "$".join(pereh['doc_card']), "$".join(pereh['params']),'',pereh['params_dict'],'','','',str(pereh['lvl'])]
                    data_list.append(tmp)
                    for j in range(len(self.sp_tk[i])):
                        if self.sp_tk[i][j] != tmp[j]:
                            #print(f' {self.sp_tk[i][j]} {tmp[j]}')
                            pass
                    i += 1
        if data_list != self.sp_tk:
            #print(f'ERROR')
            pass
        name_tk = self.dse['Номер_техкарты'] + '_' + self.dse['Номенклатурный_номер'] + ".txt"
        if F.existence_file_c(path_docs) == False:
            F.create_dir_c(path_docs)
        if save_into_mk != '':
            if F.existence_file_c(path_docs+ os.sep + nom_mk) == False:
                F.create_dir_c(path_docs+ os.sep + nom_mk)
            F.write_file_c(path_docs + os.sep + nom_mk + os.sep + name_tk, data_list, separ="|", pickl=True)
            print(f'Save successfull {path_docs + os.sep + nom_mk + os.sep + name_tk}')
        else:
            F.write_file_c(path_docs + os.sep + name_tk, data_list,separ="|", pickl=True)
            print(f'Save successfull {path_docs + os.sep + name_tk}')

    def save_approve(self, surname: str) -> bool:
        try:
            self.tk['hat']['proveril_name'] = surname
            self.save_tk()
            return True
        except Exception as e:
            return False

    def list_osn_mats(self,DICT_VID_NOMEN:dict,DICT_NOMEN:dict)->list:
        return []#todo


class Marshrut_cards():
    def __init__(self,
                 nom_mk: int,
                 db_mk,
                 db_resxml='',
                 load_resource=True,
                 row_from_db:dict=None,
                 byte_data_res_from_db=None,
                 load_znpr: bool = True,
                 DICT_RC_BY_CODE=None,
                 ):
        self.db = db_mk
        self.db_resxml = db_resxml
        request = f"""
                SELECT 
                mk.Пномер,
                mk.Дата,
                mk.Статус,
                mk.Номенклатура,
                mk.Номер_заказа,
                mk.Номер_проекта,
                mk.Вид,
                mk.Примечание,
                mk.Основание,
                mk.Прогресс,
                mk.Приоритет,
                mk.Направление,
                mk.Вес,
                mk.xml,
                mk.Количество,
                mk.Статус_ЧПУ,
                mk.Ресурсная,
                mk.Дата_завершения,
                mk.Коэф_парал,
                mk.Обеспечение,
                mk.Место,
                mk.Искл_план_рм,
                mk.Тип,
                mk.Ресурсная_дата,
                mk.ФИО,
                mk.НомКплан,
                mk.check_execute_opers,
                mk.Тип_доработки,
                mk.На_удал,

                дорезки_мк.Причина AS дорезки_мк_Причина,

                тип_дорезок.Имя AS тип_дорезок_Имя,
                тип_дорезок.Коэффициент_наряда AS тип_дорезок_Коэффициент_наряда,

                тип_доработок.Имя AS тип_доработок_Имя,
                тип_доработок.Коэффициент_наряда AS тип_доработок_Коэффициент_наряда,

                Тип_мк.Имя AS Тип_мк_Имя,
                Тип_мк.rgb AS Тип_мк_rgb

                 FROM mk LEFT JOIN дорезки_мк ON дорезки_мк.Номер_мк = mk.Пномер  
                LEFT JOIN тип_дорезок ON тип_дорезок.Пномер = дорезки_мк.Причина  
                LEFT JOIN тип_доработок ON тип_доработок.Пномер = mk.Тип_доработки 
                                LEFT JOIN Тип_мк ON Тип_мк.Пномер = mk.Тип 
                   WHERE mk.Пномер == {nom_mk};"""
        if row_from_db:
            row = row_from_db
        else:
            row = CSQ.custom_request_c(db_mk, request, rez_dict=True)[0]

        self.row = row
        self.Пномер = None,
        self.Дата = None,
        self.Статус = None,
        self.Номенклатура = None,
        self.Номер_заказа = None,
        self.Номер_проекта = None,
        self.Вид = None,
        self.Примечание = None,
        self.Основание = None,
        self.Прогресс = None,
        self.Приоритет = None,
        self.Направление = None,
        self.Вес = None,
        self.xml = None,
        self.Количество = None,
        self.Статус_ЧПУ = None,
        self.Ресурсная = None,
        self.Дата_завершения = None,
        self.Коэф_парал = None,
        self.Обеспечение = None,
        self.Место = None,
        self.Искл_план_рм = None,
        self.Тип = None,
        self.Ресурсная_дата = None,
        self.ФИО = None,
        self.НомКплан = None,
        self.check_execute_opers = None,
        self.Тип_доработки = None,
        self.На_удал = None
        self.дорезки_мк_Причина = None
        self.тип_дорезок_Имя = None
        self.тип_дорезок_Коэффициент_наряда = None
        self.тип_доработок_Имя = None
        self.тип_доработок_Коэффициент_наряда = None
        self.Тип_мк_Имя = None
        self.Тип_мк_rgb = None

        self.DICT_RC = DICT_RC_BY_CODE
        if self.DICT_RC is None:
            dict_rc(self, CFG.Config.project.db_users)

        for key in row.keys():
            exec(f'self.{key.replace(".", "_")} = row[key]')
        if self.Пномер != None:
            if db_resxml != '' and load_resource:
                self.res = Marshrut_cards._load_res(self.Пномер, db_resxml=self.db_resxml,
                                                    byte_data_res_from_db=byte_data_res_from_db)
        if load_znpr:
            try:
                config = CFG.Config.project

                squery = f"""SELECT CASE WHEN знпр.№проекта IS NOT NULL 
                       THEN знпр.№проекта 
                       ELSE mk.Номер_проекта 
                       END AS Номер_проекта, 


                        CASE WHEN знпр.№ERP IS NOT NULL 
                       THEN знпр.№ERP 
                       ELSE mk.Номер_заказа 
                       END AS Номер_заказа 

                FROM mk 
                         LEFT JOIN plan ON plan.Пномер = mk.НомКплан  
                       LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
                LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 

                           WHERE mk.Пномер = {self.Пномер}"""
                query = CSQ.custom_request_c(self.db, squery, rez_dict=True, one=True, attach_dbs=(config.db_kplan))
                self.Номер_заказа = query['Номер_заказа']
                self.Номер_проекта = query['Номер_проекта']
            except:
                print(f'Marshrut_cards __init__ : CFG.Config.project.db_kplan err')




    def is_del(self):
        if "На_удал" not in self.__dict__:
            return False
        if self.На_удал == None:
            return False
        return bool(self.На_удал)

    def update_norm_time(self, list_opers, db_dse, DICT_OPERS):
        print(f"Обновление МК {self.Пномер}")
        list_errors = []
        for i, dse in enumerate(self.res):
            for j, oper in enumerate(dse['Операции']):
                if oper['Опер_наименование'] in list_opers:
                    print(f"    ДСЕ {dse['Номенклатурный_номер']}:")
                    tk = Techkards(dse['Номенклатурный_номер'], db_dse, DICT_OP_NAME=self.DICT_OP_NAME)
                    tk._update_params_oper(DICT_OPERS)
                    rez_recalc = tk.recalc_opers(list_opers, DICT_OPERS)
                    if rez_recalc != None:
                        for item in rez_recalc:
                            list_errors.append(item)
                        continue
                    tk.save_tk()
                    tk.save_tk(self.Пномер, save_into_mk=True)
                    fl = False
                    dict_oper_tk = tk.get_oper(oper['Опер_номер'])
                    if oper['Опер_Тпз'] != dict_oper_tk['t_pz']:
                        print(f"        Тпз Было {oper['Опер_Тпз']}  Стало {dict_oper_tk['t_pz']}")
                        oper['Опер_Тпз'] = dict_oper_tk['t_pz']
                        fl = True
                    if oper['Опер_Тшт'] != round(dict_oper_tk['t_sht'] * dse['Количество'], 2):
                        print(
                            f"        Тшт Было {oper['Опер_Тшт']}  Стало {round(dict_oper_tk['t_sht'] * dse['Количество'], 2)}")
                        oper['Опер_Тшт'] = round(dict_oper_tk['t_sht'] * dse['Количество'], 2)
                        fl = True
                    if oper['Опер_Тшт_ед'] != dict_oper_tk['t_sht']:
                        print(f"        Тшт_ед Было {oper['Опер_Тшт_ед']}  Стало {dict_oper_tk['t_sht']}")
                        oper['Опер_Тшт_ед'] = dict_oper_tk['t_sht']
                        fl = True
                    if oper['Опер_КР'] != dict_oper_tk['kr']:
                        print(f"        КР Было {oper['Опер_КР']}  Стало {dict_oper_tk['kr']}")
                        oper['Опер_КР'] = dict_oper_tk['kr']
                        fl = True
                    if oper['Опер_КОИД'] != dict_oper_tk['koid']:
                        print(f"        КОИД Было {oper['Опер_КОИД']}  Стало {dict_oper_tk['koid']}")
                        oper['Опер_КОИД'] = dict_oper_tk['koid']
                        fl = True
        if len(list_errors) > 0:
            CQT.msgbox(pprint.pformat(list_errors))
            F.copy_bufer('\n'.join(list_errors))
        if fl:
            self.save_res()

    def update_naryads(self, DICT_OPERS):
        pass
        list_nar = CSQ.custom_request_c(self.db,
                                        f"""SELECT Пномер, Внеплан FROM naryad WHERE Номер_мк = {self.Пномер};""",
                                        rez_dict=True)
        for nom_nar in list_nar:
            nar = Naryads(nom_nar['Пномер'], self.db)
            nar.mk = self
            nar.recalc_by_mk(DICT_OPERS)

    def get_month_zaversh(self) -> str:
        if F.is_date(self.Дата_завершения):
            return F.datetostr(F.strtodate(self.Дата_завершения), "%Y-%m")
        return ''

    def get_pyear(self):
        pyear = self.Номер_заказа + "$" + F.datetostr(F.strtodate("20" + self.Дата), "%Y")

    def count_izdeliy(self):
        return self.Количество

    def get_dict_vid_rab(self, DICT_PROFESSIONS, only_osvoeno=False, by_one_izd=True):
        dict_vid_rab = dict()
        for dse in self.res:
            kol_dse = dse['Количество']
            for oper in dse['Операции']:
                kod_prof = oper['Опер_профессия_код']
                if kod_prof not in DICT_PROFESSIONS:
                    print(f'''err kod_prof = {kod_prof} {oper['Опер_профессия_наименование']} not 
                     in DICT_PROFESSIONS MK {self.Пномер}, dse {dse['Номенклатурный_номер']}, 
                      oper {oper['Опер_номер']} {oper['Опер_наименование']}''')
                    continue
                vid_rab = DICT_PROFESSIONS[kod_prof]['Вид_работ']
                if only_osvoeno:
                    minutes = 0
                    if 'Закрыто,шт.' in oper:
                        minutes = oper['Опер_Тпз'] + oper['Опер_Тшт'] / kol_dse * oper['Закрыто,шт.']
                else:
                    minutes = oper['Опер_Тпз'] + oper['Опер_Тшт']
                if vid_rab not in dict_vid_rab:
                    dict_vid_rab[vid_rab] = 0

                if by_one_izd:
                    dict_vid_rab[vid_rab] += minutes / self.count_izdeliy()
                else:
                    dict_vid_rab[vid_rab] += minutes
        return dict_vid_rab

    @staticmethod
    def _load_res(nom_mk: int, db_resxml='', byte_data_res_from_db=None):
        if db_resxml == '':
            db_resxml = F.bdcfg('db_resxml')
        if byte_data_res_from_db:
            res = load_res(nom_mk=[nom_mk, [byte_data_res_from_db]])
        else:
            # res = CSQ.custom_request_c(db_resxml, f'''SELECT data FROM res WHERE Номер_мк == {nom_mk}''')
            res = load_res(nom_mk, db_resxml=db_resxml)

        return res

    def save_res(self, db_resxml=''):
        if db_resxml == '':
            db_resxml = F.bdcfg('db_resxml')
        if 'res' not in self.__dict__:
            return False
        blob1 = F.to_binary_pickle(self.res)
        blob = CSQ.for_blob(blob1)

        CSQ.custom_request_c(db_resxml, f'''UPDATE res SET data = ? WHERE Номер_мк = ?;''',
                             list_of_lists_c=[blob1, self.Пномер])
        return True

    def get_etap_by_num_operation(self, num_pp: str, oper_num: str):
        try:
            for dse in self.res:
                if int(dse['Номерпп']) == int(num_pp):
                    for oper in dse['Операции']:
                        if oper['Опер_номер'] == oper_num:
                            return self.DICT_RC[oper['Опер_РЦ_код']]['etaps_name'],oper['Опер_РЦ_код'], None
        except Exception as e:
            print(f'Marshrut_cards.get_etap_by_num_operation ошибка при поиске этапа: {e}')
        return None,None, f'Не найден этап для {num_pp} с номером операции {oper_num}'


class Naryads():
    def __init__(self,p_nom_or_row,db_naryad=None,dict_dolgn_etap=None,db_users=None,dict_empl=None):
        self.params = []
        self.db = db_naryad
        self.row = []
        self.Пномер = None
        self.Дата = None
        self.Автор = None
        self.Номер_мк = None
        self.Внеплан = None
        self.Задание = None
        self.Компл_ФИО = None
        self.Компл_Дата = None
        self.Компл_номер_тара = None
        self.Компл_адрес = None
        self.Распред_ФИО = None
        self.ФИО = None#test
        self.Фвремя = None
        self.ФИО2 = None
        self.Фвремя2 = None
        self.Твремя = None
        self.ДСЕ = None
        self.ДСЕ_ID = None
        self.Операции = None
        self.Опер_время = None
        self.Опер_колво = None
        self.Примечание = None
        self.Коэфф_сложности = None
        self.Подтвержд_вып = None
        self.Категория_внепл = None
        self.Виды_работ = None
        self.Номер_замечания_журнал = None
        self.Подтвержд_вып_дата = None
        self.Подтвержд_вып_фио = None
        self.Профессии = None
        self.РЦ_наряд = None
        self.ФИО_для_ОТК = None
        self.Коэф_норм_созд = None
        self.Аутсорсинг = None
        self.Обособленная_расценка = None
        self.Заводской_комплект = None
        self.Норма_времени = None
        self.Этап_фио_1 = None
        self.Этап_фио_2 = None
        self.ФИО_для_ОТК_от_мастера = None
        self.Кол_повт_приемок = None
        self.Распред_дата = None
        self.month_closing_block = None
        self.ДатаМК = None
        self.АвтоПодтвержд:int|None = None
        if type(p_nom_or_row) == int:
            if db_naryad == None:
                print(f'Не задан db_naryad')
                return
            row = CSQ.custom_request_c(db_naryad,f'''SELECT naryad.*, mk.Дата as ДатаМК FROM naryad JOIN mk ON mk.Пномер = naryad.Номер_мк 
            WHERE naryad.Пномер == {p_nom_or_row};''',rez_dict=True)
            if row == None or row == False or row == []:
                return
            row = row[0]
        else:
            row = p_nom_or_row
        self.row = row
        for key in row.keys():
            exec(f'self.{str(key).replace(".", "_")} = row[key]')

        self.params = self._get_strukt_params()
        if db_users != None:
            if dict_dolgn_etap == None:
                dict_dolgn_etap =F.deploy_dict_c(CSQ.custom_request_c(db_naryad,f"""SELECT * FROM dolgn_etap""",rez_dict=True),'Должность')
            if dict_empl == None:
                dict_empl =F.deploy_dict_c(CSQ.custom_request_c(db_users,query = f"""SELECT * FROM employee WHERE Пномер IN( SELECT Пномер FROM (SELECT
    	MAX(Пномер) as Пномер,
    	ФИО
    FROM
    	employee
    GROUP BY
    	ФИО
    HAVING COUNT(*) >= 1 )) order by ФИО;""",rez_dict=True),'ФИО')
            if self.ДатаМК is None: #07.07.25
                print('[Cust_mes.Naryads.__init__] не задано поле ДатаМК')
                row = CSQ.custom_request_c(db_naryad,f'''SELECT mk.Дата as ДатаМК FROM naryad JOIN mk ON mk.Пномер = naryad.Номер_мк 
            WHERE naryad.Пномер == {p_nom_or_row};''',rez_dict=True, one=True)
                self.__dict__.update(row)
            if self.ФИО != '':
                self.Этап_фио_1 = etap_by_employee(date_str=self.ДатаМК, key_employee=self.ФИО) # 07.07.25
            if self.ФИО2 != '':
                self.Этап_фио_2 = etap_by_employee(date_str=self.ДатаМК, key_employee=self.ФИО2) # 07.07.25
        self.dict_dolgn_etap = dict_dolgn_etap
        self.dict_empl = dict_empl

    def etap_by_fio(self, fio: str): #17.07.25
        match str(fio):
            case self.ФИО:
                return self.Этап_фио_1
            case self.ФИО2:
                return self.Этап_фио_2
            case _:
                return ''

    def recalc_jur_n_time(self,fio):
        jur = Jurnal_nar(self.db, self.Пномер, fio)
        if jur.selected_fragment_end_date == None:
            return
        jur.calc_and_set_poditog(jur.selected_fragment_end_state, jur.selected_fragment_end_date)
        if jur.selected_fragment_end_state == 'Завершен':

            if self.Фвремя == 0 or self.Фвремя2 == 0:
                jur.calc_and_fill_nar_by_zaversh(self.dict_empl, jur.user)
        while jur.next_fragment():
            if jur.selected_fragment_end_date == None:
                break
            jur.calc_and_set_poditog(jur.selected_fragment_end_state, jur.selected_fragment_end_date)
            if jur.selected_fragment_end_state == 'Завершен':

                if self.Фвремя == 0 or self.Фвремя2 == 0:
                    jur.calc_and_fill_nar_by_zaversh(self.dict_empl, jur.user)

    def get_list_from_jurnal(self,blob_pass=False):
        jur = Jurnal_nar(self.db,self.Пномер,blob_pass=blob_pass)
        return jur

    def recalc_fact(self):
        jur = self.get_list_from_jurnal()
        summ1 = 0
        summ2 = 0
        fl_zav1 = False
        fl_zav2 = False
        for item in jur.rows:
            if self.ФИО != '' and item['ФИО'] == self.ФИО:
                summ1 += item['Подытог']
                if item['Статус'] == 'Завершен':
                    fl_zav1 = True
            if self.ФИО2 != '' and item['ФИО'] == self.ФИО2:
                summ2 += item['Подытог']
                if item['Статус'] == 'Завершен':
                    fl_zav2 = True
        if summ1 == 0:
            summ1 = ''
        if summ2 == 0:
            summ2 = ''
        if self.ФИО != '' and fl_zav1:
            self.Фвремя = summ1
        if self.ФИО2 != '' and fl_zav2:
            self.Фвремя2 = summ2
        if fl_zav1 or fl_zav2:
            self._save_nar()
        else:
            print(f'recalc_fact Наряд {self.Пномер} не выполнен нет завершения в журнале')


    def load_mats(self,DICT_PROFESSIONS,db_xml=None):
        if 'mk' not in self.__dict__:
            if db_xml==None:
                raise Exception('не указан db_xml для загрузки МК')
            self.get_mk(db_xml=db_xml,load_resource=True)
        if self.mk.res == None:
            print(f'МК № {self.mk.Пномер} не имеет ресурсной')
        fl_fix_mk = False
        for i in range(len(self.params)):
            id = self.params[i]['ДСЕ_ID']
            oper_nom = self.params[i]['Операции_номер']
            self.params[i]['Материалы'] = []
            self.params[i]['Этап_материала'] = ''
            if self.mk.res == None:
                continue
            for dse in self.mk.res:
                if dse['Номерпп'] == id:
                    for oper in dse['Операции']:
                        if oper['Опер_номер'] == oper_nom:
                            self.params[i]['Материалы'] = copy.deepcopy(oper['Материалы'])
                            self.params[i]['Этап_материала'] = oper['Этап'] # 26.06.25
                            break
                    break
        if fl_fix_mk:
            self.mk.save_res(db_xml)


    def is_closed(self):
        if self.ФИО != "" and self.Фвремя == '':
            return False
        if self.ФИО2 != "" and self.Фвремя2 == '':
            return False
        return True

    def set_koef_nar(self,val:float):
        self.Коэфф_сложности = val
        self._save_nar()

    def count_users(self):
        count = 0
        if self.ФИО != '':
            count+=1
        if self.ФИО2 != '':
            count+=1
        return count

    def is_confirmed(self):
        if self.Подтвержд_вып == '':
            return False
        return True

    def get_mk(self,db_xml='',load_resource=False):
        if db_xml== '':
            db_xml = CFG.Config.project.db_resxml
        self.mk = Marshrut_cards(self.Номер_мк,self.db,db_xml,load_resource)

    def _get_strukt_params(self):

        def _list_dse_name_nn(self):
            if self.ДСЕ == '':
                return []
            list_dse = self.ДСЕ.split('|')
            return [name_nn for name_nn in list_dse]

        def _list_dse_id(self):
            if self.ДСЕ_ID == '':
                return []
            list_dse_id = self.ДСЕ_ID.split('|')
            return [int(_) for _ in list_dse_id]

        def _list_opers_nom_name(self):
            if self.ДСЕ_ID == '$':
                return []
            list_opers = self.Операции.split('|')
            return [pnom_name.split('$') for pnom_name in list_opers]

        def _list_kolvo(self):
            if self.Опер_колво == '':
                return []
            list_kol = self.Опер_колво.split('|')
            return [int(_) for _ in list_kol ]

        def _list_prof(self):
            if self.Профессии == '':
                return []
            list_prof = self.Профессии.split('|')
            return list_prof

        def _list_time(self):
            if self.Профессии == '1' and self.ДСЕ_ID == '':
                return []
            list_time_minutes =self.Опер_время.split('|')
            return [F.valm(ch) for ch in list_time_minutes]

        def _list_time_norma(self):
            if self.Профессии == '1' and self.ДСЕ_ID == '':
                return []
            try:
                list_time_minutes =self.Опер_время.split('|')
                summ = 0
                for time in list_time_minutes:
                    summ+=F.valm(time)
                koef = self.Норма_времени/summ
                return [round(F.valm(ch)*koef,2) for ch in list_time_minutes]
            except:
                return [round(F.valm(ch),2) for ch in list_time_minutes]

        def _list_vid_r(self):
            if self.Виды_работ == '':
                return []
            list_vid_r =self.Виды_работ.split('|')
            return [vid_r for vid_r in list_vid_r]

        list_dse = _list_dse_name_nn(self)
        list_opers = _list_opers_nom_name(self)
        list_kol = _list_kolvo(self)
        list_time_minutes = _list_time(self)
        list_dse_id = _list_dse_id(self)
        list_prof = _list_prof(self)
        list_vid_r = _list_vid_r(self)
        list_time_norm = _list_time_norma(self)
        rez = []
        for i in range(len(list_dse_id)):
            if len(list_prof) != len(list_dse_id):
                print(f'naryad {self.Пномер} err list_prof')
                list_prof = ['' for _ in list_dse_id]
            if len(list_vid_r) != len(list_dse_id):
                print(f'naryad {self.Пномер} err list_prof')
                list_vid_r = ['' for _ in list_dse_id]
            rez.append({'ДСЕ':list_dse[i],
                        'ДСЕ_ID':list_dse_id[i],
                        'Операции_номер':list_opers[i][0],
                        'Операции_имя':list_opers[i][1],
                        'Опер_колво':list_kol[i],
                        'Опер_время':list_time_minutes[i],
                        'Профессии':list_prof[i],
                        'Виды_работ':list_vid_r[i],
                        'Норма_времени_пооперационно':list_time_norm[i]})
        return rez

    def recalc_by_mk(self,DICT_OPERS, DICT_PROFESSIONS):
        summ_time = 0
        zadanie = ''
        for i, item_nar in enumerate(self.params):
            naim, nn = item_nar['ДСЕ'].split('$')
            id = item_nar['ДСЕ_ID']
            nom_oper = item_nar['Операции_номер']
            count_nar = item_nar['Опер_колво']
            for dse_mk in self.mk.res:
                if dse_mk['Номерпп'] == id:
                    new_dse = '$'.join([dse_mk['Наименование'],dse_mk['Номенклатурный_номер']])
                    new_dse_z = ' '.join([dse_mk['Наименование'],dse_mk['Номенклатурный_номер']])
                    for oper_mk in dse_mk['Операции']:
                        if oper_mk['Опер_номер'] == nom_oper:
                            self.params[i]['ДСЕ'] = new_dse
                            self.params[i]['Опер_время'] = round(oper_mk['Опер_Тпз'] + oper_mk['Опер_Тшт_ед'] * item_nar['Опер_колво'],2)
                            docs = "; ".join(oper_mk['Опер_документы'])
                            perehod = "; ".join(oper_mk['Переходы'])
                            head = f'{new_dse_z} ' \
                                   f'({count_nar} шт.) - {self.params[i]["Опер_время"]} мин.'
                            body = f' {docs} ' + '\n' + \
                                   f'    {self.params[i]["Операции_имя"]} {self.params[i]["Операции_номер"]}' + '\n' + \
                                   f'   {perehod}'
                            zadanie += head + body + '\n' + '\n'
                            break
                    break
            summ_time+=self.params[i]['Опер_время']
        self.Задание = zadanie
        if self.count_users() >0:
            summ_time = summ_time/self.count_users()
        summ_time = round(summ_time,2)

        self.Твремя = summ_time
        for key in self.params[0].keys():
            elem = '|'.join([str(_[key]) for _ in self.params])
            exec(f'self.{key} = "{elem}"')
        self.recalc_astronom_time(DICT_OPERS)
        self._save_nar()

    def _recalc_selfrow(self):
        for key in self.row.keys():
            if key in self.__dict__:
                exec(f'self.row["{key}"] = self.{key}')
        if not self.params: #10.11.25
            return
        for key in self.params[0].keys():
            if key in self.__dict__:
                elem = '|'.join([str(_[key]) for _ in self.params])
                self.row[key] = elem
                exec(f'self.{key} = "{elem}"')

    def _save_nar(self):
        self._recalc_selfrow()
        row_db = CSQ.custom_request_c(self.db,f"""SELECT * FROM naryad WHERE Пномер = {self.Пномер};""",rez_dict=True)
        if row_db == None or row_db == False:
            print(f'ОШибка загрузки наряда CMS.Naryads._save_nar')
            return
        row_db = row_db[0]
        for key in row_db:
            if key not in self.row:
                CQT.msgbox(f'_save_nar Ошибка синхронизации по полю "{key}"')
                continue
            self.fix_error_zero_f_time()
            if row_db[key] != self.row[key]:
                if type(self.row[key]) == int:
                    CSQ.custom_request_c(self.db,f"""UPDATE naryad SET {key} = {self.row[key]} WHERE Пномер = {self.Пномер};""")
                else:
                    CSQ.custom_request_c(self.db, f"""UPDATE naryad SET {key} = "{self.row[key]}" WHERE Пномер = {self.Пномер};""")


    def fix_error_zero_f_time(self):
        for key, val in self.row.items():
            if key == 'ФИО' and val == '':
                self.row['Фвремя'] = ''

            if key == 'ФИО2' and val == '':
                self.row['Фвремя2'] = ''


    def get_n_time(self):
        if self.count_users() == 2:
            return round(self.Норма_времени/2,2)
        else:
            return self.Норма_времени

    def get_summ_teor_time_by_empl(self):
        if self.count_users() == 2:
            return round(self.Твремя*2,2)
        else:
            return self.Твремя

    def recalc_tvrem(self):
        summ = 0
        for item in self.params:
            summ += item['Опер_время']
        if self.count_users() == 2:
            summ= round(summ/2,2)
        self.Твремя = round(summ, 2)
        self._save_nar()


    def recalc_astronom_time(self,DICT_OPER_NAME):
        summ  = 0
        if self.count_users() == 2:
            for item in self.params:
                time = item['Опер_время']
                if item['Операции_имя'] in DICT_OPER_NAME:
                    if DICT_OPER_NAME[item['Операции_имя']]['kr_default'] == 2:
                        time = item['Опер_время']/0.7
                summ += time
        else:
            for item in self.params:
                summ += item['Опер_время']


        if summ >= 11:
            summ += F.round_up(summ / 480) * 5
            summ +=5

        self.Норма_времени = round(summ,2)
        if self.Твремя >0:
            if self.count_users() == 2:
                change = round(self.Норма_времени/self.Твремя/2,2)
            else:
                change = round(self.Норма_времени/self.Твремя,2)
        self._save_nar()
        return change

    def is_month_closing_block(self):
        if not CFG.Config.place.use_month_closing_block_for_naryads:
            return False
        if self.month_closing_block == '':
            return  False
        now = F.now('')
        curr_month = F.datetostr(now,"%Y-%m")
        if curr_month == self.month_closing_block:
            if now < F.add_days(F.start_end_dates_c(vid='m',format_out='')[0],timedelta(days=3)):
                return False
        return True

    @staticmethod
    def check_month_block(db_nar,org_key,DICT_EMPLOEE_FULL_WITH_DEL_ref):
        previos_month = F.start_end_dates_c(F.add_months(F.now(""), -1),format_in = '',vid='m', format_out="")[0]
        previos_month_int= previos_month.month
        previos_year_int = previos_month.year
        m = ODAT.OrdersComposit()
        data = m.get_response('Document_ДанныеДляРасчетаЗарплаты',f"""?$filter=DeletionMark eq false and Организация_Key eq guid'{org_key}' 
        and year(Период) eq {previos_year_int} and month(Период) eq {previos_month_int}&$top=1000&$select=Number, 
         Posted, Период, Подразделение_Key, ИспользоватьПриРасчетеПервойПоловиныМесяца, ФизическиеЛица""")
        dict_users_block = dict()
        dict_users_unblock = dict()
        for doc in data:
            name_doc  = f"Данные для расчета ЗП {doc['Number']}"
            if doc['Подразделение_Key'] == '00000000-0000-0000-0000-000000000000':
                continue
            for user in doc['ФизическиеЛица']:
                if user['ФизическоеЛицо_Key'] in DICT_EMPLOEE_FULL_WITH_DEL_ref:
                    if doc['Posted']:
                        dict_users_block[DICT_EMPLOEE_FULL_WITH_DEL_ref[user['ФизическоеЛицо_Key']]['ФИО']] = name_doc
                    else:
                        dict_users_unblock[DICT_EMPLOEE_FULL_WITH_DEL_ref[user['ФизическоеЛицо_Key']]['ФИО']] = name_doc


        nach, konec = F.start_end_dates_c(F.add_months(F.now(""), -1),format_in = '',vid='m', format_out="%Y-%m-%d %H:%M:00")
        custom_request_c = f'''SELECT jurnal.Номер_наряда, jurnal.ФИО, naryad.month_closing_block FROM jurnal 
        INNER JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда 
        INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
        INNER JOIN plan ON plan.Пномер = mk.НомКплан   
        WHERE plan.poki = {CFG.Config.place.poki} AND jurnal.Статус == "Завершен" AND jurnal.Дата <= strftime("%Y-%m-%d %H:%M:00", datetime("{konec}")) AND 
        jurnal.Дата >= strftime("%Y-%m-%d %H:%M:00", datetime("{nach}")) AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1'''
        list_per_month_c = CSQ.custom_request_c(db_nar, custom_request_c,rez_dict=True, attach_dbs=(CFG.Config.project.db_kplan))

        nar_to_block = set()
        nar_to_unblock = set()
        for item in list_per_month_c:
            if item['month_closing_block'] == "" and item['ФИО'] in dict_users_block:
                nar_to_block.add(item['Номер_наряда'])
            if item['month_closing_block'] != "" and item['ФИО'] in dict_users_unblock:
                nar_to_unblock.add(item['Номер_наряда'])
        nar_to_unblock = {_ for _ in nar_to_unblock if _ not in nar_to_block}

        now = F.now('')
        # now =F.strtodate(F.datetostr(F.add_months(F.strtodate(data_kon), 1),"%Y-%m-02 15:48:38"))
        previos_month_str = F.datetostr(F.add_months(now, -1), "%Y-%m")
        if nar_to_unblock:
            CSQ.custom_request_c(db_nar, f"""UPDATE naryad SET month_closing_block =
         "" WHERE Пномер in ({CSQ.prepare_list_to_tuple(list(nar_to_unblock))})""")
        if nar_to_block:
            CSQ.custom_request_c(db_nar, f"""UPDATE naryad SET month_closing_block = 
                     "{previos_month_str}" WHERE Пномер in ({CSQ.prepare_list_to_tuple(list(nar_to_block))})""")




class Jurnal_nar():
    PODITOG_NORM_FOR_IDLE = 0.001  # 30.05.2025 По задаче (100054819)

    def __init__(self,db_nar:str,nom_nar:int=0,user:str=None,list_dicts_jur=None,blob_pass= False):
        if user != None and len(user.split())>3:
            raise ValueError('user name error:count words')
        if nom_nar== 0 and user==None:
            raise ValueError("nom_nar== 0 and user==None")
        if list_dicts_jur == None:
            list_zap = []
            if user == '':
                pass
            else:
                postfix_nom = f'Номер_наряда = {nom_nar}'
                if nom_nar == 0 and user!=None:
                    postfix_nom = ''

                postfix = ''
                if user:
                    if postfix_nom == '':
                        postfix = f"""ФИО = '{user}'"""
                    else:
                        postfix = f""" AND ФИО = '{user}'"""
                fields = '*'
                if blob_pass:
                    dict_fields= CSQ.list_types_table(db_nar,'jurnal')
                    fields = ', '.join([k for k,v in dict_fields.items() if v != 'BLOB'])
                list_zap = CSQ.custom_request_c(db_nar, f"""SELECT {fields}
                        FROM jurnal WHERE {postfix_nom}{postfix} ORDER BY Номер_наряда, datetime(Дата) ASC;""", # 30.01.2026
                                                rez_dict=True)
        else:
            if nom_nar == 0:
                if user != None:
                    list_zap = [_ for _ in list_dicts_jur if _['ФИО'] == user]
                else:
                    raise ValueError('Jurnal_nar list_zap не определен')
            else:
                if user != None:
                    list_zap = [_ for _ in list_dicts_jur if _['ФИО'] == user and _['Номер_наряда'] == nom_nar]
                else:
                    list_zap = [_ for _ in list_dicts_jur if _['Номер_наряда'] == nom_nar]


        self.rows = list_zap
        self.user = user
        self.nom_nar = nom_nar
        self.db_nar = db_nar

        self.selected_fragment_start_s_num = None
        self.selected_fragment_start_date = None
        self.selected_fragment_start_row_obj_nom = None

        self.selected_fragment_end_s_num = None
        self.selected_fragment_end_date = None
        self.selected_fragment_end_state = None
        self.selected_fragment_end_row_obj_nom = None
        self.selected_fragment_dict_row_start = None
        self.err_zhuranl = False
        if self.user != None:
            for row in self.rows:
                if row['Статус'] == 'Начат':
                    self.set_selected_fragment(row['Пномер'])
                break
            if self.rows and self.selected_fragment_dict_row_start == None:
                self.err_zhuranl = True
                CQT.msgbox(f'для наряда {self.nom_nar} в журнале {self.user} не обнаружено `Начало работ` необходима правка журнала')


    def clear_mark_confirm(self):  # 10.04.25
        query = f"""
            UPDATE naryad
            SET Подтвержд_вып_дата = 0,
                Подтвержд_вып_дата = "",
                Подтвержд_вып_фио = ""
            WHERE Пномер = {self.nom_nar}
        """
        CSQ.custom_request_c(self.db_nar, query)

    def delete_all_rows(self):
        list_s_nums = [_['Пномер'] for _  in self.rows]
        CSQ.custom_request_c(self.db_nar,f"""DELETE FROM jurnal WHERE Пномер IN ({CSQ.prepare_list_to_tuple(list_s_nums)})""")
        self.rows = []


    def next_fragment(self):
        for row in self.rows:
            if row['Статус'] == 'Начат' and F.strtodate(row['Дата']) > F.strtodate(self.selected_fragment_start_date):
                self.set_selected_fragment(row['Пномер'])
                return True
        return False


    def get_s_num_start(self, s_num_end:int):
        rez = None
        row_end_num = None
        for i, row in enumerate(self.rows):
            if row['Пномер'] == s_num_end and row['Статус'] == 'Начат' and row['ФИО'] == self.user:
                return row['Пномер']
            if row['Пномер'] == s_num_end and row['Статус'] != 'Начат' and row['ФИО'] == self.user:
                row_end_num = i
                break
        if row_end_num == None:
            return False
        for j in range(row_end_num,-1,-1):
            if self.rows[j]['Статус'] == 'Начат' and self.rows[j]['ФИО'] == self.user:
                return self.rows[j]['Пномер']
        return  False

    def set_selected_fragment(self, s_num_start:int):
        if isinstance(s_num_start, str) and F.is_numeric(s_num_start):
            s_num_start = int(s_num_start)
        rez = None
        for i, row in enumerate(self.rows):
            if row['Пномер'] == s_num_start and row['Статус'] == 'Начат'and row['ФИО'] == self.user:
        #custom_request_c = f'''SELECT Номер_наряда, Пномер, Дата FROM jurnal WHERE ФИО == "{self.user}" AND
        #                    Статус == "Начат" and  Пномер == {s_num_start}'''
        #rez = CSQ.custom_request_c(self.db_nar, custom_request_c, hat_c=False)
                rez = [row['Номер_наряда'],row['Пномер'],row['Дата']]
                self.selected_fragment_start_row_obj_nom = i
                self.selected_fragment_dict_row_start = row
                break
        if rez == None or rez == False:
            return
        if len(rez) == 0:
            return
        #self.__init__(self.db_nar,rez[0][0],self.user)
        self.nom_nar = rez[0]
        self.selected_fragment_start_s_num = rez[1]
        self.selected_fragment_start_date = rez[2]

        self.selected_fragment_end_s_num = None
        self.selected_fragment_end_date = None
        self.selected_fragment_end_state = None
        self.selected_fragment_end_row_obj_nom = None

        #custom_request_c = f'''SELECT Номер_наряда, Пномер, Дата FROM jurnal WHERE ФИО == "{self.user}" AND
        #                            Статус != "Начат" and  Дата > {self.selected_fragment_start_date} LIMIT = 1'''
        rez = None
        for i, row in enumerate(self.rows):
            if i> self.selected_fragment_start_row_obj_nom and row['Номер_наряда'] == self.nom_nar and row['Статус'] != 'Начат' and F.strtodate(row['Дата'])  > F.strtodate(self.selected_fragment_start_date):
                rez = [row['Номер_наряда'],row['Пномер'],row['Дата']]
                self.selected_fragment_end_row_obj_nom = i
                self.selected_fragment_end_state = row['Статус']

                break
        #rez = CSQ.custom_request_c(self.db_nar, custom_request_c, hat_c=False)
        if rez != None and len(rez) > 0:

            self.selected_fragment_end_s_num = rez[1]
            self.selected_fragment_end_date = rez[2]

    def load_data_trdz_for_erp(self,parent_self,s_num_kpl,db_kpl,nom_nar,db_usres,db_resxml):
        data_etaps = CSQ.custom_request_c(self.db_nar,f"""SELECT Минут_выгружено_ЕРП, Файл_выгрузки_ЕРП 
          FROM jurnal WHERE Пномер = ?;""",list_of_lists_c=[[self.selected_fragment_start_s_num]], rez_dict=True)
        if data_etaps == None or data_etaps == False:
            CQT.msgbox(f'Ошибка выгрузки этапов из БД')
            return

        dict_etaps = F.from_binary_pickle(data_etaps[0]['Файл_выгрузки_ЕРП'])
        for item in data_etaps:
            print(item)
        data_for_update_mes_db = [[None, '', '', 0,0,
                                   self.selected_fragment_start_s_num]]

        return dict_etaps, data_for_update_mes_db


    def create_data_trdz_for_erp(self, parent_self, s_num_kpl, db_kpl, nom_nar, db_usres, db_resxml,DICT_PROFESSIONS,DICT_VID_RABOT=None,day_shift_hours=1):

        dict_rez = dict()
        if s_num_kpl == 0:
            CQT.msgbox(f'КПЛ номер 0')
            return
        data_etap_erp = CSQ.custom_request_c(db_kpl,f"""SELECT пл_оуп.№ERP, пл_оуп.Дата_заявки_на_произв, пл_оуп.НомПартии_ЗП, знпр.Ref_Key_py, знпр.data_etaps_from_erp 
         FROM знпр INNER JOIN пл_оуп ON пл_оуп.Пномер_ЗП = знпр.s_num WHERE пл_оуп.НомПл == {s_num_kpl}""", rez_dict=True, one=True)
        if data_etap_erp == None or data_etap_erp == False:
            CQT.msgbox(f'Ошибка получения Пномер_ЗП')
            return
        if F.is_date(data_etap_erp['Дата_заявки_на_произв'],"%Y-%m-%d") == False:
            CQT.msgbox(f'В КПЛ {s_num_kpl},Дата_заявки_на_произв не дата, обратиться в ПДО')
            return
        ref_Key_py = data_etap_erp['Ref_Key_py']
        dict_etaps_from_erp = F.from_binary_pickle(data_etap_erp['data_etaps_from_erp'])
        if dict_etaps_from_erp == None:
            CQT.msgbox(f'В КПЛ {s_num_kpl} Не заполнены этапы при создании, обратиться в ПДО')
            return
        part_py = data_etap_erp['НомПартии_ЗП']
        nar = Naryads(nom_nar, self.db_nar, parent_self.Data.DICT_DOLGN_ETAP, db_usres, parent_self.Data.DICT_EMPL_FULL) #07.07.25 по задаче(100056203)
        etap = nar.etap_by_fio(self.user)
        if etap in parent_self.Data.DICT_ETAPI_FULL:
            if parent_self.Data.DICT_ETAPI_FULL[etap]['ДляЕРП'] == 0:
                CQT.msgbox(f'Этап {etap} не может быть выгуржен в ЕРП')
                return
        etap_dict = calc_num_etap_from_name_etap(dict_etaps_from_erp,part_py,etap,s_num_kpl,nar.Пномер)
        if etap_dict == None:
            return
        etap_num = etap_dict['Number']
        etap_ref_key_spec = dict_etaps_from_erp[str(part_py)]['Спецификация_Key']

        subtype = None
        nar.get_mk(db_resxml,True)
        nar.load_mats(DICT_PROFESSIONS, db_resxml)
        type_vneplan = nar.mk.Тип_мк_Имя
        if type_vneplan == 'Дорезка':
            subtype = nar.mk.тип_дорезок_Имя
        if type_vneplan == 'Доработка(без дорезки)':
            subtype = nar.mk.тип_доработок_Имя


        py_year = data_etap_erp['№ERP'] + "$" + F.datetostr(F.strtodate(data_etap_erp['Дата_заявки_на_произв'], ), "%Y")
        if py_year not in dict_rez:
            dict_rez[py_year] = {"Тип": type_vneplan,
                                 "Подтип": subtype,
                                 "Этапы": dict(),
                                 'Ref_Key_py':data_etap_erp['Ref_Key_py'],
                                 'Ref_Key_spec':etap_ref_key_spec,}
        if etap_num not in dict_rez[py_year]['Этапы']:
            dict_rez[py_year]['Этапы'][etap_num] = {'Расход': [],
                                                    'Традозатраты': [],

                                                    }
        count_users = nar.count_users()
        fiod = f"{self.user} {parent_self.Data.DICT_EMPL_FULL[self.user]['Должность']}"
        if self.selected_fragment_dict_row_start == None:
            CQT.msgbox(f'Ошибка чтения фрагмента')
            return
        time_block = self.selected_fragment_dict_row_start['Подытог_нормы']
        time_nar = nar.Твремя
        koeff = 0
        if time_nar > 0 and F.is_numeric(time_block):
            koeff = time_block/time_nar
        dict_opers_by_vid_rab = dict()

        if DICT_VID_RABOT == None:
            custom_request_c = f'''SELECT * FROM professions INNER JOIN vid_rab_po_dolg 
                ON vid_rab_po_dolg.Вид_работ = professions.вид_работ,
                 group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan WHERE Вкл = 1 and group_vid_rab_for_plan.composite = 0'''
            SPIS_prof = CSQ.custom_request_c(db_usres, custom_request_c, hat_c=False, rez_dict=True)
            DICT_VID_RABOT = F.deploy_dict_c(SPIS_prof, 'вид_работ')

        for i_oper, oper in enumerate(nar.params):
            key_mes = f'{str(self.selected_fragment_start_s_num)}_{i_oper}'
            vid_rabot = oper['Виды_работ']# parent_self.DICT_VID_RABOT[oper['Виды_работ']]['Вид_работ']
            if vid_rabot == None:
                continue
            if vid_rabot not in DICT_VID_RABOT:
                CQT.msgbox(f'Вид работ {vid_rabot} не найден в БД МЕС')
                return
            if DICT_VID_RABOT[vid_rabot]['ref_Key_erp'] == None:
                continue
            nom_nar = nar.Пномер
            time_minutes = oper['Опер_время']
            if count_users:
                time_minutes = oper['Опер_время'] / count_users
            data_nar = self.selected_fragment_end_date# resp_db_mes[i]['Дата']
            data_nar = F.datetostr(F.date_add_time(F.strtodate(data_nar), hours= -1*day_shift_hours))
            count_min = round(time_minutes*koeff,2)

            count_min = 0.01 if count_min == 0 else count_min
            if vid_rabot not in dict_opers_by_vid_rab:
                dict_opers_by_vid_rab[vid_rabot] = {
                     'Количество_мин': 0,
                     'Дата выполнения': '',
                     'Исполнитель': self.user,
                     'Статья калькуляции': 'Основной ФОТ',
                     'Ключ_мес': '',
                     }
            dict_opers_by_vid_rab[vid_rabot]['Количество_мин'] +=count_min
            dict_opers_by_vid_rab[vid_rabot]['Дата выполнения'] = data_nar
            #dict_opers_by_vid_rab[vid_rabot]['Исполнитель'] = self.user
            #dict_opers_by_vid_rab[vid_rabot]['Статья калькуляции'] = 'Основной ФОТ'
            dict_opers_by_vid_rab[vid_rabot]['Ключ_мес'] = key_mes

            #dict_rez[py_year]['Этапы'][etap_num]['Традозатраты'].append(
            #        {'НаименованиеЭтапа': etap,
            #         'Вид работ': vid_rabot,
            #         'Количество_мин': count_min,
            #         'Дата выполнения': data_nar,
            #         'Исполнитель': self.user,
            #         'Статья калькуляции': 'Основной ФОТ',
            #         'Ключ_мес': key_mes,
            #         })
            # etap_mat_name = oper['Этап_материала'] #25.08.25 Вычисление этапа по работнику ( задача 100059237 )
            if etap in parent_self.Data.DICT_ETAPI_FULL:
                if parent_self.Data.DICT_ETAPI_FULL[etap]['ДляЕРП'] == 1:
                    # etap_dict = calc_num_etap_from_name_etap(dict_etaps_from_erp, part_py, etap, s_num_kpl, nar.Пномер)
                    # if etap_dict == None:
                    #     return
                    etap_num_mat = etap_dict['Number']
                    etap_ref_key_spec = dict_etaps_from_erp[str(part_py)]['Спецификация_Key']
                    for mat in oper['Материалы']:
                            if etap_num_mat not in dict_rez[py_year]['Этапы']:
                                dict_rez[py_year]['Этапы'][etap_num_mat] = {'Расход': [],
                                                                        'Традозатраты': []}
                            count_mat = round(mat['Мат_норма_ед'] * oper['Опер_колво'] , 3)
                            if count_users:
                                count_mat = round(mat['Мат_норма_ед'] * oper['Опер_колво'] / count_users, 3)

                            count_mat = 0.001 if count_mat == 0 else count_mat

                            dict_rez[py_year]['Этапы'][etap_num_mat]['Расход'].append(
                                {'Артикул': mat['Мат_код'],
                                 'Номенклатура': mat['Мат_наименование'],
                                 'Характеристика': '',
                                 'Количество': count_mat,
                                 'Упаковка': '',
                                 'Ед. изм.': mat['Мат_ед_изм'],
                                 'Израсходован': data_nar,
                                 'Статья калькуляции': 'Сырье',
                                 'Задание на резку': '',
                                 'Ключ_мес': key_mes
                                 })

        for vid_rabot, vid_rab_data in dict_opers_by_vid_rab.items():
            dict_rez[py_year]['Этапы'][etap_num]['Традозатраты'].append(
                        {'НаименованиеЭтапа': etap,
                         'Вид работ': vid_rabot,
                         'Количество_мин': vid_rab_data['Количество_мин'],
                         'Дата выполнения': vid_rab_data['Дата выполнения'],
                         'Исполнитель': self.user,
                         'Статья калькуляции': 'Основной ФОТ',
                         'Ключ_мес': vid_rab_data['Ключ_мес'],
                         })

        data_for_update_mes_db = [[F.to_binary_pickle(dict_rez),F.user_name(),F.now(),time_block,
                                   parent_self.Data.DICT_BASES_ERP[parent_self.USER_CONFIG.ERP_base_name['Значение']]['s_num'],
                                   self.selected_fragment_start_s_num]]

        return dict_rez, data_for_update_mes_db

    def update_mes_db_trdz(self,data_for_update_mes_db):
        CSQ.custom_request_c(self.db_nar,f"""UPDATE jurnal SET Файл_выгрузки_ЕРП = ?, 
        ФИО_выгрузки_ЕРП = ?, Дата_выгрузки_ЕРП = ?, Минут_выгружено_ЕРП = ?, base_ERP = ? WHERE Пномер = ?;""",
                         list_of_lists_c=data_for_update_mes_db)


    def get_ontime_naruad(self,set_as_fragment=False):
        #custom_request_c = f'''SELECT Номер_наряда, Пномер, Дата FROM jurnal WHERE ФИО == "{self.user}" AND
        #                    Статус == "Начат" and  Подытог == 0'''
        #rez = CSQ.custom_request_c(self.db_nar, custom_request_c, hat_c=False)
        rez =  ['','','']
        for i, row in enumerate(self.rows):
            if (row['Подытог'] == 0 and row['Статус'] == 'Начат'and row['ФИО'] == self.user) or (row['Статус'] == 'Начат'and row['ФИО'] == self.user and i == len(self.rows)-1):
                rez = [row['Номер_наряда'],row['Пномер'],row['Дата']]
                if set_as_fragment:
                    self.set_selected_fragment(row['Пномер'])
                break
                return rez
        return rez

    def is_fregments_unclose(self):
        rez = self.get_ontime_naruad()
        if rez[0] == '':
            return  False
        return rez

    def calc_zadel(self):
        t_zadel = 0
        rez = self.is_fregments_unclose()
        if rez   == False:
            return  t_zadel
        else:
            t_zadel = (F.now("") - F.strtodate(rez[-1])).seconds // 60
        return t_zadel


    def get_last_status_nar(self):
        if self.nom_nar == 0:
            raise ValueError('self.nom_nar= 0')
        rez =  CSQ.custom_request_c(self.db_nar, f"""SELECT Статус FROM jurnal WHERE Номер_наряда == {self.nom_nar} 
                    and ФИО == "{self.user}" ORDER BY datetime(Дата) DESC LIMIT 1""")[-1][0] #03.02.2026
        if rez == None or rez == False:
            return None
        if len(rez) == 1:
            return None
        return rez

    def clear_poditog(self):
        if self.nom_nar == None:
            self.get_tekush_naruad()
        if self.nom_nar == '':
            return None
        custom_request_c = f'UPDATE jurnal SET Подытог == ?, Подытог_нормы == ? WHERE Пномер == ?'
        param = [0,0, self.selected_fragment_start_s_num]
        CSQ.custom_request_c(self.db_nar, custom_request_c, list_of_lists_c=param)
        self.rows[self.selected_fragment_start_row_obj_nom]['Подытог'] = 0
        self.rows[self.selected_fragment_start_row_obj_nom]['Подытог_нормы'] = 0

    def calc_and_set_poditog(self, state:str=None, now:str=None, is_idle: bool = False): # 30.05.2025 По задаче (100054819)
        if state == None:
            return False
        if self.nom_nar == None:
            self.get_tekush_naruad()
        if self.nom_nar == '':
            return None
        poditog, poditog_norm = self._calc_poditog(state, now)
        # +++ 30.05.2025 По задаче (100054819)
        if is_idle:
            poditog_norm = self.PODITOG_NORM_FOR_IDLE
        # --- 30.05.2025 По задаче (100054819)
        if poditog == None:
            return False
        param= []
        if (self.rows[self.selected_fragment_start_row_obj_nom]['Подытог'] != poditog and
                self.rows[self.selected_fragment_start_row_obj_nom]['Подытог_нормы'] != poditog_norm):
            custom_request_c = f'UPDATE jurnal SET Подытог == ?, Подытог_нормы == ? WHERE Пномер == ?'
            param = [poditog, poditog_norm, self.selected_fragment_start_s_num]
            print(f"Наряд: {self.nom_nar} было {self.rows[self.selected_fragment_start_row_obj_nom]['Подытог']}", f'стало {poditog}')
        if (self.rows[self.selected_fragment_start_row_obj_nom]['Подытог'] != poditog and
                self.rows[self.selected_fragment_start_row_obj_nom]['Подытог_нормы'] == poditog_norm):
            custom_request_c = f'UPDATE jurnal SET Подытог == ? WHERE Пномер == ?'
            param = [poditog, self.selected_fragment_start_s_num]
            print(f"Наряд: {self.nom_nar} было {self.rows[self.selected_fragment_start_row_obj_nom]['Подытог']}", f'стало {poditog}')
        if (self.rows[self.selected_fragment_start_row_obj_nom]['Подытог'] == poditog and
                self.rows[self.selected_fragment_start_row_obj_nom]['Подытог_нормы'] != poditog_norm):
            custom_request_c = f'UPDATE jurnal SET Подытог_нормы == ? WHERE Пномер == ?'
            param = [poditog_norm, self.selected_fragment_start_s_num]
            print(f"Наряд: {self.nom_nar} было {self.rows[self.selected_fragment_start_row_obj_nom]['Подытог']}", f'стало {poditog}')
        if len(param)>0:
            try:
                CSQ.custom_request_c(self.db_nar, custom_request_c, list_of_lists_c=param)
                self.rows[self.selected_fragment_start_row_obj_nom]['Подытог'] = poditog
                self.rows[self.selected_fragment_start_row_obj_nom]['Подытог_нормы'] = poditog_norm
            except:
                CQT.msgbox(f'Ошибка занесения в Журнал')
                return False
        return True

    def _calc_poditog(self,state:str,now=None,nar_obj=None):
        if now == None:
            now = F.now()
        if self.nom_nar == None:
            self.get_tekush_naruad()
        if self.nom_nar == '':
            return None
        date_diff = F.strtodate(now) - F.strtodate(self.selected_fragment_start_date)
        poditog = round(date_diff.total_seconds() / 60)
        poditog = 1 if poditog < 1 else poditog
        if nar_obj == None:
            nar_obj = Naryads(self.nom_nar ,self.db_nar)
        norma = nar_obj.Твремя
        poditog_norm = 0
        summ_time = self.get_summ_poditog()
        ostatok_norm = round(norma - summ_time,2)
        if state == 'Завершен':
            if ostatok_norm <= 0:
                poditog_norm = 0
            else:
                poditog_norm = ostatok_norm

        if state == 'Приостановлен':
            if ostatok_norm <= 0:
                poditog_norm = 0
            else:
                if poditog >= ostatok_norm:
                    poditog_norm = ostatok_norm
                else:
                    poditog_norm = poditog

        return poditog, round(poditog_norm,2)

    def get_summ_poditog(self,include_selected_fragment_start_date= False):
        fact_vr = 0

        if include_selected_fragment_start_date:
            for row in self.rows:
                if not F.is_date(row['Дата'], "%Y-%m-%d %H:%M:%S"):
                    CQT.msgbox(f'В наряде {self.nom_nar} в строке  {row}  дата в некорректном формате Подытог')
                    raise TypeError()
                if  not F.is_date(self.selected_fragment_start_date, "%Y-%m-%d %H:%M:%S"):
                    CQT.msgbox(f'В наряде {self.nom_nar} дата Начала работы по журналу не найдена')
                    raise TypeError()

                if (row['ФИО'] == self.user and row['Номер_наряда'] == self.nom_nar and
                        F.strtodate(row['Дата']) <= F.strtodate(self.selected_fragment_start_date)):
                    fact_vr += row['Подытог']
        else:
            for row in self.rows:
                if (row['ФИО'] == self.user and row['Номер_наряда'] == self.nom_nar and
                        F.strtodate(row['Дата']) < F.strtodate(self.selected_fragment_start_date)):
                    fact_vr += row['Подытог']
        #custom_request_c = f'''SELECT sum(Подытог) AS "Total Salary"
        #                          FROM jurnal
        #                         WHERE ФИО == "{self.user}" AND Статус == "Начат"
        #                        AND Номер_наряда == {self.nom_nar}'''
        #fact_vr = CSQ.custom_request_c(self.db_nar, custom_request_c)[-1][0]
        return fact_vr


    def list_users(self):
        set_usres = set()
        for row in self.rows:
            set_usres.add(row['ФИО'])
        return  list(set_usres)

    def set_user(self,user):
        self.rows = [_ for _  in self.rows if _['ФИО'] == user ]
        self.user = user

    def calc_start_end_dates(self):
        start = None
        end = None
        for row in self.rows:
            if start == None or F.strtodate(row['Дата']) < start:
                start = F.strtodate(row['Дата'])
            if end == None or F.strtodate(row['Дата']) > end:
                end = F.strtodate(row['Дата'])
        if start != None:
            start =F.datetostr(start)
        if end  != None:
            end = F.datetostr(end)
        return start ,end

    def add_new_row(self,DICT_EMPL_FULL,lbl_abstract_text,date_time=None,state='Начат',primech='', is_idle = False):
        if date_time == None:
            date_time = F.now()
        minutes = 0
        shtamp = F.shtamp_from_date(date_time)
        line = [date_time,
                  shtamp,
                  self.nom_nar,
                  self.user,
                  minutes,
                  state,
                  primech,
                  '']
        if state == 'Приостановлен':
            if primech == '' or len(primech) < 4:
                CQT.msgbox('Не указана причина паузы')
                return False

        if state == 'Приостановлен' or state == 'Завершен':
            result = self.calc_and_set_poditog(state,date_time, is_idle)
            if result == None or result == False:
                raise ValueError("Ошибка расчета подытога")

            #self.nom_nar = None

        journal_pk = CSQ.custom_request_c(self.db_nar, #25.01.2026
            f"""INSERT INTO jurnal 
            (Дата, Штамп, Номер_наряда,ФИО,Подытог,Статус,Примечание,Ном_заверш)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING Пномер;""", list_of_lists_c=line, one=True, one_column=True, hat_c=False)
        # F.time_sleep(2)
        # check = CSQ.custom_request_c(self.db_nar, f"""SELECT Пномер FROM jurnal WHERE Штамп = '{shtamp}'
        #          and ФИО == '{self.user}'; """, one=True)
        if not isinstance(journal_pk, int):
            self.clear_poditog()
            if CFG.Config.app.is_ui:
                CQT.msgbox(f'Ошибка занесения в Журнал_3 попробуй позже')
                return False
            else:
                raise Exception("[Cust_mes.add_new_row] Ошибка при попытке добавить строку")

        if state == 'Завершен':
            self.calc_and_fill_nar_by_zaversh(DICT_EMPL_FULL,lbl_abstract_text)
        return journal_pk

    def refresh(self): #02.02.2026
        self.__init__(self.db_nar, self.nom_nar, self.user)

    def update_row( #02.02.2026
            self,
            DICT_EMPL_FULL,
            lbl_abstract_text,
            journal_id: int,
            is_idle: bool,
            *,  # Поля таблицы
            date_time: str = None,                  # Дата
            state: str = None,                      # Статус
            comment: str = None,                    # Примечание
            num_end: int = None,                    # Ном_заверш
            load_erp_date: str = None,              # Дата_выгрузки_ЕРП
            load_erp_fio: str = None,               # ФИО_выгрузки_ЕРП
            load_erp_file: bytes = None,            # Файл_выгрузки_ЕРП
            load_erp_minutes: float | int = None,   # Минут_выгружено_ЕРП
            base_ERP: int = None,                   # base_ERP
    ):
        """
            Обновить строку журнала
            @ Если указан date_time, то подытог пересчитывается по новому значению
            """
        body = {}
        if date_time is not None:
            body['Дата'] = date_time
            body['Штамп'] = F.shtamp_from_date(date_time)
        if state is not None:
            body['Статус'] = state
        if comment is not None:
            body['Примечание'] = comment
        if num_end is not None:
            body['Ном_заверш'] = num_end
        if load_erp_date is not None:
            body['Дата_выгрузки_ЕРП'] = load_erp_date
        if load_erp_fio is not None:
            body['ФИО_выгрузки_ЕРП'] = load_erp_fio
        if load_erp_file is not None:
            body['Файл_выгрузки_ЕРП'] = load_erp_file
        if load_erp_minutes is not None:
            body['Минут_выгружено_ЕРП'] = load_erp_minutes
        if base_ERP is not None:
            body['base_ERP'] = base_ERP
        if not body:
            return
        update_set = ','.join(f'{k} = ?' for k, v in body.items())
        update_val = list(body.values())
        if date_time and (state == 'Приостановлен' or state == 'Завершен'):
            result = self.calc_and_set_poditog(state, date_time, is_idle)
            if result == None or result == False:
                raise ValueError("Ошибка расчета подытога")
        journal_pk = CSQ.custom_request_c(
            self.db_nar,  # 25.01.2026
            f"""UPDATE jurnal SET {update_set} WHERE Пномер = {journal_id} RETURNING Пномер;""",
            list_of_lists_c=update_val,
            one=True,
            one_column=True,
            hat_c=False
        )
        if not isinstance(journal_pk, int):
            print('[Cust_mes.Journal_nar.update_row] Не удалось обновить строку журнала')
            return False
        if date_time and state == 'Завершен':
            self.calc_and_fill_nar_by_zaversh(DICT_EMPL_FULL, lbl_abstract_text)
        return True

    def calc_and_fill_nar_by_zaversh(self,DICT_EMPL_FULL,lbl_abstract_text):
        fact_vr = self.get_summ_poditog(True)

        if DICT_EMPL_FULL[self.user]['Режим'] == 'Абстракт':
            custom_request_c = f'UPDATE jurnal SET ФИО = "{lbl_abstract_text}" WHERE ФИО == "{self.user}" AND Номер_наряда == {self.nom_nar}'
            CSQ.custom_request_c(self.db_nar, custom_request_c)
            print(f'Замена абстракта {self.user} на {lbl_abstract_text}')
            CSQ.custom_request_c(self.db_nar,
                                 f"""UPDATE naryad SET ФИО = "{lbl_abstract_text}" WHERE 
                                 ФИО = "{self.user}" AND Пномер == {self.nom_nar}""")
            CSQ.custom_request_c(self.db_nar,
                                 f"""UPDATE naryad SET ФИО2 = "{lbl_abstract_text}" WHERE 
                                 ФИО2 = "{self.user}" AND Пномер == {self.nom_nar}""")
            self.user = lbl_abstract_text
        custom_request_c = (f'UPDATE naryad SET Фвремя = {fact_vr} WHERE '
                            f' ФИО == "{self.user}" AND Пномер == {self.nom_nar}')
        CSQ.custom_request_c(self.db_nar, custom_request_c)
        custom_request_c = (f'UPDATE naryad SET Фвремя2 == {fact_vr} WHERE '
                            f'ФИО2 == "{self.user}" AND Пномер == {self.nom_nar}')
        CSQ.custom_request_c(self.db_nar, custom_request_c)

    def clear_nar_by_zaversh(self):
        custom_request_c = (f'UPDATE naryad SET Фвремя = "" WHERE '
                            f' ФИО == "{self.user}" AND Пномер == {self.nom_nar}')
        CSQ.custom_request_c(self.db_nar, custom_request_c)
        custom_request_c = (f'UPDATE naryad SET Фвремя2 == "" WHERE '
                            f'ФИО2 == "{self.user}" AND Пномер == {self.nom_nar}')
        CSQ.custom_request_c(self.db_nar, custom_request_c)


    def get_dict_primech(self):
        dict_users = dict()
        for row in self.rows:
            if row['Примечание'] == '':
                continue
            if row['ФИО'] not in dict_users:
                dict_users[row['ФИО']] = []
            dict_users[row['ФИО']].append(row['Примечание'])
        return dict_users


class Month_plan():
    def __init__(self,month,db_kplan):
        self.db_kplan = db_kplan
        rez = CSQ.custom_request_c(db_kplan,f"""SELECT file_poz_plan FROM mnts_plan WHERE Дата ="{month}";""",rez_dict=True)
        self.month = month
        self.data = None
        if len(rez):
            rez = rez[0]
            if not rez['file_poz_plan'] == None:
                self.data = F.from_binary_pickle(rez['file_poz_plan'])



class Doc_order():
    def __init__(self,date=None,user=None,compare_name_left=None,compare_name_right=None,doc_data=None,type_doc=None,pozition=None,s_num=None,db_kpl=None):
        if s_num == None:
            self.date = date
            self.user = user
            self.compare_name_left = compare_name_left
            self.compare_name_right = compare_name_right
            self.data = doc_data
            self.type_doc = type_doc
            self.pozition = pozition
            self.state = 1
            self.db = None
            self.s_num = None
            self.orders_res_mat_state_name = None
            self.orders_res_type_name = None
        else:
            dict_ord = CSQ.custom_request_c(db_kpl,f"""SELECT 
                orders_res_mat.s_num,
                orders_res_mat.date,
                orders_res_mat.data,
                orders_res_mat.user,
                orders_res_mat.compare_name_left,
                orders_res_mat.compare_name_right,
                orders_res_mat.pozition,
                orders_res_mat.type,
                orders_res_mat.state,
                orders_res_mat.date_status,
                orders_res_mat_states.name as orders_res_mat_state_name,
                orders_res_types.name as orders_res_type_name
             FROM orders_res_mat 
             LEFT JOIN orders_res_mat_states ON orders_res_mat_states.s_num = orders_res_mat.state
             LEFT JOIN orders_res_types ON orders_res_types.s_num = orders_res_mat.type
             WHERE s_num = {s_num};""",rez_dict=True,one=True)
            self.date = dict_ord['date']
            self.user = dict_ord['user']
            self.compare_name_left = dict_ord['compare_name_left']
            self.compare_name_right = dict_ord['compare_name_right']
            self.data = F.from_binary_pickle(F.unpack_byte_file(dict_ord['data']))
            self.type_doc = dict_ord['type']
            self.pozition = dict_ord['pozition']
            self.state =  dict_ord['state']
            self.db = db_kpl
            self.s_num = s_num
            self.orders_res_mat_state_name = dict_ord['orders_res_mat_state_name']
            self.orders_res_type_name = dict_ord['orders_res_type_name']

    def get_dir_files(self,dir_local):
        return dir_local + F.sep() + str(self.s_num)

    def set_state(self,state:int):
        CSQ.custom_request_c(self.db,f"""UPDATE orders_res_mat SET (state,date_status) = ({state},'{F.now("%Y-%m-%d")}') WHERE s_num = {self.s_num};""")

    def delete_from_db(self,db_kpl):
        CSQ.custom_request_c(db_kpl,f"""DELETE FROM orders_res_mat WHERE data = {self.date} and user = '{self.user}'""")


    def save_db(self,db_kpl):
        type = 0
        if self.type_doc == 'prof':
            type = 1

        rez_dict= dict()
        for item in self.data:
            etap = item['Этап']
            kod = item['Код']
            val = item['Количество']
            if etap not in rez_dict:
                rez_dict[etap] = dict()
            if kod not in rez_dict[etap]:
                rez_dict[etap][kod] = 0
            rez_dict[etap][kod]+=val
        bin_file = F.to_binary_pickle(rez_dict)
        packed = F.pack_byte_file(bin_file)

        list_tmp = [self.date, packed, self.user, self.compare_name_left, self.compare_name_right, type, self.pozition]
        CSQ.custom_request_c(db_kpl,f"""INSERT INTO orders_res_mat (date,
                                                                                        data,
                                                                                        user,
                                                                                        compare_name_left,
                                                                                        compare_name_right,
                                                                                        type,
                                                                                        pozition)
                              VALUES ({CSQ.questions_for_mask(list_tmp)});""",list_of_lists_c=[list_tmp])

    def divide_reser_zmvp(self,poz,DICT_NOMEN,SCHEME_SERVICE):

        def clear_data(rez_dict_docs):
            rez = dict()
            for doc in rez_dict_docs.keys():
                if 'ЗМВП' in doc:
                    tmp_tbl = []
                    for date_etap in rez_dict_docs[doc]:
                        for mat in rez_dict_docs[doc][date_etap]:
                            if rez_dict_docs[doc][date_etap][mat] == 0:
                                continue
                            tmp_tbl.append({"Ref_Key": mat,
                                            "Номенклатура": DICT_NOMEN[mat]['Наименование'],
                                            "Характеристика":"",
                                           "Действия":"К обеспечению",
                                           "Обособленно":'Нет',
                                           'Дата отгрузки':date_etap,
                                            'Назначение':"Планово-диспетчерский отдел Производства (Пауэрз)",
                                            "Серия":"",
                                           "Упаковка":"",
                                            'Ед. изм.' :DICT_NOMEN[mat]['ЕдиницаИзмерения'],
                                            'Количество':rez_dict_docs[doc][date_etap][mat],
                                            "Доступно":"",
                                            "Группа (вид) продукции":"",
                                            "Задание на резку":"",
                                            "Отменено":'',
                                            "Старое количество":""
                                            })
                    if tmp_tbl == []:
                        rez[doc] = None
                    else:
                        rez[doc] = F.list_of_dicts_to_list_of_lists(tmp_tbl)
                if doc == 'ЗП':
                    tmp_tbl = []
                    for item in rez_dict_docs[doc]:
                        if item['Количество'] == 0:
                            continue
                        tmp_tbl.append({
                            'Ref_Key': item['Ref_Key'],
                            'Номенклатура поставщика': "",
                            'Эл архив РКД в Docs': '',
                            'Архив на общем диске О': '',
                            'Номенклатура': item['Наименование'],
                            'Характеристика': '',
                            'Назначение': '',
                            'Количество': item['Количество'],
                            'Упаковка': 'м',
                            'Ед. изм.': DICT_NOMEN[mat]['ЕдиницаИзмерения'],
                            'Вид цены': '',
                            'Цена': '',
                            '% руч.': '',
                            'Сумма руч.': '',
                            'Сумма': '',
                            'Ставка НДС': '',
                            'НДС': '',
                            'Сумма с НДС': '',
                            'Склад': item['Склад'],
                            'Подразделение-получатель': '',
                            'Статья расходов': '',
                            'Списать на расходы': 'Нет',
                            'Аналитика расходов': '',
                            'Отменено по причине': '',
                            'Отменено': 'Нет',
                            'Упаковка (Факт)': '',
                            'Количество (Факт)': '',
                            'Цена (факт)': '',
                        }

                        )
                    if tmp_tbl == []:
                        rez['ЗП'] = None
                    else:
                        rez['ЗП'] = F.list_of_dicts_to_list_of_lists(tmp_tbl)

                    tmp_tbl = []
                    for item in rez_dict_docs[doc]:
                        mat = item['Ref_Key']
                        nomen = 'Не найдено в БД'
                        sheme = ''
                        if mat in DICT_NOMEN:
                            nomen = DICT_NOMEN[mat]['Наименование']
                            key_sheme = DICT_NOMEN[mat]['СхемаОбеспечения']
                            if key_sheme != '' and key_sheme in SCHEME_SERVICE:
                                sheme = SCHEME_SERVICE[key_sheme]['ГарантированныйСрокОбеспечения']
                        tmp_tbl.append({
                            'Штрихкод': '',
                            'Код': mat,
                            'Артикул': '',
                            'Номенклатура': nomen,
                            'Характеристика': '',
                            'Количество': item['Количество'],
                            'Цена': '10',
                            '% руч.': '',
                            'Сумма руч.': '',
                            'Сумма': '',
                            'НДС': '',
                            'Сумма с НДС': '',
                            'Требуемая дата': F.date_add_days(item['Дата'], -10, "%Y-%m-%d", "%Y-%m-%d", ),
                            'Этап': item['Этап'],
                            'Проект': poz.dict_tables['пл_оуп']['№проекта'],
                            '№ERP': poz.dict_tables['пл_оуп']['№ERP'],
                            'Номенклатура изделие': poz.dict_tables['пл_оуп']['Номенклатура_ЕРП'],
                            'Схема обеспечения': sheme
                        })
                    if tmp_tbl == []:
                        rez['ЗП_mail_дозаказ'] = None
                    else:
                        rez['ЗП_mail_дозаказ'] = F.list_of_dicts_to_list_of_lists(tmp_tbl)
            return rez

        def make_tbl_editorder(order, poz):
            rez = []
            etapes_dates = poz.get_plan_etaps_dates()
            for etap in order.data.keys():
                for mat in order.data[etap]:
                    nomen = 'Не найдено в БД'
                    sheme = ''
                    if mat in self.DC.DICT_NOMEN_KOD:
                        nomen = self.DC.DICT_NOMEN_KOD[mat]
                        key_sheme = self.DC.DICT_NOMEN_KOD[mat]['СхемаОбеспечения']
                        if key_sheme != '' and key_sheme in self.DC.SCHEME_SERVICE:
                            sheme = self.DC.SCHEME_SERVICE[key_sheme]['ГарантированныйСрокОбеспечения']
                    rez.append({
                        'Код': mat,
                        'Номенклатура': nomen,
                        'Корректировка по количеству': order.data[etap][mat],
                        '№ Заказа от ПДО в ОС': '',
                        '№ Заказы от ПДО в ОС на этот материал за последний месяц': '',
                        'Позиция': '',
                        '№ERP': '',
                        'Требуемая дата': F.date_add_days(etapes_dates[etap]['нач'], -10, "%Y-%m-%d", "%Y-%m-%d", ),
                        'Этап': etap,
                        'Схема обеспечения': sheme
                    })
            tmp_tbl = dict()
            if rez == []:
                tmp_tbl['ЗП_mail_дозаказ'] = None
            else:
                tmp_tbl['ЗП_mail_дозаказ'] = F.list_of_dicts_to_list_of_lists(rez)
            return tmp_tbl

        if self.type_doc == 1:
            etapes_dates = poz.get_plan_etaps_dates()
            balance = Sclads_balance()
            dict_nomen_sclad= balance.dict_nomen_sclad
            dict_mats_from_order = copy.deepcopy(self.data)
            rez_dict_docs = dict()
            for sclad in balance.LIST_SCLADS:
                name_doc = f'ЗМВП_'+ sclad.replace(' ',"_")
                if name_doc not in rez_dict_docs:
                    rez_dict_docs[name_doc] = dict()
                    for etap in dict_mats_from_order.keys():
                        date = etapes_dates[etap]['нач']
                        if date not in rez_dict_docs[name_doc]:
                            rez_dict_docs[name_doc][date] = dict()
                        for mat in dict_mats_from_order[etap].keys():
                            sclad_by_vid =  DICT_NOMEN[mat]['ИмяСклад']
                            if sclad_by_vid not in dict_nomen_sclad:
                                print(f"Склад {sclad_by_vid} по {DICT_NOMEN[mat]['Наименование']} не обнаружен в Sclads_balance")
                                continue
                            if mat in dict_nomen_sclad[sclad_by_vid]:
                                if mat not in rez_dict_docs[name_doc][date]:
                                    rez_dict_docs[name_doc][date][mat] = 0
                                count_zayav = dict_mats_from_order[etap][mat]
                                count_sclad = dict_nomen_sclad[sclad_by_vid][mat]
                                if count_zayav <= count_sclad:
                                    delta = count_zayav
                                else:
                                    delta = count_zayav- count_sclad
                                rez_dict_docs[name_doc][date][mat] += delta
                                dict_mats_from_order[etap][mat] -= delta
                                dict_nomen_sclad[sclad_by_vid][mat] -= delta



            rez_dict_docs['ЗП'] = []
            for etap in dict_mats_from_order.keys():
                date = etapes_dates[etap]['нач']
                for mat in dict_mats_from_order[etap].keys():
                    rez_dict_docs['ЗП'].append({'Ref_Key':mat,
                                                'Наименование': DICT_NOMEN[mat]['Наименование'],
                                                'Количество':dict_mats_from_order[etap][mat],
                                                'Склад':DICT_NOMEN[mat]['ИмяСклад'],
                                                'Дата':date,
                                                'Этап':etap})
            self.reser_zmvp=  clear_data(rez_dict_docs)
        else:
            self.reser_zmvp = make_tbl_editorder(self,poz)


class Sclads_balance():
    LIST_SCLADS = ['Склад комплектующих Пауэрз', 'Склад материалов Пауэрз']
    def __init__(self):
        m = ERP.OrdersComposit()
        list_nomen_sclad = m.get_ostat_scl(Sclads_balance.LIST_SCLADS)
        dict_nomen_sclad = dict()
        for item in list_nomen_sclad:
            if item['Description'] not in dict_nomen_sclad:
                dict_nomen_sclad[item['Description']] = dict()
            if item['Номенклатура_Key'] not in dict_nomen_sclad[item['Description']]:
                dict_nomen_sclad[item['Description']][item['Номенклатура_Key']] = 0
            dict_nomen_sclad[item['Description']][item['Номенклатура_Key']] += item['ВНаличииBalance']
        self.dict_nomen_sclad= dict_nomen_sclad


class Compare_res():
    def __init__(self, dict_data_or_pnum:dict, l_res,r_res):
        self.list_docs = None
        if isinstance(dict_data_or_pnum,int):
            pass
        else:
            self.data = dict_data_or_pnum
            self.date = F.now()
            self.user = F.user_full_namre()
            rez_docs = {'prof':[],'def':[]}
            for item in dict_data_or_pnum :
                if item['Количество'] >0:
                    rez_docs['prof'].append(item)
                else:
                    rez_docs['def'].append(item)
            self.list_docs = rez_docs

            self.compare_name_left = l_res.s_num
            self.compare_name_right = r_res.s_num
            self.res_r_s_num = r_res.s_num
            self.new_ident = r_res.ident
            self.pozition = l_res.num_kpl



    def get_tbl(self,DICT_NOMEN_KOD ):
        rez = []
        for item in self.data:
            name = 'Не найден в БД'
            mat = item['Код']
            if mat in DICT_NOMEN_KOD:
                name = DICT_NOMEN_KOD[mat]['Наименование']
                kod = DICT_NOMEN_KOD[mat]['Код']
            rez.append({'Этап':item['Этап'], 'Код':kod, 'Наименование':name, 'Количество': item['Количество']})
        return rez

    def get_list_orders(self):
        rez = []
        pozition= self.pozition
        if len(self.list_docs['prof']) > 0:
            rez.append(Doc_order(self.date,self.user,self.compare_name_left,self.compare_name_right,self.list_docs['prof'],'prof',pozition))
        if len(self.list_docs['def']) > 0:
            rez.append(Doc_order(self.date,self.user,self.compare_name_left,self.compare_name_right,self.list_docs['def'],'def',pozition))
        return rez

class Msg_b24():
    # DICT_CHATS = {
    #     'Занесение новых проектов в МЕС':'chat48346',
    #     'Списание_отгрузки Пауэрз на Келаст и ПР продукция Пауэрз':'chat17309',
    #     'Отгрузка на склад':'chat21323',
    #     'готовность РС':'chat58144',
    #     'Готовность Маршрутных карт':'chat41228',
    # }

    DATA_MSG_DICT = {
        'add_new_poz':{'chats':['Занесение новых проектов в МЕС']},
        'recalc_time_technolog':{'chats':['Занесение новых проектов в МЕС']},
        'recalc_dates_disp': {'chats': ['Занесение новых проектов в МЕС']},
        'obtained_kd': {'chats': ['Готовность РКД']}, #26.08.25 по задаче 100058958
        'obtained_kod_res': {'chats': ['Занесение новых проектов в МЕС']},
        'state_valid_kod_res_one': {'chats': ['готовность РС']},
        'state_valid_kod_res_one_wo_py': {'chats': ['готовность РС']},
        'state_valid_kod_res_all': {'chats': ['готовность РС']},
        'state_valid_kod_res_recalc': {'chats': ['Занесение новых проектов в МЕС']},
        'state_poz_for_production': {'chats': ['Занесение новых проектов в МЕС']},
        'check_etaps': {'chats': ['Списание_отгрузки Пауэрз на Келаст и ПР продукция Пауэрз']},
        'fix_name_res': {'chats': ['Готовность Маршрутных карт']},
        'reset_py': {'chats': ['Готовность Маршрутных карт']},
        'upd_fdate_res_erp': {'chats': ['готовность РС']},
    }

    def __init__(self,db_kpl:str,db_naryad:str,db_resxml:str,db_users:str,nom_kpl:int=0,conn = None):
        self.nom_kpl = nom_kpl
        self.data_poz = Pozition(self.nom_kpl,db_kpl, db_naryad, db_resxml, db_users)
        self.data_poz.load_kpl_table('пл_оуп')
        self.data_poz.load_kpl_table('пл_топ')
        self.data_poz.load_kpl_table('пл_ко')
        self.napr_pseudo = self.data_poz.get_napravl()['Псевдоним']
        self.base_name_poz = (f"КПЛ: {self.data_poz.Пномер} Псевдоним {self.napr_pseudo}:  {self.data_poz.dict_tables['пл_оуп']['№проекта']} "
                             f"{self.data_poz.dict_tables['пл_оуп']['№ERP']}, поз.{self.data_poz.Позиция} - "
                              f"{self.data_poz.dict_tables['пл_оуп']['Количество']} шт.)")
        self.state_poz = self.data_poz.get_state_poz_name()
        self.base_dict = OrderedDict([('КПЛ', self.data_poz.Пномер), ('Статус', self.state_poz), ('Псевдоним', self.napr_pseudo),
                                      ('№проекта', self.data_poz.dict_tables['пл_оуп']['№проекта']),
                                      ('№ERP', self.data_poz.dict_tables['пл_оуп']['№ERP']),
                                      ('Поз.', self.data_poz.Позиция),
                                      ('Количество', self.data_poz.dict_tables['пл_оуп']['Количество']) ])

        self.basement_msg ="\n" + r'*схема: https://miro.com/app/board/uXjVKvx6xCU=/?share_link_id=77704755673'

        self.fio = F.user_full_namre()

        self.additional_str = ''

    def send_msg(self,type_msg:str,additional_str='',tbl:list[dict]=None):
        self.additional_str = additional_str
        if type_msg not in Msg_b24.DATA_MSG_DICT:
            raise ValueError("Тип сообщения отсутствует в классе")
        msg_str, form_dict, basement_msg = self.generate_msg(type_msg)
        print(f'{msg_str}\n{form_dict}\n{basement_msg}')
        for chat in Msg_b24.DATA_MSG_DICT[type_msg]['chats']:
            send_info_mk_b24_by_action(msg_str, chat,form_dict=form_dict,basement_msg=basement_msg)
            if tbl:
                send_tbl_b24_by_action('Изменения:',chat,tbl)

    def generate_msg(self,type_msg):
        base_str ='err'
        form_dict = None
        pre_basement = ''
        if type_msg == 'upd_fdate_res_erp':
            base_str = f"""{self.fio} на """
            form_dict = self.base_dict
            pre_basement = f""",после утверждения выгрузки РС, заменил даты [B]{self.additional_str}[/B]."""
        if type_msg == 'reset_py':
            base_str = f"""{self.fio} на """
            form_dict = self.base_dict
            pre_basement = f"""установил номер ЗП ЕРП [B]`{self.additional_str}`[/B] необходимо открыть МК и сделать раскладку"""
        if type_msg == 'add_new_poz':#trigger: kal_plan.btn_pl_ok_add_poz_click
            base_str = f"""{self.fio} Добавил в план новую позицию в статусе "{self.state_poz}"."""
            form_dict = self.base_dict
            pre_basement = f"""Технологу ТОП необходимо указать пл_топ.Уд_вес_ВО, пл_топ.Вид, пл_топ.Предв_спецификация_ЕРП."""
        if type_msg == 'recalc_time_technolog':#trigger: kal_plan.btn_pl_ok_add_poz_click
            base_str = f"""{self.fio} указал "пл_топ.Вид" на позицию"""
            form_dict = self.base_dict
            pre_basement = f"""Технологу ТОП Необходимо пересчитать нормы времени."""
        if type_msg == 'recalc_dates_disp':#trigger: kal_plan.btn_pl_load_norm
            base_str = f"""{self.fio} пересчитал нормы времени на позицию"""
            form_dict = self.base_dict
            pre_basement = f'''специалисту ПДО необходимо обновить гант и переопределить даты исполнения позиции.'''
        if type_msg == 'obtained_kd':#trigger: kal_plan.btn_pl_ok_add_poz_click
            base_str = f"""{self.fio} отметил, что получено КД на позицию В статусе: {self.state_poz!r}"""
            form_dict = self.base_dict
            pre_basement = f"""ТОП необходимо разработать ТД, МК, РС \nссылка на папку: 
                {path_to_proj_NPPY_c(self.data_poz.dict_tables['пл_оуп']['№проекта'],self.data_poz.dict_tables['пл_оуп']['№ERP'])}
            ссылка на КД: 
                {self.data_poz.dict_tables['пл_ко']['Ссылка_КД']}"""#вывод ссылка на папку ()#вывод ссылка на КД

        if type_msg == 'obtained_kod_res':#trigger: kal_plan.btn_pl_ok_add_poz_click
            base_str = f"""{self.fio} указал пл_топ.Спецификация_код_ЕРП на позицию"""
            form_dict = self.base_dict
            pre_basement = f"""Специалисту ФЭО необходимо согласовать ресурсную {self.data_poz.dict_tables['пл_топ']['Спецификация_код_ЕРП']}"""

        if type_msg == 'state_valid_kod_res_one':#trigger: reiting.check_and_calc_plan_kpl
            base_str = f"""Ресурсная {self.data_poz.dict_tables['пл_топ']['Спецификация_код_ЕРП']} 
                {self.data_poz.dict_tables['пл_топ']['Спецификация_ЕРП']} переведена в статус `Действует`"""
            form_dict = self.base_dict
            pre_basement = f"""Нужно к номенклатуре "{self.data_poz.dict_tables['пл_оуп']['Номенклатура_ЕРП']}" установить ресурсную и
                "{self.data_poz.dict_tables['пл_топ']['Спецификация_ЕРП']}"\nпо ЗП осталось :{self.additional_str}"""

        if type_msg == 'state_valid_kod_res_one_wo_py':#trigger: reiting.check_and_calc_plan_kpl
            base_str = f"""Ресурсная {self.data_poz.dict_tables['пл_топ']['Спецификация_код_ЕРП']} 
                {self.data_poz.dict_tables['пл_топ']['Спецификация_ЕРП']} переведена в статус `Действует`"""
            form_dict = self.base_dict
            pre_basement = f"""Нужно к номенклатуре "{self.data_poz.dict_tables['пл_оуп']['Номенклатура_ЕРП']}" установить ресурсную и
                "{self.data_poz.dict_tables['пл_топ']['Спецификация_ЕРП']}"\nзаказ на производство к позиции [B]НЕ УСТАНОВЛЕН[/B], необходимо установить в пл_оуп."""

        if type_msg == 'state_valid_kod_res_all':#trigger: reiting.check_and_calc_plan_kpl
            base_str = f"""Ресурсная {self.data_poz.dict_tables['пл_топ']['Спецификация_код_ЕРП']} 
{self.data_poz.dict_tables['пл_топ']['Спецификация_ЕРП']} переведена в статус `Действует`"""
            form_dict = self.base_dict
            pre_basement = f"""Нужно к номенклатуре "{self.data_poz.dict_tables['пл_оуп']['Номенклатура_ЕРП']}" установить ресурсную и
"{self.data_poz.dict_tables['пл_топ']['Спецификация_ЕРП']}"\n проверить ЗП и выставить статус "К производству")"""

        if type_msg == 'state_valid_kod_res_recalc':#trigger: reiting.check_and_calc_plan_kpl
            base_str = f"""Ресурсная {self.data_poz.dict_tables['пл_топ']['Спецификация_код_ЕРП']} 
{self.data_poz.dict_tables['пл_топ']['Спецификация_ЕРП']} переведена в статус `Действует`"""
            form_dict = self.base_dict
            pre_basement = f"""Технологу необходимо пересчитать нормы, специалисту ПДО сроки"""

        if type_msg == 'state_poz_for_production':#trigger: reiting.check_and_calc_plan_kpl
            base_str = f"""В ЗП выставлен статус "К производству" """
            form_dict = self.base_dict
            pre_basement = f"""Специалисту ПДО нужно создать этапы"""

        if type_msg == 'check_etaps':#trigger:
            base_str = f"""Этапы созданы."""
            form_dict = self.base_dict
            pre_basement = f"""Ответственным по этапам проверить наличие материалов"""

        if type_msg == 'fix_name_res':
            base_str = f"""{self.additional_str}"""
            form_dict = self.base_dict



        if pre_basement:
            basement_msg = f'{pre_basement}\n{self.basement_msg}'
        else:
            basement_msg = self.basement_msg
        return base_str, form_dict, basement_msg


class Materials_erp_arm():
    shabl = ['Код', 'Количество','Этап']
    @classmethod
    def check_hat(cls,tbl):

        for name in cls.shabl:
            if name not in tbl[0]:
                print(f'{name} not found in tbl')
                return False
        return True

    @staticmethod
    def get_hat_res(kod:str):
        kod = kod.replace('\n','').strip()
        m = ERP.OrdersComposit()
        res = m.get_response(doc_name="Catalog_РесурсныеСпецификации",
                             wet_filtr=f"?$filter=Code eq '{kod}' &$select=ИдентификаторВерсииДанных,Статус,Description")
        if res == []:
            CQT.msgbox(f'{kod} ресурсная не найдена в ЕРП' )
            return dict()
        ident = res[0]['ИдентификаторВерсииДанных']  # TODO add to the db res
        status = res[0]['Статус']
        if status != 'Действует':
            print(f"status != 'Действует'")
            return
        name = res[0]['Description']
        return {"name":name,"status":status,"ident":ident}

    def __init__(self,path,db_kpl=None,num_kpl=None,num_kod_res=None):
        self.err = False
        self.tbl_data = None
        self.ident = None
        self.data = dict()
        if isinstance(path,str):
            if num_kpl == None:
                print(f'num_kpl == None')
                self.err = True
                return
            if F.sep() in path: # ================================FROM TXT
                #=============== OFF========================
                data_set = F.open_file_c(path, True)
                tbl = [_.split('\t') for _ in data_set]
                if not self.check_hat(tbl):
                    print('ERROR FILE TYPE')
                    self.err = True
                    return
                if num_kod_res == None:
                    print('ERROR num_kod_res')
                    self.err = True
                    return
                new_dict = dict()
                tbl = F.list_of_lists_to_list_of_dicts(tbl)
                for item in tbl:
                    etap = item['Этап']
                    kod = item['Код']
                    val = F.valm(item['Количество'])
                    if etap not in new_dict:
                        new_dict[etap] = dict()
                    if kod not in new_dict[etap]:
                        new_dict[etap][kod] = {'Количество': 0}
                    new_dict[etap][kod]['Количество'] += val
                self.data = new_dict
                self.date_ver = F.now()
                self.num_kpl = num_kpl
                self.s_num = None
                self.active = 0
                self.user = F.user_full_namre()
                self.primech = ''

                hat = Materials_erp_arm.get_hat_res(num_kod_res)
                self.ident = hat['ident']
            else: # ================================FROM 1C
                m = ERP.OrdersComposit()
                kod = path.replace('\n','').strip()
                new_dict = dict()
                res = m.get_response(doc_name="Catalog_РесурсныеСпецификации",
                                     wet_filtr=f"?$filter=Code eq '{kod}' &$select=ИдентификаторВерсииДанных,Статус,Description,"
                                               f"МатериалыИУслуги/КоличествоУпаковок,МатериалыИУслуги/Номенклатура_Key,МатериалыИУслуги/Этап_Key")
                ident = res[0]['ИдентификаторВерсииДанных']# TODO add to the db res
                status = res[0]['Статус']
                if status != 'Действует':
                    print(f"status != 'Действует'")
                    self.err=True
                    return
                name = res[0]['Description']
                data = dict()
                for item in res[0]['МатериалыИУслуги']:
                    val = item['КоличествоУпаковок']
                    etap = 'err'
                    data_etap = m.get_etap_ref(item['Этап_Key'])
                    if data_etap != None and data_etap != []:
                        etap = data_etap['Description']
                    kod = item['Номенклатура_Key']
                    if etap not in new_dict:
                        new_dict[etap] = dict()
                    if kod not in new_dict[etap]:
                        new_dict[etap][kod] = {'Количество': 0}
                    new_dict[etap][kod]['Количество'] += val
                self.data = new_dict
                self.date_ver = F.now()
                self.num_kpl = num_kpl
                self.s_num = None
                self.active = 0
                self.user = F.user_full_namre()
                self.primech = ''
                self.ident = ident

        else:  # ================================FROM DB

            if db_kpl == None:
                print(f'ERR db_kpl --- NONE')
                return

            self.s_num = path

            if path == 0:
                if num_kpl == None:
                    print(f'num_kpl == None')
                    self.err = True
                    return
                self.s_num = path
                self.data = dict()
                self.num_kpl = num_kpl

                return
            dict_res = self.load_db(path,db_kpl)
            self.data = dict_res['data']
            self.date_ver = dict_res['date_version']
            self.num_kpl = dict_res['num_kpl']
            self.active = dict_res['active']
            self.user = dict_res['user']

            self.primech = dict_res['primech']
            self.ident = dict_res['ИдентификаторВерсииРесурсной']
        self.get_table_form_from_data()
        #self.check_make_zero_res(db_kpl) = OFF

    def add_order(self,order):
        for etap in order.data.keys():
            if etap not in self.data:
                self.data[etap] = dict()
            for kod in order.data[etap].keys():
                if kod not in self.data[etap]:
                    self.data[etap][kod] = {'Количество':0}
                self.data[etap][kod]['Количество'] += order.data[etap][kod]


    def in_db(self,db_kpl):
        rez = CSQ.custom_request_c(db_kpl, f"""SELECT s_num, 
        ИдентификаторВерсииРесурсной FROM versions_res_mat WHERE ИдентификаторВерсииРесурсной = '{self.ident}';""",
                                   rez_dict=True)
        if len(rez) > 0:
            return True
        return False


    def check_make_zero_res(self,db_kpl):
        rez = CSQ.custom_request_c(db_kpl,f"""SELECT s_num, num_kpl FROM versions_res_mat WHERE s_num = 0;""",rez_dict=True)
        if len(rez)>0:
            return
        bin_file = F.to_binary_pickle(dict())
        packed = F.pack_byte_file(bin_file)
        tmp_list = [0, '2020-01-01 13:05:56', packed, 'user', 'ident']
        CSQ.custom_request_c(db_kpl, f"""INSERT INTO versions_res_mat 
                 (num_kpl,date_version,data,user,ИдентификаторВерсииРесурсной) 
                                      VALUES (?,?,?,?,?) """, list_of_lists_c=[tmp_list])

    def delete(self,db_kpl):
        if self.s_num == None:
            CQT.msgbox(f'Materials_erp_arm.dele  -  obj not loaded')
        CSQ.custom_request_c(db_kpl,f"DELETE FROM versions_res_mat WHERE s_num = {self.s_num};")

    def compare_with(self,right_res) -> Compare_res:
        rez = dict()
        for item_r in right_res.data:
            if item_r not in rez:
                rez[item_r] = dict()
            for mat in right_res.data[item_r]:
                if mat not in rez[item_r]:
                    rez[item_r][mat] = {'Левая рес': 0, 'Правая рес': 0, 'Разница': 0}
                rez[item_r][mat]['Правая рес'] += right_res.data[item_r][mat]['Количество']
        for item_l in self.data:
            if item_l not in rez:
                rez[item_l] = dict()
            for mat in self.data[item_l]:
                if mat not in rez[item_l]:
                    rez[item_l][mat] = {'Левая рес': 0, 'Правая рес': 0, 'Разница': 0}
                rez[item_l][mat]['Левая рес'] += self.data[item_l][mat]['Количество']
        rez_tbl = []
        for etap in rez:
            for mat in rez[etap]:
                if rez[etap][mat]['Правая рес'] != rez[etap][mat]['Левая рес']:
                    rez_tbl.append({'Этап': etap, 'Код': mat,
                                    'Количество': rez[etap][mat]['Правая рес'] - rez[etap][mat]['Левая рес']})


        obj_docs = Compare_res(rez_tbl,self ,right_res)
        return obj_docs


    def get_table_form_from_data(self):
        rez = []
        for etap in self.data:
            for kod in self.data[etap]:
                rez.append({'Код':kod,'Этап':etap,'Количество':self.data[etap][kod]})
        self.data_tbl = rez

    def make_tbl(self,dict_nomen):
        rez = []
        for etap in self.data.keys():
            item = self.data[etap]
            for kod_ref in item:
                nomen = 'Не найдена в БД'
                if kod_ref in dict_nomen:
                    kod = dict_nomen[kod_ref]['Код']
                    if dict_nomen[kod_ref]['На_удаление'] == 1:
                        nomen = 'На_удаление'
                    else:
                        nomen = dict_nomen[kod_ref]['Наименование']
                rez.append({'Этап':etap,'Код':kod,'Наименование':nomen, 'Количество':item[kod_ref]['Количество']})
        self.tbl_data = rez


    @staticmethod
    def load_db(s_num,db_kpl):
        dict_res = CSQ.custom_request_c(db_kpl,f"""SELECT * FROM versions_res_mat WHERE s_num ={s_num}""",rez_dict=True,one=True)
        dict_res['data'] = F.from_binary_pickle(F.unpack_byte_file(dict_res['data']))
        return dict_res


    def add_db(self,db_kpl):
        bin_file = F.to_binary_pickle(self.data)
        packed = F.pack_byte_file(bin_file)
        tmp_list = [self.num_kpl,self.date_ver,packed,self.user,self.ident]
        CSQ.custom_request_c(db_kpl,f"""INSERT INTO versions_res_mat 
         (num_kpl, date_version,data,user,ИдентификаторВерсииРесурсной) 
                              VALUES ({CSQ.questions_for_mask(tmp_list)}) """,list_of_lists_c=[tmp_list])
        dict_s_num =  CSQ.custom_request_c(db_kpl,f"""SELECT s_num, num_kpl FROM 
         versions_res_mat WHERE date_version = '{self.date_ver}' AND num_kpl = {self.num_kpl};""",rez_dict=True,one=True)
        self.s_num = dict_s_num['s_num']


class Zakaz_postavshiky:
    db = CFG.Config.project.db_kplan
    def __init__(self,num_erp:str,year:int):
        self.db = Zakaz_postavshiky.db
        self.s_num = None
        self.num_erp = None
        self.year = None
        self.Ref_Key = None
        row = CSQ.custom_request_c(self.db,f"""SELECT * FROM зп_абстракт WHERE num_erp = "{num_erp}" and year = {year};""",rez_dict=True,one=True)
        if row == None or row == False:
            return
        for key in row.keys():
            exec(f'self.{str(key).replace(".", "_")} = row[key]')

    @classmethod
    def add_new_zp(cls,Ref_Key:str,num_erp:str,date:datetime.datetime):
        year = date.year
        trying_row = CSQ.custom_request_c(cls.db,f"""SELECT * FROM зп_абстракт WHERE Ref_Key = "{Ref_Key}";""",rez_dict=True,one=True)
        if trying_row:
            pass
        else:
            rez = CSQ.custom_request_c(cls.db,f"""INSERT INTO зп_абстракт (num_erp, year, Ref_Key) VALUES (?, ?, ?);""",list_of_lists_c=[[num_erp,year,Ref_Key]])
        return cls(num_erp, year)


class Zp_kpl:
    db = CFG.Config.project.db_kplan
    def __init__(self,parent_self):
        self.parent_self = parent_self
        self.db = Zp_kpl.db

    def get_custom_compliance_etaps(self,num_kpl:int,DICT_GROUP_VID_RAB_FOR_PLAN:dict=None):

        data  = CSQ.custom_request_c(self.db, f"""SELECT 
                    зп_абстракт.s_num,
                зп_абстракт.custom_compliance_etaps as compliance_blob
                 FROM сопост_кпл_зп 
                 INNER JOIN 
                 зп_абстракт ON зп_абстракт.s_num == сопост_кпл_зп.zp_num,   
                 plan on plan.Пномер == сопост_кпл_зп.kpl_num 
                 WHERE сопост_кпл_зп.kpl_num = {num_kpl} and plan.poki = {CFG.Config.place.poki};""", rez_dict=True)
        result = []
        for item in data:
            if item['compliance_blob']:
                item['custom_compliance_etaps'] = F.from_binary_pickle(item['compliance_blob'])
                if item['custom_compliance_etaps']:
    
                    if DICT_GROUP_VID_RAB_FOR_PLAN:
                        for mat, etap in item['custom_compliance_etaps'].items():
                            if etap not in DICT_GROUP_VID_RAB_FOR_PLAN:
                                self.set_custom_compliance_etaps(item['s_num'],mat,None)
                    result.append({'s_num':item['s_num'],'custom_compliance_etaps': item['custom_compliance_etaps']})
        data = F.deploy_dict_c(result,'s_num')
        return data

    def set_custom_compliance_etaps(self,s_num_зп_абстракт:int,cod_mat:str,name_etap_kpl:str|None):
        data = CSQ.custom_request_c(self.db, f"""SELECT 
                        s_num,    
                        custom_compliance_etaps as compliance_blob
                         FROM зп_абстракт 
                         
                         WHERE s_num = {s_num_зп_абстракт};""",
                                    rez_dict=True,one=True)
        data_obj = F.from_binary_pickle(data['compliance_blob'])
        if data_obj == None:
            data_obj = dict()
        if name_etap_kpl == None:
            data_obj.pop(cod_mat, None)
        else:
            data_obj[cod_mat] = name_etap_kpl
        data_blob = F.to_binary_pickle(data_obj)
        CSQ.custom_request_c(self.db,f"""UPDATE зп_абстракт SET  (custom_compliance_etaps)
                        = (?) WHERE s_num = {s_num_зп_абстракт};""",list_of_lists_c=[[data_blob]])

    def get_custom_ignore_maters(self,num_kpl:int):
        data  = CSQ.custom_request_c(self.db, f"""SELECT 
                    зп_абстракт.s_num,
                зп_абстракт.custom_ignore_maters as ignore_blob
                 FROM сопост_кпл_зп 
                 INNER JOIN 
                 зп_абстракт ON зп_абстракт.s_num == сопост_кпл_зп.zp_num,   
                 plan on plan.Пномер == сопост_кпл_зп.kpl_num 
                 WHERE сопост_кпл_зп.kpl_num = {num_kpl} and plan.poki = {CFG.Config.place.poki};""", rez_dict=True)
        result = []
        for item in data:
            if item['ignore_blob']:
                item['custom_ignore_maters'] = F.from_binary_pickle(item['ignore_blob'])
                if item['custom_ignore_maters']:
                    result.append({'s_num':item['s_num'],'custom_ignore_maters': item['custom_ignore_maters']})
        data = F.deploy_dict_c(result,'s_num')
        return data

    def set_custom_ignore_maters(self, s_num_зп_абстракт: int, cod_mat: str, num_kpl: int, delete=False):
        data = CSQ.custom_request_c(self.db, f"""SELECT 
                        s_num,    
                        custom_ignore_maters as ignore_blob
                         FROM зп_абстракт 

                         WHERE s_num = {s_num_зп_абстракт};""",
                                    rez_dict=True, one=True)
        data_obj = F.from_binary_pickle(data['ignore_blob'])
        if data_obj == None:
            data_obj = dict()

        if num_kpl not in data_obj:
            data_obj[num_kpl] = set()
        if delete:
            data_obj[num_kpl].discard(cod_mat)
        else:
            data_obj[num_kpl].add(cod_mat)

        data_blob = F.to_binary_pickle(data_obj)
        CSQ.custom_request_c(self.db, f"""UPDATE зп_абстракт SET  (custom_ignore_maters)
                        = (?) WHERE s_num = {s_num_зп_абстракт};""", list_of_lists_c=[[data_blob]])

    def get_list_refs(self,num_kpl:int):
        return  CSQ.custom_request_c(self.db,f"""SELECT 
        зп_абстракт.Ref_Key as Ref_Key
         FROM сопост_кпл_зп 
         INNER JOIN 
         зп_абстракт ON зп_абстракт.s_num == сопост_кпл_зп.zp_num,   
         plan on plan.Пномер == сопост_кпл_зп.kpl_num 
         WHERE сопост_кпл_зп.kpl_num = {num_kpl} and plan.poki = {CFG.Config.place.poki};""",one_column=True,hat_c=False)

    def del_compliance(self,s_num:int):
        rez = CSQ.custom_request_c(self.db, f"""DELETE FROM сопост_кпл_зп WHERE s_num = {s_num};""")
        return rez

    def add_compliance(self,num_kpl:int,list_nums_zp:[Zakaz_postavshiky]):
        if len(list_nums_zp)==0:
            return True
        list_to_add = []
        for zp in list_nums_zp:
            list_to_add.append(zp.s_num)

        old_list = CSQ.custom_request_c(self.db,f"""SELECT kpl_num FROM сопост_кпл_зп WHERE kpl_num == {num_kpl};""",hat_c=False,one_column=True)
        delta = list(set(list_to_add) - set(old_list))

        list_to_add = []
        for zp in delta:
            list_to_add.append([num_kpl,zp])
        rez = True
        if len(list_to_add):
            rez = CSQ.custom_request_c(self.db,f"""INSERT INTO сопост_кпл_зп (kpl_num, zp_num) VALUES (?, ?)""", list_of_lists_c=list_to_add)
        return rez

    def get_all(self):
        return CSQ.custom_request_c(self.db,f"""SELECT 
        сопост_кпл_зп.s_num as s_num, 
        сопост_кпл_зп.kpl_num as КПЛ, 
        зп_абстракт.num_erp as "Номер ЗП", 
        зп_абстракт.year as Год , 
        зп_абстракт.Ref_Key as Ref_Key
         FROM сопост_кпл_зп 
         INNER JOIN 
         зп_абстракт ON зп_абстракт.s_num == сопост_кпл_зп.zp_num,
         plan on plan.Пномер == сопост_кпл_зп.kpl_num
         WHERE plan.poki = {CFG.Config.place.poki} """)

    def get_by_kpl(self,kpl:int):
        return CSQ.custom_request_c(self.db,f"""SELECT 
        сопост_кпл_зп.s_num as s_num, 
        зп_абстракт.s_num as s_num_zp, 
        сопост_кпл_зп.kpl_num as КПЛ, 
        зп_абстракт.num_erp as "Номер ЗП", 
        зп_абстракт.year as Год , 
        зп_абстракт.Ref_Key as Ref_Key_зп_абстракт
         FROM сопост_кпл_зп 
         INNER JOIN 
         зп_абстракт ON зп_абстракт.s_num == сопост_кпл_зп.zp_num,
         plan on plan.Пномер == сопост_кпл_зп.kpl_num
         WHERE plan.poki = {CFG.Config.place.poki} and сопост_кпл_зп.kpl_num = {kpl} """)



class Plan_custom_weekends():
    db_kplan = CFG.Config.project.db_kplan
    current_pnom_kplan_select:int = None
    current_dict_weekends:dict|None = None

    def __init__(self,snum_kplan:int):
        Plan_custom_weekends.current_pnom_kplan_select = snum_kplan
        self._get_dict_weekends()

    def is_weekend(self,day:datetime.datetime):
        if day not in Plan_custom_weekends.current_dict_weekends:
            return None
        if Plan_custom_weekends.current_dict_weekends[day] == 1:
            return True
        else:
            return  False

    def _get_dict_weekends(self)-> dict:

        dict_weekends = CSQ.custom_request_c(self.db_kplan, f"""SELECT fact_jurnal_blolb_weekends FROM plan 
                        WHERE Пномер = {Plan_custom_weekends.current_pnom_kplan_select}""", one_column=True, one=True, hat_c=False)
        if dict_weekends == False: #11.11.25
            raise ConnectionError(f'ОШибка получения данных')
            return
        if dict_weekends == '':
            dict_weekends = dict()
        else:
            dict_weekends = F.from_binary_pickle(dict_weekends)
            if dict_weekends == None:
                dict_weekends = dict()
        Plan_custom_weekends.current_dict_weekends  = dict_weekends


    def get_list_weekends(self)->list:
        list_days_oform = [F.datetostr(_,"%Y-%m-%d") for _ in Plan_custom_weekends.current_dict_weekends]
        list_days_oform.sort()
        list_days_oform.insert(0,'Не рабочие дни')
        return list_days_oform


    def del_days(self,set_days:{datetime.datetime}):
        for day in set_days:
            Plan_custom_weekends.current_dict_weekends.pop(day,None)
        self._save()


    def add_days(self, set_days: {datetime.datetime}):
        for day in set_days:
            Plan_custom_weekends.current_dict_weekends[day] = 1
        self._save()


    def _save(self):
        CSQ.custom_request_c(self.db_kplan, f"""UPDATE plan SET (fact_jurnal_blolb_weekends) = 
                            (?) WHERE Пномер = ?""", list_of_lists_c=[
            [F.to_binary_pickle(Plan_custom_weekends.current_dict_weekends),
             Plan_custom_weekends.current_pnom_kplan_select]])

class DocumentedVariables():
    def __init__(self,сontext:str):
        self.сontext = сontext
        data = CSQ.custom_request_c(CFG.Config.project.db_dse, f"""SELECT 
               ПараметрыФормул.Наименование, 
               ПараметрыФормул.Подгруппа, 
               ПараметрыФормул.БуквенноеОбозначение , 
               ЕдиницыИзмерения.Наименование as ЕдиницаИзмерения, 
               ПараметрыФормул.Мин, 
               ПараметрыФормул.Макс, 
               ПараметрыФормул.Default_val, 
               ПараметрыФормул.ТипДанных, 
               ПараметрыФормул.КоличествоРазрядов, 
               ПараметрыФормул.Описание, 
               ПараметрыФормул.Видимый,
               ПараметрыФормул.Этап,
               molding_order_stages.emoji as emoji,
               ПараметрыФормул.editable,
               ПараметрыФормул.allowedNullAndEmpty as РазрешенНульИПусто
               FROM ПараметрыФормул 
               LEFT JOIN ЕдиницыИзмерения ON ЕдиницыИзмерения.refKey =  ПараметрыФормул.ЕдиницаИзмерения 
               LEFT JOIN molding_order_stages ON molding_order_stages.s_num =  ПараметрыФормул.Этап  
               WHERE ПараметрыФормул.Контекст = '{сontext}' and ПараметрыФормул.disabled = 0 order by orderf;""", rez_dict=True)
        self.dict_vars = {_['Наименование']:DocumentedVariable(_) for _ in data}
    def __repr__(self):
        return f'cls DocumentedVariables, сontext: "{self.сontext}": {len(self.dict_vars)} items'

    def apply_alias_list(self, list_resp):
        dict_alias = {k:v.БуквенноеОбозначение for k,v in self.dict_vars.items()}
        if list_resp == []:
            return list_resp
        result = copy.deepcopy(list_resp)
        if isinstance(result[0], dict):
            for i in range(len(result)):
                new_dict = dict()
                for k,v in result[i].items():
                    if k in dict_alias:
                        new_dict[dict_alias[k]]=v
                    else:
                        #print(f'CMS.apply_alias_list err not found alias for {k}')
                        new_dict[k] = v
                result[i] = new_dict
        else:
            for i in range(len(result)):
                for j in range(len(result[i])):
                    fl_found = False
                    if result[i][j] in dict_alias:
                        result[i][j] = dict_alias[result[i][j]]
                        fl_found = True
                    if not fl_found:
                        print(f'CMS.apply_alias_list err not found alias for {result[i][j]}')
        return result
    def get_name_by_alias(self,alias):
        for name, data in self.dict_vars.items():
            if data.БуквенноеОбозначение == alias:
                return name

class DocumentedVariable():
    def __init__(self,row:dict):
        self.Наименование:str = None
        self.Подгруппа:str = None
        self.БуквенноеОбозначение:str = None
        self.ЕдиницаИзмерения:str|None = None
        self.Мин:float|int|None = None
        self.Макс:float|int|None = None
        self.Default_val:float|str|int = None
        self.ТипДанных:str|type = None
        self.КоличествоРазрядов:int|None = None
        self.Описание:str|None = None
        self.Видимый:int|None = None
        self.Этап:int|None = None
        self.editable:int|None = None
        self.РазрешенНульИПусто: int | None = None
        self.emoji: str | None = ''
        for key in row.keys():
            exec(f'self.{str(key).replace(".", "_")} = row[key]')
        self.is_numeric =False
        if self.ТипДанных in ('int','float'):
            self.is_numeric = True
        self.ТипДанных = eval(self.ТипДанных)
        self.БуквенноеОбозначение = self.БуквенноеОбозначение.replace(r'\n','\n')

    def __repr__(self):
        return f'cls DocumentedVariable, "{self.БуквенноеОбозначение}: {self.ТипДанных}", '


class ResOper():
    def __init__(self, parent:ResDse, wet_data_row:dict):
        self.parent:ResDse = parent
        self.Этап :str|None = None
        self.Опер_наименование:str|None = None
        self.Опер_код:str|None = None
        self.Опер_вспомогательная:bool|None = None
        self.Опер_номер:str|None = None
        self.Опер_РЦ_наименование:str|None = None
        self.Опер_РЦ_код:str|None = None
        self.Опер_наименование_подразделения:str|None = None
        self.Опер_оборудование_наименование:str|None = None
        self.Опер_оборудование_код:str|None = None
        self.Опер_Тпз:float|None = None
        self.Опер_Тшт:float|None = None
        self.Опер_Тшт_ед:float|None = None
        self.Опер_профессия_наименование:str|None = None
        self.Опер_профессия_код:str|None = None
        self.Опер_КР:int|None = None
        self.Опер_КОИД:int|None = None
        self.Опер_документы:list|None = None
        self.Опер_инстумент:list|None = None
        self.Опер_оснастка:list|None = None
        self.Материалы:list|None = None
        self.Переходы:list|None = None
        for key in wet_data_row.keys():
            if key not in ('Освоено,шт.','Закрыто,шт.'):
                exec(f'self.{str(key).replace(".", "_").replace(" ", "")} = wet_data_row[key]')

        self.Освоено :int = wet_data_row['Освоено,шт.']
        self.Закрыто :int = wet_data_row['Закрыто,шт.']

    def __str__(self):
        return f'{self.Опер_номер}, {self.Опер_код} {self.Опер_наименование} - ({self.Опер_Тпз},{self.Опер_Тшт}) на {self.parent.parent.count} изд. '


class ResDse():

    def __init__(self,parent:ResSpec, wet_data_row:dict):
        self.parent: ResSpec = parent
        self.Номерпп:int|None = None
        self.Наименование:str|None = None
        self.Номенклатурный_номер:str|None = None
        self.Код_ERP:str|None = None


        self.Количество:int|None = None
        self.Количество_ед:int|None = None
        self.Уровень:int|None = None
        
        self.Параметрика:dict|None = None
        self.Документы:list|None = None
        self.ПКИ:str|None = None
        self.Мат_кд:str|None = None
        self.Ссылка:str|None = None
        self.Прим:str|None = None
        self.dreva_kod:str|None = None
        self.Способы_получения_материала:str|None = None
        self.кол_во_инф:dict|None = None
        
        if wet_data_row['Код ERP'] == '':
            self.Код_ERP = wet_data_row['Код_ERP']
        else:
            self.Код_ERP = wet_data_row['Код ERP']
        
        
        self.Операции = [ResOper(self,_) for _ in wet_data_row['Операции']]
        for key in wet_data_row.keys():
            if key not in ('Операции','Код_ERP','Код ERP',):
                exec(f'self.{str(key).replace(".", "_").replace(" ", "")} = wet_data_row[key]')

    def __str__(self):
        return f'N {self.Номерпп}, {self.Наименование} {self.Номенклатурный_номер} - {self.Количество} шт.'


class ResSpec():
    def __init__(self,num_mk:int):
        self._wet_data = load_res(num_mk, db_resxml=CFG.Config.project.db_resxml)
        
        self.DICT_PROF_BY_COD:dict[dict] = F.deploy_dict_c(CSQ.custom_request_c(CFG.Config.project.db_users, 
                         """SELECT * 
                         
                         FROM professions LEFT JOIN vid_rab_po_dolg ON professions.вид_работ = vid_rab_po_dolg.Вид_работ""",
                                                                     rez_dict=True),
                                                'код')
        self.data:list[ResDse] = [ResDse(self,_) for _ in self._wet_data]
        self.count = self.data[0].Количество
        self.mk:Marshrut_cards = Marshrut_cards(num_mk,CFG.Config.project.db_naryad,CFG.Config.project.db_resxml,
                                                False)

    def get_vids_rab(self,key_ref=False)->dict:
        dict_res = dict()
        for dse in self.data:
            for oper in dse.Операции:
                if oper.Опер_профессия_код in self.DICT_PROF_BY_COD:
                    ref_Key_erp = self.DICT_PROF_BY_COD[oper.Опер_профессия_код]['ref_Key_erp']
                    if ref_Key_erp is None:
                        continue
                    if key_ref:
                        vid_rab = ref_Key_erp
                    else:
                        vid_rab = self.DICT_PROF_BY_COD[oper.Опер_профессия_код]['вид_работ']
                    if vid_rab not in dict_res:
                        dict_res[vid_rab] = 0
                    dict_res[vid_rab] += (
                            (oper.Опер_Тпз + oper.Опер_Тшт/ oper.Опер_КОИД ) / self.count )
                    
                    

        dict_res = {k:round(v,3) for k,v in dict_res.items()}
        return dict_res

    def compare_vids_rab(self, name_key: str, right: dict[str, float], left_name: str, right_name: str,
                         result_key_ref:bool=False,sensitivity:int=2)->list[dict]:
        """сравнивает два словаря и возвращает список различий, отсортированный по ключу"""
        left = self.get_vids_rab(key_ref=True)
        all_keys = sorted(set(left) | set(right))
        result = []
        for k in all_keys:
            l_val = left.get(k, 0)
            r_val = right.get(k, 0)
            if round(l_val,sensitivity)  != round(r_val,sensitivity):
                key_val = k
                if result_key_ref:
                    key_val = k
                else:
                    key_val = self._ref_vid_rab_into_name(k)
                result.append({
                    name_key: key_val,
                    left_name: l_val,
                    right_name: r_val,
                })
        return result

    def _ref_vid_rab_into_name(self,ref):
        for kod, item in self.DICT_PROF_BY_COD.items():
            if item['ref_Key_erp'] == ref:
                return item['вид_работ']

    def find_erp_res(self,num_kpl:int=None)-> list[ResSpecERP]:
        if num_kpl is None:
            num_kpl = self.mk.НомКплан
        wet_req_text = f"""ВЫБРАТЬ
                РесурсныеСпецификации.Описание КАК Описание,
                РесурсныеСпецификации.Код КАК Код,
                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Ссылка)) КАК refKey,
                РесурсныеСпецификации.Наименование КАК Наименование,
                РесурсныеСпецификации.Статус КАК Статус,
                РесурсныеСпецификации.НачалоДействия КАК НачалоДействия,
                РесурсныеСпецификации.КонецДействия КАК КонецДействия
            ИЗ
                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
            ГДЕ
                РесурсныеСпецификации.Статус <> ЗНАЧЕНИЕ(Перечисление.СтатусыСпецификаций.Закрыта)
                И РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
                И РесурсныеСпецификации.НачалоДействия < ДАТАВРЕМЯ(2025, 10, 21, 0, 0, 0)
                И РесурсныеСпецификации.КонецДействия > ДАТАВРЕМЯ(2025, 10, 21, 0, 0, 0)
                И (ВЫРАЗИТЬ(РесурсныеСпецификации.Описание КАК СТРОКА(15))) = "Номер проекта: "
                                                ;"""
        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            print(f'find_erp_res Ошибка получения данных код ({key}) из ERP')

        res=[]
        for item in data_rez['data']:
            if 'Номер КПЛ' in item['Описание']:
                dict_Описание = ResSpecERP.dict_description(item['Описание'])
                if 'Номер КПЛ' in dict_Описание:
                    kpl = dict_Описание['Номер КПЛ']
                    if F.is_numeric(kpl) and int(kpl) == self.mk.НомКплан:
                        res.append(ResSpecERP(item['refKey']))
        return res



class TchResSpecERP():
    def __init__(self,name):
        self.name: str = name
        self.data: list[dict]|None = None

class TchNamesResSpecERP():
    ВозвратныеОтходы: TchResSpecERP = TchResSpecERP('ВозвратныеОтходы')
    МатериалыИУслуги: TchResSpecERP = TchResSpecERP('МатериалыИУслуги')
    Трудозатраты: TchResSpecERP = TchResSpecERP('Трудозатраты')
    СоответствиеСвойств: TchResSpecERP = TchResSpecERP('СоответствиеСвойств')
    ДополнительныеРеквизиты: TchResSpecERP = TchResSpecERP('ДополнительныеРеквизиты')
    ОтборПоСвойствам: TchResSpecERP = TchResSpecERP('ОтборПоСвойствам')
    ПромежуточныйВыпуск: TchResSpecERP = TchResSpecERP('ПромежуточныйВыпуск')
    ВыходныеИзделия: TchResSpecERP = TchResSpecERP('ВыходныеИзделия')

class ResSpecERP():
    def __init__(self,ref:str):
        if True:
            self.refKey: str | None = None
            self.Ссылка: str | None = None
            self.ВерсияДанных: str | None = None
            self.ПометкаУдаления: str | None = None
            self.Родитель: str | None = None
            self.ЭтоГруппа: str | None = None
            self.Код: str | None = None
            self.Наименование: str | None = None
            self.Статус: str | None = None
            self.НачалоДействия: str | None = None
            self.КонецДействия: str | None = None
            self.МинимальнаяПартияВыпуска: str | None = None
            self.МногоэтапныйПроизводственныйПроцесс: str | None = None
            self.ВыпускПроизвольнымиПорциями: str | None = None
            self.ТипПроизводственногоПроцесса: str | None = None
            self.СпособРаспределенияЗатратНаВыходныеИзделия: str | None = None
            self.Ответственный: str | None = None
            self.Описание: str | None = None
            self.ОптимальнаяПартияВыпуска: str | None = None
            self.ОграниченСрокПролеживанияВыходныхИзделий: str | None = None
            self.МаксимальныйСрокПролеживанияВыходныхИзделий: str | None = None
            self.ОптимальноеКоличествоПередачиМеждуЭтапами: str | None = None
            self.ПечатьМаршрутнойКарты: str | None = None
            self.ОсновноеИзделиеВидНоменклатуры: str | None = None
            self.ОсновноеИзделиеНоменклатура: str | None = None
            self.ОсновноеИзделиеХарактеристика: str | None = None
            self.ОсновноеИзделиеУпаковка: str | None = None
            self.ОсновноеИзделиеКоличествоУпаковок: str | None = None
            self.ОсновноеИзделиеЭтап: str | None = None
            self.Сделка: str | None = None
            self.ДопустимоеПревышениеОптимальнойПартииВыпуска: str | None = None
            self.ВариантНазначения: str | None = None
            self.ВариантПодбораВДокументы: str | None = None
            self.ЕстьУточняемоеОсновноеИзделие: str | None = None
            self.ЕстьПараметризацияРесурсов: str | None = None
            self.ЕстьВложенныеСпецификации: str | None = None
            self.ЕстьРасчетВероятности: str | None = None
            self.ЕстьНекратныеНормативыВРЦ: str | None = None
            self.ОписаниеУточненияПрименения: str | None = None
            self.ОтветственноеПодразделение: str | None = None
            self.РазрешитьВыборДляИзделийПобочногоВыхода: str | None = None
            self.ИдентификаторВерсииДанных: str | None = None
            self.ВариантПромежуточногоВыпуска: str | None = None
            self.Предопределенный: str | None = None
            self.ИмяПредопределенныхДанных: str | None = None
            self.Представление: str | None = None
            self.ВозвратныеОтходы: str | None = None
            self.МатериалыИУслуги: str | None = None
            self.Трудозатраты: str | None = None
            self.СоответствиеСвойств: str | None = None
            self.ДополнительныеРеквизиты: str | None = None
            self.ОтборПоСвойствам: str | None = None
            self.ПромежуточныйВыпуск: str | None = None
            self.ВыходныеИзделия: str | None = None
        
        wet_req_text = f"""ВЫБРАТЬ
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Ссылка)) КАК refKey,
            РесурсныеСпецификации.Ссылка КАК Ссылка,
            РесурсныеСпецификации.ВерсияДанных КАК ВерсияДанных,
            РесурсныеСпецификации.ПометкаУдаления КАК ПометкаУдаления,
            РесурсныеСпецификации.Родитель КАК Родитель,
            РесурсныеСпецификации.ЭтоГруппа КАК ЭтоГруппа,
            РесурсныеСпецификации.Код КАК Код,
            РесурсныеСпецификации.Наименование КАК Наименование,
            РесурсныеСпецификации.Статус КАК Статус,
            РесурсныеСпецификации.НачалоДействия КАК НачалоДействия,
            РесурсныеСпецификации.КонецДействия КАК КонецДействия,
            РесурсныеСпецификации.МинимальнаяПартияВыпуска КАК МинимальнаяПартияВыпуска,
            РесурсныеСпецификации.МногоэтапныйПроизводственныйПроцесс КАК МногоэтапныйПроизводственныйПроцесс,
            РесурсныеСпецификации.ВыпускПроизвольнымиПорциями КАК ВыпускПроизвольнымиПорциями,
            РесурсныеСпецификации.ТипПроизводственногоПроцесса КАК ТипПроизводственногоПроцесса,
            РесурсныеСпецификации.СпособРаспределенияЗатратНаВыходныеИзделия КАК СпособРаспределенияЗатратНаВыходныеИзделия,
            РесурсныеСпецификации.Ответственный КАК Ответственный,
            РесурсныеСпецификации.Описание КАК Описание,
            РесурсныеСпецификации.ОптимальнаяПартияВыпуска КАК ОптимальнаяПартияВыпуска,
            РесурсныеСпецификации.ОграниченСрокПролеживанияВыходныхИзделий КАК ОграниченСрокПролеживанияВыходныхИзделий,
            РесурсныеСпецификации.МаксимальныйСрокПролеживанияВыходныхИзделий КАК МаксимальныйСрокПролеживанияВыходныхИзделий,
            РесурсныеСпецификации.ОптимальноеКоличествоПередачиМеждуЭтапами КАК ОптимальноеКоличествоПередачиМеждуЭтапами,
            РесурсныеСпецификации.ПечатьМаршрутнойКарты КАК ПечатьМаршрутнойКарты,
            РесурсныеСпецификации.ОсновноеИзделиеВидНоменклатуры КАК ОсновноеИзделиеВидНоменклатуры,
            РесурсныеСпецификации.ОсновноеИзделиеНоменклатура КАК ОсновноеИзделиеНоменклатура,
            РесурсныеСпецификации.ОсновноеИзделиеХарактеристика КАК ОсновноеИзделиеХарактеристика,
            РесурсныеСпецификации.ОсновноеИзделиеУпаковка КАК ОсновноеИзделиеУпаковка,
            РесурсныеСпецификации.ОсновноеИзделиеКоличествоУпаковок КАК ОсновноеИзделиеКоличествоУпаковок,
            РесурсныеСпецификации.ОсновноеИзделиеЭтап КАК ОсновноеИзделиеЭтап,
            РесурсныеСпецификации.Сделка КАК Сделка,
            РесурсныеСпецификации.ДопустимоеПревышениеОптимальнойПартииВыпуска КАК ДопустимоеПревышениеОптимальнойПартииВыпуска,
            РесурсныеСпецификации.ВариантНазначения КАК ВариантНазначения,
            РесурсныеСпецификации.ВариантПодбораВДокументы КАК ВариантПодбораВДокументы,
            РесурсныеСпецификации.ЕстьУточняемоеОсновноеИзделие КАК ЕстьУточняемоеОсновноеИзделие,
            РесурсныеСпецификации.ЕстьПараметризацияРесурсов КАК ЕстьПараметризацияРесурсов,
            РесурсныеСпецификации.ЕстьВложенныеСпецификации КАК ЕстьВложенныеСпецификации,
            РесурсныеСпецификации.ЕстьРасчетВероятности КАК ЕстьРасчетВероятности,
            РесурсныеСпецификации.ЕстьНекратныеНормативыВРЦ КАК ЕстьНекратныеНормативыВРЦ,
            РесурсныеСпецификации.ОписаниеУточненияПрименения КАК ОписаниеУточненияПрименения,
            РесурсныеСпецификации.ОтветственноеПодразделение КАК ОтветственноеПодразделение,
            РесурсныеСпецификации.РазрешитьВыборДляИзделийПобочногоВыхода КАК РазрешитьВыборДляИзделийПобочногоВыхода,
            РесурсныеСпецификации.ИдентификаторВерсииДанных КАК ИдентификаторВерсииДанных,
            РесурсныеСпецификации.ВариантПромежуточногоВыпуска КАК ВариантПромежуточногоВыпуска,
            РесурсныеСпецификации.Предопределенный КАК Предопределенный,
            РесурсныеСпецификации.ИмяПредопределенныхДанных КАК ИмяПредопределенныхДанных,
            РесурсныеСпецификации.Представление КАК Представление
        ИЗ
            Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
        ГДЕ
            РесурсныеСпецификации.Ссылка = &Ссылка
                                                       ;"""
        refs = APIERP.Refs_wet(wet_req_text)
        ref_res = APIERP.Ref_wet('Ссылка', 'Справочники.РесурсныеСпецификации', ref)
        refs.add_ref(ref_res)

        key, data_rez = APIERP.get_wet_request(wet_req_text, refs=refs)
        
        if key != 200:
            print(f'find_erp_res Ошибка получения данных код ({key}) из ERP')
        if data_rez['data']:
            data = data_rez['data'][0]
            for key in data.keys():
                if key not in ():
                    #print(f'self.{str(key)}: str|None = None')
                    exec(f'self.{str(key)} = data[key]')
        
        for tch in TchNamesResSpecERP.__dict__.keys():
            if not tch.startswith('__'):
                #print(f'self.{str(tch)}: str|None = None')
                exec(f'self.{str(tch)} = None')
        
        self.is_predv = False
        if self.Наименование.startswith('ТКПА_'):
            self.is_predv = True
                
    @staticmethod
    def dict_description(text: str) -> dict:
        """
           Парсит многострочный текст вида:
           'Ключ:  "значение"'
           и возвращает словарь {ключ: значение или None}
           """
        result = {}
        # шаблон допускает 1 или 2 двойные кавычки, чтобы покрыть оба варианта
        pattern = re.compile(r'^\s*(.+?)\s*:\s*"{1,2}(.*?)"{1,2}\s*$', re.MULTILINE)

        for match in pattern.finditer(text):
            key = match.group(1).strip()
            value = match.group(2).strip() or None
            result[key] = value

        return result

    def dict_description_self(self) -> dict:
        text: str  = self.Описание
        return ResSpecERP.dict_description(text)

    def load_tch(self,tch_name:TchResSpecERP, ref_attrs:set=None)->tuple[int,str|list[dict]]:
        ALIAS = f'РесурсныеСпецификации{tch_name.name}'
        suffix = ''
        if ref_attrs:
            suffix = ',\n'.join([f'ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР({ALIAS}.{_}.Ссылка)) КАК {_}_refKey' for _ in ref_attrs])
            suffix = ',\n' + suffix
        text = f"""ВЫБРАТЬ
                        *{suffix}
                    ИЗ
                        Справочник.РесурсныеСпецификации.{tch_name.name} КАК {ALIAS}
                    ГДЕ
                        РесурсныеСпецификации{tch_name.name}.Ссылка = &Ссылка;
                                                                           """
        refs = APIERP.Refs_wet(text)
        ref_res = APIERP.Ref_wet('Ссылка', 'Справочники.РесурсныеСпецификации', self.refKey)
        refs.add_ref(ref_res)
        code, res = APIERP.get_wet_request(text=text,refs=refs)
        if code != 200:
            return code, f'Ошибка код {code} получения данных из ЕРП РесурсныеСпецификации '
        exec(f'self.{tch_name.name} = {res["data"]}')
        return  code, eval(f'self.{tch_name.name}')

    def calc_trdz_tch_as_dict(self,name_key:str)->dict:
        if self.Трудозатраты is None:
            raise AttributeError("Атрибут 'Трудозатраты' ещё не загружен")
        dict_trdz_tch = dict()
        for row in self.Трудозатраты:
            vid_ref = row[name_key]
            val = row['Количество']
            if vid_ref not in dict_trdz_tch:
                dict_trdz_tch[vid_ref] = 0
            dict_trdz_tch[vid_ref] += val
        return dict_trdz_tch

    def __str__(self):
        return f'{self.Код}, {self.Наименование} - {self.Статус}'

if __name__ == "__main__":
    pass
    #db_naryd = r'SRV:Naryad.db'
    #db_resxml = r'SRV:BD_resxml.db'
    #mk = Marshrut_cards(1974,db_naryd,db_resxml)


# PLACE = Organization(CFG.Config.project.db_naryad, organization_str= CFG.Config.user_config.Organization['Значение'])


DICT_STATUS_OUT = {1:'К оценке', 2:'Принято', 3:'Отклонено',4:'Подготовка'}

DICT_NAME_SQL = {'tkp': {'s_nom':'Порядковый номер',
                            'date_create':'Дата создания',
                            'user_create':'Создал',
                            'type_tkp':'Тип ТКП',
                            'name_tkp':'Наименование ТКП',
                            'nnom_tkp':'Номер ТКП',
                            'dir_rkd':'Путь до ВО',
                            'status':'Статус',
                            'nnom_izd':'Номер изделия',
                            'resp_technolog':'Ответственный технолог',
                            'date_mk':'Дата создания МК',
                            'date_res':'Дата создания ресурсной',
                             'name_res':'Наименование ресурсной ЕРП',
                         'weight_wh_pki':'Вес c ПКИ'},
    'versions_res_mat':
        {
        's_num':'Пномер',
        'num_kpl':'НомерКПЛ',
        'date_version':'ДатаВерсия',
        'data':'Файл',
        'primech':'Примечание',
         'active': "Активная",
        'user': 'Пользователь',
            'ind':'ИдентификаторВерсииРесурсной',

        }
                     }


#for key1 in DICT_TYPE_OTK_BRAK.keys():
#    for key2 in DICT_TYPE_OTK_BRAK[key1].keys():
#        for item in DICT_TYPE_OTK_BRAK[key1][key2]:
#            print("$".join([key1,key2,item]) )

@CQT.onerror
def LIST_NEGRUZ_DSE(db_nomen: str):
    poki = CFG.Config.place.poki
    return CSQ.custom_request_c(
        db_nomen,
        f'SELECT Имя FROM ТипДсе WHERE poki = {poki} AND Вкл = 0',
        hat_c=False,
        one_column=True
    )

@CQT.onerror
def DICT_RC_TBL(db_users): #27.01.2026
    current_org_id = CFG.Config.place.poki
    custom_request_c = f"""SELECT rm.Пномер,
                                   pc.adress AS Расположение,
                                   rc.Имя AS РЦ,
                                   rm.Прозвище,
                                   eq.Наименование || ' ' || eq.Инв_номер AS Оборудование,
                                   pr.имя AS Профессия_рм,

                                   COALESCE(e1.Должность, '') AS Должность_1см,
                                   COALESCE(e1.ФИО, '') AS ФИО_1см,
                                   COALESCE(sw1.employee_id, 1) AS Пномер_emp1,
                                   COALESCE(sw1.time_start, '07:00') AS Время_начала_1,
                                   COALESCE(sw1.time_end,   '15:30') AS Время_конца_1,
                                   COALESCE(sw1.Нераб_мин, 75) AS Нераб_мин1,
                                   COALESCE(sw1.Между_нар_мин, 40) AS Между_нар_мин1,
                                   COALESCE(sw1.Коэфф_производит, 1) AS Коэфф_производит1,

                                   COALESCE(e2.Должность, '') AS Должность_2см,
                                   COALESCE(e2.ФИО, '') AS ФИО_2см,
                                   COALESCE(sw2.employee_id, 1) AS Пномер_emp2,
                                   COALESCE(sw2.time_start, '15:30') AS Время_начала_2,
                                   COALESCE(sw2.time_end,   '23:59') AS Время_конца_2,
                                   COALESCE(sw2.Нераб_мин, 75) AS Нераб_мин2,
                                   COALESCE(sw2.Между_нар_мин, 40) AS Между_нар_мин2,
                                   COALESCE(sw2.Коэфф_производит, 0.9) AS Коэфф_производит2,

                                   COALESCE(e3.Должность, '') AS Должность_3см,
                                   COALESCE(e3.ФИО, '') AS ФИО_3см,
                                   COALESCE(sw3.employee_id, 1) AS Пномер_emp3,
                                   COALESCE(sw3.time_start, '00:01') AS Время_начала_3,
                                   COALESCE(sw3.time_end,   '07:00') AS Время_конца_3,
                                   COALESCE(sw3.Нераб_мин, 75) AS Нераб_мин3,
                                   COALESCE(sw3.Между_нар_мин, 40) AS Между_нар_мин3,
                                   COALESCE(sw3.Коэфф_производит, 0.8) AS Коэфф_производит3,

                                   rm.Примечание,
                                   rm.coord
                            FROM rab_mesta rm
                            LEFT JOIN places_capacity pc ON pc.serial == rm.Расположение
                            LEFT JOIN rab_c rc ON rc.Код == rm.Код_РЦ
                            LEFT JOIN equipment eq ON eq.Пномер == rm.Номер_осн_оборуд
                            LEFT JOIN professions pr ON pr.код == rm.Код_профессии

                            LEFT JOIN schedule_work_places sw1 ON sw1.workplace_id == rm.Пномер AND sw1.shift_no == 1
                            LEFT JOIN schedule_work_places sw2 ON sw2.workplace_id == rm.Пномер AND sw2.shift_no == 2
                            LEFT JOIN schedule_work_places sw3 ON sw3.workplace_id == rm.Пномер AND sw3.shift_no == 3
                            LEFT JOIN employee e1 ON e1.Пномер == sw1.employee_id
                            LEFT JOIN employee e2 ON e2.Пномер == sw2.employee_id
                            LEFT JOIN employee e3 ON e3.Пномер == sw3.employee_id
                            WHERE rm.poki = {current_org_id}
                            ORDER BY rm.Пномер"""

    return CSQ.custom_request_c(db_users, custom_request_c, hat_c=False, rez_dict=True) or []


def tmp_dir():
    ima_module = F.name_of_executable_file_c().split('.')[0]
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp'])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp']))
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module]))
    return os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])

def load_tmp_stukt(ima,default_val = None):
    puth_name = tmp_dir() + os.sep + ima + '.pickle'
    if F.existence_file_c(puth_name) == True:
        val = F.load_file_pickle(puth_name)
        return val
    return default_val



def is_autorepeat_update_fact(db_naryad, poki):
    autoload_fact_kpl = CSQ.custom_request_c(CFG.Config.project.db_naryad, f'''SELECT 
                autoload_fact_kpl_onoff FROM places WHERE poki = {poki}'''
                                             , rez_dict=True, one=True)
    return autoload_fact_kpl['autoload_fact_kpl_onoff']

@CQT.onerror
def calc_dict_vid_rabot(poki:int):
    custom_request_c = f'''SELECT * FROM professions 
       LEFT JOIN vid_rab_po_dolg ON vid_rab_po_dolg.Вид_работ = professions.вид_работ
       LEFT JOIN group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan
       WHERE professions.poki = {poki} AND professions.Вкл = 1 and group_vid_rab_for_plan.composite = 0'''
    list_prof = CSQ.custom_request_c(CFG.Config.project.db_users, custom_request_c, hat_c=False, rez_dict=True)
    return F.deploy_dict_c(list_prof, 'вид_работ')

@CQT.onerror
def calc_dict_podr(*args):
    return CSQ.custom_request_c(CFG.Config.project.db_kplan, """SELECT * FROM podrazdel""", rez_dict=True)

@CQT.onerror
def calc_list_opers(poki):
    return CSQ.custom_request_c(CFG.Config.project.db_naryad,
                                            f"""SELECT * FROM operacii WHERE poki == {poki}""")

@CQT.onerror
def calc_dicts_opers(poki):
    list_opers = calc_list_opers(poki)
    DICT_OP_NAME = F.list_to_dict(list_opers, 'name')
    DICT_OP = F.list_to_dict(list_opers, 'kod')

    renames = CSQ.custom_request_c(CFG.Config.project.db_naryad,
                                            f"""SELECT * FROM operacii_renames inner join operacii
                                             on operacii.kod == operacii_renames.kod WHERE operacii.poki == {poki}""",rez_dict=True)
    for item in renames:
        old_name = item['old_name']
        kod = item['kod']
        if kod in DICT_OP:
            current_name =  DICT_OP[kod]['name']
            DICT_OP_NAME[old_name] = DICT_OP_NAME[current_name]
    return DICT_OP, DICT_OP_NAME
    
@CQT.onerror
def calc_dict_napravlenie(*args):
    return CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""SELECT * FROM napravlenie""", rez_dict=True)

@CQT.onerror
def calc_napr_deyat(poki):
    return CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""SELECT * FROM napravl_deyat 
    WHERE state_on_off = 1 and poki == {poki} OR poki is NULL""", rez_dict=True)

@CQT.onerror
def calc_dict_group_podr_vid_rab_for_plan(*args):
    return  F.deploy_dict_c(CSQ.custom_request_c(CFG.Config.project.db_kplan, """SELECT 
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
       group_vid_rab_for_plan.etap_name_from_erp_1c,
       group_vid_rab_for_plan.average_efficiency,
       group_vid_rab_for_plan.num_podr
     FROM 
    group_vid_rab_for_plan INNER JOIN 
    podrazdel ON group_vid_rab_for_plan.num_podr == podrazdel.Пномер""", rez_dict=True, attach_dbs=CFG.Config.project.db_users), 'name')



@CQT.onerror
def calc_koefs_pogr(DICT_VID_PO_NAPR,DICT_NAPRAVLENIE,DICT_NAPR_DEYAT_NAME, vid_po_napr, napr_deyat):
    # koef_vneplana = self.Data_plan.DICT_NAPRAVLENIE[self.Data_plan.DICT_NAPR_DEYAT_NAME[napr_deyat]['Направление']][
    # 'koef_vneplana']
    koef_vneplana = 1
    if vid_po_napr in DICT_VID_PO_NAPR:
        koef_vneplana = 1 + DICT_VID_PO_NAPR[vid_po_napr]['vneplan_percent']
        if koef_vneplana > 6:# 19.08.2025 Задача № 100058908
            koef_vneplana = 6
    koef_pogr_norm = DICT_NAPRAVLENIE[DICT_NAPR_DEYAT_NAME[napr_deyat]['Направление']][
        'koef_pogr_norm']
    return koef_vneplana, koef_pogr_norm

@CQT.onerror
def recalc_fact_by_date(
                        DICT_GROUP_PODR_VID_RAB_FOR_PLAN,
                        DICT_VID_RABOT,
                        DICT_NAPR_DEYAT,
                        DICT_VID_PO_NAPR, DICT_NAPRAVLENIE, DICT_NAPR_DEYAT_NAME,
                        DICT_DOLGN_ETAP,
                        DICT_EMPLOEE_FULL_WITH_DEL,
                        DICT_OP_NAME,
                        pozition_num: int,
                        date_calc: datetime.datetime = None,
                        *args):
    estimated_vid_rab_names_fact = {v['name_fact'] for k, v in DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items()
                                    if
                                    v['estimated'] and v['poki'] == CFG.Config.place.poki}
    estimated_vid_rab_names = {v['Имя'] for k, v in DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items()
                                    if
                                    v['estimated'] and v['poki'] == CFG.Config.place.poki}
    composite_vid_rab_names = {v['name_fact'] for k, v in DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items()
                                    if
                                    v['composite'] and v['poki'] == CFG.Config.place.poki}
    estimated_vid_rab_names_fact = estimated_vid_rab_names_fact.union(estimated_vid_rab_names)
    estimated_vid_rab_names_fact = estimated_vid_rab_names_fact.union(composite_vid_rab_names)

    def vid_rab_into_name_plan(vid_rab: str):
        if vid_rab in DICT_VID_RABOT:
            return DICT_VID_RABOT[vid_rab]['group_for_plan_f'].split(';')
        return

    def vid_rab_into_name_etap(vid_rab: str):
        if vid_rab in DICT_VID_RABOT:
            return DICT_VID_RABOT[vid_rab]['name_tbl'].split(';')
        return

    def start_end_fakt_into_name_plan(vid_rab: str):
        if vid_rab in DICT_VID_RABOT:
            return DICT_VID_RABOT[vid_rab]['group_for_plan_start_f'].split(';'), DICT_VID_RABOT[vid_rab][
                'group_for_plan_end_f'].split(';')
        return None, None

    def calc_time(DICT_NAPR_DEYAT,DICT_VID_PO_NAPR,DICT_NAPRAVLENIE,DICT_NAPR_DEYAT_NAME,
                  DICT_DOLGN_ETAP,
                DICT_EMPLOEE_FULL_WITH_DEL,
                 DICT_OP_NAME,
                  pozition_num, date_calc=None):
        poz = Pozition(pozition_num, CFG.Config.project.db_kplan, CFG.Config.project.db_naryad, CFG.Config.project.db_resxml, CFG.Config.project.db_users)
        poz.load_kpl_table('пл_топ')

        vid_po_napr = poz.dict_tables['пл_топ']['Вид']
        napr_deyat = DICT_NAPR_DEYAT[poz.Направление_деятельности]['Имя']

        try:
            koef_vneplana, koef_pogr_norm = calc_koefs_pogr(DICT_VID_PO_NAPR,
                                                            DICT_NAPRAVLENIE,
                                                            DICT_NAPR_DEYAT_NAME,
                                                            vid_po_napr, napr_deyat)
        except:
            CQT.msgbox(f'Не корректно занесен направление')
            return
        postfix =''
        if date_calc:
            nach = F.datetostr(date_calc,"%Y-%m-%d 04:00:00")
            konec = F.datetostr( F.date_add_days(date_calc,1,format_out='') ,"%Y-%m-%d 03:59:59")
            postfix= f'datetime(jurnal.Дата) > datetime("{nach}") and datetime(jurnal.Дата) < datetime("{konec}") and'
        list_nars = CSQ.custom_request_c(CFG.Config.project.db_naryad, f"""SELECT DISTINCT
        {', '.join(['naryad.' + _ for _ in CSQ.list_types_table(CFG.Config.project.db_naryad, 'naryad').keys()])},
         mk.Дата as ДатаМК , mk.Тип as ТипМК 
         FROM naryad 
        INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
        INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер 
        WHERE {postfix} mk.НомКплан = {pozition_num}  and naryad.Аутсорсинг == 0;""", # убрано 29.09.2025 по задаче 100060640 naryad.Подтвержд_вып_дата != ""
                                         rez_dict=True)
        #mk.Пномер as "Номер МК", mk.Номенклатура, [_['Пномер'] for _ in list_nars]
        list_mk_nums = [_['Номер_мк'] for _ in list_nars]
        dict_mk_data = F.deploy_dict_c(CSQ.custom_request_c(CFG.Config.project.db_naryad,f"""SELECT mk.Пномер as "Номер МК", 
         mk.Номенклатура FROM mk 
         LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
        WHERE 
         mk.Пномер IN ({CSQ.prepare_list_to_tuple(list_mk_nums)}) and plan.poki = {CFG.Config.place.poki};""", rez_dict=True,
                                            attach_dbs=(CFG.Config.project.db_kplan)),"Номер МК")
        dict_summ_time = dict()
        dict_fact_jur = dict()
        dict_jur_data = dict()

        set_name_etaps = set()

        for row in list_nars:
            nar = Naryads(row, CFG.Config.project.db_naryad, DICT_DOLGN_ETAP, CFG.Config.project.db_users,
                              DICT_EMPLOEE_FULL_WITH_DEL)

            nar.recalc_fact()
            nar.recalc_jur_n_time(nar.ФИО)
            nar.recalc_jur_n_time(nar.ФИО2)

            jur = nar.get_list_from_jurnal(blob_pass=True)
            start, end = jur.calc_start_end_dates()
            if start == None or end == None:
                continue

            def calc_dict_fact_jur_by_day(jur:Jurnal_nar):

                dict_fact_jur_by_day = dict()

                for item_jur in jur.rows:
                    if item_jur['Подытог_нормы'] == '':
                        continue
                    if F.is_numeric(item_jur['Подытог_нормы']) and item_jur['Подытог_нормы'] > 0 and item_jur['Статус'] == 'Начат':
                        date_jur = F.strtodate(item_jur['Дата'])
                        if date_calc:
                            if date_calc.date() != date_jur.date():
                                continue
                        day = F.datetostr(date_jur, "%d\n%m\n%y")

                        if day not in dict_fact_jur_by_day:
                            dict_fact_jur_by_day[day] = {'time':0,'data_jur':[]}
                        dict_fact_jur_by_day[day]['time'] += item_jur['Подытог_нормы']
                        dict_fact_jur_by_day[day]['data_jur'].append(item_jur)
                return dict_fact_jur_by_day

            dict_fact_jur_by_day = calc_dict_fact_jur_by_day(jur)
            if dict_fact_jur_by_day is None:
                return
            for oper_param in nar.params:
                name_plan_list = vid_rab_into_name_plan(oper_param['Виды_работ'])

                list_name_start, list_name_end = start_end_fakt_into_name_plan(oper_param['Виды_работ'])
                if list_name_start == None or list_name_start == None:
                    continue
                for name_start in list_name_start:
                    if not start == None:
                        if name_start not in dict_summ_time or F.strtodate(start) < F.strtodate(
                                dict_summ_time[name_start]):
                            dict_summ_time[name_start] = start
                for name_end in list_name_end:
                    if not end == None:
                        if name_end not in dict_summ_time or F.strtodate(end) > F.strtodate(dict_summ_time[name_end]):
                            dict_summ_time[name_end] = end

                if name_plan_list == None:
                    continue
                if oper_param['Операции_имя'] not in DICT_OP_NAME:
                    CQT.msgbox(f'Операция "{oper_param['Операции_имя']}" отсутствует в DICT_OP_NAME')
                    return
                kr = DICT_OP_NAME[oper_param['Операции_имя']]['kr_default']
                koef_posta = 1
                if kr == 2:
                    koef_posta = 1 / 0.7

                name_etap_list = vid_rab_into_name_etap(oper_param['Виды_работ'])
                for name_etap in name_etap_list:
                    set_name_etaps.add(name_etap)
                    koef_vneplana_tmp = 1
                    if name_etap in estimated_vid_rab_names_fact:
                        koef_vneplana_tmp = copy.deepcopy(koef_vneplana)# 19.08.2025 Задача № 100058908
                        if row['ТипМК'] in (2, 3, 5):
                            if koef_vneplana_tmp > 1.27:
                                koef_vneplana_tmp = 1.27

                    name_etap = 'факт_' + name_etap
                    if name_etap not in dict_jur_data:
                        dict_jur_data[name_etap] = []
                    if name_etap not in dict_fact_jur:
                        dict_fact_jur[name_etap] = dict()
                    for day, minutes_fact_data in dict_fact_jur_by_day.items():
                        minutes_fact= minutes_fact_data['time']

                        if day not in dict_fact_jur[name_etap]:
                            dict_fact_jur[name_etap][day] = 0
                        minutes_fact_k = minutes_fact * koef_vneplana_tmp * koef_posta * koef_pogr_norm
                        part_time =  minutes_fact_k / nar.get_summ_teor_time_by_empl() * oper_param['Опер_время']
                        dict_fact_jur[name_etap][day] +=part_time

                        for row_jur in minutes_fact_data['data_jur']:

                            row_jur = copy.deepcopy(row_jur)

                            minutes_fact_k_row = row_jur['Подытог_нормы'] * koef_vneplana_tmp * koef_posta * koef_pogr_norm
                            part_time_row = round(minutes_fact_k_row / nar.get_summ_teor_time_by_empl() * oper_param['Опер_время'],3)

                            row_jur["Номенклатура"] = ""
                            if nar.Номер_мк in dict_mk_data:
                                row_jur["Номенклатура"] =dict_mk_data[nar.Номер_мк]
                            row_jur['Этап плана'] = name_etap
                            row_jur['Дата плана'] = F.datetostr(F.strtodate(day,"%d\n%m\n%y"),'%Y-%m-%d')
                            row_jur['ДСЕ'] = oper_param['ДСЕ']
                            row_jur['Операция'] = " ".join((oper_param['Операции_номер'],oper_param['Операции_имя']))
                            row_jur['minutes_fact'] = row_jur['Подытог_нормы']
                            row_jur['Опер_время'] = oper_param['Опер_время']
                            row_jur['koef_posta'] = round(koef_posta,2)

                            row_jur['koef_pogr_norm'] = koef_pogr_norm

                            row_jur['koef_vneplana'] = koef_vneplana_tmp
                            row_jur['minutes_fact_k'] =round( minutes_fact_k_row,2)
                            row_jur['summ_teor_time'] = nar.get_summ_teor_time_by_empl()
                            row_jur['Подытог_нормы_для_плана_минут'] = copy.deepcopy(round(part_time_row,3))
                            row_jur['Подытог_нормы_для_плана_час'] = copy.deepcopy(round(part_time_row/60, 3))

                            if 'Подытог' in row_jur:
                                row_jur.pop('Подытог')
                            dict_jur_data[name_etap].append(row_jur)

                for name_plan in name_plan_list:
                    koef_vneplana_tmp = 1
                    set_name_etaps.add(name_etap)
                    if name_plan in estimated_vid_rab_names_fact:
                        koef_vneplana_tmp = copy.deepcopy(koef_vneplana)  # 19.08.2025 Задача № 100058908
                        if row['ТипМК'] in (2, 3, 5):
                            if koef_vneplana_tmp > 1.27:
                                koef_vneplana_tmp = 1.27

                    if name_plan not in dict_summ_time:
                        dict_summ_time[name_plan] = 0
                    minutes_fact = sum(
                       [ _['time'] for _ in list(dict_fact_jur_by_day.values())]) * koef_vneplana_tmp * koef_posta * koef_pogr_norm
                    part_time = minutes_fact / nar.get_summ_teor_time_by_empl() * oper_param['Опер_время']
                    dict_summ_time[name_plan] += round(part_time,3)  # учитывается отдельно сумма пл_сб поэтому не надо делить на 2
                    #print(f'{name_plan} + {round(part_time,3)}')
        for k, v in dict_summ_time.items():
            if F.is_date(v):
                dict_summ_time[k] = F.datetostr(F.strtodate(v), "%Y-%m-%d")
            if F.is_numeric(v):
                dict_summ_time[k] = round(v / 60, 2)

        return poz, dict_fact_jur, dict_summ_time, dict_jur_data

    result = calc_time(
                                                                DICT_NAPR_DEYAT,
                                                                DICT_VID_PO_NAPR,
                                                                DICT_NAPRAVLENIE,
                                                                DICT_NAPR_DEYAT_NAME,
                                                                DICT_DOLGN_ETAP,
                                                                DICT_EMPLOEE_FULL_WITH_DEL,
                                                                DICT_OP_NAME,
                                                                pozition_num,
                                                                date_calc)
    if result is None:
        return
    poz, dict_fact_jur, dict_summ_time, dict_jur_data = result
    return poz, dict_fact_jur, dict_summ_time,dict_jur_data

def calc_pozition_fact_kpl(self, pozition_num,
                            DICT_GROUP_PODR_VID_RAB_FOR_PLAN,
                            DICT_VID_RABOT,
                            DICT_NAPR_DEYAT,
                            DICT_VID_PO_NAPR,
                            DICT_NAPRAVLENIE,
                            DICT_NAPR_DEYAT_NAME,
                            DICT_DOLGN_ETAP,
                            DICT_EMPLOEE_FULL_WITH_DEL,
                            DICT_OP_NAME,
                            DICT_CLD,
                            DICT_PODR,
                            repaint_graf=True):

        result = recalc_fact_by_date(
                            DICT_GROUP_PODR_VID_RAB_FOR_PLAN,
                            DICT_VID_RABOT,
                            DICT_NAPR_DEYAT,
                            DICT_VID_PO_NAPR,
                            DICT_NAPRAVLENIE,
                            DICT_NAPR_DEYAT_NAME,
                            DICT_DOLGN_ETAP,
                            DICT_EMPLOEE_FULL_WITH_DEL,
                            DICT_OP_NAME,
                            pozition_num)
        if result is None:
            return
        poz, dict_fact_jur, dict_summ_time, dict_jur_data = result
        poz.update_day_plan_etap_jurnal(dict_fact_jur)
        rez_update_row_etaps = poz.update_row_etaps(dict_summ_time)
        if rez_update_row_etaps:
            update_local_graf(self, True, pozition_num, repaint_graf, DICT_CLD = DICT_CLD, DICT_PODR = DICT_PODR)
            print(f'recalc_fact_by_date: №{poz.Пномер} {dict_summ_time}')
            pass
        return dict_jur_data, rez_update_row_etaps


@CQT.onerror
def update_local_graf(self=None, update=False,pnom:int = 0,fill_gant=True,DICT_CLD=None, DICT_PODR=None,*args):
    if self:
        self.current_kpl_table = 'tbl_preview'
        if pnom == 0:
            tbl = self.ui.tbl_kal_pl
            r = tbl.currentRow()
            if r == None or r == -1:
                return
            nk_pnom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
            if tbl.item(r, nk_pnom).text() == '-1':
                return 
            pnom = int(tbl.item(r, nk_pnom).text())
        if 'shift' in CQT.get_key_modifiers(self):
            update = True
        DICT_CLD = self.Data_plan.DICT_CLD
        DICT_PODR = self.Data_plan.DICT_PODR

    else:
        if pnom == 0:
            print(f'update_local_graf err pnom == 0')
            return
        if DICT_CLD == None or DICT_PODR == None:
            print(f'update_local_graf err DICT_CLD == None or DICT_PODR == None')
            return

    def load_dict_form(DICT_CLD,DICT_PODR,min_date,max_date,snum_kplan:int):
        def load_list_of_month(min_date,max_date):
            return  [F.start_end_dates_c(min_date,'','m','')[0],F.start_end_dates_c(max_date,'','m','')[1]]

        def genetrate_cld(DICT_CLD,DICT_PODR,list_of_month):
            weekends = Plan_custom_weekends(snum_kplan)
            rez = dict()
            list_days = sorted([k for  k in  DICT_CLD.keys()])
            for day in list_days:
                if day >= list_of_month[0] and day<= list_of_month[1]:
                    rez[day] = copy.deepcopy(DICT_CLD[day])
                    rez[day]['podr'] = dict()
                    if weekends.is_weekend(day):
                        rez[day]['Выходные'] = 1
                    for podr in DICT_PODR.keys():
                        if DICT_PODR[podr]['Порядок'] >= 0:
                            rez[day]['podr']['план_' + podr] = ""
                            rez[day]['podr']['факт_'+ podr] = ""
            return rez

        min_max_of_month = load_list_of_month(min_date,max_date)

        dict_cld = genetrate_cld(DICT_CLD,DICT_PODR,min_max_of_month)
        return dict_cld

    def save_form_db(dict_form,pnom):
        data = F.to_binary_pickle(dict_form)
        CSQ.custom_request_c(CFG.Config.project.db_kplan,f"""UPDATE plan SET local_graf = ? WHERE Пномер == ?;""",list_of_lists_c=[data,pnom])
        print(f'Update {pnom} success')
        return data

    def setText_data(self,dict_form,pnom):
        tbl = self.ui.tbl_kal_pl
        data = F.to_binary_pickle(dict_form)
        nk_pnom = CQT.num_col_by_name_c(tbl,'plan.Пномер')
        nk_graf = CQT.num_col_by_name_c(tbl,'plan.local_graf')
        for i in range(tbl.rowCount()):
            if tbl.item(i,nk_pnom).text() == str(pnom):
                tbl.item(i, nk_graf).setText(str(data))
                break
        return data

    def fill_date(DICT_PODR,dict_form,dict_dates:dict,dict_norms:dict,pnom,proj,poz, napr,napr_deyat):

        def search_norma(name,dict_norms,podr):
            # =================
            prefix = None
            if 'фдата' in name:
                prefix = 'Ф'
            if 'пдата' in name:
                prefix = 'Н'
            if prefix == None:
                return 0
            capacity = 0
            vid_etap = name.split("__")[-1]
            for field, val in dict_norms.items():
                if podr == field.split('.')[0]:
                    left_str = prefix + "час_" + vid_etap
                    if left_str.lower() == field.split('.')[1].lower():
                        capacity = val
                        break
                    left_str = prefix +  "мин_" + vid_etap
                    if left_str.lower() == field.split('.')[1].lower():
                        capacity = round(val/60,2)
                        break
            # =================
            return  capacity

        def fill_date_to_form(dict_form, podr, date_nach,date_zav,etap,capacity,name_nach,name_zav):
            fl_rab_dn = True
            rab_dn = 0
            for date in dict_form.keys():
                if date >= date_nach and date <= date_zav:
                    if dict_form[date]['Выходные'] == 0:
                        rab_dn +=1
            if rab_dn == 0:
                fl_rab_dn = False
                for date in dict_form.keys():
                    if date >= date_nach and date <= date_zav:
                        rab_dn += 1
            if rab_dn == 0:
                mosh = 0
            else:
                mosh = round(capacity / (rab_dn),3)

            for date in dict_form.keys():
                if date >= date_nach and date <= date_zav:
                    if date > date_zav:
                        break
                    if dict_form[date]['Выходные'] == 0 or not fl_rab_dn:
                        data_et = {"Время_час" : mosh, 'Этап' : etap,
                                                         "Начало" : F.datetostr(date_nach,"%d.%m.%y"),
                                                         "Конец" : F.datetostr(date_zav,"%d.%m.%y"),
                                                         "Имя_нз" : [name_nach,name_zav]}

                        if dict_form[date]['podr'][podr] != '':
                            dict_form[date]['podr'][podr].append(data_et)
                        else:
                            dict_form[date]['podr'][podr] = [data_et]

            return dict_form
        rez = ''
        dict_process = dict()
        for podr in DICT_PODR.keys():
            if DICT_PODR[podr]['Порядок'] >= 0:
                if podr not in dict_process:
                    dict_process['план_' + podr] = dict()
                    dict_process['факт_' + podr] = dict()

                for field,val in dict_dates.items():
                    if podr == field.split('.')[0]:
                        if "дата" in field.lower():
                            current_sort_c_pf = None
                            if "фдата" in field.lower():
                                current_sort_c_pf = 'факт_' + podr
                            if "пдата" in field.lower():
                                current_sort_c_pf = 'план_' + podr
                            if current_sort_c_pf == None:
                                continue
                            if "нач" in field.lower() or "зав" in field.lower():
                                name = field.lower().replace("нач",'').replace("зав",'')
                                capacity  = search_norma(name,dict_norms,podr)
                                if name not in dict_process[current_sort_c_pf]:
                                    dict_process[current_sort_c_pf][name] = dict()
                                dict_process[current_sort_c_pf][name]["Норм"] = capacity
                                if "нач" in field.lower():
                                    dict_process[current_sort_c_pf][name]["нач"] = dict()
                                    dict_process[current_sort_c_pf][name]["нач"]['val'] = ''
                                    if F.is_date(val, "%Y-%m-%d"):
                                        dict_process[current_sort_c_pf][name]["нач"]['val'] = F.strtodate(val,"%Y-%m-%d")
                                    dict_process[current_sort_c_pf][name]["нач"]['field'] = field
                                if "зав" in field.lower():
                                    dict_process[current_sort_c_pf][name]["зав"] = dict()
                                    dict_process[current_sort_c_pf][name]["зав"]['val'] = ''
                                    if F.is_date(val, "%Y-%m-%d"):
                                        dict_process[current_sort_c_pf][name]["зав"]['val'] = F.strtodate(val, "%Y-%m-%d")
                                    dict_process[current_sort_c_pf][name]["зав"]['field'] = field
                            else:
                                if field.lower() not in dict_process[current_sort_c_pf]:
                                    dict_process[current_sort_c_pf][field.lower()] = dict()
                                if "ед" not in dict_process[current_sort_c_pf][field.lower()]:
                                    dict_process[current_sort_c_pf][field.lower()]["ед"] = dict()
                                dict_process[current_sort_c_pf][field.lower()]["ед"]['val'] = ''
                                if F.is_date(val, "%Y-%m-%d"):
                                    dict_process[current_sort_c_pf][field.lower()]["ед"]['val'] = F.strtodate(val,"%Y-%m-%d")
                                dict_process[current_sort_c_pf][field.lower()]["ед"]['field'] = field
        for podr in dict_process.keys():
            for etap in dict_process[podr].keys():
                date_nach = ''
                date_zav = ''
                capacity = 0
                for vid in dict_process[podr][etap].keys():
                    if vid == 'Норм':
                        capacity = F.valm(dict_process[podr][etap][vid])
                    if vid == 'ед':
                        date_nach = date_zav = dict_process[podr][etap][vid]['val']
                        name_nach = name_zav = dict_process[podr][etap][vid]['field']
                    if vid == 'нач':
                        date_nach = dict_process[podr][etap][vid]['val']
                        name_nach = dict_process[podr][etap][vid]['field']
                    if vid == 'зав':
                        date_zav = dict_process[podr][etap][vid]['val']
                        name_zav = dict_process[podr][etap][vid]['field']
                if date_nach == "" or date_zav == '':
                    pass
                else:
                    dict_form = fill_date_to_form(dict_form,podr,date_nach,date_zav,etap,capacity,name_nach,name_zav)
        dict_form = [{'pnom':pnom,'proj':proj,'poz':poz,'napr_deya':napr_deyat,'napr':napr,'data':dict_form}]
        return dict_form

    def generane_new_gant(self: mywindow|None,DICT_CLD, DICT_PODR, dict_poz):

        poz = Pozition(dict_poz['Пномер'], CFG.Config.project.db_kplan, CFG.Config.project.db_naryad, CFG.Config.project.db_resxml, CFG.Config.project.db_users)
        dict_dates = poz.row_dates_etap |  poz.row_dates_etap_fact
        dict_dates = dict_dates |  poz.row_dates_etap_plan
        dict_dates = dict_dates |  poz.row_dates_supply

        dict_norms= poz.row_time_etap |  poz.row_time_add_etap

        if poz.max_date == '' or poz.min_date == '':
            return

        dict_form = load_dict_form(DICT_CLD,DICT_PODR, F.strtodate(poz.min_date,"%d.%m.%Y" ) , F.strtodate(poz.max_date,"%d.%m.%Y" ),dict_poz['Пномер'])

        dict_form = fill_date(DICT_PODR,
                              dict_form, dict_dates,dict_norms, dict_poz['Пномер'],
                              f"{dict_poz['№проекта']} {dict_poz['№ERP']}",
                              dict_poz['Позиция'], dict_poz['Направление'], dict_poz['Направление_деят'])

        data_bin = save_form_db(dict_form, dict_poz['Пномер'])
        if self:
            setText_data(self, dict_form, dict_poz['Пномер'])
        return data_bin

    dict_poz = load_dict_poz_from_sql(pnom)
    if dict_poz == False:
        return
    if self:
        self.pnom_kplan_select = dict_poz['Пномер']
        self.Data_plan.DICT_REPLACE_BY_DAYS = None
        if dict_poz['fact_jurnal_blolb_data']:
            self.Data_plan.DICT_REPLACE_BY_DAYS = F.from_binary_pickle(dict_poz['fact_jurnal_blolb_data'])
        if self.Data_plan.DICT_REPLACE_BY_DAYS is None: #31.07.25
            self.Data_plan.DICT_REPLACE_BY_DAYS = {}

    fl_upd = True
    dict_form = []

    if update == False:
        data = dict_poz['local_graf']
        if data != '' and data != 'None':
            dict_form = F.from_binary_pickle(data)
            if dict_form != None:
                fl_upd = False
    data_bin = None
    if fl_upd:
        data_bin = generane_new_gant(self,DICT_CLD, DICT_PODR,
                                     dict_poz)
        if data_bin == None:
            CQT.msgbox(f'ОШибка генерации ганта')
            return
    if fill_gant:
        if self:
            if dict_form != None and len(dict_form) > 0:
                dict_form[0]['napr_deya'] = dict_poz['Направление_деят']
            self.current_kpl_table = 'tbl_preview'
            fill_gant_table(self, self.ui.tbl_preview,'', dict_form, pnom)

    if fl_upd:
        return data_bin
    return

def hide_free_columns(self,tbl):
    for j in range(self.count_tbl_field, tbl.columnCount()):
        self.ui.tbl_preview.setColumnHidden(j, False)
    for j in range(self.count_tbl_field, tbl.columnCount()):
        fl_hide = True
        for i in range(2,tbl.rowCount()):
            if tbl.item(i,j).text() != '':
                fl_hide = False
                break
        if fl_hide:
            tbl.setColumnHidden(j,True)
        else:
            break

    for j in range(tbl.columnCount()-1,-1,self.count_tbl_field):
        fl_hide = True
        for i in range(2,tbl.rowCount()):
            if tbl.item(i,j).text() != '':
                fl_hide = False
                break
        if fl_hide:
            tbl.setColumnHidden(j,True)
        else:
            break
    tbl.resizeColumnsToContents()


def oforml_table(self:mywindow,tbl, tbl_filtr:QtWidgets.QTableWidget= ''):
    self.count_tbl_field = len(self.list_for_hat)
    CQT.fill_wtabl(self.dict_tbls_kpl[self.current_kpl_table],tbl,min_width_col= int(4*0.8),
                   height_row=self.val_masht*2, colorful_edit=False,auto_type= False,head_column=0,set_editeble_col_nomera={},hide_head_column=False)
    for j in range(1,self.count_tbl_field):
        CQT.set_color_text_header_wtab_horisontal_c(tbl, j, 11, 11, 11, self.val_masht*0.7, False)
        for i in range(3, len(self.dict_tbls_kpl_info[self.current_kpl_table])):
            CQT.font_cell_size_format(tbl, i - 1, j, self.val_masht)
    CQT.list_from_wtabl_c(tbl)
    for j in range(self.count_tbl_field, len(self.dict_tbls_kpl_info[self.current_kpl_table][0])):
         if self.dict_tbls_kpl_info[self.current_kpl_table][1][j] == 1:
             CQT.set_color_text_header_wtab_horisontal_c(tbl, j, 200, 11, 11, self.val_masht*0.8, True)
         else:
             CQT.set_color_text_header_wtab_horisontal_c(tbl, j, 11, 11, 11, self.val_masht*0.7, False)
    for i in range(3,len(self.dict_tbls_kpl_info[self.current_kpl_table])):
        fact= False
        if 'факт_' in self.dict_tbls_kpl_info[self.current_kpl_table][i][0].lower():
            fact= True
        podr = self.dict_tbls_kpl_info[self.current_kpl_table][i][0].replace('факт_', '').replace('план_', '')
        r = 233
        g = 233
        b = 233
        if podr in self.Data_plan.DICT_PODR:
            r, g, b = F.align_colors(self.Data_plan.DICT_PODR[podr]['Цвет'],level_percent= -5,saturation_percent=-10).split(";")
        CQT.set_color_text_header_wtab_vertical_c(tbl, i - 1, r, g, b, self.val_masht * 0.8, True)
        for j in range(self.count_tbl_field, len(self.dict_tbls_kpl_info[self.current_kpl_table][0])):
            if self.dict_tbls_kpl_info[self.current_kpl_table][i][j] != "":
                #for item in self.dict_tbls_kpl_info[self.current_kpl_table][i][j]:
                #CQT.add_color_wtab_c(tbl,i-1,j,int(r),int(g),int(b))
                CQT.set_color_wtab_c(tbl,i-1,j,int(r),int(g),int(b))
                CQT.font_cell_size_format(tbl,i-1,j,self.val_masht,bold=fact)
                #CQT.set_font_color_wtab_c(tbl,i-1,j,22,22,22)
    tbl.resizeColumnsToContents()
    if self.kpl_mode == 0:
        hide_free_columns(self,tbl)

    #self.ui.tbl_preview.setColumnWidth(0, self.val_masht*7.5)


    for field in self.list_for_hat:
        try:
            tbl.horizontalHeader().blockSignals(True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, field), False)
            tbl.horizontalHeader().blockSignals(False)
        except:
            pass
    if tbl_filtr != '':
        fields_hide = ['Пномер']
        for field in fields_hide:
            try:
                tbl.horizontalHeader().blockSignals(True)
                tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, field), True)
                tbl.horizontalHeader().blockSignals(False)
            except:
                pass

        fill_filtr_c(self, tbl_filtr, tbl,hidden_scroll=True)
        tbl_filtr.setVerticalHeaderLabels(['план_факт_подр'])
        tbl_filtr.setRowHeight(0, 25)
        for j in range(1, len(self.dict_tbls_kpl_info[self.current_kpl_table][0])):
            if self.dict_tbls_kpl_info[self.current_kpl_table][1][j] == 1:
                CQT.set_color_text_header_wtab_horisontal_c(tbl_filtr, j, 200, 11, 11, self.val_masht * 0.5, False)
            else:
                CQT.set_color_text_header_wtab_horisontal_c(tbl_filtr, j, 11, 11, 11, self.val_masht * 0.5, False)
        update_width_filtr(tbl,tbl_filtr)
    else:
        fields_hide = ['Этап','Пномер',"Проект","Поз.","Напр.",'Напр_д.']
        for field in fields_hide:
            try:
                tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, field), True)
            except:
                pass
    tbl.setRowHidden(0, True)
    tbl.setRowHidden(1, True)


def load_dict_poz_from_sql(pnom:int):
    query = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""SELECT plan.Пномер, plan.Позиция, plan.local_graf, plan.Приоритет, plan.fact_jurnal_blolb_data, 
            пл_оуп.№проекта, пл_оуп.№ERP, napravl_deyat.Псевдоним as Направление_деят, 
            napravlenie.name as Направление 
             FROM plan INNER JOIN 
            пл_оуп ON пл_оуп.НомПл = plan.Пномер, 
            napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности, 
            napravlenie ON napravlenie.Пномер = napravl_deyat.Направление 
             WHERE plan.Пномер == {pnom}""", rez_dict=True)
    if query == False or len(query) == 0:
        return False
    return query[0]

@CQT.onerror
def fill_gant_table(self: mywindow , tbl, tbl_filtr='', dict_form='', pnom=0):
    list_for_hat = ['Этап', 'Пномер', 'Проект', 'Поз.', 'Напр.', 'Напр_д.']

    def generate_list(self, pnom_kplan_select, list_for_hat,
                      DICT_PODR,DICT_REPLACE_BY_DAYS,
                      dict_form_list,min_date,max_date):
        list_tbl = []
        DICT_DAY_NAME = {1:'Пн',2:'Вт',3:'Ср',4:'Чт',5:'Пт',6:'Сб',7:'Вс'}
        set_podr = set()
        list_sablon = ["" for _ in list_for_hat]
        list_hat_full = copy.deepcopy(list_for_hat)
        list_vih = copy.deepcopy(list_sablon)
        list_dned = copy.deepcopy(list_sablon)
        for dict_form_item in dict_form_list:
            for date in dict_form_item['data'].keys():
                if max_date > date >= min_date:
                    list_hat_full.append(date)
                    list_vih.append(dict_form_item['data'][date]['Выходные'])
                    list_dned.append(dict_form_item['data'][date]['День недели'])
            list_tbl.append(list_hat_full)
            list_tbl.append(list_vih)
            list_tbl.append(list_dned)
            break
        list_tbl_info = copy.deepcopy(list_tbl)

        dict_errs = dict()
        for dict_form_item in dict_form_list:
            for date in dict_form_item['data'].keys():
                for podr in dict_form_item['data'][date]['podr'].keys():
                    set_podr.add(podr)
            tmp_list_podr = list(set_podr)
            tmp_list_podr.sort()
            list_podr = []
            for i in range(len(DICT_PODR)):
                for podr in tmp_list_podr:
                    podr_cut ="_".join(podr.split("_")[1:])
                    if podr_cut in DICT_PODR:
                        if DICT_PODR[podr_cut]['Порядок'] == i:
                            list_podr.append(podr)
            start_row = len(list_tbl)
            for podr in list_podr:
                list_tbl.append([podr,dict_form_item['pnom'],dict_form_item['proj'],dict_form_item['poz'],dict_form_item['napr'],dict_form_item['napr_deya']])
                list_tbl_info.append([podr,dict_form_item['pnom'],dict_form_item['proj'],dict_form_item['poz'],dict_form_item['napr'],dict_form_item['napr_deya']])


            for i in range(len(list_sablon),len(list_tbl[0])):
                for j in range(start_row,len(list_tbl)):
                    podr = list_tbl[j][0]
                    day = list_tbl[0][i]
                    if podr in dict_form_item['data'][day]['podr']:
                        list_vals = dict_form_item['data'][day]['podr'][podr]
                        time_rab = ''
                        if list_vals != '':
                            time_rab = 0
                            for val in list_vals:
                                time_rab += round(val['Время_час'])
                        list_tbl[j].append(time_rab)
                        list_tbl_info[j].append(list_vals)
                    else:
                        #CQT.msgbox(f'{podr} отсутствует в локальном графике, нужно обновить Пномер {str(dict_form_item["pnom"])}')
                        dict_errs[str(dict_form_item["pnom"])] = {'Этап':podr,'Пномер': str(dict_form_item["pnom"]),
                                                'Ошибка':'отсутствует в локальном графике, нужно обновить гант (включив гант, в таблице КПЛ клик на эту позицию с шифтом)'}


        if dict_errs:
            if self:
                CQT.msgboxg_get_table_ok_inf(self,'Ошибка в гантах',dict_errs)
            else:
                print('Ошибка в гантах')
                print(dict_errs )
            return None, None
        for i in range(len(list_sablon), len(list_tbl[0])):
            list_tbl[0][i] = F.datetostr(list_tbl[0][i], f"%d\n%m\n%y\n{DICT_DAY_NAME[int(list_tbl[2][i])]}")

        if self.current_kpl_table == 'tbl_preview':

            poz = Pozition(pnom_kplan_select, CFG.Config.project.db_kplan, CFG.Config.project.db_naryad,
                           CFG.Config.project.db_resxml, CFG.Config.project.db_users, self,load_day_plan=True)

            for field in DICT_REPLACE_BY_DAYS.keys():
                # print(field)
                for i_row in range(len(list_tbl)):
                    # print(f'    строка {i_row}')
                    if list_tbl[i_row][0] == field:
                        for j_clmn in range(6, len(list_tbl[0])):
                            list_tbl[i_row][j_clmn] = ''
                            for day in DICT_REPLACE_BY_DAYS[field].keys():
                                # print(f'        кол {j_clmn}')
                                if list_tbl[0][j_clmn].startswith(day):
                                    val3 = round(DICT_REPLACE_BY_DAYS[field][day] / 60, 3)
                                    val = round(val3, 1)
                                    if val3 > 0:
                                        podr_cut = "_".join(field.split("_")[1:])

                                        name_nach = DICT_PODR[podr_cut]['Имя_начала_этапа']
                                        name_zav = DICT_PODR[podr_cut]['Имя_конца_этапа']
                                        name_nach_f = DICT_PODR[podr_cut]['Имя_начала_этапа_факт']
                                        name_zav_f = DICT_PODR[podr_cut]['Имя_конца_этапа_факт']
                                        name_filed_hour = DICT_PODR[podr_cut]['Имя_поля'].split(';')[0]
                                        date_nach = ''
                                        date_zav = ''
                                        if field.startswith('план'):
                                            pass
                                            date_nach = poz.row_dates_etap_plan[f'{podr_cut}.{name_nach}']
                                            date_zav = poz.row_dates_etap_plan[f'{podr_cut}.{name_zav}']
                                        if field.startswith('факт'):
                                            pass
                                            date_nach = poz.row_dates_etap_fact[f'{podr_cut}.{name_nach_f}']
                                            date_zav = poz.row_dates_etap_fact[f'{podr_cut}.{name_zav_f}']
                                        time_hour = ''
                                        time_hour = poz.row_time_etap[f'{podr_cut}.{name_filed_hour}']
                                        data_et = {"Время_час": time_hour,
                                                   'Этап': f'{podr_cut}.{name_zav.lower().replace("нач", "").replace("зав", "")}',
                                                   "Начало": date_nach,
                                                   "Конец": date_zav,
                                                   "Имя_нз": [f'{podr_cut}.{name_nach}', f'{podr_cut}.{name_zav}'],
                                                   'По дню': val3
                                                   }

                                        if list_tbl_info[i_row][j_clmn] == '':
                                            list_tbl_info[i_row][j_clmn] = []
                                        list_tbl_info[i_row][j_clmn].append(data_et)
                                        list_tbl[i_row][j_clmn] = val
                                    else:
                                        list_tbl[i_row][j_clmn] = ''

        st_row = 3
        st_col = 6
        set_rows_to_add = set(range(st_row))
        for i, row in enumerate(list_tbl[st_row:]):
            if set(row[st_col:]) != {''}:
                set_rows_to_add.add(st_row+i)




        list_tbl = [val for _,val  in enumerate(list_tbl) if _ in set_rows_to_add]
        list_tbl_info = [val for _,val  in enumerate(list_tbl_info) if _ in set_rows_to_add]


        return list_tbl,list_tbl_info

    if dict_form == None  or dict_form == '' or dict_form == []:
        if self:
            if pnom == 0:
                tbl = self.ui.tbl_kal_pl
                r = tbl.currentRow()
                if r == None or r == -1:
                    return
                nk_pnom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
                if tbl.item(r, nk_pnom).text() == '-1':
                    return 
                pnom = int(tbl.item(r, nk_pnom).text())
        else:
            if pnom == 0:
                print(f'generate_list err pnom == 0')
                return

        dict_poz = load_dict_poz_from_sql(pnom)
        if dict_poz == False:
            return
        dict_form = F.from_binary_pickle(dict_poz['local_graf'])

    if dict_form == None:
        return
    min_date = F.strtodate('2020-01-01 00:00:01', "%Y-%m-%d %H:%M:%S")
    max_date = F.strtodate('2220-01-01 00:00:01', "%Y-%m-%d %H:%M:%S")

    if self:
        self.list_for_hat = list_for_hat
        if self.kpl_mode == 1:
            month = self.ui.de_vol_pl.date().toPyDate()
            month_end = self.ui.de_vol_pl_end.date().toPyDate()
            min_date = F.start_end_dates_c(F.date_to_datetime(month,0,0,1),'','m','')[0]
            max_date = F.start_end_dates_c(F.date_to_datetime(month_end,23,59,59),'','m','')[1]

        list_tbl, list_tbl_info = generate_list(self, pnom, list_for_hat,
                                                self.Data_plan.DICT_PODR,
                                                self.Data_plan.DICT_REPLACE_BY_DAYS,
                                                dict_form,
                                                min_date, max_date)

        self.dict_tbls_kpl[self.current_kpl_table],self.dict_tbls_kpl_info[self.current_kpl_table] = list_tbl,list_tbl_info

        if self.dict_tbls_kpl_info[self.current_kpl_table] == None:
            return
        #print(self.current_kpl_table)
        oforml_table(self, tbl, tbl_filtr)
    return True



def add_only_work_days(date1:datetime.datetime,time_delta:timedelta,self):

    db = CFG.Config.project.db_kplan
    if 'CMS_add_only_work_days_dict_month' not in self.__dict__:
        self.CMS_add_only_work_days_dict_month = dict()
    dict_month = self.CMS_add_only_work_days_dict_month

    def month_from_date(date:datetime.datetime):
        return F.datetostr(date, "m_cld_%Y_%m_01")

    def get_prod_cal(month:datetime.datetime):
        calendar = ProdCalendar(locale='ru')
        calendar_dict = calendar.month(month)
        calendar.close()
        return calendar_dict

    def get_month_cal(month:str):
        if CSQ.existence_table_c(db,month):
            return CSQ.custom_request_c(db,f"""SELECT * FROM {month} WHERE Пномер = 1""", one=True, rez_dict=True)
        else:
            calendar_dict = get_prod_cal(F.strtodate(month, "m_cld_%Y_%m_01"))
            return {F.datetostr(F.strtodate(k,"%Y.%m.%d" ),'d_%Y_%m_%d'): int(v) for k,v in calendar_dict.items()}


    def is_holy_or_week(date:datetime.datetime):
        date_str = F.datetostr(date,'d_%Y_%m_%d')
        month = month_from_date(date)
        if month not in dict_month:
            dict_month[month] = get_month_cal(month)
        return dict_month[month][date_str]


    days = 0
    new_date = copy.deepcopy(date1)
    while True:
        if days == time_delta.days:
            break
        new_date = new_date + timedelta(1)
        if is_holy_or_week(new_date):
            continue
        days+=1
    return new_date

@CQT.onerror
def add_action_config_save_tbl_filtrs(self,self_ui):
    if not hasattr(self, 'NAME_MODULE_BASE'):
        raise ValueError("Не задан self.NAME_MODULE_BASE")
        quit()
    self_ui.action_user_config = QtWidgets.QAction('Пользовательские настройки', self)
    if not hasattr(self_ui, 'menu'):
        print(f'Err add_action_config_save_tbl_filtrs no menu attr')
        quit()
    self_ui.menu.addSeparator()
    self_ui.menu.addAction(self_ui.action_user_config)
    self_ui.action_user_config.triggered.connect(lambda _: CFG.Config.user_config.gui_load(self))
    self_ui.menu.addSeparator()
    self.USER_CONFIG = CFG.Config.user_config


@CQT.onerror
def access_kpl_tbl(DICT_INFO_FIELDS_KPL:dict,full_name_field:str) -> bool:
    fl_access = True
    if DICT_INFO_FIELDS_KPL[full_name_field]['users_rule'] != "":
        if F.user_name() in DICT_INFO_FIELDS_KPL[full_name_field]['users_rule'].split(';'):
            if DICT_INFO_FIELDS_KPL[full_name_field]['rule_mode_1_disabled'] == 0:
                fl_access = True
            else:
                fl_access = False
        else:
            if DICT_INFO_FIELDS_KPL[full_name_field]['rule_mode_1_disabled'] == 0:
                fl_access = False
            else:
                fl_access = True
    return  fl_access


def calc_num_etap_from_name_etap(dict_etaps_from_erp,part_py,etap_name,s_num_kpl,Пномер_нар):
    fl = False
    part_py= str(part_py)
    if part_py in dict_etaps_from_erp:
        for val_etap in dict_etaps_from_erp[part_py]['Этапы']:
            if etap_name.strip() == val_etap['НаименованиеЭтапа'].strip(): #12.12.25
                fl = True
                return  val_etap
        if not fl:
            list_etaps_str = '\n'.join([f" {_['Number']} | {_['НаименованиеЭтапа']}"  for _ in dict_etaps_from_erp[part_py]['Этапы']])
            CQT.msgbox(f'В МЕС не найден этап для КПЛ {s_num_kpl}\nНомПартии_ЗП: {part_py}\n'
                       f'этап: `{etap_name}`\nнаряд: {Пномер_нар}\n Нужно обратиться в ПДО для корректировки\n\nТекущий список этапов:\n'
                       f' {list_etaps_str}')
            return
    else:
        CQT.msgbox(f'НомерПартииЗапуска {part_py} не найден в МЕС\n Нужно обратиться в ПДО для корректировки')

def create_nar_prosoy(self,fio:str,type_prost:int,db_nar,primech,koef,db_naryd,dop_prim_prost='',num_bad_bar=''):
    date_nar = F.now()

    stroka = [date_nar,
              name_by_empl_c(fio),
              0,
              CFG.Config.place.КодыНарядов.Простой,
              'ПРОСТОЙ',
              name_by_empl_c(fio),
              date_nar,
              '-',
              '-',
              name_by_empl_c(fio),
              '',
              '',
              '',
              1,
              '',
              '',
              '$',
              1,
              '',
              primech,
              koef, 0, type_prost, '', '']
    custom_request_c = f'''INSERT INTO naryad (Дата,	Автор,Номер_мк,Внеплан,Задание,Компл_ФИО,Компл_Дата,Компл_номер_тара,
                   Компл_адрес,ФИО,Фвремя,ФИО2,Фвремя2,Твремя,ДСЕ,ДСЕ_ID,Операции,Опер_время,Опер_колво,Примечание,Коэфф_сложности,
                   Подтвержд_вып,Категория_внепл,Виды_работ,Номер_замечания_журнал) VALUES ({", ".join(("?" * len(stroka)))});'''

    rez = CSQ.custom_request_c(db_naryd, custom_request_c, list_of_lists_c=[stroka])
    if rez == False:
        return False
    nom_new_nar = CSQ.custom_request_c(db_naryd, f"""SELECT Пномер FROM naryad WHERE Дата = '{date_nar}' 
                   AND Автор = '{name_by_empl_c(fio)}' ORDER BY Пномер DESC LIMIT 1""")
    try:
        if len(nom_new_nar) != 2 or F.is_numeric(nom_new_nar[-1][0]) == False:
            return False
    except:
        return False
    nom_new_nar = int(nom_new_nar[-1][0])
    if primech == "Ошибка нормирования и технологии":
        dict_status_out = DICT_STATUS_OUT
        nar = Naryads(int(num_bad_bar),db_naryd)
        nar.get_mk()
        kplan = nar.mk.НомКплан
        line = [kplan, nar.Номер_мк, F.now(), self.glob_login,
                f'Ошибка нормирования и технологии ({dop_prim_prost.strip()}) по наряду {num_bad_bar}', int(0), dict_status_out[4],int(num_bad_bar),nom_new_nar]
        CSQ.custom_request_c(self.db_naryd, f"""INSERT INTO jur_vnepl (Кплан_номер, МК, Дата, ФИО,
         Запрос, Кплан_номер, Статус, Номер_наряда_с_ошибкой, Номер_внепланового_наряда)
                                      VALUES ({CSQ.questions_for_mask(line)});""", list_of_lists_c=[line])
    return nom_new_nar


@CQT.onerror
def DICT_PRICE_BRAK(db_naryd):
    return F.deploy_dict_c(CSQ.custom_request_c(db_naryd,f"""SELECT * FROM brak_price""",rez_dict=True),"Имя")

@CQT.onerror
def load_tree(self, spis_xml: list,tree):
    # tree.setColumnCount(10)
    list_user = ["Наименование"
        , "Обозначение полное"
        , "Количество"
        , "Ед.изм."
        , "Масса/М1,М2,М3"
        , "Ссылка на объект DOCs"
        , "ID"
        , "Количество на изделие"
        , "Примечание"
        , 'Покупное изделие'
        , "Классификатор изделия"
        , "Код ERP"
        , 'Раздел'
                 ]
    set_hat_c = set()
    for item in spis_xml:
        for name in item['data'].keys():
            set_hat_c.add(name)
    list_hat_c = sorted(list(set_hat_c))

    for item in list_hat_c:
        if item not in list_user:
            list_user.append(item)
    list_user.append('Уровень')
    iter = 0
    tree.clear()
    self.ui.tree_base_tree.setColumnCount(len(list_user))
    for item in list_user:
        tree.headerItem().setText(iter, QtCore.QCoreApplication.translate("MainW", item))
        iter += 1

    for _ in range(0, len(list_user)):
        tree.resizeColumnToContents(_)

    tree.setSelectionBehavior(1)
    CQT.set_color_sort_cell_table_c(tree)
    tree.setSelectionMode(1)

    # tree.setColumnWidth(1, int(tree.width() * 0.1))
    # tree.setColumnWidth(0, int(tree.width() - tree.columnWidth(1) - 81) - 5)
    tree.setStyleSheet(
        "QTreeView {background-color: rgb(212, 212, 212);} QTreeView::item:hover {background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop:"
        " 0 #e7effd, stop: 1 #cbdaf1);border: 1px solid #bfcde4;} ")
    tree.setFocusPolicy(15)
    return list_user

@CQT.onerror
def check_cad_xml(lst_xml: list[dict]):
    pattern = r'^0x[0-9a-fA-F_]'
    for item in lst_xml:
        item_id = item['ID']
        if re.match(pattern, item_id):
            return True

@CQT.onerror
def prepare_lst_from_cad(lst_xml: list[dict]):
    form_for_material = '{mat1} {mat2} / {mat3}'
    val_or_empty_str = lambda key, elem: (elem.get(key, '') or '').strip()
    mat1_and_mat2_is_empty = lambda item: not val_or_empty_str('Материал2', item) and not  val_or_empty_str('Материал3', item)
    new_result = []
    for item in lst_xml:
        type_element = item['data'].get('Раздел')
        cp_item = copy.deepcopy(item)
        code = ''
        if type_element in ('Спецификации\Детали',):
            data = item['data']
            if mat1_and_mat2_is_empty(data):
                full_name = val_or_empty_str('Материал', data)
            else:
                full_name = form_for_material.format(
                    mat1=val_or_empty_str('Материал', data),
                    mat2=val_or_empty_str('Материал2', data),
                    mat3=val_or_empty_str('Материал3', data)
                )
            with CDOCS.TFlexMaterialFinderClient() as client:
                status_code, code = client.get_kod_erp_by_mat(full_name)
                if status_code != 200:
                    CQT.msgbox(code)
                    return
        if type_element in ('Спецификации\Стандартные изделия', 'Спецификации\Материалы', 'Спецификации\Прочие изделия'): #02.06.2025
            with CDOCS.TFlexMaterialFinderClient() as client:
                code = client.get_kod_erp_by_standard_izd(item['data']['Наименование'])
        cp_item['data']['Код ERP'] = code
        new_result.append(cp_item)
    return new_result


@CQT.onerror
def check_code_erp_for_pki_dse(self, lst_xml):
    def oform_correct_table(tbl: QtWidgets.QTableWidget):
        nk_btn = CQT.num_col_by_name_c(tbl, 'Подобрать')
        nk_code = CQT.num_col_by_name_c(tbl, 'Код ERP')

        def on_clicked_wrap_tbl(row: int, col: int):
            item = CQT.msgboxg_get_table(
                tbl.parentWidget(),
                'Выбор номенклатуры',
                response,
                ExtendedSelection=False
            )
            if isinstance(item, dict) and 'Код' in item:
                tbl.item(row, nk_code).setText(item['Код'])

        response = CSQ.custom_request_c(
            F.scfg('nomenklatura_erp'),
            'SELECT Наименование, Вид, Код FROM nomen WHERE На_удаление = 0',
            rez_dict=True
        )
        for row in range(tbl.rowCount()):
            CQT.add_btn(tbl, row, nk_btn, 'Подобрать', conn_func_checked_row_col=on_clicked_wrap_tbl)
    msg_lst = [['ID', 'Наименование', 'Обозначение', 'Покупное', 'Подобрать', 'Код ERP']]
    for idx, item in enumerate(lst_xml):
        code_erp = item['data'].get('Код ERP')
        is_pki = item['data']['Покупное изделие'] == '1'
        nn = item['data']['Обозначение полное']
        name = item['data']['Наименование']
        if is_pki and str(code_erp).strip() == '':
            msg_lst.append([idx, name, nn, is_pki, '', ''])
    if len(msg_lst) <= 1:
        return lst_xml # 25.04.25
    result = CQT.msgboxg_get_table(
        self,
        'Отсутсвует Код ERP у покупных деталей',
        msg_lst,
        func_oform_tbl=oform_correct_table,
        func_validate=lambda res: res,
        btn0_name='Подтвердить',
        btn1_name='Отменить'
    )
    if result:
        for res in result:
            idx_lst = res['ID']
            code_erp = res['Код ERP']
            if code_erp == '':
                return
            lst_xml[int(idx_lst)]['data']['Код ERP'] = code_erp
        return lst_xml
    return
# ++12.11.25
@CQT.onerror
def XML_check_root_on_project_product_type(putt_xml):
    data = XML.spisok_iz_xml(putt_xml)
    for idx, first_item in enumerate(data):
        return first_item['data']['Тип'] == 'Изделие проекта'
    return False

# def XML_validate_type_element(xml_head: int, element: dict, logical_index: int) -> bool:
def XML_get_unavailable_xml_types(xml_head: int):
    poki = CFG.Config.place.poki
    db_nomen = CFG.Config.project.db_nomen
    where = ''
    if xml_head == 1:
        where = ' and resxml_head_state != 1'
    return CSQ.custom_request_c(
        db_nomen,
        f'SELECT Имя FROM ТипДсе WHERE poki = {poki} AND Вкл = 0{where}',
        hat_c=False,
        one_column=True
    )
# --12.11.25

@CQT.onerror
def podgotovka_xml(self, spis_xml: list, xml_head='', show_negruz=False, correct_code_erp_tbl: bool = False):
    if spis_xml == None:
        return
    rez = []
    exclude_types = XML_get_unavailable_xml_types(xml_head)  #++ 12.11.25
    # if xml_head == '':
    #     self.xml_head = 0
    # else:
    #     self.xml_head = xml_head
    if check_cad_xml(spis_xml): #10.04.25 убрал именованые аргументы
        spis_xml = prepare_lst_from_cad(spis_xml)
        if spis_xml == None:
            return
    for i in range(len(spis_xml)):
        if spis_xml[i]['data']['Покупное изделие'] == '1':
            if spis_xml[i]['data']['Обозначение полное'].strip() == '':
                spis_xml[i]['data']['Обозначение полное'] = F.shifr(spis_xml[i]['data']['Наименование'])[:13]
        else:
            if spis_xml[i]['data']['Обозначение полное'].strip() == '' and spis_xml[i]['data']['Тип'] not in self.TIP_NEGRUZ_DSE:
                if CQT.msgboxgYN(f"{spis_xml[i]['data']['Наименование']} не имеет 'Обозначение' и отмечена как 'не покупная' отметить как 'покупная'?"):
                    spis_xml[i]['data']['Обозначение полное'] = F.shifr(spis_xml[i]['data']['Наименование'])[:13]
                    spis_xml[i]['data']['Покупное изделие'] = '1'
                else:
                    CQT.msgbox(
                        f"Ошибка {spis_xml[i]['data']['Наименование']} {spis_xml[i]['data']['Обозначение полное']} не имеет Обозначение/не покупная")
                    return
        if 'Классификатор изделия' in spis_xml[i]['data']:
            if spis_xml[i]['data']['Классификатор изделия'] == None:
                spis_xml[i]['data']['Классификатор изделия'] = ''

        if 'Код_ERP' in spis_xml[i]['data'].keys() and 'Код ERP' not in spis_xml[i]['data'].keys():
            spis_xml[i]['data']['Код ERP'] = spis_xml[i]['data']['Код_ERP'].strip()

        mat = "/".join(
            (str(spis_xml[i]['data']['Масса']).replace(',', '.'),
             F.clear_row_for_file_name_c(str(spis_xml[i]['data']['Материал'])),
             F.clear_row_for_file_name_c(str(spis_xml[i]['data']['Материал2'])),
             F.clear_row_for_file_name_c(str(spis_xml[i]['data']['Материал3']))))
        spis_xml[i]['data']['Масса/М1,М2,М3'] = mat
        spis_xml[i]['data'].pop('Материал', None)
        spis_xml[i]['data'].pop('Материал2', None)
        spis_xml[i]['data'].pop('Материал3', None)
        spis_xml[i]['data']['Наименование'] = F.clear_row_for_file_name_c(spis_xml[i]['data']['Наименование'])
        spis_xml[i]['data']['Обозначение полное'] = F.clear_row_for_file_name_c(
            spis_xml[i]['data']['Обозначение полное'])
        if 'Сводное наименование' in spis_xml[i]['data']:
            spis_xml[i]['data']['Сводное наименование'] = F.clear_row_for_file_name_c(
                spis_xml[i]['data']['Сводное наименование'])

        if 'Тип' in spis_xml[i]['data']:
            if show_negruz:
                rez.append(spis_xml[i])
            else:
                if spis_xml[i]['data']['Тип'] not in exclude_types: # 12.11.25
                    rez.append(spis_xml[i])
                else:
                    tek_ur = spis_xml[i]['level_c']
                    if i == 0:
                        pred_ur = -1
                    else:
                        pred_ur = spis_xml[i - 1]['level_c']
                    delta_ur = tek_ur - pred_ur
                    for j in range(i + 1, len(spis_xml)):
                        if spis_xml[j]['level_c'] <= tek_ur:
                            break
                        spis_xml[j]['level_c'] -= delta_ur
        else:
            rez.append(spis_xml[i])
    if correct_code_erp_tbl:
        rez = check_code_erp_for_pki_dse(self, rez)
        if not rez:
            return
    return rez

@CQT.onerror
def check_id_peresil(self,nom_nar:int,parol_from_user,kod_oper=1):
    def check_parol(self,nom_nar:int,parol_from_user:str):
        query = f"""SELECT * FROM log_peresiln WHERE num_nar == {nom_nar}"""
        rez= CSQ.custom_request_c(self.db_naryd,query,rez_dict=True)
        if rez == False or rez == None:
            CQT.blink_obj_c(self, 2, self.ui.le_id_peresil,f'Ошибка доступа к базе пересыльных')
            return False
        if rez == []:
            CQT.blink_obj_c(self, 2, self.ui.le_id_peresil,f'Пересыльный на наряд {nom_nar} не распечатан диспетчером')
            return False
        rez = rez[0]
        if F.computer_name() == rez['pc'] or F.user_name() == rez['account_win'] or self.glob_fio == rez['user_name']:
            CQT.blink_obj_c(self, 2, self.ui.le_id_peresil, f'Работу с пересыльными выполняют диспетчер и комплектовщик честно и самостоятельно')
            return False
        db_parol = rez['password']
        if str(db_parol) != parol_from_user:
            CQT.blink_obj_c(self, 2, self.ui.le_id_peresil, f'Не корректный ID пересыльного листа на наряд {nom_nar} (предоставляется на бумаге диспетчером)')
            return False
        return True

    nar_info = CSQ.custom_request_c(self.db_naryd, f'''SELECT naryad.Операции, mk.check_execute_opers FROM naryad 
     INNER JOIN mk ON naryad.Номер_мк == mk.Пномер WHERE naryad.Пномер == {nom_nar}''',rez_dict=True)
    if nar_info == False or nar_info== None:
        CQT.msgbox(f'ОШибка загрузки наряда')
        return False
    nar_info = nar_info[0]
    if nar_info['check_execute_opers'] == 0:
        print(f'{nom_nar} check_execute_opers = 0 не проверяется на выполенние предыдущего')
        return True

    fl_necessary_check = False
    list_opers = nar_info['Операции'].split('|')
    for oper in list_opers:
        nomoper, opername = oper.split('$')
        kod = ''
        for key in self.DICT_OPER.keys():
            if self.DICT_OPER[key]['name'] == opername:
                kod = key
                break
        if kod == '':
            continue
        if self.DICT_OPER[kod]['necessary_check_execute'] == kod_oper:
            fl_necessary_check = True
            break
    if not fl_necessary_check:
        return True
    if parol_from_user.strip() == '' or F.is_numeric(parol_from_user) == False:
        CQT.blink_obj_c(self, 2, self.ui.le_id_peresil, f'Не заполнен ID пересыльного листа на наряд {nom_nar} (предоставляется диспетчером с комплектом ДСЕ)')
        return False
    if not check_parol(self,nom_nar,parol_from_user):
        return False
    return True

def get_list_fio_otk(db_naryd,row_fio_or_nars,):
    if '|' in row_fio_or_nars:
        return row_fio_or_nars
    else:
        list_fio_otk = CSQ.custom_request_c(db_naryd,
                                            f"""SELECT naryad.ФИО , naryad.ФИО2 FROM naryad WHERE naryad.Пномер in ({row_fio_or_nars})""",
                                            rez_dict=True)
        if list_fio_otk == None or len(list_fio_otk) == 0:
            return ''
        else:
            set_users = set()
            for item in list_fio_otk:
                set_users.add(item['ФИО'])
                set_users.add(item['ФИО2'])
            set_users.discard('')

            return '|'.join(list(set_users))

def check_existence_peresil(self,nom_nar:int):
    query = f"""SELECT * FROM log_peresiln WHERE num_nar == {nom_nar}"""
    rez = CSQ.custom_request_c(self.db_naryd, query, rez_dict=True)
    if rez == False or rez == None:
        CQT.blink_obj_c(self, 2, self.ui.le_id_peresil, f'Ошибка доступа к базе пересыльных')
        return False
    if rez == []:
        #CQT.blink_obj_c(self, 2, self.ui.le_id_peresil, f'Пересыльный на наряд {nom_nar} не распечатан диспетчером')
        return
    return rez[0]

@CQT.onerror
def get_parent_dse(self, res, dse, list_predv_opers):
    list_dse = []
    ur = dse['Уровень']
    for i in range(dse['Номерпп'], len(res)):
        if res[i]['Уровень'] <= ur:
            break
        if res[i]['Уровень'] == ur + 1:
            print(f"Родитель {res[i]['Наименование']} {res[i]['Номенклатурный_номер']} учтен")
            if res[i]['Операции']:
                oper = res[i]['Операции'][-1]
                if self.DICT_OPER[oper['Опер_код']]['kontrol_opers']:
                    continue
                prev_osv = oper.get('Освоено,шт.', 0)
                prev_zav = oper.get('Закрыто,шт.', 0)
                prev_oper_nom = oper['Опер_номер']
                prev_oper_name = oper['Опер_наименование']
                prev_oper_rc = oper['Опер_РЦ_код']
                prev_oper_kod = oper['Опер_код']
                koef = res[i]['Количество_ед']
                prev_kol = res[i]['Количество']
                list_predv_opers.append({'dse_id':res[i]['Номерпп'],'dse': f"{res[i]['Наименование']} {res[i]['Номенклатурный_номер']}",
                                     'prev_kol': prev_kol / koef, 'prev_osv': prev_osv / koef,
                                     'prev_zav': prev_zav / koef, 'prev_oper_nom': prev_oper_nom,
                                     'prev_oper_name': prev_oper_name,
                                     'prev_oper_rc': prev_oper_rc, 'prev_oper_kod': prev_oper_kod})

    return list_predv_opers


@CQT.onerror
def check_execution_previous_operations(self,nom_nar,lvl_check=1,check_by_vip=True):
    #check_by_vip выполнение чекает иначе создание
    list_notes = []
    def check_oper(self,oper,lvl_check):
        def get_previous_oper(res, dse_id, oper_nom,list_predv_opers):



            prev_osv = ''
            prev_zav = ''
            prev_oper_nom = ''
            prev_oper_name = ''
            prev_oper_rc = ''
            dse= ''
            prev_oper_kod = ''
            for dse_i in res:
                if dse_i['Номерпп'] == dse_id:
                    dse = dse_i
                    break
            if dse == '':
                print(f'{nom_nar} не найдена операция {dse_id}')
                return False
            prev_kol = dse['Количество']
            fl = False
            for i in range(len(dse['Операции'])):
                if dse['Операции'][i]['Опер_номер'] == oper_nom:
                    if i == 0:
                        #print(f'{nom_nar} первая операция не проверяется на выполенние предыдущей')
                        list_predv_opers = get_parent_dse(self,res,dse,list_predv_opers)
                        return list_predv_opers
                    oper = dse['Операции'][i - 1]
                    prev_osv = oper.get('Освоено,шт.', 0)
                    prev_zav = oper.get('Закрыто,шт.', 0)
                    prev_oper_nom = oper['Опер_номер']
                    prev_oper_name = oper['Опер_наименование']
                    prev_oper_rc = oper['Опер_РЦ_код']
                    prev_oper_kod = oper['Опер_код']

                    fl = True
                    break
            if fl == False:
                return fl
            list_predv_opers.append({'dse_id':dse['Номерпп'],'dse':f"{dse['Наименование']} {dse['Номенклатурный_номер']}",
                                     'prev_kol':prev_kol, 'prev_osv':prev_osv,
                                    'prev_zav':prev_zav, 'prev_oper_nom':prev_oper_nom, 'prev_oper_name':prev_oper_name,
                                'prev_oper_rc':prev_oper_rc,'prev_oper_kod':prev_oper_kod, 'dse_id':dse_id})
            return list_predv_opers

        def get_oper_kod(prev_oper_name):
            oper_kod = ''
            for key in self.DICT_OPER.keys():
                if self.DICT_OPER[key]['name'] == prev_oper_name:
                    oper_kod = key
                    break
            if oper_kod == '':
                return False
            return oper_kod

        list_predv_opers = []
        list_predv_opers = get_previous_oper(res, oper['ДСЕ_ID'], oper['Операции_номер'],list_predv_opers)
        if list_predv_opers == True:
            return True
        if list_predv_opers == False:
            list_notes.append(f'Ошибка при обработке предыдущих операций,  {oper["ДСЕ"]} операция {oper["Операции_номер"]}')
            return False

        for pred_oper in list_predv_opers:
            if pred_oper['prev_oper_kod'] == '':
                pred_oper['prev_oper_kod'] = get_oper_kod(pred_oper['prev_oper_name'])
            if pred_oper['prev_oper_kod'] == False or pred_oper['prev_oper_kod'] == '':
                list_notes.append(f"Для операции {pred_oper['prev_oper_name']} не найден код в БД")
                return False
            if self.DICT_OPER[pred_oper['prev_oper_kod']]['necessary_check_execute'] != 0:
                if self.DICT_OPER[pred_oper['prev_oper_kod']]['necessary_check_execute'] == lvl_check:

                    comparable = pred_oper['prev_osv']
                    postfix = 'не РАСПРЕДЕЛЕНЫ(не созданы наряды) работы!'
                    if check_by_vip:
                        comparable = pred_oper['prev_zav']
                        postfix = f'не ЗАВЕРШЕНЫ работы! не выполнен наряд №: '
                    if oper['Опер_колво'] > comparable:
                        if check_by_vip:
                            list_naryads = CSQ.custom_request_c(self.db_naryd,f"""SELECT naryad.Пномер FROM naryad 
                            WHERE naryad.Номер_мк in (SELECT naryad.Номер_мк FROM naryad WHERE naryad.Пномер = {nom_nar}) 
                            AND naryad.Задание LIKE '%{f"{pred_oper['prev_oper_nom']}${pred_oper['prev_oper_name']}"}%'""",hat_c=False,one_column=True)
                            postfix += f" {','.join([str(_) for _ in list_naryads])}"
                        msg =  f"""Для ДСЕ "{oper['ДСЕ']}", операция "{oper['Операции_номер']}  {oper['Операции_имя']} " не выполнено условие: \n
                        на предыдущей операции в ДСЕ 
                        "{pred_oper['dse']}", операция "{pred_oper['prev_oper_nom']} {pred_oper['prev_oper_name']}"  
                        РЦ "{pred_oper['prev_oper_rc']}", \n
                        {postfix} \n
                        Нужно всего {oper["Опер_колво"]} шт.,    но на {F.now()} завершено {comparable} шт."""
                        list_notes.append(msg)

        if len(list_notes)>0:
            return False
        return True

    def nar_to_dict(nar:dict):
        rez_list = []
        list_dse_id = nar['ДСЕ_ID'].split('|')
        list_dse = nar['ДСЕ'].split('|')
        list_opers = nar['Операции'].split('|')
        list_kolvo = nar['Опер_колво'].split('|')
        for i in range(len(list_dse_id)):
            dse_id = int(list_dse_id[i])
            oper_nom, oper_name = list_opers[i].split('$')
            kolvo = int(list_kolvo[i])
            dse = list_dse[i]
            rez_list.append({'ДСЕ':dse,'ДСЕ_ID':dse_id,'Операции_номер':oper_nom,'Операции_имя':oper_name,'Опер_колво':kolvo})
        return rez_list

    query = f"""SELECT naryad.ДСЕ_ID, naryad.Операции, naryad.Опер_колво, naryad.Номер_мк, 
    naryad.ДСЕ, naryad.Внеплан, mk.check_execute_opers FROM naryad  INNER JOIN mk 
    ON mk.Пномер = naryad.Номер_мк WHERE naryad.Пномер = {nom_nar}"""
    nar = CSQ.custom_request_c(self.db_naryd,query,rez_dict=True,one=True)

    if nar['Внеплан'] != 0:
        print(f'{nom_nar} Внеплан не проверяется на выполенние предыдущего')
        return True
    if nar['check_execute_opers'] == 0:
        print(f'Наряд {nom_nar} check_execute_opers = 0 не проверяется на выполенние предыдущего')
        return True
    res = load_res(nar['Номер_мк'])
    list_opers = nar_to_dict(nar)
    #query_acces = CSQ.custom_request_c(self.db_naryd,f'''SELECT * FROM permissions WHERE action == "cms_list_necessarily_check_opers";''',rez_dict=True)
    for oper in list_opers:
        rez_check_oper = check_oper(self,oper,lvl_check)
    if len(list_notes) > 0 :
        CQT.msgbox('\n\n'.join(list_notes))
        return False
    return True




def dict_calend_days(db_users):
    list_tabels = CSQ.get_list_of_tables_c(db_users)
    dict_days = dict()
    for tbl in list_tabels:
        if tbl[:4] == 'mtdz_20':
            rez = CSQ.custom_request_c(db_users,f"""SELECT * FROM {tbl} WHERE Пномер =1""",rez_dict=True,one=True)
            for key in rez:
                if F.is_date(key,'d_%Y_%m_%d'):
                    dict_days[key]= rez[key]
    return dict_days
#dict_calend_days(r'Z:\\Data\\BD_users.db')



def edit_key_winreg_hkey_current_user(REG_PATH,name,type_reg,val):
    """winreg.REG_BINARY
Binary data in any form.

winreg.REG_DWORD
32-bit number.

winreg.REG_DWORD_LITTLE_ENDIAN
A 32-bit number in little-endian format. Equivalent to REG_DWORD.

winreg.REG_DWORD_BIG_ENDIAN
A 32-bit number in big-endian format.

winreg.REG_EXPAND_SZ
Null-terminated string containing references to environment variables (%PATH%).

winreg.REG_LINK
A Unicode symbolic link.

winreg.REG_MULTI_SZ
A sequence of null-terminated strings, terminated by two null characters. (Python handles this termination automatically.)

winreg.REG_NONE
No defined value type.

winreg.REG_QWORD
A 64-bit number."""
    dict_type = {"REG_BINARY": winreg.REG_BINARY,
    "REG_DWORD": winreg.REG_DWORD,
    "REG_DWORD_LITTLE_ENDIAN": winreg.REG_DWORD_LITTLE_ENDIAN,
    "REG_DWORD_BIG_ENDIAN": winreg.REG_DWORD_BIG_ENDIAN,
    "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
    "REG_LINK": winreg.REG_LINK,
    "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
    "REG_NONE": winreg.REG_NONE,
    "REG_QWORD": winreg.REG_QWORD,
    "REG_QWORD_LITTLE_ENDIAN": winreg.REG_QWORD_LITTLE_ENDIAN,
    "REG_RESOURCE_LIST": winreg.REG_RESOURCE_LIST,
    "REG_FULL_RESOURCE_DESCRIPTOR": winreg.REG_FULL_RESOURCE_DESCRIPTOR,
    "REG_RESOURCE_REQUIREMENTS_LIST": winreg.REG_RESOURCE_REQUIREMENTS_LIST,
    "REG_SZ": winreg.REG_SZ,
    }
    if type_reg not in dict_type:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH,  0, winreg.KEY_READ) as key:
            value, regtype = winreg.QueryValueEx(key, name)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH,  0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, name, 0, dict_type[type_reg],val)
    except WindowsError:
        return False
    return True

def route_allocation_c(list_rc):
    """ПРинимает список маршрутов с РЦ и распределеяет их в единиый маршрут"""
    set_all_mr = set()
    for mr in list_rc:
        for rc in mr:
            set_all_mr.add(rc)
    list_sorted_rc = list(set_all_mr)
    list_sorted_rc = sorted(list_sorted_rc, key=lambda x: F.valm(x))

    for mr in list_rc:
        poz = 0
        for rc in mr:
            fl = False
            for i in range(poz,len(list_sorted_rc)):
                if rc == list_sorted_rc[i]:
                    fl = True
                    poz = i+1
                    break
            if not fl:
                list_sorted_rc.insert(poz,rc)
                poz +=1
    rez = []
    for mr in list_rc:
        tmp_row = []
        for j, rc in enumerate(mr):
            while len(tmp_row) < len(list_sorted_rc):
                if list_sorted_rc[len(tmp_row)] == rc:
                    tmp_row.append(rc)
                    break
                else:
                    tmp_row.append('')
        while len(tmp_row) < len(list_sorted_rc):
            tmp_row.append('')
        rez.append(tmp_row)
    rez.insert(0,copy.deepcopy(list_sorted_rc))
    list_del_columns = []
    for j in range(len(rez[0])):
        fl = True
        for i in range(1,len(rez)):
            if rez[i][j] != '':
                fl = False
                break
        if fl:
            list_del_columns.insert(0,j)
    rez = F.delete_column(rez,numbers_del = list_del_columns)
    return rez
    #old_calc=====================
    def fix_len_lines_to_same(list_rc):
        max_len = 0
        for item in list_rc:
            if len(item) > max_len:
                max_len = len(item)
        for i in range(len(list_rc)):
            for _ in range(max_len - len(list_rc[i])):
                list_rc[i].append('')
        return list_rc
    def check_table(list_rc):
        def val_rc(rc):
            return F.valm(rc)

        hat_c = []
        j = 0
        while True:
            if j == len(list_rc[0]):
                break
            list_rc = fix_len_lines_to_same(list_rc)
            ceil = list_rc[0][j]
            for i in range(len(list_rc)):
                rc = list_rc[i][j]
                if ceil == '':
                    ceil = rc
                if rc == '':
                    continue
                if rc != ceil:
                    if val_rc(rc) > val_rc(ceil):  # все что до нее добавить в конец пусто, все что полсле нее вправо
                        list_rc[i].insert(j, '')
                    else:  # все что до нее вправо, все что полсле нее добавить в конец пусто
                        for k in range(i):
                            list_rc[k].insert(j, '')
                        ceil = rc

            hat_c.append(ceil)
            if ceil == '':
                break
            j += 1

        list_rc.insert(0, hat_c)
        return list_rc
    list_rc = check_table(list_rc)
    return list_rc


def load_ip_srv(self):
    self.ip_srv = ''
    paths = [r'Z:\MES_setup\ip_srv_mes.txt', r'Z:\ProdSoft\MES_setup\ip_srv_mes.txt']
    IP = ""
    for path in paths:
        path = os.path.normpath(path)
        if os.path.exists(path):
            try:
                self.ip_srv = F.open_file_c(path)[0]
            except:
                pass
@CQT.onerror
def load_tkp_list(self, db_dse, dict_alias,  tbl_list_tkp, tbl_list_tkp_filtr,set_editeble_col_nomera= {}, date_res = None, include_deleted=False):
    prefix =''
    if not include_deleted:
        prefix = "status != 'На удаление' and "
    form = prefix + "(date_res == '' or {postfix})" #07.04.25
    start_str_date = F.datetostr(F.add_months(F.now(''), -6))
    stop_str_date = F.datetostr(F.now(''))
    if isinstance(date_res, int):
        form = "{postfix}"
        start_str_date = F.datetostr(datetime.datetime(year=date_res, month=1, day=1))
        stop_str_date = F.datetostr(datetime.datetime(year=date_res + 1, month=1, day=1))
    postfix = f"""(datetime(date_res) >= datetime('{start_str_date}') and datetime(date_res) <= datetime('{stop_str_date}'))"""
    where = form.format(postfix=postfix)
    list_tkp = CSQ.custom_request_c(db_dse, f"""SELECT s_nom, 
        date_create, 
        vid_tkp.name as type_tkp, 
        user_create, 
        name_tkp,
        nnom_izd,  
        nnom_tkp, 
        dir_rkd, 
        status, 
        name_prices.name AS "Проверка цены",
        resp_technolog, 
        date_res,
        name_res,
        вид_по_напр,
         weight_wh_pki,
         predv_res.Имя as "Выгружено в 1С"
         FROM tkp 
            INNER JOIN vid_tkp ON vid_tkp.Pnom = tkp.type_tkp
           INNER JOIN name_prices ON name_prices.s_num = tkp.check_prices
           LEFT JOIN predv_res ON predv_res.Имя = tkp.name_res
        WHERE {where};
        """,rez_dict=True,attach_dbs=(CFG.Config.project.db_resxml))
    dict_loaded_res_erp = dict()
    #dict_loaded_res_erp = F.deploy_dict_c(CSQ.custom_request_c(CFG.Config.project.db_resxml, f"""SELECT Пномер,
    #   Имя
    #    FROM predv_res;
    #    """,rez_dict=True), 'Имя')

    for i in range(len(list_tkp)):
        if int(list_tkp[i]['вид_по_напр']) in self.Data_plan.DICT_VID_PO_NAPR:
            list_tkp[i]['вид_по_напр'] = self.Data_plan.DICT_VID_PO_NAPR[int(list_tkp[i]['вид_по_напр'])]['Имя']
        if not list_tkp[i]["Выгружено в 1С"]:
            continue
            compares_indirect = [_ for _ in dict_loaded_res_erp.keys() if f'ТКПА_{list_tkp[i]["s_nom"]}_' in _ ]
            if compares_indirect:
                list_tkp[i]["Выгружено в 1С"] = '; '.join(compares_indirect)
                CSQ.custom_request_c(self.db_dse, f"""UPDATE tkp SET (name_res) = (?) WHERE s_nom = ?""",
                                         list_of_lists_c=[[compares_indirect[-1], list_tkp[i]["s_nom"]]])
                print(f'поправлено {compares_indirect[-1]} для ТКПА_{list_tkp[i]["s_nom"]}')

            else:
                print(f'Не найден predv_res для ТКПА_{list_tkp[i]["s_nom"]}')



    list_tkp = F.list_of_dicts_to_list_of_lists(list_tkp)
    list_tkp = CSQ.apply_alias_list(list_tkp, dict_alias)

    CQT.fill_wtabl(list_tkp, tbl_list_tkp, set_editeble_col_nomera=set_editeble_col_nomera,select_last_row=True,load_links=True)
    fill_filtr_c(self, tbl_list_tkp_filtr, tbl_list_tkp, hidden_scroll=True)
    update_width_filtr(tbl_list_tkp, tbl_list_tkp_filtr)



def kontrol_ver(ver, ima):
    print('===== Контроль версий =====')
    rez = check_ver(ver, ima)
    if rez == False:
        CQT.msgbox("    Ошибка проверки обновления")
        print(f'    Ошибка проверки обновления')
        print('===== Неудачно =====')
        return False
    else:
        if rez != True:
            CQT.msgbox(rez)
            print('===== Неудачно =====')
            setup_puth = r'Z:\Setup\Setup.exe'
            if F.existence_file_c(setup_puth):
                os.startfile(r'Z:\Setup\run.bat')
            else:
                print(f'Err kontrol_ver {setup_puth} not found')
            # subprocess.Popen([r'Z:\\Setup\\py\\python.exe', r'Z:\\Setup\Setup.py'], shell=True)
            return False
    return True

def right_global_path():
    path = F.scfg('setup') + r'\list.txt'
    if F.existence_file_c(path) == False:
        print(f"     {path} не найден (CMS.right_global_path)")
        return False
    return F.sep().join(F.scfg('setup').split(F.sep())[:-1]) + F.sep()

def wrong_global_path():
    return  'Z:\\ProdSoft\\'

def fix_path_mes_setup(put):
    goal = wrong_global_path()
    new_path = right_global_path()
    if right_global_path() == False:
        return False
    return put.replace(goal, new_path)



def check_last_entry(last_date_update: str) -> bool:
    key = 'LAST_ENTRY_IN_APP'
    format_date = '%Y-%m-%d %H:%M'
    now = datetime.datetime.now()
    now_str = now.strftime(format_date)
    if last_entry := os.environ.get(key):
        datetime_last = datetime.datetime.strptime(last_entry, format_date)
        if F.is_date(last_date_update, format_date) and datetime_last < datetime.datetime.strptime(last_date_update, format_date):
            CQT.msgbox('Версия устарела, просим Вас перезапустить клиент')
            return sys.exit(-1)
        if (now - datetime_last).total_seconds() / 3600 >= 15:
            msg = '''Клиент запущен более 15 часов, просим Вас перезапускать приложение хотя бы в начале рабочего дня т.к. за длительный период могло произойти множество обновлений и срочных поправок.'''
            CQT.msgbox(msg, time_life=40, fontsize=18)
            return sys.exit(-1)
    else:
        os.environ[key] = now_str

def save_user_credentials():
    KEY_USER_SAVED = 'KEY_USER_CREDENTIALS_IS_SAVED'
    if os.environ.get(KEY_USER_SAVED):
        return
    os.environ[KEY_USER_SAVED] = '1'
    db_users = CFG.Config.project.db_users
    fio = F.user_full_namre()
    data = CSQ.custom_request_c(db_users, f'SELECT login, computer_name FROM employee WHERE ФИО = {fio!r}',
                                rez_dict=True, one=True)
    if isinstance(data, dict) and 'login' in data and 'computer_name' in data:
        computer_name = F.computer_name()
        login = F.user_name()
        if data['login'] != login or data['computer_name'] != computer_name:
            result = CSQ.custom_request_c(db_users,
                                          f'UPDATE employee SET login = {login!r}, computer_name = {computer_name!r} WHERE ФИО = {fio!r}')
            result and print('Пользователь успешно сохранен')

def check_ver(ver,ima):
    try:
        F.write_file_c('ver.txt',[[ver]],'|',False,True)
        Config = CFG.Config
        check_last_entry(Config.app.last_update)
        save_user_credentials()
        if Config.app.version == ver:
            print(f"     {ver} актуальна")
            return True
        else:
            print(f"     {ver} не актуальна")
            if Config.user_config.is_developer: #18.07.25
                Config.app.set(version=ver)
                F.open_dir_c(Config.app.path)
                F.open_dir_c(F.path_to_execut_file_c())
                F.open_dir_c(
                    r"C:\Users\{user}\AppData\Local\Programs\Python\Python312".format(user=F.user_name())
                )
            return f"Необходимо обновить {ima}"
    except Exception as e:
        print(e)
        return False


def percent_of_completion_c(res, filtr_rc = ''):
    summ = 0
    fact = 0
    for dse in res:
        kolvo = dse['Количество']
        for oper in dse['Операции']:
            if oper['Опер_РЦ_код'].startswith(filtr_rc) or filtr_rc == '':
                vrem_summ = (kolvo * oper['Опер_Тшт'])/oper['Опер_КОИД']
                zaversh_det = 0
                if 'Закрыто,шт.' in oper:
                    zaversh_det = oper['Закрыто,шт.']
                vrem_fact = (zaversh_det * oper['Опер_Тшт'])/oper['Опер_КОИД']
                summ+=vrem_summ
                fact+=vrem_fact
    return str(round(summ/60)) + '|' + str(round(fact/60))

@CQT.onerror
def resource_from_xml_c(self, spis_xml, kol_vo_izdeliy,nom_mk=None,conn='',cur=''):
    def count_in_knot_xml_c(xml, j):
        koef = 1
        koef_ur = int(xml[j]['level_c'])
        for k in range(j - 1, 0, -1):
            ur_tmp = int(xml[k]['level_c'])
            if ur_tmp < koef_ur:
                koef *= int(xml[k]['data']['Количество'])
                koef_ur = ur_tmp
            if koef_ur == 0:
                break
        return koef
    spis_xml = align_tree_code_c(self, spis_xml)
    rez_spis = []
    nach = 0
    npp = 0
    poki = CFG.Config.place.poki
    custom_request_c = f'''SELECT Номенклатурный_номер,Наименование, Номер_техкарты FROM dse WHERE poki = {poki}'''

    rez = CSQ.custom_request_c(self.db_dse, custom_request_c, hat_c=True, rez_dict=True)

    DICT_NN_NTK = F.deploy_dict_c(rez, 'Номенклатурный_номер')
    list_msg = []
    self.cr_mk_xml_koef_norm_mat = 1
    for i in range(nach, len(spis_xml)):
        npp += 1
        nn = spis_xml[i]['data']['Обозначение полное']
        naim = spis_xml[i]['data']['Наименование']
        pki = spis_xml[i]['data']['Покупное изделие']
        mat = spis_xml[i]['data']['Масса/М1,М2,М3'].strip()
        ssil = spis_xml[i]['data']['Ссылка на объект DOCs']
        prim = spis_xml[i]['data']['Примечание'].strip()
        level_c_dse = spis_xml[i]['level_c']
        kolvo_koef = count_in_knot_xml_c(spis_xml, i)
        dreva_kod =  spis_xml[i]['dreva_kod']
        if 'Код ERP' in spis_xml[i]['data']:
            erp_kod = spis_xml[i]['data']['Код ERP'].strip()
        else:
            erp_kod = spis_xml[i]['data']['Код_ERP'].strip()
        Способы_получения_материала = 'Произвести по основной спецификации'
        if pki == '1' or pki == 1:
            Способы_получения_материала = 'Обеспечивать'
        #nom_tk = CSQ.custom_request_c('',
        #    f'SELECT Номер_техкарты FROM dse WHERE Номенклатурный_номер == "{nn}" and Наименование == "{naim}"',
        #                    conn=conn1,hat_c=False,one=True)
        if nn not in DICT_NN_NTK:
            CQT.msgbox(f'{nn} не найден в БД dse')
            return
        nom_tk = DICT_NN_NTK[nn]['Номер_техкарты']
        if nom_tk == None or nom_tk == False or  nom_tk == '' or nom_tk[0] == '' or nom_tk[0][0] == '':
            CQT.msgbox(f'Номер техкарты для {nn} {naim} не может быть пустым')
            return
        if nom_mk != None:
            putf = F.scfg('mk_data') + os.sep + str(nom_mk) + os.sep + nom_tk + '_' + nn + '.pickle'
        else:
            putf = F.scfg('add_docs') + os.sep + nom_tk + "_" + nn + '.pickle'
        summ_kolvo = kolvo_koef * int(spis_xml[i]['data']['Количество']) * kol_vo_izdeliy

        if F.existence_file_c(putf):
            rez_tmp = dse_for_res(self, putf, summ_kolvo, npp, naim, nn, level_c_dse, pki, mat, ssil, prim, dreva_kod,
                                       Способы_получения_материала, int(spis_xml[i]['data']['Количество']),erp_kod,'','',naim, nn, primech=prim,  list_msg=list_msg)
        else:
            CQT.msgbox(f'Не найден файл {putf}')
            return
        rez_spis.append(rez_tmp)
    rez_spis = add_to_res_detail_counts(rez_spis)
    if len(list_msg) > 0:
        # CQT.msgbox(f'Результаты скоприрвоаны в буфер')
        # F.copy_bufer(pprint.pformat(list_msg))
        msg_list = list_msg#pprint.pformat(list_msg).split('\n')
        msg_list.insert(0, 'Изменения')
        CQT.msgboxg_get_table(self, 'Результаты применения коэффициентов', msg_list, 'OK', disable_btn1=True)
    return rez_spis

@CQT.onerror
def resursnaya_from_cust_struktura(self, spis_dse, kol_vo_izdeliy=None, ruchnoi=False,list_msg=[]):

    def calc_koef_knot(self, item):
        if item['К_узла'] == '':
            return 1
        if F.is_numeric(item['К_узла']):
            return F.valm(item['К_узла'])
        return 1

    def calc_koef_tolsh(self, item):
        koef_tolsh = 1

        kod_anal = self.DICT_DSE_save_mk[item['Обозначение_аналог']]['Код_ЕРП']
        kod_celevoy = item['Код ERP']
        if kod_anal == '':
            #CQT.msgbox(f'Код ERP аналога не распознан К_толщины = 1')
            return 1
        if kod_celevoy == '':
            #CQT.msgbox(f'Код ERP целевой не распознан К_толщины = 1')
            return 1
        if kod_anal not in self.DICT_NOMEN:
            list_msg.append(f"Код ERP аналога  {item['Обозначение']} {item['Наименование']} не найден в номенклатуре К_толщины = 1")
            return 1
        if kod_celevoy not in self.DICT_NOMEN:
            list_msg.append(f"Код ERP целевой  {item['Обозначение']} {item['Наименование']} не найден в номенклатуре К_толщины = 1")
            return 1
        if self.DICT_NOMEN[kod_anal]['П5'] != self.DICT_NOMEN[kod_celevoy]['П5']:
            list_msg.append(f"Номенклатуры {item['Обозначение']} {item['Наименование']} не равнозначны по параметру П5. К_толщины = 1")
            return 1
        if self.DICT_NOMEN[kod_anal]['П5'] != 1:
            return 1
        tol_anal = self.DICT_NOMEN[kod_anal]['П1']
        tol_celevoy = self.DICT_NOMEN[kod_celevoy]['П1']
        if tol_anal <= 5 and tol_celevoy >5:
            koef_tolsh= 1.3
        if tol_anal > 6 and tol_celevoy <=5:
            koef_tolsh = 1/1.3
        return koef_tolsh

    def calc_koef_gabar (self, item):
        if item['Уд_количество_аналог'] == '':
            return 1
        if F.is_numeric(item['Уд_количество_аналог']):
            return F.valm(item['Уд_количество_аналог'])
        return 1

    def calc_koef_mass (self, item):
        koef_mass = 1
        try:
            mass_celev = F.valm(item['Масса/М1,М2,М3'].split('/')[0])
            mass_anal = F.valm(item['Мат_аналог_кд'].split('/')[0])
            if mass_anal == 0 or mass_celev == 0:
                return koef_mass
            return mass_celev/mass_anal
        except:
            CQT.msgbox(f"Не расчитан коэффициент масс {item['Обозначение']} {item['Наименование']}")
            return koef_mass

    def calc_koef_svar(self, item):
        if item['Коэфф_длины_швов'] == '':
            return 1
        if F.is_numeric(item['Коэфф_длины_швов']):
            return F.valm(item['Коэфф_длины_швов'])
        return 1

    def calc_koef_n_m(self, item):
        if item['Коэф_н_м'] == '':
            return 1.3
        if F.is_numeric(item['Коэф_н_м']):
            return F.valm(item['Коэф_н_м'])
        return 1.3

    def calc_okras(self,item):
        if item['Окрашивание'] == '':
            return 0
        if F.is_numeric(item['Окрашивание']):
            return F.valm(item['Окрашивание'])
        return 0


    rez_spis = []
    spis_dse = align_tree_code_handly_c(self, spis_dse)
    nk_naim = F.num_col_by_name_in_hat_c(spis_dse, 'Наименование')
    nk_nn = F.num_col_by_name_in_hat_c(spis_dse, 'Обозначение')
    nk_kol = F.num_col_by_name_in_hat_c(spis_dse, 'Количество')
    nk_sumkol = F.num_col_by_name_in_hat_c(spis_dse, 'Сумм.Количество')
    nk_pki = F.num_col_by_name_in_hat_c(spis_dse, 'ПКИ')
    nk_mat = F.num_col_by_name_in_hat_c(spis_dse, 'Масса/М1,М2,М3')
    nk_ssil = F.num_col_by_name_in_hat_c(spis_dse, 'Ссылка')
    nk_prim = F.num_col_by_name_in_hat_c(spis_dse, 'Примечание')
    nk_urov = F.num_col_by_name_in_hat_c(spis_dse, 'Уровень')
    nk_dreva_kod = F.num_col_by_name_in_hat_c(spis_dse, 'dreva_kod')
    nk_erp_kod_new = F.num_col_by_name_in_hat_c(spis_dse, 'Код ERP')
    nf_etap = F.num_col_by_name_in_hat_c(spis_dse, 'Опер_потребл')
    if nk_erp_kod_new == None:
        nk_erp_kod_new = F.num_col_by_name_in_hat_c(spis_dse, 'Код_ERP')

    if nk_dreva_kod == None:
        nk_dreva_kod = 18
    nach = 1
    npp = 0
    STATISTIC_CALC = False
    # if "tkp_current_schema" in self.__dict__ and self.tkp_current_schema is not None:
    #     if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] == 4:
    if self.tkp_current_schema.is_statistic: #09.04.25
        STATISTIC_CALC= True

    dict_dse = dict()
    if not STATISTIC_CALC:
        conn1, cur1 = CSQ.connect_bd(self.db_dse)
        dict_dse = CSQ.custom_request_c(self.db_dse, f"""SELECT Номенклатурный_номер, Номер_техкарты 
            FROM dse WHERE poki = {self.place.poki};""",
                                        rez_dict=True, conn=conn1, cur=cur1)
        CSQ.close_bd(conn1, cur1)

        if dict_dse == False:
            CQT.msgbox(f'База занята, пробуй позже')
        dict_dse = F.deploy_dict_c(dict_dse, 'Номенклатурный_номер')


    list_msg_okrash = []
    for i in range(nach, len(spis_dse)):
        nn = spis_dse[i][nk_nn].strip()
        pseudo_nn = copy.copy(nn)
        naim  = spis_dse[i][nk_naim].strip()
        pseudo_naim = copy.copy(naim)
        pki = spis_dse[i][nk_pki].strip()

        new_mat = ""
        num_name_add_oper = ""
        koef_knot = 1
        koef_tolsh =1
        koef_gabar = 1
        koef_mass = 1
        koef_svar =1
        fl_okras = 1
        self.cr_mk_xml_koef_norm_mat = 1
        # if "tkp_current_schema" in self.__dict__ and self.tkp_current_schema is not None:
        if self.tkp_current_schema.is_tkp: #09.04.25
            dict_item = F.list_of_lists_to_list_of_dicts([spis_dse[0], spis_dse[i]])[0]
            # if  'type_tkp' in self.tkp_current_schema and  self.tkp_current_schema['type_tkp'] == 3:
            if self.tkp_current_schema.is_analogue:



                naim = dict_item['Наименование_аналог'].strip()
                nn = dict_item['Обозначение_аналог'].strip()



                if pki == '0':
                    new_mat = spis_dse[i][F.num_col_by_name_in_hat_c(spis_dse, 'Масса/М1,М2,М3')].strip()
                    num_name_add_oper = spis_dse[i][F.num_col_by_name_in_hat_c(spis_dse, 'Опер_потребл')].strip()
                    koef_knot = calc_koef_knot(self, dict_item)
                    koef_tolsh = calc_koef_tolsh(self, dict_item)
                    koef_gabar = calc_koef_gabar(self, dict_item)
                    koef_mass = calc_koef_mass(self, dict_item)
                    koef_svar = calc_koef_svar(self, dict_item)
                    self.cr_mk_xml_koef_norm_mat = calc_koef_n_m(self, dict_item)

                    fl_okras = calc_okras(self, dict_item)

                    list_msg.append({f'{naim} {nn}':{'koef_knot(К_узла)':koef_knot,
                                                     'koef_tolsh(по параметру П5)':koef_tolsh,
                                                     'koef_gabar(Уд_количество_аналог)':koef_gabar,
                                                     'koef_mass(К осн. мат. кд)':koef_mass,
                                                     'koef_svar(Коэфф_длины_швов)':koef_svar,
                                                     'koef_n_m(Коэф_н_м)':self.cr_mk_xml_koef_norm_mat,
                                                     'okras':fl_okras
                                                     }})
            # if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema is not None and self.tkp_current_schema['type_tkp'] == 4:
            if self.tkp_current_schema.is_statistic: #09.04.25
                if pki == '0':
                    self.cr_mk_xml_koef_norm_mat = calc_koef_n_m(self, dict_item)
        npp += 1

        mat = spis_dse[i][nk_mat].strip()
        ssil = spis_dse[i][nk_ssil].strip()
        prim = spis_dse[i][nk_prim].strip()
        dreva_kod = spis_dse[i][nk_dreva_kod]
        erp_kod_new = spis_dse[i][nk_erp_kod_new]
        Способы_получения_материала = 'Произвести по основной спецификации'
        if pki == '1':
            Способы_получения_материала = 'Обеспечивать'

        level_c_dse = int(spis_dse[i][nk_urov])
        kolvo_koef = self.kol_v_uzel(spis_dse, i, nk_naim, nk_kol, nk_urov)
        kolvo_summ = kolvo_koef * int(spis_dse[i][nk_kol]) * kol_vo_izdeliy
        kol_ed = int(spis_dse[i][nk_kol])
        if STATISTIC_CALC and prim != 'Комплексы':
            etap = spis_dse[i][nf_etap]
            if not spis_dse[i][nk_erp_kod_new] == '':
                if etap == '':
                    if CFG.Config.user_config.is_developer:
                        etap = 'Сборка+сварка'
                    else:
                        CQT.msgbox(f'Этап для {nn} {naim} не выбран')
                        return

            add_time = False
            if i == nach:
                add_time = True
            new_mat = spis_dse[i][F.num_col_by_name_in_hat_c(spis_dse, 'Масса/М1,М2,М3')].strip()
            weight = self.tkp_current_schema['weight']

            rez_tmp = dse_for_res_statistic(self,kolvo_summ, npp,naim,nn,level_c_dse,pki,mat,ssil,prim,dreva_kod,
                                            Способы_получения_материала,kol_ed,erp_kod_new,new_mat,etap,weight, prim,add_time=add_time)

            if rez_tmp == False:
                return
        else:
            if not dict_dse:
                data_nom_tk = CSQ.custom_request_c(self.db_dse, f"""SELECT  
                Номер_техкарты FROM dse WHERE Номенклатурный_номер = "{nn}" AND poki = {self.place.poki};""", one=True,
                                                rez_dict=True )
                if data_nom_tk == False:
                    CQT.msgbox(f'Номер техкарты для {nn} {naim} не найден')
                nom_tk = data_nom_tk['Номер_техкарты']
            else:
                if nn not in dict_dse:
                    CQT.msgbox(f'Номер техкарты для {nn} {naim} не найден')
                    return
                nom_tk = dict_dse[nn]
            if nom_tk == None or nom_tk == '' or nom_tk[0] == '':
                CQT.msgbox(f'Номер техкарты для {nn} {naim} не найден')
                return
            putf = F.scfg('add_docs') + os.sep + nom_tk + "_" + nn + '.pickle'
            if F.existence_file_c(putf):
                rez_tmp = dse_for_res(self, putf, kolvo_summ, npp, naim, nn, level_c_dse, pki, mat, ssil, prim, dreva_kod,
                                           Способы_получения_материала, kol_ed,erp_kod_new,
                                      new_mat,num_name_add_oper,pseudo_naim,pseudo_nn,
                                      koef_knot,
                                      koef_tolsh,
                                      koef_gabar,
                                      koef_mass ,
                                      koef_svar ,
                                      fl_okras,
                                      primech=prim,
                                      list_msg= list_msg,
                                      list_msg_okrash= list_msg_okrash
                                      )
                pprint.pprint(rez_tmp)
                if rez_tmp == None:
                    return
            else:
                CQT.msgbox(f'Не найден файл {putf}')
                return
        rez_spis.append(rez_tmp)
    rez_spis = add_to_res_detail_counts(rez_spis)
    # if "tkp_current_schema" in self.__dict__ and self.tkp_current_schema is not None:
    #     if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] in (3,4):
    if self.tkp_current_schema.is_tkp: #09.04.25
        if list_msg_okrash:
            CQT.msgboxg_get_table(self, 'Результаты применения коэффициентов', list_msg_okrash, 'OK', disable_btn1=True)
        if len(list_msg)>0:
            #CQT.msgbox(f'Результаты скоприрвоаны в буфер')
            #F.copy_bufer(pprint.pformat(list_msg))
            msg_list = pprint.pformat(list_msg).split('\n')
            msg_list.insert(0,'Изменения')
            CQT.msgboxg_get_table(self,'Результаты применения коэффициентов',msg_list,'OK',disable_btn1=True)
    return rez_spis

@CQT.onerror
def check_possibility_statistic_calc_tkp(vid_izd:str|int):
    VID_PO_NAPR = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""SELECT * FROM виды_по_направлению""", rez_dict=True) #18.07.25
    if isinstance(vid_izd,str):
        DICT_VID_PO_NAPR = F.deploy_dict_c(VID_PO_NAPR, 'Имя')
    if isinstance(vid_izd,int):
        DICT_VID_PO_NAPR = F.deploy_dict_c(VID_PO_NAPR, 'Пномер')
    if vid_izd not in DICT_VID_PO_NAPR:
        return
    if DICT_VID_PO_NAPR[vid_izd]['Выборка'] >= 20 and DICT_VID_PO_NAPR[vid_izd]['Утверждены_нормы']:
        return True
    return False

def add_mat_into_rez_spis(self, mat_cod, mat_naim, mat_edizm, mat_val, kolvo_summ, name_oper=None, oper_koef_svar=1,
                          oper_koef_gabar=1,
                          cr_mk_xml_koef_norm_mat = 1):
    fl_add = False
    if mat_cod in self.DICT_NOMEN:
        if name_oper == None:
            fl_add = True
        else:
            filtr = ''
            for item in self.DICT_FILTR_NOMEN:
                if item['kod_oper'] == self.DICT_OP_NAME[name_oper]['kod']  \
                        and mat_cod == item['kod']:
                    filtr = item['filtr']
                    break
            if filtr == '' or filtr == 0:
                fl_add = True

    if fl_add:
        dict_Материалы = self.DICT_NOMEN[mat_cod]
        Материалы_Статья_калькуляции = 'Сырье'
        if dict_Материалы['Вид'] == 'Упаковочные материалы для складского хоз-ва 10.09':
            Материалы_Статья_калькуляции = 'Упаковка'

        mat_val_ed = F.valm(mat_val)
        mat_val_ed_koeff = mat_val_ed * cr_mk_xml_koef_norm_mat * oper_koef_svar * oper_koef_gabar
        return {'Мат_код': mat_cod, "Мат_наименование": mat_naim,
                             "Мат_ед_изм": mat_edizm,
                             "Мат_норма": round(
                                 kolvo_summ * mat_val_ed_koeff, 6),
                             "Мат_норма_ед": round(mat_val_ed_koeff, 6),
                             'Мат_параметрика': dict(),
                             'Материалы_Статья_калькуляции': Материалы_Статья_калькуляции,
                             "Способы_получения_материала": 'Обеспечивать'
                             }

@CQT.onerror
def dse_for_res_statistic(self, kolvo_summ, npp, naim, nn, level_c_dse, pki, mat, ssil, prim, dreva_kod,
                Способы_получения_материала, kol_ed, erp_kod_new, new_mat,etap,weight,primech,  add_time=False, list_msg=[]):

    def prof_rc_cods(etap):
        etap_data = self.Data_plan.DICT_ETAPS_NAME[etap]
        prof_cod = etap_data['Опер_профессия_код_для_ткп_стат']
        prof_name = self.DICT_PROFESSIONS[prof_cod]['имя']
        rc_cod = etap_data['Опер_код_рц_для_ткп_стат']
        podr_name = self.DICT_RC[rc_cod]['Наим_ЕРП']
        oper_cod = etap_data['Опер_код_для_ткп_стат']
        return prof_cod,rc_cod,podr_name,prof_name,oper_cod

    def make_oper(rez_spis_op,etap,prof_cod, rc_cod, t_sht_ed,kolvo_summ,podr_name,prof_name,oper_cod, rez_spis_mat=[]):
        oper_name = ''
        if oper_cod in self.DICT_OP:
            oper_name = self.DICT_OP[oper_cod]['name']
        rez_spis_op.append({"Этап": etap,
                            "Опер_наименование": oper_name,
                            "Опер_код": oper_cod,
                            "Опер_вспомогательная": "",
                            "Опер_номер": "",
                            "Опер_РЦ_наименование": '',
                            "Опер_РЦ_код": rc_cod,
                            'Опер_наименование_подразделения': podr_name,
                            "Опер_оборудование_наименование": "",
                            "Опер_оборудование_код": "",
                            "Опер_Тпз": 0,
                            "Опер_Тшт": round(t_sht_ed * kolvo_summ, 6),
                            "Опер_Тшт_ед": round(t_sht_ed, 6),
                            "Опер_профессия_наименование": prof_name,
                            "Опер_профессия_код": prof_cod,
                            "Опер_КР": "",
                            "Опер_КОИД": "", "Опер_документы": [],
                            "Опер_инстумент": [], "Опер_оснастка": [],
                            "Материалы": rez_spis_mat, "Переходы": []})
        return rez_spis_op

    def add_mat_into_rez_spis(self,rez_spis_mat,mat_cod,mat_naim,mat_edizm,mat_val,kolvo_summ,pki):
        SET_SHT_EDIZM = {'Штука',
                        'Шт',
                        'штУДАЛИТЬ',
                        'шт.штУДАЛИТЬ',
                        'штука',
                        'штштУДАЛИТЬ',
                        'шт',
                        }
        dict_Материалы = self.DICT_NOMEN[mat_cod]
        Материалы_Статья_калькуляции = 'Сырье'
        if dict_Материалы['Вид'] == 'Упаковочные материалы для складского хоз-ва 10.09':
            Материалы_Статья_калькуляции = 'Упаковка'
        ЕдиницаИзмерения = dict_Материалы['ЕдиницаИзмерения']
        if pki:
            if ЕдиницаИзмерения in SET_SHT_EDIZM:
                mat_val_ed = 1
            else:
                mat_val_ed = F.valm(mat_val)
        else:
            mat_val_ed = F.valm(mat_val)
        mat_val_ed_koeff = mat_val_ed * self.cr_mk_xml_koef_norm_mat



        rez_spis_mat.append({'Мат_код': mat_cod, "Мат_наименование": mat_naim,
                             "Мат_ед_изм": mat_edizm,
                             "Мат_норма": round(
                                  kolvo_summ * mat_val_ed_koeff, 6),
                             "Мат_норма_ед": round(mat_val_ed_koeff, 6),
                             'Мат_параметрика': dict(),
                             'Материалы_Статья_калькуляции': Материалы_Статья_калькуляции,
                             "Способы_получения_материала": 'Обеспечивать'
                             })
        return rez_spis_mat


    additional_mat_val = F.valm(new_mat.split('/')[0])

    rez_spis_op = []
    vid_izd = self.tkp_current_schema['вид_по_напр']
    dev_analisis = []
    if add_time:
        for name, min_per_kg in self.Data_plan.DICT_VID_PO_NAPR[vid_izd].items():
            t_sht_ed = 0

            if name in self.Data_plan.DICT_ETAPS_VID_NAME:
                if self.Data_plan.DICT_ETAPS_VID_NAME[name]['ДляЕРП'] == 0:
                    continue
                etap = self.Data_plan.DICT_ETAPS_VID_NAME[name]['name']
                prof_cod, rc_cod,podr_name,prof_name,oper_cod = prof_rc_cods(etap)

                t_sht_ed = min_per_kg * weight / kolvo_summ
                dev_analisis.append({
                                    'rc_cod':rc_cod,
                                    'min_per_kg':min_per_kg,
                                     'weight':weight,
                                     'kolvo_summ':kolvo_summ,
                                        't_sht_ed' :t_sht_ed,
                                    'etap':etap
                                     })
                print(f'{rc_cod}:{t_sht_ed}')
                rez_spis_op = make_oper(rez_spis_op,etap,prof_cod, rc_cod, t_sht_ed, kolvo_summ,podr_name,prof_name,oper_cod,[])


    if erp_kod_new != '':

        if erp_kod_new not in self.DICT_NOMEN:
            CQT.msgbox(f'Код {erp_kod_new} отсутсвет в номенклатуре')
            return False
        naimen = self.DICT_NOMEN[erp_kod_new]['Наименование']
        ed_izm = self.DICT_NOMEN[erp_kod_new]['ЕдиницаИзмерения']

        rez_spis_mat = []
        rez_spis_mat = add_mat_into_rez_spis(self,rez_spis_mat, erp_kod_new, naimen, ed_izm, additional_mat_val,kolvo_summ,pki)
        prof_cod, rc_cod,podr_name,prof_name,oper_cod = prof_rc_cods(etap)
        t_sht_ed = 0
        rez_spis_op = make_oper(rez_spis_op, etap, prof_cod, rc_cod, t_sht_ed, kolvo_summ,podr_name,prof_name,oper_cod,rez_spis_mat)


    rez_tmp = {'Номерпп': npp, 'Наименование': naim, 'Номенклатурный_номер': nn, 'Код_ERP':erp_kod_new, 'Код ERP':erp_kod_new, 'Количество': kolvo_summ,
               'Количество_ед': kol_ed,
               'Уровень': level_c_dse, "Операции": rez_spis_op, 'Параметрика': dict(), 'Документы': [],
               'ПКИ': pki, 'Мат_кд': mat, 'Ссылка': ssil, 'Прим': prim,
               "dreva_kod": dreva_kod, "Способы_получения_материала": Способы_получения_материала}

    return rez_tmp
    CQT.msgboxg_get_table_ok_inf(self,'Проверка',dev_analisis,load_summ=True)

@CQT.onerror
def dse_for_res(self, putf, kolvo_summ, npp, naim, nn, level_c_dse, pki, mat, ssil, prim, dreva_kod,
                Способы_получения_материала, kol_ed, erp_kod_new, new_mat, num_name_add_oper,
                pseudo_naim, pseudo_nn,
                koef_knot=1,
                koef_tolsh=1,
                koef_gabar=1,
                koef_mass=1,
                koef_svar=1,
                fl_okras = 1,
                primech = None,
                list_msg=[],
                list_msg_okrash = []):
    tkpa = False
    # if "tkp_current_schema" in self.__dict__ and self.tkp_current_schema is not None:
    #     if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] == 3:
    if self.tkp_current_schema.is_analogue: #09.04.25
        tkpa =True

    def add_mat_into_rez_spis(self,mat_cod,mat_naim,mat_edizm,mat_val,name_oper=None,oper_koef_svar=1,oper_koef_gabar=1):

        fl_add = False
        if mat_cod in self.DICT_NOMEN:
            if name_oper==None:
                fl_add = True
            else:
                filtr = ''
                for item in self.DICT_FILTR_NOMEN:
                    if item['kod_oper'] == self.DICT_OP_NAME[name_oper]['kod'] \
                            and mat_cod == item['kod']:
                        filtr = item['filtr']
                        break
                if filtr == '' or filtr == 0:
                    fl_add = True

        if fl_add:
            dict_Материалы = self.DICT_NOMEN[mat_cod]
            Материалы_Статья_калькуляции = 'Сырье'
            if dict_Материалы['Вид'] == 'Упаковочные материалы для складского хоз-ва 10.09':
                Материалы_Статья_калькуляции = 'Упаковка'


            mat_val_ed = F.valm(mat_val)
            mat_val_ed_koeff = mat_val_ed * self.cr_mk_xml_koef_norm_mat*oper_koef_svar*oper_koef_gabar
            rez_spis_mat.append({'Мат_код': mat_cod, "Мат_наименование": mat_naim,
                                 "Мат_ед_изм": mat_edizm,
                                 "Мат_норма": round(
                                      kolvo_summ * mat_val_ed_koeff, 6),
                                 "Мат_норма_ед": round(mat_val_ed_koeff, 6),
                                 'Мат_параметрика': dict(),
                                 'Материалы_Статья_калькуляции': Материалы_Статья_калькуляции,
                                 "Способы_получения_материала": 'Обеспечивать'
                                 })
            list_msg.append(
                f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']}, Мат {mat_cod} {mat_naim}:  было {round(mat_val_ed, 2)}  стало  {round(mat_val_ed_koeff, 2)}")
        else:
            list_msg.append(
                f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']}, Мат {mat_cod} {mat_naim}:  не прошел фильтр")


    num_oper_replace_mat = ""
    additional_mat_val = 0
    if num_name_add_oper != "":
        num_oper_replace_mat = num_name_add_oper.split('$')[0]
        additional_mat_val = F.valm(new_mat.split('/')[0])

    rez_spis_op = []
    nk_rc_tk = 4
    nk_ur_tk = 20
    nk_op_tk = 2
    nk_mat_tk = 10
    nk_doc_tk = 15
    nk_textper = 0

    # sp_tk = F.open_file_c(putf, False, "|", pickl=True)
    tk_obj = Techkards(nn,self.db_dse,db_nomen=self.bd_nomen,fix_mat=True,DICT_OP_NAME=self.DICT_OP_NAME)
    try:
        tk_docs = tk_obj.sp_tk[10][nk_doc_tk].split('$')
    except:
        CQT.msgbox(f'Что-то не так в тк {putf.split(F.sep())[-1]} проверь ее!')
        return
    #====================================================UPDATE NORM TIME========================================
    print(f'\nПересчет норм начало {nn}')
    tk_obj._update_params_oper(self.DICT_OP_NAME)
    list_oper_names = [_ for _ in self.DICT_OP_NAME.keys() if self.DICT_OP_NAME[_]['auto_recalc_pred_tkp']]
    if primech != 'Комплексы':
        err, log = tk_obj.recalc_opers(DICT_OPERS=self.DICT_OP_NAME,list_opers_name=list_oper_names)
        if len(log):
            #CQT.msgbox(pprint.pformat(log))
            for item_log in log:
                list_msg.append(item_log.replace('\n',' '))
            pass
        if err != None:
            CQT.msgbox(f'Ошибка ошибка пересчета норм времени. Нужно править теккарту {nn}\n\n  {err} ')
            return
        print(f'Пересчет норм конец \n\n')
    if self.tkp_current_schema.is_tkp:
        messages = tk_obj.recalc_materials() #24.11.25
        list_msg.extend(messages)
    # ==================================================================================================================

    fl_replace_analog_mat = True
    if num_name_add_oper != '':
        fl_replace_analog_mat = False
    for oper in tk_obj.tk['bodys'][0]['opers']:
        if oper['rab_centr'] not in self.DICT_RC:
            CQT.msgbox(f'В ТК {nn} {naim}, операция {oper["s_name"]}\n РЦ {oper["rab_centr"]} не опознан.')
            return
        kod_oper = oper['cod']

        if kod_oper == '':
            CQT.msgbox(f"Ошибка kod_oper {nn} {naim} операция {oper['s_name']} {oper['name_ver']}")
            return
        oper_koef_knot = 1
        if self.DICT_OP[kod_oper]['calc_analog_use_k_mat'] != 0:
            oper_koef_knot = copy.deepcopy(koef_knot)
        oper_koef_tolsh = 1
        if self.DICT_OP[kod_oper]['calc_analog_use_k_tolsh'] != 0:
            oper_koef_tolsh = copy.deepcopy(koef_tolsh)
        oper_koef_gabar = 1
        if self.DICT_OP[kod_oper]['calc_analog_use_k_gabar'] != 0:
            oper_koef_gabar = copy.deepcopy(koef_gabar)
        oper_koef_mass = 1
        if self.DICT_OP[kod_oper]['calc_analog_use_k_mass'] != 0:
            oper_koef_mass = copy.deepcopy(koef_mass)
        oper_koef_svar = 1
        if self.DICT_OP[kod_oper]['calc_analog_use_k_shva'] != 0:
            oper_koef_svar = copy.deepcopy(koef_svar)



        rez_spis_mat = []
        if self.list_vars_vo != []:
            #sp_tk[j] = CVO.update_parametrs(self, sp_tk, j, nn)
            CQT.msgbox(f'Расчет по параметрам не доработан')
            return
        #====== add mats=============================:


        for mater in oper['materials']:
            fl_add= True
            if tkpa:
                if mater['cod'] in self.DICT_NOMEN:
                    if self.DICT_NOMEN[mater['cod']]['Вид'] in self.Data_plan.DICT_VID_NOMEN:
                        if self.Data_plan.DICT_VID_NOMEN[self.DICT_NOMEN[mater['cod']]['Вид']]['ЕстьПараметры'] == 1:
                            fl_add= False
            if fl_add:
                add_mat_into_rez_spis(self,mater['cod'],mater['naimen'],mater['ed_izm'],mater['norma'],oper['name_ver'],oper_koef_svar,oper_koef_gabar)
            else:
                list_msg.append(
                    f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']}, Мат {mater['cod']} {mater['naimen']}: убран как основной из аналога")

        if fl_replace_analog_mat == False and num_oper_replace_mat == oper['s_name']:
            if erp_kod_new not in self.DICT_NOMEN:
                CQT.msgbox(f'Код {erp_kod_new} отсутсвет в номенклатуре')
                return
            naimen = self.DICT_NOMEN[erp_kod_new]['Наименование']
            ed_izm = self.DICT_NOMEN[erp_kod_new]['ЕдиницаИзмерения']
            fl_replace_analog_mat = True
            list_msg.append(
                f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']}, Мат {erp_kod_new} {naimen}: добавлен как новый:")
            add_mat_into_rez_spis(self, erp_kod_new, naimen, ed_izm, additional_mat_val)

        # ====== add mats=============================end

        rez_spis_instr = []
        rez_spis_osn = []
        rez_spis_doc = oper['doc_card']
        rez_spis_doc = F.clear_free_items(rez_spis_doc)
        spis_per = [_['name_ver'] for _ in oper['perehs']]
        for pereh in oper['perehs']:
            for item in pereh['instrums']:
                rez_spis_instr.append(item)
            for item in pereh['prisposobs']:
                rez_spis_osn.append(item)
            for item in pereh['doc_card']:
                rez_spis_doc.append(item)


        if name_RC_by_number_c(self.SPIS_RC, oper['rab_centr']) == None:
            CQT.msgbox(f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']} не найден РЦ")
        if kod_oper not in self.DICT_OP:
            CQT.msgbox(
                f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']} не найден ""Этап"" в БД, обратиться к технологам.")
            etap = 'Неопознан'
        else:
            etap = self.DICT_RC[oper['rab_centr']]['etaps_name']
        #
        #if oper['name_ver'] not in self.DICT_ETAPI:
        #    CQT.msgbox(
        #        f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']} не найден ""Этап"" в БД, обратиться к технологам.")
        #    etap = 'Неопознан'
        #else:
        #    #etap = self.DICT_ETAPI[oper['name_ver']]  15.01.2025 по замечанию МОренко
        #    if oper['profession'] not in self.DICT_PROFESSIONS:
        #        return CQT.msgbox(f"{nn} {naim} операция {oper['s_name']} код профессии: {oper['profession']} некорректный или устарел")
        #    etap = self.DICT_PROFESSIONS[oper['profession']]['этап']
        tpz=oper['t_pz']
        if primech== 'Комплексы':
            t_sht_ed = 0
            tpz = 0
            if self.tkp_current_schema.is_analogue:
                t_sht_ed = oper['t_sht'] * self.cr_mk_xml_koef_norm_mat#19.11.2025 по Задача № 100063161
                tpz = 0
        else:
            t_sht_ed = oper['t_sht'] * self.cr_mk_xml_koef_norm_time * \
                   oper_koef_mass * oper_koef_tolsh * oper_koef_gabar * oper_koef_knot * oper_koef_svar
        try:
            list_msg.append(f"{nn} {naim} операция {oper['s_name']} {oper['name_ver']}, t_sht:  было {oper['t_sht']}  стало  {round(t_sht_ed,2)}")
        except:
            pass

        # 21.11.25 Учитывать галку окрашена в сборках
        print(f'  Окрашивание {kod_oper}  -   {fl_okras}')
        if fl_okras == 0 and primech != 'Комплексы':
            if self.DICT_OP[kod_oper]['okras_tkp_res'] == 1:
                #CQT.msgbox(
                #    f"{pseudo_nn}\nОперация {oper['s_name']} {oper['name_ver']} пропущена , т.к. окрашивание {fl_okras}")
                #
                list_msg_okrash.append({'НН':pseudo_nn,'Операция':f'{oper['s_name']} {oper['name_ver']}',
                                        'Статус': 'пропущена', 'Причина':f'окрашивание {fl_okras}' })
                continue
        rez_spis_op.append({"Этап": etap,
                            "Опер_наименование": oper['name_ver'],
                            "Опер_код": kod_oper,
                            "Опер_вспомогательная": self.DICT_OP[kod_oper]['Вспомогат'],
                            "Опер_номер": oper['s_name'],
                            "Опер_РЦ_наименование": name_RC_by_number_c(self.SPIS_RC, oper['rab_centr']),
                            "Опер_РЦ_код": oper['rab_centr'],
                            'Опер_наименование_подразделения': self.DICT_RC[oper['rab_centr']]['Наим_ЕРП'],
                            "Опер_оборудование_наименование": oper['oborudovanie'],
                            "Опер_оборудование_код": code_of_mashine_by_name_c(self.SPIS_OB,
                                                                               oper['oborudovanie']),
                            "Опер_Тпз": round(tpz, 6),
                            "Опер_Тшт": round(t_sht_ed * kolvo_summ, 6),
                            "Опер_Тшт_ед": round(t_sht_ed, 6),
                            "Опер_профессия_наименование": ima_prof_by_code_c(self.SPIS_PROF,
                                                                              oper['profession']),
                            "Опер_профессия_код": oper['profession'],
                            "Опер_КР": oper['kr'],
                            "Опер_КОИД": oper['koid'], "Опер_документы": rez_spis_doc,
                            "Опер_инстумент": rez_spis_instr, "Опер_оснастка": rez_spis_osn,
                            "Материалы": rez_spis_mat, "Переходы": spis_per})


    rez_tmp = {'Номерпп': npp, 'Наименование': pseudo_naim, 'Номенклатурный_номер': pseudo_nn, 'Код_ERP':erp_kod_new, 'Код ERP':erp_kod_new, 'Количество': kolvo_summ,
               'Количество_ед': kol_ed,
               'Уровень': level_c_dse, "Операции": rez_spis_op, 'Параметрика': dict(), 'Документы': tk_docs,
               'ПКИ': pki, 'Мат_кд': mat, 'Ссылка': ssil, 'Прим': prim,
               "dreva_kod": dreva_kod, "Способы_получения_материала": Способы_получения_материала}
    return rez_tmp



@CQT.onerror
def resursnaya_from_mk(self, nom_mk):
    return load_res(int(nom_mk),self.db_resxml,self=self,from_xml=True)

@CQT.onerror
def save_xml(self):
    if self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex()) != 'Маршрутные карты':
        CQT.msgbox('Не выбрана вкладка Маршрутные карты')
        return
    nk_pnomer = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Пномер')
    nk_nomenk = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Номенклатура')
    nk_kolich = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Количество')
    nk_sort_c = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Вид')
    nom_mk = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(), nk_pnomer).text()

    path = CQT.f_dialog_save(self,'Файл',tmp_dir(),'*.xml')
    if path == '.':
        return
    if nom_mk == None:
        CQT.msgbox(f'Номер мк не указан')
    query = f'''SELECT data, Head FROM xml 
        WHERE Номер_мк == {int(nom_mk)}
                    '''
    rez_xml = CSQ.custom_request_c(self.db_resxml, query)
    xml = rez_xml[-1][0]
    F.save_file(path,F.convert_binary_to_data(xml))
    F.open_dir_c(F.sep().join(path.split(F.sep())[:-1]))


def align_tree_code_c(self,spis_xml):
    level_c_dse = 0
    npp_ur = 1
    max_ur = 0
    for i in range(len(spis_xml)):
        ur = spis_xml[i]['level_c']
        if ur> max_ur:
            max_ur = ur
    shema = [0 for _ in range(max_ur+2)]
    for i in range(len(spis_xml)):
        shema[spis_xml[i]['level_c']] +=1
        for j in range(spis_xml[i]['level_c']+1, len(shema)):
            shema[j] = 0
        spis_xml[i]['dreva_kod'] = copy.deepcopy(shema)
    for i in range(len(spis_xml)):
        text = [str(_) for _ in spis_xml[i]['dreva_kod']]
        spis_xml[i]['dreva_kod'] = '.'.join(text[:-1])
    return spis_xml



def align_tree_code_handly_c(self,spis_dse):
    level_c_dse = 0
    npp_ur = 1
    max_ur = 0
    nk_level_c = F.num_col_by_name_in_hat_c(spis_dse,'Уровень')
    nk_dreva_kod = F.num_col_by_name_in_hat_c(spis_dse, 'dreva_kod')
    if nk_dreva_kod == None:
        nk_dreva_kod = 18
    for i in range(1,len(spis_dse)):
        spis_dse[i][nk_level_c] = int(spis_dse[i][nk_level_c])
        ur = spis_dse[i][nk_level_c]
        if ur > max_ur:
            max_ur = ur
    shema = [0 for _ in range(max_ur + 2)]
    for i in range(1,len(spis_dse)):
        shema[spis_dse[i][nk_level_c]] += 1
        shema[spis_dse[i][nk_level_c] + 1] = 0
        spis_dse[i][nk_dreva_kod] = copy.deepcopy(shema)
    for i in range(1,len(spis_dse)):
        text = [str(_) for _ in spis_dse[i][nk_dreva_kod]]
        spis_dse[i][nk_dreva_kod] = '.'.join(text[:-1])
    return spis_dse




def add_to_res_detail_counts(res):
    def count_by_struct(res, j):
        koef = 1
        koef_ur = int(res[j]['Уровень'])
        for k in range(j - 1, -1, -1):
            ur_tmp = int(res[k]['Уровень'])
            if ur_tmp < koef_ur:
                koef *= int(res[k]['Количество_ед'])
                koef_ur = ur_tmp
            if koef_ur == 0:
                break
        return koef * res[j]['Количество_ед']

    def count_all(res, j):
        nn = res[j]['Номенклатурный_номер']
        naim = res[j]['Наименование']
        count_entrys = 0
        for j, dse in enumerate(res):
            if dse['Номенклатурный_номер'] == nn and dse['Наименование'] == naim:
                count_entrys += count_by_struct(res,j)
        return count_entrys

    COUNT_DICT_TEMPL = {
        'кол_во_заказ_в_сборку': 0,
        'кол_во_заказ_по_структуре': 0,
        'кол_во_заказ_все_вхождения': 0,
        'кол_во_1_изд_в_сборку': 0,
        'кол_во_1_изд_по_структуре': 0,
        'кол_во_1_изд_все_вхождения': 0,
        'кол_во_сегментов': 0
    }

    if len(res)<1:
        return res
    if 'Количество_ед' in res[0]:
        count_izd = res[0]['Количество']/res[0]['Количество_ед']
    else:
        count_izd = res[0]['Количество']



    for dse_i, dse in enumerate(res):
        if 'Количество_ед' not in dse:
            res[dse_i]['Количество_ед'] = res[dse_i]['Количество']/count_izd
        for oper_i, oper in enumerate(res[dse_i]['Операции']):
            if 'Опер_РЦ_наименовние' in oper and 'Опер_РЦ_наименование' not in oper:
                res[dse_i]['Операции'][oper_i]['Опер_РЦ_наименование'] = res[dse_i]['Операции'][oper_i]['Опер_РЦ_наименовние']
            if 'Опер_наименовние' in oper and 'Опер_наименование' not in oper:
                res[dse_i]['Операции'][oper_i]['Опер_наименование'] = res[dse_i]['Операции'][oper_i]['Опер_наименовние']
            if 'Опер_оборудование_наименовние' in oper and 'Опер_оборудование_наименование' not in oper:
                res[dse_i]['Операции'][oper_i]['Опер_оборудование_наименование'] = res[dse_i]['Операции'][oper_i]['Опер_оборудование_наименовние']

    for dse_i, dse in enumerate(res):
        if 'кол_во_инф' in dse:
            continue

        count_segm = 1
        tmp_dict_count = copy.deepcopy(COUNT_DICT_TEMPL)
        tmp_dict_count['кол_во_1_изд_в_сборку'] = dse['Количество_ед']
        tmp_dict_count['кол_во_1_изд_по_структуре'] = count_by_struct(res,dse_i)
        tmp_dict_count['кол_во_1_изд_все_вхождения'] = count_all(res, dse_i)
        tmp_dict_count['кол_во_заказ_в_сборку'] = tmp_dict_count['кол_во_1_изд_в_сборку'] * count_izd
        tmp_dict_count['кол_во_заказ_по_структуре'] = tmp_dict_count['кол_во_1_изд_по_структуре'] * count_izd
        tmp_dict_count['кол_во_заказ_все_вхождения'] = tmp_dict_count['кол_во_1_изд_все_вхождения'] * count_izd
        for oper in dse['Операции']:
            for perehod in oper['Переходы']:
                count_segm = segment_count(perehod, 1)
                break
            break
        tmp_dict_count['кол_во_сегментов'] = count_segm
        res[dse_i]['кол_во_инф']= tmp_dict_count
    return res

def fix_mastered_count(res:list,s_num_mk:int):
    db_nar= CFG.Config.project.db_naryad
    def clc_count_fio():
        count = 0
        if item['ФИО'] != '':
            count+=1
        if item['ФИО2']!= '':
            count+=1
        return count
    def clc_count_ftime():
        count = 0
        if item['Фвремя'] != '':
            count+=1
        if item['Фвремя2']!= '':
            count+=1
        return count
    list_nars = CSQ.custom_request_c(db_nar,f"""SELECT ФИО, ФИО2, Фвремя, Фвремя2, 
       ДСЕ_ID, Операции, Опер_колво
  FROM naryad WHERE Номер_мк == {s_num_mk} and Внеплан == {CFG.Config.place.КодыНарядов.Плановая};""",rez_dict=True) #05.09.25
    dict_cr =dict()
    dict_zav = dict()
    for item in list_nars:#создан

        fl_zav = False
        count_fio = clc_count_fio()
        if count_fio:#распределен
            if count_fio == clc_count_ftime():#завершен
                fl_zav = True

        list_ids = item['ДСЕ_ID'].split('|')
        list_counts = item['Опер_колво'].split('|')
        list_opers = [_.split('$')[0] for _ in  item['Операции'].split('|')]
        for i, id in enumerate(list_ids):
            count = int(list_counts[i])
            id = int(id)
            oper_num = list_opers[i]
            if id not in dict_cr:
                dict_cr[id] = dict()
            if oper_num not in dict_cr[id]:
                dict_cr[id][oper_num] = 0

            dict_cr[id][oper_num] += count

            if fl_zav:
                if id not in dict_zav:
                    dict_zav[id] = dict()
                if oper_num not in dict_zav[id]:
                    dict_zav[id][oper_num] = 0

                dict_zav[id][oper_num] += count

    for dse in res:
        id = dse['Номерпп']
        for oper in dse['Операции']:
            oper_num = oper['Опер_номер']
            oper['Освоено,шт.'] = 0
            oper['Закрыто,шт.'] = 0
            if id in dict_cr:
                if oper_num in dict_cr[id]:
                    oper['Освоено,шт.'] = dict_cr[id][oper_num]
            if id in dict_zav:
                if oper_num in dict_zav[id]:
                    oper['Закрыто,шт.'] = dict_zav[id][oper_num]
    return res


def load_res(nom_mk:int, conn = '',cur= '',db_resxml='',self=None,
             from_xml=False, tkp = False,db_users= None,poki=None,db_naryad=None):
    if db_users is None:
        db_users = CFG.Config.project.db_users 
    if poki is None:
        poki = CFG.Config.place.poki 
    if db_naryad is None:
        db_naryad = CFG.Config.project.db_naryad 
    if db_resxml == '':
        db_resxml = F.bdcfg('db_resxml')
    #query = f'''SELECT data FROM res WHERE Номер_мк == {nom_mk}'''
    #res = CSQ.custom_request_c(db_resxml, query, conn=conn, cur = cur)
    if self == None:
        from_xml= False

    def update_name_rc_and_etaps(res):
        etaps = CSQ.custom_request_c(db_users,
                f"""SELECT etaps.name, rab_c.Код , rab_c.Имя FROM rab_c 
                LEFT JOIN etaps ON 
                etaps.s_num = rab_c.etaps_num 
                WHERE rab_c.poki = {poki}""",
                        attach_dbs = db_naryad,rez_dict=True)
        dict_etaps = F.deploy_dict_c(etaps,'Код')

        for dse_i, dse in enumerate(res):
            for oper_i, oper in enumerate(res[dse_i]['Операции']):
                rc = oper['Опер_РЦ_код']
                if rc in dict_etaps:
                    oper['Этап'] = dict_etaps[rc]['name']
                    oper['Опер_РЦ_наименование'] = dict_etaps[rc]['Имя']
        return res

    def fix_old_custom_res(rez_spis):

        for i in range(len(rez_spis)):
            if rez_spis[i]['ПКИ'] == '':
                rez_spis[i]['ПКИ'] = '0'
            for j, oper in enumerate(rez_spis[i]['Операции']):
                if "Опер_РЦ_код" not in oper:
                    CQT.msgbox(f'в ресурсной отсутвует "Опер_РЦ_код"')
                    rez_spis[i]['Операции'][j]['Опер_наименование_подразделения'] = 'err'
                    continue
                rc_kod = oper["Опер_РЦ_код"]
                if rc_kod not in self.DICT_RC:
                    CQT.msgbox(f'в бд отсутвует {rc_kod}')
                    rez_spis[i]['Операции'][j]['Опер_наименование_подразделения'] = 'err'
                    continue
                podr = self.DICT_RC[rc_kod]['Наим_ЕРП']
                rez_spis[i]['Операции'][j]['Опер_наименование_подразделения'] = podr

        return rez_spis

    if nom_mk == None:
        CQT.msgbox(f'Номер мк не указан')
    if tkp and not isinstance(nom_mk, list): # 30.05.2025 Ошибка при вызове для predv_res
        if self == '':
            raise Exception('Val err self')
        rez_xml = CSQ.custom_request_c(db_resxml,
                                    f"""SELECT data FROM predv_res WHERE Пномер = {int(nom_mk)};"""
                                    )
        rez_spis = F.from_binary_pickle(rez_xml[1][0])

        rez_spis = fix_old_custom_res(rez_spis)

    else:
        if from_xml:
            query = f'''SELECT data, Head FROM xml 
                WHERE Номер_мк == {int(nom_mk)}
                            '''
            rez_xml = CSQ.custom_request_c(db_resxml, query)
            xml = rez_xml[-1][0]
            xml_head = rez_xml[-1][1]
            if xml == '':
                from_xml = False

        if not from_xml:
            if isinstance(nom_mk, list):
                rez_spis = F.from_binary_pickle(nom_mk[1][0])
            else:
                bin_data = CSQ.custom_request_c(db_resxml, f"""SELECT data FROM res WHERE Номер_мк = {int(nom_mk)}""",
                                         rez_dict=True,
                                         one=True)
                if isinstance(bin_data, dict) and len(bin_data) == 0:
                    CQT.msgbox(f'МК №{nom_mk} не содержит данных, необходимо ее исправить или удалить. Не учтена')
                    return []
                rez_spis = F.from_binary_pickle(bin_data
                    ['data'])
            if self:
                rez_spis = fix_old_custom_res(rez_spis)
        else:
            query = f'''SELECT Количество FROM mk
                    WHERE Пномер == {int(nom_mk)}
                                '''
            kol_vo_izdeliy = CSQ.custom_request_c(db_naryad, query)[-1][0]
            spis_xml = podgotovka_xml(self,XML.spisok_iz_xml(str_f=xml), xml_head, correct_code_erp_tbl=True)
            if not spis_xml:
                return
            rez_spis = resource_from_xml_c(self, spis_xml, kol_vo_izdeliy, nom_mk)

    res = add_to_res_detail_counts(rez_spis)
    res = update_name_rc_and_etaps(res)
    if isinstance(nom_mk,list):
        s_nom_mk = nom_mk[0]
    else:
        s_nom_mk = nom_mk
    if not tkp: # 30.05.2025 Ошибка при вызове для predv_res
        res = fix_mastered_count(res,int(s_nom_mk))#починка количества освоенных дсе(создан наряд в Sozdanie -> create_naryd(self, *args):)
    return res

def save_res(db,nom_mk,res,conn = '',cur = ''):
    #CSQ.update_bd_sql(db, 'res', {'data': F.to_binary_pickle(res)},
    #                  {'Номер_мк': int(nom_mk)},conn=conn, cur = cur)
    blob1 = F.to_binary_pickle(res)
    blob = CSQ.for_blob(blob1)
    print(blob == blob1)
    CSQ.custom_request_c(db, f'''UPDATE res SET data = ? WHERE Номер_мк = ?;''',list_of_lists_c=[blob1,int(nom_mk)])

def load_order_outsourcing_c(self, tbl_nar, tbl_viev):
    tbl = tbl_nar
    tblv = tbl_viev
    if tbl.currentRow() == -1:
        CQT.msgbox('Не выбран наряд')
        return
    nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
    nom_nar = tbl.item(tbl.currentRow(), nk_nom_nar).text()
    nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Номер_мк')
    nom_nom_mk = tbl.item(tbl.currentRow(), nk_nom_mk).text()
    nk_primech = CQT.num_col_by_name_c(tbl, 'Примечание')
    primech = tbl.item(tbl.currentRow(), nk_primech).text()
    data = F.now("%d.%m.%Y %H:%M")
    custom_request_c = f'''SELECT Номенклатура,Номер_заказа FROM mk WHERE Пномер == {int(nom_nom_mk)}'''
    query = CSQ.custom_request_c(CFG.Config.project.db_naryad, custom_request_c)
    poz = query[-1][0]
    py = query[-1][1]
    rez = [['№ документа', '', 'Дата(дд.мм.гггг)', 'ВЕДОМОСТЬ АУТСОРСИНГ', f'№{nom_nar}', 'Заказ',"",""],
           [nom_nar, '', data, poz, '', py,"",""],
           ['Составил', 'ФИО', '', '', '', 'К маршрутной карте',"",""],
           [job_post_by_empl_c(self.glob_login), name_by_empl_c(self.glob_login), '', '', '', nom_nom_mk,"",""],
           ['№', 'Обозначение ДСЕ', 'Операция/Вид', 'Количество', 'Отметки', 'Норма времени, мин./код', "КД", "ТД"]
           ]
    spis = CQT.list_from_wtabl_c(tblv, hat_c=True)
    nk_kol = F.num_col_by_name_in_hat_c(spis, 'Количество')
    nk_dse = F.num_col_by_name_in_hat_c(spis, 'ДСЕ')
    nk_mar = F.num_col_by_name_in_hat_c(spis, 'Маршрут')
    nk_oper = F.num_col_by_name_in_hat_c(spis, 'Операция')
    nk_vrem = F.num_col_by_name_in_hat_c(spis, 'Время')
    nk_kd = F.num_col_by_name_in_hat_c(spis, 'КД')
    nk_td = F.num_col_by_name_in_hat_c(spis, 'ТД')
    schet = 0
    for i in range(1, len(spis)):
        if '->' in spis[i][nk_mar]:
            schet += 1
            rez.append([schet, spis[i][nk_dse], spis[i][nk_oper], spis[i][nk_kol], '', spis[i][nk_vrem],spis[i][nk_kd],spis[i][nk_td]])
        else:
            rez.append(["", spis[i][nk_dse], spis[i][nk_oper], spis[i][nk_kol], '', spis[i][nk_mar],"",""])
    rez.append(["-----", "-----", '------', "-----", "-----", "-----", "-----", "-----"])
    rez.append(['Примечание:', primech, '', "", "", "", "", ""])
    rez.append(["-----", "-----", '------', "-----", "-----", "-----", "-----", "-----"])
    rez.append(["Специалист   ", '_____', 'Сдал', '_____', "", "", "", ""])
    rez.append(["             ", '_____', 'Принял', '_____', "", "", "", ""])
    put = tmp_dir() + F.sep() + 'dir_kompl_ved.txt'
    if F.existence_file_c(put) == False:
        F.save_file(put, [[F.put_po_umolch()]])
    dir = F.load_file(put)
    dir_user = CQT.getDirectory(self, dir)
    if dir_user == ['.']:
        return
    else:
        F.save_file(put, [[dir_user]])
    rez = CEX.zap_spis(rez, dir_user, f'{nom_nar}_Ведомость_аутсорсинг.xlsx', '1', 0, 0, orient_g_v='g')
    if rez == False:
        CQT.msgbox('Файл_занят')
        return
    F.open_dir_c(dir_user)

def list_emploee_full_with_del(bd_users):
    query = f"""SELECT * FROM employee WHERE Пномер IN( SELECT Пномер FROM (SELECT
    	MAX(Пномер) as Пномер,
    	ФИО
    FROM
    	employee
    GROUP BY
    	ФИО
    HAVING COUNT(*) >= 1 )) order by ФИО;"""
    list_emploee_with_del = CSQ.custom_request_c(bd_users, query, rez_dict=True)
    return list_emploee_with_del

def dict_emploee(bd_users,conn=''):
    query = f"""SELECT * FROM employee WHERE Статус != 'Увольнение' AND Должность not in ('-','+','') """
    DICT_EMPLOEE = dict()
    list_emploee = CSQ.custom_request_c(bd_users, query, rez_dict=True,conn =conn)
    if list_emploee == False:
        return False
    for emploee in list_emploee:
        DICT_EMPLOEE[emploee['ФИО']] = emploee['Должность']
    return DICT_EMPLOEE

def dict_emploee_full(bd_users,conn='',self=None):
    list_emploee_with_del = list_emploee_full_with_del(bd_users)
    list_emploee = [_ for _ in list_emploee_with_del if _['Статус'] != 'Увольнение']
    if list_emploee == False:
        return False
    if self:
        self.DICT_EMPLOEE_FULL = F.deploy_dict_c(list_emploee,'ФИО')
        self.DICT_EMPLOEE_FULL_BY_SNUM = F.deploy_dict_c(list_emploee_with_del, 'Пномер')
        self.DICT_EMPLOEE_FULL_WITH_DEL = F.deploy_dict_c(list_emploee_with_del,'ФИО')
        self.DICT_EMPLOEE_FULL_WITH_DEL_ref = F.deploy_dict_c(list_emploee_with_del,'ID_ФизЛица')
    return F.deploy_dict_c(list_emploee,'ФИО')

def dict_emploee_full_with_del(bd_users,conn=''):
    list_emploee = list_emploee_full_with_del(bd_users)
    if list_emploee == False:
        return False
    return F.deploy_dict_c(list_emploee,'ФИО')


def DICT_CLD(bd_users):
    list_of_tbls = CSQ.get_list_of_tables_c(bd_users)
    rez = dict()
    for item in list_of_tbls:
        if 'rm_20' in item:
            list_days = CSQ.custom_request_c(bd_users,f"""SELECT * FROM {item} WHERE Пномер == 1 OR Пномер == 2""")
            for i in range(len(list_days[0])):
                if 'd_' in list_days[0][i]:
                    rez[F.strtodate(list_days[0][i],"d_%Y_%m_%d")] = {'Выходные':list_days[1][i],'День недели':list_days[2][i]}
    return  rez

def DICT_CLD_KPLAN(bd_kplan):
    list_of_tbls = CSQ.get_list_of_tables_c(bd_kplan)
    rez = dict()
    for item in list_of_tbls:
        if 'm_cld_' in item:
            list_days = CSQ.custom_request_c(bd_kplan,f"""SELECT * FROM {item}""")
            if len(list_days) <=1:
                print(f'{item} не заполнен')
                continue
            for i in range(len(list_days[0])):
                if 'd_' in list_days[0][i]:
                    dict_podr = dict()
                    for j in range(3,len(list_days)):
                        dict_podr[list_days[j][1]] = list_days[j][i]
                    try:
                        rez[F.strtodate(list_days[0][i],"d_%Y_%m_%d")] = {'Выходные':list_days[1][i],'День недели':list_days[2][i],'Подразделения':dict_podr}
                    except:
                        print(f'ОШибка расчета m_cld_')
                        return
    return  rez

def DICT_PLACES(self,bd_users):
    query = f"""SELECT * FROM places_capacity"""

    PLACES = CSQ.custom_request_c(bd_users, query, rez_dict=True)
    if PLACES == False:
        return False
    self.DICT_PLACES = F.deploy_dict_c(PLACES, 'adress')
    return

def dict_projects(self,file):
    spis = F.open_file_c(file, False, '|', False, False)
    rez = []
    tmp_list = []
    tmp_row = spis[0]
    tmp_row.insert(0, f'{spis[0][0]}${spis[0][1]}')
    tmp_row.pop(2)
    tmp_row.pop(1)
    tmp_list.append(tmp_row)
    for i in range(10, len(spis)):
        if len(spis[i]) >= 21:
            if spis[i][3] == 'к производству' or spis[i][3] == 'подготовка':
                tmp_row = spis[i]
                tmp_row.insert(0,f'{spis[i][0]}${spis[i][1]}')
                tmp_row.pop(2)
                tmp_row.pop(1)
                tmp_list.append(tmp_row)
    self.DICT_PROJECTS = F.list_to_dict(tmp_list,tmp_list[0][0])


def dict_emploee_rc(self,conn_inp = ''):
    if conn_inp == '':
        conn, cur = CSQ.connect_bd(F.bdcfg("BD_users"))
    else:
        conn = conn_inp
    custom_request_c = """SELECT rab_mesta.Код_РЦ, 
    s1.ФИО  || " " || s1.Должность as ФИО_1см,
      s2.ФИО || " " || s2.Должность as ФИО_2см, 
      s3.ФИО || " " || s3.Должность as ФИО_3см, 
      rab_mesta.Пномер, 
      rab_mesta.Прозвище 
       FROM rab_mesta
       INNER JOIN employee s1 ON s1.Пномер == rab_mesta.ФИО_1
       INNER JOIN employee s2 ON s2.Пномер == rab_mesta.ФИО_2
     INNER JOIN employee s3 ON s3.Пномер == rab_mesta.ФИО_3"""

    #custom_request_c2 = '''SELECT * FROM user_rc'''
    #rez2 = CSQ.custom_request_c(F.bdcfg("BD_users"), custom_request_c2,conn=conn)
    #if rez2 == False:
    #    return False
    self.DICT_EMPLOEE_RC = dict()
    self.DICT_EMPLOEE_RM = dict()
    try:
        rez = CSQ.custom_request_c(F.bdcfg("BD_users"),custom_request_c,conn=conn)
        self.DICT_RC_FULL = F.list_of_lists_to_dict_of_dicts(rez,'Пномер')
        if rez == False:
            return False
        for i in range(1, len(rez)):
            if rez[i][1] not in self.DICT_EMPLOEE_RC:
                self.DICT_EMPLOEE_RC[rez[i][1]] = rez[i][0]
            if rez[i][2] not in self.DICT_EMPLOEE_RC:
                self.DICT_EMPLOEE_RC[rez[i][2]] = rez[i][0]
            if rez[i][3] not in self.DICT_EMPLOEE_RC:
                self.DICT_EMPLOEE_RC[rez[i][3]] = rez[i][0]

            if rez[i][1] not in self.DICT_EMPLOEE_RM:
                self.DICT_EMPLOEE_RM[rez[i][1]] = {'Пномер':rez[i][4], 'Прозвище':rez[i][5], 'Смена':1}
            if rez[i][2] not in self.DICT_EMPLOEE_RM:
                self.DICT_EMPLOEE_RM[rez[i][2]] = {'Пномер':rez[i][4], 'Прозвище':rez[i][5], 'Смена':2}
            if rez[i][3] not in self.DICT_EMPLOEE_RM:
                self.DICT_EMPLOEE_RM[rez[i][3]] = {'Пномер':rez[i][4], 'Прозвище':rez[i][5], 'Смена':3}
        #for i in range(1, len(rez2)):
        #    if rez2[i][0] not in self.DICT_EMPLOEE_RC:
        #        self.DICT_EMPLOEE_RC[rez2[i][0]] = rez2[i][1]
    except:
        pass
    if conn_inp == '':
        CSQ.close_bd(conn,cur)
    #for key in self.DICT_EMPLOEE_RC.keys():
    #    if self.DICT_EMPLOEE_RC[key][:4] == '0103':
    #        print(key)
    return

def load_ved_komplekt(self, tbl_nar, tbl_viev):
    tbl = tbl_nar
    tblv = tbl_viev
    if tbl.currentRow() == -1:
        CQT.msgbox('Не выбран наряд')
        return
    nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
    nom_nar = tbl.item(tbl.currentRow(), nk_nom_nar).text()
    nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Номер_мк')
    nom_nom_mk = tbl.item(tbl.currentRow(), nk_nom_mk).text()
    data = F.now("%d.%m.%Y %H:%M")
    custom_request_c = f'''SELECT Номенклатура,Номер_заказа FROM mk WHERE Пномер == {int(nom_nom_mk)}'''
    query = CSQ.custom_request_c(CFG.Config.project.db_naryad, custom_request_c)
    poz = query[-1][0]
    py = query[-1][1]
    rez = [['№ документа', '', 'Дата(дд.мм.гггг)', 'ВЕДОМОСТЬ КОМПЛЕКТАЦИИ НАРЯДА', f'№{nom_nar}', 'Заказ'],
           [nom_nar, '', data, poz, '', py],
           ['Составил', 'ФИО', '', '', '', 'К маршрутной карте'],
           [job_post_by_empl_c(self.glob_login), name_by_empl_c(self.glob_login), '', '', '', nom_nom_mk],
           ['№', 'Обозначение ДСЕ', 'Операция/Вид', 'Количество', 'Отметки', 'Маршрут/Код']
           ]
    spis = CQT.list_from_wtabl_c(tblv, hat_c=True)
    nk_kol = F.num_col_by_name_in_hat_c(spis, 'Количество')
    nk_dse = F.num_col_by_name_in_hat_c(spis, 'ДСЕ')
    nk_mar = F.num_col_by_name_in_hat_c(spis, 'Маршрут')
    nk_oper = F.num_col_by_name_in_hat_c(spis, 'Операция')
    schet = 0
    for i in range(1, len(spis)):
        if '->' in spis[i][nk_mar]:
            schet += 1
            rez.append([schet, spis[i][nk_dse], spis[i][nk_oper], spis[i][nk_kol], '', spis[i][nk_mar]])
        else:
            rez.append(["", spis[i][nk_dse], spis[i][nk_oper], spis[i][nk_kol], '', spis[i][nk_mar]])
    rez.append(["---", "-----", '------', "-----", "----", "-----"])
    rez.append(["Комплектовщик", '_____', 'Сдал', '_____', "", ""])
    rez.append(["             ", '_____', 'Принял', '_____', "", ""])
    put = tmp_dir() + F.sep() + 'dir_kompl_ved.txt'
    if F.existence_file_c(put) == False:
        F.save_file(put, [[F.put_po_umolch()]])
    dir = F.load_file(put)
    dir_user = CQT.getDirectory(self, dir)
    if dir_user == ['.']:
        return
    else:
        F.save_file(put, [[dir_user]])
    rez = CEX.zap_spis(rez, dir_user, f'{nom_nar}_Ведомость_комплектации.xlsx', '1', 0, 0, orient_g_v='g')
    if rez == False:
        CQT.msgbox('Файл_занят')
        return
    F.open_dir_c(dir_user)

def load_tmp_folder(self, name_txt_file_without_rashir):
    put = tmp_dir() + F.sep() + name_txt_file_without_rashir +'.txt'
    if F.existence_file_c(put) == False:
        F.save_file(put, [[F.put_po_umolch()]])
    dir = F.load_file(put)
    dir_user = CQT.getDirectory(self, dir)
    if dir_user == ['.'] or dir_user == '.':
        return
    else:
        F.save_file(put, [[dir_user]])
    return dir_user

@CQT.onerror
def send_info_mk_b24(self, msg, id):
    conn = CB24.B24Sender()
    if not conn.send_msg_by_chat_id(id, msg):
        CQT.msgbox(f'Ошибка отправки запроса в Б24')


def b24_notation_user_fio(str_fio: str = F.user_full_namre()):
    str_fio_rez = str_fio
    wet_req_text = f"""ВЫБРАТЬ ПЕРВЫЕ 1  Пользователи.ПБ24_id_bitrix КАК ПБ24_id_bitrix
                                    ИЗ
                                        Справочник.Пользователи КАК Пользователи
                                    ГДЕ
                                        (Пользователи.Наименование = "{str_fio}"
                                        ИЛИ Пользователи.ФизическоеЛицо.ФИО = "{str_fio}")
                                    УПОРЯДОЧИТЬ ПО
                                        ПБ24_id_bitrix УБЫВ
                                        ;"""
    key, data_rez = APIERP.get_wet_request(wet_req_text)
    if key != 200:
        print(f'b24_notation_user_fio Ошибка получения данных код ({key}) из ERP')
    else:
        if data_rez['data']:
            id_user = data_rez['data'][0]['ПБ24_id_bitrix']
            str_fio_rez = f"[USER={id_user}]{str_fio}[/USER]"
    return str_fio_rez

@CQT.onerror
def send_info_mk_b24_by_action(msg, action: str,form_dict:dict=None,msg_bold:bool=False,basement_msg:str=None):
    sender = CB24.B24Sender()
    if not sender.send_msg_by_action(action, msg,form_dict=form_dict,msg_bold=msg_bold,basement_msg=basement_msg):
        CQT.msgbox(f'Ошибка отправки запроса в Б24')

@CQT.onerror
def send_tbl_b24_by_action(title, action: str,tbl:list[dict]):
    sender = CB24.B24Sender()
    if not sender.send_msg_table_by_action(action, title,tbl):
        CQT.msgbox(f'Ошибка отправки запроса в Б24')


def load_peresilniy(self, tbl_nar, tbl_viev):
    debug_mode = False
    if self.superuser:
        debug_mode = True
    def register_peresil(self,num:int,num_nar:int,password:int,list_for_b24_msg:list):
        s_num= num
        num_nar
        user_name= self.glob_ima
        account_win= F.user_name()
        pc= F.computer_name()
        date= F.now()

        list_vals = [s_num,num_nar,user_name,account_win,pc,date,password]
        query = f'''INSERT INTO log_peresiln (s_num,num_nar,user_name,account_win,pc,date,password) VALUES
         ({CSQ.questions_for_mask(list_vals)})'''
        CSQ.custom_request_c(self.db_naryd,query,list_of_lists_c=[list_vals])
        try:
            query = f"""SELECT mk.Номер_проекта, mk.Номер_заказа, mk.Номенклатура, mk.Пномер as Номер_МК,
                naryad.Пномер as Номер_нар, 
                log_peresiln.s_num, log_peresiln.user_name FROM naryad
                INNER JOIN mk on mk.Пномер == naryad.Номер_мк,
                log_peresiln on log_peresiln.num_nar == naryad.Пномер
                WHERE naryad.Пномер == {num_nar};"""
            rez = CSQ.custom_request_c(self.db_naryd,query,rez_dict=True)
            if rez == None or rez == False:
                CQT.msgbox(f'Ошибка доступа к БД')
                return
            rez = rez[0]
            msg = f"{rez['user_name']} выгрузил пересыльный на {rez['Номер_проекта']} {rez['Номер_заказа']}\n" \
                  f"(МК{rez['Номер_МК']} {rez['Номенклатура']}) наряд № {rez['Номер_нар']}"
            #tbl_str = F.list_txt_table_c(list_for_b24_msg)
            #line_tbl = '\n'.join(tbl_str)
            #send_info_mk_b24_by_action(msg, 'Управление пересыльными')
            send_tbl_b24_by_action(msg, 'Управление пересыльными',list_for_b24_msg)
            # send_info_mk_b24(self, msg, 'chat53443')
        except:
            print('Ошибка отправки в Б24')

    tbl = tbl_nar
    tblv = tbl_viev
    if tbl.currentRow() == -1:
        CQT.msgbox('Не выбран наряд')
        return
    nk_nom_nar = CQT.num_col_by_name_c(tbl,'Пномер')
    nom_nar = tbl.item(tbl.currentRow(),nk_nom_nar).text()
    existence_peresil = None
    if not debug_mode:
        existence_peresil = check_existence_peresil(self, nom_nar)
    if existence_peresil == False:
        return
    if existence_peresil:
        CQT.msgbox(
            f'Пересыльный на наряд {nom_nar} распечатан {existence_peresil["date"]} {existence_peresil["user_name"]}')
        return

    nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Номер_мк')
    nom_nom_mk = tbl.item(tbl.currentRow(), nk_nom_mk).text()
    data = F.now("%d.%m.%Y %H:%M")
    custom_request_c = f'''SELECT Номенклатура,Номер_заказа,Количество FROM mk WHERE Пномер == {int(nom_nom_mk)}'''
    query = CSQ.custom_request_c(self.db_naryd,custom_request_c)
    poz = query[-1][0]
    py = query[-1][1]
    count_izd = query[-1][2]
    last_num = CSQ.custom_request_c(self.db_naryd,f"""SELECT s_num FROM log_peresiln order by ROWID DESC limit 1""",hat_c=False, one_column=True)
    if last_num == False or last_num == None:
        CQT.msgbox(f'Ошибка загрузки из БД')
        return

    nom_peres = int(last_num[0]) + 1
    password = str(F.get_time_shtamp_c()).replace('.','')[-1:-5:-1]

    roof_tbl_part = ['№', 'Обозначение ДСЕ', 'Кол-во по нар.','Кол-во в сб. 1 изд.', 'Материал',  'Получение', 'Потребление','Отправка']
    rez = [['№ документа:','Наряд №','Дата(дд.мм.гггг):','ID','ПЕРЕСЫЛЬНЫЙ ЛИСТ НА ПРОЕКТ','','Заказ:','К маршрутной карте:'],
           [nom_peres,     nom_nar, data,               password,poz,                     '', py,       f'{nom_nom_mk} ({count_izd} изд.)'],
           ['Отправитель','ФИО','Получатель','','ФИО','','',''],
           [job_post_by_empl_c(self.glob_login),name_by_empl_c(self.glob_login),'','','','','',''],
           roof_tbl_part
           ]
    list_for_b24_msg = [copy.deepcopy(roof_tbl_part)]
    spis = CQT.list_from_wtabl_c(tblv,hat_c=True,rez_dict=True)
    def sign_osn_rc(rc):
        sign = ''
        if rc in self.DICT_RC_FULL:
            if self.DICT_RC_FULL[rc]['Вспомогательный'] == 0:
                sign = '*'
        return sign
    schet = 0
    for i in range(len(spis)):
        kolich = F.valm(spis[i]['Количество'])
        count_by_izd = spis[i]['Кол. *сегм. на заказ(вхожд)/1_изд(вхожд)/1_изд_по_структ./1_изд_в_сб']
        if len(spis[i]):
            segm_count = spis[i]['Число сегментов']
            if F.is_numeric(spis[i]['Число сегментов']):
                segm_count = F.valm(spis[i]['Число сегментов'])
                if segm_count > 1:
                    kolich = f'({segm_count} сегментов) {kolich}'
        if '->' in spis[i]['Маршрут']:
            schet +=1
            list_mar =  spis[i]['Маршрут'].split('->')
            poluch = list_mar[0]
            potr = list_mar[1]
            otpr = ''
            if len(list_mar)==3:
                otpr = list_mar[2]
            list_mat = []
            for j in range(i+1,len(spis)):
                if '->' in spis[j]['Маршрут']:
                    break
                list_mat.append(spis[j]['ДСЕ'].strip())
            mat_txt = ';'.join(list_mat)
            list_kol = count_by_izd.split(' / ')
            if len(list_kol) > 1:
                kol_by_sb = list_kol[3]

            tmp_list_for_exel = [schet,spis[i]['ДСЕ'], f'{kolich}',kol_by_sb, mat_txt ,"'"+poluch+sign_osn_rc(poluch),"'"+potr+sign_osn_rc(potr),"'"+otpr+sign_osn_rc(otpr)]
            poluch_b24 = poluch + sign_osn_rc(poluch) if poluch else "-"
            potr_b24 = potr + sign_osn_rc(potr) if potr else "-"
            otpr_b24 = otpr + sign_osn_rc(otpr) if otpr else "-"
            tmp_list_for_b24 = [schet,spis[i]['ДСЕ'], f'{kolich}',kol_by_sb, f"№{schet}) {mat_txt}" ,
                                f"№{schet}) {poluch_b24}",
                                f"№{schet}) {potr_b24}",
                                f"№{schet}) {otpr_b24}"]
            rez.append(tmp_list_for_exel)
            list_for_b24_msg.append([str(_) for _ in tmp_list_for_b24])

    #rez.append(["-------------------", "-------------------", '-------------------',  "-----------","-"*106, "-----------", "-----------", "-----------"])
    rez.append(["ОТК", '___________', 'Принял', '_________','',  "Сдал", "___________",""])

    def fcn_oform(tbl:QtWidgets.QTableWidget):
        headers = (5,6,7)
        for header_i in headers:
            for i in range(tbl.rowCount()):
                if '*' in tbl.item(i, header_i).text():
                    tbl.item(i, header_i).setText(tbl.item(i, header_i).text().replace('*',''))
                    CQT.font_cell_size_format(tbl, i, header_i, 0, True)
        headers = (0,4)
        for header_i in headers:
            for i in range(tbl.columnCount()):
                CQT.font_cell_size_format(tbl,header_i,i,0,True)
            tbl.setRowHeight(header_i,round(tbl.rowHeight(header_i)*2.1))
        font = tbl.horizontalHeaderItem(i).font()
        tbl.setColumnWidth(0,  int(12*font.pointSize()))
        tbl.setColumnWidth(1,  int(28*font.pointSize()))
        tbl.setColumnWidth(2,  int(14*font.pointSize()))
        tbl.setColumnWidth(3,  int(8 *font.pointSize()))
        tbl.setColumnWidth(4,  int(70*font.pointSize()))
        tbl.setColumnWidth(5,  int(10*font.pointSize()))
        tbl.setColumnWidth(6,  int(12*font.pointSize()))
        tbl.setColumnWidth(7,  int(10*font.pointSize()))

        #CQT.tbl_encircle(tbl,0,0,tbl.rowCount()-1,tbl.columnCount()-1)
        border = CQT.tbl_encircle(tbl, 0, 0, 0, tbl.columnCount() - 1, thick_in=1,thick_out=2)
        #CQT.tbl_encircle(tbl, tbl.rowCount()-1, 0, tbl.rowCount()-1, tbl.columnCount() - 1)
        try:
            border.add_corner_inside((1, 0), (3, tbl.columnCount() - 1), thick=2)
            border.add_corner_inside((4, 0), (4, tbl.columnCount() - 1), thick=2)
            border.add_corner_inside((5, 0), (tbl.rowCount()-2, tbl.columnCount() - 1), thick=2,horizontal_inline=True,)
            border.add_corner_inside((tbl.rowCount()-1, 0), (tbl.rowCount()-1, tbl.columnCount() - 1), thick=2)
        #tbl.resizeColumnToContents()
        except:
            CQT.msgbox('Ошибка обводки таблицы')

        tbl.custBorderInfo = border

    self.tmp_printout = False
    rez = CQT.msgboxg_get_table(self,'Сохранение пересыльного',rez,'','Выход',disable_btn0=True,show_filtr=False,
                          func_oform_tbl=fcn_oform,use_first_row_as_header=False,WindowTitle=f'Пересыльный№_{nom_peres}',print_hat=False)

    #dir_user = load_tmp_folder(self, "dir_kompl_ved")
    #rez = CEX.zap_spis(rez,dir_user,f'{nom_nar}_пересыльный.xlsx','1',0,0,orient_g_v='g')

    if self.tmp_printout == True:
        if not debug_mode:
            register_peresil(self,nom_peres,nom_nar,password,list_for_b24_msg)
        F.open_dir_c(self.tmp_printout_dir)

def dict_rc(self, db_users,conn = ''):
    self.DICT_RC = dict()
    custom_request_c = f'''SELECT 
rab_c.Код,
rab_c.Имя,
rab_c.Примечание,
rab_c.Подмена_рц_для_плана,
rab_c.Цвет,
rab_c.empl_Подразделение,
rab_c.Отв_мастер_тдз,
rab_c.Наим_СТО,
rab_c.Сокр_наим_СТО,
rab_c.Наим_ЕРП,
rab_c.СКУД_id,
rab_c.Вспомогательный,
rab_c.poki, 
etaps.name as etaps_name,
use_in_estimate_plan as use_in_estimate_plan 
     FROM rab_c INNER JOIN etaps ON etaps.s_num = rab_c.etaps_num'''
    self.SPIS_RC = CSQ.custom_request_c(CFG.Config.project.db_users, """SELECT * FROM rab_c""")
    SPIS_RC = CSQ.custom_request_c(db_users, custom_request_c, hat_c=False,rez_dict=True, attach_dbs=CFG.Config.project.db_naryad)
    self.DICT_RC = F.deploy_dict_c(SPIS_RC,'Код')
    self.DICT_PODR_RC = F.deploy_dict_c(SPIS_RC, 'empl_Подразделение')


def dict_rab_mesta(self = None, db_users: str = None, conn_users=None): #26.01.2026
    q = """SELECT rm.Пномер,
                    rm.Прозвище,
                    rm.coord,
                    rm.Расположение,
                    COALESCE(sw1.employee_id, 1) AS ФИО_1,
                    COALESCE(sw2.employee_id, 1) AS ФИО_2,
                    COALESCE(sw3.employee_id, 1) AS ФИО_3
             FROM rab_mesta rm
             LEFT JOIN schedule_work_places sw1 ON sw1.workplace_id = rm.Пномер AND sw1.shift_no = 1
             LEFT JOIN schedule_work_places sw2 ON sw2.workplace_id = rm.Пномер AND sw2.shift_no = 2
             LEFT JOIN schedule_work_places sw3 ON sw3.workplace_id = rm.Пномер AND sw3.shift_no = 3
          """
    rows = CSQ.custom_request_c(db_users, q, rez_dict=True, hat_c=False)
    DICT_RM = {} #27.01.2026
    if rows:
        for r in rows:
            pnom = int(r.get('Пномер'))
            DICT_RM[pnom] = {
                'Прозвище': r.get('Прозвище') or '',
                'coord': r.get('coord') or '',
                'Расположение': r.get('Расположение') if r.get('Расположение') is not None else 0,
                'ФИО_1': r.get('ФИО_1') if r.get('ФИО_1') is not None else 1,
                'ФИО_2': r.get('ФИО_2') if r.get('ФИО_2') is not None else 1,
                'ФИО_3': r.get('ФИО_3') if r.get('ФИО_3') is not None else 1,
            }
    if self is None:
        return DICT_RM
    self.DICT_RM = DICT_RM

def dict_napravl(self, db_kplan):
    self.DICT_NAPRAVL = dict()
    custom_request_c = f'''SELECT * FROM napravlenie'''
    SPIS_napr = CSQ.custom_request_c(db_kplan, custom_request_c, hat_c=False,rez_dict=True)
    self.DICT_NAPRAVL = F.deploy_dict_c(SPIS_napr,'name')
    return self.DICT_NAPRAVL

def dict_professions(self, db_users, conn = ''):
    self.DICT_PROFESSIONS = dict()
    custom_request_c = f'''SELECT * FROM professions 
    LEFT JOIN vid_rab_po_dolg ON vid_rab_po_dolg.Вид_работ = professions.вид_работ
    LEFT JOIN group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan
    WHERE professions.poki = {CFG.Config.place.poki} AND professions.Вкл = 1 and group_vid_rab_for_plan.composite = 0'''
    SPIS_prof = CSQ.custom_request_c(db_users, custom_request_c, hat_c=False,rez_dict=True,conn=conn)
    if SPIS_prof == False:
        return  False
    self.LIST_PROFESSIONS = SPIS_prof
    self.DICT_PROFESSIONS = F.deploy_dict_c(SPIS_prof,'код')
    self.DICT_PROFESSIONS_NAME = F.deploy_dict_c(SPIS_prof, 'имя')
    self.DICT_PROFESSIONS_PSEUDONAME = F.deploy_dict_c(SPIS_prof, 'Псевдоним')
    self.DICT_VID_RABOT = F.deploy_dict_c(SPIS_prof, 'вид_работ')
    self.DICT_PROFESSIONS_NICKNAME =F.deploy_dict_c(CSQ.custom_request_c(db_users,f"""SELECT 
    * FROM group_vid_rab_for_plan;""",rez_dict=True),'nick_name')
    return

def dict_etapi(self, db_naryd, conn = '',cur = ''):
    """
    стадия МК(ресурсной)
    этап с 24.03.2025 по РЦ до этого по имени операции (operacii)/
    вид работ - по профессии

    стадия выгрузки трудов
    этап по должности исполнителя (dolgn_etap)
    вид работ по должности исполнителя (professions)

    """
    self.DICT_ETAPI = dict()
    custom_request_c = f'''SELECT * FROM operacii WHERE poki == {CFG.Config.place.poki}'''
    SPIS_OP = CSQ.custom_request_c(db_naryd,custom_request_c,hat_c=False, conn=conn, cur = cur,rez_dict=True)
    if SPIS_OP == False:
        return False
    for i in range(len(SPIS_OP)):
        self.DICT_ETAPI[SPIS_OP[i]['name']] = SPIS_OP[i]['etap']



def dict_opers(self, db_naryd):
    self.DICT_OPER_FULL = dict()
    custom_request_c = f'''SELECT * FROM operacii WHERE poki == {CFG.Config.place.poki}'''
    SPIS_OP = CSQ.custom_request_c(db_naryd,custom_request_c,hat_c=False,rez_dict=True)
    self.DICT_OPER_FULL = F.deploy_dict_c(SPIS_OP,'name')


def dict_rc_po_oper(self, db_naryd):
    self.DICT_RC_PO_OPER = dict()
    custom_request_c = f'''SELECT * FROM operacii WHERE poki == {CFG.Config.place.poki}'''
    SPIS_OP = CSQ.custom_request_c(db_naryd,custom_request_c,hat_c=False)
    for i in range(len(SPIS_OP)):
        self.DICT_RC_PO_OPER[SPIS_OP[i][1]] = SPIS_OP[i][3]


def dict_kod_oper(self,db_naryad):
    query = f"""SELECT kod, name FROM operacii WHERE poki == {CFG.Config.place.poki}"""
    self.DICT_KOD_OPER = F.deploy_dict_c(
        CSQ.custom_request_c(self.db_naryad, query, rez_dict=True), 'name')

def segment_count(text_per:str, by_default=1):
    segment_count = by_default
    text_per= text_per.strip()
    if 'част' in text_per.lower() or \
            'егмент' in text_per.lower() or \
            'сектор' in text_per.lower():
        list_text_per = text_per.split()
        if len(list_text_per) == 2:
            if F.is_numeric(list_text_per[-1]):
                segment_count = int(list_text_per[-1])
            else:
                if F.is_numeric(list_text_per[0]):
                    segment_count = int(list_text_per[0])
            return segment_count
        if len(list_text_per) == 3:
            if F.is_numeric(list_text_per[1]):
                segment_count = int(list_text_per[1])
            return segment_count
    return segment_count


def specification_task_c(self, tblk, tblv,conn='',cur = ''):
    r = tblk.currentRow()
    if r == -1:
        return
    nk_nom_nar = CQT.num_col_by_name_c(tblk, 'Пномер')
    nk_vnepl = CQT.num_col_by_name_c(tblk, 'Внеплан')
    nom_nar = int(tblk.item(r, nk_nom_nar).text())
    vnepl = int(tblk.item(r, nk_vnepl).text())
    if vnepl == 1:
        return
    custom_request_c = f'''SELECT ДСЕ, Операции, Опер_колво, Номер_мк, Опер_время,ДСЕ_ID FROM naryad WHERE Пномер == {nom_nar}'''

    query = CSQ.custom_request_c(self.db_naryd,custom_request_c,rez_dict=True)
    if query == False:
        CSQ.close_bd(conn,cur)
        CQT.msgbox(f'БД занята пробуй позже')
        return

    rez = [['ДСЕ', "Операция", "Количество", "Маршрут", "Операции", "Время", 'КД', "ТД",'Число сегментов','Кол. *сегм. на заказ(вхожд)/1_изд(вхожд)/1_изд_по_структ./1_изд_в_сб']]
    dse = query[-1]['ДСЕ'].split('|')
    dse_id = query[-1]['ДСЕ_ID'].split('|')
    oper = query[-1]['Операции'].split('|')
    kol = query[-1]['Опер_колво'].split('|')
    vrema = query[-1]['Опер_время'].split('|')
    mk = query[-1]['Номер_мк']
    res = load_res(int(mk))
    kd = ''
    if dse == [''] and oper == [''] and kol == ['']:
        return
    count_izd = res[0]['Количество']
    for i in range(len(dse)):
        dse_name = dse[i].split('$')[0]
        dse_nn = dse[i].split('$')[1]
        oper_nom = oper[i].split('$')[0]
        oper_naim = oper[i].split('$')[1]
        id = dse_id[i]
        spis_mar = []
        spis_oper = []
        rez_vhodyash_tmp = []
        rez_vhodyash_mat_tmp = []
        flag_dse_naid = False


        for i_dse, dse_res in enumerate(res):
            if dse_res['Номерпп'] == int(id):
                segment_count_dse = 1
                flag_dse_naid = True
                kd = dse_res['Ссылка']
                # ------ расчет входящих деталей======
                level_c = dse_res['Уровень']
                if int(kol[i]) == 0:
                    koef_kolich = 0
                else:
                    koef_kolich = dse_res['Количество'] / int(kol[i])
                if i_dse + 1 < len(res) and res[i_dse + 1]['Уровень'] == level_c + 1:
                    for j in range(i_dse + 1, len(res)):
                        if res[j]['Уровень'] != level_c + 1:
                            break
                        if koef_kolich == 0:
                            res_kolich = 0
                        else:
                            res_kolich = res[j]['Количество'] / koef_kolich
                        rez_vhodyash_tmp.append([f'    {res[j]["Наименование"]} {res[j]["Номенклатурный_номер"]}',
                                                 f'{"-входящая-"}', res_kolich, '',
                                                 '','',"","","",""])
                # =============================================================
                flag = False
                last_oper = {'Опер_РЦ_код': 'xxxx', "Опер_наименование": 'xxxx', 'Опер_РЦ_наименование': 'xxxx'}
                first_nom_oper = ''
                flag_oper_naid = False
                osn_mat_dse = []
                for i_oper, oper_res in enumerate(dse_res['Операции']):
                    if i_oper == 0:
                        first_nom_oper = oper_res['Опер_номер']
                    segment_count_dse = dse_res['кол_во_инф']['кол_во_сегментов']

                    # ------ подбор основного материала ======
                    for mat in oper_res['Материалы']:
                        if mat['Мат_код'] not in self.DICT_NOMEN:
                            CQT.msgbox(f'Материал код {mat["Мат_код"]} отсутствует в БД, обратиться в ТО')
                            return
                        vid = self.DICT_NOMEN[mat['Мат_код']]['Вид']
                        vid_ref = self.DICT_NOMEN[mat['Мат_код']]['Вид_Ref_Key'] # 22.10.25 100061930
                        if vid_ref not in self.DICT_VIDS_NOMEN_BY_REF:
                            CQT.msgbox(f'В {dse_res["Номенклатурный_номер"]}, для Мат_код "{mat["Мат_код"]}" Вид номенклатуры "{vid}" отсутствует в БД ВидыНоменклатуры, обратиться в ТО')
                            return
                        if self.DICT_VIDS_NOMEN_BY_REF[vid_ref]['Основной_мат_для_пересыльных']:
                            if koef_kolich == 0:
                                res_kolich = 0
                            else:
                                res_kolich = mat["Мат_норма"] / koef_kolich
                            osn_mat_dse.append(
                                [f'    Справочно {round(res_kolich, 2)} {mat["Мат_ед_изм"]} {mat["Мат_наименование"]}', f'{"-материал-"}',
                                 0, mat["Мат_код"], "", '', "", "", "", ""])
                    if oper_res['Опер_номер'] == oper_nom:
                        flag_oper_naid = True
                        td = '$'.join(oper_res['Опер_документы'])
                        spis_mar.append(last_oper['Опер_РЦ_код'])
                        spis_oper.append(f'{last_oper["Опер_наименование"]} ({last_oper["Опер_РЦ_наименование"]})')
                        # ------ добавление основных матриалов======
                        for osn_mat in osn_mat_dse:
                            rez_vhodyash_mat_tmp.append(osn_mat)
                        # ------ расчет входящих материалов======
                        for mat in oper_res['Материалы']:
                            if mat['Мат_норма'] >= 0.001:
                                if koef_kolich == 0:
                                    res_kolich = 0
                                else:
                                    res_kolich = mat["Мат_норма"] / koef_kolich
                                rez_vhodyash_mat_tmp.append(
                                    [f'    {mat["Мат_наименование"]}, {mat["Мат_ед_изм"]}', f'{"-материал-"}',
                                     round(res_kolich,2) , mat["Мат_код"], "",'',"","","",""])
                        # =========================================
                        flag = True
                    if flag == True:
                        spis_mar.append(oper_res['Опер_РЦ_код'])
                        if i_oper+1 < len(dse_res['Операции']):
                            spis_mar.append(dse_res['Операции'][i_oper+1]['Опер_РЦ_код'])
                        spis_oper.append(f'{oper_res["Опер_наименование"]} ({oper_res["Опер_РЦ_наименование"]})')
                        break
                    last_oper = oper_res

                break
        if flag_dse_naid== False:
            CQT.msgbox(f'Не найдена в ресурсной ДСЕ, {dse_name}, {dse_nn}')
            return
        if flag_oper_naid == False:
            CQT.msgbox(f'Не найдена Операция, {oper_nom}')
            return
        oper1 = spis_oper[0]
        oper2 = spis_oper[1]

        rez.append([f'{dse_nn} {dse_name}', f'{oper_nom} {oper_naim}', kol[i], '->'.join(spis_mar),
                    f'Взять ДСЕ из операции {oper1}, и укомплектовать в операцию {oper2}',vrema[i],kd,td,
                    segment_count_dse,
                    f"{dse_res['кол_во_инф']['кол_во_заказ_все_вхождения']*segment_count_dse} / {dse_res['кол_во_инф']['кол_во_1_изд_все_вхождения']*segment_count_dse} "
                    f"/ {dse_res['кол_во_инф']['кол_во_1_изд_по_структуре']*segment_count_dse} / {dse_res['кол_во_инф']['кол_во_1_изд_в_сборку']*segment_count_dse}"])
        if oper_nom == first_nom_oper:
            for item in rez_vhodyash_tmp:
                rez.append(item)
        for item in rez_vhodyash_mat_tmp:
            rez.append(item)
    CQT.fill_wtabl(rez, tblv,{},700,20,24, True,False)
    tblv.setColumnHidden(F.num_col_by_name_in_hat_c(rez, 'Операции'), True)
    tblv.setColumnHidden(F.num_col_by_name_in_hat_c(rez, 'Время'), True)
    tblv.setColumnHidden(F.num_col_by_name_in_hat_c(rez, 'КД'), True)
    tblv.setColumnHidden(F.num_col_by_name_in_hat_c(rez, 'ТД'), True)



def list_of_mats_erp_c(self, nom_mk, spis_filtr_mat, po_tk = False, spis_dse=''):
    if spis_dse == '':
        if po_tk == False:
            spis_dse = load_res(int(nom_mk))
        else:
            query = f'''SELECT xml.data as xml, mk.Количество, res.data as Ресурсная, xml.Head as xml_head FROM mk 
                        INNER JOIN xml ON mk.Пномер = xml.Номер_мк
                        INNER JOIN res ON mk.Пномер = res.Номер_мк
                        WHERE Пномер == {int(nom_mk)}
                                    '''
            rez_xml = CSQ.custom_request_c(self.bd_naryad, query)
            xml = rez_xml[-1][0]
            xml_head = rez_xml[-1][3]
            if xml == '':
                CQT.msgbox('Нет хмл файла')
                return
            spis_dse = resource_from_xml_c(self, self.podgotovka_xml(XML.spisok_iz_xml(str_f=xml),xml_head), kol_vo_izdeliy=rez_xml[-1][1])
            #spis_dse = load_res_po_tk(self.resource_from_xml_c(sp_xml_tmp, self.kol_izdeliy))
        if spis_dse == False:
            CQT.msgbox('Не создана МК')
            return
    rez = list_of_mats_by_MK_c(spis_dse,spis_filtr_mat)
    return rez


def list_of_mats_by_MK_c(spis_dse,spis_filtr_mat):
    rez = [['Код', "Наименование", "Ед.изм.", "Норма на кол_во","Норма на кол_во по КД", 'Тпз_мин.', 'Тшт_мин. на кол_во', 'РЦ',
                'Оборудование', 'Профессия','Этап', 'N_Операция', 'Операция', 'Номенклатурный_номер', 'Наименование',
                'Количество на мк','Уровень древа']]
    err_arr = []
    for i in range(1, len(spis_dse)):
        nn = spis_dse[i]['Номенклатурный_номер']
        naim = spis_dse[i]['Наименование']
        kolvo = spis_dse[i]['Количество']
        ves_kd = 0
        list_mat = spis_dse[i]['Мат_кд'].split('/')
        if list_mat[1] != '' and list_mat[1] != '' :
            ves_kd = F.valm(list_mat[0])
        level_c = spis_dse[i]['Уровень']
        for oper in spis_dse[i]['Операции']:
            rc = oper['Опер_РЦ_код']
            oper_nom = oper['Опер_номер']
            oper_name = oper['Опер_наименование']
            tpz = oper['Опер_Тпз']
            tsht = oper['Опер_Тшт']
            oborud = oper['Опер_оборудование_наименование']
            professia = oper['Опер_профессия_наименование']
            etap = oper['Этап']
            """rez.append(
               ['', '', '', '', tpz, tsht, rc, oborud, professia, oper_nom, oper_name, nn, naim,
                 kolvo])"""
            for mat in oper['Материалы']:
                kod = mat['Мат_код']
                fl_add = True
                for f_kod, f_filtr in spis_filtr_mat:
                    if f_kod == kod:
                        if f_filtr == 1:
                            fl_add = False
                        break
                if fl_add == True:
                    mat_naim = mat['Мат_наименование']
                    ed_izm = mat['Мат_ед_изм']
                    mat_norma = mat['Мат_норма']
                    rez.append(
                        [kod, mat_naim, ed_izm, mat_norma, round(ves_kd*kolvo,2) , tpz, tsht, rc, oborud, professia,etap, oper_nom, oper_name, nn,
                         naim, kolvo,level_c])
                    tpz = 0
                    tsht = 0
                    kolvo = 0
                    ves_kd = 0
                    level_c = ''
    return rez


def add_mats_into_list_c(spis:list,list_mat,kolvo):
    if list_mat == '':
        return spis
    list_mat = list_mat.split('$')
    if len(list_mat) == 5:
        return spis
    list_mat[3] = F.valm(list_mat[3])*int(kolvo)
    flag = False
    for i in range(len(spis)):
        if spis[i][0] == list_mat[0] and spis[i][4] == list_mat[4] \
                and spis[i][5] == list_mat[5] and spis[i][6] == list_mat[6] and spis[i][7] == list_mat[7]:
            spis[i][3]+=list_mat[3]
            flag = True
            break
    if flag == False:
        spis.append(list_mat)
    return spis

def load_tmp_path(ima):
    if F.existence_file_c(tmp_dir() + os.sep + ima + '.txt') == True:
        tmp_putt = F.open_file_c(tmp_dir() + os.sep + ima + '.txt', False, '')[0]
    else:
        tmp_putt = F.put_po_umolch()
    return tmp_putt

def load_tmp_val(ima,default_val = None,autotype=False,db_kplan=None):
    fl = False
    if db_kplan:
        val = CSQ.custom_request_c(db_kplan,f"""SELECT val FROM general_settings WHERE name == "{ima}";""",one_column=True,hat_c=False)# 11.11.25
        if val == None or val == "":
            return default_val
        fl = True
    else:
        if F.existence_file_c(tmp_dir() + os.sep + ima + '.txt') == True:
            val = F.open_file_c(tmp_dir() + os.sep + ima + '.txt', False, '')
            if val == []:
                return default_val
            fl = True
    if fl:
        val = val[0]
        if autotype:
            if F.is_numeric(val):
                return F.valm(val)
            if F.is_bool(val):
                return F.boolm(val)
        return val
    return  default_val


def load_tmp_stukt(ima,default_val = None):
    puth_name = tmp_dir() + os.sep + ima + '.pickle'
    if F.existence_file_c(puth_name) == True:
        try:
            val = F.load_file_pickle(puth_name)
            return val
        except:
            print(f'Err load_tmp_stukt')
            return default_val
    return default_val

def update_width_filtr(tbl,tblf):
    for i in range(tbl.columnCount()):
        w = tbl.columnWidth(i)
        tblf.setColumnWidth(i, w)
        if tbl.isColumnHidden(i):
            tblf.hideColumn(i)
        else:
            tblf.showColumn(i)
    tblf.verticalHeader().setFixedWidth(tbl.verticalHeader().width())

def save_tmp_path(ima,put,ubrat_filename=False):
    if ubrat_filename:
        arr_tmp_putt = put.split(os.sep)
        arr_tmp_putt.pop()
        put = F.sep().join(arr_tmp_putt)
    F.write_file_c(tmp_dir() + os.sep + ima +'.txt', [put], '')
    return put


def save_tmp_val(name, val, db_kplan = None):
    if db_kplan:
        CSQ.custom_request_c(db_kplan,f"""UPDATE general_settings SET val = "{str(val)}" WHERE name = "{name}";""")
        return
    F.write_file_c(tmp_dir() + os.sep + name + '.txt', [str(val)], '')

def save_tmp_stukt(data,name):
    puth_name = tmp_dir() + os.sep + name + '.pickle'
    F.save_file_pickle(puth_name,data)

def values_of_filter_c(self,tblf):
    spis_znach = CQT.list_from_wtabl_c(tblf,'',False)
    return spis_znach

def fill_summ_tbl(self, tbls:QtWidgets.QTableWidget, tbl:QtWidgets.QTableWidget,
                  set_name_calc:(set|None) = None, hidden_scroll:bool = True,
                  calc_hidden_rows:bool= False,round_summ_digit:int = 2, average:bool=False):
    CQT.fill_summ_tbl(self, tbls, tbl,
                  set_name_calc = set_name_calc, hidden_scroll = hidden_scroll,
                  calc_hidden_rows= calc_hidden_rows,round_summ_digit = round_summ_digit, average=average)





def fill_filtr_c(self, tblf:QtWidgets.QTableWidget, tbl:QtWidgets.QTableWidget, spis_znach='', hidden_scroll=True):
    CQT.fill_filtr_c(self, tblf, tbl, spis_znach=spis_znach,
                     hidden_scroll=hidden_scroll)


def set_val_filtr_c(tblf:QtWidgets.QTableWidget, val, name_column):
    col = CQT.num_col_by_name_c(tblf,name_column)
    if col:
        tblf.item(0,col).setText(val)

def apply_summ_с(self,tbl, sredn = False):
    CQT.apply_summ_с(tbl, sredn=sredn)


def apply_filtr_c(self,tblf,tbl,save_data=True,get_dict_by_fild:None|str=None)->dict:
    return CQT.apply_filtr_c(self,tblf,tbl,save_data=save_data,get_dict_by_fild=get_dict_by_fild)

def note_OGK_c(strok:str):
    try:
        tmp = strok.split('(ОГК: ')
        tmp2 = tmp[-1].split(')')
        return tmp2[0]
    except:
        return ''

def load_csv(self,db_nomen,db_kplan):
    if self.glob_nom_mk == "":
        CQT.msgbox('Невыбрана мк')
        return False
    nom_mk = str(self.glob_nom_mk)
    nom_kpl = CSQ.custom_request_c(self.db_naryd,f'''SELECT  НомКплан FROM mk WHERE Пномер = {int(nom_mk)}''',one_column=True,one=True,hat_c=False)
    if nom_kpl == None or nom_kpl == False:
        CQT.msgbox(f'Не найден норма КПЛ')
        return #11.11.25 exclude nom_kpl (т.к. возвращается уже распакованый)
    otv_technolog_query = CSQ.custom_request_c(self.db_kplan,f'''SELECT пл_топ.Отв_технолог FROM пл_топ INNER JOIN plan
        ON plan.Пномер = пл_топ.НомПл WHERE plan.Пномер = {nom_kpl}''',one_column=True,one=True,hat_c=False)
    if otv_technolog_query == None or otv_technolog_query == False:
        otv_technolog = ''
    else:
        otv_technolog = otv_technolog_query #11.11.25

    if user_access(self.db_naryd,'создание_задание_на_резку',name_by_empl_c(self.glob_login)) == False and self.glob_ima != otv_technolog:
        return False


    tmp_putt = load_tmp_path("tmp_put_csv")

    put = CQT.getDirectory(self,tmp_putt)
    if put == None or put == '.':
        return False

    save_tmp_path("tmp_put_csv", put, False)

    rc = '010101'#010101


    conn_res, cur_res = CSQ.connect_bd(F.bdcfg('db_resxml'))
    squery = f"""SELECT CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
        
        
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа, 
        
        CASE WHEN plan.Приоритет IS NOT NULL 
       THEN plan.Приоритет 
       ELSE mk.Приоритет 
       END AS Приоритет 
        
         FROM mk 
         LEFT JOIN plan ON plan.Пномер = mk.НомКплан  
       LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 

    
               WHERE mk.Пномер = {int(nom_mk)}"""
    query = CSQ.custom_request_c(F.bdcfg('Naryad'),squery,rez_dict=True,one=True,attach_dbs=(self.db_kplan))

    np =query['Номер_проекта'][-3:]
    py =query['Номер_заказа'][-4:]
    if py == "*":
        CQT.msgbox(f'Выгрузить CSV без заказа на производство нельзя.')
        return False
    prioritet = str(query['Приоритет'])
    nppy = np + "-" + py #+"-" + nom_mk
    put += os.sep + nppy+'-'+nom_mk
    if F.existence_file_c(put)== False:
        F.create_dir_c(put)
    spis_dse = F.from_binary_pickle(CSQ.custom_request_c(F.bdcfg('db_resxml'),f"""SELECT data FROM res WHERE Номер_мк = {int(nom_mk)}""",rez_dict=True,one=True,conn=conn_res,cur=cur_res)['data'])
    try:
        test_dse = F.from_binary_pickle(CSQ.custom_request_c(F.bdcfg('db_resxml'),f"""SELECT data FROM res WHERE Номер_мк = 902""",rez_dict=True,one=True,conn=conn_res,cur=cur_res)['data'])
        CSQ.close_bd(conn_res, cur_res)
        spis_dse.insert(0, test_dse[0])
        set_mat_tolsh = set()
    except:
        CSQ.close_bd(conn1,cur1)
        CSQ.close_bd(conn_res, cur_res)
        CQT.msgbox(f'Не удалось загрузить тестовую деталь по МК902')
        return False

    rez_csv = [["путь и дет. -", "название дет. -", "кол-во -", "код из номенклатуры технолога ", "толщина из номенклауры технолога -","3проект_4ПУ_Нмк -","заменяем на номерМК -","Приоритет -","Технолог -","Гравировка -"]]

    #nomenklatura = F.open_file_c(F.scfg('bd_prof')+ os.sep + "bd_mater.txt",separ='|')
    nomenklatura = CSQ.custom_request_c(db_nomen,"""SELECT * FROM nomen WHERE На_удаление == 0""",rez_dict=True)
    nomenklatura = F.deploy_dict_c(nomenklatura,'Код')

    err_arr = []
    #найти колонку с лазерной резкой 010101 и найти операцию там

    poki = CFG.Config.place.poki
    custom_request_c = f'''SELECT Номенклатурный_номер, Номер_техкарты, Примечание FROM dse WHERE poki = {poki}''' #18.04.25
    rez = CSQ.custom_request_c(self.db_dse, custom_request_c, hat_c=True,rez_dict=True)


    DICT_NN_NTK = F.deploy_dict_c(rez,'Номенклатурный_номер')


    for dse in spis_dse:
        for oper in dse['Операции']:
            if oper['Опер_РЦ_код'] == rc:
                gravir = ''
                op = oper['Опер_номер']
                nn = dse['Номенклатурный_номер']
                naim = dse['Наименование']
                kolvo = dse['Количество']
                nom_tk = DICT_NN_NTK[nn]['Номер_техкарты']
                primech = DICT_NN_NTK[nn]['Примечание']
                if 'грав.' in primech:
                    gravir = '1'
                if nn == 'ТОП.ПР.008' and naim == 'ETALON':
                    putf = F.scfg('add_docs') + os.sep + nom_tk + '_' + nn + '.pickle'
                else:
                    putf = F.scfg('bd_mk') + os.sep + nom_mk + os.sep + nom_tk + '_' + nn + '.pickle'

                if F.existence_file_c(putf):
                    nk_rc_tk = 4
                    nk_ur_tk = 20
                    nk_op_tk = 2
                    nk_mat_tk = 10
                    nk_doc_tk = 15
                    nk_textper = 0
                    set_segment = {"част","сегм","сект"}
                    sp_tk = F.open_file_c(putf, False, "|", pickl=True)
                    if sp_tk == None:
                        F.copy_file_c(F.scfg('add_docs') + os.sep + nom_tk + '_' + nn + '.pickle',putf)
                        sp_tk = F.open_file_c(putf, False, "|", pickl=True)
                        if sp_tk == None:
                            CQT.msgbox(f'ОШибка чтения ТК {putf}')
                            return False
                    try:
                        ima_tehnolog = sp_tk[3][0]
                    except:

                        CQT.msgbox(f'ошибка в ТК {putf} ')
                        return False
                    print(f'{nn}:')
                    for j in range(11,len(sp_tk)):
                        if sp_tk[j][nk_ur_tk] == '1':
                            print(f'    {sp_tk[j][2]} {sp_tk[j][0]} {";".join(sp_tk[j][14].split("$"))}')
                        if sp_tk[j][nk_ur_tk] == '0':
                            break
                        if sp_tk[j][nk_rc_tk] == '010101' and sp_tk[j][nk_op_tk] == op:
                            kod_mat =''
                            if sp_tk[j][nk_mat_tk] == '':
                                err_arr.append(f'Не найден материал на {nom_tk + "_" + nn + " операция " + sp_tk[j][nk_op_tk]}')
                            else:
                                mat = sp_tk[j][nk_mat_tk].split('{')
                                for material in mat:
                                    if kod_mat != '':
                                        break
                                    nn_mat = material.split('$')[0]
                                    name_mat = material.split('$')[1]
                                    if nn_mat in nomenklatura:
                                        if nomenklatura[nn_mat]['П5'] == '1':
                                            kod_mat = str(nomenklatura[nn_mat]['П6'])
                                            tolsh = str(nomenklatura[nn_mat]['П1'])
                                            break
                                    else:
                                        err_arr.append(f'Не найден в номенклатуре материал {nn_mat} {name_mat} на'
                                                       f' {nom_tk + "_" + nn + "_" + naim + " операция " + sp_tk[j][nk_op_tk]}')
                            if kod_mat == '' and not sp_tk[j][nk_mat_tk] == '': #24.11.25
                                err_arr.append(f'Не найден матерал для резки (П5, П6, П1) на'
                                                f' {nom_tk + "_" + nn + "_" + naim +  " операция " + sp_tk[j][nk_op_tk]}')
                            kolvo_seg = 1 # 27.11.25
                            if j+1< len(sp_tk) and sp_tk[j+1][nk_ur_tk] == '2':
                                flag_naid = False
                                text = sp_tk[j+1][nk_textper]
                                for slovo in set_segment:
                                    if slovo.lower() in text.lower():
                                        flag_naid = True
                                        break
                                if flag_naid == True:
                                    kolvo_seg = text.split(' ')[-1]
                                    if F.is_numeric(kolvo_seg) == False or len(text.split(' ')) != 2:
                                        err_arr.append(f'Число сегментов не распознано на {nom_tk + "_" + nn} принят 1')
                                    else:
                                        kolvo_seg = int(kolvo_seg)

                            ima_dxf = sp_tk[j][15] #10.11.25
                            storage = CSTORE.FileStorage(CFG.Config.project.tk_storage_reestr)
                            new_name_dxf = f'{nom_mk}_{nn}.dxf'
                            abs_path_dxf = storage.get_dxf(ima_dxf, nn, put, new_name_dxf)
                            if abs_path_dxf is None:
                                print()
                                abs_path_dxf = storage.get_dxf(ima_dxf, nn, put, new_name_dxf)

                            if abs_path_dxf is None:
                                F.copy_bufer(ima_dxf)
                                err_arr.append(
                                    f'Отсутвует в бд файл {F.scfg("add_docs") + os.sep + ima_dxf} из текарты '
                                    f' {nom_tk + "_" + nn + ".pickle"}')
                            if err_arr == []:
                                rez_csv.append([abs_path_dxf,new_name_dxf , str(int(kolvo) * kolvo_seg), kod_mat,
                                           tolsh, nppy, nom_mk, prioritet, ima_tehnolog, gravir])
                                if nn != 'ТОП.ПР.008':
                                    set_mat_tolsh.add((tolsh,kod_mat))
                else:
                    err_arr.append(f'Не найдена техкарта {nom_tk + "_" + nn} в {F.scfg("mk_data") + os.sep + nom_mk}')
    if err_arr == []:
        сsv_sp = ['-'.join(rez_csv[0])]
        if '_ТОП.ПР.008.dxf' in rez_csv[1][1]:
            for set_ in set_mat_tolsh:
                tmp_test_obr = copy.deepcopy(rez_csv[1])
                tmp_test_obr[3] = set_[1]
                tmp_test_obr[4] = set_[0]
                сsv_sp.append(';'.join(tmp_test_obr))

            for i in range(2,len(rez_csv)):
                сsv_sp.append(';'.join(rez_csv[i]))
        else:
            for i in range(1,len(rez_csv)):
                сsv_sp.append(';'.join(rez_csv[i]))
        try:
            path = put + os.sep + nom_mk + '.csv'
            F.write_file_c(put + os.sep + nom_mk + '.csv',сsv_sp,separ='')
        except PermissionError as e:
            CQT.msgbox(f'Файл {path!r} открыт или используется другой программой')
            return


        otmetka = "_".join([F.user_name(),F.now() , put])
        custom_request_c = f'''UPDATE mk SET Статус_ЧПУ = ? WHERE Пномер == ?'''
         # spis = CSQ.list_from_db_sql_c(F.bdcfg('Naryad'), 'mk', False, True)
        perem = [otmetka,nom_mk]
        CSQ.custom_request_c(F.bdcfg('Naryad'), custom_request_c, '', True, perem)
        CQT.msgbox('Готово')
        F.open_dir_c(put)
    else:
        try:
            F.delete_dir_c(put) #25.11.25
        except PermissionError as e:
            CQT.msgbox(f'Файл {put!r} открыт или используется другой программой')
            return
        correct_width = lambda tbl: [tbl.setRowHeight(row, 46) for row in range(tbl.rowCount())] #type: QtWidgets.QTableWidget
        CQT.msgboxg_get_table_ok_inf(self, 'Ошибки при выгрузке dxf',dict_or_list=['Ошибки', *err_arr],
                                     func_oform_tbl=correct_width, show_filtr=False)
        # CQT.msgbox('\n'.join(err_arr))
        return False
    return True

def add_menu(self,*args):
    self.ui.action_style = QtWidgets.QMenu('Выбор темы', self.ui.menu)
    font = QtGui.QFont()
    font.setPointSize(16)
    self.ui.action_style.setFont(font)
    self.ui.action_dark = QtWidgets.QAction('Темная', self)
    self.ui.action_dark.triggered.connect(action_dark)
    self.ui.action_dark.setFont(font)
    self.ui.action_lite = QtWidgets.QAction('Светлая', self)
    self.ui.action_lite.triggered.connect(action_lite)
    self.ui.action_lite.setFont(font)
    self.ui.action_style.addAction(self.ui.action_dark)
    self.ui.action_style.addAction(self.ui.action_lite)
    self.ui.menu.addAction(self.ui.action_style.menuAction())


def load_dict_dse(db_dse,conn=''):
    poki = CFG.Config.place.poki
    custom_request_c = f'''SELECT Номенклатурный_номер,Наименование, Номер_техкарты, Код_ЕРП FROM dse WHERE poki = {poki}'''
    if conn == '':
        conn_dse, cur_dse = CSQ.connect_bd(db_dse)
    rez = CSQ.custom_request_c(db_dse, custom_request_c, conn=conn_dse, hat_c=True, rez_dict=True, cur = cur_dse)
    if conn == '':
        CSQ.close_bd(conn_dse, cur_dse)
    DICT_NN_NTK = F.deploy_dict_c(rez, 'Номенклатурный_номер')
    return DICT_NN_NTK

def load_column_widths(self,tbl):
    return CQT.load_column_widths(self, tbl,tmp_dir())


def on_section_resized(self,*args):
    CQT.on_section_resized(self,tmp_dir(),*args)


def get_shablon_vidov(DICT_PROFESSIONS, name_key = 'nick_name'):
    dict_vid_rab = {
        DICT_PROFESSIONS[_][name_key]: {'sort': DICT_PROFESSIONS[_]['sort']} for
        _ in DICT_PROFESSIONS.keys()}



    dict_vid_rab = dict(sorted(dict_vid_rab.items(), key=lambda item: item[1]['sort']))
    list_vid_rab = list(dict_vid_rab.keys())
    return list_vid_rab

def load_tabel_workforce(db_kplan,DICT_PROFESSIONS,DICT_VID_RABOT, name_key = 'nick_name'):
    rez_tabel_workforce = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM plan_tabel_workforce WHERE poki = {CFG.Config.place.poki} """,rez_dict=True)
    dict_rez = dict()
    list_vid_rab = get_shablon_vidov(DICT_PROFESSIONS,name_key )
    dict_vid_rab = {k: 0 for k in list_vid_rab}
    for item in rez_tabel_workforce:
        if item['month'] not in dict_rez:
            dict_rez[item['month']] = copy.deepcopy(dict_vid_rab)
        vid_rab_nick = DICT_VID_RABOT[item['vid_rabot']][name_key]
        if vid_rab_nick in dict_rez[item['month']]:
            dict_rez[item['month']][vid_rab_nick] += item['normo_smen']*480
    return dict_rez


def tmp_dir():
    ima_module = F.name_of_executable_file_c().split('.')[0]
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp'])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp']))
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module]))
    return os.sep.join([F.put_po_umolch() ,'mes_tmp' , ima_module])

def tmp_mes_dir():
    if F.existence_file_c(os.sep.join([F.put_po_umolch() ,'mes_tmp'])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch() ,'mes_tmp']))
    return os.sep.join([F.put_po_umolch() ,'mes_tmp'])

def load_theme(self):
    if F.existence_file_c(tmp_dir() + F.sep() + 'style.qss'):
        spis_korr = CQT.use_CSS_c(F.open_file_c(tmp_dir() + F.sep() + 'style.qss'))
        if spis_korr == '':
            return
        self.setStyleSheet("".join(spis_korr))

def action_dark(self):
    if F.existence_file_c("Config\\dark.qss"):
        F.copy_file_c("Config\\dark.qss",tmp_dir() + os.sep + 'style.qss')
        CQT.msgbox('Успешно, необходимо перезайти')

def action_lite(self):
    if F.existence_file_c("Config\\lite.qss"):
        F.copy_file_c("Config\\lite.qss", tmp_dir() + os.sep + 'style.qss')
        CQT.msgbox('Успешно, необходимо перезайти')


def accounting_work_rates_by_MK_c(self, spis_mk,nom_mk):#где используется?
    nom_kol_nn = F.num_col_by_name_in_hat_c(spis_mk,'Обозначение')
    nom_kol_naim = F.num_col_by_name_in_hat_c(spis_mk,'Наименование')
    nom_kol_kol_det = F.num_col_by_name_in_hat_c(spis_mk, 'Сумм.Количество')
    spis_mk2 = spis_mk[:]

    conn1, cur1 = CSQ.connect_bd(F.bdcfg('db_dse'))

    for i in range(1, len(spis_mk)):

        """nom_tk = CSQ.find_in_db_c(F.bdcfg('db_dse'), 'dse', {'Номенклатурный_номер': spis_mk[i][nom_kol_nn].strip(),
                                                           'Наименование': spis_mk[i][nom_kol_naim].strip()},
                                ['Номер_техкарты'],all=False, conn=conn1, cur=cur1 )"""
        nom_tk = CSQ.custom_request_c(F.bdcfg('db_dse'),f"""SELECT Номер_техкарты FROM dse WHERE 
        Номенклатурный_номер == '{spis_mk[i][nom_kol_nn].strip()}', Наименование == '{spis_mk[i][nom_kol_naim].strip()}'""",conn=conn1, cur=cur1,one=True,hat_c=True)
        if nom_tk == None or nom_tk == False or len(nom_tk) == 1:
            CQT.msgbox(f'по МК{nom_mk}, {spis_mk[i][nom_kol_nn].strip()} '
                     f'{spis_mk[i][nom_kol_naim].strip()} отсутсвует в БД, необходимо обратиться к технологам')
            CSQ.close_bd(conn1, cur1)
            return
        nom_tk= nom_tk[0]
        putf = F.scfg('mk_data') + os.sep + nom_mk + os.sep + nom_tk + '_' + spis_mk[i][nom_kol_nn] + '.pickle'
        if F.existence_file_c(putf):
            sp_tk = F.open_file_c(putf, False, "|", pickl=True)
            grup = grouping_TK_by_work_centres_c(self, sp_tk,spis_mk[i][nom_kol_kol_det])
            metka = nom_kol_kol_det+1
            for k in range(len(grup)):
                flag_rashod = False
                for j in range(metka,len(spis_mk[0]),4):
                    spis_mk[i][j] = ""
                    if spis_mk[0][j] == grup[k][0]:
                        metka = j +4
                        spis_mk[i][j] = 'Время: ' + str(grup[k][1]) + ' мин.' + '$' + 'Операции:' + '$' + str(grup[k][2])
                        flag_rashod = True
                        break
                if flag_rashod == False:
                    CQT.msgbox('Не совпадают маршутры')
                    CSQ.close_bd(conn1, cur1)
                    return
    CSQ.close_bd(conn1, cur1)



def level_c(strok):
    n = 0
    for i in range(0, len(strok)):
        if strok[i] == " ":
            n += 1
        else:
            break
    return int(n / 4)

def level_decor_c(strok:str,ur:int, koef = 4):
    return ' ' * ur * koef + strok.strip()

def formalize_MK_c(self,tabl_mk):
    shag = 15
    sp = CQT.list_from_wtabl_c(tabl_mk,"",True)
    nom_kol_kolich = F.num_col_by_name_in_hat_c(sp,"Количество")
    maxs = set()
    for i in range(1,len(sp)):
        maxs.add(level_c(sp[i][0]))
    maxc = max(maxs)
    for i in range(1,len(sp)):
        level_c_det = level_c(sp[i][0])
        for j in range(0, len(sp[i])):
            CQT.add_color_wtab_c(tabl_mk,i-1,j,0,0,shag*maxc-shag*level_c_det)
    for i in range(1, len(sp)):
        for j in range(11, len(sp[i]),4):
            CQT.add_color_wtab_c(tabl_mk, i - 1, j, 10, 10, 10)
            if sp[i][j] == '':
                for k in range(1,4):
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j+k, 10, 10, 10)
    tabl_mk.setColumnHidden(6,True)
    #komplekt
    for i in range(1, len(sp)):
        flag_gotova = True
        flag_brak = False
        for j in range(12, len(sp[i]), 4):
            if tabl_mk.item(i - 1,j).text() != '':
                if '(полный' in tabl_mk.item(i - 1,j).text():
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j, 0, 127, 0)
                else:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j, 37, 17, 0)
            if tabl_mk.item(i - 1, j - 1).text() != "" and 'олный' not in tabl_mk.item(i - 1, j + 1).text():
                flag_gotova = False

            if tabl_mk.item(i - 1, j + 1).text() != '':
                arr = tabl_mk.item(i - 1, j + 1).text().strip().split('\n')
                set_sost = set()
                for k in range(len(arr)):
                    arr2 = arr[k].split(' ')
                    if len(arr2) < 2:
                        set_sost.add(1)
                    else:
                        set_sost.add(arr2[1])
                if 'компл.' in set_sost:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j + 1, 0, 127, 0)  # зеленый
                elif len(set_sost) == 1 and 'Выдан' in set_sost:
                    pass
                elif len(set_sost) == 1 and 'Создан' in set_sost:
                    pass
                else:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j+1, 37, 17, 0)# оранж

            if tabl_mk.item(i - 1, j + 2).text() != '':
                arr = tabl_mk.item(i - 1, j + 2).text().strip().split('\n')
                set_sost = set()
                CQT.add_color_wtab_c(tabl_mk, i - 1, j + 2, 0, 127, 0)  # зеленый
                for k in range(len(arr)):
                    arr2 = arr[k].split(' ')
                    if len(arr2) == 1:
                        set_sost.add('Исправимый')
                    else:
                        set_sost.add(arr2[1])
                if 'Неисп-мый' in set_sost:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j + 2, 200, 10, 10)  # красный
                    CQT.add_color_wtab_c(tabl_mk, i - 1, nom_kol_kolich, 200, 10, 10)  # красный
                    flag_brak = True
                if 'Исправимый' in set_sost:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j+2, 37, 17, 0)# оранж
                    CQT.add_color_wtab_c(tabl_mk, i - 1, nom_kol_kolich, 37, 17, 0)  # оранж
                    flag_brak = True
                '''
                if len(set_sost) == 1 and 'Исправлен' in set_sost:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j + 2, 0, 127, 0)  # зеленый
                if len(set_sost) == 1 and 'Изгот.вновь' in set_sost:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j + 2, 0, 127, 0)  # зеленый
                if len(set_sost) == 2 and 'Изгот.вновь' in set_sost and 'Исправлен' in set_sost:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j + 2, 0, 127, 0)  # зеленый
                if 'Неисп-мый' in set_sost:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j + 2, 200, 10, 10)  # красный
                    CQT.add_color_wtab_c(tabl_mk, i - 1, nom_kol_kolich, 200, 10, 10)  # красный
                    flag_brak = True
                else:
                    CQT.add_color_wtab_c(tabl_mk, i - 1, j+2, 37, 17, 0)# оранж
                    CQT.add_color_wtab_c(tabl_mk, i - 1, nom_kol_kolich, 37, 17, 0)  # оранж
'''
        if flag_brak == False:
            if flag_gotova == True:
                CQT.add_color_wtab_c(tabl_mk, i - 1, nom_kol_kolich, 0, 127, 0)  # зеленый

def list_of_tasks_by_ID_oper_c(mk,id,spis_op,nar,sp_jur,max_kol_vo,poln_kompl):
    sp = []
    fakt_kol = 0
    flag_kol = True
    slov = {}
    kol_nom_oper = F.num_col_by_name_in_hat_c(nar,'N_операции')
    kol_nom_id = F.num_col_by_name_in_hat_c(nar, 'ID')
    kol_nom_chislo = F.num_col_by_name_in_hat_c(nar, 'Кол_во')
    kol_nom_zadanie_nar = F.num_col_by_name_in_hat_c(nar, 'Задание')
    kol_nom_status_nar = F.num_col_by_name_in_hat_c(nar, 'Стасус_наряда')
    kol_nom_ispr_act = F.num_col_by_name_in_hat_c(nar, 'Исправление_акт')
    for i in range(1,len(nar)):
        operac = nar[i][kol_nom_oper].strip()
        if str(nar[i][1]) == str(mk) and nar[i][kol_nom_id].strip() == str(id) and operac in spis_op:
            sost = 'Создан'
            if nar[i][17].strip() != '' or nar[i][18].strip() != '':
                sost = 'Выдан'
                #sp_jur = F.open_file_c(F.tcfg('BDzhurnal'),False,'|')
                fam = set()
                for j in range(len(sp_jur)):
                    if sp_jur[j][3] == nar[i][0]:
                        fam.add(sp_jur[j][4])
                fam = list(fam)
                if len(fam) != 0:
                    sost = 'Начат'
                    for j in range(len(sp_jur)):
                        if sp_jur[j][3] == nar[i][0] and sp_jur[j][8] == 'Завершен':
                            if nar[i][kol_nom_ispr_act] == "" and nar[i][kol_nom_status_nar] != 'Внеплана':
                                if operac in slov:
                                    slov[operac] += int(nar[i][kol_nom_chislo])
                                else:
                                    slov[operac] = int(nar[i][kol_nom_chislo])

                            fam.remove(sp_jur[j][4])
                            if len(fam) == 0:
                                sost = 'Завершен'
                                break
            sp.append(str(nar[i][0]) + ' ' + sost)
    for k in slov.keys():
        if slov[k] != max_kol_vo:
            flag_kol = False
    if len(slov) == 0:
        flag_kol = False
    if flag_kol == True and poln_kompl == True:
        sp.insert(0, 'Полный компл.')
    return sp


@CQT.onerror
def zapoln_tree_spiskom(self, spisok: list, list_user,tree, xml_head = None): # 12.11.25
    tree.clear()
    n = 0
    max_ur = 0
    for i in range(0, len(spisok)):
        if spisok[i]['level_c'] > max_ur:
            max_ur = spisok[i]['level_c']

    list_obj_lvls = ["" for _ in range(max_ur + 1)]
    nk_naim = list_user.index('Наименование')
    nk_tip = list_user.index('Тип')

    for i in range(0, len(spisok)):
        ur = spisok[i]['level_c']
        print(i)
        if ur == 0:
            list_obj_lvls[ur] = QtWidgets.QTreeWidgetItem(tree)
        else:
            list_obj_lvls[ur] = QtWidgets.QTreeWidgetItem(list_obj_lvls[ur - 1])
        root = list_obj_lvls[ur]

        for pole in range(0, len(list_user)):
            if list_user[pole] in spisok[i]['data'].keys():
                root.setText(pole, str(spisok[i]['data'][list_user[pole]]))
                # if list_user[pole] == 'Тип':
                #    if str(spisok[i]['data'][list_user[pole]]) in self.TIP_NEGRUZ_DSE:
                #        root.setTextColor(nk_naim, QtGui.QColor(222,111,111))

            else:
                if list_user[pole] == 'Уровень':
                    root.setText(pole, str(ur))
                else:
                    root.setText(pole, '')

        tree.addTopLevelItem(root)
        tree.expandItem(root)
        tree.setCurrentItem(root)
        n += 1
    available_types = XML_get_unavailable_xml_types(xml_head) # 12.11.25
    CQT.colors_into_tree_c(tree, available_types, nk_tip, 222, 111, 111, 255)


def grouping_TK_by_work_centres_c(self,tk,nn,ima):
    def get_norm_from_res(nn,ima,n_op):
        rez = 0
        for dse in self.res:
            if dse['Номенклатурный_номер'] == nn and dse['Наименование'] == ima:
                for oper in dse['Операции']:
                    if oper['Опер_номер'] == n_op:
                        return oper['Опер_Тшт']
        return  0

    spis = []
    flag = 0
    for itk in tk:
        if len(itk) == 21:
            if itk[20] == '0' and flag == 1:
                return spis
            if itk[20] == '0' and flag == 0:
                flag = 1
            if itk[20] == '1':
                rc = itk[4]
                n_op = itk[2]
                try:
                    vrem = get_norm_from_res(nn,ima,n_op) #F.valm(itk[6]) + int(kol_det_vseg) * F.valm(itk[7]) * self.cr_mk_xml_koef_norm_time
                except:
                    CQT.msgbox('Не корректные данные')
                    return
                vrem = round(vrem, 1)

                if len(spis) > 0:
                    if spis[-1][0] == rc:
                        spis[-1][1] = round(spis[-1][1] + vrem)
                        spis[-1][2] += ';' + n_op
                    else:
                        spis.append([rc, vrem, n_op])
                else:
                    spis.append([rc, vrem, n_op])
    return spis


def run_link_DOCs_c(nn_det,naim,db_dse, link=''):
    """adres = \
    CSQ.find_in_db_c(F.bdcfg('db_dse'), 'dse', {'Номенклатурный_номер': nn_det, 'Наименование': naim}, ['Путь_docs'])[0][
        0]"""
    if link == '':
        adres = CSQ.custom_request_c(db_dse, f"""SELECT Путь_docs FROM dse WHERE 
                Номенклатурный_номер == '{nn_det}' and Наименование == '{naim}'""",
                             one=True, hat_c=True)
        if adres == None or adres == False or len(adres) ==1:
            CQT.msgbox('Нет ссылки на ДСЕ в docs')
            return
        link = adres[-1][0]
    try:
        srv = link.split('/')[2]
        edit_key_winreg_hkey_current_user(r'SOFTWARE\Top Systems\T-FLEX DOCs 17\Rus\Connections','AutoConnect','REG_DWORD',0x00000001)
        edit_key_winreg_hkey_current_user(r'SOFTWARE\Top Systems\T-FLEX DOCs 17\Rus\Connections', 'LastServerAddress',
                                      'REG_SZ', srv)
    except:
        pass
    os.startfile(f"{link}")
    try:
        edit_key_winreg_hkey_current_user(r'SOFTWARE\Top Systems\T-FLEX DOCs 17\Rus\Connections', 'AutoConnect',
                                          'REG_DWORD', 0x00000000)
    except:
        pass
    return



def brak(text):
    if text == '':
        return False
    sp = text.split('\n')
    for i in range(len(sp)):
        if len(sp[i].split(' ')) > 1:
            sost = sp[i].split(' ')[1]
            if sost == 'Исправлен' or sost == 'Изгот.вновь':
                pass
            else:
                return True
        else:
            return True
    return False

def sost_vipolnenia(nom):
    if F.existence_file_c(F.scfg('mk_data') + os.sep + nom + '.txt') == False:
        CQT.msgbox('Не обнаружен файл ' + F.scfg('mk_data') + os.sep + nom + '.txt')
        return ""
    sp_det = F.open_file_c(F.scfg('mk_data') + os.sep + nom + '.txt', False, '|')
    nom_kol_summ = F.num_col_by_name_in_hat_c(sp_det,'Сумм.Количество')
    if nom_kol_summ == None:
        CQT.msgbox('Не найдена колонка Сумм.Количество')
        return
    summ = 0
    summ_got = 0
    for i in range(1,len(sp_det)):
        for j in range(nom_kol_summ+1,len(sp_det[i]),4):
            if sp_det[i][j] != '':
                summ += float(sp_det[i][j].split(' ')[1])
                if 'Полный компл.' in sp_det[i][j+2]:
                    if brak(sp_det[i][j+3]) == False:
                        summ_got += float(sp_det[i][j].split(' ')[1])
    return str(round(summ,1)), str(round(summ_got,1))

def name_RC_by_code_c(sp,kod):
    for i in range(len(sp)):
        if sp[i][0] == kod:
            return sp[i][1]
    return 'None'

def set_state_of_MK_c(nom_mk, status):#DELETE??????
    #rez = CSQ.update_bd_sql(F.bdcfg('Naryad'), 'mk',{'Прогресс':status},{'Пномер':int(nom_mk)})
    rez = CSQ.custom_request_c(F.bdcfg('Naryad'),f"""UPDATE mk SET Прогресс = {status} WHERE Пномер = {int(nom_mk)}""")
    if rez == False:
        CQT.msgbox('Запрос на изменение Прогресса не выполнен')


def get_path_to_proj_NPPY_c(NP, PU,year_py:int=None,projects_localnet_path=None):
    if projects_localnet_path == None or projects_localnet_path == '':
        projects_localnet_path = CFG.Config.place.projects_localnet_path

    Proekt = NP.strip()
    PU = PU.strip()
    year_py_str = ''
    if year_py:
        year_py_str = str(year_py) + F.sep()
    if f'{CFG.Config.place.doc_prefix}0' not in PU and PU != "":
        return F.sep().join((CFG.Config.place.prefix_projects_localnet_path, PU))
    return  F.sep().join((CFG.Config.place.prefix_projects_localnet_path,
                         projects_localnet_path + Proekt[:2],
                         Proekt, PU, str(year_py)
                         ))


def path_to_proj_NPPY_c(NP, PU,msg_gui=False,year_py:int=None,projects_localnet_path=None):
    if projects_localnet_path == None or projects_localnet_path == '':
        projects_localnet_path = CFG.Config.place.projects_localnet_path
    Proekt = NP.strip()
    PU = PU.strip()
    year_py_str = ''
    if year_py:
        year_py_str = str(year_py) + "\\"
    if f'{CFG.Config.place.doc_prefix}0' not in PU and PU != "":
        Put_k_pap =  F.sep().join([ CFG.Config.place.prefix_projects_localnet_path , PU ])
        if os.path.exists(Put_k_pap) == True:
            return Put_k_pap
    def trying_exist(projects_localnet,Proekt):
        def trying_exist_year(projects_localnet_year):
            Put_k_pap = F.sep().join([CFG.Config.place.prefix_projects_localnet_path , projects_localnet_year , Proekt ,PU , year_py_str])
            if os.path.exists(Put_k_pap) == True:
                return Put_k_pap
            Put_k_pap = F.sep().join([CFG.Config.place.prefix_projects_localnet_path ,  projects_localnet_year ,Proekt , PU ])
            if os.path.exists(Put_k_pap) == True:
                return Put_k_pap
            Put_k_pap =  F.sep().join([ CFG.Config.place.prefix_projects_localnet_path , PU ])
            if os.path.exists(Put_k_pap) == True:
                return Put_k_pap
            Put_k_pap =  F.sep().join([CFG.Config.place.prefix_projects_localnet_path , projects_localnet_year , Proekt ])
            if os.path.exists(Put_k_pap) == True:
                return Put_k_pap
            return
        projects_localnet_year = projects_localnet + Proekt[:2]
        Put_k_pap = trying_exist_year(projects_localnet_year)
        if Put_k_pap:
            return Put_k_pap

        return

    Put_k_pap = trying_exist(projects_localnet_path, Proekt)
    if Put_k_pap == None and projects_localnet_path != CFG.Config.place.projects_localnet_path:
        Put_k_pap = trying_exist(CFG.Config.place.projects_localnet_path)
    if Put_k_pap:
        return Put_k_pap
    print('Не найдена папка для проекта ' + Proekt + ' ' + PU)
    if msg_gui:
        CQT.msgbox('Не найдена папка для проекта ' + Proekt + ' ' + PU, 'Ясно', time_life=3)

def upload_task_c(self, r, k, table_det ):#DELTE?????
    tabl_mk = table_det
    if tabl_mk.item(r, k).text() == "":
        return
    #tabl_sp_mk = self.ui.tableWidget_vibor_mk
    spis_nar = []
    text = tabl_mk.item(r, k).text().strip().split('\n')
    for item in text:
        arr = item.split(' ')
        if F.is_numeric(arr[0]) == True:
            spis_nar.append(arr[0])
    spisok_vivod = []
    #stroki_Zhur = F.open_file_c(F.tcfg('BDzhurnal'), False, "|", False, False)
    #stroki_Zhur = CSQ.list_from_db_sql_c(F.bdcfg('BDzhurnal'), 'users',hat_c=True)
    stroki_Zhur = CSQ.custom_request_c(F.bdcfg('BDzhurnal'),"""SELECT * FROM users;""",hat_c=True)
    nom_kol_nom_nar = F.num_col_by_name_in_hat_c(stroki_Zhur,'Номер_наряда')
    nom_kol_nom_Дата = F.num_col_by_name_in_hat_c(stroki_Zhur, 'Дата')
    nom_kol_nom_ФИО = F.num_col_by_name_in_hat_c(stroki_Zhur, 'ФИО')
    nom_kol_nom_Статус = F.num_col_by_name_in_hat_c(stroki_Zhur, 'Статус')
    for narad in spis_nar:
        for i in range(len(stroki_Zhur)):
            if stroki_Zhur[i][nom_kol_nom_nar] == int(narad):
                spisok_vivod.append(stroki_Zhur[i][nom_kol_nom_Дата] + " "
                                    + stroki_Zhur[i][nom_kol_nom_ФИО] + " " + stroki_Zhur[i][nom_kol_nom_Статус])
    CQT.msgbox('\n'.join(spisok_vivod))
    return

def name_RC_by_number_c(SPIS_RC,rc:str):
    #SPIS_RC = F.open_file_c(F.tcfg('bd_rab_c'), separ='|')
    if rc == '':
        return
    if SPIS_RC == ['']:
        return
    SLOV_RC = {}
    for i in SPIS_RC:
        if i[2] == "":
            SLOV_RC[i[0]] = f'{i[1]}'
        else:
            SLOV_RC[i[0]] = f'{i[1]}({i[2]})'
    if rc not in SLOV_RC.keys():
        return
    return SLOV_RC[rc]

def code_of_oper_by_name_c(SPIS_OP,ima:str):
    #SPIS_OP = F.open_file_c(F.scfg('bd_rab_c') + F.sep() + 'kod_oper.txt', separ='|')
    rez = ''
    for i in range(len(SPIS_OP)):
        if SPIS_OP[i][1] == ima:
            rez = SPIS_OP[i][0]
            break
    return rez


def code_of_mashine_by_name_c(SPIS_OB, ima:str):
    #SPIS_OB = F.open_file_c(F.scfg('bd_rab_c') + F.sep() + 'bd_oborud.txt', separ='|')
    rez = ''
    for i in range(len(SPIS_OB)):
        if SPIS_OB[i][1] == ima:
            rez = SPIS_OB[i][0]
            break
    return rez

def ima_prof_by_code_c(SPIS_PROF, kod:str):
    #SPIS_PROF = F.open_file_c(F.scfg('bd_rab_c') + F.sep() + 'bd_prof.txt', separ='|')
    rez = ''
    for i in range(len(SPIS_PROF)):
        if SPIS_PROF[i][0] == str(kod):
            rez = SPIS_PROF[i][1]
            break
    return rez

def emploee_from_username(dict_empl:dict,username:str) -> str:
    '''fio from username'''
    first_letter_name, second_name = username.split('.')
    first_letter_name_rus = F.to_cirillic(first_letter_name)
    second_name_rus = F.to_cirillic(second_name)
    for user in dict_empl.keys():
        if len(user.split(' ')) != 3:
            continue
        name_user, second_name_user, third_name_user = user.split(' ')
        if name[0] == first_letter_name_rus and second_name_rus == second_name:
            return user
    return

def weight_MK_c(nom_mk:int):
    ceha = {}
    spis_sod_mk = F.open_file_c(F.scfg('mk_data') + os.sep + str(nom_mk) + '.txt', separ='|')
    n_k_sumkol = F.num_col_by_name_in_hat_c(spis_sod_mk,'Сумм.Количество')
    for i in range(1,len(spis_sod_mk)):
        for j in range(n_k_sumkol+1,len(spis_sod_mk[0]),4):
            if spis_sod_mk[i][j] != '':
                tme = spis_sod_mk[i][j].split()[1]
                if spis_sod_mk[0][j] not in ceha:
                    ceha[spis_sod_mk[0][j]] = [0,0]
                ceha[spis_sod_mk[0][j]][1] += F.valm(tme)
                if 'Полный компл.' not in spis_sod_mk[i][j + 2] or \
                        brak(spis_sod_mk[i][j + 3]) == True:
                    ceha[spis_sod_mk[0][j]][0] += F.valm(tme)
    return ceha

def prof_by_code_c(kod, sp_bd_prof):
    for i in range(len(sp_bd_prof)):
        if sp_bd_prof[i][0] == kod:
            return sp_bd_prof[i][1]

def code_by_prof_c(prof,sp_bd_prof):
    if sp_bd_prof == ['']:
        CQT.msgbox('Не найден sp_bd_prof')
        return
    for i in range(len(sp_bd_prof)):
        if sp_bd_prof[i][1] == prof:
            return sp_bd_prof[i][0]



def material_supply_c(self,nom_mk):
    tbl = self.ui.tbl_mat_komp
    CQT.clear_tbl(tbl)
    spis = [['РЦ',"Этап","Материал","Норма","Срок обеспечения"]]
    CQT.fill_wtabl_old_c(self,spis,tbl,separ='',isp_hat_c=True)


def name_by_empl_c(emp:str):
    emp = emp.replace(',',' ')
    return ' '.join(emp.split()[:3])

def job_post_by_empl_c(emp:str):
    emp = emp.replace(',',' ')
    return emp.split()[3]

def empol_by_name_c(self, ima:str):
    if type(self) is type([]):
        spis = self
    else:
        spis = self.SPIS_EMPLOEE
    for item in spis:
        if ima  == ' '.join(item[:3]):
            return ','.join(item[:4])

def check_actual_parol(fio):
    if fio == '':
        return True
    if F.existence_file_c(F.pcfg('Riba')) == False:
        CQT.msgbox('Не найден файл паролей')
        return
    spis = F.load_file_pickle(F.pcfg('Riba'))
    for i in range(len(spis)):
        if shifr(fio.strip()) in spis[i][0].strip():
            if len(spis[i]) == 2:
                return False
            try:
                if F.add_months(spis[i][2],1) < F.now(''):
                    return False
            except:
                return False
            return True
    return True

def confirm_private_parol_c(FIO,Pred_parol):
    parol = None
    if F.existence_file_c(F.pcfg('Riba')) == False:
        CQT.msgbox('Не найден файл паролей')
        return None
    spis = F.load_file_pickle(F.pcfg('Riba'))
    for i in range(len(spis)):
        log = spis[i][0]
        par = spis[i][1]
        if shifr(FIO.strip()) in log.strip():
            parol = par
            break
    if parol == None:
        return None
    if parol == shifr(Pred_parol):
        return True
    else:
        return False

def shifr(password):
    pass_hash= hashlib.md5(password.encode('utf-8')).hexdigest()
    return pass_hash


def calc_productivity_cabotki(data, db_users, db_naryad, db_act, spis_empolee):
    #test 25.08.2022 po pologeniy
    KOEF_SVERHNORMI = 1.5
    try:
        metka = ''
        metka = 'расчет дат'
        # print(F.now())
        nach = VIR.start_of_period_c(data)
        konec = VIR.end_of_period_c(data)
        metka = 'загрузка табеля'
        table_name = nach.split()[0].replace('-', '_')
        custom_request_c = F'''SELECT * FROM mtdz_{table_name}'''
        tabel = CSQ.custom_request_c(db_users, custom_request_c)
        if tabel == '':
            print('Не найден табель')
            raise ValueError('Err')
        metka = 'список работ за месяц'
        conn, cur = CSQ.connect_bd(db_naryad)
        list_of_completed_task_per_month_c = VIR.list_of_completed_task_per_month_c(db_naryad, nach, konec, conn)
        CSQ.close_bd(conn, cur)
        metka = 'список работников за месяц'
        nk_fio = F.num_col_by_name_in_hat_c(list_of_completed_task_per_month_c, 'ФИО')
        spis_rab_za_mes =  list(set(x[nk_fio] for x in list_of_completed_task_per_month_c[1:]))
        metka = 'расчет часов'
        itog = [['ФИО', "Должность", "Итог", 'Брак', 'Наряды', "Сумма_теор_часов", 'Вычет', "сумма_часов_по_табелю"]]
        for i in range(len(spis_rab_za_mes)):
            itog = VIR.add_emploee_into_list_c(list_of_completed_task_per_month_c, spis_rab_za_mes[i], itog, tabel, spis_empolee, KOEF_SVERHNORMI)
            if itog == None:
                raise ValueError('')
        metka = 'учет брака'
        list_of_defects_per_months_c = VIR.list_of_defects_per_months_new_c(db_act, nach, konec)
        metka = 'вычет табеля'
        nk_pnom = F.num_col_by_name_in_hat_c(list_of_defects_per_months_c, 'Пномер')
        nk_nomnar = F.num_col_by_name_in_hat_c(list_of_defects_per_months_c, 'Номер_наряда')
        nk_katbr = F.num_col_by_name_in_hat_c(list_of_defects_per_months_c, 'Категория_брака')
        nk_vichet_itog = F.num_col_by_name_in_hat_c(itog, 'Вычет')
        nk_itog_itog = F.num_col_by_name_in_hat_c(itog, 'Итог')
        nk_fio_itog = F.num_col_by_name_in_hat_c(itog, 'ФИО')
        conn, cur = CSQ.connect_bd(db_naryad)
        for i in range(1, len(list_of_defects_per_months_c)):
            itog = VIR.apply_defects_on_list_emploee_new_c(str(list_of_defects_per_months_c[i][nk_pnom]),
                                                       list_of_defects_per_months_c[i][nk_nomnar],
                                                       list_of_defects_per_months_c[i][nk_katbr], itog, conn)
        CSQ.close_bd(conn, cur)
        metka = 'фильтр'
        for i in range(1, len(itog)):
            if itog[i][nk_vichet_itog] != "":
                itog[i][nk_vichet_itog] = itog[i][nk_vichet_itog][:-1]
        metka = 'сортировка'
        itog.pop(0)
        itog.sort(key=lambda x: x[nk_itog_itog], reverse=True)
        itog.insert(0, ['fio', 'dol', 'prc', 'e_prc', 'sp_nar', 'summ_chas', 'sp_act', 'stavka_tab_chas'])
        metka = 'формировка сообщения'
        return itog, metka
    except:
        return '', metka

def check_and_fix_double_narayds(db_naryad,conn,cur):

    last_month = F.now("") - relativedelta(months=1)
    data_nach = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
    query = f"""
        SELECT Номер_наряда || " " || ФИО as ФИО, Статус, Пномер 
        FROM jurnal WHERE datetime(jurnal.Дата) > datetime("{data_nach}") ORDER BY datetime(Дата);"""
    list_for_check = CSQ.custom_request_c(db_naryad, query, conn=conn, cur=cur, rez_dict=True)
    list_for_del = []
    for i, line in enumerate(list_for_check):
        if line['Статус'] == "Начат":
            fio = line['ФИО']
            for j in range(i+1,len(list_for_check)):
                if list_for_check[j]['ФИО'] == fio:
                    if list_for_check[j]['Статус'] == "Начат":
                        list_for_del.append(list_for_check[j]['Пномер'])
                    else:
                        break
    if len(list_for_del):
        tuple_del = ",".join(tuple(str(_) for _ in list_for_del))
        CSQ.custom_request_c(db_naryad, f"""DELETE FROM jurnal WHERE Пномер in ({tuple_del})""")
        print()
        print(f'{F.now()} УДАЛЕНИЕ НАРЯДОВ {tuple_del} ЗАДВОЕНЫ НАЧАЛА')
        print()
    query = f"""
        SELECT Дата, Номер_наряда || " " || ФИО, Пномер, COUNT(*) AS CNT
        FROM (
            SELECT * FROM jurnal 
            WHERE jurnal.Статус == "Завершен" 
                and datetime(jurnal.Дата) > datetime("{data_nach}")
                ORDER BY datetime(jurnal.Дата) DESC) 
            GROUP BY Номер_наряда || " " || ФИО 
            HAVING COUNT(*) > 1 
            ORDER BY datetime(Дата) DESC"""
    list_for_check = CSQ.custom_request_c(db_naryad, query, conn=conn, cur=cur, rez_dict=True)
    for line in list_for_check:
        CSQ.custom_request_c(db_naryad,f"""UPDATE jurnal SET Статус = 'Приостановлен' WHERE Пномер = {line['Пномер']};""")


def check_and_fix_confirm_execute_dates_c(db_naryad,conn,cur):
    query = f"""SELECT * FROM jurnal WHERE jurnal.Номер_наряда in (
SELECT naryad.Пномер FROM naryad WHERE naryad.Подтвержд_вып = 1 and naryad.Подтвержд_вып_дата = "") and jurnal.Статус = "Завершен";"""
    list_for_check = CSQ.custom_request_c(db_naryad, query, rez_dict=True)
    set_nar = list({_['Номер_наряда'] for _ in list_for_check})

    for nnar in set_nar:
        max_date = '2000-10-24 14:16:32'

        for item in list_for_check:
            if item['Номер_наряда'] == nnar:
                if F.strtodate(item['Дата']) > F.strtodate(max_date):
                    max_date = item['Дата']
        CSQ.custom_request_c(db_naryad,f"""UPDATE naryad SET Подтвержд_вып_дата = "{max_date}" WHERE Пномер = {nnar}""")



def check_and_fix_broken_narayds(db_naryad,conn,cur):
    print(f'+++++++ контроль плохих нарядов')

    last_month = F.now("") - relativedelta(months=1)
    data_nach = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]

    def add_rec_task_c(db_naryad,conn,cur):
        #ищет в журнал сроки где начат и 0 и если далее есть пауза или завершен то ставит  сумму и дописывает в наряд если завершен
        print(f'Дозапись нарядов где по журналу завершено или пауза:')
        query = f"""
            SELECT Пномер, Штамп, Номер_наряда, ФИО, Подытог, Статус 
            FROM jurnal 
            WHERE Номер_наряда in (
                SELECT Номер_наряда 
                FROM jurnal 
                WHERE Подытог == 0 
                    AND Статус == "Начат" 
                    AND datetime(jurnal.Дата) > datetime("{data_nach}"))"""
        list_for_check = CSQ.custom_request_c(db_naryad,query,conn=conn,cur=cur,rez_dict=True)
        if list_for_check == False:
            return
        for i, item in enumerate(list_for_check):
            if item['Подытог'] == 0 and item['Статус'] == 'Начат':
                nnar = item['Номер_наряда']
                fio = item['ФИО']
                tsht1 = F.fromdateshtamp(item['Штамп'],'')

                fl_find = False
                if i == len(list_for_check)-1:
                    break
                for j in range(i+1, len(list_for_check)):
                    if list_for_check[j]['Номер_наряда'] == nnar and list_for_check[j]['ФИО'] == fio and list_for_check[j]['Статус'] != 'Начат':
                        # ==========precalc_time==========
                        date_diff = F.fromdateshtamp(list_for_check[j]['Штамп'],'') - tsht1
                        poditog = round(date_diff.total_seconds() / 60)
                        poditog = 1 if poditog < 1 else poditog
                        CSQ.custom_request_c(db_naryad,f'''UPDATE jurnal SET Подытог = {poditog} WHERE Пномер == {item['Пномер']}''',conn=conn,cur=cur)
                        print(f'Обновлен подытог {poditog} для {fio} Наряд№ {nnar}')
                        list_for_check[i]['Подытог'] = poditog
                        if list_for_check[j]['Статус'] == 'Завершен':
                            summ = 0
                            for item_3 in list_for_check:
                                if item_3['Номер_наряда'] == nnar and item_3['ФИО'] == fio:
                                    summ += item_3['Подытог']
                            CSQ.custom_request_c(db_naryad, f'''UPDATE naryad SET Фвремя = {summ} WHERE Пномер == {nnar} AND ФИО == "{fio}"''',
                                       conn=conn, cur=cur)
                            CSQ.custom_request_c(db_naryad, f'''UPDATE naryad SET Фвремя2 = {summ} WHERE Пномер == {nnar} AND ФИО2 == "{fio}"''',
                                       conn=conn, cur=cur)
                            print(f'    Обновлен наряд {nnar} для {fio} под завершение суммой {summ}')
                        break
        print(f'====================')
    def fix_not_matched_pauz_and_ends(db_naryad, conn, cur):
        print(f'Правка начал на 0 не завершенных и не пауз:')
        query = f"""SELECT Пномер, Штамп, Номер_наряда, ФИО, Подытог, Статус FROM jurnal WHERE 
        Номер_наряда not in (SELECT DISTINCT Номер_наряда FROM jurnal WHERE Статус == "Завершен" and datetime(jurnal.Дата) >= datetime("{data_nach}")) and datetime(Дата) >= datetime("{data_nach}")"""
        list_for_check = CSQ.custom_request_c(db_naryad, query, conn=conn, cur=cur, rez_dict=True)
        for i, item in enumerate(list_for_check):
            if item['Подытог'] != 0 and item['Статус'] == 'Начат':
                fl = False
                for j in range(i, len(list_for_check)):
                    if item['ФИО'] == list_for_check[j]['ФИО'] and item['Номер_наряда'] == list_for_check[j][
                        'Номер_наряда'] and list_for_check[j]['Статус'] != 'Начат':
                        fl = True
                if fl == False:
                    fact = ''
                    query = f"""SELECT ФИО, Фвремя, ФИО2, Фвремя2 FROM naryad WHERE Пномер == {item['Номер_наряда']}"""
                    fact_query = CSQ.custom_request_c(db_naryad, query, conn=conn, cur=cur, rez_dict=True,one=True)
                    if fact_query['ФИО'] == item['ФИО']:
                        fact = fact_query['Фвремя']
                    if fact_query['ФИО2'] == item['ФИО']:
                        fact = fact_query['Фвремя2']
                    if fact != '':
                        query = f"""SELECT SUM(Подытог) FROM jurnal WHERE Номер_наряда == {item['Номер_наряда']} and ФИО == '{item['ФИО']}';"""
                        rez = CSQ.custom_request_c(db_naryad, query, conn=conn, cur=cur, rez_dict=True,one=True)
                        summa = rez['SUM(Подытог)']
                        if summa != fact:
                            CSQ.custom_request_c(db_naryad,
                                       f'''UPDATE naryad SET Фвремя = {summa} WHERE Пномер == {item['Номер_наряда']} AND ФИО == "{item['ФИО']}"''',
                                       conn=conn, cur=cur)
                            CSQ.custom_request_c(db_naryad,
                                       f'''UPDATE naryad SET Фвремя2 = {summa} WHERE Пномер == {item['Номер_наряда']} AND ФИО2 == "{item['ФИО']}"''',
                                       conn=conn, cur=cur)
                            print(
                                f"      Обновлена сумма {summa} для {item['ФИО']} Наряд№ {item['Номер_наряда']}")
                        status = 'Завершен'
                    else:
                        status = 'Приостановлен'
                    date = F.fromdateshtamp(item['Штамп'],'')
                    date_end = F.datetostr(F.date_add_time(date,'',"",minutes= item['Подытог']))
                    shtamp = F.shtamp_from_date(date_end)
                    stroka = [date_end, shtamp, item['Номер_наряда'], item['ФИО'], 0,
                                  'Завершен', 'Исправлено автоматически', '']
                            # CSQ.add_line_into_db_sql_c(self.db_naryd, 'jurnal', [stroka],conn=conn)
                    CSQ.custom_request_c(db_naryad, f"INSERT INTO jurnal "
                                                      f"(Дата, Штамп, Номер_наряда,ФИО,Подытог,Статус,Примечание,Ном_заверш)"
                                                      f" VALUES  (?,?,?,?,?,?,?,?)", list_of_lists_c=[stroka],
                                       conn=conn, cur=cur)
                    print(f"   для {item['ФИО']} Наряд№ {item['Номер_наряда']} проставлено {status}")

        print(f'====================')
    def fix_broken_nar(db_naryad, conn, cur, fio_, time_):
        # ищет в нарядах те где фио не пусто а время факт пусто, если в журнале есть завершенные то суммирует подытоги и ставит в наряд
        print(f'Простановка времени в наряды в завершенных по журналу:')
        query = f"""SELECT Пномер, {fio_} FROM naryad WHERE {fio_} != '' and {time_} = '' AND Пномер in
                 (SELECT Номер_наряда FROM jurnal WHERE datetime(jurnal.Дата) > datetime("{data_nach}"))"""
        list_nar1 = CSQ.custom_request_c(db_naryad, query, conn=conn, cur=cur, rez_dict=True)
        list_nar_clear = []
        for i in range(len(list_nar1)):
            list_nar_clear.append(list_nar1[i]['Пномер'])
        list_nar_clear = ', '.join(str(nar) for nar in list_nar_clear)
        list_jurnal = CSQ.custom_request_c(db_naryad, f"""SELECT Номер_наряда, ФИО, Подытог, Статус from jurnal 
            WHERE Номер_наряда in ({list_nar_clear})  and datetime(jurnal.Дата) > datetime("{data_nach}") ORDER BY Дата ASC;""", conn=conn, cur=cur, rez_dict=True)
        for i in range(len(list_nar1)):
            fio = list_nar1[i][f'{fio_}']
            nnar = list_nar1[i]['Пномер']
            summ_pditog = 0
            for j in range(len(list_jurnal)):
                if list_jurnal[j]['Номер_наряда'] == nnar and list_jurnal[j]['ФИО'] == fio and list_jurnal[j][
                    'Статус'] == 'Завершен':
                    for k in range(j - 1, -1, -1):
                        if list_jurnal[k]['Статус'] == 'Начат' and list_jurnal[k]['Номер_наряда'] == nnar and \
                                list_jurnal[k]['ФИО'] == fio:
                            summ_pditog += list_jurnal[k]['Подытог']
            if summ_pditog > 0:
                CSQ.custom_request_c(db_naryad,
                           f"""UPDATE naryad SET {time_} = {summ_pditog} WHERE Пномер = {nnar} AND  {fio_} = '{fio}'""",
                           conn=conn, cur=cur)
        print(f'====================')
    add_rec_task_c(db_naryad, conn, cur)
    fix_broken_nar(db_naryad, conn,cur,'ФИО', 'Фвремя')
    fix_broken_nar(db_naryad,conn, cur, 'ФИО2', 'Фвремя2')
    #fix_not_matched_pauz_and_ends(db_naryad,conn,cur)

    print(f'===========================')




def calc_and_fill_weight_by_xml_and_res(self,db_resxml,bd_naryad,bd_mat, nom_mk,kol_vo_izd,  DICT_FILTR='',DICT_MAT=''):

    def calc_and_fill_weight_by_xml(self,db_resxml,nom_mk,kol_vo_izd,bd_naryad):
        ves_xml = 0
        query = f'''SELECT data, Head FROM xml
                                           WHERE Номер_мк == {int(nom_mk)}
                                                       '''
        rez_xml = CSQ.custom_request_c(db_resxml, query)
        xml = rez_xml[-1][0]
        xml_head = rez_xml[-1][1]
        if xml == '':
            if not CQT.msgboxgYN(f'{nom_mk} нет ХМЛ, Была ли создана вручную?'):
                return False
            ves_list = CSQ.custom_request_c(self.bd_naryad,f"""SELECT Пномер,Вес FROM mk WHERE Пномер = {nom_mk}""",rez_dict=True)
            CSQ.custom_request_c(bd_naryad, f"""UPDATE mk SET xml = {round(ves_list[0]['Вес'], 2)} WHERE Пномер = {nom_mk}""")
            return True
        else:
            res_new = podgotovka_xml(self, XML.spisok_iz_xml(str_f=xml))
            for item_xml in res_new:
                mat = item_xml['data']['Масса/М1,М2,М3'].split('/')
                if 'Тип' in item_xml['data']:
                    if mat[1] != '' and item_xml['data']['Тип'] == 'Деталь':
                        ves_xml += F.valm(mat[0]) * F.valm(item_xml['data']['Количество на изделие']) * kol_vo_izd
                else:
                    pass
                    if mat[1] != '' and item_xml['data']['Покупное изделие'] != '1':
                        ves_xml += F.valm(mat[0]) * F.valm(
                            item_xml['data']['Количество на изделие']) * kol_vo_izd
            CSQ.custom_request_c(bd_naryad, f"""UPDATE mk SET xml = {round(ves_xml, 2)} WHERE Пномер = {nom_mk}""")
            return True
            #list_tmp = [[_['ID'],_['data']['Тип'],_['data']['Наименование'], "         Вес: " + str(F.valm(_['data']['Масса'])*F.valm(_['data']['Количество на изделие'])*kol_vo_izd)] for _ in res_new if _['data']['Тип'] not in  ('Сборочная единица','Деталь')]
            #sum([_[3] for _ in list_tmp])

    def calc_and_fill_weight_by_res(self,db_resxml, nom_mk, DICT_FILTR, list_hz_mat, DICT_MAT):
        ves_res = 0
        ves_res_list = 0
        LIST_ED_IZM_MAT = ['Килограмм', 'кг']
        # month = F.datetostr(F.strtodate(item['Дата_завершения']),"%Y-%m")

        res = CSQ.custom_request_c(db_resxml, f'''SELECT data FROM res WHERE Номер_мк == {nom_mk};''', hat_c=False,
                                   one=True)
        if res == False:
            CQT.msgbox(f'ОШибка')
            return
        try:
            res = F.from_binary_pickle(res[-1][0])
            for dse in res:
                kol = dse['Количество']
                for oper in dse['Операции']:
                    for mat in oper['Материалы']:
                        if mat['Мат_ед_изм'] not in LIST_ED_IZM_MAT and mat['Мат_код'] not in DICT_FILTR:
                            list_hz_mat.append(f"{F.valm(mat['Мат_норма'])} {mat['Мат_ед_изм']} "
                                               f"{mat['Мат_наименование']} {mat['Мат_код']}     "
                                               f"опер: {oper['Опер_наименование']}     "
                                               f"дет: {dse['Наименование']} {dse['Номенклатурный_номер']}")

                        if mat['Мат_ед_изм'] in LIST_ED_IZM_MAT:
                            ves_res += F.valm(mat['Мат_норма'])
                            # print(f"{F.valm(mat['Мат_норма'])} опер {oper['Опер_наименование']} дет {dse['Наименование']}")
                            if mat['Мат_код'] in DICT_MAT and DICT_MAT[mat['Мат_код']]['П5'] == '1':
                                if DICT_MAT[mat['Мат_код']]['П6'] != '':
                                    ves_res_list += F.valm(mat['Мат_норма'])
            CSQ.custom_request_c(self.bd_naryad,
                                 f"""UPDATE zagot SET Вес_по_рес = {round(ves_res_list, 2)} WHERE Ном_МК = {nom_mk}""")
            # CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Ресурсная = "" WHERE Пномер = {nom_mk}""")
            CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Вес = {round(ves_res, 2)} WHERE Пномер = {nom_mk}""")
        except:
            print(f'Некорректные данные рес {nom_mk}')
        return list_hz_mat



    try:
        if DICT_FILTR == "":
            DICT_FILTR = F.deploy_dict_c(CSQ.custom_request_c(bd_mat, f"""SELECT * FROM complex_filtr""", rez_dict=True), 'kod')
        if DICT_MAT == "":
            DICT_MAT = F.deploy_dict_c(CSQ.custom_request_c(bd_mat,f"""SELECT * FROM nomen""",rez_dict=True),'Код')
        list_hz_mat = []
        if not calc_and_fill_weight_by_xml(self,db_resxml,nom_mk,kol_vo_izd,bd_naryad):
            pass
        list_hz_mat = calc_and_fill_weight_by_res(self,db_resxml, nom_mk, DICT_FILTR, list_hz_mat, DICT_MAT)
    except:
        return False
    return True

def calc_productivity_c(data,db_users,db_naryad,db_act,db_kplan,DICT_EMPLOEE,DICT_PRICE_BRAK,konec=None,
                        CALC_BASE_ONLY_PREM = True,additional_fix = True, podrazdelenie = None, organization = None):

    def get_dict_masters(spis_rc:list,podrazdelenie):
        DICT_MASTERS = dict()
        LIST_EXCLUDE = ('','-','+')
        for item in spis_rc:
            if 'мастер' in item['Прозвище'].lower():
                list_sm = item['Примечание'].split("$")
                count_sm= len(list_sm)
                if count_sm >= 1 and item['ФИО_1см'] != '' and item['ФИО_1см'] in DICT_EMPLOEE and DICT_EMPLOEE[item['ФИО_1см']]['Подразделение'] == podrazdelenie:
                    if item['ФИО_1см'] not in LIST_EXCLUDE:
                        if item['ФИО_1см'] not in DICT_MASTERS:
                            DICT_MASTERS[item['ФИО_1см']] = {'Смены': [list_sm[0]],
                                                         'Подразделение':
                                                             DICT_EMPLOEE[item['ФИО_1см']]['Подразделение'],
                                                             'Вычет':0,'Число_браков':0,'Выработка_смены':0,'Число_сотрудников':0,'Вес':0,'Ставка_таб':0}
                        else:
                            DICT_MASTERS[item['ФИО_1см']]['Смены'].append(list_sm[0])
                if count_sm >= 2 and item['ФИО_2см'] != '' and item['ФИО_2см'] in DICT_EMPLOEE and DICT_EMPLOEE[item['ФИО_2см']]['Подразделение'] == podrazdelenie:
                    if item['ФИО_2см'] not in LIST_EXCLUDE:
                        if item['ФИО_2см'] not in DICT_MASTERS:
                            DICT_MASTERS[item['ФИО_2см']] = {'Смены': [list_sm[1]],
                                                     'Подразделение': DICT_EMPLOEE[item['ФИО_2см']]['Подразделение'],
                                                             'Вычет':0,'Число_браков':0,'Выработка_смены':0,'Число_сотрудников':0,'Вес':0,'Ставка_таб':0}
                        else:
                            DICT_MASTERS[item['ФИО_2см']]['Смены'].append(list_sm[1])
                if count_sm >= 3 and item['ФИО_3см'] != '' and item['ФИО_3см'] in DICT_EMPLOEE and DICT_EMPLOEE[item['ФИО_3см']]['Подразделение'] == podrazdelenie:
                    if item['ФИО_3см'] not in LIST_EXCLUDE:
                        if item['ФИО_3см'] not in DICT_MASTERS:
                            DICT_MASTERS[item['ФИО_3см']] = {'Смены': [list_sm[2]],
                                                     'Подразделение': DICT_EMPLOEE[item['ФИО_3см']]['Подразделение'],
                                                             'Вычет':0,'Число_браков':0,'Выработка_смены':0,'Число_сотрудников':0,'Вес':0,'Ставка_таб':0}
                        else:
                            DICT_MASTERS[item['ФИО_3см']]['Смены'].append(list_sm[2])
        return DICT_MASTERS

    double_pay_holydays = True

    metka = 'расчет дат'
    nach = VIR.start_of_period_c(data)
    if konec == None:
        konec = VIR.end_of_period_c(data)
    metka = 'загрузка табеля'
    table_name = nach.split()[0].replace('-', '_')
    custom_request_c = F'''SELECT * FROM mtdz_{table_name}'''
    tabel = CSQ.custom_request_c(db_users, custom_request_c)
    if not tabel:
        print('Не найден табель ')
        raise ValueError('Err')
    metka = 'список работ за месяц'
    conn, cur = CSQ.connect_bd(db_naryad)
    #check_and_fix_confirm_execute_dates_c(db_naryad,conn,cur)
    if additional_fix:
        check_and_fix_double_narayds(db_naryad,conn,cur)
        check_and_fix_broken_narayds(db_naryad,conn,cur)



    spis_jur_full,dict_per_month_all_state_from_jur = VIR.list_per_month_new_c(db_naryad, nach, konec,db_kplan,db_users,podrazdelenie,organization,tabel_m=tabel)

    CSQ.close_bd(conn, cur)#[_ for _ in spis_jur_full if 'Гримбер' in _[1]]
    #print('=====')
    metka = 'список работников за месяц'
    spis_rab_za_mes = list({_['ФИО'] for _ in spis_jur_full})
    spis_rab_za_mes = sorted(spis_rab_za_mes)

    list_of_defects_per_months_c = report_ci.get_jur_brak(db_naryad, nach, konec)

    spis_rc = DICT_RC_TBL(db_users)
    DICT_MASTERS = get_dict_masters(spis_rc,podrazdelenie)


    metka = 'расчет часов'
    itog = []
    for i in range(len(spis_rab_za_mes)):
        if spis_rab_za_mes[i] in DICT_MASTERS:
            continue
        itog = VIR.add_emploee_into_list_new_c(spis_rab_za_mes[i], itog, tabel, DICT_EMPLOEE,
                                               spis_jur_full,double_pay_holydays,DICT_MASTERS,CALC_BASE_ONLY_PREM,dict_per_month_all_state_from_jur)
        if itog == None:
            raise ValueError('')
    metka = 'учет брака'
       # VIR.list_of_defects_per_months_new_c(db_act, nach, konec)

    metka = 'вычет табеля'


    for i, item in enumerate(itog):#[_ for _ in itog if 'Гримбер' in _['ФИО']]
        #print(itog[i])
        fio = item["ФИО"]
        smena = DICT_EMPLOEE[fio]['Режим']
        podrazd = DICT_EMPLOEE[fio]['Подразделение']

        dict_vichet = report_ci.get_summ_brak_fio(DICT_PRICE_BRAK,fio,list_of_defects_per_months_c)
        if dict_vichet['Сумма'] > 0:
            #print(fio + " " + smena + ' ' + podrazd)
            #print(fio)
            #print(pprint.pformat(dict_vichet))
            for master in DICT_MASTERS.keys():
                if DICT_MASTERS[master]['Подразделение'] == podrazd:
                    if smena in DICT_MASTERS[master]['Смены']:
                        #vichet =( dict_vichet['Неиспр_число'] * 2 + dict_vichet['Испр_число'] * 0.1 )
                        vichet = dict_vichet['Сумма']
                        DICT_MASTERS[master]['Вычет'] += vichet
                        DICT_MASTERS[master]['Число_браков'] += 1
                        if DICT_MASTERS[master]['Вычет'] >100:
                            DICT_MASTERS[master]['Вычет'] = 100

        itog[i]['Брак'] = str(0-round(dict_vichet['Сумма'],1))
        proc_prem_with_brak = itog[i]["Итог"] - dict_vichet['Сумма']
        #print(f'Премия {fio} с вычетом {proc_prem_with_brak} (было {itog[i][nk_itog_itog]}) ')
        #if proc_prem_with_brak < 100:
        #    itog[i]["Итог"] = 100
        #else:
        #    itog[i]["Итог"] = round(proc_prem_with_brak,1)
        itog[i]["Итог"] = round(proc_prem_with_brak, 1)
    for master in DICT_MASTERS.keys():
        DICT_MASTERS[master]['Вычет']=DICT_MASTERS[master]['Вычет']/(DICT_MASTERS[master]['Число_браков'] +1)
    #pprint.pprint(DICT_MASTERS)

    metka = 'сортировка'

    itog.sort(key=lambda x: x["Итог"], reverse=True)
    #itog.insert(0, ['fio', 'dol', 'prc', 'e_prc', 'sp_nar', 'summ_chas','summ_chas_wo_koef', 'sp_act', 'stavka_tab_chas','ves','tek_prc'])
    for master in DICT_MASTERS.keys():
        prc = 0
        if DICT_MASTERS[master]['Число_сотрудников'] > 0:
            prc = round(DICT_MASTERS[master]['Выработка_смены']/DICT_MASTERS[master]['Число_сотрудников'])
            tab = round(DICT_MASTERS[master]['Ставка_таб']/DICT_MASTERS[master]['Число_сотрудников'])
        itog.insert(1, {
            "ФИО": master,
            "Должность": 'Мастер',
            "Итог": prc - DICT_MASTERS[master]['Вычет'],
            'Брак': -DICT_MASTERS[master]['Вычет'],
            'Наряды': '',
            "Сумма_теор_часов_с_коэфф": 0,
            "Сумма_теор_часов_без_коэфф": 0,
            'Режим': ';'.join(DICT_MASTERS[master]['Смены']),
            'Норма времени(Астр)':0,
            "сумма_часов_по_табелю": 0,
            "кг.": DICT_MASTERS[master]['Вес'],
            "текущий_процент": prc - DICT_MASTERS[master]['Вычет'],
            'Подытог_по_нормам':0,
            'Сет_нарядов': {}
        })
    metka = 'формировка сообщения'
    return itog, metka, DICT_MASTERS


def btn_oyp_add_project(self, stroka=''):
        if stroka =='':
            spis = CQT.list_from_wtabl_c(self.ui.tbl_podr_tkp_add, '')
        else:
            spis = stroka
        if CSQ.add_line_into_db_sql_c(self.BD, 'project', spis, s_pervoi=False):
            CSQ.add_line_into_db_sql_c(self.BD, 'ogk', prepare_empty_line_c(self, 'ogk'),True)
            CSQ.add_line_into_db_sql_c(self.BD, 'ogt', prepare_empty_line_c(self, 'ogt'), True)
            CSQ.add_line_into_db_sql_c(self.BD, 'pdo', prepare_empty_line_c(self, 'pdo'), True)
            CSQ.add_line_into_db_sql_c(self.BD, 'proizv', prepare_empty_line_c(self, 'proizv'), True)
            CSQ.add_line_into_db_sql_c(self.BD, 'sklad', prepare_empty_line_c(self, 'sklad'), True)
            CSQ.add_line_into_db_sql_c(self.BD, 'snab', prepare_empty_line_c(self, 'snab'), True)
            CQT.msgbox('Успешно')
        else:
            CQT.msgbox('Ошибка')

def prepare_empty_line_c(self,table):
    ID = CSQ.last_row_db_c(self.BD, 'project', 'ID', ['ID'])[0]
    spis_ogk = CSQ.list_of_columns_c(self.BD, table)
    for i in range(len(spis_ogk)):
        if spis_ogk[i] == 'Поз':
            spis_ogk[i] = ID
        else:
            spis_ogk[i] = ''
    return [spis_ogk]

def user_access(db,rule:str,fio:str, msg = True, rez = ''):
    if rez == '':
        rez = CSQ.custom_request_c(db,f'''SELECT * FROM permissions WHERE action == "{rule}";''',rez_dict=True)
    if rez == [] or rez == False:
        CQT.msgbox(f'Не найдено правило {rule}')
        return False
    try:
        rez = rez[0]
        if rez['users'] == None:
            if msg:
                CQT.msgbox('Нет доступа')
            return False
        if rez['value'] == 1:
            if fio.lower() in rez['users'].lower():
                return True
            else:
                if msg:
                    CQT.msgbox('Нет доступа')
                return False
        else:
            if fio.lower() in rez['users'].lower():
                if msg:
                    CQT.msgbox('Нет доступа')
                return False
            else:
                return True
    except:
        print('ошибка user_access')
        return False

def extra_time_unworked_between_task_c(self,fio,data_nach,data_kon):
    if F.strtodate('2023-02-01 00:00:00') < F.strtodate(data_kon):
        return 0
    conn, cur = CSQ.connect_bd(self.bd_users)
    fiod = CSQ.custom_request_c(self.bd_users,f"""SELECT ФИО || " " || Должность FROM employee WHERE ФИО == "{fio}" """,conn=conn,cur=cur, hat_c=False,one=True)[0][0]
    dney = time_by_repo_card_c(fiod,data_nach)/60/8
    custom_request_c = f"""SELECT employee.ФИО, rab_mesta.Нераб_мин1, rab_mesta.Между_нар_мин1 FROM rab_mesta INNER JOIN 
        employee ON employee.Пномер == rab_mesta.ФИО_1 WHERE employee.ФИО == "{fio}" """
    rez = CSQ.custom_request_c(self.bd_users,custom_request_c,conn=conn,cur=cur,hat_c=False,one=True)
    if rez == []:
        custom_request_c = f"""SELECT employee.ФИО, rab_mesta.Нераб_мин1, rab_mesta.Между_нар_мин1 FROM rab_mesta INNER JOIN 
        employee ON employee.Пномер == rab_mesta.ФИО_1 WHERE employee.ФИО == "{fio}" """
        rez = CSQ.custom_request_c(self.bd_users, custom_request_c, conn=conn,cur=cur, hat_c=False, one=True)
        if rez == []:
            custom_request_c = f"""SELECT employee.ФИО, rab_mesta.Нераб_мин1, rab_mesta.Между_нар_мин1 FROM rab_mesta INNER JOIN 
               employee ON employee.Пномер == rab_mesta.ФИО_1 WHERE employee.ФИО == "{fio}" """
            rez = CSQ.custom_request_c(self.bd_users, custom_request_c, conn=conn,cur=cur, hat_c=False, one=True)
    CSQ.close_bd(conn, cur)
    if rez == []:
        return 0
    else:
        conn, cur = CSQ.connect_bd(self.bd_naryad)
        custom_request_c = f"""SELECT DISTINCT Номер_наряда
         FROM jurnal WHERE Статус == "Завершен" and ФИО == "{fio}"
    and datetime(Дата) > datetime("{data_nach}") and datetime(Дата) < datetime("{data_kon}") """
        rez2 = CSQ.custom_request_c(self.bd_naryad,custom_request_c,conn=conn,cur=cur,hat_c=False)
        chislo_naryadov = len(rez2)

        CSQ.close_bd(conn, cur)
        if rez[0][1]-60 <= 0:
            min_per_day = 0
        else:
            min_per_day = (rez[0][1]-60) * dney
        return  min_per_day + rez[0][2]*chislo_naryadov

def time_by_repo_card_c(fiod,data):
    name_table = F.datetostr(F.strtodate(data),'mtdz_%Y_%m_01')
    custom_request_c = f'''SELECT * FROM {name_table} WHERE ФИО == "{fiod}" '''
    rez = CSQ.custom_request_c(F.bdcfg("BD_users"),custom_request_c)
    if len(rez) == 1:
        CQT.msgbox(f'{fiod} не найден в {name_table} нужно проверить рабочие центра в Мкарт')
        return None
    nk_prim = F.num_col_by_name_in_hat_c(rez,'Примечание')
    summ = 0
    for j in range(nk_prim+1,len(rez[0])):
        if isinstance(rez[-1][j], int) or isinstance(rez[-1][j],float):
            summ += rez[-1][j]
        else:
            CQT.msgbox(f'Ошибка в БД {name_table} у {fiod} день {rez[0][j]} {rez[-1][j]}')
            return 0
    return summ*60

def time_by_repo_card(fio:str,data_tabel:list):
    rez = data_tabel
    fl = False
    summ = 0
    for row in data_tabel:
        if row['ФИО'].startswith(fio):
            fl = True
            for k , v in row.items():
                if F.is_date(k,"d_%Y_%m_%d"):
                    if isinstance(v, int) or isinstance(v,float):
                        summ += v
    if not  fl:
        CQT.msgbox(f'{fio} не найден в data_tabel нужно проверить рабочие центра в Мкарт')
        return None
    return summ*60


def VID_RABOT_PO_EMPL(bd_users):
    first_tbl = CSQ.custom_request_c(bd_users, f"""SELECT employee.ФИО, employee.Должность, 
    employee.Подразделение,employee.Статус, 
    vid_rab_po_dolg.Вид_работ, vid_rab_po_dolg.Руб_мин, professions.этап , professions.этап as Этап FROM employee INNER JOIN 
    professions ON professions.имя == employee.Должность,
    vid_rab_po_dolg on vid_rab_po_dolg.Вид_работ == professions.вид_работ 
    order by employee.Статус DESC;""", hat_c=False, rez_dict=True)

    VID_RABOT_PO_EMPL = F.deploy_dict_c(first_tbl, 'ФИО')

    return VID_RABOT_PO_EMPL


def ETAP_BY_FIO(bd_users, bd_naryad):
    first_tbl = CSQ.custom_request_c(bd_users, f"""SELECT employee.ФИО, employee.Должность, employee.Компания, 
        employee.Подразделение, employee.Статус, 
        etaps.name as этап, etaps.ДляЕРП 
         
         FROM employee 
        LEFT JOIN  dolgn_etap ON dolgn_etap.Должность = employee.Должность AND dolgn_etap.Подразделение = employee.Подразделение 
        LEFT JOIN etaps ON etaps.name = dolgn_etap.этап 
        WHERE employee.Подразделение != '' and employee.Подразделение not in ("+","-") 
        ;""",  rez_dict=True, attach_dbs=(bd_naryad))
    #second_tbl = CSQ.custom_request_c(bd_naryad,f"""SELECT dolgn_etap.Должность, dolgn_etap.Подразделение,
    #etaps.name as этап, etaps.ДляЕРП FROM dolgn_etap INNER JOIN etaps ON etaps.name == dolgn_etap.этап""",  rez_dict=True)
    #list_rez = []
    #for user in first_tbl:
    #    etap = None
    #    for_erp = 1
    #    for item in second_tbl:
    #        if user['Должность'] == item['Должность'] and user['Подразделение'] == item['Подразделение'] :
    #            etap  = item['этап']
    #            for_erp = item['ДляЕРП']
    #            break
    #    user['этап'] = etap
    #    user['ДляЕРП'] = for_erp
    return F.deploy_dict_c(first_tbl,'ФИО')
# +++07.07.25
@F.cache_result(minutes=3)
def list_dolgn_etap(date_str: str, date_maska: str = '%y-%m-%d'):
    replace_null_date = """
    CASE 
        WHEN ДействуетДо IS NULL OR ДействуетДо = ''
        THEN datetime(CURRENT_TIMESTAMP) 
        ELSE datetime(ДействуетДо) 
    END
    """
    date_obj = F.strtodate(date_str, date_maska)
    query = f"""
    SELECT employee.ФИО, employee.Пномер, employee.Должность, employee.Подразделение, dolgn_etap.этап, dolgn_etap.ДействуетДо
    from employee
    LEFT JOIN (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY Должность, Подразделение, Производство 
                ORDER BY ({replace_null_date}) 
                ) as rowNumber
        FROM dolgn_etap
        where ({replace_null_date}) > datetime({date_obj.isoformat()!r}) 
    ) as dolgn_etap ON employee.Должность = dolgn_etap.Должность AND employee.Подразделение = dolgn_etap.Подразделение AND 
               employee.Компания = dolgn_etap.Производство AND rowNumber = 1
    WHERE employee.Пномер IN (SELECT Пномер FROM (SELECT
    	MAX(Пномер) as Пномер,
    	ФИО
    FROM
    	employee
    GROUP BY
    	ФИО
    HAVING COUNT(*) >= 1 ))
    """
    etaps = CSQ.custom_request_c(
        CFG.Config.project.db_naryad,
        query,
        attach_dbs=(CFG.Config.project.db_users,),
        rez_dict=True
    )
    return etaps

def etap_by_employee(date_str: str, key_employee: str, date_maska: str = '%y-%m-%d'):
    patterns = {
        r'^[0-9]+$': 'Пномер',
        r'^[А-ЯЁа-яё]+\s[А-ЯЁа-яё]+\s[А-ЯЁа-яё]+$': 'ФИО',
        r'^[a-f0-9\-]{36}$': 'ID_ФизЛица'
    }
    value_str = str(key_employee)
    key = None
    for pattern, description in patterns.items():
        if re.match(pattern, value_str.strip()):
            key = description
            break
    if key is None:
        return
    etaps = list_dolgn_etap(date_str, date_maska)
    cur_employee = []
    for employee in etaps:
        if employee[key] == key_employee:
            cur_employee.append(employee)
    target_obj = None
    try:
        date_mk = datetime.datetime.strptime(date_str, date_maska)
    except Exception as e:
        print(e)
    for empl in cur_employee:
        end_etap = empl['ДействуетДо']
        if not target_obj and not end_etap:
            target_obj = empl
        elif end_etap and date_mk < datetime.datetime.strptime(end_etap, '%Y-%m-%d'):
            target_obj = empl
    return target_obj['этап']
# ---07.07.25


def NAPRAVL_DEYAT(DB_kplan):
    PLACE = CFG.Config.place
    NAPRAVL_DEYAT_tbl = CSQ.custom_request_c(DB_kplan, f"""SELECT * FROM napravl_deyat WHERE poki == {PLACE.poki};""", hat_c=False, rez_dict=True)

    NAPRAVL_DEYAT = F.deploy_dict_c(NAPRAVL_DEYAT_tbl, 'Имя')

    return NAPRAVL_DEYAT

def VID_RABOT_PO_DOLGN(bd_users):

    second_tbl = CSQ.custom_request_c(bd_users, f"""SELECT * FROM vid_rab_po_dolg;""", hat_c=False, rez_dict=True)

    VID_RABOT_PO_DOLGN = F.deploy_dict_c(second_tbl, 'Должность')
    return VID_RABOT_PO_DOLGN
def PRICES_BY_VID_RABOT(bd_users):

    second_tbl = CSQ.custom_request_c(bd_users, f"""SELECT * FROM vid_rab_po_dolg;""", hat_c=False, rez_dict=True)

    PRICES_BY_VID_RABOT = F.deploy_dict_c(second_tbl, 'Вид_работ')
    return PRICES_BY_VID_RABOT

# @CQT.onerror

def upload_work_productivity_4(self, data_nach=None, data_kon=None, list_users=None, podr_filtr=None, mk=None):
    if data_nach == None:
        data_nach, data_kon = F.start_end_dates_c()
    dict_kpl_part_py = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan,f"""SELECT НомПартии_ЗП, НомПл FROM пл_оуп""",rez_dict=True),'НомПл')
    dict_dolgn_etap = F.deploy_dict_c(CSQ.custom_request_c(self.bd_naryad, f"""
    SELECT * FROM dolgn_etap""", rez_dict=True),"Должность")
    LIST_ZAMEN_FIO = ['Работник Заготовительного Цеха', 'Работник Заготовительного Цеха2']
    dict_rez = dict()
    spis_rez = []
    # if F.strtodate(F.now()) - timedelta(days=70) > F.strtodate('2022-11-01 00:00:01'):
    # data_nach = F.datetostr(F.strtodate(F.now()) - timedelta(days=40))
    # else:
    #    data_nach = '2022-11-01 00:00:01'
    mk_condition =""
    if mk != None:
        mk_condition = f" AND mk.Пномер = {mk} "
    custom_request_c = f"""SELECT 
                        jurnal.Пномер as jurnal_Пномер,
                        jurnal.Дата, 
                       jurnal.Штамп, 
                       jurnal.Номер_наряда, 
                       jurnal.ФИО, 
                       mk.Номер_проекта || "$" || 
                       mk.Номер_заказа AS "ПУ", 
                       mk.Дата AS "Дата_МК", 
                       mk.НомКплан, 
                       mk.Статус,
                       mk.НомКплан,
                       naryad.Внеплан, 
                       naryad.Операции, 
                       naryad.Номер_мк, 
                       naryad.Виды_работ, 
                       jurnal.Статус, 
                       naryad.Твремя, 
                       jurnal.Подытог, 
                       jurnal.Примечание, 
                       naryad.Опер_время,
                       naryad.ДСЕ,
                       naryad.Пномер,
                       naryad.Виды_работ
                        FROM jurnal INNER JOIN naryad
                        ON jurnal.Номер_наряда = naryad.Пномер
                        INNER JOIN mk
                        ON naryad.Номер_мк = mk.Пномер
                        WHERE jurnal.Статус == "Начат" AND jurnal.Подытог > 0
                        and naryad.Внеплан == 0 
                        and mk.ТипВыгрузкиТрЗт == 3 {mk_condition}
                        and datetime(jurnal.Дата) > datetime("{data_nach}")
                        and datetime(jurnal.Дата) <= datetime("{data_kon}")"""
    dict_nar_tmp = dict()
    dict_mk_tmp = dict()
    resp_db_mes = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)
    if resp_db_mes == False or resp_db_mes == None:
        return
    for i in range(len(resp_db_mes)):
        if resp_db_mes[i]['Пномер'] in dict_nar_tmp:
            nar = dict_nar_tmp[resp_db_mes[i]['Пномер']]
        else:
            nar = Naryads(resp_db_mes[i]['Пномер'],self.bd_naryad)
            if nar.Номер_мк in dict_mk_tmp:
                nar.mk = dict_mk_tmp[nar.Номер_мк]
            else:
                nar.get_mk(self.db_resxml,True)
                dict_mk_tmp[nar.Номер_мк] = nar.mk
            nar.load_mats(self.DICT_PROFESSIONS, self.db_resxml)
            if nar.Пномер not in dict_nar_tmp:
                dict_nar_tmp[nar.Пномер] = nar
        #if resp_db_mes[i]['ФИО'] not in list_users:
        #    continue
        subtype = None

        type_vneplan = nar.mk.Тип_мк_Имя
        if type_vneplan == 'Дорезка':
            subtype = nar.mk.тип_дорезок_Имя
        if type_vneplan == 'Доработка(без дорезки)':
            subtype = nar.mk.тип_доработок_Имя

        if resp_db_mes[i]['ФИО'] in LIST_ZAMEN_FIO:
            resp_db_mes[i]['ФИО'] = resp_db_mes[i]['Примечание']

        if resp_db_mes[i]['ФИО'] not in self.Data.ETAP_BY_FIO:
            CQT.msgbox(f'В наряде {resp_db_mes[i]["Номер_наряда"]} пользователь {resp_db_mes[i]["ФИО"]} не имеет этап для должности в БД')
            return
        if self.Data.ETAP_BY_FIO[resp_db_mes[i]['ФИО']]['ДляЕРП'] == 0:
            continue
        np_sep_py = resp_db_mes[i]['ПУ']
        date_py = '20' + resp_db_mes[i]['Дата_МК']
        py_year = np_sep_py + "$" + F.datetostr(F.strtodate(date_py,),"%Y")
        if py_year not in dict_rez:
            dict_rez[py_year] = {"Тип": type_vneplan,
                                 "Подтип": subtype,
                                 "Этапы": dict()}
        np, py, year = py_year.split("$")
        etap = self.Data.ETAP_BY_FIO[resp_db_mes[i]['ФИО']]['этап']

        data_etap_erp = CSQ.custom_request_c(self.db_kplan,f"""SELECT Ref_Key_py, data_etaps_from_erp 
         FROM знпр WHERE №ERP = "{py}" AND Год = "{year}";""",rez_dict=True,one=True)
        ref_Key_py = data_etap_erp['Ref_Key_py']
        dict_etaps_from_erp = F.from_binary_pickle(data_etap_erp['data_etaps_from_erp'])
        if resp_db_mes[i]['НомКплан'] not in dict_kpl_part_py:
            CQT.msgbox(f'на \n{resp_db_mes[i]} \n\nне обнаржуен пл_оуп.НомПартии_ЗП\n!!Не учтено!!\nОбратиться в ПДО')
            continue
        part_py = dict_kpl_part_py[resp_db_mes[i]['НомКплан']]
        fl = False
        part_py = str(part_py)
        if part_py  in dict_etaps_from_erp:
            for val_etap in dict_etaps_from_erp[part_py]['Этапы']:
                if etap == val_etap['НаименованиеЭтапа']:
                    fl = True
                    etap_num = val_etap['Number']
                    break
            if not  fl:
                list_etaps_str = [f" {_['Number']} | {_['НаименованиеЭтапа']}" for _ in
                                  dict_etaps_from_erp[part_py]['Этапы']]
                НомКплан = resp_db_mes[i]['НомКплан']

                CQT.msgbox(f'В МЕС не найден этап для КПЛ {НомКплан}\nНомПартии_ЗП: {part_py}\nэтап: '
                           f'"{etap}"\n Нужно обратиться в ПДО для корректировки\n\nТекущий список этапов:\n'
                           f' {list_etaps_str}')
                return
        else:
                CQT.msgbox(f'НомерПартииЗапуска {part_py} не найден в МЕС\n Нужно обратиться в ПДО для корректировки')

        podr = self.Data.ETAP_BY_FIO[resp_db_mes[i]['ФИО']]['Подразделение']
        if podr == podr_filtr:
            if etap_num not in dict_rez[py_year]['Этапы']:
                dict_rez[py_year]['Этапы'][etap_num] = {'Расход':[],
                                  'Традозатраты':[]}
        else:
            continue
        if nar.Внеплан != 0:
            continue
        count_users = nar.count_users()
        fiod = f"{resp_db_mes[i]['ФИО']} {self.DICT_EMPLOEE_FULL_WITH_DEL[resp_db_mes[i]['ФИО']]['Должность']}"

        time = F.valm(int(resp_db_mes[i]['Подытог']))
        for oper in nar.params:
            vid_rabot = oper['Виды_работ']
            nom_nar = nar.Пномер

            time_minutes = oper['Опер_время']/count_users

            data_end = resp_db_mes[i]['Дата']
            if podr == podr_filtr:
                dict_rez[py_year]['Этапы'][etap_num]['Традозатраты'].append(
                    {'НаименованиеЭтапа': etap,
                     'Вид работ': vid_rabot ,
                        'Количество': time_minutes ,
                        'Норма на единицу': '' ,
                        'Ед. изм.': 'мин. заработн. плат' ,
                        'Дата выполнения': data_end ,
                        'Выполнено': 'Да' ,
                        'Исполнитель': resp_db_mes[i]['ФИО'] ,
                        'Статья калькуляции': 'Основной ФОТ' ,
                        'Задание на резку': '' ,
                        'Назначение работ': '' ,
                        'Отменено по причине': '' ,
                        'Отменено': 'Нет' ,
                        'Ключ_мес': resp_db_mes[i]['jurnal_Пномер']
                        })

            etap_mat= oper['Этап_материала']
            if podr == podr_filtr:
                for mat in oper['Материалы']:
                    if etap_mat not in dict_rez[py_year]['Этапы']:
                        dict_rez[py_year]['Этапы'][etap_mat] = {'Расход': [],
                                                   'Традозатраты': []}
                    dict_rez[py_year]['Этапы'][etap_mat]['Расход'].append(
                        {'Артикул': mat['Мат_код'] ,
                            'Номенклатура': mat['Мат_наименование'] ,
                        'Характеристика': '' ,
                        'Количество': mat['Мат_норма_ед']* oper['Опер_колво']/count_users,
                        'Упаковка': '' ,
                        'Ед. изм.': mat['Мат_ед_изм'] ,
                        'Израсходован': data_end ,
                        'Статья калькуляции': 'Сырье' ,
                        'Задание на резку': '' ,
                         'Ключ_мес': resp_db_mes[i]['jurnal_Пномер']
                         })

    dir_tdz_user_rc = save_tdz_json(dict_rez,data_nach,data_kon,self.ui.le_path_save.text(),podr_filtr)

    return dir_tdz_user_rc

def upload_work_productivity_3(self, data_nach, data_kon, list_users, podr_filtr=None,  mk=None, by_norm = False):
    suffix = 'jurnal.Подытог'
    if by_norm:
        suffix = 'jurnal.Подытог_нормы AS Подытог'
    LIST_ZAMEN_FIO = ['Работник Заготовительного Цеха', 'Работник Заготовительного Цеха2']
    dict_rez = dict()
    spis_rez = []
    # if F.strtodate(F.now()) - timedelta(days=70) > F.strtodate('2022-11-01 00:00:01'):
    # data_nach = F.datetostr(F.strtodate(F.now()) - timedelta(days=40))
    # else:
    #    data_nach = '2022-11-01 00:00:01'
    mk_condition =""
    if mk != None:
        mk_condition = f" AND mk.Пномер = {mk} "
    custom_request_c = f'SELECT jurnal.Пномер as jurnal_Пномер, jurnal.Дата, ' \
             f'jurnal.Штамп, ' \
             f'jurnal.Номер_наряда, ' \
             f'jurnal.ФИО, ' \
            f' CASE WHEN знпр.№проекта IS NOT NULL '\
       f'THEN знпр.№проекта '\
       f'ELSE mk.Номер_проекта '\
       f'END '\
             f' || "$" || ' \
    f'        CASE WHEN знпр.№ERP IS NOT NULL ' \
    f'   THEN знпр.№ERP ' \
    f'   ELSE mk.Номер_заказа ' \
    f'   END AS "НП$ПУ",' \
                       f'знпр.data_etaps_from_erp, ' \
                       f'пл_оуп.НомПартии_ЗП, ' \
                       f'naryad.Внеплан, ' \
             f'naryad.Операции, ' \
             f'naryad.Номер_мк, ' \
             f'naryad.Виды_работ, ' \
             f'jurnal.Статус, ' \
             f'naryad.Твремя, ' \
             f'{suffix}, ' \
             f'jurnal.Примечание, ' \
             f'naryad.Опер_время,' \
             f'naryad.ДСЕ,' \
             f'naryad.Виды_работ' \
             f' FROM jurnal INNER JOIN naryad' \
             f' ON jurnal.Номер_наряда = naryad.Пномер' \
             f' INNER JOIN mk' \
             f' ON naryad.Номер_мк = mk.Пномер' \
            f'   LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан ' \
            f'  LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП ' \
             f' WHERE jurnal.Статус == "Начат" AND jurnal.Подытог > 0' \
             f' and datetime(jurnal.Дата) > datetime("{data_nach}")' \
             f' and datetime(jurnal.Дата) <= datetime("{data_kon}")'
    # f' and mk.ТипВыгрузкиТрЗт == 3 {mk_condition}' \

    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True,attach_dbs=(self.db_kplan))
    if rez == False or rez == None:
        return

    def add_block(self,row,datetime_nach,dict_rez,etap,nom_nar,dse,vid_rabot_empl,dolya_time,postfix_shtamp='',ref_key_etap='00000000-0000-0000-0000-000000000000'):
        fiod = f"{row['ФИО']} {self.DICT_EMPLOEE_FULL_WITH_DEL[row['ФИО']]['Должность']}"

        dict_rez[etap].append([datetime_nach, postfix_shtamp+ "_0", nom_nar, fiod, row['НП$ПУ'],
                               etap, dse, row['Статус'],
                               "", "", F.clear_row_for_file_name_c(row['Примечание']),
                               self.DICT_EMPLOEE_FULL_WITH_DEL[row['ФИО']]['Подразделение'], vid_rabot_empl,ref_key_etap])

        time_sec = dolya_time * 60

        data_end = F.datetostr(F.strtodate(datetime_nach) + timedelta(seconds=time_sec))


        dict_rez[etap].append(
            [data_end, postfix_shtamp+ "_1", nom_nar, fiod, row['НП$ПУ'], etap, dse, "Завершен",
             round(dolya_time, 2), "Основной ФОТ",
             F.clear_row_for_file_name_c(row['Примечание'])
                , self.DICT_EMPLOEE_FULL_WITH_DEL[row['ФИО']]['Подразделение'], vid_rabot_empl,ref_key_etap])
        return dict_rez

    for i in range(len(rez)):
        if rez[i]['НП$ПУ'] == 'ПРОСТОЙ$ПРОСТОЙ':
            continue
        struct_etaps = F.from_binary_pickle(rez[i]['data_etaps_from_erp'])
        if struct_etaps == None:
            CQT.msgbox(f"""По {rez[i]['НП$ПУ']}  не распознаны этапы """)
            return
        list_etaps_erp = { _['НаименованиеЭтапа']:_ for _ in struct_etaps if _['НомерПартииЗапуска'] == str(rez[i]['НомПартии_ЗП'])}
        if rez[i]['ФИО'] in LIST_ZAMEN_FIO:
            if not rez[i]['Примечание'].strip():
                msg = f'''По {rez[i]['НП$ПУ']} в наряде №{rez[i]['Номер_наряда']} от {rez[i]['Дата']}
                отсутствует ФИО в поле "Примечание"
                Отчет не будет выгружен, пока ошибка не будет исправлена
                (Исполнители {LIST_ZAMEN_FIO} 
                должны ставить свое ФИО в примечание)'''
                CQT.msgbox(msg)
                return
            rez[i]['ФИО'] = rez[i]['Примечание']
        if rez[i]['ФИО']  not in self.Data.VID_RABOT_PO_EMPL:
            CQT.msgbox(f"Для {rez[i]['ФИО']} не найден вид работ см. db emploee")
            return
        vid_rabot_empl = self.Data.VID_RABOT_PO_EMPL[rez[i]['ФИО']]['Вид_работ']

        if rez[i]['ФИО'] not in self.Data.ETAP_BY_FIO:
            CQT.msgbox(f'В наряде {rez[i]["Номер_наряда"]} пользователь {rez[i]["ФИО"]} не обнаружен в БД')
            return
        etap = self.Data.ETAP_BY_FIO[rez[i]['ФИО']]['этап']#этап берёшь из должности по факту,
        if etap not in list_etaps_erp:
            print(f"По наряду {rez[i]['Номер_наряда']} для {rez[i]['ФИО']} {self.Data.ETAP_BY_FIO[rez[i]['ФИО']]['Должность']} нет подходящего этапа в ЕРП `{etap}`\n труды не учтены")
            continue
        ref_key_etap = list_etaps_erp[etap]['Ref_Key']
        if ref_key_etap == '00000000-0000-0000-0000-000000000000':
            print(f"По наряду {rez[i]['Номер_наряда']} для {rez[i]['ФИО']} {self.Data.ETAP_BY_FIO[rez[i]['ФИО']]['Должность']} пустая ссылка на этап `{etap}`\n труды не учтены")
            continue
        podr = self.Data.ETAP_BY_FIO[rez[i]['ФИО']]['Подразделение']
        if podr == podr_filtr:
            if etap not in dict_rez:
                dict_rez[etap] = []
            spis_oper = rez[i]['Операции'].split('|')
            spis_time = rez[i]['Опер_время'].split('|')
            spis_doley = []
            spis_dse = rez[i]['ДСЕ'].split('|')
            summ = 0
            for t in spis_time:
                summ += F.valm(t)
            for t in spis_time:
                if summ == 0:
                    spis_doley.append(0)
                else:
                    spis_doley.append(round(F.valm(t) / summ, 6))
            spis_sort_c = rez[i]['Виды_работ'].split('|')
            npp = 0
            time = F.valm(int(rez[i]['Подытог']))
            for j in range(len(spis_oper)):
                #vid_rabot = spis_sort_c[j]
                npp += 1
                nom_nar = str(rez[i]['Номер_наряда']) + str(npp)
                if etap == 'Вспомогательная' and rez[i]['Внеплан'] == 0:
                    continue

                time_min = spis_doley[j] * time

                recoded_min = 0
                p_i = 0
                while recoded_min<time_min:
                    postfix_shtamp = f"{rez[i]['jurnal_Пномер']}_{j}_{p_i}"
                    if recoded_min + 1000>= time_min:
                        time_min_part = time_min-recoded_min
                    else:
                        time_min_part = 1000
                    recoded_min+=time_min_part
                    p_i+=1
                    datetime_nach = F.datetostr(F.strtodate(rez[i]['Дата']),  "%Y-%m-%d 06:54:32")
                    dict_rez = add_block(self, rez[i], datetime_nach,dict_rez,etap,nom_nar,spis_dse[j],vid_rabot_empl,time_min_part,postfix_shtamp,ref_key_etap)

    tmp = []
    tmp_lazer = []
    for etap in dict_rez.keys():
        if etap != 'Лазерная резка':
            for item in dict_rez[etap]:
                tmp.append(item)
    dir_tdz_user_rc = None
    if len(tmp) > 0:
        dir_tdz_user_rc = save_tdz_txt(tmp, data_nach, 'Обработка', podr_filtr, self.ui.le_path_save.text())
    if 'Лазерная резка' in dict_rez:
        if len(dict_rez['Лазерная резка']) > 0:
            dir_tdz_user_rc = save_tdz_txt(dict_rez['Лазерная резка'], data_nach, 'Заготовительный', podr_filtr, self.ui.le_path_save.text())

    return dir_tdz_user_rc


    # F.write_file_c(F.scfg('employee') + F.sep() + 'Trudozatrati.txt', spis_rez,separ='|',utf8=False)

def save_tdz_json(dict_rez,data_nach,data_kon,path_save,rab_centr):
    data_str = F.datetostr(F.strtodate(data_nach), '%d%m%Y') + "_" + F.datetostr(F.strtodate(data_kon), '%d%m%Y')
    dir_tdz = path_save + F.sep() + 'Трудозатраты'
    if not F.existence_file_c(dir_tdz):
        F.create_dir_c(dir_tdz)
    dir_tdz_user = dir_tdz + F.sep() + F.user_name()
    if not F.existence_file_c(dir_tdz_user):
        F.create_dir_c(dir_tdz_user)
    dir_tdz_user_rc = dir_tdz_user + F.sep() + rab_centr
    if not F.existence_file_c(dir_tdz_user_rc):
        F.create_dir_c(dir_tdz_user_rc)
    F.write_json_c(dict_rez,dir_tdz_user_rc + F.sep() + f'{data_str}_Trudozatrati_4.json',lines=False)
    return dir_tdz_user_rc


def save_tdz_txt(tmp, data_nach, etap, rab_centr, path):
    data_str = F.datetostr(F.strtodate(data_nach), '%Y-%m-%d')
    dir_tdz = path + F.sep() + 'Трудозатраты'
    if not F.existence_file_c(dir_tdz):
        F.create_dir_c(dir_tdz)
    dir_tdz_user = dir_tdz + F.sep() + F.user_name()
    if not F.existence_file_c(dir_tdz_user):
        F.create_dir_c(dir_tdz_user)
    dir_tdz_user_rc = dir_tdz_user + F.sep() + rab_centr
    if not F.existence_file_c(dir_tdz_user_rc):
        F.create_dir_c(dir_tdz_user_rc)
    F.save_file(dir_tdz_user_rc + F.sep() + f'{data_str}_{etap}_Trudozatrati_3.txt', tmp, utf=False)
    return dir_tdz_user_rc

#@CQT.onerror
def upload_work_productivity_2(self, data_nach, data_kon, list_users,rab_centr, conn='', cur = '' ):
    LIST_ZAMEN_FIO = ['Работник Заготовительного Цеха','Работник Заготовительного Цеха2']
    spis_rez = []
    #if F.strtodate(F.now()) - timedelta(days=70) > F.strtodate('2022-11-01 00:00:01'):
    #data_nach = F.datetostr(F.strtodate(F.now()) - timedelta(days=40))
    #else:
    #    data_nach = '2022-11-01 00:00:01'
    custom_request_c = f'SELECT jurnal.Дата, ' \
             f'jurnal.Штамп, ' \
             f'jurnal.Номер_наряда, ' \
             f'jurnal.ФИО, ' \
             f'mk.Номер_проекта || "$" || ' \
             f'mk.Номер_заказа AS "НП$ПУ", ' \
             f'naryad.Внеплан, ' \
             f'naryad.Операции, ' \
             f'naryad.Номер_мк, ' \
             f'naryad.Виды_работ, ' \
             f'jurnal.Статус, ' \
             f'naryad.Твремя, ' \
             f'jurnal.Подытог, ' \
             f'jurnal.Примечание, ' \
             f'naryad.Опер_время,' \
             f'naryad.ДСЕ,' \
             f'naryad.Виды_работ' \
             f' FROM jurnal INNER JOIN naryad' \
             f' ON jurnal.Номер_наряда = naryad.Пномер' \
             f' INNER JOIN mk' \
             f' ON naryad.Номер_мк = mk.Пномер' \
             f' WHERE jurnal.Статус == "Начат" AND jurnal.Подытог > 0' \
             f' and datetime(jurnal.Дата) > datetime("{data_nach}")' \
            f' and datetime(jurnal.Дата) <= datetime("{data_kon}")'
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c,rez_dict=True,conn=conn, cur = cur)
    if rez == False or rez == None:
        return
    set_etapov = set()
    for i in range(1, len(rez)):
        if rez[i]['ФИО'] in LIST_ZAMEN_FIO:
            rez[i]['ФИО'] = rez[i]['Примечание']
        spis_oper = rez[i]['Операции'].split('|')
        spis_time = rez[i]['Опер_время'].split('|')
        spis_doley = []
        spis_dse = rez[i]['ДСЕ'].split('|')
        summ = 0
        for t in spis_time:
            summ += F.valm(t)
        for t in spis_time:
            if summ == 0:
                spis_doley.append(0)
            else:
                spis_doley.append(round(F.valm(t)/summ,3))
        spis_sort_c = rez[i]['Виды_работ'].split('|')
        npp = 0
        time = F.valm(int(rez[i]['Подытог']))
        for j in range(len(spis_oper)):
            oper_name = spis_oper[j].split('$')[1]
            vid_rabot = spis_sort_c[j]
            if oper_name in self.DICT_ETAPI:
                npp+=1
                nom_nar = str(rez[i]['Номер_наряда']) + str(npp)
                if rez[i]['Внеплан'] == 0:
                    etap = self.DICT_ETAPI[oper_name]
                else:
                    if vid_rabot not in self.DICT_VID_RABOT:
                        CQT.msgbox(f"наряд {rez[i]['Номер_наряда']} вид работ {vid_rabot} не найден в справочнике")
                        return
                    etap = self.DICT_VID_RABOT[rez[i]['Виды_работ']]['этап']
                if etap == 'Вспомогательная' and rez[i]['Внеплан'] == 0:
                    pass
                else:
                    if rez[i]['ФИО'] in list_users:
                        fiod =  f"{rez[i]['ФИО']} {self.DICT_EMPLOEE_FULL[rez[i]['ФИО']]['Должность']}"
                        spis_rez.append([rez[i]['Дата'],rez[i]['Штамп'],nom_nar,fiod,rez[i]['НП$ПУ'],
                                         etap,spis_dse[j],rez[i]['Статус'],
                                        "","",F.clear_row_for_file_name_c(rez[i]['Примечание']),self.DICT_EMPLOEE_FULL[rez[i]['ФИО']]['Подразделение']])
                        time_sec = spis_doley[j]*time*60
                        data_end = F.datetostr(F.strtodate(rez[i]['Дата']) + timedelta(seconds =time_sec))
                        shtamp = F.shtamp_from_date(data_end)
                        spis_rez.append(
                            [data_end, shtamp, nom_nar, fiod, rez[i]['НП$ПУ'], etap,spis_dse[j],"Завершен",
                             round(spis_doley[j]*time), "Основной ФОТ", F.clear_row_for_file_name_c(rez[i]['Примечание'])
                                ,self.DICT_EMPLOEE_FULL[rez[i]['ФИО']]['Подразделение']])
                        set_etapov.add(etap)
    tmp = []
    tmp_lazer = []
    for etap in set_etapov:
        if etap != 'Лазерная резка':
            for item in spis_rez:
                if etap == item[5]:
                    tmp.append(item)
        else:
            for item in spis_rez:
                if etap == item[5]:
                    tmp_lazer.append(item)
    save_tdz_txt(tmp,data_nach, 'Обработка',rab_centr,self.ui.le_path_save.text())
    dir_tdz_user_rc = save_tdz_txt(tmp_lazer,data_nach, 'Заготовительный', rab_centr,self.ui.le_path_save.text())
    if CQT.msgboxgYN('Успешно выгружено!\nОткрыть папку?'):
        F.open_dir_c(dir_tdz_user_rc)

    #F.write_file_c(F.scfg('employee') + F.sep() + 'Trudozatrati.txt', spis_rez,separ='|',utf8=False)
@CQT.onerror
def save_tdz_txt(tmp,data_nach,etap,rab_centr,path):
    data_str = F.datetostr(F.strtodate(data_nach), '%Y-%m-%d')
    dir_tdz = path + F.sep() + 'Трудозатраты'
    if not F.existence_file_c(dir_tdz):
        F.create_dir_c(dir_tdz)
    dir_tdz_user = dir_tdz + F.sep() + F.user_name()
    if not F.existence_file_c(dir_tdz_user):
        F.create_dir_c(dir_tdz_user)
    dir_tdz_user_rc = dir_tdz_user + F.sep() + rab_centr
    if not F.existence_file_c(dir_tdz_user_rc):
        F.create_dir_c(dir_tdz_user_rc)
    F.save_file(dir_tdz_user_rc + F.sep() + f'{data_str}_{etap}_Trudozatrati_2.txt', tmp, utf=False)
    return dir_tdz_user_rc

@CQT.onerror
def upload_work_productivity_old(self,conn = ''): #off
    spis_rez = []
    data_nach = F.datetostr(F.strtodate(F.now()) - timedelta(days =70))
    custom_request_c = f'SELECT jurnal.Дата, ' \
             f'jurnal.Штамп, ' \
             f'jurnal.Номер_наряда, ' \
             f'jurnal.ФИО, ' \
             f'mk.Номер_проекта, ' \
             f'mk.Номер_заказа, ' \
             f'naryad.Операции, ' \
             f'naryad.Номер_мк, ' \
             f'jurnal.Статус, ' \
             f'naryad.Твремя, ' \
             f'jurnal.Подытог, ' \
             f'jurnal.Примечание, ' \
             f'naryad.Опер_время' \
            f' FROM jurnal INNER JOIN naryad'\
    f' ON jurnal.Номер_наряда = naryad.Пномер'\
    f' INNER JOIN mk'\
    f' ON naryad.Номер_мк = mk.Пномер'\
    f' WHERE jurnal.Статус == "Начат" AND naryad.Операции NOT LIKE "%Резка(ЧПУ)%" AND jurnal.Подытог > 0 and date(jurnal.Дата) > date("{data_nach}")'

    rez = CSQ.custom_request_c(self.db_naryd,custom_request_c,conn = conn)
    rez[0][4] = "НП$ПУ"
    rez[0][6] = "Этап"
    rez[0][7] = "Ном_мк"

    for i in range(1, len(rez)):
        rez[i][4] = rez[i][4] + '$' + rez[i][5]
        #rez[i][8] = f'Теор={rez[i][8]}'
        #rez[i][9] = f'Факт={0}'
        spis_oper = rez[i][6].split('|')
        spis_time = rez[i][12].split('|')
        npp = 0
        time = round((int(rez[i][10])) * 60 + 1)
        time_h = round(int(rez[i][10]) / 60, 2)
        for j in range(len(spis_oper)):
            oper_name = spis_oper[j].split('$')[1]
            #time = round((int(spis_time[j]))*60 + 1)
            if oper_name in self.DICT_ETAPI:
                npp+=1
                nom_nar = str(rez[i][2]) + str(npp)
                rez[i][6] = self.DICT_ETAPI[oper_name]
                if rez[i][6] == 'Вспомогательная':
                    pass
                else:
                    fiod = self.fiod(rez[i][3])
                    spis_rez.append([rez[i][0],rez[i][1],nom_nar,fiod,rez[i][4],rez[i][6],"",rez[i][8],
                                    "","",F.clear_row_for_file_name_c(rez[i][11])])
                    data_end = F.datetostr(F.strtodate(rez[i][0]) + timedelta(seconds =time))
                    shtamp = F.shtamp_from_date(data_end)
                    spis_rez.append(
                        [data_end, shtamp, nom_nar, fiod, rez[i][4], rez[i][6],"","Завершен",
                         f'Теор={time_h}', f'Факт={time_h}', F.clear_row_for_file_name_c(rez[i][11])])
                    break
    #F.save_file(F.scfg('employee') + F.sep() + 'Trudozatrati.txt', spis_rez)
    F.write_file_c(F.scfg('employee') + F.sep() + 'Trudozatrati.txt', spis_rez,separ='|',utf8=False)

"""srv_kl = r'docs://srv-docs-pkb.powerz.ru:21321/OpenReferenceWindow/?refId=404&objId=8539'
srv_kt = r'docs://srv-docs.powerz.ru:21321/OpenReferenceWindow/?refId=403&objId=15560'
srv_shg = r'docs://srv-docs.powerz.ru:21361/OpenReferenceWindow/?refId=404&objId=5184'
run_link_DOCs_c('','',srv_kl)"""



def list_calc_tehnologs(bd_naryad,bd_users,db_resxml,db_dse):
    #print(f'=====Выгрузка рейтинга технологов=======')
    nach, konec = F.start_end_dates_c(vid='m')
    nach_date = F.date_add_days(nach,-1)
    nach = F.start_end_dates_c(date=nach_date, vid='m')[0]
    dict_users, dict_napr = report_ci.calc_tehpodgotovka_per_month(bd_naryad,bd_users,db_resxml, db_dse, nach, konec, 'По сотрудникам')
    F.save_file_pickle(r"Z:\Data\dict_users_reit_tk.pickle",dict_users)
    #print(f'=====Выгрузка рейтинга технологов Успешно=======')
    return

def add_cust_drevo(self, put_ima, old_list, row,count_izd=1,modifiers = ''):
    spis = F.open_file_c(put_ima, False, separ='', pickl=True)
    nk_kolvo = F.num_col_by_name_in_hat_c(spis, 'Количество')
    length_headers = len(self.hat_c) #09.04.25
    for i in range(1, len(spis)):
        if len(spis[i]) != length_headers:
            CQT.msgbox('Файл некоррктный')
            return
        if 'f' not in spis[i][nk_kolvo]:
            if not F.is_numeric(spis[i][nk_kolvo]):
                spis[i][nk_kolvo] = 1
            spis[i][nk_kolvo] = int(F.valm(spis[i][nk_kolvo])) * count_izd
    if modifiers == '':
        modifiers = CQT.get_key_modifiers(self)
    else:
        modifiers = [modifiers]
    if modifiers == ['shift']:
        if len(old_list) == 0:
            row = -1
        nk_level_c = F.num_col_by_name_in_hat_c(spis, 'Уровень')
        if row == -1:
            level_c = 0
            row = 0
        else:
            level_c = int(old_list[row][nk_level_c]) + 1
            # level_c = int(CQT.value_of_selection_row_by_column_c(self.ui.table_razr_MK, 'Уровень')) + 1
        koef = 1
        nach = 1
        if old_list == []:
            old_list = copy.deepcopy([spis[0]])
        for i in range(1, len(spis)):
            spis[i][nk_level_c] = str(int(spis[i][nk_level_c]) + level_c)
            old_list.insert(row + koef + 1, spis[i])
            koef += 1
        spis = old_list

    return spis

@CQT.onerror
def path_kd_dbl_clk(tbl,row,column):
    if column == CQT.num_col_by_name_c(tbl,'Путь до ВО'):
        path = tbl.item(row,column).text()
        if 'docs://' in path:
            path = path.strip().replace('\n', '').replace('\r', '')
            try:
                os.startfile(f"{path}")
            except:
                CQT.msgbox(f'ОШибка')
            return
        if not F.existence_file_c(path):
            CQT.msgbox(f'Путь {path} не доступен')
            return
        F.open_dir_c(path)

@CQT.onerror
def update_data_etaps_from_erp(db_kplan,resp,s_num):
    if resp is None:
        return False
    if len(resp) > 0:
        blob = F.to_binary_pickle(resp)
        CSQ.custom_request_c(db_kplan, f"""UPDATE знпр SET (data_etaps_from_erp,Этапы_ЕРП) = (?,?) 
                WHERE s_num == ?;""", list_of_lists_c=[blob, 2, s_num])
        return True
    return False


@CQT.onerror
def apply_gui_groups(self: mywindow):
    if not self.ui.chk_kpl_groups.isChecked():
        return 
    tbl:QtWidgets.QTableWidget = self.ui.tbl_kal_pl

    dict_filtr = apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, False,
                                   get_dict_by_fild='plan.Пномер')
    
    tbl.blockSignals(True)
    tbl.setUpdatesEnabled(False)

    nf = CQT.nums_col_by_name_dict(tbl)

    col_group = nf['plan.Группа']
    col_status = nf['plan.Статус']
    col_type = nf['plan.ТипГр']
    col_snum = nf['plan.Пномер']


    row_count = tbl.rowCount()

    # --- собрать все непустые группы, кроме статуса "Группа" ---
    set_groups = set()
    set_groups_filtr_all = set()
    set_groups_filtr_wiev = set()
    for i in range(row_count):
        group_item = tbl.item(i, col_group)
        if not group_item:
            continue
            
        group = group_item.text().strip()
        if group:
            set_groups_filtr_all.add(group)
        

        status_item = tbl.item(i, col_status)
        if not status_item:
            continue
        status = status_item.text()


        if group and status != 'Группа':
            snum = tbl.item(i, col_snum).text()
            if snum in dict_filtr and dict_filtr[snum]:
                set_groups_filtr_wiev.add(group)
            if tbl.isRowHidden(i):
                continue
            set_groups.add(group)


            
    set_groups_filtr_hidden = set_groups_filtr_all - set_groups_filtr_wiev
    # --- обновить только группы ---
    for i in range(row_count):
        status_item = tbl.item(i, col_status)
        if not status_item or status_item.text() != 'Группа':
            continue

        group_item = tbl.item(i, col_group)
        type_item = tbl.item(i, col_type)
        if not group_item or not type_item:
            continue

        if group_item.text() in set_groups:
            type_item.setText(FOLDER_OPEN)
        else:
            type_item.setText(FOLDER_CLOSED)
        tbl.setRowHidden(i, False)
        if group_item.text() in set_groups_filtr_hidden:
            tbl.setRowHidden(i,True)

    tbl.setUpdatesEnabled(True)
    tbl.blockSignals(False)
    tbl.viewport().update()
    
@CQT.onerror
def make_dict_etaps_from_erp(m:ERP.OrdersComposit, ref_key_py:str):
    dict_etaps = dict()
    if ref_key_py == '':
        return dict_etaps
    cod,  resp = m.get_response(doc_name='Document_ЭтапПроизводства2_2',
                          wet_filtr=f"?$filter=Распоряжение_Key "
                                    f"eq guid'{ref_key_py}' and НЭ_НулевойЭтап eq false &$select=Ref_Key,Number,"
                                    f"НаименованиеЭтапа,НомерПартииЗапуска,Спецификация_Key,НЭ_НулевойЭтап",with_cod=True)  #
    if cod != 200:
        CQT.msgbox(f'Err read Document_ЭтапПроизводства2_2 {resp}')
        return  dict()
    for item_resp in resp:
        if item_resp['НомерПартииЗапуска'] not in dict_etaps:
            cod,  name_res = m.get_response(doc_name='Catalog_РесурсныеСпецификации',
                                      wet_filtr=f"?$filter=Ref_Key eq"
                                                f" guid'{item_resp['Спецификация_Key']}'&$select=Статус, "
                                                f"Description,Code",with_cod=True)
            if cod != 200:
                CQT.msgbox(f'Err read Catalog_РесурсныеСпецификации {name_res}')
                return dict()
            if not isinstance(name_res, list):
                print(f'Ошибка загрузки спецификации Ref_Key {item_resp["Спецификация_Key"]}')
                return dict()
            dict_etaps[item_resp['НомерПартииЗапуска']] = {'Спецификация': name_res[0]['Code'],
                                                           'Спецификация_Key': item_resp['Спецификация_Key'],
                                                           'Этапы': []}
        dict_etaps[item_resp['НомерПартииЗапуска']]['Этапы'].append(
            {'Number': item_resp['Number'], 'НаименованиеЭтапа': item_resp['НаименованиеЭтапа'],'Чек':item_resp['Ref_Key']})
    return dict_etaps




class TkpSchema:
    def __init__(self) -> None:
        self.file_name: str = None  # 'ТКПА_4148_КТ.2503167.01.00_Компенсатор тканевый'
        self.nnom_tkp: str = None  # 'ТКПА_4148_КТ.2503167.01.00'
        self.name_tkp: str = None  # 'Компенсатор тканевый'
        self.s_nom: int = None  # 4148
        self.Структура: list[dict] = None
        self.расчет_по_статистике: bool = None
        self.type_tkp = None
        self.weight: float = None
        self.Параметры: dict = {}
        self.XML_start_from_project_product_type: bool = False #12.11.25

    def __contains__(self, item):
        return self.__dict__.get(item) is not None

    def __getitem__(self, item):
        return self.__dict__.get(item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def update(self, new_schema_data: dict):
        self.__dict__.update(new_schema_data)

    @property
    def is_tkp(self):
        return self.type_tkp in (2, 3, 4)

    @property
    def is_statistic(self):
        return self.type_tkp == 4

    @property
    def is_analogue(self):
        return self.type_tkp == 3

    @property
    def is_parametric(self):
        return self.type_tkp == 2

    def clear(self):
        self.__init__()


#+++29.08.25
class DATATypesNomenclature:
    def check_ref(self, label_info: QtWidgets.QLabel, ref_key: str):
        _select = '?$select=Description,Parent_Key'
        doc_name = f'Catalog_ВидыНоменклатуры(guid{ref_key!r})'
        code, resp = ODAT.OrdersComposit().get_response(doc_name, wet_filtr=_select, with_cod=True)
        if code != 200 or not resp:
            return
        desc = resp['Description']
        parent_key = resp['Parent_Key']
        label_info.setText(f'Найден вид: {desc!r}')
        return {
            'Ref_Key': ref_key,
            'Наименование': desc,
            'Родитель_Ref_Key': parent_key,
        }

    def insert_type_nomen(self, ref_key: str, name: str, parent_ref_key: str, returning: bool = False):
        poki = CFG.Config.place.poki
        resp = CSQ.custom_request_c(
            CFG.Config.project.db_nomen,
            "INSERT INTO ВидыНоменклатуры(Ref_Key, name, Родитель, poki) VALUES (?, ?, ?, ?) RETURNING s_num",
            list_of_lists_c=[ref_key, name, parent_ref_key, poki],
            rez_dict=True
        )
        if returning:
            match resp:
                case [{'s_num': s_num}]:
                    return s_num
                case _:
                    return
        return resp

    def get_all_nomen_types_mes(self, attrs=('*',), error_alert: bool = False):
        sql_select = ','.join(attrs)
        nomen_types_MES = CSQ.custom_request_c(
            CFG.Config.project.db_nomen,
            f'''SELECT {sql_select} FROM ВидыНоменклатуры WHERE comment != "Не найден в 1С"''',
            rez_dict=True
        )
        if not nomen_types_MES:
            error_alert and CQT.msgbox('Не удалось запросить ВидыНоменклатуры в БД МЕС')
            return
        return nomen_types_MES

    def get_nomen_type_from_mes_by_uuid(self, attrs: tuple[str]('*', ), ref_key: str) -> list[dict]:
        attrs = ','.join(attrs)
        return CSQ.custom_request_c(
            CFG.Config.project.db_nomen,
            f'SELECT {attrs} FROM ВидыНоменклатуры WHERE Ref_Key = {ref_key!r}',
            rez_dict=True
        )

    def mark_delete_nomens_by_ref(self, ref_key: str):
        query = f'UPDATE nomen SET На_удаление = 1 WHERE Вид_Ref_Key = {ref_key!r}'
        return CSQ.custom_request_c(CFG.Config.project.db_nomen, query)

    def get_types_nomen_from_1c(self, alert_error_msg: bool = False):
        addit_names = ''
        if CFG.Config.place.poki == 1:
            addit_names = f"""
                    ОБЪЕДИНИТЬ ВСЕ
                    
                    ВЫБРАТЬ
                        ВидыНоменклатуры.Наименование,
                        УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Ссылка),
                        ВидыНоменклатуры.Родитель.Наименование,
                        УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Родитель.Ссылка)
                    ИЗ
                        Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                    ГДЕ
                        ВидыНоменклатуры.Наименование В ("Арматура литейная") 
                    """

        text = f"""ВЫБРАТЬ 
                ВидыНоменклатуры.Наименование КАК Наименование,
                УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Ссылка) КАК Ref_Key,
                ВидыНоменклатуры.Родитель.Наименование КАК Родитель,
                УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Родитель.Ссылка) КАК Родитель_Ref_Key
            ИЗ
                Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
            ГДЕ
                ВидыНоменклатуры.Ссылка В ИЕРАРХИИ
                        (ВЫБРАТЬ ПЕРВЫЕ 1
                            ВидыНоменклатуры.Ссылка КАК Ссылка
                        ИЗ
                            Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                        ГДЕ
                            ВидыНоменклатуры.Наименование = "{CFG.Config.place.Имя}"
                            И ВидыНоменклатуры.ЭтоГруппа = ИСТИНА) 
                И ВидыНоменклатуры.ЭтоГруппа = ЛОЖЬ
                И ВидыНоменклатуры.ПометкаУдаления = ЛОЖЬ
                
                ОБЪЕДИНИТЬ ВСЕ
                
                ВЫБРАТЬ 
                ВидыНоменклатуры.Наименование ,
                УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Ссылка) ,
                ВидыНоменклатуры.Родитель.Наименование ,
                УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Родитель.Ссылка) 
            ИЗ
                Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
            ГДЕ
                ВидыНоменклатуры.Ссылка В ИЕРАРХИИ
                        (ВЫБРАТЬ ПЕРВЫЕ 1
                            ВидыНоменклатуры.Ссылка КАК Ссылка
                        ИЗ
                            Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                        ГДЕ
                            ВидыНоменклатуры.Наименование = "Услуги"
                            И ВидыНоменклатуры.ЭтоГруппа = ИСТИНА) 
                И ВидыНоменклатуры.ЭтоГруппа = ЛОЖЬ
                И ВидыНоменклатуры.ПометкаУдаления = ЛОЖЬ
                
                {addit_names}
                
            УПОРЯДОЧИТЬ ПО
                Родитель, Наименование """
        code, data = APIERP.get_wet_request(text=text)
        if code != 200 or data is None:
            alert_error_msg and CQT.msgbox('Не удалось запросить виды номенклатуры из ERP')
            return
        return data['data']

class GUITypesNomenclature(DATATypesNomenclature):
    def add_by_ref(self, dialog, window):
        ref_dialog = CQT.LinkDialog(window, validate_ref_func=self.check_ref)
        if ref_dialog.exec() == QtWidgets.QDialog.Accepted and ref_dialog.data:
            print("Подтверждён ref:", ref_dialog.data)
            match ref_dialog.data:
                case {'Ref_Key': ref_key, 'Наименование': name, 'Родитель_Ref_Key': parent_ref}:
                    if self.get_nomen_type_from_mes_by_uuid(attrs=('Ref_Key',), ref_key=ref_key):
                        return CQT.msgbox(f'{name} Уже занесен в БД МЕС')
                    resp = self.insert_type_nomen(ref_key, name, parent_ref)
                    self.fill_nomen_by_nomen_type(nomen_type_ref_key=ref_key, window=window) # 22.09.25
                    resp and CQT.msgbox('Успешно')
            dialog.reject()

    def prepare_dialog_from_select_nomen_types(self, data_for_table: list[dict], window):
        dialog = CQT.Dialog_tbl(
            window,
            msg=f'Выбор вида номенклатуры по папке: {CFG.Config.place.Имя!r}.\n Чтобы прикрепить вид по ссылке из 1С нажмите "🔗"',
            dict_or_list=data_for_table,
            ExtendedSelection=False
        )
        dialog.btn3 = QtWidgets.QPushButton("🔗")
        dialog.btn3.clicked.connect(lambda *args: self.add_by_ref(dialog, window))
        dialog.ui.buttonBox.addButton(dialog.btn3, QtWidgets.QDialogButtonBox.ActionRole)
        style = dialog.ui.btn_ok.style()
        stylesheets = dialog.ui.btn_ok.styleSheet()
        size = dialog.ui.btn_ok.size()
        font = dialog.ui.btn_ok.font()
        dialog.btn3.setStyle(style)
        dialog.btn3.setStyleSheet(stylesheets)
        dialog.btn3.setFixedSize(QtCore.QSize(size.height(), size.height()))
        dialog.btn3.setFont(font)
        dialog.btn3.setToolTip('Добавить по ссылке из 1С')
        return dialog

    def get_table_choicer_for_insert_nomen_type(self, window, *args):
        data = self.get_types_nomen_from_1c(alert_error_msg=True)
        nomen_types_mes = self.get_all_nomen_types_mes(attrs=('s_num', 'name', 'Ref_Key'))
        if not nomen_types_mes:
            return
        nomen_by_ref = F.deploy_dict_c(nomen_types_mes, 'Ref_Key')
        data_for_table = []
        for nomen in data:
            ref_key = nomen['Ref_Key']
            if ref_key in nomen_by_ref:
                continue
            data_for_table.append({
                'Наименование': nomen['Наименование'],
                'Родитель': nomen['Родитель'],
                'Родитель_Ref_Key': nomen['Родитель_Ref_Key'],
                'Ref_Key': nomen['Ref_Key'],
            })
        dialog = self.prepare_dialog_from_select_nomen_types(data_for_table, window)
        if dialog.exec():
            result = CQT.get_dict_line_form_tbl(dialog.ui.tbl)
            match result:
                case {'Ref_Key': ref_key, 'Наименование': name, 'Родитель_Ref_Key': parent_ref}:
                    resp = self.insert_type_nomen(ref_key, name, parent_ref)
                    self.fill_nomen_by_nomen_type(nomen_type_ref_key=ref_key, window=window) # 22.09.25
                    resp and CQT.msgbox('Успешно')

    @CPB.progress_decorator # ++22.09.25
    def fill_nomen_by_nomen_type(
            self,
            nomen_type_ref_key: str,
            window = None,
            ref_key_np: str='0135f909-5b65-11ee-84bf-00d861dd2b4a',  # Catalog_ВидыЦен Закупочная цена
            hook_prog_bar=None
    ):
        hook_prog_bar.text('Запрос номенклатуры из 1С')
        query = """
        ВЫБРАТЬ
            ЦеныНоменклатуры25СрезПоследних.Цена КАК Цена,
            ЦеныНоменклатуры25СрезПоследних.Номенклатура.Ссылка КАК НоменклатураСсылка
        ПОМЕСТИТЬ ВТ_Цены
        ИЗ
            РегистрСведений.ЦеныНоменклатуры25.СрезПоследних(, ВидЦены.Ссылка = &ВидЦеныСсылка) КАК ЦеныНоменклатуры25СрезПоследних
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Ссылка)) КАК Ref_Key,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.ВидНоменклатуры.Ссылка)) КАК Вид_Ref_Key,
            Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмерения,
            Номенклатура.Код КАК Код,
            Номенклатура.Наименование КАК Наименование,
            Номенклатура.Артикул КАК Артикул,
            Номенклатура.ПометкаУдаления КАК На_удаление,
            ЕСТЬNULL(ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.СхемаОбеспечения.Ссылка)), НЕОПРЕДЕЛЕНО) КАК СхемаОбеспечения,
            Номенклатура.ВидНоменклатуры.Наименование КАК Вид,
            ЕСТЬNULL(ВТ_Цены.Цена, 0) КАК Закупочная_цена
        ИЗ
            Справочник.Номенклатура КАК Номенклатура
                ЛЕВОЕ СОЕДИНЕНИЕ ВТ_Цены КАК ВТ_Цены
                ПО (ВТ_Цены.НоменклатураСсылка = Номенклатура.Ссылка)
        ГДЕ
            Номенклатура.ВидНоменклатуры = &ВидНоменклатуры
            и Номенклатура.ПометкаУдаления = ЛОЖЬ
        """
        refs = APIERP.Refs_wet(query)

        ref_price_type = APIERP.Ref_wet('ВидЦеныСсылка', 'Справочники.ВидыЦен', ref_key_np)
        ref_nomen_type = APIERP.Ref_wet('ВидНоменклатуры', 'Справочники.ВидыНоменклатуры', nomen_type_ref_key)
        refs.add_ref(ref_price_type)
        refs.add_ref(ref_nomen_type)
        code, data = APIERP.get_wet_request(
            text=query,
            refs=refs
        )
        nomens_from_1c = data['data']
        if not nomens_from_1c:
            return CQT.msgbox('Сервис не смог связаться с 1С')
        hook_prog_bar.set(30)

        hook_prog_bar.text('Поиск связанной номенклатуры в БД МЕС')

        all_nomens = CSQ.custom_request_c(
            CFG.Config.project.db_nomen,
            'SELECT Ref_Key, Вид_Ref_Key FROM nomen WHERE На_удаление != 1',
            rez_dict=True
        )
        if not all_nomens:
            return CQT.msgbox('Бд мес недоступна')
        nomen_by_ref = F.deploy_dict_c(all_nomens, 'Ref_Key')
        hook_prog_bar.set(60)

        hook_prog_bar.text('Запись изменений в БД МЕС')

        logs = []
        unique_key = 'Ref_Key'
        for nomen_1c in nomens_from_1c:
            ref = nomen_1c[unique_key]
            if ref in nomen_by_ref:
                update_template = ','.join(f'{key} = ?' for key in nomen_1c if key != unique_key)
                body = [val for key, val in nomen_1c.items() if key != unique_key]
                query_update = f"""
                    UPDATE nomen SET {update_template} WHERE {unique_key} = {ref!r}
                """
                response = CSQ.custom_request_c(
                    CFG.Config.project.db_nomen,
                    query_update,
                    list_of_lists_c=[body]
                )
                status = 'Обновлено' if response else 'Ошибка обновления'
            else:
                insert_template_keys = ','.join(nomen_1c)
                insert_template_vals = ','.join('?' for _ in nomen_1c)
                query_insert = f"""
                    INSERT INTO nomen({insert_template_keys})VALUES({insert_template_vals})
                """
                response = CSQ.custom_request_c(
                    CFG.Config.project.db_nomen,
                    query_insert,
                    list_of_lists_c=[list(nomen_1c.values())])
                status = 'Создано' if response else 'Ошибка создания'

            logs.append({'Статус': status, **nomen_1c})
        hook_prog_bar.set(90)

        hook_prog_bar.text('Формирование отчета записи')
        hook_prog_bar.close()
        if window is not None:
            CQT.msgboxg_get_table_ok_inf(window, 'Добавлено', logs)
# ---22.09.25


#18.07.25++
class TypesWorkingByDirections:
    """
    Представление таблицы: DB_kplan.виды_по_направлениям
    """
    PK_KEY_FOR_GROUP = 'Пномер'

    # Объемно-календарное-планирование->редактирование позиции->пл_топ.Вид
    # ключ для вызова таблицы подбора наименования по характеристикам
    COMBOBOX_KEY_FOR_NAME_COMPOSE = '...Подобрать наименование...'

    # Настройки редуцирования группы
    COLUMN_KEY_FOR_GROUP_UNPACK = 'etaps.имя_в_виды_по_напр' # Ключ, значение которого будет введено как имя колонки
    COLUMN_VAL_FOR_GROUP_UNPACK = 'коэфф.ratio' # Ключ, значение которого будет введено как значение колонки

    data_for_name_composite = { # ++ 25.07.25
        'КТ': {
            'Тип оборуд.': ['К', 'КВ', 'КИ', 'КВИ', 'КИБ', 'КВБ', 'КВИБ'],
            'Тип поставки': ['ТТ', 'Ч', 'М', 'МЧ'],
            'Исполнение': ['000', '010', '020', '001', '011', '021', '101', '111', '121', '202', '212', '222', '203', '213', '223', '303', '313', '323', '404', '414', 'Прокл', 'Полотно', 'Шнур', 'Уник'],
            'Геометрия': ['Кр', 'Пр', 'КП', 'Бг']
        },
        'БСИ': {
            'Тип оборуд.': ['Трмчх', 'Трмчх нф', 'Трмчх сост', 'Гофра', 'Паллет', 'КЗХ', 'Односл', 'Вышивка'],
            'Тип поставки': ['М','бМ'],
            'Исполнение': ['О', 'бО'],
            'Геометрия': []
        },
        'ПДШ': {
            'Тип оборуд.': ['Подушка'],
            'Тип поставки': [],
            'Исполнение': [],
            'Геометрия': []
        },
        'ВГ': {
            'Тип оборуд.': ['Вставка', 'Лента'],
            'Тип поставки': [],
            'Исполнение': [],
            'Геометрия': []
        },
        'ДО': {
            'Тип оборуд.': ['Поддон', 'Ящик', 'Оснастка', 'Модельная оснастка'],
            'Тип поставки': ['М', 'бМ'],
            'Исполнение': ['Обычный', 'Усиленный', 'Простая', 'Сложная'],
            'Геометрия': ['Кр', 'Пр', 'КП']
        },
        'РФ': {
            'Тип оборуд.': ['Сшивной', 'Сварной'],
            'Тип поставки': ['М', 'бМ'],
            'Исполнение': [],
            'Геометрия': ['Плоский', 'Круглый']
        },
        'ПР': {
            'Тип оборуд.': ['Прочие'],
            'Тип поставки': [],
            'Исполнение': [],
            'Геометрия': []
        },
    }

    def __init__(self):
        self.NAPR_DEYAT = CSQ.custom_request_c(CFG.Config.project.db_kplan,
                                          f"""SELECT Псевдоним, Пномер FROM napravl_deyat WHERE state_on_off = 1 and poki == {CFG.Config.place.poki} OR poki is NULL""",
                                          rez_dict=True)
        self.DICT_NAPR_DEYAT_PSDNAME = F.deploy_dict_c(self.NAPR_DEYAT, 'Псевдоним')
        self.list_vid_po_napr = self.get_old_view_response()
        self.dict_vid_po_napr_by_pk = F.deploy_dict_c(self.list_vid_po_napr, 'Пномер')
        self.dict_vid_po_napr_by_name = F.deploy_dict_c(self.list_vid_po_napr, 'Имя')

    def on_checked(self, tbl, new_status, row: int, column: int, *args):
        tbl.item(row, column).setText(str(int(new_status)))

    @CQT.onerror
    def oform_table_attach(self, nomen_types, tbl, *args):
        column_select = CQT.num_col_by_name_c(tbl, 'Выбрать')
        column_pk = CQT.num_col_by_name_c(tbl, 's_num')
        column_ref = CQT.num_col_by_name_c(tbl, 'Ref_Key') #26.08.25
        column_parent_ref = CQT.num_col_by_name_c(tbl, 'Родитель_Ref_Key')
        nomen_types_split = {nom_type for nom_type in nomen_types.split(';') if nom_type}
        for row_idx in range(tbl.rowCount()):
            s_num = tbl.item(row_idx, column_pk).text()
            checked = s_num in nomen_types_split
            CQT.add_check_box(tbl, row_idx, column_select,
                              conn_func_checked_row_col=self.on_checked,
                              self=tbl,
                              val=checked)
            tbl.item(row_idx, column_select).setText(str(int(checked)))
        if None not in (column_pk, column_ref, column_parent_ref):
            tbl.hideColumn(column_pk)
            tbl.hideColumn(column_ref)
            tbl.hideColumn(column_parent_ref)

    @CQT.onerror
    def get_marked_nomen_types(self, values):
        pks = []
        nomen_types_instance = GUITypesNomenclature()
        for item in values:
            if item['Выбрать'] == '1':
                if not item['s_num']: #26.08.25
                    name = item['Наименование']
                    ref_key = item['Ref_Key']
                    parent_ref = item['Родитель_Ref_Key']
                    s_num = nomen_types_instance.insert_type_nomen(ref_key, name, parent_ref, returning=True)
                    if s_num is None or s_num == False:
                        return CQT.msgbox(f'Не удалось создать ВидНоменклатуры {name!r} в МЕС')
                    nomen_types_instance.fill_nomen_by_nomen_type(ref_key) # 22.09.25
                    pks.append(str(s_num))
                else:
                    pks.append(str(item['s_num']))
        return ';'.join(pks)

    @CQT.onerror
    def on_attach(self, window, row, col, tbl, *args): #26.08.25
        data_nomen_instance = DATATypesNomenclature()
        data_1c = data_nomen_instance.get_types_nomen_from_1c(alert_error_msg=True)
        if not data_1c:
            return
        nomen_types_mes = data_nomen_instance.get_all_nomen_types_mes(attrs=('s_num', #27.10.25 по задаче 100062109
                                                                             'poki',
                                                                             'name',
                                                                             'Ref_Key',
                                                                             'Родитель'), error_alert=True)
        if not nomen_types_mes:
            return
        nomen_by_ref = F.deploy_dict_c(nomen_types_mes, 'Ref_Key') #29.08.25
        selected_nomen_types = ''
        column_types = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры')
        if column_types is not None:
            item = tbl.item(row, column_types)
            if item is not None:
                selected_nomen_types = item.text()
        data_for_table = []
        for nomen in data_1c: #27.10.25 по задаче 100062109
            ref_key = nomen['Ref_Key']
            s_num = ''
            if ref_key in nomen_by_ref:
                nomen_mes = nomen_by_ref.pop(ref_key)
                s_num = nomen_mes['s_num']
            data_for_table.append({
                'Выбрать': '',
                's_num': s_num,
                'Наименование': nomen['Наименование'],
                'Родитель': nomen['Родитель'],
                'Ref_Key': nomen['Ref_Key'],
                'Родитель_Ref_Key': nomen['Родитель_Ref_Key'],
            })
        for key, nomen_mes in nomen_by_ref.items(): #27.10.25 по задаче 100062109
            if CFG.Config.place.poki == F.valm(nomen_mes['poki']):
                data_for_table.append({
                    'Выбрать': '',
                    's_num': nomen_mes['s_num'],
                    'Наименование': nomen_mes['name'],
                    'Родитель': '',
                    'Ref_Key': key,
                    'Родитель_Ref_Key': nomen_mes['Родитель'],
                })
        selected_nomen_types = ''
        column_types = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры')
        if column_types is not None:
            item = tbl.item(row, column_types)
            if item is not None:
                selected_nomen_types = item.text()
        result = CQT.msgboxg_get_table(
            self=window,
            msg='Выбор видов номенклатуры',
            dict_or_list=data_for_table,
            func_oform_tbl=lambda table: self.oform_table_attach(selected_nomen_types, table),
            func_validate=self.get_marked_nomen_types
        )
        if isinstance(result, str) and len(result.split(';')) > 0:
            column_types = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры')
            if column_types is not None:
                item = tbl.item(row, column_types)
                if item is not None:
                    item.setText(result)
                    return True
        return False

    def compose_vals(self, tbl, *args):
        napr = self.combo_root.currentText()
        if napr not in self.DICT_NAPR_DEYAT_PSDNAME:
            return CQT.msgbox(f'Не найдено направление {napr!r}')
        val = '-'.join(combo.currentText() for combo in self.combo_others if combo.currentText())
        col_compose = CQT.num_col_by_name_c(tbl, 'compose')
        if col_compose is not None:
            tbl.item(0, col_compose).setText(val)

    @CQT.onerror
    def oform_table_for_name_composite(self, tbl: QtWidgets.QTableWidget, window):
        dynamic_fields = []
        for key, val in self.data_for_name_composite.items():
            dynamic_fields.extend(val.keys())
            break
        column_direction = CQT.num_col_by_name_c(tbl, 'Направление')
        self.combo_root = CQT.add_combobox(table=tbl, j=column_direction, list=self.data_for_name_composite.keys(),
                                            conn_func=self.compose_vals, self=tbl)
        self.combo_root.currentTextChanged.connect(self.update_other_combos)

        self.combo_others = [
            CQT.add_combobox(table=tbl, j=CQT.num_col_by_name_c(tbl, field), conn_func=self.compose_vals, self=tbl)
            for field in dynamic_fields
            if CQT.num_col_by_name_c(tbl, field) is not None
        ]
        self.tbl_types = QtWidgets.QTableWidget()
        CQT.add_btn(
            item=tbl,
            i=0,
            j=CQT.num_col_by_name_c(tbl, 'Подобрать виды номенклатур'),
            text='Подобрать виды номенклатур',
            conn_func_checked_row_col=self.on_attach,
            self=window,
            cell_val=tbl
        )
        column_types = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры') #26.08.25
        column_compose = CQT.num_col_by_name_c(tbl, 'compose')
        if column_types is not None:
            tbl.setColumnHidden(column_types, True)
        if column_compose is not None:
            tbl.setColumnHidden(column_compose, True)

    def blink_existing_type(self, val, tbl, column_check, msg: str = 'Вид уже существует!'):
        QtWidgets.QApplication.processEvents()
        for row_idx in range(tbl.rowCount()):
            item = tbl.item(row_idx, column_check)
            txt = item.text()
            if txt == val:
                tbl.scrollToItem(item)
                return CQT.blink_obj_c(tbl.parentWidget(), 4, item, msg)
        return

    def check_fill_nomen_types(self, parent_tbl, btn, dialog, tbl, *args):
        if dialog.ui.buttonBox.buttonRole(btn) == QtWidgets.QDialogButtonBox.NoRole:
            return dialog.reject()
        column_nomen_types_btn = CQT.num_col_by_name_c(tbl, 'Подобрать виды номенклатур')
        column_nomen_types = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры') #26.08.25
        text = tbl.item(0, column_nomen_types).text()
        nomen_types = [nomen_type for nomen_type in text.split(';') if nomen_type != '']
        row = CQT.get_dict_line_form_tbl(tbl, 0)
        if row['compose'] in self.dict_vid_po_napr_by_name:
            return dialog.accept()
        if len(nomen_types) < 1:
            btn_cell = tbl.cellWidget(0, column_nomen_types_btn)
            return CQT.blink_obj_c(dialog, 2, btn_cell, msg='Для создания необходимо привязать вид номенклкатуры')
        return dialog.accept()

    def insert_technological_type(self, type_name: str, napr_pk = '', nomen_types: str = ''):
        result = CSQ.custom_request_c(
            CFG.Config.project.db_kplan,
            'INSERT INTO виды_по_направлению(Направл, Имя, Выборка) VALUES(?, ?, ?) RETURNING Пномер',
            list_of_lists_c=[napr_pk, type_name, 0],
            rez_dict=True,
        )
        new_pk = None
        match result:
            case [{'Пномер': result}]:
                new_pk = result
        if new_pk is None:
            return CQT.msgbox(f'Не удалось сохранить вид: {nomen_types!r}')
        result_nomen = CSQ.custom_request_c(
            CFG.Config.project.db_nomen,
            'INSERT INTO ТехнологическиеВиды(Пномер, ВидыНоменклатуры) VALUES(?, ?)',
            list_of_lists_c=[[new_pk, nomen_types]])
        if not result_nomen:
            CSQ.custom_request_c(CFG.Config.project.db_kplan,
                                 f'DELETE FROM виды_по_направлению WHERE Пномер = {new_pk}')
            CSQ.custom_request_c(CFG.Config.project.db_nomen,
                                 f'DELETE FROM ТехнологическиеВиды WHERE Пномер = {new_pk}')
            return False
        return True

    @CQT.onerror
    def get_table_for_name_composite(self, window, parent_tbl) -> tuple[str | None, bool]:
        dynamic_fields = []
        for key, val in self.data_for_name_composite.items():
            dynamic_fields.extend(val.keys())
            break
        headers = ["Направление", *dynamic_fields, 'Подобрать виды номенклатур', 'ВидыНоменклатуры', 'compose'] #26.08.25
        row = [''] * len(headers)
        value = CQT.msgboxg_get_table(
            self=window,
            msg='Составление имени',
            dict_or_list=[headers, row],
            btn0_name='Подтвердить',
            func_oform_tbl=lambda tbl: self.oform_table_for_name_composite(tbl, window),
            func_btn0=lambda *args: self.check_fill_nomen_types(parent_tbl, *args),
            show_filtr=False,
            not_standart_close=True,
            ExtendedSelection=False
        )
        if not value:
            return
        napr = self.combo_root.currentText()
        if napr not in window.Data_plan.DICT_NAPR_DEYAT_PSDNAME:
            return CQT.msgbox(f'Не найдено направление {napr!r}')
        napr_pk = self.DICT_NAPR_DEYAT_PSDNAME[napr]
        val = value['compose']
        nomen_types = value['ВидыНоменклатуры'] #26.08.25
        exists = True
        if val not in window.Data_plan.DICT_VID_PO_NAPR_NAME:
            result = CSQ.custom_request_c(
                CFG.Config.project.db_kplan,
'INSERT INTO виды_по_направлению(Направл, Имя, Выборка) VALUES(?, ?, ?) RETURNING Пномер',
                list_of_lists_c=[napr_pk, val, 0],
                rez_dict=True,
            )
            new_pk = None
            match result:
                case [{'Пномер': result}]:
                    new_pk = result
            if new_pk is None:
                return CQT.msgbox(f'Не удалось сохранить вид: {val!r} По направлению: {napr}')
            result_nomen = CSQ.custom_request_c(
                CFG.Config.project.db_nomen,
                'INSERT INTO ТехнологическиеВиды(Пномер, ВидыНоменклатуры) VALUES(?, ?)',
                list_of_lists_c=[[new_pk, nomen_types]])
            if not result_nomen:
                CSQ.custom_request_c(CFG.Config.project.db_kplan,
                f'DELETE FROM виды_по_направлению WHERE Пномер = {new_pk}')
                CSQ.custom_request_c(CFG.Config.project.db_nomen,
                f'DELETE FROM ТехнологическиеВиды WHERE Пномер = {new_pk}')
                result = None
            if not result:
                return CQT.msgbox(f'Не удалось сохранить вид: {val!r} По направлению: {napr}')
            exists = False
        window.Data_plan.VID_PO_NAPR = self.get_old_view_response()
        window.Data_plan.DICT_VID_PO_NAPR = F.deploy_dict_c(window.Data_plan.VID_PO_NAPR, 'Пномер')
        window.Data_plan.DICT_VID_PO_NAPR_NAME = F.deploy_dict_c(window.Data_plan.VID_PO_NAPR, 'Имя')
        return val, exists

    def check_ratio_exists(self, type_id: int, etaps_id: int):
        return CSQ.custom_request_c(
            CFG.Config.project.db_kplan,
            'SELECT ratio, Пномер FROM коэфф_норм_этапов_по_видам_направлений WHERE виды_по_напр_id = ? AND etaps_id = ?',
            rez_dict=True,
            one=True,
            list_of_lists_c=[[type_id, etaps_id]]
        )

    def update_ratio_by_etap_pk(self, etap_id: int, type_id: int, ratio: float):
        resp_obj = self.check_ratio_exists(type_id, etap_id)
        log = f"Неудалось применить значение значение: {ratio}"
        if resp_obj and 'ratio' in resp_obj:
            previous_ratio = resp_obj['ratio']
            pk = resp_obj['Пномер']
            if str(previous_ratio) == str(ratio):
                return 'Данные не изменились'
            query = f"""
                UPDATE коэфф_норм_этапов_по_видам_направлений 
                SET ratio = {ratio}
                WHERE Пномер = {pk}
            """
            if CSQ.custom_request_c(CFG.Config.project.db_kplan, query):
                log = f"Значение обновлено было: {previous_ratio} Стало: {ratio}"
        else:
            query = """
                INSERT INTO коэфф_норм_этапов_по_видам_направлений(etaps_id, виды_по_напр_id, ratio)
                VALUES(?, ?, ?)
            """
            if CSQ.custom_request_c(CFG.Config.project.db_kplan, query, list_of_lists_c=[[etap_id, type_id, ratio]]):
                log = f"Применено новое значение: {ratio}"
        return log

    def on_click_create_type(self, parent, tbl, *args):
        result = self.get_table_for_name_composite(parent, parent_tbl=tbl)
        if not isinstance(result, tuple) or not len(result) == 2:
            return
        val, exists = result
        column_name = CQT.num_col_by_name_c(tbl, 'Имя')
        if not exists:
            list_types = self._get_list_types_data_for_on_table()
            CQT.fill_wtabl(list_types, tbl)
            self.decor_change_working_type_table(parent, tbl)
            self.blink_existing_type(val, tbl, column_name, msg='Вид успешно создан!')
            return val
        for row_idx in range(tbl.rowCount()):
            item = tbl.item(row_idx, column_name)
            txt = item.text()
            if txt == val:
                tbl.scrollToItem(item)
                return CQT.blink_obj_c(tbl.parentWidget(), 4, item, 'Вид уже существует!')
        return

    def get_dict_working_types_by_pk(self):
        list_vid_po_napr = self.get_old_view_response()
        dict_vid_po_napr = F.deploy_dict_c(list_vid_po_napr, 'Пномер')
        return dict_vid_po_napr

    # ---- Изменить вид по направлению в указанной таблице -----
    def change_vid_po_napr(self, window, target_table: QtWidgets.QTableWidget, row: int, column: int):
        dict_vid_po_napr = self.get_dict_working_types_by_pk()
        current_type = target_table.item(row, column).text()
        current_type_text = ''
        if F.is_numeric(current_type) and int(current_type) in dict_vid_po_napr:
            current_type_text = dict_vid_po_napr[int(current_type)]['Имя']

        widget = CQT.add_interactive_label(target_table, row=row, column=column,
                                           text=current_type_text, txt_cut=14, mark_not_changed_item=False)
        widget.add_button(
            txt_button='Редактировать',
            on_clicked=self.on_click_change_working_type_btn,
            img_path='btn_pl_edit_poz',
            cell_val=window
        )

    def decor_change_working_type_table(self, parent, tbl: QtWidgets.QTableWidget, *args):
        add_new_type_column = CQT.num_col_by_name_c(tbl, 'Имя')
        nomen_types_column = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры')
        if tbl.item(0, add_new_type_column).text() == '<add_new>':
            CQT.add_btn(tbl, 0, add_new_type_column, text='Создать вид',
                        conn_func_checked_row_col=lambda *args: self.on_click_create_type(parent, tbl, *args))
        # if nomen_types_column is not None: #26.08.25
        #     tbl.hideColumn(nomen_types_column)
        tbl.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QtWidgets.QTableWidget.SelectionMode.SingleSelection)

    def _get_list_types_data_for_on_table(self):
        list_types = []

        if CFG.Config.place.poki == 1:
            list_types.append({'Пномер': '-', 'Имя': '<add_new>', 'ВидыНоменклатуры': ''})
        dict_vid_po_napr = self.get_dict_working_types_by_pk()
        for key in dict_vid_po_napr.keys():
            if key != 1:
                list_types.append({
                    'Пномер': key,
                    'Имя': dict_vid_po_napr[key]['Имя'],
                    'ВидыНоменклатуры': dict_vid_po_napr[key]['НомерВидаНоменДляСозданияРесЕРП'],
                })
        return list_types

    def check_selected_type(self, window, btn: QtWidgets.QPushButton, dialog: CQT.Dialog_tbl, tbl, *args):
        if dialog.ui.buttonBox.buttonRole(btn) == QtWidgets.QDialogButtonBox.NoRole:
            return dialog.reject()
        current_row = tbl.currentRow()
        row = CQT.get_dict_line_form_tbl(tbl, tbl.currentRow())
        if not isinstance(row, dict):
            return dialog.accept()
        if row['ВидыНоменклатуры']:
            return dialog.accept()
        if not CQT.msgboxgYN('У данного вида по направлению не заполнены виды номенклатур. Заполнить?'):
            return dialog.reject()
        column_types = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры')
        column_pk = CQT.num_col_by_name_c(tbl, 'Пномер')
        if None in (column_types, column_pk):
            return dialog.reject()
        if not self.on_attach(window, current_row, column_types, tbl):
            return dialog.reject()
        nomen_types = tbl.item(current_row, column_types).text()
        pk_types = tbl.item(current_row, column_pk).text()
        if not F.is_numeric(pk_types) or int(pk_types) not in self.dict_vid_po_napr_by_pk:
            return dialog.reject()
        if isinstance(nomen_types, str) and nomen_types.strip() != '':
            resp = CSQ.custom_request_c(
                CFG.Config.project.db_nomen,
                'UPDATE ТехнологическиеВиды SET ВидыНоменклатуры = ? WHERE Пномер = ?',
                list_of_lists_c=[[nomen_types, pk_types]]
            )
            if resp:
                CQT.msgbox('Виды успешно привязаны')
                return dialog.accept
        return dialog.reject()

    def on_click_change_working_type_btn(self, widget, row, column, parent, *args):
        dict_vid_po_napr = self.get_dict_working_types_by_pk()
        list_types = self._get_list_types_data_for_on_table()
        result = CQT.msgboxg_get_table(parent, 'Выберите вид по направлению', list_types,
                                       func_oform_tbl=lambda *args: self.decor_change_working_type_table(parent, *args),
                                       func_btn0=lambda *args: self.check_selected_type(parent, *args),
                                       not_standart_close=True,
                                       ExtendedSelection=False)
        if not isinstance(result, dict):
            return
        new_pk = result['Пномер']
        new_name = result['Имя']
        widget.table.item(row, column).setText(new_pk)
        widget.label.setText(new_name)
        if not F.is_numeric(new_pk) or int(new_pk) not in dict_vid_po_napr:
            return
        widget.label.setText(new_name)

    def update_other_combos(self, root_key):
        if root_key in self.data_for_name_composite:
            for i, key in enumerate(self.data_for_name_composite[root_key].keys()):
                combo = self.combo_others[i]
                combo.setEnabled(True)
                combo.clear()
                combo.addItem("")
                combo.addItems(self.data_for_name_composite[root_key][key])
        else:
            for combo in self.combo_others:
                combo.clear()
                combo.addItem("")
                combo.setEnabled(False)

    # -- 25.07.25
    def get_table_for_select_type(self, poz: Pozition, window, *args, **kwargs): #++ 21.07.25
        types = self.get_old_view_response()
        result = []
        for item in types:
            type_pk = item['Пномер']
            type_name = item['Имя']
            if not type_name:
                continue
            napr_nickname = item['napravl_deyat.Псевдоним']
            napr_name = item['napravl_deyat.Имя']
            result.append({
                'Пномер': type_pk,
                'Вид': type_name,
                'Наименование направления': napr_name,
                'Псевдоним направления': napr_nickname
            })
        if CQT.msgboxgYN(
                f'Для КПЛ: {poz.Пномер} не заполнен "пл_топ.Вид"',
                btn0_name='Продолжить без вида',
                btn1_name='Заполнить вид'
        ):
            return True
        answer = CQT.msgboxg_get_table(
            window,
            btn0_name='Записать',
            msg=f'Выберите вид по направлению',
            dict_or_list=result,
            ExtendedSelection=False,
            selectRows=True
        )
        if not answer:
            return
        new_type_pk = answer.get('Пномер')
        new_type = answer.get('Вид')
        if not new_type_pk:
            return
        if not CQT.msgboxgYN(f'Вид: {new_type!r} будет записан в "пл_топ.Вид" КПЛ: {poz.Пномер}. Продолжить?'):
            return
        poz.set_new_type_by_direction(new_type_pk)
        confirm_change_type = poz.dict_tables['пл_топ']['Вид']
        if confirm_change_type == 1:
            return
        msg_b24_by_poz_action = Msg_b24(CFG.Config.project.db_kplan,
                                        CFG.Config.project.db_naryad,
                                        db_resxml=CFG.Config.project.db_resxml,
                                        db_users=CFG.Config.project.db_users,
                                        nom_kpl=poz.Пномер)
        msg_b24_by_poz_action.send_msg(type_msg='recalc_time_technolog')
        return True #-- 21.07.25

    def get_old_view_response(self):
        poki = CFG.Config.place.poki
        query = f"""
                    SELECT
                        виды_по_направлению.Пномер as "{self.PK_KEY_FOR_GROUP}",
                        виды_по_направлению.Имя as "Имя",
                        виды_по_направлению.Выборка as "Выборка",
                        виды_по_направлению.кг_на_пост_см as "кг_на_пост_см",
                        виды_по_направлению.vneplan_percent as "vneplan_percent",
                        виды_по_направлению.Утверждены_нормы as "Утверждены_нормы",
                        виды_по_направлению.Направл as "Направл",
                        виды_по_направлению.ВозможностьСозданияНоменМеталоармДляСозданияРесЕРП as "ВозможностьСозданияНоменМеталоармДляСозданияРесЕРП",
                        ТехнологическиеВиды.Примечание as "Примечание",
                        ТехнологическиеВиды.ВидыНоменклатуры as "НомерВидаНоменДляСозданияРесЕРП",
                        коэфф.ratio as "коэфф.ratio",
                        etaps.имя_в_виды_по_напр as "etaps.имя_в_виды_по_напр",
                        napravl_deyat.Имя as 'napravl_deyat.Имя',
                        napravl_deyat.Псевдоним as 'napravl_deyat.Псевдоним'
                    FROM виды_по_направлению
                     LEFT JOIN коэфф_норм_этапов_по_видам_направлений коэфф ON коэфф.виды_по_напр_id = виды_по_направлению.Пномер
                     LEFT JOIN etaps ON etaps.s_num = коэфф.etaps_id
                    INNER JOIN napravl_deyat ON виды_по_направлению.Направл = napravl_deyat.Пномер
                    LEFT JOIN ТехнологическиеВиды ON ТехнологическиеВиды.Пномер = виды_по_направлению.Пномер
                    WHERE napravl_deyat.poki = {poki} OR napravl_deyat.poki IS NULL
            """
        db_result = CSQ.custom_request_c(
            CFG.Config.project.db_kplan,
            query,
            rez_dict=True,
            attach_dbs=(CFG.Config.project.db_naryad, CFG.Config.project.db_nomen)
        )
        if not db_result:
            return
        grouped_data = self.__group_by(db_result, 'Пномер')
        return self.__unpack_groups_on_column(
            grouped_data,
            self.COLUMN_KEY_FOR_GROUP_UNPACK,
            self.COLUMN_VAL_FOR_GROUP_UNPACK
        )

    def __group_by(self, collection, key: str):
        """Формирование структуры {unique_key: [groups...]}"""
        groups = {}
        for item in collection:
            groups.setdefault(item[key], []).append(item)
        return groups

    def __unpack_groups_on_column(self, grouped_collection: dict[int, list], column_key: str, value_key: str):
        """
        Редуцирование горизонтальных значений группы по
        Из каждого элемента группы берется:
        * значение по ключу @column_key, которое будет выступать колонкой для агрегата.
        * значение по ключу @value_key, которое будет выступать значением колонки для агрегата.
        """
        result = []
        for group_key, group in grouped_collection.items():
            item = {self.PK_KEY_FOR_GROUP: group_key}
            for el in group:
                if column_key in el and value_key in el:
                    key_for_result = el.pop(column_key)
                    val_for_result = el.pop(value_key)
                    if key_for_result is not None and val_for_result is not None:
                        item[key_for_result] = val_for_result
                for key, val in el.items():
                    if key != column_key and key != value_key:
                        item[key] = val
            result.append(item)
        return result

# +++ 25.01.2026
def get_start_stop_journal_pairs(
        ex_fio: str | list[str] = None,
        num_naryad: int | list[int] = None,
        between_start_datetime: str = None,
        between_stop_datetime: str = None,
):
    """Выдает выборку записей журнала в разрезе старта + ближайшего финиша/паузы,
         где одна строка состоит из:
            - Старт наряда (запись со статусом Начат)
            - Ближайший финиш/пауза наряда (запись со статусом Приостановлен/Завершен, текущего "отрезка")
        С полями:
            - Номер наряда
            - ФИО исполнителя
            - Пномер старта
            - Пномер паузы/финиша
            - Дата старта
            - Дата паузы/финиша
            - Статус паузы/финиша

    CMS.get_start_stop_journal_pairs(between_start_datetime='2025-12-05', between_stop_datetime='2025-12-06')
    """
    where = ""
    journal_where = ""
    if between_start_datetime is not None:
        where += f" AND (datetime(f.start_dt) >= datetime({between_start_datetime!r}) OR datetime(f.end_dt) >= datetime({between_start_datetime!r}))"
    if between_stop_datetime is not None:
        where += f" AND (datetime(f.start_dt) <= datetime({between_stop_datetime!r}) OR datetime(f.end_dt) <= datetime({between_stop_datetime!r}))"
    if ex_fio or num_naryad:
        lst = []
        if num_naryad is not None:
            if isinstance(num_naryad, (int, str)):
                lst.append(f" j.Номер_наряда = {num_naryad}")
            else:
                pk_joined = ','.join(str(num) for num in num_naryad)
                lst.append(f" j.Номер_наряда IN ({pk_joined})")
        if ex_fio is not None:
            if isinstance(ex_fio, str):
                lst.append(f" j.ФИО = {ex_fio!r}")
            else:
                fio_joined = ','.join(repr(fio) for fio in ex_fio)
                lst.append(f" j.ФИО IN ({fio_joined})")
        journal_where = 'WHERE ' + ' AND '.join(lst)
    query = f"""
    WITH ordered AS (
              SELECT
                j.*,
                SUM(CASE WHEN j.Статус = 'Начат' THEN 1 ELSE 0 END)
                  OVER (PARTITION BY j.ФИО, j.Номер_наряда ORDER BY j.Дата, j.Пномер) AS frag_id
              FROM jurnal j
              {journal_where}
            ),
            frag AS (
              SELECT
                ФИО,
                Номер_наряда,
                frag_id,
                MIN(CASE WHEN Статус = 'Начат' THEN Пномер END) AS start_pnomer,
                MIN(CASE WHEN Статус = 'Начат' THEN Дата END)   AS start_dt,
                MIN(CASE WHEN Статус IN ('Приостановлен', 'Завершен') THEN Пномер END) AS end_pnomer,
                MIN(CASE WHEN Статус IN ('Приостановлен', 'Завершен') THEN Дата END)   AS end_dt,
                MIN(CASE WHEN Статус = 'Начат' THEN Минут_выгружено_ЕРП END)   AS Минут_выгружено_ЕРП
              FROM ordered
              WHERE frag_id > 0
              GROUP BY ФИО, Номер_наряда, frag_id
            )
            SELECT
              f.start_pnomer,
              f.end_pnomer,
              f.start_dt,
              f.end_dt,
              e.Статус AS end_status,
                e.ФИО as ФИО,
                f.Номер_наряда AS "Номер_наряда",
              ROUND((JULIANDAY(f.end_dt) - JULIANDAY(f.start_dt)) * 24 * 60, 2) AS duration_min,
              f.Минут_выгружено_ЕРП as Минут_выгружено_ЕРП
            FROM frag f
                JOIN jurnal e ON e.Пномер = f.end_pnomer
            WHERE f.start_pnomer IS NOT NULL
              AND f.end_pnomer IS NOT NULL
        {where}
            ORDER BY f.start_dt;
    """
    return CSQ.custom_request_c(CFG.Config.project.db_naryad,
                         query, rez_dict=True, attach_dbs=(CFG.Config.project.db_users))
