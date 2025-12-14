from typing import Dict
import sqlalchemy as SQA
from sqlalchemy import create_engine, Table, MetaData, Column, ForeignKey, literal_column, func, DateTime
from sqlalchemy.sql import select, and_, or_, not_, between
import sqlite3
from project_cust_38.Cust_Functions import is_numeric, valm, now, open_file_c, strtodate, existence_file_c, delete_file_c, datetostr, write_file_c
from sqlalchemy.schema import DDLElement, PrimaryKeyConstraint
import copy as kopi
import sqlalchemy.util.compat
import sip
import pysqlite2
import MySQLdb
import psycopg2


slov_tip_d = {"Integer".upper(): SQA.Integer,
                  "str".upper(): SQA.Text,
                  "float".upper(): SQA.Float,
                  "Boolean".upper(): SQA.Boolean,
                  "Date".upper(): SQA.Date,
                  "DateTime".upper(): SQA.DateTime,
                  "text".upper(): SQA.Text
                  }
slov_tip_d_2 = {"Integer".upper(): "SQA.Integer",
                  "str".upper(): "SQA.Text",
                  "float".upper(): "SQA.Float",
                  "Boolean".upper(): "SQA.Boolean",
                  "Date".upper(): "SQA.Date",
                  "DateTime".upper(): "SQA.DateTime",
                  "text".upper(): "SQA.Text"
                  }

if __name__ == '__main__':
    exit()


def log_opal(strok: str):
    SL_LOG: Dict[str, str] = {'and': "and_", 'or': "or_", 'not': "not_",'': ""}
    strok = strok.strip().lower()
    return SL_LOG[strok]


def prosmotr_bd(bd_put_name):
    sp = spis_tabl_bd(bd_put_name)
    for i in sp:
        print(i)
        spis_col = spis_col_tabl_bd(bd_put_name, i)
        print(spis_col)
        spis_stroki = spis_all_strok_tabl_bd(bd_put_name, i)
        print(spis_stroki)


def vivod_spiska(spis):
    for i in spis:
        print(i)


def dobav_stroki_bd(bd_put_name, ima_tabl: str, spis_slovarei):
    '''spis_slovarei
    [{'name': 'Rajiv', 'lastname': 'Khanna'},
    {'name': 'Komal', 'lastname': 'Bhandari'}] '''
    engine = create_engine('sqlite:///' + bd_put_name, echo=False)
    meta = MetaData(engine)
    tabl = Table(ima_tabl, meta, autoload=True)
    conn = engine.connect()
    conn.execute(tabl.insert(), spis_slovarei)


def _preabrozov_sp_pod_custom_request_c(spis_usloviy):
    '''
    :param spis_usloviy:
    [[col,'==<>!=in',znach'],[],...]
    :return:
    '''
    spis_usloviy_f = kopi.deepcopy(spis_usloviy)
    for i in range(len(spis_usloviy_f)):
        if len(spis_usloviy_f[i]) != 3:
            raise NameError('Не верное число элементов условий')
        if '.c.' not in spis_usloviy_f[i][0]:
            spis_usloviy_f[i][0] = f'tabl.c.{spis_usloviy_f[i][0]}'
        else:
            spis_usloviy_f[i][0] = _podst_dict(spis_usloviy_f[i][0])
        if isinstance(spis_usloviy_f[i][2], type('test')):
            if '.c.' not in spis_usloviy_f[i][2]:
                spis_usloviy_f[i][2] = f'"{spis_usloviy_f[i][2]}"'
            else:
                spis_usloviy_f[i][2] = _podst_dict(spis_usloviy_f[i][2])
        elif isinstance(spis_usloviy_f[i][2], type(strtodate(now()))):
            spis_usloviy_f[i][2] = f'strtodate("{datetostr(spis_usloviy_f[i][2])}")'
        else:
            spis_usloviy_f[i][2] = f'{spis_usloviy_f[i][2]}'
        if spis_usloviy_f[i][1] == 'in':
            spis_usloviy_f[i][1] = f'{spis_usloviy_f[i][0]}.contains({spis_usloviy_f[i][2]})'
            spis_usloviy_f[i][2] = ""
            spis_usloviy_f[i][0] = ""

    tmp_strok = []
    for uslovie in spis_usloviy_f:
        tmp_strok.append(' '.join(uslovie))
    tmp_strok = ', '.join(tmp_strok)
    return tmp_strok


def _preabrozov_sp_pod_custom_request_c_values(spis_znachiy):
    '''
        :param spis_usloviy:
        [[col,znach'],[],...]
        :return:
        '''
    for i in range(len(spis_znachiy)):
        if len(spis_znachiy[i]) != 2:
            raise NameError('Не верное число элементов значений')
        spis_znachiy[i][0] = f'{spis_znachiy[i][0]}'
        if isinstance(spis_znachiy[i][1], type('s')):
            spis_znachiy[i][1] = f'"{spis_znachiy[i][1]}"'
        elif isinstance(spis_znachiy[i][1], type(strtodate(now()))):
            spis_znachiy[i][1] = f'strtodate("{datetostr(spis_znachiy[i][1])}")'
        else:
            spis_znachiy[i][1] = f'{spis_znachiy[i][1]}'

    tmp_strok = []
    for znachie in spis_znachiy:
        tmp_strok.append('='.join(znachie))
    tmp_strok = ', '.join(tmp_strok)
    return tmp_strok


def delete_stroki_bd(bd_put_name, ima_tabl: str, spis_usloviy, echo_st=True, log_op='and'):
    '''
    spis_usloviy
    [[col,znak,znach],[]]
    '''
    engine = create_engine('sqlite:///' + bd_put_name, echo=echo_st)
    meta = MetaData(engine)
    conn = engine.connect()
    sp_tab = dict()
    sp_tab[ima_tabl] = (Table(ima_tabl, meta, autoload=True))
    tmp_strok = _preabrozov_sp_pod_custom_request_c(spis_usloviy)
    if tmp_strok is None:
        return
    delete_query = eval(f'sp_tab[ima_tabl].delete().where({log_opal(log_op)}({tmp_strok}))')

    conn.execute(delete_query)


def update_stroki_bd(bd_put_name, ima_tabl:str, spis_usloviy, spis_znachiy, echo_st=True, log_op='and'):
    '''
    spis_usloviy
    [[col,znak,znach],[]]
    spis_znachiy
    [[col,znach],[]]
    log_op = and/or/not
    '''
    engine = create_engine('sqlite:///' + bd_put_name, echo=echo_st)
    meta = MetaData(engine)
    #tabl = Table(ima_tabl, meta, autoload=True)
    conn = engine.connect()
    sp_tab = dict()
    sp_tab[ima_tabl] = (Table(ima_tabl, meta, autoload=True))
    tmp_strok = _preabrozov_sp_pod_custom_request_c(spis_usloviy)
    if tmp_strok is None:
        return
    tmp_strok_values = _preabrozov_sp_pod_custom_request_c_values(spis_znachiy)
    if tmp_strok_values is None:
        return
    update_query = eval(f'sp_tab[ima_tabl].update().where({log_opal(log_op)}({tmp_strok})).values({tmp_strok_values})')
    conn.execute(update_query)

def _podst_dict(stroka:str):
    arr = stroka.split('.')
    arr[0] = f'sp_tab["{arr[0]}"]'
    stroka = '.'.join(arr)
    return stroka

def spis_select_stroki_bd(bd_put_name, spis_tabl, spis_usloviy, spis_kolon=(), log_op='and', echo_st=True):
    '''
    spis_tabl
    ["zhurnal","Naryad"]
    spis_usloviy
     [[imacol,znak,znach],[]]
     spis_kolon
     ["zhurnal","Naryad"]/["zhurnal.c.Nom","Naryad.c.ID"]
    '''
    engine = create_engine('sqlite:///' + bd_put_name, echo=echo_st)
    meta = MetaData(engine)
    sp_tab = dict()
    for i in spis_tabl:
        sp_tab[i] = (Table(i, meta, autoload=True))
    spis_kolon_f = []
    if spis_kolon == ():
        spis_kolon_f = f'sp_tab["{spis_tabl[0]}"]'
    else:
        for i in range(len(spis_kolon)):
            spis_kolon_f.append(_podst_dict(spis_kolon[i]))
        spis_kolon_f = ', '.join(spis_kolon_f)
    conn = engine.connect()
    tmp_strok = _preabrozov_sp_pod_custom_request_c(spis_usloviy)
    select_query = eval(f'select([{spis_kolon_f}]).where({log_opal(log_op)}({tmp_strok}))')
    result = conn.execute(select_query)
    s = []
    for row in result:
        s.append(list(row))
    return s


def spis_tabl_bd(bd_put_name):
    engine = SQA.create_engine('sqlite:///' + bd_put_name, echo=False)
    meta = SQA.MetaData(engine)
    meta.reflect(engine)
    s = []
    for r in meta.sorted_tables:
        s.append(r.key)
    return s


def spis_col_tabl_bd(bd_put_name, ima_tabl: str):
    engine = create_engine('sqlite:///' + bd_put_name, echo=False)
    meta = MetaData(engine)
    obj = Table(ima_tabl, meta, autoload=True)
    s = []
    for r in obj.columns:
        s.append(r.key)
    return s


def spis_all_strok_tabl_bd(bd_put_name, ima_tabl: str):
    engine = create_engine('sqlite:///' + bd_put_name, echo=False)
    meta = MetaData(engine)
    obj = Table(ima_tabl, meta, autoload=True)
    conn = engine.connect()
    s = obj.select()
    result = conn.execute(s)
    stroki = []
    for row in result:
        stroki.append(row)
    return stroki


def create_bd(bd_put_name, perezapis: bool = False, echo_st=True, *spiski):
    ''' spisok[ima_tabl-str,
        [ima_kol-str,
        int/str/float/Boolean/Date/DateTime-str,
        default-  ,Значение по умолчанию в случае, если значение для столбца не указано при вставке новой строки.
        nullable-bool True, указывает, что столбец будет отображаться как разрешающий NULL,
        primary_key отмечает столбец как основной-bool,
        ForeignKey("Authors.id_author")-str]
        ,[...],...]'''
    if existence_file_c(bd_put_name):
        if not perezapis:
            return
        else:
            delete_file_c(bd_put_name)

    meta = SQA.MetaData()
    for spisok in spiski:
        spis_tmp = []
        for i in range(1, len(spisok)):
            for key in slov_tip_d.keys():
                if spisok[i][1].upper() in key:
                    spisok[i][1] = slov_tip_d[key]
                    break
            if len(spisok[i]) < 6:
                for j in range(6 - len(spisok[i])):
                    spisok[i].append("")
            for j in range(3, len(spisok[i])):
                if spisok[i][j] == "":
                    spisok[i][j] = False
            if spisok[i][5]:
                spis_tmp.append(SQA.Column(spisok[i][0], spisok[i][1], ForeignKey(spisok[i][5]),
                                           nullable=spisok[i][3], primary_key=spisok[i][4], default=spisok[i][2]))
            else:
                spis_tmp.append(SQA.Column(spisok[i][0], spisok[i][1], nullable=spisok[i][3],
                                           primary_key=spisok[i][4], default=spisok[i][2]))
        dvigenie = SQA.Table(spisok[0], meta, *spis_tmp)
    engine = SQA.create_engine('sqlite:///' + bd_put_name, echo=echo_st)
    meta.create_all(engine)


def export_bd_tabl(bd_put_name, putimaf, ima_tabl: str, shap: bool = True):
    stroki_bd = spis_all_strok_tabl_bd(bd_put_name, ima_tabl)
    spis_strok = []
    for i in range(len(stroki_bd)):
        spis_strok.append(list(stroki_bd[i]))
    if shap:
        spis_kol = spis_col_tabl_bd(bd_put_name, ima_tabl)
        spis_strok.insert(0, spis_kol)
    write_file_c(putimaf, spis_strok, "|")


# spis_n = open_file_c('P:\\Python\\Terminal\\Data\\Naryad.txt',False,'|',False)
# for i in range(len(spis_n[0])):
#   if spis_n[0][i] == 'Время, час.':
#       spis_n[0][i] = 'Время_час'
spisok_tabl = ["Naryad",
               ['No', 'int', '', '', True],
               ['МК', 'int', '', '', ''],
               ['Дата', 'DateTime', now(), '', ''],
               ['Проект,заказ', 'int', '', '', ''],
               ['Задание', 'str', '', '', ''],
               ['Время_час', 'float', '', '', ''],
               ['Сверхурочно, час.', 'int', '', '', ''],
               ['Автор', 'str', '', '', ''],
               ['Вид нормы', 'str', '', '', ''],
               ['Вечерение', 'str', '', '', ''],
               ['Вес', 'float', '', '', ''],
               ['Вид', 'str', '', '', ''],
               ['Кол-во', 'int', '', '', ''],
               ['Позиции', 'str', '', '', ''],
               ['Этап', 'str', '', '', ''],
               ['Скомплектвано', 'str', '', '', ''],
               ['Дата комплектовки', 'DateTime', None, True, ''],
               ['ФИО', 'str', '', '', ''],
               ['ФИО2', 'str', '', '', ''],
               ['Факт по наряду', 'str', '', '', ''],
               ['Разница', 'float', '', '', ''],
               ['Стасус наряда', 'str', '', '', ''],
               ['По теории', 'float', '', '', ''],
               ['Примечание', 'str', '', '', ''],
               ['N операции', 'str', '', '', ''],
               ['ID', 'str', 'none', True, ''],
               ['Код проф.', 'str', '', True, ''],
               ['КР', 'int', 1, True, ''],
               ['КОИД', 'int', 1, True, '']]


def __oformlenie_sp(spis_n):
    spis_sl = []
    for i in range(1, len(spis_n) - 1):
        slov_tmp = dict()
        for j in range(len(spis_n[0]) - 1):
            if j > len(spis_n[i]) - 1:
                spis_n[i].append(None)
            if j == 2 or j == 16:
                if spis_n[i][j] != '':
                    spis_n[i][j] = strtodate(spis_n[i][j])
                else:
                    spis_n[i][j] = None
            if j == 5 or j == 10 or j == 20 or j == 22:
                if '.' in spis_n[i][j]:
                    j = j
                spis_n[i][j] = valm(spis_n[i][j])
            if j == 25:
                if spis_n[i][j] == '':
                    spis_n[i][j] = 'None'

            slov_tmp[spis_n[0][j]] = spis_n[i][j]
        for _ in range(len(spis_n[i]), len(spis_n[0])):
            spis_n[i].append(None)
        # print(i,spis_n[i][0], spis_n[i][25])
        spis_sl.append(slov_tmp)
    return spis_sl


# spis_sl = __oformlenie_sp(spis_n)

#bd_put_name = 'P:\\Python\\testBD\\sqlachemy_test\\Naryadi.db'

# create_bd(bd_put_name,True,False,spisok_tabl)
# prosmotr_bd(bd_put_name)
# dobav_stroki_bd(bd_put_name,"Naryad",spis_sl)
# prosmotr_bd(bd_put_name)

# vivod_spiska(spis_col_tabl_bd(bd_put_name,"Naryad"))
# vivod_spiska(spis_all_strok_tabl_bd(bd_put_name,"Naryad"))


# spis_usl = [['Автор','in','решнев'],['Дата', '<', strtodate('19.10.2020 07:30:00')],
# ['Дата', '>', strtodate('19.10.2020 07:11:00')]]
# spis_usl_0 = [['No','==','2167']]
# delete_stroki_bd(bd_put_name,"Naryad",spis_usl_0)


# spis_usl_upd = [['No', '==', 5],['No', '==', 6]]
# spis_zn_upd = [['Время_час', 22.0]]
# update_stroki_bd(bd_put_name,"Naryad",spis_usl_upd,spis_zn_upd,False,'or')

#spis_usl = [['No', '==', 5], ['No', '==', 6]]
#vivod_spiska(spis_select_stroki_bd(bd_put_name, "Naryad", spis_usl, ["No", "Дата"], 'or'))

# export_bd_tabl(bd_put_name,'P:\\Python\\testBD\\sqlachemy_test\\Naryadi.txt',"Naryad",True)
#
#def sozdat_bd():
#    bd_putname = F.scfg('BDzhurnal') + os.sep + 'BDzhurnal'
#    AL.create_bd(bd_putname, True, True,
#                 ["Zhurnal",
#                  ['Nom', 'int', "", '', True],
#                  ['Дата', 'DateTime', F.now(), '', ''],
#                  ['Метка', 'float', F.get_time_shtamp_c(), '', ''],
#                  ['Наряд', 'int', '', '', ''],
#                  ['Фио', 'str', '', '', ''],
#                  ['Проектпу', 'str', '', '', ''],
#                  ['Этап', 'str', '', '', ''],
#                  ['Последний', 'str', '', True, ''],
#                  ['Статус', 'str', '', '', ''],
#                  ['Времят', 'str', '', '', ''],
#                  ['Времяф', 'str', '', '', ''],
#                  ['Примечание', 'str', '', True, '']
#                  ])
#
#
#def napolnit_bd():
#    bd_putname = F.scfg('BDzhurnal') + os.sep + 'BDzhurnal'
#    spis_dob = []
#    if F.existence_file_c(F.tcfg('BDzhurnal')) == False:
#        return
#    spis_tmp = F.open_file_c(F.tcfg('BDzhurnal'), False, "|", False)
#
#    for i in range(len(spis_tmp)):
#        if len(spis_tmp[i]) < 19:
#            for _ in range(len(spis_tmp[i]), 20):
#                spis_tmp[i].append("")
#        slovar = {
#            # 'Nom':i,
#            'Дата': F.strtodate(spis_tmp[i][0]),
#            'Метка': F.valm(spis_tmp[i][1]),
#            'Наряд': spis_tmp[i][2],
#            'Фио': spis_tmp[i][3],
#            'Проектпу': spis_tmp[i][4],
#            'Этап': spis_tmp[i][5],
#            'Последний': spis_tmp[i][6],
#            'Статус': spis_tmp[i][7],
#            'Времят': spis_tmp[i][8],
#            'Времяф': spis_tmp[i][9],
#            'Примечание': spis_tmp[i][10],
#        }
#        spis_dob.append(slovar)
#    AL.dobav_stroki_bd(bd_putname, 'Zhurnal', spis_dob)
#
