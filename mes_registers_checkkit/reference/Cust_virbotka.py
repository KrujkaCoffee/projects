def list_per_month_new_c(db,nach,konec,db_kplan,db_users,podrazdelenie,organization,tabel_m=None):
    
    def get_filtr_dolgn(podrazdelenie,organization):
        filtr_dolgn = None
        if podrazdelenie != None:
            if organization == None:
                print('Не указана организаиця')
                return
        datetime_object_start = F.strtodate(nach, "%Y-%m-%d %H:%M:%S")
        datetime_object_finish = F.strtodate(konec, "%Y-%m-%d %H:%M:%S")
        beginning_month_datetime = datetime_object_start.replace(day=1)

        beginning_month_str = F.datetostr(beginning_month_datetime, "ДАТАВРЕМЯ(%Y, %m, %d)")
        start_month_datetime_str = F.datetostr(datetime_object_start, "ДАТАВРЕМЯ(%Y, %m, %d)")
        finish_month_datetime_str = F.datetostr(datetime_object_finish, "ДАТАВРЕМЯ(%Y, %m, %d)")
        text = f"""
        ВЫБРАТЬ РАЗЛИЧНЫЕ
            ДанныеДляПодбора.Должность КАК Должность,
            ДанныеДляПодбора.Подразделение КАК Подразделение
        ИЗ
            Документ.ТабельУчетаРабочегоВремени.ДанныеОВремени КАК ТабельУчетаРабочегоВремениДанныеОВремени
            ЛЕВОЕ СОЕДИНЕНИЕ РегистрСведений.ДанныеДляПодбораСотрудников КАК ДанныеДляПодбора
                ПО ДанныеДляПодбора.Сотрудник = ТабельУчетаРабочегоВремениДанныеОВремени.Сотрудник 
        ГДЕ
Подразделение.Наименование = "{podrazdelenie}"
            И ДанныеДляПодбора.Филиал.Наименование = "{organization}"
        СГРУППИРОВАТЬ ПО
            ДанныеДляПодбора.Должность,
            ДанныеДляПодбора.Подразделение
        """

        key, result_req = APIERP.get_wet_request(text=text)
        if key == 200 and result_req['data']:
            return [item['Должность'] for item in result_req['data']]
        else:
            filtr_dolgn = CSQ.custom_request_c(db, f"""SELECT "Должность" FROM dolgn_etap WHERE 
                 "Подразделение" = '{podrazdelenie}' AND "Производство" = '{organization}' ;""", hat_c=False,
                                           one_column=True)
            return filtr_dolgn

    filtr_dolgn = get_filtr_dolgn(podrazdelenie,organization)
    postfix = ""
    dict_employee = CMS.dict_emploee_full(db_users)
    if filtr_dolgn != None:
        filtr_fio = []
        if tabel_m == None:
            name_table = F.datetostr(F.strtodate(nach),"mtdz_%Y_%m_%d")
            users = CSQ.custom_request_c(db_users,f"""SELECT "ФИО" FROM "{name_table}";""",hat_c=False,one_column=True)
        else:
            users = [_[1] for _ in tabel_m[3:]]
        for user in users:
            fio = ' '.join(user.split()[:3])
            company = USRCNF.Config.place.Имя
            if fio not in dict_employee or dict_employee[fio]['Компания'] != company or dict_employee[fio]['Подразделение'] != podrazdelenie: #28.01.2026
                continue
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
    dict_per_month_c = {item['ФИО']: 0 for item in spis_jur} #28.01.2026
    for row in spis_per_month_c:
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
