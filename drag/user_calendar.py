from project_cust_38.isdayoff_cust import ProdCalendar
import datetime
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.api_erp_commands as APIERP
import copy
#F.test_path()

put_db = F.bdcfg('BD_users')
put_emploee = F.tcfg('employee')
db_kplan = F.bdcfg('DB_kplan')
plecho = 15
WEEK_STEP_DAYS = -7


first_day_1 = F.date_add_days(F.now(''),WEEK_STEP_DAYS,'','').replace(day=1).date()


months = [first_day_1]
for i in range(1, plecho + 1):
    months.append(F.add_months(first_day_1, i).date())
calendar = ProdCalendar(locale='ru')

def count_empl_by_workforce(tabel_workforce,date_str,count_rab_day,podr,DICT_PODRAZD):
    data_month = tabel_workforce[date_str]
    summ_minutes = 0
    for key in data_month.keys():
        if key.startswith(podr):
            summ_minutes += data_month[key]/480
    count = summ_minutes/count_rab_day
    # ========db mnts_plan учет больных и прогулов по статистике ==========================
    statistic_deficit_emploers_time_percent = 0
    if podr in DICT_PODRAZD:
        statistic_deficit_emploers_time_percent = DICT_PODRAZD[podr]['statistic_deficit_emploers_time_percent']
    count *= (1 - statistic_deficit_emploers_time_percent / 100)
    # ========
    return round(count,2)


def count_empl(podr, spis_empl, DICT_PODRAZD, DICT_MNTS_PLAN, month,count_rab_day):
    count = 0
    #if month in DICT_MNTS_PLAN and DICT_PODRAZD[podr]['mnts_plan_names'] != '':
    #    list_mnts_fields = DICT_PODRAZD[podr]['mnts_plan_names'].split(';')
    #    for mnts_field in list_mnts_fields:
    #        if mnts_field in DICT_MNTS_PLAN[month]:
    #            count += DICT_MNTS_PLAN[month][mnts_field]
    #        else:
    #            print(f'{mnts_field} not in DICT_MNTS_PLAN[month]')
    #    count /= count_rab_day
    #    #========db mnts_plan учет больных и прогулов по статистике ==========================
    #    count *= (1 - DICT_MNTS_PLAN[month]['statistic_deficit_emploers_time_percent']/100)
    #    # ========
    #    return round(count,2)

    name_podr_ERP = ''
    if podr in DICT_PODRAZD:
        name_podr_ERP = DICT_PODRAZD[podr]['Наименование_ЕРП']
    else:
        print(f'{podr} не найден в DICT_PODRAZD')
    for i in range(len(spis_empl)):
        if name_podr_ERP in spis_empl[i][4]:
            count += 1


    return count * 0.762

def count_rab_days(clnd_dict):
    count= 0
    for i in clnd_dict:
        if clnd_dict[i].value == 0:
            count+=1
    return count
def add_jurnal_kplan(dict_podr, res, ima_table_jurnal_kplan,spis_empl,DICT_PODRAZD,DICT_MNTS_PLAN,month_str,tabel_workforce,DICT_PROFESSIONS_NICKNAME):

    list_podr_range = []
    for i in range(len(dict_podr)):
        for name in dict_podr.keys():
            if dict_podr[name]['Порядок'] == i:
                list_podr_range.append(name)
    cols = []
    cols_stat = ['', 'Выходные']
    cols_dn = ['podr', 'День недели']
    row_empl = []
    count_rab_day = count_rab_days(res)
    for i in range(len(list_podr_range)):
        row_empl.append([])
        row_empl[-1].append(list_podr_range[i])
        row_empl[-1].append(count_empl(dict_podr[list_podr_range[i]]['Наименование'],spis_empl,DICT_PODRAZD,DICT_MNTS_PLAN, month_str,count_rab_day))

    for i in res:
        cols.append('d_' + i.replace('.', '_'))
        cols_stat.append(res[i].value)
        cols_dn.append(F.strtodate(i, '%Y.%m.%d').weekday() + 1)
        for podr in row_empl:
            if res[i].value == 1:
                podr.append(0)
            else:
                podr.append(8 * podr[1])
    text = ' INTEGER, '.join(cols)
    frase_tmp = f"""CREATE TABLE IF NOT EXISTS {ima_table_jurnal_kplan}(
                           Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
                           Подразделение TEXT,
                            Примечание TEXT,
                           {text} INTEGER);
                        """
    CSQ.create_db_sql_c(db_kplan, frase_tmp)
    CSQ.add_line_into_db_sql_c(db_kplan, ima_table_jurnal_kplan, [cols_stat])
    CSQ.add_line_into_db_sql_c(db_kplan, ima_table_jurnal_kplan, [cols_dn])
    CSQ.add_line_into_db_sql_c(db_kplan, ima_table_jurnal_kplan, row_empl)
    print(f'    Добавлен {ima_table_jurnal_kplan}')


def add_tbl_empl(DICT_EMPLOYEE,res,ima_table_empl,dict_rab_vrema):
    cols = []
    cols_stat = ['', 'Выходные']
    cols_dn = ['ФИО', 'День недели']
    row_empl = []
    for empl in DICT_EMPLOYEE:
        if empl['Статус'] == "":
            continue
        row_empl.append([])
        row_empl[-1].append(f"{empl['ФИО']} {empl['Должность']}")
        row_empl[-1].append('')
    for i in res:
        cols.append('d_' + i.replace('.', '_'))
        cols_stat.append(res[i].value)
        cols_dn.append(F.strtodate(i, '%Y.%m.%d').weekday() + 1)
        for rc in row_empl:
            if res[i].value == 1:
                rc.append(0)
            else:
                norma = 8
                if ' '.join(rc[0].split()[:3]) in dict_rab_vrema:
                    norma = dict_rab_vrema[' '.join(rc[0].split()[:3])]
                rc.append(norma)
    text = ' INTEGER, '.join(cols)
    frase_tmp = f"""CREATE TABLE IF NOT EXISTS {ima_table_empl}(
                       Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
                       ФИО TEXT,
                        Примечание TEXT,
                       {text} INTEGER);
                    """
    CSQ.create_db_sql_c(put_db, frase_tmp)
    CSQ.add_line_into_db_sql_c(put_db, ima_table_empl, [cols_stat])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_empl, [cols_dn])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_empl, row_empl)
    print(f'    Добавлен {ima_table_empl}')


def add_tbl_jurnaltdz(list_rc,res,ima_table_empl):
    cols = []
    cols_stat = ['', 'Выходные']
    cols_dn = ['РЦ', 'Отв./День недели']
    row_rc = []
    for rc in list_rc.keys():
        if rc[:3] == '010' and rc[-2:] == '00' and '0000' not in rc:
            row_rc.append([])
            row_rc[-1].append(rc)
            row_rc[-1].append(list_rc[rc]['Отв_мастер_тдз'])
    for i in res:
        cols.append('d_' + i.replace('.', '_'))
        cols_stat.append(res[i].value)
        cols_dn.append(F.strtodate(i, '%Y.%m.%d').weekday() + 1)
        for rc in row_rc:
            if res[i].value == 1:
                rc.append(1)
            else:
                rc.append(0)
    text = ' INTEGER, '.join(cols)
    frase_tmp = f"""CREATE TABLE IF NOT EXISTS {ima_table_empl}(
                       Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
                       РЦ TEXT,
                        Примечание TEXT,
                       {text} INTEGER);
                    """
    CSQ.create_db_sql_c(put_db, frase_tmp)
    CSQ.add_line_into_db_sql_c(put_db, ima_table_empl, [cols_stat])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_empl, [cols_dn])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_empl, row_rc)
    print(f'    Добавлен {ima_table_empl}')

def add_tbl_eq(row_equip, res, ima_table_eq):
    row_equip_tmp = copy.deepcopy(row_equip)
    cols = []
    cols_stat = ['', 'Выходные']
    cols_dn = ['Пномер_оборудования', 'День недели']
    for i in res:
        cols.append('d_' + i.replace('.', '_'))
        cols_stat.append(res[i].value)
        cols_dn.append(F.strtodate(i, '%Y.%m.%d').weekday() + 1)
        for rc in row_equip_tmp:
            kol_vo = rc[0]
            if res[i].value == 1:
                rc.append(24*kol_vo)
            else:
                rc.append(24*kol_vo)
    for rc in row_equip_tmp:
        rc.pop(0)
    text = ' INTEGER, '.join(cols)
    frase_tmp = f"""CREATE TABLE IF NOT EXISTS {ima_table_eq}(
                       Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
                       Пномер_оборудования INTEGER,
                        Примечание TEXT,
                       {text} INTEGER);
                    """
    CSQ.create_db_sql_c(put_db, frase_tmp)
    CSQ.add_line_into_db_sql_c(put_db, ima_table_eq, [cols_stat])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_eq, [cols_dn])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_eq, row_equip_tmp)
    print(f'    Добавлен {ima_table_eq}')

def add_tbl_rm(row_rm, res, ima_table_rm):
    row_rm_tmp = copy.deepcopy(row_rm)
    cols = []
    cols_stat = ['', 'Выходные']
    cols_dn = ['Пномер_рм', 'День недели']
    for i in res:
        cols.append('d_' + i.replace('.', '_'))
        cols_stat.append(res[i].value)
        cols_dn.append(F.strtodate(i, '%Y.%m.%d').weekday() + 1)
        for rc in row_rm_tmp:
            if res[i].value == 1:
                rc.append(96)
            else:
                rc.append(96)
    text = ' INTEGER, '.join(cols)
    frase_tmp = f"""CREATE TABLE IF NOT EXISTS {ima_table_rm}(
                       Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
                       Пномер_рм INTEGER,
                        Примечание TEXT,
                       {text} INTEGER);
                    """
    CSQ.create_db_sql_c(put_db, frase_tmp)
    CSQ.add_line_into_db_sql_c(put_db, ima_table_rm, [cols_stat])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_rm, [cols_dn])
    CSQ.add_line_into_db_sql_c(put_db, ima_table_rm, row_rm_tmp)
    print(f'    Добавлен {ima_table_rm}')

def reload_tbl_empl(ima_table_empl, LIST_DICT_EMPLOYEE_FULL, res, dict_rab_vrema):
    USE_SINCHRON_FACT_TIME = False
    list_erp_tabels = []
    if 'mtdz' in ima_table_empl:
        USE_SINCHRON_FACT_TIME =True

    week_step = F.datetostr(F.date_add_days(F.now(''),WEEK_STEP_DAYS,'',''),"mtdz_%Y_%m_01")

    if USE_SINCHRON_FACT_TIME and (ima_table_empl == F.now("mtdz_%Y_%m_01") or week_step == ima_table_empl):
        ПериодРегистрации = F.datetostr(F.strtodate(ima_table_empl,"mtdz_%Y_%m_%d"),"ДАТАВРЕМЯ(%Y, %m, %d)")
        ПериодРегистрации_str = F.datetostr(F.strtodate(ima_table_empl, "mtdz_%Y_%m_%d"), "%d.%m.%Y")
        text = f"""
       ВЫБРАТЬ
    ТабельУчетаРабочегоВремениДанныеОВремени.Сотрудник.Наименование КАК Сотрудник,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени1.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов1
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов1,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени2.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов2
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов2,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени3.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов3
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов3,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени4.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов4
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов4,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени5.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов5
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов5,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени6.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов6
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов6,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени7.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов7
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов7,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени8.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов8
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов8,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени9.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов9
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов9,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени10.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов10
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов10,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени11.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов11
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов11,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени12.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов12
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов12,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени13.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов13
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов13,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени14.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов14
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов14,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени15.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов15
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов15,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени16.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов16
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов16,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени17.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов17
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов17,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени18.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов18
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов18,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени19.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов19
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов19,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени20.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов20
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов20,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени21.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов21
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов21,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени22.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов22
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов22,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени23.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов23
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов23,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени24.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов24
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов24,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени25.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов25
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов25,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени26.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов26
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов26,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени27.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов27
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов27,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени28.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов28
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов28,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени29.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов29
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов29,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени30.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов30
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов30,
    СУММА(ВЫБОР
            КОГДА ТабельУчетаРабочегоВремениДанныеОВремени.ВидВремени31.БуквенныйКод В ("Я", "Н", "РВ", "С")
                ТОГДА ТабельУчетаРабочегоВремениДанныеОВремени.Часов31
            ИНАЧЕ 0
        КОНЕЦ) КАК Часов31
ИЗ
    Документ.ТабельУчетаРабочегоВремени.ДанныеОВремени КАК ТабельУчетаРабочегоВремениДанныеОВремени
ГДЕ
    (ВЫРАЗИТЬ(ТабельУчетаРабочегоВремениДанныеОВремени.Ссылка.Комментарий КАК СТРОКА(20))) = "Фактическая явка"
    И ТабельУчетаРабочегоВремениДанныеОВремени.Ссылка.ПериодРегистрации = {ПериодРегистрации}

СГРУППИРОВАТЬ ПО
    ТабельУчетаРабочегоВремениДанныеОВремени.Сотрудник.Наименование
    """

        key, result_req = APIERP.get_wet_request(text=text)
        if key != 200:
            print(f'Ошибка получения данных из ЕРП')
            return
        if not result_req['data']:
            print(f'Табели Факт. явки за  {ПериодРегистрации_str} пуст')
        else:
            list_erp_tabels = result_req['data']

    def calc_summ_time(fio:str, day:str)->int|float:
        summ = 0
        name_field_erp = F.datetostr(F.strtodate(day,"d_%Y_%m_%d"),"Часов%#d")
        for item in list_erp_tabels:
            if item['Сотрудник'] == fio:
                for erp_day, erp_val_item in item.items():
                    if erp_day == name_field_erp:
                        summ+=erp_val_item

        return summ

    def update_time_fields(res,Пномер,start=None, end = None, clear=False):
        if start == None:
            for item in res:
                start = F.strtodate(item, "%Y.%m.%d")
                break

        if end == None:
            for item in res:
                end = F.strtodate(item, "%Y.%m.%d")


        list_fields = ['Примечание']
        list_times = ['"Увольнение"']
        for i in res:
            obj_date_res = F.strtodate(i, "%Y.%m.%d")
            if obj_date_res >=  start and obj_date_res <= end:
                list_fields.append(F.datetostr(obj_date_res, 'd_%Y_%m_%d'))
                if clear:
                    list_times.append("0")
                else:
                    if res[i].value == 1:
                        list_times.append('0')
                    else:
                        list_times.append('8')

        CSQ.custom_request_c(put_db, f"""UPDATE {ima_table_empl} SET ({', '.join(list_fields)}) = 
                 ({', '.join(list_times)}) WHERE Пномер = {Пномер};""")

    custom_request_c = f'SELECT * FROM {ima_table_empl} WHERE Пномер > 2 and ФИО != "";'
    list_from_scedule_month = CSQ.custom_request_c(put_db, custom_request_c,rez_dict=True)
    list_to_add_scedule = []
    print(f'    Обновление времени {ima_table_empl} ')
    used_indexes = set()
    for empl in LIST_DICT_EMPLOYEE_FULL:
        if empl['Режим'] == 'Абстракт' or empl['Статус'] == 'Увольнение':
                continue
        fio = empl['ФИО']
        Пномер = None

        for idx, item_scedule in enumerate(list_from_scedule_month):
            if f"{fio} {empl['Должность']}" == item_scedule['ФИО']:
                if USE_SINCHRON_FACT_TIME and list_erp_tabels:
                    Пномер = item_scedule['Пномер']# Если юзер найден в табеле то обновляем его
                    used_indexes.add(idx)
                    for day, val in item_scedule.items():
                        if 'd_' in day:
                            erp_val = calc_summ_time(fio,day)
                            # if erp_val != val:
                            CSQ.custom_request_c(put_db, f"""UPDATE {ima_table_empl} SET ({day}) = 
                                                                     ({erp_val}) and Примечание = '' WHERE Пномер == {Пномер};""")
                            print(f"        {fio}   {empl['Должность']}    {F.datetostr(F.strtodate(day, 'd_%Y_%m_%d'),'%d.%m.%Y')},  было {val} / стало {erp_val} час." )

                break
        if Пномер == None:# Если юзер не найден в табеле то добавляем его

            strok = [f"{fio} {empl['Должность']}", '']
            tek_dat = F.now('')  # Если он удален
            if empl['ДатаИзмененияДолжности'] != '':
                tek_dat = F.strtodate(empl['ДатаИзмененияДолжности'], "%Y-%m-%d")
            for i in res:
                if F.strtodate(i, "%Y.%m.%d") <= tek_dat:
                    strok.append(0)
                else:
                    if res[i].value == 1:
                        strok.append(0)
                    else:
                        norma = 8
                        if fio in dict_rab_vrema:
                            norma = dict_rab_vrema[fio]
                        strok.append(norma)
            list_to_add_scedule.append(strok)
    # ++ 04.07.25 по задаче 100056115 (Задвоение времени при смене должности + ошибка в отчете из-за дубликатов имен)
    for idx, item_scedule in enumerate(list_from_scedule_month):
        if idx not in used_indexes and item_scedule['Примечание'] != 'Увольнение':
            fields_to_update = {'Примечание': 'Увольнение'}
            pk = item_scedule['Пномер']
            for key, val in item_scedule.items():
                if F.is_date(key, 'd_%Y_%m_%d'):
                    fields_to_update[key] = 0
            fields = ','.join(f'{key} = {val!r}' for key, val in fields_to_update.items())
            CSQ.custom_request_c('SRV:BD_users.db', f'UPDATE {ima_table_empl} SET {fields} WHERE Пномер = {pk}')
    # -- 04.07.25

    for empl in LIST_DICT_EMPLOYEE_FULL:
        if empl['Режим'] == 'Абстракт' or empl['Статус'] != 'Увольнение':
            continue
        Пномер = None
        for item_scedule in list_from_scedule_month:
            if f"{empl['ФИО']} {empl['Должность']}" == item_scedule['ФИО'] and item_scedule['Примечание'] != 'Увольнение':
                Пномер = item_scedule['Пномер']
                break
        if Пномер == None:
            continue
        tek_dat =F.now("")# Если юзер ! найден в табеле
        if empl['ДатаИзмененияДолжности'] != '':
            tek_dat = F.strtodate(empl['ДатаИзмененияДолжности'], "%Y-%m-%d")
        else:
            tek_dat = F.strtodate(F.start_end_dates_c(tek_dat,format_in='',format_out="%Y-%m-%d",vid='m')[0])
            CSQ.custom_request_c(put_db, f"""UPDATE {ima_table_empl} SET (Примечание) = 
                                                     ("{empl['Статус']}") WHERE Пномер == {Пномер};""")
        update_time_fields(res,Пномер,tek_dat,None,True)

    if len(list_to_add_scedule)>0:
        CSQ.add_line_into_db_sql_c(put_db, ima_table_empl, list_to_add_scedule)
    print(f'        delete duplicaters')
    delete_duplicates(put_db,ima_table_empl,'ФИО')

def delete_duplicates(put_db, tbl,name_row):
    CSQ.custom_request_c(put_db,f"""delete   from {tbl} 
    where   rowid not in (select  min(rowid)
             from  {tbl} 
             group by {name_row});""")

def reload_tbl_eq(ima_table_eq, row_equip, res):
    row_equip_tmp = copy.deepcopy(row_equip)
    print(f'    {ima_table_eq} на месте')
    print(f'     обновление')
    custom_request_c = f'SELECT Пномер_оборудования FROM {ima_table_eq} WHERE Пномер_оборудования != "" AND Пномер > 2'
    rez = CSQ.custom_request_c(put_db, custom_request_c, hat_c=False)
    rez = [i[0] for i in rez]
    strok_rez = []
    for i in range(len(row_equip_tmp)):
        if row_equip_tmp[i][1] not in rez:
            strok = [row_equip_tmp[i][1], '']
            tek_dat = F.now()
            for day in res:
                if F.strtodate(day, "%Y.%m.%d") <= F.strtodate(tek_dat):
                    strok.append(0)
                else:
                    strok.append(24*row_equip_tmp[i][0])
            strok_rez.append(strok)
    CSQ.add_line_into_db_sql_c(put_db, ima_table_eq, strok_rez)


def reload_tbl_jurnaltdz(list_podr, ima_table_jurnaltdz):
    custom_request_c = f'SELECT * FROM {ima_table_jurnaltdz}'
    rez = CSQ.custom_request_c(put_db, custom_request_c, rez_dict=True)
    for i in range(len(rez)):
        if rez[i]['РЦ'] in list_podr:
            if rez[i]['Примечание'] != list_podr[rez[i]['РЦ']]['Отв_мастер_тдз']:
                CSQ.custom_request_c(put_db,f"""UPDATE {ima_table_jurnaltdz} SET Примечание 
                = '{list_podr[rez[i]['РЦ']]['Отв_мастер_тдз']}' WHERE Пномер = {rez[i]['Пномер']}""")


def reload_tbl_rm(ima_table_rm, row_rm, res):
    row_rm_tmp = copy.deepcopy(row_rm)
    print(f'    {ima_table_rm} на месте')
    print(f'     обновление')
    custom_request_c = f'SELECT Пномер_рм FROM {ima_table_rm} WHERE Пномер_рм != "" AND Пномер > 2'
    rez = CSQ.custom_request_c(put_db, custom_request_c, hat_c=False)
    rez = [i[0] for i in rez]
    strok_rez = []
    for i in range(len(row_rm_tmp)):
        if row_rm_tmp[i][0] not in rez:
            strok = [row_rm_tmp[i][0], '']
            tek_dat = F.now()
            for i in res:
                if F.strtodate(i, "%Y.%m.%d") <= F.strtodate(tek_dat):
                    strok.append(0)
                else:
                    strok.append(96)
            strok_rez.append(strok)
    CSQ.add_line_into_db_sql_c(put_db, ima_table_rm, strok_rez)


def reload_jurnal_kplan(dict_podr, res, ima_table_jurnal_kplan,spis_empl,DICT_PODRAZD,DICT_MNTS_PLAN,month_str,tabel_workforce, DICT_PROFESSIONS_NICKNAME):

    def count_empl_adapt(month_str, tabel_workforce,DICT_PODRAZD,podr,count_rab_day,DICT_MNTS_PLAN,spis_empl):
        if month_str in tabel_workforce and DICT_PODRAZD[podr]['Группа_для_расч_норм_и_ганта'] != '':
            count_user = count_empl_by_workforce(tabel_workforce, month_str, count_rab_day, podr,DICT_PODRAZD)
            if count_user == 0:
                count_user = count_empl(podr, spis_empl, DICT_PODRAZD, DICT_MNTS_PLAN, month_str, count_rab_day)
        else:
            count_user = count_empl(podr, spis_empl, DICT_PODRAZD, DICT_MNTS_PLAN, month_str, count_rab_day)
        return count_user


    print(f'    {ima_table_jurnal_kplan} обновление')
    dict_podr_old = F.deploy_dict_c(CSQ.custom_request_c(db_kplan,f"""SELECT Подразделение,
     Примечание FROM {ima_table_jurnal_kplan}""",rez_dict=True),'Подразделение')
    dict_to_add = dict()
    dict_to_edit = dict()
    count_rab_day = count_rab_days(res)
    for podr in dict_podr.keys():
        count_user = count_empl_adapt(month_str, tabel_workforce, DICT_PODRAZD, podr, count_rab_day, DICT_MNTS_PLAN,
                                      spis_empl)
        if podr not in dict_podr_old:
            dict_to_add[podr] = count_user
        else:
            if round( F.valm(dict_podr_old[podr]),3) != round(count_user,3):
                CSQ.custom_request_c(db_kplan,f"""UPDATE {ima_table_jurnal_kplan} SET Примечание = "{count_user}" WHERE Подразделение = "{podr}";""")
                dict_to_edit[podr] = count_user
    if len(dict_to_add) > 0:
        row_empl = []
        for name_podr, count_empl_int in dict_to_add.items():
            row_empl.append([])
            row_empl[-1].append(name_podr)
            row_empl[-1].append(count_empl_int)
        for date_clnd in res:
            for podr in row_empl:
                if res[date_clnd].value == 1:
                    podr.append(0)
                else:
                    podr.append(8 * podr[1])

        list_kol = CSQ.list_of_columns_c(db_kplan, ima_table_jurnal_kplan)[1:]
        CSQ.custom_request_c(db_kplan,f"""INSERT INTO {ima_table_jurnal_kplan}({", ".join(list_kol)}) 
         VALUES ({CSQ.questions_for_mask(row_empl[0])})""",list_of_lists_c=row_empl)
        print(f'    Добавлены {dict_to_add}')

    if len(dict_to_edit) != 0:
        row_empl = []

        for podr in dict_to_edit.keys():
            row_empl.append([])
            row_empl[-1].append(podr)
            row_empl[-1].append(dict_to_edit[podr])
        list_kol = CSQ.list_of_columns_c(db_kplan, ima_table_jurnal_kplan)[1:]
        tmp_list_kol = [list_kol[0],list_kol[1]]
        for i, name_podr in enumerate(res):
            if F.now('') >= F.strtodate(name_podr, "%Y.%m.%d"):
                continue
            tmp_list_kol.append(list_kol[i + 2])
            for podr in row_empl:
                if res[name_podr].value == 1:
                    podr.append(0)
                else:
                    podr.append(8 * podr[1])
        for podr in row_empl:
            CSQ.custom_request_c(db_kplan,f"""UPDATE {ima_table_jurnal_kplan} SET ({", ".join(tmp_list_kol)}) 
             = ({CSQ.questions_for_mask(row_empl[0])}) WHERE Подразделение = "{podr[0]}";""",list_of_lists_c=[podr])
        print(f'    Изменены {dict_to_edit.keys()}')

    #==============UPDATE HOLYDAYS+++++++++++++++++
    dict_holy_old = CSQ.custom_request_c(db_kplan,f"""SELECT * FROM {ima_table_jurnal_kplan} WHERE Пномер = 1""", one=True, rez_dict=True)
    for k,v in dict_holy_old.items():
        if not F.is_date(k,'d_%Y_%m_%d'):
            continue
        date_for_api = F.datetostr(F.strtodate(k,'d_%Y_%m_%d'),"%Y.%m.%d")
        if v != int(res[date_for_api]):
            CSQ.custom_request_c(db_kplan,f"""UPDATE {ima_table_jurnal_kplan} SET ({k}) = ({int(res[date_for_api])}) WHERE Пномер = 1""")
            print(f'Обновлен выходной {ima_table_jurnal_kplan} - {k} было {v} стало {int(res[date_for_api])}')
def check_empl(ima_table_empl,LIST_DICT_EMPLOYEE_FULL,res,dict_rab_vrema):
    if ima_table_empl not in CSQ.get_list_of_tables_c(put_db):
        add_tbl_empl(LIST_DICT_EMPLOYEE_FULL, res, ima_table_empl,dict_rab_vrema)
    else:
        print(f'    {ima_table_empl} на месте')
        print(f'     обновление')
        reload_tbl_empl(ima_table_empl, LIST_DICT_EMPLOYEE_FULL, res,dict_rab_vrema)

def check_eq(ima_table_eq, row_equip, res):
    if ima_table_eq not in CSQ.get_list_of_tables_c(put_db):
        add_tbl_eq(row_equip, res, ima_table_eq)
    else:
        print(f'    {ima_table_eq} на месте')
        print(f'     обновление')
        reload_tbl_eq(ima_table_eq, row_equip, res)

def check_rm(ima_table_rm, row_rm, res):
    if ima_table_rm not in CSQ.get_list_of_tables_c(put_db):
        add_tbl_rm(row_rm, res, ima_table_rm)
    else:
        print(f'    {ima_table_rm} на месте')
        print(f'     обновление')
        reload_tbl_rm(ima_table_rm, row_rm, res)

def check_jurnal_kplan(ima_table_jurnal_kplan, res, spis_empl,DICT_PODRAZD,DICT_MNTS_PLAN,month_str,tabel_workforce,
                       DICT_PROFESSIONS_NICKNAME):
    list_podr = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM podrazdel""", rez_dict=True)
    list_podr = F.deploy_dict_c(list_podr, 'Имя')
    if ima_table_jurnal_kplan not in CSQ.get_list_of_tables_c(db_kplan):
        add_jurnal_kplan(list_podr, res, ima_table_jurnal_kplan,spis_empl,DICT_PODRAZD,DICT_MNTS_PLAN,month_str,
                         tabel_workforce, DICT_PROFESSIONS_NICKNAME)
    else:
        print(f'    {ima_table_jurnal_kplan} на месте')
        print(f'     обновление')
        reload_jurnal_kplan(list_podr, res, ima_table_jurnal_kplan,spis_empl,DICT_PODRAZD,DICT_MNTS_PLAN,month_str,
                            tabel_workforce, DICT_PROFESSIONS_NICKNAME)

def check_jurnaltdz(ima_table_jurnaltdz, res):
    list_podr = CSQ.custom_request_c(put_db,f"""SELECT * FROM rab_c""", rez_dict=True)
    list_podr = F.deploy_dict_c(list_podr,'Код')
    if ima_table_jurnaltdz not in CSQ.get_list_of_tables_c(put_db):
        add_tbl_jurnaltdz(list_podr, res, ima_table_jurnaltdz)
    else:
        print(f'    {ima_table_jurnaltdz} на месте')
        print(f'     обновление')
        reload_tbl_jurnaltdz(list_podr, ima_table_jurnaltdz)

def delta_time(nach,konec):
    d_nach = F.shtamp_from_date(f'2022-01-11 {nach}', "%Y-%m-%d %H:%M")
    d_konec = F.shtamp_from_date(f'2022-01-11 {konec}', "%Y-%m-%d %H:%M")
    if d_nach > d_konec:
        d_konec += 86400
    if d_konec - d_nach > 1800:
        delta = (d_konec - d_nach-1800) / 3600
    else:
        delta = (d_konec - d_nach) / 3600
    return round(delta,1)

def get_dict_prof_vid(db_users):
    custom_request_c = f'''SELECT * FROM professions INNER JOIN vid_rab_po_dolg 
    ON vid_rab_po_dolg.Вид_работ = professions.вид_работ,
     group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan WHERE Вкл = 1 and group_vid_rab_for_plan.composite = 0'''
    SPIS_prof = CSQ.custom_request_c(db_users, custom_request_c, hat_c=False,rez_dict=True,)
    if SPIS_prof == False:
        return  False
    DICT_VID_RABOT = F.deploy_dict_c(SPIS_prof, 'вид_работ')
    DICT_PROFESSIONS = F.deploy_dict_c(SPIS_prof, 'код')
    return DICT_PROFESSIONS,DICT_VID_RABOT

def main():
    print('==================================')
    print('Проверка производственного календаря...')
    #spis_empl = CSQ.custom_request_c(put_db,"""SELECT * FROM employee""")
    spis_empl_live = CSQ.custom_request_c(put_db, """SELECT * FROM employee WHERE Статус == "Работа";""")
    LIST_DICT_EMPLOYEE_FULL = CMS.list_emploee_full_with_del(put_db)

    query = f"""SELECT Кол_во, Пномер, "" AS Прим FROM equipment"""
    row_equip = CSQ.custom_request_c(put_db,query,hat_c=False)

    query = f"""SELECT Пномер, "" AS Прим FROM rab_mesta"""
    row_rm = CSQ.custom_request_c(put_db,query,hat_c=False)
    DICT_PODRAZD = F.deploy_dict_c(CSQ.custom_request_c(db_kplan, """SELECT * FROM podrazdel """,rez_dict=True),'Имя')
    DICT_MNTS_PLAN = F.deploy_dict_c(CSQ.custom_request_c(db_kplan, """SELECT * FROM mnts_plan """,rez_dict=True),'Дата')
    custom_request_c = """SELECT 
         s1.ФИО as ФИО_1см, s1.Должность as Должность_1см, rab_mesta.Время_начала_1, rab_mesta.Время_конца_1,
         s2.ФИО as ФИО_2см, s2.Должность as Должность_2см, rab_mesta.Время_начала_2, rab_mesta.Время_конца_2,
         s3.ФИО as ФИО_3см, s3.Должность as Должность_3см, rab_mesta.Время_начала_3, rab_mesta.Время_конца_3
         FROM rab_mesta
         INNER JOIN employee s1 ON s1.Пномер == rab_mesta.ФИО_1
         INNER JOIN employee s2 ON s2.Пномер == rab_mesta.ФИО_2
         INNER JOIN employee s3 ON s3.Пномер == rab_mesta.ФИО_3"""
    spis_rab_mesta = CSQ.custom_request_c(put_db, custom_request_c, hat_c=True, rez_dict=True)
    dict_rab_vrema = dict()
    for  i in range(len(spis_rab_mesta)):
        dict_rab_vrema[spis_rab_mesta[i]['ФИО_1см']] = delta_time(spis_rab_mesta[i]["Время_начала_1"],spis_rab_mesta[i]["Время_конца_1"])
        dict_rab_vrema[spis_rab_mesta[i]['ФИО_2см']] = delta_time(spis_rab_mesta[i]["Время_начала_2"],
                                                                  spis_rab_mesta[i]["Время_конца_2"])
        dict_rab_vrema[spis_rab_mesta[i]['ФИО_3см']] = delta_time(spis_rab_mesta[i]["Время_начала_3"],
                                                                  spis_rab_mesta[i]["Время_конца_3"])
    DICT_PROFESSIONS, DICT_VID_RABOT = get_dict_prof_vid(put_db)
    DICT_PROFESSIONS_NICKNAME = F.deploy_dict_c(CSQ.custom_request_c(put_db, f"""SELECT 
     * FROM group_vid_rab_for_plan WHERE composite = 0;""", rez_dict=True), 'name')
    tabel_workforce = CMS.load_tabel_workforce(db_kplan,DICT_PROFESSIONS, DICT_VID_RABOT,'name')
    for m in months:
        # ima_table_empl = 'm_' + str(m).replace('-', '_') #04.07.25
        ima_table_empl_tdz = 'mtdz_' + str(m).replace('-', '_')
        ima_table_eq = 'eq_' + str(m).replace('-', '_')
        ima_table_rm = 'rm_' + str(m).replace('-', '_')
        ima_table_jur_tdz = 'jurnaltdz_' + str(m).replace('-', '_')
        ima_table_jurnal_kplan = 'm_cld_' + str(m).replace('-', '_')

        month_str = F.datetostr(m,"%Y-%m-%d")

        calendar_dict = calendar.month(m)

        check_jurnal_kplan(ima_table_jurnal_kplan, calendar_dict, spis_empl_live,DICT_PODRAZD,DICT_MNTS_PLAN,
                           month_str,tabel_workforce,DICT_PROFESSIONS_NICKNAME)
        check_empl(ima_table_empl_tdz, LIST_DICT_EMPLOYEE_FULL, calendar_dict, dict_rab_vrema)
        # check_empl(ima_table_empl,LIST_DICT_EMPLOYEE_FULL,calendar_dict,dict_rab_vrema) # #04.07.25
        check_eq(ima_table_eq, row_equip, calendar_dict)
        check_rm(ima_table_rm, row_rm, calendar_dict)
        check_jurnaltdz(ima_table_jur_tdz, calendar_dict)
    print('Проверка производственного календаря завершено')
    print('==================================')
    calendar.close()
    return


print('==================================')
