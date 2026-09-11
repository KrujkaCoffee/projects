from __future__ import annotations

import json

if __name__ == "__main__":
    import sys
    import os
    os.environ['MODIFIED_CFG'] = '{"BD_users": "SRV:BD_users.db"}'


import copy
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.xml_v_drevo as XML

from project_cust_38.sub_mes.cutting_segment_manager.dataClasses import data_app as DTCLS
from project_cust_38.sub_mes.cutting_segment_manager.dataClasses import ReferenceStore as STORE_C
import project_cust_38.sub_mes.cutting_segment_manager.cutting_mngr_ui as cutting_mngr_ui
import project_cust_38.sub_mes.cutting_segment_manager.sub_classes as CLSS

if DTCLS.CONFIG.user_config.is_developer:
    if CQT.convert_UI_into_PY_c(str(F.Cust_path(cutting_mngr_ui)) + F.sep()):
        import importlib
        importlib.reload(cutting_mngr_ui)

import project_cust_38.sub_mes.cutting_segment_manager.connects as _con


from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    pass

STORE = STORE_C()
STORE.load_data_reference()

class CentralWindow(CQT.QtWidgets.QMainWindow):
    def __init__(self,app_self=None):
        """
        BD_users -> app_config -> new_sub_app				new_sub_app.py	0
        :param app_self:
        """

        super(CentralWindow, self).__init__()
        self.VER:str= '0.1'
        self.ui = cutting_mngr_ui.Ui_MainWindow()
        self.ui.setupUi(self)

        DTCLS.app_self = app_self
        DTCLS.sub_self = self

        if DTCLS.app_self:
            self.setStyleSheet(DTCLS.app_self.styleSheet())
        else:
            self._load_free_css()
            pass

        self.setAttribute(CQT.Qt.WA_DeleteOnClose)
        CQT.connect_to_resize(self, CMS.tmp_dir())
        CMS.connect_manuals(self)

        CQT.load_icons(self, 26, dir=str(F.Cust_path(cutting_mngr_ui)) + F.sep() + 'icons' + F.sep())
        self.setWindowModality(CQT.Qt.ApplicationModal)
        self.apply_subj()

        _con.load_connects(self)
    def _____________service_______________(self):pass

    def keyReleaseEvent(self, e):
        key = e.key()
        mod = e.modifiers()
        _con.key_release_event(self, key, mod)

    def eventFilter(self, obj, event):
        # noinspection PyUnresolvedReferences
        if isinstance(obj, CQT.QtWidgets.QDockWidget) and event.type() == CQT.QtCore.QEvent.MouseButtonDblClick:
            # noinspection PyUnresolvedReferences
            if event.button() == CQT.QtCore.Qt.LeftButton:
                obj.setFloating(True)
                screen = CQT.QtWidgets.QApplication.primaryScreen()
                rect = screen.availableGeometry()
                if obj.geometry() == rect:
                    # Уже развернут — вернуть нормальный размер
                    # self.ui.dockNavigator.showNormal()
                    obj.showMaximized()
                else:
                    # Растянуть ровно по рабочей области (без панели задач)
                    obj.setGeometry(rect)
                    obj.show()
                return True

        if isinstance(obj, CQT.QtWidgets.QDockWidget) and event.type() == CQT.QtCore.QEvent.Resize:
            if CQT.QtWidgets.QApplication.mouseButtons() == CQT.QtCore.Qt.LeftButton:
                key = f'QDockWidget:{obj.objectName()}'
                target = getattr(self, '_resize_targets', {}).get(key)
                if target is not None:
                    CQT._on_resize_event(self, target)
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        #before_close(self)
        event.accept()
    @classmethod
    def start_sub_app(cls,app_self)->'CentralWindow':
        window_manual = CentralWindow(app_self)
        window_manual.showMaximized()
        return window_manual

    def _____________sub__________________(self):pass

    def init_data(self):
        CQT.load_resize_splitters(self, CQT.qt_tmp_dir())
        DTCLS.init_data()
        DTCLS.connections_dse = CLSS.ConnectionsDSE()

    def _load_free_css(self):
        theme_path = F.sep().join([F.path_to_execut_file_c(), 'css'])
        CQT.apply_css_theme(self, theme_path + F.sep()  + 'metallic.qss')

    def apply_subj(self,subject_mode:str=None):
        if subject_mode is None:
            subject_mode = ''
        self.NAME_MODULE_BASE = f'Менеджер учета сегментов раскроя v{self.VER} - {subject_mode}'
        DTCLS.CONFIG.user_config.set_sub_window_title(self)
        # CONNECTS
        _con.prepare_ui(self)
        self.init_data()
        self.tab_changed()


    def _____________________________(self):pass

    def set_val_tbl_reg_paths(self,name:str,value:str=''):
        t = CQT.TableContext(self.ui.tbl_reg_paths)
        row = t.find_row({'_name':name},True)
        if row is None:
            raise Exception('Не найдена строка')
        row.set_value('data',value)

    def clear_reg_paths(self):
        DTCLS.connection_dse.clear_dir_selected()
        CQT.soft_clear_tbl(self.ui.tbl_reg_parts)
        self.set_val_tbl_reg_paths('select_dir_parts')

    def clear_select_dse(self):
        DTCLS.connection_dse.clear_dse()
        self.set_val_tbl_reg_paths('select_dse')
    def fill_reg_tab(self):

        def fnc_select_xml(self:CentralWindow,i,j,*args):
            name_tmp_file = 'cutting_mngr_xml'

            pathf = CQT.f_dialog_name(self,'Выбор XML файла',CMS.load_tmp_path(name_tmp_file),'*.xml',True)
            if pathf is None or pathf == '.':
                return
            CMS.save_tmp_path(name_tmp_file,pathf,True)
            xml = XML.spisok_iz_xml(pathf)

            spis_xml = CMS.podgotovka_xml(self, xml, show_negruz=True)
            tab_str = 4*' '

            self.ALIASES_xml  = {
                        "_position": "Position",
                        "_include_in_doc": "IncludeInDoc",
                        "_include_in_assembly": "IncludeInAssembly",
                        "_type_": "Тип",

                        "_section": "Раздел",
                        "name": "Наименование",
                        "full_designation": "Обозначение полное",
                        "_designation": "Обозначение",
                        "quantity": "Количество",
                        "unit_of_measurement": "Единица измерения",
                        "mass": "Масса",
                        "quantity_per_product": "Количество на изделие",
                        "erp_code": "Код ERP",
                        "_purchased_item": "Покупное изделие",
                        "link_to_docs_object": "Ссылка на объект DOCs",
                        "note": "Примечание",
                        "item": "Изделие",
                        "_document_code": "Код документа",
                        "_id_": "ID",
                        "mass_m1_m2_m3": "Масса/М1,М2,М3"
                    }

            DTCLS.template_xml = [
                {'_position':                        _['data']['Position'],
                 '_include_in_doc':                  _['data']['IncludeInDoc'],
                 '_include_in_assembly':              _['data']['IncludeInAssembly'],
                 '_type_':                            _['data']['Тип'],


                 'name':                               _['level_c']*tab_str + _['data']['Наименование'],
                 'full_designation':                   _['level_c']*tab_str + _['data']['Обозначение полное'],
                 '_name':                               _['data']['Наименование'],
                 '_full_designation':                   _['data']['Обозначение полное'],
                 'mass_m1_m2_m3': _['data']['Масса/М1,М2,М3'],
                 'quantity':                          _['data']['Количество'],
                 'unit_of_measurement':                _['data']['Единица измерения'],
                 'mass':                              _['data']['Масса'],
                 'quantity_per_product':              _['data']['Количество на изделие'],
                 'note':                            _['data']['Примечание'],
                 'erp_code':                         _['data']['Код ERP'],
                 '_purchased_item':                   _['data']['Покупное изделие'],
                 'link_to_docs_object':               _['data']['Ссылка на объект DOCs'],
                 'item':                             _['data']['Изделие'],
                 '_document_code':                   _['data']['Код документа'],
                 '_id_':                             _['data']['ID'],
                  }

            for _ in spis_xml if 'лист' in _['data']['Масса/М1,М2,М3'].lower() and _['data']['Покупное изделие'] == '0']
            self.set_val_tbl_reg_paths('select_xml',pathf)
            DTCLS.connection_dse = CLSS.ConnectionDSE()


            self.clear_select_dse()
            self.clear_reg_paths()
            pass

        def fnc_select_dir_parts(self: CentralWindow, i, j, *args):
            if DTCLS.connection_dse is None:
                CQT.msgbox('Не выбран XML', app_self=self)
                return



            name_tmp_file = 'cutting_dir_parts'

            pathd = CQT.getDirectory(self, CMS.load_tmp_path(name_tmp_file))
            if pathd is None or pathd == '.':
                return
            CMS.save_tmp_path(name_tmp_file, pathd, True)

            self.clear_reg_paths()

            suc, err = DTCLS.connection_dse.add_raw_dir_name(pathd)
            if not suc:
                CQT.msgbox(err, app_self=self)
                return

            founded = [_ for _ in DTCLS.template_xml
                       if _['_name'] == DTCLS.connection_dse.raw_dir_name and _[
                           '_full_designation'] == DTCLS.connection_dse.raw_dir_nn]

            if not founded:
                CQT.msgbox(f'Не найдена ДСЕ "{DTCLS.connection_dse.raw_dir_str}" в XML', app_self=self)
                return

            list_files = [_ for _ in F.list_of_files_c(pathd)[0][2] if _.endswith('.dxf')]



            for name in list_files:
                pathf = F.sep().join([F.list_of_files_c(pathd)[0][0], name])
                file_o = CLSS.FileDXF(pathf)
                DTCLS.connection_dse.add_file(file_o)

            template = DTCLS.connection_dse.get_template_files_edit()

            CQT.fill_wtabl(template, self.ui.tbl_reg_parts, styleSheet=CQT.MES_EDIT_CSS)
            CQT.fill_filtr_c(self, self.ui.tbl_reg_parts_filter, self.ui.tbl_reg_parts, hidden_scroll=True,
                             show_header=False)

            t_pr = CQT.TableContext(self.ui.tbl_reg_parts)
            t_pr.set_editable('Количество', False)
            for row in t_pr.rows():
                count = row.value('Количество')
                if count and F.is_numeric(count):
                    continue
                row.set_editable('Количество', True)
            t_pr.hide_if_not_dev(CFG, True)
            def edit_cell(t:CQT.TableContext,name_field:str,new_row:CQT.TableRow,new_val,old_val,add_data,*args)->bool:
                if not F.is_numeric_positive_integer(new_val,zero_admit=False):
                    return False
                id_dse = int(new_row.value('_id'))
                file_edit_o = DTCLS.connection_dse.files_dxf[id_dse]
                file_edit_o.set_count(int(new_val))

                return True



            t_pr.add_cell_edit_events(edit_cell)
            self.set_val_tbl_reg_paths('select_dir_parts', DTCLS.connection_dse.raw_dir)
            self.clear_select_dse()


        def fnc_select_dse(self:CentralWindow,i,j,*args):

            def oform_tbl(tbl:CQT.QTableWidget):
                t = CQT.TableContext(tbl)
                t.hide_if_not_dev(CFG)


            if DTCLS.template_xml is None:
                CQT.msgbox('Не выбран XML',app_self=self)
                return


            if not  DTCLS.connection_dse.files_dxf:
                CQT.msgbox('Не выбрана папка с файлами',app_self=self)
                return

            self.clear_select_dse()

            template_xml = [_ for _ in DTCLS.template_xml if _['_name'] == DTCLS.connection_dse.raw_dir_name
                            and _['_full_designation']== DTCLS.connection_dse.raw_dir_nn]

            rez = CQT.msgboxg_get_table(self,'Выбрать ДСЕ для связывания',template_xml,selectRows=True,
                                        ExtendedSelection=False,selection_from_tbl=True,styleSheet=CQT.MES_CSS,
                                        aliases_header=self.ALIASES_xml,func_oform_tbl=oform_tbl)
            if rez is None or not rez:
                return
            #rs = CMS.ResSpec(10639)
            #rs._wet_data
            DTCLS.connection_dse.add_dse(rez['_name'],rez['_full_designation'],rez['item'],
                                         rez['link_to_docs_object'],
                                         rez['erp_code'])
            self.set_val_tbl_reg_paths('select_dse',str(DTCLS.connection_dse))
            pass

        DTCLS.connection_dse = None
        DTCLS.template_xml = None

        tbl = self.ui.tbl_reg_paths
        template = [

            {'_name':'select_xml','':CEMOJ.ДокументыДанные.database.symbol,'text':'Выбор XML','btn':'...','data':''},
            {'_name': 'select_dir_parts', '': CEMOJ.ДокументыДанные.folder_closed.symbol, 'text': 'Выбор Папки c dxf',
             'btn': '...', 'data': ''},
            {'_name':'select_dse','':CEMOJ.ОперацииПроизводства.dse.symbol,'text':'Выбор ДСЕ','btn':'...','data':''},

        ]

        CQT.fill_wtabl(template,tbl,styleSheet=CQT.MES_CSS,hide_head_rows=True)
        t = CQT.TableContext(tbl)

        icon_path = F.sep().join([F.path_to_caller_file_c(False),'icons','select_btn'])
        for row in t.rows():
            name_row = row.value('_name')
            if name_row == 'select_xml':
                CQT.add_btn(t.tbl,row.i,t.nf['btn'],'Выбор данных',conn_func_checked_row_col=fnc_select_xml,self=self,img_path=icon_path)
            if name_row == 'select_dse':
                CQT.add_btn(t.tbl,row.i,t.nf['btn'],'Выбор данных',conn_func_checked_row_col=fnc_select_dse,self=self,img_path=icon_path)
            if name_row == 'select_dir_parts':
                CQT.add_btn(t.tbl,row.i,t.nf['btn'],'Выбор данных',conn_func_checked_row_col=fnc_select_dir_parts,self=self,img_path=icon_path)
        t.h_header.hide()
        t.set_width('btn',row.heigt)

    def select_dse(self):
        t = CQT.TableContext(self.ui.tbl_dse)
        row = t.current_row()
        if row.no_selection:
            return
        id = int(row.value('id'))
        conn = DTCLS.connections_dse.find(id)
        templ = conn.get_template_files_edit()

        CQT.fill_wtabl(templ,self.ui.tbl_parts,styleSheet=CQT.MES_CSS,selectionBehavior=CQT.SelectionBehaviors.SelectRows)
        t_p = CQT.TableContext(self.ui.tbl_parts)
        t_p.hide_if_not_dev(CFG,True)
        CQT.fill_filtr_c(self,self.ui.tbl_parts_filter,self.ui.tbl_parts,show_header=False,hidden_scroll=True)

    def tab_changed(self,*args):
        current_tab_name = self.ui.tabWidget.currentWidget().objectName()
        if current_tab_name == 'tab_reg':
            self.fill_reg_tab()

        if current_tab_name == 'tab_viewer':
            self.fill_viewer_tab()

    def check_reg(self)->tuple[bool,list[dict]]:
        if DTCLS.connection_dse is None:
            return False,[{'err':'Не выбрана XML'}]
        return DTCLS.connection_dse.check_to_serialize()


    def reg_ok(self):
        succ,list_err = self.check_reg()
        if not succ:
            CQT.msgboxg_get_table_ok_inf(self,'Ошибки загрузки',list_err,styleSheet=CQT.MES_CSS)
            return
        suc, err = DTCLS.connection_dse.save_db()
        if suc:
            CQT.msgbox(f'Успешно сохранено')
            return
        CQT.msgboxg_get_table_ok_inf(self, 'Ошибки сохранения', err, styleSheet=CQT.MES_CSS)
    def __________vierwer_tab_______________(self):pass

    def fill_viewer_tab(self):
        DTCLS.connections_dse.load_from_db()
        template_dse_list = DTCLS.connections_dse.template()
        CQT.fill_wtabl(template_dse_list,self.ui.tbl_dse,aliases_header=CLSS.ConnectionDSE.ALIASES,styleSheet=CQT.MES_CSS,
                       selectionBehavior='SelectRows',selectionMode='SingleSelection')
        t = CQT.TableContext(self.ui.tbl_dse)
        t.hide_if_not_dev(CFG,forced_text=True)
        CQT.fill_filtr_c(self,self.ui.tbl_dse_filter,self.ui.tbl_dse, hidden_scroll=True,show_header=False)


if __name__ == "__main__":

    from project_cust_38.Cust_application import install_crash_guard, SafeApplication
    app = SafeApplication(sys.argv)
    install_crash_guard(app, app_name='',user_name='', log_qt_warnings=False,log_qt_debug_info=False, enable_native_fault_handler=False)
    #CQT.ThemeManager.apply(app)
    sub_window = CentralWindow(None)
    sub_window.showMaximized()
    sys.exit(app.exec())
