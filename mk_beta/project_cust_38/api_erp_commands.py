import pprint
import requests
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_odata_erp as CODATA
import json as JS
import base64
import project_cust_38.Cust_config as CFG
import hashlib
import sys
import json
from subprocess import call as subprocess_call

USER_ERP = 'mes_user'
PASS_ERP = '89Luham'


HOSTNAME_LOCAL_MES = False
PORT_MES = 20011
if HOSTNAME_LOCAL_MES: #"POW-ING22":
    HOST_MES = '192.168.14.71'# AG local
else:
    HOST_MES = '192.168.50.44'# server

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

def get_wet_request(text: str, refs: Refs_wet | None = None, lazy_method_huours=0, **kwargs):
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
                                     f"""UPDATE odata_lazy_resps set (resp_date ) = (?) 
                                     WHERE resp == ?;""",
                                     list_of_lists_c=[[time,sum_hash]])
            else:
                CSQ.custom_request_c(db_files,
                                     f"""UPDATE odata_lazy_resps set (resp_date, file, 
                                     file_size, hash_file ) = (?,?,?,?) WHERE resp == ?;""",
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
    url = f'{CFG.Config.project.ERB_BASE_URL}/{
            CFG.Config.user_config.ERP_base_name["Значение"]}/ru_RU/hs/mes/sysexchange/v1/wet_request/none'
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
        data = CSQ.custom_request_c(CFG.Config.project.db_files, f"""SELECT s_num, resp_date,
            CASE WHEN datetime(resp_date) >= datetime(?)  
                THEN file 
            ELSE null  
                END AS file, 
              hash_file FROM odata_lazy_resps 
        where resp == ? limit 1""",
            list_of_lists_c=[[date_limit, sum_hash]], rez_dict=True)
        if data and len(data):
            fl_naid_lazy = True
            file_hash_lazy = data[0]['hash_file']
            old_data_db = F.from_binary_pickle(data[0]['file'])
            if F.strtodate(data[0]['resp_date']) >= date_limit:
                print(f'wet_req end DB {(F.now('') - start).total_seconds()}')
                return 200, old_data_db
    try:
        response = requests.get(url, json=dict_data, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
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