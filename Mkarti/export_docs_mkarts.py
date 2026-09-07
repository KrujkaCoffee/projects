import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.xml_v_drevo as XML




@CQT.onerror
def spis_res_erp_po_mk(self, nom_mk: int, kolich: int):
    list_set_mat_report = set()
    list_mat_report = []
    rez = [['Наименование_РС', 'Номенклатура_Продукция', 'Количество_Выпуск', 'Номенклатура_Материал', 'Количество',
            'Этап_применения', 'Статья_калькуляции', 'Вид_работ', 'Количество', 'Этап_применения',
            'Статья_калькуляции', 'Наименование_Этапа', 'Подразделение_исполнитель', 'ВРЦ', 'Время_выполнения',
            'Способы получения материала', 'Древо_код', 'Уровень']]
    # spis_dse = load_res(nom_mk)
    query = f'''SELECT data, Head FROM xml WHERE Номер_мк == {int(nom_mk)}'''
    rez_xml = CSQ.custom_request_c(self.db_resxml, query)
    xml = rez_xml[-1][0]
    xml_head = rez_xml[-1][1]
    if xml == '':
        CQT.msgbox('Нет хмл файла')
        spis_dse = F.from_binary_pickle(CSQ.custom_request_c(self.db_resxml,f"""SELECT data FROM res WHERE Номер_мк = {int(nom_mk)}""",rez_dict=True,one=True)['data'])
        #spis_dse = CMS.align_tree_code_c(self, spis_dse)
        for i in range(len(spis_dse)):
            if spis_dse[i]['ПКИ'] == '':
                spis_dse[i]['ПКИ'] = '0'
    else:
        spis_dse = CMS.resource_from_xml_c(self, CMS.podgotovka_xml(self, XML.spisok_iz_xml(str_f=xml), xml_head),
                                            kol_vo_izdeliy=1)
    if spis_dse == None:
        return
    list_polyfabricatov = export_bd_polyfabricatov(spis_dse)
    if spis_dse == False:
        CQT.msgbox('Не создана МК')
        return
    for i in range(len(spis_dse)):
        if spis_dse[i]['ПКИ'] == '0':

            try:
                dreva_kod = spis_dse[i]['dreva_kod']
            except:
                dreva_kod = ''
            Основное_наименование_РС = ' '.join(
                (dreva_kod, spis_dse[i]['Номенклатурный_номер'], spis_dse[i]['Наименование']))
            Основное_Номенклатура_Продукция = ' '.join((spis_dse[i]['Номенклатурный_номер'], spis_dse[i]['Наименование']))

            Основное_Количество_Выпуск = spis_dse[i]['Количество']
            level_c_tmp = spis_dse[i]['Уровень']

            dict_sort_cov = dict()
            for oper in spis_dse[i]['Операции']:
                if oper['Опер_профессия_код'] in self.DICT_PROFESSIONS:
                    Трудозатраты_вид_работ = self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['вид работ']
                    try:
                        Трудозатраты_Этап_применения = oper['Этап']
                    except:
                        try:
                            Трудозатраты_Этап_применения = self.DICT_VAR_OPER[oper['Опер_наименование']][0]['etap']
                        except:
                            Трудозатраты_Этап_применения = ''
                    tpz = oper['Опер_Тпз'] / spis_dse[i]['Количество']
                    try:
                        tsht = oper['Опер_Тшт_ед']
                    except:
                        tsht = oper['Опер_Тшт']/spis_dse[i]['Количество']

                    Трудозатраты_Количество = tpz + tsht
                    if (Трудозатраты_вид_работ,Трудозатраты_Этап_применения) in dict_sort_cov:
                        dict_sort_cov[(Трудозатраты_вид_работ, Трудозатраты_Этап_применения)] =\
                            dict_sort_cov[(Трудозатраты_вид_работ, Трудозатраты_Этап_применения)] + Трудозатраты_Количество
                    else:
                        dict_sort_cov[(Трудозатраты_вид_работ,Трудозатраты_Этап_применения)] = Трудозатраты_Количество

            for oper in spis_dse[i]['Операции']:
                if oper['Опер_профессия_код'] not in self.DICT_PROFESSIONS:
                    CQT.msgbox(f'не найдена в бд профессий {oper["Опер_профессия_код"]} в {Основное_наименование_РС}')
                else:
                    Трудозатраты_вид_работ = self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['вид работ']
                    tpz = oper['Опер_Тпз'] / spis_dse[i]['Количество']
                    try:
                        tsht = oper['Опер_Тшт_ед']
                    except:
                        tsht = oper['Опер_Тшт'] / spis_dse[i]['Количество']
                    Трудозатраты_Количество = round(tpz + tsht, 2)
                    try:
                        Трудозатраты_Этап_применения = oper['Этап']
                    except:
                        try:
                            Трудозатраты_Этап_применения = self.DICT_VAR_OPER[oper['Опер_наименование']][0]['etap']
                        except:
                            Трудозатраты_Этап_применения = ''
                    Трудозатраты_Статья_калькуляции = 'Основной ФОТ'
                    Пп_наименование_Этапа = Трудозатраты_Этап_применения
                    #Пп_Подразделение_исполнитель = '_'.join((oper['Опер_РЦ_наименование'], oper['Опер_РЦ_код']))
                    Пп_Подразделение_исполнитель = ''
                    Пп_ВРЦ = self.DICT_RC[oper['Опер_РЦ_код'][:-2] + '00']['Имя']
                    Пп_Время_выполнения = ''
                    if self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['Прямые'] != 0:
                        if (Трудозатраты_вид_работ,Трудозатраты_Этап_применения) in dict_sort_cov:
                            Трудозатраты_Количество = dict_sort_cov[(Трудозатраты_вид_работ,Трудозатраты_Этап_применения)]
                            rez.append(
                            [Основное_наименование_РС, Основное_Номенклатура_Продукция, Основное_Количество_Выпуск,
                             '', '', '',
                             '',
                             Трудозатраты_вид_работ, round(Трудозатраты_Количество,2), Трудозатраты_Этап_применения,
                             Трудозатраты_Статья_калькуляции,
                             Пп_наименование_Этапа, Пп_Подразделение_исполнитель, Пп_ВРЦ, Пп_Время_выполнения, '',
                             dreva_kod, level_c_tmp])
                            dict_sort_cov.pop((Трудозатраты_вид_работ,Трудозатраты_Этап_применения))

            for oper in spis_dse[i]['Операции']:
                if oper['Опер_профессия_код'] not in self.DICT_PROFESSIONS:
                    CQT.msgbox(f'не найдена в бд профессий {oper["Опер_профессия_код"]} в {Основное_наименование_РС}')
                else:
                    try:
                        Пп_наименование_Этапа = oper['Этап']
                    except:
                        try:
                            Пп_наименование_Этапа = self.DICT_VAR_OPER[oper['Опер_наименование']][0]['etap']
                        except:
                            Пп_наименование_Этапа = ''
                    Пп_Подразделение_исполнитель = '_'.join((oper['Опер_РЦ_наименование'], oper['Опер_РЦ_код']))
                    Пп_ВРЦ = self.DICT_RC[oper['Опер_РЦ_код'][:-2] + '00']['Имя']
                    Пп_Время_выполнения = ''
                    for mat in oper['Материалы']:
                        fl_add, list_set_mat_report,list_mat_report = calc_filtr(self,oper,mat,list_set_mat_report,list_mat_report)
                        if fl_add:
                            list_Материалы = self.DICT_NOMEN[mat['Мат_код']]
                            Материалы_Этап_применения = Пп_наименование_Этапа
                            Материалы_Статья_калькуляции = 'Сырье'
                            if list_Материалы['Вид'] == 'Упаковочные материалы для складского хоз-ва 10.09':
                                Материалы_Статья_калькуляции = 'Упаковка'
                            Материалы_Номенклатура_Материал = list_Материалы['Наименование']
                            try:
                                Материалы_Количество = str("{:.3f}".format(round(mat['Мат_норма_ед'], 3)))
                            except:
                                CQT.msgbox(f'не учтено ОШибка в строке {mat} для {Основное_Номенклатура_Продукция} в операции {Пп_Подразделение_исполнитель} попробуйте обновить мк')
                            rez.append(
                                [Основное_наименование_РС, Основное_Номенклатура_Продукция, Основное_Количество_Выпуск,
                                 Материалы_Номенклатура_Материал, Материалы_Количество, Материалы_Этап_применения,
                                 Материалы_Статья_калькуляции,
                                 "", "", "", "",
                                 Пп_наименование_Этапа, Пп_Подразделение_исполнитель, Пп_ВРЦ, Пп_Время_выполнения,
                                 'Обеспечивать', dreva_kod, level_c_tmp])

            if i + 1 < len(spis_dse):
                for j in range(i + 1, len(spis_dse)):
                    if spis_dse[j]['Уровень'] == level_c_tmp + 1:
                        Материалы_Номенклатура_Материал_dse = ' '.join(
                            (spis_dse[j]['Номенклатурный_номер'], spis_dse[j]['Наименование']))
                        Способы_получения_материала = 'Произвести по основной спецификации'
                        if spis_dse[j]['ПКИ'] == '1':
                            Материалы_Номенклатура_Материал_dse = spis_dse[j]['Наименование']
                            Способы_получения_материала = 'Обеспечивать'
                        rez.append(
                            [Основное_наименование_РС, Основное_Номенклатура_Продукция, Основное_Количество_Выпуск,
                             Материалы_Номенклатура_Материал_dse, spis_dse[j]['Количество']/spis_dse[i]['Количество'],
                             'Сборка+сварка',
                             'Сырье',
                             '', '', '', '',
                             'Сборка+сварка', 'Сборка_010301', 'Слесарно-каркасные и сборочно-сварочые работы', '',
                             Способы_получения_материала,
                             dreva_kod, level_c_tmp])
                    if spis_dse[j]['Уровень'] <= level_c_tmp:
                        break
    list_set_mat_report = list(list_set_mat_report)
    #CQT.msgbox(f'не найдены в бд МЕС {list_set_mat}')
    return rez, list_polyfabricatov, list_set_mat_report, list_mat_report

def calc_filtr(self,oper,mat,list_set_mat_report,list_mat_report):
    fl_add = False
    if mat['Мат_код'] not in self.DICT_NOMEN:
        list_set_mat_report.add(f"{mat['Мат_код']} {mat['Мат_наименование']}")
        return fl_add, list_set_mat_report,list_mat_report
    filtr = ''
    prich_add = f'не найден в фильтре в операции {oper["Опер_код"]}'
    for item in self.DICT_FILTR_NOMEN:
        if item['kod_oper'] == oper['Опер_код'] and mat['Мат_код'] == item['kod']:
            filtr = item['filtr']
            prich_add = f'найден в операции {oper["Опер_код"]} с фильтром {filtr}'
            break
    if filtr == '' or filtr == 0:
        fl_add = True
        list_mat_report.append(f'Материал {mat["Мат_код"]} {mat["Мат_наименование"]} добавлен потому что {prich_add}')
        print('')
    else:
        list_mat_report.append(f'Материал {mat["Мат_код"]} {mat["Мат_наименование"]} не добавлен потому что {prich_add}')
    return  fl_add,list_set_mat_report,list_mat_report


def export_res_erp(self):
    if self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex()) != 'Маршрутные карты':
        CQT.msgbox('Не выбрана вкладка Маршрутные карты')
        return
    if self.ui.table_spis_MK.currentRow() == -1:
        CQT.msgbox('Не выбрана маршрутная карта')
        return
    put_tmp = CMS.load_tmp_path('ved_mat')
    put = CQT.getDirectory(self, put_tmp)
    if put == '.':
        return
    CMS.save_tmp_path('ved_mat', put)
    nk_pnomer = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Пномер')
    nk_nomenk = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Номенклатура')
    nk_kolich = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Количество')
    nk_sort_c = CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Вид')
    nom_mk = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(), nk_pnomer).text()
    nomenk = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(), nk_nomenk).text()
    kolich = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(), nk_kolich).text()
    vid = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(), nk_sort_c).text()

    rez = spis_res_erp_po_mk(self, int(nom_mk), int(kolich))
    if rez == None:
        return
    else:
        spis, list_polyfabricatov, list_set_mat_report, list_mat_report = rez

    name_dir =put + F.sep() + f'{vid} {nomenk} МК{nom_mk}'
    if F.existence_file_c(name_dir):
        F.ochist_papky(name_dir)
    else:
        F.create_dir_c(name_dir)
    tmp_kod = 0
    name_rs = ''
    tmp = [spis[0][:-2]]
    try:
        for i in range(1,len(spis)+1):
            if i == len(spis) or spis[i][spis[0].index('Древо_код')] != tmp_kod:
                if tmp_kod != 0:
                    try:
                        rez = CEX.zap_spis(tmp,name_dir,f"{name_rs}.xls",'Ресурсная',0,0)
                        if rez == False:
                            F.write_file_c(name_dir + F.sep() + f'{name_rs}.txt',tmp, '\t')
                    except:
                        CQT.msgbox(f'Не удалось выгрузить {name_rs}.xls')
                    if i == len(spis):
                        break
                tmp = [spis[0][:-2]]
                tmp_kod = spis[i][spis[0].index('Древо_код')]
                name_rs = spis[i][spis[0].index('Наименование_РС')]
            tmp.append(spis[i][:-2])
    except:
        CQT.msgbox(f'Ошибка компиляции')
        return
    CEX.zap_spis(list_polyfabricatov, name_dir, f"Полуфабрикаты {vid} {nomenk} МК{nom_mk}.xls",
                 'Список полуфабрикатов', 0, 0)
    F.save_file_pickle(name_dir + '/list.pickle' ,spis)
    F.save_file_pickle(name_dir + '/list_pf.pickle', list_polyfabricatov)
    F.save_file(name_dir + '/report_unfound_db.txt', list_set_mat_report)
    F.save_file(name_dir + '/report_found_db.txt', list_mat_report)
    # CEX.zap_spis(spis, put, f'Нормы материалов на МК{nom_mk}_{nomenk}.xlsx', '1', 1, 1)
    #F.save_file(put + F.sep() + f'Ресурсная на МК{nom_mk}_{nomenk}.txt', spis)
    CQT.msgbox('Успешно')
    F.open_dir_c(put)


def export_bd_polyfabricatov(list_dse):
    """        put_tmp = CMS.load_tmp_path('polyfabricati')
    put = CQT.getDirectory(self, put_tmp)
    if put == '':
        return
    CMS.save_tmp_path('ved_mat', put)
    query = fSELECT Тип номенклатуры:   Товар
    Оформление продажи: Реализация товаров и услуг      Группа доступа: Продукция Пауэрз  Единица хранения:  шт.
    Единица для отчетов: шт.     Складская группа: Листы     Ставка НДС: 20%
    Группа аналитического учета:  Полуфабрикаты клапана    Группа финансового учета: Полуфабрикаты (21)"""
    rez = [['Наименование','Тип номенклатуры',
           'Оформление продажи','Группа доступа','Единица хранения',
           'Единица для отчетов','Складская группа','Ставка НДС',
           'Группа аналитического учета','Группа финансового учета']]
    set_rez = set()
    for dse in list_dse:
        if dse['Уровень'] != 0 and dse['ПКИ'] == '0':
            set_rez.add(dse['Номенклатурный_номер'] + ' ' + dse['Наименование'])
    for dse in set_rez:
        rez.append([dse, 'Товар', 'Реализация товаров и услуг', 'Продукция Пауэрз', 'шт.',
                    'шт.', 'Листы', '20%', 'Полуфабрикаты клапана', 'Полуфабрикаты (21)' ])
    return  rez
