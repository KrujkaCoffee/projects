import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import copy
import project_cust_38.Cust_Qt as CQT
from datetime import timedelta

def transponirivat_table_calendar(table:list,rez:list,pole:str):
    if  table == None:
        print('Ошибка загрузки таблицы')
        return []
    for j in range(3,len(table[0])):
        tmp_dict = dict()
        for i in range(3, len(table)):
            tmp_dict[table[i][1]] = table[i][j]
        rez.append({'date': F.strtodate(table[0][j],"d_%Y_%m_%d"),'holiday':table[1][j],pole:tmp_dict})
    return rez

def load_calendar(self,conn):
    date_start_today = F.strtodate(F.start_end_dates_c(F.now(), vid='m', format_out="%Y-%m-%d")[0], "%Y-%m-%d")
    spis_tables = CSQ.get_list_of_tables_c(self.bd_users)
    rez_table_empl = []
    for table in spis_tables:
        if table.startswith('m_'):
            date_table = F.strtodate(table[2:],format="%Y_%m_%d")
            if date_table >= date_start_today:
                query = f"""SELECT * FROM {table}"""
                rez_table_empl = transponirivat_table_calendar(CSQ.custom_request_c(self.bd_users,query,conn=conn),rez_table_empl,'empl')

    rez_table_eq = []
    for table in spis_tables:
        if table.startswith('eq_'):
            date_table = F.strtodate(table[3:], format="%Y_%m_%d")
            if date_table >= date_start_today:
                query = f"""SELECT * FROM {table}"""
                rez_table_eq = transponirivat_table_calendar(CSQ.custom_request_c(self.bd_users, query, conn=conn),
                                                               rez_table_eq,'equip')
    rez_table_rm = []
    for table in spis_tables:
        if table.startswith('rm_'):
            date_table = F.strtodate(table[3:], format="%Y_%m_%d")
            if date_table >= date_start_today:
                query = f"""SELECT * FROM {table}"""
                rez_table_rm = transponirivat_table_calendar(CSQ.custom_request_c(self.bd_users, query, conn=conn),
                                                               rez_table_rm,'rm')
    for i in range(len(rez_table_empl)):
        if 'equip' not in rez_table_eq[i]:
            CQT.msgbox(f'Не найдены в БД табели с оборудованием')
            return
        if 'rm' not in rez_table_rm[i]:
            CQT.msgbox(f'Не найдены в БД табели с рабочими местами')
            return
        rez_table_empl[i]['equip'] = rez_table_eq[i]['equip']
        rez_table_empl[i]['rm'] = rez_table_rm[i]['rm']
    #rez_table_empl, rez_table_eq, rez_table_rm
        for key in rez_table_empl[i]['equip'].keys():
            rez_table_empl[i]['equip'][key] *= 60
        for key in rez_table_empl[i]['rm'].keys():
            rez_table_empl[i]['rm'][key] *= 60
    return rez_table_empl

def current_val_proc_napravl(self):
    NAPRAVLENIYA = CSQ.custom_request_c(self.db_kplan, """SELECT * FROM napravlenie""", rez_dict=True)
    rez = dict()
    for item in NAPRAVLENIYA:
        rez[item['name']] = {'val': item['val']}
    return rez

def load_distinct_rc(self, conn,DOSTUPNIE_PLOSHADI):
    query = f"""SELECT DISTINCT Код_РЦ, COUNT(*) as Число FROM rab_mesta WHERE Расположение IN {tuple(DOSTUPNIE_PLOSHADI)} AND ФИО_1 != 1 AND ФИО_1 != 2 GROUP BY Код_РЦ"""
    dict_rc1 = dict(CSQ.custom_request_c(self.bd_users, query, hat_c=False,conn=conn))
    query = f"""SELECT DISTINCT Код_РЦ, COUNT(*) as Число FROM rab_mesta WHERE Расположение IN {tuple(DOSTUPNIE_PLOSHADI)}  AND ФИО_2 != 1 AND ФИО_2 != 2  GROUP BY Код_РЦ"""
    dict_rc2 = dict(CSQ.custom_request_c(self.bd_users, query, hat_c=False,conn=conn))
    for key in dict_rc2.keys():
        if key in dict_rc1:
            dict_rc1[key] += dict_rc2[key]
        else:
            dict_rc1[key] = dict_rc2[key]
    query = f"""SELECT DISTINCT Код_РЦ, COUNT(*) as Число FROM rab_mesta WHERE Расположение IN {tuple(DOSTUPNIE_PLOSHADI)}  AND ФИО_3 != 1 AND ФИО_3 != 2  GROUP BY Код_РЦ"""
    dict_rc3 = dict(CSQ.custom_request_c(self.bd_users, query, hat_c=False,conn=conn))
    for key in dict_rc3.keys():
        if key in dict_rc1:
            dict_rc1[key] += dict_rc3[key]
        else:
            dict_rc1[key] = dict_rc3[key]
    return dict_rc1

def load_grafic_moshnostey(self,DOSTUPNIE_PLOSHADI):
    dict_proc_napravl = current_val_proc_napravl(self)
    if dict_proc_napravl == None:
        return
    conn, cur = CSQ.connect_bd(self.bd_users)
    dict_rc  = load_distinct_rc(self, conn,DOSTUPNIE_PLOSHADI)
    calendar_empl  = load_calendar(self, conn)
    if calendar_empl == None:
        return
    sxema = load_rab_mesta(self, DOSTUPNIE_PLOSHADI, conn)
    CSQ.close_bd(conn)
    grafic = create_grafic(calendar_empl,sxema,dict_rc,dict_proc_napravl)
    if grafic == None:
        return
    return grafic

def create_grafic(calendar_empl,sxema,dict_rc,dict_proc_napravl):
    rez = []
    for i in range(len(calendar_empl)):
        if calendar_empl[i]['date'] >= F.start_end_dates_c(F.now(""),format_in='',format_out='',vid='d')[0]:
            day = create_day(calendar_empl[i],sxema,dict_rc,dict_proc_napravl)
            if day == None:
                return
            rez.append(day)
    return rez

def create_day(day:dict,sxema:list,dict_rc:dict,dict_proc_napravl:dict):
    koef_first_day = 1
    if day['date'] == F.start_end_dates_c(F.now(""), format_in='', format_out='', vid='d')[0]:
        koef_first_day = 0
    sxema_tmp = copy.deepcopy(sxema)
    dict_rc_tmp = copy.deepcopy(dict_rc)
    for rc in dict_rc_tmp.keys():
        tmp_dict_napr = dict()
        for key in sorted(dict_proc_napravl.keys()):
            tmp_dict_napr[key] = dict_rc_tmp[rc]*dict_proc_napravl[key]['val']/100
        dict_rc_tmp[rc] = tmp_dict_napr
    emploee = day['empl']
    for i in range(len(sxema)):
        fiod = f'{sxema_tmp[i]["ФИО"]} { sxema_tmp[i]["Должность"]}'
        if fiod in emploee:
            sxema_tmp[i]['Пулл'] = dict()
            rc = sxema_tmp[i]['Код_РЦ']
            sxema_tmp[i]['Раб_час'] = emploee[fiod]
            pull_smen_empl = 1
            for napr in dict_rc_tmp[rc].keys():
                sxema_tmp[i]['Пулл'][napr] = 0
                rab_mest_po_napr = dict_rc_tmp[rc][napr]
                if pull_smen_empl > 0:
                    ostatok_po_napr = pull_smen_empl

                    if rab_mest_po_napr < pull_smen_empl:
                        ostatok_po_napr = rab_mest_po_napr

                    sxema_tmp[i]['Пулл'][napr] = emploee[fiod]  * 60 * ostatok_po_napr

                    dict_rc_tmp[rc][napr] -=ostatok_po_napr
                    pull_smen_empl -= ostatok_po_napr
        else:
            print(f'create_day не найден {fiod} в emploee нужно добавить в бд  обновить календари')

    for i in range(len(sxema_tmp)):
        pull_eq = analiz_deficitov(day,'equip','Номер_осн_оборуд',sxema_tmp[i])
        pull_rm = analiz_deficitov(day, 'rm', 'Пномер', sxema_tmp[i])
        if pull_eq == None or pull_rm == None:
            return
        sxema_tmp[i]['Время'] = F.date_add_time(day['date'],sxema_tmp[i]['Время_начала'])
        sxema_tmp[i]['Время_начала'] = F.date_add_time(day['date'],sxema_tmp[i]['Время_начала'])
        sxema_tmp[i]['Время_конца'] = sxema_tmp[i]['Время_начала'] + timedelta(seconds=sxema_tmp[i]['Раб_час']*3600)
        if koef_first_day == 0:
            dt_nachalo = sxema_tmp[i]['Время_начала']
            dt_konec = sxema_tmp[i]['Время_конца']
            rabochih_minut = (dt_konec - dt_nachalo).total_seconds() / 60.0
            ostalos = (dt_konec - F.now('')).total_seconds() / 60.0
            ostalos = 0 if ostalos < 0 else ostalos
            koef_first_day = ostalos / rabochih_minut
            sxema_tmp[i]['Время'] = F.now('')
            sxema_tmp[i]['Время_начала'] = F.now('')
        for napr in sxema_tmp[i]['Пулл'].keys():
            sxema_tmp[i]['Пулл'][napr] = round(min(pull_rm[napr],pull_eq[napr])*koef_first_day)
    day['empl'] = sxema_tmp
    return day


def analiz_deficitov(day,name:str,name_pole:str,current_sxema):
    pull = copy.deepcopy(current_sxema['Пулл'])
    nom = current_sxema[name_pole]
    if nom not in day[name]:
        CQT.msgbox(f'В табeле {name} на {day["date"]} нет {name_pole} с номером {nom}')
        return
    for napr in pull.keys():
        if day[name][nom] > 0:
            day[name][nom] -= pull[napr]
            if day[name][nom] <= 0:
                pull[napr] += day[name][nom]
                day[name][nom] = 0
        else:
            pull[napr] = 0
    return pull

def load_rab_mesta(self,DOSTUPNIE_PLOSHADI,conn):
    query = f"""SELECT rab_mesta.Пномер, rab_mesta.Расположение, rab_mesta.Код_РЦ, rab_mesta.Прозвище, 
rab_mesta.Номер_осн_оборуд, rab_mesta.Код_профессии, 
s1.ФИО as ФИО_1см, s1.Должность as Должность_1см, rab_mesta.Время_начала_1, rab_mesta.Время_конца_1, rab_mesta.Нераб_мин1, rab_mesta.Между_нар_мин1, rab_mesta.Коэфф_производит1, 
s2.ФИО as ФИО_2см, s2.Должность as Должность_2см, rab_mesta.Время_начала_2, rab_mesta.Время_конца_2, rab_mesta.Нераб_мин2, rab_mesta.Между_нар_мин2, rab_mesta.Коэфф_производит2, 
s3.ФИО as ФИО_3см, s3.Должность as Должность_3см, rab_mesta.Время_начала_3, rab_mesta.Время_конца_3, rab_mesta.Нераб_мин3, rab_mesta.Между_нар_мин3, rab_mesta.Коэфф_производит3, 
rab_mesta.Примечание, rab_mesta.coord, rab_mesta.Доступен_с
                    FROM rab_mesta 
     INNER JOIN employee s1 ON s1.Пномер == rab_mesta.ФИО_1
     INNER JOIN employee s2 ON s2.Пномер == rab_mesta.ФИО_2
     INNER JOIN employee s3 ON s3.Пномер == rab_mesta.ФИО_3
            WHERE Расположение IN {tuple(DOSTUPNIE_PLOSHADI)}"""

    sxema = CSQ.custom_request_c(self.bd_users,query,rez_dict=True,conn=conn)


    rez = []
    for item in sxema:
        tmp = {'Пномер':item['Пномер']
                ,'Расположение':item['Расположение']
               ,'Код_РЦ'           : item['Код_РЦ'           ] 
               ,'Прозвище'         : item['Прозвище'         ] 
               ,'Номер_осн_оборуд' : item['Номер_осн_оборуд' ] 
               ,'Код_профессии'    : item['Код_профессии'    ] 
               ,'ФИО'          : item['ФИО_1см'          ]
               ,'Должность'    : item['Должность_1см'    ]
               ,'Время_начала'   : item['Время_начала_1'   ]
               ,'Время_конца'    : item['Время_конца_1'    ]
               ,'Нераб_мин'       : item['Нераб_мин1'       ]
               ,'Между_нар_мин'   : item['Между_нар_мин1'   ]
               ,'Коэфф_производит': item['Коэфф_производит1']
               ,'Пулл': dict()}
        tmp2 = {'Пномер':item['Пномер']
                ,'Расположение':item['Расположение']
               ,'Код_РЦ'           : item['Код_РЦ'           ] 
               ,'Прозвище'         : item['Прозвище'         ] 
               ,'Номер_осн_оборуд' : item['Номер_осн_оборуд' ] 
               ,'Код_профессии'    : item['Код_профессии'    ] 
               ,'ФИО'          : item['ФИО_2см'          ]
               ,'Должность'    : item['Должность_2см'    ]
               ,'Время_начала'   : item['Время_начала_2'   ]
               ,'Время_конца'    : item['Время_конца_2'    ]
               ,'Нераб_мин'       : item['Нераб_мин2'       ]
               ,'Между_нар_мин'   : item['Между_нар_мин2'   ]
               ,'Коэфф_производит': item['Коэфф_производит2']
               ,'Пулл': dict()}
        tmp3 = {'Пномер':item['Пномер']
                ,'Расположение': item['Расположение']
            , 'Код_РЦ': item['Код_РЦ']
            , 'Прозвище': item['Прозвище']
            , 'Номер_осн_оборуд': item['Номер_осн_оборуд']
            , 'Код_профессии': item['Код_профессии']
            , 'ФИО': item['ФИО_3см']
            , 'Должность': item['Должность_3см']
            , 'Время_начала': item['Время_начала_3']
            , 'Время_конца': item['Время_конца_3']
            , 'Нераб_мин': item['Нераб_мин3']
            , 'Между_нар_мин': item['Между_нар_мин3']
            , 'Коэфф_производит': item['Коэфф_производит3']
               ,'Пулл': dict()}
        if tmp['ФИО'] != '' and tmp['ФИО'] != '-':
            rez.append(tmp)

        if tmp2['ФИО'] != '' and tmp2['ФИО'] != '-':
            rez.append(tmp2)

        if tmp3['ФИО'] != '' and tmp3['ФИО'] != '-':
            rez.append(tmp3)

    return rez
