from __future__ import annotations

import copy
import pprint
from PyQt5 import QtWidgets
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite  as CSQ
import project_cust_38.Cust_mes as CMS

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Sozdanie import mywindow

dict_status_out = CMS.DICT_STATUS_OUT


@CQT.onerror
def check_words(self: mywindow, row: str, proc=20):
    extra_words = {'?','-',',','.','(',')'}
    words = row.split()
    all_count = len(words)
    if all_count < 2:
        CQT.msgbox('Короткая фраза')
        return False
    list_err = []
    for word in words:
        fix_word = word.lower()
        for item in extra_words:
            fix_word= fix_word.replace(item,'')
        if fix_word not in self.SET_RUS_WORDS and word not in extra_words:
            list_err.append(word)
    if len(list_err) <= 1:
        return True
    if len(list_err) / all_count * 100 > proc:
        CQT.msgbox(f'Нужно уточнить слова {pprint.pformat(list_err)}')
        return False
    return True


@CQT.onerror
def outplan_ok(self:mywindow, *args, **kwargs):
    if "астер" not in self.glob_login and 'ехнолог' not in self.glob_login and 'ачальник' not in self.glob_login:
        CQT.msgbox(f'Нет доступа')
        return

    nom_kpl = self.ui.cmb_outplan.currentText().split(' | ')[4]
    nom_mk = self.ui.cmb_outplan.currentText().split(' | ')[0]
    if not F.is_numeric(nom_kpl):
        CQT.msgbox(f'Не выбрана позиция')
        return
    msg_inic = self.ui.plt_outplan.toPlainText().strip().replace('\n',' ')
    if not check_words(self,msg_inic):
        return

    tbl = self.ui.tbl_outplan
    list_selection_naruad = []
    nf_nnar = CQT.num_col_by_name_c(self.ui.tbl_select_nar,'Пномер')
    for i in range(self.ui.tbl_select_nar.rowCount()):
        if self.ui.tbl_select_nar.item(i,0).text() == '1':
            list_selection_naruad.append(self.ui.tbl_select_nar.item(i,nf_nnar).text())
    str_list_selection_naruad = ';'.join(list_selection_naruad)


    line = [int(nom_mk), F.now(), self.glob_login, msg_inic.lower(), int(nom_kpl), dict_status_out[1],
            str_list_selection_naruad]
    CSQ.custom_request_c(self.db_naryd, f"""INSERT INTO jur_vnepl (МК, Дата, ФИО, Запрос,
                                            Кплан_номер, Статус, Номер_наряда_с_ошибкой)
                                              VALUES ({CSQ.questions_for_mask(line)});""", list_of_lists_c=[line])
    load_form(self)
    CQT.clear_tbl(self.ui.tbl_select_nar)
    print('Успешно')


@CQT.onerror
def start_form(self:mywindow,*args,**kwargs):
    current_mk = str(self.glob_nom_mk)
    self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget,'Внеплан'))
    query = f"""SELECT Пномер FROM plan WHERE МК = {current_mk}"""
    rez = CSQ.custom_request_c(self.db_kplan,query,one_column=True,one=True,hat_c=False)
    if rez== None or rez==False:
        CQT.msgbox(f'Ошибка запроса')
        return
    if rez[0] == '':
        CQT.msgbox(f'МК в плане не найдена')
        return
    rez = rez[0]
    for i in range(self.ui.cmb_outplan.count()):
        tmp_list= self.ui.cmb_outplan.itemText(i).split(' | ')
        if tmp_list[4] == str(rez):
            self.ui.cmb_outplan.setCurrentIndex(i)
            fill_table_nar(self, int(current_mk))
            return
    CQT.msgbox(f'{rez} в плане не обнаружена')
def select_mk(self:mywindow,*args,**kwargs):
    if self.ui.cmb_outplan.currentText() == '':
        return
    current_mk = self.ui.cmb_outplan.currentText().split(" | ")[0]
    if not F.is_numeric(current_mk):
        return
    fill_table_nar(self, int(current_mk))
def check_nar(self,checked,row,col):
    val = ''
    if checked:
        val = '1'
    self.ui.tbl_select_nar.item(row,col).setText(val)
@CQT.onerror
def fill_table_nar(self:mywindow,nom_mk:int):
    CQT.clear_tbl(self.ui.tbl_select_nar)
    list_nar = CSQ.custom_request_c(self.db_naryd, f"""SELECT "" as Чек, Пномер,Примечание,ФИО,ФИО2 
     FROM naryad WHERE Внеплан = 0 and Номер_мк = {nom_mk}""",rez_dict=True)
    tbl = self.ui.tbl_select_nar
    CQT.fill_wtabl(list_nar,tbl,{},auto_type=False)
    for i in range(tbl.rowCount()):
        CQT.add_check_box(tbl,i,0,conn_func_checked_row_col=check_nar,self= self)

@CQT.onerror
def fill_kplan_izd(self:mywindow):
    query = f"""SELECT пл_оуп.№ERP, пл_оуп.№проекта, пл_оуп.Номенклатура_ЕРП, plan.МК, status_poz.Имя, пл_оуп.НомПл FROM plan INNER JOIN
    пл_оуп ON пл_оуп.НомПл = plan.Пномер,
    status_poz ON status_poz.Пномер = plan.Статус WHERE  plan.poki = {self.place.poki} AND plan.Статус IN (3, 7) order by plan.МК ASC;
"""
    rez = CSQ.custom_request_c(self.db_kplan,query,rez_dict=True)

    list_for_cmb = [[str(_['МК']),_['№ERP'],_['№проекта'],_['Номенклатура_ЕРП'],str(_['НомПл'])] for _ in rez]
    list_for_cmb = F.sort_by_column_c(list_for_cmb,0,hat_c=False)
    list_for_cmb = [' | '.join(_) for _ in list_for_cmb]
    self.ui.cmb_outplan.clear()
    self.ui.cmb_outplan.addItem("МК | №ERP | №проекта | Номенклатура_ЕРП | НомПл")
    self.ui.cmb_outplan.addItems(list_for_cmb)

@CQT.onerror
def load_form(self:mywindow):
    fill_kplan_izd(self)
    query = f"""SELECT jur_vnepl.Пномер, 
          
        
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа, 
       
              CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
        
        jur_vnepl.МК, 
        jur_vnepl.Дата, 
        jur_vnepl.ФИО, 
        jur_vnepl.Запрос, 
        jur_vnepl.Номер_наряда_с_ошибкой as Наряд_ошибка,
        jur_vnepl.Номер_внепланового_наряда,
        jur_vnepl.Кплан_номер,
        jur_vnepl.Примечание_цех_техн, 
        пл_топ.Отв_технолог as Ответственный, 
        jur_vnepl.Дата_ответ, 
        jur_vnepl.Журнал_замеч_номер, 
        jur_vnepl.Номер_нов_мк, 
        jur_vnepl.Ответ, 
        jur_vnepl.Статус,
        jur_vnepl.Утверждено
        
        
         FROM jur_vnepl 
          INNER JOIN mk 
          ON mk.Пномер = jur_vnepl.МК 
          
        LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
        LEFT JOIN пл_топ ON пл_топ.НомПл = пл_оуп.НомПл 
        LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
        LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
          WHERE  plan.poki = {self.place.poki} AND mk.Статус = 'Открыта' or mk.Пномер = 0; """

    #list_fio_techn = CSQ.custom_request_c(self.db_kplan,f"""SELECT НомПл, Отв_технолог FROM пл_топ""",rez_dict=True)
    #if list_fio_techn == None or list_fio_techn == False:
    #    CQT.msgbox(f'Ошибка загрузки БД')
    #    return
    #dict_fio = F.deploy_dict_c(list_fio_techn,'НомПл')

    rez = CSQ.custom_request_c(self.db_naryd,query,rez_dict=True,attach_dbs=(self.db_kplan))
    if rez == None or rez == False:
        CQT.msgbox(f'Ошибка загрузки')
        return
    #for i in range(len(rez)):
    #    if rez[i]['Кплан_номер'] in dict_fio:
    #        rez[i]['Ответственный'] = dict_fio[rez[i]['Кплан_номер']]
    set_edit = {'Ответ'}
    if 'ехнолог' in self.glob_login or 'астер' in self.glob_login:
        set_edit.add('Примечание_цех_техн')
    CQT.fill_wtabl(rez,self.ui.tbl_outplan,auto_type=False,set_editeble_col_nomera=set_edit)
    self.ui.tbl_outplan.setColumnWidth(F.num_col_by_name_in_hat_c(rez,'Ответ'),322)
    self.ui.tbl_outplan.setColumnWidth(F.num_col_by_name_in_hat_c(rez,'Статус'), 100)

    CMS.fill_filtr_c(self,self.ui.tbl_outplan_filtr,self.ui.tbl_outplan,hidden_scroll=True)
    CMS.update_width_filtr(self.ui.tbl_outplan,self.ui.tbl_outplan_filtr)
    self.ui.plt_outplan.clear()
    self.ui.tbl_outplan.setSelectionMode(1)
    CQT.set_color_sort_cell_table_c(self.ui.tbl_outplan)

@CQT.onerror
def tbl_outplan_change_cell(self:mywindow, *args):
    tbl = self.ui.tbl_outplan
    row = tbl.currentRow()
    clmn = tbl.currentColumn()
    if row == -1:
        return
    if tbl.horizontalHeaderItem(clmn).text() == 'Примечание_цех_техн':
        snum = int(tbl.item(row, CQT.num_col_by_name_c(tbl, 'Пномер')).text())
        val = tbl.item(row, clmn).text()
        CSQ.custom_request_c(self.db_naryd, f"""UPDATE jur_vnepl SET Примечание_цех_техн = ? WHERE Пномер = ?;""",
                             list_of_lists_c=[val, snum])



@CQT.onerror
def ansver_row(self:mywindow, *args):

    tbl = self.ui.tbl_outplan
    row = tbl.currentRow()
    if row == -1:
        return
    if tbl.cellWidget(row, tbl.currentColumn()) != None:
        return

    dict_row = CQT.list_from_wtabl_c(tbl, '', True, rez_dict=True)[row]

    tmp = [F.now(),dict_row['Ответ'].strip().lower()]
    CSQ.custom_request_c(self.db_naryd, f"""UPDATE jur_vnepl SET  (Дата_ответ, Ответ)
       = ({CSQ.questions_for_mask(tmp)}) WHERE Пномер == {int(dict_row['Пномер'])}""", list_of_lists_c=[tmp])
    load_form(self)
    CQT.msgbox('Успешно')

@CQT.onerror
def confirm_row(self:mywindow, *args):
    def check_row(self: mywindow, dict_row):
        if dict_row['Статус'] == dict_status_out[1]:
            CQT.msgbox(f'Статус не выбран')
            return False
        if dict_row['Статус'] == dict_status_out[4]:
            CQT.msgbox(f'Утвердить подготовку нельзя')
            return False
        return True
    tbl = self.ui.tbl_outplan
    row = tbl.currentRow()
    if row == -1:
        return
    if tbl.cellWidget(row, tbl.currentColumn()) != None:
        return

    dict_row = CQT.list_from_wtabl_c(tbl, '', True, rez_dict=True)[row]
    if not check_row(self, dict_row):
        return

    if not CQT.msgboxgYN(f"Утвердить статус {dict_row['Статус']} в заявке с причиной \n {dict_row['Запрос']}"):
        return
    tmp = [F.now()]
    CSQ.custom_request_c(self.db_naryd, f"""UPDATE jur_vnepl SET  (Утверждено)
       = ({CSQ.questions_for_mask(tmp)}) WHERE Пномер == {int(dict_row['Пномер'])}""", list_of_lists_c=[tmp])
    load_form(self)
    CQT.msgbox('Успешно')


@CQT.onerror
def apply_row_technolog(self:mywindow):
    def check_row(self:mywindow,dict_row):
        if dict_row['Статус'] == dict_status_out[1]:
            CQT.msgbox(f'Статус не выбран')
            return False
        if dict_row['Статус'] == dict_status_out[4]:
            CQT.msgbox(f'Статус Подготовка провести нельзя')
            return False
        if len(dict_row['Ответ'].strip()) <3 or len(dict_row['Ответ'].strip()) > 100:
            CQT.msgbox(f'Поле ответ не заполнено должным образом от 3 до 100 символов')
            return False
        if not check_words(self, dict_row['Ответ']):
            return False
        if dict_row['Статус'] == dict_status_out[2]:#ПРИНЯТО

            if dict_row['Журнал_замеч_номер'] == '0':
                CQT.msgbox(f'Номер журанала замечаний не выбран')
                return False
            if dict_row['Номер_нов_мк'] == '0':
                CQT.msgbox(f'Номер новой МК не выбран')
                return False
        if dict_row['Статус'] == dict_status_out[3]:  # Отклонено

            if dict_row['Журнал_замеч_номер'] != '0':
                CQT.msgbox(f'Номер журанала должен быть 0')
                return False
            if dict_row['Номер_нов_мк'] != '0':
                CQT.msgbox(f'Номер новой МК должнен быть 0')
                return False
        return True

    tbl = self.ui.tbl_outplan
    row = tbl.currentRow()
    if row == -1:
        return
    if tbl.cellWidget(row, tbl.currentColumn()) != None:
        return

    dict_row = CQT.list_from_wtabl_c(tbl, '', True, rez_dict=True)[row]
    if not check_row(self,dict_row):
        return

    if dict_row['Номер_нов_мк'] == '0':
        if CQT.msgboxgYN(f'Не указана новая МК!\n Создаем МК ?'):
           return
    tmp = [dict_row['Статус'],dict_row['Журнал_замеч_номер'],dict_row['Номер_нов_мк']]
    CSQ.custom_request_c(self.db_naryd,f"""UPDATE jur_vnepl SET  (Статус, Журнал_замеч_номер,Номер_нов_мк)
   = ({CSQ.questions_for_mask(tmp)}) WHERE Пномер == {int(dict_row['Пномер'])}""",list_of_lists_c=[tmp])


    if dict_row['Номер_внепланового_наряда'] != '0':
        nar = CMS.Naryads(int(dict_row['Номер_внепланового_наряда']),self.db_naryd)
        nar.set_koef_nar(0.0001)



    load_form(self)
    CQT.msgbox('Успешно')

@CQT.onerror
def tbl_out_select_row(self:mywindow):
    def apply_status_into_cmb(self:mywindow,row):
        for j in range(tbl.columnCount()):
            if tbl.cellWidget(row, j) != None:
                if type(tbl.cellWidget(row, j)) == QtWidgets.QComboBox:
                    val = tbl.item(row,j).text()
                    if val in CQT.list_from_cmb_c(tbl.cellWidget(row, j)):
                        tbl.cellWidget(row, j).setCurrentText(val)


    def select_status(self:mywindow, text, row, col):
        print(text)
        self.ui.tbl_outplan.item(row,col).setText(text)

        key = F.dict_key_from_value(dict_status_out,text)
        if key == 4:
            tmp = [text]
            dict_row = CQT.get_dict_line_form_tbl(self.ui.tbl_outplan,row)
            CSQ.custom_request_c(self.db_naryd, f"""UPDATE jur_vnepl SET  (Статус)
            = ({CSQ.questions_for_mask(tmp)}) WHERE Пномер == {int(dict_row['Пномер'])}""", list_of_lists_c=[tmp])
        if key in (2,3):
            tbl.removeCellWidget(row, col)
        pass


    def select_nom_j_zam(self:mywindow, text, row, col):
        print(text)
        self.ui.tbl_outplan.item(row, col).setText(text)
        tbl.removeCellWidget(row, col)
        pass

    def select_nom_mk(self:mywindow, text, row, col):
        self.ui.tbl_outplan.item(row, col).setText(text)
        tbl.removeCellWidget(row, col)
        print(text)
        pass


    tbl = self.ui.tbl_outplan
    row = tbl.currentRow()
    if row == -1:
        return
    if tbl.cellWidget(row,tbl.currentColumn()) != None:
        return
    dict_row = CQT.list_from_wtabl_c(tbl,'',True,rez_dict=True)[row]

    for i in range(tbl.rowCount()):
        for j in range(tbl.columnCount()):
            if tbl.cellWidget(i,j) != None:
                tbl.cellWidget(i,j).clear()
                tbl.removeCellWidget(i,j)


    if dict_row['МК'] == "0":
        self.ui.plt_outplan.setPlainText(dict_row['Запрос'])
        return

    if not self.outplan_edit_acces and dict_row['Ответственный'] != self.glob_ima:
        return
    nf = CQT.num_col_by_name_c(tbl, 'Статус')
    if dict_row['Статус'] == dict_status_out[1]:
        CQT.add_combobox(self,tbl,row,nf,[dict_status_out[_] for _ in dict_status_out.keys()],False,select_status)
    if dict_row['Статус'] == dict_status_out[4]:
        CQT.add_combobox(self,tbl,row,nf,[dict_status_out[_] for _ in dict_status_out.keys() if _ in (2,3,4)],False,select_status)
    if dict_row['Журнал_замеч_номер'] == '0':
        nom_mk = int(dict_row['МК'])
        list_zam = CSQ.custom_request_c(self.db_naryd,f"""SELECT Пномер, Содержание FROM zamech WHERE МК = {nom_mk}""",hat_c=True,rez_dict=True)
        list_zam = F.deploy_dict_c(list_zam, 'Пномер')
        nf = CQT.num_col_by_name_c(tbl,'Журнал_замеч_номер')
        result_dict_zam = dict()
        for k in list_zam.keys():
            result_dict_zam[str(k)] = list_zam[k]
        CQT.add_combobox(self,tbl,row,nf,result_dict_zam,False,select_nom_j_zam)
    if dict_row['Номер_нов_мк'] == '':#!!!!!!!!!!!!!!!!!!!! Доработать для фильтра на мастера
        nom_kpl = int(dict_row['Кплан_номер'])
        list_mk = CSQ.custom_request_c(self.db_naryd,f"""SELECT Пномер, Номенклатура FROM mk WHERE НомКплан = {nom_kpl} and Тип in (2,5)""",hat_c=True,rez_dict=True)
        list_mk = F.deploy_dict_c(list_mk,'Пномер')
        list_used = CSQ.custom_request_c(self.db_naryd, f"""SELECT Номер_нов_мк FROM jur_vnepl""",
                                       hat_c=False)
        result_dict_mk = dict()
        for k in list_mk.keys():
            if not k in list_used:
                result_dict_mk[str(k)] = list_mk[k]

        nf = CQT.num_col_by_name_c(tbl,'Номер_нов_мк')
        CQT.add_combobox(self,tbl,row,nf,result_dict_mk,True,select_nom_mk)
    CQT.clear_tbl(self.ui.tbl_outplan_naruad)
    if dict_row['Наряд_ошибка'] != '' :
        summ_params = []
        for nar_nom in dict_row['Наряд_ошибка'].split(";"):
            nar = CMS.Naryads(int(nar_nom),self.db_naryd)
            for param in nar.params:
                param['Наряд'] = nar_nom
                summ_params.append(param)
        CQT.fill_wtabl(summ_params,self.ui.tbl_outplan_naruad,{},auto_type=False)
        CMS.fill_filtr_c(self,self.ui.tbl_outplan_naruad_filtr,self.ui.tbl_outplan_naruad)
        CMS.update_width_filtr(self.ui.tbl_outplan_naruad,self.ui.tbl_outplan_naruad_filtr)
    apply_status_into_cmb(self,row)