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
import project_cust_38.Cust_docs as CDCS
import project_cust_38.Cust_b24 as CB24
import project_cust_38.Cust_RichTextEditor as RTE


from project_cust_38.sub_mes.resource_planning.dataClass_res_pl import data_app as DTCLS
import project_cust_38.sub_mes.resource_planning.main_ui as main_ui
if DTCLS.CONFIG.user_config.is_developer:
    if CQT.convert_UI_into_PY_c(str(F.Cust_path(main_ui)) + F.sep()):
        import importlib
        importlib.reload(main_ui)

import project_cust_38.sub_mes.resource_planning.connects as _con


from project_cust_38 import dynamic_db_models as DDM
from project_cust_38 import Cust_orm as CORM
import project_cust_38.sub_mes.resource_planning.clses as CLSS
from project_cust_38.sub_mes.resource_planning import planner_mes_types
from project_cust_38.sub_mes.resource_planning import planner_mes_entities


from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    from Viewer import mywindow



DTSUB = DTCLS.module_manage_sub_app
STORE = DTCLS.ReferenceStore




class Plwindow(CQT.QtWidgets.QMainWindow):
    def __init__(self,app_self,subject_pl:SubjectPl):
        super(Plwindow, self).__init__()
        self.ui = main_ui.Ui_mainWindow()
        self.ui.setupUi(self)
        self.app_self = app_self

        if self.app_self:
             self.setStyleSheet(self.app_self.styleSheet())
        else:
             self._load_free_css()

        self.setAttribute(CQT.Qt.WA_DeleteOnClose)
        CQT.connect_to_resize(self, CMS.tmp_dir())
        DTSUB.sub_self = self
        CQT.load_icons(self, 26, dir=str(F.Cust_path(main_ui)) + F.sep() + 'icons' + F.sep())
        self.setWindowModality(CQT.Qt.ApplicationModal)
        self.apply_subj(subject_pl)


        _con.load_connects(self)


    def _____________sub__________________(self):
        pass

    def init_data(self):
        CQT.load_resize_splitters(self, CQT.qt_tmp_dir())

        DTCLS.init_data()

        planner_mes_types_o = getattr(DTSUB,'planner_mes_types',None)
        if planner_mes_types_o is not None:
            planner_mes_types_o.close()
        DTSUB.planner_mes_types = planner_mes_types.PlannerMesTypeCatalog()
        DTSUB.custom_types = CLSS.CustomTypes(DTSUB.planner_mes_types)

        DTCLS.module_manage_sub_app.shablons_res = CLSS.ShablonsRes()
        self.load_s_shab(CLSS.Type_entitys.Res,True)
        DTCLS.module_manage_sub_app.shablons_eve = CLSS.ShablonsEve()
        self.load_s_shab(CLSS.Type_entitys.Eve,True)
        DTCLS.module_manage_sub_app.info_o = CLSS.Info(self.ui.tbl_info,self.ui.btn_info_ok,self.ui.btn_info_cancel)
        DTCLS.module_manage_sub_app.resources = CLSS.Resources()
        self.load_resources(True)
        DTCLS.module_manage_sub_app.events = CLSS.Events()
        self.load_events(True)
        DTCLS.module_manage_sub_app.crosses = CLSS.Crosses()
        self.load_crosses(True)

        self.fill_cmb_reports()
        DTCLS.module_manage_sub_app.user_config_sub_plan = CLSS.UserConfigSubPlan()
        DTCLS.module_manage_sub_app.user_config_sub_plan.load_config()

    def _load_free_css(self):
        theme_path = F.sep().join([F.path_to_execut_file_c(), 'css'])
        CQT.apply_css_theme(self, theme_path + F.sep()  + 'metallic.qss')

    def keyReleaseEvent(self,e):
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
        planner_mes_types_o = getattr(DTSUB,'planner_mes_types',None)
        if planner_mes_types_o is not None:
            planner_mes_types_o.close()
            DTSUB.planner_mes_types = None
        event.accept()

    def _____________subjects_________________(self):
        pass
    def apply_subj(self,subject_pl):
        DTSUB.subj_pl = subject_pl
        self.NAME_MODULE_BASE = f'Планирование ресуросов v0.1 - {subject_pl.text}'
        DTCLS.CONFIG.user_config.set_sub_window_title(self)
        # CONNECTS
        _con.prepare_ui(self)
        self.init_data()
    def select_sbjpl(self,*args):
        cmb = self.ui.cmb_select_sbjpl
        name_sbjpl = CQT.get_cmb_current_data(cmb)
        self.apply_subj(CLSS.SubjectsPl.get(name_sbjpl))


    def _____________info__________________(self):
        pass
    @CQT.onerror
    def info_resource(self, dimention_o: CLSS.Resource | CLSS.Event| CLSS.Cross):
        def fnc_update_data(t:CQT.TableContext,delta:dict):
            rez, err = dimention_o.set_data(delta)
            if not rez:
                CQT.msgbox(f'{err}')
                return
            if isinstance(dimention_o,CLSS.Cross):
                self.list_crosses_reload()
                self.select_cross()
                self.crosses_save()
                return
            if dimention_o._TYPE_DIMENSION is CLSS.Type_entitys.Res:
                self.list_resources_reload()
                self.select_resource()
                self.resources_save()
                self.list_crosses_reload()
            if dimention_o._TYPE_DIMENSION is CLSS.Type_entitys.Eve:
                self.list_events_reload()
                self.select_event()
                self.events_save()
                self.list_crosses_reload()

        def fnc_edit_cells(tbl:CQT.QtWidgets.QTableWidget,
                           item:CQT.QtWidgets.QTableWidgetItem,
                           addit_data):
            t = CQT.TableContext(tbl)
            row = t.get_row(item.row())
            def check_str(val):
                if len(val)<3:
                    return False
                return True
            val = row.value('Значение')

            if check_str(val):
                CQT.setCustData(item,val,False,101)
                return True
            return False

        def func_oform(t:CQT.TableContext,*args,**kwargs):
            # ==========================emoj==========================================
            row_emo = t.find_row({'_name':'emoj'},first=True)
            if row_emo:
                list_emoj = [ _.symbol for _ in F.get_all_attrs(CEMOJ.СтатусыПроизводства).values()]
                list_emoj.extend([ _.symbol for _ in F.get_all_attrs(CEMOJ.ОперацииПроизводства).values()])
                list_emoj.extend([ _.symbol for _ in F.get_all_attrs(CEMOJ.ПерсоналРоли).values()])
                def fnc_select(sub_app,emo_str,row,col):
                    t.tbl.item(row,col).setText(emo_str)
                    CQT.setCustData(t.tbl.item(row,col),emo_str,modifier=101)

                CQT.add_combobox(DTSUB.sub_self,t.tbl,row_emo.i,t.nf['Значение'],list_emoj,first_void=True,conn_func=fnc_select)

            #==========================delete==========================================
            def fnc_switch(sub_self, tbl, val, i,j, *args):
                tbl.item(i,j).setText(str(val))
                CQT.setCustData(tbl.item(i,j),val,modifier=101)

            row_del =  t.find_row({'_name':'for_delete'},first=True)
            if row_del:
                CQT.add_check_box_switcher(t.tbl,row_del.i,t.nf['Значение'],
                                           row_del.value('Значение',get_cust_content=True),
                                           fnc_switch,DTSUB.sub_self)
            #==========================clr==========================================
            row_clr =  t.find_row({'_name':'color'},first=True)
            if row_clr:
                val_o:CMS.Color = row_clr.value('Значение',get_cust_content=True)
                row_clr.set_color_background(*val_o.rgba, col_name='Значение')

                def fnc_select_clr(lbl:CQT.InteractiveLabelInstance,sub_self,i,j,row:CQT.TableRow):
                    val_o: CMS.Color = row_clr.value('Значение', get_cust_content=True)
                    clr_tuple = CQT.color_dialog_c(DTSUB.sub_self,val_o.qcolor,return_color_type=CQT.ColorPickReturn.rgb)
                    clr_o = CMS.Color(clr_tuple)
                    row_clr.set_color_background(*clr_o.rgba, col_name='Значение')
                    row_clr.set_value('Значение',clr_o,True)


                widg = CQT.add_interactive_label(t.tbl, row_clr.i, t.nf['Значение'], row_clr.value('Значение'),
                                                 parent_self=DTSUB.sub_self, grab_style_from_cell=True,
                                                 autoupdate_column_size=False)
                widg.add_button('...', 'Выбор',
                                fnc_select_clr,
                                cell_val=row_clr, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                     'icons', 'btn_select']))
            # ==============================cdt======================================
            def fnc_select_date(lbl:CQT.InteractiveLabelInstance,sub_self,i,j,row:CQT.TableRow):
                rez, dates = CQT.get_data_dialog_choose(DTSUB.sub_self,'Выбрать дату')
                if not rez:
                    return
                date = dates['date_from']

                row.set_value('Значение',CLSS.Cdt(date).to_string_ru_wo_s())
                row.set_value('Значение',CLSS.Cdt(date),set_cust_content=True)


            def fnc_select_time(lbl:CQT.InteractiveLabelInstance,sub_self,i,j,row:CQT.TableRow):
                date:CLSS.Cdt = row.value('Значение', get_cust_content=True)
                if not date :
                    CQT.msgbox(f'Не выбрана дата')
                    return
                rez, times = CQT.get_time_dialog_choose(DTSUB.sub_self,'Выберите время')
                if not rez:
                    return
                time = times['time_from']
                date = date.set_time(time,copy_obj=True)
                row.set_value('Значение', date.to_string_ru_wo_s())
                row.set_value('Значение', date, set_cust_content=True)
                pass

            # ==============================start======================================
            row_start = t.find_row({'_name': 'start'}, first=True)
            if row_start:
                widg = CQT.add_interactive_label(t.tbl, row_start.i, t.nf['Значение'], row_start.value('Значение'),
                                                 parent_self=DTSUB.sub_self, grab_style_from_cell=True,
                                                 autoupdate_column_size=False)
                widg.add_button('...', 'Выбор дата',
                                fnc_select_date,
                                cell_val=row_start, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                         'icons', 'btn_select_date']))
                widg.add_button('...', 'Выбор время',
                                fnc_select_time,
                                cell_val=row_start, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                         'icons', 'btn_select_time']))
            # ==============================end======================================
            row_end = t.find_row({'_name': 'end'}, first=True)
            if row_start:
                widg = CQT.add_interactive_label(t.tbl, row_end.i, t.nf['Значение'], row_end.value('Значение'),
                                                 parent_self=DTSUB.sub_self, grab_style_from_cell=True,
                                                 autoupdate_column_size=False)
                widg.add_button('...', 'Выбор дата',
                                fnc_select_date,
                                cell_val=row_end, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                         'icons', 'btn_select_date']))
                widg.add_button('...', 'Выбор время',
                                fnc_select_time,
                                cell_val=row_end, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                         'icons', 'btn_select_time']))
            get_cust_attrs = getattr(dimention_o,'get_dict_cust_attrs',None)
            cust_attrs = get_cust_attrs() if callable(get_cust_attrs) else {}
            for attr_name,attr in cust_attrs.items():
                type_attr = attr.info.type
                if not isinstance(type_attr,type) or not issubclass(type_attr,CLSS.Mes_type):
                    continue
                row_mes = t.find_row({'_name':attr_name},first=True)
                if not row_mes :# or attr.info.protected:
                    continue

                def fnc_select_mes_entity(lbl:CQT.InteractiveLabelInstance,sub_self,i,j,row:CQT.TableRow,
                                          type_attr=type_attr,presentation_key=attr.info.attr_view):
                    try:
                        DTSUB.custom_types.refresh_mes_types()
                        choice = DTSUB.planner_mes_types.choice_for_type(type_attr)
                        if presentation_key and not any(
                                item.presentation_key == presentation_key
                                for item in choice.presentations):
                            presentation_key = choice.default_presentation.presentation_key
                        service = planner_mes_entities.MesEntityService.from_type_catalog(
                            DTSUB.planner_mes_types
                        )
                        current_value = row.value('Значение',get_cust_content=True)
                        current_ref = getattr(current_value,'reference',None)
                        result = planner_mes_entities.select_mes_entity(
                            DTSUB.sub_self,service,choice,
                            presentation_key=presentation_key or None,
                            current=current_ref,
                        )
                    except Exception as exc:
                        CQT.msgbox(f'Не удалось выбрать сущность МЕС: {exc}')
                        return
                    if not result.accepted:
                        return
                    new_value = None if result.reference is None else type_attr(result.reference)
                    text_value = '' if new_value is None else str(new_value)
                    row.set_value('Значение',text_value)
                    row.set_value('Значение',new_value,set_cust_content=True)
                    lbl.set_text(text_value)

                widg = CQT.add_interactive_label(
                    t.tbl,row_mes.i,t.nf['Значение'],row_mes.value('Значение'),
                    parent_self=DTSUB.sub_self,grab_style_from_cell=True,
                    autoupdate_column_size=False
                )
                widg.add_button(
                    '...','Выбрать сущность МЕС',fnc_select_mes_entity,cell_val=row_mes,
                    img_path=F.sep().join([F.path_to_caller_file_c(),'icons','btn_select'])
                )
            # ====================================================================
            # =======================cross_res==============================
            row_res = t.find_row({'_name': 'res'}, first=True)
            if row_res:
                res_id = row_res.value('Значение',get_cust_content=True)
                res_o:CLSS.Resource = DTSUB.resources.get(res_id)
                row_res.set_value('Значение', res_o)

            # ====================================================================
            # =======================cross_eve==============================
            row_eve = t.find_row({'_name': 'evr'}, first=True)
            if row_eve:
                eve_id = row_eve.value('Значение',get_cust_content=True)
                eve_o:CLSS.Resource = DTSUB.events.get(eve_id)
                row_eve.set_value('Значение', eve_o)

            # ====================================================================
            t.hide_if_not_dev(CFG,forced_text=True)
            pass


        data, dict_data, dict_aliases = dimention_o.template_info()
        DTSUB.info_o.update_info(data, dict_data, True, fnc_update_data=fnc_update_data, dict_aliases=dict_aliases,
                                 fnc_edit_cells= fnc_edit_cells,
                                 protected_names = dimention_o.get_protected_names(), fnc_oform= func_oform)
    def info_shablon(self,shablon_o,read_only=False):


        def fnc_update_data(t:CQT.TableContext,delta:dict):
            if shablon_o.set_data(delta):
                if DTSUB.current_settings_mode:
                    self.list_shablons_reload()
                    self.select_shablon()


        def fnc_edit_cells(tbl:CQT.QtWidgets.QTableWidget,
                           item:CQT.QtWidgets.QTableWidgetItem,
                           addit_data):
            t = CQT.TableContext(tbl)
            row = t.get_row(item.row())
            def check_str(val):
                if len(val)<3:
                    return False
                return True
            val = row.value('Значение')

            if check_str(val):
                CQT.setCustData(item,val,False,101)
                return True
            return False

        def func_oform(t:CQT.TableContext,info_o:CLSS.Info,*args,**kwargs):
            # ==========================emoj==========================================

            row_emo = t.find_row({'_name':'emoj'},first=True)
            if not row_emo:
                return
            list_emoj = [ _.symbol for _ in F.get_all_attrs(CEMOJ.СтатусыПроизводства).values()]
            list_emoj.extend([ _.symbol for _ in F.get_all_attrs(CEMOJ.ОперацииПроизводства).values()])
            list_emoj.extend([ _.symbol for _ in F.get_all_attrs(CEMOJ.ПерсоналРоли).values()])
            def fnc_select(sub_app,emo_str,row,col):
                t.tbl.item(row,col).setText(emo_str)
                CQT.setCustData(t.tbl.item(row,col),emo_str,modifier=101)

            CQT.add_combobox(DTSUB.sub_self,t.tbl,row_emo.i,t.nf['Значение'],list_emoj,first_void=True,conn_func=fnc_select,enabled= not read_only)

            #==========================delete==========================================
            def fnc_switch(sub_self, tbl, val, i,j, *args):
                tbl.item(i,j).setText(str(val))
                CQT.setCustData(tbl.item(i,j),val,modifier=101)

            row_del =  t.find_row({'_name':'for_delete'},first=True)
            CQT.add_check_box_switcher(t.tbl,row_del.i,t.nf['Значение'],
                                       row_del.value('Значение',get_cust_content=True),
                                       fnc_switch,DTSUB.sub_self,enabled= not read_only)
            #==========================clr==========================================
            row_clr =  t.find_row({'_name':'color'},first=True)
            val_o:CMS.Color = row_clr.value('Значение',get_cust_content=True)
            row_clr.set_color_background(*val_o.rgba, col_name='Значение')

            def fnc_select_clr(lbl:CQT.InteractiveLabelInstance,sub_self,i,j,row:CQT.TableRow):
                val_o: CMS.Color = row_clr.value('Значение', get_cust_content=True)
                clr_tuple = CQT.color_dialog_c(DTSUB.sub_self,val_o.qcolor,return_color_type=CQT.ColorPickReturn.rgb)
                clr_o = CMS.Color(clr_tuple)
                row_clr.set_color_background(*clr_o.rgba, col_name='Значение')
                row_clr.set_value('Значение',clr_o,True)

            widg = CQT.add_interactive_label(t.tbl, row_clr.i, t.nf['Значение'], row_clr.value('Значение'),
                                             parent_self=DTSUB.sub_self, grab_style_from_cell=True,
                                             autoupdate_column_size=False)
            if not read_only:

                widg.add_button('...', 'Выбор',
                                fnc_select_clr,
                                cell_val=row_clr, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                     'icons', 'btn_select']))

            t.hide_if_not_dev(CFG,forced_text=True)
            pass
            # ==========================clr==========================================
            def fnd_click_btn_add_attr(path,i,j, addit_data, *args):
                if info_o.add_new_attr():
                    if DTSUB.current_settings_mode is CLSS.Type_entitys.Res:
                        dimensions = DTSUB.resources
                    else:
                        dimensions = DTSUB.events
                    shablon_o.upadte_child_attrs(dimensions)
                    self.info_shablon(shablon_o,read_only=read_only)
            def fnd_click_btn_del_attr(sub_self:Plwindow,i,j, *args):
                pass
            def fnd_click_btn_edit_attr(sub_self:Plwindow,i,j, *args):
                pass
            row_cust_attr = t.find_row({'_name': 'cust_attrs'}, first=True)

            CQT.add_image(row_cust_attr.tbl,row_cust_attr.i,row_cust_attr.nf['Дств'],tooltip= 'Добавить атрибут', conn_func_click=
                        fnd_click_btn_add_attr, addit_data=  DTSUB.sub_self, path= F.sep().join([F.path_to_caller_file_c(),
                                                                     'icons', 'btn_add']),stylesheet=DTSUB.sub_self.styleSheet())

            t_sub = row_cust_attr.value('Значение',sub_table=True,as_table_context=True)
            if t_sub:

                for sub_row in t_sub.rows():

                    CQT.add_image(t_sub.tbl, sub_row.i, sub_row.nf['ca_del'], tooltip='Удалить атрибут',
                                  conn_func_click=
                                  fnd_click_btn_del_attr, addit_data=DTSUB.sub_self,
                                  path=F.sep().join([F.path_to_caller_file_c(),
                                                     'icons', 'btn_del']), stylesheet=DTSUB.sub_self.styleSheet())

                    CQT.add_image(t_sub.tbl, sub_row.i, sub_row.nf['ca_edit'], tooltip='Изменить атрибут',
                                  conn_func_click=
                                  fnd_click_btn_edit_attr, addit_data=DTSUB.sub_self,
                                  path=F.sep().join([F.path_to_caller_file_c(),
                                                     'icons', 'btn_edit']), stylesheet=DTSUB.sub_self.styleSheet())
                t_sub.hide_if_not_dev(CFG,True)




        data, dict_data, dict_aliases = shablon_o.full_template()
        dict_aliases:dict
        dict_aliases.update(CLSS.CustAttrs.aliases())
        DTSUB.info_o.update_info(data,dict_data,not read_only,fnc_update_data=fnc_update_data,dict_aliases=dict_aliases,
                                 fnc_edit_cells= fnc_edit_cells,
                                 protected_names = shablon_o.get_protected_names(),fnc_oform= func_oform)


    def _____________settings__________________(self):
        pass

    def s_shab_save(self):
        if DTSUB.current_settings_mode is CLSS.Type_entitys.Res:
            data = CLSS.ShablonsResDB().to_dict(DTSUB.shablons_res)
        if DTSUB.current_settings_mode is CLSS.Type_entitys.Eve:
            data = CLSS.ShablonsEveDB().to_dict(DTSUB.shablons_eve)
        if data:
            name = DTSUB.current_settings_mode.name
            name_pl = DTSUB.subj_pl.name
            file_name = f"{name}_{name_pl}.json"
            F.save_file_pickle(file_name, data)

    def load_s_shab(self,current_settings_mode:CLSS.Type_entity, reload_ui=False):
        if reload_ui:
            CQT.soft_clear_tbl(self.ui.tbl_s_list_shabl)

        name = current_settings_mode.name
        name_pl = DTSUB.subj_pl.name
        file_name = f"{name}_{name_pl}.json"
        if not F.existence_file_c(file_name):
            return
        data = F.load_file_pickle(file_name)
        if not data:
            return
        if current_settings_mode is CLSS.Type_entitys.Res:
            DTSUB.shablons_res = CLSS.ShablonsResDB().from_dict(data)
        if current_settings_mode is CLSS.Type_entitys.Eve:
            DTSUB.shablons_eve = CLSS.ShablonsEveDB().from_dict(data)
        if reload_ui:
            self.list_shablons_reload()


    def new_shablon(self):
        new = None
        if DTSUB.current_settings_mode is CLSS.Type_entitys.Res:
            new = DTSUB.shablons_res.add()
        if DTSUB.current_settings_mode is CLSS.Type_entitys.Eve:
            new = DTSUB.shablons_eve.add()

        if new:
            self.list_shablons_reload()
        else:
            CQT.msgbox(f"Не удалось создать")
            return

    def get_shablon(self,id:int,type_o:CLSS.Type_entity)->None|CLSS.ShablonRes|CLSS.ShablonEve:
        shablon_o = None
        if type_o is CLSS.Type_entitys.Res:
            shablon_o = DTSUB.shablons_res.get(id)
        elif type_o is CLSS.Type_entitys.Eve:
            shablon_o = DTSUB.shablons_eve.get(id)
        return shablon_o

    def select_shablon(self):
        tbl = self.ui.tbl_s_list_shabl
        t = CQT.TableContext(tbl)
        row = t.current_row()
        if row.no_selection:
            return
        id = int(row.value('id'))
        type_entity_o = CLSS.Type_entitys.get_by_name(row.value('type_entity',get_cust_content=True))
        if not type_entity_o:
            return
        shablon_o = self.get_shablon(id,type_entity_o)
        self.info_shablon(shablon_o)


    def list_shablons_reload(self):
        template = None
        storage = None
        if DTSUB.current_settings_mode is CLSS.Type_entitys.Res:
            storage = DTSUB.shablons_res

        if DTSUB.current_settings_mode is CLSS.Type_entitys.Eve:
            storage = DTSUB.shablons_eve
        if storage:
            template, template_data, dict_aliases = storage.template()
        if template:
            CQT.fill_wtabl(template, self.ui.tbl_s_list_shabl, aliases_header=dict_aliases, styleSheet=CQT.MES_EDIT_CSS,
                           dict_or_list_user_data=template_data)
            t = CQT.TableContext(self.ui.tbl_s_list_shabl)
            t.hide_if_not_dev(CFG, forced_text=True)
            for row in t.rows():
                id_sh = int(row.value('id'))
                sh_o = storage.get(id_sh)

                clr = sh_o.color.value
                row.set_color_background(*clr.rgba, col_name='name')
                row.set_color_font(*clr.text_color.rgba, col_name='name')

        else:
            CQT.clear_tbl(self.ui.tbl_s_list_shabl)

    def ____________base_res_eve__________________(self):
        pass

    @CQT.onerror()
    def oform_maint_tbl(self,tbl:CQT.QtWidgets.QTableWidget,mnger_dims:CLSS.Resources | CLSS.Events):

        t = CQT.TableContext(tbl)
        for row in t.rows():

            res_id = int(row.value('id'))
            dim_o:CLSS.Resource|CLSS.Event = mnger_dims.get(res_id)
            clr_o: CMS.Color = dim_o.color.value
            shabl_o = dim_o.get_shablon()
            clr_shabl_c = shabl_o.color.value.copy()
            clr_shabl_c.a = 85
            row.set_color_background(*clr_shabl_c.rgba, col_name='shablon')
            row.set_color_font(*clr_shabl_c.text_color.rgba, col_name='shablon')
            clr_o_c = clr_o.copy()
            clr_o_c.a = 85
            row.set_color_background(*clr_o_c.rgba, col_name='name')
            row.set_color_font(*clr_o_c.text_color.rgba, col_name='name')

        t.hide_if_not_dev(CFG,forced_text=True)
    @CQT.onerror()
    def new_dim(self):
        mnger_shablons:CLSS.ShablonsRes|CLSS.ShablonsEve = None
        mnger_dims:CLSS.Resources|CLSS.Events = None
        if DTSUB.current_focus_type is CLSS.FocusTypes.EVENT:
            mnger_shablons = DTSUB.shablons_eve
            mnger_dims = DTSUB.events
        if DTSUB.current_focus_type is CLSS.FocusTypes.RESOURCE:
            mnger_shablons = DTSUB.shablons_res
            mnger_dims = DTSUB.resources

        if mnger_shablons is None:
            CQT.msgbox("Ошибка иницализации шаблонов")
            return
        list_shabl, list_data, list_alises = mnger_shablons.template(include_deleted=False)
        if not list_shabl:
            CQT.msgbox("Нет шаблонов")
            return
        def fnc_oform_tbl(tbl:CQT.QtWidgets.QTableWidget,*args,**kwargs):
            if DTSUB.current_focus_type is CLSS.FocusTypes.EVENT:
                mnger_shablons = DTSUB.shablons_eve

            if DTSUB.current_focus_type is CLSS.FocusTypes.RESOURCE:
                mnger_shablons = DTSUB.shablons_res

            t = CQT.TableContext(tbl)
            for row in t.rows():
                id = int(row.value('id',get_cust_content=True))
                obj = mnger_shablons.get(id)
                clr_o = obj.color.value
                row.set_color_background(*clr_o.rgba,'name')
            t.hide_if_not_dev(CFG,forced_text=True)

        shabl = CQT.msgboxg_get_table(self,'Выбор шаблона',list_shabl,styleSheet=CQT.MES_EDIT_CSS,selectRows=True,
                                      ExtendedSelection=False,selection_from_tbl=True,aliases_header=list_alises,
                                      func_oform_tbl=fnc_oform_tbl,dict_or_list_user_data=list_data
                                      )
        if not shabl:
            return

        def fnc_oform(tbl:CQT.QtWidgets.QTableWidget,*args,**kwargs):
            t = CQT.TableContext(tbl)
            row_shabl = t.find_row({'_name':'shablon'},first=True)

            t.set_editable('Значение')
            row_shabl.set_editable('Значение',False)
            shabl_o:CLSS.ShablonRes = mnger_shablons.get( row_shabl.value('Значение',get_cust_content=True))
            clr_sh = shabl_o.color.value
            row_shabl.set_color_background(*clr_sh.rgba,col_name='Значение')
            row_shabl.set_color_font(*clr_sh.text_color.rgba,col_name='Значение')

            t.hide_if_not_dev(CFG,forced_text=True)


        def fnc_result(data,*args,**kwargs):
            return {_['_name']:_['Значение'] for _ in data }



        id_shabl = int(shabl['id'])

        new_dim_o = mnger_dims.new(id_shabl)
        dict_text, dict_data = new_dim_o.template_new()
        selected_dim = CQT.msgboxg_get_table(self,f'Новый {mnger_dims._TYPE.name_one}',dict_text,styleSheet=CQT.MES_EDIT_CSS,
                                        func_oform_tbl=fnc_oform,func_validate=fnc_result,
                                        dict_or_list_user_data=dict_data)
        if not selected_dim:
            return
        data = selected_dim
        new_dim_o.name.set_value(data['name'])
        new_dim_o.descr.set_value(data['descr'])


    def update_table(self):
        if self.ui.tbl_cross.hasFocus():
            self.list_crosses_reload()
        if self.ui.tbl_resuorces.hasFocus():
            self.list_resources_reload()
        if self.ui.tbl_events.hasFocus():
            self.list_events_reload()
        if self.ui.tbl_gr.hasFocus():
            self.select_report()


    def ____________resources__________________(self):
        pass

    @CQT.onerror()
    def select_resource(self):
        tbl = self.ui.tbl_resuorces
        t = CQT.TableContext(tbl)
        row = t.current_row()
        if row.no_selection:
            return

        id = int(row.value('id'))
        resource_o = DTSUB.resources.get(id)
        if t.current_column_name() == 'shablon':
            shablon_o = resource_o.get_shablon()
            self.info_shablon(shablon_o,read_only=True)
        else:
            self.info_resource(resource_o)
        self.apply_cross_filter(id_res=id)
    @CQT.onerror()
    def list_resources_reload(self,clear=False):
        if clear:
            template_list, template_list_data, template_aliases = ([], [], {})
        else:
            template_list,template_list_data,template_aliases  = DTSUB.resources.template_list()
        tbl = self.ui.tbl_resuorces
        CQT.fill_wtabl(template_list,tbl,styleSheet=CQT.MES_EDIT_CSS,dict_or_list_user_data=template_list_data,
                       aliases_header=template_aliases,auto_type=True,sortingEnabled=True,selectionBehavior='SelectRows')
        CMS.fill_filtr_c(self,self.ui.tbl_resuorces_filtr,self.ui.tbl_resuorces,show_header=False,check_box_dict={'shablon':None,'name':None})

        t = CQT.TableContext(tbl)
        self.oform_maint_tbl(tbl,DTSUB.resources)

    @CQT.onerror()
    def new_res(self):
        self.new_dim()
        self.resources_save()
        self.list_resources_reload()


    def resources_save(self):
        data = DTSUB.resources.to_dict()
        if data:
            name = DTSUB.subj_pl.name
            file_name = f"{name}_resources.json"
            F.save_file_pickle(file_name, data)

    def load_resources(self, reload_ui=False):
        if reload_ui:
            self.list_resources_reload(clear=True)

        name = DTSUB.subj_pl.name
        file_name = f"{name}_resources.json"
        if not F.existence_file_c(file_name):
            return
        data = F.load_file_pickle(file_name)
        if not data:
            return
        DTSUB.resources = CLSS.Resources().from_dict(data)

        if reload_ui:
            self.list_resources_reload()
    def ____________events__________________(self):
        pass

    @CQT.onerror()
    def select_event(self):
        tbl = self.ui.tbl_events
        t = CQT.TableContext(tbl)
        row = t.current_row()
        if row.no_selection:
            return

        id = int(row.value('id'))
        event_o = DTSUB.events.get(id)
        if t.current_column_name() == 'shablon':
            shablon_o = event_o.get_shablon()
            self.info_shablon(shablon_o, read_only=True)
        else:
            self.info_resource(event_o)

        self.apply_cross_filter(id_eve=id)
    @CQT.onerror()
    def new_eve(self):
        self.new_dim()
        self.events_save()
        self.list_events_reload()

    def events_save(self):
        data = DTSUB.events.to_dict()
        if data:
            name = DTSUB.subj_pl.name
            file_name = f"{name}_events.json"
            F.save_file_pickle(file_name, data)


    def load_events(self, reload_ui=False):
        if reload_ui:
            self.list_events_reload(clear=True)
        name = DTSUB.subj_pl.name
        file_name = f"{name}_events.json"
        if not F.existence_file_c(file_name):
            return
        data = F.load_file_pickle(file_name)
        if not data:
            return
        DTSUB.events = CLSS.Events().from_dict(data)

        if reload_ui:
            self.list_events_reload()


    @CQT.onerror()
    def list_events_reload(self,clear=False):
        if clear:
            template_list, template_list_data, template_aliases = ([],[],{})
        else:
            template_list,template_list_data,template_aliases  = DTSUB.events.template_list()
        tbl = self.ui.tbl_events
        CQT.fill_wtabl(template_list,tbl,styleSheet=CQT.MES_EDIT_CSS,dict_or_list_user_data=template_list_data,
                       aliases_header=template_aliases,auto_type=True,sortingEnabled=True,selectionBehavior='SelectRows')
        CMS.fill_filtr_c(self,self.ui.tbl_events_filtr,self.ui.tbl_events,show_header=False,check_box_dict={'shablon':None,'name':None})

        self.oform_maint_tbl(tbl,DTSUB.events)

    def ____________crosses__________________(self):
        pass

    @CQT.onerror()
    def select_cross(self):
        tbl = self.ui.tbl_cross
        t = CQT.TableContext(tbl)
        row = t.current_row()
        if row.no_selection:
            return

        id = int(row.value('id'))
        cross_o = DTSUB.crosses.get(id)
        self.info_resource(cross_o)
    def oform_cross_tbl(self,tbl):
        def oform_dim(clmn_name:str):
            id = row.value(clmn_name, get_cust_content=True)
            if clmn_name == 'eve':
                dim: CLSS.Event = DTSUB.events.get(int(id))
            if clmn_name == 'res':
                dim: CLSS.Resource = DTSUB.resources.get(int(id))
            clr = dim.color.value
            clr.a = 85
            row.set_color_background(*clr.rgba, col_name=clmn_name)
            row.set_color_font(*clr.text_color.rgba, col_name=clmn_name)

        t = CQT.TableContext(tbl)
        for row in t.rows():
            oform_dim('eve')
            oform_dim('res')

        t.hide_if_not_dev(CFG,True)


    @CQT.onerror()
    def list_crosses_reload(self,clear=False):

        by_res = DTSUB.filtr_cross_by_res
        by_eve = DTSUB.filtr_cross_by_eve
        if clear:
            template_list, template_list_data, template_aliases = ([],[],{})
        else:
            template_list,template_list_data,template_aliases  = DTSUB.crosses.template_list(by_res=by_res,by_eve=by_eve)
        for it in template_list:
            id_eve = it['eve']
            eve:CLSS.Event = DTSUB.events.get(id_eve)
            eve_name = str(eve)
            id_res = it['res']
            res:CLSS.Resource = DTSUB.resources.get(id_res)
            res_name = str(res)
            it['eve'] = eve_name
            it['res'] = res_name
            it['start_eve'] = eve.start.value.to_string_ru_wo_s()
            it['end_eve'] = eve.end.value.to_string_ru_wo_s()

        tbl = self.ui.tbl_cross
        CQT.fill_wtabl(template_list,tbl,styleSheet=CQT.MES_EDIT_CSS,dict_or_list_user_data=template_list_data,
                       aliases_header=template_aliases,auto_type=True,sortingEnabled=True,selectionBehavior='SelectRows')
        CMS.fill_filtr_c(self,self.ui.tbl_cross_filtr,self.ui.tbl_cross,show_header=False)

        self.oform_cross_tbl(tbl)
    @CQT.onerror
    def apply_cross_filter(self,id_res:int=None,id_eve:int=None):
        DTSUB.filtr_cross_by_res = id_res
        DTSUB.filtr_cross_by_eve = id_eve
        self.list_crosses_reload()
        pass
    @CQT.onerror
    def cross_show_all(self):
        self.apply_cross_filter()

    def cross_add(self):
        def fnc_oform(tbl: CQT.QtWidgets.QTableWidget, *args):
            t = CQT.TableContext(tbl)
            t.hide_if_not_dev(CFG, forced_text=True)

        fl_add = False
        if DTSUB.current_focus_type is CLSS.FocusTypes.EVENT:
            t = CQT.TableContext(self.ui.tbl_events)
            current_row = t.current_row()
            if current_row.no_selection:
                return
            id_eve = int(current_row.value('id'))
            eve:CLSS.Event = DTSUB.events.get(id_eve)

            template_list,template_list_data,template_aliases = DTSUB.resources.template_list(include_deleted=False)

            results = CQT.msgboxg_get_table(self,'Выбор ресурсов', template_list,func_oform_tbl=fnc_oform,
                                  styleSheet=CQT.MES_CSS,selectRows=True,ExtendedSelection=True,aliases_header=template_aliases)
            if not results:
                return
            ids_res = [int(_['id']) for _ in results]

            fl_add = DTSUB.crosses.add([eve.id.value],ids_res)

        if DTSUB.current_focus_type is CLSS.FocusTypes.RESOURCE:
            t = CQT.TableContext(self.ui.tbl_resuorces)
            current_row = t.current_row()
            if current_row.no_selection:
                return
            id_res = int(current_row.value('id'))
            res: CLSS.Resource = DTSUB.resources.get(id_res)

            template_list, template_list_data, template_aliases = DTSUB.events.template_list(
                include_deleted=False)

            results = CQT.msgboxg_get_table(self, 'Выбор событий', template_list, func_oform_tbl=fnc_oform,
                                            styleSheet=CQT.MES_CSS, selectRows=True, ExtendedSelection=True,
                                            aliases_header=template_aliases)
            if not results:
                return
            ids_еvents = [int(_['id']) for _ in results]

            fl_add = DTSUB.crosses.add(ids_еvents, [res.id.value])

        if not fl_add:
            CQT.msgbox(f'Не добавлено пересечений')
            return

        self.crosses_save()
        self.list_crosses_reload()


    def crosses_save(self):
        data = DTSUB.crosses.to_dict()
        if data:
            name = DTSUB.subj_pl.name
            file_name = f"{name}_crosses.json"
            F.save_file_pickle(file_name, data)

    def load_crosses(self, reload_ui=False):
        if reload_ui:
            self.list_crosses_reload(clear=True)
        name = DTSUB.subj_pl.name
        file_name = f"{name}_crosses.json"
        if not F.existence_file_c(file_name):
            return
        data = F.load_file_pickle(file_name)
        if not data:
            return
        DTSUB.crosses = CLSS.Crosses().from_dict(data)

        if reload_ui:
            self.list_crosses_reload()

    def ____________outputs_graph_________________(self):
        pass
    @CQT.onerror
    def on_layout_changed(self, *args):
        if not getattr(self,'_sort_clicked',False):
            return
        print('clicked')
        t_sub = CQT.TableContext(self.ui.tbl_gr_v_sub)

        order_res = {int(_.value('id')) : _.i for _ in t_sub.rows()}
        list_crosses = CLSS.CrossManager.get_ordered_data(DTSUB.resources, DTSUB.events, DTSUB.crosses)
        list_text_v_sub, list_data_v_sub, list_text, list_data, dict_aliases, dict_descr = CLSS.CrossManager.templates_pivot(
            list_crosses,order_res= order_res)
        self._fill_right_part_pivot_table(list_text,list_data,dict_aliases)
        self._sort_clicked = False

    @CQT.onerror
    def on_sort_changed(self, logical_index: int, order: Qt.SortOrder):
        self._sort_clicked = True



    @CQT.onerror
    def select_graph_sub_tbl(self):
        tbl = self.ui.tbl_gr_v_sub
        name_gr = CQT.get_cmb_current_data(self.ui.cmb_type_gr)
        t = CQT.TableContext(tbl)
        row = t.current_row()
        if row.no_selection:
            return
        DTSUB.info_o.clear()
        clmn_name = t.current_column_name()
        dim_name, attr_name = None, None

        if name_gr == CLSS.Reports.pivottable.name:
            id_res = int(row.value('id'))
            res = DTSUB.resources.get(id_res)
            if res:
                self.info_resource(res)
            return


    @CQT.onerror
    def select_graph(self):
        tbl = self.ui.tbl_gr
        name_gr = CQT.get_cmb_current_data(self.ui.cmb_type_gr)
        t = CQT.TableContext(tbl)
        row = t.current_row()
        if row.no_selection:
            return
        DTSUB.info_o.clear()
        clmn_name = t.current_column_name()
        dim_name, attr_name = None, None

        if name_gr == CLSS.Reports.pivottable.name:

            if isinstance(clmn_name,str):
                if '.' in clmn_name:
                    dim_name, attr_name = clmn_name.split('.')
            elif isinstance(clmn_name,int):
                eve = DTSUB.events.get(clmn_name)
                if eve:
                    self.info_resource(eve)
                return
        if name_gr == CLSS.Reports.table.name:

            if isinstance(clmn_name,str):
                if '.' in clmn_name:
                    dim_name, attr_name = clmn_name.split('.')

            if dim_name and attr_name:
                id_cross = int(row.value('cross.id'))
                entity = CLSS.CrossManager.get_cross_entity(DTSUB.resources, DTSUB.events, DTSUB.crosses,id_cross)
                if not entity:
                    return
                obj = getattr(entity, dim_name,None)
                if obj is None:
                    return
                if isinstance(obj, CLSS._Attribute):
                    obj = obj.value
                if isinstance(obj,(CLSS.Resource, CLSS.Event,CLSS.Cross)):
                    self.info_resource(obj)
                else:
                    pass

    def _fill_right_part_pivot_table(self, list_text, list_data,dict_aliases):
        CQT.fill_wtabl(list_text, self.ui.tbl_gr, styleSheet=CQT.MES_EDIT_CSS, dict_or_list_user_data=list_data,
                       aliases_header=dict_aliases, auto_type=True, sortingEnabled=False, hide_head_rows=True)

        t = CQT.TableContext(self.ui.tbl_gr)

        t.hide_if_not_dev(CFG, True)

        for row in t.rows():
            for clmn_name, j in t.nf.items():
                if not F.is_numeric(clmn_name):
                    continue
                val = row.value(clmn_name)
                if not val:
                    continue
                eve_o = DTSUB.events.get(int(clmn_name))

                clr: CMS.Color = eve_o.color.value
                row.set_color_background(*clr.rgba, col_name=clmn_name)

    @staticmethod
    @CQT.onerror
    def apply_user_config(name_gr, list_text, list_data, sort=True, filter=True)->tuple[list, list]:
        def filter_and_sort(list_data, sort=True, filter=True):
            new_list_data = list_data
            if filter:
                new_list_data = [{k: v for k, v in _.items() if k not in ucfg or (k in ucfg and ucfg[k].enable)} for _
                                 in new_list_data]
            if sort:
                new_list_data = [F.sort_dict_by_sample(_, ucfg) for _ in new_list_data]
            return new_list_data

        ucfg: dict[str, CLSS.UserConfigSubPlanElement] = DTSUB.user_config_sub_plan.oform_reports[name_gr]
        list_text = filter_and_sort(list_text, sort=sort, filter=filter)
        list_data = filter_and_sort(list_data, sort=sort, filter=filter)
        return list_text, list_data

    @CQT.onerror
    def select_report(self):
        self.ui.tbl_gr_v_sub.setVisible(False)
        t = CQT.TableContext(self.ui.tbl_gr)
        CQT.clear_tbl(t.tbl)
        name_gr = CQT.get_cmb_current_data(self.ui.cmb_type_gr)
        if not name_gr:
            return
        list_crosses = CLSS.CrossManager.get_ordered_data(DTSUB.resources, DTSUB.events, DTSUB.crosses)
        if name_gr == 'table':

            list_text,list_data,dict_descr, dict_aliases = CLSS.CrossManager.templates(list_crosses)
            list_text, list_data = self.apply_user_config(name_gr, list_text,list_data)



            CQT.fill_wtabl(list_text,self.ui.tbl_gr,styleSheet=CQT.MES_EDIT_CSS,dict_or_list_user_data = list_data,
                           aliases_header=dict_aliases,auto_type=True,sortingEnabled=True)

            t = CQT.TableContext(self.ui.tbl_gr)
            t.hide_if_not_dev(CFG,True)
            clr_names = {
                'res.color':       'res.name',
                'eve.color':       'eve.name',
                'res_sh.color':    'res_sh.name',
                'eve_sh.color':    'eve_sh.name',
            }

            for row in t.rows():
                for clr_name, col_name in clr_names.items():
                    if clr_name in t.nf and col_name in t.nf:

                        clr:CMS.Color = row.value(clr_name,get_cust_content=True)
                        row.set_color_background(*clr.rgba, col_name=col_name)

        if name_gr == 'pivot_table':
            self.ui.tbl_gr_v_sub.setVisible(True)

            list_text_v_sub, list_data_v_sub, list_text, list_data,dict_aliases, dict_descr = CLSS.CrossManager.templates_pivot(list_crosses)
            #list_text, list_data = self.apply_user_config(name_gr, list_text,list_data)



            CQT.fill_wtabl(list_text_v_sub, self.ui.tbl_gr_v_sub, styleSheet=CQT.MES_EDIT_CSS, dict_or_list_user_data=list_data_v_sub,
                           aliases_header=dict_aliases, auto_type=True, sortingEnabled=True)
            t_sub = CQT.TableContext(self.ui.tbl_gr_v_sub)
            t_sub.hide_if_not_dev(CFG, True)

            for row in t_sub.rows():
                id_res = int(row.value('id'))
                res:CLSS.Resource = DTSUB.resources.get(id_res)
                clr: CMS.Color = res.color.value
                row.set_color_background(*clr.rgba, col_name='name')
                if 'shablon' in t_sub.nf:
                    sh_o = res.get_shablon()
                    clr = sh_o.color.value
                    row.set_color_background(*clr.rgba, col_name='shablon')


            self._fill_right_part_pivot_table(list_text,list_data,dict_aliases)

            t = CQT.TableContext(self.ui.tbl_gr)
            t.sync_vertical_scroll(t_sub)
            t_sub.set_vertical_scroll_visible(False)





    @CQT.onerror
    def fill_cmb_reports(self):
        template:list[CLSS.Report] = CLSS.Reports.template()
        CQT.fill_list_combobx(self,self.ui.cmb_type_gr,[_.text for _ in template],
                              list_tooltip=[_.descr for _ in template],
                              first_void=True,
                              list_data=[_.name for _ in template])
        self.ui.cmb_type_gr.setMaxVisibleItems(len(template)+1)


    def __________presets_settings__________(self):pass
    def report_preset(self):
        name_gr = CQT.get_cmb_current_data(self.ui.cmb_type_gr)
        if name_gr == 'table':
            list_crosses = CLSS.CrossManager.get_ordered_data(DTSUB.resources, DTSUB.events, DTSUB.crosses)

            list_text,list_data,dict_descr, dict_aliases = CLSS.CrossManager.templates(list_crosses)
            list_text, list_data = self.apply_user_config(name_gr, list_text, list_data,filter=False )

            ucfg: dict[str, CLSS.UserConfigSubPlanElement] = DTSUB.user_config_sub_plan.oform_reports[name_gr]
            template_settings = []
            aliases_settings = {'description':'Описание', 'alias':'Название', 'enabled':'Видимость'}
            for i, name in enumerate(list_text[0].keys()):
                alias = dict_aliases[name]
                if alias.startswith('_') or name.startswith('_'):
                    continue
                descr = dict_descr[name]
                enabled = True
                if name in ucfg:
                    enabled = ucfg[name].enable
                template_settings.append({'_name':name,'_order':i, 'alias':alias, 'enabled':enabled, 'description':descr})

            def fnc_switch(app_self, tbl: CQT.QtWidgets.QTableWidget, value: bool, i: int, j: int, *args):
                t = CQT.TableContext(tbl)
                row = t.get_row(i)
                row.set_value(t.name_by_idx(j), str(value))
            def fnc_drdr(tbl:CQT.QtWidgets.QTableWidget,i_row_old:int, i_row_new:int, *args):
                t = CQT.TableContext(tbl)
                row = t.get_row(i_row_new)
                CQT.add_check_box_switcher(t.tbl,row.i,t.nf['enabled'],F.boolm(row.value('enabled')),fnc_switch,self_obj=self)

            def fnc_oform_tbl(tbl:CQT.QtWidgets.QTableWidget,*args):
                t = CQT.TableContext(tbl)



                for row in t.rows():
                    CQT.add_check_box_switcher(t.tbl,row.i,t.nf['enabled'],F.boolm(row.value('enabled')),fnc_switch,self_obj=self)

            def fnc_ok(t: CQT.TableContext, *args) -> None:
                rez = []

                for row in t.rows():
                    name = row.value('_name')
                    enabled = F.boolm(row.value('enabled'))
                    new_order = row.i
                    rez.append({'name': name, 'enabled': enabled, 'new_order': new_order})
                return rez



            rez = CQT.msgboxg_get_table(self,'Настройки графика',template_settings,'Применить','Отмена',func_oform_tbl=fnc_oform_tbl,
                                  ExtendedSelection=False,selectRows=True,styleSheet=CQT.MES_CSS,aliases_header=aliases_settings,fnc_drag_drop=fnc_drdr,
                                        func_validate_t=fnc_ok
                                        )

            if not rez:
                return

            data =rez
            DTSUB.user_config_sub_plan.save_config(CLSS.Reports.get_by_name(name_gr), data)
            self.select_report()


    def _____________________________(self):pass
if __name__ == "__main__":
    from project_cust_38.Cust_application import install_crash_guard, SafeApplication
    app = SafeApplication(sys.argv)
    install_crash_guard(app, app_name='',user_name='', log_qt_warnings=False,log_qt_debug_info=False, enable_native_fault_handler=False)
    #CQT.ThemeManager.apply(app)
    sub_window = Plwindow(None,CLSS.SubjectsPl.rab_place)
    sub_window.showMaximized()
    sys.exit(app.exec())
