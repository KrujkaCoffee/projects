import json as JS
import urllib.request
import requests
import datetime
import re
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
import hashlib
import sys
import project_cust_38.Cust_config as USRCNF
from collections import OrderedDict


EMPTY_KEY = '00000000-0000-0000-0000-000000000000'

class OrdersComposit():
    # https://42clouds.com/ru-ru/techdocs/interfeys-odata-vozmozhnosti-i-nastroyka/
    # https://master1c8.ru/platforma-1s-predpriyatie-8/rukovodstvo-razrabottchika/glava-17-mehanizm-internet-servisov/7188/
    # https://infostart.ru/1c/articles/1570140/
    # https://infostart.ru/1c/articles/719982/        Практика доступа в базу 1С через протокол oData. Изменение данных
    # https://its.1c.ru/db/v8325doc#bookmark:dev:TI000001358 17.4. Cтандартный интерфейс OData (2z2kZwRB3H1aBGllUAKC, kelast)

    headers = dict(Accept='application/json')
    params = dict()
    def __init__(self, srv_name = 'ERP') -> None:
        self.user = 'OdataZNP'
        self.pswd = 'znp'
        self.temp_json = 'temp.json'
        self.all_avaliable_urls = 'urls.txt'
        self.all_ordres = {}
        #self.dict_objs = dict()
        #self.load_meta()
        self.srv_name = srv_name
        self.erp_path = f'{CFG.Config.project.ERB_BASE_URL}/{self.srv_name}/odata/standard.odata/'
        
    def load_meta(self):
        url = fr"{self.erp_path}?$select=url"
        response = requests.get(url, headers=OrdersComposit.headers, params=OrdersComposit.params,
                                auth=(self.user, self.pswd))
        dict_objs = dict()
        response = response.json()['value']
        for item in response:
            type_data = item['url'].split('_')[0]
            if type_data not in dict_objs:
                dict_objs[type_data] = []
            dict_objs[type_data].append(item['url'])
            dict_objs[type_data] = sorted(dict_objs[type_data])
        self.dict_objs = dict_objs
        [_ for _ in dict_objs['Catalog'] if 'риостан' in _]
    def get_response(self, doc_name:str = None, wet_filtr:str = None,get_response_val=True,lazy_method_huours=0,
                     db_files=None,with_cod=False,
                    dict_aliases: dict = None  # Словарь алиасов {"старое_имя": "новое_имя"}
                     ):
        '''
        wet_filtr=f"?$filter=Code eq '{kod}' &$select=ИдентификаторВерсииДанных,Статус,Description"
        :param doc_name: 
        :param wet_filtr: 
        :return: 
        '''
        #Параметры $inlinecount, $orderby и $expand применимы только для запросов, выдающих список элементов. 
        # Параметр $expand не может использоваться для расширения реквизитов табличных частей.

        def _apply_aliases( data: dict, aliases: dict):
            def _apply_aliases_row( data: dict, aliases: dict):
                """Рекурсивно применяет алиасы к данным OData"""
                if "value" in data:
                    # Обрабатываем список элементов
                    for item in data["value"]:
                        item =_rename_fields(item, aliases)
                else:
                    # Обрабатываем единичный объект
                    data = _rename_fields(data, aliases)
                return data
            if isinstance(data,list):
                for data_row in data:
                    data_row = _apply_aliases_row(data_row,aliases)
            if isinstance(data,dict):
                data = _apply_aliases_row(data, aliases)
            return data


        def _rename_fields( item: dict, aliases: dict):

            """Переименовывает поля в соответствии с aliases"""
            # Создаем новый упорядоченный словарь
            new_item = OrderedDict()

            # Проходим по всем ключам исходного словаря
            for key in item.keys():
                if key in aliases:
                    # Если ключ нужно переименовать
                    new_key = aliases[key]
                    new_item[new_key] = item[key]
                elif any(key.startswith(old + '/') for old in aliases if '/' in old):
                    # Обработка вложенных структур с путями (Партнер/Наименование)
                    parts = key.split('/')
                    if parts[0] in aliases:
                        new_key = aliases[parts[0]] + '/' + '/'.join(parts[1:])
                        new_item[new_key] = item[key]
                    else:
                        new_item[key] = item[key]
                else:
                    # Ключ остается без изменений
                    new_item[key] = item[key]

            # Очищаем исходный словарь и обновляем его новыми значениями
            item.clear()
            item.update(new_item)

            # Рекурсивная обработка вложенных словарей
            for value in item.values():
                if isinstance(value, dict):
                    value = _rename_fields(value, aliases)
                elif isinstance(value, list):
                    for elem in value:
                        if isinstance(elem, dict):
                            elem = _rename_fields(elem, aliases)
            return item


        if db_files == None:
            db_files = USRCNF.Config.project.db_files
        def add_data_db(db_files:str ,fl_naid_lazy:int|None, url_hash:str, file,description, file_hash):
            size = sys.getsizeof(file)
            new_hash  = hashlib.md5(F.to_binary_pickle(file)).hexdigest()
            if fl_naid_lazy == None:
                CSQ.custom_request_c(db_files, """INSERT into odata_lazy_resps (resp, resp_date, description, file, file_size, hash_file)
                          VALUES (?, ?, ?, ? ,? ,?);""",
                                     list_of_lists_c=[[url_hash, F.now(), description, F.to_binary_pickle(file), size, new_hash]])
            else:
                if new_hash == file_hash:
                    CSQ.custom_request_c(db_files,
                    f"""UPDATE odata_lazy_resps set (resp_date ) = (?) WHERE s_num == {fl_naid_lazy};""",
                    list_of_lists_c=[[F.now()]])
                else:
                    CSQ.custom_request_c(db_files,
                    f"""UPDATE odata_lazy_resps set (resp_date, file, file_size, hash_file ) = (?,?,?,?) WHERE s_num == {fl_naid_lazy};""",
                    list_of_lists_c=[[F.now(), F.to_binary_pickle(file),size,new_hash]])
        
        headers = self.headers
        params = self.params
        url = self.get_url(doc_name=doc_name,wet_filtr=wet_filtr,meta= not get_response_val)
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        fl_naid_lazy = None
        file_hash_lazy = None
        if lazy_method_huours > 0 and db_files != None:
            now_date = F.now('')
            date_limit = F.date_add_time(now_date,hours=-lazy_method_huours)
            data = CSQ.custom_request_c(db_files,f"""SELECT s_num, resp_date,
            CASE WHEN datetime(resp_date) >= datetime("{date_limit}")  
        THEN file 
        ELSE null  
        END AS file, 
             
              hash_file FROM odata_lazy_resps 
            where resp == "{url_hash}" limit 1""",rez_dict=True)
            if len(data):
                fl_naid_lazy = data[0]['s_num']
                file_hash_lazy = data[0]['hash_file']
                if F.strtodate(data[0]['resp_date']) >= date_limit:
                    if with_cod:
                        return  200, F.from_binary_pickle(data[0]['file'])
                    else:
                        return F.from_binary_pickle(data[0]['file'])


        try:
            response = requests.get(url, headers=headers, params=params, auth=(self.user, self.pswd))
            cod = response.status_code
            if cod != 200:
                err_val = F.convert_binary_to_data(response.content)
                print(err_val)
                if with_cod:
                    return cod, f'error get obj "{doc_name}": {err_val}'
                else:
                    return  None
        except (
        requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.JSONDecodeError):
            print(f'{F.now()} not connect ERP')
            if with_cod:
                return None, None
            else:
                return None
        response_j = response.json()
        if get_response_val and 'value' in response_j:
            rez = response_j['value']
        else:
            rez = response_j

        if lazy_method_huours > 0 and db_files != None:
            add_data_db(db_files, fl_naid_lazy,url_hash,rez,f"{doc_name}:{wet_filtr}",file_hash_lazy)

        # Применяем алиасы к данным
        if dict_aliases:
            _apply_aliases(rez, dict_aliases)

        if with_cod:
            return cod, rez 
        else:
            return rez



        #url = r"http://novgorod:8088/ERP/odata/standard.odata/InformationRegister_ЦеныНоменклатуры25/SliceLast(Period=datetime'2024-07-23T00:00:00')?$select=*&$format=json;odata=nometadata"

    def undertake_doc(self, doc_name:str, guid:str , val:bool=True):
        doc_name = doc_name + f"(guid'{guid}')"
        postfix = 'Unpost'
        if val:
            postfix = 'PostingModeOperational=false'
        headers = self.headers
        params = self.params
        url = self.get_url(doc_name=doc_name, wet_filtr=f'/Post?{postfix}', meta=False)
        try:
            response = requests.post(url, headers=headers, auth=(self.user, self.pswd),)
            cod = response.status_code
            if 'odata.error' in response:
                return cod, response['odata.error']['message']['value']
        except (
        requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.JSONDecodeError):
            print(f'{F.now()} not connect ERP')
            return 0, None
        return cod, response

    def post_responce(self, doc_name:str = None): #16.06.25
        headers = self.headers
        params = self.params
        url = self.get_url(doc_name=doc_name, patch =True)
        try:
            response = requests.post(url, json=params, headers=headers, auth=(self.user, self.pswd),)
            cod = response.status_code
            response = response.json()
            self.params = dict()
            if 'odata.error' in response:
                return cod, response['odata.error']['message']['value']
        except (
        requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.JSONDecodeError):
            print(f'{F.now()} not connect ERP')
            return 0, None
        return cod, response

    def patch_responce(self, doc_name:str = None):
        headers = self.headers
        params = self.params
        wet_filtr = None
        url = self.get_url(doc_name=doc_name,wet_filtr=wet_filtr, patch =True)
        try:
            response = requests.patch(url, data= JS.dumps(params), headers=headers, auth=(self.user, self.pswd),)
            cod = response.status_code
            response = response.json()
            self.params = dict()
            if 'odata.error' in response:
                return cod, response['odata.error']['message']['value']
        except (
        requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.JSONDecodeError):
            print(f'{F.now()} not connect ERP')
            return 0, None
        return cod, response

        #url = "http://novgorod:8088/ERP_Audit/odata/standard.odata/Document_ЭтапПроизводства2_2(guid('49b73ab6-354d-11ef-8568-00d861dd2b4a'))?$format=json"
    

    def get_url(self, doc_name=False, wet_filtr = False, patch = False,meta=False):
        url = f'{self.erp_path}{doc_name}'
        postfix = '&$format=json;odata=nometadata'
        if meta:
            postfix = '&$format=json;odata=fullmetadata'


        if not patch:
            url += wet_filtr
            url += postfix
        else:
            url += '?$format=json'
        return url.replace('\n','')
    
    @staticmethod
    def del_carry_fields(data:dict,list_del:list=None):
        if list_del == None:
            list_del = ['type', 'key']
        new_data = dict()
        for k, v in data.items():
            fl_del = False
            for del_item in list_del:
                if del_item.lower() in k.lower():
                    fl_del = True
                    break
            if fl_del:
                continue
            if isinstance(v,list):
                new_v = []
                for item_v in v:
                    item_v = OrdersComposit.del_carry_fields(item_v,list_del)
                    new_v.append(item_v)
                v = new_v

            new_data[k] = v
        return new_data

    @staticmethod
    def fix_camelcase(data:dict):
        def fix(strin:str):
            return F.capital_letter_c(F.camel_to_snake(strin).replace('_'," "))
        if not isinstance(data,dict):
            return data
        new_data = dict()
        for k, v in data.items():
            k = fix(k)
            if isinstance(v,dict):
                v = fix_camelcase(v)
            if isinstance(v, list):
                new_list = []
                for item_v in v:
                    item_v = OrdersComposit.fix_camelcase(item_v)
                    new_list.append(item_v)
                v = new_list
            new_data[k]= v
        return new_data
    
    @staticmethod
    def fix_dates_form_erp_to_rus(data: dict|str):
        list_data_fields = ['дата', 'date', 'начатьне']
        def fix(strin):
            if F.is_date(strin, "%Y-%m-%dT00:00:00"):
                return F.datetostr(F.strtodate(strin, "%Y-%m-%dT%H:%M:%S"), "%d.%m.%Y")
            if F.is_date(strin, "%Y-%m-%dT%H:%M:%S"):
                return F.datetostr(F.strtodate(strin, "%Y-%m-%dT%H:%M:%S"), "%d.%m.%Y %H:%M:%S")
            return strin
        if isinstance(data,str):
            return fix(data)

        for k, v in data.items():
            fl_check = False
            for name in list_data_fields:
                if name in k.lower():
                    fl_check= True
                    break
            if fl_check:
                data[k] = fix(v)
            if isinstance(v, list):
                for ie, dic in enumerate(v):
                    v[ie] = OrdersComposit.fix_dates_form_erp_to_rus(dic)
        return data