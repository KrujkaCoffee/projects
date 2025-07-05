from __future__ import annotations


import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import copy
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow

@CQT.onerror
def cmb_select_month(self:mywindow):
    tbl = self.ui.tbl_tabeli_person
    if self.ui.cmb_tabeli.currentText() == '':
        CQT.clear_tbl(tbl)
        return
    if self.ui.tabWidget_8.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_8,'Правка персоналии'):
        if not CMS.user_access(self.bd_naryad, 'update_tabel_person', F.user_name(), 'Нет прав'):
            return
        name_tbl_db = F.datetostr(F.strtodate(self.ui.cmb_tabeli.currentText().split(' ')[0], '%d.%m.%Y'), 'mtdz_%Y_%m_%d')
        tpl_cexs = ("Сборочный цех Производства",
            "Цех механической обработки Производства",
            "Заготовительный цех Производства",
            "Цех выпуска готовой продукции Производства",
            "Ремонтный цех Производства",
            )
        data_tabel = CSQ.custom_request_c(self.db_users,
            f"""SELECT * FROM {name_tbl_db} WHERE {name_tbl_db}.ФИО IN 
             (SELECT employee.ФИО || " " || employee.Должность FROM employee WHERE 
              employee.Подразделение IN {tpl_cexs}  and employee.Компания == "{self.place.Имя}" ) or {name_tbl_db}.Пномер IN (1,2);""",rez_dict=True)
        set_editable = set()
        #for key in data_tabel[0].keys():
        #    if 'd_' in key:
        #        set_editable.add(key)

        CQT.fill_wtabl(data_tabel,tbl,set_editeble_col_nomera=set_editable,auto_type=False,ogr_maxshir_kol=400,colorful_edit=False)
        tbl.blockSignals(True)
        for j in range(tbl.columnCount()):
            CQT.set_cell_editable(tbl,0,j,False)
            CQT.set_cell_editable(tbl, 1, j, False)

        for i in range(2,tbl.rowCount()):
            CQT.set_cell_editable(tbl, i, 2, True)

        CMS.fill_filtr_c(self,self.ui.tbl_tabeli_person_filtr,self.ui.tbl_tabeli_person,hidden_scroll=True)
        CMS.update_width_filtr(self.ui.tbl_tabeli_person,self.ui.tbl_tabeli_person_filtr)
        self.ui.tbl_tabeli_person.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_tabeli_person_filtr.horizontalScrollBar().setValue)
        dict_dned = {'1': 'Пн', '2': 'Вт', '3': 'Ср', '4': 'Чт', '5': 'Пт', '6': 'Сб', '7': 'Вс'}
        for j in range(3, tbl.columnCount()):
            if tbl.item(0, j).text() == '1':
                tbl.item(0, j).setText('Вых')
            else:
                tbl.item(0, j).setText('')
            tbl.item(1, j).setText(dict_dned[tbl.item(1, j).text()])
        for j in range(2,tbl.columnCount()):
            if tbl.item(0,j).text() == 'Вых':
                for i in range(tbl.rowCount()):
                    CQT.set_color_wtab_c(tbl,i,j,243,253,253)
            else:
                if j == 2:
                    continue
                for i in range(tbl.rowCount()):
                    if tbl.item(i,j).text() =='0':
                        #CQT.add_color_wtab(tbl,i,j,11,0,0)
                        CQT.set_font_color_wtab_c(tbl,i,j, 120,10,10)
                        CQT.font_cell_size_format(tbl,i,j,italic=True)
                    else:
                        if F.is_numeric(tbl.item(i,j).text()):
                            CQT.font_cell_size_format(tbl,i,j,bold=True,size=12)
        for i in range(0,tbl.rowCount(),2):
            for j in range(tbl.columnCount()):
                CQT.set_color_wtab_c(tbl,i,j,254,243,223)

    tbl.blockSignals(False)
@CQT.onerror
def update_val(self:mywindow, *args):
    def check_cell(self:mywindow):
        if tbl.horizontalHeaderItem(col).text() == 'Примечание':
            return True
        if not F.is_numeric(tbl.item(row, col).text()):
            CQT.msgbox(f'Не число')
            return False
        return True

    tbl = self.ui.tbl_tabeli_person
    row = tbl.currentRow()
    col =tbl.currentColumn()
    p_num = CQT.get_dict_line_form_tbl(tbl)

    name_tbl_db = F.datetostr(F.strtodate(self.ui.cmb_tabeli.currentText().split(' ')[0], '%d.%m.%Y'), 'mtdz_%Y_%m_%d')

    if not check_cell(self):
        old_val = CSQ.custom_request_c(self.db_users,
                                       f"""SELECT * FROM {name_tbl_db} WHERE Пномер 
                                        == {int(p_num['Пномер'])}""",rez_dict=True)
        tbl.item(row,col).setText(
            str(old_val[0][tbl.horizontalHeaderItem(col).text()])
        )
        return

    #if tbl.horizontalHeaderItem(col).text() == 'Примечание':
    list_of_lists = [[F.valm(tbl.item(row,col).text()),int(p_num['Пномер'])]]
    #else:
    #    list_of_lists = [[F.valm(tbl.item(row, col).text(), int(p_num['Пномер'])]]

    CSQ.custom_request_c(self.db_users,f"""UPDATE {name_tbl_db} 
         SET {tbl.horizontalHeaderItem(col).text()} = ? WHERE Пномер = ?;""",
                         list_of_lists_c=list_of_lists)

