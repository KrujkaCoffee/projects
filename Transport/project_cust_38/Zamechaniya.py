import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F
from project_cust_38 import Cust_config as CFG

@CQT.onerror
def load_zamech_to_edit(self,*args):
    tbl = self.ui.tbl_zamech
    tbl_add = self.ui.tbl_zamech_add_field
    row = tbl.currentRow()
    nk_nom = CQT.num_col_by_name_c(tbl, 'Пномер')
    nk_mk = CQT.num_col_by_name_c(tbl, 'МК')
    nk_vin = CQT.num_col_by_name_c(tbl, 'Виновное_подразделение')
    nk_smesh = CQT.num_col_by_name_c(tbl, 'Фсмещение_дней')
    nk_poter_chas = CQT.num_col_by_name_c(tbl, 'Фпотери_времени_час')
    nk_poter_mat = CQT.num_col_by_name_c(tbl, 'Фпотери_материала_марка')
    nk_poter_art = CQT.num_col_by_name_c(tbl, 'Артикул_ЕРП')
    nk_poter_ves = CQT.num_col_by_name_c(tbl, 'Фпотери_материала_вес')
    nk_kod = CQT.num_col_by_name_c(tbl, 'Код')
    nk_primech = CQT.num_col_by_name_c(tbl, 'Примечание')
    nk_soder = CQT.num_col_by_name_c(tbl, 'Содержание')
    nk_nom2 = CQT.num_col_by_name_c(tbl_add, 'Пномер')
    nk_mk2 = CQT.num_col_by_name_c(tbl_add, 'МК')
    nk_vin2 = CQT.num_col_by_name_c(tbl_add, 'Виновное_подразделение')
    nk_smesh2 = CQT.num_col_by_name_c(tbl_add, 'Фсмещение_дней')
    nk_poter_chas2 = CQT.num_col_by_name_c(tbl_add, 'Фпотери_времени_час')
    nk_poter_mat2 = CQT.num_col_by_name_c(tbl_add, 'Фпотери_материала_марка')
    nk_poter_ves2 = CQT.num_col_by_name_c(tbl_add, 'Фпотери_материала_вес')
    nk_kod2 = CQT.num_col_by_name_c(tbl_add, 'Код')
    nk_poter_art2 = CQT.num_col_by_name_c(tbl_add, 'Артикул_ЕРП')
    tbl_add.item(0, nk_nom2).setText(tbl.item(row, nk_nom).text())
    tbl_add.item(0, nk_mk2).setText(tbl.item(row, nk_mk).text())
    tbl_add.item(0, nk_vin2).setText(tbl.item(row, nk_vin).text())
    tbl_add.item(0, nk_smesh2).setText(tbl.item(row, nk_smesh).text())
    tbl_add.item(0, nk_poter_chas2).setText(tbl.item(row, nk_poter_chas).text())
    tbl_add.item(0, nk_poter_mat2).setText(tbl.item(row, nk_poter_mat).text())
    tbl_add.item(0, nk_poter_ves2).setText(tbl.item(row, nk_poter_ves).text())
    tbl_add.item(0, nk_kod2).setText(tbl.item(row, nk_kod).text())
    tbl_add.item(0, nk_poter_art2).setText(tbl.item(row, nk_poter_art).text())
    self.ui.pte_zamechnie.setPlainText(tbl.item(row, nk_soder).text())
    self.ui.pte_primechanie.setPlainText(tbl.item(row, nk_primech).text())


def load_table(self):
    tbl = self.ui.tbl_zamech
    custom_request_c = f"""SELECT 
       z.Пномер,
       z.Дата_создания,
       z.МК,
       z.Инициатор,
       z.Содержание,
       rab_c.empl_Подразделение as Виновное_подразделение,
       z.Фсмещение_дней,
       z.Фпотери_времени_час,
       z.Фпотери_материала_марка,
       z.Артикул_ЕРП,
       z.Фпотери_материала_вес,
       z.Код,
       z.Примечание,
       z.Пояснение_вп,
       z.Код_вп,
       z.Ответственный,
       z.ФИО_виновный
                              FROM zamech as z
                              LEFT JOIN rab_c ON rab_c.Код = z.Виновное_подразделение
                             ORDER BY Пномер DESC;
                             """
    db_users = CFG.Config.project.db_users # (По задаче 100054795 ) 28.05.2025
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, attach_dbs=db_users)
    #nk_podr = F.num_col_by_name_in_hat_c(rez,'Виновное_подразделение')
    #for i in range(len(rez)):
    #    if rez[i][nk_podr] in self.DICT_RC:
    #        rez[i][nk_podr] = self.DICT_RC[rez[i][nk_podr]]['Сокр_наим_СТО']
    #CQT.fill_wtabl_old_c(self, rez, tbl, isp_hat_c=True, separ='')
    CQT.fill_wtabl(rez,tbl,auto_type=False,selectionBehavior="SelectRows",sortingEnabled=True)
    CMS.fill_filtr_c(self, self.ui.tbl_zamech_filtr, tbl)
    
def load_table_zamech(self):
    load_table(self)

def select_podrazd(self,text, row, col):
    tbl = self.ui.tbl_zamech_add_field
    kod_rc = ''
    for key in self.DICT_RC.keys():
        if self.DICT_RC[key]['Сокр_наим_СТО'] == text:
            kod_rc = key
    tbl.item(row, col).setText(kod_rc)
    nk_kod = CQT.num_col_by_name_c(self.ui.tbl_zamech_add_field, 'Код')
    tbl.removeCellWidget(0,nk_kod)
    tbl.item(row, nk_kod).setText('')
    if text == "":
        return
    list_kod = []
    for key in self.SL_OSHIBKI.keys():
        if self.SL_OSHIBKI[key]['Подразделения'] == '' or text in self.SL_OSHIBKI[key]['Подразделения'].split(';'):
            list_kod.append(self.SL_OSHIBKI[key]['Имя'])
    CQT.add_combobox(self, tbl, 0, nk_kod, list_kod, True, select_kod)
    
def select_kod(self, text, row, col):
    nk_podr = CQT.num_col_by_name_c(self.ui.tbl_zamech_add_field,'Виновное_подразделение')
    if self.ui.tbl_zamech_add_field.item(0,nk_podr).text() == '':
        CQT.msgbox(f'Не выбрано поразделение')
        tbl.item(row, col).setText('')
        tbl.cellWidget(row, col).setCurrentText('')
        return
    if text == "":
        return
    tbl = self.ui.tbl_zamech_add_field
    for key in self.SL_OSHIBKI.keys():
        if self.SL_OSHIBKI[key]['Имя'] == text:
            tbl.item(row, col).setText(str(key))
            return
    CQT.msgbox('Код ошибки не найден')
    return

def select_art(self, text, row, col):
    if text == "":
        return
    tbl = self.ui.tbl_zamech_add_field
    fl = False
    for art in self.DICT_NOMEN.keys():
        if text == self.DICT_NOMEN[art]['Наименование']:
            fl = True
            art_mat= art
            break
    if fl:
        tbl.item(row, col).setText(art_mat)
        return
    else:
        CQT.msgbox('Артикул не найден')
    return

def select_kod_mat(self, text, row, col):
    if text == "":
        return
    tbl = self.ui.tbl_zamech_add_field
    if text in self.SL_KOD_MATER:
        tbl.item(row, col).setText(str(self.SL_KOD_MATER[text]))
        return
    else:
        CQT.msgbox('Код материала не найден')
    return


def init_zamech_const(self):
    SL_OSHIBKI = CSQ.custom_request_c(self.bd_naryad,f"""SELECT * FROM kod_zamech""", rez_dict=True)
    self.SL_OSHIBKI = F.deploy_dict_c(SL_OSHIBKI,'Пномер')
    exclude_podr = ['070000']
    #self.SET_PODRAZD = ("ОУП", "ОГК", "Снабжение", "ОГТ", "Склад", "ПДО", "Производство")
    self.SET_PODRAZD = [self.DICT_RC[_]['Сокр_наим_СТО'] for _ in self.DICT_RC.keys() if _[-4:] == '0000' and _[-4:] not in exclude_podr]
    self.DICT_PODRAZD = {self.DICT_RC[_]['Сокр_наим_СТО']:self.DICT_RC[_]['Наим_СТО'] for _ in self.DICT_RC.keys() if
                        _[-4:] == '0000' and _[-4:] not in exclude_podr}
    rez = CSQ.custom_request_c(self.bd_naryad,'''SELECT * FROM material_kod''',hat_c= False)
    if rez == False:
        CQT.msgbox(f'Нет данных {init_zamech_const}')
        return 
    self.SL_KOD_MATER = dict()
    for name, kod, kod_for_normatives in rez:
        self.SL_KOD_MATER[name] = kod

def load_table_add(self):
    tbl = self.ui.tbl_zamech_add_field
    rez = [["Пномер", "МК", "Виновное_подразделение", "Фсмещение_дней", "Фпотери_времени_час", "Фпотери_материала_марка","Артикул_ЕРП",
    "Фпотери_материала_вес",'Код']]
    rez.append(['' for _ in rez[0]])
    set_edit_column = {_ for _ in range(len(rez[0])) if _ not in [F.num_col_by_name_in_hat_c(rez,'Пномер')]}
    CQT.fill_wtabl_old_c(self, rez, tbl, isp_hat_c=True, separ='',set_editeble_col_nomera=set_edit_column)
    tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,'Пномер'), True)
    nk_vinov = F.num_col_by_name_in_hat_c(rez,'Виновное_подразделение')
    CQT.add_combobox(self,tbl,0,nk_vinov,self.DICT_PODRAZD,True, select_podrazd)
    nk_kod = CQT.num_col_by_name_c(self.ui.tbl_zamech_add_field, 'Код')
    CQT.set_cell_editable(tbl,0,nk_kod,False)
    nk_mater = F.num_col_by_name_in_hat_c(rez, 'Фпотери_материала_марка')
    CQT.add_combobox(self, tbl, 0, nk_mater, [_ for _ in self.SL_KOD_MATER.keys()], True, select_kod_mat)
    nk_art = F.num_col_by_name_in_hat_c(rez, 'Артикул_ЕРП')
    CQT.add_combobox(self, tbl, 0, nk_art, [self.DICT_NOMEN[_]['Наименование'] for _ in self.DICT_NOMEN.keys()], True, select_art)
    tbl.cellWidget(0,nk_art).setEditable(True)
    self.ui.pte_zamechnie.setPlainText('')
    self.ui.pte_primechanie.setPlainText('')

def check_add_zamech(self):
    tbl = self.ui.tbl_zamech_add_field
    spis = CQT.list_from_wtabl_c(tbl,hat_c=True)
    spis_err = []
    nk_mk = F.num_col_by_name_in_hat_c(spis,'МК')
    if spis[-1][nk_mk] == '':
        spis_err.append('МК пусто')
    else:
        if F.is_numeric(spis[-1][nk_mk]) == False:
            spis_err.append(f'МК {spis[-1][nk_mk]} не число')
        else:
            rez = CSQ.custom_request_c(self.bd_naryad,f'''SELECT Пномер FROM mk WHERE Пномер == {int(spis[-1][nk_mk])}''')
            if len(rez) == 1:
                spis_err.append(f'МК {spis[-1][nk_mk]} не существет')

    nk_vinov = F.num_col_by_name_in_hat_c(spis, 'Виновное_подразделение')
    if spis[-1][nk_vinov] == '':
        spis_err.append('Не указан виновник')
    nk_smesh = F.num_col_by_name_in_hat_c(spis, 'Фсмещение_дней')
    if spis[-1][nk_smesh] == '':
        spis_err.append('Не указано смещение_дней')
    else:
        if F.is_numeric(spis[-1][nk_smesh]) == False:
            spis_err.append('Не число смещение_дней')
    nk_poteri_vrem = F.num_col_by_name_in_hat_c(spis, 'Фпотери_времени_час')
    if spis[-1][nk_poteri_vrem] == '':
        spis_err.append('Не указано потери_времени_час')
    else:
        if F.is_numeric(spis[-1][nk_poteri_vrem]) == False:
            spis_err.append('Не число потери_времени_час')
    nk_poteri_ves = F.num_col_by_name_in_hat_c(spis, 'Фпотери_материала_вес')
    if spis[-1][nk_poteri_ves] != '':
        if F.is_numeric(spis[-1][nk_poteri_ves]) == False:
            spis_err.append('Не число Фпотери_материала_вес')

    nk_kod = F.num_col_by_name_in_hat_c(spis, 'Код')
    if spis[-1][nk_kod] == '':
        spis_err.append('Не указано Код')
    else:
        if F.is_numeric(spis[-1][nk_kod]) == False:
            spis_err.append('Не число Код')

    if self.ui.pte_zamechnie.toPlainText() == '':
        spis_err.append('Не указано содержание')

    if spis_err == []:
        return True
    else:
        CQT.msgbox('\n'.join(spis_err))
        return False

def add_zamech(self):
    if check_add_zamech(self) == False:
        return

    tbl = self.ui.tbl_zamech_add_field
    spis = CQT.list_from_wtabl_c(tbl,hat_c=True)
    nk_nom = F.num_col_by_name_in_hat_c(spis, 'Пномер')
    nk_mk = F.num_col_by_name_in_hat_c(spis, 'МК')
    nk_vinov = F.num_col_by_name_in_hat_c(spis, 'Виновное_подразделение')
    nk_smesh = F.num_col_by_name_in_hat_c(spis, 'Фсмещение_дней')
    nk_poteri_vrem = F.num_col_by_name_in_hat_c(spis, 'Фпотери_времени_час')
    nk_poteri_mat = F.num_col_by_name_in_hat_c(spis, 'Фпотери_материала_марка')
    nk_poteri_ves = F.num_col_by_name_in_hat_c(spis, 'Фпотери_материала_вес')
    nk_kod = F.num_col_by_name_in_hat_c(spis, 'Код')
    nk_poteri_art = F.num_col_by_name_in_hat_c(spis, 'Артикул_ЕРП')
    if spis[-1][nk_nom] != "":
        rez = CSQ.custom_request_c(self.bd_naryad, f'''SELECT Пномер FROM zamech WHERE Пномер == {int(spis[-1][nk_nom])}''')
        if len(rez) == 2:
            custom_request_c = f'''UPDATE zamech SET МК = ?, Содержание = ?, 
                            Виновное_подразделение = ?, Фсмещение_дней = ?,
                                  Фпотери_времени_час = ?, Фпотери_материала_марка = ?,
                        Фпотери_материала_вес = ?, Код = ?, Примечание = ?
                                  WHERE Пномер == {int(spis[-1][nk_nom])}'''
            CSQ.custom_request_c(self.bd_naryad, custom_request_c,list_of_lists_c=[spis[-1][nk_mk],
                    self.ui.pte_zamechnie.toPlainText(),spis[-1][nk_vinov],spis[-1][nk_smesh],spis[-1][nk_poteri_vrem],
                        spis[-1][nk_poteri_mat],spis[-1][nk_poteri_ves],spis[-1][nk_kod],self.ui.pte_primechanie.toPlainText()
                                                               ])
            CQT.msgbox('Замечание успешно Обновлено')
        else:
            CQT.msgbox(f'Замечание {spis[-1][nk_nom]} не найдено')
    else:
        custom_request_c = '''INSERT INTO zamech
                              (Дата_создания, МК, Инициатор, Содержание, Виновное_подразделение, Фсмещение_дней,
                              Фпотери_времени_час, Фпотери_материала_марка, Артикул_ЕРП, Фпотери_материала_вес, Код, Примечание)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'''
        CSQ.custom_request_c(self.bd_naryad,custom_request_c,list_of_lists_c=[[F.now(), spis[-1][nk_mk], F.user_name(), self.ui.pte_zamechnie.toPlainText(), spis[-1][nk_vinov], spis[-1][nk_smesh],
                              spis[-1][nk_poteri_vrem], spis[-1][nk_poteri_mat], spis[-1][nk_poteri_art], spis[-1][nk_poteri_ves], spis[-1][nk_kod], self.ui.pte_primechanie.toPlainText()]])
        CQT.msgbox('Замечание успешно добавлено')
    load_table_add(self)
    load_table(self)
