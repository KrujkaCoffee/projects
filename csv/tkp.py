from __future__ import annotations

import pprint

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_b24 as CB24
from project_cust_38 import Cust_mes as CMS
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csv_tkp import mywindow

if __name__ == '__main__':
    quit()


@CQT.onerror
def btn_status(self: mywindow, NEW_STATUS):
    curr_row = self.ui.tbl_list_tkp.currentRow()
    if curr_row == -1:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_list_tkp, self.Data_mes.DICT_NAME_SQL['tkp']['s_nom'])
    nk_status = CQT.num_col_by_name_c(self.ui.tbl_list_tkp, self.Data_mes.DICT_NAME_SQL['tkp']['status'])
    pnom = int(self.ui.tbl_list_tkp.item(curr_row, nk_pnom).text())

    CSQ.custom_request_c(self.Data_mes.db_dse, f"""UPDATE tkp SET status = "{NEW_STATUS}" WHERE s_nom = {pnom}""")
    self.ui.tbl_list_tkp.item(curr_row, nk_status).setText(NEW_STATUS)
    msg = f'{F.user_full_namre()} изменил статус ТКП№ {pnom} на  {NEW_STATUS}'
    CMS.send_info_mk_b24_by_action(msg, "Разработка ТКП по ВО")
    # msg_to_b24(f'{F.user_full_namre()} изменил статус ТКП№ {pnom} на  {NEW_STATUS}')
    CQT.msgbox(f'Успешно')


@CQT.onerror
def btn_reset(self):
    self.ui.tbl_var.clear()
    self.ui.tbl_var.setRowCount(0)
    self.ui.tbl_dse.blockSignals(False)
    for i in range(self.ui.tbl_dse.rowCount()):
        self.ui.tbl_dse.cellWidget(i, 0).setChecked(False)
    self.ui.tbl_dse.blockSignals(True)


@CQT.onerror
def btn_ok(self: mywindow):
    rez_dict = generate_rez_dict(self)
    if rez_dict == None:
        return

    byte_dict = F.to_binary_pickle(rez_dict)
    now = F.now()
    res_pnom_last = CSQ.last_row_db_c(self.Data_mes.db_dse,'tkp','s_nom',['s_nom'])
    if res_pnom_last == False:
        CQT.msgbox(f'ОШибка обращения к БД')
        return

    nom_tkp = "ТКПП_" + str(res_pnom_last[0]) + '_' + self.ui.le_nnom_izd.text()
    list_vals = [
        now,
        F.user_full_namre(),
        2,
        self.ui.le_name_tkp.text(),
        self.ui.le_nnom_izd.text(),
        nom_tkp,
        byte_dict,
        self.ui.le_path_vo.text(),
        'В работе',
        '',
        '',
        '']
    CSQ.custom_request_c(self.Data_mes.db_dse, f"""INSERT INTO tkp (date_create, 
        user_create, 
        type_tkp, 
        name_tkp, 
        nnom_izd, 
        nnom_tkp, 
        pickle_file, 
        dir_rkd, 
        status, 
        resp_technolog, 
        date_res,
        name_res)
                              VALUES ({('?,' * len(list_vals))[:-1]});""", list_of_lists_c=[list_vals])
    p_nom = CSQ.custom_request_c(self.Data_mes.db_dse,f"""SELECT s_nom FROM tkp WHERE date_create = '{now}'""",hat_c=False,one_column=True)
    msg = f'{F.user_full_namre()} создал структуру параметрику № {p_nom} на {self.ui.le_name_tkp.text()} {self.ui.le_nnom_izd.text()}'
    CMS.send_info_mk_b24_by_action(msg, "Разработка ТКП по ВО")
    # msg_to_b24(f'{F.user_full_namre()} создал структуру параметрику № {p_nom} на {self.ui.le_name_tkp.text()} {self.ui.le_nnom_izd.text()}')
    CQT.msgbox(f'Успешно')

def check_name_tkp(name,nn,path_vo):
    if 'docs://' not in path_vo:
        if len(path_vo) == 0:
            CQT.msgbox(f'Путь ВО не может быть пусто')
            return False
        if not F.existence_file_c(path_vo):
            CQT.msgbox(f'Путь {path_vo} не существует')
            return False
    if name == "":
        CQT.msgbox('Имя ТКП не может быть пусто')
        return False
    if len(name) < 5:
        CQT.msgbox('Имя ТКП не может быть менее 5 символов')
        return False
    if nn == "":
        CQT.msgbox('Номер ТКП не может быть пусто')
        return False
    if len(nn) < 5:
        CQT.msgbox('Номер ТКП не может быть менее 5 символов')
        return False
    return True

@CQT.onerror
def generate_rez_dict(self):
    def check_vars(self: mywindow):
        tbl = self.ui.tbl_var
        for i in range(tbl.rowCount()):
            if tbl.item(i, 3).text() == '':
                CQT.msgbox(f'В значении параметра {tbl.item(i, 0).text()} ошибка')
                return False
            if not F.is_numeric(tbl.item(i, 3).text()):
                CQT.msgbox(f'В значении параметра {tbl.item(i, 0).text()} ошибка, не число')
                return False
        return True

    def check_kol_vo():
        if nk_kolvo == None:
            return False
        for i in range(tbl_dse.rowCount()):
            if tbl_dse.cellWidget(i, 0).isChecked():
                if tbl_dse.item(i, nk_kolvo).text() == "":
                    CQT.msgbox('Кол-во не может быть пусто')
                    return False

                if not F.is_numeric(tbl_dse.item(i, nk_kolvo).text()):
                    CQT.msgbox('Кол-во не может быть не число')
                    return False

                if tbl_dse.item(i, nk_kolvo).text() == '0':
                    CQT.msgbox('Кол-во не может быть 0')
                    return False
        return True


    def check_root():
        list_korn = []
        for i in range(tbl_dse.rowCount()):
            if tbl_dse.cellWidget(i, 0).isChecked():

                if tbl_dse.item(i, nk_root).text() == "1":
                    list_korn.append(tbl_dse.item(i, nk_dse).text())
                    if len(list_korn)>1:
                        CQT.msgbox(f'Не может быть больше 1 корневого ({pprint.pformat(list_korn)})')
                        return False

        if len(list_korn) == 0:
            CQT.msgbox(f'Не выбран корневой узел')
            return False
        return True

    def check_usl(self):
        tbl = self.ui.tbl_var
        for i in range(tbl.rowCount()):
            if tbl.item(i, 2).text() != '' and '-' in tbl.item(i, 2).text():
                list_diap = tbl.item(i, 2).text().split('-')
                if not len(list_diap) == 2:
                    continue
                if F.is_numeric(list_diap[0]) and F.is_numeric(list_diap[1]):
                    if not F.is_numeric(tbl.item(i, 3).text()):
                        CQT.msgbox(f'Параметр {tbl.item(i, 0).text()} должен быть числом')
                        return False
                    if not F.valm(list_diap[0]) <= F.valm(tbl.item(i, 3).text()) <= F.valm(list_diap[1]):
                        CQT.msgbox(f'Параметр {tbl.item(i, 0).text()} должен быть в диапазоне {list_diap[0]}-{list_diap[1]}')
                        return False
        return True

    tbl_dse = self.ui.tbl_dse
    tbl_var = self.ui.tbl_var
    nk_kolvo = CQT.num_col_by_name_c(tbl_dse, 'Кол-во')
    nk_dse = CQT.num_col_by_name_c(tbl_dse, 'Узел')
    nk_check = CQT.num_col_by_name_c(tbl_dse, 'Чек')
    nk_root = CQT.num_col_by_name_c(tbl_dse, 'Корневой')
    if not check_vars(self):
        return
    if not check_name_tkp(self.ui.le_name_tkp.text().strip(),self.ui.le_nnom_izd.text().strip(),self.ui.le_path_vo.text()):
        return
    if not check_kol_vo():
        return
    if not check_root():
        return
    if not check_usl(self):
        return
    dict_rez = {'Структура': dict(), 'Параметры': dict()}

    for i in range(tbl_dse.rowCount()):
        if tbl_dse.cellWidget(i, nk_check).isChecked():
            dse = tbl_dse.item(i, nk_dse).text()
            if tbl_dse.item(i, nk_root).text()== '1':
                dict_rez['Корневой'] = dse
            kol_vo = int(tbl_dse.item(i, nk_kolvo).text())
            dict_rez['Структура'][dse] = kol_vo

    nk_param = CQT.num_col_by_name_c(tbl_var, 'Параметр')
    nk_val_param = CQT.num_col_by_name_c(tbl_var, 'Значение')
    for i in range(tbl_var.rowCount()):
        param = tbl_var.item(i, nk_param).text()
        val_param = tbl_var.item(i, nk_val_param).text()
        dict_rez['Параметры'][param] = val_param

    return dict_rez


@CQT.onerror
def tkp_create_list_var(self, checked, row, col):
    def fill_combo(self:mywindow):
        def apply_combo(self:mywindow, text, row, col):
            self.ui.tbl_var.item(row,col).setText(text)
        tbl = self.ui.tbl_var
        nk_usl = CQT.num_col_by_name_c(tbl,'Условие')
        nk_znach = CQT.num_col_by_name_c(tbl, 'Значение')
        nk_prim = CQT.num_col_by_name_c(tbl, 'Прим.')
        for i in range(tbl.rowCount()):
            if tbl.item(i,nk_usl).text() != '' and ';' in tbl.item(i,nk_usl).text():
                list_usl = tbl.item(i,nk_usl).text().split(';')
                if ';' in tbl.item(i,nk_prim).text():
                    if len(tbl.item(i,nk_prim).text().split(';')) == len(list_usl):
                        list_usl = dict(zip(list_usl,tbl.item(i,nk_prim).text().split(';')))
                CQT.add_combobox(self,tbl,i,nk_znach,list_usl,True,apply_combo)


    tbl_dse = self.ui.tbl_dse
    tbl_var = self.ui.tbl_var
    set_vars = set()
    for i in range(tbl_dse.rowCount()):
        if tbl_dse.cellWidget(i, 0).isChecked():
            dse = tbl_dse.item(i, 1).text()
            set_vars = add_vars(self, dse, set_vars)
    list_var = sorted(list(set_vars))
    list_var.insert(0, ['Параметр', 'Прим.', 'Условие', 'Значение'])
    tbl_var.clear()
    CQT.fill_wtabl(list_var, tbl_var, set_editeble_col_nomera={3}, auto_type=False)
    fill_combo(self)



@CQT.onerror
def tkp_select_root(self:mywindow, checked, row, col):
    tbl_dse = self.ui.tbl_dse
    for i in range(tbl_dse.rowCount()):
        if i != row:
            tbl_dse.cellWidget(i, col).setChecked(False)
            tbl_dse.item(row, col).setText('0')
    tbl_dse.item(row, col).setText(str(int(checked)))

@CQT.onerror
def load_list_params(self):
    db_vo = F.tcfg('BD_vo')
    if not F.existence_file_c(db_vo):
        CQT.msgbox(f'Не найден файл BD_vo')
        quit()
    self.list_param = F.load_file(db_vo)

@CQT.onerror
def add_vars(self, dse, set_vars):
    for i in range(3, len(self.list_param)):
        if dse == self.list_param[i][0]:
            for j in range(1, len(self.list_param[0])):
                if self.list_param[i][j] == '1':
                    set_vars.add((self.list_param[0][j], self.list_param[1][j], self.list_param[2][j], ''))
    return set_vars
