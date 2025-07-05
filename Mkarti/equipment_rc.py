from __future__ import annotations

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from PyQt5.QtCore import QDate
from PyQt5 import   QtGui, QtCore ,QtWidgets

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow
@CQT.onerror
def load_equipment(self:mywindow,*args):
    tbl = self.ui.tbl_equipment
    tblf = self.ui.tbl_equipment_filtr
    dict_eq = CSQ.custom_request_c(self.db_users,f"""SELECT * FROM equipment""",rez_dict=True)
    exclude_fields = ('Пномер')
    set_editable_fields = {_ for _ in dict_eq[0].keys() if _ not in exclude_fields}
    CQT.fill_wtabl(dict_eq,tbl,set_editable_fields,400,auto_type=False)
    CMS.fill_filtr_c(self,tblf,tbl,hidden_scroll=True)
    tbl.horizontalScrollBar().valueChanged.connect(
        tblf.horizontalScrollBar().setValue)
    CMS.update_width_filtr(tbl,tblf)
    pass
@CQT.onerror
def tbl_eq_change_cell(self:mywindow, *args):
    tbl = self.ui.tbl_equipment
   # _,row,column = args
    column = tbl.currentColumn()
    row = tbl.currentRow()
    name_f = tbl.horizontalHeaderItem(column).text()
    snum = int(tbl.item(row,CQT.num_col_by_name_c(tbl,'Пномер')).text())
    val = tbl.item(row,column).text()
    CSQ.custom_request_c(self.db_users,f"""UPDATE equipment SET {name_f} = ? WHERE Пномер = ?;""",
                         list_of_lists_c=[val,snum])

@CQT.onerror
def tbl_eq_add_new_row(self:mywindow,*args):
    CSQ.custom_request_c(self.db_users,f"""INSERT INTO equipment (Инв_номер) VALUES("");""",
                         )
    load_equipment(self)