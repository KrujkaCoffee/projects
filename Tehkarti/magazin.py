from __future__ import annotations
from typing import TYPE_CHECKING
import copy
import re

from PyQt5 import QtWidgets

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
if TYPE_CHECKING:
    from TehKart import mywindow
#+++20.06.25 ( по задаче 100055627 )
class PreviewMaterials:
    INDEX_OPERATION_NAME = 0
    INDEX_OPERATION_NUM = 2
    INDEX_MATERIAL = 10

    MATERIAL_ROW_SEPARATOR = '{'
    MATERIAL_VALUE_SEPARATOR = '$'

    def __init__(self, window: QtWidgets.QMainWindow, list_tk: list[list[str]]):
        self.window = window
        self.list_operations = list_tk

    def prepare_data_for_user_changes(self):
        data = []
        for idx, item in enumerate(self.list_operations):
            if len(item) > 9:
                mats = item[10].split('{')
                for mat_idx, mat in enumerate(mats):
                    if mat and len(mat.split(self.MATERIAL_VALUE_SEPARATOR)) == 4:
                        code_erp, mat_name, mat_ed, mat_norma = mat.split(self.MATERIAL_VALUE_SEPARATOR)
                        data.append(
                            {'Row': idx,
                             'Col': mat_idx,
                             'Чек': '1',
                             'Операция': item[self.INDEX_OPERATION_NAME],
                             'Номер': item[self.INDEX_OPERATION_NUM],
                             'Code': code_erp,
                             'Наименование материала': mat_name,
                             'Единица измерения материала': mat_ed,
                             'Норма материала': mat_norma
                             })
        return data

    def check_box(self, tbl: QtWidgets.QTableWidget, check: bool, row: int, col: int, *args):
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        if nk_check is None:
            return
        state = '1' if check else ''
        tbl.item(row, nk_check).setText(state)

    def oform_preview_mats_tbl(self, tbl: QtWidgets.QTableWidget):
        nk_row = CQT.num_col_by_name_c(tbl, 'Row')
        nk_col = CQT.num_col_by_name_c(tbl, 'Col')
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        if nk_row is not None:
            tbl.setColumnHidden(nk_row, True)
        if nk_col is not None:
            tbl.setColumnHidden(nk_col, True)
        if nk_check is None:
            return
        for row in range(tbl.rowCount()):
            CQT.add_check_box(tbl, row, nk_check, conn_func_checked_row_col=self.check_box, self=tbl, val=True)

    def get_tk_without_mats(self):
        new_data = []
        for item in self.list_operations:
            cp_oper = copy.deepcopy(item)
            cp_oper[self.INDEX_MATERIAL] = ''
            new_data.append(cp_oper)
        return new_data

    def get_tk_with_user_changes(self, changes: list[dict]):
        cp_tk = copy.deepcopy(self.list_operations)
        for item in changes:
            row_idx = int(item['Row'])
            col_idx = int(item['Col'])
            if item['Чек'] == '':
                split_mats = cp_tk[row_idx][self.INDEX_MATERIAL].split(self.MATERIAL_ROW_SEPARATOR)
                split_mats.pop(col_idx)
                cp_tk[row_idx][self.INDEX_MATERIAL] = self.MATERIAL_ROW_SEPARATOR.join(split_mats)
        return cp_tk

    def on_confirm(self, text, data):
        correct_answers = ('да', 'нет')
        error_msg = f'Введен некорректный ответ {text!r} (Принимается да/нет)'
        count_checked_mats = 0
        if not any(answer.lower() == text.lower() in correct_answers for answer in correct_answers):
            return CQT.msgbox(error_msg)
        if text.lower() == 'нет': return True
        for item in data:
            count_checked_mats += int(item['Чек'] == '1')
        if count_checked_mats > 0:
            return True
        if CQT.msgboxgYN('Ни один материал не был выбран. Вы уверены, что хотите закрыть таблицу подбора?'):
            return True
        return False

    def call_preview_table(self):
        data = self.prepare_data_for_user_changes()
        if data == []:
            return self.list_operations
        text, data = CQT.get_answer_dialog_table(self.window, 'Для применения отмеченных материалов \nнапишите Да/Нет в поле ввода',
                                       dict_or_list=data, func_oform_tbl=self.oform_preview_mats_tbl, return_entire=True,
                                                 line_edit_default_value='Нет', on_confirm=self.on_confirm)
        if not isinstance(text, str) or text.lower() != 'да':
            return self.get_tk_without_mats()
        else:
            return self.get_tk_with_user_changes(data)
#---20.06.25 ( по задаче 100055627)

def update_magaz(self):
    nk_teg = CQT.num_col_by_name_c(self.ui.tbl_magaz, 'Теги')
    nk_sort_c = CQT.num_col_by_name_c(self.ui.tbl_magaz, 'Вид')
    nk_block = CQT.num_col_by_name_c(self.ui.tbl_magaz, 'Пномер')
    nom_row = self.ui.tbl_magaz.currentRow()
    pnom = int(self.ui.tbl_magaz.item(nom_row, nk_block).text())
    if self.ui.tbl_magaz.currentColumn() == nk_teg:
        CQT.list_from_wtabl_c(self.ui.tbl_magaz,sep='',hat_c=True)
        CSQ.custom_request_c(self.putf_magaz,
                   f"""UPDATE blocks SET Теги = '{self.ui.tbl_magaz.item(nom_row, nk_teg).text()}' 
                                            WHERE Пномер = {pnom} AND poki = {self.place.poki};""")
    if self.ui.tbl_magaz.currentColumn() == nk_sort_c:
        CSQ.custom_request_c(self.putf_magaz,
                   f"""UPDATE blocks SET Вид = '{self.ui.tbl_magaz.item(nom_row, nk_sort_c).text()}' 
                                                                WHERE Пномер = {pnom} AND poki = {self.place.poki};""")

def magazin_na_del(self):
    tbl = self.ui.tbl_magaz
    rez = CQT.msgboxgYN('Произойдет удаление выбранных галками блоков')
    if rez:
        list_check = []
        list_check_tbl = []
        nk_check = CQT.num_col_by_name_c(tbl, 'Статус')
        nk_nom = CQT.num_col_by_name_c(tbl, 'Пномер')
        for i in range(tbl.rowCount()):
            item = tbl.cellWidget(i, nk_check)
            if item and item.isChecked():
                list_check.append(tbl.item(i, nk_nom).text())
                list_check_tbl.append(i + 1)
        if list_check == []:
            CQT.msgbox('Не выбраны блоки')
            return
        rez = CQT.msgboxgYN(f'Подтверждаешь удаление блоков {list_check_tbl}?')
        if rez:
            conn, cur = CSQ.connect_bd(self.putf_magaz)
            for i in range(len(list_check)):
                custom_request_c = f'''
                    DELETE FROM blocks
                    WHERE Пномер='{list_check[i]}' AND poki = {self.place.poki}; '''
                CSQ.custom_request_c('', custom_request_c, conn)
            CSQ.close_bd(conn)
            load_magaz(self)


def mag_down(self):
    tbl = self.ui.tbl_magaz
    cur_row = tbl.currentRow() + 1
    if cur_row > tbl.rowCount() - 1:
        return
    spis = CQT.list_from_wtabl_c(tbl, hat_c=True)
    spis[cur_row], spis[cur_row + 1] = spis[cur_row + 1], spis[cur_row]
    load_magaz(self,spis)
    tbl.setCurrentCell(cur_row, 2)


def magazin_up(self):
    tbl = self.ui.tbl_magaz
    cur_row = tbl.currentRow() + 1
    if cur_row < 2:
        return
    spis = CQT.list_from_wtabl_c(tbl, hat_c=True)
    spis[cur_row], spis[cur_row - 1] = spis[cur_row - 1], spis[cur_row]
    load_magaz(self,spis)
    tbl.setCurrentCell(cur_row - 2, 2)

@CQT.onerror
def magazin_primenit(self:mywindow,*args):
    len_msg = 45
    tab = '    '
    tbl = self.ui.tbl_magaz
    list_check = []
    nk_check = CQT.num_col_by_name_c(tbl, 'Статус')
    nk_nom = CQT.num_col_by_name_c(tbl, 'Пномер')
    for i in range(tbl.rowCount()):
        if tbl.cellWidget(i, nk_check).isChecked():
            list_check.append(int(tbl.item(i, nk_nom).text()))
    if list_check == []:
        CQT.msgbox('Не выбраны блоки')
        return
    conn, cur = CSQ.connect_bd(self.putf_magaz)

    custom_request_c = f'''
                                SELECT Пномер, Запись FROM blocks
                                WHERE Пномер IN ({CSQ.prepare_list_to_tuple(list_check)}) AND poki = {self.place.poki}; '''
    query = CSQ.custom_request_c('', custom_request_c, conn,rez_dict=True)
    CSQ.close_bd(conn)
    if query:
        query = F.deploy_dict_c(query,'Пномер')
    else:
        return
    spis = []#TODO
    front_spis = []

    for s_num in list_check:
        if s_num in query:
            list_str_data = query[s_num].split('@')
            spis.extend([_.split('|') for _ in list_str_data])
            tk_ = ['' for _ in range(10)]
            tk_.extend(list_str_data)
            tk_obj = CMS.Techkards(tk_, DICT_PROFESSIONS=self.DICT_PROFESSIONS,DICT_OP_NAME=self.DICT_OPERS)
            active_tk = tk_obj.active_tk

            front_spis.append({'Наименование':active_tk.template()})
            for oper in active_tk.opers:
                front_spis.append({'Наименование': oper.template()})
                for mat in oper.materials:
                    front_spis.append({'Наименование': mat.template()})
                for ph in oper.perehs:
                    front_spis.append({ 'Наименование': ph.template()})

    rez = CQT.msgboxg_get_table(self,f'Применить к ТК, блоки?',front_spis,styleSheet=CQT.MES_CSS,yesNoMode=True)
    if rez == False:
        return

    tree = self.ui.tree
    item = tree.currentItem()
    spis_dreva = CQT.list_from_tree_c(tree)
    if item == None:
        cur_str = ''
    else:
        cur_str = self.ui.tree.currentItem().text(3)
    cur_row = -1
    for i in range(len(spis_dreva)):
        if spis_dreva[i][3] == cur_str:
            cur_row = i
            break
    celev_row = len(spis_dreva) - 1
    cur_ur = int(spis[0][20])
    for i in range(cur_row + 1, len(spis_dreva)):
        if int(spis_dreva[i][20]) <= cur_ur:
            celev_row = i - 1
            break
    cur_row = celev_row
    preview_mats = PreviewMaterials(window=self, list_tk=spis)
    user_changes = preview_mats.call_preview_table()
    for i in range(len(user_changes) - 1, -1, -1):
        spis_dreva.insert(cur_row + 1, user_changes[i])
    rez = []
    ur = -1
    for i in range(len(spis_dreva)):
        obr_ur = int(spis_dreva[i][20])
        if obr_ur == ur or obr_ur == ur + 1 or obr_ur < ur:
            rez.append(spis_dreva[i])
            ur = obr_ur
    self.zapoln_tree_spiskom(rez)
    CQT.highlight_tree_values_c(self.ui.tree, 3, cur_str)


def magazin_na_polky(self):
    tree = self.ui.tree
    item = tree.currentItem()
    if item == None:
        return
    obr = item.text(3)
    tmp = []
    spisok = CQT.list_from_tree_c(tree)
    is_approve = bool(re.match(r'^[А-ЯЁ]{3}', self.ui.lineEdit_prover.text()))

    for i in range(0, len(spisok)):
        if obr in spisok[i][3]:
            stroka = [x.replace('|', '-') for x in spisok[i]]
            stroka = [x.replace('@', '-') for x in stroka]
            if not is_approve:
                if stroka[20] == '1' or stroka[20] == '2':
                    # stroka[6] = '*'  # тпз
                    stroka[7] = '*'  # тшт
                # if stroka[20] == '1':  #20.06.25 ( по задаче 100055627 )
                #     stroka[10] = ''  # материал
                stroka[15] = ''  # имя файла прикрепления
                stroka[1] = ''  # отметка ... файла прикрепления

            tmp.append(stroka)
    if not is_approve:
        for i in range(len(tmp)):  # удаление чило дхф
            if tmp[i][20] == '2' and (tmp[i - 1][4] == '010101' or tmp[i - 1][4] == '010100') and 'ЧПУ' in tmp[i - 1][
                0]:
                if 'част' in tmp[i][0].lower() or 'егмент' in tmp[i][0].lower() or 'сектор' in tmp[i][0].lower():
                    tmp[i][0] = 'Сегменты ?'


    for i in range(len(tmp)):
        tmp[i] = '|'.join(tmp[i])
    zapis = '@'.join(tmp)
    #CSQ.add_line_into_db_sql_c(self.putf_magaz, 'blocks', [[0, zapis, '', '']], s_pervoi=False)
    CSQ.custom_request_c(self.putf_magaz,f"""INSERT INTO blocks(Статус,Запись,Вид,Теги,poki) VALUES (?,?,?,?,?)""",list_of_lists_c=[[0, zapis, '', '', self.place.poki]])
    load_magaz(self)
    return


def load_magaz(self, spis=False):
    tab = '    '
    tbl = self.ui.tbl_magaz

    if spis == False:
        custom_request_c = f'''SELECT Пномер, Статус, Запись, Вид, Теги FROM blocks WHERE poki = {self.place.poki}'''
        spis = CSQ.custom_request_c(self.putf_magaz, custom_request_c=custom_request_c,hat_c=True)

    """rez = [spis[0]]

    for i in range(1, len(spis)):
        rez.append([spis[i][nk_pnom], str(spis[i][nk_stat]), spis[i][nk_zapis], spis[i][nk_teg]])"""
    nk_zapis = F.num_col_by_name_in_hat_c(spis, 'Запись')

    nk_pnom = F.num_col_by_name_in_hat_c(spis, 'Пномер')
    nk_stat = F.num_col_by_name_in_hat_c(spis, 'Статус')
    nk_teg = F.num_col_by_name_in_hat_c(spis, 'Теги')
    nk_sort_c = F.num_col_by_name_in_hat_c(spis, 'Вид')
    CQT.fill_wtabl_old_c(self, spis, tbl, set_isp_nomera_col=0, separ='', isp_hat_c=True,
                     set_editeble_col_nomera={nk_teg,nk_sort_c}, ogr_maxshir_kol=500)
    tbl.setColumnWidth(nk_zapis, int(tbl.width() * 0.7))
    tbl.hideColumn(nk_pnom)
    tbl.setColumnWidth(nk_teg, int(tbl.width() * 0.2))
    tbl.setColumnWidth(nk_stat, int(tbl.width() * 0.03))
    visota_stroki = 22
    for i in range(1, len(spis)):
        block = spis[i][nk_zapis].split('@')
        for j in range(len(block)):
            ur = block[j].split('|')[20]
            block[j] = [tab * int(ur) + block[j]]
            # tmp_block.append([tmp_str])
        tbl.setRowHeight(i - 1, visota_stroki)
        CQT.add_table(tbl, i - 1, nk_zapis, block, visota=int(visota_stroki / len(block)),show_verticalHeader=False,show_horizontalHeader=False)
        CQT.add_check_box(tbl, i - 1, nk_stat, conn_func_checked_row_col=click_check, self= self)
        if tbl.item(i - 1, nk_stat).text() == '0':
            tbl.cellWidget(i - 1, nk_stat).setChecked(False)
            CQT.set_color_row_wtab_c(tbl, i - 1, 211, 211, 211)
        else:
            tbl.cellWidget(i - 1, nk_stat).setChecked(True)
            CQT.set_color_row_wtab_c(tbl, i - 1, 255, 255, 255)


def click_check(self, stat, row,col):
    tbl = self.ui.tbl_magaz
    nk_stat = CQT.num_col_by_name_c(tbl, 'Статус')
    if stat:
        tbl.item(row, nk_stat).setText('1')
        CQT.set_color_row_wtab_c(tbl, row, 255, 255, 255)
    else:
        tbl.item(row, nk_stat).setText('0')
        CQT.set_color_row_wtab_c(tbl, row, 211, 211, 211)

def tbl_magaz_click(self):
    tbl = self.ui.tbl_magaz
    nk_stat = CQT.num_col_by_name_c(tbl, 'Статус')
    row = tbl.currentRow()
    if tbl.currentColumn() == nk_stat:
        if tbl.cellWidget(row, tbl.currentColumn()).isChecked():
            tbl.cellWidget(row, tbl.currentColumn()).setChecked(False)
            tbl.item(row, nk_stat).setText('0')
            CQT.set_color_row_wtab_c(tbl, row, 211, 211, 211)
        else:
            tbl.cellWidget(row, tbl.currentColumn()).setChecked(True)
            tbl.item(row, nk_stat).setText('1')
            CQT.set_color_row_wtab_c(tbl, row, 255, 255, 255)
