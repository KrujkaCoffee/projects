import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
from PyQt5.QtCore import QDate


def zapisat(self):
    tbl = self.ui.tbl_obespechenie
    spis = CQT.list_from_wtabl_c(tbl, hat_c=True)
    rez = check_spisok(spis)
    if rez != []:
        CQT.msgbox('\n'.join(rez))
        return
    zapis_obesp_v_mk(self, spis)


def zapis_obesp_v_mk(self, spis):
    rez = []
    nom_mk = self.glob_nom_mk_obesp
    if nom_mk == '':
        CQT.msgbox(f'Не выбрана МК')
        return
    nk_s_nn = F.num_col_by_name_in_hat_c(spis, 'НН')
    nk_s_defic = F.num_col_by_name_in_hat_c(spis, 'Дефицит_кол-во')
    nk_s_pdata = F.num_col_by_name_in_hat_c(spis, 'ПДата')
    nk_s_prim = F.num_col_by_name_in_hat_c(spis, 'Примечание')
    nk_s_fdata = F.num_col_by_name_in_hat_c(spis, 'ФДата')
    for i in range(1, len(spis)):
        if spis[i][nk_s_pdata] != "":
            rez.append(spis[i])
    custom_request_c = f'''UPDATE mk SET Обеспечение = ? WHERE  Пномер == ?'''
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, list_of_lists_c=[F.to_binary_pickle(rez),nom_mk])
    if rez:
        CQT.msgbox('Запись прошла упешно')
    else:
        CQT.msgbox('Ошибка записи')
    return


def check_spisok(spis):
    rez = []
    nk_s_nn = F.num_col_by_name_in_hat_c(spis, 'НН')
    nk_s_defic = F.num_col_by_name_in_hat_c(spis, 'Дефицит_кол-во')
    nk_s_pdata = F.num_col_by_name_in_hat_c(spis, 'ПДата')
    nk_s_prim = F.num_col_by_name_in_hat_c(spis, 'Примечание')
    nk_s_fdata = F.num_col_by_name_in_hat_c(spis, 'ФДата')
    for i in range(1, len(spis)):
        if spis[i][nk_s_pdata] != "":
            if F.is_numeric(spis[i][nk_s_defic]) == False:
                rez.append(f'Дефицит_кол-во не число, строка {i}')
            if F.is_date(spis[i][nk_s_pdata], "%Y-%m-%d") == False:
                rez.append(f'ПДата не дата, строка {i}')
            if spis[i][nk_s_fdata] != '':
                if F.is_date(spis[i][nk_s_fdata], "%Y-%m-%d") == False:
                    rez.append(f'ФДата не дата, строка {i}')
    return rez

def select_obesp_po_mk_from_table(self,row,column):
    tbl = self.ui.tbl_obespechenie
    nk_pnom = CQT.num_col_by_name_c(tbl,'Пномер')
    if column != nk_pnom:
        return
    if nk_pnom == None:
        return
    try:
        nom_mk = int(tbl.item(row,nk_pnom).text())
        load_obesp_mk(self, nom_mk)
    except:
        return

@CQT.onerror
def load_obesp_mk(self, nom: int = ''):
    tbl = self.ui.table_spis_MK
    if nom == '':
        row = tbl.currentRow()
        if row == None or row == -1:
            return
        nk_nom = CQT.num_col_by_name_c(tbl,'Пномер')
        nom = int(tbl.item(row, nk_nom).text())
    self.glob_nom_mk_obesp = nom

    res = CMS.load_res(nom_mk=nom, db_resxml=self.db_resxml)
    shablon = load_shablon_dsem(res)
    if shablon == None:
        CQT.msgbox(f'Не создана ресурсная')
        self.ui.tabWidget_3.setCurrentIndex(0)
        return
    nk_s_nn = F.num_col_by_name_in_hat_c(shablon,'НН')
    nk_s_defic = F.num_col_by_name_in_hat_c(shablon, 'Дефицит_кол-во')
    nk_s_pdata = F.num_col_by_name_in_hat_c(shablon, 'ПДата')
    nk_s_prim = F.num_col_by_name_in_hat_c(shablon, 'Примечание')
    nk_s_fdata = F.num_col_by_name_in_hat_c(shablon, 'ФДата')
    nk_s_oper = F.num_col_by_name_in_hat_c(shablon, 'Опер_имя/ед_изм')
    custom_request_c = f'''SELECT Обеспечение FROM mk WHERE Пномер == {nom}'''
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c)
    if rez[-1][0] != '':
        for item in F.from_binary_pickle(rez[-1][0]):
            for i in range(1,len(shablon)):
                if item[nk_s_nn] == shablon[i][nk_s_nn] and item[nk_s_oper] == shablon[i][nk_s_oper]:
                    shablon[i][nk_s_defic] = item[nk_s_defic]
                    shablon[i][nk_s_pdata] = item[nk_s_pdata]
                    shablon[i][nk_s_prim] = item[nk_s_prim]
                    shablon[i][nk_s_fdata] = item[nk_s_fdata]
    set_edit = {nk_s_defic,nk_s_prim}
    CQT.fill_wtabl_old_c(self,shablon,self.ui.tbl_obespechenie,separ='',isp_hat_c=True,
                     set_editeble_col_nomera=set_edit,min_shir_col=40)
    CMS.fill_filtr_c(self,self.ui.tbl_obespechenie_filtr,self.ui.tbl_obespechenie)

def spis_obesp_po_mk(self):
    self.glob_nom_mk_obesp = ''
    custom_request_c = f'''SELECT Номер_заказа, Номер_проекта, Пномер, Обеспечение FROM mk WHERE Статус == "Открыта"'''
    query = CSQ.custom_request_c(self.bd_naryad,custom_request_c)
    nk_nz = F.num_col_by_name_in_hat_c(query,'Номер_заказа')
    nk_np = F.num_col_by_name_in_hat_c(query, 'Номер_проекта')
    nk_mk = F.num_col_by_name_in_hat_c(query, 'Пномер')
    nk_obesp = F.num_col_by_name_in_hat_c(query, 'Обеспечение')

    rez = [["Номер_заказа", "Номер_проекта", "Пномер", 'НН','Наименование','Количество','Опер_имя/ед_изм',
           'ПДата','Дефицит_кол-во','ФДата','Примечание']]
    for i in range(1,len(query)):
        nz = query[i][nk_nz]
        np = query[i][nk_np]
        mk = query[i][nk_mk]
        if query[i][nk_obesp] != "":
            spis_obesp = F.from_binary_pickle(query[i][nk_obesp])
            if spis_obesp != None:
                for item in spis_obesp:
                    item.insert(0,mk)
                    item.insert(0,np)
                    item.insert(0,nz)
                    rez.append(item)
    CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_obespechenie, separ='', isp_hat_c=True,
                     min_shir_col=40)
    CMS.fill_filtr_c(self, self.ui.tbl_obespechenie_filtr, self.ui.tbl_obespechenie)

def load_shablon_dsem(res):
    if res == None:
        return
    spis_oper = [['НН','Наименование','Количество','Опер_имя/ед_изм','ПДата','Дефицит_кол-во','ФДата','Примечание']]
    dict_mat = dict()
    for dse in res:
        for oper in dse['Операции']:
            spis_oper.append([dse['Номенклатурный_номер'],dse['Наименование'],
                              dse['Количество'],f'{oper["Опер_номер"]}_{oper["Опер_наименование"]}','','','',''])
            for material in oper['Материалы']:
                if material['Мат_код'] not in dict_mat:
                    dict_mat[material['Мат_код']] = [material['Мат_код'],material['Мат_наименование'],
                                                     material['Мат_норма'],material['Мат_ед_изм'],'','','','']
                else:
                    dict_mat[material['Мат_код']][2] += material['Мат_норма']
    for key in dict_mat.keys():
        dict_mat[key][2]= round(dict_mat[key][2],6)
        spis_oper.append(dict_mat[key])
    return  spis_oper


def data_obespech(self):
    date = self.ui.cld_obespechenie.selectedDate()
    tbl = self.ui.tbl_obespechenie
    row = tbl.currentRow()
    col = tbl.currentColumn()
    if row == -1:
        return
    nk_s_nn = CQT.num_col_by_name_c(tbl, 'НН')
    nk_s_defic = CQT.num_col_by_name_c(tbl, 'Дефицит_кол-во')
    nk_s_pdata = CQT.num_col_by_name_c(tbl, 'ПДата')
    nk_s_prim = CQT.num_col_by_name_c(tbl, 'Примечание')
    nk_s_fdata = CQT.num_col_by_name_c(tbl, 'ФДата')
    if tbl.item(row,nk_s_defic).text() == '':
        CQT.migat(self,tbl,row,nk_s_defic,2)
        return
    if col == nk_s_pdata or col == nk_s_fdata:
        if tbl.item(row, nk_s_defic).text() == '0':
            tbl.item(row, nk_s_pdata).setText('')
            tbl.item(row, nk_s_fdata).setText('')
        else:
            if tbl.item(row,col).text() != '':
                if CQT.msgboxgYN('Дата уже установлена, заменить?'):
                    tbl.item(row,col).setText(F.datetostr(QDate.toPyDate(date), "%Y-%m-%d"))
            else:
                tbl.item(row, col).setText(F.datetostr(QDate.toPyDate(date), "%Y-%m-%d"))

