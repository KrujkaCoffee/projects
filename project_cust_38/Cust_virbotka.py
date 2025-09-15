import project_cust_38.Cust_Functions as F
import os
import project_cust_38.Cust_SQLite as CSQ
import datetime as DT
import calendar
import project_cust_38.Cust_mes as CMS
import copy
import project_cust_38.Cust_config as USRCNF

def start_of_period_c(data):
    date = F.strtodate(data)
    nach = DT.datetime(date.year, date.month, 1, 5, 0, 0)
    return F.datetostr(nach)

def end_of_period_c(data):
    date = F.strtodate(data)
    nach = DT.datetime(date.year, date.month, 1, 4, 59, 59)
    days_in_month = calendar.monthrange(date.year, date.month)[1]
    konec = nach + DT.timedelta(days=days_in_month)
    return F.datetostr(konec)

def number_of_day_c():
    return DT.date.today().day
    
def summ_hours_repo_card_c(fio,tabel,number_of_day_c = ''):
    try:
        n_k_sotr = F.num_col_by_name_in_hat_c(tabel,'Сотрудник')
        if n_k_sotr == None:
            print(' Не найдена колонка Сотрудник в табеле')
            raise 
        for i in range(len(tabel)):
            if len(tabel[i]) > n_k_sotr and tabel[i][n_k_sotr] == fio:
                summ = 0
                for k in range(i, len(tabel)):
                    if len(tabel[k]) == len(tabel[0]):
                        if number_of_day_c == '':
                            number_of_day_c = len(tabel[k])-3
                        for j in range(3, number_of_day_c + 3):
                            if F.is_numeric(tabel[k][j]):
                                summ += F.valm(tabel[k][j])
                        summ = 1 if summ == 0 else summ
                        return summ
        return 1
    except:
        print(tabel[i])
        return

def summ_hours_repo_card_new_c(fio,tabel,number_of_day_c = ''):
    try:
        n_k_sotr = F.num_col_by_name_in_hat_c(tabel,'ФИО')
        if n_k_sotr == None:
            print(' Не найдена колонка ФИО в табеле')
            raise
        for empl_tabel in reversed(tabel): #08.08.25 по задаче
            if len(empl_tabel) > n_k_sotr and fio in empl_tabel[n_k_sotr]:
                summ = 0
                for k in range(3, len(empl_tabel)):
                    summ += F.valm(empl_tabel[k])
                summ = 1 if summ == 0 else summ
                return summ
        return 1
    except Exception as e:
        return


def load_repo_card_c(nach,konec):
    spis_tabelei = F.list_of_files_c('O:\Производство Powerz\Отдел технолога\ТД\Учет табель\Табели')
    tabel = ''
    data_f = ''
    for i in range(len(spis_tabelei[0][2])):
        try:
            data_f = F.strtodate(F.throw_out_extention_c(spis_tabelei[0][2][i]), "%d.%m.%Y %H:%M:%S")
            data_f += DT.timedelta(hours=6)
            if data_f >= F.strtodate(nach) and data_f < F.strtodate(konec):
                tabel = F.open_file_c(spis_tabelei[0][0] + os.sep + spis_tabelei[0][2][i], True, propuski=True, separ='\t')
                break
        except:
            pass

    return tabel

def list_per_month_c(nach,konec):
    query = "Дата <= strftime('%Y-%m-%d %H:%M:00', datetime('" + \
            konec + "')) AND Дата >= strftime('%Y-%m-%d %H:%M:00', datetime('" + nach \
            + "'))"# + " AND ФИО LIKE '%рщик%'"

    list_per_month_c = CSQ.find_in_db_c(F.bdcfg('BDzhurnal'),
                                         'users', {},siroe_usl=query,dict=True,hat_c=True)
    return list_per_month_c



def list_of_completed_task_per_month_c(db,nach,konec,conn):
    #test po pologeniy 25.08.2022
    custom_request_c = f'''SELECT jurnal.Пномер, jurnal.ФИО, jurnal.Подытог, jurnal.Номер_наряда, jurnal.Статус, naryad.Твремя, naryad.Коэфф_сложности FROM jurnal 
INNER JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда 
WHERE jurnal.Статус == "Завершен" AND jurnal.Дата <= strftime("%Y-%m-%d %H:%M:00", datetime("{konec}")) AND 
jurnal.Дата >= strftime("%Y-%m-%d %H:%M:00", datetime("{nach}")) AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1'''
    list_per_month_c = CSQ.custom_request_c(db,custom_request_c,conn=conn)
    return list_per_month_c


def list_per_month_new_c(db,nach,konec,db_kplan,db_users,podrazdelenie,organization,tabel_m=None):
    
    def get_filtr_dolgn(podrazdelenie,organization):
        filtr_dolgn = None
        if podrazdelenie != None:
            if organization == None:
                print('Не указана организаиця')
                return
            filtr_dolgn = CSQ.custom_request_c(db, f"""SELECT Должность FROM dolgn_etap WHERE 
                     Подразделение == "{podrazdelenie}" AND Производство == "{organization}" ;""", hat_c=False,
                                               one_column=True)
        return filtr_dolgn

    filtr_dolgn = get_filtr_dolgn(podrazdelenie,organization)
    postfix = ""
    if filtr_dolgn != None:
        filtr_fio = []
        if tabel_m == None:
            name_table = F.datetostr(F.strtodate(nach),"mtdz_%Y_%m_%d")
            users = CSQ.custom_request_c(db_users,f"""SELECT ФИО FROM {name_table}""",hat_c=False,one_column=True)  
        else:
            users = [_[1] for _ in tabel_m[3:]]
        for user in users:
            fio = ' '.join(user.split()[:3])
            dolgn =  ' '.join(user.split()[3:])
            if dolgn in filtr_dolgn:
                filtr_fio.append(fio)

        postfix = f"""AND jurnal.ФИО IN ({CSQ.prepare_list_to_tuple(filtr_fio)})"""

    custom_request_c = f'''SELECT jurnal.Пномер, jurnal.Дата, jurnal.ФИО, jurnal.Подытог, jurnal.Номер_наряда, jurnal.Статус, naryad.Твремя, 
        naryad.Норма_времени, jurnal.Подытог_нормы, naryad.Коэфф_сложности, naryad.Внеплан, naryad.Подтвержд_вып, 
        CASE WHEN знпр.№проекта IS NOT NULL 
           THEN знпр.№проекта 
           ELSE mk.Номер_проекта 
           END AS Номер_проекта 
            FROM jurnal 
        INNER JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда 
        INNER JOIN mk ON naryad.Номер_мк == mk.Пномер  
       LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
       LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
       LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
       LEFT JOIN коды_веплана_для_наряда ON коды_веплана_для_наряда.code = naryad.Внеплан
        WHERE коды_веплана_для_наряда.poki == {USRCNF.Config.place.poki} and jurnal.Дата <= strftime("%Y-%m-%d %H:%M:00", datetime("{konec}")) AND 
        jurnal.Дата >= strftime("%Y-%m-%d %H:%M:00", datetime("{nach}")) {postfix};'''
    spis_jur = CSQ.custom_request_c(db,custom_request_c,rez_dict=True, attach_dbs=(db_kplan))

    spis_jur_full = [_ for _ in spis_jur #04.08.25
                     if _['Внеплан'] != USRCNF.Config.place.КодыНарядов.НеподтвержденныйВнеплан
                     and  _['Подтвержд_вып'] == 1 ]

    spis_per_month_c = [_ for _ in spis_jur if _['Статус'] == "Начат"]
    dict_per_month_c = dict()
    for row in spis_per_month_c:
        if row['ФИО'] not in dict_per_month_c:
            dict_per_month_c[row['ФИО']] = 0
        if not F.is_numeric(row['Подытог_нормы']):
            jur = CMS.Jurnal_nar(db, row['Номер_наряда'], row['ФИО'])
            por_nom = row['Пномер']
            if por_nom == False:
                CQT.msgbox(f'ОШибка, не занесено')
                return
            jur.set_selected_fragment(por_nom)
            jur.calc_and_set_poditog(jur.selected_fragment_end_state, jur.selected_fragment_end_date)
            poditog, poditog_norm = jur._calc_poditog(jur.selected_fragment_end_state, jur.selected_fragment_end_date)
            row['Подытог_нормы'] = poditog_norm
        dict_per_month_c[row['ФИО']] += F.valm(row['Подытог_нормы'])
    #[_ for _ in spis_jur if _['ФИО'] == 'Абдуллоев Кароматулло Хасанович']
    return spis_jur_full, dict_per_month_c

def holyday(dtime,tabel):
    den = F.strtodate(dtime.split()[0])
    rez = False
    for j in range(len(tabel[0])):
        if F.is_date(tabel[0][j],'d_%Y_%m_%d'):
            den_tab = F.strtodate(tabel[0][j],'d_%Y_%m_%d')
            if den == den_tab:
                rez = tabel[1][j]
                return rez
    return False

def koeff_double_pay_holydays(spis_jur_full,nom_nar,tabel):
    return 1 #"С 08.2024 учет в ЕРП"
    KOEF_RAB_VIHODNOI = 1.5
    if isinstance(spis_jur_full[0],list):
        nk_nom_nar = F.num_col_by_name_in_hat_c(spis_jur_full,'Номер_наряда')
        nk_data = F.num_col_by_name_in_hat_c(spis_jur_full,'Дата')
        nk_status = F.num_col_by_name_in_hat_c(spis_jur_full, 'Статус')
        nk_poditog = F.num_col_by_name_in_hat_c(spis_jur_full, 'Подытог')
        nk_zad = F.num_col_by_name_in_hat_c(spis_jur_full, 'Номер_проекта')
        summ_minut_holy = 0
        summ_minut_full = 0
        for zapis in spis_jur_full:
            if zapis[nk_nom_nar] == nom_nar and zapis[nk_status] == 'Начат':
                if zapis[nk_zad] == 'ПРОСТОЙ':
                    return 1
                if holyday(zapis[nk_data],tabel):
                    summ_minut_holy+= zapis[nk_poditog]
                summ_minut_full+=zapis[nk_poditog]
        if summ_minut_full == 0:
            return 1
        return 1 + summ_minut_holy/summ_minut_full*(KOEF_RAB_VIHODNOI-1)
    elif isinstance(spis_jur_full[0],dict):
        summ_minut_holy = 0
        summ_minut_full = 0
        for zapis in spis_jur_full:
            if zapis['Номер_наряда'] == nom_nar and zapis['Статус'] == 'Начат':
                if zapis['Номер_проекта'] == 'ПРОСТОЙ':
                    return 1
                if holyday(zapis['Дата'], tabel):
                    summ_minut_holy += zapis['Подытог']
                summ_minut_full += zapis['Подытог']
        if summ_minut_full == 0:
            return 1
        return 1 + summ_minut_holy / summ_minut_full * (KOEF_RAB_VIHODNOI - 1)
 
def calc_month_rates_c(tabel):
    rez = 0
    for i in range(len(tabel[1])):
        if tabel[1][i] == 0:
            rez+=8
    return rez*60

def add_emploee_into_list_c(list_per_month_c,fiod,itog,tabel,spis_empolee,KOEF_SVERHNORMI):#off
    return 
    #po pologeniy 25.08.2022 test
    mes_norma = calc_month_rates_c(tabel)
    try:
        сумма_по_нарядам = 0
        сумма_по_нарядам_без_сложности = 0
        nar_vr = []
        nk_fio = F.num_col_by_name_in_hat_c(list_per_month_c,'ФИО')
        nk_teor = F.num_col_by_name_in_hat_c(list_per_month_c, 'Твремя')
        nk_nomnar = F.num_col_by_name_in_hat_c(list_per_month_c, 'Номер_наряда')
        nk_koef_slojnosti = F.num_col_by_name_in_hat_c(list_per_month_c, 'Коэфф_сложности')
        for j in range(1, len(list_per_month_c)):
            if list_per_month_c[j][nk_fio] == fiod:
                сумма_по_нарядам_без_сложности += F.valm(list_per_month_c[j][nk_teor])
                rez_koeff_double_pay = 1
                if сумма_по_нарядам_без_сложности >= mes_norma:
                    rez_koeff_double_pay = KOEF_SVERHNORMI
                vrema = list_per_month_c[j][nk_teor] * list_per_month_c[j][nk_koef_slojnosti] * rez_koeff_double_pay
                сумма_по_нарядам += vrema
                nar_vr.append(f'Нар.{str(list_per_month_c[j][nk_nomnar])}: {str(list_per_month_c[j][nk_teor])}мин.(К_св.норм.:{rez_koeff_double_pay}, К_слож{list_per_month_c[j][nk_koef_slojnosti]}))')
    except:
        print(f'В строке {list_per_month_c[j]}')
        return
    try:
        number_of_day_c_mes = number_of_day_c()
        сумма_часов_по_табелю = mes_norma/60
    except:
        print(f'Сумма часов табель ошибка для {fiod}')
        return
    try:
        сумма_теор_часов = round(сумма_по_нарядам/60,2)# 148 наряды
        коэффициент_выработки  = сумма_теор_часов / сумма_часов_по_табелю
        коэффициент_выработки = 0.5 if коэффициент_выработки < 0.5 else коэффициент_выработки
        итог = round(коэффициент_выработки * 200,2)
        emp = CMS.empol_by_name_c(spis_empolee,fiod)
        if emp != None:
            itog.append([CMS.name_by_empl_c(fiod), CMS.job_post_by_empl_c(emp), итог, 0, ';'.join(nar_vr), сумма_теор_часов , '', сумма_часов_по_табелю])
        return itog
    except:
        print(f'ошибка расчета итога')
        return

def add_emploee_into_list_new_c(fio,itog,tabel,DICT_EMPLOEE,spis_jur_full,double_pay_holydays,
                                DICT_MASTERS='',CALC_BASE_ONLY_PREM=False,dict_per_month_all_state_from_jur=None):
    try:
        сумма_по_нарядам_с_коэфф = 0
        сумма_чист_по_нарядам =0
        сумма_по_нарядам = 0
        сумма_по_нарядам_астроном = 0
        nar_vr = []

        set_naryads = set()
        for j in range(1, len(spis_jur_full)):
            if spis_jur_full[j]['Статус'] != "Завершен":
                continue
            if spis_jur_full[j]['ФИО'] == fio:
                rez_koeff_double_pay_holydays = 1
                if double_pay_holydays:
                    try:
                        rez_koeff_double_pay_holydays = koeff_double_pay_holydays(spis_jur_full, spis_jur_full[j]['Номер_наряда'], tabel)
                    except:
                        pass
                vrema = spis_jur_full[j]['Твремя'] * spis_jur_full[j]['Коэфф_сложности'] * rez_koeff_double_pay_holydays
                #print(f'нар. {spis_jur_full[j]['Номер_наряда']} - {vrema}({spis_jur_full[j]['Твремя']}) мин.')
                сумма_по_нарядам_с_коэфф += F.valm(vrema)
                сумма_по_нарядам += spis_jur_full[j]['Твремя']
                сумма_чист_по_нарядам += spis_jur_full[j]['Твремя']
                сумма_по_нарядам_астроном += spis_jur_full[j]['Норма_времени']
                nar_vr.append(f'Нар.{str(spis_jur_full[j]["Номер_наряда"])}: {str(round(spis_jur_full[j]["Твремя"]))} '
                              f'чист.мин. ({str(round(vrema))}мин.=К_вых:{round(rez_koeff_double_pay_holydays,1)},'
                              f' К_слож{round(spis_jur_full[j]["Коэфф_сложности"],1)}))')
                set_naryads.add(spis_jur_full[j]['Номер_наряда'])
    except:
        print(f'Ошибка в строке {spis_jur_full[j]}')
        return
    try:
        number_of_day_c_mes = number_of_day_c()
        сумма_часов_по_табелю = summ_hours_repo_card_new_c(fio, tabel)#number_of_day_c_mes #по графику 128
    except:
        print(f'Сумма часов табель ошибка для {fio}')
        return
    try:
        сумма_чист_теор_час = round(сумма_чист_по_нарядам/60,2)
        сумма_теор_часов_с_коэфф = round(сумма_по_нарядам_с_коэфф/60,2)# 148 наряды
        сумма_теор_часов = round(сумма_по_нарядам/60,2)
        коэффициент_выработки  = сумма_теор_часов_с_коэфф / сумма_часов_по_табелю
        сумма_астроном_час = round(сумма_по_нарядам_астроном/60,2)
        if CALC_BASE_ONLY_PREM:
            текущий_процент = round((коэффициент_выработки * 100))
            чистый_процент = copy.deepcopy(текущий_процент)
            итог = текущий_процент
            if текущий_процент < 100:
                итог = 100
        else:
            текущий_процент = round((коэффициент_выработки * 100 - 50) / 50 * 100)
            чистый_процент = copy.deepcopy(текущий_процент)
            итог = текущий_процент
            if текущий_процент < 100:
                итог = 100
            итог = итог + 100
            чистый_процент += 100

        if fio in DICT_EMPLOEE:
            include_nezaversh = 0
            if fio in dict_per_month_all_state_from_jur:
                include_nezaversh = round(dict_per_month_all_state_from_jur[fio]/60,2)
            itog.append({"ФИО" : fio   ,
             "Должность" :  DICT_EMPLOEE[fio]['Должность']   ,
             "Итог" :  итог   ,
             'Брак' : 0   ,
             'Наряды' :  ';'.join(nar_vr)   ,
             "Сумма_теор_часов_с_коэфф" :  сумма_теор_часов_с_коэфф   ,
             "Сумма_теор_часов_без_коэфф" :  сумма_теор_часов    ,
             'Режим' :  DICT_EMPLOEE[fio]['Режим']   ,
              'Норма времени(Астр)': сумма_астроном_час,
             "сумма_часов_по_табелю" : сумма_часов_по_табелю   ,
            "кг." :  round(сумма_чист_теор_час*84/8)   ,
            "текущий_процент" : round(чистый_процент),
                         'Подытог_по_нормам': include_nezaversh,
                         'Сет_нарядов': set_naryads 
            })
            if DICT_MASTERS != '':
                for master in DICT_MASTERS:
                    if DICT_EMPLOEE[fio]['Режим'] in DICT_MASTERS[master]['Смены'] and DICT_EMPLOEE[fio]['Подразделение'] == DICT_MASTERS[master]['Подразделение'] :
                        DICT_MASTERS[master]['Выработка_смены'] += чистый_процент
                        DICT_MASTERS[master]['Число_сотрудников'] += 1
                        DICT_MASTERS[master]['Вес'] += round(сумма_чист_теор_час*84/8)
                        DICT_MASTERS[master]['Ставка_таб'] += сумма_часов_по_табелю
                        #print(f'{master} - {fio}:{чистый_процент}')
                pass
        return itog
    except:
        print(f'ошибка расчета итога')
        return



def list_of_defects_per_months_c(nach,konec):
    query = "Дата <= strftime('%Y-%m-%d %H:%M:00', datetime('" + \
            konec + "')) AND Дата >= strftime('%Y-%m-%d %H:%M:00', datetime('" + nach \
            + "'))"
    list_of_defects_per_months_c = CSQ.find_in_db_c('O:/Журналы и графики/Ведомости для передачи/BDact.db',
                                      'act', {}, siroe_usl=query, dict=True, hat_c=True)
    return list_of_defects_per_months_c

def list_of_defects_per_months_new_c(db,nach,konec):
    custom_request_c = f'''SELECT * FROM act 
    WHERE act.Дата <= strftime("%Y-%m-%d %H:%M:00", datetime("{konec}")) AND 
    act.Дата >= strftime("%Y-%m-%d %H:%M:00", datetime("{nach}"))'''
    list_of_defects_per_months_c = CSQ.custom_request_c(db, custom_request_c)
    return list_of_defects_per_months_c

def apply_defects_on_list_emploee_c(nom_acta,nom_nar, kat_braka,itog):
    spis_vinovnih = []
    if nom_nar != "":
        spis_vinovnih = CSQ.find_in_db_c(r'O:\Журналы и графики\Ведомости для передачи\BDzhurnal.db',
                                       'users',
                                       {'Номер_наряда': nom_nar},
                                       ['ФИО'])
    
    if spis_vinovnih == []:
        if kat_braka == 'Исправимый':
            sila = 0
        else:
            sila = 0
        for j in range(1, len(itog)):
            itog[j][3] -= sila
            #itog[j][6] = itog[j][6]  + nom_acta + ":"+ str(sila) + ";"
    else:
        if kat_braka == 'Исправимый':
            sila = 2
        else:
            sila = 4
        for j in list(set(spis_vinovnih)):
            for k in range(len(itog)):
                if itog[k][0] == ' '.join(j[0].split()[:3]):
                    itog[k][3] -= sila
                    itog[k][6] = itog[k][6] + nom_acta + ":" + str(sila) + ";"
    
    return itog


def apply_defects_on_list_emploee_new_c(nom_acta, nom_nar, kat_braka, itog, conn):
    nk_brak = F.num_col_by_name_in_hat_c(itog, 'Брак')
    nk_fio = F.num_col_by_name_in_hat_c(itog, 'ФИО')
    nk_vichet = F.num_col_by_name_in_hat_c(itog, 'Режим')
    spis_vinovnih = []
    if nom_nar != "" and F.is_numeric(nom_nar):
        custom_request_c = f'''SELECT ФИО, ФИО2 FROM naryad WHERE Пномер == {int(nom_nar)}
                    '''
        spis_vinovnih = CSQ.custom_request_c('',custom_request_c,conn)

    if len(spis_vinovnih) == 1:
        print(f'Неопознаный наряд по акту№ {nom_acta}')
        if kat_braka == 'Исправимый':
            sila = 0#2
        else:
            sila = 0#5
        for j in range(1, len(itog)):
            itog[j][nk_brak] -= sila
            # itog[j][6] = itog[j][6]  + nom_acta + ":"+ str(sila) + ";"
    else:
        if kat_braka == 'Исправимый':
            sila = 2
        else:
            sila = 4
        for user in list(set(spis_vinovnih[-1])):
            for k in range(1, len(itog)):
                if itog[k][nk_fio] == user:
                    itog[k][nk_brak] -= sila
                    itog[k][nk_vichet] = itog[k][nk_vichet] + nom_acta + ":" + str(sila) + ";"
    return itog

def conversion_file_from_zp_into_picle_c(file_spis_zp,to_pickle):
    spis_zp = F.load_file(file_spis_zp)
    rez = []
    for item in spis_zp:
        if len(item) == 2:
            rez.append(item)
    F.save_file_pickle(to_pickle,rez)
