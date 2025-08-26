import os
import sys
import operator
from datetime import datetime

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWinExtras import QtWin
import config

from mydesign import Ui_MainWindow  # импорт нашего сгенерированного файла
#from mydesign2 import Ui_Dialog  # импорт нашего сгенерированного файла
from TKP_parametrics import get_params, set_params, reset_params, json_generation
import project_cust_38.Cust_Functions as F
import project_cust_38.xml_v_drevo as XML
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from data_class import Data_mes
import analogues_tree as ANAL
import tkp


CQT.convert_UI_into_PY_c()
cfg = config.Config(r'Config\CFG.cfg')
F.test_path()
#class mywindow2(QtWidgets.QDialog):  # диалоговое окно
#    def __init__(self,parent=None,item_o="",p1=0,p2=0):
#        self.item_o = item_o
#        self.p1 = p1
#        self.p2 = p2
#        self.myparent = parent
#        super(mywindow2, self).__init__()
#        self.ui2 = Ui_Dialog()
#        self.ui2.setupUi(self)
#        self.setWindowModality(QtCore.Qt.ApplicationModal)


class mywindow(QtWidgets.QMainWindow):

    resized = QtCore.pyqtSignal()
    def __init__(self):

        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.versia = '0.2.3.7'
        self.setWindowTitle(f"Создание CSV/ВО v{self.versia}")
        #pyinstaller.exe --onefile --icon=1.ico --noconsole csv_tkp.py


        #h = ctypes.windll.user32.GetSystemMetrics(1)-75
        #w = round(ctypes.windll.user32.GetSystemMetrics(0)/2)
        #self.setGeometry(0,0,w,h)
        self.params = None

        self.Data_mes = Data_mes

        tkp.load_list_params(self)
        list_dse = [['Чек', 'Узел', 'Кол-во','Корневой']]
        for i in range(3,len(self.list_param)):
            list_dse.append(['',self.list_param[i][0],0,0])
        #06.06.2024
        # CQT.fill_wtabl(list_dse,self.ui.tbl_dse,{2},auto_type=False)
        # for i in range(self.ui.tbl_dse.rowCount()):
        #     CQT.add_check_box(self.ui.tbl_dse, i, 0, False, False, tkp.tkp_create_list_var, self)
        #     CQT.add_check_box(self.ui.tbl_dse, i, 3, False, False, tkp.tkp_select_root, self)

        self.sl_mat = {
            '': '',}

        for item in self.Data_mes.dict_mat:
            self.sl_mat[item['name']] = item['kod']

        self.glob_edit_red_tree_snum = ''
        self.calculation = ANAL.CalculationAnalog(self)
        self.load_nomen_config()
        self.ui.fr_dse_erp_view.setHidden(True)
        #===========tabwidget
        self.ui.tabWidget.currentChanged[int].connect(self.tab_clcik)
        #===========TBL===============
        self.ui.tbl_red_tree.clicked.connect(lambda: ANAL.apply_tooltip_tree_edit_tbl(self))
        self.ui.tbl_list_tkp.cellDoubleClicked[int, int].connect(self.CVO_path_kd_dbl_clk)
        self.ui.tbl_anal_dse.cellDoubleClicked[int, int].connect(self.anal_dse_dbl_clk)
        tabl = self.ui.tableWidget
        CQT.set_color_sort_cell_table_c(tabl)
        tabl.setSelectionMode(1)
        tabl.doubleClicked.connect(self.otkr_dxf)
        self.shap = ['Путь','Файл','Кол-во, шт.','Материал детали','Толщина, мм.','Гибка','Т+Фрез.','Просмотр']
        self.ui.tbl_list_tkp.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_list_tkp_filtr.horizontalScrollBar().setValue)
        self.ui.tbl_anal_dse.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_anal_dse_filtr.horizontalScrollBar().setValue)
        self.ui.tbl_anal_mat.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_anal_mat_filtr.horizontalScrollBar().setValue)
        self.ui.tbl_anal_mat.clicked.connect(lambda: ANAL.click_row_mat(self))
        self.ui.tbl_red_tree.clicked.connect(lambda: ANAL.click_row_strukt(self))
        self.ui.tbl_red_tree.cellChanged[int,int].connect(lambda: ANAL.recalc_weight(self))
        self.ui.tbl_red_tree.itemSelectionChanged.connect(lambda *_: self.calculation.item_selection())
        self.ui.tbl_red_tree.horizontalHeader().sectionResized.connect(lambda i,j,k: CMS.on_section_resized(self,i,j,k))
        self.ui.tbl_red_tree.cellChanged[int, int].connect(lambda row, col: ANAL.accumulate_tree_mass(self, row=row, col=col))
        self.ui.tbl_red_tree.cellChanged[int, int].connect(lambda row, col: ANAL.fill_tab_to_level(self.ui.tbl_red_tree))
        #========lineedit
        self.ui.le_udk_len.textEdited.connect(lambda: ANAL.calc_udk(self))
        self.ui.le_udk_len_a.textEdited.connect(lambda: ANAL.calc_udk(self))
        self.ui.le_udk_wid.textEdited.connect(lambda: ANAL.calc_udk(self))
        self.ui.le_udk_wid_a.textEdited.connect(lambda: ANAL.calc_udk(self))
        self.ui.le_udk_diam_nar.textEdited.connect(lambda: ANAL.calc_udk_d(self))
        self.ui.le_udk_diam_vn.textEdited.connect(lambda: ANAL.calc_udk_d(self))
        self.ui.le_udk_diam_a_nar.textEdited.connect(lambda: ANAL.calc_udk_d(self))
        self.ui.le_udk_diam_a_vn.textEdited.connect(lambda: ANAL.calc_udk_d(self))

        # =======btn
        vib_pap = self.ui.pushButton
        vib_pap.clicked.connect(self.vibor_pap)
        sohr_button = self.ui.pushButton_2
        sohr_button.clicked.connect(self.sohr_file)
        zagr_csv = self.ui.pushButton_3
        zagr_csv.clicked.connect(self.import_csv)

        button_xml = self.ui.pushButton_xml
        button_xml.clicked.connect(self.import_xml)

        but_reload = self.ui.pushButton_reload
        but_reload.clicked.connect(self.reload)
        but_reload.setToolTip('открывался проводник (лучше где лежит прога) и оператор просто выбирал нужный файл, который впоследствии добавлялся в прогу.')

        but_obnov = self.ui.pushButton_obn_puti
        but_obnov.clicked.connect(self.obnov_puti)
        but_obnov.setToolTip('старый ксв файл, после открытия через прогу что бы путь автоматически обновлялся')

        self.red_tree_deque = []
        self.ui.btn_show_fr_erp_dse_view.clicked.connect(self.show_fr_erp_dse_view)
        self.ui.btn_get_into_red.clicked.connect(lambda: ANAL.get_into_red(self))
        self.ui.btn_ok_udk.clicked.connect(lambda: ANAL.set_udk(self))
        self.ui.btn_add_row.clicked.connect(lambda: ANAL.add_row(self))
        self.ui.btn_load_xml.clicked.connect(lambda : ANAL.load_xml(self))
        self.ui.btn_get_knot.clicked.connect(lambda: ANAL.get_knot(self))
        self.ui.btn_plus_lvl.clicked.connect(lambda: ANAL.change_lvl(self, operator.add))
        self.ui.btn_minus_lvl.clicked.connect(lambda: ANAL.change_lvl(self, operator.sub))
        self.ui.btn_red_tree_clear.clicked.connect(lambda: ANAL.prepare_tbl_red_stukt(self))
        self.ui.btn_red_tree_del_knot.clicked.connect(lambda: ANAL.red_tree_del_knot(self))
        self.ui.btn_red_tree_save.clicked.connect(lambda: ANAL.red_tree_save(self))
        self.ui.btn_red_tree_load.clicked.connect(lambda: ANAL.red_tree_load(self))
        self.ui.btn_red_tree_up.clicked.connect(lambda: ANAL.red_tree_move(self, operator.sub))
        self.ui.btn_red_tree_down.clicked.connect(lambda: ANAL.red_tree_move(self, operator.add))
        self.ui.btn_mat_apply_mat.clicked.connect(lambda: ANAL.mat_apply_mat(self))
        self.ui.btn_mat_apply_only_mat.clicked.connect(lambda: ANAL.change_mat(self))
        self.ui.btn_mat_apply_wout_mat.clicked.connect(lambda: ANAL.mat_apply_wout_mat(self))
        self.ui.btn_dse_apply.clicked.connect(lambda: ANAL.apply_dse(self))
        self.ui.btn_save_red_tree.clicked.connect(lambda: ANAL.save_red_tree(self))
        self.ui.cmb_vid_napr.currentIndexChanged.connect(lambda: ANAL.check_tree_on_type_tkp(self))

        self.ui.btn_reset.clicked.connect(lambda : reset_params(self))

        self.ui.set_var_btn.setEnabled(False)
        self.ui.get_json_cotl.setEnabled(False)
        self.ui.btn_ok.clicked.connect(lambda : get_params(self, self.ui.le_nnom_izd.text()))

        self.ui.set_var_btn.clicked.connect(lambda : set_params(self, self.ui.le_nnom_izd.text()))
        self.ui.get_json_cotl.clicked.connect(lambda : json_generation(self))


        self.ui.btn_pause.clicked.connect(lambda : tkp.btn_status(self,'Пауза'))
        self.ui.btn_to_del.clicked.connect(lambda: tkp.btn_status(self,'На удаление'))
        self.ui.btn_to_work.clicked.connect(lambda: tkp.btn_status(self,'В работе'))

        self.ui.btn_art_repl.clicked.connect(lambda: ANAL.art_repl(self))
        self.ui.btn_art_repl.clicked.connect(lambda: ANAL.replace_arts(self))
        self.ui.btn_kmass_ok.clicked.connect(lambda: ANAL.kmass_apply(self))
        self.ui.btn_recalc_weight.clicked.connect(lambda: ANAL.recalc_weight(self))

        self.ui.btn_check_prices.clicked.connect(lambda: ANAL.check_prices(self))
        self.ui.btn_load_nomen_wo_prices.clicked.connect(lambda: ANAL.load_nomen_wo_prices(self))
        #=============checkbox============
        self.ui.chk_change_mass.setCheckState(1)
        self.ui.chk_nomen_desc.clicked.connect(self.save_nomen_config)
        self.ui.chk_nomen_unit.clicked.connect(self.save_nomen_config)
        self.ui.chk_nomen_maker.clicked.connect(self.save_nomen_config)
        self.ui.chk_nomen_describe.clicked.connect(self.save_nomen_config)
        self.ui.chk_nomen_add_r.clicked.connect(self.save_nomen_config)

        #=============combobox============
        self.ui.cmb_select_year.currentTextChanged.connect(self.on_cmb_select_year_changed)
        self.put_csv = ""
        ANAL.prepare_tbl_red_stukt(self)
        ANAL.load_mats(self)
        ANAL.load_dse(self)
        ANAL.load_vids(self)
        CQT.load_css(self)
        CQT.load_icons(self)
        ANAL.clear_add_info(self)
        self.Data_plan = Data_mes()

    def anal_dse_dbl_clk(self,r,c):
        if c == CQT.num_col_by_name_c(self.ui.tbl_anal_dse,'Путь_docs'):
            path = self.ui.tbl_anal_dse.item(r,c).text()
            if 'docs://' in path:
                CMS.run_link_DOCs_c('','','',path)
            return

        self.ui.le_add_naim.setText(self.ui.tbl_anal_dse.item(r,CQT.num_col_by_name_c(self.ui.tbl_anal_dse,'Наименование')).text())
        self.ui.le_add_nn.setText(self.ui.tbl_anal_dse.item(r, CQT.num_col_by_name_c(self.ui.tbl_anal_dse,'Номенклатурный_номер')).text())


    def CVO_path_kd_dbl_clk(self, r, c):
        CMS.path_kd_dbl_clk(self.ui.tbl_list_tkp, r, c)

    def on_cmb_select_year_changed(self, new_value: str, *args): #07.04.25
        if new_value == '': return
        if new_value == 'По умолчанию':
            data_res = None
        else:
            data_res = int(new_value)
        CMS.load_tkp_list(
            self,
            self.Data_mes.db_dse,
            self.Data_mes.DICT_NAME_SQL['tkp'],
            self.ui.tbl_list_tkp,
            self.ui.tbl_list_tkp_filtr,
            date_res=data_res
        )

    @CQT.onerror
    def tab_clcik(self,num_tab):
        if self.ui.tabWidget.tabText(num_tab) == 'Список ТКП':
            data = ['По умолчанию'] + [str(datetime.now().year - num) for num in range(3)]
            self.ui.cmb_select_year.clear()
            self.ui.cmb_select_year.addItems(data)
            CMS.load_tkp_list(
                self,
                self.Data_mes.db_dse,
                self.Data_mes.DICT_NAME_SQL['tkp'],
                self.ui.tbl_list_tkp,
                self.ui.tbl_list_tkp_filtr,
            )


    @CQT.onerror
    def keyReleaseEvent(self, e):
        if e.key() == 67 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())
        if self.ui.tbl_anal_dse_filtr.hasFocus():
            if e.key() == 16777220 or e.key() == 16777221:
                CMS.apply_filtr_c(self, self.ui.tbl_anal_dse_filtr, self.ui.tbl_anal_dse)
        if self.ui.tbl_anal_mat_filtr.hasFocus():
            if e.key() == 16777220 or e.key() == 16777221:
                CMS.apply_filtr_c(self, self.ui.tbl_anal_mat_filtr, self.ui.tbl_anal_mat)
        if self.ui.tbl_list_tkp_filtr.hasFocus():
            if e.key() == 16777220 or e.key() == 16777221:
                CMS.apply_filtr_c(self, self.ui.tbl_list_tkp_filtr, self.ui.tbl_list_tkp)
        if self.ui.tableWidget.hasFocus() == True:
            if self.ui.tableWidget.currentRow() != -1:
                if e.key() == QtCore.Qt.Key_Delete:
                    spis = self.spec_spisok_iz_tabl()
                    spis.pop(self.ui.tableWidget.currentRow()+1)
                    self.zap_tabl(spis)
        if e.key() == 80 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.refill_tbl_into_msgbox_get_table(self, QtWidgets.QApplication.focusWidget())

    @CQT.onerror
    def show_fr_erp_dse_view(self,*args):
        if self.ui.fr_dse_erp_view.isHidden():
            self.ui.fr_dse_erp_view.setHidden(False)
        else:
            self.ui.fr_dse_erp_view.setHidden(True)
    @CQT.onerror
    def save_nomen_config(self,*args):
        val_chk_nomen_desc = self.ui.chk_nomen_desc.isChecked()
        val_chk_nomen_unit = self.ui.chk_nomen_unit.isChecked()
        val_chk_nomen_maker = self.ui.chk_nomen_maker.isChecked()
        val_chk_nomen_describe = self.ui.chk_nomen_describe.isChecked()
        val_chk_nomen_add_r = self.ui.chk_nomen_add_r.isChecked()

        CMS.save_tmp_stukt([val_chk_nomen_desc,val_chk_nomen_add_r,val_chk_nomen_unit,val_chk_nomen_maker,val_chk_nomen_describe],'nomen_config')

    @CQT.onerror
    def load_nomen_config(self,*args):
        val_chk_nomen_desc= False
        val_chk_nomen_unit= False
        val_chk_nomen_maker= False
        val_chk_nomen_describe= False
        val_chk_nomen_add_r= False
        data = CMS.load_tmp_stukt('nomen_config')
        if data:
            val_chk_nomen_desc, val_chk_nomen_add_r, val_chk_nomen_unit, val_chk_nomen_maker, val_chk_nomen_describe = data


        self.ui.chk_nomen_desc.blockSignals(True)
        self.ui.chk_nomen_unit.blockSignals(True)
        self.ui.chk_nomen_maker.blockSignals(True)
        self.ui.chk_nomen_describe.blockSignals(True)
        self.ui.chk_nomen_add_r.blockSignals(True)

        self.ui.chk_nomen_desc.setChecked(val_chk_nomen_desc)
        self.ui.chk_nomen_unit.setChecked(val_chk_nomen_unit)
        self.ui.chk_nomen_maker.setChecked(val_chk_nomen_maker)
        self.ui.chk_nomen_describe.setChecked(val_chk_nomen_describe)
        self.ui.chk_nomen_add_r.setChecked(val_chk_nomen_add_r)

        self.ui.chk_nomen_desc.blockSignals(False)
        self.ui.chk_nomen_unit.blockSignals(False)
        self.ui.chk_nomen_maker.blockSignals(False)
        self.ui.chk_nomen_describe.blockSignals(False)
        self.ui.chk_nomen_add_r.blockSignals(False)

    @CQT.onerror
    def obnov_puti(self):
        if self.put_csv == '':
            return
        arr_csv_tmp = self.put_csv.split(os.sep)
        arr_csv_tmp.pop()
        tabl = self.ui.tableWidget
        for i in range(tabl.rowCount()):
            if tabl.item(i,0) != None:
                if tabl.item(i,0).text() != "":
                    arr_tmp = tabl.item(i,0).text().split('\\')
                    arr_csv_tmp2 = arr_csv_tmp.copy()
                    arr_csv_tmp2.append(arr_tmp[-1])
                    tabl.item(i, 0).setText("\\".join(arr_csv_tmp2))

    @CQT.onerror
    def spec_spisok_iz_tabl(self):
        tabl = self.ui.tableWidget
        spis = []
        spis.append(self.shap)
        #spis[0].remove('Просмотр')
        if tabl.rowCount() == 0:
            return
        for i in range(tabl.rowCount()):
            if tabl.rowCount() == 0:
                return
            if tabl.item(0, 0) is None:
                return
            if tabl.item(i, 0) == None or tabl.item(i, 0).text().strip() == '':
                continue
            tmp = []
            tmp.append(tabl.item(i, 0).text())
            tmp.append(tabl.item(i, 1).text())
            tmp.append(tabl.item(i, 2).text().strip())

            mat = self.sl_mat[tabl.cellWidget(i, 3).currentText()]

            tmp.append(str(mat))

            tmp.append(tabl.item(i, 4).text().strip())

            for j in range(5, tabl.columnCount() - 1):
                etap = tabl.cellWidget(i, j).checkState()
                if etap == 2:
                    zn = tabl.cellWidget(i, j).text()
                else:
                    zn = ''
                tmp.append(zn)
            if tabl.cellWidget(i, tabl.columnCount() - 1).text() == 'Просмотрено':
                tmp.append("True")
            else:
                tmp.append("False")
            spis.append(tmp)
        return spis

    @CQT.onerror
    def import_xml(self, *args):
        tabl = self.ui.tableWidget
        tabl.clearContents()
        tabl.clear()
        tabl.setRowCount(0)
        self.put_csv = ""
        #umolch = r'P:\test\DXF'
        umolch = os.path.abspath(os.curdir)
        if F.existence_file_c(umolch) == False:
            umolch = F.put_po_umolch()
        s = CQT.f_dialog_name(self,'выбрать csv',umolch,'*.xml')
        if s == '.' or s == '':
            return
        spis = XML.spisok_iz_xml(s)
        if spis == None:
            return
        itog_tabl = []
        itog_tabl.append(self.shap)
        putt_dxf_arr = os.path.normpath(s).split(os.sep)
        putt_dxf_arr.pop()
        putt_dxf = os.sep.join(putt_dxf_arr)

        sp_dxf = F.list_of_files_c(putt_dxf)
        sp_nenaid = []

        for det in spis:
            if not isinstance(det,list):
                CQT.msgbox(f'Структура файла XML не корректная')
                return
            flag = False
            tolsh = ''
            kod_mat = ''
            kolvo = ''
            ima = '*'
            for i in sp_dxf:
                if flag == True:
                    break
                for j in i[2]:
                    if j[-4:] == '.dxf':
                        ima_dxf = F.throw_out_extention_c(j)

                        if det[0].strip() in ima_dxf and det[1].strip() in ima_dxf:
                            tolsh = det[10]
                            kod_mat = det[11]
                            kolvo = det[7]
                            ima = j
                            flag = True
                            break
            itog_tabl.append([i[0] + os.sep + ima, ima, kolvo, kod_mat, tolsh, '', ''])
            if flag == False:
                sp_nenaid.append(det[0] + ' ' + det[1])

        self.zap_tabl(itog_tabl)
        if len(sp_nenaid) > 0:
            CQT.msgbox('Не найдены dxf на ' + ','.join(sp_nenaid))

    @CQT.onerror
    def import_csv(self,*args):
        tabl = self.ui.tableWidget
        tabl.clearContents()
        tabl.clear()
        tabl.setRowCount(0)
        self.put_csv = ""
        #umolch = r'O:\Производство Powerz\Отдел технолога\В работе\2020\2011007\ПУ00-000414\КЛ.2011007.02.00\DXF 02'
        umolch = os.path.abspath(os.curdir)
        if F.existence_file_c(umolch) == False:
            umolch = F.put_po_umolch()
        s = CQT.f_dialog_name(self,'выбрать csv',umolch,'*.csv')
        if s == '.' or s == '':
            return
        sp = F.open_file_c(s,False,';')
        if len(sp)==0:
            CQT.msgbox('Пустой файл')
            return
        self.put_csv = s
        spis = []
        spis.append(self.shap)
        for i in sp:
            spis.append(i)

        self.zap_tabl(spis)
        self.statusBar().showMessage(s)

    @CQT.onerror
    def reload(self):

        spis = self.spec_spisok_iz_tabl()
        if spis == None:
            spis = []
            spis.append(self.shap)
        tabl = self.ui.tableWidget
        put_dxf = self.statusBar().currentMessage()
        if put_dxf == "":
            return
        put_dxf_tmp = os.path.normpath(put_dxf).split(os.sep)
        put_dxf_tmp.pop()
        put_dxf=os.sep.join(put_dxf_tmp)
        tabl.clearContents()
        tabl.clear()
        tabl.setRowCount(0)

        if put_dxf == '.':
            return
        sp = CQT.f_dialog_name(self,'Выбрать файл',put_dxf,"*.dxf",False)
        for i in range(len(sp)):
            ima_f = sp[i].split(os.sep)[-1]
            spis.append([sp[i], ima_f, '', '', '', '', '', "False"])

        #sp = F.list_of_files_c(put_dxf)
        #for i in sp:
        #    for j in i[2]:
        #        if j[-4:] == '.dxf':
        #            spis.append([i[0] + os.sep + j, j, '', '', '', '', '', "False"])
        #    break
        if len(spis) == 1:
            CQT.msgbox('dxf в папке ' + put_dxf + ' не найдены')
            return
        self.zap_tabl(spis)

    @CQT.onerror
    def otkr_dxf(self):
        tabl = self.ui.tableWidget

        if tabl.currentColumn() == 1:
            obr = tabl.item(tabl.currentRow(),0).text()
            if obr == '':
                return
            F.run_file_c(obr)
        if tabl.currentColumn() == 0:
            obr = tabl.item(tabl.currentRow(),0).text()
            if obr == '':
                return
            obr = F.path_up_c(obr)
            F.open_dir_c(obr)

    @CQT.onerror
    def vibor_pap(self):
        tabl = self.ui.tableWidget
        tabl.clearContents()
        tabl.clear()
        tabl.setRowCount(0)
        self.put_csv = ""
        umolch = os.path.abspath(os.curdir)#r'O:\Производство Powerz\Отдел технолога\В работе\2020\2011007\ПУ00-000414\КЛ.2011007.02.00\DXF 02'
        if F.existence_file_c(umolch) == False:
            umolch = F.put_po_umolch()
        s = CQT.getDirectory(self,umolch)
        if s == '.':
            return
        spis = []
        spis.append(self.shap)
        sp = F.list_of_files_c(s)
        for i in sp:
            for j in i[2]:
                if j[-4:] == '.dxf':
                    spis.append([i[0] + os.sep + j,j,'','','','',''])
            break
        if len(spis) == 1:
            CQT.msgbox('dxf в папке ' + s + ' не найдены')
            return
        self.zap_tabl(spis)

    @CQT.onerror
    def mat_po_kod(self,kod):
        for i in self.sl_mat.keys():
            if self.sl_mat[i] == kod:
                return i
        return ''

    @CQT.onerror
    def zap_tabl(self,spis):
        tabl = self.ui.tableWidget
        tabl.clearContents()
        tabl.clear()
        tabl.setRowCount(0)
        set_edit = {2,3,4,5}
        CQT.fill_wtabl_old_c(self,spis,tabl,0,set_edit,'','',200,True,'',30,50)
        for i in range(tabl.rowCount()):
            combo = QtWidgets.QComboBox()
            combo.wheelEvent = lambda event: None
            k = []
            for item in self.sl_mat.keys():
                combo.addItem(item)
                k.append(item)
            tabl.setCellWidget(i, 3, combo)
            if F.is_numeric(spis[i+1][3]) == True:
                kod = int(spis[i+1][3])
            else: kod = ''
            tabl.cellWidget(i,3).setCurrentIndex(k.index(self.mat_po_kod(kod)))
            push = QtWidgets.QPushButton('Click', self)
            push.clicked.connect(lambda _, x=i + 1: self.button(x))
            if spis[i+1][-1] == 'True':
                push.setText('Просмотрено')
            else:
                push.setText('Просмотр *.PDF')
            tabl.setCellWidget(i,tabl.columnCount()-1,push)
            for j in range(5,len(spis[0])-1):
                check = QtWidgets.QCheckBox()
                check.setText(spis[0][j][0])
                tabl.setCellWidget(i, j, check)
                if j <= len(spis[i+1])-1:
                    if spis[i+1][j].upper() == 'Г' and tabl.horizontalHeaderItem(j).text()[0] == 'Г':
                        tabl.cellWidget(i,j).setCheckState(2)
                    if spis[i+1][j].upper() == 'Т' and tabl.horizontalHeaderItem(j).text()[0] == 'Т':
                        tabl.cellWidget(i,j).setCheckState(2)
        if tabl.rowCount() == 0:
            return
        n_proekt = tabl.item(0, 1).text()
        arr_t = n_proekt.split(' ')
        n_proekt = arr_t[0]

        arr_t = n_proekt.split('.')
        if len(arr_t) > 2:
            n_proekt = arr_t[1]
            n_poz = arr_t[2]
        else:
            n_proekt = tabl.item(0, 1).text()
            n_poz = ''
        self.ui.lineEdit.setText(n_proekt)
        self.ui.lineEdit_2.setText(n_poz)
        return

    @CQT.onerror
    def button(self,strok):

        tabl = self.ui.tableWidget
        strok-=1
        sp_iskl = [' (Г)',' (П)', ' (Т+Ф)', ' (Т)', ' (Ф)','(Г)','(П)', '(Т+Ф)', '(Т)', '(Ф)']
        tabl.cellWidget(strok, tabl.columnCount()-1).setText('Просмотрено')
        obr = F.throw_out_extention_c(tabl.item(strok,1).text())
        obr2 = F.throw_out_extention_c(tabl.item(strok,1).text()) + ' '
        obr3 = self.ubrat_skobki(obr)
        obr4 = self.ubrat_skobki(obr2)
        obr5 = self.ubrat_skobki(obr,False)
        obr6 = self.ubrat_skobki(obr2,False)
        put_dxf = tabl.item(strok,0).text()
        try:
            for level_c  in range(2,4):
                put = F.path_up_c(put_dxf,level_c)
                s = F.list_of_files_c(put)
                for i in range(len(s)):
                    if len(s[i][2])>0:
                        for j in range(len(s[i][2])):
                            tmp = s[i][2][j]
                            for k in sp_iskl:
                                tmp = tmp.replace(k,'')
                            if tmp[-4:] == '.pdf':
                                tmp = F.throw_out_extention_c(tmp)
                                if tmp in obr:
                                    F.run_file_c(s[i][0] + os.sep + s[i][2][j])
                                    return
                                if tmp in obr2:
                                    F.run_file_c(s[i][0] + os.sep + s[i][2][j])
                                    return
                                if tmp in obr3:
                                    F.run_file_c(s[i][0] + os.sep + s[i][2][j])
                                    return
                                if tmp in obr4:
                                    F.run_file_c(s[i][0] + os.sep + s[i][2][j])
                                    return
                                if tmp in obr5:
                                    F.run_file_c(s[i][0] + os.sep + s[i][2][j])
                                    return
                                if tmp in obr6:
                                    F.run_file_c(s[i][0] + os.sep + s[i][2][j])
                                    return
            CQT.msgbox('Не найден файл ' + obr + '\n' + 'Файл должен иметь имя, совпадающее с *.dxf и распологаться не дальше 2 уровней вверх')
            return
        except:
            CQT.msgbox('Некорректное название')
            return

    @CQT.onerror
    def ubrat_skobki(self,obr,probel = True):
        if obr.count('(') == 0 or obr.count(')') == 0:
            return obr
        arr1 = obr.split('(')
        arr2 = obr.split(')')
        if probel is True:
            return arr1[0] + arr2[-1]
        else:
            return arr1[0].strip() + ' ' + arr2[-1].strip()

    def preparate_table_for_clipboard(self):
        res = self.get_main_table(self.ui.tbl_list_tkp)
        str_table = ''
        for row in res:
            str_table += '\t'.join(row)
            str_table += '\r\n'
        return str_table


    def get_selected_area(self, li_items):
        for i in li_items:
            return i.topRow(), i.leftColumn(), i.bottomRow(), i.rightColumn()

    def get_table_select_items(self):
        li_items = self.ui.tbl_list_tkp.selectedRanges()
        if not li_items:
            res = self.preparate_table_for_clipboard()
        else:
            start_row, start_column, stop_row, stop_column = self.get_selected_area(li_items)
            res = ''
            for row in range(self.ui.tbl_list_tkp.rowCount()):
                for column in range(self.ui.tbl_list_tkp.columnCount()):
                    if start_row <= row <= stop_row and start_column <= column <= stop_column:
                        res += f'{self.ui.tbl_list_tkp.item(row, column).text()}\t'
                res += '\r\n'
        return res

    @CQT.onerror
    def status_otkl_prosm(self):
        data = F.date(4).replace('.','')
        if data in self.ui.lineEdit_2.text():
            return data
        return False

    @CQT.onerror
    def sohr_file(self):
        tabl = self.ui.tableWidget
        if tabl.rowCount() == 0:
            return
        flag_otkl_prosm = False
        flag_otkl_prosm = self.status_otkl_prosm()

        for i in range(tabl.rowCount()):
            if flag_otkl_prosm == False:
                if tabl.cellWidget(i, tabl.columnCount() - 1).text() != 'Просмотрено':
                    CQT.msgbox('PDF в строке ' + str(i + 1) + ' не просмотрен.')
                    return
            if tabl.rowCount() == 0:
                return
            if tabl.item(0, 0) is None:
                return
            if tabl.item(i, 0) == None or tabl.item(i, 0).text().strip() == '':
                continue

            if tabl.item(i, 2).text().strip() == '':
                CQT.msgbox('Не указано количество в ' + str(i+1) + ' строке')
                return
            if F.is_numeric(tabl.item(i, 2).text().strip()) == False:
                CQT.msgbox('Количество не является числом в ' + str(i+1) + ' строке')
                return

            mat = self.sl_mat[tabl.cellWidget(i,3).currentText()]
            if mat == '':
                CQT.msgbox('Не указан материал в ' + str(i + 1) + ' строке')
                return

            if tabl.item(i, 4).text().strip() == '':
                CQT.msgbox('Не указана толщина в ' + str(i+1) + ' строке')
                return
            if F.is_numeric(tabl.item(i, 4).text().strip()) == False:
                CQT.msgbox('Толщина не является числом в ' + str(i+1) + ' строке')
                return

        spis = self.spec_spisok_iz_tabl()
        s =[]
        for item in range(1, len(spis)):
            spis[item].pop()

            s.append(';'.join(spis[item]))

        put_dxf = tabl.item(0, 0).text()
        put = F.path_up_c(put_dxf, 1)

        if flag_otkl_prosm != False:
            self.ui.lineEdit_2.setText(self.ui.lineEdit_2.text().replace(flag_otkl_prosm,''))

        name = self.ui.lineEdit.text() + '.' + self.ui.lineEdit_2.text()
        put = CQT.f_dialog_save(self, 'тест',put + os.sep + name ,'*.csv' )
        if put == '.':
            return
        F.write_file_c(put,s,'')
        CQT.msgbox('Сохранено')


app = QtWidgets.QApplication([])

myappid = 'Powerz.BAG.CSV.SustControlWork.0.0.0'  # !!!
QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
try:
    app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "icon.png")))
finally:
    pass
#S = F.scfg('Stile').split(",") 'Fusion,Windows,windowsvista'
app.setStyle('Fusion')

application = mywindow()
from project_cust_38.widget_spy import install_pyqt_event_hook
install_pyqt_event_hook(app)
# ======================================================
versia = application.versia
if CMS.kontrol_ver(versia,"csv") == False:
    sys.exit()
# =========================================================
application.showMaximized()
sys.exit(app.exec())
#python -OO -m py_compile csv_tkp.py
#pyinstaller.exe --onefile --icon=1.ico --noconsole csv_tkp.py
