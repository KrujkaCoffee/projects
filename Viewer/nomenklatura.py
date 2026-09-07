# coding=cp1251
import pythoncom
import win32com.client
import Cust_SQLite as CSQ
import Cust_Functions as F

# import Cust_Qt as CQT

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
    }
}


def check_db(self,spis_izm):
    if F.nalich_file(self.db_mater) == False:
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
        CSQ.sozd_bd_sql(self.db_mater, frase_tmp)
        spis_izm.append(['БД', 'Создана вновь'])
        print('')


def query_run_unify(V83, querytxt):
    query = V83.NewObject("Query", querytxt)
    return query.Execute().Choose()


def connect():
    print('Try connect to ERP')
    print(F.user_name())
    put_f = F.scfg('cash') + F.sep() + 'users_erp.txt'
    if F.nalich_file(put_f) == False:
        return 'Не найен файл с ключами пользователей ерп'
    print("Файл найден")
    spis_users = F.otkr_f(put_f,True,separ='|')
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
    vid_old = rez[-1][F.nom_kol_po_im_v_shap(rez, 'Вид')]
    if vid_old != vid:
        spis_izm.append([kod, f"{kod}, Было: {vid_old}, Стало: {vid}"])
        zapros = f'''
                                                    UPDATE nomen SET Вид == '{vid}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.zapros('', zapros=zapros, conn=conn)

    art_old = rez[-1][F.nom_kol_po_im_v_shap(rez, 'Артикул')]
    if art_old != table[i][nk_art]:
        spis_izm.append([kod, f"{kod}, Было: {art_old}, Стало: {table[i][nk_art]}"])
        zapros = f'''
                                                    UPDATE nomen SET Артикул == '{table[i][nk_art]}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.zapros('', zapros=zapros, conn=conn)

    naim_old = rez[-1][F.nom_kol_po_im_v_shap(rez, 'Наименование')]
    if naim_old != table[i][nk_naim]:
        spis_izm.append([kod, f"{kod}, Было: {naim_old}, Стало: {table[i][nk_naim]}"])
        zapros = f'''
                                                    UPDATE nomen SET Наименование == '{table[i][nk_naim]}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.zapros('', zapros=zapros, conn=conn)

    edizm_old = rez[-1][F.nom_kol_po_im_v_shap(rez, 'ЕдиницаИзмерения')]
    if edizm_old != table[i][nk_edizm]:
        spis_izm.append([kod, f"{kod}, Было: {edizm_old}, Стало: {table[i][nk_edizm]}"])
        zapros = f'''
                                                    UPDATE nomen SET Наименование == '{table[i][nk_edizm]}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                                                    '''
        CSQ.zapros('', zapros=zapros, conn=conn)

def synchron_param(kod, vid, conn, cur, spis_izm, rez=''):
    put = F.sep().join([F.scfg('cash'), 'bd_mater', f'{vid}.txt'])
    if F.nalich_file(put):
        spis_tex_param = F.otkr_f(put, separ='|', utf8=True)
        nk_kod = F.nom_kol_po_im_v_shap(spis_tex_param, 'Код')
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
            nk = F.nom_kol_po_im_v_shap(spis_tex_param, DICT_POLE[vid][key])
            znach = spis_tex_param[stroka][nk]
            if rez != '':
                znach_old = rez[-1][F.nom_kol_po_im_v_shap(rez, key)]
            if rez == '' or znach != znach_old:
                zapros = f'''
                            UPDATE nomen SET {key} == '{znach}', Дата_изменения == '{F.now()}' WHERE Код == "{kod}"
                            '''
                CSQ.zapros('', zapros=zapros, conn=conn)
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
    SPIS_VIDOV = CSQ.zapros(self.db_mater, f"""SELECT DISTINCT Вид FROM nomen""", conn=conn_db,shapka=False)
    for vid in SPIS_VIDOV:
        vid = vid[0]
        table = query_mat(vid, conn)
        nk_kod = F.nom_kol_po_im_v_shap(table, "rez.Код")
        nk_art = F.nom_kol_po_im_v_shap(table, "rez.Артикул")
        nk_naim = F.nom_kol_po_im_v_shap(table, "rez.Наименование")
        nk_edizm = F.nom_kol_po_im_v_shap(table, "rez.ЕдиницаИзмерения")
        nk_udal = F.nom_kol_po_im_v_shap(table, "rez.ПометкаУдаления")
        for i in range(1, len(table)):
            kod = table[i][nk_kod]
            query = f"""
            SELECT * FROM nomen WHERE Код == "{kod}"
            """
            rez = CSQ.zapros('', query, conn_db)
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
                CSQ.dob_strok_v_bd_sql(self.db_mater, 'nomen', [strok_input], conn=conn_db, cur=cur_db)
                spis_izm.append([table[i][nk_kod], 'Добавлен'])
    if spis_izm != []:
        put_f = F.putt_k_isp_file() + F.now('%d.%m.%Y') + '_Изменения ЕРП.txt'
        F.zap_f(put_f, spis_izm, separ='|')
        F.zapyst_file(put_f)
    return True

#general()