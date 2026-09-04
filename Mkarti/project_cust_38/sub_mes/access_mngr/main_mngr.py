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

from project_cust_38.sub_mes.access_mngr.dataClasses import data_app as DTCLS
from project_cust_38.sub_mes.access_mngr.dataClasses import ReferenceStore as RefStore
import project_cust_38.sub_mes.access_mngr.access_ui as access_ui
import project_cust_38.sub_mes.access_mngr.sub_classes as CLSS

if DTCLS.CONFIG.user_config.is_developer:
    if CQT.convert_UI_into_PY_c(str(F.Cust_path(access_ui)) + F.sep()):
        import importlib
        importlib.reload(access_ui)

import project_cust_38.sub_mes.access_mngr.connects as _con


from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    pass

STORE = RefStore()
#STORE.load_data_reference()

class CentralWindow(CQT.QtWidgets.QMainWindow):
    def __init__(self,app_self):
        """
        BD_users -> app_config -> new_sub_app				new_sub_app.py	0
        :param app_self:
        """

        super(CentralWindow, self).__init__()
        self.VER:str= '0.1'
        self.ui = access_ui.Ui_MainWindow()
        self.ui.setupUi(self)

        DTCLS.app_self = app_self
        DTCLS.sub_self = self

        if DTCLS.app_self:
             self.setStyleSheet(DTCLS.app_self.styleSheet())
        else:
             self._load_free_css()

        self.setAttribute(CQT.Qt.WA_DeleteOnClose)
        CQT.connect_to_resize(self, CMS.tmp_dir())

        CQT.load_icons(self, 26, dir=str(F.Cust_path(access_ui)) + F.sep() + 'icons' + F.sep())
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

    def _load_free_css(self):
        theme_path = F.sep().join([F.path_to_execut_file_c(), 'css'])
        CQT.apply_css_theme(self, theme_path + F.sep()  + 'metallic.qss')

    def _____________sub__________________(self):
        pass

    def init_data(self):
        CQT.load_resize_splitters(self, CQT.qt_tmp_dir())
        DTCLS.init_data()

        DTCLS.mngr_acess = CMS.ManagerAccess()
        #DTCLS.mngr_acess.import_from_old_db()
        #DTCLS.mngr_acess._synch_rules()
        #DTCLS.mngr_acess.save()
        DTCLS.mngr_acess.load()



    def apply_subj(self,subject_mode:str=None):
        if subject_mode is None:
            subject_mode = ''
        self.NAME_MODULE_BASE = f'Менеджер прав доступа v{self.VER} - {subject_mode}'
        DTCLS.CONFIG.user_config.set_sub_window_title(self)
        # CONNECTS
        _con.prepare_ui(self)
        self.init_data()
        self.reset_filters()


    def __________main_______________(self):pass

    def new_role(self):
        succ, name = CQT.get_dialog_choose_text(self,'Введите название нового правила')
        if not succ:
            return
        if ' ' in name:
            name = name.replace(' ','_').lower()
        if not DTCLS.mngr_acess.make_new_rule(name):
            CQT.msgbox(f'Ошибка создания правила "{name}"')
            return
        self.reset_filters()

    def del_rule(self):
        tr = CQT.TableContext(self.ui.tbl_rules)
        td = CQT.TableContext(self.ui.tbl_dolgn)
        list_dolgn = [(int(_.value('poki')), _.value('_ref_dolgn')) for _ in td.rows() if not _.is_hidden()]
        list_dolgn_names = [(int(_.value('poki')), _.value('Должность')) for _ in td.rows() if not _.is_hidden()]
        row_or = tr.current_row()
        if row_or.no_selection:
            CQT.msgbox('Должность не выбрана')
            return

        name_r = row_or.value('Правило')

        if not CQT.msgboxgYN(f'Правило "{name_r}" будет удалено из должностей:\n{"\n".join([f'{_[0]}-{_[1]}' for _ in list_dolgn_names])}'):
            return

        for key in list_dolgn:
            poki_d, ref_d = key
            DTCLS.mngr_acess.delete_access(name_r, poki_d, ref_d)
        CQT.msgbox(f'Успешно', time_life=1)
    def del_dolgn(self):
        tr = CQT.TableContext(self.ui.tbl_rules)
        td = CQT.TableContext(self.ui.tbl_dolgn)
        list_rules = [_.value('Правило') for _ in tr.rows() if not _.is_hidden()]
        row_od = td.current_row()
        if row_od.no_selection:
            CQT.msgbox('Должность не выбрана')
            return

        ref_d = row_od.value('_ref_dolgn')
        name_d = row_od.value('Должность')
        poki_d = int(row_od.value('poki'))
        if not CQT.msgboxgYN(f'Должность {poki_d} "{name_d}" будет удалена из правил:\n{"\n".join(list_rules)}'):
            return

        for rule in list_rules:
            DTCLS.mngr_acess.delete_access(rule,poki_d,ref_d)
        CQT.msgbox(f'Успешно', time_life=1)

    def add_new_dolgn(self):
        t = CQT.TableContext(self.ui.tbl_rules)
        list_rules = [_.value('Правило') for _ in t.rows() if not _.is_hidden()]

        rez = CQT.msgboxg_get_table(self,'Выбор должности',DTCLS.mngr_acess._dict_dolgn_names,
                                    styleSheet=CQT.MES_CSS,
                                    selection_from_tbl=True,selectRows=True,ExtendedSelection=False)
        if not rez:
            return
        ref_d = rez['Список']
        name_d = rez['Наименование']
        poki_d = int(rez['Организация_poki'])
        if not CQT.msgboxgYN(f'Должность {poki_d} "{name_d}" будет добавлена в правила:\n{"\n".join(list_rules)}'):
            return
        list_rezult=[]
        for rule in list_rules:
            tmp_row = {'Правило':rule,'Должность':name_d,'poki':poki_d,'Добавлено':CEMOJ.СтатусыПроизводства.normal.symbol,'Примечание':''}
            rez,err_str = DTCLS.mngr_acess.new_access(rule,poki_d,ref_d)
            if not rez:
                tmp_row['Добавлено'] = CEMOJ.СтатусыПроизводства.stopped.symbol
                tmp_row['Примечание'] = err_str
            list_rezult.append(tmp_row)
        CQT.msgboxg_get_table_ok_inf(self,'Результат',list_rezult,styleSheet=CQT.MES_CSS)

    def add_new_rule(self):
        t = CQT.TableContext(self.ui.tbl_dolgn)
        list_dolgn = [(int(_.value('poki')),_.value('_ref_dolgn')) for _ in t.rows() if not _.is_hidden()]
        list_dolgn_names = [(int(_.value('poki')),_.value('Должность')) for _ in t.rows() if not _.is_hidden()]

        rez = CQT.msgboxg_get_table(self, 'Выбор правила', DTCLS.mngr_acess.template_by_rules() ,
                                    styleSheet=CQT.MES_CSS,
                                    selection_from_tbl=True, selectRows=True, ExtendedSelection=False)
        if not rez:
            return

        rule = rez['Правило']

        if not CQT.msgboxgYN(f'Правило "{rule}" будет добавлено для должностей:\n{"\n".join([f'{_[0]}-{_[1]}' for _ in list_dolgn_names])}'):
            return

        list_rezult = []
        for i, dolgn in enumerate(list_dolgn):
            name_d = list_dolgn_names[i][1]
            poki_d, ref_d = dolgn
            tmp_row = {'Правило': rule, 'Должность': name_d, 'poki': poki_d,
                       'Добавлено': CEMOJ.СтатусыПроизводства.normal.symbol, 'Примечание': ''}
            rez, err_str = DTCLS.mngr_acess.new_access(rule, poki_d, ref_d)
            if not rez:
                tmp_row['Добавлено'] = CEMOJ.СтатусыПроизводства.stopped.symbol
                tmp_row['Примечание'] = err_str
            list_rezult.append(tmp_row)
        CQT.msgboxg_get_table_ok_inf(self, 'Результат', list_rezult, styleSheet=CQT.MES_CSS)

    def set_filter(self,filter:CLSS.Filters,val = None):
        if filter == CLSS.Filters.r:
            DTCLS.filtred_r = val
            if DTCLS.filtred_r:
                text = DTCLS.filtred_r.replace('_', ' ')
                self.ui.lbl_filtred_u.setText(f'Фильтр по: "{text}"')
            else:
                self.ui.lbl_filtred_u.clear()
            self.reload_u()

        if filter == CLSS.Filters.u:
            DTCLS.filtred_u = val
            if DTCLS.filtred_u:
                text = DTCLS.mngr_acess.get_name_dolgn(DTCLS.filtred_u[-1]).replace('_',' ')
                self.ui.lbl_filtred_r.setText(f'Фильтр по: "{text}"')
            else:
                self.ui.lbl_filtred_r.clear()
            self.reload_r()
    def reset_filters(self):
        self.set_filter(CLSS.Filters.r)
        self.set_filter(CLSS.Filters.u)


    def reload_u(self):
        template_by_dolgn = DTCLS.mngr_acess.template_by_dolgn(DTCLS.filtred_r)
        CQT.fill_wtabl(template_by_dolgn, self.ui.tbl_dolgn, styleSheet=CQT.MES_CSS, selectionMode="SingleSelection",
                       selectionBehavior="SelectRows",sortingEnabled=True)
        CQT.fill_filtr_c(self, self.ui.tbl_dolgn_filter, self.ui.tbl_dolgn, show_header=False,hidden_scroll=True)
        if DTCLS.filtred_r is None:
            self.set_fio_filter(DTCLS.filtred_r)
    def reload_r(self):
        temlate_by_rules = DTCLS.mngr_acess.template_by_rules(DTCLS.filtred_u)
        CQT.fill_wtabl(temlate_by_rules, self.ui.tbl_rules, styleSheet=CQT.MES_CSS, selectionMode="SingleSelection",
                       selectionBehavior="SelectRows",sortingEnabled=True)

        CQT.fill_filtr_c(self, self.ui.tbl_rules_filter, self.ui.tbl_rules, show_header=False,hidden_scroll=True)

        self.set_fio_filter(DTCLS.filtred_u)

    def reset_rule_filter(self):
        self.set_filter(CLSS.Filters.r)

    def reset_dolgn_filter(self):
        self.set_filter(CLSS.Filters.u)

    def select_rule(self,*args):
        t = CQT.TableContext(self.ui.tbl_rules)
        row = t.current_row()
        if row.no_selection:
            return
        rule = row.value('Правило')
        self.set_filter(CLSS.Filters.r,rule)

    def select_dolgn(self,*args):
        t = CQT.TableContext(self.ui.tbl_dolgn)
        row = t.current_row()
        if row.no_selection:
            return
        poki = int(row.value('poki'))
        ref_dolgn = row.value('_ref_dolgn')
        self.set_filter(CLSS.Filters.u,(poki,ref_dolgn))
    def select_fio(self,*args):
        t = CQT.TableContext(self.ui.tbl_fio)
        row = t.current_row()
        if row.no_selection:
            return
        poki = int(row.value('poki'))
        ref_dolgn = row.value('Должность_ref')
        t = CQT.TableContext(self.ui.tbl_dolgn_filter)
        row = t.get_row(0)
        row.set_value('_ref_dolgn',ref_dolgn)
        row.set_value('poki',poki)

        CQT.apply_filtr_c(self,self.ui.tbl_dolgn_filter,self.ui.tbl_dolgn,
                          )


    def set_fio_filter(self,key:tuple[int,str]):
        users = DTCLS.mngr_acess.template_active_users(key)
        CQT.fill_wtabl(users, self.ui.tbl_fio, styleSheet=CQT.MES_CSS, selectionMode="SingleSelection",
                       selectionBehavior="SelectRows",sortingEnabled=True)
        CQT.fill_filtr_c(self, self.ui.tbl_fio_filter, self.ui.tbl_fio, show_header=False, hidden_scroll=True)

    def apply_filter_r(self):
        pass

    def _____________________________(self):pass


if __name__ == "__main__":

    from project_cust_38.Cust_application import install_crash_guard, SafeApplication
    app = SafeApplication(sys.argv)
    install_crash_guard(app, app_name='',user_name='', log_qt_warnings=False,log_qt_debug_info=False, enable_native_fault_handler=False)
    #CQT.ThemeManager.apply(app)
    sub_window = CentralWindow(None)
    sub_window.showMaximized()
    sys.exit(app.exec())
