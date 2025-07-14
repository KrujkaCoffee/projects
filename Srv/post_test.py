import pprint
import requests
import project_cust_38.Cust_Functions as F

USER = 'Obmen_proizv'
PASS = 'nE6zamap'
url3 = f'http://novgorod:8088/ERP_050923/ru_RU/hs/mes/factexp/v1/meth/'

USER = 'mes_user'
PASS = '89Luham'

headers = dict(Accept='application/json')
params = dict()
url = f'http://novgorod:8088/ERP_Audit/ru_RU/hs/SDE/Staff/'
url = f'http://novgorod:8088/ERP_Audit/ru_RU/hs/mes/factexp/v1/meth/'

response = requests.get(url, headers=headers, params=params, auth=(USER, PASS))
if response.status_code == 200:
    if 'text/html;charset=utf-8' == response.headers._store['content-type'][-1]:
        response =  F.convert_binary_to_data(response.content)
    elif 'json' in response.headers._store['content-type'][-1]:
        response = response.json()
else:
    response = response.status_code
pprint.pprint(response)