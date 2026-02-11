import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import copy
import project_cust_38.Cust_Qt as CQT


def load_zagruzka(self):

    list_mk = load_list_mk(self)

    list_mk = prepare_list_mk(self,list_mk)
    if list_mk == None:
        return
    list_mk = load_list_dse(self,list_mk)
    list_mk = prepare_list_dse(self,list_mk)
    list_mk = edit_rc_for_transport_oper(self,list_mk)
    return list_mk


def edit_rc_for_transport_oper(self,list_mk):
    for i,mk in enumerate(list_mk):
        for j, dse in enumerate(mk['Ресурсная']):
            for k, oper in enumerate(dse['Операции']):
                if oper['Опер_профессия_код'] in self.DICT_PROFESSIONS:
                    if self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['Подмена_рц_для_плана'] == 1 and \
                        self.DICT_RC[oper['Опер_РЦ_код']]['Подмена_рц_для_плана'][:2] != oper['Опер_РЦ_код'][:2]:
                        list_mk[i]['Ресурсная'][j]['Операции'][k]['Опер_РЦ_код'] = self.DICT_RC[oper['Опер_РЦ_код']]['Подмена_рц_для_плана']
                        print(f"Замена {list_mk[i]['Ресурсная'][j]['Операции'][k]['Опер_РЦ_наименование']} на"
                            f" {self.DICT_RC[self.DICT_RC[oper['Опер_РЦ_код']]['Подмена_рц_для_плана']]['Имя']} т.к. для"
                              f" {self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['Подмена_рц_для_плана']} Подмена_рц_для_плана = 1")
                        list_mk[i]['Ресурсная'][j]['Операции'][k]['Опер_РЦ_наименование'] = self.DICT_RC[self.DICT_RC[oper['Опер_РЦ_код']]['Подмена_рц_для_плана']]['Имя']
    return list_mk

def load_list_mk(self):
    query = """SELECT mk.Пномер, mk.Дата, mk.Статус, mk.Номенклатура, mk.Номер_заказа, mk.Номер_проекта, mk.Вид, 
    mk.Примечание, mk.Основание, mk.Прогресс, mk.Приоритет, mk.Направление, mk.Вес, mk.xml, mk.Количество, 
    mk.Статус_ЧПУ,  mk.Дата_завершения, mk.Коэф_парал, mk.Обеспечение, mk.Место, mk.Искл_план_рм,
    zagot.Прим_резка, "" as Ресурсная
        FROM mk 
        INNER JOIN zagot ON mk.Пномер = zagot.Ном_МК 
        WHERE mk.Статус == "Открыта" ORDER BY mk.Приоритет ASC;"""

    responce = CSQ.custom_request_c(self.bd_naryad, query,'', True,rez_dict=True)
    filtr_plan = CSQ.custom_request_c(self.db_kplan, """SELECT ПУ FROM list_py_month""",hat_c=False,one_column=True)
    ans = []
    for item in responce:
        if item['Номер_заказа'] in filtr_plan:
            ans.append(item)
        else:
            print(f'{item["Пномер"]}  попала в конец , т.к. {item["Номер_заказа"]} не в списке db_kplan.list_py_month')

    for item in responce:
        if item['Номер_заказа'] not in filtr_plan:
            ans.append(item)

    rez = []
    con,cur = CSQ.connect_bd(self.db_resxml)
    for i in range(len(ans)):
        nom_mk= ans[i]['Пномер']
        res = CSQ.custom_request_c(self.db_resxml,f"""SELECT data FROM res WHERE Номер_мк = {nom_mk};""",one=True,one_column=True,cur=cur,conn=con)
        if res == False:
            print(f'Ошибка загрузки ресурсной {nom_mk}')
        else:
            ans[i]['Ресурсная'] = res[-1]
        rez.append(ans[i])
    CSQ.close_bd(conn=con,cur=cur)
    return rez

def prepare_list_mk(self,list_mk):
    for i in range(len(list_mk)):
        if list_mk[i]['Ресурсная'] == "":
            CQT.msgbox(f"Нет ресурсной мк {list_mk[i]['Пномер']}")
            return
        list_mk[i]['Ресурсная'] = F.from_binary_pickle(list_mk[i]['Ресурсная'])
        if list_mk[i]['Обеспечение'] != '':
            list_mk[i]['Обеспечение'] = F.from_binary_pickle(list_mk[i]['Обеспечение'])
    return list_mk

def load_list_dse(self,list_mk):
    for i in range(len(list_mk)):
        list_mk[i]['Ресурсная'] = list(reversed(list_mk[i]['Ресурсная']))
    return list_mk

def prepare_list_dse(self,list_mk):
    LIMIT_DATE = F.strtodate('2021-10-12')
    nk_nomen_nom_usl = 0
    nk_data_usl = 4
    nk_ima_usl = 1
    for i in range(len(list_mk)):
        list_obesp = list_mk[i]['Обеспечение']
        for j in range(len(list_mk[i]['Ресурсная'])):
            list_mk[i]['Ресурсная'][j]['Лимит_дата_начала'] = LIMIT_DATE
            for k in range(len(list_mk[i]['Ресурсная'][j]['Операции'])):
                list_mk[i]['Ресурсная'][j]['Операции'][k]['Лимит_дата_начала'] = LIMIT_DATE
                #list_mk[i]['Ресурсная'][j]['Операции'][k]['План_завершение'] = LIMIT_DATE
        if list_obesp != '':
            for yslovie in list_obesp:
                limit_date = copy.deepcopy(LIMIT_DATE)
                if F.is_date(yslovie[nk_data_usl], "%Y-%m-%d"):
                    if F.strtodate(yslovie[nk_data_usl], "%Y-%m-%d") > F.strtodate(limit_date, "%Y-%m-%d"):
                        kod_i_nomen = yslovie[nk_nomen_nom_usl]
                        new_data = yslovie[nk_data_usl]
                        for j in range(len(list_mk[i]['Ресурсная'])):
                            fl_naid = False
                            nomen_nom = list_mk[i]['Ресурсная'][j]['Номенклатурный_номер']
                            if kod_i_nomen == nomen_nom:
                                limit_date = new_data
                                list_mk[i]['Ресурсная'][j]['Лимит_дата_начала'] = limit_date
                                print(
                                    f"найден Лимит_дата_начала по {yslovie[nk_ima_usl]} в {list_mk[i]['Ресурсная'][j]['Номенклатурный_номер']} новая дата {limit_date}")
                                fl_naid = True
                            if fl_naid == False:
                                for k, oper in enumerate(list_mk[i]['Ресурсная'][j]['Операции']):
                                    if fl_naid:
                                        break
                                    list_mat = oper['Материалы']
                                    for material in list_mat:
                                        mater_kod = material['Мат_код']
                                        if kod_i_nomen == mater_kod:
                                            limit_date = new_data
                                            list_mk[i]['Ресурсная'][j]['Операции'][k]['Лимит_дата_начала'] = limit_date
                                            print(
                                                f"найден мат Лимит_дата_начала по {yslovie[nk_ima_usl]} в {list_mk[i]['Ресурсная'][j]['Номенклатурный_номер']} новая дата {limit_date}")
                                            fl_naid = True
                                            break
                else:
                    CQT.msgbox(
                        f'В {yslovie[nk_data_usl]} {yslovie[nk_ima_usl]} в мк {list_mk[i]["Пномер"]} дата не корректная: {yslovie[nk_data_usl]}')
    return list_mk
