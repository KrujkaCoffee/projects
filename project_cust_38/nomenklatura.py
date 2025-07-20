# coding=cp1251
import pprint

import pythoncom
import win32com.client
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
# import Cust_Qt as CQT
import project_cust_38.Erp_connector_plan as ERP
import project_cust_38.Cust_mes as CMS



#if __name__ == '__main__':
#    exit()

DICT_POLE = {
    'Листовой металл (10,01)': {
        'П1': 'Толщина',
        'П2': 'Длина',
        'П3': 'Ширина',
        'П4': 'Плотность',
        'П5': 'Сортамент',
        'П6': 'Код_для_cam',
    },
    'Паронит ГОСТ 481-80': {
        'П1': 'Толщина',
        'П2': 'Длина',
        'П3': 'Ширина',
        'П4': 'Плотность',
        'П5': 'Сортамент',
    },
    'Прутки (10,01)': {
        'П1': 'Диаметр',
        'П2': 'Длина',
        'П3': 'Плотность',
        'П4': 'Сортамент',
    },
    'Круги (10,01)': {
        'П1': 'Диаметр',
        'П2': 'Длина',
        'П3': 'Плотность',
        'П4': 'Сортамент',
    },
    'Труба ГОСТ 9941-81 (нерж)': {
        'П1': 'Толщина',
        'П2': 'Нар.диаметр',
        'П3': 'Вн.диаметр',
        'П4': 'Плотность',
        'П5': 'Сортамент',
        'П6': 'Длина трубы',
    },
    'Трубы': {
        'П1': 'Толщина',
        'П2': 'Нар.диаметр',
        'П3': 'Вн.диаметр',
        'П4': 'Плотность',
        'П5': 'Сортамент',
        'П6': 'Длина трубы',
    },
    'Труба квадратная (10,01)': {
        'П1': 'Толщина',
        'П2': 'Высота',
        'П3': 'Ширина',
        'П4': 'Длина трубы',
        'П5': 'Плотность',
        'П6': 'Сортамент',
    },
    'Трубы по ГОСТ (10,01)': {
        'П1': 'Толщина',
        'П2': 'Нар.диаметр',
        'П3': 'Вн.диаметр',
        'П4': 'Плотность',
        'П5': 'Сортамент',
        'П6': 'Длина трубы',
    },
    'Трубы по ТУ (10,01)': {
        'П1': 'Толщина',
        'П2': 'Нар.диаметр',
        'П3': 'Вн.диаметр',
        'П4': 'Плотность',
        'П5': 'Сортамент',
        'П6': 'Длина трубы',
    },
    'Двутавр (10,01)': {
        'П1': 'b-ширина полки',
        'П2': 's-толщина стенки',
        'П3': 't-толщина полки',
        'П4': 'h-высота балки',
        'П5': 'Длина двутавра',
        'П6': 'Плотность',
        'П7': 'Сортамент',
    },
    'Уголок (10,01)': {
        'П1': 'Толщина',
        'П2': 'a-ширина',
        'П3': 'b-ширина',
        'П4': 'Длина уголка',
        'П5': 'Плотность',
        'П6': 'Сортамент',
    },
    'Швеллер (10,01)': {
        'П1': 's-площадь поперечного сечения',
        'П2': 'Длина швеллера',
        'П3': 'Плотность',
        'П4': 'Сортамент',
    },
    'Квадрат (10,01)':{
        'П1':'s-площадь поперечного сечения',
        'П2':'Длина квадрата',
        'П3':'Плотность',
        'П4':'Сортамент',
    },
    'Шестигранник (10,01)':{
        'П1':'d–диаметр вписанной окружности',
        'П2':'Длина шестигранника',
        'П3':'Плотность',
        'П4':'Сортамент',
    },
    'Набивки': {
        'П1': 'Коэффициент',
        'П2': 'Сортамент',
    }
}

@CQT.onerror
def obn_mat_erp(self, *args):
    if CQT.msgboxgYN(
            'Произойдет загрузка материалов из ЕРП и синхронизация баз, это займет около 5 минут. Продолжаем?'):
        rez = general(self)
        if rez == True:
            CQT.msgbox('Базы успешно обновлены')
        else:
            CQT.msgbox(rez)

@CQT.onerror
def zagruz_mat_iz_nomenklatyri(self, *args):
    tbl = self.ui.tableW_oper_mat
    if tbl.currentRow() == -1:
        CQT.msgbox('Не выбрана строка материала')
        return
    nk_kod = CQT.num_col_by_name_c(tbl, 'Код')
    nk_mat = CQT.num_col_by_name_c(tbl, 'Материал')
    nk_edizm = CQT.num_col_by_name_c(tbl, 'Ед.Изм')
    nk_norm = CQT.num_col_by_name_c(tbl, 'Норма')
    if nk_kod == None:
        CQT.msgbox(f'Ошибка инициализации таблицы')
        return
    custom_request_c = f"""SELECT Код_ЕРП FROM dse WHERE Номенклатурный_номер == '{self.dse_nn}' AND Наименование == '{self.dse_naim}' """
    rez = CSQ.custom_request_c(self.db_dse, custom_request_c)
    if rez[1][0] == '':
        CQT.msgbox('Код не определен в БД')
        return
    else:
        kod = rez[1][0].strip()
        if F.existence_file_c(self.db_mater):
            try:
                query = f"""SELECT Код, Наименование, ЕдиницаИзмерения 
                        FROM nomen WHERE Код == '{kod}'"""
                spisok = CSQ.custom_request_c(self.db_mater, query, rez_dict=True, one=True)
                if spisok == False:
                    CQT.msgbox(f'Не удалось загрузить данные из БДмат, попробуй позже')
                    return
            except:
                CQT.msgbox(f'Не найден {kod} в bd_mater')
                return
            if spisok == False:
                CQT.msgbox(f'Не загружены данные попробуй еще')
                return
            tbl.item(tbl.currentRow(), nk_kod).setText(spisok['Код'])
            tbl.item(tbl.currentRow(), nk_mat).setText(spisok['Наименование'])
            tbl.item(tbl.currentRow(), nk_edizm).setText(spisok['ЕдиницаИзмерения'])
            tbl.item(tbl.currentRow(), nk_norm).setText('*')
        else:
            CQT.msgbox(f'Не найдена база данных {self.db_mater}')


def check_db(self,spis_izm):
    if F.existence_file_c(self.db_mater) == False:
        frase_tmp = """CREATE TABLE IF NOT EXISTS nomen(
               Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
               Вид TEXT,
               Код TEXT,
               Артикул TEXT,
               Наименование TEXT,
               ЕдиницаИзмерения TEXT,
               На_удаление INTEGER,
               Дата_изменения TEXT,
               Примечание TEXT,
               П1 TEXT,
               П2 TEXT,
               П3 TEXT,
               П4 TEXT,
               П5 TEXT,
               П6 TEXT,
               П7 TEXT);
            """
        CSQ.create_db_sql_c(self.db_mater, frase_tmp)
        spis_izm.append(['БД', 'Создана вновь'])
        print('')


def query_run_unify(V83, querytxt):
    query = V83.NewObject("Query", querytxt)
    return query.Execute().Choose()


def connect():
    print('Try connect to ERP')
    print(F.user_name())
    put_f = F.scfg('cash') + F.sep() + 'users_erp.txt'
    if F.existence_file_c(put_f) == False:
        return 'Не найен файл с ключами пользователей ерп'
    print("Файл найден")
    spis_users = F.open_file_c(put_f,True,separ='|')
    login = ''
    password = ''
    for i in range(len(spis_users)):
        if spis_users[i][0] == F.user_name():
            print("Пользователь найден")
            login = spis_users[i][1]
            password = spis_users[i][2]
            break
    if login == '' or password == '':
        return 'Не найден логин/пароль'
    #V83_CONN_STRING = 'Srvr="novgorod";Ref="ERP";Usr="Беляков Антон Геннадьевич";Pwd="25012022";'
    V83_CONN_STRING = f'Srvr="novgorod";Ref="ERP";Usr="{login}";Pwd="{password}";'
    print(f'Ввод {V83_CONN_STRING}')
    pythoncom.CoInitialize()
    V83 = win32com.client.Dispatch("V83.COMConnector").Connect(V83_CONN_STRING)
    print('         .... OK')
    print('')
    return V83


def query_mat(mat, V83):
    # get = lambda obj,attr: getattr(obj, str(attr.encode('cp1251', 'ignore')))
    # catalog = getattr(V83.Catalogs, "Документы.ЗаданиеНаРезку")
    spis = [["rez.Код", "rez.Артикул", "rez.Наименование", "rez.ЕдиницаИзмерения", "rez.ПометкаУдаления"]]
    query_mat = f'''ВЫБРАТЬ
        Номенклатура.ПометкаУдаления КАК ПометкаУдаления,
        Номенклатура.Наименование КАК Наименование,
        Номенклатура.Артикул КАК Артикул,
        Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмерения,
        Номенклатура.Код КАК Код
    ИЗ
        Справочник.Номенклатура КАК Номенклатура
    ГДЕ
        Номенклатура.ВидНоменклатуры.Наименование = "{mat}"'''

    rez = query_run_unify(V83, query_mat)
    while rez.next():
        print(rez.Код, rez.Артикул, rez.Наименование, rez.ЕдиницаИзмерения, rez.ПометкаУдаления)
        spis.append([rez.Код, rez.Артикул, rez.Наименование, rez.ЕдиницаИзмерения, rez.ПометкаУдаления])
    return spis

def synchron_zapis(rez,vid,spis_izm,kod,table,i,conn,nk_art,nk_naim,nk_edizm):
    vid_old = rez[-1][F.num_col_by_name_in_hat_c(rez, 'Вид')]
    if vid_old != vid:
        spis_izm.append([kod, f"{kod}, Было: {vid_old}, Стало: {vid}"])
        custom_request_c = f'''
                                                    UPDATE nomen SET Вид == '{vid}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.custom_request_c('', custom_request_c=custom_request_c, conn=conn)

    art_old = rez[-1][F.num_col_by_name_in_hat_c(rez, 'Артикул')]
    if art_old != table[i][nk_art]:
        spis_izm.append([kod, f"{kod}, Было: {art_old}, Стало: {table[i][nk_art]}"])
        custom_request_c = f'''
                                                    UPDATE nomen SET Артикул == '{table[i][nk_art]}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.custom_request_c('', custom_request_c=custom_request_c, conn=conn)

    naim_old = rez[-1][F.num_col_by_name_in_hat_c(rez, 'Наименование')]
    if naim_old != table[i][nk_naim]:
        spis_izm.append([kod, f"{kod}, Было: {naim_old}, Стало: {table[i][nk_naim]}"])
        custom_request_c = f'''
                                                    UPDATE nomen SET Наименование == '{table[i][nk_naim]}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.custom_request_c('', custom_request_c=custom_request_c, conn=conn)

    edizm_old = rez[-1][F.num_col_by_name_in_hat_c(rez, 'ЕдиницаИзмерения')]
    if edizm_old != table[i][nk_edizm]:
        spis_izm.append([kod, f"{kod}, Было: {edizm_old}, Стало: {table[i][nk_edizm]}"])
        custom_request_c = f'''
                                                    UPDATE nomen SET Наименование == '{table[i][nk_edizm]}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.custom_request_c('', custom_request_c=custom_request_c, conn=conn)

def synchron_param(kod, vid, conn, cur, spis_izm, rez=''):
    put = F.sep().join([F.scfg('cash'), 'bd_mater', f'{vid}.txt'])
    if F.existence_file_c(put):
        spis_tex_param = F.open_file_c(put, separ='|', utf8=True)
        nk_kod = F.num_col_by_name_in_hat_c(spis_tex_param, 'Код')
        stroka = ''
        for i in range(len(spis_tex_param)):
            if spis_tex_param[i][nk_kod] == kod:
                stroka = i
                break
        if stroka == '':
            return
        if vid not in DICT_POLE:
            print(f'Не найден {vid} в словаре')
            spis_izm.append(["ОШИБКА", f'Не найден {vid} в словаре'])
            return
        for key in DICT_POLE[vid].keys():
            nk = F.num_col_by_name_in_hat_c(spis_tex_param, DICT_POLE[vid][key])
            znach = spis_tex_param[stroka][nk]
            if rez != '':
                znach_old = rez[-1][F.num_col_by_name_in_hat_c(rez, key)]
            if rez == '' or znach != znach_old:
                custom_request_c = f'''
                            UPDATE nomen SET {key} == '{znach}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                            '''
                CSQ.custom_request_c('', custom_request_c=custom_request_c, conn=conn)
                spis_izm.append([kod, f"{key}, Было: {znach_old}, Стало: {znach}"])

def general(self):
    spis_izm = []
    if check_db(self,spis_izm) == False:
        return 'Ошибка'
    try:
        conn = connect()
        if type(conn) is type('123'):
            return conn
    except:
        return 'Unable connect, EXIT'

    conn_db, cur_db = CSQ.connect_bd(self.db_mater)
    SPIS_VIDOV = CSQ.custom_request_c(self.db_mater, f"""SELECT DISTINCT Вид FROM nomen""", conn=conn_db,hat_c=False)
    for vid in SPIS_VIDOV:
        vid = vid[0]
        table = query_mat(vid, conn)
        nk_kod = F.num_col_by_name_in_hat_c(table, "rez.Код")
        nk_art = F.num_col_by_name_in_hat_c(table, "rez.Артикул")
        nk_naim = F.num_col_by_name_in_hat_c(table, "rez.Наименование")
        nk_edizm = F.num_col_by_name_in_hat_c(table, "rez.ЕдиницаИзмерения")
        nk_udal = F.num_col_by_name_in_hat_c(table, "rez.ПометкаУдаления")
        for i in range(1, len(table)):
            kod = table[i][nk_kod]
            query = f"""
            SELECT * FROM nomen WHERE Код == "{kod}"
            """
            rez = CSQ.custom_request_c('', query, conn_db)
            if len(rez) > 1:
                print(f'Проверка {kod}')
                synchron_zapis(rez,vid,spis_izm,kod,table,i,conn,nk_art,nk_naim,nk_edizm)
            else:
                strok_input = [vid,
                               table[i][nk_kod],
                               table[i][nk_art],
                               table[i][nk_naim],
                               table[i][nk_edizm],
                               table[i][nk_udal],
                               F.now(),
                               '',
                               '',
                               '',
                               '',
                               '',
                               '',
                               '',
                               '']
                #CSQ.add_line_into_db_sql_c(self.db_mater, 'nomen', [strok_input], conn=conn_db, cur=cur_db)
                CSQ.custom_request_c(self.db_mater,f"""INSERT INTO nomen (Вид
,Код
,Артикул
,Наименование
,ЕдиницаИзмерения
,На_удаление
,Дата_изменения
,Примечание
,П1
,П2
,П3
,П4
,П5
,П6
,П7) VALUES ({','.join('?'*len(strok_input))})""",conn=conn_db,cur=cur_db,list_of_lists_c=[strok_input])
                spis_izm.append([table[i][nk_kod], 'Добавлен'])
    if spis_izm != []:
        put_f = F.path_to_execut_file_c() + F.now('%d.%m.%Y') + '_Изменения ЕРП.txt'
        F.write_file_c(put_f, spis_izm, separ='|')
        F.run_file_c(put_f)
    return True

#general()




def sunc_schemas_from_erp(db_mater, schemas_rez):
    CSQ.custom_request_c(db_mater,f"""DELETE FROM СхемыОбеспечения;""")
    CSQ.custom_request_c(db_mater,f"""INSERT INTO СхемыОбеспечения
                              (Key, Description, Склад, ГарантированныйСрокОбеспечения)
                              VALUES (?, ?, ?, ?); """,list_of_lists_c=schemas_rez)

def sunc_nomen_from_erp(db_mater, file_erp,dict_nomen_mes, path_dir,dict_vids_nomen):
    list_exclude_fields = ['СхемаОбеспечения',
                           'Закупочная_цена',
                           ]


    set_nomen_wh_params = set()
    keys_dict = {'ЕдиницаИзм': 'ЕдиницаИзмерения'}
    file_erp = F.deploy_dict_c(file_erp, 'Код')

    dict_change = {'add': [], 'change': {}, 'del': []}
    log_change = []
    except_fields = ['ПНомер', 'Код']
    for key_erp in list(file_erp.keys()):
        line_erp = file_erp[key_erp]
        if key_erp in dict_nomen_mes:
            if dict_nomen_mes[key_erp]['На_удаление'] == 1:  # В ерп есть в мес удаление вернуть 0
                fiel_del = 'На_удаление'
                if fiel_del not in dict_change['change']:
                    dict_change['change'][fiel_del] = []
                dict_change['change']['На_удаление'].append({'kod': key_erp, 'key': fiel_del, 'val': 0})
                log_change.append(f'КОД: {key_erp}, На_удаление :, было:1 ; стало: 0')
            for key_field in line_erp.keys():
                if key_field in except_fields:
                    continue
                key_field_wrapped = key_field
                if key_field in keys_dict:
                    key_field_wrapped = keys_dict[key_field_wrapped]
                if key_field_wrapped in dict_nomen_mes[key_erp]:
                    if dict_nomen_mes[key_erp][key_field_wrapped] != line_erp[key_field]:
                        if key_field_wrapped not in dict_change['change']:
                            dict_change['change'][key_field_wrapped] = []
                        dict_change['change'][key_field_wrapped].append({'kod': key_erp, 'key': key_field_wrapped, 'val': line_erp[key_field]})
                        if key_field_wrapped not in list_exclude_fields:
                            log_change.append(
                            f'КОД: {key_erp}, {key_field_wrapped} :, было:{dict_nomen_mes[key_erp][key_field_wrapped]} ; стало: {line_erp[key_field]}')
                else:
                    if key_field_wrapped not in except_fields:
                        print(f"{key_field_wrapped} не найден в {dict_nomen_mes[key_erp]}")

        else:
            if line_erp['Вид'] not in dict_vids_nomen:
                log_change.append(f"КОД: {key_erp}, ОШИБКА в строке{line_erp}, ВИД НОМЕНКЛАТУРЫ {line_erp['Вид']} отсутсвует в БД МЕС. Не занесено ")
            else:
                dict_change['add'].append([key_erp, line_erp])
                log_change.append(f'КОД: {key_erp}, добавлен {line_erp}')
                if dict_vids_nomen[line_erp['Вид']]['ЕстьПараметры'] == 1:
                    set_nomen_wh_params.add(line_erp['Артикул'])

    for key_field_wrapped in dict_nomen_mes.keys():
        if dict_nomen_mes[key_field_wrapped]['На_удаление'] == 0:
            if key_field_wrapped not in file_erp:
                dict_change['del'].append(key_field_wrapped)
                log_change.append(f'КОД: {key_field_wrapped}, на удаление было 0 стало 1')

    strok_input = []
    for item in dict_change['add']:
        key_field_wrapped = item[0]
        line_erp = item[1]
        input_row = [line_erp['Вид'],
                     key_field_wrapped,
                     line_erp['Артикул'],
                     line_erp['Наименование'],
                     line_erp['ЕдиницаИзм'],
                     0,
                     F.now(),
                     '',
                     '',
                     '',
                     '',
                     '',
                     '',
                     '',
                     '',
                     line_erp['СхемаОбеспечения'],
                     line_erp['Ref_Key']]
        strok_input.append(input_row)
    if strok_input != []:
        CSQ.custom_request_c(db_mater, f"""INSERT INTO nomen (Вид
                ,Код
                ,Артикул
                ,Наименование
                ,ЕдиницаИзмерения
                ,На_удаление
                ,Дата_изменения
                ,Примечание
                ,П1
                ,П2
                ,П3
                ,П4
                ,П5
                ,П6
                ,П7
                ,СхемаОбеспечения
                ,Ref_Key) VALUES ({','.join('?' * len(strok_input[0]))})""", list_of_lists_c=strok_input)

    for field in dict_change['change'].keys():
        strok_input = []
        counter = 0
        limit_counter = 20
        for item in dict_change['change'][field]:
            input_row = [item['val'], F.now(), item['kod']]
            strok_input.append(input_row)
            counter += 1
            if counter >= limit_counter:
                CSQ.custom_request_c(db_mater, f"""UPDATE nomen SET ({field}, Дата_изменения) =
                     (?, ?) WHERE Код = ?;""", list_of_lists_c=strok_input)
                strok_input = []
                counter = 0
                #F.sleep(1)
        CSQ.custom_request_c(db_mater, f"""UPDATE nomen SET ({field}, Дата_изменения) =
                                 (?, ?) WHERE Код = ?;""", list_of_lists_c=strok_input)

    len_del = len(dict_change['del'])
    i = 0
    strok_input = []
    counter = 0
    limit_counter = 20

    for item in dict_change['del']:
        print(f'Удал. {i} из {len_del}')
        input_row = [1, F.now(), item]
        strok_input.append(input_row)
        i += 1
        counter += 1
        if counter >= limit_counter:
            CSQ.custom_request_c(db_mater, f"""UPDATE nomen SET (На_удаление, Дата_изменения) =
                                     (?, ?) WHERE Код = ?;""", list_of_lists_c=strok_input)
            strok_input = []
            counter = 0
            #F.sleep(1)
    if strok_input != []:
        CSQ.custom_request_c(db_mater, f"""UPDATE nomen SET (На_удаление, Дата_изменения) =
                         (?, ?) WHERE Код = ?;""", list_of_lists_c=strok_input)

    for item in set_nomen_wh_params:
        log_change.append(f'Необходимо занести ПАРАМЕТРЫ на {item}')

    if log_change != []:
        put_f = path_dir + F.sep() + F.now('%d.%m.%Y') + '_Изменения ЕРП.txt'
        F.write_file_c(put_f, log_change, separ='|')
        #F.run_file_c(put_f)
        return log_change
    return False




@CQT.onerror
def obn_mat_erp_file(db_mater, *args):
    #!!!OLD func
    #def load_from_file(db_mater, file_erp, path_dir): #OLD!!
    #    keys_dict={'ЕдиницаИзм':'ЕдиницаИзмерения'}
    #    file_erp = F.deploy_dict_c(file_erp, 'Код')
    #    list_nomen_db = CSQ.custom_request_c(db_mater,f"""SELECT * FROM nomen""",rez_dict=True)
    #    dict_nomen_mes = F.deploy_dict_c(list_nomen_db,'Код')
    #    dict_change = {'add':[],'change':{},'del':[]}
    #    log_change = []
    #    except_fields = ['ПНомер','Код']
    #    for key_f  in list(file_erp.keys()):
    #        line = file_erp[key_f]
    #        if key_f in dict_nomen_mes:
    #            if dict_nomen_mes[key_f]['На_удаление'] == 1:#В ерп есть в мес удаление вернуть 0
    #                fiel_del= 'На_удаление'
    #                if fiel_del not in dict_change['change']:
    #                    dict_change['change'][fiel_del] = []
    #                dict_change['change']['На_удаление'].append({'kod': key_f, 'key': fiel_del, 'val': 0})
    #                log_change.append(f'КОД: {key_f}, На_удаление :, было:1 ; стало: 0')
    #            for key_pre in line.keys():
    #                if key_pre in except_fields:
    #                    continue
    #                key = key_pre
    #                if key_pre in keys_dict:
    #                    key = keys_dict[key]
    #                if key in dict_nomen_mes[key_f]:
    #                    if dict_nomen_mes[key_f][key] != line[key_pre]:
    #                        if key not in dict_change['change']:
    #                            dict_change['change'][key]=[]
    #                        dict_change['change'][key].append({'kod':key_f,'key':key,'val':line[key_pre]})
    #                        log_change.append(f'КОД: {key_f}, {key} :, было:{dict_nomen_mes[key_f][key]} ; стало: {line[key_pre]}')
    #                else:
    #                    if key not in except_fields:
    #                        print(f"{key} не найден в {dict_nomen_mes[key_f]}")
    #
    #        else:
    #            dict_change['add'].append([key_f, line])
    #            log_change.append(f'КОД: {key_f}, добавлен {line}')
    #
    #
    #    for key in dict_nomen_mes.keys():
    #        if dict_nomen_mes[key]['На_удаление'] == 0:
    #            if key not in file_erp:
    #                dict_change['del'].append(key)
    #                log_change.append(f'КОД: {key}, на удаление было 0 стало 1')
    #
    #    strok_input = []
    #    for item in dict_change['add']:
    #        key = item[0]
    #        line= item[1]
    #        input_row = [line['Вид'],
    #                       key,
    #                       line['Артикул'],
    #                       line['Наименование'],
    #                       line['ЕдиницаИзм'],
    #                       0,
    #                       F.now(),
    #                       '',
    #                       '',
    #                       '',
    #                       '',
    #                       '',
    #                       '',
    #                       '',
    #                       '']
    #        strok_input.append(input_row)
    #    if strok_input != []:
    #        CSQ.custom_request_c(db_mater, f"""INSERT INTO nomen (Вид
    #                ,Код
    #                ,Артикул
    #                ,Наименование
    #                ,ЕдиницаИзмерения
    #                ,На_удаление
    #                ,Дата_изменения
    #                ,Примечание
    #                ,П1
    #                ,П2
    #                ,П3
    #                ,П4
    #                ,П5
    #                ,П6
    #                ,П7) VALUES ({','.join('?' * len(strok_input[0]))})""", list_of_lists_c=strok_input)
    #
    #    for field in dict_change['change'].keys():
    #        strok_input = []
    #        counter = 0
    #        limit_counter = 20
    #        for item in dict_change['change'][field]:
    #            input_row = [item['val'],F.now(),item['kod']]
    #            strok_input.append(input_row)
    #            counter+=1
    #            if counter>= limit_counter:
    #                CSQ.custom_request_c(db_mater,f"""UPDATE nomen SET ({field}, Дата_изменения) =
    #                     (?, ?) WHERE Код = ?;""",list_of_lists_c=strok_input)
    #                strok_input = []
    #                counter = 0
    #                F.sleep(1)
    #        CSQ.custom_request_c(db_mater, f"""UPDATE nomen SET ({field}, Дата_изменения) =
    #                                 (?, ?) WHERE Код = ?;""", list_of_lists_c=strok_input)
    #
    #    len_del = len(dict_change['del'])
    #    i = 0
    #    strok_input = []
    #    counter = 0
    #    limit_counter = 20
    #
    #    for item in dict_change['del']:
    #        print(f'Удал. {i} из {len_del}')
    #        input_row = [1, F.now(), item]
    #        strok_input.append(input_row)
    #        i += 1
    #        counter += 1
    #        if counter >= limit_counter:
    #            CSQ.custom_request_c(db_mater, f"""UPDATE nomen SET (На_удаление, Дата_изменения) =
    #                                     (?, ?) WHERE Код = ?;""", list_of_lists_c=strok_input)
    #            strok_input = []
    #            counter = 0
    #            F.sleep(1)
    #    if strok_input != []:
    #        CSQ.custom_request_c(db_mater, f"""UPDATE nomen SET (На_удаление, Дата_изменения) =
    #                         (?, ?) WHERE Код = ?;""",list_of_lists_c=strok_input)
    #
    #
    #    if log_change != []:
    #        put_f = path_dir + F.now('%d.%m.%Y') + '_Изменения ЕРП.txt'
    #        F.write_file_c(put_f, log_change, separ='|')
    #        F.run_file_c(put_f)
    #    return True ####OLD
    ##==========
    dict_vids_nomen = F.deploy_dict_c(CSQ.custom_request_c(db_mater,'SELECT * FROM ВидыНоменклатуры;',rez_dict=True),'name')
    m = ERP.OrdersComposit()
    for k, vid in dict_vids_nomen.items():
        if vid['Ref_Key'] == None or vid['Ref_Key'] == "":
            res = m.get_response(doc_name="Catalog_ВидыНоменклатуры",
                                 wet_filtr=f"?$filter=Description eq '{k}'&$select=Ref_Key,Description")
            if res:
                Ref_Key = res[0]['Ref_Key']
                CSQ.custom_request_c(db_mater,
                                     f"""UPDATE ВидыНоменклатуры SET (Ref_Key) = ('{Ref_Key}') WHERE name = "{k}"; """)
            else:
                Ref_Key = str(F.shtamp_from_date(F.now())).replace('.','-')
                CSQ.custom_request_c(db_mater,
                                     f"""UPDATE ВидыНоменклатуры SET (Ref_Key,comment) = ('{Ref_Key}','Не найден в 1С') WHERE name = "{k}"; """)
                
        
    list_vids_nomen = list(dict_vids_nomen.keys())

    res, schemas_rez = m.get_nomen_mater(list_vids_nomen)
    
    if res == None or schemas_rez == None:
        print('Err obn_mat_erp_file')
        return
    list_nomen_db = CSQ.custom_request_c(db_mater, f"""SELECT * FROM nomen""", rez_dict=True)
    dict_nomen_mes = F.deploy_dict_c(list_nomen_db, 'Код')

    path_dir = F.dir_workdesc_c()
    sunc_schemas_from_erp(db_mater, schemas_rez)
    rez = sunc_nomen_from_erp(db_mater, res,dict_nomen_mes, path_dir, dict_vids_nomen)

    if rez:
        step = 5
        print(f'{F.now()} Базы материалов успешно обновлены')
        for i in range(0,len(rez),step):
            start = i
            end = i+step
            if end > len(rez):
                end = len(rez)
            CMS.send_info_mk_b24("",pprint.pformat(rez[start:end]),"chat59299")
            F.sleep(0.25)
    else:
        print(f'{F.now()} Изменений материалов нет')
    return
    #====================== OLD FILE
    ###if CQT.msgboxgYN(
    ###        'Произойдет загрузка материалов из ЕРП и синхронизация баз, это займет около 5 минут. Продолжаем?'):
    ###    file_path = CQT.f_dialog_name(self,'Выбрать файл для загрузки',F.cfg['defolt_fold'],'*.json')
    ###    if file_path == '.':
    ###        return
    ###    file_erp = F.load_json_c(file_path,lines=False)
    ###    path_dir = "\n".join(file_path.split('\n')[:-1])
    ###
    ###    rez = load_from_file(self,file_erp,path_dir)
    ###
    ###    if rez == True:
    ###        CQT.msgbox('Базы успешно обновлены')
    ###    else:
    ###        CQT.msgbox(rez)

if __name__ == '__main__':

    db_mater = 'SRV:DB_nomenklatura_erp.db'
    obn_mat_erp_file(db_mater)