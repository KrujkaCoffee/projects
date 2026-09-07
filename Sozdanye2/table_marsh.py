from __future__ import annotations

import copy

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import copy as CPY
import project_cust_38.Cust_Functions as F
import pprint
template_roof = ['Уровень','ДСЕ', 'Количество,шт.','Родитель', 'Материал' ,'id', 'ПКИ']

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Sozdanie import mywindow

class Custom_marshruts():
    puthfile = CMS.tmp_dir() + F.sep() + 'dict_values_filtr_dse.pickle'
    def __init__(self):
        dict_values = dict()
        if F.existence_file_c(Custom_marshruts.puthfile):
            dict_values = F.load_file_pickle(Custom_marshruts.puthfile)
        self.data = dict_values

    def add(self,name:str,new_mar:list):
        self.data[name] = new_mar

    def check_name(self,name:str):
        if name == '' or len(name) < 4:
            return False
        if name in self.data:
            return False
        return True

    def check_mar(self,mar:list):
        if len(mar) == 0:
            return False
        return True

    def save(self):
        F.save_file_pickle(Custom_marshruts.puthfile, self.data)

    def load_list_mar(self):
        list = ['']
        for mar, vals in self.data.items():
            list.append(f"{mar}({'->'.join(vals)})")
        return list

    def delete_mar(self,name):
        if name in self.data:
            self.data.pop(name)


class Tmp_mar():
    def __init__(self):
        self.mar = []

    def add_rc(self,add_list:list):
        for rc in add_list:
            self.mar.append(rc)

    def fill_gui_lbl(self,obj_lbl):
        obj_lbl.setText('->'.join(self.mar))

    def clear_gui_lbl(self, obj_lbl):
        obj_lbl.setText('')

    def del_rc(self):
        self.mar.pop()

@CQT.onerror
def add_rc_custom(self:mywindow, *args):
    if 'tmp_mar' not in self.__dict__:
        self.tmp_mar = Tmp_mar()
    tbl = self.ui.tbl_select_visible_rc
    list_to_add = []
    for i in range(tbl.rowCount()):
        if int(tbl.item(i, 1).text()) == 1:
            list_to_add.append(tbl.item(i, 0).text())
    self.tmp_mar.add_rc(list_to_add)
    self.tmp_mar.fill_gui_lbl(self.ui.lbl_add_rc_custom)

@CQT.onerror
def apply_custom_mar(self:mywindow,*args):
    tbl = self.ui.tbl_select_marsh
    if self.ui.cmb_custom_marsh.currentText()=='':
        nf_id = CQT.num_col_by_name_c(tbl,'id')
        self.ui.tbl_select_marsh_filtr.item(0,nf_id).setText('')
        CMS.apply_filtr_c(self,self.ui.tbl_select_marsh_filtr,self.ui.tbl_select_marsh)
        apply_filtr_on_tbl_filtr_dse(self, '')
        return

    current_mar = self.ui.cmb_custom_marsh.currentText().split('(')[0]
    if 'c_m' not in self.__dict__:
        self.c_m = Custom_marshruts()
    list_rc = self.c_m.data[current_mar]

    tbl_list = CQT.list_from_wtabl_c(tbl,hat_c=True)
    nf_id = F.num_col_by_name_in_hat_c(tbl_list,'id')
    list_filtr_id = []
    fl_poz_start = 0
    for hi, head in enumerate(tbl_list[0]):
        if F.is_numeric(head):
            fl_poz_start = hi
            break

    def is_match_filtr(list_rc,filtr_rc):#tbl_list[0][j],filtr_rc
        fl_match = True
        for il, l in enumerate(list_rc):
            if l == filtr_rc[il] or filtr_rc[il] == "*":
                pass
            else:
                fl_match = False
                break
        return fl_match

    for i in range(1,len(tbl_list)):
        id = tbl_list[i][nf_id]
        fl_poz = copy.copy(fl_poz_start)
        list_filtr_rc_tmp = copy.copy(list_rc)
        for k, filtr_rc in enumerate(list_filtr_rc_tmp):
            fl_add = False
            for j in range(fl_poz, len(tbl_list[0])):
                if tbl_list[i][j] == '':
                    continue
                if is_match_filtr(tbl_list[0][j],filtr_rc):
                    fl_add = True
                    fl_poz = j + 1
                    break
            if not fl_add:
                list_filtr_rc_tmp[k] = None
                break
        if not None in list_filtr_rc_tmp:#is none not add
            list_filtr_id.append(str(id))#add ID view
    text = fr"'{'|'.join(list_filtr_id)}"
    #self.ui.tbl_select_marsh_filtr.item(0,nf_id).setText(text)
    #CMS.apply_filtr_c(self, self.ui.tbl_select_marsh_filtr, self.ui.tbl_select_marsh)
    apply_filtr_on_tbl_filtr_dse(self,text)



@CQT.onerror
def del_rc_custom(self:mywindow, *args):
    if 'tmp_mar' not in self.__dict__:
        self.tmp_mar = Tmp_mar()
    self.tmp_mar.del_rc()
    self.tmp_mar.fill_gui_lbl(self.ui.lbl_add_rc_custom)

@CQT.onerror
def save_custom_list_marsh(self:mywindow, *args):
    if 'tmp_mar' not in self.__dict__:
        CQT.msgbox(f'Не сформирован маршрут')
        return
    self.c_m = Custom_marshruts()
    name = self.ui.le_custom_list_marsh.text()
    if not self.c_m.check_name(name):
        CQT.msgbox(f'Не корректное имя')
        return
    if not self.c_m.check_mar(self.tmp_mar.mar):
        CQT.msgbox(f'Не корректный маршрут')
    self.c_m.add(name,self.tmp_mar.mar)
    self.c_m.save()
    self.__dict__.pop('tmp_mar')
    load_cmb_cust_mar(self)
    self.ui.lbl_add_rc_custom.clear()
    self.ui.le_custom_list_marsh.clear()
    clear_vals_tbl_mar(self)


@CQT.onerror
def clear_vals_tbl_mar(self:mywindow,*args):
    tbl = self.ui.tbl_select_visible_rc
    for i in range(tbl.rowCount()):
        tbl.item(i, 1).setText('0')
        tbl.cellWidget(i,1).setCheckState(0)

@CQT.onerror
def delete_selected_custom_mar(self:mywindow):
    current_text = self.ui.cmb_custom_marsh.currentText().split('(')[0]
    if not CQT.msgboxgYN(f'Удалить маршрут {current_text}?'):
        return
    if 'c_m' not in self.__dict__:
        self.c_m = Custom_marshruts()
    self.c_m.delete_mar(current_text)
    self.c_m.save()
    load_cmb_cust_mar(self)

@CQT.onerror
def load_cmb_cust_mar(self:mywindow, *args):
    if 'c_m' not in self.__dict__:
        self.c_m = Custom_marshruts()
    self.ui.cmb_custom_marsh.clear()
    self.ui.cmb_custom_marsh.addItems(self.c_m.load_list_mar())


@CQT.onerror
def apply_tbl_select_visible_rc(self):
    tbl = self.ui.tbl_select_visible_rc
    dict_values = dict()
    for i in range(tbl.rowCount()):
        dict_values[tbl.item(i, 0).text()] = int(tbl.item(i, 1).text())

    for j in range(self.ui.tbl_select_marsh.columnCount()):
        hedaer = self.ui.tbl_select_marsh.horizontalHeaderItem(j).text()
        if hedaer in dict_values and not dict_values[hedaer]:
            self.ui.tbl_select_marsh.setColumnHidden(j,True)
        else:
            self.ui.tbl_select_marsh.setColumnHidden(j, False)

@CQT.onerror
def fill_filtr_rc(self:mywindow):
    tbl = self.ui.tbl_select_visible_rc
    def select_row_fill_filtr_rc(self:mywindow,checked,row,col):
        if checked:
            self.ui.tbl_select_visible_rc.item(row,col).setText('1')
        else:
            self.ui.tbl_select_visible_rc.item(row, col).setText('0')
    list_vals = []
    for rc,info in self.DICT_RC_FULL.items():
        val = 0
        rc = ''.join([rc[_:_+2] if not rc[_:_+2]=='00' else "**"  for _ in range(0,len(rc),2)])
        list_vals.append([rc,val,info['Имя'],info['Цвет']])
    CQT.fill_wtabl(list_vals,tbl,{},hide_head_column=True,head_column=0,auto_type=False)
    for i in range(tbl.rowCount()):
        r,g,b = tbl.item(i,3).text().split(',')
        CQT.set_color_header_wtab_vertical_c(tbl,i,r,g,b)
        CQT.add_check_box(tbl,i,1,False,bool(int(tbl.item(i,1).text())),select_row_fill_filtr_rc,self)
    tbl.setColumnHidden(3,True)
    self.ui.splitter_6.setSizes([2000,0])


@CQT.onerror
def fill_tbl_select_marsh(self:mywindow, *args):
    if self.ui.cmb_vid_inf_marsh.count() == 0:
        self.ui.cmb_vid_inf_marsh.clear()
        self.ui.cmb_vid_inf_marsh.addItems(['Операция', 'Номер операции', 'Количество', 'РЦ', 'Имя РЦ', 'Время,мин.', 'Операция_время,мин.','Допустимые проф.'])
        self.ui.cmb_vid_inf_marsh.setCurrentText('Количество')

    def create_dict_of_marsh(self):
        spis_dse = CQT.list_from_wtabl_c(self.ui.tbl_dse, hat_c=True, rez_dict=True, only_visible=False)
        dict_dse = dict()

        for i, item in enumerate(spis_dse):
            if self.ui.tbl_dse.isRowHidden(i):
                continue
            name = item['Обозначение'].strip() + " " + item['Наименование'].strip()
            id = item['ID']
            mat = item['Масса/М1,М2,М3']
            oper = item['Операция']
            nom_oper = item['Ном_оп']
            kol_vo = '/'.join([item['Количество,шт.'], item['Освоено,шт.'], item['Закрыто,шт.']])
            rc = item['РЦ']
            rc_name = item['РЦ_имя']
            pki = item['ПКИ']
            level = item['Уровень']
            time = round(F.valm(item['Тпз']) + F.valm(item['Тшт']),2)
            parent = ''
            tmp_lvl = int(level)
            dostup_prof = self.DICT_ETAPI[item['Операция']]
            for j in range(i,len(spis_dse)):
                if tmp_lvl > int(spis_dse[j]['Уровень']):
                    parent = f"{spis_dse[j]['ID']}_{spis_dse[j]['Обозначение'].strip()} {spis_dse[j]['Наименование'].strip()}"
                    break

            if id not in dict_dse:
                dict_dse[id] = {'level':level,'name': name, 'id': id, 'mat': mat, 'kolvo': item['Количество,шт.'], 'pki': pki,
                                'mar': [], 'parent':parent}
            dict_for_rc = {'Операция': oper, 'Номер операции': nom_oper, 'Количество': kol_vo, 'РЦ': rc,
                           'Имя РЦ': rc_name, 'nom_strok': i, 'Время,мин.':time, 'Операция_время,мин.':f'{oper}_{time}','Допустимые проф.':dostup_prof}
            dict_dse[id]['mar'].append(dict_for_rc)
        return dict_dse

    @CQT.onerror
    def oforml_tbl_marsh(self:mywindow, list_of_lists, *args):
        tbl_marsh = self.ui.tbl_select_marsh
        CQT.fill_wtabl(list_of_lists, tbl_marsh, auto_type=False, height_row=20, set_editeble_col_nomera={})
        CMS.fill_filtr_c(self, self.ui.tbl_select_marsh_filtr, self.ui.tbl_select_marsh, '', True)
        CMS.update_width_filtr(self.ui.tbl_select_marsh, self.ui.tbl_select_marsh_filtr)
        # list_marsh = CQT.list_from_wtabl_c(tbl_marsh, hat_c=True)
        # if list_marsh == [[]]:
        #    return
        for j in range(len(template_roof), tbl_marsh.columnCount()):
            rc = tbl_marsh.horizontalHeaderItem(j).text()
            if rc in self.DICT_RC_FULL:
                r, g, b = self.DICT_RC_FULL[rc]['Цвет'].split(',')
                r = int(r)
                g = int(g)
                b = int(b)
                for i in range(tbl_marsh.rowCount()):
                    CQT.set_color_wtab_c(tbl_marsh, i, j, r, g, b,120)

            fl_column_hide = True
            for i in range(tbl_marsh.rowCount()):
                if tbl_marsh.item(i, j).text() != '':
                    kolvo = get_dict_from_tbl_marsh(self,i + 1, j, list_of_lists, 'Количество')
                    kol, osv, zak = kolvo.split('/')
                    color= False
                    if F.valm(osv) != F.valm(kol):
                        fl_column_hide = False
                        color = CMS.Color_tbl(0)
                    if F.valm(zak) == F.valm(kol):
                        color = CMS.Color_tbl(100)
                    if F.valm(osv) == F.valm(kol) and F.valm(zak) != F.valm(kol):
                        color = CMS.Color_tbl(0)
                    if F.valm(osv) == 0:
                        color = CMS.Color_tbl(0)
                    if color:
                        CQT.set_font_color_wtab_c(self.ui.tbl_select_marsh, i, j, color.r, color.g, color.b)

            if fl_column_hide:
                pass
                # self.ui.tbl_select_marsh.setColumnHidden(j,True)
                # CQT.set_color_wtab_c(self.ui.tbl_select_marsh,0,j,169,208,142)

        bold_in_marsh_selected_dse(self)

    self.dict_dse_for_marsh = create_dict_of_marsh(self)

    list_rc = []

    rez = [CPY.deepcopy(template_roof)]
    for dse in self.dict_dse_for_marsh.keys():
        list_rc.append([])
        rez.append([self.dict_dse_for_marsh[dse]['level'],self.dict_dse_for_marsh[dse]['name'], self.dict_dse_for_marsh[dse]['kolvo'],self.dict_dse_for_marsh[dse]['parent'],
                    self.dict_dse_for_marsh[dse]['mat'], self.dict_dse_for_marsh[dse]['id'],
                    self.dict_dse_for_marsh[dse]['pki']])
        for item in self.dict_dse_for_marsh[dse]['mar']:
            rc = item['РЦ']
            list_rc[-1].append(rc)
    #if list_rc == []:
        #CQT.msgbox(f'Ошибка генерации списка РЦ')

    list_rc_new = CMS.route_allocation_c(CPY.deepcopy(list_rc))

    for i in range(len(list_rc_new)):
        for j in range(len(list_rc_new[0])):
            rez[i].append(list_rc_new[i][j])

    body = rez[1:]
    body = sorted(body, key=lambda x: x[0])
    for j in range(len(rez[0]) - 1, 2, -1):
        body = sorted(body, key=lambda x: x[j])
    rez = [rez[0]]
    for item in body:
        rez.append(item)

    for i in range(1, len(rez)):
        for j in range(len(template_roof), len(rez[i])):
            if rez[i][j] != '':
                rez[i][j] = get_dict_from_tbl_marsh(self,i, j, rez, self.ui.cmb_vid_inf_marsh.currentText())

    oforml_tbl_marsh(self, rez)


@CQT.onerror
def get_dict_from_tbl_marsh(self, r, c, list='', key='', *args):
    if list == '':
        list = CQT.list_from_wtabl_c(self.ui.tbl_select_marsh, hat_c=True)
    nk_id = F.num_col_by_name_in_hat_c(list, 'id')
    id = list[r][nk_id]
    num_ceil = 0
    for j in range(len(template_roof), c + 1):
        if list[r][j] != '':
            num_ceil += 1
    if num_ceil == 0:
        return None
    if key == '':
        return self.dict_dse_for_marsh[id]['mar'][num_ceil - 1]
    return self.dict_dse_for_marsh[id]['mar'][num_ceil - 1][key]


@CQT.onerror
def select_dse_po_marsh(self, *args):
    if self.ui.cmb_list_marsh.currentText() == '':
        text = ''
    else:
        text = fr"'{'|'.join([str(_) for _ in self.dict_dse_marh[self.ui.cmb_list_marsh.currentText()]])}"
    apply_filtr_on_tbl_filtr_dse(self,text)


@CQT.onerror
def apply_filtr_on_tbl_filtr_dse(self,text):
    tblf = self.ui.tbl_filtr_dse
    nk_imaop = CQT.num_col_by_name_c(tblf, 'ID')
    tblf.item(0, nk_imaop).setText(text)
    CMS.apply_filtr_c(self, tblf, self.ui.tbl_dse)
    fill_tbl_select_marsh(self)


def bold_in_marsh_selected_dse(self):
    tbl_dse = self.ui.tbl_dse
    list_dse = CQT.list_from_wtabl_c(tbl_dse, hat_c=True)
    nk_check = F.num_col_by_name_in_hat_c(list_dse, 'Чек')
    list_marsh = CQT.list_from_wtabl_c(self.ui.tbl_select_marsh, hat_c=True)
    nk_id = F.num_col_by_name_in_hat_c(list_marsh, 'id')
    for i in range(1, len(list_marsh)):
        # i_id = list_marsh[i][nk_id]
        for j in range(len(template_roof), len(list_marsh[i])):
            if list_marsh[i][j] == '':
                continue
            nom_strok = get_dict_from_tbl_marsh(self,i, j, list=list_marsh, key='nom_strok')
            if nom_strok == None:
                continue
            # nom_strok = self.dict_dse_for_marsh[i_id]['nom_strok']
            if list_dse[nom_strok + 1][nk_check] == '1':
                CQT.font_cell_size_format(self.ui.tbl_select_marsh, i - 1, j,bold=True, underline=True)
            else:
                CQT.font_cell_size_format(self.ui.tbl_select_marsh, i - 1, j,bold=True, underline=False)

def tbl_select_marsh_dblclk(self):
    tbl = self.ui.tbl_select_marsh
    r = tbl.currentRow()
    c = tbl.currentColumn()
    if c < len(template_roof):
        tbl.setToolTip('')
        nk_id = CQT.num_col_by_name_c(tbl, 'id')
        id = tbl.item(r, nk_id).text()
        tbl_dse = self.ui.tbl_dse

        nk_nom_id = CQT.num_col_by_name_c(tbl_dse, 'ID')
        for i in range(tbl_dse.rowCount()):
            if tbl_dse.item(i, nk_nom_id).text() == id:
                CQT.select_cell(tbl_dse, i, 1)
                break
        return
    if tbl.item(r, c).text() == '':
        tbl.setToolTip('')

        return
    nom_oper = get_dict_from_tbl_marsh(self,r + 1, c, key='Номер операции')
    nk_id = CQT.num_col_by_name_c(tbl, 'id')
    id = tbl.item(r, nk_id).text()
    tbl_dse = self.ui.tbl_dse
    nk_nom_oper = CQT.num_col_by_name_c(tbl_dse, 'Ном_оп')
    nk_nom_id = CQT.num_col_by_name_c(tbl_dse, 'ID')
    for i in range(tbl_dse.rowCount()):
        if tbl_dse.item(i, nk_nom_oper).text() == nom_oper and tbl_dse.item(i, nk_nom_id).text() == id:
            self.select_dse(0, i)
            bold_in_marsh_selected_dse(self)
            return

    CQT.msgbox(f'Ошибка')

def tbl_select_marsh_clk(self):
    tbl = self.ui.tbl_select_marsh
    r = tbl.currentRow()
    c = tbl.currentColumn()
    if c < len(template_roof):
        tbl.setToolTip('')
        return
    if tbl.item(r, c).text() == '':
        tbl.setToolTip('')
        return
    txt = get_dict_from_tbl_marsh(self,r + 1, c)
    tbl.setToolTip(pprint.pformat(txt))

