import requests
import datetime
import re
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_config as CFG


COMPARE_PRODUCT = {  # если не сработал поиск по номенглатуре то искать в второподств
    'КЛ.': ['клапан', 'задвижк', 'затвор', 'шибер'],
    'КТ.': ['компенсатор'],
    'ШГ.': ['горелк'],
    # 'БСИ.': ['fri', '', '', ''],
    # 'ТППР.': ['горелка', '', '', ''],
}

ALLOWED = ['ПУ', ]  #'КЭ' те заказы которые берем

class OneOrder():
    def __init__(self, erp_order_key, number, date, queue_num, need_date,status,komment):
        self.erp_order_key = erp_order_key
        self.number = number
        self.date = date
        self.queue_num = queue_num
        self.need_date = need_date
        self.status = status
        self.komment = komment
        self.row_nomenglatures = []
        self.clean_nomenglatures = {}

    def append_nomenglature(self, value):
        self.row_nomenglatures.append(value)

    def count_all_nomenglatures(self):
        return len(self.clean_nomenglatures)

    def count_all_row_nomenglatures(self):
        return len(self.row_nomenglatures)
    
    def __str__(self) -> str:
        return f'Заказ номер {self.number}'


class OrdersComposit():
    # https://42clouds.com/ru-ru/techdocs/interfeys-odata-vozmozhnosti-i-nastroyka/
    # https://master1c8.ru/platforma-1s-predpriyatie-8/rukovodstvo-razrabottchika/glava-17-mehanizm-internet-servisov/7188/
    def __init__(self) -> None:
        self.erp_path = f'{CFG.Config.project.ERB_BASE_URL}/ERP/odata/standard.odata/'
        self.user = 'OdataZNP'
        self.pswd = 'znp'
        self.temp_json = 'temp.json'
        self.all_avaliable_urls = 'urls.txt'
        self.all_ordres = {}

    def count_all_orders(self):
        return len(self.all_ordres)

    def get_ostat_scl(self,list_sclads:list):
        #list_sclads = ['Склад комплектующих Пауэрз', 'Склад материалов Пауэрз']
        sclads = self.get_response(doc_name='Catalog_Склады',
                                   wet_filtr=f"?$filter=Description eq '{list_sclads[0]}' or Description eq '{list_sclads[1]}' &$select=Ref_Key,Description")

        list_keys_sclads = [f"Склад_Key eq guid'{_['Ref_Key']}'" for _ in sclads]
        str_list_keys_sclads = " or ".join(list_keys_sclads)

        #ref_key_pdo = self.get_response(doc_name=f"AccumulationRegister_ТоварыНаСкладах/Balance(Condition = '{str_list_keys_sclads}',Dimensions='Номенклатура,Склад')",
        #                            wet_filtr=f"?$top=1000&$select= *")
        res = self.get_response(
            doc_name=f"AccumulationRegister_ТоварыНаСкладах/Balance(Condition = '{str_list_keys_sclads}',Dimensions='Номенклатура,Склад')",
            wet_filtr=f"?$select= *")
        res = self.left_join_dicts(res,sclads,'Склад_Key','Ref_Key','Sclad')
        if res == []:
            return None
        return res

    def get_list_plpr(self):
        ref_key_pdo = self.get_response(doc_name='Catalog_СтруктураПредприятия',
                          wet_filtr=f"?$filter=Description eq 'Планово-диспетчерский отдел Производства (Пауэрз)' &$select= Ref_Key")[0]['Ref_Key']
        #res = self.get_response(doc_name='Document_ПланПроизводства',
        #                        wet_filtr=f"?$filter=Подразделение_Key eq guid'{ref_key_pdo}' &$top=1&$select= *")
        res = self.get_response(doc_name='Document_ПланПроизводства',
                                wet_filtr=f"?$filter=Подразделение_Key eq guid'{ref_key_pdo}' &$select= Date, Ref_Key, Статус, Number, Комментарий")
        #res = self.get_response(doc_name='Document_ПланПроизводства',
        #                        find_me=f"Статус eq 'ВПодготовке'$select= *")
        #res = self.get_response(doc_name='AccumulationRegister_ПланыПроизводства',
        #                        wet_filtr=f"?$filter=RecordSet/any(c:%20c/Статус eq 'Утвержден')")
        if res == []:
            return None
        return res

    def get_plpr(self,ref_Key):
        res_wet = self.get_response(doc_name='Document_ПланПроизводства',
                                wet_filtr=f"?$filter=Ref_Key eq guid'{ref_Key}'&$select= Продукция/Номенклатура_Key,Продукция/Спецификация_Key")
        set_nomens = set()
        set_spec = set()
        if len(res_wet) == 0:
            return []
        res = []
        for poz in res_wet[0]['Продукция']:
            set_nomens.add(poz['Номенклатура_Key'])
            set_spec.add(poz['Спецификация_Key'])
            res.append({'ПлПр_Key': ref_Key, 'Номенклатура_Key': poz['Номенклатура_Key'],
                        'Спецификация_Key': poz['Спецификация_Key']})
        list_nomens = list(set_nomens)
        list_spec = list(set_spec)

        step = 5
        res_nomen = []
        for i in range(0, len(list_nomens), step):
            tmp_list = []
            for j in range(i, i + step):
                if j >= len(list_nomens):
                    break
                tmp_list.append(list_nomens[j])
            list_vids_str = [f"Ref_Key eq guid'{_}'" for _ in tmp_list]
            str_vids = " or ".join(list_vids_str)
            nomen = self.get_response(doc_name='Catalog_Номенклатура',
                                      wet_filtr=f"?$filter=DeletionMark eq false and ({str_vids}) &$select=Ref_Key,"
                                                f"Description,НаименованиеПолное")
            for item in nomen:
                res_nomen.append(item)

        step = 5
        res_spec = []
        for i in range(0, len(list_spec), step):
            tmp_list = []
            for j in range(i, i + step):
                if j >= len(list_spec):
                    break
                tmp_list.append(list_spec[j])
            list_str = [f"Ref_Key eq guid'{_}'" for _ in tmp_list]
            str_ = " or ".join(list_str)
            spec = self.get_response(doc_name='Catalog_РесурсныеСпецификации',
                                     wet_filtr=f"?$filter=DeletionMark eq false and ({str_}) &$select=Ref_Key,Code,Статус,Описание,"
                                               f"Description,ИдентификаторВерсииДанных")
            for item in spec:
                res_spec.append(item)

        res = self.left_join_dicts(res, res_nomen, 'Номенклатура_Key', 'Ref_Key', 'nomen')
        res = self.left_join_dicts(res, res_spec, 'Спецификация_Key', 'Ref_Key', 'spec')

        if res == []:
            return None
        return res

    def get_etap_ref(self,ref_Key):
        res = self.get_response(doc_name='Catalog_ЭтапыПроизводства',
                                find_me=f"Ref_Key eq guid'{ref_Key}'&$select= Description")
        if res == []:
            return None
        res = res[0]
        return res

    def get_list_res_data(self,ref_Key=''):
        if ref_Key == '':
            ref_Key = "'00-054891' or Code eq '00-054867'"
        res = self.get_response(doc_name='Catalog_РесурсныеСпецификации',
                                wet_filtr=f"?$filter=Code eq {ref_Key}")
        if res == []:
            return None
        res = res[0]
        return res
    
    def get_nomen_mat_ref(self,ref_Key):
        res = self.get_response(doc_name='Catalog_Номенклатура',
                                find_me=f"Ref_Key eq guid'{ref_Key}'$select= Code")
        if res == []:
            return None
        res = res[0]
        return res

    def get_zakaz_py(self, order_num):
        res = self.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                find_me=f"number eq '{order_num}'$select= Ref_Key, Code, Description, НаименованиеПолное, Описание")
        if res == []:
            return None 
        res = res[0]
        return res
    
    def get_py_year(self, order_num,year):
        res_wet = self.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                wet_filtr=f"?$filter=year(Date) eq {year} and Number eq '{order_num}' &$top=10&$select= Продукция/Номенклатура_Key,Продукция/Спецификация_Key")
        set_nomens = set()
        set_spec = set()
        if len(res_wet)==0:
            return []
        res = []
        for poz in res_wet[0]['Продукция']:
            set_nomens.add(poz['Номенклатура_Key'])
            set_spec.add(poz['Спецификация_Key'])
            res.append({'PY':order_num,'year':year,'Номенклатура_Key':poz['Номенклатура_Key'],'Спецификация_Key':poz['Спецификация_Key'] })
        list_nomens = list(set_nomens)
        list_spec = list(set_spec)
        
        
        step = 5
        res_nomen = []
        for i in range(0, len(list_nomens), step):
            tmp_list = []
            for j in range(i, i + step):
                if j >= len(list_nomens):
                    break
                tmp_list.append(list_nomens[j])
            list_vids_str = [f"Ref_Key eq guid'{_}'" for _ in tmp_list]
            str_vids = " or ".join(list_vids_str)
            nomen = self.get_response(doc_name='Catalog_Номенклатура',
                                      wet_filtr=f"?$filter=DeletionMark eq false and ({str_vids}) &$select=Ref_Key,"
                                                f"Description,НаименованиеПолное")
            for item in nomen:
                res_nomen.append(item)

        step = 5
        res_spec = []
        for i in range(0, len(list_spec), step):
            tmp_list = []
            for j in range(i, i + step):
                if j >= len(list_spec):
                    break
                tmp_list.append(list_spec[j])
            list_str = [f"Ref_Key eq guid'{_}'" for _ in tmp_list]
            str_ = " or ".join(list_str)
            spec = self.get_response(doc_name='Catalog_РесурсныеСпецификации',
                                      wet_filtr=f"?$filter=DeletionMark eq false and ({str_}) &$select=Ref_Key,Code,Статус,Описание,"
                                                f"Description,ИдентификаторВерсииДанных")
            for item in spec:
                res_spec.append(item)
               
        res = self.left_join_dicts(res,res_nomen,'Номенклатура_Key','Ref_Key','nomen')
        res = self.left_join_dicts(res, res_spec, 'Спецификация_Key', 'Ref_Key', 'spec')
        
        if res == []:
            return None 
        return res
    
    def get_nomen_prodution(self,nomenglature_key):
        res = self.get_response(doc_name='Catalog_Номенклатура',
                                find_me=f"Ref_Key eq guid'{nomenglature_key}'$select= *")
        if res == []:
            return None
        return res

    @staticmethod
    def left_join_dicts(l_tbl, r_tbl, l_field, r_field,r_tbl_name:str):
        if len(r_tbl) == 0:
            return l_tbl
        hat = {k: None for k in r_tbl[0].keys()}
        for i in range(len(l_tbl)):
            if l_field not in l_tbl[i]:
                print(f'err l_field not found in l_tbl row{i}')
                return
            l_val = l_tbl[i][l_field]
            fl_naid = False
            for j in range(len(r_tbl)):
                if r_field not in r_tbl[j]:
                    print(f'err r_field not found in r_tbl row{j}')
                    return
                if l_val == r_tbl[j][r_field]:
                    for k, v in r_tbl[j].items():
                        name = k
                        if k in l_tbl[i]:
                            name = r_tbl_name + "_" + name 
                        l_tbl[i][name] = v
                    fl_naid = True
                    break
            if fl_naid == False:
                for k, v in hat.items():
                    name = k
                    if k in l_tbl[i]:
                        name = r_tbl_name + "_" + name 
                    l_tbl[i][name] = v
        return l_tbl



    
    @F.time_of_exec_cls_func_args_c
    def get_nomen_mater(self,list_vids):

        def get_list_vids(step,list_vids):
            step = 10

            rez = []
            for i in range(0, len(list_vids), step):
                tmp_list_vids = []
                for j in range(i, i + step):
                    if j >= len(list_vids):
                        break
                    tmp_list_vids.append(list_vids[j])
                list_vids_str = [f"Description eq '{_}'" for _ in tmp_list_vids]
                str_vids = " or ".join(list_vids_str)
                vids = self.get_response(doc_name='Catalog_ВидыНоменклатуры',
                                         wet_filtr=f"?$filter={str_vids} &$select=Ref_Key,Description")
                if vids == None:
                    return
                for item in vids:
                    rez.append(item)
            return rez

        def add_prices(list_nomen):

            prices = self.get_response(doc_name=fr"InformationRegister_ЦеныНоменклатуры25_RecordType/SliceLast("
                                                fr"  Condition=ВидЦены_Key eq guid'0135f909-5b65-11ee-84bf-00d861dd2b4a' and Цена gt 0)",
                                       wet_filtr=f"?$select= Цена, Номенклатура_Key ")
            dict_prices = F.deploy_dict_c(prices,'Номенклатура_Key')
            for i, nomen in enumerate(list_nomen):
                if nomen['Ref_Key'] in dict_prices:
                    list_nomen[i]['Цена'] = dict_prices[nomen['Ref_Key']]
                else:
                    list_nomen[i]['Цена'] = 0

            return list_nomen

        def get_list_nomen(step,list_vids):
            step = 5

            rez = []
            for i in range(0, len(list_vids), step):
                tmp_list_vids = []
                for j in range(i, i + step):
                    if j >= len(list_vids):
                        break
                    tmp_list_vids.append(list_vids[j])
                list_vids_str = [f"ВидНоменклатуры_Key eq guid'{_}'" for _ in tmp_list_vids]
                str_vids = " or ".join(list_vids_str)
                nomen = self.get_response(doc_name='Catalog_Номенклатура',
                                          wet_filtr=f"?$filter=DeletionMark eq false and ({str_vids}) &$select=Ref_Key,ВидНоменклатуры_Key,Code,"
                                            f"Артикул,Description,ЕдиницаИзмерения_Key,DeletionMark,СхемаОбеспечения_Key")
                for item in nomen:
                    rez.append(item)
            return rez


        #f_name = f'08052024_res'
        #if F.existence_file_c(f_name):
        #    res, schemas_rez = F.load_file_pickle(f_name)
        #    return  res, schemas_rez
        #

        list_sclads = ['Склад комплектующих Пауэрз', 'Склад материалов Пауэрз']
        sclads = self.get_response(doc_name='Catalog_Склады',
                                 wet_filtr=f"?$filter=Description eq '{list_sclads[0]}' or Description eq '{list_sclads[1]}' &$select=Ref_Key,Description")
        if sclads == None:
            return None, None
        list_keys_sclads = [f"Склад eq '{_['Ref_Key']}'" for _ in sclads]
        str_list_keys_sclads =  " or ".join(list_keys_sclads)
        
        schemas_tmp = self.get_response(doc_name='InformationRegister_СхемыОбеспечения',
                                    wet_filtr=f"?$select= СхемаОбеспечения_Key, Склад, СпособОбеспеченияПотребностей_Key")
        if schemas_tmp == None:
            return None, None
        schemas = []
        for item in schemas_tmp:
            if item['Склад'] in str_list_keys_sclads:
                schemas.append(item)
        
        sposob_obesp = self.get_response(doc_name='Catalog_СпособыОбеспеченияПотребностей',
                                    wet_filtr=f"?$select=Ref_Key,Description,ГарантированныйСрокОбеспечения")
        if sposob_obesp == None:
            return None, None
        schemas = self.left_join_dicts(schemas, sposob_obesp, 'СпособОбеспеченияПотребностей_Key', 'Ref_Key','sposObesp')
        schemas = self.left_join_dicts(schemas, sclads, 'Склад', 'Ref_Key','sclads')
        schemas_rez = []
        for item in schemas:
            period = None
            if F.is_numeric(item['ГарантированныйСрокОбеспечения']):
                period = int(item['ГарантированныйСрокОбеспечения'])
            schemas_rez.append({
                'Key': item['СхемаОбеспечения_Key'],
                'Description': item['Description'],
                'Склад': item['sclads_Description'],
                'ГарантированныйСрокОбеспечения': period,
            })
        
        vids = get_list_vids(10, list_vids)
        list_vids = [_['Ref_Key'] for _ in vids]
        nomen = get_list_nomen(10, list_vids)
        nomen = add_prices( nomen)
        edizm = self.get_response(doc_name='Catalog_УпаковкиЕдиницыИзмерения',
                                  wet_filtr=f"?$select=Ref_Key,Description")
        if edizm == None:
            return None, None
        nomen = self.left_join_dicts(nomen, vids, 'ВидНоменклатуры_Key', 'Ref_Key','vidsNomen')
        nomen = self.left_join_dicts(nomen, edizm, 'ЕдиницаИзмерения_Key', 'Ref_Key','edizm')
        if schemas_rez == None or nomen == None:
            return  None, None 
        #nomen = self.left_join_dicts(nomen,schemas,'СхемаОбеспечения_Key','СхемаОбеспечения_Key','schemasObesp')
        res = []
        s_num = 0
        for item in nomen:
            s_num+=1
            res.append({'ПНомер' : s_num,
                        'Вид' :     item['vidsNomen_Description'],
                        'Код' :item['Code'],
                        'Артикул' : item['Артикул'],
                        'Наименование' : item['Description'],
                        'ЕдиницаИзм' : item['edizm_Description'],
                        'СхемаОбеспечения' : item['СхемаОбеспечения_Key'],
                        'Ref_Key': item['Ref_Key'],
                        'Закупочная_цена': item['Цена']
                        })
            
        #F.save_file_pickle(f_name,(res, schemas_rez))
        return res, schemas_rez


    def get_plpr_doc(self,plpr_key):
        res = self.get_response(doc_name='Document_ПланПроизводства',
                                find_me=f"Ref_Key eq guid'{plpr_key}'$select= *")
        if res == []:
            return None
        return res


    def get_nomenglature_order(self, order_num):
        order = self.all_ordres.get(order_num)
        if order:
            for nom in order.row_nomenglatures:
                res = self.get_response(doc_name='Catalog_Номенклатура', 
                find_me=f"Ref_Key eq guid'{nom['nomenglature_key']}'$select= Ref_Key, Code, Description, НаименованиеПолное, Описание")
                if res == []:
                    return None
                res = res[0]
                one_nomenglature = {}
                one_nomenglature['ref_key'] = res['Ref_Key']
                one_nomenglature['erp_key'] = res['Code']
                one_nomenglature['Количество'] = nom['quantity']
                one_nomenglature['Дата_доставки'] = nom['shipment_date']
                full_description = res['Description']
                description  = res['Описание']
                name_full = res['НаименованиеПолное']
                articule = res['Артикул']
                one_nomenglature['Описание'] = full_description
                one_nomenglature['описание_материала'] = description
                one_nomenglature['артикул'] = articule
                one_nomenglature['НаименованиеПолное'] = name_full
                number = self.number_normalization(articule, name_full)  # description, full_description
                #print(f'найден  {full_description}\n    {one_nomenglature}')
                #if number:
                order.clean_nomenglatures[full_description] =  one_nomenglature
            return order.clean_nomenglatures
    
    def find_product_code(self, val):
        for pr_code, find_li in COMPARE_PRODUCT.items():
            for find_word in find_li:
                if find_word in val:
                    return pr_code

    def number_normalization(self, articule, name_full):
        # print('    артикул-', articule,'\n    наименование-', name_full, '\n    описание', description, '\n    полное_описание', full_description)
        if articule == '':
            return None
        number = re.compile(r'[А-Я]+\.(\d+.){1,10}')
        full_number = number.search(articule)
        if full_number:
            full_number = full_number.group()
            return full_number.strip()  # КТ.1808121.57 в артикуле
        full_number = number.search(name_full)
        if full_number:
            full_number = full_number.group()
            return full_number.strip()  # КТ.1808121.57 в полном наименовании


        pr_code = self.find_product_code(name_full.lower())
        if pr_code:
            return f'{pr_code}{articule}'
        return f"{'ПН.'}{articule}"

    def check_order_number(self, number):
        for i in ALLOWED:
            if number.startswith(i):
                return True
        return False

    def add_orders_from_odata(self, odata_response):
        for order in odata_response:
            number=order['Number']
            one_order = OneOrder(erp_order_key=order['Ref_Key'], number=number, date=order['Date'], 
                                 queue_num=order['Очередь'], need_date=order['ДатаПотребности'], 
                                 status=order['Статус'], komment=order['Комментарий'])
            sub_order = order['Продукция']
            if sub_order != []:
                for nomengl in sub_order:
                    nomenglature = {}
                    nomenglature['quantity'] = nomengl.get('Количество')
                    nomenglature['shipment_date'] = nomengl.get('ДатаОтгрузки')
                    nomenglature['nomenglature_key'] = nomengl.get('Номенклатура_Key')
                    one_order.append_nomenglature(nomenglature)
            if self.check_order_number(number):
                self.all_ordres[number] = one_order

    def get_all_numbres_orders(self):
        return list(self.all_ordres.keys())

    def get_orders(self, **kwargs):
        response = self.get_response(doc_name='Document_ЗаказНаПроизводство2_2', **kwargs)
        self.add_orders_from_odata(response)
        return self.all_ordres

    def get_response(self, **kwargs):
        headers = dict(Accept='application/json')
        params = dict()
        if kwargs.get('doc_name'):
            url = self.get_url(**kwargs)
        else:
            url = f'{CFG.Config.project.ERB_BASE_URL}/ERP/odata/standard.odata/'
        # print(url)  !!!!!!!!!!!!!!!!!!!
        try:

            response = requests.get(url, headers=headers, params=params, auth=(self.user, self.pswd))
            response = response.json()
            if 'odata.error' in response:
                return response['odata.error']['message']['value']
        except (
        requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.JSONDecodeError):
            print(f'{F.now()} not connect ERP')
            return None
        if 'value' in response:

            return response['value']
        else:
            print(f'err {response}')
            return None
        url = r"http://novgorod:8088/ERP/odata/standard.odata/InformationRegister_ЦеныНоменклатуры25/SliceLast(Period=datetime'2024-07-23T00:00:00')?$select=*&$format=json;odata=nometadata"
        
        
    def get_url(self, doc_name=False, last_days=None, year=None, number=None, find_me=False, print_result=False, code_rs=False,wet_filtr = False):
        url = f'{CFG.Config.project.ERB_BASE_URL}/ERP/odata/standard.odata/{doc_name}'
        if last_days:
            day_now = datetime.datetime.now().date()
            old_date = day_now - datetime.timedelta(days=last_days)
            old_date = old_date.strftime("%Y-%m-%d")
            old_date += 'T00:00:00'
            url += f"?$filter=Date ge datetime'{old_date}'"

        elif year and number:
            url += f"?$filter=substring(Number, 1, 11) eq '{number}' and year(Date) eq {year}"
        elif year:
            url += f"?$filter=year(Date) eq {year}"
        elif number:
            url += f"?$filter=substring(Number, 1, 11) eq '{number}'"
        elif find_me:
            url += f"?$filter={find_me}"
        elif code_rs:
            url += f"?$filter=Code eq'{code_rs}'"
        elif wet_filtr:
            url += wet_filtr
        url += '&$format=json;odata=nometadata'
        return url

if __name__ == '__main__':
    m = OrdersComposit()
    #m.get_zakaz_py('ПУ00-000145')
    #orders = m.get_orders(last_days=2)

                
    kod = '00-054891'
    res = m.get_response(doc_name="Catalog_РесурсныеСпецификации",
                         code_rs=kod, print_result=True)
    ind = res[0]['ИдентификаторВерсииДанных']
    status = res[0]['Статус']
    name = res[0]['Description']
    data = dict()
    for item in res[0]['МатериалыИУслуги']:
        val = item['КоличествоУпаковок']
        nomenglatures = m.get_nomen_mat_ref(item['Номенклатура_Key'])
        code = nomenglatures['Code']
        etap = dict_etap[item_n['Этап_Key']]

    # m.get_orders(last_days=2)  # find_me="Статус eq 'КПроизводству'"
    #orders = m.get_orders(last_days=30)
    #for order_name, v in orders.items():
    #    print(order_name)
    #    nomenglatures = m.get_nomenglature_order(order_name)
    
    # print(nomenglatures)
    # for k, v in nomenglatures.items():
    #     print('8'*8)
    #     print(k)
    #     print(v)
        
    # print(m.all_ordres['КЭ00-000113'].count_all_row_nomenglatures())
    # print(m.all_ordres['КЭ00-000113'].row_nomenglatures)



    
    # print(m.all_ordres['КЭ00-000113'].count_all_nomenglatures())
    # print(m.all_ordres['КЭ00-000113'].clean_nomenglatures)
    
    # # print(nomenglatures)
    


