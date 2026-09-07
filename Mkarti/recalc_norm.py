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
def show_fr(self:mywindow,*args):
    if self.ui.fr_recacl_norm.isVisible():
        self.ui.fr_recacl_norm.setVisible(False)
    else:
        self.ui.fr_recacl_norm.setVisible(True)
        load_opers(self)

@CQT.onerror
def load_opers(self:mywindow,*args):
    def apply_check(self:mywindow ,checked,row,col):
        if checked:
            self.ui.tbl_recalc_norm.item(row,col).setText('1')
        else:
            self.ui.tbl_recalc_norm.item(row, col).setText('')

    tbl = self.ui.tbl_recalc_norm
    list_rez = [['kod','name','Tpz','Check']]
    for oper in self.DICT_OP.values():
        list_rez.append([oper['kod'],oper['name'],oper['Tpz'],''])
    CQT.fill_wtabl(list_rez,tbl,{3},auto_type=False)
    for i in range(tbl.rowCount()):
        CQT.add_check_box(tbl,i,3,val=False,conn_func_checked_row_col= apply_check,self=self)

@CQT.onerror
def recalc_opers_norm(self:mywindow,*args):
    #if self.ui.le_recalc_norm.text()=='':
    #    CQT.msgbox(f'Не выбрана дата')
    #    return
    #if not F.is_date(self.ui.le_recalc_norm.text(),"%y-%m-%d"):
    #    CQT.msgbox(f'Не тот формат дата')
    #    return
    #DICT_DSE = CMS.load_dict_dse(self.db_dse)
    dict_recalc_opers = dict()
    tbl = self.ui.tbl_recalc_norm
    for i in range(tbl.rowCount()):
        if tbl.item(i,CQT.num_col_by_name_c(tbl,'Check')).text() == '1':
            dict_recalc_opers[tbl.item(i,CQT.num_col_by_name_c(tbl,'name')).text()] =\
                self.DICT_OP[tbl.item(i,CQT.num_col_by_name_c(tbl,'kod')).text()]


    #data_le = self.ui.le_recalc_norm.text()




    #list_mk = CSQ.custom_request_c(self.bd_naryad,f"""SELECT Пномер, Статус FROM mk WHERE date("20" || mk.Дата) >= date("20" || "{data_le}");""",rez_dict=True)
    #list_mk = CSQ.custom_request_c(self.bd_naryad,
    #                               f"""SELECT Пномер, Статус FROM mk WHERE Пномер = 2323;""",
    #                               rez_dict=True)
    list_mk = CQT.list_from_wtabl_c(self.ui.table_spis_MK, '', True, True, True, True, False)
    list_opers = [_ for _ in dict_recalc_opers.keys()]
    self.DICT_OPERS = F.deploy_dict_c(
        CSQ.custom_request_c(self.bd_naryad , f"""SELECT * FROM operacii""", rez_dict=True), 'name')
    for item_mk in list_mk:
        mk = CMS.Marshrut_cards(item_mk['Пномер'],db_mk=self.bd_naryad,db_resxml=self.db_resxml)
        #mk = CMS.Marshrut_cards(3522,self.db_naryad,self.db_resxml,True)
        mk.update_norm_time(list_opers,self.db_dse,self.DICT_OPERS)
        mk.update_naryads(self.DICT_OPERS)



