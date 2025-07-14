from __future__ import annotations

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QStyle
from form_1 import Ui_Form_first

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Functions as F
from project_cust_38 import Cust_config as CFG
from copy import deepcopy
import project_cust_38.operacii as operacii

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow




class mywindow2(QtWidgets.QDialog):  # диалоговое окно
    def __init__(self, parent):
        self.myparent = parent
        super(mywindow2, self).__init__()
        self.ui2 = Ui_Form_first()
        self.ui2.setupUi(self)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle("Заголовок")
        self.ui2.tbtn_max.clicked.connect(self.full_screen)
        self.ui2.tbtn_min.clicked.connect(self.minized)
        self.ui2.tbtn_exit.clicked.connect(self.exit_form)
        self.ui2.btn_calc.clicked.connect(self.calc_var_from_gvar)
        self.ui2.btn_ok.clicked.connect(self.create_mk)
        self.ui2.tbl_var_tk.clicked.connect(self.take_name_column_tk)
        self.ui2.tbl_var_tk_mat.clicked.connect(self.take_name_column_tk)
        self.ui2.tbl_var_vo.clicked.connect(self.take_name_column_vo)
        self.ui2.btn_reload_glob_vars.clicked.connect(self.load_glob_vars)

        self.load_parametrs_vo()
        self.app_icons()
        self.showMaximized()
        self.dragPos = QtCore.QPoint()
        CQT.load_css(self)
        CQT.load_icons(self,24)

        self.load_glob_vars_csv()
        list_funcs = ['',
         'nomen(толщина,код_кам,вид (0-плотоность 1- НН), номер элемента)',
         'tblv(pole,kod)',
                'tblm(kod)',
                      'arr(строка,коллонка,[["масс","сив"],[1,2]])',
                      'cam_to_mat(Код кам)']
        self.ui2.cmb_tkp_funcs.addItems(list_funcs)
        self.ui2.cmb_tkp_funcs.activated[str].connect(self.cmb_select_func)

    # вызывается при нажатии кнопки мыши по форме
    @CQT.onerror
    def mousePressEvent(self, event):
        # Если нажата левая кнопка мыши
        if event.button() == QtCore.Qt.LeftButton:
            # получаем координаты окна относительно экрана
            x_main = self.geometry().x()
            y_main = self.geometry().y()
            # получаем координаты курсора относительно окна нашей программы
            cursor_x = QtGui.QCursor.pos().x()
            cursor_y = QtGui.QCursor.pos().y()
            # проверяем условием позицию курсора на нужной области программы(у нас это верхний бар)
            # если всё ок - перемещаем
            # иначе игнорируем
            if x_main <= cursor_x <= x_main + self.geometry().width():
                if y_main <= cursor_y <= y_main + self.ui2.line.geometry().y():
                    self.old_pos = event.pos()
                else:
                    self.old_pos = None
        elif event.button() == QtCore.Qt.RightButton:
            self.old_pos = None

    # вызывается при отпускании кнопки мыши
    @CQT.onerror
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.old_pos = None

    # вызывается всякий раз, когда мышь перемещается
    @CQT.onerror
    def mouseMoveEvent(self, event):
        if 'old_pos' not in self.__dict__ :
            return
        if not self.old_pos:
            return
        delta = event.pos() - self.old_pos
        self.move(self.pos() + delta)


    def cmb_select_func(self):
        F.copy_bufer(self.ui2.cmb_tkp_funcs.currentText())
        CQT.msgbox(f'Скопировано в буфер',time_life=0.8)

    def take_name_column_tk(self):
        modifiers = CQT.get_key_modifiers(self)
        if modifiers == ['alt']:
            if self.ui2.tbl_var_tk.hasFocus():
                pole = self.ui2.tbl_var_tk.horizontalHeaderItem(self.ui2.tbl_var_tk.currentColumn()).text()
                kod = self.ui2.tbl_var_tk.item(self.ui2.tbl_var_tk.currentRow(),CQT.num_col_by_name_c(self.ui2.tbl_var_tk,'Код')).text()
                F.copy_bufer(f'{{tblv("{pole}","{kod}")}}')
            if self.ui2.tbl_var_tk_mat.hasFocus():
                kod = self.ui2.tbl_var_tk_mat.item(self.ui2.tbl_var_tk_mat.currentRow(),CQT.num_col_by_name_c(self.ui2.tbl_var_tk_mat,'Код')).text()
                F.copy_bufer(f'{{tblm("{kod}")}}')
        if self.ui2.tbl_var_tk.hasFocus():
            self.ui2.lbl_glob_var.setText(str(self.glob_dict_from_tk[CQT.value_of_selection_row_by_column_c(self.ui2.tbl_var_tk,'ДСЕ')]))
        if self.ui2.tbl_var_tk_mat.hasFocus():
            self.ui2.lbl_glob_var.setText(str(self.glob_dict_from_tk[CQT.value_of_selection_row_by_column_c(self.ui2.tbl_var_tk_mat,'ДСЕ')]))


    def take_name_column_vo(self):
        modifiers = CQT.get_key_modifiers(self)
        if modifiers == ['alt']:
            F.copy_bufer(self.ui2.tbl_var_vo.horizontalHeaderItem(self.ui2.tbl_var_vo.currentColumn()).text())

    def create_mk(self):
        list_vars_vo =CQT.list_from_wtabl_c(self.ui2.tbl_rez_tk, hat_c=True)
        list_mat_vo = CQT.list_from_wtabl_c(self.ui2.tbl_rez_tk_mat, hat_c=True)
        dict_mat_vo = F.list_to_dict(list_mat_vo)
        if list_vars_vo == [[]] or list_mat_vo == [[]]:
            return
        for row in list_vars_vo:
            for item in row:
                if item == 'ERR':
                    CQT.msgbox(f'Ошибки в результатах')
                    return
        dict_mat = dict()
        for item in dict_mat_vo:
            if item['Норма'] == 0:
                continue
            key = f"{item['ДСЕ']}${item['Код']}"
            val ='$'.join([item['НН'],item['Материал'],item['Ед.Изм'],'{:.8f}'.format(round(F.valm(item['Норма']), 8))])
            if key in dict_mat:
                dict_mat[key].append(val)
            else:
                dict_mat[key] = [val]
        for key in dict_mat.keys():
            dict_mat[key] = '{'.join(dict_mat[key])
        self.myparent.list_vars_vo = list_vars_vo
        self.myparent.dict_mat_vo = dict_mat
        self.hide()

    def check_insert_gvars(self,gvars):
        for item in list(gvars.values()):
            if item == '':
                return False
            if F.is_numeric(item)== False:
                return False
        return True

    def tblv(self,var_name, kod = ''):
        if kod == '':
            kod = self.current_calc_kod
        list = CQT.list_from_wtabl_c(self.ui2.tbl_var_tk,hat_c=True,rez_dict=True)
        for item in list:
            if item['Код'] == kod:
                if var_name in item:
                    tmp = item[var_name]
                    tmp = str(self.cust_eval(tmp, 4))
                    tmp = self.apply_vars(tmp, self.dict_form_tk, self.list_gvars)
                    return self.cust_eval(tmp,4)
        return

    def tblm(self,kod):
        list = CQT.list_from_wtabl_c(self.ui2.tbl_var_tk_mat,hat_c=True,rez_dict=True)
        for item in list:
            if item['Код'] == kod:
                tmp = item['Норма']
                tmp = str(self.cust_eval(tmp, 4))
                tmp = self.apply_vars(tmp, self.dict_form_tk, self.list_gvars)
                return self.cust_eval(tmp,4)
        return

    def arr(self,rval,cval,arr):
        try:
            arr = eval(arr)
        except:
            pass
        if type(arr[1][0]) == type(1):
            row = len(arr)-1
            for i in range(1,len(arr)):
                if arr[i][0] >= rval:
                    row = i
                    break
        else:
            row = len(arr) - 1
            for i in range(1,len(arr)):
                if arr[i][0] == rval:
                    row = i
                    break
        if type(arr[0][1]) == type(1):
            col = len(arr[0])-1
            for j in range(1,len(arr[i])):
                if arr[0][j] >= cval:
                    col = j
                    break
        else:
            col = len(arr[0]) - 1
            for j in range(1,len(arr[i])):
                if arr[0][j] == cval:
                    col = j
                    break
        return arr[row][col]


    def nomen(self,tolsh,cam_cod,rez:int = 0,selection_num=0):
        if rez == 0: #pl
            list_nomen = [str(F.valm(self.myparent.DICT_NOMEN[k]['П4'])) for k in self.myparent.DICT_NOMEN.keys() if
                          self.myparent.DICT_NOMEN[k]['П6'] == str(cam_cod) and F.valm(self.myparent.DICT_NOMEN[k]['П1']) == F.valm(tolsh)]
            if selection_num > 0:
                return list_nomen[selection_num-1]
            else:
                return ';'.join(list_nomen)
        if rez == 1: #nn
            list_nomen = [k for k in self.myparent.DICT_NOMEN.keys() if
                          self.myparent.DICT_NOMEN[k]['П6'] == str(cam_cod) and F.valm(self.myparent.DICT_NOMEN[k]['П1']) == F.valm(tolsh)]
            if selection_num > 0:
                return list_nomen[selection_num-1]
            else:
                return ';'.join(list_nomen)

    def cam_to_mat(self:mywindow2, nom_cam:int) -> int:
        for k in self.myparent.DICT_KOD_CAM.keys():
            if self.myparent.DICT_KOD_CAM[k]['kod'] == nom_cam:
                return self.myparent.DICT_KOD_CAM[k]['kod_for_normatives']
        return -1


    def calc_var_time(self):
        list_tk = CQT.list_from_wtabl_c(self.ui2.tbl_var_tk, hat_c=True)
        list_tk_old = deepcopy(list_tk)
        list_tk = self.claculate_cells(list_tk, self.list_gvars)
        set_edit = {_ for _ in range(len(list_tk[0])) if _ not in (0, 1, 2, 3)}
        CQT.fill_wtabl(list_tk, self.ui2.tbl_rez_tk, set_editeble_col_nomera=set_edit)
        for i in range(1, len(list_tk)):
            for j in range(4, len(list_tk[i])):
                if list_tk[i][j] == '_':
                    CQT.set_color_wtab_c(self.ui2.tbl_rez_tk, i - 1, j, 245, 245, 245)
                else:
                    if "ERR" == list_tk[i][j] or list_tk[i][j] == '0':
                        CQT.set_color_wtab_c(self.ui2.tbl_rez_tk, i - 1, j, 253, 200, 200)
                    else:
                        if type(list_tk_old[i][j]) == str and "f'" in list_tk_old[i][j]:
                            CQT.set_color_wtab_c(self.ui2.tbl_rez_tk, i - 1, j, 200, 250, 200)



    def calc_var_mat(self):
        list_oper = CQT.list_from_wtabl_c(self.ui2.tbl_var_tk_mat, hat_c=True)
        list_oper_old = deepcopy(list_oper)
        list_tk = self.claculate_cells(list_oper, self.list_gvars)
        set_edit = {_ for _ in range(len(list_tk[0])) if _ not in (0, 1, 2, 3,4,5)}
        CQT.fill_wtabl(list_tk, self.ui2.tbl_rez_tk_mat, set_editeble_col_nomera=set_edit)
        for i in range(1, len(list_tk)):
            for j in range(4, len(list_tk[i])):
                if list_tk[i][j] == '_':
                    CQT.set_color_wtab_c(self.ui2.tbl_rez_tk_mat, i - 1, j, 245, 245, 245)
                else:
                    if "ERR" == list_tk[i][j] or list_tk[i][j] == '0':
                        CQT.set_color_wtab_c(self.ui2.tbl_rez_tk_mat, i - 1, j, 253, 200, 200)
                    else:
                        if type(list_oper_old[i][j]) == str and "f'" in list_oper_old[i][j]:
                            CQT.set_color_wtab_c(self.ui2.tbl_rez_tk_mat, i - 1, j, 200, 250, 200)
            if list_tk[i][3] in self.myparent.DICT_NOMEN:
                CQT.set_color_wtab_c(self.ui2.tbl_rez_tk_mat, i - 1, 3, 200, 250, 200)
                list_tk[i][4] = self.myparent.DICT_NOMEN[list_tk[i][3]]['Наименование']
                self.ui2.tbl_rez_tk_mat.item(i-1,4).setText(list_tk[i][4])
                CQT.set_color_wtab_c(self.ui2.tbl_rez_tk_mat, i - 1, 4, 200, 250, 200)
                list_tk[i][5] = self.myparent.DICT_NOMEN[list_tk[i][3]]['ЕдиницаИзмерения']
                self.ui2.tbl_rez_tk_mat.item(i - 1, 5).setText(list_tk[i][5])
                CQT.set_color_wtab_c(self.ui2.tbl_rez_tk_mat, i - 1, 5, 200, 250, 200)

    def calc_var_from_gvar(self):
        self.list_gvars = CQT.list_from_wtabl_c(self.ui2.tbl_var_vo, hat_c=True, rez_dict=True)[0]
        if self.check_insert_gvars(self.list_gvars) == False:
            CQT.msgbox(f'Не корректно внесены глобальные переменные')
            return
        self.calc_var_time()
        self.calc_var_mat()
        self.claculate_struct()
        self.claculate_mass()

    def calc_dse_ves(self) -> dict:
        list_dse_mat = CQT.list_from_wtabl_c(self.ui2.tbl_rez_tk_mat, hat_c=True,rez_dict=True)
        dict_dse = dict()
        for item in list_dse_mat:
            try:
                if item['ДСЕ'] not in dict_dse:
                    dict_dse[item['ДСЕ']] = F.valm(item['Норма'])
                else:
                    dict_dse[item['ДСЕ']] += F.valm(item['Норма'])
            except:
                CQT.msgbox(f"ОШибка суммирования массы в {item['ДСЕ']} {item['Код']} не учтено!")

        return dict_dse


    def claculate_mass(self):
        dict_dse = self.calc_dse_ves()
        list_struct = CQT.list_from_wtabl_c(self.myparent.ui.table_razr_MK, hat_c=True)
        nk_mass = F.num_col_by_name_in_hat_c(list_struct, 'Масса/М1,М2,М3')
        nk_naim = F.num_col_by_name_in_hat_c(list_struct, 'Обозначение')
        for i in range(1, len(list_struct)):
            arr_mass = list_struct[i][nk_mass].split('/М1')
            dse = list_struct[i][nk_naim]
            try:
                if dse in dict_dse:
                    arr_mass[0] = str(round(dict_dse[dse],3))
                else:
                    arr_mass[0] = '1'
            except:
                CQT.msgbox(f'Ошибка {dse} не рассчитана')
            list_struct[i][nk_mass] = '/М1'.join(arr_mass)
        CQT.fill_wtabl(list_struct, self.myparent.ui.table_razr_MK,
                       set_editeble_col_nomera=self.myparent.edit_cr_mk_ruch, auto_type=False)

    def claculate_struct(self):
        list_struct = CQT.list_from_wtabl_c(self.myparent.ui.table_razr_MK,hat_c=True)
        nk_kolich = F.num_col_by_name_in_hat_c(list_struct,'Количество')
        for i in range(1,len(list_struct)):
            self.dict_form_tk = self.use_global_var_form_tk(list_struct[i][1])
            if "f'" in str(list_struct[i][nk_kolich]):
                try:
                    list_struct[i][nk_kolich] = self.calc_funcs(list_struct[i][nk_kolich])
                    list_struct[i][nk_kolich] = self.apply_vars(list_struct[i][nk_kolich], self.dict_form_tk, self.list_gvars)
                    list_struct[i][nk_kolich] = self.cust_eval(list_struct[i][nk_kolich],4)
                except:
                    pass
        CQT.fill_wtabl(list_struct, self.myparent.ui.table_razr_MK, set_editeble_col_nomera=self.myparent.edit_cr_mk_ruch,auto_type=False)

    def calc_funcs(self,func:str):
        try:
            func = func.replace("arr(", "self.arr(")
            func = func.replace("tblv(", "self.tblv(")
            func = func.replace("tblm(", "self.tblm(")
            func = func.replace("nomen(", "self.nomen(")
            func = func.replace("cam_to_mat(", "self.cam_to_mat(")
            return func
        except:
            return func

    def claculate_cells(self,list_tk,list_gvars):
        for i in range(1,len(list_tk)):
            self.dict_form_tk = self.use_global_var_form_tk(list_tk[i][0])
            for j in range(3, len(list_tk[i])):
                if list_tk[i][j] == '_':
                    continue
                else:
                    list_tk[i][j] = self.calc_funcs(list_tk[i][j])
                if type(list_tk[i][j]) == str and ("f'" in list_tk[i][j] or
                                                   'tbl' in list_tk[i][j] or
                                                   'arr' in list_tk[i][j] or
                                                   'nomen' in str(list_tk[i][j]) or
                                                   'cam_to_mat' in str(list_tk[i][j])
                ):
                    list_tk[i][j] = self.apply_vars(list_tk[i][j], self.dict_form_tk, list_gvars)
                    try:
                        self.current_calc_nn = list_tk[i][0]
                        self.current_calc_nn = list_tk[i][3]
                        if "tbl" in str(list_tk[i][j]) or \
                                "arr" in str(list_tk[i][j]) or \
                                'nomen' in str(list_tk[i][j]) or \
                                'cam_to_mat' in str(list_tk[i][j]):
                            list_tk[i][j] = str(self.cust_eval(list_tk[i][j],44))
                            list_tk[i][j] = self.apply_vars(list_tk[i][j], self.dict_form_tk, list_gvars)
                        list_tk[i][j] = self.cust_eval(list_tk[i][j],4)
                    except:
                        list_tk[i][j] = 'ERR'
                else:
                    try:
                        list_tk[i][j] = self.cust_eval(list_tk[i][j], 4)
                    except:
                        list_tk[i][j] = 'ERR'
                try:
                    if F.is_numeric(list_tk[i][j]):
                        list_tk[i][j] = str(round(F.valm(list_tk[i][j]),4))
                except:
                    pass
        return list_tk

    def cust_eval(self,item,count):
        for _ in range(count):
            try:
                item = str(eval(item))
            except:
                return item
        return item

    def apply_glob_tk(self,item, dict_form_tk):
        for key in dict_form_tk.keys():
            item = item.replace(key, str(dict_form_tk[key]))
        return item

    def apply_list_gvars(self,item, list_gvars):
        for key in list_gvars.keys():
            item = item.replace(key, str(list_gvars[key]))
        return item

    def apply_vars(self,item:str, dict_form_tk, list_gvars):
        item = self.apply_glob_tk(item, dict_form_tk)
        item = self.apply_list_gvars(item, list_gvars)
        return item


    def use_global_var_form_tk(self,nn):
        if nn not in self.glob_dict_from_tk:
            return dict()
        if '{' in self.glob_dict_from_tk[nn] and '}' in self.glob_dict_from_tk[nn]:
            try:
                tmp_dict = eval(self.glob_dict_from_tk[nn])
            except:
                return dict()
            if type(tmp_dict) == type(dict()):
                return tmp_dict
            else:
                return dict()
        else:
            return dict()


    def exit_form(self):
        self.close()

    def full_screen(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


    def minized(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.showMinimized()

    def vars_oper_from_db(self,dict_of_dse):
        set_var = set()
        for dse in dict_of_dse.keys():
            for oper in dict_of_dse[dse]:
                if oper[2] == '1':
                    if oper[0] in self.myparent.DICT_VAR_OPER:
                        list_var = self.myparent.DICT_VAR_OPER[oper[0]][0]['Vars'].split(';')
                        for var in list_var:
                            set_var.add(var)
                    else:
                        CQT.msgbox(f'{oper[0]} не найден в списке операций')
                else:
                    if oper[2] in self.myparent.DICT_VAR_OPER:
                        dict_pereh = self.myparent.DICT_VAR_OPER[oper[2]][1]
                        if oper[0] in dict_pereh:
                            list_pereh_var = dict_pereh[oper[0]]
                            for var in list_pereh_var:
                                set_var.add(var)

                    else:
                        CQT.msgbox(f'{oper[0]} не найден в списке операций')
        return set_var


    def load_mater(self):
        dict_of_dse = self.calc_list_of_operations()
        list_rez = [['ДСЕ', 'Операция', 'Код', 'НН','Материал','Ед.Изм','Норма']]

        for dse in dict_of_dse.keys():
            for oper in dict_of_dse[dse]:
                if oper[2] == '1' and oper[4] != [['']]:
                    for m in range(len(oper[4])):
                        tmp = []
                        tmp.append(dse)
                        tmp.append(oper[0])
                        tmp.append(oper[3])
                        tmp.append(oper[4][m][0])
                        tmp.append(oper[4][m][1])
                        tmp.append(oper[4][m][2])
                        tmp.append(mat_line_replace_separ(oper[4][m][3]))
                        list_rez.append(tmp)
        set_edit = {_ for _ in range(len(list_rez[0])) if _ not in (0, 1, 2, 4, 5)}
        CQT.fill_wtabl(list_rez, self.ui2.tbl_var_tk_mat, set_editeble_col_nomera=set_edit, height_row=18)
        for i in range(1, len(list_rez)):
            if "f'" in list_rez[i][6]:
                CQT.set_color_wtab_c(self.ui2.tbl_var_tk_mat, i - 1, 6, 253, 200, 200)

    def load_time(self):
        dict_of_dse = self.calc_list_of_operations()
        set_var = self.vars_oper_from_db(dict_of_dse)
        list_rez = [['ДСЕ', 'Операция', 'Переход', 'Код']]
        for var in sorted(list(set_var)):
            list_rez[0].append(var)

        for dse in dict_of_dse.keys():
            for oper in dict_of_dse[dse]:
                list_var = oper[1].split('$')
                list_var_name = ['']
                tmp = ['_' for _ in list_rez[0]]
                tmp[0] = dse
                tmp[3] = oper[3]
                if oper[2] == '1':
                    tmp[1] = oper[0]
                    tmp[2] = ''
                    if oper[0] in self.myparent.DICT_VAR_OPER:
                        list_var_name = self.myparent.DICT_VAR_OPER[oper[0]][0]['Vars'].split(';')
                else:
                    tmp[1] = oper[2]
                    tmp[2] = oper[0]
                    if oper[2] in self.myparent.DICT_VAR_OPER:
                        if oper[0] in self.myparent.DICT_VAR_OPER[oper[2]][1]:
                            list_var_name = self.myparent.DICT_VAR_OPER[oper[2]][1][oper[0]]


                if len(list_var_name) != len(list_var):
                    CQT.msgbox(f'Не совпадают переменные в {dse} {oper} не учтена!')
                else:
                    for i in range(len(list_var_name)):
                        if list_var_name[i] != '':
                            nk = F.num_col_by_name_in_hat_c(list_rez, list_var_name[i])
                            if nk == None:
                                print(f' {list_var_name[i]} не найден в {tmp}')
                            tmp[nk] = list_var[i]
                list_rez.append(tmp)
        set_edit = {_ for _ in range(len(list_rez[0])) if _ not in (0, 1, 2, 3)}
        CQT.fill_wtabl(list_rez, self.ui2.tbl_var_tk, set_editeble_col_nomera=set_edit, height_row=18)
        for i in range(1, len(list_rez)):
            for j in range(4, len(list_rez[i])):
                if list_rez[i][j] == '_':
                    CQT.set_color_wtab_c(self.ui2.tbl_var_tk, i - 1, j, 245, 245, 245)
                if "f'" in list_rez[i][j]:
                    CQT.set_color_wtab_c(self.ui2.tbl_var_tk, i - 1, j, 253, 200, 200)


    def load_parametrs_vo(self):
        self.set_glob_var = set()
        self.load_mater()
        self.load_time()
        self.load_glob_vars()

    def load_glob_vars_csv(self):
        try:
            list_vars = CQT.list_from_wtabl_c(self.ui2.tbl_var_vo,sep='',hat_c=True,rez_dict=True)[0]
            for key in self.myparent.tkp_current_schema['Параметры'].keys():
                if key in list_vars:
                    list_vars[key] = self.myparent.tkp_current_schema['Параметры'][key]
            list_vars = F.dict_to_list(list_vars,transponir=True)
            CQT.fill_wtabl(list_vars,self.ui2.tbl_var_vo,auto_type=False)
        except:
            CQT.msgbox(f'Глобальные переменные не загружены')
            return

    def load_csv(self):
        defolt_path = r'O:\Служба главного конструктора\Временная\CSV'
        if not F.existence_file_c(defolt_path):
            defolt_path = F.put_po_umolch()
        file = CQT.f_dialog_name(self,'Выбор',defolt_path,'*.csv;*.txt')
        if file == ['.']:
            return
        list = F.load_file(file)
        return dict(list)

    def load_glob_vars(self):
        self.set_glob_var = set()
        list_tk = CQT.list_from_wtabl_c(self.ui2.tbl_var_tk,hat_c=True,rez_dict=True)
        list_tk_mat = CQT.list_from_wtabl_c(self.ui2.tbl_var_tk_mat, hat_c=True, rez_dict=True)

        for i in range(len(list_tk)):
            for key in list_tk[i].keys():
                if key not in ('ДСЕ', 'Операция', 'Переход', 'Код',''):
                    if "f'" in str(list_tk[i][key]):
                        list_glob_var = self.catch_glob_var(list_tk[i][key])
                        for _ in list_glob_var:
                            self.set_glob_var.add(_)
        for i in range(len(list_tk_mat)):
            for key in list_tk_mat[i].keys():
                if key in ('Норма'):
                    if "f'" in str(list_tk_mat[i][key]):
                        list_glob_var = self.catch_glob_var(list_tk_mat[i][key])
                        for _ in list_glob_var:
                            self.set_glob_var.add(_)
        list_fields_glob_var =sorted(list(self.set_glob_var))
        rez_list_glob_var = [list_fields_glob_var, ['' for _ in list(self.set_glob_var)]]

        CQT.fill_wtabl(rez_list_glob_var, self.ui2.tbl_var_vo)

    def catch_glob_var(self,text:str):
        list_var = []
        list_1 = text.split('{')
        for item in list_1[1:]:
            var = item.split('}')[0]
            if var[:3] != 'tbl' and var[:3] != 'arr' and var[:5]  != 'nomen' and var[:10]  != 'cam_to_mat':
                list_var.append(var)
        return list_var

    def calc_list_of_operations(self):
        DICT_NN_NTK = CMS.load_dict_dse(self.myparent.db_dse)
        list_of_operations = dict()
        list_pre_mk = CQT.list_from_wtabl_c(self.myparent.ui.table_razr_MK ,'',True,False,True)
        self.glob_dict_from_tk = dict()
        for tk in list_pre_mk:
            operations = self.operations_tk(tk['Обозначение'],DICT_NN_NTK)
            if operations != None:
                list_of_operations[tk['Обозначение']] = operations
        return  list_of_operations


    def operations_tk(self, nn,DICT_NN_NTK):
        if nn not in DICT_NN_NTK:
            CQT.msgbox(f'{nn} не найдена в БД')
            return
        nom_tk = DICT_NN_NTK[nn]['Номер_техкарты']
        put_name_tk = F.scfg('add_docs') + F.sep() + nom_tk + "_" + nn
        tk = F.open_file_c(put_name_tk + '.txt', False, "|", True, True)
        if tk == ['']:
            CQT.msgbox(f'Не найдена техкарта {put_name_tk}')
            return
        list_oper = []
        fl = False
        for item in tk:
            if len(item) == 21:
                if fl and item[20] == '0':
                    break
                if item[20] == '0':
                    fl = True
                    tmp_oper_name = ''
                    self.glob_dict_from_tk[nn] = item[7]
                    if '[' in self.glob_dict_from_tk[nn] and ']' in self.glob_dict_from_tk[nn]:
                        self.glob_dict_from_tk[nn] = self.glob_dict_from_tk[nn].replace("[", '{')
                        self.glob_dict_from_tk[nn] = self.glob_dict_from_tk[nn].replace("]", '}')
                    else:
                        self.glob_dict_from_tk[nn] = ''
                if fl == True and item[20] == '1':
                    mats = [_.split('$') for _ in [m for m in item[10].split('{')]]
                    for i in range(len(mats)):
                        if len(mats[i]) >=4:
                            mats[i][3] = mat_line_replace_separ(mats[i][3])
                            mats[i][0] = mat_line_replace_separ(mats[i][0])
                    list_oper.append([item[0],item[14],item[20],item[3],mats])
                    tmp_oper_name = item[0]
                if fl == True and item[20] == '2':
                    list_oper.append([item[0],item[14],tmp_oper_name,item[3],[]])
        return  list_oper

    def app_icons(self):
        # from PyQt5.QtGui import QIcon
        # from PyQt5.QtWidgets import QApplication, QStyle
        self.ui2.tbtn_exit.setIcon(QtGui.QIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarCloseButton)))
        self.ui2.tbtn_exit.setIconSize(QtCore.QSize(8, 8))
        self.ui2.tbtn_min.setIcon(QtGui.QIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarMinButton)))
        self.ui2.tbtn_min.setIconSize(QtCore.QSize(8, 8))
        self.ui2.tbtn_max.setIcon(QtGui.QIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarMaxButton)))
        self.ui2.tbtn_max.setIconSize(QtCore.QSize(8, 8))
        self.ui2.btn_calc.setIcon(QtGui.QIcon(QApplication.style().standardIcon(QStyle.SP_DialogOkButton)))
        self.ui2.btn_calc.setIconSize(QtCore.QSize(32, 32))
        self.ui2.btn_ok.setIcon(QtGui.QIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)))
        self.ui2.btn_ok.setIconSize(QtCore.QSize(32, 32))
        self.ui2.btn_reload_glob_vars.setIcon(QtGui.QIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload)))
        self.ui2.btn_reload_glob_vars.setIconSize(QtCore.QSize(32, 32))


def update_parametrs(self,spis_tk:list,j:int,nn:str):
    nk_mat_tk = 10
    nk_op_tst = 7
    list_vars_vo = deepcopy(self.list_vars_vo)
    for i in range(1,len(list_vars_vo)):
        list_vars_vo[i][3]= "$".join([list_vars_vo[i][0],list_vars_vo[i][3]])
    dict_vo = F.list_to_dict(list_vars_vo,'Код')
    current_row = "$".join([nn,spis_tk[j][3]])
    if current_row not in dict_vo:
        CQT.msgbox(f'{current_row} не найдена в шаблоне под ТКП')
        return spis_tk[j]
    list_vars = [[],[]]
    for key in dict_vo[current_row].keys():
        if key not in ['ДСЕ','Операция','Переход','Код']:
            if dict_vo[current_row][key] != '_':
                list_vars[0].append(key)
                list_vars[1].append(str(dict_vo[current_row][key]))

    time = operacii.vremya_tsht(dict_vo[current_row]['Операция'], list_vars)
    if isinstance(time,tuple):
        time = time[0]
    list_mat = operacii.materiali(self, dict_vo[current_row]['Операция'], list_vars)
    #==============ADD OSN MATS±+++++++++++++
    if current_row in self.dict_mat_vo:
        list_vsp_mat_tmp = list_mat.split('{')
        list_osn_mat = self.dict_mat_vo[current_row].split('{')
        for mat in list_vsp_mat_tmp:
            if mat != '':
                list_osn_mat.append(mat)
        list_mat= '{'.join(list_osn_mat)
    #+++++++++++++++++++++++++++++

    if j < len(spis_tk)-1:
        for i in range(j + 1,len(spis_tk)):
            current_row = "$".join([nn, spis_tk[i][3]])
            if spis_tk[i][20] == '1' or spis_tk[i][20] == '0':
                break
            if spis_tk[i][20] == '2':
                list_vars_pereh = [[], []]
                if current_row in dict_vo:
                    for key in dict_vo[current_row].keys():
                        if key not in ['ДСЕ', 'Операция', 'Переход', 'Код']:
                            if dict_vo[current_row][key] != '_':
                                list_vars_pereh[0].append(key)
                                list_vars_pereh[1].append(str(dict_vo[current_row][key]))

                    vrema = operacii.vremya_tsht_perehodi(dict_vo[current_row]['Операция'],spis_tk[i][0], list_vars_pereh, list_vars)

                    time += vrema
                #for mat in materials:
                #    list_mat.append(mat)
    spis_tk[j][nk_mat_tk] = list_mat
    spis_tk[j][nk_op_tst] = time
    return spis_tk[j]


def DICT_VAR_OPER(self):
    self.DICT_VAR_OPER = dict()
    if self.SPIS_OP == None:
        quit()
    dict_var_oper = F.list_to_dict(self.SPIS_OP,'name')
    #dict_var_oper = list_var_from_txt(F.open_file_c(F.tcfg('oper'), separ='|'))
    DICT_OPERS_CALC = operacii.Data_oper_norm.DICT_OPERS_CALC
    for oper in dict_var_oper.keys():
        dict_var_pereh =[]
        if F.existence_file_c(F.scfg('oper') + F.sep() + f'{oper}.txt'):
            dict_var_pereh = list_var_from_txt(F.open_file_c(F.scfg('oper') + F.sep() + f'{oper}.txt', separ='|'),2)
        self.DICT_VAR_OPER[oper] = [dict_var_oper[oper],dict_var_pereh]
        if oper in DICT_OPERS_CALC:
            str_oper = ';'.join([f'{k}:{DICT_OPERS_CALC[oper][k]["type"]}' for k in DICT_OPERS_CALC[oper].keys()])
            self.DICT_VAR_OPER[oper][0]['Vars'] = str_oper

def list_var_from_txt(list,shag=3):
    dict_ = dict()
    for oper in list:
        if len(oper) > shag:
            list_var = oper[shag].split(';')
            tmp_var = []
            for var in list_var:
                tmp_var.append(var.split(':')[0])
            dict_[oper[0]] = tmp_var
    return dict_




def load_le_tkp_dir_shablons(self):
    path = CMS.load_tmp_path('dir_tkp_shablons')
    self.ui.le_tkp_dir_shablons.setText(path)
def load_vid_izd(self:mywindow):
    self.ui.cmb_vid_izd.clear()
    tbl = self.ui.tbL_tkp_list
    row = CQT.get_dict_line_form_tbl(tbl)
    if 'вид_по_напр' not in row:
        return
    #if row['вид_по_напр'] == '1':
    for vid in self.Data_plan.DICT_VID_PO_NAPR_NAME.keys():
        self.ui.cmb_vid_izd.addItem(vid)


def cmb_select_vid_izd(self:mywindow):
    tbl = self.ui.tbL_tkp_list
    row = CQT.get_dict_line_form_tbl(tbl)
    if 'вид_по_напр' not in row:
        return
    val_vid = self.Data_plan.DICT_VID_PO_NAPR_NAME[self.ui.cmb_vid_izd.currentText()]['Пномер']
    CQT.set_val_tbl_by_name(tbl,'','вид_по_напр',self.ui.cmb_vid_izd.currentText())
    s_nom = row[CMS.DICT_NAME_SQL['tkp']['s_nom']]
    if not CQT.msgboxgYN(f'Установить для ТКП №{s_nom} новый вид {self.ui.cmb_vid_izd.currentText()}'):
        return
    CSQ.custom_request_c(self.db_dse,f"""UPDATE tkp SET вид_по_напр = ? WHERE s_nom = ?;""",list_of_lists_c=[[int(val_vid),int(s_nom)]])
    CQT.msgbox('Удачно')

def load_le_tkp_dir_res(self):
    path = CMS.load_tmp_path('dir_tkp_res')
    self.ui.le_tkp_dir_res.setText(path)

def edit_tkp_dir_shablons(self):
    def save_le_tkp_dir_shablons(self):
        path = self.ui.le_tkp_dir_shablons.text()
        if F.existence_file_c(path):
            CMS.save_tmp_path('dir_tkp_shablons', path)
        else:
            CQT.msgbox(f'Директория не обнаружена')
            self.ui.le_tkp_dir_shablons.setText('')
    save_le_tkp_dir_shablons(self)

def edit_tkp_dir_res(self):
    def save_le_tkp_dir_res(self):
        path = self.ui.le_tkp_dir_res.text()
        if F.existence_file_c(path):
            CMS.save_tmp_path('dir_tkp_res', path)
        else:
            CQT.msgbox(f'Директория не обнаружена')
            self.ui.le_tkp_dir_res.setText('')
    save_le_tkp_dir_res(self)
@CQT.onerror
def btn_tkp_load_strukt(self:mywindow,*args):
    def check_tkp_param(self):
        return True

    def check_tkp_analogue(self):
        tbl = self.ui.tbL_tkp_list
        row = CQT.get_dict_line_form_tbl(tbl)
        if row['вид_по_напр'] == '1':
            CQT.msgbox(f'Не выбран вид изделия')
            return False
        return True

    def check_dir_shabl(self:mywindow):
        if F.existence_file_c(self.ui.le_tkp_dir_shablons.text()):
            return True
        CQT.msgbox(f'Отсутствует директория {self.ui.le_tkp_dir_shablons.text()}')
        return False

    def get_dict_files(strukt_files):
        dict_pickle = dict()
        for item in strukt_files:
            if len(item) > 2:
                for file in item[2]:
                    if '.pickle' == F.keep_extention_c(file):
                        dict_pickle[F.throw_out_extention_c(file)] = item[0] + F.sep() + file
        return  dict_pickle

    def select_oper_potrebl(self:mywindow, text, row, col):
        self.ui.table_razr_MK.item(row,col).setText(text)

    def set_okrash(self:mywindow, text, row, col):
        self.ui.table_razr_MK.item(row,col).setText(str(int(text)))

    def add_izd(put_ima,main_list,row=-1,count_izd=1):
        if row == -1:
            row = len(main_list)-1
        spis = CMS.add_cust_drevo(self, put_ima, main_list, row,count_izd,modifiers='shift')
        return spis

    def add_column(rez_list,name):
        rez_list[0].append(name)
        for i in range(1,len(rez_list)):
            rez_list[i].append('')
        return rez_list

    curr_row = self.ui.tbL_tkp_list.currentRow()
    if curr_row == -1:
        return

    path = self.ui.le_tkp_dir_res.text()
    if not F.existence_file_c(path):
        CQT.msgbox(f'Директория вывода не обнаружена')
        return

    nk_pnom = CQT.num_col_by_name_c(self.ui.tbL_tkp_list, CMS.DICT_NAME_SQL['tkp']['s_nom'])
    if nk_pnom == None:
        CQT.msgbox(f"Не найдено поле {CMS.DICT_NAME_SQL['tkp']['s_nom']}")
        return
    s_nom = int(self.ui.tbL_tkp_list.item(curr_row, nk_pnom).text())
    result = CSQ.custom_request_c(self.db_dse,
                                  f"""SELECT pickle_file, type_tkp, name_tkp, nnom_tkp, вид_по_напр  FROM tkp WHERE s_nom = {s_nom}""",
                                   rez_dict=True, one=True)
    if result == False:
        CQT.msgbox(f'Ошибка загрузки БД')
        return

    self.ui.cmb_cr_mk_pr.setCurrentText('КТ.ВО')
    self.cmb_cr_mk_select_pr()
    self.ui.cmb_cr_mk_plpr.setCurrentIndex(0)
    self.cmb_cr_mk_select_plpr()
    self.ui.cmb_cr_mk_py.setCurrentIndex(0)
    self.cmb_cr_mk_select_py()
    self.ui.cmb_cr_mk_poz.setCurrentIndex(0)
    self.cmb_cr_mk_select_poz()

    dict_tkp_byte = result['pickle_file']
    dict_tkp = F.from_binary_pickle(dict_tkp_byte)
    for elem in dict_tkp['Структура']:
        if elem['Масса/М1,М2,М3'] == '//':
            elem['Масса/М1,М2,М3'] = ''
    name_tkp = result['name_tkp']
    nnom_tkp = result['nnom_tkp']
    type_tkp = result['type_tkp']
    vid_izd = result['вид_по_напр']
    расчет_по_статистике = False
    if type_tkp == 2:# Parametrics
        if not check_tkp_param(self):
            return
        if not check_dir_shabl(self):
            return
        strukt_files = F.list_of_files_c(self.ui.le_tkp_dir_shablons.text())
        dict_files = get_dict_files(strukt_files)

        list_err = []
        for izd in dict_tkp['Структура'].keys():
            if izd not in dict_files:
                list_err.append(izd)
        if len(list_err) > 0:
            CQT.msgbox(f'{list_err} \n не найдено в директории шаблонов')
            return
        spis = add_izd(dict_files[dict_tkp['Корневой']],[],-1,count_izd = 0)
        for izd in dict_tkp['Структура'].keys():
            if izd in dict_files:
                if izd != dict_tkp['Корневой']:
                    spis = add_izd(dict_files[izd],spis,1,count_izd = dict_tkp['Структура'][izd])
                    if spis == None:
                        return
        nk_kol_z = F.num_col_by_name_in_hat_c(spis,'Кол. по заявке')

        for i in range(1,len(spis)):
            spis[i][nk_kol_z]= ''
        spis[1][nk_kol_z] = '1'
        CQT.fill_wtabl_old_c(self, spis, self.ui.table_razr_MK, 0, self.edit_cr_mk_ruch, (), (),
                             200, True, '', 30)
        self.tkp_current_schema = dict_tkp

    if type_tkp in (3,4):  # Analogue , statistic
        if not check_tkp_analogue(self):
            return

        rez_list = [deepcopy(self.hat_c)]
        rez_list[0].append('Мат_аналог_кд')
        rez_list[0].append('Код_аналог_кд')
        rez_list[0].append('К_узла')
        rez_list[0].append('Коэф_н_м')
        for item in dict_tkp['Структура']:
            tmp_line = []
            for hat_i in rez_list[0]:
                if hat_i in item:
                    tmp_line.append(item[hat_i])
                else:
                    tmp_line.append('')
            rez_list.append(tmp_line)

        nk_kol_z = F.num_col_by_name_in_hat_c(rez_list, 'Кол. по заявке')
        nk_k_knot = F.num_col_by_name_in_hat_c(rez_list, 'К_узла')
        nk_k_norm_mat = F.num_col_by_name_in_hat_c(rez_list, 'Коэф_н_м')
        nk_k_okras = F.num_col_by_name_in_hat_c(rez_list, 'Окрашивание')
        for i in range(1, len(rez_list)):
            rez_list[i][nk_kol_z] = ''
            rez_list[i][nk_k_knot] = '1'
            rez_list[i][nk_k_norm_mat] = '1.3'
            rez_list[i][nk_k_okras] = ''

        rez_list[1][nk_kol_z] = '1'
        edit_cr_mk_analogue = {F.num_col_by_name_in_hat_c(rez_list,'К_узла'),
                               F.num_col_by_name_in_hat_c(rez_list, 'Коэф_н_м'),
        }
        CQT.fill_wtabl_old_c(self, rez_list, self.ui.table_razr_MK, 0, edit_cr_mk_analogue, (), (), 200, True, '', 30)
        self.set_btns_manual_edit_enabled(False)

        if vid_izd in self.Data_plan.DICT_VID_PO_NAPR:
            if type_tkp == 4:
                расчет_по_статистике = True
            else:
                if type_tkp == 3 and CMS.check_possibility_statistic_calc_tkp(vid_izd):
                    if CQT.msgboxgYN(
                            f"Поздравляем!\nВам достался `{self.Data_plan.DICT_VID_PO_NAPR[vid_izd]['Имя']}`\nА это значит, что его возможно обсчитать по упрощенной схеме:\n"
                            f"Расчет времени без техкарт, по статистическим данным.\n\n Использовать упрощенный режим?"):
                        расчет_по_статистике = True
                        type_tkp = 4
            if расчет_по_статистике:
                for name_field in (
                'Сумм.Количество', 'Наименование_аналог', 'Обозначение_аналог', 'Уд_количество_аналог',
                'Коэфф_длины_швов', 'dreva_kod', 'Мат_аналог_кд', 'Код_аналог_кд', 'К_узла', 'Окрашивание'):
                    self.ui.table_razr_MK.setColumnHidden(CQT.num_col_by_name_c(self.ui.table_razr_MK, name_field),
                                                          True)


        self.ui.pushButton_create_paralel.setEnabled(True)
        self.ui.pushButton_create_udalituzel.setEnabled(True)
        nf_koef_mat = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'Коэф_н_м')
        nf_name_oper_potr_mat = CQT.num_col_by_name_c(self.ui.table_razr_MK,'Опер_потребл')
        nf_name_okrash = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'Окрашивание')
        nf_mat_analog = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'Мат_аналог_кд')
        nf_cod_analog = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'Код_аналог_кд')
        nf_name_dse = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'Обозначение_аналог')
        nf_mat = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'Масса/М1,М2,М3')
        nf_pki = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'ПКИ')
        nf_kod_erp = CQT.num_col_by_name_c(self.ui.table_razr_MK, 'Код ERP')
        poki = self.place.poki
        DICT_DSE = CSQ.custom_request_c(self.db_dse, f'''SELECT * FROM dse WHERE poki = {poki}''', rez_dict=True)
        self.DICT_DSE_save_mk = F.deploy_dict_c(DICT_DSE, 'Номенклатурный_номер')
        for i in range(self.ui.table_razr_MK.rowCount()):
            if расчет_по_статистике:
                if self.ui.table_razr_MK.item(i,nf_kod_erp).text() == '':
                    continue
                list_opers = list(self.Data_plan.DICT_ETAPS_NAME.keys())
                CQT.add_combobox(self, self.ui.table_razr_MK, i, nf_name_oper_potr_mat, list_opers, True,
                                 select_oper_potrebl)
                kod_erp = self.ui.table_razr_MK.item(i,nf_kod_erp).text()
                etap = None
                if kod_erp in self.DICT_NOMEN:
                    vid = self.DICT_NOMEN[kod_erp]['Вид']
                    if vid in self.Data_plan.DICT_VID_NOMEN:
                        etap = self.Data_plan.DICT_VID_NOMEN[vid]['этап_по_умолч_созд_ткп']
                if etap in list_opers:
                    select_oper_potrebl(self, etap, i, nf_name_oper_potr_mat)
                    self.ui.table_razr_MK.cellWidget(i, nf_name_oper_potr_mat).setCurrentText(etap)
            else:

                dse = self.ui.table_razr_MK.item(i,nf_name_dse).text()
                tk_obj = CMS.Techkards(dse, self.db_dse,DICT_OP_NAME=self.DICT_OP_NAME)
                if tk_obj == None:
                    CQT.msgbox(f'Не найдена техкарта {dse}')
                    return


                oper_with_cod_analog = ''
                if dse not in self.DICT_DSE_save_mk:
                    CQT.msgbox(f'ДСЕ {dse} не найдена в БД ДСЕ' )
                    return
                old_mat_vid = self.DICT_DSE_save_mk[dse]['Мат_кд']
                old_mat_cod = self.DICT_DSE_save_mk[dse]['Код_ЕРП']
                self.ui.table_razr_MK.item(i, nf_mat_analog).setText(old_mat_vid)
                self.ui.table_razr_MK.item(i, nf_cod_analog).setText(old_mat_cod)


                list_opers = []
                if tk_obj.tk is None:
                    return CQT.msgbox(f'Не удалось инициализировать техкарту с обозначением: {dse!r}')
                if len(tk_obj.tk['bodys']) == 0:
                    return CQT.msgbox(f'Ошибка: Найдна пустая техкарта с обозначением: {dse!r}')
                for oper in tk_obj.tk['bodys'][0]['opers']:
                    str_oper = "$".join([oper['s_name'], oper['name_ver']])
                    list_opers.append(str_oper)
                    for mat in oper['materials']:
                        if mat['cod'] == old_mat_cod:
                            oper_with_cod_analog = str_oper
                    if oper['name_ver'] == 'Окрашивание':
                                CQT.add_check_box(self.ui.table_razr_MK, i, nf_name_okrash, False, False, set_okrash, self)

                if (
                        self.ui.table_razr_MK.item(i,nf_mat).text() == "" or
                        self.ui.table_razr_MK.item(i,nf_pki).text() == "1" or
                        self.ui.table_razr_MK.item(i,nf_mat).text() == "//"):
                    continue
                CQT.add_combobox(self,self.ui.table_razr_MK,i,nf_name_oper_potr_mat,list_opers,True,select_oper_potrebl)
                if len(list_opers)>0:
                    if oper_with_cod_analog == '':
                        for oper in list_opers:
                            name_oper = oper.split('$')[-1]
                            if self.DICT_OP_NAME[name_oper]['Вспомогат'] == 0:
                                oper_with_cod_analog = oper
                                break

                    select_oper_potrebl(self, oper_with_cod_analog, i, nf_name_oper_potr_mat)
                    self.ui.table_razr_MK.cellWidget(i, nf_name_oper_potr_mat).setCurrentText(oper_with_cod_analog)

        self.tkp_current_schema = dict_tkp


    self.spis_poziciy_rez_ruchnoi = []
    nnom_tkp = 'None' if nnom_tkp == None else nnom_tkp
    name_tkp = 'None' if name_tkp == None else name_tkp
    self.tkp_current_schema['file_name'] = f'{F.clear_row_for_file_name_c(nnom_tkp)}_{F.clear_row_for_file_name_c(name_tkp)}'
    self.tkp_current_schema['nnom_tkp'] = nnom_tkp
    self.tkp_current_schema['name_tkp'] = name_tkp
    self.tkp_current_schema['type_tkp'] = type_tkp
    self.tkp_current_schema['s_nom'] = s_nom
    self.tkp_current_schema['вид_по_напр'] = vid_izd
    self.tkp_current_schema['расчет_по_статистике'] = расчет_по_статистике
    self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Разработка МК'))



    def calc_weidth_tkp():
        ves_summ = 0
        for item in dict_tkp['Структура']:
            if item['ПКИ'] == '0':
                list_mat_line = item['Масса/М1,М2,М3'].split('/')
                if len(list_mat_line) == 3:
                    ves = F.valm(list_mat_line[0])
                    count = F.valm(item['Количество на изделие'])
                    ves_summ += ves * count
        return ves_summ
    weight, weight_wo_pki = recalc_weight(self)
    self.tkp_current_schema['weight'] = weight
    #ves = calc_weidth_tkp()
    self.ui.le_name_predv_res.setText(self.tkp_current_schema['nnom_tkp'])

def btn_tkp_add_to_plan(self:mywindow):
    list_poz = CSQ.custom_request_c(self.db_kplan,f"""SELECT 
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE пл_оуп.№ERP  
       END AS "№ERP", 
       
        CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE пл_оуп.№проекта 
       END AS Проект, 
  
         
     plan.Приоритет, 
 
        пл_оуп.№Пл_Пр as "ПлПр",
        napravl_deyat.Псевдоним as "Вид",
        

     napravlenie.name  AS Направление, 
       
       пл_оуп.Количество as "Колчество", 
       
       
       plan.Позиция,
       plan.Пномер as "Пномер", 
       пл_топ.Предв_спецификация_ЕРП 
       
    FROM plan 
          LEFT JOIN napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности 
          LEFT JOIN napravlenie ON napravlenie.Пномер = napravl_deyat.Направление  
         LEFT JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер 
         LEFT JOIN пл_топ ON пл_топ.НомПл = plan.Пномер 
         LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
        
         WHERE plan.poki = {self.place.poki} and plan.Статус IN (1,2,5,8,9) and plan.Статус_норм IN (0,1);""",rez_dict=True)
    rez = CQT.msgboxg_get_table(self,"Выбор позиции",list_poz,'Выбор',selection_from_tbl=True,ExtendedSelection=False,selectRows=True)
    if rez:
        self.dict_cur_poz_cr_mk = rez
        self.ui.lbl_cr_mk.setText(str(self.dict_cur_poz_cr_mk))

def edit_le_tkp_name_res(self:mywindow):
    row = self.ui.tbL_tkp_list.currentRow()
    if row == -1:
        return
    text = self.ui.le_tkp_name_res.text()
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbL_tkp_list, CMS.DICT_NAME_SQL['tkp']['s_nom'])
    nk_name_res = CQT.num_col_by_name_c(self.ui.tbL_tkp_list, CMS.DICT_NAME_SQL['tkp']['name_res'])

    pnom = int(self.ui.tbL_tkp_list.item(row, nk_pnom).text())
    CSQ.custom_request_c(self.db_dse,
               f"""UPDATE tkp SET name_res = ? WHERE s_nom = {pnom} """, list_of_lists_c=[[text]])
    self.ui.tbL_tkp_list.item(row, nk_name_res).setText(text)
    CQT.msgbox('Успешно')


def btn_tkp_date_res(self:mywindow):
    if self.ui.le_tkp_name_res.text().strip() == '':
        CQT.msgbox(f'Ну указан номер ресурсной ЕРП')
        return
    row = self.ui.tbL_tkp_list.currentRow()
    if row == -1:
        return

    nk_pnom = CQT.num_col_by_name_c(self.ui.tbL_tkp_list, CMS.DICT_NAME_SQL['tkp']['s_nom'])

    nk_date_res = CQT.num_col_by_name_c(self.ui.tbL_tkp_list, CMS.DICT_NAME_SQL['tkp']['date_res'])
    pnom = int(self.ui.tbL_tkp_list.item(row, nk_pnom).text())
    now = F.now()
    CSQ.custom_request_c(self.db_dse,
               f"""UPDATE tkp SET date_res = "{now}" WHERE s_nom = {pnom} """)
    self.ui.tbL_tkp_list.item(row, nk_date_res).setText(now)
    CQT.msgbox('Успешно')

def cmb_tkp_otv_techn(self):
    row = self.ui.tbL_tkp_list.currentRow()
    if row == -1:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbL_tkp_list, CMS.DICT_NAME_SQL['tkp']['s_nom'])
    nk_resp_technolog = CQT.num_col_by_name_c(self.ui.tbL_tkp_list, CMS.DICT_NAME_SQL['tkp']['resp_technolog'])
    pnom = int(self.ui.tbL_tkp_list.item(row, nk_pnom).text())
    CSQ.custom_request_c(self.db_dse,
               f"""UPDATE tkp SET resp_technolog = "{self.ui.cmb_tkp_otv_techn.currentText()}" WHERE s_nom = {pnom} """)
    self.ui.tbL_tkp_list.item(row, nk_resp_technolog).setText(self.ui.cmb_tkp_otv_techn.currentText())
    CQT.msgbox('Успешно')

def mat_line_replace_separ(line:str):
    tmp = line.replace("£", "{")
    return tmp.replace("¢", "}")



@CQT.onerror
def recalc_weight(self, *args):
    def calc_count(self,num_row):
        tbl = self.ui.table_razr_MK
        current_row = CQT.get_dict_line_form_tbl(tbl,num_row)
        count = int(current_row['Количество'])
        ur = int(current_row['Уровень'])
        for i in range(num_row-1,-1,-1):
            row = CQT.get_dict_line_form_tbl(tbl,i)
            if int(row['Уровень']) == 0:
                break
            if int(row['Уровень']) == ur-1:
                count *= int(row['Количество'])
                ur -=1
        return count


    rez = 0
    rez_wo_pki = 0
    self.ui.lbl_summ_weight.setText('')
    self.ui.lbl_summ_weight_wo_pki.setText('')
    tbl = self.ui.table_razr_MK
    if tbl.rowCount() == 0:
        return
    for i in range(tbl.rowCount()):
        row = CQT.get_dict_line_form_tbl(tbl, i)
        str_weight = row['Масса/М1,М2,М3'].split('/')[0]
        pki = row['ПКИ']
        count = calc_count(self,i)
        #if count != int(row['Количество на изделие']):
        #    CQT.msgbox(f'Ошибка расчетка количества на изделие')
        #    return
        rez+= F.valm(str_weight)*count
        if pki == '0':
            rez_wo_pki += F.valm(str_weight)*count*1.3
    if rez > 0:
        self.ui.lbl_summ_weight.setText(str(round(rez,2)))
    if rez_wo_pki > 0:
        self.ui.lbl_summ_weight_wo_pki.setText(str(round(rez_wo_pki,2)))
    return round(rez,2), round(rez_wo_pki,2)
