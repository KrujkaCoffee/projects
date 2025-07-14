import json

import requests
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_odata_erp as CODATA
import json as JS


def post_res_json(json:dict, erp_base_name:str = 'ERP'):
    USER = 'mes_user'
    PASS = '89Luham'
    headers = dict(Accept='application/json')
    params = dict()
    url = f'http://novgorod:8088/{erp_base_name}/ru_RU/hs/mes/resspec/v1/make_res/'
    response = requests.post(url, json=json, headers=headers, params=params, auth=(USER, PASS))
    print(F.convert_binary_to_data(response.content))
    return response.status_code, F.convert_binary_to_data(response.content)


