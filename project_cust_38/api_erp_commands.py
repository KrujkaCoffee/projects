import datetime
import functools
import pprint
import requests
import logging
from subprocess import call as subprocess_call
import json as JS
import base64
import hashlib
import sys
import json

import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

USER_ERP = 'mes_user'
PASS_ERP = '89Luham'

USER_DO = 'mes_user'
PASS_DO= '89Luham'


HOSTNAME_LOCAL_MES = False
PORT_MES = 20011
if HOSTNAME_LOCAL_MES: #"POW-ING22":
    HOST_MES = '192.168.14.71'# AG local
else:
    HOST_MES = '192.168.50.44'# server

class _ImportDb():
    def parce_row_dict(self,item:dict):
        attrs = F.get_all_attrs_with_properties(self,include_private=True)
        for key,val in item.items():
            fix_key = str(key).replace(".", "_")
            if fix_key not in attrs:
                print(f'class {self.__class__.__name__} ImportDbRow attr not declared :{fix_key}' )
            exec(f'self.{fix_key} = val')

    def __repr__(self):
        return (f"{', '.join([f'"{k}" : {v if F.is_numeric(v) else f'"{v}"'}' for k,v in self.__dict__.items()])}")

class Ref_wet():

    def __init__(self,name_var:str, path_conf_1c:str, ref_key:str):
        """
        
        :param name_var: 
        :param path_conf_1c: 'Документы.ЗаказПоставщику'
        :param ref_key: 
        """
        if '&' in name_var:
            raise ValueError(f'В name_var не должно быть `&`')
        if not F.is_unique_identifier(ref_key):
            raise ValueError(f'Некорректный UUID: {ref_key} для {name_var}')
        self.name_var:str = name_var
        self.path_conf_1c:str = path_conf_1c
        self.ref_key:str = ref_key
        

class Refs_wet():
    """
    refs = APIERP.Refs_wet(text)
            ref_obj = APIERP.Ref_wet('ВиртуальныйЗаказПоставщику', 'Документы.ЗаказПоставщику', ref)
            ref_obj2 = APIERP.Ref_wet('Ссылка', 'Документы.ЗаказПоставщику', ref)
            refs.add_ref(ref_obj)
            refs.add_ref(ref_obj2)
    """
    def __init__(self,text_req:str):
        self.refs:dict = dict()
        self.text_req:str = text_req
    
    def add_ref(self,ref_wet:Ref_wet):
        if f'&{ref_wet.name_var}' not in self.text_req:
            raise ValueError(f'&{ref_wet.name_var} not in self.text_req')
        
        self.refs[ref_wet.name_var] =  {'путь':ref_wet.path_conf_1c,'уид': ref_wet.ref_key}
        
    

def patch_state_doc_znpr(ref_key:str,name_obj:str,dict_data:dict, erp_base_name:str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    dict_data["_RefKeyDoc"] =ref_key
    dict_data["_NameDoc"] = name_obj
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/factexp/v1/trdz/'
    response = requests.patch(url, data=JS.dumps(dict_data), headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    return response.status_code, F.convert_binary_to_data(response.content)

def post_kty_json(json_data:dict, erp_base_name:str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/factexp/v1/kty/'
    response = requests.post(url, json=json_data, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    data_str = F.convert_binary_to_data(response.content)
    try:
        data = json.loads(data_str)
    except:
        data = []
    return response.status_code, data

def post_trdz_json(json:dict, erp_base_name:str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/factexp/v1/trdz/'
    response = requests.post(url, json=json, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    return response.status_code, F.convert_binary_to_data(response.content)


def delete_trdz_json(json:list, erp_base_name:str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/factexp/v1/trdz/'
    response = requests.delete(url, json=json, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    return response.status_code, F.convert_binary_to_data(response.content)



def get_nomen(uid='all',erp_base_name:str = 'ERP_Audit'):#TEST
    uid = '3cdfb37a-bee5-11e7-80cb-4ccc6a67082d'#TEST UID!!!!!!!!!
    headers = dict(Accept='application/json')
    params = dict()
    if uid == '':
        print('err uid val')
        return
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/sysexchange/v1/nomen/{uid}/?senttomes=true&carddoccreated=false'
    response = requests.get(url, json= {'d':3}, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    return response.status_code, JS.loads(F.convert_binary_to_data(response.content))

def patch_nomen(erp_base_name:str = 'ERP_Audit'):
    uid = '3cdfb37a-bee5-11e7-80cb-4ccc6a67082d'
    dict_data = dict()
    headers = dict(Accept='application/json')
    params = dict()
    dict_data["senttomes"] = 'True'
    dict_data["carddoccreated"] = 'false'
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/sysexchange/v1/nomen/{uid}/'
    response = requests.patch(url, data=JS.dumps(dict_data), headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    return response.status_code, F.convert_binary_to_data(response.content)


def clear_res_json(json:dict, erp_base_name:str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/resspec/v1/clear_res/'
    response = requests.patch(url, json=json, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    answ = JS.loads(F.convert_binary_to_data(response.content))
    if not isinstance(answ,dict):
        if response.status_code == 200:
            answ = {"Ошибки": [],
                    "ЕстьОшибки": False,
                    "Код": answ}
        else:
            answ = {"Ошибки":answ,
                "ЕстьОшибки":True,
                "Код":None}

    return response.status_code, answ

def delete_res_json(json:dict, erp_base_name:str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/resspec/v1/delete_res/'
    response = requests.patch(url, json=json, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    answ = JS.loads(F.convert_binary_to_data(response.content))
    if not isinstance(answ,dict):
        if response.status_code == 200:
            answ = {"Ошибки": [],
                    "ЕстьОшибки": False,
                    "Код": answ}
        else:
            answ = {"Ошибки":answ,
                "ЕстьОшибки":True,
                "Код":None}

    return response.status_code, answ

def post_res_json(json:dict, erp_base_name:str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/resspec/v1/make_res/'
    response = requests.post(url, json=json, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    try:
        answ = JS.loads(F.convert_binary_to_data(response.content))
    except:
        answ = F.convert_binary_to_data(response.content)
    if not isinstance(answ,dict):
        answ = {"Ошибки":answ,
                "ЕстьОшибки":True,
                "Код":None}

    return response.status_code, answ


def get_meta(erp_base_name: str = 'ERP',path: str = 'Документы.ЗаказКлиента') -> tuple[int, dict]:
    response = None
    try:
        headers = dict(Accept='application/json')
        url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/sysexchange/v1/metadata/none'
        json = {"path":path}
        response = requests.get(url, headers=headers, params=json, auth=(USER_ERP, PASS_ERP), timeout=26)
        if response.status_code == 200:
            return response.status_code, JS.loads(F.convert_binary_to_data(response.content))
        else:
            return response.status_code, None
    except Exception as e:
        logger.warning('Ошибка при валидации ответа 1С ' + str(e))
        return False
    return False


def ping_http_services(erp_base_name: str = 'ERP') -> bool:
    response = None
    try:
        headers = dict(Accept='application/json')
        url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/sysexchange/v1/ping/pong'
        response = requests.get(url, headers=headers, auth=(USER_ERP, PASS_ERP), timeout=26)
        response.raise_for_status()
    except Exception as e:
        logger.warning('Сервер 1С недоступен')
        if response and response.status_code == 404:
            logger.warning('HTTP Сервисы 1С не опубликованы')
        return False
    return True


def ping_http_services_decorator(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not ping_http_services():
            logger.warning(f'Вызов {fn.__name__!r} пропущен т.к. http сервисы 1С недоступны')
            return None
        return fn(*args, **kwargs)
    return wrapper


def is_validate_wet_response(api_response: tuple[int, dict | None]) -> bool:
    try:
        code, response = api_response
        if code == 200 and response is not None and response['data'] is not None:
            return True
    except Exception as e:
        logger.warning('Ошибка при валидации ответа 1С ' + str(e))
        return False
    return False


def get_enum(name_enum:str, erp_base_name: str = 'ERP'):
    headers = dict(Accept='application/json')
    params = dict()
    if name_enum == '':
        print('err name_enum val')
        return
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/mes/sysexchange/v1/enumeration/{name_enum}'
    response = requests.get(url, json={}, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    if response.status_code == 200:
        return response.status_code, JS.loads(F.convert_binary_to_data(response.content))
    else:
        return response.status_code, None

def hash_data_for_api(dict_data:dict)->str:
    return  F.hash_data(dict_data)

class Autentication1C:
    def __init__(self, base:CFG.Erp_base, login:str, password:str,rootURL:str ):
        self.base:CFG.Erp_base = base
        self.login:str = login
        self.password:str = password
        self.rootURL:str = rootURL#/ru_RU/hs/mes/sysexchange/v1/wet_request/none

def get_wet_request(text: str, refs: Refs_wet | None = None, lazy_method_huours=0, **kwargs):
    return _get_wet_request_base(text=text, refs=refs, lazy_method_huours=lazy_method_huours,
                         aut = Autentication1C(CFG.Config.user_config.ERP_base, USER_ERP,PASS_ERP,
                                               f'/ru_RU/hs/mes/sysexchange/v1/wet_request/none'
                                               ), kwargs=kwargs)

def get_wet_request_DO(text: str, refs: Refs_wet | None = None, lazy_method_huours=0, **kwargs):
    return _get_wet_request_base(text=text, refs=refs, lazy_method_huours=lazy_method_huours,
                         aut = Autentication1C(CFG.Config.user_config.DO_base, USER_DO,PASS_DO,
                                               f'/ru_RU/hs/MIE/contract/v1/none'
                                               ), kwargs=kwargs)

def _get_wet_request_base(text: str, refs: Refs_wet | None = None, lazy_method_huours=0, aut: Autentication1C = None,
                         **kwargs):
    start = F.now('')
    print()
    print(f'---------------')
    print(f'{start} wet_req start: {text}')
    def tmp_dir():
        ima_module = F.name_of_executable_file_c().split('.')[0]
        if F.existence_file_c(F.sep().join([F.put_po_umolch(), 'mes_tmp'])) == False:
            F.create_dir_c(F.sep().join([F.put_po_umolch(), 'mes_tmp']))
        if F.existence_file_c(F.sep().join([F.put_po_umolch(), 'mes_tmp', ima_module])) == False:
            F.create_dir_c(F.sep().join([F.put_po_umolch(), 'mes_tmp', ima_module]))
        return F.sep().join([F.put_po_umolch(), 'mes_tmp', ima_module])

    def save_tmp_stukt(data, name):
        puth_name = tmp_dir() + F.sep() + name + '.pickle'
        F.save_file_pickle(puth_name, data)

    def load_tmp_stukt(ima, default_val=None):
        puth_name = tmp_dir() + F.sep() + ima + '.pickle'
        if F.existence_file_c(puth_name) == True:
            val = F.load_file_pickle(puth_name)
            return val
        return default_val

    BASE_NAME_TMP_STUKT = "lazy_wet_request"

    def add_data_db(db_files: str, fl_naid_lazy: bool, sum_hash: str, file, description, file_hash, time):
        size = sys.getsizeof(file)
        new_file_hash = hashlib.md5(F.to_binary_pickle(file)).hexdigest()
        fl_upd = True
        if not fl_naid_lazy:
            try:
                CSQ.custom_request_c(db_files, """INSERT into odata_lazy_resps (resp, resp_date, 
                        description, file, file_size, hash_file)
                      VALUES (?, ?, ?, ? ,? ,?);""",
                                 list_of_lists_c=[
                                     [sum_hash, time, description, F.to_binary_pickle(file), size, new_file_hash]])
                fl_upd = False
            except:
                print(f'error INSERT into odata_lazy_resps')

        if fl_upd:
            if new_file_hash == file_hash: #те же данные (не изменились)
                CSQ.custom_request_c(db_files,
                                     f"""UPDATE odata_lazy_resps set resp_date = ?
                                     WHERE resp = ?;""",
                                     list_of_lists_c=[[time,sum_hash]])
            else:
                CSQ.custom_request_c(db_files,
                                     f"""UPDATE odata_lazy_resps set (resp_date, file, 
                                     file_size, hash_file ) = (?,?,?,?) WHERE resp = ?;""",
                                     list_of_lists_c=[[time, F.to_binary_pickle(file),
                                                            size, new_file_hash,sum_hash]])

    old_data_db = None

    headers = dict(Accept='application/json')
    params = dict()
    dict_data = dict()
    dict_data['text'] = text
    if refs:
        dict_data['refs'] = refs.refs
    for k, v in kwargs.items():
        dict_data[k] = v
    url = f'{CFG.Config.project.ERB_BASE_URL}/{aut.base.name
            }{aut.rootURL}'
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    dict_data_hash = hash_data_for_api(dict_data)
    params_hash = hash_data_for_api(params)
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    sum_hash = hashlib.md5(''.join([url_hash, dict_data_hash, params_hash, text_hash]
                                   ).encode('utf-8')).hexdigest()
    name_tmp_stukt = f'{BASE_NAME_TMP_STUKT}_{sum_hash}'
    fl_naid_lazy = False
    file_hash_lazy = None
    if lazy_method_huours > 0:
        now_date = F.now('')

        date_limit_half = F.date_add_time(now_date, hours=-(lazy_method_huours * 0.6))

        data_cach = load_tmp_stukt(name_tmp_stukt, False)
        fl_load_from_srv = True
        if data_cach:
            delta = (F.now('') - F.strtodate(data_cach['date'])).total_seconds()
            if F.strtodate(data_cach['date']) > date_limit_half:
                print(f'wet_req end PC {(F.now('') - start).total_seconds()} secs.')
                old_data_db = data_cach['data']
                return 200, data_cach['data']

        date_limit = F.date_add_time(now_date, hours=-lazy_method_huours)
        query = CSQ.SqlQuery(
            sqlite=f"""SELECT s_num, resp_date,
            CASE WHEN datetime(resp_date) >= datetime(?)  
                THEN file 
            ELSE null  
                END AS file, 
              hash_file FROM odata_lazy_resps 
        where resp = ? limit 1""",
            postgres=f"""
            SELECT 
                s_num, 
                resp_date,
                CASE WHEN CAST(resp_date AS TIMESTAMP) >= CAST(%s AS TIMESTAMP)  
                    THEN file 
                    ELSE null  
                END AS file, 
              hash_file FROM odata_lazy_resps 
            WHERE resp = %s 
            LIMIT 1"""
        )
        data = CSQ.custom_request_c(CFG.Config.project.db_files, query,
            list_of_lists_c=[[date_limit, sum_hash]], rez_dict=True)
        if data and len(data):
            fl_naid_lazy = True
            file_hash_lazy = data[0]['hash_file']
            if data[0]['file'] is not None: # 19.06.2026

                old_data_db = F.from_binary_pickle(data[0]['file'])
                if F.strtodate(data[0]['resp_date']) >= date_limit:
                    print(f'wet_req end DB {(F.now('') - start).total_seconds()}')
                    return 200, old_data_db
    try:
        response = requests.get(url, json=dict_data, headers=headers, params=params, auth=(aut.login, aut.password))
    except:
        print(f'wet_req end err (Code: None) resp {(F.now('')  - start).total_seconds()}')
        if old_data_db:
            print(f'    restored_old_data')
            return 200, old_data_db
        return 408, None
    # print(F.convert_binary_to_data(response.content))
    if response.status_code == 200:
        rez = JS.loads(F.convert_binary_to_data(response.content))
        if lazy_method_huours > 0:
            time = F.now()
            add_data_db(CFG.Config.project.db_files, fl_naid_lazy, sum_hash, rez,
                            f"{text}", file_hash_lazy, time)
            save_tmp_stukt({"data": rez, "date": time}, name_tmp_stukt)
        print(f'wet_req end {(F.now('') - start).total_seconds()}')
        return response.status_code, rez
    else:
        print(f'wet_req end err (Code: {response.status_code}) answ {(F.now('') - start).total_seconds()}')
        if old_data_db:
            print(f'    restored_old_data')
            return 200, old_data_db
        return response.status_code, None

def get_wet_request_result(text: str, refs: Refs_wet | None = None, lazy_method_huours=0, msg_err ='None', **kwargs)->None|list[dict]:
    key, res = get_wet_request(text=text, refs=refs, lazy_method_huours=lazy_method_huours,kwargs=kwargs)
    if key != 200:
        F.win_msgbox(f'Внимание!', f'Ошибка получения данных из ЕРП')
        return
    if not res['data']:
        if msg_err == 'None':
            msg_err = f'Данные не найдены'
        if msg_err:
            F.win_msgbox(f'Внимание!', msg_err)
        return
    data = res['data']
    return data


def make_nomen(dict_data:dict):
    headers = dict(Accept='application/json')
    params = dict()

    url = f'{CFG.Config.project.ERB_BASE_URL}/{CFG.Config.user_config.ERP_base_name["Значение"]}/ru_RU/hs/mes/sysexchange/v1/make_nomen/none'
    response = requests.post(url, json=dict_data, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    data = F.convert_binary_to_data(response.content)
    try:
        data = JS.loads(data)
    except:
        if not response.status_code == 200:
            data = {'Код':'','ЕстьОшибки':True, 'Ошибки':[data]}
    return response.status_code, data 



def test_post_json(json:dict, erp_base_name:str = 'ERP',postfix=''):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{erp_base_name}/ru_RU/hs/{postfix}'
    response = requests.patch(url, json=json, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    #print(F.convert_binary_to_data(response.content))
    try:
        answ = JS.loads(F.convert_binary_to_data(response.content))
    except:
        answ = F.convert_binary_to_data(response.content)

    if not isinstance(answ,dict):
        answ = {"Ошибки":answ,
                "ЕстьОшибки":True,
                }

    return response.status_code, answ

    
#================== MES==============================




def get_file(path:str|list = None):
    if path == None or F.sep() not in path:
        err = f'Err {path}'
        print(err)
        return None, [err]
    if isinstance(path,str):
        path = [path]

    headers = dict(Accept='application/json')
    params = dict()

    url = f'http://{HOST_MES}:{PORT_MES}/hs/mes/get_file/v1'
    response = requests.get(url, json= {'path_files':[{'path_file':_} for _ in path]}, headers=headers, params=params)
    #print(F.convert_binary_to_data(response.content))
    if response.status_code == 200:
        data_ = JS.loads(F.convert_binary_to_data(response.content))
        return response.status_code, [{k:base64.b64decode(v) for k,v in item.items() if v != None} for item in data_['Данные'] if isinstance(item,dict)]
    else:
        return response.status_code, JS.loads(F.convert_binary_to_data(response.content))


def _generate_link(ref:str,TYPE_DOC:str)->tuple[str,str]:
    c1_link = fr'/data/{TYPE_DOC}?ref={F.uuid_to_1c_ref(ref)}'
    path = F.get_1c_executor_path()
    path_o = F.Cust_path(path)
    prefix = path_o.as_raw_literal()  #prefix = fr'"%programfiles%\1cv8\common\1cestart.exe" '
    claster = CFG.Config.user_config.ERP_base.КластерСерверов
    name_srv = CFG.Config.user_config.ERP_base.name
    out_link = fr'e1c://server/{claster}/{name_srv}#e1cib{c1_link}'
    line = prefix + fr'/url "{out_link}"'
    return line, out_link



def open_in_1c(ref:str,TYPE_DOC:str)->tuple[bool,str|None]:
    line, out_link = _generate_link(ref,TYPE_DOC)
    try:
        subprocess_call(line, shell=True)
        return True,None
    except:
        F.copy_bufer(out_link)
        return False,out_link




class Etap_erp(_ImportDb):
    def __init__(self,
                    item:dict
                 ):
        self.ref:str = None
        self.НаименованиеЭтапа:str = None
        self.Комментарий:str = None
        self.ПометкаУдаления:bool = None
        self.Организация:str = None
        self.Подразделение:str = None
        self.ref_Подразделение:str = None
        self.Спецификация:str = None
        self.Спецификация_ref:str = None
        self.Спецификация_code:str = None
        self.Статус:str = None
        self.Распоряжение:str = None
        self.Номер:str = None
        self.Дата:str = None
        self.Проведен:bool = None
        self.НЭ_НулевойЭтап:bool = None
        self.НомерСтрокиЗП:int = None
        self.НомерПартииЗапуска:int = None
        self.НомерЭтапа:int = None
        self.НомерСледующегоЭтапа:int = None
        self.ФактическоеНачалоЭтапа:datetime.datetime = None
        self.ФактическоеОкончаниеЭтапа:datetime.datetime = None
        self.parce_row_dict(item)
        if F.is_date(self.ФактическоеНачалоЭтапа,"%Y-%m-%dT%H:%M:%S"):
            self.ФактическоеНачалоЭтапа = F.strtodate(self.ФактическоеНачалоЭтапа,"%Y-%m-%dT%H:%M:%S")
        if F.is_date(self.ФактическоеОкончаниеЭтапа,"%Y-%m-%dT%H:%M:%S"):
            self.ФактическоеОкончаниеЭтапа = F.strtodate(self.ФактическоеОкончаниеЭтапа,"%Y-%m-%dT%H:%M:%S")

    def __repr__(self):
        return f"Etap_erp({self.НаименованиеЭтапа}, №{self.НомерЭтапа})"

    @property
    def emoj_deletion_mark(self):
        if self.ПометкаУдаления:
            return CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol
        return ''

class NotFoundNomenclature(Exception): ...

class Etaps_erp():
    def __init__(self,kpl:int):
        data_znpr = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""SELECT 
        пл_оуп.Номенклатура_ЕРП_ref, знпр.Ref_Key_py, пл_оуп.НомПартии_ЗП, знпр.№ERP FROM пл_оуп 
         LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
         WHERE пл_оуп.НомПл = {kpl};""", one=True, rez_dict=True)
        self.НомПартии_ЗП:str = data_znpr['НомПартии_ЗП']
        self.ref_py:str = data_znpr['Ref_Key_py']
        self.num_zp:str = data_znpr['№ERP']
        self.nomenclature_ref:str  = data_znpr['Номенклатура_ЕРП_ref']
        self.specification_ref:str = ''
        self.specification_code:str = ''
        self.err = False
        self.err_msg = ''
        if not self.nomenclature_ref:
            raise NotFoundNomenclature('Некорректно привязана номенклатура!')
        try:
            self.list_etaps = self.get_etaps_by_znpr_nomen_ref(self.ref_py, self.nomenclature_ref)
            if not self.list_etaps:
                self.list_etaps = self.get_etaps_by_znpr_nomen_ref_alter_join(self.ref_py, self.nomenclature_ref)
            if self.list_etaps:
                self.specification_ref = self.list_etaps[0].Спецификация_ref
                self.specification_code = self.list_etaps[0].Спецификация_code
                self.НомПартии_ЗП = self.list_etaps[0].НомерПартииЗапуска   # noqa
        except Exception as e:
            print(e)
            self.err = True
            self.err_msg = e
            raise e
    @staticmethod
    def get_znpr_etaps_by_kpl(kpl: int):
        data_znpr = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""SELECT пл_оуп.Номенклатура_ЕРП_ref, знпр.Ref_Key_py, пл_оуп.НомПартии_ЗП, знпр.№ERP FROM пл_оуп 
         LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
         WHERE пл_оуп.НомПл = {kpl};""", one=True, rez_dict=True)
        list_etaps = Etaps_erp.get_etaps_by_znpr_nomen_ref(data_znpr['Ref_Key_py'], data_znpr['Номенклатура_ЕРП_ref'])
        if list_etaps:
            return list_etaps
        return Etaps_erp.get_etaps_by_znpr_nomen_ref_alter_join(data_znpr['Ref_Key_py'], data_znpr['Номенклатура_ЕРП_ref'])

    @staticmethod
    def get_etap_by_ref_etap(ref_etap:str)->tuple[bool, dict|None]:
        text = f"""ВЫБРАТЬ
                                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Ссылка)) КАК ref,
                                ЭтапПроизводства2_2.НаименованиеЭтапа КАК НаименованиеЭтапа,
                                ЭтапПроизводства2_2.ПометкаУдаления КАК ПометкаУдаления,
                                ЭтапПроизводства2_2.Комментарий КАК Комментарий,
                                ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Организация) КАК Организация,
                                ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Подразделение) КАК Подразделение,
                                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Подразделение.Ссылка)) КАК ref_Подразделение,
                                ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Спецификация) КАК Спецификация,
                                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Спецификация)) КАК Спецификация_ref,
                                ЭтапПроизводства2_2.Спецификация.Код КАК Спецификация_code,
                                ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Статус) КАК Статус,
                                ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Распоряжение) КАК Распоряжение,
                                ЭтапПроизводства2_2.Номер КАК Номер,
                                ЭтапПроизводства2_2.Дата КАК Дата,
                                ЭтапПроизводства2_2.Проведен КАК Проведен,
                                ЭтапПроизводства2_2.НЭ_НулевойЭтап КАК НЭ_НулевойЭтап,
                                ЗаказНаПроизводство2_2Продукция.НомерСтроки КАК НомерСтрокиЗП,
                                ЭтапПроизводства2_2.НомерПартииЗапуска КАК НомерПартииЗапуска,
                                ЭтапПроизводства2_2.НомерЭтапа КАК НомерЭтапа,
                                ЭтапПроизводства2_2.НомерСледующегоЭтапа КАК НомерСледующегоЭтапа,
                                ЭтапПроизводства2_2.ФактическоеНачалоЭтапа,
                                ЭтапПроизводства2_2.ФактическоеОкончаниеЭтапа
                            ИЗ
                                Документ.ЭтапПроизводства2_2 КАК ЭтапПроизводства2_2
                                    ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказНаПроизводство2_2.Продукция КАК ЗаказНаПроизводство2_2Продукция
                                    ПО (ЭтапПроизводства2_2.Спецификация = ЗаказНаПроизводство2_2Продукция.Спецификация
                                    И ЭтапПроизводства2_2.ПартияПроизводства.ОсновноеИзделиеНоменклатура = ЗаказНаПроизводство2_2Продукция.Номенклатура)
                            ГДЕ
                                ЭтапПроизводства2_2.Ссылка = &Этап

                """
        refs = Refs_wet(text)
        ref_obj_etap = Ref_wet('Этап', "Документы.ЭтапПроизводства2_2", ref_etap)
        refs.add_ref(ref_obj_etap)
        key, res = get_wet_request(text=text, refs=refs)
        if key != 200:
            raise ValueError(f'Ошибка получения данных из ЕРП')
        if res['data']:
            return True, res['data'][0]
        return False, 'Не найден этап по ref'


    @staticmethod
    def get_etaps_by_znpr_nomen_ref(ref_py: str, nomen_ref: str):
        text = f"""ВЫБРАТЬ
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Ссылка)) КАК ref,
                        ЭтапПроизводства2_2.НаименованиеЭтапа КАК НаименованиеЭтапа,
                        ЭтапПроизводства2_2.ПометкаУдаления КАК ПометкаУдаления,
                        ЭтапПроизводства2_2.Комментарий КАК Комментарий,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Организация) КАК Организация,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Подразделение) КАК Подразделение,
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Подразделение.Ссылка)) КАК ref_Подразделение,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Спецификация) КАК Спецификация,
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Спецификация)) КАК Спецификация_ref,
                        ЭтапПроизводства2_2.Спецификация.Код КАК Спецификация_code,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Статус) КАК Статус,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Распоряжение) КАК Распоряжение,
                        ЭтапПроизводства2_2.Номер КАК Номер,
                        ЭтапПроизводства2_2.Дата КАК Дата,
                        ЭтапПроизводства2_2.Проведен КАК Проведен,
                        ЭтапПроизводства2_2.НЭ_НулевойЭтап КАК НЭ_НулевойЭтап,
                        ЗаказНаПроизводство2_2Продукция.НомерСтроки КАК НомерСтрокиЗП,
                        ЭтапПроизводства2_2.НомерПартииЗапуска КАК НомерПартииЗапуска,
                        ЭтапПроизводства2_2.НомерЭтапа КАК НомерЭтапа,
                        ЭтапПроизводства2_2.НомерСледующегоЭтапа КАК НомерСледующегоЭтапа,
                        ЭтапПроизводства2_2.ФактическоеНачалоЭтапа,
                        ЭтапПроизводства2_2.ФактическоеОкончаниеЭтапа
                    ИЗ
                        Документ.ЭтапПроизводства2_2 КАК ЭтапПроизводства2_2
                            ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказНаПроизводство2_2.Продукция КАК ЗаказНаПроизводство2_2Продукция
                            ПО (ЭтапПроизводства2_2.Спецификация = ЗаказНаПроизводство2_2Продукция.Спецификация
                            И ЗаказНаПроизводство2_2Продукция.Ссылка = &Распоряжение)
                    ГДЕ
                        ЭтапПроизводства2_2.Распоряжение = &Распоряжение
                        И ЗаказНаПроизводство2_2Продукция.Спецификация.ОсновноеИзделиеНоменклатура = &Номенклатура
                        И ЭтапПроизводства2_2.ПометкаУдаления = ЛОЖЬ
                        И ЭтапПроизводства2_2.Проведен = ИСТИНА
        """
        refs = Refs_wet(text)
        ref_obj_znpr = Ref_wet('Распоряжение', "Документы.ЗаказНаПроизводство2_2", ref_py)
        ref_obj_nomen = Ref_wet('Номенклатура', "Справочники.Номенклатура", nomen_ref)

        refs.add_ref(ref_obj_znpr)
        refs.add_ref(ref_obj_nomen)
        key, res = get_wet_request(text=text, refs=refs)
        if key != 200:
            raise ValueError(f'Ошибка получения данных из ЕРП')
        list_etaps: list[Etap_erp] = []
        for it in res['data']:
            list_etaps.append(Etap_erp(it))
        return list_etaps


    @staticmethod
    def get_etaps_by_znpr_nomen_ref_alter_join(ref_py: str, nomen_ref: str):
        text = f"""ВЫБРАТЬ
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Ссылка)) КАК ref,
                        ЭтапПроизводства2_2.НаименованиеЭтапа КАК НаименованиеЭтапа,
                        ЭтапПроизводства2_2.ПометкаУдаления КАК ПометкаУдаления,
                        ЭтапПроизводства2_2.Комментарий КАК Комментарий,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Организация) КАК Организация,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Подразделение) КАК Подразделение,
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Подразделение.Ссылка)) КАК ref_Подразделение,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Спецификация) КАК Спецификация,
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Спецификация)) КАК Спецификация_ref,
                        ЭтапПроизводства2_2.Спецификация.Код КАК Спецификация_code,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Статус) КАК Статус,
                        ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Распоряжение) КАК Распоряжение,
                        ЭтапПроизводства2_2.Номер КАК Номер,
                        ЭтапПроизводства2_2.Дата КАК Дата,
                        ЭтапПроизводства2_2.Проведен КАК Проведен,
                        ЭтапПроизводства2_2.НЭ_НулевойЭтап КАК НЭ_НулевойЭтап,
                        ЗаказНаПроизводство2_2Продукция.НомерСтроки КАК НомерСтрокиЗП,
                        ЭтапПроизводства2_2.НомерПартииЗапуска КАК НомерПартииЗапуска,
                        ЭтапПроизводства2_2.НомерЭтапа КАК НомерЭтапа,
                        ЭтапПроизводства2_2.НомерСледующегоЭтапа КАК НомерСледующегоЭтапа,
                        ЭтапПроизводства2_2.ФактическоеНачалоЭтапа,
                        ЭтапПроизводства2_2.ФактическоеОкончаниеЭтапа
                    ИЗ
                        Документ.ЭтапПроизводства2_2 КАК ЭтапПроизводства2_2
                            ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказНаПроизводство2_2.Продукция КАК ЗаказНаПроизводство2_2Продукция
                            ПО (ЭтапПроизводства2_2.ПартияПроизводства.ОсновноеИзделиеНоменклатура = ЗаказНаПроизводство2_2Продукция.Номенклатура)
                    ГДЕ
                        ЭтапПроизводства2_2.Распоряжение = &Распоряжение
                        И ЗаказНаПроизводство2_2Продукция.Спецификация.ОсновноеИзделиеНоменклатура = &Номенклатура
                        И ЭтапПроизводства2_2.ПометкаУдаления = ЛОЖЬ
                        И ЭтапПроизводства2_2.Проведен = ИСТИНА
        """
        refs = Refs_wet(text)
        ref_obj_znpr = Ref_wet('Распоряжение', "Документы.ЗаказНаПроизводство2_2", ref_py)
        ref_obj_nomen = Ref_wet('Номенклатура', "Справочники.Номенклатура", nomen_ref)

        refs.add_ref(ref_obj_znpr)
        refs.add_ref(ref_obj_nomen)
        key, res = get_wet_request(text=text, refs=refs)
        if key != 200:
            raise ValueError(f'Ошибка получения данных из ЕРП alter_join')
        list_etaps: list[Etap_erp] = []
        for it in res['data']:
            list_etaps.append(Etap_erp(it))
        return list_etaps

    def __repr__(self):
        status = "error" if self.err else "ok"
        return f"Etaps_erp(НомПартии={self.НомПартии_ЗП}, etaps={len(self.list_etaps)}, status={status})"
    
    @property  
    def is_deleted(self):
        list_delete_states =[_.ПометкаУдаления for _ in self.list_etaps if not _.НЭ_НулевойЭтап]
        set_delete_state = set(list_delete_states)
        if len(set_delete_state)==1 and list_delete_states[0] == True:
            return True
        return False

    @property
    def is_empty_notnull(self):
        list_delete_states =[_ for _ in self.list_etaps if not _.НЭ_НулевойЭтап]
        if not list_delete_states:
            return True
        return False

    def create_new_etap(self,name:str,ref_podr:str)->tuple[int,list[str]|dict]:
        json_data = {'name':name,
                'ref_py':self.ref_py,
                'НомПартии_ЗП':self.НомПартии_ЗП,
                'Подразделение_Key':ref_podr
                }
        headers = dict(Accept='application/json')
        params = dict()
        url = f'{CFG.Config.project.ERB_BASE_URL}/{CFG.Config.user_config.ERP_base_name['Значение']}/ru_RU/hs/mes/etaps/v1/add_etap/'
        response = requests.post(url, json = json_data, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
        # print(F.convert_binary_to_data(response.content))
        if response.status_code == 200:
            return response.status_code, json.loads(F.convert_binary_to_data(response.content))
        return response.status_code, F.convert_binary_to_data(response.content)

    def is_etap_existance(self,name_etap:str)->bool:
        return name_etap in {_.НаименованиеЭтапа for _ in self.list_etaps if not _.ПометкаУдаления}
    
    def get_permited_to_create_etaps(self,mes_code_podr:str):
        DICT_ETAPI_FULL = F.deploy_dict_c(CSQ.custom_request_c(CFG.Config.project.db_naryad, f'''SELECT * FROM etaps''', rez_dict=True),
                                          'name')

        etaps_names = {_.НаименованиеЭтапа for _ in self.list_etaps}
        
        rez = [{'Этап': k, '_s_num': v['s_num'], '_color': v['color']} for k, v in DICT_ETAPI_FULL.items() if
            k not in etaps_names
            and v['poki'] == CFG.Config.place.poki and v['ДляЕРП'] 
            and v['Опер_код_рц_для_ткп_стат'][:4] == mes_code_podr[:4]]
        return rez

    def filtered_by_podr(self, podr_name)->list[Etap_erp]:
        text = f'''SELECT 
                rab_c.Имя,
                rab_c.ref_СтруктураПредприятия, 
                rab_c.poki, 
                rab_c.empl_Подразделение,
                etaps.name as etaps_name,
                use_in_estimate_plan as use_in_estimate_plan 
             FROM rab_c 
             INNER JOIN etaps ON etaps.s_num = rab_c.etaps_num 
             LEFT JOIN СтруктураПредприятия ON СтруктураПредприятия.Ref =  rab_c.ref_СтруктураПредприятия 
             WHERE rab_c.poki = {CFG.Config.place.poki} and rab_c.empl_Подразделение = "{podr_name}";'''

        data_rc = CSQ.custom_request_c(CFG.Config.project.db_users, text, rez_dict=True,  
                                       attach_dbs=CFG.Config.project.db_naryad)
        set_refs = set([_['ref_СтруктураПредприятия'] for _ in data_rc])
        return [_ for _ in self.list_etaps if _.ref_Подразделение in set_refs]

    def make_dict_etaps(self) ->  dict:

        dict_etap = {'Спецификация': self.specification_code,
                    'Спецификация_Key': self.specification_ref,
                                                               'Этапы': []}
        for et in self.list_etaps:
            dict_etap['Этапы'].append(
                {'Номер': et.Номер, 'НаименованиеЭтапа': et.НаименованиеЭтапа,
                 'Чек': et.ref})
        return dict_etap


