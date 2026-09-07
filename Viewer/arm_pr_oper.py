from __future__ import annotations
import copy
import datetime

import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_config as CFG
from typing import TYPE_CHECKING
from dataClass import data_app as DTCLS
import project_cust_38.Cust_emoji as CEMOJ
if TYPE_CHECKING:
    from Viewer import mywindow
import project_cust_38.Cust_odata_erp as ODAT


#

@CQT.onerror
def fill_tbl_report_add(self:mywindow,*args):


    tbl_p = self.ui.tbl_report_c
    tbl = self.ui.tbl_report_add
    row_data = CQT.get_dict_line_form_tbl(tbl_p)
    user_name = row_data['ФИО']
    self.global_arm_oper_user_fio = user_name
    nach = self.ui.le_start_of_period.text()
    konec = self.ui.le_end_of_period.text()
    lbl_report = CQT.CustLabel(self.ui.lbl_sort_c_report)
    vid = lbl_report.text
    name_report = lbl_report.get_user_data()
    podrazd = self.ui.cmb_podrazdelenie.currentText()

    CQT.clear_tbl(tbl)
    CQT.clear_tbl(self.ui.tbl_report_add_summ)
    CQT.clear_tbl(self.ui.tbl_viev_etaps_name)
    CQT.clear_tbl(self.ui.tbl_viev_etaps_erp)

    list_narjur = []

    list_ends = CSQ.custom_request_c(self.bd_naryad,f"""SELECT  
                 "" AS НомКплан,
                 "" AS Номер_заказа, 
                 "" AS Номер_мк, 
                 jurnal.Номер_наряда AS  "Наряд№",  
                 "" AS  "Подтвержден",  
                 jurnal.Пномер as Пномер_жур, 
                 jurnal.Дата, 
                 "" AS Дата_выгрузки_ЕРП,
                 "" AS  "БД",
                 "" AS Минут_выгружено_ЕРП,    
                 "" AS  "Факт мин.", 
                 "" AS  "Труды в ЕРП", 
                 jurnal.Статус, 
                 "" AS Примечание
    FROM jurnal 
    WHERE jurnal.ФИО = "{user_name}" and jurnal.Статус != "Начат" and 
    datetime(jurnal.Дата) >= datetime("{add_6_hours(nach)}") and datetime(jurnal.Дата) <= datetime("{add_6_hours(konec)}");
    """,rez_dict=True, attach_dbs=(self.db_kplan,self.bd_users))

    if len(list_ends) == 0:
        return
    for item in list_ends:
        list_nar_start = CSQ.custom_request_c(self.bd_naryad,f"""SELECT mk.НомКплан,
        CASE WHEN знпр.№ERP IS NOT NULL 
        THEN знпр.№ERP 
        ELSE mk.Номер_заказа 
        END AS Номер_заказа, 
        naryad.Номер_мк, naryad.Пномер as "Наряд№",  
        naryad.Подтвержд_вып_дата as "Подтвержден",  
        jurnal.Пномер as Пномер_жур, 
        jurnal.Дата, 
        jurnal.Дата_выгрузки_ЕРП,
        bases_ERP.name as "БД",
        jurnal.Минут_выгружено_ЕРП,    
        jurnal.Подытог as "Факт мин.", 
        jurnal.Подытог_нормы as "Труды в ЕРП", 
        jurnal.Статус, 
        naryad.Примечание FROM mk 
        INNER JOIN naryad ON naryad.Номер_мк = mk.Пномер 
        LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
        LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
        LEFT JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер 
        LEFT JOIN bases_ERP ON jurnal.base_ERP = bases_ERP.s_num 
        WHERE jurnal.ФИО = "{user_name}" and jurnal.Номер_наряда == {item["Наряд№"]} 
         and jurnal.Статус == "Начат" and datetime(jurnal.Дата) < datetime({item['Дата']!r}) ORDER BY datetime(jurnal.Дата) DESC LIMIT 1
        """,rez_dict=True, attach_dbs=(self.db_kplan,self.bd_users),one=True) # 02.02.2026
        item['Номер_мк'] = list_nar_start['Номер_мк']
        list_narjur.append(list_nar_start)
        list_narjur.append(item)

    set_exclude = set()
    static_fields = ('НомКплан','Номер_заказа','Номер_мк',"Наряд№","Подтвержден",'Пномер_жур',"Факт мин.","Труды в ЕРП",'Примечание')
    joined_list = []
    for i, item in enumerate(list_narjur):
        if  item['Пномер_жур'] in set_exclude:
            continue
        tmp_dict_block = {k: v for k, v in item.items() if k in static_fields}
        tmp_dict_block['Старт'] = ''
        tmp_dict_block['Дата старт'] = ''
        tmp_dict_block['Стоп'] = ''
        tmp_dict_block['Дата стоп'] = ''
        tmp_dict_block["БД"]  = ''
        tmp_dict_block['Выгружено в ЕРП минут'] = ''
        tmp_dict_block['Дата выгрузки в ЕРП'] = ''

        if item['Статус'] == "Начат":
            tmp_dict_block['Старт'] = item['Статус']
            tmp_dict_block['Дата старт'] = item['Дата']
            if item['Дата_выгрузки_ЕРП'] != "":
                tmp_dict_block['Дата выгрузки в ЕРП'] = item['Дата_выгрузки_ЕРП']
                tmp_dict_block['Выгружено в ЕРП минут'] = item['Минут_выгружено_ЕРП']
                tmp_dict_block["БД"] = item["БД"]
            if tmp_dict_block['Номер_мк'] == 0:
                tmp_dict_block['Труды в ЕРП'] = 0
            set_exclude.add(item['Пномер_жур'])
            for j in range(i+1, len(list_narjur)):
                if list_narjur[j]['Пномер_жур'] not in set_exclude and list_narjur[j]['Номер_мк'] == item['Номер_мк'] and \
                    list_narjur[j]['Наряд№'] == item['Наряд№'] and \
                    list_narjur[j]['Статус'] != item['Статус'] and \
                     F.strtodate(list_narjur[j]['Дата']) > F.strtodate(item['Дата']):
                    tmp_dict_block['Стоп'] = list_narjur[j]['Статус']
                    tmp_dict_block['Дата стоп'] = list_narjur[j]['Дата']
                    if list_narjur[j]['Примечание'] != '':
                        tmp_dict_block['Примечание'] += ";" + list_narjur[j]['Примечание']
                    set_exclude.add(list_narjur[j]['Пномер_жур'])
                    break
        else:
            tmp_dict_block['Стоп'] = item['Статус']
            tmp_dict_block['Дата стоп'] = item['Дата']
            set_exclude.add(item['Пномер_жур'])
        joined_list.append(tmp_dict_block)

    joined_list = F.sort_by_column_c(joined_list, 'Дата старт',date_time=True)
    joined_list = F.sort_by_column_c(joined_list,'Наряд№')
    joined_list = F.sort_by_column_c(joined_list, 'Номер_мк')

    for item in joined_list:
        item['Примечание'] = item.pop('Примечание')

    CQT.fill_wtabl(joined_list,tbl,height_row=24,auto_type=False)
    CMS.fill_filtr_c(self,self.ui.tbl_report_add_filtr,tbl,hidden_scroll=True)
    CMS.update_width_filtr(tbl,self.ui.tbl_report_add_filtr)
    CMS.fill_summ_tbl(self,self.ui.tbl_report_add_summ,tbl,set_name_calc={"Факт мин.","Труды в ЕРП",},average=False)

    nf_py = CQT.num_col_by_name_c(tbl,'Номер_заказа')
    nf_db = CQT.num_col_by_name_c(tbl, 'БД')
    nf_state = CQT.num_col_by_name_c(tbl,'Стоп')
    nf_norma = CQT.num_col_by_name_c(tbl, "Труды в ЕРП")
    nf_time_erp = CQT.num_col_by_name_c(tbl, 'Выгружено в ЕРП минут')

    obj_color_bad = CMS.Color_tbl(0)
    obj_color_good = CMS.Color_tbl(100)
    obj_color_middle = CMS.Color_tbl(50)

    for i in range(tbl.rowCount()):
        if tbl.item(i,nf_db).text() != '' and tbl.item(i,nf_db).text() != self.USER_CONFIG.ERP_base_name['Значение']:
            CQT.set_color_wtab_c(tbl,i,nf_db,*obj_color_bad.rgb)
        if tbl.item(i,nf_py).text() == 'ПРОСТОЙ':
            CQT.set_color_wtab_c(tbl,i,nf_py,*obj_color_bad.rgb)
        if tbl.item(i, nf_state).text() == 'Завершен':
            CQT.set_color_wtab_c(tbl, i, nf_state, *obj_color_good.rgb)
        if tbl.item(i, nf_state).text() == 'Приостановлен':
            CQT.set_color_wtab_c(tbl, i, nf_state, *obj_color_middle.rgb)
        if tbl.item(i, nf_time_erp).text() != '':
            if tbl.item(i, nf_norma).text() != tbl.item(i, nf_time_erp).text():
                CQT.set_color_wtab_c(tbl, i, nf_time_erp, *obj_color_bad.rgb)
            else:
                CQT.set_color_wtab_c(tbl, i, nf_time_erp, *obj_color_good.rgb)

def add_6_hours(date:str|datetime.datetime,mask:str="%Y-%m-%d %H:%M:%S",minus=False):
    h = 1
    if minus:
        h = h * -1
    if isinstance(date,datetime.datetime):
        return F.date_add_time(date, hours=h)
    else:
        if F.is_date(date,mask):
           return F.datetostr(F.date_add_time(F.strtodate(date, mask), hours=h),mask)


@CQT.progress_decorator
@CQT.onerror
def post_block_to_erp(self:mywindow,hook_prog_bar=None,*args):
    fl_custom_etap = False
    foreced_ref = False

    if 'shift' in CQT.get_key_modifiers(self):#Выбор этапа вручную
        fl_custom_etap = True

    if self.global_arm_oper_user_fio == None:
        CQT.msgbox(f'Не выбран работник')
        return

    hook_prog_bar.open()
    hook_prog_bar.set(0)
    hook_prog_bar.text('Проверки')


    tbl = self.ui.tbl_report_add
    old_row = tbl.currentRow()
    old_colmn = tbl.currentColumn()
    tbl_etap = self.ui.tbl_viev_etaps_name
    old_row_etap = tbl_etap.currentRow()
    old_colmn_etap = tbl_etap.currentColumn()

    row = CQT.get_dict_line_form_tbl(tbl)
    if row == {}:
        CQT.msgbox(f'Не выбран блок журнала')
        return
    if row['Дата выгрузки в ЕРП'] != '':
        CQT.msgbox(f'Уже выгружено {row["Дата выгрузки в ЕРП"]}')
        return
    fio = self.global_arm_oper_user_fio
    s_num_jur = int(row['Пномер_жур'])
    s_num_kpl = int(row['НомКплан'])
    s_num_nar = int(row['Наряд№'])
    if s_num_kpl == 0:
        CQT.msgbox(f'Пустой КПЛ')
        return


    if fl_custom_etap:
        ref_current_etap = None

        t = CQT.TableContext(tbl)
        if t.current_row().no_selection:
            return
        current_jur_obj = DTCLS.module_arm_oper.current_jur_obj
        if current_jur_obj is None:
            CQT.msgbox(f"Не выбрана строка в таблице")
            return
        dict_info_zp, err = current_jur_obj.get_data_etap_erp_from_kpl(int(t.current_row().value('НомКплан')),self.db_kplan)
        if dict_info_zp is None:
            CQT.msgbox(err)
            return



        key_zp = dict_info_zp['Ref_Key_py']

        wet_req_text = f"""ВЫБРАТЬ
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Ссылка)) КАК _ref,
                    ЭтапПроизводства2_2.НаименованиеЭтапа КАК НаименованиеЭтапа,
                    ЭтапПроизводства2_2.Номер КАК Номер,
                    ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Статус) КАК Статус,
                    ЭтапПроизводства2_2.Комментарий КАК Комментарий,
                    ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Организация) КАК Организация,
                    ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Подразделение) КАК Подразделение,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Подразделение.Ссылка)) КАК _ref_Подразделение,
                    ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Спецификация) КАК Спецификация,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Спецификация)) КАК _Спецификация_ref,
                    ЭтапПроизводства2_2.Спецификация.Код КАК _Спецификация_code,
                    
                    ПРЕДСТАВЛЕНИЕ(ЭтапПроизводства2_2.Распоряжение) КАК Распоряжение,
                    
                    ЭтапПроизводства2_2.Дата КАК Дата,

                    ЭтапПроизводства2_2.НЭ_НулевойЭтап КАК Нулевой,
                    ЭтапПроизводства2_2.ФактическоеНачалоЭтапа,
                    ЭтапПроизводства2_2.ФактическоеОкончаниеЭтапа
                ИЗ
                    Документ.ЭтапПроизводства2_2 КАК ЭтапПроизводства2_2
                        ЛЕВОЕ СОЕДИНЕНИЕ Документ.ЗаказНаПроизводство2_2.Продукция КАК ЗаказНаПроизводство2_2Продукция
                        ПО (ЭтапПроизводства2_2.Спецификация = ЗаказНаПроизводство2_2Продукция.Спецификация
                        И ЗаказНаПроизводство2_2Продукция.Ссылка = &Распоряжение)
                ГДЕ
                    ЭтапПроизводства2_2.Распоряжение = &Распоряжение
                   
                    И ЭтапПроизводства2_2.ПометкаУдаления = ЛОЖЬ
                    И ЭтапПроизводства2_2.Проведен = ИСТИНА
                                    """
        refs = APIERP.Refs_wet(wet_req_text)
        ref_res = APIERP.Ref_wet('Распоряжение', 'Документы.ЗаказНаПроизводство2_2', key_zp)
        refs.add_ref(ref_res)

        key, data_rez = APIERP.get_wet_request(wet_req_text, refs=refs)

        if key == 200:
            list_etaps = data_rez['data']
        else:
            CQT.msgbox(f'Ошибка {key}')
            return

        def fnc_oform_tbl(tbl,*args):
            t = CQT.TableContext(tbl)
            t.hide_if_not_dev(CFG)
            for row in t.rows():
                row.apply_bool_emo('Нулевой')
                row.set_value('Дата',F.dateStrToStr(row.value('Дата'),"%Y-%m-%dT%H:%M:%S","%d.%m.%Y %H:%M:%S",''))
                row.set_value('ФактическоеНачалоЭтапа',F.dateStrToStr(row.value('Дата'),"%Y-%m-%dT%H:%M:%S","%d.%m.%Y %H:%M:%S",''))
                row.set_value('ФактическоеОкончаниеЭтапа',F.dateStrToStr(row.value('Дата'),"%Y-%m-%dT%H:%M:%S","%d.%m.%Y %H:%M:%S",''))
            pass


        selected_etap = CQT.msgboxg_get_table(self,'Выберите этап',list_etaps,styleSheet=CQT.MES_CSS,
                                              selectRows=True,ExtendedSelection=False,selection_from_tbl=True,func_oform_tbl=fnc_oform_tbl)
        if not selected_etap:
            return

        ref_current_etap =selected_etap['_ref']
        foreced_ref = True
    else:
        t_etaps = CQT.TableContext(tbl_etap)
        current_etap_row_o = t_etaps.current_row()
        if current_etap_row_o.no_selection:
            if not t_etaps.tbl.rowCount():
                return
            elif t_etaps.tbl.rowCount() == 1:
                current_etap_row_o = t_etaps.get_row(0)
            else:
                self.show()
                CQT.blink_widget_border(t_etaps.tbl,2,msg=f'Не выбран этап')
                return #Ref_Key
        ref_current_etap = current_etap_row_o.value('Ref_Key')

    if ref_current_etap is None:
        return
    
    

    jur_obj = CMS.Jurnal_nar(self.bd_naryad,s_num_nar,fio)
    jur_obj.set_selected_fragment(s_num_jur)
    if jur_obj.selected_fragment_end_date == None:
        CQT.msgbox(f'Значение "Стоп" наряда {row["Наряд№"]} не установлено')
        return
    #if F.strtodate(jur_obj.selected_fragment_start_date).date() != F.strtodate(add_6_hours( jur_obj.selected_fragment_end_date,minus=True)).date():
    #    CQT.msgbox(f'Дата закрытия блока наряда {row["Наряд№"]} не совпадает с началом')
    #    return
    if row['Стоп'] == "Завершен" and row['Подтвержден'] == '':
        if not CQT.msgboxgYN(f'Завершенный наряд {row["Наряд№"]} не подтвержден',btn0_name='Продолжить',
                             btn1_name='Выход',fontsize=16,icon_str='Question'):
            return
    hook_prog_bar.set(5)
    hook_prog_bar.text('Подготовка данных')
    dict_for_update_mes_db, list_data_for_update_mes_db, err = (
        jur_obj.create_data_trdz_for_erp(self, s_num_kpl, self.db_kplan,
                                                s_num_nar, self.bd_users, self.db_resxml,
                                                self.DICT_PROFESSIONS,
                                         DICT_VID_RABOT=self.Data.DICT_VID_RABOT,
                                         ref_current_etap=ref_current_etap,foreced_ref=foreced_ref))
    if dict_for_update_mes_db == None:
        CQT.msgbox(err)
        return

    hook_prog_bar.set(10)
    hook_prog_bar.text('Обработка 1С...')
    resp, msg = APIERP.post_trdz_json(dict_for_update_mes_db,erp_base_name=self.ERP_base_name)
    if resp != 200:
        if resp == 500:
            CQT.msgbox(f'В Пномер_жур №{s_num_jur}\n{msg}\nКод ошибки {resp}')
        else:
            CQT.msgbox(f'В Пномер_жур №{s_num_jur}\nОшибка отправки. Код ошибки {resp}')
        return
    hook_prog_bar.set(90)
    hook_prog_bar.text('Оформление результата')
    jur_obj.update_mes_db_trdz(list_data_for_update_mes_db)
    fill_tbl_report_add(self)
    report_add_itemSelectionChanged(self,row)
    recalc_min_vigr_ERP_in_tbl_report(self)
    CQT.select_cell(tbl,old_row,old_colmn)
    CQT.select_cell(tbl_etap, old_row_etap, old_colmn_etap)
    hook_prog_bar.close()
    CQT.msgbox(f'Успешно',time_life=0.5)
    pass
@CQT.progress_decorator
@CQT.onerror
def del_block_to_erp(self:mywindow,hook_prog_bar=None,*args):
    if self.global_arm_oper_user_fio == None:
        CQT.msgbox(f'Не выбран работник')
        return
    hook_prog_bar.open()
    hook_prog_bar.set(0)
    hook_prog_bar.text('Проверки')
    tbl = self.ui.tbl_report_add
    old_row = tbl.currentRow()
    old_colmn = tbl.currentColumn()
    tbl_etap = self.ui.tbl_viev_etaps_name
    old_row_etap = tbl_etap.currentRow()
    old_colmn_etap = tbl_etap.currentColumn()


    row = CQT.get_dict_line_form_tbl(tbl)
    if  row == {}:
        CQT.msgbox(f'Не выбран блок журнала')
        return
    if row['Дата выгрузки в ЕРП'] == '':
        CQT.msgbox(f'Еще не выгружено')
        return
    if row['БД'] != '' and row['БД'] != self.USER_CONFIG.ERP_base_name['Значение']:
        CQT.msgbox(f'БД ЕРП не совпадает с БД загрузки Трудов')
        return

    fio = self.global_arm_oper_user_fio
    s_num_jur = int(row['Пномер_жур'])
    s_num_kpl = int(row['НомКплан'])
    s_num_nar = int(row['Наряд№'])
    jur_obj = CMS.Jurnal_nar(self.bd_naryad,s_num_nar,fio)
    jur_obj.set_selected_fragment(s_num_jur)
    if F.strtodate(jur_obj.selected_fragment_start_date).date() != F.strtodate(add_6_hours(jur_obj.selected_fragment_end_date,minus=True)).date():
        CQT.msgbox(f'Дата закрытия блока наряда {row["Наряд№"]} не совпадает с началом')
        return
    if row['Стоп'] == "Завершен" and row['Подтвержден'] == '':
        CQT.msgbox(f'Завершенный наряд {row["Наряд№"]} не подтвержден')
        return
    hook_prog_bar.set(5)
    hook_prog_bar.text('Подготовка данных')
    file_and_data_for_update_mes_db = jur_obj.load_data_trdz_for_erp(self,s_num_kpl,self.db_kplan,s_num_nar,self.bd_users,self.db_resxml)
    if file_and_data_for_update_mes_db == None:
        return
    fl_naid_key_row_for_delete = False
    list_etaps_for_del = []
    m = ODAT.OrdersComposit(self.ERP_base_name)
    for py_data in file_and_data_for_update_mes_db[0].values():
        Ref_Key_py = py_data['Ref_Key_py']
        for etap_name, val_etap in py_data['Этапы'].items():
            resp = m.get_response('Document_ЭтапПроизводства2_2', f"""?$filter=Number eq '{etap_name}' 
             and Распоряжение_Key eq guid'{Ref_Key_py}' &$select=Ref_Key, Статус, Трудозатраты/LineNumber, Трудозатраты/НомерЧертежа, 
         Трудозатраты/ДатаВыполнения, Трудозатраты/ВидРабот_Key, Трудозатраты/Количество, Трудозатраты/Исполнитель""")
            if resp:
                etap_Ref= resp[0]['Ref_Key']
            else:
                CQT.msgbox(f'Этап {etap_name} не найден в ЕРП')
                return
            set_trdz_form_erp = {_['НомерЧертежа'] for _ in resp[0]['Трудозатраты']}
            for item in val_etap['Традозатраты']:
                list_etaps_for_del.append({'etap_Ref': etap_Ref,'etap_name':etap_name,'НомерЧертежа':item['Ключ_мес']})
                if item['Ключ_мес'] in set_trdz_form_erp:
                    fl_naid_key_row_for_delete =True
                    break

    if not fl_naid_key_row_for_delete:
        if not CQT.msgboxgYN(f'В ЕРП не найдены записи для удаления.\n'
                   f'Затереть отметку о выгрузке в МЕС?',btn1_name='Нет(выход)', fontsize=16,icon_str='Warning'):
            return
    else:
        hook_prog_bar.set(10)
        hook_prog_bar.text('Обработка 1С...')
        resp, msg = APIERP.delete_trdz_json(list_etaps_for_del,erp_base_name=self.ERP_base_name)
        if resp != 200:
            if resp == 500:
                CQT.msgbox(f'В Пномер_жур №{s_num_jur}\n{msg}\nКод ошибки {resp}')
            else:
                CQT.msgbox(f'В Пномер_жур №{s_num_jur}\nОшибка отправки. Код ошибки {resp}')
            return
        hook_prog_bar.set(90)
        hook_prog_bar.text('Оформление результата')
    jur_obj.update_mes_db_trdz(file_and_data_for_update_mes_db[1])
    fill_tbl_report_add(self)
    report_add_itemSelectionChanged(self,row)
    recalc_min_vigr_ERP_in_tbl_report(self)
    tbl.setFocus()
    CQT.select_cell(tbl, old_row, old_colmn)
    CQT.select_cell(tbl_etap,old_row_etap,old_colmn_etap)
    #fill_etaps_from_erp(self)
    CQT.msgbox(f'Успешно',time_life=0.5)
    pass


@CQT.progress_decorator
@CQT.onerror
def post_all_block_to_erp(self:mywindow,hook_prog_bar=None,*args):
    if self.global_arm_oper_user_fio == None:
        CQT.msgbox(f'Не выбран работник')
        return
    tbl = self.ui.tbl_report_add
    old_row = tbl.currentRow()
    old_colmn = tbl.currentColumn()
    rez_list = []
    EMOJ_OK= CEMOJ.EmojiMain.СтатусыПроизводства.success.symbol
    EMOJ_WARN = CEMOJ.EmojiMain.СтатусыПроизводства.warning.symbol
    EMOJ_ERR = CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol
    for i in range(tbl.rowCount()):
        if tbl.isRowHidden(i): # 12.12.25 по задаче 100061422
            continue
        fl_pass = False #fl_pass = True
        hook_prog_bar.open()
        hook_prog_bar.set(0)
        hook_prog_bar.text(f'{i+1}/{tbl.rowCount()} Проверки')
        row = CQT.get_dict_line_form_tbl(tbl,i)

        rez_list.append({'Строка таблицы':i+1,'Пномер_жур':row['Пномер_жур'],'Наряд№':row['Наряд№'],
                             'Номер_заказа':row['Номер_заказа'],'Результат':EMOJ_OK,'Прим.':''})
        info_dict = rez_list[-1]
        if row['Дата выгрузки в ЕРП'] != '':
            info_dict['Результат'] = EMOJ_WARN
            info_dict['Прим.'] = 'Дата выгрузка в ERP уже есть'
            if not fl_pass:
                continue
        if row['Номер_заказа'] == 'ПРОСТОЙ':
            info_dict['Результат'] = EMOJ_WARN
            info_dict['Прим.'] = 'Наряд не закреплен за проектом'
            if not fl_pass:
                continue
        fio = self.global_arm_oper_user_fio
        s_num_jur = int(row['Пномер_жур'])
        s_num_kpl = int(row['НомКплан'])
        s_num_nar = int(row['Наряд№'])
        jur_obj = CMS.Jurnal_nar(self.bd_naryad, s_num_nar, fio)
        jur_obj.set_selected_fragment(s_num_jur)
        if F.strtodate(jur_obj.selected_fragment_start_date).date() != F.strtodate(
                add_6_hours( jur_obj.selected_fragment_end_date,minus=True)).date():
            info_dict['Результат'] = EMOJ_WARN
            info_dict['Прим.'] = f'Дата закрытия блока наряда {row["Наряд№"]} не совпадает с началом'
            if not fl_pass:
                continue
        if row['Стоп'] == "Завершен" and row['Подтвержден'] == '':
            info_dict['Результат'] = EMOJ_WARN
            info_dict['Прим.'] = f'Завершенный наряд {row["Наряд№"]} не подтвержден'
            if not fl_pass:
                continue
        if jur_obj.selected_fragment_dict_row_start['Подытог_нормы'] == 0:
            info_dict['Результат'] = EMOJ_WARN
            info_dict['Прим.'] = f'Подытог_нормы к выгрузке = 0'
            if not fl_pass:
                continue
        hook_prog_bar.set(5)
        hook_prog_bar.text(f'{i+1}/{tbl.rowCount()} Подготовка данных')
        dict_for_update_mes_db, list_data_for_update_mes_db, err = jur_obj.create_data_trdz_for_erp(
                        self, s_num_kpl, self.db_kplan, s_num_nar,
                         self.bd_users, self.db_resxml,self.DICT_PROFESSIONS,DICT_VID_RABOT=self.Data.DICT_VID_RABOT)
        if dict_for_update_mes_db == None:
            info_dict['Результат'] = EMOJ_WARN
            info_dict['Прим.'] = f'Завершенный наряд {row["Наряд№"]} не подтвержден'
            if not fl_pass:
                continue

        check_state_etaps = True
        for pr, data_pr in dict_for_update_mes_db.items():
            for name_etap, etap_data in data_pr['Этапы'].items():
                key_etap = etap_data['ref_Key_etap']

                wet_req_text = f"""ВЫБРАТЬ 
                                    ЭтапПроизводства2_2.Статус КАК Статус
                                ИЗ
                                    Документ.ЭтапПроизводства2_2 КАК ЭтапПроизводства2_2
                                ГДЕ
                                    ЭтапПроизводства2_2.Ссылка = &Ссылка
                                """
                refs = APIERP.Refs_wet(wet_req_text)
                ref_res = APIERP.Ref_wet('Ссылка', 'Документы.ЭтапПроизводства2_2', key_etap)
                refs.add_ref(ref_res)

                key, data_rez = APIERP.get_wet_request(wet_req_text, refs=refs)

                if key != 200:
                    check_state_etaps = False
                    info_dict['Результат'] = EMOJ_ERR
                    info_dict['Прим.'] = f'Ошибка получения данных этапа {name_etap}, код ({key}) из ERP'
                    break
                state_etap =  data_rez['data'][0]['Статус']
                if state_etap == 'Начат':
                    if not fl_pass:
                        continue
                check_state_etaps =False
                info_dict['Результат'] = EMOJ_ERR
                info_dict['Прим.'] = f'Этап {name_etap} в статусе "{state_etap}"'
                break

        if not  check_state_etaps:
            if not fl_pass:
                continue
        hook_prog_bar.set(10)
        hook_prog_bar.text(f'{i+1}/{tbl.rowCount()}Обработка 1С...')
        resp, msg = APIERP.post_trdz_json(dict_for_update_mes_db,erp_base_name=self.ERP_base_name)
        if resp != 200:
            info_dict['Результат'] = EMOJ_ERR

            if resp == 500:
                info_dict['Прим.'] = f'В Пномер_жур №{s_num_jur}\n{msg}\nКод ошибки {resp}'
            else:
                info_dict['Прим.'] = f'В Пномер_жур №{s_num_jur}\nОшибка отправки. Код ошибки {resp}'
            if not fl_pass:
                continue
        rez_upd =  jur_obj.update_mes_db_trdz(list_data_for_update_mes_db)
        if not rez_upd :
            info_dict['Результат'] = EMOJ_ERR
            info_dict['Прим.'] = f"1С создан, но ошибка записи отметки в БД МЕС"


    hook_prog_bar.set(90)
    hook_prog_bar.text('Оформление результата')
    fill_tbl_report_add(self)
    recalc_min_vigr_ERP_in_tbl_report(self)
    CQT.select_cell(tbl, old_row, old_colmn)
    def fnc_oform(tbl:CQT.QtWidgets.QTableWidget):
        t = CQT.TableContext(tbl)
        for row in t.rows():
            row.set_height(72)
    CQT.msgboxg_get_table_ok_inf(self,f'Результат выполнения для {self.global_arm_oper_user_fio}',rez_list,styleSheet=CQT.MES_CSS,showMaximized=True,func_oform_tbl=fnc_oform)
    return


@CQT.onerror
def recalc_min_vigr_ERP_in_tbl_report(self:mywindow,*args):
    data_nach = self.ui.le_start_of_period.text()
    data_kon = self.ui.le_end_of_period.text()

    tbl = self.ui.tbl_report_c
    nf_post_erp = CQT.num_col_by_name_c(tbl, 'Минут_выгружено_ЕРП')
    row = CQT.get_dict_line_form_tbl(tbl)


    custom_request_c = f"""SELECT sum(Подытог_нормы) AS "Сумм_Минут_нормы" , sum(Минут_выгружено_ЕРП) AS "Минут_выгружено_ЕРП" 
    FROM (SELECT jurnal.Подытог_нормы, jurnal.Минут_выгружено_ЕРП  
     FROM jurnal INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
    WHERE jurnal.ФИО = "{row['ФИО']}" AND jurnal.Подытог <> 0 AND jurnal.Статус = 'Начат' 
    and datetime(jurnal.Дата) > datetime("{data_nach}") 
    and datetime(jurnal.Дата) <= datetime("{data_kon}"));"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    if rez_jur == None or rez_jur == False:
        return

    if F.valm(row["Сумм_Минут"]) > 0:
        row["Минут_выгружено_ЕРП"] = f'{rez_jur[0]["Минут_выгружено_ЕРП"]}({round(rez_jur[0]["Минут_выгружено_ЕРП"] / rez_jur[0]["Сумм_Минут_нормы"] * 100)}%)'
        tbl.item(tbl.currentRow(),nf_post_erp).setText(row["Минут_выгружено_ЕРП"])
    koef = 0
    val_summ_min = rez_jur[0]["Сумм_Минут_нормы"]
    if val_summ_min > 0:
        val_erp_min =rez_jur[0]["Минут_выгружено_ЕРП"]
        koef = round(val_erp_min / val_summ_min * 100)
    obj_col = CMS.Color_tbl(koef)

    CQT.set_color_wtab_c(tbl, tbl.currentRow(), nf_post_erp, obj_col.r, obj_col.g, obj_col.b)




@CQT.onerror
def load_data_etaps_from_erp(self,*args):
    if self.global_arm_oper_user_fio == None:
        CQT.msgbox(f'Не выбран работник')
        return
    tbl = self.ui.tbl_viev_etaps_name
    row = CQT.get_dict_line_form_tbl(tbl)
    if row == {}:
        CQT.msgbox(f'Не выбран этап"')
        return

    rez_list_trdz = []
    if row["Ref_Key"] == '':
        return
    m = ODAT.OrdersComposit(self.ERP_base_name)

    resp = m.get_response('Document_ЭтапПроизводства2_2',f"""?$filter=Ref_Key eq guid'{row["Ref_Key"]}' 
    &$select=Ref_Key, Статус, Трудозатраты/LineNumber, Трудозатраты/НомерЧертежа, 
         Трудозатраты/ДатаВыполнения, Трудозатраты/ВидРабот_Key, Трудозатраты/Количество, Трудозатраты/Исполнитель""")
    if resp == None:
        CQT.msgbox(f'Ошибка получения данных с сервера "{self.ERP_base_name}"')
        return rez_list_trdz
    if resp:
        for item_trdz in resp[0]['Трудозатраты']:
            if item_trdz['ВидРабот_Key'] in self.Data.DICT_TRDZ:
                item_trdz['ВидРабот_Key'] = self.Data.DICT_TRDZ[item_trdz['ВидРабот_Key']]
            if item_trdz['Исполнитель'] != '' and item_trdz['Исполнитель'] in self.Data.DICT_REF_USERS:
                item_trdz['Исполнитель'] = self.Data.DICT_REF_USERS[item_trdz['Исполнитель']]
            item_trdz["etap_name"] = row["Номер"]
            item_trdz["etap_Ref"] = row["Ref_Key"]
            item_trdz['НомерЧертежа'] = str(item_trdz['НомерЧертежа'])
            item_trdz["ДатаВыполнения"]  = F.datetostr(F.strtodate(item_trdz["ДатаВыполнения"],"%Y-%m-%dT%H:%M:%S"))
            rez_list_trdz.append(item_trdz)
    else:
        CQT.msgbox(f'Этап {row["Номер"]} не найден в ЕРП')

    return rez_list_trdz


@CQT.onerror
def calc_list_names_etaps(self,dict_line_form_tbl=None,*args):
    if self.global_arm_oper_user_fio == None:
        CQT.msgbox(f'Не выбран работник')
        return
    tbl = self.ui.tbl_report_add
    if dict_line_form_tbl== None:
        row = CQT.get_dict_line_form_tbl(tbl)
        if row == {}:
            CQT.msgbox(f'Не выбран блок журнала')
            return
        if row['НомКплан'] == '0' or row['Номер_мк'] == '0':
            return
    else:
        row = dict_line_form_tbl
    DTCLS.module_arm_oper.current_row_jurnal = row
    fio = self.global_arm_oper_user_fio
    s_num_jur = int(row['Пномер_жур'])
    s_num_kpl = int(row['НомКплан'])
    s_num_nar = int(row['Наряд№'])
    jur_obj = CMS.Jurnal_nar(self.bd_naryad,s_num_nar,fio)
    jur_obj.set_selected_fragment(s_num_jur)

    DTCLS.module_arm_oper.current_jur_obj = jur_obj  # для использования в ручном выборе этапа

    dict_for_update_mes_db, list_data_for_update_mes_db, err = (
        jur_obj.create_data_trdz_for_erp(self, s_num_kpl, self.db_kplan, s_num_nar,
                      self.bd_users, self.db_resxml,self.DICT_PROFESSIONS,DICT_VID_RABOT=self.Data.DICT_VID_RABOT))
    if dict_for_update_mes_db == None:
        CQT.msgbox(err)
        return
    list_refs_names = []

    rez_dict = dict()
    for py, py_val in dict_for_update_mes_db.items():
        ref_key = py_val['Ref_Key_py']
        for etap_name, etap in py_val['Этапы'].items():
            if 'Традозатраты' in etap:
                for dict_line in etap['Традозатраты']:
                    if etap_name not in rez_dict:
                        rez_dict[etap_name] = {"X":False,'Номер':etap_name, "Название":"",
                                               "Статус":"","Минут":0,"Ref_Key":"",
                                               'ФактНачало':"",
                                               'ФактОкончание':""
                                               }
                        list_refs_names.append({'etap_name':etap_name,"ref_key":ref_key})
                    rez_dict[etap_name]["Минут"] += dict_line['Количество_мин']
    if list_refs_names == []:
        CQT.msgbox(f'Видов работ для выгрузки в наряде не обнаружено(см. состав операций)')
        return [[]]

    it = DTCLS.module_arm_oper.current_row_jurnal
    etaps_o = APIERP.Etaps_erp(it['НомКплан'])
    if etaps_o.err:
        return
    current_podr = DTCLS.app_self.current_podr_text
    list_filtered_etaps = etaps_o.filtered_by_podr(current_podr)

    for etap in list_filtered_etaps:
        if not etap.Номер in rez_dict:
            rez_dict[etap.Номер] = {"X":False,'Номер':etap.Номер,"Название":"","Статус":"",
                                    "Минут":0,"Ref_Key":"",'ФактНачало':"",'ФактОкончание':""}
        rez_dict[etap.Номер]["Статус"] = etap.Статус
        rez_dict[etap.Номер]["Название"] = etap.НаименованиеЭтапа
        rez_dict[etap.Номер]["Ref_Key"] = etap.ref
        rez_dict[etap.Номер]["X"] = etap.emoj_deletion_mark
        if etap.ФактическоеНачалоЭтапа:
            rez_dict[etap.Номер]["ФактНачало"] = F.datetostr(
                etap.ФактическоеНачалоЭтапа, "%Y-%m-%d")
        if etap.ФактическоеОкончаниеЭтапа:
            rez_dict[etap.Номер]["ФактОкончание"] = F.datetostr(
                etap.ФактическоеОкончаниеЭтапа, "%Y-%m-%d")


    for etap in rez_dict.values():
        etap['Минут'] = round(etap['Минут'],3)

    rez_list = F.list_of_dicts_to_list_of_lists(list(rez_dict.values()))
    return rez_list
@CQT.onerror
def show_history_nar(self:mywindow,*args):
    row  = CQT.get_dict_line_form_tbl(self.ui.tbl_report_add)
    if row == {}:
        CQT.msgbox(f'Не выбрана строка')
        return
    obj_jur = CMS.Jurnal_nar(self.bd_naryad,int(row['Наряд№']))
    rez = CQT.msgboxg_get_table(self,"Журнал работ",obj_jur.rows,disable_btn0=True,btn1_name='ОК')
    return


@CQT.onerror
def show_structure_nar(self:mywindow,*args):
    row  = CQT.get_dict_line_form_tbl(self.ui.tbl_report_add)
    if row == {}:
        CQT.msgbox(f'Не выбрана строка')
        return
    obj_nar = CMS.Naryads(int(row['Наряд№']),self.bd_naryad,self.Data.DICT_DOLGN_ETAP,self.bd_users,self.Data.DICT_EMPL_FULL)
    obj_nar.get_mk(self.db_resxml,True)
    for row in obj_nar.params:
        row['Код проф'] = 'Не найден в БД'
        row['Прим. проф'] = 'Не найден в БД'
        row['Прямые затраты'] = 'Не найден в БД'
        for dse in obj_nar.mk.res:
            if dse['Номерпп'] == row['ДСЕ_ID']:
                for oper in dse['Операции']:
                    if oper['Опер_номер'] == row['Операции_номер']:
                        row['Код проф'] = oper['Опер_профессия_код']
                        row['Этап'] = oper['Этап']
                        row['Опер_РЦ_код'] = oper['Опер_РЦ_код']
                        row['Опер_РЦ_наименование'] = oper['Опер_РЦ_наименование']
                        if row['Код проф'] in self.DICT_PROFESSIONS:
                            row['Прим. проф'] = self.DICT_PROFESSIONS[row['Код проф']]['примечание']
                            row['Прямые затраты'] = self.DICT_PROFESSIONS[row['Код проф']]['Прямые']
                        break
                break
    rez = CQT.msgboxg_get_table(self,"Структура наряда",obj_nar.params,disable_btn0=True,btn1_name='ОК')
    return

@CQT.onerror
def btn_delete_block_from_etap(self:mywindow,*args):
    tbl = self.ui.tbl_viev_etaps_erp

    row = CQT.get_dict_line_form_tbl(tbl)
    if row == {}:
        CQT.msgbox(f'Не выбрана запись этапа')
        return
    old_row = tbl.currentRow()
    old_colmn = tbl.currentColumn()

    if row['Исполнитель'] == '' or row['ДатаВыполнения'] == '0001-01-01 00:00:00' or row['НомерЧертежа'] == '':
        CQT.msgbox(f'Удалять плановые записи нельзя')
        return
    if  row['НомерЧертежа'].count('_') == 1:
        CQT.msgbox(f'Удалять объектные строки нельзя')
        return
    data_ = {'etap_Ref':row['etap_Ref'],
             'etap_name':row['etap_name'],
             'НомерЧертежа':row['НомерЧертежа'],}
    if not CQT.msgboxgYN(f"В этапе {row['etap_name']} будет удалена запись НомерЧертежа: `{row['НомерЧертежа']}`\nПродолжить?"):
        return
    resp, msg = APIERP.delete_trdz_json([data_], erp_base_name=self.ERP_base_name)
    if resp != 200:
        if resp == 500:
            CQT.msgbox(f'В записи № {row["LineNumber"]}\n{msg}\nКод ошибки {resp}')
        else:
            CQT.msgbox(f'В записи {row["LineNumber"]}\nОшибка отправки. Код ошибки {resp}')
        return

    viev_etaps_name_itemSelectionChanged(self)
    tbl.setFocus()
    CQT.select_cell(tbl, old_row, old_colmn)

    CQT.msgbox(f'Успешно',time_life=0.5)
    pass


@CQT.onerror
def btn_add_etap_erp(self:mywindow, *args):
    current_podr = DTCLS.app_self.current_podr_text
    if current_podr not in self.DICT_PODR_RC:
        CQT.msgbox(f'Для {current_podr} связь не настроена')
        return
    code_podr = self.DICT_PODR_RC[current_podr]['Код']
    ref_podr = self.DICT_PODR_RC[current_podr]['ref_СтруктураПредприятия']

    it = DTCLS.module_arm_oper.current_row_jurnal
    etaps_o = APIERP.Etaps_erp(it['НомКплан'])
    list_permited_etap = etaps_o.get_permited_to_create_etaps(code_podr)
    if not list_permited_etap:
        CQT.msgbox(f"Этапы к созданию по {current_podr} отсутствуют")
        return
    def fnc_oform(tbl,*args):
        t = CQT.TableContext(tbl)
        t.hide_if_not_dev(DTCLS.CONFIG)
        for row in t.rows():
            clr = row.value('_color')
            clr_o = CMS.Color(clr)
            clr_o = clr_o.align_colors(level_percent=-30, saturation_percent=-20,copy=True)
            row.set_color_font(*clr_o.rgb,col_name= 'Этап')

    rez = CQT.msgboxg_get_table(self,'Выбрать этап для создания',list_permited_etap,styleSheet=CQT.MES_CSS,
                                selection_from_tbl=True,ExtendedSelection=False,selectRows=True,func_oform_tbl=fnc_oform)
    if not rez:
        return
    name_new_etap = rez['Этап']
    rez, err_data = etaps_o.create_new_etap(name_new_etap,ref_podr)
    if not rez or rez != 200:
        if err_data:
            CQT.msgboxg_get_table_ok_inf(self,"Ошибка создания",err_data,styleSheet=CQT.MES_CSS)
        else:
            CQT.msgbox(f'Неизвестная ошибка 1С')
        return
    self.tbl_report_add_itemSelectionChanged()
    CQT.msgbox(f"Этап {err_data['ИмяЭтапа']} {name_new_etap} создан")




@CQT.onerror
def btn_start_etap_erp(self:mywindow, *args):
    tbl = self.ui.tbl_viev_etaps_name
    row = CQT.get_dict_line_form_tbl(tbl)
    if row == {}:
        CQT.msgbox(f'Не выбрана строка')
        return
    ref_key = row['Ref_Key']
    name_obj = row['Номер']
    code, state = APIERP.patch_state_doc_znpr(ref_key,name_obj,{"Статус": "Начат","ФактическоеНачалоЭтапа":F.now("%d.%m.%Y %H:%M:%S")},erp_base_name=self.ERP_base_name)
    if code != 200:
        CQT.msgbox(state)
        return
    report_add_itemSelectionChanged(self,)
    return 

@CQT.onerror
def fill_etaps_from_erp(self,*args):
    tbl_view = self.ui.tbl_viev_etaps_erp
    tbl_add = self.ui.tbl_report_add
    rez_list_trdz = load_data_etaps_from_erp(self)
    CQT.fill_wtabl(rez_list_trdz, tbl_view,height_row=20,auto_type=False,ogr_maxshir_kol=400)
    tbl_view.setStyleSheet(CQT.ERP_CSS)
    nf_etap_ref =  CQT.num_col_by_name_c(tbl_view, 'etap_Ref')
    if nf_etap_ref == None:
        return
    tbl_view.setColumnHidden(nf_etap_ref,True)
    CMS.fill_filtr_c(self, self.ui.tbl_viev_etaps_erp_filtr, tbl_view, hidden_scroll=True)
    CMS.update_width_filtr(tbl_view, self.ui.tbl_viev_etaps_erp_filtr)
    row_tbl_add = CQT.get_dict_line_form_tbl(tbl_add)
    if row_tbl_add == {}:
        return
    nf_num_chert = CQT.num_col_by_name_c(tbl_view,'НомерЧертежа')

    for i in range(tbl_view.rowCount()):
        if tbl_view.item(i,nf_num_chert).text().split("_")[0] == row_tbl_add['Пномер_жур']:
            for j in range(tbl_view.columnCount()):
                CQT.font_cell_size_format(tbl_view,i,j,bold=True)
        if tbl_view.item(i,nf_num_chert).text() == '':
            for j in range(tbl_view.columnCount()):
                CQT.font_cell_size_format(tbl_view,i,j,italic=True)
                CQT.set_font_color_wtab_c(tbl_view,i,j,100,100,100)



@CQT.onerror
def viev_etaps_name_itemSelectionChanged(self:mywindow,*args):
    tbl = self.ui.tbl_viev_etaps_name
    tbl_view = self.ui.tbl_viev_etaps_erp
    CQT.clear_tbl(tbl_view)
    row = CQT.get_dict_line_form_tbl(tbl)
    if row == {}:
        CQT.msgbox(f'Не выбран этап')
        return
    if row['Статус'] in ("Формируется","Сформирован","КВыполнению","Завершен"):
        self.ui.btn_start_etap_erp.setEnabled(True)
    else:
        self.ui.btn_start_etap_erp.setEnabled(False)
    fill_etaps_from_erp(self)


@CQT.onerror
def report_add_itemSelectionChanged(self,dict_line_form_tbl=None,*args):
    lbl_report = CQT.CustLabel(self.ui.lbl_sort_c_report)
    report_name = lbl_report.get_user_data()
    if report_name == 'labor_costs':
        tbl_name = self.ui.tbl_viev_etaps_name
        data = calc_list_names_etaps(self,dict_line_form_tbl)
        CQT.clear_tbl(tbl_name)
        if data == None:
            return
        CQT.fill_wtabl(data,tbl_name,auto_type=False)
        tbl_name.setStyleSheet(CQT.ERP_CSS)
        nf_ref = CQT.num_col_by_name_c(tbl_name, 'Ref_Key')
        if nf_ref:
            tbl_name.setColumnHidden(nf_ref, True)
        obj_col_bad = CMS.Color_tbl(10)
        obj_col_good = CMS.Color_tbl(90)
        nf_state = CQT.num_col_by_name_c(tbl_name,'Статус')
        for i in range(tbl_name.rowCount()):
            if tbl_name.item(i,nf_state).text() != "Начат":
                CQT.set_color_wtab_c(tbl_name,i,nf_state,obj_col_bad.r,obj_col_bad.g,obj_col_bad.b)
            else:
                CQT.set_color_wtab_c(tbl_name, i, nf_state, obj_col_good.r, obj_col_good.g, obj_col_good.b)
