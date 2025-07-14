from __future__ import annotations

import pprint

import project_cust_38.Cust_google_sheets_gspread as GS
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow

@CQT.onerror
def load_tbl(self:mywindow):
    query = f"""SELECT * FROM inv_proj"""
    list_proj = CSQ.custom_request_c(self.Data_plan.db_invest,query)
    CQT.fill_wtabl(list_proj,self.ui.tbl_invest)
    return

@CQT.onerror
def load_tbl_add(self:mywindow):
    query = f"""SELECT * FROM inv_proj Limit 1"""
    list_proj = CSQ.custom_request_c(self.Data_plan.db_invest,query)
    for j in range(len(list_proj[0])):
        list_proj[-1][j] = ''
    CQT.fill_wtabl(list_proj,self.ui.tbl_invest_add)
    return
