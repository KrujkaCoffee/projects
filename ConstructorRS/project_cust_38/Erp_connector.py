import requests
import json
import datetime


class Main:
    def __init__(self) -> None:
        self.erp_path = 'http://novgorod:8088/ERP/odata/standard.odata/'
        self.user = 'OdataZNP'
        self.pswd = 'znp'
        self.temp_json = 'temp.json'
        self.all_avaliable_urls = 'urls.txt'

    def get_response(self, doc_name=False, print_result=False, last_days=None, year=None, number=None, save_json=False, find_me=False):
        headers = dict(Accept='application/json')
        params = dict()
        if doc_name:
            url = self.get_url(doc_name, last_days, year, number, find_me)
        else:
            url = 'http://novgorod:8088/ERP/odata/standard.odata/'
        print(url)
        response = requests.get(url, headers=headers, params=params, auth=(self.user, self.pswd))
        json_result = response.json()
        if print_result:
            print(json_result)
        if save_json:
            with open(self.temp_json, 'w') as file:
                json.dump(json_result, file)
        return json_result.get('value')

    def get_url(self, doc_name,  last_days=None, year=None, number=None, find_me=False):
        url = f'http://novgorod:8088/ERP/odata/standard.odata/{doc_name}'
        if last_days:
            day_now = datetime.datetime.now().date()
            old_date = day_now - datetime.timedelta(days=last_days)
            old_date = old_date.strftime("%Y-%m-%d")
            old_date += 'T00:00:00'
            url += f"?$filter=Date ge datetime'{old_date}'&$format=json"

        elif year and number:
            url += f"?$filter=substring(Number, 1, 11) eq '{number}' and year(Date) eq {year}&$format=json"
        elif year:
            url += f"?$filter=year(Date) eq {year}&$format=json"
        elif number:
            url += f"?$filter=substring(Number, 1, 11) eq '{number}'&$format=json"
        elif find_me:
            url += f"{find_me}"
        url += '&$format=json;odata=nometadata'
        return url
    
    # def run(self, doc_name, **kwargs):
    #     url = self.get_url(doc_name, **kwargs)
    #     response = self.get_response()
    #     print(response)
    #     with open(settings.JSON_PATH, "w", encoding='utf-8') as write_file:
    #         json.dump(response, write_file)
    

    def get_available_url(self):
        print(f'документы к которым сейчас есть доступ(сохранены в ):')
        url_list = self.get_response()
        urls = []
        for val in url_list:
            print(val['url'])
            urls.append(f"{val['url']}\n")
        with open(self.all_avaliable_urls, 'w', encoding='utf-8') as file:
            file.writelines(urls)



if __name__ == '__main__':
    m = Main()
    # m.get_available_url()   # получение доступных адресов
    
    # работают с фильтрацией проверено
    res = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2?$top=3', print_result=True)  # ?$top=3' , find_me='?$filter=DeletionMark eq False
    # # res = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2', find_me="?$filter=Number eq 'ПУ00-000376' and year(Date) eq 2018") 
    # # res = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2', find_me="?$filter=Статус eq 'КПроизводству'")  # last_days=10,  # , find_me="Ref_Key eq '4744af71-c657-11ee-8503-00d861dd2b4a'"
    # # res = m.get_response(doc_name='Catalog_Номенклатура?$top=1')  # find_me="?$filter=startswith(Number, 'АПЗ.') eq true") 
    # # res = m.get_response(doc_name='Catalog_Номенклатура', find_me="?$filter=startswith(Number, 'ИЦ.') eq true")
    
    print(res)
    # print(len(res))
    # res = res[0]
    # for k, v in res.items():
    #     if v:
    #         print(k, '  ', v)
    # m.get_response(doc_name='Catalog_Номенклатура', , save_json=True,  print_result=True)  # last_days=10,  # 
            
#  'Закрыт'