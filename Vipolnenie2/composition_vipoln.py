from __future__ import annotations
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from docxtpl import DocxTemplate
from pathlib import Path
from typing import TYPE_CHECKING
import classes as CLSS
from app_dataclasses import data_app as DTCLS
if TYPE_CHECKING:
    from vipoln import mywindow


def load_user_compositions(list_nars:list[int])->CMS.Compositions:
    return CMS.Compositions(list_nars)

def fill_table_compositions():
    tbl_comp:CQT.QtWidgets.QTableWidget = DTCLS.app_self.ui.tbl_compositions
    comps = DTCLS.user_compositions
    if not (comps.comps):
        tbl_comp.setHidden(True)
        return

    templ = comps.template()
    CQT.fill_wtabl(templ, tbl_comp, styleSheet=CQT.MES_CSS, selectionBehavior="SelectRows", sortingEnabled=True,
                   aliases_header=CMS.Composition.ALIASES)
    t = CQT.TableContext(tbl_comp)
    with CQT.table_updating(tbl_comp):
        if not CFG.Config.user_config.is_developer:
            t.hide_startsunderscore(True)
        CMS.load_column_widths(DTCLS.app_self, tbl_comp)

