import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
"""Опер
0-Название оп, 1 - отметка документа ... , 2-номер операции, 3-сводный код, 4- рабочий центр код, 5-Оборудование, 6-Тпз, 7 - Тшт, 
8 -Профессия, 9 - КР , 10 - маетриалы (kod$naim$ed$norma{kod$naim$ed$norma), 11 - КОИД , 12 - , 13 - документы($ op), 14- параметрика($), 20 - уровень
"""
dict_nk_oper = {'Операция': 0, 'Раб.центр': 4, 'Оборудование': 5, "Тп.з.": 6, "Тшт.": 7, "Проф.": 8,
                   "N раб.": 9, "КОИД": 11}

def check_uslovie(line,dict_set):
    rez = True
    if len(dict_set) == 0:
        return False
    for key in dict_set.keys():
        if line[dict_nk_oper[key]] != dict_set[key]:
            rez = False
            break
    return rez



def corr_ok(self):
    change_count = 0
    tk_count = 0

    def list_compare(list_dse, put_tk, dict_set, dict_where):
        nonlocal change_count
        nonlocal tk_count

        def primenit_corr(line, dict_where):
            nonlocal change_count
            nonlocal tk_count
            nonlocal fl
            for key in dict_where.keys():
                if line[dict_nk_oper[key]] != dict_where[key]:
                    line[dict_nk_oper[key]] = dict_where[key]
                    change_count += 1
                    if fl == False:
                        tk_count += 1
                        fl = True
            return line

        nk_tk = F.num_col_by_name_in_hat_c(list_dse, 'Номер_техкарты')
        nk_dse = F.num_col_by_name_in_hat_c(list_dse, 'Номенклатурный_номер')
        for dse in list_dse[1:]:
            n_tk = dse[nk_tk]
            n_dse = dse[nk_dse]
            ima = n_tk + '_' + n_dse + ".pickle"
            if F.existence_file_c(put_tk + ima):
                tk = F.open_file_c(put_tk + ima, False, '|', pickl=True, propuski=True)
                fl_change = False
                if len(tk) > 10:
                    fl = False
                    for i in range(11, len(tk)):
                        if tk[i][20] == '1':
                            if check_uslovie(tk[i], dict_where):
                                fl_change = True
                                tk[i] = primenit_corr(tk[i], dict_set)
                        if tk[i][20] == '0':
                            break
                if fl_change:
                    F.write_file_c(put_tk + ima, tk, separ='|', pickl=True)

    list_dse = CQT.list_from_wtabl_c(self.ui.tbl_corr_select, hat_c=True, only_visible=True)
    list_mk = self.ui.le_corr_list_mk.text().strip().split(',')
    dict_set = {pole:val for pole, val in CQT.list_from_wtabl_c(self.ui.tbl_corr_set,hat_c=False) if val != '?'}
    dict_where = {pole:val for pole, val in CQT.list_from_wtabl_c(self.ui.tbl_corr_where,hat_c=False) if val != '?'}
    if list_mk == ['']:  # по тк
        put_tk = F.scfg("add_docs") + F.sep()
        list_compare(list_dse,put_tk,dict_set,dict_where)
        vid = 'БД'
    else:#по МК
        try:
            list_mk = [str(int(mk)) for mk in list_mk]
        except:
            CQT.msgbox('Не прочитать список МК')
            return
        for nom_mk in list_mk:
            put_tk = F.scfg('Mk') + F.sep() + nom_mk + F.sep()
            list_compare(list_dse, put_tk,dict_set,dict_where)
        vid = 'МК'
    CQT.msgbox(f'Успешно, по {vid} произведено {change_count} измененений в {tk_count} картах из {len(list_dse)-1} карт')


def load(self):
    list_dse = CQT.list_from_wtabl_c(self.ui.tblw_dse, hat_c=True, only_visible=True)
    CQT.fill_wtabl_old_c(self, list_dse, self.ui.tbl_corr_select, separ='', isp_hat_c=True)
    dict_plane_oper = {'Операция': '?', 'Раб.центр': '?', 'Оборудование': '?', "Тп.з.": '?', "Тшт.": '?', "Проф.": '?',
                       "N раб.": '?', "КОИД": '?'}
    CQT.fill_wtabl_old_c(self, F.dict_to_list(dict_plane_oper), self.ui.tbl_corr_set, set_editeble_col_nomera={1}, separ='',
                     isp_hat_c=False)
    CQT.fill_wtabl_old_c(self, F.dict_to_list(dict_plane_oper), self.ui.tbl_corr_where, set_editeble_col_nomera={1},
                     separ='', isp_hat_c=False)



