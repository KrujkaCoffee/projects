
from __future__ import annotations

import copy

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QStyle
import subprocess
from form_res import Ui_WindowRes
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Functions as F
from copy import deepcopy
import project_cust_38.operacii as operacii
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_odata_erp as CODAT
import project_cust_38.Cust_config as USRCNF
from typing import TYPE_CHECKING

from project_cust_38.Cust_mes import TkpSchema

if TYPE_CHECKING:
    from MKart import mywindow

class mywindow_res(QtWidgets.QDialog):  # диалоговое окно
    def __init__(self, parent,name_res_for_ERP=None,possible_upload_ERP=False,nom_mk=None,save_as_predv_res=False,num_kpl=None,primech:str|None=None):
        self.myparent:mywindow = parent
        super(mywindow_res, self).__init__()
        self.ui3 = Ui_WindowRes()
        self.ui3.setupUi(self)
        self.setStyleSheet(parent.styleSheet())
        #self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle("Заголовок")
        self.err = False
        self.db_resxml = USRCNF.Config.project.db_resxml
        self.db_kplan = USRCNF.Config.project.db_kplan
        self.db_dse = USRCNF.Config.project.db_dse
        self.ui3.mouseReleaseEvent=lambda event,my_variable:self.clck_form(event,my_variable)
        self.ui3.btn_send_toERP.clicked.connect(self.send_to_ERP)
        self.ui3.btn_compare_res.clicked.connect(self.show_hide_list_old_res)
        self.ui3.btn_show_options_upload_erp.clicked.connect(self.show_options_upload)
        self.ui3.btn_show_options_upload_erp.setEnabled(possible_upload_ERP)
        self.ui3.tbl_list_res.doubleClicked.connect(self.select_res_compare)
        self.showMaximized()
        self.dragPos = QtCore.QPoint()
        CQT.load_css(self)
        CQT.load_icons(self,24)
        self.generate_and_fill_tbl_res(self.myparent.res, name_res_for_ERP, nom_mk=nom_mk, num_kpl=num_kpl, primech=primech)
        if self.err:
            return
        self.ui3.fr_list_res.setHidden(True)
        self.save_as_predv_res= save_as_predv_res
        self.load_list_old_res()
        self.ui3.fr_res2.setHidden(True)
        self.ui3.fr_options_upload.setHidden(True)
        self.fact_load_res = False
        self.check_box_tkp()

    def check_box_tkp(self):
        list_points = [
            {'Пункт': '1. Обрезь отсутствует в РС', 'Чек': ''},
            {'Пункт': '2. Привод, находящийся в проработке, отсутствует в РС', 'Чек': ''},
            {'Пункт': '3. Проверить, соответствует ли масса чертежу ВО', 'Чек': ''},
            {'Пункт': '4. Проверить наполняемость структуры изделия сравнивая с ВО', 'Чек': ''},

        ]
        def add_check(tbl:QtWidgets.QTableWidget):
            for i in range(tbl.rowCount()):
                CQT.add_check_box(tbl,i,1)
            tbl.setColumnWidth(0,600)
        CQT.msgboxg_get_table_ok_inf(self,'Чек-лист',list_points,selectRows=True,func_oform_tbl=add_check)





    def full_screen(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonDblClick:
            self.full_screen()


    def keyReleaseEvent(self, e):
        if self.ui3.tbl_res_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui3.tbl_res_filtr, self.ui3.tbl_res)
                CMS.fill_summ_tbl(self, self.ui3.tbl_res_summ, self.ui3.tbl_res, {'Количество'}, round_summ_digit=3)
        if self.ui3.tbl_list_res_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui3.tbl_list_res_filtr, self.ui3.tbl_list_res)
        if self.ui3.tbl_res_filtr_2.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui3.tbl_res_filtr_2, self.ui3.tbl_res_2)
                CMS.fill_summ_tbl(self, self.ui3.tbl_res_summ_2, self.ui3.tbl_res_2, {'КолРес_1','КолРес_2','Дельта','Дельта%'}, round_summ_digit=2,average=True)

        if e.key() == 67 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())
        if e.key() == QtCore.Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()


    def generate_and_fill_tbl_res(self, res, name_res_for_ERP="", nom_mk=None, num_kpl=None, primech: str | None=None):
        # if 'tkp_current_schema' in self.myparent.__dict__: #09.04.25
        tkp_current_schema = self.myparent.tkp_current_schema

        proj_name = self.myparent.dict_cur_poz_cr_mk['Проект']
        if proj_name and len(proj_name) == 5 and '.ВО' in proj_name:
            if 'file_name' in self.myparent.tkp_current_schema:
                name_res_for_ERP = self.myparent.tkp_current_schema['file_name']
            else:
                name_res_for_ERP = (f"{F.clear_row_for_file_name_c(self.myparent.tkp_current_schema['nnom_tkp'])}"
                                    f"_{F.clear_row_for_file_name_c(self.myparent.tkp_current_schema['name_tkp'])}")

        res_obj = CMS.Resourse_mk(res,self.myparent.db_resxml,self.myparent.db_kplan,self.myparent.bd_naryad,
                                  self.myparent.db_users,tkp_current_schema,self,name_res_for_ERP,nom_mk=nom_mk,num_kpl=num_kpl,primech=primech)
        list_data = res_obj.generate_table_form(self.myparent.DICT_DSE_save_mk,self.myparent.DICT_PROF_CODE,self.myparent.DICT_NOMEN, silent_mode=True)
        if list_data == None:
            self.close()
            self.err=True
            return
        CQT.fill_wtabl(list_data,self.ui3.tbl_res,auto_type=False,height_row=24)
        CMS.fill_filtr_c(self,self.ui3.tbl_res_filtr,self.ui3.tbl_res,hidden_scroll=True)
        CMS.update_width_filtr(self.ui3.tbl_res,self.ui3.tbl_res_filtr)
        CMS.fill_summ_tbl(self,self.ui3.tbl_res_summ,self.ui3.tbl_res,{'Количество'},round_summ_digit=3)
        self.res_data = list_data
        self.ui3.le_res_first.setText(res_obj.nn)
        self.res_obj = res_obj
    def compare_res(self,list_data_l,res_r):

        def dict_form_list_data_res(res):
            dict_data = dict()
            for item in res:
                key = '$'.join([item['Этап'], item['Подразделение'], item['Номер']])
                val = F.valm(item['Количество'])
                if key not in dict_data:
                    dict_data[key] = {'data':item,'val':0}
                dict_data[key]['val'] += val
            return dict_data

        def compare_lr(dict_data_l,dict_delta_r):
            dict_delta_rez = dict()
            for item_l, vals_l in dict_data_l.items():
                delta = vals_l['val']
                l_val = 0
                if item_l in dict_delta_r:
                    delta = vals_l['val'] - dict_delta_r[item_l]['val']
                    l_val= dict_delta_r[item_l]['val']
                if delta > 0:
                    dict_delta_rez[item_l] = {'item':vals_l['data'],'delta': delta,'l_val':l_val,'r_val':vals_l['val']}
            return dict_delta_rez

        tkp_current_schema = self.myparent.tkp_current_schema #09.04.25
        # if 'tkp_current_schema' in self.myparent.__dict__:
        #     tkp_current_schema = self.myparent.tkp_current_schema

        res_obj_r = CMS.Resourse_mk(res_r, self.myparent.db_resxml,self.myparent.db_kplan,self.myparent.bd_naryad,
                                    self.myparent.db_users,tkp_current_schema,self)
        list_data_r = res_obj_r.generate_table_form(self.myparent.DICT_DSE_save_mk, self.myparent.DICT_PROF_CODE, self.myparent.DICT_NOMEN)

        if list_data_r == None:
            return
        dict_data_l = dict_form_list_data_res(list_data_l)
        dict_data_r = dict_form_list_data_res(list_data_r)

        dict_delta_l = compare_lr(dict_data_l,dict_data_r)
        dict_delta_r = compare_lr(dict_data_r,dict_data_l)

        delta_rez = []
        def add_delta_to_rez(list_rez,dict_delta,name_l,name_r):
            for item, val in dict_delta.items():

                tmp_item:dict
                tmp_item = copy.deepcopy(val['item'])
                tmp_item.pop('Количество', None)
                tmp_item.pop('lvl', None)
                name_kol_l = 'КолРес_' + name_l
                name_kol_r = 'КолРес_' + name_r
                tmp_item[name_kol_l] = round(val['r_val'],3)
                tmp_item[name_kol_r] = round(val['l_val'],3)
                tmp_item['Дельта'] = round(val['delta'],3)
                list_rez.append(tmp_item)
            return list_rez

        delta_rez = add_delta_to_rez(delta_rez,dict_delta_l,'1','2')
        delta_rez = add_delta_to_rez(delta_rez, dict_delta_r, '2','1')

        for item in delta_rez:
            item['Дельта'] = item.pop("Дельта")
            delta_p = 100
            if item['Дельта'] == 0:
                delta_p = 0
            else:
                if item['КолРес_1'] > 0:
                    delta_p = round(item['Дельта']/item['КолРес_1']*100,2)
            item['Дельта%'] = delta_p

        delta_rez = F.sort_by_column_c(delta_rez,'Дельта%',revers=True)
        CQT.fill_wtabl(delta_rez,self.ui3.tbl_res_2,auto_type=False,height_row=24,ogr_maxshir_kol=500)
        CMS.fill_filtr_c(self,self.ui3.tbl_res_filtr_2,self.ui3.tbl_res_2,hidden_scroll=True)
        CMS.update_width_filtr(self.ui3.tbl_res_2,self.ui3.tbl_res_filtr_2)
        CMS.fill_summ_tbl(self, self.ui3.tbl_res_summ_2, self.ui3.tbl_res_2, {'КолРес_1','КолРес_2','Дельта','Дельта%'}, round_summ_digit=2,average=True)




    @CQT.onerror
    def load_list_old_res(self,*args):
        list_mk_res = CSQ.custom_request_c(self.myparent.db_resxml,f"""SELECT Номер_мк FROM res""",hat_c=False,one_column=True)
        list_mk = CSQ.custom_request_c(self.myparent.bd_naryad, f"""SELECT 'МК' as 'Тип', Пномер, Номенклатура as Имя FROM mk WHERE Пномер in ({CSQ.prepare_list_to_tuple(list_mk_res)})""", rez_dict=True)
        list_tkp =  CSQ.custom_request_c(self.myparent.db_resxml,f"""SELECT 'ТКП' as 'Тип', Пномер as Пномер,  Имя as Имя FROM predv_res;""",rez_dict=True)

        for row in list_mk:
            list_tkp.append(row)

        CQT.fill_wtabl(list_tkp,self.ui3.tbl_list_res,auto_type=False,height_row=24)
        CMS.fill_filtr_c(self,self.ui3.tbl_list_res_filtr,self.ui3.tbl_list_res,hidden_scroll=True)
        CMS.update_width_filtr(self.ui3.tbl_list_res,self.ui3.tbl_list_res_filtr)

    @CQT.onerror
    def show_hide_list_old_res(self, *args):
        if self.ui3.fr_list_res.isHidden():
            self.ui3.fr_list_res.setHidden(False)
            self.ui3.fr_options_upload.setHidden(True)
        else:
            self.ui3.fr_list_res.setHidden(True)
    @CQT.onerror
    def select_res_compare(self, *args):
        row = CQT.get_dict_line_form_tbl(self.ui3.tbl_list_res)
        if row == {}:
            return

        res_old = None
        if row['Тип'] == 'МК':
            res_old = int(row['Пномер'])


        if row['Тип'] == 'ТКП':
            s_num = row['Пномер']
            #data = CSQ.custom_request_c(self.myparent.db_resxml, f"""SELECT * FROM predv_res WHERE Пномер = {row['Пномер']};""",
            #                                        rez_dict=True)
            res_old = CMS.load_res(s_num,'','',self=self.myparent, tkp=True)

        self.show_hide_list_old_res()
        self.ui3.le_res_second.setText(row['Имя'])
        self.compare_res(self.res_data,res_old)

        self.ui3.fr_res2.setHidden(False)
        self.ui3.fr_options_upload.setHidden(True)

    @CQT.onerror
    def show_options_upload(self, *args):

        LIST_VIDS_NOMEN  = ("Металлическая арматура", "Фильтры рукавные", "ФР.2403088", "Аппараты обдувки",
                            "Газоходы", "Горелки", "Испытательный цех", "Клапаны", "Линзовые компенсаторы",
                            "Металлоизделия", "Прочая продукция Пауэрза", "Рукава фильтровальные",
                            "Системы газоочистки и компоненты", "Системы сухого золоудаления и ком-ты",
                            "Шумоглушители")

        self.ui3.fr_res2.setHidden(True)
        self.ui3.fr_options_upload.setHidden(False)
        self.ui3.fr_list_res.setHidden(True)
        start_date =F.now()
        if not self.res_obj.is_tkp and F.is_date(self.res_obj.poz.max_date,"%d.%m.%Y"):
            start_date = F.datetostr(F.strtodate(self.res_obj.poz.max_date,"%d.%m.%Y" ))
        date_end = F.date_add_days(start_date,28)





        headers = [['Параметр',"Значение",'Действие','Создать'],
                   ['Наименование ресурсной',self.res_obj.name_res_for_ERP,'',''],
                   ['Код ресурсной', '', '', ''],
                   ['НачалоДействия ресурсной',F.now(),'',''],
                   ['КонецДействия ресурсной', date_end,'',''],
                   ['ОсновноеИзделиеНоменклатура','','',''],
                   ['ОсновноеИзделиеАртикул', '', '', ''],
                   ['ОсновноеИзделиеКод','','','']]

        def coord(row_name=None, col_name=None):
            row = None
            col = None
            if row_name:
                for i in range(len(headers)):
                    if headers[i][0] == row_name:
                        row = i-1
                        break
            if col_name:
                for j in range(len(headers[0])):
                    if headers[0][j] == col_name:
                        col = j
                        break
            return row,col

        CQT.fill_wtabl(headers ,self.ui3.tbl_options_for_erp,{"Значение"},800,height_row=24,auto_type=False,min_width_col=200,styleSheet=CQT.ERP_CSS)

        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеНоменклатура',"Значение") ,False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('Код ресурсной', "Значение"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул',"Значение"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеКод',"Значение"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул',"Создать"), False)
        def edit_art():
            row = self.ui3.tbl_options_for_erp.currentRow()
            col = self.ui3.tbl_options_for_erp.currentColumn()
            if (row, col) == coord('ОсновноеИзделиеАртикул','Создать'):
                art = self.ui3.tbl_options_for_erp.item(*(row, col)).text()
                if art.strip() == '':
                    text_art = ''
                else:
                    text_art = 'Металлическая арматура для компенсатора ' + art
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеНоменклатура','Создать')).setText(text_art)

            if (row, col) == coord('Наименование ресурсной','Значение'):
                self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText('')

        self.ui3.tbl_options_for_erp.cellChanged.connect(edit_art)
        str_НомерВидаНоменДляСозданияРесЕРП = self.myparent.Data_plan.DICT_VID_PO_NAPR[self.res_obj.вид_по_напр]['НомерВидаНоменДляСозданияРесЕРП']
        if str_НомерВидаНоменДляСозданияРесЕРП == None or str_НомерВидаНоменДляСозданияРесЕРП == '':
            list_tmp = copy.deepcopy(LIST_VIDS_NOMEN)
        else:
            list_tmp = copy.deepcopy([self.myparent.Data_plan.DICT_VID_NOMEN_NUM[int(_)]['name'] for _ in str_НомерВидаНоменДляСозданияРесЕРП.split(';')])

        list_vids = ', '.join([ '"' +  _ + '"' for _ in list_tmp])
        affix = ''

        msg_about_nomen = f''

        if not self.res_obj.is_tkp:
            name_izd = self.res_obj.izd
            if name_izd:
                affix = f' И Номенклатура.Наименование = "{name_izd}"'
                msg_about_nomen = f'- Наличие номенклатуры в ЕРП\n      `{name_izd}`\n'

        text = f"""ВЫБРАТЬ 
    ВидыНоменклатуры.Наименование КАК Вид,
    Номенклатура.Наименование КАК Наименование,
    Номенклатура.Код КАК Код,
    Номенклатура.Артикул КАК Артикул
ИЗ
    Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
        ЛЕВОЕ СОЕДИНЕНИЕ Справочник.Номенклатура КАК Номенклатура
        ПО (Номенклатура.ВидНоменклатуры = ВидыНоменклатуры.Ссылка)
ГДЕ
    ВидыНоменклатуры.Наименование В ({list_vids})
    И Номенклатура.ПометкаУдаления = ЛОЖЬ {affix}"""
        code, data  = APIERP.get_wet_request(text=text)
        list_nomen = []
        if code != 200:
            CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
            self.close()
            return

        if not len(data['data']):
            CQT.msgbox(f'Номенклатура не найдена!\n Необходимо проверить:\n'
                       f'- Текущую базу ЕРП в настройках МЕС\n'
                       f'- Номенклатуру, указанную в МЕС в КПЛ\n'
                       f'{msg_about_nomen}'
                       
                       f'- НомерВидаНоменДляСозданияРесЕРП\n      на {self.res_obj.вид_по_напр} вид\n'
                       )
            self.close()
            return
        @CQT.onerror
        def check_exist_res(self, row, col):

            def check_is_block_state_res(new_name) -> (bool, list):
                text = f"""ВЫБРАТЬ 
                    РесурсныеСпецификации.Код КАК Код,
                	РесурсныеСпецификации.Статус КАК Статус
                ИЗ
                    Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                ГДЕ
                    РесурсныеСпецификации.Наименование = "{new_name}"
                    И РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
                    И РесурсныеСпецификации.ЭтоГруппа = ЛОЖЬ"""
                code, data = APIERP.get_wet_request(text=text)
                if code != 200:
                    CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
                    return True, []
                if len(data['data']):
                    list_blocked_res = []
                    for res in data['data']:
                        if res['Статус'] == 'Действует':
                            list_blocked_res.append(res)
                    if list_blocked_res:
                        CQT.msgboxg_get_table_ok_inf(self, 'Ресурсные с таким именем, имеют статус `Действует` и заблокированы от затирания и удаления',
                                                     list_blocked_res, show_filtr=False)
                        return True, []
                return False, data

            def check_is_used_in_ZP(new_name):
                text = f"""ВЫБРАТЬ
                                    
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Код КАК СпецификацияКод,
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Наименование КАК СпецификацияНаименование,
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Статус КАК СпецификацияСтатус,
                                    ЗаказНаПроизводство2_2Продукция.Ссылка.Статус КАК ЗаказНаПроизводствоСтатус,
                                    ЗаказНаПроизводство2_2Продукция.Ссылка КАК ЗаказНаПроизводство
                                    ИЗ
                                    Документ.ЗаказНаПроизводство2_2.Продукция КАК ЗаказНаПроизводство2_2Продукция
                                    ГДЕ
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Наименование = "{new_name}" 
                                    И ЗаказНаПроизводство2_2Продукция.Спецификация.ПометкаУдаления = ЛОЖЬ 
                                    И ЗаказНаПроизводство2_2Продукция.Ссылка.ПометкаУдаления = ЛОЖЬ"""
                code, data = APIERP.get_wet_request(text=text)
                if code != 200:
                    CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
                    return True
                return data['data']

            new_name = self.ui3.tbl_options_for_erp.item(0 ,1).text()
            self.ui3.tbl_options_for_erp.item(1, 1).setText('')


            is_block_state, data_list_found_res = check_is_block_state_res(new_name)
            if is_block_state:
                self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной', 'Создать')).setText("")
                return

            is_used_in_ZP = check_is_used_in_ZP(new_name)
            if is_used_in_ZP:
                CQT.msgboxg_get_table_ok_inf(self, 'Ресурсная с таким именем уже используется в ЗП',
                                             is_used_in_ZP, show_filtr=False)
                return

            if len(data_list_found_res['data']):
                if len(data_list_found_res['data']) > 1:
                    self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной', 'Создать')).setText(
                        'Создать новую')
                else:
                    res_code = data_list_found_res['data'][0]['Код']
                    if CQT.msgboxgYN(f"Ресурсная\n{res_code}\n{new_name}\nуже существует",'Создать новую',"Перезаполнить"):
                        self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText('Создать новую')
                    else:
                        self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText(f"Перезаполнить")
                        self.ui3.tbl_options_for_erp.item(1, 1).setText(res_code)
            else:
                self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText("Свободно")


        @CQT.onerror
        def select_nomen(self, row, col, *args):
            if args:
                rez = args[0]
            else:
                rez = CQT.msgboxg_get_table(self,'Выбор номенклатуры',list_nomen,selectRows=True,ExtendedSelection=False,selection_from_tbl=True)
            if  rez:
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеНоменклатура','Значение')).setText(rez['Наименование'])
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеАртикул','Значение')).setText(rez['Артикул'])
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеКод','Значение')).setText(rez['Код'])

        @CQT.onerror
        def create_nomen(self, row, col):
            new_art = self.ui3.tbl_options_for_erp.item(5,3).text()
            new_nomen = self.ui3.tbl_options_for_erp.item(4,3).text()

            if new_art == '':
                CQT.msgbox(f'Артикул не введен')
                return
            msg_yn = f'''Будет создана новая номенклатура:\n
            Наименование: `{new_nomen}`
            Артикул: `{new_art}`'''
            if not CQT.msgboxgYN(msg_yn):
                return

            dict_nomen = {'Наименование':new_nomen,
                               'Артикул':new_art,
                          'ТипНоменклатуры': 'Товар',
                          'ВариантОформленияПродажи': 'РеализацияТоваровУслуг',
                          'ГруппаДоступа': 'Продукция Пауэрз для Эластика',
                          'ЕдиницаИзмерения': 'Штука',
                          'ЕдиницаДляОтчетов': 'Штука',
                          'СкладскаяГруппа': 'Листы',
                          'СтавкаНДС': '20%',
                          'ГруппаАналитическогоУчета': 'Металлоизделия',
                          'ГруппаФинансовогоУчета': 'Продукция собственного производства (Пауэрз)',

                          }
            code, data  =APIERP.make_nomen(dict_nomen)
            if code != 200:
                CQT.msgbox(f'Запрос создания номенклатуры в 1С ошибка код {code}\n{data["Ошибки"]}')
                return
            new_cod = data["Код"]
            self.ui3.tbl_options_for_erp.item(3, 1).setText(new_nomen)
            self.ui3.tbl_options_for_erp.item(4, 1).setText(new_art)
            self.ui3.tbl_options_for_erp.item(5, 1).setText(new_cod)

            CQT.msgbox('Успешно',time_life=0.5)


        list_nomen = data['data']
        CQT.add_btn(self.ui3.tbl_options_for_erp, *coord('Наименование ресурсной','Действие'),
                    'Чек наличие', conn_func_checked_row_col=check_exist_res,
                    self=self)
        if len(list_nomen) == 1:
            select_nomen(self,1,1,list_nomen[0])
        else:
            CQT.add_btn(self.ui3.tbl_options_for_erp,*coord('ОсновноеИзделиеНоменклатура','Действие'),
                    'Подбор номенклатуры',conn_func_checked_row_col=select_nomen, self=self)
        if self.myparent.Data_plan.DICT_VID_PO_NAPR[self.res_obj.вид_по_напр]['ВозможностьСозданияНоменМеталоармДляСозданияРесЕРП']:
            self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеАртикул', "Создать")).setText('Ввод наименования ...')
            CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул', "Создать"), True)
            CQT.add_btn(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул', 'Действие'),
                        'Создать номенклатуру ->', conn_func_checked_row_col=create_nomen, self=self)

    @CQT.onerror
    def send_to_ERP(self, *args):
        def check():
            tbl = self.ui3.tbl_options_for_erp
            if tbl.item(0 ,3).text() == "":
                CQT.blink_obj_c(self,2,tbl.cellWidget(0,2),f'Не проверено наличие ресурсной')
                return False
            if tbl.item(4 ,1).text() == "":
                CQT.blink_obj_c(self,2,tbl.cellWidget(4,2),f'Не указан ОсновноеИзделиеНоменклатура')
                return False
            if tbl.item(5 ,1).text() == "":
                CQT.blink_obj_c(self,2,tbl.cellWidget(4,2),f'Не указан ОсновноеИзделиеАртикул')
                return False
            if tbl.item(6 ,1).text() == "":
                CQT.blink_obj_c(self,2,tbl.cellWidget(4,2),f'Не указан ОсновноеИзделиеКод')
                return False
            if tbl.item(0 ,1).text() == "":
                CQT.migat(self,tbl,0,1 ,2,f'Не указан Наименование ресурсной')
                return False
            if not F.is_date(tbl.item(2 ,1).text()):
                CQT.migat(self,tbl,2,1 ,2,f'Не указан НачалоДействия ресурсной\nформат: "%Y-%m-%d %H:%M:%S"')
                return False
            if not F.is_date(tbl.item(3 ,1).text()):
                CQT.migat(self,tbl,3,1 ,2,f'Не указан КонецДействия ресурсной\nформат: "%Y-%m-%d %H:%M:%S"')
                return False
            return True

        def generate(code_old_res=None):

            hat = {_['Параметр']: _['Значение'] for _ in
                   CQT.list_from_wtabl_c(self.ui3.tbl_options_for_erp, rez_dict=True)}
            hat['РежимЗамены'] = self.ui3.tbl_options_for_erp.item(0 ,3).text()
            hat['ТекущийПользователь'] = F.user_full_namre()
            hat['НачалоДействия'] = F.datetostr(F.strtodate(hat['НачалоДействия ресурсной']),"%d.%m.%Y")
            hat['КонецДействия'] = F.datetostr(F.strtodate(hat['КонецДействия ресурсной']), "%d.%m.%Y")
            hat['Сохранять'] = True
            hat['ИмяБазы'] = USRCNF.Config.user_config.ERP_base_name['Значение']
            hat['КластерСерверов'] = self.myparent.Data_plan.DICT_BASES_ERP[hat['ИмяБазы']]['КластерСерверов']
            hat['Описание'] = ''
            if self.res_obj.primech:
                hat['Описание'] = self.res_obj.primech
            if code_old_res:
                hat['Код'] = code_old_res

            data, err = self.res_obj.generate_list_res_for_erp(DICT_PROF_CODE=self.myparent.DICT_PROF_CODE,
                                                          DICT_NOMEN= self.myparent.DICT_NOMEN,
                                                          DICT_OP=self.myparent.DICT_OP,
                                                          DICT_RC = self.myparent.DICT_RC)

            if err:
                err.insert(0,['Ошибки'])
                if not CQT.msgboxg_get_table(self,'Ошибки компоновки',err,
                                             'Продолжить выгрузку','Прервать',
                                             show_filtr=False,use_first_row_as_header=True,print_hat=True,yesNoMode=True):
                    return

            if data == None:
                return
            a = [[_['Этап'], _['Данные']['Трудозатраты']] for _ in data]
            return {'hat': hat, 'data': data}

        @CQT.onerror
        def send(data):
            code, answ = APIERP.post_res_json(data,self.myparent.ERP_base_name)
            if code == 200:
                return answ
            else:
                CQT.msgbox(f'Ошибка создания ресурсной. Код {code}\n{answ["Ошибки"]}')
            return False

        @CQT.onerror
        def delete_res(name):
            data = {"data": {'Наименование':name}}
            code, answ = APIERP.delete_res_json(data, self.myparent.ERP_base_name)
            if code == 200:
                CMS.send_info_mk_b24_by_action(f'{F.user_full_namre()}\nУдалены, не использующиеся в ЗП, ресурсные:\n{answ["Код"]}', 'готовность РС')
                CQT.msgbox(f'Удалены ресурсные. \n{answ["Код"]}')
                return True
            else:
                CQT.msgbox(f'Ошибка удаления ресурсной. Код {code}\n{answ["Ошибки"]}')
            return False

        @CQT.onerror
        def clear_res(code):
            data = {"data": {'Код': code}}
            code_resp, answ = APIERP.clear_res_json(data, self.myparent.ERP_base_name)
            if code_resp == 200:
                CMS.send_info_mk_b24_by_action(f'{F.user_full_namre()}\nОчищена и перезаполнена, не использующаяся в ЗП, ресурсная:\n{answ["Код"]}',
                                               'готовность РС')
                CQT.msgbox(f'Очищена ресурсная. \n{code}')
                return True
            else:
                CQT.msgbox(f'Ошибка очистки ресурсной. Код ошибки {code_resp}\n{answ["Ошибки"]}')
            return False


        @CQT.onerror
        def open_link(lnk,*args):
            c1_lint_wet = args[3]
            c1_link = c1_lint_wet.replace('e1cib','')
            prefix = fr'"%programfiles%\1cv8\common\1cestart.exe" '
            line = prefix + fr'/url "e1c://server/srv-1c:3541/ERP_MES1#e1cib{c1_link}"'
            try:
                subprocess.call(line, shell=True)
            except:
                F.copy_bufer(c1_lint_wet)
                CQT.msgbox(f'Скопировано в буфер\n{c1_lint_wet}')

        wo_erp = False
        if 'shift' in CQT.get_key_modifiers(self):
            wo_erp=True

        if not check():
            return

        mode = self.ui3.tbl_options_for_erp.item(0 ,3).text()
        code_old_res = None
        if mode != "":
            if mode == 'Перезаполнить':
                code_old_res = self.ui3.tbl_options_for_erp.item(1 ,1).text()


        data_to_ERP = generate(code_old_res)
        if data_to_ERP == None:
            return
        code = 'None'
        data_answ = {'Ссылка':'None'}
        if not wo_erp:
            if mode != "":
                if mode == 'Создать новую':
                    if not delete_res(self.ui3.tbl_options_for_erp.item(0 ,1).text()):
                        return
                elif mode == 'Перезаполнить':
                    code_old_res = self.ui3.tbl_options_for_erp.item(1 ,1).text()
                    if not clear_res(code_old_res):
                        return

            data_answ = send(data_to_ERP)
            if not data_answ:
                return
            code = data_answ['Код']

        name_res = self.ui3.tbl_options_for_erp.item(0, 1).text()
        if code:
            link = data_answ['Ссылка']
            #CQT.msgbox(f'Успешно создана Код "{code}"',time_life=3)
            self.ui3.tbl_options_for_erp.item(0, 3).setText('')
            self.ui3.tbl_options_for_erp.item(1, 1).setText(str(code))
            connection_kpl_state = f'Ресурсная НЕ записана в КПЛ'
            if self.res_obj.is_tkp and self.save_as_predv_res: #08.04.25
                self.write_data_res_analogue(self.res_obj.res,name_res,self.res_obj.num_kpl,self.res_obj.s_num_tkp)
                if self.res_obj.num_kpl and self.res_obj.s_num_tkp and self.res_obj.num_kpl != 3345:
                    self.write_name_analogue_into_kplan(name_res, self.res_obj.num_kpl)
                    connection_kpl_state = f'Записана в КПЛ №{self.res_obj.num_kpl}'
            # if self.save_as_predv_res and self.res_obj.is_tkp and self.res_obj.num_kpl and self.res_obj.s_num_tkp and self.res_obj.num_kpl != 3345:
            CQT.msgboxg_get_table_ok_inf(self, 'Результат', [{'Поле': 'Ссылка', 'Значение': '|'.join([link,'Открыть в 1С'])},
                                                             {'Поле': 'Код', 'Значение': code},
                                                             {'Поле': 'ИмяРесурсной', 'Значение': name_res},
                                                             {'Поле': 'Связь с КПЛ', 'Значение': connection_kpl_state},
                                                             ],load_links=True,styleSheet=CQT.ERP_CSS)
            self.close()

    @CQT.onerror #08.04.25
    def write_data_res_analogue(self, rez,name_res,num_kpl,s_num_tkp,*args):
        res_pickle = F.to_binary_pickle(rez)
        predv_sp = CSQ.custom_request_c(self.db_resxml, f"""SELECT Имя FROM predv_res WHERE Имя = ?;""",
                                        list_of_lists_c=(name_res,))
        if predv_sp == False or predv_sp == None:
            CQT.msgbox(f'Ошибка SELECT Имя FROM predv_res')
            return
        if len(predv_sp) == 1:
            CSQ.custom_request_c(self.db_resxml, f"""INSERT INTO predv_res(Имя,data) VALUES (?,?);""",
                                 list_of_lists_c=[[name_res, res_pickle]])
        else:
            CSQ.custom_request_c(self.db_resxml, f"""UPDATE predv_res SET data = ? WHERE Имя = ?;""",
                                 list_of_lists_c=[[res_pickle, name_res]])
        CSQ.custom_request_c(self.db_dse, f"""UPDATE tkp SET (name_res,date_res) = (?,?) WHERE s_nom = ?""",
                             list_of_lists_c=[[name_res, F.now(), s_num_tkp]])

    @CQT.onerror
    def write_name_analogue_into_kplan(self, name_res,num_kpl, *args):
        res = CSQ.custom_request_c(self.db_kplan,
                             f"""UPDATE пл_топ SET Предв_спецификация_ЕРП = "{name_res}" WHERE НомПл = {num_kpl};""")#self.dict_cur_poz_cr_mk['Пномер']
