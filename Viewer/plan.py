from __future__ import annotations
import project_cust_38.Cust_Functions as F
import datetime as DT
import mosh as MSH
import zagruzka as ZG
import project_cust_38.Cust_SQLite as CSQ
import copy
import project_cust_38.Cust_Excel as CEX

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Viewer import mywindow

#TODO указывать время работы каждой смены по участкам, каждый участок будет иметь несколько смен
#TODO учитывать резерв загрузки начало и конец смены и между нарядами по каждому рц
#TODO и учесть коэффицет времени -2 это в 2 раза медленнее работает при построении табеля
#TODO не менять праздники и выходные в календаре если они ранее были установлены
#TODO настройка изменения условий с такого то числа
#TODO сравнение вариантов планирования
"""
определить соотношение направлений в % == направление, % *
определить порядок по приоритету мк по направлению, которые еще не зыкрыты == направление, номер мк *
каждую мк разложить на последовательность деталей, которые еще не сделаны  == направление, номер мк, имя детали, рц *
каждую деталь разложить на последовательность операций, которые еще не сделаны  == направление, номер мк, имя детали, рц, операция, время выполнения *
сформировать картину мощностей == направление, РЦ, часы, даты *
каждую операцию рассчитать на параллельное выполнение(сделать две но короче) == направление, номер мк, имя детали, рц, операция + операция, время выполнения
наполнять мощности операциями по порядку, фиксировать время начала операции и время конца
свести операции на диаграмму == направление, номер мк, имя детали, рц, операция , начало , конец

условия предшествования технологических операций;
доступность основных рабочих центров;
транспортировка между рабочими центрами или между подразделениями;
наличие необходимых для выполнения операций товарно-материальных ценностей.
"""

def load_plan(self:mywindow,delete_cash_plan):
    #zagruzka = ZG.load_zagruzka(self)
    #==================
    imafp = self.files_tmp +F.sep() + f'plan_{F.now("%Y_%m_%d")}.pickle'
    imafz = self.files_tmp +F.sep() + f'zagruzka_{F.now("%Y_%m_%d")}.pickle'
    imafm = self.files_tmp +F.sep() + f'mosh_{F.now("%Y_%m_%d")}.pickle'
    if delete_cash_plan:
        F.delete_file_c(imafp)
        F.delete_file_c(imafz)
        F.delete_file_c(imafm)
    if F.existence_file_c(imafp):
        rez_list =  F.load_file_pickle(imafp)
    else:
        if F.existence_file_c(imafz):
            zagruzka = F.load_file_pickle(imafz)
        else:
            zagruzka = ZG.load_zagruzka(self)
            F.save_file_pickle(imafz, zagruzka)
        if zagruzka == False or zagruzka == None:
            return
        DOSTUPNIE_PLOSHADI = [1, 2, 3, 4, 5]
        if F.existence_file_c(imafm):
            dict_moshn = F.load_file_pickle(imafm)
        else:
            dict_moshn = MSH.load_grafic_moshnostey(self, DOSTUPNIE_PLOSHADI)
            F.save_file_pickle(imafm, dict_moshn)
        #========Расчет мощностей================
        if dict_moshn == None:
            return
        rez = [['Дата','Код_РЦ', 'Пномер', 'ФИО','Пулл','Время_начала','Время_конца','Раб_мин','напр1','напр2','напр3','напр4','summ']]
        for day in dict_moshn:
            for empl in day['empl']:
                summ = 0
                tmp = [day['date'],empl['Код_РЦ'], empl['Пномер'], empl['ФИО'],empl['Пулл'],empl['Время_начала'],empl['Время_конца'],empl['Раб_час']*60]
                for vid in empl['Пулл'].keys():
                    tmp.append(empl['Пулл'][vid])
                    summ+=empl['Пулл'][vid]
                tmp.append(summ)
                rez.append(tmp)
        now = F.now("%Y-%m-%d")
        try:
            CEX.zap_spis(rez, self.files_tmp , f'mosh_{now}.xlsx', '1', 1, 1)
        except:
            pass
        # ========================

        rez_list = nalogenie(self, dict_moshn,zagruzka)

        # ========================
        print('Сохранение пикл....')
        F.save_file_pickle(imafp,rez_list)

        # ========================

        if delete_cash_plan:
            try:
                F.open_dir_c(self.files_tmp)
            except:
                pass
        # ==Загрузка работников========
    dict_users_time = dict()
    for item in rez_list:
        if item['Должность'] in self.Data.VID_RABOT_PO_DOLGN:
            if F.strtodate(self.ui.le_nach_per.text()) <= item['Начало'] < F.strtodate(self.ui.le_end_of_period_c.text()):
                if item['ФИОД'] not in dict_users_time:
                    dict_users_time[item['ФИОД']] = {'Должность': item['Должность'], 'Дельта': item['Дельта']}
                else:
                    dict_users_time[item['ФИОД']]['Дельта'] += item['Дельта']
    list_users_time = F.dict_of_dicts_to_list_of_lists(dict_users_time)
    for i in range(1,len(list_users_time)):
        list_users_time[i][2] = round(list_users_time[i][2].total_seconds()/60/480,1)
    CEX.zap_spis(list_users_time, self.files_tmp, f'users_time_{F.now("%Y-%m-%d")}.xlsx', '1', 1, 1)
    # ========================
    return
    now = F.now("%Y-%m-%d")
    name = f'plan_{now}.xlsx'
    if not F.existence_file_c(self.files_tmp + F.sep() + name):

        print('Сохранение эксель....')
        self.save_excell_plan(rez_list, self.files_tmp, name)

    self.rez_plan = rez_list
    return rez_list

def save_excell_plan_materials(self:mywindow,rez_list,files_tmp,name,nach,konec):

    dt_nach = F.strtodate(nach)
    dt_konec = F.strtodate(konec)
    set_rc = set()
    tmp_dict= dict()
    for item in rez_list:
        if item['Начало'] > dt_nach and item['Начало'] < dt_konec:
            rc = item['РЦ'][:4]
            if rc not in tmp_dict:
                tmp_dict[rc] = []
            tmp_dict[rc].append(item)
    for rc in tmp_dict:
        dict_prof = dict()
        dict_opers = dict()
        for item in tmp_dict[rc]:
            oper = item['Операция']
            if oper not in dict_opers:
                dict_opers[oper] = 0
            prof = item['Должность']
            if prof not in dict_prof:
                dict_prof[prof] = 0
            dict_opers[oper] += item['На_исполнение_минут']
            dict_prof[prof] += item['На_исполнение_минут']

        dict_maters = dict()
        for oper in dict_opers:
            kod_oper = self.DICT_OPER_FULL[oper]['kod']
            query = f"""SELECT complex_filtr.kod, nomen.Наименование, nomen.ЕдиницаИзмерения,  complex_filtr.expenditure_per_smena FROM complex_filtr 
                        INNER JOIN nomen ON nomen.Код == complex_filtr.kod 
                                    WHERE complex_filtr.kod_oper == '{kod_oper}'
                            AND complex_filtr.filtr == 1"""
            list_mats = CSQ.custom_request_c(self.bd_mat,query,rez_dict=True)
            for item in list_mats:
                if item['kod'] not in dict_maters:
                    dict_maters[item['kod']] = {'№':0,'Уникальный идентификатор (Номенклатура)':'',
                                                'Уникальный идентификатор (Характеристика)':'',
                                                'Уникальный идентификатор (Назначение)':'',
                                                'Уникальный идентификатор (Упаковка)':'',
                                                'Уникальный идентификатор (Клиент)':'',
                                                'Уникальный идентификатор (Соглашение)':'',
                                                'Уникальный идентификатор (Склад)':'',
                                                'Код':item['kod'], 'Номенклатура':item['Наименование'],
                                                'Характеристика':'', 'Ед. изм.':item['ЕдиницаИзмерения'],'Норма':0}
                if F.is_numeric(item['expenditure_per_smena']):
                    ud_norm = F.valm(item['expenditure_per_smena'])
                else:
                    ud_norm = 0
                    print(f'{item["kod"]} : {item["expenditure_per_smena"]}' )
                dict_maters[item['kod']]['Норма'] += ud_norm/480 * dict_opers[oper]
        list_mats_rez = F.dict_of_dicts_to_list_of_lists(dict_maters,'№')
        nk_norma= F.num_col_by_name_in_hat_c(list_mats_rez,'Норма')
        nk_pnom = F.num_col_by_name_in_hat_c(list_mats_rez, '№')
        for i in range(1,len(list_mats_rez)):
            list_mats_rez[i][nk_pnom] = i
            list_mats_rez[i][nk_norma] = round(list_mats_rez[i][nk_norma],3)
        CEX.zap_spis(list_mats_rez, files_tmp, f'{rc}_{name}', '1', 1, 1)
        list_prof = F.dict_to_list(dict_prof)
        CEX.zap_spis(list_prof, files_tmp, f'{rc}_prof_for_' + name, '1', 1, 1)
    F.open_dir_c(files_tmp)


def calc_limit_po_childrens(mk,iter_dse,iter_oper,limit_tmp):
    current_level_c = mk[iter_dse]['Уровень']
    for i in range(iter_dse - 1, -1,-1):
        if mk[i]['Уровень'] <= current_level_c:
            break
        if mk[i]['Уровень'] == current_level_c + 1:
            if 'План_завершение' in mk[i]['Операции'][-1]:
                if limit_tmp < mk[i]['Операции'][-1]['План_завершение']:
                    limit_tmp = mk[i]['Операции'][-1]['План_завершение']
    return limit_tmp

def calc_limit_po_oper(mk,iter_dse,iter_oper,limit_tmp):
    for i in range(iter_oper-1,-1,-1):
        if 'План_завершение' in mk[iter_dse]['Операции'][i]:
            if limit_tmp < mk[iter_dse]['Операции'][i]['План_завершение']:
                limit_tmp = mk[iter_dse]['Операции'][i]['План_завершение']
                break
    return limit_tmp

def calculate_start_limit_oper(mk,iter_dse,iter_oper):
    limit_tmp = copy.deepcopy(mk[iter_dse]['Лимит_дата_начала'])
    lim_child = calc_limit_po_childrens(mk,iter_dse,iter_oper,limit_tmp)
    lim_oper = calc_limit_po_oper(mk,iter_dse,iter_oper,lim_child)
    return lim_oper


def nalogenie(self,dict_moshn,zagruzka):
    list_plan = []
    npp = 1
    i =0
    cc = len(zagruzka)
    set_defecit_rc = set()
    for mk in zagruzka:
        i+=1
        print(f'{i} из {cc}')
        for iter_dse, dse in enumerate(mk['Ресурсная']):
            name_dse =f"{dse['Номенклатурный_номер']} {dse['Наименование']}"
            arr_mat_dse = dse['Мат_кд'].split('/')
            ves_dse = 0
            if arr_mat_dse[1] != '' and arr_mat_dse[2] != '':
                ves_dse = round(F.valm(arr_mat_dse[0]) * dse['Количество'],2)

            for iter_oper, oper in enumerate(dse['Операции']):
                start_limit = calculate_start_limit_oper(mk['Ресурсная'],iter_dse,iter_oper)
                rc = oper['Опер_РЦ_код']
                t_pz = round(oper['Опер_Тпз'],2)
                t_sht = round(oper['Опер_Тшт'] / dse['Количество'], 2)

                oper_name = oper['Опер_наименование']
                oper_nom = oper['Опер_номер']
                oper_prof = oper['Опер_профессия_наименование']
                limit_data_oper = oper['Лимит_дата_начала']
                koef_paral = mk['Коэф_парал']
                list_partiy = generate_partii(dse['Количество'],koef_paral)
                vid_rabot = oper['Опер_профессия_код']
                if oper['Опер_профессия_код'] in self.DICT_PROFESSIONS:
                    vid_rabot = self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['вид работ']
                for dse_part in list_partiy:
                    time_rasch = round(t_sht * dse_part + t_pz, 2)
                    t_operacionnoe = round(t_sht * dse_part,2)
                    list_plan = nalogenie_operacii(self,list_plan,dict_moshn, t_operacionnoe, t_pz, rc, mk,start_limit,set_defecit_rc,
                                                   name_dse,oper,
                           time_rasch,mk['Вес'],ves_dse,dse,oper_name,oper_nom,limit_data_oper,iter_dse,iter_oper,vid_rabot,dse_part,npp)

    list_plan = start_end_mk(list_plan)
    for item in set_defecit_rc:
        print(item)
    return list_plan

def generate_partii(kol_vo,koef):
    chast = kol_vo//koef
    rez = [chast] * koef
    ost = kol_vo%koef
    if ost > 0:
        rez.append(ost)
    return rez

def nalogenie_operacii(self,list_plan,dict_moshn, t_operacionnoe, t_pz, rc, mk,start_limit,set_defecit_rc,name_dse,oper,
                       time_rasch,ves,ves_dse,dse,oper_name,oper_nom,limit_data_oper,iter_dse,iter_oper,vid_rabot,dse_part,npp):
    list_plan_dse = add_time_to_day(dict_moshn, t_operacionnoe, t_pz, rc, mk['Направление'], start_limit,npp)
    if list_plan_dse == []:
        pass
        # print(f'Для {rc} под {oper["Опер_наименование"]} {oper["Опер_профессия_наименование"]} не найдены мощности')
        #set_defecit_rc.add((
        #                   'Рц найден, но не найдено время', rc, name_dse, oper['Опер_номер'], oper["Опер_наименование"],
        #                   mk['Пномер']))
        # add_time_to_day(dict_moshn, t_operacionnoe, t_pz, rc, mk['Направление'])
    else:
        if list_plan_dse == False:
            # print(f'Для {rc} под {oper["Опер_наименование"]} {oper["Опер_профессия_наименование"]} не найдены мощности')
            set_defecit_rc.add(
                ('Рц не найден', rc, name_dse, oper['Опер_номер'], oper["Опер_наименование"], mk['Пномер']))
            # add_time_to_day(dict_moshn, t_operacionnoe, t_pz, rc, mk['Направление'])
        else:
            for deistvie in list_plan_dse:
                ves_test_sborka = 0

                if rc == '010301' or rc == '010302':
                    ves_test_sborka = round(time_rasch / 480 * 102, 3)
                list_plan.append({'#':deistvie['#'], 'ФИОД': deistvie['ФИОД'], 'Начало': deistvie['Начало'],
                                                       'Конец': deistvie['Конец'], 'РЦ': rc, 'РМ': deistvie['РМ'],
                                                       'Должность': deistvie['Должность'], "Направление": mk['Направление'],
                                                       'Номер_заказа': mk['Номер_заказа'],
                                                       'Номер_проекта': mk['Номер_проекта'],
                                                       'Вид': mk['Вид'], 'Примечание': mk['Примечание'],
                                                       'Основание': mk['Основание'],
                                                       'Количество_изд_МК': mk['Количество'], 'Вес_мк': ves,
                                                       'Прим_резка': mk['Прим_резка'], "МК": mk['Пномер'],
                                                       "ДСЕ": name_dse,
                                                       "Вес_ДСЕ(на кол-во)": ves_dse, "Количество_ДСЕ(на_МК)": dse['Количество'],
                                                       'Операция': oper_name, 'Номер_опер': oper_nom, 'Время_пз(мин)': t_pz,
                                                       'Время_тшт_на_партию(мин)': t_operacionnoe,
                                                        'Время_тшт_тпз_на_партию(мин)': time_rasch,
                                                       'Партия': dse_part,
                                                       'Остаток': deistvie['Остаток'],
                                                       'Дельта': deistvie['Дельта'],
                                                        'На_исполнение_минут': deistvie['На_исполнение_минут'],
                                                       'Лимит_дата_опер': limit_data_oper,
                                                       'Лимит_дата_дсе': mk['Ресурсная'][iter_dse]['Лимит_дата_начала'],
                                                       'Лимит_по_входящим': start_limit,

                                                       'Вес_для_оценки_сборка': ves_test_sborka,
                                                       'Вид работ': vid_rabot,
                                                       'Профессия': oper['Опер_профессия_наименование']})
                time_rasch = 0
                t_operacionnoe = 0
                mk['Ресурсная'][iter_dse]['Операции'][iter_oper]['План_завершение'] = deistvie[
                    'Конец']  # ограничение, запрос идет в
                ves = 0
    return list_plan

def start_end_mk(list_plan):
    dict_sroki_end_proecta = dict()
    dict_sroki_start_proecta = dict()
    for i in range(len(list_plan)):
        if list_plan[i]['МК'] in dict_sroki_end_proecta:
            if list_plan[i]['Конец'] > dict_sroki_end_proecta[list_plan[i]['МК']]:
                dict_sroki_end_proecta[list_plan[i]['МК']] = list_plan[i]['Конец']
        else:
            dict_sroki_end_proecta[list_plan[i]['МК']] = list_plan[i]['Конец']
        if list_plan[i]['МК'] in dict_sroki_start_proecta:
            if list_plan[i]['Начало'] < dict_sroki_start_proecta[list_plan[i]['МК']]:
                dict_sroki_start_proecta[list_plan[i]['МК']] = list_plan[i]['Начало']
        else:
            dict_sroki_start_proecta[list_plan[i]['МК']] = list_plan[i]['Начало']
    for i in range(len(list_plan)):
        list_plan[i]['Начало мк'] = dict_sroki_start_proecta[list_plan[i]['МК']]
        list_plan[i]['Завершение мк'] = dict_sroki_end_proecta[list_plan[i]['МК']]
    return list_plan

def find_user_in_day(moshn,ispolnotel,start_limit):
    fl_naid_ispolnitel = False
    if ispolnotel == '':
        fl_naid_ispolnitel = True
    else:
        for j in range(len(moshn['empl'])):
            if ispolnotel == f"{moshn['empl'][j]['ФИО']} {moshn['empl'][j]['Должность']}" \
                    and moshn['empl'][j]['Время'] >= start_limit:
                fl_naid_ispolnitel = True
                break
    if fl_naid_ispolnitel == False:
        ispolnotel = ''
    return ispolnotel

def add_time_to_day(dict_moshn,t_operacionnoe,t_pz,rc,napravlenie, start_limit,npp):
    list_plan_dse = []
    ispolnotel = ''
    t_pz_tmp = copy.deepcopy(t_pz)
    fl_naiden_rc = False
    for i in range(len(dict_moshn)): #по каждому дню
        if t_operacionnoe <= 0:
            break
        ispolnotel = find_user_in_day(dict_moshn[i],ispolnotel,start_limit)
        for j in range(len(dict_moshn[i]['empl'])): #по каждому рабочему месту
            if ispolnotel != "":
                if f"{dict_moshn[i]['empl'][j]['ФИО']} {dict_moshn[i]['empl'][j]['Должность']}" != ispolnotel: # подбор исполнителя
                    continue
            if dict_moshn[i]['empl'][j]['Код_РЦ'] == rc: # выбор РЦ
                fl_naiden_rc = True
                if dict_moshn[i]['empl'][j]['Пулл'][napravlenie] > 0 and dict_moshn[i]['empl'][j]['Время'] >= start_limit: #Если есть резерв по мощности и дата время начала не ранее лимита
                    KOEF_VREMENI = 1/dict_moshn[i]['empl'][j]['Коэфф_производит']
                    KOEF_BETWEEN_ORDER = round(dict_moshn[i]['empl'][j]['Между_нар_мин']/6,1)
                    t_oper_tmp = (t_operacionnoe + t_pz_tmp)*KOEF_VREMENI + KOEF_BETWEEN_ORDER

                    if t_oper_tmp > dict_moshn[i]['empl'][j]['Пулл'][napravlenie]:
                        t_oper_tmp = dict_moshn[i]['empl'][j]['Пулл'][napravlenie]
                    dict_moshn[i]['empl'][j]['Пулл'][napravlenie] -= t_oper_tmp
                    dt_nachalo = dict_moshn[i]['empl'][j]['Время']
                    dt_konec = dict_moshn[i]['empl'][j]['Время_конца']
                    if dt_nachalo > dt_konec:
                        print(f'ОШибка конец раньше начала')
                        return
                    rez_dt = F.date_add_time(dict_moshn[i]['empl'][j]['Время'], minutes=int(t_oper_tmp))
                    dolgnost = dict_moshn[i]['empl'][j]['Должность']
                    ispolnotel = f"{dict_moshn[i]['empl'][j]['ФИО']} {dolgnost}"
                    if rez_dt > dt_konec: # если предпологаемое время завершения работ позже конца рабочего дня
                        deficit_time_float = (rez_dt - dt_konec).total_seconds() / 60.0  #не помещается минут
                        dict_moshn[i]['empl'][j]['Время'] = dt_konec #переменное время  = концу дня
                        time_to_oper =round(((t_oper_tmp - deficit_time_float - KOEF_BETWEEN_ORDER) / KOEF_VREMENI)-t_pz_tmp,2) #Тшт = операционное время - пз - дефицит
                        t_operacionnoe -= time_to_oper
                        t_operacionnoe = round(t_operacionnoe,1)
                        list_plan_dse.append({'#':npp,'РМ':dict_moshn[i]['empl'][j]['Пномер'],'ФИОД':ispolnotel,
                                              'Должность':dolgnost,'Начало':dt_nachalo,'Конец':dt_konec,
                                              'Остаток':t_operacionnoe,'Дельта':rez_dt-dt_nachalo,'На_исполнение_минут':time_to_oper})
                        npp += 1
                        t_pz_tmp = 0
                        break
                    else:
                        dict_moshn[i]['empl'][j]['Время'] = rez_dt
                        time_to_oper =round(((t_oper_tmp - KOEF_BETWEEN_ORDER) / KOEF_VREMENI)-t_pz_tmp,2)
                        t_operacionnoe -= time_to_oper
                        t_operacionnoe = round(t_operacionnoe, 1)
                        list_plan_dse.append({'#':npp,'РМ':dict_moshn[i]['empl'][j]['Пномер'],'ФИОД': ispolnotel,
                                              'Должность':dolgnost, 'Начало': dt_nachalo, 'Конец': rez_dt,
                                              'Остаток':t_operacionnoe, 'Дельта':rez_dt-dt_nachalo,'На_исполнение_минут':time_to_oper})
                        npp += 1
                        t_pz_tmp = 0
                        break
    if t_operacionnoe > 0 and fl_naiden_rc==False:
        return False
    return list_plan_dse
