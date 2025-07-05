import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F


def load_py(self):
    custom_request_c = f'SELECT Номер_заказа, Номер_проекта, Вид, Дата_завершения  from mk'
    set_py = set()
    rez = CSQ.custom_request_c(self.db_naryd,custom_request_c)
    for item in rez[1:]:
        set_py.add(item[0])
    itog = [["Номер_заказа", "Номер_проекта", "Вид", "Дата_завершения"]]
    for py in set_py:
        fl_all_close = True
        np = ''
        vid = ''
        data = ''
        for item in rez[1:]:
            if item[0] == py:
                np = item[1]
                vid = item[2]
                data = item[3]
                if data == '':
                    fl_all_close = False
                    break
        if fl_all_close and np != '':
            itog.append([py,np,vid,data])
    CQT.fill_wtabl_old_c(self,itog,self.ui.tbl_anal_mk,separ='',isp_hat_c=True)
    CMS.fill_filtr_c(self, self.ui.tbl_anal_mk_filtr, self.ui.tbl_anal_mk)
    try:
        if self.compare_erp_putf != None:
            self.ui.lbl_txt_erp.setText(self.compare_erp_putf.split("\\")[-1])
    except:
        pass
    try:
        if self.compare_mes_putf != None:
            self.ui.lbl_txt_mes.setText(self.compare_mes_putf.split("\\")[-1])
    except:
        pass


def filtr_py(self):
    CMS.apply_filtr_c(self, self.ui.tbl_anal_mk_filtr, self.ui.tbl_anal_mk)

def load_txt_mes(self):
    ima = 'compare'
    put = CMS.load_tmp_path(ima)
    put = CQT.f_dialog_name(self, 'Выбрать файл трудозатрат ', put, '*Trudozatrati*.txt', True)
    if put == '.':
        return
    CMS.save_tmp_path(ima, put, True)
    self.compare_mes_putf = put
    self.ui.lbl_txt_mes.setText(self.compare_mes_putf.split("\\")[-1])
    return put

def load_txt(self):
    ima= 'compare'
    put = CMS.load_tmp_path(ima)
    put = CQT.f_dialog_name(self,'Выбрать файл ЕРП ',put,'*erp*.txt',True)
    if put == '.':
        return
    CMS.save_tmp_path(ima,put,True)
    self.compare_erp_putf = put
    self.ui.lbl_txt_erp.setText(self.compare_erp_putf.split("\\")[-1])
    return put

def anal_start(self):
    current_py = CQT.value_of_selection_row_by_column_c(self.ui.tbl_anal_mk,"Номер_заказа")
    if current_py == False:
        CQT.msgbox(f'Не выбран заказ')
        return
    try:
        self.compare_erp_putf
        self.compare_mes_putf
    except:
        CQT.msgbox(f'Не выбраны файлы для сравнения')
        return
    list_of_users = F.open_file_c(self.compare_erp_putf, separ='\t', utf8=True)
    # F.open_file_c(r'O:\Журналы и графики\Ведомости для передачи\Trudozatrati.txt',separ="|")
    p = 1
    date_et = ''
    dict_1 = dict()
    date_min = F.strtodate(F.now())
    date_max = F.strtodate(F.now())
    for item in list_of_users:
        if len(item) == 6:
            if F.is_date(item[0], '%d.%m.%Y %H:%M:%S'):
                date_et = F.strtodate(item[0], '%d.%m.%Y %H:%M:%S')
                if date_et < date_min:
                    date_min = date_et
                if date_et > date_max:
                    date_max = date_et
            else:
                if " (Пауэрз)" in item[0] and item[3] != '':
                    etap = item[0].replace(" (Пауэрз)", '')
                    py = item[3].split('Заказ на производство ')[-1].split(' от ')[0]
                    if py == current_py:
                        if py not in dict_1:
                            dict_1[py] = dict()
                        if date_et not in dict_1[py]:
                            dict_1[py][date_et] = dict()
                        if etap not in dict_1[py][date_et]:
                            dict_1[py][date_et][etap] = dict()
                        if fio not in dict_1[py][date_et][etap]:
                            dict_1[py][date_et][etap][fio] = dict()
                        if 'erp' not in dict_1[py][date_et][etap][fio]:
                            dict_1[py][date_et][etap][fio]['erp'] = 0
                        dict_1[py][date_et][etap][fio]['erp'] += F.valm(item[4])
                else:
                    fio = item[0]

    data_nach = F.datetostr(date_min)
    data_kon = F.datetostr(date_max)
    #list_of_users = F.load_file(r'O:\Журналы и графики\Ведомости для передачи\Trudozatrati_test.txt', sep='|', )
    list_of_users = F.open_file_c(self.compare_mes_putf,separ="|")
    di_userss = dict()

    for item in list_of_users:
        if item[7] != 'Начат' and F.strtodate(item[0]) >= date_min and F.strtodate(item[0]) <= date_max:
            fio = ' '.join(item[3].split()[:3])
            py = item[4].split('$')[1]
            date_et = F.strtodate(item[0])
            etap = item[5]
            if py == current_py:
                if py not in dict_1:
                    dict_1[py] = dict()
                if date_et not in dict_1[py]:
                    dict_1[py][date_et] = dict()
                if etap not in dict_1[py][date_et]:
                    dict_1[py][date_et][etap] = dict()
                if fio not in dict_1[py][date_et][etap]:
                    dict_1[py][date_et][etap][fio] = dict()
                if 'mes' not in dict_1[py][date_et][etap][fio]:
                    dict_1[py][date_et][etap][fio]['mes'] = 0
                dict_1[py][date_et][etap][fio]['mes'] += F.valm(item[8])

    list_osh = [["py", "etap", "date_et", "fio", "erp", "mes"]]
    for py in dict_1.keys():
        for date_et in dict_1[py].keys():
            for etap in dict_1[py][date_et].keys():
                for fio in dict_1[py][date_et][etap].keys():
                    if 'erp' not in dict_1[py][date_et][etap][fio]:
                        erp = 0
                    else:
                        erp = dict_1[py][date_et][etap][fio]['erp']
                    if 'mes' not in dict_1[py][date_et][etap][fio]:
                        mes = 0
                    else:
                        mes = dict_1[py][date_et][etap][fio]['mes']
                    if erp != mes:
                        list_osh.append([py, etap, date_et, fio, erp, mes])
    if len(list_osh) == 1:
        itog = [['Результат'],[f'По диапазону от {data_nach} до {data_kon}  Все ОК']]
        CQT.fill_wtabl_old_c(self, itog, self.ui.tbl_anal_rez, separ='', isp_hat_c=True)
        CMS.fill_filtr_c(self, self.ui.tbl_anal_rez_filtr, self.ui.tbl_anal_rez)
    else:
        CQT.fill_wtabl_old_c(self, list_osh, self.ui.tbl_anal_rez, separ='', isp_hat_c=True)
        CMS.fill_filtr_c(self, self.ui.tbl_anal_rez_filtr, self.ui.tbl_anal_rez)

