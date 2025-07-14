

from __future__ import annotations

import project_cust_38.Cust_Functions as F

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow
@CQT.onerror
def apply_select_filtr(self:mywindow):
    cmb = self.ui.pl_cmb_filtrs
    name = cmb.currentText()
    if name == '':
        return
    dict_filtrs = load_pl_user_filtrs(self)
    if name not in dict_filtrs:
        CQT.msgbox(f'Имя не в списке')
        return
    dict_fields = dict_filtrs[name]
    CMS.fill_filtr_c(self,self.ui.tbl_filtr_kal_pl,self.ui.tbl_kal_pl,dict_fields)
    CMS.update_width_filtr(self.ui.tbl_kal_pl,self.ui.tbl_filtr_kal_pl)
    CMS.apply_filtr_c(self,self.ui.tbl_filtr_kal_pl,self.ui.tbl_kal_pl,False)

@CQT.onerror
def load_pl_user_filtrs(*args):
    path_mes_dir = CMS.tmp_dir()
    name_filtr_file = "pl_user_filters.pickle"
    patf = path_mes_dir + F.sep() + name_filtr_file
    if F.existence_file_c(patf):
        dict_filtrs = F.load_file_pickle(patf)
    else:
        dict_filtrs = dict()
    return dict_filtrs

@CQT.onerror
def fill_pl_user_filtrs(self:mywindow):
    dict_filtrs = load_pl_user_filtrs(self)
    self.ui.pl_cmb_filtrs.clear()
    self.ui.pl_cmb_filtrs.addItem('')
    for key in dict_filtrs:
        self.ui.pl_cmb_filtrs.addItem(key)

@CQT.onerror
def add_pl_user_filtrs(self:mywindow):
    tbl_filtr = self.ui.tbl_filtr_kal_pl
    name = self.ui.pl_le_name_new_filtr.text()
    if name == "" or len(name) <= 4:
        CQT.msgbox(f'Имя нового фильтра не достаточной длины')
        return

    dict_fields = dict()
    for j in range(tbl_filtr.columnCount()):
        name_field = tbl_filtr.horizontalHeaderItem(j).text()
        val = tbl_filtr.item(0,j).text()
        dict_fields[name_field]= val
    dict_filtrs = load_pl_user_filtrs(self)
    dict_filtrs[name] = dict_fields
    save_pl_user_filtrs(dict_filtrs)
    fill_pl_user_filtrs(self)
    self.ui.pl_le_name_new_filtr.clear()
    CQT.msgbox(f'Успешно')


@CQT.onerror
def save_pl_user_filtrs(dict_filtr:dict):
    path_mes_dir = CMS.tmp_dir()
    name_filtr_file = "pl_user_filters.pickle"
    patf = path_mes_dir + F.sep() + name_filtr_file
    F.save_file_pickle(patf, dict_filtr)
    return

@CQT.onerror
def del_filt_pl_user_filtrs(self:mywindow):
    cmb = self.ui.pl_cmb_filtrs
    name = cmb.currentText()
    if name == '':
        return
    dict_filtrs  = load_pl_user_filtrs(self)
    if name in dict_filtrs:
        dict_filtrs.pop(name)
        save_pl_user_filtrs(dict_filtrs)
        fill_pl_user_filtrs(self)
