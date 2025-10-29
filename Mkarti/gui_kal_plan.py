from __future__ import annotations

import copy
import datetime as DT
import re
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite  as CSQ
import kal_plan as KPL
from  copy import deepcopy
import project_cust_38.Cust_mes as CMS
import gui_vol_plan as VPL
from typing import TYPE_CHECKING, Dict, Any, List
import project_cust_38.Cust_odata_erp as CODAT
import project_cust_38.api_erp_commands as APIERP
from project_cust_38 import Cust_config as CFG
import project_cust_38.Cust_emoji as CEMOJ
if TYPE_CHECKING:
    from MKart import mywindow
from PyQt5 import QtWidgets, QtCore
def hover_tbl_kal_pl_header(self:mywindow, event):
    tbl = self.ui.tbl_kal_pl
    row, column = CQT.get_hover_row_col(self, tbl, event)
    if column == None:
        return
    if tbl.horizontalHeaderItem(column) == None:
        return
    nick = name = tbl.horizontalHeaderItem(column).text()
    if name in self.Data_plan.DICT_INFO_FIELDS_KPL:
        nick = self.Data_plan.DICT_INFO_FIELDS_KPL[name]['nickname']
    tbl.horizontalHeader().setToolTip(nick)

def hover_tbl_pl_gaf(self, event):
    tbl = self.ui.tbl_pl_gaf
    row, column = CQT.get_hover_row_col(self, tbl, event)
    if row == None or column == None:
        return
    if tbl.item(row, column) == None:
        return
    val = tbl.item(row, column).text()
    if val != '':
        load_info_select_block(self,tbl,row,column)
    else:
        load_info_select_block(self, tbl, row, column,True)

def hover_tbl_preview(self, event):
    tbl = self.ui.tbl_preview
    row, column = CQT.get_hover_row_col(self, tbl, event)
    if row == None or column == None:
        return
    if tbl.item(row, column) == None:
        return
    val = tbl.item(row, column).text()
    if val != '':
        load_info_select_block(self,tbl,row,column)
    else:
        load_info_select_block(self, tbl, row, column,True)
def max_mosh(self:mywindow, day, podr:str):
    podr = podr.split('план_')[-1]
    podr = podr.split('факт_')[-1]
    try:
        return round(self.KPLAN_max_mosh[day][podr]*self.selected_napr_koef,2)
    except:
        return 'err'

def load_info_select_block(self,tbl,r = '',c = '',clear=False):
    if clear:
        CQT.statusbar_text(self, '')
        tbl.setToolTip('')
        return
    if r =="":
        r = tbl.currentRow()
    if c == "":
        c = tbl.currentColumn()
    try:
        if self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r+1][c] == '':
            CQT.statusbar_text(self,'')
            tbl.setToolTip('')
    except:
        return
    list = copy.deepcopy(self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r+1][c])
    info = ''
    if type(list) == type([]):
        tmp = []
        for item in list:
            item.pop("Имя_нз",list)
            tmp.append(str(item))
        info = ('\n'.join(tmp))
        tbl.setToolTip(info)
    mosh = ''
    try:
        day = self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][0][c]
        podr = self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r+1][0]
        mosh = f'Максимальная мощность по {self.selected_napr} : {max_mosh(self,day,podr)} н-час.'
    except:
        pass
    CQT.statusbar_text(self,
                       f'{self.glob_kpl_summ_selct_tbl} |  {info} | {mosh}' )

def get_ref_and_nomen_from_tbl_poz(self,m,exel_mode=False):
    poz= None
    if not exel_mode:
        line = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl)
        if line == {}:
            return None, None, None
        kpl_num = line['plan.Пномер']

        poz = CMS.Pozition(kpl_num, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
        poz.load_kpl_table('пл_оуп')
        Ref_Key_py = poz.dict_tables['пл_оуп']['Ref_Key_py']
        nomen_poz = poz.dict_tables['пл_оуп']['Номенклатура_ЕРП']
    else:
        line = CQT.get_dict_line_form_tbl(self.ui.tbl_poz_from_exel)
        poz = line
        nomen_poz_izd = line['изделие']
        nomen_poz_key = None
        for k, v in self.DICT_plan_erp_nomen_refs.items():
            if nomen_poz_izd == v['Description'] or nomen_poz_izd == v['Артикул']:
                nomen_poz_key = k
                nomen_poz= v['Description']
                break
        if nomen_poz_key == None:
            CQT.msgbox(f'изделие `{nomen_poz_izd}` не найдено в номенклатуре')
            return None, None, None
        part_zp = line['номер\nкэ в 1С']

        if not F.is_date(line['ЗК\nдата'], "%d.%m.%y"):
            CQT.msgbox(f'ЗК\nдата не дата')
            return None, None, None
        if not F.is_date(line['ДАТА\nПЛАН\n\nготовн'], "%d.%m.%y"):
            CQT.msgbox(f'ДАТА ПЛАН\nдата не дата')
            return None, None, None
        date_zk_year = F.strtodate(line['ЗК\nдата'], "%d.%m.%y").year
        part_zk = line['ЗК']

        zk = m.get_response(doc_name="Document_ЗаказКлиента?$",
                            wet_filtr=f"filter= like(Number, '%{part_zk}%') and year(Date) eq {date_zk_year} &$select=Ref_Key")
        if len(zk) != 1:
            CQT.msgbox(f'Заказ клиента не определен')
            return None, None, None
        zk = zk[0]
        zk_Ref_Key = zk['Ref_Key']
        lsit_zp_f = m.get_response(doc_name="Document_ЗаказНаПроизводство2_2?$",
                                   wet_filtr=f"filter= like(Number, '%{part_zp}%') and ДокументОснование_Type eq 'StandardODATA.Document_ЗаказКлиента'&$select=Ref_Key,ДокументОснование, Продукция/Номенклатура_Key")
        zp = None
        for item in lsit_zp_f:
            if item['ДокументОснование'] == zk_Ref_Key:
                zp = item
                break

        if zp == None:
            CQT.msgbox(f'Заказ на производство не найден')
            return None, None, None
        Ref_Key_py = zp['Ref_Key']

        fl_nomen_poz_in_zp = False
        for prod in zp['Продукция']:
            if prod['Номенклатура_Key'] == nomen_poz_key:
                fl_nomen_poz_in_zp = True
                break
        if not fl_nomen_poz_in_zp:
            CQT.msgbox(f'Заказ на производство не содержит изделие')
            return None, None, None

    return Ref_Key_py, nomen_poz, poz


@CQT.onerror
def dbl_click_etap_addit_info_poz_gant(self: mywindow, *args):

    def get_vid_rab_by_key(str_key):

        for k, item in self.DICT_VID_RABOT.items():
            if str_key == item['ref_Key_erp']:
                return k
        return str_key

    def count_trailing_zeros(lst_strings: list[str]) -> list[str]:
        lst_length = set()
        for string in lst_strings:
            if string.strip():
                match = re.search(r'0+$', string)
                lst_length.add(len(match.group(0)) if match else 0)
        if lst_length:
            min_length = min(lst_length)
            return [string[:len(string) - min_length] for string in lst_strings]


    r,c,val = args
    Ref_Key = val

    ansv = CQT.msgboxgYN('Вид затрат', btn0_name='Материалы', btn1_name='Труды')
    name = None
    if ansv:
        name = 'РасходМатериаловИРабот'
    else:
        name = 'Трудозатраты'

    m = CODAT.OrdersComposit(self.USER_CONFIG.ERP_base_name['Значение'])

    cod, resp = m.get_response(doc_name=f"Document_ЭтапПроизводства2_2(guid'{Ref_Key}')",
                               wet_filtr=f"?$select={name}", with_cod=True)  #
    if cod != 200:
        CQT.msgbox(f'Err read Document_ЭтапПроизводства2_2 {resp}')
        return
    data = resp[name]
    if name == 'Трудозатраты':
        fix_lists_chert = count_trailing_zeros([_['НомерЧертежа'] for _ in data])
        set_num_chert = set()
        set_db_nums_jur = set(CSQ.custom_request_c(self.bd_naryad,f"""SELECT Пномер FROM jurnal;""",hat_c=False,one_column=True))
        for i, item in enumerate(data):
            num_chert = item['НомерЧертежа']
            num_jur = ''
            if len(num_chert)>0:
                if '_' not in num_chert:
                    num_jur_str = fix_lists_chert[i]
                else:
                    num_jur_str = num_chert.split("_")[0]
                if F.is_numeric(num_jur_str):
                    if int(num_jur_str) in set_db_nums_jur:
                        num_jur = int(num_jur_str)
                        set_num_chert.add(int(num_jur_str))
            item['НомерЧертежа'] = num_jur

        list_data_nar = CSQ.custom_request_c(self.bd_naryad,
                                                    fr'''SELECT mk.Пномер, Тип_мк.Имя as Тип,  mk.Дата, mk.Статус,  mk.Номенклатура, 
                    CASE WHEN знпр.№ERP IS NOT NULL 
                   THEN знпр.№ERP 
                   ELSE mk.Номер_заказа 
                   END AS Номер_заказа, 
                   
                    CASE WHEN знпр.№проекта IS NOT NULL 
                   THEN знпр.№проекта 
                   ELSE mk.Номер_проекта 
                   END AS Номер_проекта, 
                   
                   CASE WHEN napravl_deyat.Псевдоним IS NOT NULL 
                   THEN napravl_deyat.Псевдоним 
                   ELSE mk.Вид 
                   END AS Вид, 
                       mk.Ресурсная_дата, mk.Примечание, mk.Основание, 
                     mk.Прогресс, 
                     
                     CASE WHEN plan.Приоритет IS NOT NULL 
                   THEN plan.Приоритет 
                   ELSE mk.Приоритет 
                   END AS Приоритет, 
                    
                    CASE WHEN napravlenie.name IS NOT NULL 
                   THEN napravlenie.name 
                   ELSE mk.Направление 
                   END AS Направление, 
                    jurnal.Пномер as jurnal_Пномер,
                     jurnal.Номер_наряда, 
                     plan.Позиция, 
                     mk.Вес, mk.Количество,  mk.Дата_завершения,  mk.Коэф_парал, 
                      mk.Искл_план_рм, тип_дорезок.Имя AS тип_дорезок, тип_доработок.Имя AS тип_доработок, 
                      mk.НомКплан as "Номер КПЛ" 
                       FROM jurnal 
                      LEFT JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда 
                      LEFT JOIN mk ON mk.Пномер = naryad.Номер_мк 
                      LEFT JOIN plan ON plan.Пномер = mk.НомКплан  
                      LEFT JOIN napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности 
                      LEFT JOIN napravlenie ON napravlenie.Пномер = napravl_deyat.Направление  
                     LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
                     LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
                     LEFT JOIN Тип_мк ON Тип_мк.Пномер = mk.Тип 
                     LEFT JOIN дорезки_мк ON дорезки_мк.Номер_мк = mk.Пномер 
                     LEFT JOIN тип_дорезок ON тип_дорезок.Пномер = дорезки_мк.Причина 
                     LEFT JOIN тип_доработок ON тип_доработок.Пномер = mk.Тип_доработки 
                     WHERE jurnal.Пномер in ({CSQ.prepare_list_to_tuple(list(set_num_chert))}) and plan.poki = {self.place.poki} ''', rez_dict=True,
                                                    attach_dbs=self.db_kplan)
        dict_data_nar = F.deploy_dict_c(list_data_nar,'jurnal_Пномер')

        for i, item in enumerate(data):
            mk = ''
            nar = ''
            nomen = ''
            poz = ''
            py = ''
            proj = ''
            kpl = ''
            num_chert = item['НомерЧертежа']
            num_jur = None
            if item['Исполнитель'] in self.DICT_EMPLOEE_FULL_WITH_DEL_ref:
                item['Исполнитель'] = self.DICT_EMPLOEE_FULL_WITH_DEL_ref[item['Исполнитель']]['Должность'] + ' ' + \
                self.DICT_EMPLOEE_FULL_WITH_DEL_ref[item['Исполнитель']]['ФИО']
            item['Вид работ'] = get_vid_rab_by_key(item['ВидРабот_Key'])

            if num_chert in dict_data_nar:
                data_nar = dict_data_nar[num_chert]

                mk = data_nar['Пномер']
                nar = data_nar['Номер_наряда']
                nomen = data_nar['Номенклатура']
                poz = data_nar['Позиция']
                py = data_nar['Номер_заказа']
                proj = data_nar['Номер_проекта']
                kpl = data_nar["Номер КПЛ"]

            item['Пномер МК'] = mk
            item['Номер_наряда'] = nar
            item['Номенклатура'] = nomen
            item['Позиция'] = poz
            item['Номер_заказа'] = py
            item['Номер_проекта'] = proj
            item['НомКплан'] = kpl

    for item in data:
        set_del_keys = set()
        for k in item.keys():
            if '_Key' in k or '_Type' in k:
                set_del_keys.add(k)
        for key in set_del_keys:
            item.pop(key)

    CQT.msgboxg_get_table_ok_inf(self,f'{name} по этапу',data,load_summ=True)




def tab_addit_info_poz_gant_click(self:mywindow,ind):
    exel_mode = False
    if not self.ui.fr_poz_from_exel.isHidden():
        exel_mode=True
    def replace_nomen(data:dict, name_field_nonem_key):
        def fix(ref:str):
            if ref in self.DICT_plan_erp_nomen_refs:
                return  self.DICT_plan_erp_nomen_refs[ref]['Description']
            return ref
        new_data = dict()
        for k, v in data.items():
            if isinstance(v,list):
                new_list = []
                for item in v:
                    item = replace_nomen(item,name_field_nonem_key)
                    new_list.append(item)
                v = new_list
            new_data[k] = v
            if k == name_field_nonem_key:
                new_data['Номенклатура'] = fix(v)
        return new_data


    tbl:QtWidgets.QTableWidget  = self.ui.tbl_addit_info_poz_gant
    CQT.clear_tbl(tbl)
    self.ui.btn_pl_send_dates_into_ERP.setEnabled(False)
    self.glob_plan_addit_info_poz_gant_old_date = None
    self.glob_dict_etaps_from_erp = None
    tab = self.ui.tab_addit_info_poz_gant
    if tab.tabText(ind) == 'Позиция':
        if exel_mode:
            fill_select_poz_exel(self)
        else:
            fill_select_poz_kpl(self)
        tbl.setStyleSheet(self.styleSheet())
    else:
        tbl.setStyleSheet(CQT.ERP_CSS)
        m = CODAT.OrdersComposit(self.USER_CONFIG.ERP_base_name['Значение'])

        Ref_Key_py, nomen_poz, poz = get_ref_and_nomen_from_tbl_poz(self,m, exel_mode)

        if Ref_Key_py == None or Ref_Key_py == '':
            return

        if tab.tabText(ind) == 'Этапы':

            def fnc_upd_etaps_znpr(lblself:CQT.InteractiveLabelInstance,self, row, col, poz:CMS.Pozition):
                list_proj = CSQ.custom_request_c(self.db_kplan, f"""SELECT s_num, Статус_поз_ЕРП, 
                      №ERP, Дата_заявки_на_произв, Ref_Key_py 
                                    FROM знпр 
                               WHERE s_num = {poz.dict_tables['пл_оуп']['s_num']};""",
                                                 rez_dict=True)
                m = CMS.ODAT.OrdersComposit()
                for item in list_proj:
                    py = item['№ERP']
                    s_num = item['s_num']
                    if py == '-':
                        continue
                    ref_key_py = item['Ref_Key_py']
                    resp = CMS.make_dict_etaps_from_erp(m, ref_key_py)
                    CMS.update_data_etaps_from_erp(self.db_kplan, resp, s_num)

            if exel_mode:
                return
            resp = CMS.make_dict_etaps_from_erp(m, Ref_Key_py)
            list_etaps_erp = []
            НомПартии_ЗП = str(poz.dict_tables['пл_оуп']['НомПартии_ЗП'])
            if НомПартии_ЗП in resp and  'Этапы' in resp[НомПартии_ЗП]:
                list_etaps_erp = resp[НомПартии_ЗП]['Этапы']

            list_etaps_mes = []
            if not poz.dict_tables['пл_оуп']['data_etaps_from_erp'] == None:
                data_mes  = F.from_binary_pickle(poz.dict_tables['пл_оуп']['data_etaps_from_erp'])
                if НомПартии_ЗП in data_mes:
                    list_etaps_mes = data_mes[НомПартии_ЗП]['Этапы']
            result_data = [{'Версия':"MES","Список":list_etaps_mes},
                           {'Версия':"ERP","Список":list_etaps_erp},]
            CQT.fill_wtabl(result_data, tbl, height_row=24, ogr_maxshir_kol=500, selectionBehavior='SelectRows')
            for i in range(tbl.rowCount()):
                if tbl.item(i,0).text() == "ERP":
                    if tbl.cellWidget(i,1) == None:
                        continue
                    for j in range(tbl.cellWidget(i,1).rowCount()):
                        CQT.add_btn(tbl.cellWidget(i,1),j,2,'Затраты',
                                    conn_func_checked_row_col=dbl_click_etap_addit_info_poz_gant,self=self,
                                    cell_val=tbl.cellWidget(i,1).item(j,2).text())


            if len(list_etaps_mes) != len(list_etaps_erp):
                bad = CMS.Color_tbl(10)
                CQT.set_font_color_wtab_c(tbl,0,0,bad.r,bad.g,bad.b)
                CSQ.custom_request_c(self.db_kplan, f"""UPDATE знпр SET Этапы_ЕРП = 1 WHERE s_num == {poz.dict_tables['пл_оуп']['s_num']};""")
            self.ui.btn_pl_send_dates_into_ERP.setEnabled(True)
            self.glob_dict_etaps_from_erp = resp
            widg = CQT.add_interactive_label(tbl, 0,0, tbl.item(0,0).text(), parent_self=self)
            widg.add_button(CEMOJ.EmojiMain.ДокументыДанные.refresh.symbol, 'Принудительно обновить этапы', fnc_upd_etaps_znpr,
                            cell_val=poz)


        if tab.tabText(ind) in ('ЗП','ЗК'):
            data_py = m.get_response(doc_name=f"Document_ЗаказНаПроизводство2_2(guid'{Ref_Key_py}')",
                                     wet_filtr=f"?$select=Статус,ДокументОснование_Type,ДокументОснование,Number, Date, "
                                               f"Продукция/LineNumber, Продукция/Номенклатура_Key, "
                                               f"Продукция/Спецификация_Key, Продукция/ДатаОтгрузки,"
                                               f"НачатьНеРанее, ДатаПотребности, ДатаПриостановки, ДатаВозобновления,"
                                               f"Причина_Key, ДатаПлановогоНачала, ДатаПлановогоОкончания, ДатаЗакрытия")
            if not isinstance(data_py,dict):
                return

            name_t_ch = ''

            if tab.tabText(ind) == 'ЗП':

                name_t_ch = "Продукция"

                name_link_doc_osn = data_py['ДокументОснование_Type'].split('.')[-1]
                descr_name_link_doc_osn = F.capital_letter_c(F.camel_to_snake(name_link_doc_osn.split('_')[-1]).replace('_'," "))

                data_doc_osn = m.get_response(doc_name=f"{name_link_doc_osn}(guid'{data_py['ДокументОснование']}')",
                                   wet_filtr=f"?$select=Number,Date", get_response_val=True)
                data_py['ДокументОснование']  = f"{descr_name_link_doc_osn} {data_doc_osn['Number']} от {m.fix_dates_form_erp_to_rus(data_doc_osn['Date'])}"

                data_py['Причина приостановки'] = ''
                if data_py['Причина_Key'] in self.DICT_plan_erp_ПричиныПриостановкиПроизводства:
                    data_py['Причина приостановки'] = self.DICT_plan_erp_ПричиныПриостановкиПроизводства[data_py['Причина_Key']]
                data_py = replace_nomen(data_py, 'Номенклатура_Key')
                data_py = m.fix_dates_form_erp_to_rus(data_py)
                data_py = m.fix_camelcase(data_py)
                data_py = m.del_carry_fields(data_py)

                main_data = [{'Параметр': k, 'Значение': v} for k, v in data_py.items()]
                main_data = F.sort_by_column_c(main_data,'Параметр')
                CQT.fill_wtabl(main_data, tbl, height_row=24,ogr_maxshir_kol=500,selectionBehavior='SelectRows')

            if tab.tabText(ind) == 'ЗК':

                if data_py['ДокументОснование_Type'] not in ('StandardODATA.Document_ЗаказКлиента',
                                                             'StandardODATA.Document_ЗаказНаСборку',
                                                             'StandardODATA.Document_ЗаказНаВнутреннееПотребление'):
                    CQT.msgbox(f"Основание для {self.place.doc_prefix}:\n{data_py['ДокументОснование_Type']}.\n Нужен Заказа клиента/Заказ на сборку")
                    return
                client_order = data_py['ДокументОснование']



                if data_py['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаСборку':
                    sb_order = data_py['ДокументОснование']
                    data_sb = m.get_response(doc_name=f"Document_ЗаказНаСборку(guid'{sb_order}')",
                                             wet_filtr=f"?$select=ДокументОснование_Key,Номенклатура_Key")
                    client_order = data_sb['ДокументОснование_Key']

                    nomen_poz = self.DICT_plan_erp_nomen_refs[data_sb['Номенклатура_Key']]['Description']
                if data_py['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаВнутреннееПотребление':
                    sb_order = data_py['ДокументОснование']
                    data_co = m.get_response(doc_name=f"Document_ЗаказНаВнутреннееПотребление(guid'{sb_order}')",
                                             wet_filtr=f"?$select= Number,Date,Статус,ДокументОснование,"
                                                           f"ДокументОснование_Type,Комментарий,Товары/LineNumber,"
                                                           f"Товары/Номенклатура_Key,Товары/Количество,"
                                                           f"Товары/ДатаОтгрузки,НеОтгружатьЧастями,"
                                                           f"Сделка_Key ")


                    data_co['Документ'] = f"ЗаказНаВнутреннееПотребление {data_co['Number']}"



                else:
                    data_co = m.get_response(doc_name=f"Document_ЗаказКлиента(guid'{client_order}')",
                                                 wet_filtr=f"?$select=Number,Date,Статус,ДокументОснование,"
                                                           f"ДокументОснование_Type,Комментарий,Товары/LineNumber,"
                                                           f"Товары/Номенклатура_Key,Товары/Количество,"
                                                           f"Товары/ДатаОтгрузки,НеОтгружатьЧастями,"
                                                           f"Сделка_Key, Менеджер_Key, ДатаСогласования, "
                                                           f"ЭтапыГрафикаОплаты/LineNumber,ЭтапыГрафикаОплаты/ВариантОплаты,"
                                                           f"ЭтапыГрафикаОплаты/ДатаПлатежа,ЭтапыГрафикаОплаты/Сдвиг,"
                                                           f"ЭтапыГрафикаОплаты/ВариантОтсчета")


                    if data_co['ДокументОснование_Type'] == 'StandardODATA.Document_КоммерческоеПредложениеКлиенту':
                        data_doc_osn = m.get_response(doc_name=f"Document_КоммерческоеПредложениеКлиенту(guid'{data_co['ДокументОснование']}')",
                                       wet_filtr=f"?$select=Number,Date", get_response_val=True)
                        data_co['ДокументОснование']  = f"Коммерческое предложение клиенту {data_doc_osn['Number']} от {m.fix_dates_form_erp_to_rus(data_doc_osn['Date'])}"
                    elif data_co['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаданиеТорговомуПредставителю':
                        #text = f"""ВЫБРАТЬ
                        #                ЗаданиеТорговомуПредставителю.Номер КАК Номер,
                        #                ЗаданиеТорговомуПредставителю.Дата КАК Дата
                        #            ИЗ
                        #                Документ.ЗаданиеТорговомуПредставителю КАК ЗаданиеТорговомуПредставителю
                        #            ГДЕ
                        #                ЗаданиеТорговомуПредставителю.Ссылка = &Ссылка
                        #                    """
                        #refs = APIERP.Refs_wet(text)
                        #ref_obj = APIERP.Ref_wet('Ссылка', 'Документы.ЗаданиеТорговомуПредставителю', data_co['ДокументОснование'])
                        #
                        #refs.add_ref(ref_obj)
                        #key, res = APIERP.get_wet_request(text=text)
                        #if key != 200:
                        #    CQT.msgbox(f'Ошибка получения данных из ЕРП')
                        #    return
                        #if not res['data']:
                        #    CQT.msgbox(f'Ресурсная {Спецификация_код_ЕРП} пустая в материалах')
                        #    return


                        cod, data_doc_osn = m.get_response(doc_name=f"Document_ЗаданиеТорговомуПредставителю(guid'{data_co['ДокументОснование']}')",
                                       wet_filtr=f"?$select=Number,Date", get_response_val=True,with_cod=True)
                        if isinstance(data_doc_osn,str):
                            data_co['ДокументОснование'] = data_doc_osn
                        else:
                            data_co['ДокументОснование']  = f"Задание торговому представителю {data_doc_osn['Number']} от {m.fix_dates_form_erp_to_rus(data_doc_osn['Date'])}"
                    elif data_co['ДокументОснование'] == '' and data_co['ДокументОснование_Type'] == 'StandardODATA.Undefined':
                        data_co['ДокументОснование'] = 'Отсутсувует'
                    data_co['Сделка']= m.get_response(doc_name=f"Catalog_СделкиСКлиентами(guid'{data_co['Сделка_Key']}')",
                                       wet_filtr=f"?$select=Description", get_response_val=True)['Description']


                    data_co['Менеджер'] = ''
                    if data_co['Менеджер_Key'] in self.DICT_plan_erp_Пользователи:
                        data_co['Менеджер'] = self.DICT_plan_erp_Пользователи[data_co['Менеджер_Key']]

                data_co['Комментарий'] = data_co['Комментарий'].replace('\n', '; ')
                data_co = replace_nomen(data_co, 'Номенклатура_Key')
                data_co = m.fix_dates_form_erp_to_rus(data_co)
                data_co = m.fix_camelcase(data_co)
                data_co = m.del_carry_fields(data_co)
                main_data = [{'Параметр': k, 'Значение': v} for k, v in data_co.items()]
                self.ui.btn_pl_send_dates_into_ERP.setEnabled(True)

                main_data = F.sort_by_column_c(main_data,'Параметр')
                CQT.fill_wtabl(main_data, tbl, height_row=24,ogr_maxshir_kol=500,selectionBehavior='SelectRows')

                name_t_ch = "Товары"

            plan_addit_info_poz_gant_old_date_max = None
            for row in range(tbl.rowCount()):
                if tbl.item(row,1).text() in ('False','True'):
                    CQT.add_check_box(tbl,row,1,val=eval(tbl.item(row,1).text()),enabled=False)
                    tbl.item(row, 1).setText('')

                if tbl.item(row,0).text() == name_t_ch:
                    tbl_child:QtWidgets.QTableWidget = tbl.cellWidget(row,1)
                    nf_nomen = CQT.num_col_by_name_c(tbl_child,'Номенклатура')
                    nf_date_ot= CQT.num_col_by_name_c(tbl_child, 'Дата отгрузки')
                    if nf_nomen != None:
                        for i in range(tbl_child.rowCount()):
                            date_poz_data = F.strtodate(tbl_child.item(i,nf_date_ot).text(),"%d.%m.%Y")
                            if plan_addit_info_poz_gant_old_date_max == None or plan_addit_info_poz_gant_old_date_max< date_poz_data:
                                plan_addit_info_poz_gant_old_date_max = date_poz_data
                            if tbl_child.item(i,nf_nomen).text() == nomen_poz:
                                if tab.tabText(ind) == 'ЗК':
                                    self.glob_plan_addit_info_poz_gant_old_date = tbl_child.item(i,nf_date_ot).text()
                                for j in range(tbl_child.columnCount()):
                                    CQT.font_cell_size_format(tbl_child,i,j,bold=True)
                    break
            if self.glob_plan_addit_info_poz_gant_old_date == None:
                self.glob_plan_addit_info_poz_gant_old_date = F.datetostr(plan_addit_info_poz_gant_old_date_max,"%d.%m.%Y %H:%M:%S")


def fill_select_poz_exel(self):
    tbl = self.ui.tbl_poz_from_exel
    r = tbl.currentRow()
    CQT.clear_tbl(self.ui.tbl_addit_info_poz_gant)
    if r == None or r == -1:
        return
    self.ui.btn_pl_send_dates_into_ERP.setEnabled(False)
    self.ui.tab_addit_info_poz_gant.blockSignals(True)
    self.ui.tab_addit_info_poz_gant.setCurrentIndex(0)
    self.ui.tab_addit_info_poz_gant.blockSignals(False)
    row = CQT.get_dict_line_form_tbl(tbl,r)
    row_fix = [[k,v] for k,v in row.items()]
    row_fix.insert(0,["Параметр","Значение"])
    CQT.fill_wtabl(row_fix,self.ui.tbl_addit_info_poz_gant,height_row=24)

def fill_select_poz_kpl(self,row=None):
    if row == None:
        tbl = self.ui.tbl_kal_pl
        r = tbl.currentRow()

        CQT.clear_tbl(self.ui.tbl_addit_info_poz_gant)
        if r == None or r == -1:
            return
        row = CQT.get_dict_line_form_tbl(tbl,r)
    row_fix = [[k,v] for k,v in row.items()]
    row_fix.insert(0,["Параметр","Значение"])
    CQT.fill_wtabl(row_fix,self.ui.tbl_addit_info_poz_gant,height_row=24)

@CQT.onerror
def update_dates_obesp(self:mywindow,*args):
    tbl = self.ui.tbl_kal_pl  # 17.04.2025
    result_all = []
    list_not_identity_mats = []
    LIMIT = 50
    sootv = CMS.Zp_kpl(self)

    list_rows_kpl= []
    nums_kpl = dict()

    if 'shift' in CQT.get_key_modifiers(self):
        count = 0
        for i in range(tbl.rowCount()):
            if not tbl.isRowHidden(i):
                count+=1
        if count > LIMIT:
            CQT.msgbox(f'Выборка в ТЧ более {LIMIT} строк')
            return
        for i in range(tbl.rowCount()):
            if not tbl.isRowHidden(i):
                row = CQT.get_dict_line_form_tbl(tbl, i)
                list_rows_kpl.append(row)
    else:
        num_row = tbl.currentRow()
        if num_row == -1:
            return
        row = CQT.get_dict_line_form_tbl(tbl, num_row)
        list_rows_kpl.append(row)


    for row in list_rows_kpl:
        num_kpl = int(row['plan.Пномер'])
        dict_custom_etaps_compliance = sootv.get_custom_compliance_etaps(num_kpl,self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN)
        poz = CMS.Pozition(num_kpl, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
        poz.load_kpl_table('пл_оуп')
        custom_ignore_maters = sootv.get_custom_ignore_maters(num_kpl)

        data = {"poz": poz,
                'wage_batch_number':poz.dict_tables['пл_оуп']['НомПартии_ЗП'],
                'dict_custom_etaps_compliance': dict_custom_etaps_compliance,
                'new_dates': dict(),
                'dict_mat_etaps': dict(),
                'custom_ignore_maters':custom_ignore_maters}
        nums_kpl = {num_kpl: data,}

    for num_kpl, data_kpl in nums_kpl.items():
        def calc_etaps(s_num_kpl:int,wage_batch_number:int ):
            data_etap_erp = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""SELECT пл_оуп.№ERP, пл_оуп.Дата_заявки_на_произв, пл_оуп.НомПартии_ЗП, знпр.Ref_Key_py, знпр.data_etaps_from_erp 
                     FROM знпр INNER JOIN пл_оуп ON пл_оуп.Пномер_ЗП = знпр.s_num WHERE пл_оуп.НомПл == {s_num_kpl}""",
                                                 rez_dict=True, one=True)
            if data_etap_erp == None or data_etap_erp == False:
                CQT.msgbox(f'Ошибка получения Пномер_ЗП')
                return
            if F.is_date(data_etap_erp['Дата_заявки_на_произв'], "%Y-%m-%d") == False:
                CQT.msgbox(f'В КПЛ {s_num_kpl},Дата_заявки_на_произв не дата, обратиться в ПДО')
                return
            ref_Key_py = data_etap_erp['Ref_Key_py']
            dict_etaps_from_erp = F.from_binary_pickle(data_etap_erp['data_etaps_from_erp'])
            if dict_etaps_from_erp == None:
                CQT.msgbox(f'В КПЛ {s_num_kpl} Не заполнены этапы при создании, обратиться в ПДО')
                return
            data_etaps_from_erp = F.from_binary_pickle(data_etap_erp['data_etaps_from_erp'])
            if str(wage_batch_number) not in data_etaps_from_erp:
                CQT.msgbox(f'В КПЛ {s_num_kpl} Не cоответстувет номер партии ЗП')
                return
            return data_etaps_from_erp[str(wage_batch_number)]

        def add_mat_in_dict_mat_etaps(dict_mat_etaps,mat_etap):
            RANGES_RS_TYPE = {
                        "Этапы":0,
                        "Боевая":1,
                        "Предв.":2,
                              }
            key = mat_etap['НоменклатураКод']
            rs_type_lvl = RANGES_RS_TYPE[mat_etap['ВидРС']]
            if key in dict_mat_etaps:
                rs_type_old = dict_mat_etaps[key]['ВидРС']
                rs_type_lvl_old = RANGES_RS_TYPE[rs_type_old]
                if rs_type_lvl_old > rs_type_lvl:
                    dict_mat_etaps[key] = mat_etap
                else:
                    pass
                    #print(f' мат. {key} {rs_type_old} не обновлен')
            else:
                dict_mat_etaps[key] = mat_etap
            return dict_mat_etaps

        list_mat_etaps_from_etaps = calc_etaps(num_kpl,data_kpl['wage_batch_number'])
        if list_mat_etaps_from_etaps:
            for etap_etaps in list_mat_etaps_from_etaps['Этапы']:
                ref_mat_etap = etap_etaps['Чек']
                text = f"""
                ВЫБРАТЬ
                    "Этапы" КАК ВидРС,
                    ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами.Номенклатура.Наименование КАК НоменклатураНаименование,
                    ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами.Номенклатура.Код КАК НоменклатураКод,
                    ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами.Ссылка.Этап.Наименование КАК ЭтапНаименование,
                    ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами.КоличествоУпаковок КАК КоличествоУпаковок,
                    ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами.Упаковка.Наименование КАК УпаковкаНаименование,
                    ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами.Номенклатура.ЕдиницаИзмерения.Наименование КАК НоменклатураЕдиницаИзмеренияНаименование
                ИЗ
                    Документ.ЭтапПроизводства2_2.ОбеспечениеМатериаламиИРаботами КАК ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами
                ГДЕ
                    ЭтапПроизводства2_2ОбеспечениеМатериаламиИРаботами.Ссылка.Ссылка = &Ссылка
                """

                refs = APIERP.Refs_wet(text)
                ref_obj = APIERP.Ref_wet('Ссылка', 'Документы.ЭтапПроизводства2_2', ref_mat_etap)
                refs.add_ref(ref_obj)
                key, res = APIERP.get_wet_request(text=text, refs=refs)
                if key != 200:
                    CQT.msgbox(f'Ошибка получения данных ЭтапПроизводства2_2 из ЕРП ')
                    return

                for mat_etap_etaps in res['data']:
                    data_kpl['dict_mat_etaps'] = add_mat_in_dict_mat_etaps(data_kpl['dict_mat_etaps'],mat_etap_etaps)

        data_res_num = CSQ.custom_request_c(self.db_kplan,f"""SELECT Спецификация_ЕРП, 
        Спецификация_код_ЕРП, Предв_спецификация_ЕРП FROM пл_топ WHERE НомПл = {num_kpl}""", rez_dict=True,one=True)

        Спецификация_код_ЕРП = data_res_num['Спецификация_код_ЕРП']
        Предв_спецификация_ЕРП = data_res_num['Предв_спецификация_ЕРП'].strip()

        if Спецификация_код_ЕРП and not Предв_спецификация_ЕРП:
            text = f"""ВЫБРАТЬ
                        "Боевая" КАК ВидРС,
                        РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Наименование КАК НоменклатураНаименование,
                        РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Код КАК НоменклатураКод,
                        РесурсныеСпецификацииМатериалыИУслуги.Этап.Наименование КАК ЭтапНаименование,
                        РесурсныеСпецификацииМатериалыИУслуги.КоличествоУпаковок КАК КоличествоУпаковок,
                        РесурсныеСпецификацииМатериалыИУслуги.Упаковка.Наименование КАК УпаковкаНаименование,
                        РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.ЕдиницаИзмерения КАК НоменклатураЕдиницаИзмерения
                    ИЗ   
                        Справочник.РесурсныеСпецификации.МатериалыИУслуги КАК РесурсныеСпецификацииМатериалыИУслуги
                    ГДЕ    
                        РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Код = "{Спецификация_код_ЕРП.strip()}"
                """
            key, res = APIERP.get_wet_request(text=text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')
                return


            for mat_etap_etaps in res['data']:
                data_kpl['dict_mat_etaps'] = add_mat_in_dict_mat_etaps(data_kpl['dict_mat_etaps'], mat_etap_etaps)
        def calc_middlefix(Предв_спецификация_ЕРП):
            middlefix = ''
            if Предв_спецификация_ЕРП.startswith('ТКПА_'):
                list_parts_Предв_спецификация_ЕРП = Предв_спецификация_ЕРП.split('_')
                if len(list_parts_Предв_спецификация_ЕРП) > 1 and F.is_numeric(list_parts_Предв_спецификация_ЕРП[1]):
                    partName = '_'.join(list_parts_Предв_спецификация_ЕРП[:2])
                    middlefix = f' ИЛИ РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Наименование ПОДОБНО "{partName}%" '
            return middlefix

        if not Спецификация_код_ЕРП and Предв_спецификация_ЕРП:
            middlefix = calc_middlefix(Предв_спецификация_ЕРП)
            text = f"""ВЫБРАТЬ
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Наименование КАК НоменклатураНаименование,
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Код КАК НоменклатураКод,
                            РесурсныеСпецификацииМатериалыИУслуги.Этап.Наименование КАК ЭтапНаименование,
                            РесурсныеСпецификацииМатериалыИУслуги.КоличествоУпаковок КАК КоличествоУпаковок,
                            РесурсныеСпецификацииМатериалыИУслуги.Упаковка.Наименование КАК УпаковкаНаименование,
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.ЕдиницаИзмерения КАК НоменклатураЕдиницаИзмерения,
                            "Предв." КАК ВидРС
                        ИЗ
                            Справочник.РесурсныеСпецификации.МатериалыИУслуги КАК РесурсныеСпецификацииМатериалыИУслуги
                        ГДЕ
                            (РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Наименование = "{Предв_спецификация_ЕРП.strip()}" 
                            ИЛИ РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Код = "{Предв_спецификация_ЕРП.strip()}"{middlefix})
                            И РесурсныеСпецификацииМатериалыИУслуги.Ссылка.ПометкаУдаления = ЛОЖЬ
                """
            key, res = APIERP.get_wet_request(text=text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')
                return

            for mat_etap_etaps in res['data']:
                data_kpl['dict_mat_etaps'] = add_mat_in_dict_mat_etaps(data_kpl['dict_mat_etaps'], mat_etap_etaps)

        if Предв_спецификация_ЕРП and Спецификация_код_ЕРП:
            middlefix = calc_middlefix(Предв_спецификация_ЕРП)
            text = f"""ВЫБРАТЬ
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Наименование КАК НоменклатураНаименование,
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Код КАК НоменклатураКод,
                            РесурсныеСпецификацииМатериалыИУслуги.Этап.Наименование КАК ЭтапНаименование,
                            РесурсныеСпецификацииМатериалыИУслуги.КоличествоУпаковок КАК КоличествоУпаковок,
                            РесурсныеСпецификацииМатериалыИУслуги.Упаковка.Наименование КАК УпаковкаНаименование,
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.ЕдиницаИзмерения КАК НоменклатураЕдиницаИзмерения,
                            "Боевая" КАК ВидРС
                        ИЗ
                            Справочник.РесурсныеСпецификации.МатериалыИУслуги КАК РесурсныеСпецификацииМатериалыИУслуги
                        ГДЕ
                            РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Код = "{Спецификация_код_ЕРП.strip()}"
                            И РесурсныеСпецификацииМатериалыИУслуги.Ссылка.ПометкаУдаления = ЛОЖЬ
                        ОБЪЕДИНИТЬ ВСЕ
                        
                        ВЫБРАТЬ
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Наименование,
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.Код,
                            РесурсныеСпецификацииМатериалыИУслуги.Этап.Наименование,
                            РесурсныеСпецификацииМатериалыИУслуги.КоличествоУпаковок,
                            РесурсныеСпецификацииМатериалыИУслуги.Упаковка.Наименование,
                            РесурсныеСпецификацииМатериалыИУслуги.Номенклатура.ЕдиницаИзмерения,
                            "Предв." 
                        ИЗ
                            Справочник.РесурсныеСпецификации.МатериалыИУслуги КАК РесурсныеСпецификацииМатериалыИУслуги
                        ГДЕ
                            (РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Наименование = "{Предв_спецификация_ЕРП.strip()}" 
                            ИЛИ РесурсныеСпецификацииМатериалыИУслуги.Ссылка.Код = "{Предв_спецификация_ЕРП.strip()}"{middlefix})
                            И РесурсныеСпецификацииМатериалыИУслуги.Ссылка.ПометкаУдаления = ЛОЖЬ
                    """

            key, res = APIERP.get_wet_request(text=text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')
                return

            for mat_etap_etaps in res['data']:
                data_kpl['dict_mat_etaps'] = add_mat_in_dict_mat_etaps(data_kpl['dict_mat_etaps'], mat_etap_etaps)

        list_refs = F.list_of_lists_to_list_of_dicts(sootv.get_by_kpl(num_kpl))

        #list_refs = ['85dc77a4-2044-11f0-a3cb-30e1716be59f']
        if not list_refs:
            continue

        for data_refs in list_refs:
            ref = data_refs['Ref_Key_зп_абстракт']
            text = """ВЫБРАТЬ
    
        ЗаказПоставщикуТовары.Ссылка КАК ЗП_Реальный,
        ЗаказПоставщикуТовары.Номенклатура КАК Номенклатура,
        ЗаказПоставщикуТовары.КоличествоУпаковок КАК Количество,
        ВЫБОР
            КОГДА ЗаказПоставщикуТовары.Ссылка.ПоступлениеОднойДатой = ИСТИНА
                ТОГДА ЗаказПоставщикуТовары.Ссылка.ДатаПоступления
            ИНАЧЕ ЗаказПоставщикуТовары.ДатаПоступления
        КОНЕЦ КАК ПлановаяДата,
        ЗаказПоставщикуТоварыВиртуальный.НомерСтроки КАК НомерСтрокиЗППДО,
        "" КАК ЭтапКПЛ,
        "" КАК ДатаОбеспСтарая,
        "" КАК Игнорировать,
        ЗаказПоставщикуТоварыВиртуальный.ИдентификаторСтроки КАК ИдентификаторСтроки
    ПОМЕСТИТЬ ВТ_1
    ИЗ
        Документ.ЗаказПоставщику.Товары КАК ЗаказПоставщикуТовары
            ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказПоставщику.MES_ТоварыДеталировка КАК ЗаказПоставщикуMES_ТоварыДеталировка
                ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказПоставщику.Товары КАК ЗаказПоставщикуТоварыВиртуальный
                ПО (ЗаказПоставщикуMES_ТоварыДеталировка.ВиртуальныйЗаказПоставщику = ЗаказПоставщикуТоварыВиртуальный.Ссылка)
                    И (ЗаказПоставщикуMES_ТоварыДеталировка.ИдентификаторСтрокиВиртуальныйЗаказПоставщику = ЗаказПоставщикуТоварыВиртуальный.ИдентификаторСтроки)
            ПО (ЗаказПоставщикуТовары.Ссылка = ЗаказПоставщикуMES_ТоварыДеталировка.Ссылка)
                И (ЗаказПоставщикуТовары.Номенклатура = ЗаказПоставщикуMES_ТоварыДеталировка.Номенклатура)
    ГДЕ
        ЗаказПоставщикуMES_ТоварыДеталировка.ВиртуальныйЗаказПоставщику = &ВиртуальныйЗаказПоставщику
    ;
    
    ////////////////////////////////////////////////////////////////////////////////
    ВЫБРАТЬ
        ВТ_1.ЗП_Реальный КАК ЗП_Реальный,
        ЗаказПоставщикуТовары.Номенклатура.Код КАК НоменклатураКод,
        ЗаказПоставщикуТовары.Номенклатура КАК Номенклатура,
        ЗаказПоставщикуТовары.Количество КАК Количество,
        ВТ_1.ПлановаяДата КАК ПлановаяДата,
        ВТ_1.ЭтапКПЛ КАК ЭтапКПЛ,
        ВТ_1.ДатаОбеспСтарая КАК ДатаОбеспСтарая,
        ВТ_1.Игнорировать КАК Игнорировать,
        "" КАК Выбор_этапа
    ИЗ
        Документ.ЗаказПоставщику.Товары КАК ЗаказПоставщикуТовары
            ЛЕВОЕ СОЕДИНЕНИЕ ВТ_1 КАК ВТ_1
            ПО (ВТ_1.ИдентификаторСтроки = ЗаказПоставщикуТовары.ИдентификаторСтроки)
    ГДЕ
        ЗаказПоставщикуТовары.Ссылка = &Ссылка"""

            refs = APIERP.Refs_wet(text)
            ref_obj = APIERP.Ref_wet('ВиртуальныйЗаказПоставщику', 'Документы.ЗаказПоставщику', ref)
            ref_obj2 = APIERP.Ref_wet('Ссылка', 'Документы.ЗаказПоставщику', ref)
            refs.add_ref(ref_obj)
            refs.add_ref(ref_obj2)
            key, res = APIERP.get_wet_request(text=text, refs=refs)
            if key == 200:
                if res['data']:
                    for item in res['data']:

                        for k,v in data_refs.items():
                            item[k] = v
                        if F.is_date(item['ПлановаяДата'],"%Y-%m-%dT%H:%M:%S"):
                            item['ПлановаяДата'] = F.dateStrToStr(item['ПлановаяДата'],"%Y-%m-%dT%H:%M:%S","%d.%m.%Y")
                        if item['ПлановаяДата'] == None:
                            item['ПлановаяДата'] = ''
                        result_all.append(item)
                else:
                    item = {

                    'ЗП_Реальный' : '',
                    'НоменклатураКод': '',
                    'Номенклатура' : '',
                    'Количество' : '',
                    'ПлановаяДата' : '',

                    'ЭтапКПЛ' : '',
                    'ДатаОбеспСтарая' : '',
                    'Игнорировать' : '',

                    'Выбор_этапа' : '',

                    }
                    for k, v in data_refs.items():
                        item[k] = v
                    result_all.append(item)
            else:
                CQT.msgbox(f'Ошибка получения данных из ЕРП')
                return

    def add_etap_kpl_in_calc(etap_kpl,poz):

        if etap_kpl == None:
            CQT.msgbox(f'Для {etap} не установлен в соответствие этап КПЛ В БД')
            return
        if etap_kpl == '':
            dict_etaps_kpl[('', '')] = ''
            return

        name_tbl = etap_kpl.split('.')[0]
        name_etap_kpl = self.Data_plan.DICT_PODR[name_tbl]['Наименование']

        name_field_obespech = self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN[etap_kpl][
            'name_field_obespech']

        field_dates_supply = f'{name_tbl}.{name_field_obespech}'
        date_supply = poz.row_dates_supply[field_dates_supply]

        dict_etaps_kpl[(field_dates_supply,name_etap_kpl)] =      date_supply


    if not result_all:
        CQT.msgbox(f'Связанных ЗП не обнаружено')
        return
    for item in result_all:
        num_kpl = item['КПЛ']
        data_kpl = nums_kpl[num_kpl]
        poz = data_kpl['poz']
        cod = item['НоменклатураКод']

        dict_etaps_kpl = dict()
        if item['s_num_zp'] in data_kpl['custom_ignore_maters']:
            if num_kpl in data_kpl['custom_ignore_maters'][item['s_num_zp']]:
                if cod in data_kpl['custom_ignore_maters'][item['s_num_zp']][num_kpl]:
                    add_etap_kpl_in_calc('',poz)
                    item['Игнорировать'] = '1'



        if item['s_num_zp'] in data_kpl['dict_custom_etaps_compliance']:
            if cod in data_kpl['dict_custom_etaps_compliance'][item['s_num_zp']]:
                etap_kpl = data_kpl['dict_custom_etaps_compliance'][item['s_num_zp']][cod]
                add_etap_kpl_in_calc(etap_kpl,poz)
                item['Выбор_этапа'] = etap_kpl
        Источник = ''
        if cod in data_kpl['dict_mat_etaps']:
            mat_res = data_kpl['dict_mat_etaps'][cod]
            Источник = mat_res['ВидРС']
            etap = mat_res['ЭтапНаименование']
            if etap not in self.Data_plan.DICT_ETAPS_NAME:
                CQT.msgbox(f'Ошибка. Этап {etap} отсутствует в БД')
                return
            etap_kpl = self.Data_plan.DICT_ETAPS_NAME[etap]['sopost_etapov_vo'].split('|')[0]
            add_etap_kpl_in_calc(etap_kpl,poz)
        if dict_etaps_kpl:
            ЭтапКПЛ = []
            ИмяЭтапКПЛ = []
            ДатаОбеспСтарая = []

            for k,v in dict_etaps_kpl.items():
                ЭтапКПЛ.append(k[0])
                ИмяЭтапКПЛ.append(k[1])
                ДатаОбеспСтарая.append(v)
            item['ЭтапКПЛ'] = ';'.join(ЭтапКПЛ)
            item['Имя Этапа КПЛ'] = ';'.join(ИмяЭтапКПЛ)
            item['ДатаОбеспСтарая'] = ';'.join(ДатаОбеспСтарая)
            item['Источник'] = Источник
        else:
            item['Имя Этапа КПЛ'] = 'Мат. не найден в рес.'
            item_tmp = copy.deepcopy(item)
            item_tmp['ЭтапКПЛ'] = ''
            list_not_identity_mats.append(item_tmp)


        try:
            item['ПлановаяДата'] =F.datetostr(F.strtodate(item['ПлановаяДата'], "%d.%m.%Y %H:%M:%S"),"%Y-%m-%d" )
        except:
            pass


    @CQT.onerror
    def hide_fields_list_not_identity_mats(tbl:QtWidgets.QTableWidget):
        nf_etap_kpl = CQT.num_col_by_name_c(tbl, 'ЭтапКПЛ')

        def fnc_check(self,checked,row,col):
            cmb:QtWidgets.QComboBox = tbl.cellWidget(row, nf_etap_kpl)

            if checked:
                tbl.item(row,col).setText('1')
                cmb.setEnabled(False)
                cmb.setCurrentText('')
            else:
                tbl.item(row, col).setText('')
                cmb.setEnabled(True)
        def select_etap(self, text, row, col):
            if text:
                nf_etap_kpl_name = CQT.num_col_by_name_c(tbl, 'Имя Этапа КПЛ')
                nf_etap_kpl = CQT.num_col_by_name_c(tbl, 'ЭтапКПЛ')

                etap_kpl = [ {'etap':k,'fields':_['Имя_поля']}  for k, _ in self.Data_plan.DICT_PODR.items() if _['poki'] == self.place.poki and _['Наименование'] == text][0]
                field = etap_kpl['fields'].split(';')[-1]
                etap_kpl = f"{etap_kpl['etap']}.{field}"
                tbl.item(row,nf_etap_kpl).setText(etap_kpl)
                tbl.item(row, nf_etap_kpl_name).setText(text)


        list_etaps_kpl_shabl = []
        for etap,  _ in self.Data_plan.DICT_PODR.items():
            if _['poki'] == self.place.poki:
                for field in _['Имя_поля'].split(';'):
                    if '.'.join([etap,field]) in self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN:
                        list_etaps_kpl_shabl.append([_['Наименование'],field])



        nf_ignore = CQT.num_col_by_name_c(tbl, 'Игнорировать')
        for i in range(tbl.rowCount()):
            CQT.add_combobox(self,tbl,i,nf_etap_kpl,[_[0] for _ in list_etaps_kpl_shabl],True,select_etap,list_tooltips=[_[1] for _ in list_etaps_kpl_shabl])

            val = F.boolm(tbl.item(i, nf_ignore).text())
            cmb: QtWidgets.QComboBox = tbl.cellWidget(i, nf_etap_kpl)
            if not val:
                cmb.setEnabled(True)
            else:
                cmb.setEnabled(False)
            CQT.add_check_box(tbl, i, nf_ignore, False, val, fnc_check, self)


        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'ДатаОбеспСтарая'), True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 's_num'), True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 's_num_zp'), True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Ref_Key_зп_абстракт'), True)


    def fnc_get_result_tbl(btn:QtWidgets.QPushButton,dialog:CQT.Dialog_tbl,tbl:QtWidgets.QTableWidget):
        if btn.text() == 'Принять':
            nf_etap_kpl = CQT.num_col_by_name_c(tbl, 'ЭтапКПЛ')
            nf_etap_kpl_name = CQT.num_col_by_name_c(tbl, 'Имя Этапа КПЛ')
            nf_s_num = CQT.num_col_by_name_c(tbl, 's_num_zp')
            nf_НоменклатураКод = CQT.num_col_by_name_c(tbl, 'НоменклатураКод')
            nf_num_kpl = CQT.num_col_by_name_c(tbl, 'КПЛ')
            nf_ignore = CQT.num_col_by_name_c(tbl, 'Игнорировать')

            for i in range(tbl.rowCount()):
                if tbl.item(i,nf_etap_kpl).text() == '' and tbl.item(i, nf_ignore).text() == '':
                    CQT.migat(dialog,tbl,i,nf_etap_kpl_name,msg='Не выбрано')
                    return
            for i in range(tbl.rowCount()):
                s_num = tbl.item(i,nf_s_num).text()
                НоменклатураКод = tbl.item(i,nf_НоменклатураКод).text()
                etap_kpl = tbl.item(i, nf_etap_kpl).text()
                ignore = F.boolm(tbl.item(i, nf_ignore).text())

                if ignore:
                    num_kpl = tbl.item(i,nf_num_kpl).text()
                    sootv.set_custom_ignore_maters(int(s_num),НоменклатураКод,int(num_kpl))

                sootv.set_custom_compliance_etaps(int(s_num),НоменклатураКод,tbl.item(i,nf_etap_kpl).text())
            dialog.accept()
        else:
            dialog.reject()

    debug = True #debug = True
    if CFG.Config.user_config.is_developer and not debug:
        list_not_identity_mats = []
    if list_not_identity_mats:
        if not CQT.msgboxg_get_table(self, f'Не найдено в рес. {Спецификация_код_ЕРП}', list_not_identity_mats, 'Принять',
                                     WindowTitle='Выбрать этап КПЛ', yesNoMode=True,
                                     func_oform_tbl=hide_fields_list_not_identity_mats,func_btn0=fnc_get_result_tbl, not_standart_close=True):
            return
        CQT.msgbox(f'Данные записаны, обновление дат доступно')
        return


    def hide_fields(tbl:QtWidgets.QTableWidget):
        nf_num_kpl = CQT.num_col_by_name_c(tbl, 'КПЛ')
        nf_НоменклатураКод = CQT.num_col_by_name_c(tbl, 'НоменклатураКод')
        nf_s_num = CQT.num_col_by_name_c(tbl, 's_num_zp')
        nf_stage_selection = CQT.num_col_by_name_c(tbl, 'Выбор_этапа')

        def fnc_del_etap(lblself:CQT.InteractiveLabelInstance,self, row, col,dialog:QtWidgets.QDialog):
            etap_kpl = None
            НоменклатураКод = tbl.item(row, nf_НоменклатураКод).text()
            s_num = tbl.item(row, nf_s_num).text()
            sootv.set_custom_compliance_etaps(int(s_num), НоменклатураКод, etap_kpl)

            CQT.msgbox(f'Перезапустить окно дат обеспечения')
            dialog.reject()
            return
        def fnc_select_etap(lblself:CQT.InteractiveLabelInstance,self, row, col,dialog:QtWidgets.QDialog):


            list_etaps_kpl_shabl_second = []
            for etap, _ in self.Data_plan.DICT_PODR.items():
                if _['poki'] == self.place.poki:
                    for field in _['Имя_поля'].split(';'):
                        if '.'.join([etap, field]) in self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN:
                            list_etaps_kpl_shabl_second.append([_['Наименование'],field])

            lst_new_stage = CQT.msgboxg_get_table(self, 'Даты обеспечения из ЕРП', list_etaps_kpl_shabl_second, 'Выбрать',
                                  show_filtr=False, use_first_row_as_header=False, selection_from_tbl=True,selectRows=True,
                                  WindowTitle='Выбрать этап КПЛ', yesNoMode=False)
            if lst_new_stage:
                new_stage = lst_new_stage[0]['0']
                etap_kpl = [{'etap': k, 'fields': _['Имя_поля']} for k, _ in self.Data_plan.DICT_PODR.items() if
                            _['poki'] == self.place.poki and _['Наименование'] == new_stage][0]
                field = etap_kpl['fields'].split(';')[-1]
                etap_kpl = f"{etap_kpl['etap']}.{field}"
                НоменклатураКод = tbl.item(row, nf_НоменклатураКод).text()
                s_num = tbl.item(row, nf_s_num).text()
                sootv.set_custom_compliance_etaps(int(s_num), НоменклатураКод, etap_kpl)

                CQT.msgbox(f'Перезапустить окно дат обеспечения')
                dialog.reject()
                return

        def fnc_check(self,checked,row,col,):
            num_kpl = tbl.item(row, nf_num_kpl).text()
            НоменклатураКод = tbl.item(row, nf_НоменклатураКод).text()
            s_num = tbl.item(row, nf_s_num).text()
            if checked:
                tbl.item(row,col).setText('1')

                sootv.set_custom_ignore_maters(int(s_num),НоменклатураКод,int(num_kpl))
            else:
                tbl.item(row, col).setText('')
                sootv.set_custom_ignore_maters(int(s_num), НоменклатураКод, int(num_kpl),delete=True)

        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,'s_num'),True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 's_num_zp'), True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Год'), True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'ЭтапКПЛ'), True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Ref_Key_зп_абстракт'), True)
        nf_ignore = CQT.num_col_by_name_c(tbl,'Игнорировать')
        for i in range(tbl.rowCount()):
            val = F.boolm(tbl.item(i, nf_ignore).text())
            stage_selection = tbl.item(i, nf_stage_selection).text()
            CQT.add_check_box(tbl,i,nf_ignore,False,val,fnc_check,self)
            if stage_selection:
                widg = CQT.add_interactive_label(tbl,i,nf_stage_selection,stage_selection,parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol,'Выбрать этап',fnc_select_etap,cell_val=tbl.parent().parent().parent())
                widg.add_button(CEMOJ.EmojiMain.Статусы.error.symbol,'Удалить этап',fnc_del_etap,cell_val=tbl.parent().parent().parent())



    if not CQT.msgboxg_get_table(self, 'Даты обеспечения из ЕРП', result_all,'Обновить даты',
                                 WindowTitle='Даты обеспечения к обновлению',yesNoMode=True,func_oform_tbl=hide_fields):
        return


    for item in result_all:
        num_kpl = item['КПЛ']
        list_etaps = item['ЭтапКПЛ'].split(';')
        if item['Игнорировать'] == '1':
            continue
        if item['ПлановаяДата'] == '':
            continue
        date = F.dateStrToStr(item['ПлановаяДата'],format_out="")
        if date == None:
            CQT.msgbox(f'Дата в {item} не распознана' )
            continue
        for i, field_dates_supply in enumerate(list_etaps):


            if field_dates_supply in data_kpl['new_dates']:
                if date > F.strtodate(data_kpl['new_dates'][field_dates_supply],"%Y-%m-%d"):

                    data_kpl['new_dates'][field_dates_supply] = F.dateStrToStr(date, "%Y-%m-%d")
            else:
                data_kpl['new_dates'][field_dates_supply] = F.dateStrToStr(date, "%Y-%m-%d")

    for data in nums_kpl.values():
        poz = data['poz']
        new_dates = data['new_dates']
        rez = poz.update_dates_supply(new_dates)
        if rez:
            CQT.msgbox(f'По КПЛ {poz.Пномер}:\nОбновлено:\n{str(rez)}')
        else:
            CQT.msgbox(f'По КПЛ {poz.Пномер}:\nИзменений нет')
        return

@CQT.onerror
def le_edit_local_gant_full_etap(self:mywindow):
    self.ui.le_edit_local_gant_kon.setText(self.ui.le_edit_local_gant_full_etap.text())
    self.ui.le_edit_local_gant_nach.setText(self.ui.le_edit_local_gant_full_etap.text())

def move_left(self):
    move(self, -1)

def move_right(self):
    move(self, 1)
@CQT.onerror
def move(self, direction = 1):
    set_masks_date = {"%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%y-%m-%d", }
    def update_db(self, list_name_field_change, delta_nach, direction):
        delta_days = 0
        for name_field_change in list_name_field_change:
            table, field = name_field_change.split('.')
            name_field_snom = 'НомПл'
            if table == "plan":
                name_field_snom = 'Пномер'
            list_old_date = CSQ.custom_request_c(self.db_kplan,
                                  f"""SELECT {field} FROM {table} WHERE {name_field_snom} == {self.pnom_kplan_select};""")
            if list_old_date == False or list_old_date == None or len(list_old_date) != 2:
                CQT.msgbox(f'ОШибка загрузки даты {field}')
                return False
            old_date = list_old_date[-1][0]
            if not F.is_date(old_date,"%Y-%m-%d"):
                CQT.msgbox(f'ОШибка распознавания дат {old_date} {field}')
                return False
            delta_days = delta_nach
            if F.is_date(delta_nach, "%Y-%m-%d"):
                new_date = delta_nach
                delta_days = F.delta_days(F.strtodate(new_date), F.strtodate(old_date))
            else:
                if not F.is_numeric(delta_nach):
                    CQT.msgbox(f'Ошибка типа данных')
                    return False
                new_date = F.date_add_days(old_date, delta_nach*direction, "%Y-%m-%d", "%Y-%m-%d")
            CSQ.custom_request_c(self.db_kplan,
                       f"""UPDATE {table} SET {field} = "{new_date}"  WHERE {name_field_snom} == {self.pnom_kplan_select};""")
        return delta_days

    r = self.ui.tbl_preview.currentRow()
    c = self.ui.tbl_preview.currentColumn()
    if self.ui.le_edit_local_gant_nach.text() == '':
        self.ui.le_edit_local_gant_nach.setText('0')
    if self.ui.le_edit_local_gant_kon.text() == '':
        self.ui.le_edit_local_gant_kon.setText('0')

    fl_is_date_n = False
    fl_is_date_k = False
    fl_check_data_n = True
    fl_check_data_k = True
    if not F.is_numeric(self.ui.le_edit_local_gant_nach.text()):
        fl_check_data_n = False
        for mask in set_masks_date:
            if F.is_date(self.ui.le_edit_local_gant_nach.text(),mask):
                self.ui.le_edit_local_gant_nach.setText(F.datetostr(F.strtodate(self.ui.le_edit_local_gant_nach.text(),mask),"%Y-%m-%d"))
                fl_check_data_n = True
                fl_is_date_n = True
                break

    if not F.is_numeric(self.ui.le_edit_local_gant_kon.text()):
        fl_check_data_k = False
        for mask in set_masks_date:
            if F.is_date(self.ui.le_edit_local_gant_kon.text(), mask):
                self.ui.le_edit_local_gant_kon.setText(
                    F.datetostr(F.strtodate(self.ui.le_edit_local_gant_kon.text(), mask), "%Y-%m-%d"))
                fl_check_data_k = True
                fl_is_date_k = True
                break

    if not(fl_check_data_k and fl_check_data_n):
        CQT.msgbox(f'Смещение не число и не дата')
        return
    #if 'shift' in CQT.get_key_modifiers(self):
    set_name_nach = set()
    set_name_zav = set()
    current_ifo_tbl_name = KPL.calc_current_ifo_tbl_name(self)
    try:
        tbls_kpl_info_val = self.dict_tbls_kpl_info[current_ifo_tbl_name]
    except:
        CQT.msgbox(f'Ошибка, не обработана активная таблица')
        return


    for ix in self.ui.tbl_preview.selectedIndexes():
        r = ix.row()+1
        c = ix.column()

        if not isinstance(tbls_kpl_info_val, list):
            continue
        if tbls_kpl_info_val[r][c] == '' or "Имя_нз" not in tbls_kpl_info_val[r][c][0]:
            continue
        set_name_nach.add(tbls_kpl_info_val[r][c][0]["Имя_нз"][0])
        set_name_zav.add(tbls_kpl_info_val[r][c][0]["Имя_нз"][1])
    list_name_nach= list(set_name_nach)
    list_name_zav = list(set_name_zav)
    if not len(list_name_nach):
        CQT.msgbox(f'Не выбран этап')
        return

    if not len(list_name_zav):
        CQT.msgbox(f'Не выбран этап')
        return

    #else:
    #    if type(self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r + 1][c]) != list:
    #        return
    #    else:
    #        if "Имя_нз" not in self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r + 1][c][0]:
    #            return
    #    list_name_nach = [deepcopy(self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r + 1][c][0])["Имя_нз"][0]]
    #    #name_nach = deepcopy(self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r + 1][c][0])["Имя_нз"][0]
    #    #name_zav =  deepcopy(self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r + 1][c][0])["Имя_нз"][1]
    #    list_name_zav = [deepcopy(self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r + 1][c][0])["Имя_нз"][1]]



    delta_nach =self.ui.le_edit_local_gant_nach.text()
    delta_kon = self.ui.le_edit_local_gant_kon.text()
    if not fl_is_date_n:
        delta_nach = F.valm(delta_nach)
    if not fl_is_date_k:
        delta_kon = F.valm(delta_kon)

    fl = False
    if delta_nach != 0:
        rez = update_db(self,list_name_nach,delta_nach,direction)
        if rez == False:
            return
        if fl_is_date_n:
            delta_nach = rez.days
        c = c + delta_nach * direction
        if c >= self.ui.tbl_preview.columnCount():
            c = self.ui.tbl_preview.columnCount()-1
        if c < 1:
            c = 1
        fl = True
    if delta_kon != 0:
        rez = update_db(self,list_name_zav,delta_kon,direction)
        if rez == False:
           return
        c = c + delta_nach * direction
        if c >= self.ui.tbl_preview.columnCount():
            c = self.ui.tbl_preview.columnCount()-1
        if c < 1:
            c = 1
        fl = True
    if fl:
        CMS.update_local_graf(self,True,self.pnom_kplan_select)
        self.ui.tbl_preview.setCurrentCell(r-1,c)
        CMS.hide_free_columns(self,self.ui.tbl_preview)
        if self.kpl_mode == 1:
            VPL.load_tbl_gant(self)  # объемный загрузка


@CQT.onerror
def show_hide_tree_fields(self:mywindow):
    fr = self.ui.fr_tree_fields
    if fr.isHidden():
        load_fields_for_tree(self)
        fr.setHidden(False)
    else:
        fr.setHidden(True)
        self.ui.splitter_8.setSizes([650, 180])
@CQT.onerror
def load_fields_for_tree(self:mywindow):
    tree = self.ui.tree_fields
    tbl = self.ui.tbl_kal_pl
    currentRow = None
    if tbl.currentRow() !=-1:
        currentRow = CQT.get_dict_line_form_tbl(tbl)


    dict_of_dicts = dict()
    #for j in range(tbl.columnCount()):
    #    name = tbl.horizontalHeaderItem(j).text()
    #    if '.' in name:
    #        tbl_name, field = name.split('.')
    #    else:
    #        tbl_name = name
    #        field = None
    #    if tbl_name not in dict_of_dicts:
    #        dict_of_dicts[tbl_name] = []
    #    dict_of_dicts[tbl_name].append(field)
    if currentRow == None:
        CQT.msgbox(f'Не выбрана позиция')
        return
    data_from_db, fields_info = KPL.load_db(self,currentRow['plan.Пномер'])
    data_from_db_dict = F.list_of_lists_to_list_of_dicts(data_from_db)[0]
    dict_of_dicts = dict()
    for j in range(len(data_from_db[0])):
        name = data_from_db[0][j]
        if '.' in name:
            tbl_name, field = name.split('.')
        else:
            tbl_name = name
            field = None
        if tbl_name not in dict_of_dicts:
            dict_of_dicts[tbl_name] = []
        dict_of_dicts[tbl_name].append(field)

    list_of_dict = []

    for k,v in dict_of_dicts.items():
        nick = ''
        if v == []:
            if k in self.Data_plan.DICT_INFO_FIELDS_KPL:
                nick = self.Data_plan.DICT_INFO_FIELDS_KPL[k]['nickname']
        else:
            if k in self.Data_plan.DICT_PODR:
                nick = self.Data_plan.DICT_PODR[k]['Наименование']
        color_background = '254;254;254'
        color_font = None
        bold_font = None
        italic_font = None
        size_font = None
        if k in self.Data_plan.DICT_PODR:
            color_font = F.align_colors(self.Data_plan.DICT_PODR[k]['Цвет'],level_percent=-20,saturation_percent=-20)
            bold_font = True
        tmp_dict = {'Поле': k,  'Значение': '','Примечание': nick, '_lvl':0,'_Поле_tooltip':nick, '_Поле_gui':
            {'color_background':color_background, 'color_font':color_font, 'bold_font':bold_font, 'italic_font':italic_font,'size_font':size_font}}
        list_of_dict.append(tmp_dict)
        color1= '254;254;254'
        color2 = '234;234;234'
        fl_back = True
        for field in v:
            if field == None:
                continue
            full_name =  '.'.join([k,field])
            nick = ''
            if full_name in self.Data_plan.DICT_INFO_FIELDS_KPL:
                nick = self.Data_plan.DICT_INFO_FIELDS_KPL[full_name]['nickname']

            fl_back= not fl_back
            if fl_back:
                color_background = color1
            else:
                color_background = color2

            color_font = None
            bold_font = None
            italic_font = None
            size_font = None

            if k in self.Data_plan.DICT_PODR:
                color_font = F.align_colors(self.Data_plan.DICT_PODR[k]['Цвет'],level_percent=-20)
                bold_font = True
            field_gui = {'color_background':color_background, 'color_font':color_font, 'bold_font':bold_font, 'italic_font':italic_font,'size_font':size_font}
            field_gui_not_colored = {'color_background': color_background, 'color_font': '10;10;10', 'bold_font': False,
                         'italic_font': italic_font, 'size_font': size_font}
            tmp_dict = {'Поле': field, 'Значение' : '', 'Примечание': nick, '_lvl':1,'_Поле_tooltip':nick,
                        '_Поле_gui':field_gui,
                        '_Значение_gui': field_gui_not_colored,
                        '_Примечание_gui': field_gui_not_colored,

                        }
            if currentRow:
                tmp_dict['Значение'] = ''
                if full_name in data_from_db_dict:
                    tmp_dict['Значение'] = str(data_from_db_dict[full_name])
            list_of_dict.append(tmp_dict)

    CQT.fill_wtree_unique(tree,list_of_dict, False)


@CQT.onerror
def tree_fields_dbl_clck(self:mywindow,*args):
    tree = self.ui.tree_fields
    #row = CQT.treeCurrentRow(tree)

    if tree.currentItem().parent() == None:
        str_find = tree.currentItem().text(0)
    else:
        field = tree.currentItem().text(0)
        tbl = tree.currentItem().parent().text(0)
        str_find = tbl+'.'+field

    tbl = self.ui.tbl_kal_pl
    tbl_config = self.ui.tbl_pl_add_poz


    if self.regim == 'cnf':
        fl_naid = False
        for j in range(tbl_config.columnCount()):
            if tbl_config.horizontalHeaderItem(j).text() == str_find:
                tbl_config.setCurrentCell(0, j)
                tbl_config.selectColumn(j)
                fl_naid = True
                break
        if not fl_naid:
            CQT.msgbox(f'Поле {str_find} не найдено в табличной части настроек')
    else:
        row_tbl = 0
        if tbl.currentRow() != -1:
            row_tbl = tbl.currentRow()
        fl_naid = False
        for j in range(tbl.columnCount()):
            if tbl.horizontalHeaderItem(j).text() == str_find:
                tbl.setCurrentCell(row_tbl, j)
                tbl.selectColumn(j)
                fl_naid = True
                break
        if not fl_naid:
            CQT.msgbox(f'Поле {str_find} не найдено в табличной части')
    pass



@CQT.onerror
def del_dates_etaps(self:mywindow):
    if 'pnom_kplan_select' not in self.__dict__:
        CQT.msgbox(f'Не выбрана позиция(гант)')
        return
    if not CQT.msgboxgYN(f'Будут удалены для номера КПЛ   {self.pnom_kplan_select}  даты этапов:'
                         f':\n\n{[_["Имя_поля"] for _ in self.Data_plan.DICT_PODR.values() if _["Имя_поля"] != ""]}'):
        return
    for name_tbl, item in self.Data_plan.DICT_PODR.items():
        if item['Имя_поля'] != '':
            name_field_nach = item['Имя_начала_этапа']
            name_field_zav = item['Имя_конца_этапа']
            CSQ.custom_request_c(self.db_kplan,f"""UPDATE {name_tbl} SET ({name_field_nach} , {name_field_zav}) 
                = ("","") WHERE {item['Имя_первичного_поля']} = {int(self.pnom_kplan_select)} """)
    CMS.update_local_graf(self, True, self.pnom_kplan_select)
    clear_dates_etaps_le(self)
    CQT.msgbox(f'Успешно')


@CQT.onerror
def set_start_end_dates(self:mywindow):
    tbl= None
    if self.current_kpl_table == 'tbl_preview':
        list_tbl = self.dict_tbls_kpl_info['tbl_preview']
        tbl = self.ui.tbl_preview
    if self.current_kpl_table == 'tbl_pl_gaf_svod':
        list_tbl = self.dict_tbls_kpl_info['tbl_pl_gaf']
        tbl = self.ui.tbl_pl_gaf_svod
    if self.current_kpl_table == 'tbl_pl_gaf':
        list_tbl = self.dict_tbls_kpl_info['tbl_pl_gaf']
        tbl = self.ui.tbl_pl_gaf
    if tbl == None:
        return
    set_column = set()
    for ix in tbl.selectedIndexes():
        c = ix.column()
        set_column.add(c)
    list_column = sorted(list(set_column))
    if len(list_column) == 0:
        CQT.msgbox(f'Не выбрано ни одной ячейки')
        return
    start = list_column[0]
    end = list_column[-1]
    start_date = F.datetostr(list_tbl[0][start],"%Y-%m-%d")
    end_date =F.datetostr(list_tbl[0][end],"%Y-%m-%d")
    self.ui.le_start_set_dates_etaps.setText(start_date)
    self.ui.le_end_set_dates_etaps.setText(end_date)

@CQT.onerror
def clear_dates_etaps_le(self:mywindow):
    self.ui.le_start_set_dates_etaps.setText('')
    self.ui.le_end_set_dates_etaps.setText('')
@CQT.onerror
def set_dates_etaps(self:mywindow,by_sbork = False):
    SB_GROUP = [ _['Группа_для_расч_норм_и_ганта'] for _ in self.Data_plan.DICT_PODR_POKI.values() if _['Это_группа_сборки']]

    if 'pnom_kplan_select' not in self.__dict__ or self.pnom_kplan_select is None:
        CQT.msgbox(f'Не выбрана позиция(гант)')
        return
    start_str = self.ui.le_start_set_dates_etaps.text()
    end_str = self.ui.le_end_set_dates_etaps.text()
    #start_str = "2024-06-25"
    #end_str = "2024-07-25"
    def check_dates(str_date):
        if F.is_date(str_date,"%Y-%m-%d"):
            return F.strtodate(str_date,"%Y-%m-%d")
        if F.is_date(str_date, "%d.%m.%Y"):
            return F.strtodate(str_date, "%d.%m.%Y")
        return False
    def make_dict_groupes(self:mywindow,poz):
        summ_time = 0
        dict_groups = dict()
        tmp_list= [['tbl','data','poz']]
        for name_tbl, item in self.Data_plan.DICT_PODR.items():
            if item['Группа_для_расч_норм_и_ганта'] != '':
                tmp_list.append([name_tbl,item,item['Группа_для_расч_норм_и_ганта']])
        tmp_list = F.sort_by_column_c(tmp_list,'poz')

        for name_tbl, item, _ in tmp_list[1:]:
            group = item['Группа_для_расч_норм_и_ганта']
            name_field = item['Имя_поля'].split(';')[0]
            full_name = '.'.join([name_tbl,name_field])
            if full_name not in poz.row_time_etap:
                continue
            time_current = poz.row_time_etap[full_name]
            if time_current == 0:
                continue
            if group not in dict_groups:
                dict_groups[group] = {'time':0,
                                      'start':'',
                                      'end':'',
                                      'name_field_start':[],
                                      'name_field_end': [],
                                      'part_of_summ':0,
                                      'days':0}

            if time_current > dict_groups[group]['time']:
                dict_groups[group]['time'] = time_current
                dict_groups[group]['name_field_start'].append(name_tbl + '.' + item['Имя_начала_этапа'])
                dict_groups[group]['name_field_end'].append(name_tbl + '.' +item['Имя_конца_этапа'])
                summ_time+=time_current

        return dict_groups, summ_time

    start_date = check_dates(start_str)
    end_date = check_dates(end_str)
    if start_date == False or end_date == False:
        CQT.msgbox(f'Дата введена не корректно')
        return
    if end_date <= start_date:
        CQT.msgbox(f'Разница дат не корректна')
        return
    if 'pnom_kplan_select' not in self.__dict__:
        CQT.msgbox(f'Нужно выбрать позицию КПЛ')
        return
    poz = CMS.Pozition(self.pnom_kplan_select, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self,
                       False)
    dict_groups: dict[int,str,str,list,list,int,int]
    dict_groups,summ_time = make_dict_groupes(self,poz)
    if summ_time == 0:
        CQT.msgbox(f'Сумма норм времени на позицию = 0')
        return

    for group in dict_groups.keys():
        dict_groups[group]['part_of_summ'] = dict_groups[group]['time'] / summ_time
    days_from_user = (end_date - start_date).days -1
    if by_sbork and len(SB_GROUP):
        part_before_sb = 0
        part_after_sb = 0
        count_before = 1
        count_after = 0
        if SB_GROUP[0] in dict_groups:
            for key in dict_groups.keys():
                if key < SB_GROUP[0]:
                    part_before_sb +=  dict_groups[key]['part_of_summ']
                    count_before +=1
                if key> SB_GROUP[0]:
                    part_after_sb +=   dict_groups[key]['part_of_summ']
                    count_after += 1
            part_sb = dict_groups[SB_GROUP[0]]['part_of_summ']
            days_before_sb = F.round_up(part_before_sb/part_sb*days_from_user*5/7)+count_before
            days_after_sb = F.round_up(part_after_sb/part_sb*days_from_user*5/7)+count_after
            start_date = F.date_add_days(start_date,-days_before_sb,'','')
            end_date = F.date_add_days(end_date, days_after_sb, '', '')
        else:
            CQT.msgbox(f'Сборки не обнаружено')
            return

    delta = (end_date - start_date).days*5/7
    prev_date = F.datetostr(start_date,"%Y-%m-%d")
    for group in dict_groups.keys():
        dict_groups[group]['days'] = F.round_up(dict_groups[group]['part_of_summ'] * delta)
        dict_groups[group]['start'] = prev_date
        dict_groups[group]['end'] = F.date_add_days(prev_date,dict_groups[group]['days'],"%Y-%m-%d","%Y-%m-%d")
        prev_date = F.date_add_days(dict_groups[group]['end'],1,"%Y-%m-%d","%Y-%m-%d")


    new_poz_row_etap = copy.deepcopy(poz.row_dates_etap_plan)
    for group in dict_groups.keys():
        for full_name_start in dict_groups[group]['name_field_start']:
            new_poz_row_etap[full_name_start] = dict_groups[group]['start']
        for full_name_end in dict_groups[group]['name_field_end']:
            new_poz_row_etap[full_name_end] = dict_groups[group]['end']
    poz.update_row_etaps(new_poz_row_etap)
    CMS.update_local_graf(self, True, self.pnom_kplan_select)
    clear_dates_etaps_le(self)
    CQT.msgbox(f'Успешно')


def load_form_db(self,pnom):
    rez = CSQ.custom_request_c(self.db_kplan,f"""SELECT local_graf FROM plan WHERE Пномер == {pnom};""",)
    data = F.from_binary_pickle(rez)
    return data


def tbl_preview_on_header_click(self, ind):
    tbl = self.ui.tbl_preview
    text = tbl.horizontalHeaderItem(ind).text()
    if len(text.split('\n')) ==4:
        pre_date = "\n".join(text.split('\n')[:3])
        if F.is_date( pre_date, "%d\n%m\n%y"):
            text = F.datetostr(F.strtodate(pre_date,"%d\n%m\n%y"),"%d.%m.%Y" )
    F.copy_bufer(text)
    CQT.msgbox(f'Скопировано в буфер: {text}',time_life=0.5)

@CQT.onerror
def apply_field_filter_hat_name(tbl_filtr):
    tbl_filtr.setVerticalHeaderLabels(['план_факт_подр'])
    tbl_filtr.setRowHeight(0, 25)