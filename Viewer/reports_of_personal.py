from __future__ import annotations
if __name__ == "__main__":
    quit()
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_emoji as CEMOJ
from project_cust_38 import Cust_b24 as CB24
try:
    from dataClass import data_app as DTCLS
except:
    pass

from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from Viewer import mywindow


class Rules():
    def __init__(self):
        self.name = None
        self.id = None
        self.doc_types:Doc_types|None = None
        self.period:Periods|None = None
        self.count_by_period:int|None = None

class Doc_types():
    def __init__(self):
        self.name  = None
        self.id = None
        self.parent:Rules|None =None

class Periods():
    def __init__(self):
        self.name = None
        self.id = None

def load_glsv_reports():
    pass


def load_glsv_rules():
    pass



def fill_cmb_to_select_regime():
    cmb = DTCLS.app_self.ui.cmb_podrazdelenie
    cmb.clear()
    CQT.fill_list_combobx(DTCLS.app_self,cmb,
                          [f'{CEMOJ.EmojiMain.ДокументыДанные.analysis.symbol} Отчет'
                                ,f'{CEMOJ.EmojiMain.ОборудованиеИнструменты.tool.symbol} Настройки'],
                          first_void=True,list_data=['report','settings'])


