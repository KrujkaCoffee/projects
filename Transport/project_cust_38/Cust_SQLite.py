import copy
import os.path
import sqlite3
import re

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_client_socket as CSQS

def add_db(bd,text):
    conn = sqlite3.connect(bd)
    cur = conn.cursor()
    cur.executescript(text)
    conn.commit()
    conn.close()


WAIT_TIME = 2
RE_COUNT_SRV = 4


def get_tables_from_select(conn, sql, body): #18.08.25
    cur = conn.execute(sql)
    tables = set()
    for _, _, _, detail in cur.fetchall():
        m = re.search(r"(?:SCAN|SEARCH)\s+([^\s]+)", detail)
        if m:
            tables.add(m.group(1))
    return sorted(tables)

def check_existance_record_sql_c(bd, table_name, spis_novih_zap, kol_sravnenia_sp, kol_sravnenia_bd):
    spis_bd = list_from_db_sql_c(bd, table_name)
    for item in spis_novih_zap:
        flag_naid_item = False
        for zap in range(len(spis_bd) - 1, -1, -1):
            if item[kol_sravnenia_sp] == spis_bd[zap][kol_sravnenia_bd]:
                flag_naid_item = True
                break
        if flag_naid_item == False:
            return False
    return True


def get_list_of_tables_c(bd, conn="", cur=""):
    if 'SRV:' in bd:
        custom_request_c = 'SELECT name from sqlite_master where type= "table"'
        bd, port = CSQS.db_path(bd)
        n_try = 1 if 'select' in custom_request_c.lower() else RE_COUNT_SRV - 1
        while n_try < RE_COUNT_SRV:
            rez = CSQS.client_sql_query(bd, custom_request_c=custom_request_c,
                                        name_module=F.name_of_executable_file_c(),
                                        client_name=F.user_name(), port=port)
            if rez == None or rez == False:
                F.sleep(WAIT_TIME)
                n_try += 1
            else:
                return [_[0] for _ in rez if _[0] != 'sqlite_sequence']
        return [_[0] for _ in rez if _[0] != 'sqlite_sequence']

    if conn == '':
        conn = sqlite3.connect(bd)
        close = True
    else:
        close = False
    if cur == "":
        cur = conn.cursor()
    cur.execute('SELECT name from sqlite_master where type= "table"')
    return [_[0] for _ in cur.fetchall() if _[0] != 'sqlite_sequence']


def list_from_db_sql_c(bd, table_name, bez_pervoi=False, hat_c=False, conn="", cur="", close=True):
    if cur == "":
        conn = sqlite3.connect(bd, timeout=4)
        cur = conn.cursor()
    else:
        close = False
    cur.execute(f"SELECT * FROM {table_name};")
    spisok = cur.fetchall()
    if hat_c == True:
        spisok.insert(0, list_of_columns_c(bd, table_name))
    if bez_pervoi == True:
        sp = [list(x)[1:] for x in spisok]
    else:
        sp = [list(x) for x in spisok]
    if close == True:
        conn.close()
    return sp


def create_db_sql_c(bd, frase, foreign_keys=False, conn="", cur=""):
    # "VACUUM;" - пустая база
    frase_tmp = """CREATE TABLE IF NOT EXISTS users(
       Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
       Дата TEXT DEFAULT "",
       Штамп TEXT DEFAULT "",
       Номер_наряда INTEGER DEFAULT (0),
       ФИО TEXT,
       Номер_проекта TEXT,
       Этап TEXT,
       Последний TEXT,
       Статус TEXT,
       Твремя TEXT,
       Фвремя TEXT,
       Примечание TEXT,
       FOREIGN KEY (Пномер) REFERENCES Главнаятаблица(ПолеГлавной таблицы));
    """
    if 'SRV:' in bd:
        
        
        bd, port = CSQS.db_path(bd)
        if foreign_keys:
            frase1 = 'PRAGMA foreign_keys=on;'
            rez = CSQS.client_sql_query(bd, custom_request_c=frase1,
                                        name_module=F.name_of_executable_file_c(),
                                        client_name=F.user_name(), port=port)
        rez = CSQS.client_sql_query(bd, custom_request_c=frase,
                                    name_module=F.name_of_executable_file_c(),
                                    client_name=F.user_name(), port=port)
       
        if rez == None or rez == False:
            print(f'ОШибка create_db_sql_c')
            return
        return
    
    if conn == '':
        conn = sqlite3.connect(bd)
        close = True
    else:
        close = False
    if cur == "":
        cur = conn.cursor()

    # https://pythonru.com/osnovy/sqlite-v-python
    if foreign_keys:
        frase1 = 'PRAGMA foreign_keys=on;'
        cur.execute(frase1)
    cur.executescript(frase)
    conn.commit()
    if close == True:
        conn.close()


def create_table_db_c(bd, table_name, spis_name_col_ogr):
    for i in range(len(spis_name_col_ogr)):
        if len(spis_name_col_ogr[i]) != 2:
            print('Не верный список')
            return False
    frase = []
    for i in range(len(spis_name_col_ogr)):
        frase.append(f'{spis_name_col_ogr[i][0]} {spis_name_col_ogr[i][1]}')
    ogr = ', '.join(frase)
    frase_tmp = f"CREATE TABLE IF NOT EXISTS {table_name}({ogr});"
    conn = sqlite3.connect(bd)
    cur = conn.cursor()  # https://pythonru.com/osnovy/sqlite-v-python
    cur.execute(frase_tmp)
    conn.commit()
    conn.close()
    if existence_table_c(bd, table_name) == True:
        return True
    return False


def existence_table_c(bd, ima):
    if 'SRV:' in bd:
        bd, port = CSQS.db_path(bd)
        custom_request_c = f"SELECT count(*) as count FROM sqlite_master WHERE type='table' AND name='{ima}'"
        rez = CSQS.client_sql_query(bd, custom_request_c=custom_request_c, hat_c=True, list_of_lists_c=[[]],
                                        rez_dict=True, one=True, name_module=F.name_of_executable_file_c(),
                                        client_name=F.user_name(), port=port, one_column=False)
        return rez['count']
    else:
        conn = sqlite3.connect(bd)
        cur = conn.cursor()
        frase = f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{ima}'"
        cur.execute(frase)
        result = cur.fetchone()
        conn.close()
        
        if result[0] == 1:
            return True
        return False


def add_line_into_db_sql_c(bd, table, stroki_strok, s_pervoi=False, conn="", cur="", proverka=False):
    '''Если не хочешь подавать на вход порядковый номер(AUTOINCREMENT),
    и список на одно поле короче то надо ставить s_pervoi = False '''


    if stroki_strok == []:
        return
    if type(stroki_strok[0]) == type([]) or type(stroki_strok[0]) == type(()):
        pass
    else:
        print('Не верный формат спсика списков')
        return False
    if s_pervoi == False:
        spis_kol = list_of_columns_c(bd, table)[1:]
    else:
        spis_kol = list_of_columns_c(bd, table)
    str_kol = ", ".join(spis_kol)
    mask = "?, " * len(spis_kol)
    mask = mask[:-2]

    if 'SRV:' in bd:
        bd, port = CSQS.db_path(bd)
        custom_request_c = f"INSERT INTO {table}({str_kol}) VALUES ({mask})"
        rez = CSQS.client_sql_query(bd, custom_request_c=custom_request_c, hat_c=True, list_of_lists_c=stroki_strok,
                                        rez_dict=False, one=True, name_module=F.name_of_executable_file_c(),
                                        client_name=F.user_name(), port=port, one_column=False)
        return True
    else:
        if conn == '':
            conn = sqlite3.connect(bd)
            close = True
        else:
            close = False
        if cur == "":
            cur = conn.cursor()

        try:
            cur.executemany(f"INSERT INTO {table}({str_kol}) VALUES ({mask})", stroki_strok)
            conn.commit()


        except:
            if close == True:
                cur.close()
                conn.close()
            return False

        if close == True:
            cur.close()
            conn.close()
    rez = True
    if proverka:
        if s_pervoi == False:
            rez = check_existance_record_sql_c(bd, table, stroki_strok, 1, 2)
        else:
            rez = check_existance_record_sql_c(bd, table, stroki_strok, 1, 1)
    return rez


def list_of_columns_c(bd, table, dict=False):
    if 'SRV:' in bd:
        bd, port = CSQS.db_path(bd)
        custom_request_c = f'select * from {table} Limit 1'
        rez = CSQS.client_sql_query(bd, custom_request_c=custom_request_c, hat_c=True, list_of_lists_c=[[]],
                                    rez_dict=False, one=True, name_module=F.name_of_executable_file_c(),
                                    client_name=F.user_name(), port=port, one_column=False)
        rez = rez[0]
        if dict == True:
            dict_tmp = {}
            for i in range(len(rez)):
                dict_tmp[rez[i]] = i
            return dict_tmp
        return rez

    conn = sqlite3.connect(bd)
    cursor = conn.execute(f'select * from {table} Limit 1')
    rez = [x[0] for x in cursor.description]
    if dict == True:
        dict_tmp = {}
        for i in range(len(rez)):
            dict_tmp[rez[i]] = i
        return dict_tmp
    return rez

def dict_zero_val_row(db,tbl_name):
    objs = {
        int: 0,
        float: 0.0,
        str:'',
        bytes: b'',
    }
    row = dict_types_tbl(db,tbl_name)
    for k, v in row.items():
        if v in objs:
            row[k] = objs[v]
        else:
            row[k] = None
    return row

def dict_types_tbl(db,tbl_name)->dict[str,type]:
    list_dicts = custom_request_c(db, custom_request_c=f"""SELECT name, type FROM pragma_table_info('{tbl_name}')""",
                                  rez_dict=True)
    objs = {
        'INTEGER':int,
        'INT':int,
        'REAL':float,
        'TEXT':str,
        'BLOB':bytes,
            }
    return {_['name']:objs[_['type']] for _ in list_dicts}

def list_types_table(bd, table):
    list_dicts = custom_request_c(bd, custom_request_c=f"""SELECT name, type FROM pragma_table_info('{table}')""",
                                  rez_dict=True)
    name_key_column = 'name'
    rez = dict()
    for dic in list_dicts:
        if type(dic) == type(dict()):
            if name_key_column in dic:
                if len(dic.keys()) == 2:
                    val = ''
                    for key in dic.keys():
                        if key != name_key_column:
                            val = dic[key]
                            break
                else:
                    val = dict()
                    for key in dic.keys():
                        if key != name_key_column:
                            val[key] = dic[key]
                rez[dic[name_key_column]] = val
    return rez


def convert_dict_to_sqlite_types(data: dict, type_map: dict) -> dict:
    """
    Приводит значения словаря `data` к типам из словаря `type_map`,
    где type_map[field] = тип (например int, float, str, bytes).
    """
    result = {}
    for field, value in data.items():
        target_type = type_map.get(field)
        if target_type is None:
            # поля нет в таблице — оставляем как есть
            result[field] = value
            continue

        if value is None:
            result[field] = None
            continue

        try:
            # если уже нужного типа — не трогаем
            if isinstance(value, target_type):
                result[field] = value
            else:
                # особые случаи: конвертация строк, чисел и булевых
                if target_type is int:
                    result[field] = int(float(value))  # если число в виде строки "3.0"
                elif target_type is float:
                    result[field] = float(value)
                elif target_type is str:
                    result[field] = str(value)
                elif target_type is bytes:
                    if isinstance(value, str):
                        result[field] = value.encode("utf-8")
                    else:
                        result[field] = bytes(value)
                else:
                    result[field] = value  # fallback
        except Exception:
            # если конвертация не удалась, оставляем оригинал
            result[field] = value
            raise TypeError(f'convert_dict_to_sqlite_types error to convert "{field}" ')
    return result


def fix_types_table(table, types_dict: dict):
    """list_types_table = types_dict"""
    for i in range(len(table[0])):
        if types_dict[table[0][i]] == 'INTEGER':
            for j in range(1, len(table)):
                if F.is_numeric(table[j][i]):
                    table[j][i] = int(table[j][i])
                else:
                    table[j][i] = 0
        if types_dict[table[0][i]] == 'REAL':
            for j in range(1, len(table)):
                if F.is_numeric(table[j][i]):
                    table[j][i] = F.valm(table[j][i])
                else:
                    table[j][i] = 0.0
        if types_dict[table[0][i]] == 'TEXT':
            for j in range(1, len(table)):
                table[j][i] = str(table[j][i])
    return table


def for_blob(data):
    return sqlite3.Binary(data)


def apply_alias_list(list_resp, dict_alias):
    if list_resp == []:
        return list_resp
    result = copy.deepcopy(list_resp)
    if isinstance(result[0], dict):
        for i in range(len(result)):
            new_dict = dict()
            for k, v in result[i].items():
                if k in dict_alias:
                    new_dict[dict_alias[k]] = v
                else:
                    print(f'CSQ.apply_alias_list err not found alias for {k}')
                    new_dict[k] = v
            result[i] = new_dict
    elif isinstance(result[0], list):
        for j in range(len(result[0])):
            fl_found = False
            if result[0][j] in dict_alias:
                result[0][j] = dict_alias[result[0][j]]
                fl_found = True
            if not fl_found:
                print(f'CMS.apply_alias_list err not found alias for {result[0][j]}')
    else:
        for i in range(len(result)):
            for j in range(len(result[i])):
                fl_found = False
                if result[i][j] in dict_alias:
                    result[i][j] = dict_alias[result[i][j]]
                    fl_found = True
                if not fl_found:
                    print(f'CMS.apply_alias_list err not found alias for {result[i][j]}')
    return result

def prepare_list_to_tuple(list_nums:list|set|tuple) -> str:
    if not list_nums:
        return ''
    if isinstance(list_nums,(set,tuple)):
        list_nums = list(list_nums)
    if isinstance(list_nums[0], float) or isinstance(list_nums[0], int):
        tmp_list = [str(_) for _ in list_nums]
        return ','.join(tmp_list)
    tmp_list = [f'{_!r}' for _ in list_nums]
    if len(tmp_list) == 1:
        return tmp_list[0]
    return ','.join(tmp_list)

def quote_text_values(values: list, quote: str = "'") -> list:
    """
    Возвращает новый список, где строковые элементы обёрнуты в указанные кавычки.
    Нестроковые элементы остаются без изменений.

    :param values: список значений
    :param quote: символ кавычки, например "'" или '"'
    """
    if not values:
        return ''
    result = []
    for v in values:
        if isinstance(v, str):
            # экранируем внутренние кавычки
            escaped = v.replace(quote, quote * 2)
            result.append(f"{quote}{escaped}{quote}")
        else:
            result.append(v)
    return result

def check_operator_returning(query: str) -> bool: #11.11.25
    pattern = r'\bRETURNING\b'
    return bool(re.search(pattern, query, re.IGNORECASE))

def unpack_single_value(result): #11.11.25
    if result and isinstance(result, list):
        return unpack_single_value(result[0])
    if result and isinstance(result, dict):
        return unpack_single_value(list(result.values()))
    return result

@F.StatisticDecorator #18.08.25
def custom_request_c(bd, custom_request_c, conn='', hat_c=True, list_of_lists_c=[[]], rez_dict=False, one=False, cur='',
                     one_column=False, returning=False, attach_dbs: tuple | str=()):
    '''sqlite_insert_with_param = """INSERT INTO sqlitedb_developers
                              (id, name, email, joining_date, salary)
                              VALUES (?, ?, ?, ?, ?);"""
        UPDATE users
                SET  (field1, field2, field3)
                    = ('value1', 'value2', 'value3')
                            WHERE some_condition ;'''
    if isinstance(list_of_lists_c[0],dict):
        list_of_lists_c = F.list_of_dicts_to_list_of_lists(list_of_lists_c)[1:]
    if 'SRV:' in bd: #18.08.25
        bd, port = CSQS.db_path(bd)
        rez = CSQS.client_sql_query(bd, custom_request_c=custom_request_c, hat_c=hat_c,
                                    list_of_lists_c=list_of_lists_c,
                                    rez_dict=rez_dict, one=one, name_module=F.name_of_executable_file_c(),
                                    client_name=F.user_name(), port=port, one_column=one_column, attach_dbs=attach_dbs)
        return rez

    RE_COUNT = 1
    try:
        if conn == '' or conn == False:
            conn = sqlite3.connect(bd, timeout=4)
            close = True
        else:
            close = False
        if cur == '':
            cur = conn.cursor()

    except:
        print(f'Ошибка соединения с БД {bd}')
        return

    while True: # 19.09.25
        result = False
        returning = False
        type_query = custom_request_c.replace('\n', '').strip().split(' ')[0].upper()
        if 'EXPLAIN' == type_query: #15.08.25
            result = get_tables_from_select(cur, custom_request_c.replace('?', "''"), list_of_lists_c)
        if 'PRAGMA'  == type_query:
            cur.execute(custom_request_c)
            result = True
        if 'CREATE'  == type_query:
            cur.executescript(custom_request_c)
            conn.commit()
            result = True
        if 'INSERT' == type_query:
            if check_operator_returning(custom_request_c):
                cur.execute(custom_request_c, list_of_lists_c)
                returning = True
            else:
                cur.executemany(custom_request_c, list_of_lists_c)
                conn.commit()
                result = True
        if 'UPDATE' == type_query:
            if check_operator_returning(custom_request_c):
                if list_of_lists_c == [[]]:
                    cur.execute(custom_request_c)
                else:
                    cur.execute(custom_request_c, list_of_lists_c)
                returning = True
            else:
                if list_of_lists_c == [[]]:
                    cur.execute(custom_request_c)
                else:
                    if type(list_of_lists_c[0]) == list:
                        cur.executemany(custom_request_c, list_of_lists_c)
                    else:
                        cur.execute(custom_request_c, list_of_lists_c)
                conn.commit()
                result = True
        if 'DELETE' == type_query:
            if check_operator_returning(custom_request_c):
                if list_of_lists_c == [[]]:
                    cur.execute(custom_request_c)
                else:
                    cur.execute(custom_request_c, list_of_lists_c)
                returning = True
            else:
                if list_of_lists_c == [[]]:
                    cur.execute(custom_request_c)
                else:
                    if type(list_of_lists_c[0]) == list:
                        cur.executemany(custom_request_c, list_of_lists_c)
                    else:
                        cur.execute(custom_request_c, list_of_lists_c)
                conn.commit()
                result = True
        if 'SELECT' == type_query or 'WITH' == type_query: # 25.01.2025s
            if list_of_lists_c == [[]]:
                cur.execute(custom_request_c)
            else:
                if isinstance(list_of_lists_c, (list, tuple)):
                    if type(list_of_lists_c[0]) == list or type(list_of_lists_c[0]) == tuple:
                        cur.execute(custom_request_c, (list_of_lists_c[0][0],))
                    else:
                        cur.execute(custom_request_c,(list_of_lists_c[0],))
                else:
                    cur.execute(custom_request_c, (list_of_lists_c,))
            returning = True

        if returning:
            if one == True:
                result = cur.fetchone()
            else:
                result = cur.fetchall()
            if rez_dict:
                tmp = []
                cols = [x[0] for x in cur.description]
                if one == True:
                    if result == None:
                        result = []
                    else:
                        result = [result]
                for item in result:
                    tmp_dict = dict()
                    for i in range(len(cols)):
                        if cols[i] in tmp_dict:
                            cols[i] = str(i) + '_' + cols[i]
                        tmp_dict[cols[i]] = item[i]
                    tmp.append(tmp_dict)
                if one == True:
                    result = dict()
                    if len(tmp):
                        result = tmp[0]
                else:
                    result = tmp
            else:
                if one == True:
                    if result == None:
                        result = []
                    else:
                        result = [list(result)]
                else:
                    if result != []:
                        #startTime = F.now('')
                        result = [list(x) for x in result]
                        #F.microseconds_passed(startTime,len(result))
                if hat_c == True:
                    cols = [x[0] for x in cur.description]
                    result.insert(0, cols)
            if one_column:
                result = [_[0] for _ in result]
            if one and one_column:
                result = unpack_single_value(result)
        if close:
            cur.close()
            conn.close()
        return result



def update_bd_sql(bd, table, slovar_set, slovar_where, log='and ', conn="", cur="", close=True):
    if conn == '':
        conn = sqlite3.connect(bd, timeout=4)
    else:
        close = False
    if cur == "":
        cur = conn.cursor()

    stroka_set = list(slovar_set.keys())
    rez = []
    for item in stroka_set:
        rez.append(slovar_set[item])

    stroka_where = list(slovar_where.keys())

    for item in stroka_where:
        rez.append(slovar_where[item])
    tmp_set = ' = ? , '
    tmp_where = ' = ? ' + log

    setstr = tmp_set.join(stroka_set) + ' = ?'
    wherestr = tmp_where.join(stroka_where) + ' = ?'
    cur.execute(f'UPDATE {table} SET {setstr} where {wherestr}', rez)
    conn.commit()
    if close == True:
        conn.close()


def upload_db_into_txt_c(bd, table, putf, bez_pervoi=False):
    all_results = list_from_db_sql_c(bd, table, bez_pervoi)
    spisok = []
    for i in all_results:
        spisok.append(list(i))
    F.write_file_c(putf, spisok, '|')


def delete_all(bd, table):
    conn = sqlite3.connect(bd)
    cur = conn.cursor()
    cur.execute(f'DELETE FROM {table}')
    conn.commit()
    conn.close()



def delete(bd, table, slovar_where='', log='and ', conn="", cur=""):
    close = True
    if conn == '':
        conn = sqlite3.connect(bd)
    else:
        close = False
    if cur == "":
        cur = conn.cursor()
    stroka_where = list(slovar_where.keys())
    rez = []
    for item in stroka_where:
        rez.append(slovar_where[item])
    tmp_where = ' = ? ' + log
    wherestr = tmp_where.join(stroka_where) + ' = ?'
    cur.execute(f'DELETE FROM {table} where {wherestr}', rez)
    conn.commit()
    if find_in_db_c(bd, table, slovar_where, log=log, conn=conn, cur=cur) == []:
        if close:
            conn.close()
        return True
    if close:
        conn.close()
    return False


def last_row_db_c(bd, table, ima_kol_order_by, spis_col_select: list = '*', hat_c: bool = False, conn="", cur=""):
    if spis_col_select != '*':
        col = ', '.join(spis_col_select)
    else:
        col = '*'

    result = \
        custom_request_c(bd, f"SELECT {col} FROM {table} ORDER BY {ima_kol_order_by} DESC LIMIT 1", conn=conn, cur=cur,
                         hat_c=hat_c, one=True)[0]

    return result


def connect_bd(bd, timeout_=6):
    if 'SRV:' in bd:
        return '', ''
    if F.existence_file_c(bd) == False:
        print(f'DB {bd} not found')
        return False, False
    RETRY_COUNT = 5
    while RETRY_COUNT:
        RETRY_COUNT -= 1
        try:
            conn = sqlite3.connect(bd, timeout=timeout_)
            conn.isolation_level = 'IMMEDIATE'
            cur = conn.cursor()
            cur.execute('BEGIN IMMEDIATE')
            cur.execute('SELECT name from sqlite_master where type= "table"')
            conn.rollback()
            cur.close()
            conn.isolation_level = None
            break
        except:
            cur.close()
            conn.close()
            if RETRY_COUNT == 1:
                return False, False
            print(f'connect_bd не удалось, попыток {RETRY_COUNT}')
            F.sleep(timeout_ - 1)
    cur = conn.cursor()
    return conn, cur


def close_bd(conn, cur=''):
    try:
        if cur != '':
            cur.close()
        conn.close()
    except:
        pass


def find_in_db_c(bd, table='', slovar_where='', spis_col='*', log='and', sravn='=', all: bool = True, hat_c: bool = False,
               ne=False, siroe_usl='', dict=False, conn="", cur="", close=True, last: bool = False,
               siroy_custom_request_c=''):
    '''and/or, =/LIKE
    Знак процента (%)
Подчеркивание (_)
Знак процента представляет ноль, один или несколько чисел или символов. Подчеркнутый символ представляет собой одно 
число или символ. Эти символы могут использоваться в комбинациях.
siroe_usl= "Дата <= strftime('%Y-%m-%d %H:%M:00', datetime('"
       + le_dat2.text() + "')) AND Дата >= strftime('%Y-%m-%d %H:%M:00', datetime('"
       + le_dat1.text() + "'))")
       
"Категория_брака == 'Неисправимый' AND Ном_мк_повт_изг == ''"
'''
    if conn == '':
        conn = sqlite3.connect(bd, timeout=4)
    else:
        close = False
    if cur == "":
        cur = conn.cursor()
    col = '*'
    if siroy_custom_request_c == "":
        if siroe_usl == '':
            log = log + ' '
            rez = []
            stroka_where = list(slovar_where.keys())
            if ne == False:
                otr = ''
            else:
                otr = '!'
            for item in stroka_where:
                rez.append(slovar_where[item])
            tmp = ' = ? ' + log
            wherestr = tmp.join(stroka_where) + f' {otr + sravn} ?'

        if spis_col != '*':
            col = ', '.join(spis_col)
        if siroe_usl != '':
            cur.execute(f'SELECT {col} FROM {table} WHERE {siroe_usl}')
        else:
            cur.execute(f'SELECT {col} FROM {table} WHERE {wherestr}', rez)
        if all == True:
            result = cur.fetchall()
            result = list(result)
            if col == '*':
                if hat_c == True:
                    result.insert(0, list_of_columns_c(bd, table, dict))
            else:
                if hat_c == True:
                    if dict == False:
                        result.insert(0, col.split(', '))
                    else:
                        dict_tmp = {}
                        spis_shap = col.split(', ')
                        for i in range(len(spis_shap)):
                            dict_tmp[spis_shap[i]] = i
                        result.insert(0, dict_tmp)
        else:
            if last == True:
                result = cur.fetchall()[-1]
            else:
                result = cur.fetchone()
            if col == '*':
                if hat_c == True:
                    if result == None:
                        result = [list_of_columns_c(bd, table, dict)]
                    else:
                        result = [list_of_columns_c(bd, table, dict), list(result)]
            else:
                if hat_c == True:
                    if dict == False:
                        result = [col.split(', '), list(result)]
                    else:
                        dict_tmp = {}
                        spis_shap = col.split(', ')
                        for i in range(len(spis_shap)):
                            dict_tmp[spis_shap[i]] = i
                        result = [dict_tmp, list(result)]
    else:
        cur.execute(siroy_custom_request_c)
        result = cur.fetchall()
        result = list(result)
        if hat_c == True:
            cols = siroy_custom_request_c.split(' FROM')[0].split('SELECT ')[-1].split(',')

            if cols == ["*"]:
                table = siroy_custom_request_c.split(' WHERE')[0].split('FROM ')[-1]
                cols = list_of_columns_c(bd, table, dict)
            cols_clear = []
            for i in cols:
                if i.split('.')[-1].strip() in cols_clear:
                    cols_clear.append(i.strip())
                else:
                    cols_clear.append(i.split('.')[-1].strip())
            if dict == False:
                result.insert(0, cols_clear)
            else:
                dict_tmp = {}
                spis_shap = cols_clear
                for i in range(len(spis_shap)):
                    dict_tmp[spis_shap[i]] = i
                result.insert(0, dict_tmp)
    if close:
        conn.close()
    return result


def translate_date_in_db_new_c(pyt_bd, imatabl, ima_kol, ident):
    conn = sqlite3.connect(pyt_bd)
    cur = conn.cursor()
    spis_is_bd = CSQ.list_from_db_sql_c(pyt_bd, imatabl, False, True, close=False, cur=cur, conn=conn)
    o_k_dat = num_col_by_name_in_hat_c(spis_is_bd, ima_kol)
    n_k_idetn = num_col_by_name_in_hat_c(spis_is_bd, ident)
    for i in range(1, len(spis_is_bd)):
        if '-' not in spis_is_bd[i][o_k_dat]:
            old = strtodateold(spis_is_bd[i][o_k_dat])
            new = datetostr(old)
            CSQ.update_bd_sql(pyt_bd, imatabl, {ima_kol: new}, {ident: spis_is_bd[i][n_k_idetn]}, cur=cur, conn=conn,
                              close=False)
    conn.close()


def if_db_lock(funcd):
    def wrapper(self, *args, **kwargs):
        try:
            rez = funcd(self, *args, **kwargs)
            if rez == False:
                msgbox(f'Доступ к БД затруднен, попробуй чуть позже')
                quit()
            return rez
        except Exception as ex:
            pass

    return wrapper


def questions_for_mask(list: list) -> str:
    list_q = ['?' for _ in list]
    return ','.join(list_q)


if __name__ == '__main__':
    quit()
    text = """PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

CREATE TABLE пл_рскр (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_рскр REAL DEFAULT "(0)", Фчас_рскр REAL DEFAULT "(0)", ПДата_нач_рскр TEXT DEFAULT "", ПДата_зав_рскр TEXT DEFAULT "", ФДата_нач_рскр TEXT DEFAULT "", ФДата_зав_рскр TEXT DEFAULT "", Примечание_рскр TEXT DEFAULT "", Дата_обесп_рскр TEXT DEFAULT "");
CREATE TABLE пл_оснтк (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_оснтк REAL DEFAULT "(0)", Фчас_оснтк REAL DEFAULT "(0)", ПДата_нач_оснтк TEXT DEFAULT "", ПДата_зав_оснтк TEXT DEFAULT "", ФДата_нач_оснтк TEXT DEFAULT "", ФДата_зав_оснтк TEXT DEFAULT "", Примечание_оснтк TEXT DEFAULT "", Дата_обесп_оснтк TEXT DEFAULT "");
CREATE TABLE пл_швк (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_швк REAL DEFAULT "(0)", Фчас_швк REAL DEFAULT "(0)", ПДата_нач_швк TEXT DEFAULT "", ПДата_зав_швк TEXT DEFAULT "", ФДата_нач_швк TEXT DEFAULT "", ФДата_зав_швк TEXT DEFAULT "", Примечание_швк TEXT DEFAULT "", Дата_обесп_швк TEXT DEFAULT "");
CREATE TABLE пл_сбтк (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_сбтк REAL DEFAULT "(0)", Фчас_сбтк REAL DEFAULT "(0)", ПДата_нач_сбтк TEXT DEFAULT "", ПДата_зав_сбтк TEXT DEFAULT "", ФДата_нач_сбтк TEXT DEFAULT "", ФДата_зав_сбтк TEXT DEFAULT "", Примечание_сбтк TEXT DEFAULT "", Дата_обесп_сбтк TEXT DEFAULT "");
CREATE TABLE пл_сбмл (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_сбмл REAL DEFAULT "(0)", Фчас_сбмл REAL DEFAULT "(0)", ПДата_нач_сбмл TEXT DEFAULT "", ПДата_зав_сбмл TEXT DEFAULT "", ФДата_нач_сбмл TEXT DEFAULT "", ФДата_зав_сбмл TEXT DEFAULT "", Примечание_сбмл TEXT DEFAULT "", Дата_обесп_сбмл TEXT DEFAULT "");
CREATE TABLE пл_нбвк (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_нбвк REAL DEFAULT "(0)", Фчас_нбвк REAL DEFAULT "(0)", ПДата_нач_нбвк TEXT DEFAULT "", ПДата_зав_нбвк TEXT DEFAULT "", ФДата_нач_нбвк TEXT DEFAULT "", ФДата_зав_нбвк TEXT DEFAULT "", Примечание_нбвк TEXT DEFAULT "", Дата_обесп_нбвк TEXT DEFAULT "");
CREATE TABLE пл_свг (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_свг REAL DEFAULT "(0)", Фчас_свг REAL DEFAULT "(0)", ПДата_нач_свг TEXT DEFAULT "", ПДата_зав_свг TEXT DEFAULT "", ФДата_нач_свг TEXT DEFAULT "", ФДата_зав_свг TEXT DEFAULT "", Примечание_свг TEXT DEFAULT "", Дата_обесп_свг TEXT DEFAULT "");
CREATE TABLE пл_сббси (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_сббси REAL DEFAULT "(0)", Фчас_сббси REAL DEFAULT "(0)", ПДата_нач_сббси TEXT DEFAULT "", ПДата_зав_сббси TEXT DEFAULT "", ФДата_нач_сббси TEXT DEFAULT "", ФДата_зав_сббси TEXT DEFAULT "", Примечание_сббси TEXT DEFAULT "", Дата_обесп_сббси TEXT DEFAULT "");
CREATE TABLE пл_упквк (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_упквк REAL DEFAULT "(0)", Фчас_упквк REAL DEFAULT "(0)", ПДата_нач_упквк TEXT DEFAULT "", ПДата_зав_упквк TEXT DEFAULT "", ФДата_нач_упквк TEXT DEFAULT "", ФДата_зав_упквк TEXT DEFAULT "", Примечание_упквк TEXT DEFAULT "", Дата_обесп_упквк TEXT DEFAULT "");
CREATE TABLE пл_кмпл (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_кмпл REAL DEFAULT "(0)", Фчас_кмпл REAL DEFAULT "(0)", ПДата_нач_кмпл TEXT DEFAULT "", ПДата_зав_кмпл TEXT DEFAULT "", ФДата_нач_кмпл TEXT DEFAULT "", ФДата_зав_кмпл TEXT DEFAULT "", Примечание_кмпл TEXT DEFAULT "", Дата_обесп_кмпл TEXT DEFAULT "");
CREATE TABLE пл_откк (НомПл INTEGER UNIQUE REFERENCES "plan" (Пномер) PRIMARY KEY, Нчас_откк REAL DEFAULT "(0)", Фчас_откк REAL DEFAULT "(0)", ПДата_нач_откк TEXT DEFAULT "", ПДата_зав_откк TEXT DEFAULT "", ФДата_нач_откк TEXT DEFAULT "", ФДата_зав_откк TEXT DEFAULT "", Примечание_откк TEXT DEFAULT "", Дата_обесп_откк TEXT DEFAULT "");

ALTER TABLE пл_заг ADD COLUMN Дата_обесп_заг TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_ко ADD COLUMN Дата_обесп_ко TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_компл ADD COLUMN Дата_обесп_компл TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_мех ADD COLUMN Дата_обесп_мех TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_оуп ADD COLUMN Дата_обесп_оуп TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_покр ADD COLUMN Дата_обесп_покр TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_сб ADD COLUMN Дата_обесп_сб TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_топ ADD COLUMN Дата_обесп_топ TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_отк ADD COLUMN Дата_обесп_отк TEXT NOT NULL DEFAULT "";
ALTER TABLE пл_осил ADD COLUMN Дата_обесп_осил TEXT NOT NULL DEFAULT "";

COMMIT;
PRAGMA foreign_keys = on;"""
    #add_db(r'C:/DB_srv/DB_kplan.db',text)
    exit()