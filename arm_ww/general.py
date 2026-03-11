from __future__ import annotations
if __name__ == "__main__":
    quit()

import main_classes as CLSS

from typing import  TYPE_CHECKING
from PyQt5 import QtWidgets
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F

import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_emoji as CEMOJ
from app_dataclasses import data_app as DTCLS
import doc_modules.doc_rd as DCRD
import doc_modules.doc_zp as DCZP
import doc_modules.doc_vsk as DCVSK
import doc_modules.doc_zmp as DCZMP
import doc_modules.doc_zsb as DCZSB
import doc_modules.doc_zvp as DCZVP
import doc_modules.doc_common as DCCOM
import project_cust_38.api_erp_commands as APIERP
import subprocess
if TYPE_CHECKING:
    from arm_ww import mywindow


ALIASES = {
    'doc_name':'Тип документа',
    '_ref': 'ref',
    '_Warehouse_ref': 'Склад_ref',
    'Warehouse': 'Склад',
    'Operation': 'Операция',
    'Date_shipment': 'Дата',
    '_Foundation_document_ref':'_Документ-основание_ref',
    'Foundation_document': 'Документ-основание',
    'Date_foundation_document': 'Дата документа\n-основания',
    'Status_foundation_document': 'Статус документа\n-основания',
    'State':'Статус',
    'Activity': 'Действие',
    'Counterparty': 'Контрагент',
    'Recipient_sender': 'Получатель/\nотправитель',
    'Initiator': 'Инициатор',
    'Project': 'Проект',
    '_Nomenclature_ref': 'Номенклатура_ref',
    'Nomenclature': 'Номенклатура',
    'Nomenclature_params': 'Характеристики',
    'Quantity': 'Кол-во\nуп.',
    'Quantity_unit': 'Кол-во уп.\nЕд.Изм.',
    'Quantity_abs': 'Кол-во',
    'Quantity_abs_unit': 'Кол-во\nЕд.Изм.',
    'Order_Quantity': 'Кол-во уп.\nпо ордерам',
    'Order_Quantity_unit': 'Кол-во уп. по\nордерам Ед.Изм.',
    'Order_Quantity_abs': 'Кол-во\nпо ордерам',
    'Order_Quantity_abs_unit': 'Кол-во по\nордерам Ед.Изм.',
    'Available': 'Доступно',
    'Available_unit': 'Доступно\nЕд.Изм.'
}
def load_plane_text()->str:
    text = CSQ.custom_request_c(DTCLS.USER_CONFIG.common_config.db_files,
                                f"""SELECT text FROM notes WHERE name = "arm_ww" """,
                                one=True,
                                one_column=True,
                                hat_c=False)
    return text

def save_plane_text():
    pline = DTCLS.pline
    msg = pline.ple.toPlainText()
    data = [msg,F.curr_user_c(),F.now()]
    rez = CSQ.custom_request_c(DTCLS.USER_CONFIG.common_config.db_files,
                         f""" UPDATE notes
                SET  (text, user,date)
                    = ({CSQ.questions_for_mask(data)})
                            WHERE name = "arm_ww" ;""",list_of_lists_c=[data])
    print(str(rez))

def tab_w_currentChanged():
    update_tab()

def update_dates():
    suc, data = CQT.get_data_dialog_choose(DTCLS.app_self,'Выбор диапазона',range_dates=True,
                                            start_date=DTCLS.dateFiltr.qstart)
    if not suc:
        return
    start = data['date_from']
    end = data['date_to']
    DTCLS.dateFiltr.set_start(start)
    DTCLS.dateFiltr.set_end(end)

def startup():
    update_tab()

def update_tab(*args):
    if CMS.kontrol_ver(DTCLS.app_self.versia, 'АРМ складского работника') == False:
        quit()
    tab = DTCLS.app_self.ui.tab_w
    tab_name = CQT.object_name_by_index_tab(tab, tab.currentIndex())

    if tab_name == 'tab_start':
        return

    CQT.clear_tbl(DTCLS.app_self.ui.tbl_detail)

    if not DTCLS.storages.load_user_filter():
        CQT.blink_obj_c(DTCLS.app_self,2,DTCLS.app_self.ui.btn_storage,f'Не выбраны склады')
        return

    if tab_name == 'tab_common':#Распоряжение на доставку
        DCCOM.fill_table(DTCLS.app_self)
    if tab_name == 'tab_rd':#Распоряжение на доставку
        DCRD.fill_table(DTCLS.app_self)
    if tab_name == 'tab_zp':#Заказы поставщикам
        DCZP.fill_table(DTCLS.app_self)
    if tab_name == 'tab_vsk':#Возврат материалов из кладовой
        DCVSK.fill_table(DTCLS.app_self)
    if tab_name == 'tab_zvp':#Заказы на внутреннее потребление
        DCZVP.fill_table(DTCLS.app_self)
    if tab_name == 'tab_zmp':#Заказ материалов в производство
        DCZMP.fill_table(DTCLS.app_self)
    if tab_name == 'tab_zsb':#Заказ на сборку
        DCZSB.fill_table(DTCLS.app_self)

def calc_leftover(ref_storage,use_params)->dict[dict]:
    m = int(F.now('%M'))
    part = m%DTCLS.lazy_time_munutes
    if part > 0:
        m = round(m - part)
    str_now = F.now(f"%Y,%m,%d,%H,{m},0")
    fl_mult = False
    if isinstance(ref_storage, (list,set)):
        dict_storages = {f'stor_{i}':_ for i, _ in enumerate(ref_storage)}
        str_storages = ', '.join([f'&{_}' for _ in dict_storages.keys()])
        storage_filtr = f'Склад В ({str_storages})'
        fl_mult = True
    else:
        dict_storages = {f'stor_1':ref_storage}
        storage_filtr = f'Склад = &stor_1'

    text = f"""
    ВЫБРАТЬ
    ТоварыНаСкладахОстатки.Номенклатура КАК Номенклатура,
    ТоварыНаСкладахОстатки.Характеристика КАК Характеристика,
    ТоварыНаСкладахОстатки.Характеристика.Представление КАК ХарактеристикаПредставление,
    ТоварыНаСкладахОстатки.ВНаличииОстаток КАК ВНаличииТовары,
    ТоварыНаСкладахОстатки.КОтгрузкеОстаток КАК КОтгрузкеТовары,
    ЕСТЬNULL(ЗапасыИПотребности.ВНаличииОстаток, 0) КАК ВНаличииЗапасы,
    ЕСТЬNULL(ЗапасыИПотребности.РезервироватьНаСкладеОстаток, 0) КАК ВРезервеЗапасы,
    ЕСТЬNULL(ЗапасыИПотребности.ВНаличииОстаток - ЗапасыИПотребности.РезервироватьНаСкладеОстаток, 0) КАК ДоступноЗапасы,
    ЕСТЬNULL(ТоварыНаСкладахОстатки.ВНаличииОстаток - ЕСТЬNULL(ЗапасыИПотребности.РезервироватьНаСкладеОстаток, 0), 0) КАК Available,
    ТоварыНаСкладахОстатки.Склад КАК Склад,
    ТоварыНаСкладахОстатки.Номенклатура.ЕдиницаИзмерения.Ссылка.Представление КАК ЕдИзм,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ТоварыНаСкладахОстатки.Номенклатура.Ссылка)) КАК ref,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ТоварыНаСкладахОстатки.Склад)) КАК Склад_ref
ИЗ
    РегистрНакопления.ТоварыНаСкладах.Остатки(ДАТАВРЕМЯ({str_now}), {storage_filtr}) КАК ТоварыНаСкладахОстатки
    ЛЕВОЕ СОЕДИНЕНИЕ РегистрНакопления.ЗапасыИПотребности.Остатки(ДАТАВРЕМЯ({str_now}), {storage_filtr}) КАК ЗапасыИПотребности
    ПО 
        ТоварыНаСкладахОстатки.Номенклатура = ЗапасыИПотребности.Номенклатура
        И (ТоварыНаСкладахОстатки.Характеристика = ЗапасыИПотребности.Характеристика 
            ИЛИ (ТоварыНаСкладахОстатки.Характеристика ЕСТЬ NULL И ЗапасыИПотребности.Характеристика ЕСТЬ NULL))
ГДЕ
    ТоварыНаСкладахОстатки.ВНаличииОстаток <> 0
    ИЛИ ТоварыНаСкладахОстатки.КОтгрузкеОстаток <> 0
    
    """
    refs = APIERP.Refs_wet(text)

    for name, ref_storage in dict_storages.items():
        refs.add_ref(APIERP.Ref_wet(name, 'Справочники.Склады', ref_storage))


    if (data := APIERP.get_wet_request_result(text=text, refs=refs,lazy_method_huours=DTCLS.lazy_time_munutes,
                                              msg_err=None)) is None:
        return dict()
    if fl_mult:
        result = dict()
        for item in data:
            stor_ref = item['Склад_ref']
            if stor_ref not in result:
                result[stor_ref] = []
            result[stor_ref].append(item)
        for stor_ref, data in result.items():
            if use_params:
                result[stor_ref] = F.deploy_dict_c(data, ('ref', 'Характеристика'))
            else:
                result[stor_ref] = F.deploy_dict_c(data, 'ref')
        return result

    else:
        if use_params:
            return F.deploy_dict_c(data,('ref','Характеристика'))
        else:
            return F.deploy_dict_c(data,'ref')


def _generate_link(ref:str,TYPE_DOC:str)->tuple[str,str]:
    c1_link = fr'/data/{TYPE_DOC}?ref={F.uuid_to_1c_ref(ref)}'
    path = F.get_1c_executor_path()
    path_o = F.Cust_path(path)
    prefix = path_o.as_raw_literal()  #prefix = fr'"%programfiles%\1cv8\common\1cestart.exe" '
    claster = DTCLS.USER_CONFIG.ERP_base.КластерСерверов
    name_srv = DTCLS.USER_CONFIG.ERP_base.name
    out_link = fr'e1c://server/{claster}/{name_srv}#e1cib{c1_link}'
    line = prefix + fr'/url "{out_link}"'
    return line, out_link



def open_in_1c(ref:str,TYPE_DOC:str):
    line, out_link = _generate_link(ref,TYPE_DOC)
    try:
        subprocess.call(line, shell=True)
    except:
        F.copy_bufer(out_link)
        CQT.msgbox(f'Скопировано в буфер\n{out_link}')

def select_storages():
    aliases = {'is_output':'Получатель-\nотправитель',
               'text':'Название',
               'chk':'',
               }
    def fnc_oform(tbl:QtWidgets.QTableWidget):
        selected_storages = DTCLS.storages.load_user_filter()
        t = CQT.TableContext(tbl)
        for row in t.rows():
            ref = row.value('ref')
            CQT.add_check_box(t.tbl,row.i,row.nf['chk'],val=ref in selected_storages)
        def fnc_context(self: mywindow, tbl: QtWidgets.QTableWidget, row: int, col: int,
                       menu_builder: CQT.ContextMenuBuilder):
            def fnc_select_all(*args):
                for row in t.rows():
                    chk: QtWidgets.QCheckBox = row.widget('chk')
                    chk.setChecked(True)
            def fnc_revers_all(*args):
                for row in t.rows():
                    chk: QtWidgets.QCheckBox = row.widget('chk')
                    chk.setChecked(not chk.isChecked())
            #menu_builder.add_submenu(f"{emoji.symbol} График")
            menu_builder.add_menu(f'{CEMOJ.EmojiMain.СтатусыПроизводства.success_tin.symbol*2}\tВыбрать все', fnc_select_all)
            menu_builder.add_menu(f'{CEMOJ.EmojiMain.ДокументыДанные.revers.symbol}\tРеверс', fnc_revers_all)

        t.add_column_events('chk',context_menu=True,on_context_menu=fnc_context,parent_self=DTCLS.app_self)

        t.hide('ref')

    def fnc_ok(btn:QtWidgets.QPushButton, dialog:CQT.Dialog_tbl, tbl:QtWidgets.QTableWidget):
        if btn.text() == 'Принять':
            selected_storages = set()
            t = CQT.TableContext(tbl)
            for row in t.rows():
                chk: QtWidgets.QCheckBox = row.widget('chk')
                if chk.isChecked():
                    selected_storages.add(row.value('ref'))
            if not selected_storages:
                CQT.msgbox(f'Должно быть не менее одного элемент')
                return
            DTCLS.storages.save_user_filter(selected_storages)
            dialog.accept()
        else:
            dialog.reject()



    templ = DTCLS.storages.list_template()
    templ = F.insert_key_to_dicts(templ,0,'chk','')
    list_selected = CQT.msgboxg_get_table(DTCLS.app_self,'Выбор складов',templ,'Принять',
                                          func_oform_tbl=fnc_oform,styleSheet=CQT.ERP_CSS,sortingEnabled=True,
                                          aliases_header=aliases,func_btn0=fnc_ok,not_standart_close=True)

    if not list_selected:
        return


def prepare_stor_vars(stort_addr,refs:APIERP.Refs_wet=None)->tuple[APIERP.Refs_wet,str]:
    filtr_war = ''
    selected_stors = DTCLS.storages.req_form_selected()
    storage_wars = ', '.join([f"&{_['var_name']}" for _ in selected_stors])
    if selected_stors:
        filtr_war = f'И {stort_addr} В ({storage_wars})'
    if refs is None:
        refs = APIERP.Refs_wet(filtr_war)
    for item in  selected_stors:
        var_name = item['var_name']
        ref_key = item['ref']
        refs.add_ref(APIERP.Ref_wet(var_name,'Справочники.Склады', ref_key))
    return refs, filtr_war

def get_params_module(name_file:str, name_param:str)->tuple:
    NAME_TAB = name_file.replace('doc', 'tab').split('.')[-1]
    return DTCLS.DICT_TYPES_DOC[NAME_TAB][name_param]