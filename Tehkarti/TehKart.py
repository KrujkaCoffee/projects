import pprint

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWinExtras import QtWin
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyle
import os
import random
# import subprocess
import project_cust_38.Cust_Qt as CQT
from ezdxf.zoom import window

CQT.convert_UI_into_PY_c()
import copy
import re
from mydesign import Ui_MainW  # импорт нашего сгенерированного файла
from mydesign2 import Ui_Dialog  # импорт нашего сгенерированного файла

import project_cust_38.Cust_SQLite as CSQ
import sys
import project_cust_38.Cust_Functions as F
from GOST3111882F3 import vigruzit2 as GF3
import project_cust_38.Cust_mes as CMS
from pathlib import Path
import project_cust_38.operacii as operacii
from project_cust_38 import Cust_xl_formul as CXLF
from project_cust_38 import Cust_docs as CDOCS
import tk_operation_docs as TOD
import project_cust_38.api_erp_commands as APIERP

import hashlib
import osn_materials as osn_mat
import project_cust_38.nomenklatura as nomen_erp
# import proizv_calendar# Проверка производственного календаря...
import project_cust_38.Cust_dxf as CDXF
import project_cust_38.Cust_config as USRCNF
from project_cust_38 import Cust_config as CFG
import  magazin as MAGAZ
import correctirovka as CORR
import ko_izv_izm as II
import k_plan_top as KPT
'''
ТК 
0 Название техкарты , 1-отметка о прикреплении ... , 2- номер ТК, 3-сводный код, 4-, 5-Дата, 6-ФИО разработал , 7- примечание  .... 
13 - документ карты ($), , 14- параметрика($) , 15- Документ, 20 - уровень

Опер
0-Название оп, 1 - отметка документа ... , 2-номер операции, 3-сводный код, 4- рабочий центр код, 5-Оборудование, 6-Тпз, 7 - Тшт, 
8 -Профессия, 9 - КР , 10 - материалы (kod$naim$ed$norma{kod$naim$ed$norma), 11 - КОИД , 12 - , 13 - документы($ op),
 14- параметрика($), 15- Документ, 16- Словарь параметрика($), 20 - уровень

переход
0 - название перехода, 1-отметка о прикреплении ... , 2- номер ТК, 3-сводный код, 4- номер чего то, 7 - Тшт, 11 - приспособления ($)
12 - инструмент ($), 13 - документы($ op), 14- параметрика($), 16- Словарь параметрика($) ... 20 - уровень
'''




# @CQT.onerror
# def db_files_nalich(self, put_file,nom_tk):
#     def update_data(size, hesh, bin_file, date, usr, pnom):
#         CSQ.custom_request_c(self.db_files, f"""UPDATE reestr SET (size, hesh, file, Date_edit, usr)
#                          = (?,?,?,?,?) WHERE Пномер == {pnom};""",
#                    list_of_lists_c=[[size, hesh, bin_file, date, usr]])
#         return
#     def add_data(size, hesh, bin_file, date, usr):
#         CSQ.custom_request_c(self.db_files, """INSERT INTO reestr(size, hesh, file, Date_edit, usr)
#                          VALUES (?,?,?,?,?);""",
#                    list_of_lists_c=[[size, hesh, bin_file, date, usr]])
#         query = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM reestr WHERE size == '{size}' and hesh == '{hesh}'""",rez_dict=True)
#         if query == []:
#             return
#         return query[0]['Пномер']
#     def add_name(nom_data, name, date_edit, usr):
#         CSQ.custom_request_c(self.db_files, """INSERT INTO names(nom_data, name, date_edit, usr)
#                                  VALUES (?,?,?,?);""",
#                    list_of_lists_c=[[nom_data, name, date_edit, usr]])
#
#     def add_tkart(file_name,t_kard_name):
#         query = CSQ.custom_request_c(self.db_files,f"""SELECT file_name,t_kard_name FROM t_kards WHERE file_name == '{file_name}' AND t_kard_name == '{t_kard_name}' """)
#         if len(query)==1:
#             CSQ.custom_request_c(self.db_files, """INSERT INTO t_kards(file_name,t_kard_name)
#                                          VALUES (?,?);""",
#                    list_of_lists_c=[[file_name,t_kard_name]])
#
#     file = put_file.split(os.sep)[-1]
#
#     size = os.path.getsize(put_file)
#     bin_file = F.load_file_convert_to_binary(put_file)
#     hesh = hashlib.sha1(bin_file).hexdigest()
#     name = file
#
#     """если есть файл
#             если имя совпадает
#                 Ничего не далать предупредить
#                     выход
#             если имя не совпадает
#                 предупреждение добавлять файл и связанные карты
#                     да запрос
#                     нет выход
#         если нет файла
#             если имя существует
#                  заменить файл и связанные карты
#                     да запрос
#                     нет выход
#             если  имя не существует
#                 Ничего не далать занести
#                     выход
#                     """
#
#     custom_request_c = f"""SELECT * FROM reestr WHERE size == {size} and hesh == '{hesh}'"""
#     query = CSQ.custom_request_c(self.db_files, custom_request_c, rez_dict=True)
#     if query == []: # если нет файла
#         custom_request_c2 = f"""SELECT * FROM names WHERE name == '{name}'"""
#         query2 = CSQ.custom_request_c(self.db_files, custom_request_c2, rez_dict=True)
#         if query2 == []:#если имя не существует
#             nom = add_data(size, hesh, bin_file, F.now("%Y-%m-%d %H-%M"), F.user_name())
#             if nom == None:
#                 CQT.msgbox(f'Ошибка загрузки')
#                 return
#             add_name(nom, name, F.now("%Y-%m-%d %H-%M"), F.user_name())
#             add_tkart(name, nom_tk)
#
#         else:#если имя существует
#             nom = query2[0]['Пномер']
#             custom_request_c3 = f"""SELECT t_kard_name, Пномер FROM t_kards WHERE file_name == '{name}'"""
#             query3 = CSQ.custom_request_c(self.db_files, custom_request_c3, rez_dict=True)
#             list_cards = [_['t_kard_name'] for _ in query3]
#             if not CQT.msgboxgYN(f'файл с именем {name} уже существует, но с содержимое файла отличается от предложенного.\n'
#                              f'Нужно убедиться что новый файл правильный и актуальный\n\n'
#                              f'Обновить файл? Изменение затронет резку связанных техкарт:\n({str(list_cards)})'):
#                 return
#             # занести
#             update_data(size, hesh, bin_file, F.now("%Y-%m-%d %H-%M"), F.user_name(),nom)
#             add_tkart(name, nom_tk)
#
#
#     else:#если есть файл
#         nom_data = query[0]['Пномер']
#         custom_request_c2 = f"""SELECT * FROM names WHERE nom_data == {nom_data}"""
#         query2 = CSQ.custom_request_c(self.db_files, custom_request_c2, rez_dict=True)
#         if query2 == []:#если имя отсутсвует
#             add_name(nom_data, name, F.now("%Y-%m-%d %H-%M"), F.user_name())
#             add_tkart(name, nom_tk)
#         else:
#             names_from_db = [_['name'] for _ in query2]
#             if not name in names_from_db:#если имя не совпадает
#                 list_other_names = CSQ.custom_request_c(self.db_files,f"""SELECT names.name, t_kards.t_kard_name FROM names INNER JOIN
#                 t_kards ON  t_kards.file_name = names.name WHERE names.nom_data == {nom_data}""")
#                 if not CQT.msgboxgYN(f'Файл уже существует с другим наименованием :\n{pprint.pformat(list_other_names)}.'
#                                  f' \n\n Вероятно это ошибка!\n\n Следует ли '
#                                  f'вносить этому файлу дополнительное имя в БД?',icon = QtWidgets.QMessageBox.Warning):
#                     return
#                 # занести
#                 add_name(nom_data, name, F.now("%Y-%m-%d %H-%M"), F.user_name())
#                 add_tkart(name, nom_tk)
#                 pass
#             else:#если имя совпадает
#                 add_tkart(name, nom_tk)
#     return file


@CQT.onerror
def db_files_load(self, name):
    custom_request_c = f"""SELECT reestr.file FROM reestr INNER JOIN names on names.nom_data = reestr.Пномер WHERE names.name == '{name}'"""
    query = CSQ.custom_request_c(self.db_files, custom_request_c,rez_dict=True)
    if len(query) == 0:
        return False
    #return query[1][nk_name]
    put_tmp = CMS.tmp_dir() + os.sep + 'tmp_files'
    if F.existence_file_c(put_tmp):
        F.ochist_papky(put_tmp)
    else:
        F.create_dir_c(put_tmp)
    put_file_tmp = CMS.tmp_dir() + os.sep + 'tmp_files' + os.sep + \
                   str(F.get_time_shtamp_c()).split('.')[-1] + "_" +\
                   F.transliterate(name.replace('ь', ''))
    F.save_binary_convert_to_file(query[0]['file'],put_file_tmp)
    return put_file_tmp


@CQT.onerror
def db_files_del(self,name,nom_tk):
    list_uses_tk = CSQ.custom_request_c(self.db_files,f"""SELECT * FROM t_kards WHERE file_name == '{name}'""",rez_dict=True)
    if len(list_uses_tk) == 1 or len(list_uses_tk) == 0:
        list_uses_names = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM names WHERE name == '{name}'""", rez_dict=True)
        if len(list_uses_names) == 1:
            nom_data = list_uses_names[0]['nom_data']
            datas = CSQ.custom_request_c(self.db_files, f"""SELECT * FROM names WHERE nom_data == '{nom_data}'""", rez_dict=True)
            if len(datas)==1:
                CSQ.custom_request_c(self.db_files, f"""DELETE FROM reestr WHERE Пномер == {nom_data}""")
        CSQ.custom_request_c(self.db_files, f"""DELETE FROM names WHERE name == '{name}'""")
    CSQ.custom_request_c(self.db_files,f"""DELETE FROM t_kards WHERE file_name == '{name}'""")
    return


class mywindow(QtWidgets.QMainWindow):
    resized = QtCore.pyqtSignal()

    def __init__(self):
        super(mywindow, self).__init__()
        self.ui = Ui_MainW()
        self.ui.setupUi(self)
        self.versia = '2.5.6'
        self.NAME_MODULE_BASE = f"Техкарты"
        self.name_module = f'{self.NAME_MODULE_BASE}'
        self.USER_CONFIG: USRCNF.User_config = None
        self.place: USRCNF.Place = None
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        CFG.Config.user_config.load_user_config(self)
        CQT.load_icons(self, 24)
        CQT.connect_to_resize(self, CMS.tmp_dir())
        CMS.add_action_config_save_tbl_filtrs(self, self.ui)

        self.nom_tk = ''
        self.dse_nn = ''
        self.dse_naim = ''
        self.global_param_tk_dxf = ''
        self.mat_kd_erp = ''
        self.glob_tk_title:str = ''
        self.SPIS_PARAMETR_DXF = ['Периметр','Врезы','Площадь']
        self.showMaximized()

        self.db_files = F.bdcfg('BD_files')
        self.db_naryad = F.bdcfg('Naryad')
        self.db_mater = F.bdcfg('nomenklatura_erp')
        self.db_users = F.bdcfg('BD_users')
        self.db_dse = F.bdcfg('BD_dse')
        self.db_resxml = F.bdcfg('db_resxml')
        self.db_kplan = F.bdcfg('DB_kplan')
        self.putf_magaz = F.bdcfg('mag')
        self.PUT_K_TMP = F.put_po_umolch() + os.sep + "tmptehkart"
        self.SET_RUS_WORDS = F.load_file_pickle('summary.pickle')
        self.path_cash_poki = os.path.join(F.scfg('cash'), str(self.place.poki))

        F.test_path()
        self.resized.connect(self.widths) # 10.11.25 конфликт с connect_to_resize
        self.chbox_edit_combos = False
        self.flag_proverka_op = True
        CMS.dict_kod_oper(self, self.db_naryad)
        CMS.dict_professions(self, self.db_users)
        self.DICT_EMPLOEE_FULL = CMS.dict_emploee_full(self.db_users)
        self.LIST_NOMEN = CSQ.custom_request_c(self.db_mater,f"""SELECT * FROM nomen""", rez_dict=True)
        self.DICT_NOMEN = F.deploy_dict_c(self.LIST_NOMEN,'Код')





        tree = self.ui.tree
        tree.setColumnCount(3)
        tree.headerItem().setText(0, QtCore.QCoreApplication.translate("MainW", "Элемент"))
        tree.headerItem().setText(1, QtCore.QCoreApplication.translate("MainW", "Документ"))
        tree.headerItem().setText(2, QtCore.QCoreApplication.translate("MainW", "№"))




        tree.setFocusPolicy(15)
        # tree.itemPressed.connect(self.obnovit_param_tablic)
        tree.doubleClicked.connect(self.spisok)
        tree.itemSelectionChanged.connect(self.obnovit_param_tablic)
        #================TABLES======================
        self.ui.tbl_ii.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_ii_filtr.horizontalScrollBar().setValue)
        tabl = self.ui.tab_op
        hat_c = ['ID', '№', 'Операция', 'Раб.центр', 'Оборудование', 'Тп.з.', 'Тшт.', 'Проф.', 'N раб.', 'КОИД']
        CQT.fill_wtabl([hat_c], tabl, list_column_widths=CMS.load_column_widths(self, tabl))

        tabl.verticalHeader().hide()

        tabl.cellChanged.connect(self.cvet_knopki)
        tabl.cellActivated.connect(self.cvet_knopki)
        CQT.set_color_sort_cell_table_c(tabl)


        tab2 = self.ui.tap_per
        hat_c = ['ID', '№', 'Тшт.']
        CQT.fill_wtabl([hat_c], tab2, list_column_widths=CMS.load_column_widths(self, tab2))

        tab2.verticalHeader().hide()
        tab2.cellChanged.connect(self.cvet_knopki)
        tab2.cellActivated.connect(self.cvet_knopki)
        CQT.set_color_sort_cell_table_c(tab2)

        tab3 = self.ui.tab_kar
        hat_c = ['ID', 'Изменен', 'Разработал', 'Примечание']
        CQT.fill_wtabl([hat_c],tab3,list_column_widths=CMS.load_column_widths(self,tab3))

        tab3.verticalHeader().hide()

        tab3.cellChanged.connect(self.cvet_knopki)
        tab3.cellActivated.connect(self.cvet_knopki)
        CQT.set_color_sort_cell_table_c(tab3)

        tab_per_osn = self.ui.tap_per_osnast

        list_data_osn = [['Оснастка']]
        for i in range(9):
            list_data_osn.append([''])
        CQT.fill_wtabl(list_data_osn, tab_per_osn, list_column_widths=CMS.load_column_widths(self, tab_per_osn),set_editeble_col_nomera={0})
        tab_per_osn.verticalHeader().hide()
        tab_per_osn.cellChanged.connect(self.cvet_knopki)
        tab_per_osn.cellActivated.connect(self.cvet_knopki)


        tab_per_ins = self.ui.tap_per_insrt
        list_data_per_ins = [['Инструмент']]
        for i in range(9):
            list_data_per_ins.append([''])
        CQT.fill_wtabl(list_data_per_ins, tab_per_ins, list_column_widths=CMS.load_column_widths(self, tab_per_ins),set_editeble_col_nomera={0})

        tab_per_ins.verticalHeader().hide()
        tab_per_ins.cellChanged.connect(self.cvet_knopki)
        tab_per_ins.cellActivated.connect(self.cvet_knopki)

        tab_op_doc = self.ui.tab_op_doc
        hat_c = ['Документы']
        CQT.fill_wtabl([hat_c], tab_op_doc, list_column_widths=CMS.load_column_widths(self, tab_op_doc))

        tab_op_doc.verticalHeader().hide()

        tab_op_doc.cellChanged.connect(self.cvet_knopki)
        tab_op_doc.cellActivated.connect(self.cvet_knopki)

        tab_tk_doc = self.ui.tab_tk_doc
        hat_c = ['Документы']
        CQT.fill_wtabl([hat_c], tab_tk_doc, list_column_widths=CMS.load_column_widths(self, tab_tk_doc))

        tab_tk_doc.verticalHeader().hide()

        tab_tk_doc.cellChanged.connect(self.cvet_knopki)
        tab_tk_doc.cellActivated.connect(self.cvet_knopki)

        tab_mk = self.ui.tbl_isp_mk
        tab_mk.setSelectionBehavior(1)
        tab_mk.setSelectionMode(1)
        tab_mk.cellDoubleClicked[int, int].connect(self.zagruzit_tk_from_mk)

        self.ui.tableW_oper_mat.clicked.connect(lambda _, x=self: osn_mat.zagr_sortament(x))

        tab_buf1 = self.ui.t_buff_1
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '1.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '1.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf1, 0, 0, (), (), 200, False, "|", 5)

        tab_buf2 = self.ui.t_buff_2
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '2.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '2.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf2, 0, 0, (), (), 200, False, "|", 5)

        tab_buf3 = self.ui.t_buff_3
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '3.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '3.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf3, 0, 0, (), (), 200, False, "|", 5)

        tab_buf4 = self.ui.t_buff_4
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '4.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '4.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf4, 0, 0, (), (), 200, False, "|", 5)

        tab_buf5 = self.ui.t_buff_5
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '5.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '5.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf5, 0, 0, (), (), 200, False, "|", 5)

        tab_buf6 = self.ui.t_buff_6
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '6.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '6.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf6, 0, 0, (), (), 200, False, "|", 5)

        tab_buf7 = self.ui.t_buff_7
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '7.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '7.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf7, 0, 0, (), (), 200, False, "|", 5)

        tab_buf8 = self.ui.t_buff_8
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '8.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '8.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf8, 0, 0, (), (), 200, False, "|", 5)

        tab_buf9 = self.ui.t_buff_9
        if F.existence_file_c(self.PUT_K_TMP + os.sep + '9.txt'):
            spisok = F.open_file_c(self.PUT_K_TMP + os.sep + '9.txt')
            CQT.fill_wtabl_old_c(mywindow, spisok, tab_buf9, 0, 0, (), (), 200, False, "|", 5)

        self.ui.btn_mag_napolky.clicked.connect(lambda _, x=self: MAGAZ.magazin_na_polky(x))
        self.ui.btn_mag_sbros.clicked.connect(lambda _, x=self: MAGAZ.magazin_na_del(x))
        tbl_magaz = self.ui.tbl_magaz
        tbl_magaz.clicked.connect(lambda _, x=self: MAGAZ.tbl_magaz_click(x))
        self.ui.btn_mag_prim.clicked.connect(lambda _, x=self: MAGAZ.magazin_primenit(x))
        self.ui.btn_mag_up.clicked.connect(lambda _, x=self: MAGAZ.magazin_up(x))
        self.ui.btn_mag_down.clicked.connect(lambda _, x=self: MAGAZ.mag_down(x))
        tbl_magaz.setSelectionBehavior(1)
        tbl_magaz.setSelectionMode(1)
        CQT.set_color_sort_cell_table_c(tbl_magaz)

        self.ui.btn_obnov_sp_mk.clicked.connect(self.nalichie_nevip_mk)

        # Утвержден action
        self.ui.btn_validate.clicked.connect(lambda *_: self.validate_approve())

        butt_op = self.ui.Button_t_op
        butt_op.clicked.connect(self.obnovt_drevo_s_tabl1_op)

        butt_kar = self.ui.Button_t_kar
        butt_kar.clicked.connect(self.obnovt_drevo_s_tabl3_kar)

        butt_per = self.ui.Button_t_per
        butt_per.clicked.connect(self.obnovt_drevo_s_tab2_per)

        butt_sozd = self.ui.pushButton_sozd
        butt_sozd.clicked.connect(self.btn_create_or_edit_tk)
        self.ui.pushButton_sozd.setEnabled(False)

        self.ui.tableW_oper_mat.clicked.connect(self.click_tableW_oper_mat)

        butt_mat = self.ui.Button_prim_mat
        butt_mat.clicked.connect(self.zap_mat_v_tree)

        butt_add_mat = self.ui.Button_create_mater
        butt_add_mat.clicked.connect(self.add_line_mat)

        butt_del_mat = self.ui.Button_del_mater
        butt_del_mat.clicked.connect(self.del_mat)

        butt_load_kod = self.ui.Button_load_kod
        butt_load_kod.clicked.connect(lambda: nomen_erp.zagruz_mat_iz_nomenklatyri(self))


        butt_up = self.ui.pushButton_Vverh
        butt_up.clicked.connect(self.tree_vverh)

        butt_down = self.ui.pushButton_Vniz
        butt_down.clicked.connect(self.tree_vniz)

        butt_copy = self.ui.pushButton_Copy
        self.copy_is_approve = False
        butt_copy.clicked.connect(self.tree_copy)

        butt_paste = self.ui.pushButton_Paste
        butt_paste.clicked.connect(self.tree_paste)

        butt_del = self.ui.pushButton_Del
        butt_del.clicked.connect(self.tree_del)

        butt_vigruz = self.ui.pushButton_vigruzit
        butt_vigruz.clicked.connect(self.vigruzit)

        butt_otm_i_vihod = self.ui.pushButton_otm_i_vihod
        butt_otm_i_vihod.clicked.connect(self.otm_i_vihod)

        btn_vvod_rasch_mat = self.ui.btn_vvod_rez_mat
        btn_vvod_rasch_mat.clicked.connect(lambda _, x=self: osn_mat.vvod_rasch_mat(x))

        self.ui.btn_corr_ok.clicked.connect(lambda _, x=self: CORR.corr_ok(x))

        self.ui.pushButton_save.clicked.connect(self.save_tk_lite)
        self.ui.btn_apply_ii.clicked.connect(lambda: II.apply_row(self))

        self.ui.btn_copy_nr.clicked.connect(self.btn_copy_nr)
        self.ui.btn_copy_nv.clicked.connect(self.btn_copy_nv)
        self.ui.btn_add_row_edit_mat.clicked.connect(self.edit_mat_add_row)
        self.ui.btn_del_row_edit_mat.clicked.connect(self.edit_mat_del_row)
        #===================== TABLES ====================
        tab_oper_mat = self.ui.tbl_oper_mat
        tab_oper_mat.setSelectionBehavior(1)
        tab_oper_mat.clicked.connect(self.obnovit_mater_tabl)

        tab_oper_mat_red = self.ui.tableW_oper_mat
        self.tab_oper_mat_red_hat_c = ['Код', 'Материал', 'Ед.Изм', 'Норма']
        tab_oper_mat_red.setColumnCount(4)
        tab_oper_mat_red.setHorizontalHeaderLabels(self.tab_oper_mat_red_hat_c)

        tab = self.ui.tabW
        tab.currentChanged[int].connect(self.tab_click)

        tab_razr = self.ui.tabWidget
        tab_razr.currentChanged.connect(self.change_tab)

        self.ui.tabWidget.setTabEnabled(CQT.number_table_by_name_c(self.ui.tabWidget,"Разработка"), False)
        self.ui.tabWidget.setTabEnabled(CQT.number_table_by_name_c(self.ui.tabWidget,'Рейтинг ТК'), False)

        self.ui.comboBox_liter.addItems(F.open_file_c(F.tcfg('liter'),propuski=True))

        tabl_bd = self.ui.tblw_dse
        tabl_bd.clicked.connect(lambda _, x=False: self.vibor_dse(x))
        tabl_bd.cellChanged.connect(self.tex_zametki)
        tabl_bd.setSelectionBehavior(1)
        tabl_bd.setSelectionMode(1)
        self.ui.tblw_dse.horizontalScrollBar().valueChanged.connect(
            self.ui.tblw_dse_find.horizontalScrollBar().setValue)

        self.ui.tbl_mat_edit.cellChanged[int,int].connect(self.edit_tbl_mat)
        #============================================================
        # self.load_nomen() # 10.11.25 Дубликат без ссылок (замедлял время запуска)

        btn_prim_izm_shablon = self.ui.btn_prim_shablon_op
        btn_prim_izm_shablon.clicked.connect(self.btn_prim_izm_shablon)

        btn_open_docs = self.ui.btn__open_docs
        btn_open_docs.clicked.connect(self.zapusk_docs)


        self.ui.opt_but_list.clicked.connect(lambda _, x=self: osn_mat.mat_list_load(x))
        self.ui.opt_but_krug.clicked.connect(lambda _, x=self: osn_mat.mat_krug_load(x))
        self.ui.opt_but_truba.clicked.connect(lambda _, x=self: osn_mat.mat_truba_load(x))
        self.ui.opt_but_ygol.clicked.connect(lambda _, x=self: osn_mat.mat_ygol_load(x))
        self.ui.opt_but_shvel.clicked.connect(lambda _, x=self: osn_mat.mat_shvel_load(x))
        self.ui.opt_but_dvut.clicked.connect(lambda _, x=self: osn_mat.mat_dvut_load(x))
        self.ui.opt_but_truba_kv.clicked.connect(lambda _, x=self: osn_mat.mat_truba_kv_load(x))
        self.ui.opt_but_kv.clicked.connect(lambda _, x=self: osn_mat.mat_kv_load(x))
        self.ui.opt_but_shestig.clicked.connect(lambda _, x=self: osn_mat.mat_shestigr_load(x))

        action_docs = self.ui.action_Docs
        action_docs.triggered.connect(self.zapusk_docs)

        action_dse = self.ui.action_reload_dse
        action_dse.triggered.connect(self.obnov_dse)

        action_obn_mat_erp = self.ui.action_sinc_mat
        action_obn_mat_erp.triggered.connect(lambda: nomen_erp.obn_mat_erp_file(self.db_mater))

        action_unlock_tk = self.ui.action_unlock_tk
        action_unlock_tk.triggered.connect(self.unlock_tk)
        # ===============CMB=============
        self.ui.cmb_mat_tbl.currentTextChanged.connect(self.select_tbl_mat_edit)


        #===================================
        # ==== БД файлов

        CMS.dict_opers(self, self.db_naryad)
        self.DICT_OPERS = self.DICT_OPER_FULL
        spis_op = []
        for oper in self.DICT_OPERS:
            spis_op.append([oper,
                            100,
                            F.valm(self.DICT_OPERS[oper]['Tpz']),
                            self.DICT_OPERS[oper]['Vars']])
        self.spis_op = spis_op
        self.app_icons()
        self.obnov_dse()

        self.xl_formulas = CXLF.XlFormula(self)
        # self.ui.pushButton_load_doc.clicked.connect(self.dob_doc)
        # self.ui.pushButton_view_doc.clicked.connect(self.opn_doc)

        self.operation_docs = TOD.OperationDocs(window=self, main_tbl=self.ui.tableWidget)
        self.ui.tree.itemSelectionChanged.connect(self.operation_docs.fill_docs_table)
        self.ui.pushButton_prosm_doc.clicked.connect(self.operation_docs.show_modal)


        #II.fill_table(self)
    def set_glob_tk_title(self,val:str):
        self.glob_tk_title = val
        self.ui.lbl_glob_tk_title.setText(self.glob_tk_title)

    def is_valid_row_approve(self):
        return bool(re.match(r'^[А-ЯЁ]{3}', self.ui.lineEdit_prover.text()))

    def validate_approve(self):
        if self.is_valid_row_approve():
            CQT.msgbox('Техкарта уже утверждена')
            return
        if not CMS.user_access(self.db_naryad, 'тк_утверждение_тк', F.user_name()):
            return
        if not len(F.user_full_namre().split(' ')) ==3:
            return
        tech_card = CMS.Techkards(self.ui.lineEdit_dse.text(), self.db_dse)
        sur_name = F.user_full_namre().split(' ')[0].upper()
        if not tech_card.save_approve(sur_name):
            return
        self.ui.lineEdit_prover.setText(sur_name)


    @CQT.onerror
    def app_icons(self):
        # from PyQt5.QtGui import QIcon
        # from PyQt5.QtWidgets import QApplication, QStyle
        self.ui.pushButton_sozd.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon)))
        self.ui.pushButton_sozd.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_vigruzit.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DriveFDIcon)))
        self.ui.pushButton_vigruzit.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn__open_docs.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DesktopIcon)))
        self.ui.btn__open_docs.setIconSize(QtCore.QSize(16, 16))
        self.ui.pushButton_save.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton )))
        self.ui.pushButton_save.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_Vverh.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp)))
        self.ui.pushButton_Vverh.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_Vniz.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown)))
        self.ui.pushButton_Vniz.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_Copy.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder)))
        self.ui.pushButton_Copy.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_Paste.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogEnd)))
        self.ui.pushButton_Paste.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_Del.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton)))
        self.ui.pushButton_Del.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_otm_i_vihod.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_MessageBoxCritical)))
        self.ui.pushButton_otm_i_vihod.setIconSize(QtCore.QSize(32, 32))
        self.ui.pushButton_prosm_doc.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView)))
        self.ui.pushButton_prosm_doc.setIconSize(QtCore.QSize(32, 32))
        self.ui.Button_t_kar.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)))
        self.ui.Button_t_kar.setIconSize(QtCore.QSize(32, 32))
        self.ui.Button_t_op.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)))
        self.ui.Button_t_op.setIconSize(QtCore.QSize(32, 32))
        self.ui.Button_t_per.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)))
        self.ui.Button_t_per.setIconSize(QtCore.QSize(32, 32))
        self.ui.Button_create_mater.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder)))
        self.ui.Button_create_mater.setIconSize(QtCore.QSize(32, 32))
        self.ui.Button_del_mater.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton)))
        self.ui.Button_del_mater.setIconSize(QtCore.QSize(32, 32))
        self.ui.Button_prim_mat.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)))
        self.ui.Button_prim_mat.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn_prim_shablon_op.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)))
        self.ui.btn_prim_shablon_op.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn_mag_prim.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_MediaSeekBackward)))
        self.ui.btn_mag_prim.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn_mag_napolky.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_MediaSkipForward)))
        self.ui.btn_mag_napolky.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn_mag_up.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp)))
        self.ui.btn_mag_up.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn_mag_down.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown)))
        self.ui.btn_mag_down.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn_mag_sbros.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_BrowserStop)))
        self.ui.btn_mag_sbros.setIconSize(QtCore.QSize(32, 32))

    @CQT.onerror
    def is_edge_operation(self): #30.09.25
        current_row = self.ui.tab_op.currentRow()
        row_count = self.ui.tab_op.rowCount() - 1
        if not self.ogr_rezim():
            return False
        QtWidgets.QTableWidget().rowCount()
        if current_row == 0 or current_row == row_count:
            return True
        return False

    @CQT.onerror
    def is_naryad_operation(self): #01.10.25
        if not self.ogr_rezim():
            return False
        num_mk = self.ui.tbl_isp_mk.property('current_mk')
        tbl_operation = self.ui.tab_op
        current_row = tbl_operation.currentRow()
        oper_name = CQT.valt(tbl_operation, 'Операция', current_row)
        oper_num = CQT.valt(tbl_operation, '№', current_row)
        full_oper_name = f"{oper_num}${oper_name}"
        full_name_dse = f'{self.dse_naim}${self.dse_nn}'
        response = CSQ.custom_request_c(
            USRCNF.Config.project.db_naryad,
            f'''
                SELECT * 
                FROM naryad 
                WHERE Операции LIKE "%{full_oper_name}%" 
                    AND ДСЕ LIKE "%{full_name_dse}%"
                    AND Номер_мк = {num_mk}
            ''',
            rez_dict=True
        )
        if response in (False, None):
            return False
        for naryad in response:
            nar_obj = CMS.Naryads(naryad)
            for param in nar_obj.params:
                full_oper_name_naryad = '$'.join((param['Операции_номер'], param['Операции_имя']))
                if param['ДСЕ'] == full_name_dse and full_oper_name_naryad == full_oper_name:
                    return True
        return False


    @CQT.onerror
    def keyReleaseEvent(self, e):
        if e.key() == 80 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.refill_tbl_into_msgbox_get_table(self,QtWidgets.QApplication.focusWidget())
        if e.key() == QtCore.Qt.Key_C and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())
        if self.ui.lineEdit_nntk.hasFocus():
            if e.key() == QtCore.Qt.Key_Return:
                row =self.ui.tblw_dse.currentRow()
                if row ==-1:
                    return
                nk_dse = CQT.num_col_by_name_c(self.ui.tblw_dse,'Номенклатурный_номер')
                nk_name_dse = CQT.num_col_by_name_c(self.ui.tblw_dse, 'Наименование')
                nk_tk = CQT.num_col_by_name_c(self.ui.tblw_dse, 'Номер_техкарты')
                nk_pnom = CQT.num_col_by_name_c(self.ui.tblw_dse, 'Пномер')
                dse = self.ui.tblw_dse.item(row,nk_dse).text()
                dse_name = self.ui.tblw_dse.item(row, nk_name_dse).text()
                tk = self.ui.tblw_dse.item(row, nk_tk).text()
                new_name = self.ui.lineEdit_nntk.text().strip()
                if tk == new_name:
                    return
                pnom = self.ui.tblw_dse.item(row, nk_pnom).text()
                if CQT.msgboxgYN(f'Заменить для {dse} {dse_name} номер {tk} на {new_name} ?'):
                    ima_file = tk + '_' + tk + ".pickle"
                    if F.existence_file_c(F.scfg("add_docs")) == False:
                        CQT.msgbox('Не найден каталог с ТК')
                        return
                    if F.existence_file_c(F.scfg("add_docs") + os.sep + ima_file):
                        if not CQT.msgboxgYN(f'Файл с техкартой {ima_file} уже создан.\n'
                                      f'продолжаем?'):
                            return
                    CSQ.custom_request_c(self.db_dse,f"""UPDATE dse SET Номер_техкарты = "{new_name}" WHERE Пномер = {int(pnom)}""")
                    self.ui.tblw_dse.item(row, nk_tk).setText(new_name)
                    CQT.msgbox(f'Успешно')
        item = self.ui.tree.currentItem()
        # t#odo РАЗРЕШИТЬ ПЕРЕХОДЫ?
        # t#odo РАЗРЕШИТЬ ОБОРУДОВАНИЕ, ДОКУМЕНТЫ, ОСНАСТКУ ИНСТРУМЕНТ
        if e.key() == QtCore.Qt.Key_Return:
            if self.ui.tbl_ii_filtr.hasFocus():
                CMS.apply_filtr_c(self, self.ui.tbl_ii_filtr, self.ui.tbl_ii)
            if self.ui.tbl_magaz_filtr.hasFocus():
                CMS.apply_filtr_c(self, self.ui.tbl_magaz_filtr, self.ui.tbl_magaz)
            if self.ui.tblw_dse_find.hasFocus():
                CMS.apply_filtr_c(self, self.ui.tblw_dse_find, self.ui.tblw_dse)
            if self.ui.tbl_mat_edit_filtr.hasFocus():
                CMS.apply_filtr_c(self, self.ui.tbl_mat_edit_filtr, self.ui.tbl_mat_edit)
            if self.ui.tbl_formulas_filtr.hasFocus():
                CMS.apply_filtr_c(self, self.ui.tbl_formulas_filtr, self.ui.tbl_formulas)
        if self.ui.tblw_dse.hasFocus():
            if e.key() == QtCore.Qt.Key_F5:
                self.obnov_dse()
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                nk_teg = CQT.num_col_by_name_c(self.ui.tblw_dse, 'Теги')
                if self.ui.tblw_dse.currentColumn() == nk_teg:
                    nk_tk = CQT.num_col_by_name_c(self.ui.tblw_dse, 'Номер_техкарты')
                    nom_row = self.ui.tblw_dse.currentRow()
                    #CSQ.update_bd_sql(self.db_naryad, 'dse', {'Теги': self.ui.tblw_dse.item(nom_row, nk_teg).text()},
                    #                  {'Номер_техкарты': self.ui.tblw_dse.item(nom_row, nk_tk).text()})
                    CSQ.custom_request_c(self.db_naryad,f"""UPDATE dse SET Теги = '{self.ui.tblw_dse.item(nom_row, nk_teg).text()}' 
                    WHERE Номер_техкарты = '{self.ui.tblw_dse.item(nom_row, nk_tk).text()}';""")
        if self.ui.tbl_magaz.hasFocus():
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                MAGAZ.update_magaz(self)
        if self.ui.tap_per.hasFocus():
            if e.modifiers() == QtCore.Qt.ControlModifier and  e.key() == QtCore.Qt.Key_Return:
                if self.ui.tap_per.currentColumn() == 2:
                    self.obnovt_drevo_s_tab2_per()

        if self.ui.tap_per_osnast.hasFocus():
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                cu = self.ui.tap_per_osnast
                if cu.rowCount() == 0:
                    return
                print("Нажата клавиша <Enter>")
                self.w2 = mywindow2(self, cu, "Оснастка", cu.currentRow())
                self.w2.showNormal()
                if cu.item(cu.currentRow(), 0) != None:
                    self.w2.ui2.lineEdit.setText(cu.item(cu.currentRow(), 0).text())
                self.w2.ui2.lineEdit.setFocus()
        if self.ui.tap_per_insrt.hasFocus():
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                cu = self.ui.tap_per_insrt
                if cu.rowCount() == 0:
                    return
                print("Нажата клавиша <Enter>")
                self.w2 = mywindow2(self, cu, "Инструмент", cu.currentRow())
                self.w2.showNormal()
                if cu.item(cu.currentRow(), 0) != None:
                    self.w2.ui2.lineEdit.setText(cu.item(cu.currentRow(), 0).text())
                self.w2.ui2.lineEdit.setFocus()
        if self.ui.tbl_oper_mat.hasFocus():
            if e.key() == QtCore.Qt.Key_F5:
                print("Нажата клавиша <F5>")
                self.add_line_mat()
            if e.key() == QtCore.Qt.Key_Return:
                self.ui.tableW_oper_mat.setFocus()
                return
            if e.key() == QtCore.Qt.Key_Up or e.key() == QtCore.Qt.Key_Down:
                self.obnovit_mater_tabl()
        if self.ui.tableW_oper_mat.hasFocus():
            tab = self.ui.tableW_oper_mat
            if e.key() == QtCore.Qt.Key_Escape:  # esc
                self.ui.tbl_oper_mat.setFocus()
            if e.key() == QtCore.Qt.Key_F5:
                print("Нажата клавиша <F5>")
                self.add_line_mat()
            if e.key() == QtCore.Qt.Key_Delete:
                print("Нажата клавиша <Del>")
                self.del_mat()
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                print("Нажата клавиша <Enter>")
                if tab.rowCount() == 0:
                    return
                self.w2 = mywindow2(self, self.ui.tree, "Материал")
                self.w2.showNormal()
                self.w2.ui2.lineEdit.setFocus()
            if e.key() == QtCore.Qt.Key_S or e.key() == 1067:
                if e.modifiers() == QtCore.Qt.AltModifier:
                    print("Нажата клавиша <alt + Enter>")
                    self.zap_mat_v_tree()
        if self.ui.tab_op.hasFocus():
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                if self.ui.tab_op.currentRow() == None:
                    return
                if self.ui.tab_op.currentColumn() == 3:
                    if self.is_edge_operation(): #30.09.25
                        return CQT.msgbox('Нельзя менять РЦ в первой или последней операции в подмаршрутной техкарте')
                    if self.is_naryad_operation(): #01.10.25
                        return CQT.msgbox('Нельзя менять РЦ в операции, которая уже участвует в наряде')
                    self.w2 = mywindow2(self, self.ui.tree, "Раб_ц")
                    self.w2.showNormal()
                    self.w2.ui2.lineEdit.setFocus()
                if self.ui.tab_op.currentColumn() == 4:
                    self.w2 = mywindow2(self, self.ui.tree, "Оборудование")
                    self.w2.showNormal()
                    self.w2.ui2.lineEdit.setFocus()
                if self.ui.tab_op.currentColumn() == 7:
                    self.w2 = mywindow2(self, self.ui.tree, "Профессия")
                    self.w2.showNormal()
                    self.w2.ui2.lineEdit.setFocus()
            if e.modifiers() == QtCore.Qt.AltModifier:
                if e.key() == QtCore.Qt.Key_S or e.key() == 1067:
                    self.obnovt_drevo_s_tabl1_op()
                if e.key() == QtCore.Qt.Key_Down :
                    self.ui.tab_op_doc.setFocus()
        if self.ui.tab_op_doc.hasFocus():
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                if self.ui.tab_op_doc.currentRow() == None:
                    return
                if self.ui.tab_op_doc.rowCount() > 0:
                    if self.ui.tab_op_doc.currentRow() > 0:
                        if self.ui.tab_op_doc.item(self.ui.tab_op_doc.currentRow() - 1, 0) == None \
                                or self.ui.tab_op_doc.item(self.ui.tab_op_doc.currentRow() - 1, 0).text() == '':
                            CQT.msgbox("Не заполенена предыдушая запись")
                            return
                self.w2 = mywindow2(self, self.ui.tree, "Док_оп")
                self.w2.showNormal()
                self.w2.ui2.lineEdit.setFocus()
            if e.modifiers() == QtCore.Qt.AltModifier:
                if e.key() == QtCore.Qt.Key_Up:
                    self.ui.tab_op.setFocus()
                if e.key() == QtCore.Qt.Key_S or e.key() == 1067:
                    self.obnovt_drevo_s_tabl1_op()
        if self.ui.tab_tk_doc.hasFocus():
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
                if self.ui.tab_tk_doc.currentRow() == None:
                    return
                self.w2 = mywindow2(self, self.ui.tree, "Док_тк")
                self.w2.showNormal()
                self.w2.ui2.lineEdit.setFocus()
                return
            if e.modifiers() == QtCore.Qt.AltModifier:
                if e.key() == QtCore.Qt.Key_Up :
                    self.ui.tab_kar.setFocus()

        # =====клавиши из древа
        if self.ui.tree.hasFocus():
            # =====================================ограничение по режиму
            if self.ogr_rezim() == False:
                if e.key() == QtCore.Qt.Key_Delete:
                    self.tree_del()
                if int(e.modifiers()) == QtCore.Qt.ControlModifier:
                    if e.key() == QtCore.Qt.Key_C or e.key() == 67:
                        self.tree_copy_buf_n(self.ui.t_buff_0)
                    if e.key() == QtCore.Qt.Key_V or e.key() == 86:
                        self.tree_paste_buf_n(self.ui.t_buff_0)
                if int(e.modifiers()) == 100663296:# ctrl+shift
                    if e.key() == 33:
                        self.tree_copy_buf_n(self.ui.t_buff_1)
                        self.sohran_buff(1, self.ui.t_buff_1)
                    if e.key() == 50:
                        self.tree_copy_buf_n(self.ui.t_buff_2)
                        self.sohran_buff(2, self.ui.t_buff_2)
                    if e.key() == 35 or e.key() == 8470:
                        self.tree_copy_buf_n(self.ui.t_buff_3)
                        self.sohran_buff(3, self.ui.t_buff_3)
                    if e.key() == 36 or e.key() == 59:
                        self.tree_copy_buf_n(self.ui.t_buff_4)
                        self.sohran_buff(4, self.ui.t_buff_4)
                    if e.key() == 37:
                        self.tree_copy_buf_n(self.ui.t_buff_5)
                        self.sohran_buff(5, self.ui.t_buff_5)
                    if e.key() == 94:
                        self.tree_copy_buf_n(self.ui.t_buff_6)
                        self.sohran_buff(6, self.ui.t_buff_6)
                    if e.key() == 38 or e.key() == 63:
                        self.tree_copy_buf_n(self.ui.t_buff_7)
                        self.sohran_buff(7, self.ui.t_buff_7)
                    if e.key() == 42:
                        self.tree_copy_buf_n(self.ui.t_buff_8)
                        self.sohran_buff(8, self.ui.t_buff_8)
                    if e.key() == 40:
                        self.tree_copy_buf_n(self.ui.t_buff_9)
                        self.sohran_buff(9, self.ui.t_buff_9)
                if int(e.modifiers()) == QtCore.Qt.ControlModifier:
                    if e.key() == 49:
                        self.tree_paste_buf_n(self.ui.t_buff_1)
                    if e.key() == 50:
                        self.tree_paste_buf_n(self.ui.t_buff_2)
                    if e.key() == 51:
                        self.tree_paste_buf_n(self.ui.t_buff_3)
                    if e.key() == 52:
                        self.tree_paste_buf_n(self.ui.t_buff_4)
                    if e.key() == 53:
                        self.tree_paste_buf_n(self.ui.t_buff_5)
                    if e.key() == 54:
                        self.tree_paste_buf_n(self.ui.t_buff_6)
                    if e.key() == 55:
                        self.tree_paste_buf_n(self.ui.t_buff_7)
                    if e.key() == 56:
                        self.tree_paste_buf_n(self.ui.t_buff_8)
                    if e.key() == 57:
                        self.tree_paste_buf_n(self.ui.t_buff_9)
                if e.key() == QtCore.Qt.Key_F5:
                    print("Нажата клавиша <F5>")
                    self.dobav_V_tree_root(self.ui.tree.topLevelItemCount() + 1)
                    if '*' not in self.glob_tk_title:
                        self.set_glob_tk_title(self.glob_tk_title + '*')
                    # self.obnovit_param_tabl_kar()
                if e.key() == QtCore.Qt.Key_F6:
                    print("Нажата клавиша <F6>")

                    if item == None:
                        return
                    if item.text(item.columnCount() - 1) == "0":
                        level_c = item.text(3)
                        self.dobav_V_tree_oper(item, level_c)
                    if item.text(item.columnCount() - 1) == "1":
                        level_c = item.parent().text(3)
                        self.dobav_V_tree_oper(item.parent(), level_c)
                    self.obnovit_param_tabl_oper()
                    if '*' not in self.glob_tk_title:
                        self.set_glob_tk_title(self.glob_tk_title + '*')
            # =====================================ограничение по режиму

            if e.key() == QtCore.Qt.Key_F7:
                print("Нажата клавиша <F7>")
                item = self.ui.tree.currentItem()
                if item == None:
                    return
                if item.text(item.columnCount() - 1) == "1":
                    level_c = item.text(3)
                    self.dobav_V_tree_perex(item, level_c)
                if item.text(item.columnCount() - 1) == "2":
                    level_c = item.parent().text(3)
                    self.dobav_V_tree_perex(item.parent(), level_c)
                if '*' not in self.glob_tk_title:
                    self.set_glob_tk_title(self.glob_tk_title + '*')
            if e.modifiers() == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:  # ввод через интер операции перехода карты
                self.w2 = mywindow2(self, self.ui.tree, "Древо")
                self.w2.showNormal()
                if self.ui.tree.currentItem() == None:
                    return
                self.w2.ui2.lineEdit.setText(self.ui.tree.currentItem().text(0))

                for i in range(self.w2.ui2.combo2.count()):
                    if self.ui.tree.currentItem().text(0) == self.w2.ui2.combo2.itemText(i).split(' / ')[0]:
                        self.w2.ui2.combo2.setCurrentIndex(i)
                        self.w2.vibor_elem2()
                        break

                self.w2.ui2.lineEdit.setFocus()

            if e.modifiers() == QtCore.Qt.AltModifier:  # ввод доп данных
                item = self.ui.tree.currentItem()
                if item == None:
                    return
                if item.text(item.columnCount() - 1) == "0":
                    if e.key() == QtCore.Qt.Key_D or e.key() == 1042:
                        cu = self.ui.tab_tk_doc
                        for i in range(cu.rowCount() - 1):
                            if cu.item(i, 0) == None or cu.item(i, 0).text() == "":
                                cu.selectRow(i)
                                break
                        self.w2 = mywindow2(self, cu, "Док_тк", cu.currentRow())
                        self.w2.showNormal()
                        if cu.item(cu.currentRow(), 0) != None:
                            self.w2.ui2.lineEdit.setText(cu.item(cu.currentRow(), 0).text())
                    if e.key() == QtCore.Qt.Key_S or e.key() == 1067:
                        self.obnovt_drevo_s_tabl3_kar()
                        return
                if item.text(item.columnCount() - 1) == "1":
                    if e.key() == QtCore.Qt.Key_D or e.key() == 1042:
                        cu = self.ui.tab_op_doc
                        for i in range(cu.rowCount() - 1):
                            if cu.item(i, 0) == None or cu.item(i, 0).text() == "":
                                cu.selectRow(i)
                                break
                        self.w2 = mywindow2(self, cu, "Док_оп", cu.currentRow())
                        self.w2.showNormal()
                        if cu.item(cu.currentRow(), 0) != None:
                            self.w2.ui2.lineEdit.setText(cu.item(cu.currentRow(), 0).text())
                    if e.key() == QtCore.Qt.Key_S or e.key() == 1067:
                        self.obnovt_drevo_s_tabl1_op()
                        return
                if item.text(item.columnCount() - 1) == "2":
                    if e.key() == QtCore.Qt.Key_Q or e.key() == 1049:
                        cu = self.ui.tap_per_osnast
                        for i in range(cu.rowCount() - 1):
                            if cu.item(i, 0) == None or cu.item(i, 0).text() == "":
                                cu.selectRow(i)
                                break
                        self.w2 = mywindow2(self, cu, "Оснастка", cu.currentRow())
                        self.w2.showNormal()
                        if cu.item(cu.currentRow(), 0) != None:
                            self.w2.ui2.lineEdit.setText(cu.item(cu.currentRow(), 0).text())
                        # self.w2.ui2.lineEdit.setFocus()
                    if e.key() == QtCore.Qt.Key_W or e.key() == 1062:
                        cu = self.ui.tap_per_insrt
                        for i in range(cu.rowCount() - 1):
                            if cu.item(i, 0) == None or cu.item(i, 0).text() == "":
                                cu.selectRow(i)
                                break
                        self.w2 = mywindow2(self, cu, "Инструмент", cu.currentRow())
                        self.w2.showNormal()
                        if cu.item(cu.currentRow(), 0) != None:
                            self.w2.ui2.lineEdit.setText(cu.item(cu.currentRow(), 0).text())
                        # self.w2.ui2.lineEdit.setFocus()
                    if e.key() == QtCore.Qt.Key_S or e.key() == 1067:
                        self.obnovt_drevo_s_tab2_per()
                        return
            return

        # ==движение по вкладкам и таблицам
        if e.modifiers() == QtCore.Qt.AltModifier:
            if e.key() == QtCore.Qt.Key_Z or e.key() == 1071:
                self.ui.tree.setFocus()
                self.ui.tabW.setCurrentIndex(0)
            if e.key() == QtCore.Qt.Key_X or e.key() == 1063:
                if item.text(item.columnCount() - 1) == "0":
                    self.ui.tab_kar.setFocus()
                if item.text(item.columnCount() - 1) == "1":
                    self.ui.tab_op.setFocus()
                if item.text(item.columnCount() - 1) == "2":
                    self.ui.tap_per.setFocus()
                self.ui.tabW.setCurrentIndex(0)
            if e.key() == QtCore.Qt.Key_C or e.key() == 1057:
                self.ui.tbl_oper_mat.setFocus()
                self.ui.tabW.setCurrentIndex(1)
            if e.key() == QtCore.Qt.Key_V or e.key() == 1052:
                self.ui.tabW.setCurrentIndex(2)
            if self.ui.tap_per.hasFocus():
                if e.key() == QtCore.Qt.Key_Down or e.key() == 16777237:
                    self.ui.tap_per_osnast.setFocus()
                    return
            if self.ui.tap_per_osnast.hasFocus():
                if e.key() == QtCore.Qt.Key_Down or e.key() == 16777237:
                    self.ui.tap_per_insrt.setFocus()
                    return
                if e.key() == QtCore.Qt.Key_Up or e.key() == 16777235:
                    self.ui.tap_per.setFocus()
                    return
            if self.ui.tap_per_insrt.hasFocus():
                if e.key() == QtCore.Qt.Key_Up or e.key() == 16777235:
                    self.ui.tap_per_osnast.setFocus()
                    return
            if self.ui.tab_kar.hasFocus():
                if e.key() == QtCore.Qt.Key_Down or e.key() == 16777237:
                    self.ui.tab_tk_doc.setFocus()
                    return
        return

    @CQT.onerror
    def change_tab(self,*args):
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget,'Номенклатура'):
            self.ui.tblw_dse.setEnabled(True)
        if self.ui.tabWidget.currentIndex() != CQT.number_table_by_name_c(self.ui.tabWidget,'Разработка'):
            if '*' in self.glob_tk_title:
                self.save_tk_vklad()
            else:
                n_dse = self.ui.lineEdit_dse
                naim_dse = self.ui.lineEdit_dse_naim
                self.unblock_tk(naim_dse.text(), n_dse.text())
                self.dse_nn = ''
                self.dse_naim = ''

        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget,'Корректировка'):
            CORR.load(self)
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget,'Извещения об изменении'):
            II.fill_table(self)
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget,'Рейтинг ТК'):
            return
            #self.fill_calc_reiting_tk()  Выключено до момента доработки от руководитея ТО методики оценки работников (генерация в рейтинге)
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget,'Материалы'):
            list_tbls = CSQ.get_list_of_tables_c(self.db_mater)
            try:
                list_tbls.remove('name')
                list_tbls.insert(0,'')
            except ValueError:
                pass
            CQT.clear_tbl(self.ui.tbl_mat_edit) #29.08.25
            CQT.clear_tbl(self.ui.tbl_mat_edit_filtr)
            self.ui.cmb_mat_tbl.blockSignals(True)
            self.ui.cmb_mat_tbl.clear()
            self.ui.cmb_mat_tbl.addItems(list_tbls)
            self.ui.cmb_mat_tbl.blockSignals(False)
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Управление формулами'):
            self.xl_formulas.fill_table()


    def fill_calc_reiting_tk(self):
        def generate_table(month,dict_users):
            rab_dney = dict_users[month]['rab_dn']
            norma_tk_per_month = rab_dney*NORM_TK_PER_DAY
            rez = [['ФИО','Удельных ТК, шт.',f'{month} Премия, %']]
            for user in dict_users[month]['users']:
                if True:
                    koef_normi = dict_users[month]['users'][user]['дсе']/norma_tk_per_month
                    if koef_normi < 1:
                        koef_normi = 1
                    summ = base_without_tk
                    for param in dict_users[month]['users'][user]:
                        if param in DICT_PRICE:
                            summ += DICT_PRICE[param]*dict_users[month]['users'][user][param] * koef_normi
                    prem = (summ-prem_base)/prem_base*100
                    rez.append([user,dict_users[month]['users'][user]['дсе'],round(prem)])
            rez = F.sort_by_column_c(rez,f'{month} Премия, %',revers=True)
            return rez

        EARN_RUB = 60000
        prem_base = EARN_RUB/2
        NORM_TK_PER_DAY = 38
        NORM_TK_PER_DAY_WEEKEND = 73
        koef_time_tk = NORM_TK_PER_DAY/NORM_TK_PER_DAY_WEEKEND
        base_for_tk_rub = prem_base*koef_time_tk
        base_without_tk = EARN_RUB-base_for_tk_rub
        DICT_PRICE = {"документов": 0.022187070972199,
                        "дсе": 11.1327524031065,
                        "инструмента": 0.101440850746027,
                        "материалов": 1.15643983700931,
                        "операций": 0.187266484870431,
                        "оснастки": 0.113789412684957,
                        "переходов": 0.113789412684957
                        }
        self.bd_naryad = self.db_naryad
        self.bd_users = self.db_users
        #dict_users, dict_napr = calc_reiting.list_calc_tehnologs(self)
        dict_users = F.load_file_pickle(r"Z:\Data\dict_users_reit_tk.pickle")
        last_month, current_month = list(dict_users.keys())

        CQT.fill_wtabl( generate_table(current_month,dict_users) ,self.ui.tbl_reit_tk)
        self.ui.lbl_diapaz_reit.setText(current_month)
        CQT.fill_wtabl(generate_table(last_month, dict_users), self.ui.tbl_reit_tk_old)
        self.ui.lbl_diapaz_reit_old.setText(last_month)


    @CQT.onerror
    def tab_click(self, ind,*args):
        print(int)
        self.widths()
        if ind == 1:
            self.obnovit_param_tabl_oper_mat()
        if ind == 2:
            pass
        if ind == 3:
            putf = self.PUT_K_TMP + os.sep + "shablon_op.txt"

            if F.existence_file_c(putf):
                spis_sh = F.open_file_c(putf, False, "|")
            else:
                spis_sh = []
            rez = [['Операция', 'Рабочий ценр', 'Оборудование', 'Профессия', 'Документация($)']]
            for i in range(len(self.spis_op)):
                ima = self.spis_op[i][0]
                rc = ''
                obor = ''
                prof = ''
                doc = ''
                for j in range(1, len(spis_sh)):
                    if ima == spis_sh[j][0]:
                        rc = spis_sh[j][1]
                        obor = spis_sh[j][2]
                        prof = spis_sh[j][3]
                        doc = '' if len(spis_sh[j]) < 5 else spis_sh[j][4]
                        break
                rez.append([ima, rc, obor, prof, doc])
            set_red = {1, 2, 3, 4}
            CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_shablon_op, separ='', isp_hat_c=True,
                             set_editeble_col_nomera=set_red)
        if ind == 4:
            if F.existence_file_c(self.putf_magaz) == False:
                frase_tmp = """CREATE TABLE IF NOT EXISTS blocks(
                   Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
                   Статус INTEGER,
                   Запись TEXT,
                   Вид TEXT,
                   Теги TEXT
                   );
                """
                CSQ.create_db_sql_c(self.putf_magaz, frase_tmp)
            MAGAZ.load_magaz(self)
            CMS.fill_filtr_c(self, self.ui.tbl_magaz_filtr, self.ui.tbl_magaz)


    def add_zapis_jurnal(self,status:str = '',name_dse:str = '',add_ves:bool = True):
        def take_mat_from_db(self, name_dse):
            mat = False
            rez  = CSQ.custom_request_c(self.db_dse,f"""SELECT Материалы FROM dse WHERE Номенклатурный_номер == '{name_dse}';""",hat_c=True)
            if len(rez) == 2:
                mat = rez[-1][0]
            return mat

        if add_ves:
            row = self.ui.tblw_dse.currentRow()
            if row == None or row == -1:
                mat = take_mat_from_db(self,name_dse)
            else:
                nk_name_dse = CQT.num_col_by_name_c(self.ui.tblw_dse,'Номенклатурный_номер')
                nk_mat = CQT.num_col_by_name_c(self.ui.tblw_dse, 'Мат_кд')
                if name_dse == self.ui.tblw_dse.item(row,nk_name_dse).text():
                    mat = self.ui.tblw_dse.item(row,nk_mat).text()
                else:
                    mat = take_mat_from_db(self,name_dse)

            try:
                ves = F.valm(mat.split('/')[0])
            except:
                ves = ''
        else:
            ves = ''
        data_now = F.now()
        fio = F.user_full_namre()
        CSQ.custom_request_c(self.db_dse,f"""INSERT INTO jurnal_td(Дата, ФИО, ДСЕ, Вес, Статус)
                              VALUES (?, ?, ?, ?, ?)""",list_of_lists_c= [[data_now,fio,name_dse,ves,status]])

    def mark_attributes_on_table_data(self, tbl_instance: QtWidgets.QTableWidget,
                                      main_tbl_name: str,
                                      data: list[list],
                                      attaches: str | tuple[str]
        ):
        new_tbl_data = copy.deepcopy(data)
        property = {}
        new_header = []
        if isinstance(new_tbl_data, list) and len(new_tbl_data) >= 1:
            header = new_tbl_data.pop(0)
            for head_name in header:
                split_name = head_name.split('.')
                cleaned_head = head_name
                if len(split_name) == 2:
                    table_name, attr_name = split_name
                    property[attr_name] = table_name
                    cleaned_head = attr_name
                else:
                    table_name = main_tbl_name
                new_header.append(cleaned_head)
                property[cleaned_head] = {
                    'table_name': table_name,
                    'attach_dbs': attaches
                }
            tbl_instance.setProperty(main_tbl_name.encode('utf8'), property)
            new_tbl_data.insert(0, new_header)
        return new_tbl_data


    def select_tbl_mat_edit(self):
        tbl_name = self.ui.cmb_mat_tbl.currentText()
        tbl = self.ui.tbl_mat_edit
        CQT.clear_tbl(tbl)
        CQT.clear_tbl(self.ui.tbl_mat_edit_filtr)
        if tbl_name == '':
            return
        if not CMS.user_access(self.db_naryad,'тк_tbl_mat_view',F.user_name()):  # 11.07.25
            return
        editeble_col_nomera = {} #27.08.25
        attach_dbs = ()
        if tbl_name == 'ТехнологическиеВиды':

            attach_dbs = USRCNF.Config.project.db_kplan
            table_data = CSQ.custom_request_c(
                self.db_mater,
                f"""
                    SELECT 
                        {tbl_name}.Пномер as "{tbl_name}.Пномер",
                         виды_по_направлению.Имя as "виды_по_направлению.Имя", 
                        {tbl_name}.ВидыНоменклатуры as "{tbl_name}.ВидыНоменклатуры", 
                        {tbl_name}.Примечание as "{tbl_name}.Примечание"
                    FROM {tbl_name} 
                    INNER JOIN виды_по_направлению ON виды_по_направлению.Пномер = {tbl_name}.Пномер
                    INNER JOIN napravl_deyat ON виды_по_направлению.Направл = napravl_deyat.Пномер
                    WHERE napravl_deyat.poki = {USRCNF.Config.place.poki} ORDER BY {tbl_name}.Пномер
                """,
                attach_dbs=USRCNF.Config.project.db_kplan
            )
            editeble_col_nomera = {'Примечание', 'Имя'}
        else:
            table_data = CSQ.custom_request_c(self.db_mater,f"""SELECT * FROM {tbl_name};""")
        table_data = self.mark_attributes_on_table_data(tbl, tbl_name, table_data, attach_dbs)
        if table_data == None or table_data == False:
            CQT.msgbox(f'Ошибка загрузки')
            return

        if CMS.user_access(self.db_naryad,'тк_tbl_mat_edit_full',F.user_name(),msg=False):
            if tbl_name == 'nomen':
                editeble_col_nomera = {"П1",
                                       "П2",
                                       "П3",
                                       "П4",
                                       "П5",
                                       "П6",
                                       "П7",}

        CQT.fill_wtabl(table_data,tbl,height_row=20,auto_type=False,set_editeble_col_nomera=editeble_col_nomera)
        self.decor_catalog_configuration_table(ui_table_object=tbl, db_table_name=tbl_name) #27.08.25
        CMS.fill_filtr_c(self,self.ui.tbl_mat_edit_filtr,tbl,hidden_scroll=True)
        CMS.update_width_filtr(tbl,self.ui.tbl_mat_edit_filtr)
        self.ui.tbl_mat_edit.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_mat_edit_filtr.horizontalScrollBar().setValue)

    #++ 27.08.25
    def on_types_attach(self, types_working_instance, window, widget: CQT.InteractiveLabelInstance, tbl, row, col):
        if not CMS.user_access(self.db_naryad,'тк_tbl_mat_edit_full',F.user_name(),msg=False):
            return CQT.msgbox('Нет доступа')
        types_working_instance.on_attach(window=window, row=row, col=col, tbl=tbl)
        nomen_types_column = CQT.num_col_by_name_c(tbl, 'ВидыНоменклатуры')
        item = tbl.item(row, nomen_types_column)
        if item is not None:
            nomen_types = ','.join(n_type for n_type in item.text().split(';') if n_type.strip())
            if not nomen_types:
                return
            result = CSQ.custom_request_c(
                USRCNF.Config.project.db_nomen,
                f'SELECT name FROM ВидыНоменклатуры WHERE s_num IN ({nomen_types})',
                one_column=True,
                hat_c=False
            )
            widget.set_text(', '.join(result))

    def decor_catalog_configuration_table(self, ui_table_object: QtWidgets.QTableWidget, db_table_name: str):
        if db_table_name == 'ТехнологическиеВиды':
            edit_column = CQT.num_col_by_name_c(ui_table_object, 'ВидыНоменклатуры')
            types_working = CMS.TypesWorkingByDirections()
            if edit_column is None:
                return
            window = self
            with QtCore.QSignalBlocker(ui_table_object):
                for row in range(ui_table_object.rowCount()):
                    interactive_widget = CQT.add_interactive_label(ui_table_object, row, edit_column,
                                                                   parent_self=ui_table_object,
                                                                   txt_cut=40)
                    interactive_widget.label.setStyleSheet('border: none;')
                    interactive_widget.add_button(
                        txt_button='📝',
                        tooltip='Редактировать',
                        on_clicked=lambda widget, row, col, *args: self.on_types_attach(types_working, window, widget, row, col, ui_table_object)
                    )
                    item = ui_table_object.item(row, edit_column)
                    nomen_types = ','.join(n_type for n_type in item.text().split(';') if n_type.strip())
                    result = CSQ.custom_request_c(
                        USRCNF.Config.project.db_nomen,
                        f'SELECT name FROM ВидыНоменклатуры WHERE s_num IN ({nomen_types})',
                        one_column=True,
                        hat_c=False
                    )
                    interactive_widget.set_text(', '.join(result))

    #-- 27.08.25
    @CQT.onerror
    def edit_tbl_mat(self,*args):
        if not CMS.user_access(self.db_naryad,'тк_tbl_mat_edit_full',F.user_name(),msg=False):
            return CQT.msgbox('Нет доступа') # 11.07.25
        row,col = args
        tbl_name = self.ui.cmb_mat_tbl.currentText()
        tbl = self.ui.tbl_mat_edit
        new_val = self.ui.tbl_mat_edit.item(row,col).text()
        column_name= tbl.horizontalHeaderItem(col).text()
        table_conf = tbl.property(tbl_name.encode('utf8'))
        table_property = table_conf.get(column_name)
        table_name = table_property.get('table_name')
        attach_dbs = table_property.get('attach_dbs')
        key_col = tbl.horizontalHeaderItem(0).text()
        key = self.ui.tbl_mat_edit.item(row,0).text()
        CSQ.custom_request_c(self.db_mater,
                             f"""UPDATE {table_name} SET {column_name} = ? WHERE {key_col} = ?;""",
                             list_of_lists_c=[[new_val,key]],
                             attach_dbs=attach_dbs)

    @CQT.onerror
    def edit_mat_add_row(self,*args):
        if not CMS.user_access(self.db_naryad,'тк_tbl_mat_edit_full',F.user_name(),msg=False):
            return CQT.msgbox('Нет доступа') # 11.07.25
        tbl_name = self.ui.cmb_mat_tbl.currentText()
        if tbl_name == 'ТехнологическиеВиды':
            CMS.TypesWorkingByDirections().insert_technological_type(type_name='')
        if tbl_name == 'ВидыНоменклатуры':
            gui_instance = CMS.GUITypesNomenclature()
            gui_instance.get_table_choicer_for_insert_nomen_type(self)
        else:
            list_columns = CSQ.list_of_columns_c(self.db_mater,tbl_name)
            CSQ.custom_request_c(self.db_mater,f"""INSERT INTO {tbl_name} ({str(list_columns[1])}) VALUES (?);""",list_of_lists_c=[['']])
        self.select_tbl_mat_edit()

    @CQT.onerror
    def edit_mat_del_row(self,*args):
        CQT.msgbox(f'Отключено')
        return
        if not CMS.user_access(self.db_naryad,'тк_tbl_mat_edit_full',F.user_name(),msg=False):
            return CQT.msgbox('Нет доступа') # 11.07.25
        tbl_name = self.ui.cmb_mat_tbl.currentText()
        tbl = self.ui.tbl_mat_edit
        row = CQT.get_dict_line_form_tbl(tbl)
        if not CQT.msgboxgYN(f'БУдет удалена строка {pprint.pformat(row)} \n\n продолжить?'):
            return
        s_key = next(iter(row))
        s_num =   row[s_key]
        response = CSQ.custom_request_c(self.db_mater,f"""DELETE FROM {tbl_name} WHERE {s_key} = {int(s_num)}""")
        if response and tbl_name == 'ВидыНоменклатуры': #22.09.25
            if CQT.msgboxgYN('Пометить всю привязанную номенклатуру меткой "На удаление"'):
                ref_key = row.get('Ref_Key')
                if not F.is_unique_identifier(ref_key):
                    return
                data_nomen_types = CMS.DATATypesNomenclature()
                data_nomen_types.mark_delete_nomens_by_ref(ref_key) and CQT.msgbox('Успешно')
        self.select_tbl_mat_edit()


    def load_nomen(self):
        custom_request_c = f'''SELECT DISTINCT Вид FROM nomen;'''
        self.nomenclature = CSQ.custom_request_c(self.db_mater, custom_request_c=custom_request_c, hat_c=False)
        if self.nomenclature == None or self.nomenclature == False:
            CQT.msgbox('Ошибка загрузки из БД')
            quit()
        try:
            self.nomenclature.sort()
        except:
            CQT.msgbox(f'БД с номенлатурой имеет некорректное значение в поле "Вид"')
            quit()
        custom_request_c = f'''SELECT * FROM nomen WHERE На_удаление == 0 ;'''
        self.ne_del_nomen = CSQ.custom_request_c(self.db_mater, custom_request_c=custom_request_c, hat_c=True)
        if self.ne_del_nomen == None or self.ne_del_nomen == False:
            CQT.msgbox('Ошибка загрузки из БД')
            quit()

    @CQT.onerror
    def check_lock_db(self, func, conn,cur):
        rez = func
        if rez == False:
            CSQ.close_bd(conn,cur)
            CQT.msgbox(f'Нет доступа к БД попробуй позже')
            quit()



    @CQT.onerror
    def corr_ok(self):
        try:
            list_mk = [int(mk) for mk in self.ui.le_corr_list_mk.text().strip().split(',')]
        except:
            CQT.msgbox('Не прочитать список МК')
            return


    @CQT.onerror
    def load_param_from_dxf(self,sp_tree):
        # ==================DXF==========================
        self.global_param_tk_dxf = ''
        flag = False
        for i in range(len(sp_tree)):
            if len(sp_tree[i]) >= 20:
                if sp_tree[i][20] == '0' and flag:
                    return
                if sp_tree[i][20] == '0' and flag == False:
                    flag = True
                if sp_tree[i][20] == '1'and sp_tree[i][0] == 'Резка(ЧПУ)' and sp_tree[i][4] == '010101':
                    if sp_tree[i][15] != '':
                        file = self.operation_docs.storage.get_dxf(sp_tree[i][15], self.dse_nn) # 10.11.25
                        if file == None or file == False:
                            nom_op = sp_tree[i][2]
                            name_op = sp_tree[i][0]
                            # CQT.msgbox(f'[{nom_op} {name_op}]DXF файл в базе не найден')
                            break
                        dict_rez = CDXF.raschet_dxf(file)
                        if dict_rez != None:
                            self.global_param_tk_dxf = dict_rez
                        else:
                            CQT.msgbox('DXF не корректный, не распознать.')
                        break
        # ===============================================


    @CQT.onerror
    def obnov_dse(self,conn = '', cur = '', *args):
        if CMS.kontrol_ver(self.versia, 'Техкарты') == False:
            quit()
        tabl_bd = self.ui.tblw_dse
        row = False
        if tabl_bd.currentRow() != None and tabl_bd.currentRow() != -1:
            row = tabl_bd.currentRow()
        spis_filtr = CQT.list_from_wtabl_c(self.ui.tblw_dse_find)
        #stroki = CSQ.list_from_db_sql_c(self.db_naryad, 'dse', True, True)

        stroki = CSQ.custom_request_c(self.db_dse,f'''SELECT 
            Пномер, 
            Номенклатурный_номер, 
            Наименование, 
            Номер_техкарты, 
            Примечание, 
            Путь_docs, 
            Доступ, 
            
            Мат_кд, 
            Код_ЕРП, 

            Нр_техн_дет, 
            Нв_техн_раскрой 
         FROM dse WHERE poki == {self.place.poki}''',conn=conn, cur = cur)
        #self.set_kol_bd_dse = {0, 1, 2, 3, 6, 7, 8, 9, 10,11,12,13}

        """ tk = CMS.Techkards('КТ.2209018.03.04.002', self.db_dse)  # 'КЛ.2108001.29.20.001'
        if tk != None:
            tk._update_params_oper(self.DICT_OPERS)
            tk.recalc_opers(['Сварка'],self.DICT_OPERS)
            tk.save_tk()
           
        for dse in stroki[1:]:
            print(
            tk = CMS.Techkards(dse[1], self.db_dse)#'КЛ.2108001.29.20.001'
            if tk != None:
                tk._update_params_oper(self.DICT_OPERS)
                #tk.save_tk()"""

        if stroki == False:
            CQT.msgbox(f'Бд занята')
            return
        # CQT.fill_wtabl_old_c(self, stroki, tabl_bd, 0, {},
        #                  isp_hat_c=True, separ='', max_vis_row=20)
        CQT.fill_wtabl(stroki, tabl_bd, height_row=20, auto_type=False)
        tabl_bd.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # CQT.fill_vtable_c(self,tabl_bd,stroki,isp_hat_c = True, separ= '')
        tabl_bd.setColumnHidden(CQT.num_col_by_name_c(tabl_bd, 'Пномер'), True)
        tabl_bd.setColumnHidden(CQT.num_col_by_name_c(tabl_bd, 'Путь_docs'), True)
        tabl_bd.setColumnHidden(CQT.num_col_by_name_c(tabl_bd, 'Доступ'), True)

        tabl_bd.horizontalHeader().setStretchLastSection(True)
        #CMS.fill_filtr_c(self, self.ui.tblw_dse_find, tabl_bd)
        if row:
            tabl_bd.setCurrentCell(row,0)
        CMS.fill_filtr_c(self, self.ui.tblw_dse_find, tabl_bd,hidden_scroll=True) # 05.06.2025(сообщение в Проект разработка внедрение)
        CMS.update_width_filtr(tabl_bd,self.ui.tblw_dse_find)


    @CQT.onerror
    def tex_zametki(self,*args):
        tbl = self.ui.tblw_dse
        row = tbl.currentRow()
        if row == -1:
            return
        n_k_nn = CQT.num_col_by_name_c(tbl, 'Номенклатурный_номер')
        n_k_texzam = CQT.num_col_by_name_c(tbl, 'Тех_заметки')
        if tbl.currentColumn()== n_k_texzam:
            CSQ.custom_request_c(self.db_naryad,
                   f'''UPDATE dse SET Тех_заметки = "{tbl.item(row, n_k_texzam).text()}" WHERE Номенклатурный_номер = "{tbl.item(row, n_k_nn).text()}"''')


    @CQT.onerror
    def zagruzit_tk_from_mk(self, row, col,*args):
        kol_nom_mk = CQT.num_col_by_name_c(self.ui.tbl_isp_mk, 'Пномер')
        if kol_nom_mk == None:
            return
        nom_mk = self.ui.tbl_isp_mk.item(row, kol_nom_mk).text()
        if not self.vibor_dse(nom_mk):
            return
        self.load_redaktor_tk(nom_mk)
        resource = CMS.load_res(nom_mk) #01.01.25
        self.ui.tbl_isp_mk.setProperty('current_mk', nom_mk)
        self.ui.tbl_isp_mk.setProperty('resource', resource)

        #self.sozd_file(nom_mk)
        self.ui.pushButton_Vverh.setEnabled(False)
        self.ui.pushButton_Vniz.setEnabled(False)
        self.ui.pushButton_Copy.setEnabled(False)
        self.ui.pushButton_Paste.setEnabled(False)
        self.ui.pushButton_Del.setEnabled(False)
        self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget,'Разработка'))
        self.ui.tabWidget.setTabEnabled(CQT.number_table_by_name_c(self.ui.tabWidget,'Разработка'),True)
        # t#odo ОТКЛЮЧИТЬ КОНОПКИ ВВЕРХ,ВНИЗ, ВСТАВИТЬ, УДАЛИТЬ,КОПИРОВАТЬ
        # t#odo ЗАБЛОКИРОВАТЬ РЕДАКТИРОВАНИЕ РАБОЧИХ ЦЕНТРОВ, НАЗВАНИЯ ОПЕРАЦИЙ, НОМЕРВ

    @CQT.onerror
    def ogr_rezim(self):
        if 'по маршрутной карте' in self.glob_tk_title:
            return True
        return False

    @CQT.onerror
    def nalichie_nevip_mk(self,*args):
        tbl_dse = self.ui.tblw_dse
        current_row = tbl_dse.currentRow()
        if current_row == -1: return
        nk_nn = CQT.num_col_by_name_c(tbl_dse,'Номенклатурный_номер')
        nk_naim = CQT.num_col_by_name_c(tbl_dse, 'Наименование')
        nn = tbl_dse.item(tbl_dse.currentRow(),nk_nn).text()
        naim = tbl_dse.item(tbl_dse.currentRow(), nk_naim).text()
        try:
            custom_request_c = f'''
                SELECT mk.Пномер, mk.Дата, mk.Статус, 
                    CASE 
                        WHEN знпр.№ERP IS NOT NULL 
                        THEN знпр.№ERP 
                        ELSE mk.Номер_заказа 
                    END AS Номер_заказа, 
                               
                    CASE 
                        WHEN знпр.№проекта IS NOT NULL 
                        THEN знпр.№проекта 
                        ELSE mk.Номер_проекта 
                    END AS Номер_проекта, 
                    mk.Вид, res.data
                FROM mk 
                INNER JOIN plan ON plan.Пномер = mk.НомКплан 
                INNER JOIN пл_оуп ON plan.Пномер = пл_оуп.НомПл
                INNER JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП
                INNER JOIN res ON res.Номер_мк = mk.Пномер
                WHERE plan.poki = {CFG.Config.place.poki} and mk.Прогресс != "Завершено" AND mk.Статус != "НаУдаление" 
            '''
            spis_mk = CSQ.custom_request_c(
                self.db_naryad,custom_request_c,
                attach_dbs=(self.db_kplan, self.db_resxml),
                rez_dict=True
            )
            spis_mk_rez = [["Пномер","Дата","Статус", "Номер_заказа", "Номер_проекта","Вид"]]
            for mk in spis_mk:
                res = F.from_binary_pickle(mk.get('data'))
                if res == ['']:
                    continue
                for dse in res:
                    if dse.get('Наименование', '').strip() == naim and dse.get('Номенклатурный_номер', '').strip() == nn:
                        spis_mk_rez.append([
                            mk.get('Пномер'),
                            mk.get('Дата'),
                            mk.get('Статус'),
                            mk.get('Номер_заказа'),
                            mk.get('Номер_проекта'),
                            mk.get('Вид')]
                        )
            set_isp_kol = {0, 1, 2, 3, 4, 5}
            CQT.fill_wtabl_old_c(self, spis_mk_rez, self.ui.tbl_isp_mk, isp_hat_c=True, separ='',
                             set_isp_nomera_col=set_isp_kol)
        except Exception as e:
            print(f'[error] - TehKart.nalichie_nevip_mk: {e}')
            CQT.fill_wtabl_old_c(self, [['Ошибка']], self.ui.tbl_isp_mk, isp_hat_c=False, separ='')

    @CQT.onerror
    def zapusk_docs(self,*args):
        tbl = self.ui.tblw_dse
        strok = tbl.currentRow()
        kol_naim = CQT.num_col_by_name_c(tbl, 'Наименование')
        kol_nn = CQT.num_col_by_name_c(tbl, 'Номенклатурный_номер')
        if strok == -1:
            if self.dse_nn == '':
                CQT.msgbox('Не выбрана ТК')
                return
            nn_det = self.dse_nn
            naim =self.dse_naim
        else:
            nn_det = tbl.item(strok, kol_nn).text()
            naim = tbl.item(strok, kol_naim).text()
        CMS.run_link_DOCs_c(nn_det, naim, self.db_dse)
        # F.run_file_c(adres,False)

    @CQT.onerror
    def del_mat(self,*args):
        tab = self.ui.tableW_oper_mat
        tab.removeRow(tab.currentRow())




    @CQT.onerror
    def add_line_mat(self,*args):
        tab = self.ui.tableW_oper_mat
        if tab.rowCount() > 0:
            for i in range(0, tab.columnCount()):
                if tab.item(tab.rowCount() - 1, i) == None:
                    CQT.msgbox("Не заполенена предыдушая запись")
                    return
        list_list = CQT.list_from_wtabl_c(tab,'',hat_c=True)
        list_list.insert(tab.rowCount()+1,['' for _ in list_list[0]])
        set_edit = {F.num_col_by_name_in_hat_c(list_list, 'Код'), F.num_col_by_name_in_hat_c(list_list, 'Норма')}
        CQT.fill_wtabl(list_list,tab,ogr_maxshir_kol=500,set_editeble_col_nomera=set_edit,auto_type=False)
        #tab.setRowCount(tab.rowCount() + 1)

    @CQT.onerror
    def prov_filtr(self, text, stroka, kolonka, spisok, spis_rez):
        if len(text) > 0:
            if text[0] == '!':
                if text[1:] == "*":
                    if str(spisok[stroka][kolonka]) != "":
                        return False
                else:
                    if text[1:] in str(spisok[stroka][kolonka]):
                        return False
            if text[0] == '=':
                for i in range(1, len(spis_rez)):
                    if spis_rez[i][kolonka] == str(spisok[stroka][kolonka]):
                        return False
            if text[0] != '!':
                if text[0] == "*":
                    if str(spisok[stroka][kolonka]) == '':
                        return False
                else:
                    if text.replace('=', '') not in str(spisok[stroka][kolonka]):
                        return False
        return True

    @CQT.onerror
    def otm_i_vihod(self,*args):
        n_dse = self.ui.lineEdit_dse
        n_tk = self.ui.lineEdit_nntk
        naim_dse = self.ui.lineEdit_dse_naim
        ima = n_tk.text() + '_' + n_dse.text() + ".txt"
        tmpf = F.put_po_umolch() + os.sep + "tmp_tk"
        vosst_mk = False
        if 'по маршрутной карте' in self.glob_tk_title:
            vosst_mk = True
            nom_mk = self.glob_tk_title.split('карте ')[-1].replace('*','')
        self.ui.tabWidget.setTabEnabled(1, False)
        self.ui.tabWidget.setCurrentIndex(0)
        if vosst_mk:
            relf = F.scfg('Mk') + os.sep + nom_mk + os.sep + ima.replace('.txt', '.pickle')
        else:
            relf = F.scfg("add_docs") + os.sep + ima.replace('.txt', '.pickle')
        if F.existence_file_c(tmpf):
            rez = F.copy_file_c(tmpf, relf)
            if rez == False:
                print(False)
            F.delete_file_c(tmpf)
        self.unblock_tk(naim_dse.text(), n_dse.text())

    @CQT.onerror
    def cvet_knopki(self,*args):
        tabl = self.ui.tab_op
        tabl_1 = self.ui.tab_op_doc
        tab2 = self.ui.tap_per
        tab21 = self.ui.tap_per_insrt
        tab22 = self.ui.tap_per_osnast
        tab3 = self.ui.tab_kar
        tab31 = self.ui.tab_tk_doc
        butt_op = self.ui.Button_t_op
        butt_kar = self.ui.Button_t_kar
        butt_per = self.ui.Button_t_per
        tree = self.ui.tree
        if tabl.hasFocus() or tabl_1.hasFocus():
            CQT.set_color_text_of_object_c(butt_op, 225, 10, 10)
        if tab2.hasFocus() or tab21.hasFocus() or tab22.hasFocus():
            CQT.set_color_text_of_object_c(butt_per, 225, 10, 10)
        if tab3.hasFocus() or tab31.hasFocus():
            CQT.set_color_text_of_object_c(butt_kar, 225, 10, 10)
        if tree.hasFocus():
            CQT.set_color_text_of_object_c(butt_op, 180, 180, 170)
            CQT.set_color_text_of_object_c(butt_per, 180, 180, 170)
            CQT.set_color_text_of_object_c(butt_kar, 180, 180, 170)

    @CQT.onerror
    def vigruzit(self,*args):
        sp = GF3(self)
        # for i in sp:
        #   print(i)
        # return
        if sp == None:
            return
        n_tk = self.ui.lineEdit_nntk
        putt = F.scfg('vivod_tk')
        if F.existence_file_c(putt) == False:
            F.create_dir_c(putt)
        if len(putt) < 3:
            putt = os.path.expanduser('~')
        ima = CQT.f_dialog_save(self, "Сохранить", putt + os.sep + n_tk.text() + '.txt', 'Текст файл(*.txt);;Все(*.*)')
        if ima == ".":
            return
        F.write_file_c(ima, sp)
        CQT.msgbox("Файл " + ima + " сохранен")
        F.run_file_c(ima)

    @CQT.onerror
    def block_tk(self, naim, nn):
        file = os.path.join(self.path_cash_poki, 'lock_tk.picle')
        if F.existence_file_c(file):
            try:
                dic = F.load_file_pickle(file)
            except:
                F.save_file_pickle(file, {nn: F.user_name()})
                return True
            if nn in dic:
                if dic[nn] != F.user_name() and dic[nn] != '':
                    return dic[nn]
            dic[nn] = F.user_name()
            F.save_file_pickle(file,dic)
            return True
        else:
            F.save_file_pickle(file, {nn:F.user_name()})
            return True



    def unlock_tk(self):
        if not CMS.user_access(self.db_naryad,'тк_разблокировать_тк',F.user_name()):
            return
        if self.ui.tblw_dse.currentRow() == -1:
            CQT.msgbox(f'Не выбрана ДСЕ')
            return
        nn = self.ui.tblw_dse.item(self.ui.tblw_dse.currentRow(),CQT.num_col_by_name_c(self.ui.tblw_dse,'Номенклатурный_номер')).text()
        file = os.path.join(self.path_cash_poki, 'lock_tk.picle')
        if F.existence_file_c(file):
            dic = F.load_file_pickle(file)
            if nn in dic:
                dic.pop(nn, None)
                F.save_file_pickle(file, dic)
                CQT.msgbox(f'Успешно')
            return True
        CQT.msgbox(f'Не заболкирована')
        return

    @CQT.onerror
    def unblock_tk(self, naim, nn):
        file = os.path.join(self.path_cash_poki, 'lock_tk.picle')
        if F.existence_file_c(file):
            dic = F.load_file_pickle(file)
            if nn in dic:
                if dic[nn] != F.user_name():
                    return dic[nn]
                dic.pop(nn, None)
                F.save_file_pickle(file, dic)
            return True
        else:
            F.save_file_pickle(file, dict())
            return True

    @CQT.onerror
    def zagr_tk(self, po_mk=False):
        n_dse = self.ui.lineEdit_dse
        nazv_dse = self.ui.lineEdit_dse_naim
        n_tk = self.ui.lineEdit_nntk

        if nazv_dse.text() == '':
            CQT.msgbox('Не заполнено название ДСЕ')
            return
        if n_tk.text() == '':
            CQT.msgbox('Не заполнен номер технологической карты')
            return
        ima = n_tk.text() + '_' + n_dse.text() + ".txt"
        if F.existence_file_c(F.scfg("add_docs")) == False:
            CQT.msgbox('Не найден каталог с ТК')
            return

        if po_mk == False:
            spisok_tk = F.open_file_c(F.scfg("add_docs") + os.sep + ima, False, '|', pickl=True, propuski=True)
            where = f'WHERE Номенклатурный_номер = {n_dse.text()!r} AND poki = {self.place.poki}'
            if spisok_tk == ['']:
                rez = CQT.msgboxgYN('Не найдена ТК, Создать техкарту заново?')
                if rez:
                    conn, cur = CSQ.connect_bd(self.db_dse,1)
                    CSQ.custom_request_c(
                        self.db_dse,
                        f"""UPDATE dse SET Номер_техкарты = '{n_tk.text()}' {where}""",
                    conn = conn, cur= cur)
                    self.obnov_dse(conn=conn,cur =cur)
                    CSQ.close_bd(conn, cur)
                    self.save_tk()
                else:
                    return False
            if self.ui.tblw_dse.currentRow() == -1:
                return
            if self.ui.tblw_dse.item(self.ui.tblw_dse.currentRow(), CQT.num_col_by_name_c(self.ui.tblw_dse,'Номер_техкарты')).text() == '':
                conn, cur = CSQ.connect_bd(self.db_dse, 1)
                CSQ.custom_request_c(self.db_dse,
                           f"""UPDATE dse SET Номер_техкарты = '{n_tk.text()}' {where}""",
                           conn=conn,cur = cur)
                self.obnov_dse(conn=conn,cur = cur)
                CSQ.close_bd(conn, cur)
            F.copy_file_c(F.scfg("add_docs") + os.sep + ima.replace('.txt', '.pickle'),
                          F.put_po_umolch() + os.sep + "tmp_tk")

            self.set_glob_tk_title(n_tk.text() + '$' + n_dse.text() + "$" + nazv_dse.text())

        else:
            spisok_tk = F.open_file_c(F.scfg("Mk") + os.sep + po_mk + os.sep + ima, False, '|', pickl=True, propuski=True)
            if spisok_tk == ['']:
                CQT.msgbox('Не найдена ТК')
                return
            F.copy_file_c(F.scfg("Mk") + os.sep + po_mk + os.sep + ima.replace('.txt', '.pickle'),
                          F.put_po_umolch() + os.sep + "tmp_tk")
            self.set_glob_tk_title(
                n_tk.text() + '$' + n_dse.text() + "$" + nazv_dse.text() + "$по маршрутной карте " + po_mk)
        self.nom_tk = n_tk.text()
        self.dse_nn = n_dse.text()
        self.dse_naim = nazv_dse.text()

        sp_tree = []
        for i in range(10, len(spisok_tk)):
            sp_tree.append(spisok_tk[i])
        self.zapoln_tree_spiskom(sp_tree)
        self.load_param_from_dxf(sp_tree)
        self.ui.tree.setCurrentIndex(self.ui.tree.model().index(0, 0))
        return


    @CQT.onerror
    def save_tk_vklad(self):
        self.save_tk_lite(msg = 0)
        self.set_glob_tk_title(F.put_po_umolch())
        self.ui.tabWidget.setTabEnabled(1, False)
        self.ui.pushButton_sozd.setEnabled(True)
        n_dse = self.ui.lineEdit_dse
        naim_dse = self.ui.lineEdit_dse_naim
        self.unblock_tk(naim_dse.text(), n_dse.text())
        self.dse_nn = ''
        self.dse_naim = ''

    @CQT.onerror
    def save_tk_lite(self, p1 = '' ,msg = 1 ,*args):
        self.save_shir_kol_tree()
        if self.save_tk() == None:
            if msg == 1:
                CQT.msgbox('Не сохранено')
            return
        if '*' in  self.glob_tk_title:
            self.set_glob_tk_title(self.glob_tk_title.replace('*',''))
        if msg == 1:
            CQT.msgbox('Успешно сохранено')


    @CQT.onerror
    def btn_prim_izm_shablon(self,*args):
        if F.existence_file_c(self.PUT_K_TMP) == False:
            F.create_dir_c(self.PUT_K_TMP)
        putf = self.PUT_K_TMP + os.sep + "shablon_op.txt"
        spis = CQT.list_from_wtabl_c(self.ui.tbl_shablon_op, "", True)
        F.write_file_c(putf, spis, separ='|')
        CQT.msgbox("Успешно")


    @CQT.onerror
    def save_tk(self):
        osn_nadp = []
        n_dse = self.ui.lineEdit_dse
        naim_dse = self.ui.lineEdit_dse_naim
        n_tk = self.ui.lineEdit_nntk
        n_tk_km = self.ui.lineEdit_nntk_mat
        n_tk_es = self.ui.lineEdit_nntk_esk
        lit = self.ui.comboBox_liter
        razr = self.ui.lineEdit_razrab
        d_raz = self.ui.lineEdit_dat_raz
        prov = self.ui.lineEdit_prover
        norm = self.ui.lineEdit_normir
        metr = self.ui.lineEdit_metr_eksp
        nor_kont = self.ui.lineEdit_Norm_k
        prim = self.ui.lineEdit_Primech
        if 'по маршрутной карте' not in self.glob_tk_title:
            if naim_dse.text() == '':
                CQT.msgbox('Не заполнен наиенование ДСЕ')
                return
            if n_tk.text() == '':
                CQT.msgbox('Не заполнен номер технологической карты')
                return
            if lit.currentText() == '-':
                CQT.msgbox('Не выбрана литера')
                return
            if prov.text() == '':
                prov.setText('-')
                # CQT.msgbox('Не заполнена графа Проверил')
                # return
            if norm.text() == '':
                CQT.msgbox('Не заполнена графа Нормировал')
                return
            if metr.text() == '':
                CQT.msgbox('Не заполнена графа Метрологическая эксп.')
                return
            if nor_kont.text() == '':
                CQT.msgbox('Не заполнена графа Нормоконтроль')
                return
            if razr.text() == '':
                CQT.msgbox('Не заполнена графа Разработчик')
                return
            if d_raz.text() == '':
                CQT.msgbox('Не заполнена графа Дата разработки')
                return
        osn_nadp.append(n_dse.text() + '$' + naim_dse.text())
        osn_nadp.append(n_tk.text() + '/' + n_tk_km.text() + '/' + n_tk_es.text())
        osn_nadp.append(lit.currentText())
        osn_nadp.append(razr.text())
        osn_nadp.append(d_raz.text())
        osn_nadp.append(prov.text())
        osn_nadp.append(norm.text())
        osn_nadp.append(metr.text())
        osn_nadp.append(nor_kont.text())
        osn_nadp.append(prim.text())
        telo = CQT.list_from_tree_c(self.ui.tree)
        sp_soh = []
        for i in osn_nadp:
            sp_soh.append(i)
        for i in telo:
            sp_soh.append("|".join(i))
        ima = n_tk.text() + '_' + n_dse.text() + ".txt"
        if F.existence_file_c(F.scfg("add_docs")) == False:
            F.create_dir_c(F.scfg("add_docs"))
        if 'по маршрутной карте' in self.glob_tk_title:
            nom_mk = self.glob_tk_title.split('карте ')[-1].replace('*','')
            F.write_file_c(F.scfg('Mk') + os.sep + nom_mk + os.sep + ima, sp_soh, pickl=True)
            self.add_zapis_jurnal('Правка МК', n_dse.text(), False)
        else:
            file_name = F.scfg("add_docs") + os.sep + ima
            if F.existence_file_c(file_name.replace('.txt','.pickle')):
                self.add_zapis_jurnal('Перезапись',n_dse.text(), False)
            else:
                self.add_zapis_jurnal('Создание',n_dse.text())
            F.write_file_c(file_name, sp_soh, pickl=True)

        return sp_soh

    @CQT.onerror
    def tree_noma_vrem(self):
        tree = self.ui.tree
        item = tree.currentItem()
        kod = tree.currentItem().text(3)
        spisok = CQT.list_from_tree_c(tree)
        if item == None:
            return
        obr = item.text(3)
        ur = item.text(20)
        if ur == "0":
            return
        flag = False
        for i in range(0, len(spisok)):
            if obr == spisok[i][3]:
                flag = True
                for j in range(i, 0, -1):
                    if 1 == int(spisok[j][20]):
                        metka = j
                        break
            if flag:
                break

        flag_vse = True
        flag_odna = False
        summ = 0
        for i in range(metka + 1, len(spisok)):
            if spisok[i][20] != '2':
                break

            if spisok[i][7] != "":
                spisok[i][7] = spisok[i][7].replace(',', '.')
                if F.is_numeric(spisok[i][7]):
                    flag_odna = True
                    summ += float(spisok[i][7])
                else:
                    flag_vse = False
            else:
                flag_vse = False

        if flag_vse:
            spisok[metka][7] = str(round(summ, 1))
            CQT.msgbox('Время штучное на ' + spisok[metka][2] + " операцию, успешно пересчитано")
        else:
            if flag_odna:
                spisok[metka][7] = '0'
                CQT.msgbox('Время штучное на ' + spisok[metka][
                    2] + " операцию, не рассчитано. Не заполнено время на все переходы")
        self.zapoln_tree_spiskom(spisok)
        CQT.highlight_tree_values_c(self.ui.tree, 3, kod)

    @CQT.onerror
    def tree_del(self,*args):
        rez = CQT.msgboxgYN('Точно удалить?')
        if rez == False:
            return
        tree = self.ui.tree
        item = tree.currentItem()
        spisok = CQT.list_from_tree_c(tree)
        cur_str = self.ui.tree.currentItem().text(3)
        if item == None:
            return
        obr = item.text(3)
        ur = item.text(20)
        flag = False
        spisok_tmp = spisok.copy()
        for i in range(0, len(spisok)):
            if obr == spisok[i][3]:
                spisok_tmp.remove(spisok[i])
                flag = True
                for j in range(i + 1, len(spisok)):
                    if int(ur) < int(spisok[j][20]):
                        spisok_tmp.remove(spisok[j])
                    else:
                        break
            if flag:
                break
        self.zapoln_tree_spiskom(spisok_tmp)
        CQT.highlight_tree_values_c(self.ui.tree, 3, cur_str, -1)

    @CQT.onerror
    def tree_paste(self,*args):
        buf = self.ui.t_buff_0
        if self.ui.tree.currentItem() == None:
            cur_str = 'Т1'
        else:
            cur_str = self.ui.tree.currentItem().text(3)
        self.tree_paste_buf_n(buf)
        CQT.highlight_tree_values_c(self.ui.tree, 3, cur_str)
        return

    @CQT.onerror
    def tree_copy(self,*args):
        self.copy_is_approve = self.is_valid_row_approve()
        buf = self.ui.t_buff_0
        self.tree_copy_buf_n(buf)
        return

    @CQT.onerror
    def tree_paste_buf_n(self, obj):
        tree = self.ui.tree
        item = tree.currentItem()
        buf = obj
        if item == None:
            cur_str = ""
        else:
            cur_str = self.ui.tree.currentItem().text(3)
        spisok = CQT.list_from_tree_c(tree)
        if item == None and len(spisok) != 0:
            return
        if buf.rowCount() == 0:
            return
        tmp = CQT.list_from_wtabl_c(buf)
        mat_preview = MAGAZ.PreviewMaterials(self, tmp)#20.06.25 ( по задаче 100055627 )
        tmp = mat_preview.call_preview_table()
        if self.dse_nn_from_copy != self.dse_nn:
            for i in range(len(tmp)):
                if not self.copy_is_approve:
                    if tmp[i][20] == '0':
                        tmp[i][14] = ""
                    if tmp[i][20] == '1':
                        tmp[i][7] = ""
                        tmp[i][14] = ""
                        tmp[i][15] = ""
                        # tmp[i][10] = ""#20.06.25 ( по задаче 100055627 )
                    if tmp[i][20] == '2':
                        if i >0 and tmp[i-1][20] == '1' and tmp[i-1][0] == 'Резка(ЧПУ)':
                            if 'егмент' in tmp[i][0].lower() or 'сектор' \
                                    in tmp[i][0].lower() or 'сектор' in tmp[i][0].lower():
                                tmp[i][0] = "Сегменты ?"
                        tmp[i][7] = ""
                        tmp[i][14] = ""
                else:
                    if tmp[i][20] == '1':
                        tmp[i][15] = ""
        if len(spisok) == 0:
            spisok = tmp
            self.zapoln_tree_spiskom(spisok)
            return
        tmp_ur = tmp[0][20]
        obr = item.text(3)
        ur = item.text(20)
        metka = len(spisok)
        flag = False
        for i in range(0, len(spisok)):
            if obr == spisok[i][3]:
                for j in range(i + 1, len(spisok)):
                    if int(tmp_ur) >= int(spisok[j][20]):
                        metka = j
                        flag = True
                        break
            if flag:
                break
        n = 0
        for i in range(len(tmp)):
            if tmp[i][20] == '1' or tmp[i][20] == '2':
                tmp[i][7] = '*'
            # if tmp[i][20] == '1':
            #     tmp[i][10] = '' # ""#20.06.25 ( по задаче 100055627 )

            tmp[i][15] = ''
            tmp[i][1] = ''
            spisok.insert(metka + n, tmp[i])
            n += 1
        self.zapoln_tree_spiskom(spisok)
        CQT.highlight_tree_values_c(self.ui.tree, 3, cur_str)

    @CQT.onerror
    def tree_copy_buf_n(self, obj):
        tree = self.ui.tree
        item = tree.currentItem()
        buf = obj
        if item == None:
            return
        obr = item.text(3)
        ur = item.text(20)
        tmp = []
        spisok = CQT.list_from_tree_c(tree)
        for i in range(0, len(spisok)):
            if obr in spisok[i][3]:
                tmp.append("|".join(spisok[i]))
        isp_n_k = 0
        CQT.fill_wtabl_old_c(mywindow, tmp, buf, isp_n_k, 0, (), (), 200, False, "|", 5)
        self.dse_nn_from_copy = copy.deepcopy(self.dse_nn)
        return

    @CQT.onerror
    def resizeEvent(self, event):
        self.resized.emit()
        return super(mywindow, self).resizeEvent(event)

    @CQT.onerror
    def widths(self,*args):
        tab_per_ins = self.ui.tap_per_insrt
        tab_per_ins.setColumnWidth(0, int(tab_per_ins.width()))
        tab_per_osn = self.ui.tap_per_osnast
        tab_per_osn.setColumnWidth(0, int(tab_per_osn.width()))

        tab2 = self.ui.tap_per
        tab2.setColumnWidth(0, int(tab2.width() * 0.3))
        tab2.setColumnWidth(1, int(tab2.width() * 0.3))
        tab2.setColumnWidth(2, int(tab2.width() * 0.4) - 5)
        tabl = self.ui.tab_op
        tabl.setColumnWidth(0, int(tabl.width() * 0))
        tabl.setColumnWidth(1, int(tabl.width() * 0.05))
        tabl.setColumnWidth(2, int(tabl.width() * 0.2))
        tabl.setColumnWidth(4, int(tabl.width() * 0.3))
        tabl.setColumnWidth(5, int(tabl.width() * 0.05))
        tabl.setColumnWidth(6, int(tabl.width() * 0.05))
        tabl.setColumnWidth(7, int(tabl.width() * 0.05))
        tabl.setColumnWidth(8, int(tabl.width() * 0.05))
        tabl.setColumnWidth(9, int(tabl.width() * 0.05))
        tabl.setColumnWidth(4, int(tabl.width() - tabl.columnWidth(0) - tabl.columnWidth(1) - tabl.columnWidth(2)
                                   - tabl.columnWidth(3) - tabl.columnWidth(5) - tabl.columnWidth(6)
                                   - tabl.columnWidth(7) - tabl.columnWidth(8) - tabl.columnWidth(9)) - 5)
        tab_oper_mat = self.ui.tbl_oper_mat
        tab_oper_mat.setColumnWidth(0, int(tab_oper_mat.width() * 0.3))
        tab_oper_mat.setColumnWidth(1, int(tab_oper_mat.width() * 0.3))
        tab_oper_mat.setColumnWidth(2, int(tab_oper_mat.width() * 0.4))

        tab_doc_tk = self.ui.tab_tk_doc
        tab_doc_tk.setColumnWidth(0, tab_doc_tk.width())
        tab_doc_op = self.ui.tab_op_doc
        tab_doc_op.setColumnWidth(0, tab_doc_op.width())

    @CQT.onerror
    def tree_vverh(self,*args):
        tree = self.ui.tree

        tci = tree.currentItem()
        if tci == None:
            return
        obr = tci.text(3)
        ur = tci.text(20)
        rez = self.tree_move_vverh(obr, ur)
        CQT.highlight_tree_values_c(tree, 3, rez)
        tree.setFocus(True)

    @CQT.onerror
    def tree_vniz(self,*args):
        tree = self.ui.tree
        tci = tree.currentItem()
        obr = tci.text(3)
        ur = tci.text(20)
        spisok = CQT.list_from_tree_c(tree)
        for i in range(0, len(spisok)):
            if spisok[i][3] == obr:
                nach = i
                break
        metka = None
        for i in range(nach + 1, len(spisok)):
            if spisok[i][20] == ur:
                metka = i
                break
            if int(spisok[i][20]) < int(ur):
                break
        if metka != None:
            obr = spisok[metka][3]
            ur = spisok[metka][20]
            rez = self.tree_move_vverh(obr, ur)
        CQT.highlight_tree_values_c(tree, 3, rez)
        tree.setFocus(True)

    @CQT.onerror
    def tree_move_vverh(self, obr, ur):
        tree = self.ui.tree
        ci = tree.currentIndex().row()
        # obr = item.text(3)
        # ur = item.text(20)
        tmp = []
        spisok = CQT.list_from_tree_c(tree)
        for i in range(0, len(spisok)):
            if spisok[i][3] == obr:
                nach = i
                break

        metka = None
        for i in range(nach - 1, -1, -1):
            if int(spisok[i][20]) < int(ur):
                return
            if spisok[i][20] == ur:
                metka = i
                break
        if metka == nach:
            return
        if metka == None:
            return

        for i in range(0, len(spisok)):
            if obr in spisok[i][3]:
                tmp.append(spisok[i])

        for i in range(0, len(tmp)):
            spisok.remove(tmp[i])

        for i in range(len(tmp) - 1, -1, -1):
            spisok.insert(metka, tmp[i])

        self.zapoln_tree_spiskom(spisok)
        # tree.itemAt(metka,0).setSelected(True)

        tree.selectionModel().select(tree.model().index(metka, 0),
                                     QtCore.QItemSelectionModel.Clear | QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
        tree.selectionModel().setCurrentIndex(tree.model().index(metka, 0),
                                              QtCore.QItemSelectionModel.Clear | QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
        # treeWidget->selectionModel()->select(treeWidget->model()->index(row, 0),
        #                                                          QItemSelectionModel::SelectCurrent | QItemSelectionModel::Rows );
        # self.device_view.selectionModel().select(self.dev_model.index(0),
        #                                         QItemSelectionModel.Select)
        return spisok[metka][3]

    @CQT.onerror
    def zapoln_tree_spiskom(self, spisok):
        spisok = self.obnovit_numeraciy(spisok)
        tree = self.ui.tree
        tree.clear()

        n = 0
        tmp = ''
        tmp2 = ''
        root = ''
        for i in range(0, len(spisok)):
            if spisok[i][20] == '0':
                root = QtWidgets.QTreeWidgetItem(tree)
                tmp = root
            if spisok[i][20] == '1':
                if tmp == '':
                    CQT.msgbox(f'Структура ТК не корректная, отсутствует 0 уровень')
                    return
                root = QtWidgets.QTreeWidgetItem(tmp)
                tmp2 = root
            if spisok[i][20] == '2':
                if tmp2 == '':
                    CQT.msgbox(f'Структура ТК не корректная, отсутствует 1 уровень')
                    return
                root = QtWidgets.QTreeWidgetItem(tmp2)
            for j in range(0, len(spisok[i])):
                if root == '':
                    CQT.msgbox(f'Структура ТК не корректная')
                    return
                root.setText(j, spisok[i][j])
            tree.addTopLevelItem(root)
            tree.expandItem(root)
            n += 1
        try:
            tree.setCurrentItem(root)
        except:
            pass

        self.load_shir_kol_tree()

        self.colors_into_tree_c(145, 218, 145, 255)

    @CQT.onerror
    def opn_doc(self,*args):
        tree = self.ui.tree
        item = tree.currentItem()
        if item == None:
            return
        if item.text(15) == "":
            return
        rez = db_files_load(self,item.text(15))
        if rez == False:
            CQT.msgbox(f'Файл {item.text(15)} не найден в бд')
            return
        F.run_file_c(rez)

    # @CQT.onerror
    # def dob_doc(self,*args):
    #     def clear_old_files_from_db():
    #         set_pnoms_del = set()
    #         list_files = CSQ.custom_request_c(self.db_files,f"""SELECT Пномер,name, teh_karts FROM reestr""",rez_dict=True)
    #         for i in range(len(list_files)-1,-1,-1):
    #             if list_files[i]['teh_karts'] == '':
    #                 continue
    #             list_tk_name = list_files[i]["teh_karts"].split('|')
    #             for tk_name in list_tk_name:
    #                 for j in range(i-1,-1,-1):
    #                     if tk_name in list_files[j]['teh_karts'] and list_files[j]['name'] == list_files[i]['name']:
    #                         if list_files[j]['teh_karts'] == tk_name:
    #                             set_pnoms_del.add(list_files[j]['Пномер'])
    #                             list_files[j]['teh_karts'] = ''
    #                         else:
    #                             tmp_list = list_files[j]['teh_karts'].split('|')
    #                             tmp_list.remove(tk_name)
    #                             tmp_str = '|'.join(tmp_list)
    #                             list_files[j]['teh_karts'] = tmp_str
    #                             CSQ.custom_request_c(self.db_files,f"""UPDATE reestr SET teh_karts = '{tmp_str}' WHERE Пномер = {list_files[j]['Пномер']}""")
    #         tuple_del = tuple(set_pnoms_del)
    #         CSQ.custom_request_c(self.db_files,f"""DELETE FROM reestr WHERE Пномер in {tuple_del}""")
    #         pass
    #     #clear_old_files_from_db()
    #     def fill_names():
    #         list_list_names = []
    #         list_list_tk = []
    #         list_files = CSQ.custom_request_c(self.db_files, f"""SELECT Пномер, name, teh_karts FROM reestr""", rez_dict=True)
    #         for i in range(len(list_files) - 1, -1, -1):
    #             list_tk_name = list_files[i]["teh_karts"].split('|')
    #             for tk_name in list_tk_name:
    #                 list_list_tk.append([list_files[i]["name"], tk_name,F.now("%Y-%m-%d %H-%M"), F.user_name()])
    #             list_list_names.append([list_files[i]["Пномер"], list_files[i]["name"],F.now("%Y-%m-%d %H-%M"), F.user_name()])
    #
    #         #CSQ.custom_request_c(self.db_files,
    #         #                               f"""INSERT INTO names(nom_data, name, date_edit, usr)
    #         #             VALUES (?,?,?,?);""",list_of_lists_c=list_list_names)
    #
    #         CSQ.custom_request_c(self.db_files,
    #                    f"""INSERT INTO t_kards(file_name, t_kard_name, date_edit, usr)
    #                        VALUES (?,?,?,?);""", list_of_lists_c=list_list_tk)
    #
    #         pass
    #
    #
    #     tree = self.ui.tree
    #     item = tree.currentItem()
    #     if item == None:
    #         return
    #     ima_det = self.glob_tk_title.split('$')[1].replace('*','')
    #     tmp_putt = CMS.load_tmp_path("tmp_addtk_doc")
    #
    #     putf = CQT.f_dialog_name(self, 'Выбрать файл', tmp_putt, f"Файлы (*{ima_det.replace(' ','')}*.dxf *.jpg *.pdf)")
    #     if putf == '' or putf == '.':
    #         return
    #     CMS.save_tmp_path("tmp_addtk_doc", putf, True)
    #     db_files_del(self,item.text(15),self.nom_tk)
    #     file_name_bd = db_files_nalich(self,putf,self.nom_tk)
    #     if file_name_bd == None:
    #         return
    #     r"""
    #     ima_f = putf.split(os.sep)[-1]
    #     new_ima = F.throw_out_extention_c(ima_f) + '_' + str(F.get_time_shtamp_c()) + F.keep_extention_c(ima_f)
    #     nputf = F.scfg('add_docs') + '\\' + new_ima
    #     rez = F.copy_file_c(putf, nputf)"""
    #
    #     try:
    #         item.setText(15, file_name_bd)
    #         item.setText(1, '...')
    #         CQT.msgbox("Файл прикреплен успешно")
    #         sp_soh = self.save_tk()
    #     except:
    #         CQT.msgbox("Не удалось сохранить файл после прикрепления")
    #         return
    #     sp_tree = []
    #     for i in range(10, len(sp_soh)):
    #         sp_tree.append(sp_soh[i].split('|'))
    #     self.load_param_from_dxf(sp_tree)


    @CQT.onerror
    def ydal_doc(self,*args):
        tree = self.ui.tree
        item = tree.currentItem()
        if item == None:
            return
        if item.text(15) == "":
            return
        #F.delete_file_c(F.scfg('add_docs') + '//' + item.text(15))
        db_files_del(self,item.text(15),self.nom_tk)
        CQT.msgbox("Файл откреплен успешно")
        item.setText(15, "")
        item.setText(1, '')
        self.save_tk()
        return

    @CQT.onerror
    def click_tableW_oper_mat(self,*args):
        tbl = self.ui.tableW_oper_mat

        _translate = QtCore.QCoreApplication.translate
        #tbl.setToolTipDuration()
        if tbl.currentItem() == None:
            return
        tbl.setToolTip(_translate("MainW", tbl.currentItem().text()))

    @CQT.onerror
    def zap_mat_v_tree(self,*args):
        tab = self.ui.tableW_oper_mat
        tab_oper = self.ui.tbl_oper_mat
        if tab_oper.currentIndex().row() == -1:
            CQT.msgbox('Не выбрана операция')
            return
        nk_norm = CQT.num_col_by_name_c(tab, 'Норма')
        nk_kod = CQT.num_col_by_name_c(tab, 'Код')
        if tab.rowCount() >= 0:
            strok = []
            for st in range(0, tab.rowCount()):
                podstrok = []
                if tab.item(st, nk_norm) != None:
                    if tab.item(st, nk_norm).text() == '':
                        CQT.msgbox(f'В строке {st+1} пусто!')
                        return
                    if tab.item(st, nk_norm).text()[0] != 'f':
                        if not F.is_numeric(tab.item(st, nk_norm).text()):
                            CQT.msgbox(f'В строке {st + 1} не число!')
                            return
                        value = F.valm(tab.item(st, nk_norm).text())
                        #if value > 100:
                        #    CQT.msgbox(f'Вес {tab.item(st, nk_kod).text()} больше 100 кг!',icon=QtWidgets.QMessageBox.Warning)
                        tab.item(st, nk_norm).setText('{:.8f}'.format(round(value, 8)))

                    if tab.item(st, nk_kod).text() == '':
                        CQT.msgbox(f'В строке {st+1} код пусто!')
                        return

                    if tab.item(st, nk_kod).text()[0] != 'f':
                        if tab.item(st, nk_kod).text() not in self.DICT_NOMEN:
                            CQT.msgbox(f'В строке {st + 1} код {tab.item(st, nk_kod).text()} отсутствет в номенклатуре!')
                            return

                    for i in range(0, tab.columnCount()):
                        if tab.item(st, i) == None:
                            CQT.msgbox("Не полностью заполнена запись")
                            return
                        tmp = tab.item(st, i).text().replace("{", "£")
                        tmp = tmp.replace("}", "¢")
                        tmp = F.clear_row_for_separ_c(tmp)
                        podstrok.append(tmp)
                    strok.append('$'.join(podstrok))
            strok = '{'.join(strok)
            #nom_op = CQT.cells(tab_oper.currentIndex().row(), 0, tab_oper)
            nom_op = tab_oper.item(tab_oper.currentRow(),CQT.num_col_by_name_c(tab_oper,'ID')).text()
            self.zapis_v_drevo(nom_op, 10, strok)
            CQT.msgbox('Записано успешно')


    @CQT.onerror
    def obnovit_mater_tabl(self,*args):
        tab_oper = self.ui.tbl_oper_mat
        tab_oper_mat_red = self.ui.tableW_oper_mat
        if tab_oper.currentRow() == -1:
            return
        if tab_oper.item(tab_oper.currentRow(),CQT.num_col_by_name_c(tab_oper,'ID')) == None:
            return
        id_op = tab_oper.item(tab_oper.currentRow(),CQT.num_col_by_name_c(tab_oper,'ID')).text()
        if id_op == None:
            return
        slov_op = self.slovar_drev(1, id_op)
        CQT.clear_tbl(tab_oper_mat_red)
        rez_list = [copy.deepcopy(self.tab_oper_mat_red_hat_c)]
        spis_strok_mat = []
        for i in slov_op.keys():
            spis_k = slov_op[i]
            spis_strok_mat = spis_k[10].split('{')
            if spis_strok_mat[0] == '' and len(spis_strok_mat) == 1:
                set_edit = {F.num_col_by_name_in_hat_c(rez_list, 'Код'), F.num_col_by_name_in_hat_c(rez_list, 'Норма')}
                CQT.fill_wtabl(rez_list, tab_oper_mat_red, ogr_maxshir_kol=500, set_editeble_col_nomera=set_edit,
                               auto_type=False)
                return
            break
        for i in range(0, len(spis_strok_mat)):
            spis_mat = spis_strok_mat[i].split('$')
            for j in range(0, len(spis_mat)):
                if j == 3:
                    spis_mat[j] = spis_mat[j].replace('¢','}')
                    spis_mat[j] = spis_mat[j].replace('£', '{')
                    if F.is_numeric(spis_mat[j]):
                        value = F.valm(spis_mat[j])
                        spis_mat[j] = '{:.8f}'.format(round(value, 8))
            rez_list.append(spis_mat)
        set_edit = {F.num_col_by_name_in_hat_c(rez_list, 'Код'), F.num_col_by_name_in_hat_c(rez_list,'Норма')}
        CQT.fill_wtabl(rez_list,tab_oper_mat_red,ogr_maxshir_kol=500,set_editeble_col_nomera=set_edit,auto_type=False)


    @CQT.onerror
    def btn_create_or_edit_tk(self, nom_mk,*args):
        n_dse = self.ui.lineEdit_dse
        n_tk = self.ui.lineEdit_nntk
        n_tk_km = self.ui.lineEdit_nntk_mat
        n_tk_es = self.ui.lineEdit_nntk_esk
        lit = self.ui.comboBox_liter
        razr = self.ui.lineEdit_razrab
        d_raz = self.ui.lineEdit_dat_raz
        prov = self.ui.lineEdit_prover
        norm = self.ui.lineEdit_normir
        metr = self.ui.lineEdit_metr_eksp
        nor_kont = self.ui.lineEdit_Norm_k
        prim = self.ui.lineEdit_Primech
        naim_dse = self.ui.lineEdit_dse_naim
        tbl_dse = self.ui.tblw_dse
        nom_kol_nom_tk = CQT.num_col_by_name_c(tbl_dse, 'Номер_техкарты')
        if self.ui.pushButton_sozd.text() == 'Создать':
            if len(n_tk.text()) < 7:
                CQT.msgbox(f'Номер техкарты короткий')
                return

        n_k_nn = CQT.num_col_by_name_c(tbl_dse, 'Номенклатурный_номер')
        n_k_naim = CQT.num_col_by_name_c(tbl_dse, 'Наименование')
        if tbl_dse.item(tbl_dse.currentRow(), n_k_nn) != None:
            if n_dse.text() != tbl_dse.item(tbl_dse.currentRow(), n_k_nn).text():
                n_dse.setText(tbl_dse.item(tbl_dse.currentRow(), n_k_nn).text())
        if tbl_dse.item(tbl_dse.currentRow(), n_k_nn) != None:
            if naim_dse.text() != tbl_dse.item(tbl_dse.currentRow(), n_k_naim).text():
                naim_dse.setText(tbl_dse.item(tbl_dse.currentRow(), n_k_naim).text())


        if n_dse.text() == '' and naim_dse.text() == "":
            CQT.msgbox('Не заполнен номер, название ДСЕ')
            return
        if naim_dse.text() == "":
            CQT.msgbox('Не заполнен название ДСЕ')
            return
        if n_tk.text() == '':
            CQT.msgbox('Не заполнен номер технологической карты')
            return
        if razr.text() == '':
            CQT.msgbox('Не заполнена графа Разработчик')
            return
        if d_raz.text() == '':
            CQT.msgbox('Не заполнена графа Дата разработки')
            return
        if lit.currentText() == '-':
            CQT.msgbox('Не выбрана литера')
            return
        if prov.text() == '':
            prov.setText('-')
            #CQT.msgbox('Не заполнена графа Проверил')

        if norm.text() == '':
            CQT.msgbox('Не заполнена графа Нормировал')
            return
        if metr.text() == '':
            CQT.msgbox('Не заполнена графа Метрологическая эксп.')
            return
        if nor_kont.text() == '':
            CQT.msgbox('Не заполнена графа Нормоконтроль')
            return

        self.ui.tab_kar.setRowCount(0)
        self.ui.tab_tk_doc.setRowCount(0)
        self.ui.tab_op.setRowCount(0)
        self.ui.tab_op_doc.setRowCount(0)
        self.ui.tap_per.setRowCount(0)
        self.ui.tableW_oper_mat.setRowCount(0)


        rez = self.block_tk(naim_dse.text(), n_dse.text())
        if rez != True:
            CQT.msgbox(f'Техкарта на редактировании {rez}')
            self.ui.pushButton_sozd.setEnabled(False)
            return
        else:
            self.ui.pushButton_sozd.setEnabled(True)


        rez = self.load_redaktor_tk(nom_mk)
        if rez == False:
            return
        self.ui.tabWidget.setTabEnabled(1, True)
        self.ui.tabWidget.setCurrentIndex(1)

        if self.ui.pushButton_sozd.text() == 'Изменить':
            #self.save_tk()
            pass
        else:
            # ogr_rezhim = self.nalichie_nevip_mk(n_dse.text(), naim_dse.text())
            #self.set_glob_tk_title(n_tk.text() + '$' + n_dse.text() + "$" + naim_dse.text())
            self.nom_tk = n_tk.text()
            self.dse_nn = n_dse.text()
            self.dse_naim = naim_dse.text()



    @CQT.onerror
    def load_redaktor_tk(self,po_mk):
        tabl_bd = self.ui.tblw_dse
        prim_dse = CQT.cells(tabl_bd.currentIndex().row(), CQT.num_col_by_name_c(tabl_bd, 'Примечание'), tabl_bd)
        self.ui.lbl_primech_dse.setText(prim_dse)
        if po_mk == False:
            self.ui.pushButton_Vverh.setEnabled(True)
            self.ui.pushButton_Vniz.setEnabled(True)
            self.ui.pushButton_Copy.setEnabled(True)
            self.ui.pushButton_Paste.setEnabled(True)
            self.ui.pushButton_Del.setEnabled(True)
        self.ui.tree.clear()
        rez = self.zagr_tk(po_mk)
        self.ui.splitter_3.setSizes([500, 80])
        self.ui.splitter_2.setSizes([80, 500])
        return rez


    @CQT.onerror
    def btn_copy_nr(self,*args):
        F.copy_bufer(self.ui.lbl_copy_nr.text())

    @CQT.onerror
    def btn_copy_nv(self,*args):
        F.copy_bufer(self.ui.lbl_copy_nv.text())

    @CQT.onerror
    def load_zagolovok_dse(self,po_mk):

        self.ui.lbl_copy_nr.setText('')
        self.ui.lbl_copy_nv.setText('')

        def  fill_for_new(self):
            # self.ui.pushButton_zagruz.setEnabled(False)
            self.ui.pushButton_sozd.setText('Создать')
            name = F.user_full_namre()
            try:
                name = F.user_full_namre().split(' ')[0].upper()
            except:
                pass
            self.ui.lineEdit_razrab.setText(name)
            self.ui.lineEdit_dat_raz.setText(F.date())
            le_n_dse.setEnabled(True)
            le_n_tk.setEnabled(True)
            le_naim_dse.setEnabled(True)

            if nom_dse == '':
                le_n_tk.setText(f'ТДТК{self.place.letter}.{F.clear_row_for_file_name_c(nom_nazv)}')
            else:
                le_n_tk.setText(f'ТДТК{self.place.letter}.{nom_dse}')
            le_n_tk_km.setText('ВСН')
            self.set_glob_tk_title('')
            self.nom_tk = ''
            self.dse_nn = ""
            self.dse_naim = ""


        tabl_bd = self.ui.tblw_dse
        dict_row = CQT.get_dict_line_form_tbl(tabl_bd,tabl_bd.currentIndex().row())
        nom_dse = CQT.cells(tabl_bd.currentIndex().row(), CQT.num_col_by_name_c(tabl_bd,'Номенклатурный_номер'), tabl_bd)
        nom_tk = CQT.cells(tabl_bd.currentIndex().row(), CQT.num_col_by_name_c(tabl_bd,'Номер_техкарты'), tabl_bd)
        nom_nazv = CQT.cells(tabl_bd.currentIndex().row(), CQT.num_col_by_name_c(tabl_bd,'Наименование'), tabl_bd)
        nf_mat_kd = CQT.cells(tabl_bd.currentIndex().row(), CQT.num_col_by_name_c(tabl_bd, 'Мат_кд'), tabl_bd)
        nf_mat_kd_kod_erp = CQT.cells(tabl_bd.currentIndex().row(), CQT.num_col_by_name_c(tabl_bd, 'Код_ЕРП'), tabl_bd)

        self.ui.lbl_copy_nr.setText(dict_row['Нр_техн_дет'])
        self.ui.lbl_copy_nv.setText(dict_row['Нв_техн_раскрой'])

        self.mat_kd_erp = f'{nf_mat_kd_kod_erp}${nf_mat_kd}'
        le_n_dse = self.ui.lineEdit_dse
        le_n_tk = self.ui.lineEdit_nntk
        le_naim_dse = self.ui.lineEdit_dse_naim
        le_n_tk_km = self.ui.lineEdit_nntk_mat
        le_n_tk_es = self.ui.lineEdit_nntk_esk
        le_n_dse.setText(nom_dse)
        le_naim_dse.setText(nom_nazv)
        self.ui.lbl_marsh.setText('')
        lit = self.ui.comboBox_liter
        razr = self.ui.lineEdit_razrab
        d_raz = self.ui.lineEdit_dat_raz
        prov = self.ui.lineEdit_prover
        norm = self.ui.lineEdit_normir
        metr = self.ui.lineEdit_metr_eksp
        nor_kont = self.ui.lineEdit_Norm_k
        prim = self.ui.lineEdit_Primech

        def prep_fill_for_new():
            tabl_bd.blockSignals(True)
            tabl_bd.item(tabl_bd.currentRow(), CQT.num_col_by_name_c(tabl_bd, 'Номер_техкарты')).setText('')
            tabl_bd.blockSignals(False)
            fill_for_new(self)

        le_n_tk.clear()
        lit.setCurrentIndex(0)
        razr.clear()
        d_raz.clear()
        prov.clear()
        norm.clear()
        metr.clear()
        nor_kont.clear()
        prim.clear()
        le_n_tk_km.clear()
        le_n_tk_es.clear()
        self.ui.pushButton_sozd.setEnabled(True)
        if self.ui.tabWidget_2.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_2, 'ЦП'):
            self.ui.axWidget.dynamicCall('Navigate(const QString&)', "")
        CQT.clear_tbl(self.ui.tbl_isp_mk)
        if nom_tk != '':
            self.ui.pushButton_sozd.setText('Изменить')
            le_n_tk.setText(nom_tk)
            le_n_dse.setEnabled(False)
            le_n_tk.setEnabled(True)
            le_naim_dse.setEnabled(False)
        else:
            fill_for_new(self)
            return
        ima = nom_tk + '_' + nom_dse + ".txt"
        if po_mk == False:
            if not F.existence_file_c(F.scfg("add_docs") + os.sep + ima.replace('.txt','.pickle')):
                if not CQT.msgboxgYN(f'Файл с ТК не найден.\nСоздать новую?'):
                    return
                else:
                    prep_fill_for_new()
            spisok_tk = F.open_file_c(F.scfg("add_docs") + os.sep + ima, False, '|', pickl=True, propuski=True)
            if spisok_tk == None:
                if not CQT.msgboxgYN(f'Файл битый, открыть невозможно.\nЗатереть его для создания нового?'):
                    return
                F.delete_file_c(F.scfg("add_docs") + os.sep + ima.replace('.txt','.pickle'))
                prep_fill_for_new()
                CQT.msgbox(f"Успешно. Выбрать строку еще раз.")
                return
            self.set_glob_tk_title(nom_tk + '$' + nom_dse + "$" + nom_nazv)
        else:
            spisok_tk = F.open_file_c(F.scfg("Mk") + os.sep + po_mk + os.sep + ima, False, '|', pickl=True, propuski=True)
            self.set_glob_tk_title(
                nom_tk + '$' + nom_dse + "$" + nom_nazv + "$по маршрутной карте " + po_mk)

        if spisok_tk == ['']:
            return
        self.nom_tk = nom_tk
        self.dse_nn = nom_dse
        self.dse_naim = nom_nazv
        marshrut = []
        flag_naid = False
        for i in range(10, len(spisok_tk)):
            if spisok_tk[i][20] == '1':
                marshrut.append(spisok_tk[i][4])
            if spisok_tk[i][20] == '0':
                if flag_naid:
                    break
                flag_naid = True

        self.ui.lbl_marsh.setText('-->'.join(marshrut))
        if self.ui.tabWidget_2.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_2, 'ЦП'):
            if len(spisok_tk) > 10 and 'фровая подпи' in spisok_tk[10][15]:
                # CQT.msgbox(f'Документ подписан {spisok_tk[10][15]}')
                # self.WebBrowser = self.ui.axWidget
                self.ui.axWidget.setFocusPolicy(QtCore.Qt.StrongFocus)
                self.ui.axWidget.setControl("{8856F961-340A-11D0-A96B-00C04FD705A2}")
                rez = db_files_load(self,spisok_tk[10][15])
                if rez:
                    f = Path(rez).as_uri()
                    self.ui.axWidget.dynamicCall('Navigate(const QString&)', f)

        nn, nazv = [x for x in spisok_tk[0][0].split('$')]
        le_n_dse.setText(nn)
        le_naim_dse.setText(nazv)
        tk, km, es = [x for x in spisok_tk[1][0].split('/')]
        le_n_tk.setText(tk)
        le_n_tk_km.setText(km)
        le_n_tk_es.setText(es)
        lit.setCurrentText(spisok_tk[2][0])
        razr.setText(spisok_tk[3][0])
        d_raz.setText(spisok_tk[4][0])
        prov.setText(spisok_tk[5][0])
        prov.setEnabled(False)
        self.ui.btn_validate.setEnabled(True)
        if self.is_valid_row_approve():
            self.ui.btn_validate.setEnabled(False)
        norm.setText(spisok_tk[6][0])
        metr.setText(spisok_tk[7][0])
        nor_kont.setText(spisok_tk[8][0])
        prim.setText(spisok_tk[9][0])

    @CQT.onerror
    def vibor_dse(self, po_mk=False,*args):
        if self.place.ИспПроверкуТехартыВнесениеВидаИВесаТО:
            if not KPT.check_plan_responce_sort_c_weight(self):
                self.ui.tblw_dse.setEnabled(False)
                return False
        self.ui.tblw_dse.setEnabled(True)
        self.load_zagolovok_dse(po_mk)
        if F.user_full_namre() in self.DICT_EMPLOEE_FULL:
            if self.DICT_EMPLOEE_FULL[F.user_full_namre()]['Подразделение'] == 'Технологический отдел Производства':
                neobr_ii = II.check_neobr_ii(self)
                if type(neobr_ii) == int:
                    if CQT.msgboxgYN(f'Имеются необработанные извещения об изменении(см. вкладку Извещения об изменении).\n'
                                     f'Перейти к обработке?'):
                        self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget,'Извещения об изменении'))
                    else:
                        #CQT.msgbox('Очень жаль, их не много, может посчитаем сколько накопилось ИИ?')
                        #F.sleep(round(neobr_ii/15))
                        #CQT.msgbox(f'Не обработано {neobr_ii} ИИ, не нравится ждать? \n\n Не трать свое время, обработай ИИ это важно.')
                        pass
                return True
        return True


    @CQT.onerror
    def save_shir_kol_tree(self):
        tree = self.ui.tree
        arr_shir = []
        for i in range(tree.columnCount()):
            arr_shir.append(tree.columnWidth(i))
        if F.existence_file_c(CMS.tmp_dir()) == False:
            F.create_dir_c(CMS.tmp_dir())
        F.write_file_c(CMS.tmp_dir() + os.sep + 'shir_kol_tree.txt', arr_shir, separ='', pickl=True)

    @CQT.onerror
    def load_shir_kol_tree(self):
        tree = self.ui.tree
        if F.existence_file_c(CMS.tmp_dir() + os.sep + 'shir_kol_tree.pickle'):
            arr = F.open_file_c(CMS.tmp_dir() + os.sep + 'shir_kol_tree.txt', pickl=True)
            for i in range(len(arr)):
                tree.setColumnWidth(i, int(arr[i]))

    @CQT.onerror
    def obnovit_param_tablic(self,*args):
        tree = self.ui.tree
        item = tree.currentItem()
        if item == None:
            return
        level_c = item.text(20)

        tree.setToolTip(f'{item.text(0)} | Файл: {item.text(15)}')

        self.ui.tab_op.clearContents()
        self.ui.tab_op.setRowCount(0)
        self.ui.tap_per.clearContents()
        self.ui.tap_per.setRowCount(0)
        self.ui.tap_per_insrt.clearContents()
        self.ui.tap_per_insrt.setRowCount(0)
        self.ui.tap_per_osnast.clearContents()
        self.ui.tap_per_osnast.setRowCount(0)
        self.cvet_knopki()
        if level_c == "0":
            self.obnovit_param_tabl_kar(item)
            self.obnovit_param_tabl_kar_doc(item)
            self.obnovit_param_tabl_oper_mat()
        if level_c == "1":
            self.obnovit_param_tabl_oper_doc(item)
            self.obnovit_param_tabl_oper()
            self.obnovit_param_tabl_kar(item.parent())
            self.obnovit_param_tabl_oper_mat()
            self.obnovit_param_tabl_kar_doc(item.parent())
        if level_c == "2":
            self.obnovit_param_tabl_oper_doc(item.parent())
            self.obnovit_param_tabl_oper()
            self.obnovit_param_tabl_kar(item.parent().parent())
            self.obnovit_param_tabl_kar_doc(item.parent().parent())
            self.obnovit_param_tabl_pereh()

    @CQT.onerror
    def obnovit_param_tabl_oper_mat(self):
        tab_oper_mat = self.ui.tbl_oper_mat
        if self.ui.tree.currentItem() == None:
            return
        par = self.ui.tree.currentItem().parent()
        if par == None:
            kod_par = self.ui.tree.currentItem().text(3)
        else:
            kod_par = par.text(3)
        slov_op = self.slovar_drev(1, kod_par)
        spisok_zn_op = []
        spisok_zn_op.append('ID' + "|" + 'Номер' + "|" + 'Операция')
        n = 0
        for i in slov_op.keys():
            spis_k = slov_op[i]
            spisok_zn_op.append(spis_k[3] + "|" + spis_k[2] + "|" + spis_k[0])
        #CQT.fill_vtable_c(self, tab_oper_mat, spisok_zn_op, "|", True)
        CQT.fill_wtabl_old_c(self,spisok_zn_op,tab_oper_mat,separ='|',isp_hat_c=True)
        tab_oper_mat.resizeColumnsToContents()
        tab_oper_mat.horizontalHeader().setStretchLastSection(True)

    @CQT.onerror
    def obnovit_param_tabl_pereh(self):
        tabl = self.ui.tap_per
        tabl_osn = self.ui.tap_per_osnast
        tabl_ins = self.ui.tap_per_insrt
        par = self.ui.tree.currentItem()
        kod_par = par.text(3)
        slov_per = self.slovar_drev(2, kod_par)
        tabl.clearContents()
        tabl.setRowCount(len(slov_per))
        tabl_osn.clearContents()
        tabl_osn.setRowCount(9)
        tabl_ins.clearContents()
        tabl_ins.setRowCount(9)
        n = 0
        for i in slov_per.keys():
            spis_k = slov_per[i]
            cellinfo = QtWidgets.QTableWidgetItem(spis_k[3])
            tabl.setItem(n, 0, cellinfo)
            cellinfo = QtWidgets.QTableWidgetItem(spis_k[2])
            tabl.setItem(n, 1, cellinfo)
            cellinfo = QtWidgets.QTableWidgetItem(spis_k[7])
            tabl.setItem(n, 2, cellinfo)
            for j in range(4, 3):
                cellinfo = QtWidgets.QTableWidgetItem(spis_k[j])
                tabl.setItem(n, j - 1, cellinfo)
            s_osn = spis_k[11].split('$')
            for j in range(0, len(s_osn)):
                cellinfo = QtWidgets.QTableWidgetItem(s_osn[j])
                tabl_osn.setItem(j, 0, cellinfo)
            s_ins = spis_k[12].split('$')
            for j in range(0, len(s_ins)):
                cellinfo = QtWidgets.QTableWidgetItem(s_ins[j])
                tabl_ins.setItem(j, 0, cellinfo)
            n += 1
        for i in range(0, tabl_osn.rowCount()):
            tabl_osn.setRowHeight(i, 18)
        for i in range(0, tabl_ins.rowCount()):
            tabl_ins.setRowHeight(i, 18)
        tabl_osn.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        tabl_ins.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        tabl.horizontalHeader().setStretchLastSection(True)
        tabl.resizeColumnsToContents()
        tabl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

    @CQT.onerror
    def obnovt_drevo_s_tabl1_op(self,*args):
        if '*' not in  self.glob_tk_title:
            self.set_glob_tk_title(self.glob_tk_title + '*')
        tree = self.ui.tree
        tabl = self.ui.tab_op
        tabl_doc = self.ui.tab_op_doc
        if self.ui.tree.currentItem() == None:
            CQT.msgbox('Не выполнено')
            return
        cur_str = self.ui.tree.currentItem().text(3)
        if tabl.rowCount() == 0:
            return
        hint_combination = "Используйте комбинацию (CTRL + ENTER Нажав на ячейку для более точного подбора)"
        msg_list = [['№', 'Операция', 'Сообщение']]
        for i in range(0, tabl.rowCount()):
            tsht = tabl.item(i, 6).text().replace(',', '.').strip()
            tpz = tabl.item(i, 5).text().replace(',', '.').strip()
            tabl.item(i, 5).setText(tpz)
            tabl.item(i, 6).setText(tsht)
            if self.flag_proverka_op:
                oper_id = CQT.valt(tabl, '№', i)
                oper_name = CQT.valt(tabl, 'Операция', i)
                append_msg = lambda msg: msg_list.append([oper_id, oper_name, msg])
                if not F.is_numeric(tpz.lstrip(CMS.Techkards.UNRECALC_MARK)):
                    append_msg('Тпз не число')
                    tabl.setCurrentCell(i, 5)
                if not F.is_numeric(tsht.lstrip(CMS.Techkards.UNRECALC_MARK)):
                    append_msg('Тшт не число')
                    tabl.setCurrentCell(i, 6)
                if F.is_numeric(tabl.item(i, 7).text().strip()) == False:
                    append_msg('Код профессии не число')
                    tabl.setCurrentCell(i, 7)
                if F.is_numeric(tabl.item(i, 8).text().strip()) == False:
                    append_msg('Кол-во исполнителей не число')
                    tabl.setCurrentCell(i, 8)
                if F.is_numeric(tabl.item(i, 9).text().strip()) == False:
                    append_msg('КОИД не число')
                    tabl.setCurrentCell(i, 9)
                if F.valm(tabl.item(i, 5).text().strip()) == 0:
                    append_msg('В операциях не может Тпз равно 0 ' + tabl.item(i, 1).text().strip())
                if F.valm(tabl.item(i, 8).text().strip()) > 2:
                    append_msg('В операциях не может быть больше двух исполнителей ' + tabl.item(i, 1).text().strip())
                prof = CQT.valt(tabl, 'Проф.', i)
                if prof not in self.DICT_PROFESSIONS:
                    append_msg(f'Код профессии "{prof}" некорректен или устарел\n{hint_combination}')
        if len(msg_list) > 1:
            CQT.msgboxg_get_table_ok_inf(self, 'Обнаружены ошибки', msg_list)
            return
        for i in range(0, tabl.rowCount()):
            for j in range(3, tabl.columnCount() - 1):
                self.zapis_v_drevo(tabl.item(i, 0).text(), j + 1, F.clear_row_for_separ_c(tabl.item(i, j).text()))
            self.zapis_v_drevo(tabl.item(i, 0).text(), 11, F.clear_row_for_separ_c(tabl.item(i, 9).text()))

        if tree.currentItem().text(20) == '2':
            obr = tree.currentItem().parent().text(3)
        if tree.currentItem().text(20) == '1':
            obr = tree.currentItem().text(3)

        s_doc = []
        for i in range(0, tabl_doc.rowCount()):
            if tabl_doc.item(i, 0) != None:
                s_doc.append(F.clear_row_for_separ_c(tabl_doc.item(i, 0).text()))
        self.zapis_v_drevo(obr, 13, '$'.join(s_doc))
        try:
            self.save_tk()
        except:
            CQT.msgbox(f'Неудачно')
            return
        CQT.set_color_of_obj_c(self.ui.Button_t_op)
        CQT.highlight_tree_values_c(self.ui.tree, 3, cur_str)

    @CQT.onerror
    def obnovt_drevo_s_tabl3_kar(self,*args):
        if '*' not in  self.glob_tk_title:
            self.set_glob_tk_title(self.glob_tk_title + '*')
        tabl = self.ui.tab_kar
        tabl_doc = self.ui.tab_tk_doc
        if self.ui.tree.currentItem() == None:
            return
        cur_str = self.ui.tree.currentItem().text(3)

        iskl_sp = []
        if tabl.rowCount() == 0:
            return
        for i in range(0, tabl.rowCount()):
            for j in range(1, tabl.columnCount()):
                if j not in iskl_sp:
                    self.zapis_v_drevo(tabl.item(i, 0).text(), j + 4, F.clear_row_for_separ_c(tabl.item(i, j).text()))
        s_doc = []
        for i in range(0, tabl_doc.rowCount()):
            if tabl_doc.item(i, 0) != None:
                s_doc.append(F.clear_row_for_separ_c(tabl_doc.item(i, 0).text()))
        self.zapis_v_drevo(tabl.item(0, 0).text(), 13, '$'.join(s_doc))
        try:
            self.save_tk()
        except:
            CQT.msgbox(f'Неудачно')
            return
        CQT.set_color_of_obj_c(self.ui.Button_t_kar)
        CQT.highlight_tree_values_c(self.ui.tree, 3, cur_str)

    @CQT.onerror
    def obnovt_drevo_s_tab2_per(self,*args):
        if '*' not in  self.glob_tk_title:
            self.set_glob_tk_title(self.glob_tk_title + '*')
        tabl = self.ui.tap_per
        tabl_osn = self.ui.tap_per_osnast
        tabl_ins = self.ui.tap_per_insrt
        cur_str = self.ui.tree.currentItem().text(3)

        if tabl.rowCount() == 0:
            return
        for i in range(0, tabl.rowCount()):
            tabl.item(i, 2).setText(tabl.item(i, 2).text().replace(',', '.'))
            self.zapis_v_drevo(tabl.item(i, 0).text(), 7, F.clear_row_for_separ_c(tabl.item(i, 2).text()))
            self.zapis_v_drevo(tabl.item(i, 0).text(), 4, '')
        s_osn = []
        for i in range(0, tabl_osn.rowCount()):
            if tabl_osn.item(i, 0) != None:
                s_osn.append(F.clear_row_for_separ_c(tabl_osn.item(i, 0).text()))
        self.zapis_v_drevo(tabl.item(0, 0).text(), 11, '$'.join(s_osn))

        s_ins = []
        for i in range(0, tabl_ins.rowCount()):
            if tabl_ins.item(i, 0) != None:
                s_ins.append(F.clear_row_for_separ_c(tabl_ins.item(i, 0).text()))
        self.zapis_v_drevo(tabl.item(0, 0).text(), 12, '$'.join(s_ins))
        self.tree_noma_vrem()
        try:
            self.save_tk()
        except:
            CQT.msgbox(f'Неудачно')
            return
        CQT.set_color_of_obj_c(self.ui.Button_t_per)
        # index = self.ui.tree.model().index()
        CQT.highlight_tree_values_c(self.ui.tree, 3, cur_str)
        # self.ui.tree.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.NoUpdate)

    @CQT.onerror
    def zapis_v_drevo(self, ID, kol, item):
        it = QtWidgets.QTreeWidgetItemIterator(self.ui.tree)
        while it.value():
            currentItem = it.value()
            if currentItem.text(3) == str(ID):
                currentItem.setText(kol, item)
                return
            it += 1

    @CQT.onerror
    def colors_into_tree_c(self, r, g, b, a):
        it = QtWidgets.QTreeWidgetItemIterator(self.ui.tree)
        while it.value():
            currentItem = it.value()
            if currentItem.parent() == None:
                obr = currentItem.text(2)
                while it.value():
                    currentItem = it.value()
                    if obr in currentItem.text(3):
                        for _ in range(0, 3):
                            currentItem.setBackground(_, QtGui.QColor(r, g, b, a))
                    it += 1
                return
            it += 1

    @CQT.onerror
    def obnovit_param_tabl_kar_doc(self, obj):
        tabl_doc = self.ui.tab_tk_doc
        tabl_doc.clearContents()
        tabl_doc.setRowCount(9)
        s_doc = obj.text(13).split('$')
        for j in range(0, len(s_doc)):
            cellinfo = QtWidgets.QTableWidgetItem(s_doc[j])
            tabl_doc.setItem(j, 0, cellinfo)
        for i in range(0, tabl_doc.rowCount()):
            tabl_doc.setRowHeight(i, 18)
        # tabl_doc.resizeColumnsToContents()
        # tabl_doc.horizontalHeader().setStretchLastSection(True)
        tabl_doc.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

    @CQT.onerror
    def obnovit_param_tabl_kar(self, item):
        tabl = self.ui.tab_kar
        if item == None:
            return
        spis = []
        spis.append(item.text(3))
        for i in range(5, 8):
            spis.append(item.text(i))
        tabl.clearContents()
        tabl.setRowCount(1)
        n = 0
        for i in spis:
            cellinfo = QtWidgets.QTableWidgetItem(i)
            tabl.setItem(0, n, cellinfo)
            n += 1
        # tabl.resizeColumnsToContents()
        # tabl.horizontalHeader().setStretchLastSection(True)
        tabl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

    @CQT.onerror
    def obnovit_param_tabl_oper_doc(self, obj):
        tabl_doc = self.ui.tab_op_doc
        tabl_doc.clearContents()
        tabl_doc.setRowCount(9)
        s_doc = obj.text(13).split('$')
        for j in range(0, len(s_doc)):
            cellinfo = QtWidgets.QTableWidgetItem(s_doc[j])
            tabl_doc.setItem(j, 0, cellinfo)
        for i in range(0, tabl_doc.rowCount()):
            tabl_doc.setRowHeight(i, 18)
        # tabl_doc.resizeColumnsToContents()
        # tabl_doc.horizontalHeader().setStretchLastSection(True)
        tabl_doc.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

    @CQT.onerror
    def obnovit_param_tabl_oper(self):
        tabl = self.ui.tab_op
        par = self.ui.tree.currentItem().parent()
        if par == None:
            return
        kod_par = par.text(3)
        slov_op = self.slovar_drev(1, kod_par)

        list_of_dicts = []
        for k,v in slov_op.items():
            list_of_dicts.append({
                'ID':v[3], '№':v[2], 'Операция':v[0], 'Раб.центр':v[4], 'Оборудование':v[5], 'Тп.з.':v[6], 'Тшт.':v[7],
                'Проф.':v[8], 'N раб.':v[9], 'КОИД':v[11]}
                )
        exclude_edit = []
        if self.ogr_rezim():
            exclude_edit = ['Раб.центр']
        set_editable = {}
        if len(list_of_dicts):
            set_editable = {i for i,k in enumerate(list_of_dicts[0].keys()) if k not in exclude_edit}
        CQT.fill_wtabl(list_of_dicts,tabl,set_editeble_col_nomera=set_editable,height_row=24,min_width_col=0,
                       auto_type=False,list_column_widths=CMS.load_column_widths(self,tabl))
        return


    @CQT.onerror
    def spisok(self,*args):
        self.slovar_drev()

    @CQT.onerror
    def slovar_drev(self, level_c='xxx', kod_par=''):
        spisok = {}
        it = QtWidgets.QTreeWidgetItemIterator(self.ui.tree)
        while it.value():
            currentItem = it.value()

            if level_c == 'xxx':
                sp = []
                for i in range(0, currentItem.columnCount()):
                    sp.append(currentItem.text(i))
                spisok[currentItem.text(3)] = sp
            if level_c == 0:
                if currentItem.text(currentItem.columnCount() - 1) == "0":
                    sp = []
                    for i in range(0, currentItem.columnCount()):
                        sp.append(currentItem.text(i))
                    spisok[currentItem.text(3)] = sp
            if level_c == 1:
                if currentItem.text(currentItem.columnCount() - 1) == "1":
                    if kod_par in currentItem.text(3):
                        sp = []
                        for i in range(0, currentItem.columnCount()):
                            sp.append(currentItem.text(i))
                        spisok[currentItem.text(3)] = sp
            if level_c == 2:
                if currentItem.text(currentItem.columnCount() - 1) == "2":
                    if kod_par == currentItem.text(3): # по задаче (100056163 )
                        sp = []
                        for i in range(0, currentItem.columnCount()):
                            sp.append(currentItem.text(i))
                        spisok[currentItem.text(3)] = sp

            if currentItem.childCount() == 0:
                if currentItem.checkState(0) == 0:
                    pass
            it += 1
        if level_c == 'xxx':
            for i in spisok.keys():
                # print(i + ' - ' + ','.join(spisok[i]))
                pass
        return spisok

    @CQT.onerror
    def sost(self):
        it = QtWidgets.QTreeWidgetItemIterator(self.ui.tree)
        while it.value():
            currentItem = it.value()
            print('-------------')
            for i in range(0, currentItem.columnCount() + 1):
                print(currentItem.text(i), end='|')
            if currentItem.childCount() == 0:
                if currentItem.checkState(0) == 0:
                    pass
            print('')
            it += 1


    @CQT.onerror
    def dobav_V_tree_root(self, strok):
        tree = self.ui.tree
        root = QtWidgets.QTreeWidgetItem(tree)
        root.setText(0, 'Техкарта ' + str(strok))
        root.setText(1, '')
        root.setText(2, 'Т' + str(strok))
        root.setText(3, 'Т' + str(strok))
        root.setText(5, F.date())
        root.setText(6, os.environ.get("USERNAME"))
        root.setText(20, '0')
        # root.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        tree.addTopLevelItem(root)
        tree.setCurrentItem(root)
        self.colors_into_tree_c(145, 218, 145, 255)
        self.w2 = mywindow2(self, tree, "Древо")
        self.w2.showNormal()
        self.w2.ui2.lineEdit.setText(self.ui.tree.currentItem().text(0))
        self.w2.ui2.lineEdit.setFocus()

    @CQT.onerror
    def zagruzka_shablona_operacii(self, child, PUT_K_TMP):
        putf = PUT_K_TMP + os.sep + "shablon_op.txt"
        if F.existence_file_c(putf):
            spis = F.open_file_c(putf, separ='|')
            for i in range(1, len(spis)):
                if spis[i][0] == child.text(0):
                    if child.text(4).strip() == '':
                        child.setText(4, spis[i][1])
                    if child.text(5).strip() == '':
                        child.setText(5, spis[i][2])
                    if child.text(8).strip() == '':
                        child.setText(8, spis[i][3])
                    if child.text(13).strip() == '':
                        child.setText(13, spis[i][4]) if len(spis[i]) > 4 else None
                    break
            return child
        return child

    @CQT.onerror
    def dobav_V_tree_oper(self, item="", level_c=""):
        tree = self.ui.tree
        if item == "":
            item = tree
        strok = item.childCount()
        child1 = QtWidgets.QTreeWidgetItem(item)
        child1.setText(0, 'Операция')
        zap_strok = '0' * (3 - len(str((strok + 1) * 5))) + str((strok + 1) * 5)
        child1.setText(1, '')
        child1.setText(2, zap_strok)
        child1.setText(3, level_c + '-' + zap_strok)
        child1.setText(9, '1')
        child1.setText(11, '1')
        child1.setText(20, '1')

        # root.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        tree.addTopLevelItem(child1)
        tree.expandItem(item)
        tree.setCurrentItem(child1)
        self.colors_into_tree_c(145, 218, 145, 255)
        self.w2 = mywindow2(self,tree, "Древо")
        self.w2.showNormal()
        self.w2.ui2.lineEdit.setText(self.ui.tree.currentItem().text(0))
        # self.w2.ui2.lineEdit.setFocus()

    @CQT.onerror
    def dobav_V_tree_perex(self, item="", level_c=""):
        tree = self.ui.tree
        # root = QtWidgets.QTreeWidgetItem(tree)

        if item == "":
            item = tree
        por_nom = item.childCount() + 1
        child1 = QtWidgets.QTreeWidgetItem(item)
        child1.setText(0, 'Переход')
        child1.setText(1, '')
        child1.setText(2, str(por_nom))
        child1.setText(3, level_c + '-' + str(por_nom))
        child1.setText(20, '2')
        # root.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        tree.addTopLevelItem(child1)
        tree.expandItem(item)
        tree.setCurrentItem(child1)
        self.colors_into_tree_c(145, 218, 145, 255)
        self.w2 = mywindow2(self,tree, "Древо")
        self.w2.showNormal()
        self.w2.ui2.lineEdit.setText(self.ui.tree.currentItem().text(0))
        self.w2.ui2.lineEdit.setFocus()

    @CQT.onerror
    def obnovit_numeraciy(self, spisok):
        spisok_old = copy.deepcopy(spisok)
        t = 0
        fl = False
        for i in range(0, len(spisok)):
            if spisok[i][20] == "0":
                t += 1
                o = 0
                spisok[i][2] = "Т" + str(t)
                spisok[i][3] = "Т" + str(t)
                fl= True

            if spisok[i][20] == "1":
                if fl == False:
                    CQT.msgbox(f'Не корректная структура техкарты')
                    return spisok_old
                o += 1
                p = 0
                zap_op = '0' * (3 - len(str(o * 5))) + str(o * 5)
                spisok[i][2] = zap_op
                spisok[i][3] = "Т" + str(t) + "-" + zap_op

            if spisok[i][20] == "2":
                if fl == False:
                    CQT.msgbox(f'Не корректная структура техкарты')
                    return spisok_old
                p += 1
                zap_per = str(p)
                spisok[i][2] = zap_per
                spisok[i][3] = "Т" + str(t) + "-" + zap_op + "-" + zap_per
        return spisok

    @CQT.onerror
    def sohran_buff(self, nom, tabl):
        item = tabl
        stroki = CQT.list_from_wtabl_c(item, '|')
        if F.existence_file_c(self.PUT_K_TMP) == False:
            F.create_dir_c(self.PUT_K_TMP)
        puttf = self.PUT_K_TMP + os.sep + str(nom) + ".txt"
        F.write_file_c(puttf, stroki)

    @CQT.onerror
    def get_oper_osn_path(self, operation: str) -> str:
        return os.path.join(self.path_cash_poki, f"osn_{operation}.txt")

    @CQT.onerror
    def get_oper_ins_path(self, operation: str) -> str:
        return os.path.join(self.path_cash_poki, f"ins_{operation}.txt")

    @CQT.onerror
    def get_oper_prim(self, operation: str, pereh: str = '') -> str:
        return str(Path(self.path_cash_poki) / 'tables' / operation / pereh / 'prim.txt')

class mywindow2(QtWidgets.QDialog):  # диалоговое окно
    @CQT.onerror
    def __init__(self, pself:mywindow,  parent=None, item_o="", p1=0, p2=0):
        self.item_o = item_o
        self.p1 = p1
        self.p2 = p2
        self.pself = pself
        self.myparent = parent
        super(mywindow2, self).__init__()
        self.ui2 = Ui_Dialog()
        self.ui2.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle(pself.windowTitle() + " / " +  self.item_o)
        self.PUT_K_TMP = F.put_po_umolch() + os.sep + "tmptehkart"
        self.db_files = pself.db_files
        self.db_naryad = pself.db_naryad
        self.db_mater = pself.db_mater
        self.db_users = pself.db_users
        self.DICT_KOD_OPER = pself.DICT_KOD_OPER
        self.DICT_OPERS = pself.DICT_OPERS
        self.spis_op = pself.spis_op
        self.setFixedWidth(pself.width())
        self.setStyleSheet(pself.styleSheet())
        combo1 = self.ui2.combo1
        combo2 = self.ui2.combo2
        self.ui2.fr_vid.setHidden(True)
        combo1.setEnabled(False)
        combo2.setEnabled(False)
        combo1.setEditable(True)
        combo1.activated.connect(self.vibor_elem1)
        combo2.activated.connect(self.vibor_elem2)

        poki = str(self.pself.place.poki)
        cash = self.pself.xl_formulas.base_dir
        self.bd_docs_txt = str(cash / poki / 'bd_docs.txt')
        self.osnast_txt = str(cash / poki / 'osnast.txt')
        self.instrum_txt = str(cash / poki / 'instrum.txt')
        self.kart_txt = str(cash / poki / 'kart.txt')

        self.ui2.btn_add_weld.clicked.connect(self.btn_add_weld)
        self.ui2.btn_del_welds.clicked.connect(self.btn_del_welds)
        self.ui2.btn_del_one_weld.clicked.connect(lambda *_: operacii.del_one_weld(self))
        self.ui2.tab_vib.cellChanged.connect(lambda row, col: operacii.table_sum_cell_changed(self, row, col))
        self.ui2.btn_del_one_weld.setDefault(False)
        self.ui2.btn_del_one_weld.setAutoDefault(False)
        tab_v = self.ui2.tab_vib
        tab_v.doubleClicked.connect(self.vibor_iz_tab_vib_v_tableW_oper_mat)
        tab_v.itemSelectionChanged.connect(self.get_prim) #14.07.25

        try:
            pself.obj_tbl_tbl_nomen.horizontalScrollBar().valueChanged.connect(
                self.ui2.tbl_filtr.horizontalScrollBar().setValue)
        except:
            pass
        self.ui2.chbox_edit_combos.clicked.connect(self.click_chbox_edit_combos)

        text = self.ui2.lineEdit
        text.setEnabled(False)
        tab = self.ui2.tab_vib
        tab.setEnabled(False)
        self.ui2.lbl_prim.setWordWrap(True)

        if self.item_o == "Док_оп" or self.item_o == "Док_тк":
            tab.setEnabled(True)
            if F.existence_file_c(self.bd_docs_txt):
                spisok = F.open_file_c(self.bd_docs_txt, False)
                spisok.insert(0, 'Код|Наименование|Комментарий')
                CQT.fill_wtabl_old_c(self, spisok, tab, isp_hat_c=True, separ='|', ogr_maxshir_kol=800)
                self.setGeometry(self.frameGeometry().getCoords()[0], 33, self.width(), 1000)
                tab.setFocus()
                CMS.fill_filtr_c(self, self.ui2.tbl_filtr, self.ui2.tab_vib)

        if self.item_o == "Профессия":
            tab.setEnabled(True)

            CQT.fill_wtabl_old_c(self, self.pself.LIST_PROFESSIONS, tab, isp_hat_c=True, separ='', ogr_maxshir_kol=800)
            self.setGeometry(self.frameGeometry().getCoords()[0], 33, self.width(), 1000)
            tab.setFocus()
            CMS.fill_filtr_c(self, self.ui2.tbl_filtr, self.ui2.tab_vib)

        if self.item_o == "Оборудование":
            tab.setEnabled(True)
            list_equipment = CSQ.custom_request_c(self.db_users, f"""SELECT Инв_номер, Наименование, 
             Примечание FROM equipment WHERE poki = {pself.place.poki};""")
            CQT.fill_wtabl_old_c(self, list_equipment, tab, isp_hat_c=True, separ='', ogr_maxshir_kol=800)
            self.setGeometry(self.frameGeometry().getCoords()[0], 33, self.width(), 1000)
            tab.setFocus()
            CMS.fill_filtr_c(self, self.ui2.tbl_filtr, self.ui2.tab_vib)

        if self.item_o == "Раб_ц":
            tab.setEnabled(True)
            list_rc = CSQ.custom_request_c(self.db_users, f"""SELECT Код, Имя, Примечание FROM 
             rab_c WHERE Примечание != 'не использовать' and enabled = 1 and poki == {pself.place.poki} order by Код""") # 07.10.25
            CQT.fill_wtabl_old_c(self, list_rc, tab, isp_hat_c=True, separ='', ogr_maxshir_kol=800)
            self.setGeometry(self.frameGeometry().getCoords()[0], 33, self.width(), 1000)
            tab.setFocus()
            CMS.fill_filtr_c(self, self.ui2.tbl_filtr, self.ui2.tab_vib)

        if item_o == "Материал":
            tab.setEnabled(True)
            #combo1.addItems([_[0] for _ in pself.nomenclature])
            #combo1.setEnabled(True)
            #combo1.setEditable(False)
            #combo1.setMaxVisibleItems(15)
            #combo1.setFocus()

            tab = self.ui2.tab_vib

            list_nomen_by_vid = pself.LIST_NOMEN
            #for _ in self.pself.DICT_NOMEN.keys():
            #
            #    tmp = copy.copy(self.pself.DICT_NOMEN[_])
            #    tmp['Код'] = _
            #    list_nomen_by_vid.append(tmp)
            CQT.set_color_sort_cell_table_c(tab)
            CQT.fill_wtabl(list_nomen_by_vid, tab, ogr_maxshir_kol=800)
            self.ui2.lbl_prim.setText(f'В КД заложено {pself.mat_kd_erp.replace("$"," ")}')
            kod_erp = pself.mat_kd_erp.split("$")[0]
            for i in range(len(list_nomen_by_vid)):
                if list_nomen_by_vid[i]['Код']== kod_erp:
                    CQT.select_cell(tab,i,0)
                    break

            CMS.fill_filtr_c(self, self.ui2.tbl_filtr, tab, spis_znach={'На_удаление':'0'}, hidden_scroll=True)
            CMS.apply_filtr_c(self,self.ui2.tbl_filtr,tab)
            CMS.update_width_filtr(tab, self.ui2.tbl_filtr)

            #custom_request_c = f'''SELECT * FROM nomen WHERE  == 0 ;'''
            #rez = CSQ.custom_request_c(self.db_mater, custom_request_c=custom_request_c, hat_c=True,conn=conn, cur = cur)
            #CQT.fill_wtabl(pself.ne_del_nomen,tab)
            #CQT.fill_wtabl_old_c(self, pself.ne_del_nomen, tab, isp_hat_c=True, separ='', ogr_maxshir_kol=800)
            #CMS.fill_filtr_c(self, self.ui2.tbl_filtr, tab)

            self.setGeometry(application.frameGeometry().getCoords()[0], application.frameGeometry().getCoords()[1], application.width(), application.height())
        self.ui2.lineEdit.setReadOnly(False)

        if item_o == "Оснастка":
            text = f"""ВЫБРАТЬ
                    ВидыНоменклатуры.Наименование КАК Наименование
                ИЗ
                    Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                ГДЕ
                    ВидыНоменклатуры.Ссылка В ИЕРАРХИИ
                            (ВЫБРАТЬ ПЕРВЫЕ 1
                                ВидыНоменклатуры.Ссылка КАК Ссылка
                            ИЗ
                                Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                            ГДЕ
                                ВидыНоменклатуры.Наименование = "{pself.place.Имя}"
                                И ВидыНоменклатуры.ЭтоГруппа = ИСТИНА)
                    И ВидыНоменклатуры.ЭтоГруппа = ЛОЖЬ
                    И ВидыНоменклатуры.ПометкаУдаления = ЛОЖЬ
                УПОРЯДОЧИТЬ ПО
                    Наименование"""
            code, data = APIERP.get_wet_request(text=text)
            list_nomen = []
            if code != 200:
                CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
                self.close()
                return
            list_nomen = [ _["Наименование"] for  _ in data['data']]

            self.ui2.fr_vid.setHidden(False)
            combo1.setEnabled(True)
            combo1.addItems(list_nomen)
            combo1.setEditable(False)
            self.ui2.label_2.setVisible(False)
            self.ui2.combo2.setVisible(False)
            self.ui2.fr_weld.setVisible(False)
            self.ui2.lbl_info_dxf.setVisible(False)
            self.ui2.lineEdit.setReadOnly(True)
            tab.setEnabled(True)
            self.ui2.lbl_prim.setVisible(False)

            #if F.existence_file_c(self.osnast_txt):
            #    sp_sort_c_osn = F.open_file_c(self.osnast_txt, False)
            #    combo1.addItems(sp_sort_c_osn)
            #    self.vibor_elem1()
            #    text.setEnabled(True)
            #    combo1.setFocus()


        if item_o == "Инструмент":
            self.ui2.fr_vid.setHidden(False)
            combo1.setEnabled(True)
            if F.existence_file_c(self.instrum_txt):
                sp_sort_c_ins = F.open_file_c(self.instrum_txt, False)
                combo1.addItems(sp_sort_c_ins)
                self.vibor_elem1()
                text.setEnabled(True)
                combo1.setFocus()

        if item_o == "Древо":
            text.setEnabled(True)
            if parent.currentItem() == None:
                return
            if parent.currentItem().text(20) == '0':
                limit = int(F.scfg('limit_k'))
                if F.existence_file_c(self.kart_txt):
                    strList = F.open_file_c(self.kart_txt, False, "|")
                    list_tmp = []
                    for item in strList:
                        if int(item[1]) > limit:
                            list_tmp.append(item[0])
                    completer = QtWidgets.QCompleter(list_tmp, parent=None)
                    text.setCompleter(completer)
                    combo2.setEnabled(True)
                    combo2.addItems(list_tmp)
                    combo2.setFocus()

            if parent.currentItem().text(20) == '1':
                #limit = int(F.scfg('limit_o'))
                if self.DICT_KOD_OPER == False:
                    CQT.msgbox(f'Не корректно загружена программа')
                    quit()
                spis_oper = [f"{k} / {v}" for k,v in self.DICT_KOD_OPER.items()]
                if spis_oper == False:
                    CQT.msgbox(f'Не удалось загрузить список операций')
                    return
                list_tmp = []
                for oper in spis_oper:
                    list_tmp.append(oper)
                completer = QtWidgets.QCompleter(list_tmp, parent=None)
                text.setCompleter(completer)
                combo2.setEnabled(True)
                combo2.addItems(sorted(list_tmp))

                #combo2.setCurrentIndex(ind)
                combo2.setFocus()
                self.ui2.lbl_info_dxf.setText(str(pself.global_param_tk_dxf))

            if parent.currentItem().text(20) == '2':
                ima_oper = parent.currentItem().parent().text(0)
                pereh_path = self.pself.xl_formulas.get_pereh_txt_path(ima_oper)
                limit_o = int(F.scfg('limit_o'))
                limit = int(F.scfg('limit_p'))
                strList = self.spis_op
                list_tmp = []
                flag_naid = 0
                for item in strList:
                    if item[0] == ima_oper and int(item[1]) > limit_o:
                        flag_naid = 1
                        break
                if flag_naid == 1:
                    if F.existence_file_c(pereh_path):
                        strList = F.open_file_c(pereh_path, False, "|")
                        list_tmp = []
                        for item in strList:
                            if int(item[1]) > limit:
                                list_tmp.append(item[0])
                completer = QtWidgets.QCompleter(list_tmp, parent=None)
                text.setCompleter(completer)
                combo2.setEnabled(True)
                combo2.addItems(sorted(list_tmp)) #16.09.25
                combo2.setFocus()
                combo2.setCurrentText('')
                self.ui2.lbl_prim.setText(pself.ui.lbl_primech_dse.text())
                if 'частей' in self.ui2.lbl_prim.text().lower():
                    CQT.msgbox(self.ui2.lbl_prim.text(),'Я понял',icon=QtWidgets.QMessageBox.Warning)
            self.toggle_access_main_widgets(self.ui2.tab_vib.columnCount() != 0)


        if self.pself.chbox_edit_combos:
            self.ui2.chbox_edit_combos.setChecked(True)
        else:
            self.ui2.chbox_edit_combos.setChecked(False)


    def btn_add_weld(self):
        operacii.add_weld(self)

    def btn_del_welds(self):
        operacii.del_welds(self)

    #+++14.07.25
    def get_prim(self,*args, **kwargs):

        if self.item_o == "Оснастка":
            row = CQT.get_dict_line_form_tbl(self.ui2.tab_vib)
            self.ui2.lineEdit.setText(row['Код'])
            return


        column = self.ui2.tab_vib.currentColumn()
        if column == -1:
            return
        tree = self.pself.ui.tree
        current_item = tree.currentItem()
        selected_text = self.ui2.combo2.currentText()
        level = self.pself.ui.tree.currentItem().text(20)
        oper, pereh = '', ''
        is_excel = False
        if level == '1':
            oper = selected_text
            is_excel = self.pself.xl_formulas.check_op(operation=oper, approved=True)
        elif level == '2':
            oper = current_item.parent().text(0)
            pereh = selected_text
            is_excel = self.pself.xl_formulas.check_per(operation=oper, pereh=pereh, approved=True)
        if is_excel:
            credentials = self.pself.xl_formulas.convert_old_struct(oper, pereh)
            name = self.ui2.tab_vib.horizontalHeaderItem(column).text()
            if isinstance(credentials, dict) and name in credentials:
                comment = credentials[name].get('comment', '')
                self.ui2.lbl_prim.setText(comment)
        elif CFG.Config.place.poki == 1 and oper in operacii.Data_oper_norm.DICT_OPERS_CALC:
            if oper in operacii.Data_oper_norm.DICT_OPERS_CALC:
                name = self.ui2.tab_vib.horizontalHeaderItem(column).text()
                if name in operacii.Data_oper_norm.DICT_OPERS_CALC[oper]:
                    comment = operacii.Data_oper_norm.DICT_OPERS_CALC[oper][name].get("comment", '')
                    self.ui2.lbl_prim.setText(comment)


    #---14.07.25


    @CQT.onerror
    def vibor_iz_tab_vib_v_tableW_oper_mat(self,*args):
        if self.item_o == "Материал":
            tab_v = self.ui2.tab_vib
            tab_mat = self.pself.ui.tableW_oper_mat
            nk_db_nn = CQT.num_col_by_name_c(tab_v, 'Код')
            nk_db_naim = CQT.num_col_by_name_c(tab_v, 'Наименование')
            nk_db_edizm = CQT.num_col_by_name_c(tab_v, 'ЕдиницаИзмерения')
            nk_tblm_nn = CQT.num_col_by_name_c(tab_mat, 'Код')
            nk_tblm_naim = CQT.num_col_by_name_c(tab_mat, 'Материал')
            nk_tblm_edizm = CQT.num_col_by_name_c(tab_mat, 'Ед.Изм')
            nk_tblm_norma = CQT.num_col_by_name_c(tab_mat, 'Норма')
            for i in range(0, tab_mat.columnCount()):
                if tab_mat.item(tab_mat.currentRow(), i) == None:
                    cellinfo = QtWidgets.QTableWidgetItem(tab_v.item(tab_v.currentRow(), i).text())
                    tab_mat.setItem(tab_mat.currentRow(), i, cellinfo)
            tab_mat.item(tab_mat.currentRow(), nk_tblm_nn).setText(
                tab_v.item(tab_v.currentRow(), nk_db_nn).text())
            tab_mat.item(tab_mat.currentRow(), nk_tblm_naim).setText(
                tab_v.item(tab_v.currentRow(), nk_db_naim).text())
            tab_mat.item(tab_mat.currentRow(), nk_tblm_edizm).setText(
                tab_v.item(tab_v.currentRow(), nk_db_edizm).text())
            tab_mat.item(tab_mat.currentRow(), nk_tblm_norma).setText(
                '0')
            self.hide()
            osn_mat.zagr_sortament(self.pself)
            #application.ui.tabW_mat.setCurrentIndex(1)
            self.pself.ui.tbl_resch_mater.setFocus()
            if self.pself.ui.tbl_resch_mater.item(0, 0) != None:
                self.pself.ui.tbl_resch_mater.setCurrentCell(0, 0)
            tab_mat.horizontalHeader().setStretchLastSection(True)
            tab_mat.resizeColumnsToContents()

        if self.item_o == "Оснастка":
            self.cust_keyReleaseEvent(16777220,QtCore.Qt.ControlModifier)

    @CQT.onerror
    def cust_keyReleaseEvent(self, ekey:int,modifiers:int):
        # print(str(int(modifiers)) + ' ' +  str(ekey))
        if self.ui2.tbl_filtr.hasFocus():
            if ekey == 16777220:
                CMS.apply_filtr_c(self, self.ui2.tbl_filtr, self.ui2.tab_vib)
                return
        tbl_handler = False
        if self.item_o == "Док_оп":
            tab_v = self.ui2.tab_vib
            if tab_v.hasFocus() == False:
                return
            if ekey == QtCore.Qt.Key_Return:
                tab_doc = self.pself.ui.tab_op_doc
                if tab_doc.item(tab_doc.currentRow(), 0) != None:
                    tab_doc.item(tab_doc.currentRow(), 0).setText(tab_v.item(tab_v.currentRow(), 0).text())
                else:
                    cellinfo = QtWidgets.QTableWidgetItem(tab_v.item(tab_v.currentRow(), 0).text())
                    tab_doc.setItem(tab_doc.currentRow(), 0, cellinfo)
                self.hide()
        if self.item_o == "Док_тк":
            tab_v = self.ui2.tab_vib
            if tab_v.hasFocus() == False:
                return
            if ekey == QtCore.Qt.Key_Return:
                tab_doc = self.pself.ui.tab_tk_doc
                if tab_doc.item(tab_doc.currentRow(), 0) != None:
                    tab_doc.item(tab_doc.currentRow(), 0).setText(tab_v.item(tab_v.currentRow(), 0).text())
                else:
                    cellinfo = QtWidgets.QTableWidgetItem(tab_v.item(tab_v.currentRow(), 0).text())
                    tab_doc.setItem(tab_doc.currentRow(), 0, cellinfo)
                self.hide()
        if self.item_o == "Профессия":
            tab_v = self.ui2.tab_vib
            if tab_v.hasFocus() == False:
                return
            if ekey == QtCore.Qt.Key_Return:
                tab_op = self.pself.ui.tab_op
                if tab_op.item(tab_op.currentRow(), 7) != None:
                    tab_op.item(tab_op.currentRow(), 7).setText(tab_v.item(tab_v.currentRow(), 0).text())
                else:
                    cellinfo = QtWidgets.QTableWidgetItem(tab_v.item(tab_v.currentRow(), 0).text())
                    tab_op.setItem(tab_op.currentRow(), 7, cellinfo)
                self.hide()
        if self.item_o == "Оборудование":
            tab_v = self.ui2.tab_vib
            if tab_v.hasFocus() == False:
                return
            if ekey == QtCore.Qt.Key_Return:
                tab_op = self.pself.ui.tab_op
                if tab_op.item(tab_op.currentRow(), 4) != None:
                    tab_op.item(tab_op.currentRow(), 4).setText(tab_v.item(tab_v.currentRow(), 1).text())
                else:
                    cellinfo = QtWidgets.QTableWidgetItem(tab_v.item(tab_v.currentRow(), 1).text())
                    tab_op.setItem(tab_op.currentRow(), 4, cellinfo)
                self.hide()
        if self.item_o == "Раб_ц":
            tab_v = self.ui2.tab_vib
            if tab_v.hasFocus() == False:
                return
            if ekey == QtCore.Qt.Key_Return:
                tab_op = self.pself.ui.tab_op
                if tab_op.item(tab_op.currentRow(), 3) != None:
                    tab_op.item(tab_op.currentRow(), 3).setText(tab_v.item(tab_v.currentRow(), 0).text())
                else:
                    cellinfo = QtWidgets.QTableWidgetItem(tab_v.item(tab_v.currentRow(), 0).text())
                    tab_op.setItem(tab_op.currentRow(), 3, cellinfo)
                self.hide()
        if self.item_o == "Материал":
            tab_v = self.ui2.tab_vib
            if tab_v.hasFocus():
                if ekey == QtCore.Qt.Key_Return:
                    self.vibor_iz_tab_vib_v_tableW_oper_mat()
            if self.ui2.tbl_filtr.hasFocus():
                if ekey == QtCore.Qt.Key_Return:
                    CMS.apply_filtr_c(self, self.ui2.tbl_filtr, tab_v)
        if self.item_o == "Оснастка":
            if self.ui2.tab_vib.hasFocus():
                tbl_handler = True
        if modifiers == QtCore.Qt.ControlModifier: 
            if ekey == 83:
                if self.ui2.tab_vib.isEnabled():
                    self.ui2.tab_vib.setFocus(True)
            if ekey == 87:
                self.ui2.lineEdit.setFocus(True)

        if self.ui2.lineEdit.text().strip() == "":
            return
        if len(self.ui2.lineEdit.text().strip()) < 4:
            return
        if not tbl_handler and self.ui2.lineEdit.hasFocus() == False:
            return

        if self.item_o == "Оснастка" or self.item_o == "Инструмент":

            if ekey == QtCore.Qt.Key_Return:  # and int(modifiers) == QtCore.Qt.ControlModifier:
                combo1 = self.ui2.combo1
                combo2 = self.ui2.combo2
                if combo1.currentText() == '':
                    combo1.setFocus(True)
                    CQT.msgbox('Не выбрана категория')
                    return
                print("Нажата клавиша <Enter>")
                cu = self.myparent
                strok = self.ui2.lineEdit.text().strip().replace('\n', ' ')
                strok = F.clear_row_for_separ_c(strok)
                strok = F.capital_letter_c(strok)
                self.hide()
                cellinfo = QtWidgets.QTableWidgetItem(strok)
                cu.setItem(cu.currentRow(), 0, cellinfo)
                cu.item(self.p1, 0).setText(strok)
                if self.item_o == "Оснастка":
                    if F.existence_file_c(self.osnast_txt):
                        arr_tmp = F.open_file_c(self.osnast_txt)
                        flag_naid = 0
                        for item_arr in arr_tmp:
                            if item_arr == combo1.currentText():
                                flag_naid = 1
                                break
                        if flag_naid == 0:
                            arr_tmp.append(combo1.currentText())
                        F.write_file_c(self.osnast_txt, arr_tmp)
                    else:
                        arr_tmp = []
                        arr_tmp.append(combo1.currentText())
                        F.write_file_c(self.osnast_txt, arr_tmp)
                    osn_path = self.pself.get_oper_osn_path(combo1.currentText())
                    if F.existence_file_c(osn_path):
                        arr_osn = F.open_file_c(osn_path)
                        flag_naid = 0
                        for item_arr in arr_osn:
                            if item_arr == strok:
                                flag_naid = 1
                                break
                        if flag_naid == 0:
                            arr_osn.append(strok)
                        F.write_file_c(osn_path, arr_osn)
                    else:
                        arr_osn = []
                        arr_osn.append(strok)
                        F.write_file_c(osn_path, arr_osn)
                if self.item_o == "Инструмент":
                    if F.existence_file_c(self.instrum_txt):
                        arr_tmp = F.open_file_c(self.instrum_txt)
                        flag_naid = 0
                        for item_arr in arr_tmp:
                            if item_arr == combo1.currentText():
                                flag_naid = 1
                                break
                        if flag_naid == 0:
                            arr_tmp.append(combo1.currentText())
                        F.write_file_c(self.instrum_txt, arr_tmp)
                    else:
                        arr_tmp = []
                        arr_tmp.append(combo1.currentText())
                        F.write_file_c(self.instrum_txt, arr_tmp)
                    ins_path = self.pself.get_oper_ins_ins_path(combo1.currentText())
                    if F.existence_file_c(ins_path):
                        arr_ins = F.open_file_c(ins_path)
                        flag_naid = 0
                        for item_arr in arr_ins:
                            if item_arr == strok:
                                flag_naid = 1
                                break
                        if flag_naid == 0:
                            arr_ins.append(strok)
                        F.write_file_c(ins_path, arr_ins)
                    else:
                        arr_ins = []
                        arr_ins.append(strok)
                        F.write_file_c(ins_path, arr_ins)

        if self.item_o == "Древо":
            if ekey == QtCore.Qt.Key_Return:
                print("Нажата клавиша <Control Enter>tree")
                strok = self.ui2.lineEdit.text().strip().replace('\n', ' ')
                strok = F.clear_row_for_separ_c(strok)
                strok = F.capital_letter_c(strok)
                item = self.pself.ui.tree.currentItem()
                if item == None:
                    return

                #print(item.text(0))
                item.setText(0, strok)
                #print(item.text(0))

                if item.text(20) == '0':
                    if F.existence_file_c(self.kart_txt):
                        arr_tmp = F.open_file_c(self.kart_txt, False, "|")
                        flag_naid = 0
                        for item_arr in arr_tmp:
                            if item_arr[0] == strok:
                                item_arr[1] = str(int(item_arr[1]) + 1)
                                flag_naid = 1
                                break
                        if flag_naid == 0:
                            arr_tmp.append([strok, '1'])
                        F.write_file_c(self.kart_txt, arr_tmp, "|")
                    else:
                        arr_tmp = []
                        arr_tmp.append([strok, '1'])
                        F.write_file_c(self.kart_txt, arr_tmp, "|")
                if self.ui2.tab_vib.rowCount() == 0:
                    item.setText(7, '0')
                else:

                    if item.text(20) == '1':
                        tmp = CQT.list_from_wtabl_c(self.ui2.tab_vib,'',True,False,True,False)
                        if tmp != []:
                            f = {}
                            if len(tmp) > 1:
                                for idx, hat in enumerate(tmp[0].keys()):
                                    f[hat] = ';'.join(elem[hat] for elem in tmp)
                                tmp = [f]
                            CQT.fill_wtabl(tmp,self.ui2.tab_vib,'*',auto_type=False)

                        if self.DICT_KOD_OPER == False:
                            CQT.msgbox(f'Не корректно запущена программа')
                            quit()
                        item = mywindow.zagruzka_shablona_operacii(mywindow, item, self.PUT_K_TMP)

                        arr_tmp = self.spis_op
                        set_oper = {_ for _ in self.DICT_KOD_OPER.keys()}
                        if self.ui2.lineEdit.text() not in set_oper:
                            item.setText(0, 'ОШИБКА')
                            CQT.msgbox('Операция не в списке, проверяйся')
                            return
                        rez_control = self.kontrol_zapolnenia_peremennih()
                        if rez_control == 'calc':
                            arr_tmp = CQT.list_from_wtabl_c(self.ui2.tab_vib, hat_c=True)
                            item.setText(14, '$'.join(arr_tmp[-1]))
                            item.setText(16, str(F.list_of_lists_to_list_of_dicts(arr_tmp)[0]))
                            item.setText(7, '0')
                        else:
                            if rez_control == True:
                                item = self.raschet_tsht(item, self.ui2.tab_vib)
                                item = self.raschet_kompleksov(item, self.ui2.tab_vib)
                                self.pself.obnovit_mater_tabl()
                            else:
                                CQT.msgbox('Контроль переменных не пройден, нормы не рассчитаны')

                        if not self.ui2.combo2.currentText().split(' / ')[0] in operacii.Data_oper_norm.DICT_OPERS_CALC:
                            item.setText(6, str(self.tpz_na_operaciy(item.text(0), arr_tmp)))

                if item.text(20) == '2':
                    oper = self.pself.ui.tree.currentItem().parent().text(0)
                    pereh_txt_path = self.pself.xl_formulas.get_pereh_txt_path(oper)
                    limit_o = int(F.scfg('limit_o'))
                    limit_p = int(F.scfg('limit_p'))
                    arr_tmp = self.spis_op
                    flag_naid = 0
                    for item_arr in arr_tmp:
                        if item_arr[0] == oper:
                            if int(item_arr[1]) > limit_p:
                                flag_naid = 1
                            break
                    if flag_naid == 1:
                        if F.existence_file_c(pereh_txt_path):
                            arr_tmp = F.open_file_c(pereh_txt_path, False, "|")
                            if self.ui2.tab_vib.rowCount() > 0:
                                if self.kontrol_zapolnenia_peremennih():
                                    item = self.raschet_tsht(item, self.ui2.tab_vib)
                                    self.pself.tree_noma_vrem()
                                    item = self.raschet_kompleksov(self.pself.ui.tree.currentItem().parent(), self.ui2.tab_vib, True)
                                    self.pself.obnovit_mater_tabl()
                                else:
                                    CQT.msgbox('Контроль переменных не пройден, нормы не рассчитаны')

                            flag_naid2 = 0
                            for item_arr in arr_tmp:
                                if item_arr[0] == strok:
                                    item_arr[1] = str(int(item_arr[1]) + 1)
                                    flag_naid2 = 1
                                    break
                            if flag_naid2 == 0:
                                arr_tmp.append([strok, '1'])
                            F.write_file_c(pereh_txt_path, arr_tmp, "|")
                        else:
                            arr_tmp = []
                            arr_tmp.append([strok, '1'])
                            F.write_file_c(pereh_txt_path, arr_tmp, "|")
                self.pself.obnovit_param_tablic()
                if '*' not in self.pself.glob_tk_title:
                    self.pself.set_glob_tk_title(self.pself.glob_tk_title + '*')
                self.hide()
        return

    @CQT.onerror
    def keyReleaseEvent(self, e):
        self.cust_keyReleaseEvent(e.key(),e.modifiers()) #QtCore.Qt.NoModifier


    def click_chbox_edit_combos(self):
        self.pself.chbox_edit_combos = self.ui2.chbox_edit_combos.isChecked()


    @CQT.onerror
    def raschet_kompleksov(self, item, tbl, perehod = False):
        if perehod:
            ima_operacii = item.text(0)
            arr_tmp = ['',item.text(7).split('$')]
        else:
            ima_operacii = item.text(0)
            arr_tmp = CQT.list_from_wtabl_c(tbl, hat_c=True)
            if len(arr_tmp) > 2:
                tmp = [arr_tmp[0], []]
                for idx, hat in enumerate(arr_tmp[0]):
                    tmp[1].append(';'.join(elem[idx] for elem in arr_tmp[1:]))
                arr_tmp = tmp
        try:
            mat = operacii.materiali(self, ima_operacii, arr_tmp)
            if mat is None: #25.11.25
                return item
        except:
            mat = ""
            CQT.msgbox('Материалы не расчитаны')
            return item
        if item.text(10) == '' or self.ui2.optbtn_new_mat.isChecked():
            old_spis_mat = []
        else:
            old_spis_mat = [x.split('$') for x in item.text(10).split('{')]
        new_spis_mat = [x.split('$') for x in mat.split('{')]
        for i in range(len(new_spis_mat)):
            flag_naid = False
            for j in range(len(old_spis_mat)):
                if new_spis_mat[i][0] == old_spis_mat[j][0]:
                    flag_naid = True
                    old_spis_mat[j] = new_spis_mat[i]
                    break
            if flag_naid == False:
                old_spis_mat.append(new_spis_mat[i])

        mat = '{'.join(['$'.join(strok) for strok in old_spis_mat if strok != ['']])
        item.setText(10, mat)
        return item

    @CQT.onerror
    def raschet_tsht(self, item, tbl):
        arr_tmp = CQT.list_from_wtabl_c(tbl, hat_c=True)
        if len(arr_tmp) > 2:
            tmp = [arr_tmp[0], []]
            for col in range(len(arr_tmp[0])):
                tmp[-1].append(';'.join(row[col] for row in arr_tmp[1:]))
            arr_tmp = tmp

        item.setText(14, '$'.join(arr_tmp[-1]))

        if len(arr_tmp[0]):
            item.setText(16, str(F.list_of_lists_to_list_of_dicts(arr_tmp)[0]))
        if item.text(20) == '1':
            ima_operacii = item.text(0)
            try:
                vrema = operacii.vremya_tsht(ima_operacii, arr_tmp)
                if type(vrema) == tuple:
                    vrema_pz = vrema[1]
                    vrema = vrema[0]
                    item.setText(6, str(vrema_pz))
            except Exception as e:
                vrema = 0
        if item.text(20) == '2':
            arr_tmp_parent = self.myparent.currentItem().parent().text(14).split("$")
            ima_operacii = self.myparent.currentItem().parent().text(0)
            ima_perehod = item.text(0)
            try:
                vrema = operacii.vremya_tsht_perehodi(ima_operacii,ima_perehod, arr_tmp, arr_tmp_parent)
            except Exception as e:
                vrema = 0
        if vrema == 0:
            CQT.msgbox('Не рассчиано время, материалы не заненсены.')
        item.setText(7, str(vrema))
        return item

    @CQT.onerror
    def kontrol_zapolnenia_peremennih(self):
        tbl = self.ui2.tab_vib
        spis = CQT.list_from_wtabl_c(tbl, hat_c=True)
        if len(spis) != 2:
            return True
        for i in range(len(spis[0])):
            if spis[1][i] == '+':
                continue
            if "f'" == spis[1][i][:2]:
                return 'calc'
            if spis[1][i] == "-":
                CQT.msgbox(f'{spis[0][i]} не заполнен')
                return False
            if self.ui2.combo2.currentText() in operacii.Data_oper_norm.DICT_OPERS_CALC:
                field = tbl.horizontalHeaderItem(i).text()
                tip = operacii.Data_oper_norm.DICT_OPERS_CALC[self.ui2.combo2.currentText()][field]['type']
            else:
                tip = spis[0][i].split(':')[-1].strip()
            if tip == 'int' or tip == 'float':
                if ';' not in spis[1][i]:
                    if F.is_numeric(spis[1][i]) == False:
                        CQT.msgbox(f'{spis[0][i]} не число')
                        return False
        return True

    @CQT.onerror
    def vibor_elem1(self,*args):
        combo1 = self.ui2.combo1
        combo2 = self.ui2.combo2
        text = self.ui2.lineEdit
        if self.item_o == "Оснастка":
            vid_osn = combo1.currentText()

            text = f"""ВЫБРАТЬ
                    Номенклатура.Код КАК Код,
                    Номенклатура.Наименование КАК Наименование,
                    Номенклатура.Артикул КАК Артикул,
                    Номенклатура.ЕдиницаИзмерения КАК ЕдиницаИзмерения,
                    Номенклатура.Описание КАК Описание
                ИЗ
                    Справочник.Номенклатура КАК Номенклатура
                ГДЕ
                    Номенклатура.ВидНоменклатуры.Наименование = "{vid_osn}"
                    И Номенклатура.ЭтоГруппа = ЛОЖЬ
                    И Номенклатура.ПометкаУдаления = ЛОЖЬ
                
                УПОРЯДОЧИТЬ ПО
                    Код УБЫВ"""
            code, data = APIERP.get_wet_request(text=text)

            if code != 200:
                CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
                self.close()
                return
            list_nomen = data['data']

            #osn_path = self.pself.get_oper_osn_path(vid_osn)
            #if F.existence_file_c(osn_path):
            #    arr_tmp = F.open_file_c(osn_path)
            #    combo2.clear()
            #    combo2.setEnabled(True)
            #    combo2.addItems(arr_tmp)
            CQT.fill_wtabl(list_nomen,self.ui2.tab_vib,auto_type=False,selectionBehavior="SelectRows",sortingEnabled=True,selectionMode="SingleSelection")
            CMS.fill_filtr_c(self,self.ui2.tbl_filtr,self.ui2.tab_vib)
            return
        if self.item_o == "Инструмент":
            vid_ins = combo1.currentText()
            ins_path = self.pself.get_oper_ins_path(vid_ins)
            print(ins_path)
            if F.existence_file_c(ins_path):
                arr_tmp = F.open_file_c(ins_path)
                combo2.clear()
                combo2.setEnabled(True)
                combo2.addItems(arr_tmp)
            return
        if self.item_o == "Материал":
            pass
            return

    @CQT.onerror
    def vibor_elem2(self,*args):
        combo1 = self.ui2.combo1
        combo2 = self.ui2.combo2
        tbl = self.ui2.tab_vib
        text = self.ui2.lineEdit
        text.setText(combo2.currentText())
        if self.item_o == 'Инструмент' or self.item_o == 'Оснастка':
            return
        item = self.pself.ui.tree.currentItem()
        self.ui2.lbl_prim.setText('')
        if self.item_o == 'Древо':
            if item.text(20) == '1':
                rez = []
                oper_name = combo2.currentText().split(' / ')[0]
                text.setText(oper_name)
                rez.append(self.spis_parametrov_na_operaciy(oper_name, self.spis_op))
                if rez != [['']]:
                    self.ui2.tab_vib.setEnabled(True)
                    # rez.append(['-' for _ in range(len(rez[0]))])
                    fl_weld = False
                    if item.text(14) != '':
                        spis_per_param = item.text(14).split('$')

                        for sep in  operacii.Data_oper_norm.SET_BLOCK_LINE:
                            for id_param, param in enumerate(spis_per_param):
                                spis_per_param[id_param] = param.replace(sep,';')

                        if spis_per_param:
                            upper_params = rez[0].index('Виды швов') if 'Виды швов' in rez[0] else None
                            type_weds = operacii.Data_oper_norm.DICT_KOD_VALS_SVARKA['Виды швов']
                            weds = max(len(param.split(';')) for param in spis_per_param)
                            if weds > 1:
                                fl_weld = True
                            for idx in range(weds):
                                tmp = []
                                for i_param, row in enumerate(spis_per_param):
                                    text = ''
                                    if len(row.split(';')) > idx:
                                        text = row.split(';')[idx]
                                    if i_param == upper_params and text:
                                        for key, value in type_weds.items():
                                            if value == text.upper():
                                                text = str(key)
                                                break
                                    tmp.append(text)
                                rez.append(tmp)
                                length_row = len(rez[0]) - len(rez[idx + 1])
                                if length_row != 0:
                                    rez[idx + 1] += length_row * '-'

                    if fl_weld:
                        CQT.fill_wtabl(rez,self.ui2.tab_vib, set_editeble_col_nomera='*', auto_type=False)
                        self.ui2.tab_vib.resizeColumnsToContents()


                    if self.pself.global_param_tk_dxf != '':
                        for parametr in self.pself.SPIS_PARAMETR_DXF:
                            for i in range(len(rez[0])):
                                if parametr == rez[0][i].split(':')[0]:
                                    #if CQT.msgboxgYN(f'Загрузить {parametr} из dxf?'):
                                    param_val = ''
                                    if parametr == 'Периметр':
                                        param_val = self.pself.global_param_tk_dxf['perimetr_elems_mm']
                                    if parametr == 'Врезы':
                                        param_val = self.pself.global_param_tk_dxf['elems']
                                    if parametr == 'Площадь':
                                        param_val = self.pself.global_param_tk_dxf['rect_area_mm2']
                                    rez[1][i] = param_val

                    if item.text(4) == '010101' and 'ЧПУ' in item.text(0):
                        segment_count = '?'
                        try:
                            if item.child(0).text(0) != '':
                                segment_count = CMS.segment_count(item.child(0).text(0),segment_count)
                                for i in range(len(rez[0])):
                                    if 'Число сегментов' == rez[0][i].split(':')[0]:
                                        rez[1][i] = segment_count
                                        break
                        except:
                            pass


                    set_corr = set(range(len(rez[0])))
                    if not fl_weld:
                        CQT.fill_wtabl_old_c(self, rez, tbl, separ='', isp_hat_c=True, set_editeble_col_nomera=set_corr)
                    putf = self.pself.get_oper_prim(oper_name)
                    if F.existence_file_c(putf):
                        prim = F.open_file_c(putf, True, propuski=True)
                        prim = '; '.join([F.clear_row_for_separ_c(x.strip()) for x in prim])
                        self.ui2.lbl_prim.setText(prim)
                    if len(rez) > 1:
                        operacii.oform_operation(self,tbl,oper_name)
                    if fl_weld:
                        for i in range(self.ui2.tab_vib.rowCount()):
                            if oper_name == 'Сварка':
                                operacii.validate_welds(self, i)


            if item.text(20) == '2':
                ima_oper = self.myparent.currentItem().parent().text(0)
                pereh_name = combo2.currentText()
                pereh_txt_path = self.pself.xl_formulas.get_pereh_txt_path(ima_oper)
                if F.existence_file_c(pereh_txt_path):
                    spis_pereh = F.open_file_c(pereh_txt_path, False, "|")
                    rez = []
                    # TODO 2 Переходы
                    is_xl = self.pself.xl_formulas.check_per(ima_oper, pereh_name, True)
                    if is_xl:
                        self.pself.xl_formulas.get_actual_srv_data()
                        tmp = self.pself.xl_formulas.get_per_params(ima_oper, combo2.currentText())
                        rez.append(tmp)
                    else:
                        tmp = self.spis_parametrov_na_perehod(combo2.currentText(), spis_pereh)
                        rez.append(tmp)
                    if rez != [['']] and not all(len(elem) == 0 for elem in rez):
                        self.ui2.tab_vib.setEnabled(True)
                        if item.text(14) != '':
                            row_pereh_params = item.text(14).split('$')
                            count_rows = min(len(row.split(';')) for row in row_pereh_params) # 02.06.2025 (По задаче 100055042 )
                            count_cols = len(row_pereh_params)
                            header_length = len(tmp) # 26.08.25
                            template = [['' for _ in range(header_length)] for _ in range(count_rows)]
                            for column in range(count_cols):
                                for row in range(count_rows):
                                    if row < len(template) and column < len(template[row]):
                                        template[row][column] = row_pereh_params[column].split(';')[row]
                            rez = [*rez, *template]
                        set_corr = set(range(len(rez[0])))
                        CQT.fill_wtabl(rez, tbl, set_editeble_col_nomera=set_corr, auto_type=False) #14.07.25
                        tbl.resizeColumnsToContents()
                        # CQT.fill_wtabl_old_c(self, rez, tbl, separ='', isp_hat_c=True, set_editeble_col_nomera=set_corr)
                        if is_xl:
                            #TODO 3 Заполнение combobox переходов
                            struct = self.pself.xl_formulas.convert_old_struct(ima_oper, combo2.currentText())
                            operacii.oform_pereh(self, tbl, combo2.currentText(), struct)
                            #TODO 3 end
                        putf = self.pself.get_oper_prim(operation=ima_oper, pereh=combo2.currentText())
                        if F.existence_file_c(putf):
                            prim = F.open_file_c(putf, True, propuski=True)
                            prim = '; '.join([F.clear_row_for_separ_c(x.strip()) for x in prim])
                            self.ui2.lbl_prim.setText(prim)
                    else:
                        CQT.clear_tbl(self.ui2.tab_vib)
            self.toggle_access_main_widgets(self.ui2.tab_vib.columnCount() != 0)

    def toggle_access_main_widgets(self, state: bool = True):
        ui = self.ui2
        for elem in (ui.btn_add_weld, ui.btn_del_welds, ui.btn_del_one_weld, ui.tab_vib):
            elem.setEnabled(state)

    @CQT.onerror
    def spis_parametrov_na_operaciy(self, oper: str, spis_op: list):
        # TODO 1 Операции
        rez = []
        xl_srv_data = self.pself.xl_formulas.get_actual_srv_data()
        if self.pself.xl_formulas.check_op(oper, True):
            params = self.pself.xl_formulas.convert_old_struct(oper)
            operacii.Data_oper_norm.DICT_OPERS_CALC[oper] = params
            return list(params.keys())
        # TODO 1 end
        if CFG.Config.place.poki == 0 and oper in operacii.Data_oper_norm.DICT_OPERS_CALC:
            for key in operacii.Data_oper_norm.DICT_OPERS_CALC[oper].keys():
                rez.append(key)
            return rez
        for i in range(len(spis_op)):
            if spis_op[i][0] == oper and len(spis_op[i]) > 3:
                if spis_op[i][3] is None:
                    return rez
                spis_per = spis_op[i][3].split(';')
                for j in range(len(spis_per)):
                    rez.append(spis_per[j])
                break
        return rez

    @CQT.onerror
    def spis_parametrov_na_perehod(self, oper: str, spis_op: list):
        rez = []
        for i in range(len(spis_op)):
            if spis_op[i][0] == oper and len(spis_op[i]) > 2:
                spis_per = spis_op[i][2].split(';')
                for j in range(len(spis_per)):
                    rez.append(spis_per[j])
                break
        return rez

    @CQT.onerror
    def tpz_na_operaciy(self, oper: str, spis_op: list):
        tpz = ''
        for i in range(len(spis_op)):
            if spis_op[i][0] == oper and len(spis_op[i]) > 2:
                if F.is_numeric(spis_op[i][2]):
                    return F.valm(spis_op[i][2])
        return tpz




# if not F.test_path():
#    exit()

rootitem1 = QtGui.QStandardItem('QAbstractItemView')

app = QtWidgets.QApplication(sys.argv)

args = sys.argv[1:]

myappid = 'Powerz.BAG.SustControlWork.0.0.0'  # !!!

QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "icon.png")))
print(QtWidgets.QStyleFactory.keys())
S = F.scfg('Stile').split(",")
app.setStyle(S[1])
application = mywindow()
from project_cust_38.widget_spy import install_pyqt_event_hook
install_pyqt_event_hook(app)

#=============================================================
versia = application.versia
if F.is_frozen()== False:
    if CMS.kontrol_ver(versia,'Техкарты') == False:
        quit()
#=============================================================

application.show()


sys.exit(app.exec())
# pyinstaller.exe --onefile --icon=1.ico --noconsole TehKart.py
# pyinstaller.exe --onefile --icon=1.ico TehKart.py


