from __future__ import annotations

import pprint

import project_cust_38.Cust_google_sheets_gspread as GS
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow


def fix_np(np):
    np_new = np.split('.')[0]
    np_new = np_new.split('/')[0]
    return np_new


def get_pdo():
    name_sheet = 'ПДО'
    book = GS.Gbook(key_book=GS.keybook)
    # list_sheets = book.list_sheets()
    # plan_name = list_sheets[-1]
    sht = GS.Gsheet(book, name_sheet)
    # print(sht.cell_val('Y49'))
    # list_of_lists = sht.list_of_lists()
    # sht.cell_set('Y49',value= F.now())
    list_of_lists = GS.Gsheet.list_of_lists(sht)
    list_of_lists[1].append('ROW')
    list_of_lists[2].append('')
    for i in range(3,len(list_of_lists)):
        list_of_lists[i].append(str(i+1))

    for j in range(1,len(list_of_lists[1])):
        if list_of_lists[1][j].strip() == '':
            list_of_lists[1][j] = list_of_lists[1][j-1].strip()
    for j in range(len(list_of_lists[2])):
        if list_of_lists[2][j] != '':
            list_of_lists[2][j] = list_of_lists[1][j] + '_' + list_of_lists[2][j]
        else:
            list_of_lists[2][j] = list_of_lists[1][j]

    for j in range(len(list_of_lists[2])):
        list_of_lists[2][j] = name_sheet + '_' + list_of_lists[2][j]

    dict_of_list = F.list_of_lists_to_list_of_dicts(list_of_lists[2:])

    for i in range(len(dict_of_list)):
        dict_of_list[i][name_sheet + '_№ проекта'] = fix_np(dict_of_list[i][name_sheet+ '_№ проекта'])
    return dict_of_list

def get_top():
    name_sheet = 'ТОП'
    book = GS.Gbook(key_book=GS.keybook)
    # list_sheets = book.list_sheets()
    # plan_name = list_sheets[-1]
    sht = GS.Gsheet(book, name_sheet)
    # print(sht.cell_val('Y49'))
    # list_of_lists = sht.list_of_lists()
    # sht.cell_set('Y49',value= F.now())
    list_of_lists = GS.Gsheet.list_of_lists(sht)
    list_of_lists[1].append('ROW')
    list_of_lists[2].append('')
    for i in range(3,len(list_of_lists)):
        list_of_lists[i].append(str(i+1))

    for j in range(1,len(list_of_lists[1])):
        if list_of_lists[1][j].strip() == '':
            list_of_lists[1][j] = list_of_lists[1][j-1].strip()
    for j in range(len(list_of_lists[2])):
        if list_of_lists[2][j] != '':
            list_of_lists[2][j] = list_of_lists[1][j] + '_' + list_of_lists[2][j]
        else:
            list_of_lists[2][j] = list_of_lists[1][j]

    for j in range(len(list_of_lists[2])):
        list_of_lists[2][j] = 'ТОП_' + list_of_lists[2][j]

    dict_of_list = F.list_of_lists_to_list_of_dicts(list_of_lists[2:])

    for i in range(len(dict_of_list)):
        dict_of_list[i]['ТОП_№ проекта'] = fix_np(dict_of_list[i]['ТОП_№ проекта'])
    return dict_of_list
def get_op():
    name_sheet = 'ОП (ПУ)'
    book = GS.Gbook(key_book=GS.keybook)
    #list_sheets = book.list_sheets()
    #plan_name = list_sheets[-1]
    sht = GS.Gsheet(book,name_sheet)
    #print(sht.cell_val('Y49'))
    #list_of_lists = sht.list_of_lists()
    #sht.cell_set('Y49',value= F.now())
    list_of_lists = GS.Gsheet.list_of_lists(sht)
    for j in range(len(list_of_lists[1])):
        list_of_lists[1][j] = 'ОП_' + list_of_lists[1][j]
    dict_of_list = F.list_of_lists_to_list_of_dicts(list_of_lists[1:])
    for i in range(len(dict_of_list)):
        dict_of_list[i]['ОП_№ проекта'] = fix_np(dict_of_list[i]['ОП_№ проекта'])
    return dict_of_list
def get_ko():
    name_sheet = 'КО'
    book = GS.Gbook(key_book=GS.keybook)
    #list_sheets = book.list_sheets()
    #plan_name = list_sheets[-1]
    sht = GS.Gsheet(book,name_sheet)
    #print(sht.cell_val('Y49'))
    #list_of_lists = sht.list_of_lists()
    #sht.cell_set('Y49',value= F.now())
    list_of_lists = GS.Gsheet.list_of_lists(sht)
    for j in range(1,len(list_of_lists[1])):
        if list_of_lists[1][j].strip() == '':
            list_of_lists[1][j] = list_of_lists[1][j-1].strip()
    for j in range(len(list_of_lists[2])):
        if list_of_lists[2][j] != '':
            list_of_lists[2][j] = list_of_lists[1][j] + '_' + list_of_lists[2][j]
        else:
            list_of_lists[2][j] = list_of_lists[1][j]

    for j in range(len(list_of_lists[2])):
        list_of_lists[2][j] = 'КО_' + list_of_lists[2][j]

    dict_of_list = F.list_of_lists_to_list_of_dicts(list_of_lists[2:])
    for i in range(len(dict_of_list)):
        dict_of_list[i]['КО_№ проекта'] = fix_np(dict_of_list[i]['КО_№ проекта'])
    return dict_of_list
    #print(sht.cell_val('Y49'))
def fix_date_to_iso(date_str:str):
    if F.is_date(date_str, "%d.%m.%Y"):
         return F.datetostr(F.strtodate(date_str, "%d.%m.%Y"), '%Y-%m-%d')
    if F.is_date(date_str, "%d.%m.%y"):
         return F.datetostr(F.strtodate(date_str, "%d.%m.%y"), '%Y-%m-%d')
    return date_str

def date_from_iso_to_loacal(date_str:str):
    if F.is_date(date_str, '%Y-%m-%d'):
         return F.datetostr(F.strtodate(date_str), "%d.%m.%y")
    return date_str
def fix_dates_to_iso(item:dict):
    for k in item.keys():
        if F.is_date(item[k],"%d.%m.%Y"):
            item[k] = F.datetostr(F.strtodate(item[k],"%d.%m.%Y"),'%Y-%m-%d')
        if F.is_date(item[k],"%d.%m.%y"):
            item[k] = F.datetostr(F.strtodate(item[k],"%d.%m.%y"),'%Y-%m-%d')
    return item

def date_obj_from_str(date_str:str):
    if F.is_date(date_str, "%d.%m.%Y"):
        return F.strtodate(date_str, "%d.%m.%Y")
    if F.is_date(date_str, "%d.%m.%y"):
        return F.strtodate(date_str, "%d.%m.%y")
    if F.is_date(date_str, '%Y-%m-%d'):
        return F.strtodate(date_str, '%Y-%m-%d')
    else:
        return False
def merge_dicts(list_list_dicts:list):

    rez = []
    min_len = min([len(_) for _ in list_list_dicts])

    for i in range(min_len):
        tmp = dict()
        for j in range(len(list_list_dicts)):
            for key in list_list_dicts[j][i].keys():
                tmp[key.replace("\n", "").replace("\r", "")] = list_list_dicts[j][i][key].replace("\n", "").replace("\r", "")

        check_val_py = ''
        for key in tmp.keys():
            if 'ПУ' in key:
                if check_val_py == '':
                    check_val_py = tmp[key]
                else:
                    if tmp[key] != check_val_py:
                        print(f'ОШибка сведения общей таблица из гугл плана {tmp[key]} не равна '
                              f'{check_val_py} по полю {key} в строке {i}')
                        return False
        rez.append(tmp)
    return rez


dict_match_plans = {'пл_ко':{'КО_Задание на оборудование для доукомплектования_Факт':'Дата_задание_доукомплектование',
                  'КО_РКД, рев1_План':'Пдата_зав_КД',
                  'КО_РКД, рев1_Факт':'Фдата_зав_КД',
                  'КО_Сдача РКД в архив_План':'Пдата_зав_КДрев2',
                  'КО_Сдача РКД в архив_Факт':'Фдата_зав_КДрев2',},

                  'пл_оуп':{
                  'ОП_Ответственный':'Ответственный',
                  'ОП_Тип оборудования':'Тип_оборудования',
                  'ОП_Поручение на доставку': 'Дата_поручение_на_доставку',
                    'ОП_Передача последней версии ОЛ, ТЗ':'Дата_передача_последне_версии_ОЛ_ТЗ',
                    'ОП_Дата поставки по контракту':'Дата_поставлено_подписано'},

                    #'пл_топ':{'ТОП_Наличие работ переработчика_(да/нет)':'Аутсорс_ТП',
                    #         'ТОП_Проверка РКД, рев1 проверено и согласовано_План':'Пдата_зав_Тсогл1',
                    #        'ТОП_Проверка РКД, рев1 проверено и согласовано_Факт':'Фдата_зав_Тсогл1',
                    #        'ТОП_Проверка РКД, рев2 проверено и согласовано_План':'Пдата_зав_Тсогл2',
                    #        'ТОП_Проверка РКД, рев2 проверено и согласовано_Факт':'Фдата_зав_Тсогл2',
                    #        'ТОП_Ресурсная спецификация подготовлена и согласован_План':'Пдата_зав_спецЕРП',
                    #        'ТОП_Ресурсная спецификация подготовлена и согласован_Факт':'Фдата_зав_спецЕРП',
                    #
                    #}
                  }

def is_date_all(str_date):
    if F.is_date(str_date,"%d.%m.%Y"):
        return True
    if F.is_date(str_date,"%d.%m.%y"):
        return True
    if F.is_date(str_date,'%Y-%m-%d'):
        return True
    return False

def get_year_from_date(date_str):
    year = False
    if date_str == '':
        return year
    try:
        year = F.datetostr(F.strtodate(date_str,"%d.%m.%Y"),'%Y')
    except:
        try:
            year = F.datetostr(F.strtodate(date_str, "%d.%m.%y"), '%Y')
        except:
            try:
                year = F.datetostr(F.strtodate(date_str), '%Y')
            except:
                print(f"error to date{date_str}")
    return year



def fill_date_from_gsheets_to_db(self:mywindow,dict_from_db,dict_data_gbook):

    def check_condition_update(dict_match_plans,tbl_db,key,item,itemdb):
        if 'дата' in dict_match_plans[tbl_db][key]:
            if is_date_all(item[key]):
                if fix_date_to_iso(item[key]) != str(itemdb[dict_match_plans[tbl_db][key]]):
                    return True
        else:
            if str(item[key]) != str(itemdb[dict_match_plans[tbl_db][key]]):
                return True
        return False
    def write_in_db_mes(self,fields,vals,tbl_db,pnom):
        fields_str = ', '.join(fields)
        vals_str = CSQ.questions_for_mask(vals)

        query = f"""UPDATE {tbl_db} SET ({fields_str}) = ({vals_str}) WHERE НомПл = {pnom}"""
        CSQ.custom_request_c(self.db_kplan, query, list_of_lists_c=[vals])
        print(f'OK//// {query}')

    list_change = []
    for item_ in dict_data_gbook:
        item = fix_dates_to_iso(item_)
        py = item['КО_№ ПУ']
        #np = item['КО_№ проекта']
        year = get_year_from_date(item['ОП_Оформление заказа на производство'])
        if year == False:
            continue
        for itemdb in dict_from_db:
            year_db = get_year_from_date(itemdb['Дата_заявки_на_произв'])
            if year == False:
                continue
            if py == itemdb['№ERP'] and year == year_db:
                pnom = itemdb['Пномер']
                for tbl_db in dict_match_plans.keys():
                    fields = []
                    vals = []
                    for key in dict_match_plans[tbl_db].keys():
                        fl = check_condition_update(dict_match_plans,tbl_db,key,item,itemdb)
                        if fl:
                            fields.append(dict_match_plans[tbl_db][key])
                            vals.append(fix_date_to_iso(item[key]))
                    if len(vals) > 0:
                        write_in_db_mes(self,fields,vals,tbl_db,pnom)
                        list_change.append(str([list(zip(fields, vals))]))
    return list_change

@CQT.onerror
def fill_g_plan(self:mywindow,*args):
    tbl = self.ui.tbl_kal_pl
    list_active_pnoms = []
    nf_pnom = CQT.num_col_by_name_c(tbl,'plan.Пномер')
    for i in range(tbl.rowCount()):
        if not tbl.isRowHidden(i):
            list_active_pnoms.append(tbl.item(i,nf_pnom).text())
    dict_data_pdo = get_pdo()
    dict_data_top = get_top()
    dict_data_op = get_op()
    dict_data_ko = get_ko()

    dict_data_gbook = merge_dicts([dict_data_op, dict_data_ko, dict_data_top,dict_data_pdo])
    if dict_data_gbook == False:
        return
    set_py = set()
    for gitem in dict_data_gbook:
        py = gitem['ТОП_№ ПУ']
        if py != '':
            set_py.add(F.clear_row_for_file_name_c(py.replace("\n", "")))

    list_py = list(set_py)
    dict_from_db = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Пномер, plan.Статус, пл_оуп.№проекта, пл_оуп.№ERP, пл_оуп.Дата_заявки_на_произв,
              пл_оуп.Ответственный, пл_оуп.Тип_оборудования, пл_оуп.Дата_поручение_на_доставку, пл_оуп.Дата_передача_последне_версии_ОЛ_ТЗ, пл_оуп.Дата_поставлено_подписано,
              пл_ко.Дата_задание_доукомплектование, пл_ко.Пдата_зав_КД, пл_ко.Фдата_зав_КД, пл_ко.Пдата_зав_КДрев2, пл_ко.Фдата_зав_КДрев2,
               пл_топ.Аутсорс_ТП as "пл_топ.Аутсорс_ТП",  пл_топ.Пдата_зав_Тсогл1 as "пл_топ.Пдата_зав_Тсогл1", 
               пл_топ.Фдата_зав_Тсогл1 as "пл_топ.Фдата_зав_Тсогл1", пл_топ.Пдата_зав_Тсогл2 as "пл_топ.Пдата_зав_Тсогл2", 
               пл_топ.Фдата_зав_Тсогл2 as "пл_топ.Фдата_зав_Тсогл2", пл_топ.Пдата_зав_спецЕРП as "пл_топ.Пдата_зав_спецЕРП",
                пл_топ.Фдата_зав_спецЕРП as "пл_топ.Фдата_зав_спецЕРП",
              plan.Пдата_зав_заявка_мат as "plan.Пдата_зав_заявка_мат", plan.Фдата_зав_заявка_мат as "plan.Фдата_зав_заявка_мат",
              plan.Пдата_зав_заявка_аутсорс as "plan.Пдата_зав_заявка_аутсорс", 
              plan.Фдата_зав_заявка_аутсорс as "plan.Фдата_зав_заявка_аутсорс", 
              пл_заг.ПДата_зав_заг as "пл_заг.ПДата_зав_заг",
              пл_заг.ФДата_зав_заг as "пл_заг.ФДата_зав_заг",
              пл_сб.Пдата_зав_сб as "пл_сб.Пдата_зав_сб",
              пл_сб.Фдата_зав_сб as "пл_сб.Фдата_зав_сб",
              пл_компл.ПДата_зав_комплект_упаковки as "пл_компл.ПДата_зав_комплект_упаковки",
              пл_компл.ФДата_зав_комплект_упаковки as "пл_компл.ФДата_зав_комплект_упаковки"
               FROM пл_оуп
              INNER JOIN пл_ко ON пл_ко.НомПл = пл_оуп.НомПл,
               plan ON plan.Пномер = пл_оуп.НомПл,
               пл_топ ON пл_топ.НомПл = пл_оуп.НомПл,
               пл_заг ON пл_заг.НомПл = пл_оуп.НомПл,
               пл_сб ON пл_сб.НомПл = пл_оуп.НомПл,
               пл_компл ON пл_компл.НомПл = пл_оуп.НомПл
               WHERE plan.Статус != 4 and plan.Пномер IN ({','.join(list_active_pnoms)}) and пл_оуп.№ERP IN {tuple(list_py)}""",
                                        rez_dict=True)
    if dict_from_db == False:
        CQT.msgbox(f'Выборка проектов не подходящая')
        return
    fill_gbook_from_db(self,dict_from_db,dict_data_gbook)



@CQT.onerror
def get_g_plan(self:mywindow,*args):
    warn_msg = f"""Обновление по полям\n\n
    {dict_match_plans}"""
    if not CQT.msgboxgYN(warn_msg):
        return
    tbl = self.ui.tbl_kal_pl
    list_active_pnoms = []
    nf_pnom = CQT.num_col_by_name_c(tbl,'plan.Пномер')
    for i in range(tbl.rowCount()):
        if not tbl.isRowHidden(i):
            list_active_pnoms.append(tbl.item(i,nf_pnom).text())
    #dict_data_to = get_top()
    dict_data_op = get_op()
    dict_data_ko = get_ko()
    dict_data_gbook = merge_dicts([dict_data_op,dict_data_ko])
    if dict_data_gbook == False:
        return
    list_py =[]
    for gitem in dict_data_gbook:
        py = gitem['КО_№ ПУ']

        list_py.append(py)

    dict_from_db = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Пномер, plan.Статус, пл_оуп.№проекта, пл_оуп.№ERP, пл_оуп.Дата_заявки_на_произв,
            пл_оуп.Ответственный, пл_оуп.Тип_оборудования, пл_оуп.Дата_поручение_на_доставку, пл_оуп.Дата_передача_последне_версии_ОЛ_ТЗ, пл_оуп.Дата_поставлено_подписано,
            пл_ко.Дата_задание_доукомплектование, пл_ко.Пдата_зав_КД, пл_ко.Фдата_зав_КД, пл_ко.Пдата_зав_КДрев2, пл_ко.Фдата_зав_КДрев2,
             пл_топ.Аутсорс_ТП as "Аутсорс_ТП",  пл_топ.Пдата_зав_Тсогл1 as "Пдата_зав_Тсогл1", 
             пл_топ.Фдата_зав_Тсогл1 as "Фдата_зав_Тсогл1", пл_топ.Пдата_зав_Тсогл2 as "Пдата_зав_Тсогл2", 
             пл_топ.Фдата_зав_Тсогл2 as "Фдата_зав_Тсогл2", пл_топ.Пдата_зав_спецЕРП as "Пдата_зав_спецЕРП",
              пл_топ.Фдата_зав_спецЕРП as "Фдата_зав_спецЕРП"
                                         
             FROM пл_оуп
            INNER JOIN пл_ко ON пл_ко.НомПл = пл_оуп.НомПл,
             plan ON plan.Пномер = пл_оуп.НомПл,
             пл_топ ON пл_топ.НомПл = пл_оуп.НомПл
             WHERE plan.Статус != 4 and plan.Пномер IN ({','.join(list_active_pnoms)}) and пл_оуп.№ERP IN {tuple(list_py)}""", rez_dict=True)

    list_change = fill_date_from_gsheets_to_db(self,dict_from_db,dict_data_gbook)
    if len(list_change) > 0:
        CQT.msgbox(pprint.pformat(list_change))
    else:
        CQT.msgbox(f'Успешно')

def check_condition_of_rewrite_google(g_val, val_db):
    if g_val != '' and val_db == "":
        return False
    if g_val.lower().strip() == val_db.lower().strip():
        return False
    return True
def write_into_gsheet(sht, row, column, val_db,name_field,list_log,py_pr,g_val):
    sht.cell_set(row, column, val_db)
    print(f'{py_pr} {name_field}, было {g_val}')
    print(f'                      , стало {val_db}')
    list_log.append([f'{py_pr} {name_field}, было {g_val}'])
    list_log.append([f'                      , стало {val_db}'])
    F.sleep(1.1)


def fill_gbook_from_db(self:mywindow,dict_from_db,dict_data_gbook):
    def fill_value_to_tmp_top_lines_gsheet(dict_tmp_lines_gsheet,value_item,key,py_year):
        if py_year not in dict_tmp_lines_gsheet:
            return dict_tmp_lines_gsheet
        if key in dict_tmp_lines_gsheet[py_year]['values']:
            if 'дата' in key.lower():
                if F.is_date(value_item,"%d.%m.%y"):
                    if F.strtodate(value_item,"%d.%m.%y") > dict_tmp_lines_gsheet[py_year]['values'][key]:
                        dict_tmp_lines_gsheet[py_year]['values'][key] = F.strtodate(value_item,"%d.%m.%y")
            else:
                if value_item != '' and value_item != '0':
                    dict_tmp_lines_gsheet[py_year]['values'][key] = value_item
        else:
            if 'дата' in key.lower():
                if F.is_date(value_item,"%d.%m.%y"):
                    dict_tmp_lines_gsheet[py_year]['values'][key] = F.strtodate(value_item,"%d.%m.%y")
            else:
                if value_item != '' and value_item != '0'and value_item != 0:
                    dict_tmp_lines_gsheet[py_year]['values'][key] = value_item
        return dict_tmp_lines_gsheet




    def send_data_to_gsheets(dict_tmp_lines_gsheet,dict_match_plans_from_db_to_gbook):
        list_log = [['Выгружено из МЕС в Гугул']]
        list_sheets = list(set([v[0] for k,v in dict_match_plans_from_db_to_gbook.items()]))
        book = GS.Gbook(key_book=GS.keybook)
        for name_sheet in list_sheets:
            print(f'Лист {name_sheet} Обновлено:')
            list_log.append([f'Лист {name_sheet} Обновлено:'])
            sht = GS.Gsheet(book, name_sheet)
            for pyear in dict_tmp_lines_gsheet.keys():
                row = int(dict_tmp_lines_gsheet[pyear]['item'][f'{name_sheet}_ROW'])
                for name_field in dict_tmp_lines_gsheet[pyear]['values'].keys():
                    if dict_match_plans_from_db_to_gbook[name_field][0] == name_sheet:
                        column =dict_match_plans_from_db_to_gbook[name_field][1]
                        name_field_gsheet = dict_match_plans_from_db_to_gbook[name_field][2]
                        g_val = dict_tmp_lines_gsheet[pyear]['item'][name_field_gsheet]
                        val_db = dict_tmp_lines_gsheet[pyear]['values'][name_field]
                        if 'дата' in name_field.lower():
                            val_db = F.datetostr(val_db,"%d.%m.%y")
                        if not check_condition_of_rewrite_google(g_val,val_db):
                            continue
                        py_pr = dict_tmp_lines_gsheet[pyear]['item']['ОП_№ ПУ'] + ' ' + dict_tmp_lines_gsheet[pyear]['item']['ОП_№ проекта']
                        write_into_gsheet(sht, row, column, val_db,name_field,list_log,py_pr,g_val)
        return list_log


    dict_match_plans_from_db_to_gbook = {'пл_топ.Аутосорс_ТП':['ТОП',8,'ТОП_Наличие работ переработчика_(да/нет)' ],
                                         'пл_топ.Пдата_зав_Тсогл1':['ТОП',11, 'ТОП_Проверка РКД, рев1 проверено и согласовано_План'],
                                         'пл_топ.Фдата_зав_Тсогл1': ['ТОП', 12, 'ТОП_Проверка РКД, рев1 проверено и согласовано_Факт'],
                                         'пл_топ.Пдата_зав_Тсогл2': ['ТОП', 15, 'ТОП_Проверка РКД, рев2 проверено и согласовано_План'],
                                         'пл_топ.Фдата_зав_Тсогл2': ['ТОП', 16, 'ТОП_Проверка РКД, рев2 проверено и согласовано_Факт'],
                                         'пл_топ.Пдата_зав_спецЕРП': ['ТОП', 17, 'ТОП_Ресурсная спецификация подготовлена и согласован_План'],
                                         'пл_топ.Фдата_зав_спецЕРП': ['ТОП', 18, 'ТОП_Ресурсная спецификация подготовлена и согласован_Факт'],

                                         'plan.Пдата_зав_заявка_мат': ['ПДО', 6,
                                                                      'ПДО_Задания на закупку подготовлены и направлены в ОС_План'],
                                         'plan.Фдата_зав_заявка_мат': ['ПДО', 7,
                                                                      'ПДО_Задания на закупку подготовлены и направлены в ОС_Факт'],
                                         'plan.Пдата_зав_заявка_аутсорс': ['ПДО', 12,
                                                                       'ПДО_Заявки на аутсорсинг подготовлена и отправлена_План'],
                                         'plan.Фдата_зав_заявка_аутсорс': ['ПДО', 13,
                                                                       'ПДО_Заявки на аутсорсинг подготовлена и отправлена_Факт'],
                                         'пл_заг.ПДата_зав_заг': ['ПДО', 18,
                                                                           'ПДО_Заготовительные работы: скомплектовано для сборки_План'],
                                         'пл_заг.ФДата_зав_заг': ['ПДО', 19,
                                                                           'ПДО_Заготовительные работы: скомплектовано для сборки_Факт'],
                                         'пл_сб.Пдата_зав_сб': ['ПДО', 20,
                                                                           'ПДО_Сборочные работы: собрано, принято ОТК_План'],
                                         'пл_сб.Фдата_зав_сб': ['ПДО', 21,
                                                                           'ПДО_Сборочные работы: собрано, принято ОТК_Факт'],
                                         'пл_компл.ПДата_зав_комплект_упаковки': ['ПДО', 22,
                                                                           'ПДО_Упаковка: упаковано, принято ОТК_План'],
                                         'пл_компл.ФДата_зав_комплект_упаковки': ['ПДО', 23,
                                                                           'ПДО_Упаковка: упаковано, принято ОТК_Факт'],

                                         }

    dict_tmp_lines_gsheet = dict()

    for gitem in dict_data_gbook:
        py = gitem['ТОП_№ ПУ']
        year = get_year_from_date(gitem['ОП_Оформление заказа на производство'])
        dict_tmp_lines_gsheet[f'{py}_{year}'] = {'item':gitem,'values': dict()}


    for item in dict_from_db:
        year = get_year_from_date(item['Дата_заявки_на_произв'])
        if year == False:
            continue
        py = item['№ERP']
        pnom = item['Пномер']

        for key in dict_match_plans_from_db_to_gbook.keys():
            if key in item:
                if item[key] == '':
                    continue
                value_item = item[key]
                if 'дата' in key.lower():
                    value_item = date_from_iso_to_loacal(item[key])
                dict_tmp_lines_gsheet = fill_value_to_tmp_top_lines_gsheet(dict_tmp_lines_gsheet,value_item,key,f'{py}_{year}')

    list_log = send_data_to_gsheets(dict_tmp_lines_gsheet,dict_match_plans_from_db_to_gbook)
    CQT.msgbox( pprint.pformat(f'Успешно: {list_log}'))


