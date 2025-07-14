import pprint
import requests
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_odata_erp as CODATA
import json as JS
import base64
import project_cust_38.Cust_config as CFG
USER_ERP = 'mes_user'
PASS_ERP = '89Luham'


HOSTNAME_LOCAL_MES = False
PORT_MES = 20011
if HOSTNAME_LOCAL_MES: #"POW-ING22":
    HOST_MES = '192.168.18.91'# AG local
else:
    HOST_MES = '192.168.50.44'# server

class Ref_wet():
    def __init__(self,name_var:str, path_conf_1c:str, ref_key:str):
        if '&' in name_var:
            raise ValueError
        self.name_var:str = name_var
        self.path_conf_1c:str = path_conf_1c
        self.ref_key:str = ref_key
        

class Refs_wet():
    def __init__(self,text_req:str):
        self.refs:dict = dict()
        self.text_req:str = text_req
    
    def add_ref(self,ref_wet:Ref_wet):
        if f'&{ref_wet.name_var}' not in self.text_req:
            raise ValueError
        
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
    answ = JS.loads(F.convert_binary_to_data(response.content))
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
    

def get_wet_request(text:str,refs:Refs_wet|None=None, **kwargs):
    headers = dict(Accept='application/json')
    params = dict()
    dict_data = dict()
    dict_data['text']=text
    if refs:
        dict_data['refs'] = refs.refs
    for k,v in kwargs.items():
        dict_data[k] = v
    url = f'{CFG.Config.project.ERB_BASE_URL}/{CFG.Config.user_config.ERP_base_name["Значение"]}/ru_RU/hs/mes/sysexchange/v1/wet_request/none'
    response = requests.get(url, json=dict_data, headers=headers, params=params, auth=(USER_ERP, PASS_ERP))
    # print(F.convert_binary_to_data(response.content))
    if response.status_code == 200:
        return response.status_code, JS.loads(F.convert_binary_to_data(response.content))
    else:
        return response.status_code, None


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