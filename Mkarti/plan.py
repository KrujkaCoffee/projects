import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import datetime
import project_cust_38.Cust_mes as CTM
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets

import gant_ploty as gp

"""
определить соотношение направлений в % == направление, % *
определить порядок по приоритету мк по направлению, которые еще не зыкрыты == направление, номер мк *
каждую мк разложить на последовательность деталей, которые еще не сделаны  == направление, номер мк, имя детали, рц *
каждую деталь разложить на последовательность операций, которые еще не сделаны  == направление, номер мк, имя детали, рц, операция, время выполнения *
сформировать картину мощностей == направление, РЦ, часы, даты *
каждую операцию рассчитать на параллельное выполнение(сделать две но короче) == направление, номер мк, имя детали, рц, операция + операция, время выполнения
наполнять мощности операциями по порядку, фиксировать время начала операции и время конца
свести операции на диаграмму == направление, номер мк, имя детали, рц, операция , начало , конец
"""

F.test_path()


def ur_struk(name: str):
    return name.count('    ')


def spis_operaciy_iz_tehkart(putima):
    tehkarta = F.open_file_c(putima, False, '|', True)
    spis = [['Имя', "РЦ", "Тпз", "Тшт", "КР", "КОИД"]]
    for i in range(11, len(tehkarta)):
        if tehkarta[i][20] == '0':
            break
        if tehkarta[i][20] == '1':
            spis.append(
                [tehkarta[i][0], tehkarta[i][4], F.valm(tehkarta[i][6]), F.valm(tehkarta[i][7]), F.valm(tehkarta[i][9]),
                 F.valm(tehkarta[i][11])])
    return spis


def vivod_grafika(plan,vid=0,rc='',proj=''):
    """0 - fig_podetalno_narc_projects  rc?
        1 - fig_podetalno_naproject_rc proj?
        2 - fig_porc_projects"""
    class Widget(QtWidgets.QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            # self.button = QtWidgets.QPushButton('Plot', self)
            self.browser = QtWebEngineWidgets.QWebEngineView(self)

            vlayout = QtWidgets.QVBoxLayout(self)
            # vlayout.addWidget(self.button, alignment=QtCore.Qt.AlignHCenter)
            vlayout.addWidget(self.browser)

            # self.button.clicked.connect(self.show_graph)
            self.resize(1000, 800)
            self.show_graph()

        def show_graph(self):
            # df = px.data.tips()
            if vid == 0:
                fig = gp.fig_podetalno_narc_projects(plan, '010302')
            if vid == 1:
                fig = gp.fig_podetalno_naproject_rc(plan, '1601001')
            if vid == 2:
                fig = gp.fig_porc_projects(plan)
            self.vivod_gant(fig,self.browser)
            #self.browser.setHtml(fig.to_html(include_plotlyjs='cdn'))

        def vivod_gant(self, fig, obj):
            html = fig.to_html()
            print('2.1')
            putf = CTM.tmp_dir() + F.sep() + 'text.html'
            print('2.2')
            with open(putf, 'w+') as f:
                f.write(html)
            # rez = self.browser.setHtml(html)
            print('2.3')
            # self.ui.browser.setUrl(QtCore.QUrl(f"file://{putf.replace(F.sep(),'/')}"))
            obj.setUrl(QtCore.QUrl(f"file:///{putf.replace(F.sep(), '/')}"))
            print('2.4')
            # print(rez)

    if __name__ == "__main__":
        app = QtWidgets.QApplication([])
        widget = Widget()
        widget.show()
        app.exec()


DICT_NAPRAVL = {'КЛ': 0.5, 'КТ': 0.25, 'ШГ': 0.125, 'ПР': 0.125}
put_rc = F.tcfg('bd_rab_c')
spis_rc = F.open_file_c(put_rc, False, separ='|')

DICT_RC_IMA = dict()
for i in range(len(spis_rc)):
    DICT_RC_IMA[spis_rc[i][0]] = spis_rc[i][1]

DICT_RC_IMA['Ошибка'] = ''

PREDEL_PARALEL_MINUT = 20
KOEF_RAZDUPLENIYA_MIN = 2

DICT_SMENY = {'s1': {'начало': datetime.time(hour=7, minute=00, second=0),
                     'конец': datetime.time(hour=15, minute=29, second=59)},
              's2': {'начало': datetime.time(hour=15, minute=30, second=0),
                     'конец': datetime.time(hour=23, minute=59, second=58)},
              's0': {'начало': datetime.time(hour=0, minute=0, second=0),
                     'конец': datetime.time(hour=6, minute=59, second=59)}}

SCHAS = datetime.datetime.today()


def obiuem(napravl=''):
    dict_napravl_tmp = DICT_NAPRAVL
    if napravl != '':
        dict_napravl_tmp = {napravl: DICT_NAPRAVL[napravl]}
    # ===========================================================
    # put_k_mk = r'P:\Python\Mkarti\data\bd_mk.txt'
    # spis_mk = F.open_file_c(put_k_mk, separ='|')
    # ================
    custom_request_c = f'''SELECT * FROM mk WHERE Статус == "Открыта" AND Направление == "{napravl}" '''
    spis_mk = CSQ.custom_request_c(F.bdcfg('bd_mk'), custom_request_c)
    if len(spis_mk) == 1:
        print('Не найдены проекты')
        return

    nk_data = F.num_col_by_name_in_hat_c(spis_mk, 'Дата')
    nk_nom = F.num_col_by_name_in_hat_c(spis_mk, 'Пномер')
    nk_napr = F.num_col_by_name_in_hat_c(spis_mk, 'Направление')
    nk_prior = F.num_col_by_name_in_hat_c(spis_mk, 'Приоритет')
    nk_kol_izd = F.num_col_by_name_in_hat_c(spis_mk, 'Количество')
    nk_proj = F.num_col_by_name_in_hat_c(spis_mk, 'Номер_проекта')
    nk_pu = F.num_col_by_name_in_hat_c(spis_mk, 'Номер_заказа')
    nk_ves = F.num_col_by_name_in_hat_c(spis_mk, 'Вес')
    dict_nap_spis_mk = dict()

    spis_mk_uporyad_nap = [['Проект', 'Номер МК', 'Дата создания МК', 'Приоритет', 'Вес', 'Количество изделий', 'ДСЕ']]
    nk_tmp_nommk = F.num_col_by_name_in_hat_c(spis_mk_uporyad_nap, 'Номер МК')
    nk_tmp_dse = F.num_col_by_name_in_hat_c(spis_mk_uporyad_nap, 'ДСЕ')
    nk_tmp_kolizd = F.num_col_by_name_in_hat_c(spis_mk_uporyad_nap, 'Количество изделий')
    nk_tmp_datsozd = F.num_col_by_name_in_hat_c(spis_mk_uporyad_nap, 'Дата создания МК')
    nk_tmp_prioret = F.num_col_by_name_in_hat_c(spis_mk_uporyad_nap, 'Приоритет')
    nk_tmp_ves = F.num_col_by_name_in_hat_c(spis_mk_uporyad_nap, 'Вес')

    spis_mk_uporyad_nap_nesort = []
    for i in range(1, len(spis_mk)):
        if int(spis_mk[i][nk_kol_izd]) == 0:
            spis_mk[i][nk_kol_izd] = 1
        spis_mk_uporyad_nap_nesort.append(
            [spis_mk[i][nk_proj] + ' ' + spis_mk[i][nk_pu], spis_mk[i][nk_nom],
             F.strtodate(spis_mk[i][nk_data], "%y-%m-%d"), int(spis_mk[i][nk_prior]), int(spis_mk[i][nk_ves]),
             int(spis_mk[i][nk_kol_izd])])

    spis_mk_uporyad_nap_nesort.sort(key=lambda x: (x[nk_tmp_prioret], x[nk_tmp_datsozd]))

    spis_mk_uporyad_nap_nesort.insert(0, spis_mk_uporyad_nap[0])
    spis_mk_uporyad_nap = spis_mk_uporyad_nap_nesort
    # ===========================================================
    put_k_mk_det = F.scfg('mk_data')

    for i in range(1, len(spis_mk_uporyad_nap)):
        spis_det = F.open_file_c(put_k_mk_det + F.sep() + str(spis_mk_uporyad_nap[i][nk_tmp_nommk]) + '.txt', separ='|')
        nk_nazv_det = F.num_col_by_name_in_hat_c(spis_det, 'Наименование')
        nk_nn_det = F.num_col_by_name_in_hat_c(spis_det, 'Обозначение')
        nk_id_det = F.num_col_by_name_in_hat_c(spis_det, 'ID')
        nk_kol_det = F.num_col_by_name_in_hat_c(spis_det, 'Сумм.Количество')
        spis_det_tmp = []
        for j in range(1, len(spis_det)):
            # условие незавершенности ?????????
            spis_det_tmp.append([ur_struk(spis_det[j][nk_nazv_det]),
                                 spis_det[j][nk_nazv_det].strip(),
                                 spis_det[j][nk_nn_det].strip(),
                                 spis_det[j][nk_id_det],
                                 spis_det[j][nk_kol_det]])
        spis_det_tmp.sort(key=lambda x: (x[0], x[2]))
        spis_det_tmp = spis_det_tmp[::-1]
        spis_mk_uporyad_nap[i].append(spis_det_tmp)

    # ===========================================================
    put_k_texkart = F.scfg('add_docs')
    put_k_dse = F.bdcfg('BD_dse')
    conn, cur = CSQ.connect_bd(put_k_dse)

    for i in range(1, len(spis_mk_uporyad_nap)):  # MK
        for j in range(len(spis_mk_uporyad_nap[i][nk_tmp_dse])):  # dse
            ima_tehkart = ''
            custom_request_c = f'''
            SELECT Номер_техкарты FROM dse WHERE Номенклатурный_номер = '{spis_mk_uporyad_nap[i][nk_tmp_dse][j][2]}'
            '''
            nom_tk = CSQ.custom_request_c(put_k_dse, custom_request_c, conn, False)
            if nom_tk != []:
                ima_tehkart = nom_tk[0][0] + "_" + spis_mk_uporyad_nap[i][nk_tmp_dse][j][2]
            spis_mk_uporyad_nap[i][nk_tmp_dse][j].append(ima_tehkart)
    CSQ.close_bd(conn)

    for i in range(1, len(spis_mk_uporyad_nap)):  # MK
        kol_izd = spis_mk_uporyad_nap[i][nk_tmp_kolizd]
        for j in range(len(spis_mk_uporyad_nap[i][nk_tmp_dse])):  # dse
            ima_tehkart = spis_mk_uporyad_nap[i][nk_tmp_dse][j][5]
            kolvo = int(spis_mk_uporyad_nap[i][nk_tmp_dse][j][4])
            spis_op_tmp = [['Имя', "РЦ", "Т", "КР"]]
            if ima_tehkart != '':
                put_k_texkart_ima = put_k_texkart + F.sep() + ima_tehkart + '.pickle'
                spis_op = spis_operaciy_iz_tehkart(put_k_texkart_ima)
                for k in range(1, len(spis_op)):
                    # условие незавершенности операций по базе данных?????????
                    spis_op_tmp.append([spis_op[k][0],
                                        spis_op[k][1],
                                        round(KOEF_RAZDUPLENIYA_MIN +
                                              (spis_op[k][2] + spis_op[k][3] * kolvo * kol_izd)
                                              / spis_op[k][5], 1), spis_op[k][4]])
            spis_mk_uporyad_nap[i][nk_tmp_dse][j].append(spis_op_tmp)
    return spis_mk_uporyad_nap


def moshnost(napravl=''):
    koef_napravlenia = DICT_NAPRAVL[napravl]

    plecho_moshnosti = 2
    # =======================================

    put_db = F.scfg('bd_mk') + r'\proizv_cal.db'

    if not F.existence_file_c(put_db):
        print('Отсутствует бд')
        return

    first_day_1 = datetime.datetime.today().replace(day=1).date()
    months = [first_day_1]
    for i in range(1, plecho_moshnosti + 1):
        months.append(F.add_months(first_day_1, i).date())

    moschn_po_napravleniy = []
    conn, cur = CSQ.connect_bd(put_db)
    for m in months:
        ima_table = 'mtdz_' + str(m).replace('-', '_')
        if ima_table not in CSQ.get_list_of_tables_c(put_db, conn=conn, cur=cur):
            print(f'Отсутствует {ima_table} в базе')
            CSQ.close_bd(conn)
            return
        mesyac = CSQ.list_from_db_sql_c(put_db, ima_table, True, True, conn=conn, cur=cur)
        for i in range(4, len(mesyac[0])):
            den = F.strtodate('-'.join(mesyac[0][i].split('_')[1:])).date()
            smena = mesyac[0][i].split('_')[0]
            dict_rc = dict()
            for j in range(3, len(mesyac)):
                moshnost_posta_min = 450 * DICT_NAPRAVL[napravl]
                chislo_postov = mesyac[j][i] / 8
                vrema = 0 if mesyac[j][i] - 0.5 * chislo_postov < 0 else (mesyac[j][
                                                                              i] - 0.5 * chislo_postov) * 60 * koef_napravlenia
                vsego_vrema = vrema
                spis_postov = []
                for _ in range(int(vsego_vrema // moshnost_posta_min)):
                    spis_postov.append({'план': moshnost_posta_min, 'остат': moshnost_posta_min,
                                        'врсвоб': datetime.datetime.combine(den, DICT_SMENY[smena]['начало'])})
                if vsego_vrema % moshnost_posta_min > 0:
                    spis_postov.append(
                        {'план': vsego_vrema % moshnost_posta_min, 'остат': vsego_vrema % moshnost_posta_min})
                dict_rc[mesyac[j][1]] = spis_postov
            moschn_po_napravleniy.append([den, smena, dict_rc])
    CSQ.close_bd(conn)
    segodnya = SCHAS.date()
    for i in range(len(moschn_po_napravleniy)):
        dict_rc = moschn_po_napravleniy[i][2]
        dat = moschn_po_napravleniy[i][0]
        smena = moschn_po_napravleniy[i][1]
        if dat < segodnya:
            for rc in dict_rc.keys():
                for j in range(len(dict_rc[rc])):
                    dict_rc[rc][j]['план'] = 0
                    dict_rc[rc][j]['остат'] = 0
        if dat == segodnya:
            dat_konec = datetime.datetime.combine(dat, DICT_SMENY[smena]['конец'])
            dat_nach = datetime.datetime.combine(dat, DICT_SMENY[smena]['начало'])
            if SCHAS > dat_konec:
                for rc in dict_rc.keys():
                    for j in range(len(dict_rc[rc])):
                        dict_rc[rc][j]['план'] = 0
                        dict_rc[rc][j]['остат'] = 0
            if SCHAS > dat_nach and SCHAS < dat_konec:
                proshlo_min = (SCHAS - dat_nach).total_seconds() / 60
                dolya_ostavshego = 1 - proshlo_min / 480
                for rc in dict_rc.keys():
                    for j in range(len(dict_rc[rc])):
                        dict_rc[rc][j]['план'] *= dolya_ostavshego
                        dict_rc[rc][j]['остат'] *= dolya_ostavshego

    return moschn_po_napravleniy



def create_plan(napravl):
    napr = obiuem(napravl)
    moschn = moshnost(napravl)


    nk_tmp_proj = F.num_col_by_name_in_hat_c(napr, 'Проект')
    nk_tmp_nommk = F.num_col_by_name_in_hat_c(napr, 'Номер МК')
    nk_tmp_dse = F.num_col_by_name_in_hat_c(napr, 'ДСЕ')
    nk_tmp_kolizd = F.num_col_by_name_in_hat_c(napr, 'Количество изделий')
    nk_tmp_datsozd = F.num_col_by_name_in_hat_c(napr, 'Дата создания МК')
    nk_tmp_prioret = F.num_col_by_name_in_hat_c(napr, 'Приоритет')
    nk_tmp_ves = F.num_col_by_name_in_hat_c(napr, 'Вес')

    plan = []
    for i in range(1, len(napr)):
        mk = napr[i]  # MK
        for j in range(len(mk[nk_tmp_dse])):  # dse
            for k in range(1, len(mk[nk_tmp_dse][j][6])):  # oper
                nom_mk = mk[nk_tmp_nommk]
                det = mk[nk_tmp_dse][j][2]
                vrema_izn = mk[nk_tmp_dse][j][6][k][2]
                vrema_na_op = mk[nk_tmp_dse][j][6][k][2]
                kol_rab = mk[nk_tmp_dse][j][6][k][3]
                rc = mk[nk_tmp_dse][j][6][k][1]
                ima_op = mk[nk_tmp_dse][j][6][k][0]
                nach = ''
                konec = ''
                nomer_posta = ''
                if rc == '010302':
                    print('')
                if 'КТ.1602165.02.03' in det and rc == '010301' and 'Сборка под сварку' in ima_op and j == 44 and k == 2 and j_m == 0:
                    print('')
                for i_m in range(len(moschn)):
                    if vrema_na_op <= 0:# выход по трате всего времени на операцию
                        break
                    smena = moschn[i_m][1]# Номер сменый

                    if rc not in moschn[i_m][2]:#если у операции РЦ, отсутствующий в базе
                        print(f'В плане на {moschn[i_m][0]} нет мощностей по {rc}, '
                            f'для {ima_op} из {mk[nk_tmp_dse][j][1], mk[nk_tmp_dse][j][2]}')
                        nach = datetime.datetime.combine(moschn[i_m][0], DICT_SMENY['s1']['начало'])
                        konec = nach
                        nomer_posta = '1'
                        rc = 'Ошибка'
                        break

                    for j_m in range(len(moschn[i_m][2][rc])):# по всем постам
                        if nomer_posta != '':
                            if chislo_postov == len(moschn[i_m][2][rc]):
                                if nomer_posta != j_m + 1:
                                    continue

                        if vrema_na_op <= 0:
                            break
                        if moschn[i_m][2][rc][j_m]['остат'] > 0:

                            if nach == '':
                                if rc == '010101':
                                    print('')
                                nach = moschn[i_m][2][rc][j_m]['врсвоб']
                                nomer_posta = j_m + 1
                                chislo_postov = len(moschn[i_m][2][rc])

                            if vrema_na_op <= moschn[i_m][2][rc][j_m]['остат']:# если можно завержить операцию сейчас
                                moschn[i_m][2][rc][j_m]['остат'] -= vrema_na_op
                                if rc == '010101':
                                    print('')
                                moschn[i_m][2][rc][j_m]['врсвоб'] = moschn[i_m][2][rc][j_m]['врсвоб'] +\
                                                                    datetime.timedelta( minutes=vrema_na_op)
                                konec = moschn[i_m][2][rc][j_m]['врсвоб']
                                vrema_na_op = 0
                            else:# если завершить нельзя
                                if moschn[i_m][2][rc][j_m]['остат'] < moschn[i_m][2][rc][j_m]['план']:# если остается меньше чем смена
                                    ostat_na_den = moschn[i_m][2][rc][j_m]['остат']
                                else:
                                    ostat_na_den = moschn[i_m][2][rc][j_m]['план']
                                vrema_na_op -= ostat_na_den
                                moschn[i_m][2][rc][j_m]['остат'] -= ostat_na_den
                                moschn[i_m][2][rc][j_m]['врсвоб'] = ''
                                konec = datetime.datetime.combine(moschn[i_m][0],
                                                                  DICT_SMENY[smena]['начало']) + datetime.timedelta(
                                    minutes=480)
                                gotovnost = round((vrema_na_op / mk[nk_tmp_dse][j][6][k][2] * 100))
                                plan.append(
                                    {'Проект': mk[nk_tmp_proj], 'МК': nom_mk, 'Наменование': mk[nk_tmp_dse][j][1],
                                     'Номер': mk[nk_tmp_dse][j][2], 'Минут': vrema_izn,
                                     'РЦ': f'{DICT_RC_IMA[rc]}({rc})',
                                     'Операция': ima_op, 'Смена': smena.replace('s', ''), 'Начало': nach,
                                     'Завершение': konec,
                                     "Вес": round(mk[nk_tmp_ves] / 1000, 1),
                                     'Пост': int(nomer_posta), 'Статус': 'Пауза', 'Осталось': gotovnost})
                                nach = ''
                            break
                if nomer_posta == '':
                    print(f'На {ima_op} не распределены работы {vrema_na_op} минут, дефицит мощностей с {moschn[i_m][0]}' )
                else:
                    plan.append({'Проект': mk[nk_tmp_proj], 'МК': nom_mk, 'Наменование': mk[nk_tmp_dse][j][1],
                                 'Номер': mk[nk_tmp_dse][j][2], 'Минут': vrema_izn, 'РЦ': f'{DICT_RC_IMA[rc]}({rc})',
                                 'Операция': ima_op, 'Смена': smena.replace('s', ''), 'Начало': nach, 'Завершение': konec,
                                 "Вес": round(mk[nk_tmp_ves] / 1000, 1), 'Пост': int(nomer_posta),
                                 'Статус': 'Завершен', 'Осталось': 100})

    return plan


TEK_NAPRAVL = 'КТ'

plan = create_plan(TEK_NAPRAVL)

vivod_grafika(plan, 2)
