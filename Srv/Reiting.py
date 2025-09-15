import sys, io, logging, os
import builtins, logging

logging.basicConfig(filename=r'C:\srv_mes\srv_mes\db_logs\Reiting.log', level=logging.INFO, force=True, encoding='utf-8')
_orig_print = builtins.print

def logging_print(*args, **kwargs):
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    s = sep.join(map(str, args)) + ('' if end == '' else end)
    logging.getLogger('PRINT').info(s.rstrip('\n'))
    _orig_print(*args, **kwargs)

builtins.print = logging_print

import datetime
import pprint

if __name__ != '__main__':
    exit()
import requests
import project_cust_38.Cust_Functions as F
import time
import project_cust_38.report_ci as reports
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.nomenklatura as nomen_erp
import project_cust_38.Cust_odata_erp as ERP
import project_cust_38.Cust_config as USRCNF
from PyQt5 import QtWidgets
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_Excel as CEX
import project_cust_38.cust_pars_common_exel_b24 as GETPLIT
import user_calendar
# pyinstaller.exe --onefile main.py

# m = ERP.OrdersComposit()

# Condition=Номенклатура_Key eq guid'a7aeaba7-6da4-11ea-8432-00d861c603dc'
# prices = m.get_response(doc_name=r"InformationRegister_ЦеныНоменклатуры25_RecordType/SliceLast("
#                                 r" Condition=ВидЦены_Key eq guid'0135f909-5b65-11ee-84bf-00d861dd2b4a' and Цена gt 0)",#, Condition=ВидЦены_Key eq guid'0135f909-5b65-11ee-84bf-00d861dd2b4a'
#                                       wet_filtr=f"?$select= Цена, Номенклатура_Key ")#Condition=ВидЦены_Key eq guid'0135f909-5b65-11ee-84bf-00d861dd2b4a'  Номенклатура_Key, Цена
#
# print()
# dict_prices = F.deploy_dict_c(prices,'Номенклатура_Key')
# dict_prices['a7aeaba7-6da4-11ea-8432-00d861c603dc']
# tmp_list = [_ for _ in prices if _['Номенклатура_Key'] == 'a7aeaba7-6da4-11ea-8432-00d861c603dc']




def load_ip_hostnames() -> list[dict]:
    import ipaddress
    import subprocess
    import socket
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def ping_and_resolve(ip: str):
        """Проверяет, жив ли IP, и пытается получить hostname"""
        try:
            output = subprocess.run(
                ["ping", "-n", "1", "-w", "50", ip],  # Windows: 1 пакет, таймаут 50 мс
                capture_output=True, text=True
            )
            if "TTL=" not in output.stdout:
                return None
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                hostname = None
            return (ip, hostname)
        except Exception:
            return None

    def scan_subnet(subnet: str, max_threads=100):
        """Сканирует один /24 диапазон"""
        net = ipaddress.ip_network(subnet, strict=False)
        results = []
        with ThreadPoolExecutor(max_threads) as executor:
            futures = {executor.submit(ping_and_resolve, str(ip)): ip for ip in net.hosts()}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        return results


    # список нужных диапазонов
    subnets = [
        "192.168.14.0/24",
        "192.168.18.0/24",
        "192.168.19.0/24",
        "192.168.20.0/24",
        "192.168.21.0/24",
    ]

    all_devices = []
    with ThreadPoolExecutor(len(subnets)) as executor:  # параллельно сканируем все подсети
        futures = {executor.submit(scan_subnet, subnet): subnet for subnet in subnets}
        for future in as_completed(futures):
            all_devices.extend(future.result())
    rez = []
    # сортируем по IP
    for ip, host in sorted(all_devices, key=lambda x: list(map(int, x[0].split(".")))):
        print(f"{ip:15} -> {host}")
        rez.append({'ip':ip,'host':host})
    return rez



def export_data_for_excel_plan():
    query2 = "SELECT * FROM jurnal;"  # arr = select_SQL(putdb, query2, True)
    F.save_file(r'Z:\Data\for_exel_plan\query2.txt', CSQ.custom_request_c(db_naryad, query2), False)
    query3 = "SELECT naryad.Пномер, naryad.Номер_мк, mk.Номер_проекта, mk.Номер_заказа FROM naryad INNER JOIN mk ON mk.Пномер = naryad.Номер_мк;"  # arr_nar = select_SQL(putdb, query3, True)
    F.save_file(r'Z:\Data\for_exel_plan\query3.txt', CSQ.custom_request_c(db_naryad, query3), False)
    query4 = 'SELECT ФИО, Должность FROM employee WHERE Статус != "Увольнение";'  # arr_emp = select_SQL(putdb_users, query4, True)
    F.save_file(r'Z:\Data\for_exel_plan\query4.txt', CSQ.custom_request_c(db_users, query4), False)
    query5 = "SELECT Номер_проекта, Номер_заказа  FROM mk;"  # arr_mk = select_SQL(putdb_mk, query5, True)
    F.save_file(r'Z:\Data\for_exel_plan\query5.txt', CSQ.custom_request_c(db_naryad, query5), False)

def update_employee_registr_states_from_1c():
    print(f'======= update_employee_registr_states_from_1c =======')
    def get_empl_states():
        data = None

        code, data = APIERP.get_enum('СостоянияСотрудника',erp_base_name='ERP')
        if code == 200:
            return data

    empl_states = get_empl_states()

    if empl_states == None:
        print(f'update_employee_registr_states_from_1c ERROR data')
        return
    set_empl_erp = {_['Ссылка'] for _ in empl_states['data']}
    DICT_EMPLOYEE_REGISTR_STATES = \
        F.deploy_dict_c(CSQ.custom_request_c(db_users, f"""
                SELECT * FROM employee_registr_states;""", rez_dict=True), 'name')
    set_empl = set(DICT_EMPLOYEE_REGISTR_STATES.keys())
    for_add = set_empl_erp - set_empl
    for_del = set_empl - set_empl_erp
    if for_add:
        CSQ.custom_request_c(db_users, f"""INSERT INTO employee_registr_states (name) VALUES (?)""",list_of_lists_c=[[_] for _ in for_add])
        print(f'    INSERT INTO employee_registr_states:')
        print('\n'.join(list(for_add)))
    if for_del:
        print(f'    DELETE FROM employee_registr_states:')
        for item in for_del:
            print(item)
            CSQ.custom_request_c(db_users, f"""DELETE FROM employee_registr_states WHERE name = '{item}';""",)
    print(f'=======END   update_employee_registr_states_from_1c =======')

def plan_it_form_b24():
    SET_UPLOADED_FIELDS = {'НОМЕР',
                           'Тип',
                           'НАЗВАНИЕ ЗАДАЧИ',
                           'ПП',
                           'Задача',
                           'ОПИСАНИЕ',
                           'ПОСТАНВОЩИК',
                           'ОТВЕТСТВЕННЫЙ',
                           'ДАТА НАЧАЛА',
                           'В месяце',
                           'ДАТА ОКОНЧАНИЯ',
                           'ПРОЦЕНТ ВЫПОЛНЕНИЯ',
                           'ПРОД-НОСТЬ, РАБ. ДН',
                           }
    try:
        bitrix_file_reader = GETPLIT.GetBitrixFiles('89a19d9b18995d279d8e7aa189cfb495')
        data_plan_it = bitrix_file_reader.parse_xlsx_data(sheet_name='Диаграмма Ганта')

        data_plan_it = [{k: v for k, v in _.items() if k in SET_UPLOADED_FIELDS} for _ in data_plan_it]
        F.save_file_pickle("plan_it_form_b24(gen by reiting).pickle", data_plan_it)
    except:
        print(f'ERROR GetBitrixFiles')


def update_dolgn_etap():
    dict_podr_etap = F.deploy_dict_c(CSQ.custom_request_c(db_naryad,f"""SELECT places.Имя || "$" || rab_c.empl_Подразделение as Компания$Подразделение, etaps.name as Этап 
            FROM rab_c INNER JOIN 
            etaps ON etaps.s_num == rab_c.etaps_num, 
            places ON places.poki == rab_c.poki 

""",rez_dict=True,attach_dbs=db_users),"Компания$Подразделение")

    list_empty_dolg_etap = CSQ.custom_request_c(db_naryad,f"""SELECT Производство || "$" || Подразделение as Компания$Подразделение,  этап, Пномер FROM dolgn_etap""",rez_dict=True)

    for item in list_empty_dolg_etap:
        komp_podr = item['Компания$Подразделение']
        if komp_podr in dict_podr_etap:
            if dict_podr_etap[komp_podr] != item['этап']:
                if item['этап'] != None:
                    print(f"""Не обновлено, dolgn_etap есть несоответствие этапа для {komp_podr} : {dict_podr_etap[komp_podr]} FROM rab_c  != {item['этап']} dolgn_etap""")
                    pass
                else:
                    print(
                        f"""Обновлено несоответствие этапа dolgn_etap ({item['Пномер']}) для {komp_podr} : {dict_podr_etap[komp_podr]} FROM rab_c """)
                    CSQ.custom_request_c(db_naryad,f"""UPDATE dolgn_etap SET (этап) = ("{dict_podr_etap[komp_podr]}") WHERE Пномер == {item['Пномер']}""")

def update_vid_rab_from_1c():



    DICT_CTALOGS = {"Новые виды работ": {'Code': '00-000060', 'Description': 'Новые виды работ', 'Ref_Key': 'a99e57e8-4e02-11ed-8469-00d861dd2b4a'},
                    'Келаст': {'Code': '00-000012', 'Description': 'Келаст', 'Ref_Key': '03181fa9-fc30-11e7-80cd-4ccc6a67082d'},
                    'Таткуз': {'Code': '00-000092', 'Description': 'Таткуз', 'Ref_Key': '1ace4f2d-9cfb-11ef-85c2-00d861dd2b4a'},
                    }


    m = ERP.OrdersComposit()

    dict_prices = F.deploy_dict_c(m.get_response(doc_name=r"InformationRegister_РасценкиРаботСотрудников/SliceLast("
                                     r" Condition= Расценка gt 0)",
                                           wet_filtr=f"?$select= ВидРабот_Key, Расценка"), 'ВидРабот_Key')

    prfix = ' or '.join([f"Parent_Key eq guid'{_['Ref_Key']}'" for _ in DICT_CTALOGS.values()])

    list_vid_rab = m.get_response(doc_name='Catalog_ВидыРаботСотрудников',
                                  wet_filtr=f"?$filter= {prfix} &$select=Ref_Key,Description,Parent_Key,DeletionMark")
    dict_catalog = F.deploy_dict_c(DICT_CTALOGS.values(), 'Ref_Key')

    list_mes_vid_rab = CSQ.custom_request_c(db_users, f"SELECT * FROM vid_rab_po_dolg WHERE ref_Key_erp IS NOT NULL",
                                            rez_dict=True)
    dict_mes_vid_rab = F.deploy_dict_c(list_mes_vid_rab, 'ref_Key_erp')
    dict_mes_vid_rab_descr = F.deploy_dict_c(list_mes_vid_rab, 'ERP_name')
    for item in list_vid_rab:

        if item['Ref_Key'] not in dict_mes_vid_rab:
            list_insert = [item['Description'], item['Description'], item['Ref_Key'],
                           dict_catalog[item['Parent_Key']]['Code'], 0, item['DeletionMark']]
            CSQ.custom_request_c(db_users, f"INSERT INTO vid_rab_po_dolg "
                                           f"(Вид_работ,ERP_name,ref_Key_erp,Родитель,Руб_мин,DeletionMark) VALUES "
                                           f" ({CSQ.questions_for_mask(list_insert)})", list_of_lists_c=[list_insert])
        else:
            if dict_mes_vid_rab[item['Ref_Key']]['ERP_name'] != item['Description']:
                CSQ.custom_request_c(db_users, f'UPDATE vid_rab_po_dolg SET '
                                               f' ERP_name = "{item["Description"]}" WHERE ref_Key_erp = "{item["Ref_Key"]}";')
            if dict_mes_vid_rab[item['Ref_Key']]['Родитель'] != dict_catalog[item['Parent_Key']]['Code']:
                CSQ.custom_request_c(db_users, f'UPDATE vid_rab_po_dolg SET '
                                               f' Родитель = "{dict_catalog[item["Parent_Key"]]["Code"]}" WHERE ref_Key_erp = "{item["Ref_Key"]}";')
            if dict_mes_vid_rab_descr[item['Description']]['ref_Key_erp'] != item['Ref_Key']:
                ERP_name =item['Description']
                CSQ.custom_request_c(db_users, f'UPDATE vid_rab_po_dolg SET '
                                               f' ref_Key_erp = "{item["Ref_Key"]}" WHERE ERP_name = "{ERP_name}" and Родитель = "{dict_catalog[item["Parent_Key"]]["Code"]}";')
            if dict_mes_vid_rab[item['Ref_Key']]['DeletionMark'] != item['DeletionMark']:
                CSQ.custom_request_c(db_users, f'UPDATE vid_rab_po_dolg SET '
                                               f' DeletionMark = "{item["DeletionMark"]}" WHERE ref_Key_erp = "{item["Ref_Key"]}";')

            if item['Ref_Key'] in dict_prices:
                if dict_mes_vid_rab[item['Ref_Key']]['Руб_мин'] != dict_prices[item['Ref_Key']]:
                    CSQ.custom_request_c(db_users, f'UPDATE vid_rab_po_dolg SET '
                                                   f' Руб_мин = {dict_prices[item["Ref_Key"]]} WHERE ref_Key_erp = "{item["Ref_Key"]}";')
            else:
                if dict_mes_vid_rab[item['Ref_Key']]['Руб_мин'] != 0:
                    CSQ.custom_request_c(db_users, f'UPDATE vid_rab_po_dolg SET '
                                                   f' Руб_мин = 0 WHERE ref_Key_erp = "{item["Ref_Key"]}";')


def update_emploee_to_db_from_1c(write=False):
    obj = CMS.Emploee_db(F.bdcfg('BD_users'))
    # rezult = obj.update_db(F.bdcfg('Naryad'),False)
    # print(rezult)
    print(f'===== {F.now()} UPDATE EMPLOYEE========')
    print(f'\n')
    obj.update_db(F.bdcfg('Naryad'), write)
    print(f'==============================')
    print(f'\n')
    print(f'\n')


def DEL_update_emploee_to_db(write=False):
    putf = F.tcfg('employee')
    put_db = F.bdcfg('BD_users')
    db_naryad = F.bdcfg('Naryad')
    if F.existence_file_c(putf) == False:
        print(f'Не найден файл employee')
        return
    empolee = F.load_file(putf, ',')
    spis_empolee = []
    for emploer in empolee:
        if emploer[4] == 'Пауэрз':
            spis_empolee.append([emploer[0], emploer[1], emploer[2], emploer[3], emploer[5], emploer[6]])
    if spis_empolee == []:
        print(f'Файл emploee пустой')
        return
    spis_empolee.append(["", "", "", "", "", ""])
    spis_empolee.append(["-", "", "", "-", "-", "-"])
    spis_empolee.append(["+", "", "", "+", "+", "+"])
    # |_| вакант = нет
    # - не нужен = нет
    # + не нужен = есть
    conn, cur = CSQ.connect_bd(put_db)
    spis_tabls = CSQ.get_list_of_tables_c(put_db, conn=conn)
    if 'employee' not in spis_tabls:
        print('employee таблица не найдена')
        frase = """CREATE TABLE employee (
                    Пномер    INTEGER PRIMARY KEY
                      UNIQUE
                      NOT NULL,
                        ФИО       TEXT    NOT NULL,
                    Должность TEXT    NOT NULL,
                    Статус TEXT     DEFAULT []
                            );"""
        CSQ.create_db_sql_c(put_db, frase, conn=conn)
        custom_request_c = """INSERT INTO employee
                                      (ФИО, Должность, Статус)
                                      VALUES (?, ?, ?);"""
        CSQ.custom_request_c(put_db, custom_request_c, list_of_lists_c=[['', '', ''], ['-', '-', ''], ['+', '+', '']],
                             conn=conn)
        print('employee таблица создана')
    print('employee обновление')
    users_db = CSQ.custom_request_c(put_db, '''SELECT * FROM employee WHERE Статус != "Увольнение"''', conn=conn)
    nk_fio = F.num_col_by_name_in_hat_c(users_db, 'ФИО')
    nk_dolg = F.num_col_by_name_in_hat_c(users_db, 'Должность')
    nk_stat = F.num_col_by_name_in_hat_c(users_db, 'Статус')
    nk_pnom = F.num_col_by_name_in_hat_c(users_db, 'Пномер')
    nk_podr = F.num_col_by_name_in_hat_c(users_db, 'Подразделение')
    nk_rejim = F.num_col_by_name_in_hat_c(users_db, 'Режим')
    spis_add = []
    spis_edit = []

    # ================= проверка на увольнение(нет фио в списке)
    for i in range(1, len(users_db)):
        fl_naid = False
        if users_db[i][nk_rejim] == 'Абстракт':
            continue
        for user in spis_empolee:
            fio = ' '.join(user[:3]).strip()
            dolg = user[3].replace('.', '')
            dolg = dolg.replace('  ', ' ')
            if users_db[i][nk_fio] == fio and users_db[i][nk_dolg] == dolg:
                fl_naid = True
                break
        if fl_naid == False:
            if write:
                CSQ.custom_request_c(put_db,
                                     f'''UPDATE employee SET Статус = "Увольнение" WHERE Пномер = {users_db[i][nk_pnom]} ''',
                                     conn=conn)
            print(f'{users_db[i][nk_fio]} {users_db[i][nk_dolg]} уволен')
    # ==================== проверка на устройство(нет фио в бд)
    for user in spis_empolee:
        fio = ' '.join(user[:3]).strip()
        dolg = user[3].replace('.', '')
        dolg = dolg.replace('  ', ' ')
        podr = user[4]
        fl_naid = False
        for user_db in users_db:
            if fio == user_db[nk_fio] and dolg == user_db[nk_dolg] and user_db[nk_stat] == '':
                fl_naid = True
                break
        if fl_naid == False:
            spis_add.append([fio, dolg, '', podr])
            print(f'Добавлен {fio} {dolg} {podr}')

    custom_request_c = """INSERT INTO employee
                              (ФИО, Должность, Статус, Подразделение)
                              VALUES (?, ?, ?, ?);"""
    if write:
        if len(spis_add) > 0:
            CSQ.custom_request_c(put_db, custom_request_c, list_of_lists_c=spis_add, conn=conn)
    # ==================== проверка на режим и подразделение
    for user in spis_empolee:
        fio = ' '.join(user[:3]).strip()
        dolg = user[3].replace('.', '')
        dolg = dolg.replace('  ', ' ')
        podr = user[4]
        regim = user[5]

        for user_db in users_db:
            if user_db[nk_stat] == 'Увольнение' or user_db[nk_rejim] == 'Абстракт':
                continue
            if fio == user_db[nk_fio] and dolg == user_db[nk_dolg] and user_db[nk_stat] == '':
                if write:
                    if podr != user_db[nk_podr]:
                        CSQ.custom_request_c(put_db,
                                             f"""UPDATE employee SET Подразделение = "{podr}"
                                             WHERE Пномер = {user_db[nk_pnom]}""")
                    if regim != user_db[nk_rejim]:
                        CSQ.custom_request_c(put_db,
                                             f"""UPDATE employee SET Режим = "{regim}" 
                                             WHERE Пномер = {user_db[nk_pnom]}""")
                else:
                    if podr != user_db[nk_podr]:
                        spis_edit.append(f'{fio} Подразд. Было {user_db[nk_podr]}     Стало {podr}')
                    if regim != user_db[nk_rejim]:
                        spis_edit.append(f'{fio} Режим. Было {user_db[nk_rejim]}     Стало {regim}')
                break
    if not write:
        print(pprint.pformat(spis_edit))
    CSQ.close_bd(conn)

    if write:
        list_from_empl = CSQ.custom_request_c(put_db,
                                              f"""SELECT DISTINCT Должность, Подразделение, Компания FROM employee WHERE Подразделение != '' and Подразделение not in ("+","-")""",
                                              rez_dict=True)
        list_from_etaps = CSQ.custom_request_c(db_naryad,
                                               f"""SELECT DISTINCT Должность, Подразделение, Производство FROM dolgn_etap """,
                                               rez_dict=True)
        list_add = []
        for item in list_from_empl:
            fl_naid = False
            for item_et in list_from_etaps:
                if item['Должность'] == item_et['Должность'] and item['Подразделение'] == item_et['Подразделение'] and item['Компания'] == item_et['Производство']:
                    fl_naid = True
                    break
            if fl_naid == False:
                list_add.append([item['Должность'], item['Подразделение'], item['Компания']])
        if len(list_add) > 0:
            CSQ.custom_request_c(db_naryad, f"""INSERT INTO dolgn_etap
                              (Должность, Подразделение, Производство)
                              VALUES (?, ?, ?);""", list_of_lists_c=list_add)


# =================for db.kplan releases_from_erp=============================
def upload_two_years_docs_releases(month=False):
    def date_fix(date_erp):
        return F.datetostr(F.strtodate(date_erp, "%Y-%m-%dT%H:%M:%S"))

    def get_list_nomen(step, list_vids):
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
            nomen = m.get_response(doc_name='Catalog_Номенклатура',
                                   wet_filtr=f"?$filter=({str_vids}) &$select=Ref_Key,ВидНоменклатуры_Key,Code,"
                                             f"Артикул,Description,DeletionMark")
            for item in nomen:
                rez.append(item)
        return rez

    print(f'===== {F.now()} UPDATE RELEASES_FROM_ERP========')
    print(f'\n')

    dict_releases_mes = F.deploy_dict_c(CSQ.custom_request_c(db_kplan, f"""SELECT s_num,
     ref_key FROM releases_from_erp""", rez_dict=True), 'ref_key')

    m = ERP.OrdersComposit()
    name_tmp_file_releases = CMS.tmp_dir() + F.sep() + 'tmp_file_dict_docs_vip.pickle'
    name_tmp_file_dict_nomens = CMS.tmp_dir() + F.sep() + 'name_tmp_file_dict_nomens.pickle'
    if F.existence_file_c(name_tmp_file_releases):
        dict_docs_vip = F.load_file_pickle(name_tmp_file_releases)
        dict_nomens = F.load_file_pickle(name_tmp_file_dict_nomens)
    else:
        list_vids_names = m.get_response(doc_name='Catalog_ВидыНоменклатуры',
                                         wet_filtr=f"?$filter=Parent_Key eq guid'f193e0db-9ed7-11e7-80c5-4ccc6a67082d'&$select= "
                                                   f" Description, Ref_Key")
        ADDITIONAL_VIDS = {'6408f542-48c8-11ee-84b8-00d861dd2b4a',
                           '334d2619-7c39-11ed-8472-00d861dd2b4a',
                           '50089bf2-917d-11ed-8475-00d861dd2b4a',
                           'a515ce0f-72f1-11ec-8464-00d861dd2b4a',
                           '12a92ef4-131c-11ed-8468-00d861dd2b4a',
                           '3fdaec00-2ea1-11ed-8469-00d861dd2b4a',
                           '7f67988e-82dd-11ea-8437-00d861c603dc',
                           'cb6da273-0585-11e8-80cd-4ccc6a67082d',
                           'a48c91cf-48c8-11ee-84b8-00d861dd2b4a',
                           'ff24f7a2-cb33-11ee-8505-00d861dd2b4a'
                           }
        list_vids_refs = [_['Ref_Key'] for _ in list_vids_names]
        for add_vid in ADDITIONAL_VIDS:
            list_vids_refs.append(add_vid)
        dict_nomens = F.deploy_dict_c(get_list_nomen(5, list_vids_refs), 'Ref_Key')
        ref_key_skl = m.get_response(doc_name='Catalog_Склады',
                                     wet_filtr=f"?$filter=DeletionMark eq false and Description eq "
                                               f" 'Склад готовой продукции Пауэрз'&$select= Ref_Key")[0]['Ref_Key']
        this_year = F.now("%Y")
        if month == False:

            begin_year = F.start_end_dates_c(F.date_add_days(F.now(), -365), format_out="%Y-%m-%d 00:00:01")[0]
            last_year = F.datetostr(F.strtodate(begin_year), "%Y")

            docs_vip = m.get_response(doc_name='Document_ДвижениеПродукцииИМатериалов',
                                      wet_filtr=f"?$filter="
                                                f"DeletionMark eq false and (year(Date) eq {last_year} or year(Date) eq {this_year}) "
                                                f" and Статус eq 'Принято' and ХозяйственнаяОперация eq 'ПередачаПродукцииИзПроизводства' and Получатель eq cast(guid'{ref_key_skl}','Catalog_Склады')&$"
                                                f"select= Ref_Key, Number, Date, Комментарий, Распоряжение, Товары/Номенклатура_Key, Товары/Количество")  #
        else:
            this_month = F.valm(F.now("%m"))
            last_month = F.valm(F.datetostr(F.add_months(F.now(''), -1), "%m"))
            docs_vip = m.get_response(doc_name='Document_ДвижениеПродукцииИМатериалов',
                                      wet_filtr=f"?$filter="
                                                f"DeletionMark eq false and year(Date) eq {this_year} and (month(Date) eq {this_month} or month(Date) eq {last_month}) "
                                                f" and Статус eq 'Принято' and ХозяйственнаяОперация eq 'ПередачаПродукцииИзПроизводства' and Получатель eq cast(guid'{ref_key_skl}','Catalog_Склады')&$"
                                                f"select= Ref_Key, Number, Date, Комментарий, Распоряжение, Товары/Номенклатура_Key, Товары/Количество")  #
        if isinstance(docs_vip, str):
            print(f'         !!!!Данные из Document_ДвижениеПродукцииИМатериалов не получены {docs_vip}')
            return

        dict_docs_vip = F.deploy_dict_c(docs_vip,
                                        'Ref_Key')

        F.save_file_pickle(name_tmp_file_releases, dict_docs_vip)
        F.save_file_pickle(name_tmp_file_dict_nomens, dict_nomens)
    c_er = 0
    for k, doc in dict_docs_vip.items():
        c_er += 1
        # print(f'{c_er}/{len(dict_docs_vip)}')
        if k in dict_releases_mes:
            continue
        ref_key_etap = doc['Распоряжение']
        ref_key_zp = m.get_response(doc_name='Document_ЭтапПроизводства2_2',
                                    wet_filtr=f"?$filter=Ref_Key eq guid'{ref_key_etap}'&$select=Распоряжение_Key")[0][
            'Распоряжение_Key']  # filter=Распоряжение eq cast(guid'2212fdef-5a87-11ed-846a-00d861dd2b4a' ,'Document_ЭтапПроизводства2_2')
        zp = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                            wet_filtr=f"?$filter=Ref_Key eq guid'{ref_key_zp}'&$select= Number,Date")[0]
        list_add_db = []
        msg_add_kt = []
        msg_add_pw = []

        for i, obj in enumerate(doc['Товары']):
            dict_docs_vip[k]['Товары'][i]['Description'] = ''
            if obj['Номенклатура_Key'] not in dict_nomens:
                print(f"{obj['Номенклатура_Key']} не найден в выборке по видам")
                print(m.get_response(doc_name='Catalog_Номенклатура',
                                     wet_filtr=f"?$filter=Ref_Key eq guid'{obj['Номенклатура_Key']}' &$select=Ref_Key,ВидНоменклатуры_Key,Code,"
                                               f"Артикул,Description,DeletionMark"))
                continue

            tmp_dict_add = {
                "ref_key": k,
                "number": doc['Number'],
                "date_rel": date_fix(doc['Date']),
                "comment": doc['Комментарий'],
                "py_zp": zp['Number'],
                "zp_date": date_fix(zp['Date']),
                "nomen_name": dict_nomens[obj['Номенклатура_Key']]['Description'],
                "nomen_count": obj['Количество'],
            }
            list_add_db.append(tmp_dict_add)
            chat = 'chat21323'  # pw
            list_poz_nom_name_napr = CSQ.custom_request_c(db_kplan, f"""SELECT Пномер FROM plan INNER JOIN 
             пл_оуп ON пл_оуп.НомПл = plan.Пномер WHERE 
             пл_оуп.Номенклатура_ЕРП = "{dict_nomens[obj['Номенклатура_Key']]['Description']}" AND plan.Направление_деятельности = 10 """,
                                                          rez_dict=True)
            if list_poz_nom_name_napr != None and len(list_poz_nom_name_napr) > 0:
                chat = 'chat17309'  # kt
            if chat == 'chat21323':
                msg_add_pw.append(f"   {dict_nomens[obj['Номенклатура_Key']]['Description']} - {obj['Количество']} шт.")
            else:
                msg_add_kt.append(f"   {dict_nomens[obj['Номенклатура_Key']]['Description']} - {obj['Количество']} шт.")
        if len(list_add_db):
            list_add_db_list = F.list_of_dicts_to_list_of_lists(list_add_db)[1:]
            CSQ.custom_request_c(db_kplan, f"""INSERT INTO releases_from_erp (ref_key, number, date_rel, comment, py_zp, zp_date, nomen_name, nomen_count) 
                            VALUES ({CSQ.questions_for_mask(list_add_db_list[0])})""", list_of_lists_c=list_add_db_list)
            str_msg_add_kt = '\n'.join(msg_add_kt)
            str_msg_add_pw = '\n'.join(msg_add_pw)
            if len(msg_add_kt) > 0:
                full_msg = f"Выпуск готов. Передача продукции из производства {doc['Number']} от {date_fix(doc['Date'])}:\n{str_msg_add_kt}"
                CMS.send_info_mk_b24(None, full_msg, 'chat17309')
            if len(msg_add_pw) > 0:
                full_msg = f"Выпуск готов. Передача продукции из производства {doc['Number']} от {date_fix(doc['Date'])}:\n{str_msg_add_pw}"
                CMS.send_info_mk_b24(None, full_msg, 'chat21323')
    F.delete_file_c(name_tmp_file_releases)
    F.delete_file_c(name_tmp_file_dict_nomens)
    print(f'==============================')
    print(f'\n')
    print(f'\n')

    return


# ========================calc report_by_execute_month_plan=================
def calc_execute_month_plan():
    month_str = F.now("%Y-%m-01")
    print(f'генерация месячного отчета')
    rez_spis = reports.ispoln_pl_month(db_kplan, db_resxml, db_naryad, DICT_PROFESSIONS, DICT_VID_RABOT, month_str,
                                       from_reiting_py=True)
    if not rez_spis:
        print(f'ошибка при генерации месячного отчета')
        return
    print(f'сохранение месячного отчета')
    dir_z = r'Z:\Data\viewer'
    F.save_file_pickle(dir_z + F.sep() + 'isp_month_' + month_str.replace('-', '_') + f'.pickle', rez_spis)
    app = QtWidgets.QApplication(['', '--no-sandbox'])
    tbl_qt = QtWidgets.QTableWidget()
    CQT.fill_wtabl_old_c(None, rez_spis, tbl_qt, separ='', isp_hat_c=True, max_vis_row=500)
    tbl_color = reports.oform_tbl_execute_monh_plan(tbl_qt)
    F.save_file_pickle(dir_z + F.sep() + 'tbl_color_isp_month_' + month_str.replace('-', '_') + f'.pickle', tbl_color)
    wb_name = 'isp_month_' + month_str.replace('-', '_')
    ws_name = '1'
    file_path = CEX.save_table_colour_openpyxl(tbl_qt, dir_z, wb_name, ws_name) #01.09.25
    print(f'======= СОХРАНЕНИЕ МЕСЯЧНОГО ОТЧЕТА УСПЕШНО ======')


# ========================calc обновление статусов КПЛ ТЧ=================
def check_and_calc_plan_kpl():
    print(f'===== {F.now()} UPDATE КПЛ МЕС И ERP========')

    # =================================UDATE_KPL_INSERT_ZP_TABLE=======================
    def FIX_FIELDS_ADD_ZNPR():
        # CSQ.custom_request_c(db_kplan, 'DELETE FROM знпр WHERE s_num > 0')

        list_proj = CSQ.custom_request_c(db_kplan, f"""SELECT 
                пл_оуп.Дата_заявки_на_произв, 
                пл_оуп.№ERP, 
                пл_оуп.№проекта, 
                plan.Статус_поз_ЕРП, 
                plan.Заказ_клиента, 
                пл_оуп.Дата_отгрузки_ПУ, 
                plan.ЗП_келаст_КЭ, 
                plan.Этапы_ЕРП,
                пл_оуп.НомПл  
                                FROM пл_топ INNER JOIN
                           plan ON plan.Пномер = пл_топ.НомПл,
                           пл_оуп ON пл_оуп.НомПл = пл_топ.НомПл
                           ;""", rez_dict=True)

        dict_zp_mes = F.deploy_dict_c(CSQ.custom_request_c(db_kplan, f"""SELECT 
                s_num, Год || "$" || №ERP as pyear 
                                FROM знпр 
                           ;""", rez_dict=True), 'pyear')

        dict_zp = dict()
        for item in list_proj:
            if 'ПУ' not in item["№ERP"]:
                continue
            py = item["№ERP"]
            if r'Отдел технолога' in item["№ERP"]:
                py = item["№ERP"].split(F.sep())[-1]
                CSQ.custom_request_c(db_kplan, f"""UPDATE пл_оуп SET №ERP = "{py}" WHERE НомПл = {item["НомПл"]}""")
            year = F.datetostr(F.strtodate(item['Дата_заявки_на_произв']), "%Y")
            pyear = f'{year}${py}'
            if pyear in dict_zp:
                continue
            dict_zp[pyear] = item
        list_to_add = []
        m = ERP.OrdersComposit()
        for pyear, vals in dict_zp.items():
            if pyear not in dict_zp_mes:
                year, py = pyear.split('$')
                ref_Key_py_from_erp = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                                     wet_filtr=f"?$filter= year(Date) eq {year} and Number eq '{py}'&$select=Ref_Key")
                if len(ref_Key_py_from_erp):
                    ref_Key_py = ref_Key_py_from_erp[0]['Ref_Key']
                    list_to_add.append(
                        [int(year), vals['Дата_заявки_на_произв'], py, vals['№проекта'], vals['Статус_поз_ЕРП'],
                         vals['Заказ_клиента'], vals['Дата_отгрузки_ПУ'], vals['ЗП_келаст_КЭ'], vals['Этапы_ЕРП'],
                         ref_Key_py])
                else:
                    print(pyear)
        if len(list_to_add):
            CSQ.custom_request_c(db_kplan, f"""INSERT INTO знпр (Год, 
                Дата_заявки_на_произв, 
                №ERP, 
                №проекта, 
                Статус_поз_ЕРП, 
                Заказ_клиента, 
                Дата_отгрузки_ПУ, 
                ЗП_келаст_КЭ, 
                Этапы_ЕРП,
                Ref_Key_py) VALUES ({CSQ.questions_for_mask(list_to_add[0])})""", list_of_lists_c=list_to_add)

        dict_zp_mes = F.deploy_dict_c(CSQ.custom_request_c(db_kplan, f"""SELECT 
            s_num, Год || "$" || №ERP as pyear 
                                    FROM знпр 
                               ;""", rez_dict=True), 'pyear')
        i = 0
        for poz in list_proj:
            print(f'{i}/{len(list_proj)}')
            i += 1
            if 'ПУ' not in poz["№ERP"]:
                CSQ.custom_request_c(db_kplan, f"""UPDATE пл_оуп SET (Пномер_ЗП) = (0) WHERE НомПл = {poz['НомПл']}""")
                continue
            year = F.datetostr(F.strtodate(poz['Дата_заявки_на_произв']), "%Y")
            pyear = f'{year}${poz["№ERP"]}'

            if pyear in dict_zp_mes:
                s_num = dict_zp_mes[pyear]
                CSQ.custom_request_c(db_kplan,
                                     f"""UPDATE пл_оуп SET (Пномер_ЗП) = ({s_num}) WHERE НомПл = {poz['НомПл']}""")
        # ============================================================================

    # FIX_FIELDS_ADD_ZNPR()

    # ==================================CHECK_STATE_RES_ERP==============================

    list_kod_res = CSQ.custom_request_c(db_kplan, f"""SELECT пл_оуп.Пномер_ЗП, 
     пл_топ.НомПл, пл_топ.Спецификация_код_ЕРП,
    пл_топ.Спецификация_ЕРП,
     пл_топ.Рес_действует, 
     '' as 'Статус', 
     '' as 'Description' 
     FROM пл_топ INNER JOIN
    пл_оуп ON пл_оуп.НомПл = пл_топ.НомПл, 
    plan ON plan.Пномер = пл_топ.НомПл, 
    status_poz ON status_poz.Пномер = plan.Статус 
    WHERE Спецификация_код_ЕРП != '' AND status_poz.Имя IN (
    "Подготовка",
    "Приостановлена",
    "К производству",
    "Перепроверка");""", rez_dict=True)

    list_py_mes = CSQ.custom_request_c(db_kplan, f"""SELECT s_num, Год, Статус_поз_ЕРП, 
        №ERP, Дата_заявки_на_произв,Ref_Key_py, Дата_отгрузки_ПУ, Комментарий  FROM знпр WHERE Статус_поз_ЕРП != "Закрыт" and s_num > 0;""",
                                       rez_dict=True)

    dict_py_mes = F.deploy_dict_c(list_py_mes, 's_num')

    for item in list_kod_res:
        item['Спецификация_код_ЕРП'] = F.clear_str_ntrs(item['Спецификация_код_ЕРП'])

    m = ERP.OrdersComposit()

    def get_list_res(list_kod_res, step=5):
        rez = dict()
        for i in range(0, len(list_kod_res), step):
            tmp_list_kod_res = []
            for j in range(i, i + step):
                if j >= len(list_kod_res):
                    break
                if list_kod_res[j]['Спецификация_код_ЕРП'] != '':
                    tmp_list_kod_res.append(list_kod_res[j]['Спецификация_код_ЕРП'])
            list_kod_res_str = [f"Code eq '{_}'" for _ in tmp_list_kod_res]
            str_ = " or ".join(list_kod_res_str)
            resp = m.get_response(doc_name='Catalog_РесурсныеСпецификации',
                                  wet_filtr=f"?$filter=({str_}) &$select=Статус, Description,Code")
            for item in resp:
                key = F.clear_str_ntrs(item['Code'])
                rez[key] = item
        return rez

    # m.get_response(doc_name='Catalog_РесурсныеСпецификации',
    #               wet_filtr=f"?$filter=Code eq '00-047473' &$select=Статус, Description,Code")
    def get_not_poz_valid(list_kod_res, list_poz_form_erp, s_num_py):
        list_not_valid = []
        for zp in list_poz_form_erp:
            for poz in zp['Продукция']:
                name_poz = m.get_response(doc_name='Catalog_Номенклатура',
                                          wet_filtr=f"?$filter=Ref_Key eq guid'{poz['Номенклатура_Key']}'&$select=Description")
                for item in list_kod_res:
                    if item["Спецификация_ЕРП"] == name_poz and item['Пномер_ЗП'] == s_num_py:
                        if item['Рес_действует'] == 0:
                            list_not_valid.append(item['Спецификация_ЕРП'])
        return list_not_valid

    rezult_form_erp = get_list_res(list_kod_res, 10)
    for resoutse_mes_item in list_kod_res:
        if resoutse_mes_item['Спецификация_код_ЕРП'] in rezult_form_erp:
            resoutse_mes_item['Description'] = rezult_form_erp[resoutse_mes_item['Спецификация_код_ЕРП']]['Description']
            state_str = rezult_form_erp[resoutse_mes_item['Спецификация_код_ЕРП']]['Статус']
            if state_str == 'Действует':
                resoutse_mes_item['Статус'] = 1
            else:
                resoutse_mes_item['Статус'] = 0
    for i, resoutse_mes_item in enumerate(list_kod_res):
        if resoutse_mes_item['Description'] != resoutse_mes_item['Спецификация_ЕРП']:
            CSQ.custom_request_c(db_kplan, f"""UPDATE пл_топ SET (Спецификация_ЕРП) 
             = ("{resoutse_mes_item['Description']}") WHERE НомПл = {resoutse_mes_item['НомПл']}""")
            obj_msg = CMS.Msg_b24(db_kplan, db_naryad, db_resxml, db_users, resoutse_mes_item['НомПл'])
            obj_msg.send_msg('fix_name_res',
                             f"По рес. код {resoutse_mes_item['Спецификация_код_ЕРП']} исправлено наименование в МЕС."
                             f'\nБыло "{resoutse_mes_item["Спецификация_ЕРП"]}"\nСтало "{resoutse_mes_item["Description"]}"')
            list_kod_res[i]['Спецификация_ЕРП'] = resoutse_mes_item['Description']
        if resoutse_mes_item['Статус'] != resoutse_mes_item['Рес_действует']:
            CSQ.custom_request_c(db_kplan, f"""UPDATE пл_топ SET (Рес_действует) 
                         = ({resoutse_mes_item['Статус']}) WHERE НомПл = {resoutse_mes_item['НомПл']}""")
            if resoutse_mes_item['Статус'] == 1:
                list_kod_res[i]['Рес_действует'] = resoutse_mes_item['Статус']
                obj_msg = CMS.Msg_b24(db_kplan, db_naryad, db_resxml, db_users, resoutse_mes_item['НомПл'])

                obj_msg.send_msg('state_valid_kod_res_recalc')
                if resoutse_mes_item['Пномер_ЗП'] != 0 and resoutse_mes_item['Пномер_ЗП'] in dict_py_mes:
                    ref_key_pu = dict_py_mes[resoutse_mes_item['Пномер_ЗП']]['Ref_Key_py']
                    list_poz_form_erp = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                                       wet_filtr=f"?$filter= Ref_Key eq guid'{ref_key_pu}'&$select=Продукция/Номенклатура_Key")
                    list_not_valid_poz = get_not_poz_valid(list_kod_res, list_poz_form_erp,
                                                           resoutse_mes_item['Пномер_ЗП'])

                    if len(list_not_valid_poz) == 0:
                        obj_msg.send_msg('state_valid_kod_res_all')
                    else:
                        obj_msg.send_msg('state_valid_kod_res_one',
                                         pprint.pformat(list_not_valid_poz))
                else:
                    obj_msg.send_msg('state_valid_kod_res_one_wo_py')

    # ==================================CHECK_STATE_POZ_ERP==============================

    list_proj = list_py_mes
    print()
    m = ERP.OrdersComposit()
    for item in list_proj:
        resp = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                              wet_filtr=f"?$filter= Ref_Key eq guid'{item['Ref_Key_py']}'&$select=Статус, Date, ДатаПотребности, Комментарий")
        if len(resp) == 0:
            print(f"Ошибка загрузки Document_ЗаказНаПроизводство2_2  по Ref_Key eq guid'{item['Ref_Key_py']}")
            continue
        if 'Статус' in resp[0]:
            state = resp[0]['Статус']
            if item['Статус_поз_ЕРП'] != state:
                if state == 'КПроизводству':
                    list_poz = CSQ.custom_request_c(db_kplan, f"""SELECT plan.Статус, plan.Пномер  FROM plan 
                    INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер WHERE пл_оуп.Пномер_ЗП == {item['s_num']}""",
                                                    rez_dict=True)
                    num_kpl_poz = False
                    for poz in list_poz:
                        if poz['Статус'] in (1, 2):
                            CSQ.custom_request_c(db_kplan,
                                                 f"""UPDATE plan SET (Статус) = (7) WHERE Пномер = {poz['Пномер']};""")
                            num_kpl_poz = poz['Пномер']

                    if num_kpl_poz:
                        obj_msg = CMS.Msg_b24(db_kplan, db_naryad, db_resxml, db_users, num_kpl_poz)
                        obj_msg.send_msg('state_poz_for_production')

                upd = True
                if item['s_num'] == 1224: #просьба Козырькова для теста в келаст от 05.09.2025
                    if F.now('') < F.strtodate('2025-09-12 14:00:20'):
                        upd = False
                if upd:
                    CSQ.custom_request_c(db_kplan,
                                     f"""UPDATE знпр SET (Статус_поз_ЕРП) = ("{state}") WHERE s_num = {item['s_num']};""")

        msg1 = f'В ЗП {item["№ERP"]} от {item["Год"]}г. изменились  данные\n'
        msg2 = f'\nСпециалисту ПДО необходимо провести ревизию'
        id_chat = 'chat48346'
        date = F.datetostr(F.strtodate(resp[0]['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y-%m-%d")
        date_otgr = F.datetostr(F.strtodate(resp[0]['ДатаПотребности'], "%Y-%m-%dT%H:%M:%S"), "%Y-%m-%d")
        if item['Дата_заявки_на_произв'] != date:
            CSQ.custom_request_c(db_kplan,
                                 f"""UPDATE знпр SET (Дата_заявки_на_произв) = ("{date}") WHERE s_num = {item['s_num']};""")
            CSQ.custom_request_c(db_kplan,
                                 f"""UPDATE пл_оуп SET (Дата_заявки_на_произв) = ("{date}") WHERE Пномер_ЗП = {item['s_num']};""")

            # CMS.send_info_mk_b24(None,msg1 + f"Дата_заявки_на_произв\n    было {item['Дата_заявки_на_произв']}\n    стало {date}" + msg2,id_chat)

        if resp[0]['Комментарий'] != item['Комментарий']:
            CSQ.custom_request_c(db_kplan,
                                 f"""UPDATE знпр SET (Комментарий) = ("{resp[0]['Комментарий']}") WHERE s_num = {item['s_num']};""")
            # CMS.send_info_mk_b24(None,
            #                     msg1 + f"Комментарий\n    было {item['Комментарий']}\n    стало {resp[0]['Комментарий']}" + msg2,
            #                     id_chat)
        if date_otgr != item['Дата_отгрузки_ПУ']:
            CSQ.custom_request_c(db_kplan,
                                 f"""UPDATE знпр SET (Дата_отгрузки_ПУ) = ("{date_otgr}") WHERE s_num = {item['s_num']};""")
            CSQ.custom_request_c(db_kplan,
                                 f"""UPDATE пл_оуп SET (Дата_отгрузки_ПУ) = ("{date_otgr}") WHERE Пномер_ЗП = {item['s_num']};""")
            CMS.send_info_mk_b24(None,
                                 msg1 + f"Дата_отгрузки_ПУ\n    было {item['Дата_отгрузки_ПУ']}\n    стало {date_otgr}" + msg2,
                                 id_chat)
    # ===================================================================================

    # ==================================CHECK_ETAPS_ERP==============================
    list_proj = CSQ.custom_request_c(db_kplan, f"""SELECT s_num, Статус_поз_ЕРП, 
      №ERP, Дата_заявки_на_произв, Ref_Key_py 
                    FROM знпр 
               WHERE s_num > 0 and Статус_поз_ЕРП != '' and Этапы_ЕРП = {1}  and  №ERP != "-";""", rez_dict=True)  #

    #conn_b24 = CMS.Msg_b24.make_conn()
    m = ERP.OrdersComposit()
    for item in list_proj:
        py = item['№ERP']
        s_num = item['s_num']
        if py == '-':
            continue
        ref_key_py = item['Ref_Key_py']
        resp = CMS.make_dict_etaps_from_erp(m,ref_key_py)
        CMS.update_data_etaps_from_erp(db_kplan,resp,s_num)

    # ================================================================================


db_users = F.bdcfg('BD_users')
db_naryad = F.bdcfg('Naryad')
db_act = F.bdcfg('BDact')
BD_dse = F.scfg('BD_dse')
db_mater = F.bdcfg('nomenklatura_erp')
spis_empolee = F.load_file(F.tcfg('employee'))
db_kplan = F.bdcfg('DB_kplan')
db_resxml = F.bdcfg('db_resxml')
# DICT_EMPLOEE = CMS.dict_emploee(db_users)
DICT_EMPLOEE = CMS.dict_emploee_full(db_users)
custom_request_c = f'''SELECT * FROM professions INNER JOIN vid_rab_po_dolg 
ON vid_rab_po_dolg.Вид_работ = professions.вид_работ,
 group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan WHERE Вкл = 1 and group_vid_rab_for_plan.composite = 0'''
SPIS_prof = CSQ.custom_request_c(db_users, custom_request_c, hat_c=False, rez_dict=True)
LIST_PROFESSIONS = SPIS_prof
DICT_PROFESSIONS = F.deploy_dict_c(SPIS_prof, 'код')
DICT_VID_RABOT = F.deploy_dict_c(SPIS_prof, 'вид_работ')
DICT_PRICE_BRAK = CMS.DICT_PRICE_BRAK(db_naryad)
data = F.now()

CALC_SINCHRONS = True
CALC_user_calendar = True

metka = ''

counter_timer_middle = 3600 * 24
# count_reset_middle = 3600 * 24  # каждые 24 часа обновление
count_reset_middle = 3600 * 0.5  # каждые 24 часа обновление

counter_timer = 3600 * 0.5
count_reset = 3600 * 0.5  # каждые 0.5 часа обновление

vrem = 600

#update_vid_rab_from_1c()#TODO Виды работ для моямсина
#quit()
#user_calendar.main()
#quit()
#nomen_erp.obn_mat_erp_file(db_mater)
while True:
    counter_timer += vrem
    counter_timer_middle += vrem
    print(f'{F.now()} counter_mater: {counter_timer}/{count_reset}')
    print(f'{F.now()} counter_mater: {counter_timer_middle}/{count_reset_middle}')
    current_hour = datetime.datetime.now().hour
    if counter_timer_middle >= count_reset_middle and current_hour >= 0 and current_hour <= 5: #01.09.25
        counter_timer_middle = 0
        ## обновление dolgn_etap
        try:
            if CALC_SINCHRONS:
                update_dolgn_etap()
        except:
            print(f'Не удачная попытка обновление dolgn_etap')
        ## обновление видов работ
        try:
            if CALC_SINCHRONS:
                update_vid_rab_from_1c()
        except:
            print(f'Не удачная попытка обновление видов работ')

        ## обновление сотрудников
        try:
            if CALC_SINCHRONS:
                update_employee_registr_states_from_1c()
                update_emploee_to_db_from_1c(True)
            if CALC_user_calendar:

                user_calendar.main()
        except:
            print(f'Не удачная попытка обновления сотрудников')

        # обновление месячного отчета
        try:
            if CALC_SINCHRONS:
                print('\n')
                calc_execute_month_plan()
            pass
        except:
            print(f'Не удачная попытка обновления месячного отчета')


        ## скачивание плана ИТ Б24
        plan_it_form_b24()

    if counter_timer >= count_reset:
        counter_timer = 0

        # обновление статусов КПЛ ТЧ
        # check_and_calc_plan_kpl()
        try:
            if CALC_SINCHRONS:
                print('\n')
                check_and_calc_plan_kpl()
            pass
        except:
            print(f'Не удачная попытка обновления статусов КПЛ ТЧ')

        # обновление материалов
        try:
            if CALC_SINCHRONS:
                print('\n')
                nomen_erp.obn_mat_erp_file(db_mater)
            pass
        except:
            print(f'Не удачная попытка обновления материалов')

        # обновление выпусков db.kplan releases_from_erp
        try:
            if CALC_SINCHRONS:
                upload_two_years_docs_releases(True)
            pass
        except:
            print(f'Не удачная попытка обновления выпусков')

    try:
        print(f'#==={F.now()}====#')
        print(f'Расчет производительности')

        # export_data_for_excel_plan()

        # VIR.conversion_file_from_zp_into_picle_c('O:\Производство Powerz\Отдел управления\табель УРВ' + F.sep() + 'employeeFOT.txt',
        #                               F.scfg('BDact') + F.sep() + 'tmp_empl_fant.pickle')

        metka = 'подготовка расчета производительности '
        itog, metka, dict_masters = CMS.calc_productivity_c(data, db_users, db_naryad, db_act, db_kplan, DICT_EMPLOEE,
                                                            DICT_PRICE_BRAK, CALC_BASE_ONLY_PREM=True,
                                                            podrazdelenie='Сборочный цех Производства',
                                                            organization='Пауэрз')

        if itog == '':
            print(f'Ошибка {metka}')
            continue
        [_.pop('Сет_нарядов', None) for _ in itog]
        itog_wo_set_nar = itog
        F.write_json_c(itog_wo_set_nar, r"Z:\Data\Virabotka_sbdn.json", False)

        # arr_msg = F.open_file_c(r"Z:\ProdSoft\Data\Создание\Data\Msg_tel.txt",utf8=True)
        list_masters_brak = [[dict_masters[_]['Подразделение'], _, str(round(dict_masters[_]['Вычет']))] for _ in
                             dict_masters.keys()]
        list_masters_brak.insert(0, ['Подразделение', 'ФИО', 'Вычет, %'])
        F.write_json_c(list_masters_brak, r"Z:\Data\msg_sbdn.json", False)
        arr_msg = F.list_txt_table_c(list_masters_brak)

        XML_mssg = []
        XML_mssg.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        XML_mssg.append('<Root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">')
        for i in arr_msg:
            XML_mssg.append('        <msg>' + i + "</msg>")
        XML_mssg.append('</Root>')
        F.write_file_c(r"Z:\Data\msg_sbdn.xml", XML_mssg, '', False, True)
        F.write_file_c(r"O:\Журналы и графики\Ведомости для передачи\msg_sbdn.xml", XML_mssg, '', False, True)
        try:
            F.write_file_c(r"C:\DB_srv\msg_sbdn.xml", XML_mssg, '', False, True)
        except:
            print(fr'Ошибка выгрузки C:\DB_srv\msg_sbdn.xml')
            pass

        metka = 'формировка таблицы'
        XML = []
        XML.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        XML.append('<Root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">')
        XML.append("<date>" + F.now("%d.%m.%Y %H:%M:%S") + "</date>")
        spis_isp_kol = ['fio', 'dol', 'prc', 'e_prc']
        for i in range(len(itog_wo_set_nar)):
            XML.append('    <Emploe>')
            if itog_wo_set_nar[i]["Итог"] < 300:
                XML.append('        <' + spis_isp_kol[
                    0] + '>' + f'{str(itog_wo_set_nar[i]["ФИО"])}            (Итог {str(itog_wo_set_nar[i]["Итог"])}%)</{spis_isp_kol[0]}>')
                XML.append(
                    '        <' + spis_isp_kol[1] + '>' + str(itog_wo_set_nar[i]["Должность"]) + "</" + spis_isp_kol[
                        1] + ">")
                XML.append(
                    '        <' + spis_isp_kol[2] + '>' + str(itog_wo_set_nar[i]["кг."]) + "</" + spis_isp_kol[2] + ">")
                XML.append(
                    '        <' + spis_isp_kol[3] + '>' + str(round(F.valm(itog_wo_set_nar[i]['Брак']), 1)) + "</" +
                    spis_isp_kol[3] + ">")
            XML.append('    </Emploe>')
        XML.append('</Root>')
        F.write_file_c(r"Z:\Data\Virabotka_sbdn.xml", XML, '', False, True)
        # F.write_file_c(r"Z:\Data\Virabotka_sbdn.txt",itog_wo_set_nar,'|')
        F.write_file_c(r"O:\Журналы и графики\Ведомости для передачи\Virabotka_sbdn.xml", XML, '', False, True)
        try:
            F.write_file_c(r"C:\DB_srv\Virabotka_sbdn.xml", XML, '', False, True)
        except:
            print(fr'Ошибка выгрузки C:\DB_srv\Virabotka_sbdn.xml')
            pass
        # F.write_file_c(r"O:\Журналы и графики\Ведомости для передачи\Virabotka_sbdn.txt",itog_wo_set_nar,'|')

        # CMS.list_calc_tehnologs(F.bdcfg('Naryad'),F.bdcfg('BD_users'),F.bdcfg('db_resxml'),BD_dse) #Отключено жо момента как нач ТО доработает методу управления выработкой( обрабатывается в модуле ТК )


    except Exception as e:
        print(e)
        import traceback
        tb_to_str = traceback.print_exc()
        print(tb_to_str)
        print(f'Ошибка {metka}')
    finally:
        print('Цикл ожидание.')
        time.sleep(vrem)
# pyinstaller.exe --onefile Reiting.py
