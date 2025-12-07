from __future__ import annotations
import base64
import copy

import dataClass
import main_classes as CLSS

from typing import  TYPE_CHECKING
from PyQt5 import QtWidgets
from project_cust_38 import Cust_config as CFG
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F

import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_tree_widget as CTREE
import project_cust_38.api_erp_commands as APIERP
from dataClass import data_app as DTCLS
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.Cust_odata_erp as ODAT


if TYPE_CHECKING:
    from constr_rc import mywindow



def ___________Support____________():
    pass
def init_guo_qt():
    DTCLS.gui_qt = CLSS.Gui_tb()

def sort_hierarchical(items):
    by_parent = {}
    for i in items:
        parent = i["Parent"]
        by_parent.setdefault(parent, []).append(i)

    # чтобы порядок был стабильным, можно отсортировать внутри каждого уровня по Code или Name
    for lst in by_parent.values():
        lst.sort(key=lambda x: x["Наименование"])
        lst.sort(key=lambda x: x["Тип"])

    result = []

    def walk(parent=None, level=0):
        for i in by_parent.get(parent, []):
            i["Level"] = level
            result.append(i)
            walk(i["Ref"], level + 1)

    walk('00000000-0000-0000-0000-000000000000')  # или '00000000-0000-0000-0000-000000000000', если так в базе
    return result

def compute_levels(items):
    # строим индекс по ссылкам
    by_ref = {i["Ref"]: i for i in items}
    def get_level(item):
        lvl = 0
        parent = item["Parent"]
        visited = set()
        while parent and parent in by_ref and parent not in visited:
            visited.add(parent)
            lvl += 1
            parent = by_ref[parent]["Parent"]
        return lvl

    for i in items:
        i["Level"] = get_level(i)
    return items

def toggle_select_struct(self:mywindow,val=False):
    self.ui.fr_add_erp.setEnabled(val)


def load_tree_add_res_cursor(self:mywindow,ref:str|None= None):
    if not ref:
        tree_add_res_data = CMS.load_tmp_stukt('tree_add_res')
        if tree_add_res_data:
            ref = tree_add_res_data['ref']
    if ref:
        tree:CTREE.ExtTreeWidget = self.ui.tree_add_res
        clmn_num = CQT.num_col_by_name_c(tree,'Ref')
        if clmn_num:
            cell = tree.get_item_cell_by_value(ref,clmn_num)
            if cell:
                cell.row_item.expand_parents()
def load_tree_add_dse_cursor(self:mywindow,ref:str|None= None):
    if not ref:
        tree_add_res_data = CMS.load_tmp_stukt('tree_add_dse')
        if tree_add_res_data:
            ref = tree_add_res_data['ref']
    if ref:
        tree:CTREE.ExtTreeWidget = self.ui.tree_add_dse
        clmn_num = CQT.num_col_by_name_c(tree,'Ref')
        if clmn_num:
            cell = tree.get_item_cell_by_value(ref,clmn_num)
            if cell:
                cell.row_item.expand_parents()


def find_fr_add_erp():
    ui = DTCLS.app_self.ui
    val = ui.le_fr_add_erp_filtr.text()
    tree = None
    if ui.tabw_add_erp.currentIndex() == CQT.number_table_by_name_c(ui.tabw_add_erp, 'ДСЕ'):
        tree:CTREE.ExtTreeWidget = ui.tree_add_dse
    if ui.tabw_add_erp.currentIndex() == CQT.number_table_by_name_c(ui.tabw_add_erp, 'Ресурсная'):
        tree:CTREE.ExtTreeWidget = ui.tree_add_res
    if tree is None:
        return

    elems = tree.get_item_cell_by_value(val,many=True,strict_compare=False)
    if not val or elems is None:
        items = None
    else:
        items = [cell.row_item for cell in elems]
    roots = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    for root_item in roots:
        hide_not_in_list(tree,root_item,items)


def hide_not_in_list(tree,root_item, allowed_items:list|None):
    """
    root_item: QTreeWidgetItem
    allowed_items: set[QTreeWidgetItem] или list[...] — лучше set для скорости
    """

    def recurse(tree,item):
        child_count = item.childCount()

        # сначала проверить детей
        any_visible_child = False
        for i in range(child_count):
            child = item.child(i)
            child_visible = recurse(tree,child)
            if child_visible:
                any_visible_child = True

        # логика скрытия
        if allowed_items is None:
            item.setHidden(False)
            return True

        if item in allowed_items or any_visible_child:
            item.setHidden(False)
            tree.expandItem(item)
            return True
        else:
            item.setHidden(True)
            return False

    recurse(tree, root_item)
def tbox_page_changed(self:mywindow, index):
    pg = DTCLS.gui_qt.get_page(index)
    if pg.name == 'pg_cards1c':
        clicked_btn_show_card_1c(self)
    pass
def clicked_cbtn_favour(self:mywindow):
    if self.ui.cbtn_favour.isChecked():
        CQT.msgbox(f'{CEMOJ.EmojiMain.ОборудованиеИнструменты.tool.symbol} В разработке...')
    else:
        CQT.msgbox(f'{CEMOJ.EmojiMain.ОборудованиеИнструменты.tool.symbol} В разработке...')

def clicked_btn_import_exel(self:mywindow):
    CQT.msgbox(f'{CEMOJ.EmojiMain.ОборудованиеИнструменты.tool.symbol} В разработке...')
def ___________saves_____________():
    pass

@CQT.onerror
def clicked_btn_save_tree(self:mywindow,*args):
    if not DTCLS.check_is_tree_accessed():
        return
    current_tree = DTCLS.current_process.tree_res
    current_tree.save('shift' not in CQT.get_key_modifiers(self))

@CQT.onerror
def clicked_btn_load_tree(self:mywindow):
    if not DTCLS.check_is_tree_accessed():
        return
    current_tree = DTCLS.current_process.tree_res
    current_tree.load('shift' not in CQT.get_key_modifiers(self))

@CQT.onerror
def clicked_btn_show_card_1c(self:mywindow):
    if not DTCLS.check_is_tree_accessed():
        return
    current_elem = DTCLS.current_elem
    if current_elem is None:
        return
    show_1c_card(self,current_elem.ref,current_elem.type_doc)



def ___________config_____________():
    pass


@CQT.onerror
def view_hidden_fields(self,*args):
    if CFG.User_config.is_developer:
        if self.ui.chk_view_hidden_fields.isChecked():
            DTCLS.view_hidden_fields = True
        else:
            DTCLS.view_hidden_fields = False
        CMS.save_tmp_stukt(DTCLS.view_hidden_fields, 'view_hidden_fields')
@CQT.onerror
def use_cache_params(self,*args):
    if self.ui.chk_use_cache_params.isChecked():
        DTCLS.use_cache_params = True
    else:
        DTCLS.use_cache_params = False
    CMS.save_tmp_stukt(DTCLS.use_cache_params, 'use_cache_params')


@CQT.onerror
def save_nomen_config(self,*args):
    val_chk_nomen_images = self.ui.chk_nomen_images.isChecked()
    val_chk_nomen_desc = self.ui.chk_nomen_desc.isChecked()
    val_chk_nomen_unit = self.ui.chk_nomen_unit.isChecked()
    val_chk_nomen_maker = self.ui.chk_nomen_maker.isChecked()
    val_chk_nomen_describe = self.ui.chk_nomen_describe.isChecked()
    val_chk_nomen_add_r = self.ui.chk_nomen_add_r.isChecked()
    CMS.save_tmp_stukt([val_chk_nomen_desc,val_chk_nomen_add_r,
                        val_chk_nomen_unit,val_chk_nomen_maker,val_chk_nomen_describe,val_chk_nomen_images],
                       'nomen_config')

@CQT.onerror
def load_nomen_config(self,*args):

    val_chk_nomen_desc= False
    val_chk_nomen_unit= False
    val_chk_nomen_maker= False
    val_chk_nomen_describe= False
    val_chk_nomen_add_r= False
    val_chk_nomen_images= False
    data = CMS.load_tmp_stukt('nomen_config')
    if data:
        val_chk_nomen_desc = data[0] if len(data)> 0 else False
        val_chk_nomen_add_r = data[1] if len(data)> 1 else False
        val_chk_nomen_unit = data[2] if len(data)> 2 else False
        val_chk_nomen_maker = data[3] if len(data)> 3 else False
        val_chk_nomen_describe = data[4] if len(data)> 4 else False
        val_chk_nomen_images = data[5] if len(data)> 5 else False


    self.ui.chk_nomen_desc.blockSignals(True)
    self.ui.chk_nomen_unit.blockSignals(True)
    self.ui.chk_nomen_maker.blockSignals(True)
    self.ui.chk_nomen_describe.blockSignals(True)
    self.ui.chk_nomen_add_r.blockSignals(True)
    self.ui.chk_nomen_images.blockSignals(True)

    self.ui.chk_nomen_desc.setChecked(val_chk_nomen_desc)
    self.ui.chk_nomen_unit.setChecked(val_chk_nomen_unit)
    self.ui.chk_nomen_maker.setChecked(val_chk_nomen_maker)
    self.ui.chk_nomen_describe.setChecked(val_chk_nomen_describe)
    self.ui.chk_nomen_add_r.setChecked(val_chk_nomen_add_r)
    self.ui.chk_nomen_images.setChecked(val_chk_nomen_images)

    self.ui.chk_nomen_desc.blockSignals(False)
    self.ui.chk_nomen_unit.blockSignals(False)
    self.ui.chk_nomen_maker.blockSignals(False)
    self.ui.chk_nomen_describe.blockSignals(False)
    self.ui.chk_nomen_add_r.blockSignals(False)
    self.ui.chk_nomen_images.blockSignals(False)


def ___________Orders_____________():
    pass
def load_list_folders(self:mywindow):
    orders = CLSS.OrdersDocs()
    orders.load_folders()
    cmb:QtWidgets.QComboBox = self.ui.cmb_list_folders_docs
    cmb.clear()
    cmb.addItem('', None)
    for item in orders.list_folders:
        cmb.addItem(item.name,item)

@CQT.onerror
def load_res_structure(self:mywindow):
    def oform(items):
        for i in items:
            if i['НаУдаление']:
                i['НаУдаление'] = CEMOJ.EmojiMain.Статусы.error.symbol
            else:
                i['НаУдаление'] = ''
            i['Тип'] = CEMOJ.EmojiMain.ДокументыДанные.folder.symbol
        return items

    text = f"""ВЫБРАТЬ
                "" КАК Тип,
                РесурсныеСпецификации.ПометкаУдаления КАК НаУдаление,
                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Ссылка)) КАК Ref,
                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Родитель)) КАК Parent,
                РесурсныеСпецификации.Код КАК Код,
                РесурсныеСпецификации.Наименование КАК Наименование
            ИЗ
                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
            ГДЕ
                РесурсныеСпецификации.ЭтоГруппа = ИСТИНА
                        """
    key, res = APIERP.get_wet_request(text=text,lazy_method_huours=24)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных из ЕРП')
        return
    if not res['data']:
        CQT.msgbox(f'Иерархия ресурсных-пусто')
        return
    list_res =  compute_levels(res['data'])
    list_res =  sort_hierarchical(list_res)
    DTCLS.res_stucture = oform(list_res)

    fill_tree_add_res(self)
    load_tree_add_res_cursor(self)



@CQT.onerror
def load_dse_structure(self:mywindow):
    def oform(items):
        for i in items:
            if i['НаУдаление']:
                i['НаУдаление'] = CEMOJ.EmojiMain.Статусы.error.symbol
            else:
                i['НаУдаление'] = ''
            if i['ЭтоГруппа']:
                i['Тип'] = CEMOJ.EmojiMain.ДокументыДанные.folder.symbol
            else:
                i['Тип'] = CEMOJ.EmojiMain.ДокументыДанные.document.symbol
        return items

    text = f"""ВЫБРАТЬ
            "" КАК Тип,
            ВидыНоменклатуры.ЭтоГруппа,
            ВидыНоменклатуры.ПометкаУдаления КАК НаУдаление,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Ссылка)) КАК Ref,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Родитель)) КАК Parent,
            ВидыНоменклатуры.Наименование КАК Наименование
        ИЗ
            Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                        """
    key, dse = APIERP.get_wet_request(text=text,lazy_method_huours=24)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных из ЕРП')
        return
    if not dse['data']:
        CQT.msgbox(f'Иерархия ресурсных-пусто')
        return
    list_dse =  compute_levels(dse['data'])
    list_dse =  oform(list_dse)
    list_dse =  sort_hierarchical(list_dse)
    DTCLS.dse_stucture = list_dse

    fill_tree_add_dse(self)
    load_tree_add_dse_cursor(self)

@CQT.onerror
def load_orders_form_rs(self:mywindow, *args):

    DTCLS.dict_orders_docs = None
    CQT.clear_tbl(DTCLS.app_self.ui.tbl_list_orders)
    if not DTCLS.current_folder_docs:
        return
    CLSS.Process.update_view(DTCLS.current_folder_docs.uuid)



def reload_list_projects(self:mywindow):
    load_orders_form_rs(self)


def ______Elems_actions_______________():
    pass


@CQT.onerror
def clear_rs(self:mywindow,*args):
    tbl = self.ui.tbl_list_orders
    s_num_docs = CQT.get_dict_line_form_tbl(tbl)['s_num_docs']
    order: CLSS.OrderDocs = DTCLS.dict_orders_docs[s_num_docs]
    process: CLSS.Process = order.get_process()
    process.clear_res()

@CQT.onerror
def check_rs(self:mywindow,*args):
    if DTCLS.current_process is None:
        return
    tree = DTCLS.current_process.tree_res
    root = tree.get_root()
    suc, errs = root.check_ready_for_1c_export()
    if not suc:
        CQT.msgboxg_get_table_ok_inf(self,f"Несоответствия",errs.list_errs,WindowTitle=str(DTCLS.current_process),
                                     style_icon="SP_MessageBoxWarning")
        return

    def fnc_oform(tbl:QtWidgets.QTableWidget):
        fn = CQT.nums_col_by_name_dict(tbl)
        tbl.setColumnWidth(fn['Наименование'],500)
        tbl.setColumnWidth(fn['Код'],120)
        tbl.setColumnWidth(fn['Несоответствия'],1000)
        tbl.setColumnHidden(fn['uid'],True)
        tbl.setColumnHidden(fn['Несоответствия'],True)



    @CQT.onerror
    def fnc_progress(btn:QtWidgets.QPushButton,dialog:CQT.Dialog_tbl,tbl:QtWidgets.QTableWidget):
        if btn.text() == 'Начать':

            fn = CQT.nums_col_by_name_dict(tbl)
            tree = DTCLS.current_process.tree_res
            DTCLS.tree_data_manager._toggle_tree_gui()
            fl_errs = False
            for i in range(tbl.rowCount()):#dse
                row = CQT.get_dict_line_form_tbl(tbl,i)
                uid = row['uid']
                row_data = tree.find_by_uid(uid)
                fl_make_osn_izd = False
                if row['Тип'] == CLSS.TypesDoc.osn_izd.user_name:
                    fl_make_osn_izd = True

                if (row_data.changed and row_data.type_doc == CLSS.TypesDoc.dse) or fl_make_osn_izd:
                    suc, result = row_data.make_doc_erp()
                    with CQT.table_updating(tbl):
                        if not suc:
                            fl_errs = True
                            tbl.item(i,fn['Результат']).setText(f'{CEMOJ.СтатусыПроизводства.alert.symbol}')
                            errs = result
                            if 'Ошибки' in result:
                                errs = result['Ошибки']
                            tbl.item(i,fn['Несоответствия']).setText('; '.join(errs))
                            tbl.setColumnHidden(fn['Несоответствия'], False)
                        else:
                            tbl.item(i,fn['Результат']).setText(f'{CEMOJ.СтатусыПроизводства.success.symbol}')
                            tbl.item(i,fn['Код']).setText(result["Код"])

            if fl_errs:
                DTCLS.tree_data_manager._toggle_tree_gui(False)
                return

            for row_data in tree.sorted_docs_by_level():
                if fl_errs:
                    break
                if row_data.changed and row_data.type_doc == CLSS.TypesDoc.res:
                    for i in range(tbl.rowCount()):
                        row = CQT.get_dict_line_form_tbl(tbl, i)
                        uid = row['uid']
                        if uid == row_data.uid and row['Тип'] == row_data.type_doc.user_name:
                            suc, result = row_data.make_doc_erp()
                            with CQT.table_updating(tbl):
                                if not suc:
                                    tbl.item(i, fn['Результат']).setText(f'{CEMOJ.СтатусыПроизводства.alert.symbol}')
                                    errs = result
                                    if 'Ошибки' in result:
                                        errs = result['Ошибки']
                                    tbl.item(i, fn['Несоответствия']).setText('; '.join(errs))
                                    tbl.setColumnHidden(fn['Несоответствия'], False)
                                    fl_errs = True
                                    break
                                else:
                                    tbl.item(i, fn['Результат']).setText(f'{CEMOJ.СтатусыПроизводства.success.symbol}')
                                    tbl.item(i, fn['Код']).setText(result["Код"])
                            break
            #dialog.accept()


            dialog.disabled_btn0()
            DTCLS.tree_data_manager._toggle_tree_gui(False)
            if fl_errs:
                return
            DTCLS.current_process.save_res()

        else:
            dialog.reject()


    list_activities = root.calc_plan_for_1c_export()
    if not list_activities:

        if not CQT.msgboxgYN(f'Ресурсная {DTCLS.current_process.tree_res} уже существует и корректна.\nПерезаписать ее в процесс {str(DTCLS.current_process)}?'):
            return
        DTCLS.current_process.save_res()
        return

    CQT.msgboxg_get_table(self, f"План обмена с 1С", list_activities,
                                     style_icon="SP_MessageBoxInformation",
                                     func_oform_tbl=fnc_oform,
                                     not_standart_close=True,
                                     yesNoMode = True,
                                    btn0_name='Начать',
                                    btn1_name='Выход',
                                    func_btn0 = fnc_progress,
                                     )

    return

@CQT.onerror
def clicked_btn_add_row(self:mywindow,*args):
    if DTCLS.current_process is None:
        return
    tree = DTCLS.current_process.tree_res
    data_row = tree.current_row()
    if data_row is None:
        CQT.msgbox(f'Не выбрана строка')
        return

    newRow = data_row.parent.insert_row_after(data_row.uid)
    DTCLS.current_process.tree_res.update_levels()
    newRow.set_parent_change(newRow.uid)
    newRow.gui_obj.expand_parents()
    treeNavigator_itemSelectionChanged(self)




@CQT.onerror
def clicked_btn_delete_row(self:mywindow):
    tree = DTCLS.current_process.tree_res
    if tree.count() < 2:
        return
    data_row = tree.current_row()
    if data_row is None:
        return
    if data_row.uid_parent == None:
        CQT.msgbox(f'Удалить корневой узел нельзя')
        return
    data_row.set_parent_change(data_row.uid)
    if not tree.delete_row(data_row.uid):
        CQT.msgbox(f'ошибка удаления')
        return
    DTCLS.current_process.tree_res.update_levels()
    DTCLS.current_process.tree_res.clearCurrentElem(DTCLS)


@CQT.onerror
def clicked_btn_clear_tree(self:mywindow):
    tree = DTCLS.current_process.tree_res
    tree.reset()
@CQT.onerror
def clicked_btn_clear_row(self:mywindow):
    tree = DTCLS.current_process.tree_res
    data_row = tree.current_row()
    if data_row is None:
        CQT.msgbox(f'Не выбрана строка')
        return
    data_row.clear()
    DTCLS.current_process.tree_res.update_levels()
    data_row.set_parent_change(data_row.uid)
    DTCLS.current_process.tree_res.clearCurrentElem(DTCLS)




@CQT.onerror
def clicked_btn_select(self:mywindow, selected):
    if not selected:
        DTCLS.gui_qt.toggle_select()
        return
    tbl = self.ui.tbl_select
    result = CQT.get_dict_line_form_tbl(tbl)
    if not result:
        return
    ref_result = result['Ref']
    obj_type = CQT.getCustData(tbl)
    tree = DTCLS.current_process.tree_res
    data_row = tree.current_row()
    if data_row is None:
        if tree.count() == 1:
            data_row = tree.get_root()

    if data_row is None:
        CQT.msgbox(f'Не выбрана строка в древе')
        DTCLS.gui_qt.toggle_select()
        return
    if DTCLS.current_elem is None:
        data_row.setCurrentElem(DTCLS)
    data_row.type_doc = obj_type # меняю данные

    data_row.ref = ref_result # меняю данные

    new_elems =  data_row.reload_erp()

    #if data_row.is_root():
    #    data_row.set_change()
    #    data_row.count= 1

    if new_elems:
        last_ins = new_elems[-1].gui_obj
        last_ins.expand_parents()
    DTCLS.gui_qt.toggle_select()

@CQT.onerror
def clicked_btn_add_obj(self:mywindow, obj_type:CLSS.TypeDoc):
    CQT.clear_tbl(self.ui.tbl_select)

    if DTCLS.current_process is None:
        return
    tree = DTCLS.current_process.tree_res
    data_row = tree.current_row()
    if data_row.type_doc != obj_type:
        return
    if obj_type == CLSS.TypesDoc.res:
        tree_ui = self.ui.tree_add_res
        row_obj:CTREE.ExtTreeWidgetItem = tree_ui.currentItem()
        if not row_obj:
            return
        row_data = row_obj.to_dict()
        ref = row_data['Ref']
        text = """
                    ВЫБРАТЬ
                РесурсныеСпецификации.ЭтоГруппа КАК Тип,
                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Ссылка)) КАК Ref,
                РесурсныеСпецификации.ПометкаУдаления КАК НаУдаление,
                РесурсныеСпецификации.Статус КАК Статус,
                РесурсныеСпецификации.Код КАК Код,
                РесурсныеСпецификации.Наименование КАК Наименование
            ИЗ
                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
            ГДЕ
                РесурсныеСпецификации.Родитель.Ссылка = &Ссылка И 
                РесурсныеСпецификации.ЭтоГруппа = ЛОЖЬ        """

        refs = APIERP.Refs_wet(text)
        ref_obj = APIERP.Ref_wet('Ссылка', obj_type.path_conf_1c, ref)

        refs.add_ref(ref_obj)
        key, res = APIERP.get_wet_request(text=text,refs=refs)
        if key != 200:
           CQT.msgbox(f'Ошибка получения данных из ЕРП')
           return
        if not res['data']:
           CQT.msgbox(f'{obj_type.user_name} для {row_data["Наименование"]} не найдены')
           return

    elif obj_type == CLSS.TypesDoc.dse:
        if data_row.is_root():
            CQT.msgbox(f'Для корневого узла нельзя назначить ДСЕ')
            return
        tree_ui = self.ui.tree_add_dse
        row_obj: CTREE.ExtTreeWidgetItem = tree_ui.currentItem()
        if not row_obj:
            return
        row_data = row_obj.to_dict()
        ref = row_data['Ref']
        res = CLSS.get_list_nomen(ref,obj_type,row_data['Наименование'])
    else:
        return

    list_data = res['data']
    list_data = CLSS.oform_НаУдаление(list_data)

    CQT.fill_wtabl(list_data,self.ui.tbl_select,selectionBehavior='SelectRows',styleSheet=CQT.ERP_CSS,parent_self=self,
                   sortingEnabled=True,selectionMode='SingleSelection')
    CLSS.fnc_oform_tbl_select_dse(self.ui.tbl_select)

    CMS.fill_filtr_c(self,self.ui.tbl_select_filtr,self.ui.tbl_select)

    CQT.setCustData(self.ui.tbl_select,obj_type)
    if self.ui.fr_select.isHidden():
        DTCLS.gui_qt.toggle_select()



def toggleMaximizeRestore(self, dock:QtWidgets.QDockWidget,btn:QtWidgets.QPushButton):
    screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
    if dock.geometry() == screen:
        if dock._normalGeometry:
            dock.setGeometry(dock._normalGeometry)
        btn.setText("⛶")  # смотри: у dock есть titleBar
        g = dock.geometry()
        g.moveTop(g.top() + 50)
        dock.setGeometry(g)
    else:
        dock._normalGeometry = dock.geometry()
        dock.setFloating(True)
        dock.setGeometry(screen)
        btn.setText("❐")
def restore_dock_to_splitter(dock, splitter, index=None):
    dock.setFloating(False)
    dock.setParent(None)

    if index is None:
        splitter.addWidget(dock)
    else:
        splitter.insertWidget(index, dock)

    dock.show()
def insert_dockW(self:mywindow, dock:QtWidgets.QDockWidget,btn:QtWidgets.QPushButton,ceil):

    if dock.isFloating():
        restore_dock_to_splitter(dock,ceil,0)
        btn.setText("📍")
    else:
        dock.setFloating(True)
        g = dock.geometry()
        g.moveTop(g.top() + 50)
        dock.setGeometry(g)
        btn.setText("📌")

@CQT.onerror
def fill_tree_add_res(self: mywindow,*args):

    tree = self.ui.tree_add_res
    tree.fill_table(
        DTCLS.res_stucture,
        min_row_height=26,
        hide_horizontal_header=False,
        min_col_width=80,
        stretch_last_column=True,
        nick_name_level='Level',
        odd_item_color='#ffffff',
        even_item_color='#f0f8ff',
        hover_indicator_color=(233, 233, 111),
        # branch_icon_if_can_close='./Mkarti/icons/1.ico',
        selected_item_color = '#D0D0D0',
        hover_item_color="#E6EEF5",
        on_header_resized = CQT.on_section_resized_tree

    )
    tree.header().blockSignals(True)
    tree.hideColumn(CQT.num_col_by_name_c(tree,'Ref'))
    tree.hideColumn(CQT.num_col_by_name_c(tree,'Parent'))
    tree.hideColumn(CQT.num_col_by_name_c(tree,'Level'))
    CQT.load_column_widths(self,tree,CMS.tmp_dir())
    CQT.FillHorizontalHeaderSort(tree)
    tree.header().blockSignals(False)
@CQT.onerror
def fill_tree_add_dse(self: mywindow,*args):

    tree = self.ui.tree_add_dse
    tree.fill_table(
        DTCLS.dse_stucture,
        min_row_height=26,
        hide_horizontal_header=False,
        min_col_width=80,
        stretch_last_column=True,
        nick_name_level='Level',
        odd_item_color='#ffffff',
        even_item_color='#f0f8ff',
        hover_indicator_color=(233, 233, 111),
        # branch_icon_if_can_close='./Mkarti/icons/1.ico',
        selected_item_color='#D0D0D0',
        hover_item_color="#E6EEF5",
        on_header_resized = CQT.on_section_resized_tree
    )
    tree.header().blockSignals(True)
    tree.hideColumn(CQT.num_col_by_name_c(tree,'Ref'))
    tree.hideColumn(CQT.num_col_by_name_c(tree,'Parent'))
    tree.hideColumn(CQT.num_col_by_name_c(tree,'Level'))
    tree.hideColumn(CQT.num_col_by_name_c(tree,'ЭтоГруппа'))
    CQT.load_column_widths(self, tree, CMS.tmp_dir())
    CQT.FillHorizontalHeaderSort(tree)
    tree.header().blockSignals(False)
@CQT.onerror
def tbl_current_elem_cellEntered(self: mywindow, i,j ):
    if CQT.is_table_updating(self.ui.tbl_current_elem):
        return
    item: QtWidgets.QTableWidgetItem = self.ui.tbl_current_elem.item(i,j)
    save_old_val(item)
@CQT.onerror
def tbl_cr_res_itemActivated(self: mywindow, item:QtWidgets.QTableWidgetItem):
    if CQT.is_table_updating(item.tableWidget()):
        return
    save_old_val(item)
@CQT.onerror
def tbl_current_elem_itemActivated(self: mywindow, item:QtWidgets.QTableWidgetItem):
    save_old_val(item)

@CQT.onerror
def save_old_val( item:QtWidgets.QTableWidgetItem):
    DTCLS._old_val_cell =  item.text() if item else None
@CQT.onerror
def tbl_cr_res_itemChanged(self: mywindow, item:QtWidgets.QTableWidgetItem,tbl:QtWidgets.QTableWidget):
    if CQT.is_table_updating(tbl):
        return

    if item is None:
        return

    i, j = item.row(), item.column()
    new_value = item.text()
    row = CQT.get_dict_line_form_tbl(tbl,i)
    column_name = CQT.name_col_by_num(tbl,j)
    name_field = row['name']
    current_doc = DTCLS.current_elem
    if current_doc is None:
        return
    def check_type():
        if tbl == DTCLS.app_self.ui.tbl_cr_dse:
            if name_field not in current_doc.cr_dse_data.body.SET_FREE_FIELDS:
                if column_name != 'ref_key':
                    return False
                if new_value != '' and not F.is_unique_identifier(new_value):
                    return False
        return True

    if not check_type():
        return


    def check_val(name,val):
        if tbl == DTCLS.app_self.ui.tbl_cr_dse:
            if getattr(current_doc._cr_dse_data.body, name_field, '__None') == '__None':
                return False
            return True
        if tbl == DTCLS.app_self.ui.tbl_cr_res:
            if (getattr(current_doc._cr_dse_data.body, name_field, '__None') == '__None' and
                    getattr(current_doc._cr_res_data.schema, name_field, '__None') == '__None'):
                return False
            if name == 'count':
                if DTCLS.current_elem.is_root() and val != 1:
                    return False
            return True
        return True
    if not check_val(name_field,new_value):
        with CQT.table_updating(tbl):
            item.setText(DTCLS._old_val_cell)
            return
    if tbl == DTCLS.app_self.ui.tbl_cr_dse:
        if new_value == '':
            exec(f'current_doc._cr_dse_data.body.{name_field} = None')
        else:
            exec(f'current_doc._cr_dse_data.body.{name_field} = "{new_value}"')
        current_doc.cr_dse_data.body.save_attr_cache(name_field)
    if tbl == DTCLS.app_self.ui.tbl_cr_res:
        if getattr(current_doc._cr_res_data.schema,name_field,'__None') != '__None':
            exec(f'current_doc._cr_res_data.schema.{name_field} = "{new_value}"')
            current_doc._cr_res_data.schema.save_attr_cache(name_field)
        if getattr(current_doc._cr_dse_data.body,name_field,'__None') != '__None':
            exec(f'current_doc._cr_dse_data.body.{name_field} = "{new_value}"')
            current_doc._cr_res_data.schema.save_attr_cache(name_field)

@CQT.onerror
def tbl_cr_etaps_res_itemChanged(self: mywindow, item:QtWidgets.QTableWidgetItem,tbl:QtWidgets.QTableWidget):
    if CQT.is_table_updating(tbl):
        return

    if item is None:
        return

    i, j = item.row(), item.column()
    new_value = item.text()

    row = CQT.get_dict_line_form_tbl(tbl,i)
    name_field = tbl.horizontalHeaderItem(j).text()
    s_num_etap = row['Код']
    def check(name,val):
        if name == 'count':
            if DTCLS.current_elem.is_root() and val != 1:
                return False
        return True

    if not check(name_field,new_value):
        with CQT.table_updating(tbl):
            item.setText(DTCLS._old_val_cell)
            return
    else:
        if name_field == 'Минут':
            DTCLS.current_elem._cr_res_data.body.set_minutes(int(s_num_etap), F.valm(new_value))

@CQT.onerror
def tbl_current_elem_itemChanged(self: mywindow, item:QtWidgets.QTableWidgetItem):
    if CQT.is_table_updating(self.ui.tbl_current_elem):
        return

    if item is None:
        return

    i, j = item.row(), item.column()
    new_value = item.text()
    tbl = self.ui.tbl_current_elem
    row = CQT.get_dict_line_form_tbl(tbl,i)
    current_doc = DTCLS.current_elem
    if current_doc is None:
        return
    name_field = row['name']
    def check(name,val):
        if name == 'count':
            if DTCLS.current_elem.is_root() and val != 1:
                return False
        if name == 'name':
            if current_doc.is_nomen_name_exists_erp(new_value):
                CQT.msgbox(f'{current_doc.type_doc.user_name} с таким названием уже существует в 1С')
                return False
        return True

    if not check(name_field,new_value):
        with CQT.table_updating(tbl):
            item.setText(DTCLS._old_val_cell)
            return
    else:
        exec(f'current_doc.{name_field} = "{new_value}"')

    if name_field in current_doc.ATTRS_FOR_CHANGED_PARENT:
        current_doc.set_parent_change(current_doc.uid)

    if current_doc.type_doc != CLSS.TypesDoc.trd and name_field in current_doc.ATTRS_FOR_CHANGED_ITEM :
        current_doc.set_change()

    DTCLS._old_val_cell = None
@CQT.onerror
def tbl_cr_res_cellEntered(self: mywindow, i,j,tbl:QtWidgets.QTableWidget ):

    if CQT.is_table_updating(tbl):
        return
    item: QtWidgets.QTableWidgetItem = tbl.item(i,j)
    save_old_val(item)
@CQT.onerror
def tbl_select_itemSelectionChanged(self: mywindow):
    tbl = self.ui.tbl_select
    if self.ui.fr_select.isHidden():
        return
    row = CQT.get_dict_line_form_tbl(tbl)
    ref = row['Ref']
    obj_type = CQT.getCustData(self.ui.tbl_select)
    show_1c_card(self,ref,obj_type)
    DTCLS.gui_qt.select_import()
@CQT.onerror
def show_1c_card(self: mywindow,ref:str,obj_type:CLSS.TypeDoc):
    if not F.is_unique_identifier(ref):
        return
    tbl_card = self.ui.tbl_card_nomen
    CQT.clear_tbl(tbl_card)
    if obj_type == CLSS.TypesDoc.dse:
        click_row_mat(self,ref,tbl_card)
    if obj_type == CLSS.TypesDoc.res:
        click_row_res(self,ref,tbl_card)


@CQT.onerror
def tbl_list_orders_itemSelectionChanged(self: mywindow):

    def init_from_blob(tree:CLSS.TreeRes, res_blob:bytearray):
        tree_data = F.from_binary_pickle(res_blob)
        manger = CLSS.TreeDataManager(tree)
        proc_obj = DTCLS.current_process
        proc_obj.tree_res = manger._parse_tree_from_data(tree_data)
        proc_obj.tree_res.tree_gui = DTCLS.treeNavigator
        proc_obj.tree_res.fill_gui()
        proc_obj.tree_res.united_gui()
        manger._gen_objs(proc_obj.tree_res, tree_data['needs'])

    tbl = self.ui.tbl_list_orders

    row = CQT.get_dict_line_form_tbl(tbl)
    proc_obj = CLSS.Process(row['s_num_docs'])
    proc_obj.setCurrentProcess(DTCLS)
    tree_data = None

    DTCLS.treeNavigator.clear_table()

    proc_obj.tree_res = CLSS.TreeRes(DTCLS.treeNavigator, tree_data)
    if proc_obj.res_blob:
        init_from_blob(proc_obj.tree_res,proc_obj.res_blob)
    else:
        treeNavigator_itemSelectionChanged(self)
    toggle_select_struct(self,True)


@CQT.onerror
def tbl_list_orders_simulate(self: mywindow):
    tree_res = CLSS.TreeRes(DTCLS.treeNavigator)
    toggle_select_struct(self,True)



def cmb_list_folders_docs_activated(self: mywindow):
    cmb: QtWidgets.QComboBox = self.ui.cmb_list_folders_docs
    current_folder = cmb.currentData()
    DTCLS.current_folder_docs = current_folder
    if DTCLS.current_process and DTCLS.current_process.tree_res:
        DTCLS.current_process.tree_res.clear()
    load_orders_form_rs(self)
    toggle_select_struct(self)

@CQT.onerror
def treeNavigator_doubleClicked(self: mywindow,*args):
    pass
    data_row:CLSS.TreeDoc = DTCLS.treeNavigator.currentItem().temp_data
    tree:CTREE.ExtTreeWidget
    if data_row.type_doc == CLSS.TypesDoc.dse:
        self.ui.tabw_add_erp.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabw_add_erp,'ДСЕ'))
        tree = self.ui.tree_add_dse
    elif data_row.type_doc == CLSS.TypesDoc.res:
        self.ui.tabw_add_erp.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabw_add_erp,'Ресурсная'))
        tree = self.ui.tree_add_res
    else:
        return
    if data_row.ref_struct_parent == None:
        return
    item_struct_cell:CTREE.ExtTreeWidgetCell = tree.get_item_cell_by_value(data_row.ref_struct_parent,
                                                                           CQT.num_col_by_name_c(tree, 'Ref'))
    item_struct_parent = item_struct_cell.row_item
    item_struct_parent.expand_parents()



@CQT.onerror
def treeNavigator_itemSelectionChanged(self: mywindow,*args):
    def fnc_clear_code(self:CQT.InteractiveLabelInstance, parent_self, row, column, cell_val:CLSS.TreeDoc):
        data_row.set_change()
        CQT.delete_cellWidget(tbl_context,row,column)
        with CQT.table_updating(tbl_context):
            tbl_context.item(row,column).setText('')
        cell_val.recalc_filled_bodyHat_erp_export()
        
    def fnc_select_type(self, data, row, col):
        data_row.type_doc = data
        treeNavigator_itemSelectionChanged(self)

    tree = DTCLS.current_process.tree_res
    if tree is None or not tree.tree_rows:
        return
    data_row = tree.current_row()
    if data_row is None:
        return


    with CQT.table_updating(self.ui.tbl_current_elem) as tbl_context:
        self.ui.tbl_current_elem.updatesEnabled()
        tbl_context.property('_updating_table')
        data_row.setCurrentElem(DTCLS)
        DTCLS.gui_qt.select_elem()

        self.ui.fr_chk_nomen.setHidden(True)

        dict_obj = data_row.get_vert_dict()
        CQT.fill_wtabl(dict_obj, tbl_context, height_row=24, ogr_maxshir_kol=200, selectionBehavior='SelectRows',
                       count_rows_cell_max=-1, load_links=True, styleSheet='',set_editeble_col_nomera={},)

        num_field_val = CQT.num_col_by_name_c(tbl_context, 'Значение')
        num_field_name = CQT.num_col_by_name_c(tbl_context,'name')



        for row in range(tbl_context.rowCount()):

            field_name = tbl_context.item(row,num_field_name).text()
            field_val = tbl_context.item(row,num_field_val).text()
            if field_name not in data_row.EDITABLE_VIEW_ATTRS:
                CQT.set_cell_editable(tbl_context, row, num_field_val, False)
                CQT.set_font_color_wtab_c(tbl_context, row, num_field_val, 114, 114, 114)
            else:
                if data_row.is_root() and field_name in data_row.ROOT_NON_EDITABLE_VIEW_ATTRS:
                    CQT.set_cell_editable(tbl_context, row, num_field_val, False)
                    CQT.set_font_color_wtab_c(tbl_context, row, num_field_val, 114, 114, 114)

                CQT.set_cell_editable(tbl_context, row, num_field_val, True)
                CQT.set_font_color_wtab_c(tbl_context, row, num_field_val, 1, 1, 1)
            if field_name == 'type_doc' and data_row.type_doc == CLSS.TypesDoc.none:

                list_types = CLSS.TypesDoc.list_types()
                if data_row.is_root():
                    list_types.remove(CLSS.TypesDoc.dse)
                combo_type: QtWidgets.QComboBox = CQT.add_combobox(self, tbl_context, row, num_field_val,
                                 {str(_):_ for _ in list_types},
                                 list_tooltips=[_.user_name for _ in list_types],
                                 conn_func=fnc_select_type,
                                 first_void=False,list_data=list_types,return_data=True)


            if field_name == 'code' and data_row._code.code and data_row.type_doc != CLSS.TypesDoc.trd:
                widg = CQT.add_interactive_label(tbl_context, row, num_field_val, field_val, parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.error.symbol, 'Очистить', on_clicked=fnc_clear_code,
                                cell_val=data_row)

            def fnc_select_vid_rab(lblself:CQT.InteractiveLabelInstance, parent_self, row, column, cell_val):

                def fnc_oform_tbl(tbl,parent_self,*args):
                    pass
                list_vid_rab = [
                    {'Вид работ':_['Вид_работ'],'Стоимость мин.':_['Руб_мин'],'Ref':_['ref_Key_erp']}
                    for _ in DTCLS.LIST_VID_RAB if _['DeletionMark'] == 0]
                result = CQT.msgboxg_get_table(self, f'Выбор вида работ', list_vid_rab , "Выбор",
                                               styleSheet=CQT.ERP_CSS, ExtendedSelection=False,
                                               selectRows=True, selection_from_tbl=True, func_oform_tbl=fnc_oform_tbl,
                                               parent_self=DTCLS.app_self)
                if result:
                    tbl_context.item(row, column).setText(result['Вид работ'])
                    lblself.set_text(result['Вид работ'])
                    data_row.ref = result['Ref']
                    data_row.code  = CLSS.Code(data_row,code=result['Вид работ'],is_exists_doc=True)
                    treeNavigator_itemSelectionChanged(DTCLS.app_self)
            if field_name == 'name' and data_row.type_doc == CLSS.TypesDoc.trd:
                widg = CQT.add_interactive_label(tbl_context, row, num_field_val, field_val, parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать', on_clicked=fnc_select_vid_rab,
                                cell_val=data_row, img_path=  F.sep().join([F.path_to_execut_file_c(),
                                                                              'icons','btn_select']) )



            def fnc_select_etap(lblself:CQT.InteractiveLabelInstance, parent_self, row, column, cell_val):

                def fnc_oform_tbl(tbl,parent_self,*args):
                    pass
                list_еtaps = [
                    {'Номер':_['s_num'],'Имя':_['name']}
                    for _ in DTCLS.LIST_ETAPS if _['ДляЕРП'] == 1]
                result = CQT.msgboxg_get_table(self, f'Выбор этапа', list_еtaps , "Выбор",
                                               styleSheet=CQT.ERP_CSS, ExtendedSelection=False,
                                               selectRows=True, selection_from_tbl=True, func_oform_tbl=fnc_oform_tbl,
                                               parent_self=DTCLS.app_self)
                if result:
                    with CQT.table_updating(self.ui.tbl_current_elem) as tbl:
                        data_row.belongs_to_etap  = CLSS.EtapTreeDoc(int(result['Номер']),data_row)
                        tbl.item(row, column).setText(str(data_row.belongs_to_etap))
                        lblself.set_text(str(data_row.belongs_to_etap))
                    treeNavigator_itemSelectionChanged(DTCLS.app_self)

            if field_name == 'belongs_to_etap' and not data_row.is_root() and data_row.type_doc != CLSS.TypesDoc.none :
                widg = CQT.add_interactive_label(tbl_context, row, num_field_val, field_val, parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать', on_clicked=fnc_select_etap,
                                cell_val=data_row, img_path=  F.sep().join([F.path_to_execut_file_c(),
                                                                              'icons','btn_select']) )


        if data_row is not None:
            DTCLS.current_elem.fill_tables_dse_res()

        if not DTCLS.view_hidden_fields:
            if num_field_name is not None:
                tbl_context.setColumnHidden(num_field_name, True)
            for row in range(tbl_context.rowCount()):
                if tbl_context.item(row, num_field_name).text() in tree.HIDDEN_FIELDS:
                    tbl_context.setRowHidden(row, True)


    CQT.load_column_widths(self, tbl_context, CMS.tmp_dir())

@CQT.onerror
def tree_add_res_itemSelectionChanged(self: mywindow,*args):
    tree:CTREE.ExtTreeWidget = self.ui.tree_add_res
    row = tree.currentItem()
    if row is None:
        return
    data = row.to_dict()
    CMS.save_tmp_stukt({'ref':data['Ref']},'tree_add_res')


@CQT.onerror
def tree_add_dse_itemSelectionChanged(self: mywindow,*args):
    tree: CTREE.ExtTreeWidget = self.ui.tree_add_dse
    row = tree.currentItem()
    if row is None:
        return
    data = row.to_dict()
    CMS.save_tmp_stukt({'ref': data['Ref']}, 'tree_add_dse')


@CQT.onerror
def click_row_res(self: mywindow,Ref_Key,tbl_dse_erp_view):

    if not F.is_unique_identifier(Ref_Key):
        return

    res_obj = CLSS.Erp_res(Ref_Key)
    tch = res_obj.get_tch_mat()
    trdz = res_obj.get_tch_trdz()


    text = """
        ВЫБРАТЬ
            РесурсныеСпецификации.Наименование КАК Наименование,
            РесурсныеСпецификации.Код КАК Код,
            РесурсныеСпецификации.Статус КАК Статус,
                РесурсныеСпецификации.ОсновноеИзделиеНоменклатура КАК ОсновноеИзделиеНоменклатура,
            РесурсныеСпецификации.Описание КАК Описание
        
        ИЗ
            Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
        ГДЕ
            РесурсныеСпецификации.Ссылка = &Ссылка
                        """
    obj_type = CLSS.TypesDoc.res
    refs = APIERP.Refs_wet(text)
    ref_obj = APIERP.Ref_wet('Ссылка', obj_type.path_parent_conf_1c, Ref_Key)

    refs.add_ref(ref_obj)
    key, res = APIERP.get_wet_request(text=text, refs=refs)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных из ЕРП')
        return
    if not res['data']:
        CQT.msgbox(f'{obj_type.user_name} не найдены')
        return
    DICT_ALIASES = {
        'ОсновноеИзделиеНоменклатура':'Осн.Изд.',

    }
    dict_res = res['data']
    filter_resp = []
    for k, val in dict_res[0].items():
        if isinstance(val,bool):
            if val:
                val = 'Да'
            else:
                val = 'Нет'
        if k in DICT_ALIASES:
            k = DICT_ALIASES[k]
        filter_resp.append({'Параметр': k, 'Значение': val})

    for row in tch:
        type_obj = CLSS.TypesDoc.calc_type_by_tch(row['СпособПолучения'])
        row['Тип'] = type_obj.emo.symbol
    for row in trdz:
        type_obj = CLSS.TypesDoc.trd
        row['Тип'] = type_obj.emo.symbol

    filter_resp.append({'Параметр': 'Материалы', 'Значение': tch})
    filter_resp.append({'Параметр': 'Трудозатраты', 'Значение': trdz})

    tbl_dse_erp_view.setStyleSheet(CQT.ERP_CSS)
    with CQT.table_updating(tbl_dse_erp_view):
        # main_data = F.sort_by_column_c(filter_resp, 'Параметр')
        CQT.fill_wtabl(filter_resp, tbl_dse_erp_view, height_row=24, ogr_maxshir_kol=500, selectionBehavior='SelectRows',
                       count_rows_cell_max=-1, load_links=True)
        for i, val in enumerate(filter_resp):
            if val['Значение'] == '<не указано>':
                CQT.font_cell_size_format(tbl_dse_erp_view, i, 1, italic=True, size=8)


@CQT.onerror
def click_row_mat(self: mywindow,Ref_Key,tbl_dse_erp_view):
    if not F.is_unique_identifier(Ref_Key):
        return
    self.ui.fr_chk_nomen.setHidden(False)
    val_chk_nomen_images = self.ui.chk_nomen_images.isChecked()
    val_chk_nomen_desc = self.ui.chk_nomen_desc.isChecked()
    val_chk_nomen_unit = self.ui.chk_nomen_unit.isChecked()
    val_chk_nomen_maker = self.ui.chk_nomen_maker.isChecked()
    val_chk_nomen_describe = self.ui.chk_nomen_describe.isChecked()
    val_chk_nomen_add_r = self.ui.chk_nomen_add_r.isChecked()

    options = {
        'load_nomen_images': val_chk_nomen_images,
        'load_nomen_desc': val_chk_nomen_desc,
        'load_nomen_describe': val_chk_nomen_describe,
        'load_nomen_add_r': val_chk_nomen_add_r,
        'load_nomen_maker': val_chk_nomen_maker,
        'load_nomen_unit': val_chk_nomen_unit,
    }
    headers = {
         '':'load_nomen_desc',
         'Описание:':'load_nomen_describe',
         'Дополнительные реквизиты:':'load_nomen_add_r',
         'Сведения о производителе:':'load_nomen_maker',
         'Единицы измерения и условия хранения:':'load_nomen_unit',
    }
    requisites = {
        'load_nomen_desc': ['Description',
                   'НаименованиеПолное', 'Артикул', 'Code','ВидНоменклатуры_Key'],
        'load_nomen_describe': ['ФайлКартинки_Key', 'Описание', 'ФайлОписанияДляСайта_Key',
                   'ВестиУчетСертификатовНоменклатуры'],
        'load_nomen_add_r': ['ДополнительныеРеквизиты'],
        'load_nomen_maker': ['ПроизводительИмпортерКонтрагент_Key', 'Производитель_Key', 'Марка_Key', 'СтранаПроисхождения_Key',],
        'load_nomen_unit': ['ИспользоватьУпаковки', 'ЕдиницаИзмерения_Key', 'ЕдиницаДляОтчетов_Key',
                    'ВесЗнаменатель','ВесЧислитель','ВесЕдиницаИзмерения_Key',
                    'ОбъемЗнаменатель','ОбъемЧислитель', 'ОбъемЕдиницаИзмерения_Key',
                    'ДлинаЗнаменатель', 'ДлинаЧислитель', 'ДлинаЕдиницаИзмерения_Key',
                    'ПлощадьЗнаменатель', 'ПлощадьЧислитель', 'ПлощадьЕдиницаИзмерения_Key',
                    'СкладскаяГруппа_Key', 'ВесИспользовать', 'ОбъемИспользовать', 'ДлинаИспользовать', 'ПлощадьИспользовать'],
    }



    DICT_REPLACE_NAMES = {
        'Description':"Рабочее наименование:",
        'НаименованиеПолное': "Наименование для печати:",
        'Артикул': "Артикул:",
        'Code': "Код:",
        'ВидНоменклатуры_Key': "Вид номенклатуры:",

        'Описание:':'Описание:',
        'ФайлКартинки_Key': "Изображение",
        'Описание': "Текстовое описание",
        'ФайлОписанияДляСайта_Key': 'Файл описания для сайта',
        "ВестиУчетСертификатовНоменклатуры": "Учет сертификатов номенклатуры",

        'Дополнительные реквизиты:':'Дополнительные реквизиты:',


    }
    DICT_REPLACE_NAMES_add_1 = {

        'Сведения о производителе:': 'Сведения о производителе:',
        'ПроизводительИмпортерКонтрагент_Key': 'Производитель, импортер (контрагент)',
        'Производитель_Key': 'Производитель (бренд)',
        'Марка_Key': 'Марка (бренд)',
        'СтранаПроисхождения_Key': 'Страна происхождения',

        'Единицы измерения и условия хранения:': 'Единицы измерения и условия хранения:',
        'ИспользоватьУпаковки': 'Упаковки',#Булево
        'ЕдиницаИзмерения_Key': 'Единица хранения',#СправочникСсылка.УпаковкиЕдиницыИзмерения
        'ЕдиницаДляОтчетов_Key': 'Единица для отчетов',#СправочникСсылка.УпаковкиЕдиницыИзмерения
        'Вес': 'Вес',#расчетный
        'Объем': 'Объем',#расчетный
        'Длина': 'Длина',#расчетный
        'Площадь': 'Площадь',#расчетный
        'СкладскаяГруппа_Key': 'Складская группа',#СправочникСсылка.СкладскиеГруппыНоменклатуры

    }

    #Номенклатура - модуль менеджера - 1359

    fields = []
    for k,v in requisites.items():
        if k in options:
            if options[k]:
                fields.append(', '.join(v))
    fields = ', '.join(fields)
    if fields == '':
        return


    m = ODAT.OrdersComposit(CFG.Config.user_config.ERP_base_name['Значение'])
    code, resp_general = m.get_response(doc_name='Catalog_Номенклатура',
                  wet_filtr=f"""?$filter= Ref_Key eq guid'{Ref_Key}'&$select= 
                  Ref_Key, {fields} 
                    """,with_cod=True,timeout=20)
    if code != 200:
        CQT.msgbox(f'Ошибка загрузки данных из ЕРП')
        return

    resp_general = resp_general[0]

    def is_key_description_load(key_desc:str):
        for k,v in DICT_REPLACE_NAMES.items():
            if v == key_desc:
                for kr, vr in requisites.items():
                    if k in vr:
                        if options[kr]:
                            return True
                        else:
                            return False
        return False

    DICT_DESCRIPTIONS = {
        'Производитель, импортер (контрагент)': 'Catalog_Контрагенты',
        'ВидНоменклатуры': 'Catalog_ВидыНоменклатуры',
        'Производитель (бренд)': 'Catalog_Производители',
        'Марка (бренд)': 'Catalog_Марки',
        'Страна происхождения': 'Catalog_СтраныМира',
        'Единица хранения': 'Catalog_УпаковкиЕдиницыИзмерения',
        'Единица для отчетов': 'Catalog_УпаковкиЕдиницыИзмерения',
        'Складская группа': 'Catalog_СкладскиеГруппыНоменклатуры',
    }
    
    DICT_DESCRIPTIONS_WET_REQ = {
        'Производитель, импортер (контрагент)': 'Контрагенты',
        "Вид номенклатуры:": 'ВидыНоменклатуры',
        'Производитель (бренд)': 'Производители',
        'Марка (бренд)': 'Марки',
        'Страна происхождения': 'СтраныМира',
        'Единица хранения': 'УпаковкиЕдиницыИзмерения',
        'Единица для отчетов': 'УпаковкиЕдиницыИзмерения',
        'Складская группа': 'СкладскиеГруппыНоменклатуры',
    }
    
    if options['load_nomen_unit']:
        if resp_general['ВесИспользовать']:
            DICT_DESCRIPTIONS['ВесЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'
        if resp_general['ОбъемИспользовать']:
            DICT_DESCRIPTIONS['ОбъемЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'
        if resp_general['ДлинаИспользовать']:
            DICT_DESCRIPTIONS['ДлинаЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'
        if resp_general['ПлощадьИспользовать']:
            DICT_DESCRIPTIONS['ПлощадьЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'


    if options['load_nomen_add_r']:
        for dop in resp_general['ДополнительныеРеквизиты']:
            dop_name = m.get_response(doc_name='ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения',
                           wet_filtr=f"""?$filter= Ref_Key eq guid'{dop['Свойство_Key']}'
                           &$select= Description""",timeout=20)
            dop_val = m.get_response(doc_name='Catalog_ЗначенияСвойствОбъектов',
                                  wet_filtr=f"""?$filter= Ref_Key eq guid'{dop['Значение']}'
                                  &$select= Description""",timeout=20)
            if dop_name and dop_val:
                dop_name = dop_name[0]['Description']
                dop_val = dop_val[0]['Description']
                DICT_REPLACE_NAMES[dop_name] = dop_name
                resp_general[dop_name] = dop_val

    for k,v in DICT_REPLACE_NAMES_add_1.items():
        DICT_REPLACE_NAMES[k] = v

    ref_key_nomen = resp_general['Ref_Key']
    for name , psd in DICT_REPLACE_NAMES.items():
        if name in resp_general and name != psd:
            resp_general[psd] = resp_general[name]
            resp_general.pop(name,None)

    def get_file(row_add_file:dict):
        типХраненияФайла = row_add_file['ТипХраненияФайла']
        if типХраненияФайла == 'ВТомахНаДиске':
            том_Key = row_add_file['Том_Key']
            img_data = m.get_response(doc_name='Catalog_ТомаХраненияФайлов',
                                      wet_filtr=f"""?$filter= Ref_Key eq guid'{том_Key}'
                                      &$select= ПолныйПутьWindows""",timeout=20)
            ПолныйПутьWindows = img_data[0]['ПолныйПутьWindows'] + row_add_file['ПутьКФайлу']

            code, dict_file = APIERP.get_file(ПолныйПутьWindows)
            if code != 200:
                return

            file_data = dict_file[0][ПолныйПутьWindows]
        else:
            ПолныйПутьWindows =  row_add_file['Том_Key']
            img_b64 = row_add_file['ТекстХранилище_Base64Data']
            file_data = base64.decodebytes(str.encode(img_b64))

        ext = F.keep_extention_c(ПолныйПутьWindows)
        tmp_win_dir = F.save_tmp_win_dir_file(file_data, extention=ext)
        return tmp_win_dir
    if options['load_nomen_describe']:
        img = '<не указано>'
        if resp_general['Изображение'] != ODAT.EMPTY_KEY:
            img = CEMOJ.EmojiMain.ДокументыДанные.database
            if options['load_nomen_images']:
                img_data = m.get_response(doc_name='Catalog_НоменклатураПрисоединенныеФайлы',
                          wet_filtr=f"""?$filter= Ref_Key eq guid'{resp_general['Изображение']}'
                          &$select= ТипХраненияФайла,Том_Key,ПутьКФайлу""",timeout=20)#resp['Изображение']
                img = get_file(img_data[0])
        resp_general['Изображение'] = img

        files = []
        if options['load_nomen_images']:
            add_files =  m.get_response(doc_name='Catalog_НоменклатураПрисоединенныеФайлы',
                          wet_filtr=f"""?$filter=ВладелецФайла_Key eq guid'{ref_key_nomen}'
                          &$select=ТипХраненияФайла,Том_Key,ПутьКФайлу""",timeout=20)
            for row in add_files:
                files.append(get_file(row))
        resp_general["Файлы"] = ';'.join(files) #f'Файлы ({len(files)})'

        file = '<не указано>'
        if resp_general['Файл описания для сайта'] != ODAT.EMPTY_KEY:
            if options['load_nomen_images']:
                file_data = m.get_response(doc_name='Catalog_НоменклатураПрисоединенныеФайлы',
                          wet_filtr=f"""?$filter= Ref_Key eq guid'{resp_general['Файл описания для сайта']}'
                          &$select= ТипХраненияФайла,Том_Key,ПутьКФайлу""",timeout=20)
                file = get_file(file_data[0])
        resp_general['Файл описания для сайта'] = file
    DICT_ADDIT_PARAMS = {
        'ВидыНоменклатуры': 'Родитель'
    }

    for k,v in DICT_DESCRIPTIONS_WET_REQ.items():
        if not is_key_description_load(k):
            continue
        default_val = '<не указано>'
        if resp_general[k] != ODAT.EMPTY_KEY:
            postfix = ''
            add_name = None
            if v in DICT_ADDIT_PARAMS:
                add_name = DICT_ADDIT_PARAMS[v]
                postfix = f', {v}.{add_name} КАК {add_name}'
            text = f"""ВЫБРАТЬ
                            {v}.Наименование КАК Наименование{postfix}
                        ИЗ
                            Справочник.{v} КАК {v}
                        ГДЕ
                            {v}.Ссылка = &Ссылка"""
            refs = APIERP.Refs_wet(text)
            ref_obj = APIERP.Ref_wet('Ссылка', f'Справочники.{v}', resp_general[k])

            refs.add_ref(ref_obj)
            key, res = APIERP.get_wet_request(text=text, refs=refs)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')

            if not res['data']:
                CQT.msgbox(f'{v}-пусто')
                continue
            resp_data = res['data']

            if resp_data:
                default_val = f"{resp_data[0]['Наименование']}"
            if add_name:
                default_val = f'{default_val}({(resp_data[0][add_name])})'
        resp_general[k] = default_val
    if options['load_nomen_unit']:
        #============calc weight, val, lenght, area===============

        resp_general['Вес'] = '<не указано>'
        resp_general['Объем'] = '<не указано>'
        resp_general['Длина'] = '<не указано>'
        resp_general['Площадь'] = '<не указано>'

        ЕдиницаИзмерения = resp_general['Единица хранения']

        if resp_general['ВесИспользовать']:
            ВесЗнаменатель = resp_general['ВесЗнаменатель']
            ВесЧислитель = resp_general['ВесЧислитель']
            ВесЕдиницаИзмерения = resp_general['ВесЕдиницаИзмерения_Key']
            resp_general['Вес'] = f'{ВесЗнаменатель} {ЕдиницаИзмерения} весит {ВесЧислитель} {ВесЕдиницаИзмерения}'

        if resp_general['ОбъемИспользовать']:
            ОбъемЗнаменатель = resp_general['ОбъемЗнаменатель']
            ОбъемЧислитель = resp_general['ОбъемЧислитель']
            ОбъемЕдиницаИзмерения = resp_general['ОбъемЕдиницаИзмерения_Key']
            resp_general['Объем'] = f'{ОбъемЗнаменатель} {ЕдиницаИзмерения} весит {ОбъемЧислитель} {ОбъемЕдиницаИзмерения}'
        if resp_general['ДлинаИспользовать']:
            ДлинаЗнаменатель = resp_general['ДлинаЗнаменатель']
            ДлинаЧислитель = resp_general['ДлинаЧислитель']
            ДлинаЕдиницаИзмерения = resp_general['ДлинаЕдиницаИзмерения_Key']
            resp_general['Длина'] = f'{ДлинаЗнаменатель} {ЕдиницаИзмерения} весит {ДлинаЧислитель} {ДлинаЕдиницаИзмерения}'
        if resp_general['ПлощадьИспользовать']:
            ПлощадьЗнаменатель = resp_general['ПлощадьЗнаменатель']
            ПлощадьЧислитель = resp_general['ПлощадьЧислитель']
            ПлощадьЕдиницаИзмерения = resp_general['ПлощадьЕдиницаИзмерения_Key']
            resp_general['Площадь'] = f'{ПлощадьЗнаменатель} {ЕдиницаИзмерения} весит {ПлощадьЧислитель} {ПлощадьЕдиницаИзмерения}'
    filter_resp = []
    for k, v in DICT_REPLACE_NAMES.items():
        if v in resp_general:
            val = resp_general[v]
            if isinstance(val,bool):
                if val:
                    val = 'Да'
                else:
                    val = 'Нет'
            filter_resp.append({'Параметр': v, 'Значение': val})
        else:
            if v in headers and options[headers[v]]:
                filter_resp.append({'Параметр': f'-        {v}', 'Значение': ''})

        #======================================
    if filter_resp is None:
        return

    tbl_dse_erp_view.setStyleSheet(CQT.ERP_CSS)
    with CQT.table_updating(tbl_dse_erp_view) :
        #main_data = F.sort_by_column_c(filter_resp, 'Параметр')
        CQT.fill_wtabl(filter_resp,tbl_dse_erp_view, height_row=24,ogr_maxshir_kol=500,selectionBehavior='SelectRows',
                       count_rows_cell_max=-1,load_links=True)
        for i ,val in enumerate(filter_resp) :
            if val['Параметр'].startswith('-        '):
                for j in range(tbl_dse_erp_view.columnCount()):
                    CQT.font_cell_size_format(tbl_dse_erp_view,i,j,bold=True)
            if val['Значение'] == '<не указано>':
                CQT.font_cell_size_format(tbl_dse_erp_view, i, 1, italic=True,size=8)



