from __future__ import annotations

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from MKart import mywindow


@CQT.onerror
def fill_pull(self: mywindow, *args, **kwargs):
    CQT.clear_tbl(self.ui.tbl_cld_plan_summ)
    CQT.clear_tbl(self.ui.tbl_pull_poz)
    if Month_plan.file == None:
        return
    start_day, end_day = F.start_end_dates_c(Month_plan.month, "%Y-%m-%d", 'm', '')
    self.ui.lbl_current_moth_pl.setText(Month_plan.month)
    list_pnums = list(Month_plan.file.keys())
    req = f"""SELECT plan.Пномер, napravlenie.name as "Направление", пл_оуп.№ERP, пл_оуп.№проекта,plan.Позиция, "План" as "Тип", 
    пл_оуп.Номенклатура_ЕРП, 
    пл_топ.Спецификация_ЕРП, пл_топ.Спецификация_код_ЕРП, "Штука" as "Ед. изм.", пл_оуп.Вес_кг as "Вес",
    пл_оуп.Количество as "Количество_заказ", "" as "Количество", "" as "Дата", "" as "Статус РС" , 
    status_poz.Имя as "Статус проекта", "" as "Примечание", "" as "Всего н-смен на поз." FROM plan 
        INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер, 
        пл_топ ON пл_топ.НомПл = plan.Пномер,  

         napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
         status_poz ON status_poz.Пномер = plan.Статус, 
        napravlenie ON napravlenie.Пномер = napravl_deyat.Направление WHERE plan.poki = {self.place.poki} AND plan.Пномер IN ({CSQ.prepare_list_to_tuple(list_pnums)})"""
    rez = CSQ.custom_request_c(self.db_kplan, req, rez_dict=True)
    list_vid_rab = CMS.get_shablon_vidov(self.DICT_PROFESSIONS)
    if rez == []:
        CQT.clear_tbl(self.ui.tbl_pull_poz)
        return
    dict_napravl = dict()
    dict_gant = dict()
    for i in range(len(rez)):
        poz = CMS.Pozition(rez[i]['Пномер'], self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self, True)
        dict_gant_time = poz.get_norm_by_range_dates(start_day, end_day, self.LIST_PROFESSIONS)
        for etap, val in dict_gant_time.items():
            if etap not in dict_gant:
                dict_gant[etap] = 0
            dict_gant[etap] += val
        min_count = rez[i]['Количество_заказ']
        norma_poz = 0
        dict_napravl[rez[i]['Пномер']] = rez[i]['Направление']
        for vid_r in list_vid_rab:
            if vid_r not in Month_plan.file[rez[i]['Пномер']]['Группы_работ']:
                Month_plan.file[rez[i]['Пномер']]['Группы_работ'][vid_r] = {'Заверш_н_см': 0, 'Норма_н_см': 0,
                                                                            'Остаток_н_см': 0, 'Остаток_шт': 0}

            if Month_plan.file[rez[i]['Пномер']]['Группы_работ'][vid_r]['Норма_н_см'] > 0:
                if Month_plan.file[rez[i]['Пномер']]['Группы_работ'][vid_r]['Остаток_шт'] < min_count:
                    min_count = Month_plan.file[rez[i]['Пномер']]['Группы_работ'][vid_r]['Остаток_шт']
                norma_poz += Month_plan.file[rez[i]['Пномер']]['Группы_работ'][vid_r]['Норма_н_см']

            rez[i][vid_r] = round(Month_plan.file[rez[i]['Пномер']]['Группы_работ'][vid_r]['Остаток_н_см'], 2)

        if rez[i]["Спецификация_код_ЕРП"] != '':
            rez[i]["Статус РС"] = "Создана"
        rez[i]["Дата"] = Month_plan.file[rez[i]['Пномер']]['max_date']
        rez[i]["Всего н-смен на поз."] = round(norma_poz, 2)

        if 'Количество' not in Month_plan.file[rez[i]['Пномер']] or Month_plan.file[rez[i]['Пномер']][
            'Количество'] == -1:
            Month_plan.file[rez[i]['Пномер']]['Количество'] = F.round_up(min_count)
        rez[i]['Количество'] = Month_plan.file[rez[i]['Пномер']]['Количество']

        if 'Примечание' in Month_plan.file[rez[i]['Пномер']]:
            rez[i]['Примечание'] = Month_plan.file[rez[i]['Пномер']]['Примечание']
        if 'Тип' in Month_plan.file[rez[i]['Пномер']]:
            rez[i]['Тип'] = Month_plan.file[rez[i]['Пномер']]['Тип']
    editeble_col_nomera = {"Количество", "Примечание"}
    CQT.fill_wtabl(rez, self.ui.tbl_pull_poz, auto_type=False, set_editeble_col_nomera=editeble_col_nomera,
                   height_row=24)
    calc_fill_svod_and_get_dict_summ_plan(self, dict_napravl, dict_gant)


def btn_set_poz_vnepl(self: mywindow):
    row = CQT.get_dict_line_form_tbl(self.ui.tbl_pull_poz)
    if row == dict():
        return
    pnum = int(row['Пномер'])
    if pnum in Month_plan.file:

        if row['Тип'] == 'План':
            Month_plan().set_type(pnum, 'Внеплан')
        else:
            Month_plan().set_type(pnum, 'План')
    fill_pull(self)


def btn_pull_poz_del_all(self: mywindow):
    clear_plan(self)
    fill_pull(self)


def btn_pull_poz_del(self: mywindow):
    row = CQT.get_dict_line_form_tbl(self.ui.tbl_pull_poz)
    if row == dict():
        return
    pnum = int(row['Пномер'])
    if pnum in Month_plan.file:
        Month_plan.file.pop(pnum)
    fill_pull(self)

#++ 06.06.2025 (по задаче 100055177 )
@CQT.onerror
def btn_pull_poz_add_all(self: mywindow):
    tbl_kpl = self.ui.tbl_kal_pl
    if Month_plan.month == None:
        return CQT.msgbox(f'Не выбран месяц')
    list_rows_kpl = CQT.list_from_wtabl_c(tbl_kpl, rez_dict=True, only_visible=True)
    pnoms = [pl['plan.Пномер'] for pl in list_rows_kpl]
    pozitions = CMS.Pozitions(pnoms, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users)
    usr_messages = [['Номер КПЛ', 'Сообщение']]
    for pnom, pozition in pozitions.dict_pozs.items():
        errors_cur_iter = []
        pozition.load_kpl_table('пл_оуп')
        error = recalc_nsmen_by_count_izd(self, pozition, alert_msgbox=False)
        if error:
            errors_cur_iter.append([pnom, error])
        self.current_poz_for_pull_poz = pozition
        if self.current_poz_for_pull_poz.Статус_норм != 2:
            errors_cur_iter.append([pnom, f'Позиция статус норм не По ТК'])
        if Month_plan.file == None:
            errors_cur_iter.append([pnom, f'Не иницализирован месяц'])
        s_num = int(self.current_poz_for_pull_poz.Пномер)
        usr_messages.extend(errors_cur_iter)
        if len(errors_cur_iter) == 0:
            Month_plan.file[s_num] = {'Группы_работ': self.current_poz_for_pull_poz.dict_vid_rab_tmp,
                                      'max_date': self.current_poz_for_pull_poz.max_date,
                                      'Примечание': '',
                                      'Количество': -1
                                      }
    fill_pull(self)
    if usr_messages:
        CQT.msgboxg_get_table_ok_inf(self, 'Номера кпл невошедшие в выборку', usr_messages, show_filtr=False)
# --06.06.2025 (по задаче 100055177 )

@CQT.onerror
def btn_pull_all_update(self: mywindow):
    tbl = self.ui.tbl_pull_poz
    for i in range(tbl.rowCount()):
        row = CQT.get_dict_line_form_tbl(tbl, i)
        clck_tbl_kal_pl(self, int(row['Пномер']))
        s_num = int(self.current_poz_for_pull_poz.Пномер)
        if 'dict_vid_rab_tmp' not in self.current_poz_for_pull_poz.__dict__:

            CQT.msgbox(f'По поз.№{4150} ошибка')
            return
        Month_plan.file[s_num] = {'Группы_работ': self.current_poz_for_pull_poz.dict_vid_rab_tmp,
                                  'max_date': self.current_poz_for_pull_poz.max_date,
                                  'Примечание': '',
                                  'Количество': F.valm(row['Количество'])
                                  }
    fill_pull(self)
    self.ui.tbl_kal_pl.setFocus()
    CQT.msgbox(f'Успешно')


@CQT.onerror
def btn_pull_poz_update(self: mywindow):
    row = CQT.get_dict_line_form_tbl(self.ui.tbl_pull_poz)
    if not F.is_numeric(row['Количество']):
        CQT.msgbox(f'Количество не число')
        return
    if 'current_poz_for_pull_poz' not in self.__dict__:
        CQT.msgbox(f'Не выбрана позиция')
        return
    if self.current_poz_for_pull_poz.Статус_норм != 2:
        CQT.msgbox(f'Позиция статус норм не По ТК')
        return
    if Month_plan.month == None:
        CQT.msgbox(f'Не выбран месяц')
        return
    if Month_plan.file == None:
        CQT.msgbox(f'Не иницализирован месяц')
        return
    s_num = int(self.current_poz_for_pull_poz.Пномер)
    Month_plan.file[s_num] = {'Группы_работ': self.current_poz_for_pull_poz.dict_vid_rab_tmp,
                              'max_date': self.current_poz_for_pull_poz.max_date,
                              'Примечание': '',
                              'Количество': F.valm(row['Количество'])
                              }
    fill_pull(self)
    self.ui.tbl_kal_pl.setFocus()


@CQT.onerror
def btn_pull_poz_add(self: mywindow, *args, **kwargs):
    # row = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl)
    if 'current_poz_for_pull_poz' not in self.__dict__:
        CQT.msgbox(f'Не выбрана позиция')
        return
    if self.current_poz_for_pull_poz.Статус_норм != 2:
        CQT.msgbox(f'Позиция статус норм не По ТК')
        return
    if Month_plan.month == None:
        CQT.msgbox(f'Не выбран месяц')
        return
    if Month_plan.file == None:
        CQT.msgbox(f'Не иницализирован месяц')
        return
    s_num = int(self.current_poz_for_pull_poz.Пномер)
    if s_num in Month_plan.file:
        CQT.msgbox(f'ПОзиция {s_num} уже добавлена')
        return
    Month_plan.file[s_num] = {'Группы_работ': self.current_poz_for_pull_poz.dict_vid_rab_tmp,
                              'max_date': self.current_poz_for_pull_poz.max_date,
                              'Примечание': '',
                              'Количество': -1
                              }
    fill_pull(self)
    self.ui.tbl_kal_pl.setFocus()


@CQT.onerror
def save_local_pl(self: mywindow, *args):
    path = CMS.load_tmp_path("local_pl_poz")
    put_ima = CQT.f_dialog_save(self, 'Сохранить план', path + F.sep() + f'{Month_plan.month}_Poz_plan.pickle',
                                "*.pickle")
    if put_ima == '.':
        return
    CMS.save_tmp_path('local_pl_poz', put_ima, True)

    F.write_file_c(put_ima, {'data': Month_plan.file, 'month': Month_plan.month}, separ='', pickl=True)
    CQT.msgbox('Успешно')
    pass


@CQT.onerror
def load_local_pl(self: mywindow, *args):
    if not CQT.msgboxgYN(f'Не сохраненные данные потеряются, Загрузить?'):
        return
    path = CMS.load_tmp_path("local_pl_poz")
    put_ima = CQT.f_dialog_name(self, 'Выбрать план', path, "*.pickle", True)
    if put_ima == '.':
        return
    file = F.load_file_pickle(put_ima)
    try:
        load_plan(self, file['data'], file['month'])
    except:
        CQT.msgbox(f'Ошикба загрузки файла')
        return
    fill_pull(self)


@CQT.onerror
def reselect_month(self: mywindow, *args):
    tbl = self.ui.tbl_cld_plan_workforce
    row = CQT.get_dict_line_form_tbl(tbl)
    month = row['Дата']
    if not CQT.msgboxgYN(f'Переопределить месяц текущей выборки {Month_plan.month} на {month}?'):
        return
    Month_plan.month = month
    self.ui.lbl_current_moth_pl.setText(Month_plan.month)
    pass


def select_month(self: mywindow):
    tbl = self.ui.tbl_cld_plan_workforce
    month = tbl.item(tbl.currentRow(), 0).text()
    if Month_plan.month == None:
        load_plan(self, dict(), month)
        self.ui.lbl_current_moth_pl.setText(Month_plan.month)


def recalc_nsmen_by_count_izd(self: mywindow, poz, alert_msgbox: bool = True):
    poz.load_kpl_table('пл_топ')
    vid_po_napr = poz.dict_tables['пл_топ']['Вид']
    napr_deyat = poz.Направление_деятельности
    koef_vneplana = 1
    if vid_po_napr in self.Data_plan.DICT_VID_PO_NAPR:
        koef_vneplana = 1 + self.Data_plan.DICT_VID_PO_NAPR[vid_po_napr]['vneplan_percent']
    koef_pogr_norm = self.Data_plan.DICT_NAPRAVLENIE[self.Data_plan.DICT_NAPR_DEYAT[napr_deyat]['Направление']][
        'koef_pogr_norm']

    error = poz.calc_osvoeno(self.DICT_PROFESSIONS, self.DICT_OP_NAME, koef_vneplana, koef_pogr_norm)
    if error and alert_msgbox: # 06.06.2025 (по задаче 100055177 ) (спам msgbox в итерации)
        CQT.msgbox(error)
    fill_tbl_pull_etap(self, poz)
    return error


@CQT.onerror
def calc_row_tbl_pull_etaps(self: mywindow, *args, **kwargs):
    def check_new_val(self: mywindow):
        new_val = tbl.item(tbl.currentRow(), tbl.currentColumn()).text()
        if not F.is_numeric(new_val):
            CQT.msgbox(f'Введено не число')
            return False
        if F.valm(new_val) > get_old_val(self):
            CQT.msgbox(f'Количество больше допустимого')
            return False
        if F.valm(new_val) < 0:
            CQT.msgbox(f'Количество меньше допустимого')
            return False
        return True

    def get_old_val(self: mywindow):
        r = tbl.currentRow()
        c = tbl.currentColumn()
        list_list = F.dict_of_dicts_to_list_of_lists(self.current_poz_for_pull_poz.dict_vid_rab_tmp)
        return list_list[r + 1][c]

    def set_old_val(self: mywindow):
        r = tbl.currentRow()
        c = tbl.currentColumn()
        tbl.item(r, c).setText(str(get_old_val(self)))

    tbl = self.ui.tbl_pull_etaps
    if tbl.currentColumn() != CQT.num_col_by_name_c(tbl, 'Остаток_шт'):
        return
    if not check_new_val(self):
        set_old_val(self)
        return
    r = tbl.currentRow()
    c = tbl.currentColumn()
    nf_vid_rab = 0
    nf_ost_n_min = CQT.num_col_by_name_c(tbl, 'Остаток_н_см')
    new_val = F.valm(tbl.item(r, c).text())
    vid_rab = tbl.item(r, nf_vid_rab).text()
    count_izd = self.current_poz_for_pull_poz.dict_tables['пл_оуп']['Количество']
    norma = self.current_poz_for_pull_poz.dict_vid_rab[vid_rab]['Норма_н_см']
    new_norma = round(norma / count_izd * new_val, 2)

    self.current_poz_for_pull_poz.dict_vid_rab_tmp[vid_rab]['Остаток_н_см'] = new_norma
    tbl.item(r, nf_ost_n_min).setText(str(new_norma))


def corr_tbl_pull_etaps(self: mywindow):
    # if not self.ui.tbl_pull_etaps.hasFocus():
    #    CQT.clear_tbl(self.ui.tbl_pull_etaps)
    #    return
    calc_row_tbl_pull_etaps(self)


@CQT.onerror
def fill_tbl_pull_etap(self: mywindow, poz):
    if 'dict_vid_rab_tmp' not in poz.__dict__:
        return
    tbl = self.ui.tbl_pull_etaps
    tbl.blockSignals(True)
    CQT.fill_wtabl(poz.dict_vid_rab_tmp, tbl, {'Остаток_шт'}, 40, 10, 20, auto_type=False, hide_head_rows=True,
                   StretchLastSection=False)

    tbl_width = tbl.verticalHeader().width() + 10
    tbl_height = tbl.horizontalHeader().height() + 10
    for j in range(0, tbl.columnCount()):
        try:
            CQT.set_color_text_header_wtab_horisontal_c(tbl, j, 111, 11, 11, 8, False)
        except:
            pass
        tbl.setColumnWidth(j, 80)
        tbl_width += tbl.columnWidth(j)

    for i in range(0, tbl.rowCount()):
        r, g, b = None,None,None
        CQT.font_cell_size_format(tbl, i, 0, 6)
        tbl_height += tbl.rowHeight(i)

        for key in self.DICT_PROFESSIONS.keys():
            if self.DICT_PROFESSIONS[key]['nick_name'] == tbl.item(i, 0).text():
                r, g, b = F.hex_to_rgb(self.DICT_PROFESSIONS[key]['color'][1:])
        if r != None:
            CQT.set_color_wtab_c(tbl, i, 0, r, g, b)
    # tbl.setFixedWidth(tbl_width)
    # tbl.setFixedHeight(tbl_height)
    self.ui.lbl_count_pull_poz.setText(str(poz.dict_tables['пл_оуп']['Количество']))
    tbl.blockSignals(False)


def clck_tbl_kal_pl(self: mywindow, s_nom_kpl: int = None):
    if s_nom_kpl == None:
        tbl = self.ui.tbl_kal_pl
        # ======ПРИ СОСТАВЛЕНИИ ПЛАНА==========
        row = CQT.get_dict_line_form_tbl(tbl)
        if 'plan.Пномер' not in row:
            return
        s_nom_kpl = int(row['plan.Пномер'])
    pozition = CMS.Pozition(s_nom_kpl, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
    pozition.load_kpl_table('пл_оуп')

    recalc_nsmen_by_count_izd(self, pozition)
    self.current_poz_for_pull_poz = pozition




def calc_fill_svod_and_get_dict_summ_plan(self: mywindow, dict_napravl, dict_gant):

    #LIST_SUMM_SB = ('Сборка_н_см', 'Сварка_н_см', 'Зачистка_н_см')
    #TODO

    month = Month_plan.month
    list_vid_rab = CMS.get_shablon_vidov(self.DICT_PROFESSIONS)

    dict_gant = {k: 0 for k in list_vid_rab}
    dict_gant_adopt = dict()

    dict_workface = {k: 0 for k in list_vid_rab}
    percent = {k: 0 for k in list_vid_rab}

    for copmosite_gr, copmosite_gr_val  in self.Data_plan.DICT_COMPOSITE_PODRAZD.items():
        list_vid_rab.insert(copmosite_gr_val['sort'], copmosite_gr)
        dict_workface[copmosite_gr] = 0
        dict_gant_adopt[copmosite_gr] = 0

    for etap in list_vid_rab:
        if etap in dict_gant:
            dict_gant_adopt[etap] = round(dict_gant[etap] / 480)
        else:
            dict_gant_adopt[etap] = 0

    dict_summ = {k: 0 for k in list_vid_rab}
    dict_napr_summ = dict()


    for copmosite_gr, copmosite_gr_val  in self.Data_plan.DICT_COMPOSITE_PODRAZD.items():
        LIST_SUMM_SB = [_ for _ in copmosite_gr_val['dict_input_fields'].values()]
        for vid_r_s in LIST_SUMM_SB:
            dict_workface[copmosite_gr] += round(Month_plan.tabel_workforce_pull_poz_pl[month][vid_r_s] / 480, 2)
            dict_gant_adopt[copmosite_gr] += dict_gant_adopt[vid_r_s]
            dict_gant_adopt[copmosite_gr] = round(dict_gant_adopt[copmosite_gr])

    for vid_r in dict_summ.keys():
        for key in Month_plan.file.keys():
            norm = 0
            if vid_r in self.Data_plan.DICT_COMPOSITE_PODRAZD.keys():
                LIST_SUMM_SB =[_ for _ in  self.Data_plan.DICT_COMPOSITE_PODRAZD[vid_r]['dict_input_fields'].values()]
                for vid_r_s in LIST_SUMM_SB:
                    dict_summ[vid_r] += Month_plan.file[key]['Группы_работ'][vid_r_s]['Остаток_н_см']
                    norm += Month_plan.file[key]['Группы_работ'][vid_r_s]['Остаток_н_см']
            else:
                dict_summ[vid_r] += Month_plan.file[key]['Группы_работ'][vid_r]['Остаток_н_см']
                norm += Month_plan.file[key]['Группы_работ'][vid_r]['Остаток_н_см']
            if key not in dict_napravl:
                CQT.msgbox(f'{key} отсутствует в {dict_napravl}')
                return
            napr = dict_napravl[key]
            if napr not in dict_napr_summ:
                dict_napr_summ[napr] = dict()
            if vid_r not in dict_napr_summ[napr]:
                dict_napr_summ[napr][vid_r] = 0
            dict_napr_summ[napr][vid_r] += norm

        percent[vid_r] = 0
        if vid_r in self.Data_plan.DICT_COMPOSITE_PODRAZD.keys():
            dict_workface[vid_r] = round(dict_workface[vid_r], 2)
        else:
            dict_workface[vid_r] = round(Month_plan.tabel_workforce_pull_poz_pl[month][vid_r] / 480, 2)

        if dict_workface[vid_r] > 0:
            percent[vid_r] = round(dict_summ[vid_r] / dict_workface[vid_r] * 100, 2)
    list_of_lists = F.list_of_dicts_to_list_of_lists([dict_workface, dict_gant_adopt, dict_summ, percent])
    list_of_lists[0].insert(0, 'Поле')
    list_of_lists[1].insert(0, 'Табель')
    list_of_lists[2].insert(0, 'Гант')
    list_of_lists[3].insert(0, 'Сумма')
    list_of_lists[4].insert(0, 'Наполн.%')
    for napr in self.Data_plan.DICT_NAPRAVLENIE.values():
        name = napr['name']
        val = napr['val']
        name_row_napr = f'{name} {val}%'

        if name in dict_napr_summ:
            row_napr = [round(dict_napr_summ[name][k] / dict_summ[k] * 100, 2) if dict_summ[k] > 0 else 0 for k in
                        list_vid_rab]
            row_napr.insert(0, name_row_napr)
            list_of_lists.append(row_napr)

    tbl_summ = self.ui.tbl_cld_plan_summ
    CQT.fill_wtabl(list_of_lists, tbl_summ, height_row=24, head_column=0)
    for j in range(tbl_summ.columnCount()):
        val = F.valm(tbl_summ.item(3, j).text())
        r = 254 - val / 100 * 254
        g = val / 100 * 254
        CQT.set_color_wtab_c(tbl_summ, 3, j, r, g, 0)
    for i in range(5, len(list_of_lists)):
        val_max = F.valm(list_of_lists[i][0].split()[-1].replace("%", ''))
        if val_max == 0:
            val_max = 1
        for j in range(1, len(list_of_lists[0])):
            val = list_of_lists[i][j]
            r = 254 - val / val_max * 254
            r = r * (-1) if r < 1 else r
            g = 254 - r
            CQT.set_color_wtab_c(tbl_summ, i - 1, j, r, g, 0)


@CQT.onerror
def adapt_pl_with_gant(self: mywindow, mode='left_right'):
    if Month_plan.month == None:
        CQT.msgbox(f'Не выбран месяц')
        return
    if Month_plan.file == None:
        CQT.msgbox(f'Не иницализирован месяц')
        return
    napr_adapt = self.ui.cmb_for_adapt.currentText()
    if napr_adapt == '':
        CQT.msgbox(f'Не выбрано направление')
        return
    start_date_obj, end_date_obj = F.start_end_dates_c(Month_plan.month, "%Y-%m-%d", 'm', '')
    tbl = self.ui.tbl_pull_poz
    if 'shift' in CQT.get_key_modifiers(self):
        list_pnoms_pozitions = [_ for _ in Month_plan.file.keys()]

        postfix_msg = 'ы все позиции стакана'
    else:
        row = CQT.get_dict_line_form_tbl(tbl)
        if len(row) == 0:
            CQT.msgbox(f'Не выбрана позиция')
            return
        list_pnoms_pozitions = [int(row["Пномер"])]
        postfix_msg = f'a позиция {row["Пномер"]}'
    pozitions = CMS.Pozitions(list_pnoms_pozitions, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self,
                              True)
    for poz in pozitions.dict_pozs.values():
        dict_range = poz.get_norm_by_range_dates(start_date_obj, end_date_obj, self.LIST_PROFESSIONS, mode=mode)
        for etap, item in Month_plan.file[poz.Пномер]['Группы_работ'].items():
            if etap != napr_adapt:
                continue
            if mode == 'after_right':
                if etap in dict_range:
                    time_per_month = dict_range[etap] / 480
                    if time_per_month == 0:
                        continue
                    if item['Остаток_н_см'] == 0:
                        koef = 0
                    else:
                        koef = (item['Остаток_н_см'] - time_per_month) / item['Остаток_н_см']
                    item['Остаток_н_см'] -= time_per_month
                    item['Остаток_н_см'] = round(item['Остаток_н_см'], 2)
                    if item['Остаток_н_см'] < 0:
                        item['Остаток_н_см'] = 0
                        item['Остаток_шт'] = 0
                    else:
                        item['Остаток_шт'] = round(item['Остаток_шт'] * koef, 2)
            else:
                time_per_month = 0
                if etap in dict_range:
                    time_per_month = dict_range[etap] / 480
                if item['Остаток_н_см'] > time_per_month:
                    item['Остаток_н_см'] = round(time_per_month, 2)
                    if item['Остаток_н_см'] == 0:
                        item['Остаток_шт'] = 0
                    else:
                        item['Остаток_шт'] = round(item['Остаток_шт'] * time_per_month / item['Остаток_н_см'], 2)
    fill_pull(self)
    CQT.msgbox(f'Успешно обновлен{postfix_msg}')


def cld_pl_apply_filtr_month(self: mywindow):
    if Month_plan.month == None:
        CQT.msgbox(f'Не выбран месяц')
        return
    if Month_plan.file == None:
        CQT.msgbox(f'Не иницализирован месяц')
        return

    last_date_obj = F.start_end_dates_c(Month_plan.month, "%Y-%m-%d", 'm', '')[1]
    if not CQT.msgboxgYN(f""" Фильтр по этапам производства <= {last_date_obj} и статусам "Подготовка", 
    "Изготовление",  
    "К производству" \n\nпродолжить?"""):
        return
    list_pnoms_pozitions = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Пномер FROM plan 
     LEFT JOIN status_poz ON status_poz.Пномер = plan.Статус WHERE plan.poki = {self.place.poki} AND status_poz.Имя IN (
    "Подготовка", 
    "Изготовление",  
    "К производству" );""", hat_c=False, one_column=True)
    pozitions = CMS.Pozitions(list_pnoms_pozitions, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
    list_s_nums = []
    for poz in pozitions.dict_pozs.values():
        if poz.Статус in (2, 3, 7) and poz.МК != 0:  # Подготовка Изготовление К производству
            for field in poz.row_dates_etap_plan.keys():
                if poz.row_dates_etap_plan[field] != '':
                    if F.strtodate(poz.row_dates_etap_plan[field]) <= last_date_obj:
                        list_s_nums.append(str(poz.Пномер))
                        break
    str_pnums = '|'.join(list_s_nums)
    CMS.fill_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, {'plan.Пномер': str_pnums}, True)
    CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl)


def fill_list_month_pozplan(self: mywindow):
    rez = CSQ.custom_request_c(self.db_kplan, f"""SELECT Дата,file_poz_plan as Файл  FROM mnts_plan WHERE poki = {self.place.poki};""", rez_dict=True)
    Month_plan.tabel_workforce_pull_poz_pl = CMS.load_tabel_workforce(self.db_kplan, self.DICT_PROFESSIONS,
                                                                      self.DICT_VID_RABOT)
    set_dates_mnts = {_['Дата'] for _ in rez}
    fl_update = False
    for data in Month_plan.tabel_workforce_pull_poz_pl:
        if data not in set_dates_mnts:
            fl_update = True
            CSQ.custom_request_c(self.db_kplan, f"""INSERT INTO mnts_plan
                                  (Дата, poki) 
                                  VALUES (?,?);""", list_of_lists_c=[[data,self.place.poki]])
    if fl_update:
        rez = CSQ.custom_request_c(self.db_kplan, f"""SELECT Дата,file_poz_plan as Файл  FROM mnts_plan WHERE poki = {self.place.poki}""",
                                   rez_dict=True)
    rez_filtred = []

    for i in range(len(rez)):
        if rez[i]['Дата'] in Month_plan.tabel_workforce_pull_poz_pl:
            if rez[i]['Файл'] == None:
                rez[i]['Файл'] = ''
            else:
                rez[i]['Файл'] = "*"
            rez_filtred.append(rez[i])

    tbl = self.ui.tbl_cld_plan_workforce
    rez_filtred = F.sort_by_column_c(rez_filtred,'Дата',date_time=True,date_format="%Y-%m-%d")
    CQT.fill_wtabl(rez_filtred, tbl, {}, 120, 15, 20, auto_type=False, hide_head_rows=True)
    # tbl.setFixedWidth(self.ui.tbl_pull_etaps.width())


@CQT.onerror
def apply_diap_dates_to_sb_in_tbl(self: mywindow, *args):
    month = self.ui.cmb_apply_diap_dates_to_sb_in_tbl.currentText()
    str_pnums = ''
    if month == "Не в плане":
        set_kpls = set()
        rez = CSQ.custom_request_c(self.db_kplan,
                                   f"""SELECT file_poz_plan FROM mnts_plan WHERE poki = {self.place.poki} and file_poz_plan is not null;""",
                                   one_column=True, hat_c=False)
        for item in rez:
            data_pl = F.from_binary_pickle(item)
            set_kpls = set_kpls.union({str(_) for _ in data_pl.keys()})
        rez_snums = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Пномер, plan.Группа FROM plan INNER JOIN  status_poz ON 
        status_poz.Пномер == plan.Статус WHERE plan.Пномер NOT IN ({CSQ.prepare_list_to_tuple(list(set_kpls))}) AND 
         plan.poki = {self.place.poki} AND status_poz.Имя IN ("К производству","Подготовка");""",
                                         one_column=False,rez_dict=True)


        str_pnums = '|'.join([str(_["Пномер"]) for _ in rez_snums])  # '(?!3273|3332)
        reg_groups = ''
        if self.ui.chk_kpl_groups.isChecked():
            str_groups = '|'.join([str(_["Группа"]) for _ in rez_snums if _["Группа"] != '' ])  #
            str_pnums = str_pnums + '|-1'
            reg_groups = rf"'^\s*(?:{str_groups})?\s*$"
        sp_znch = {'plan.Пномер': str_pnums}#, 'plan.Группа':reg_groups}


    else:
        if not F.is_date(month, "%Y-%m-%d"):
            CQT.msgbox('Не выбран месяц')
            return
        rez = CSQ.custom_request_c(self.db_kplan, f"""SELECT file_poz_plan FROM mnts_plan WHERE poki = {self.place.poki} and Дата ="{month}";""")


        data_pl = F.from_binary_pickle(rez[-1][0])
        list_noms = [str(_) for _ in data_pl.keys()]
        reg_groups = ''
        if self.ui.chk_kpl_groups.isChecked():
            rez_groups = CSQ.custom_request_c(self.db_kplan, f"""SELECT DISTINCT plan.Группа FROM plan 
             WHERE plan.Пномер IN ({CSQ.prepare_list_to_tuple(list(data_pl.keys()))}) and plan.Группа != '';""",
                                             one_column=True, hat_c=False)
            list_noms.append('-1')
            str_groups = '|'.join([str(_) for _ in rez_groups])  #
            reg_groups = rf"'^\s*(?:{str_groups})?\s*$"
        str_pnums = '|'.join(list_noms)
        sp_znch = {'plan.Пномер': str_pnums}#, 'plan.Группа':reg_groups}
    CMS.fill_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, sp_znch, True)
    CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl)
    CMS.apply_gui_groups(self)

def load_poz_pl_from_db(self: mywindow):
    # F.from_binary_pickle(res[-1][0])
    if not CQT.msgboxgYN(f'Не сохраненные данные потеряются, Загрузить?'):
        return
    tbl = self.ui.tbl_cld_plan_workforce

    if tbl.item(tbl.currentRow(), 1) == None or tbl.item(tbl.currentRow(), 1).text() == '':
        return
    month = tbl.item(tbl.currentRow(), 0).text()
    rez = CSQ.custom_request_c(self.db_kplan, f"""SELECT file_poz_plan FROM mnts_plan WHERE mnts_plan.poki = {self.place.poki} AND Дата ="{month}";""")

    load_plan(self, F.from_binary_pickle(rez[-1][0]), month)

    fill_pull(self)



@CQT.onerror
def select_poz_from_pull(self: mywindow, *args):
    tbl_pull = self.ui.tbl_pull_poz
    tbl_plan = self.ui.tbl_kal_pl
    row = CQT.get_dict_line_form_tbl(tbl_pull)
    poz_num = row['Пномер']
    nf_poz = CQT.num_col_by_name_c(tbl_plan, 'plan.Пномер')
    for i in range(tbl_plan.rowCount()):
        if tbl_plan.item(i, nf_poz).text() == str(poz_num):
            tbl_plan.setCurrentCell(i, nf_poz)
            # tbl_plan.selectRow(i)
            clck_tbl_kal_pl(self)
            break


@CQT.onerror
def edit_handle_pl(self: mywindow):
    tbl = self.ui.tbl_pull_poz
    col = tbl.currentColumn()
    dict_row = CQT.get_dict_line_form_tbl(tbl)
    nom = int(dict_row['Пномер'])
    if tbl.horizontalHeaderItem(col).text() == 'Примечание':
        Month_plan.file[nom]['Примечание'] = dict_row['Примечание']
    if tbl.horizontalHeaderItem(col).text() == 'Количество':
        Month_plan.file[nom]['Количество'] = dict_row['Количество']


@CQT.onerror
def save_kpl_plan(self: mywindow):
    if Month_plan.file == "":
        CQT.msgbox(f'План не сформирован')
        return
    print(f'план сформирован')
    tbl = self.ui.tbl_cld_plan_workforce
    if tbl.item(tbl.currentRow(), 1).text() == '*':
        if not CQT.msgboxgYN(f'План был ранее сохранен, обновить?'):
            return
    month = tbl.item(tbl.currentRow(), 0).text()
    if month != Month_plan.month:
        CQT.msgbox(f'Сохранить план {Month_plan.month} в ячейку {month} невозможно')
        return
    print(f'месяц определен')
    if len(Month_plan.file) == 0:
        print(f'длина Month_plan.file = 0')
        if tbl.item(tbl.currentRow(), 1).text() == '':
            print(f'Пустое сохранение')
            return
        if CQT.msgboxgYN(f'План пустой, затереть данные?'):
            CSQ.custom_request_c(self.db_kplan, f'''UPDATE mnts_plan SET file_poz_plan = ? WHERE Дата = ? and poki == {self.place.poki};''',
                                 list_of_lists_c=[None, month])
            tbl.item(tbl.currentRow(), 1).setText('')
            CQT.msgbox(f'Успешно')
            return

    blob1 = F.to_binary_pickle(Month_plan.file)
    CSQ.custom_request_c(self.db_kplan, f'''UPDATE mnts_plan SET file_poz_plan = ? WHERE Дата = ? and poki == {self.place.poki};''',
                         list_of_lists_c=[blob1, month])
    tbl.item(tbl.currentRow(), 1).setText('*')
    dict_db = {_['nick_name']: _['mnts_plan_names'] for _ in self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN.values()}
    DICT_GROUP_VID_RAB_FOR_PLAN_by_mnts_plan_name = F.deploy_dict_c(F.list_of_lists_to_list_of_dicts(F.dict_of_dicts_to_list_of_lists(self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN,'name')),'mnts_plan_names')
    rez_dict = {_: 0 for _ in dict_db.values()}
    rez_dict_kg = {_['name']: 0 for _ in self.Data_plan.DICT_NAPRAVLENIE.values()}
    list_pnums = list(Month_plan.file.keys())
    extra_data_plan = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Пномер, napravlenie.name FROM plan 
        INNER JOIN 
         napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
         
        napravlenie ON napravlenie.Пномер = napravl_deyat.Направление WHERE plan.poki = {self.place.poki} AND plan.Пномер IN ({CSQ.prepare_list_to_tuple(list_pnums)})""",
                                           rez_dict=True)
    extra_data_plan = F.deploy_dict_c(extra_data_plan, 'Пномер')
    for nom_poz, item in Month_plan.file.items():
        if 'Тип' in item and item['Тип'] != 'План':
            continue
        resp = CSQ.custom_request_c( #05.12.2025
            self.db_kplan,
            f"""
            UPDATE знпр 
            SET Дата_занесения_в_план_месяца = ? 
            WHERE s_num = (SELECT Пномер_ЗП FROM пл_оуп WHERE НомПл = {nom_poz}) AND Дата_занесения_в_план_месяца == ''""", #10.12.2025
            list_of_lists_c=[F.now('%Y-%m-%d')]
        )
        for rabot, dict_rabot in item['Группы_работ'].items():
            rabot_db = dict_db[rabot]
            rez_dict[rabot_db] += dict_rabot['Остаток_н_см']
            if rabot_db in DICT_GROUP_VID_RAB_FOR_PLAN_by_mnts_plan_name and DICT_GROUP_VID_RAB_FOR_PLAN_by_mnts_plan_name[rabot_db]['estimated']: #('Нормо_смены_сб', 'Нормо_смены_св', 'Нормо_смены_зачист'):
                # poz = CMS.Pozition(nom_poz,self.db_kplan,self.bd_naryad,self.db_resxml,self.db_users,'')
                # napr = poz.get_napravl()['name']
                napr = extra_data_plan[nom_poz]
                rez_dict_kg[napr] += dict_rabot['Остаток_н_см']*DICT_GROUP_VID_RAB_FOR_PLAN_by_mnts_plan_name[rabot_db]['koef_estimate']
    list_hats = [_ for _ in dict_db.values()]
    str_hats = ', '.join(list_hats)
    rez = CSQ.custom_request_c(self.db_kplan, f"""UPDATE mnts_plan SET ( {str_hats} ) = 
     ({CSQ.questions_for_mask(list_hats)}) WHERE Дата = '{month}' and poki == {self.place.poki}""",
                         list_of_lists_c=[[round(_, 2) for _ in rez_dict.values()]])
    if not rez:
        CQT.msgbox(f'Ошибка записи нормо-смен в mnts_plan')
        return
    list_hats = [_ for _ in rez_dict_kg.keys()]
    str_hats = ', '.join(list_hats)
    for key in rez_dict_kg.keys():
        rez_dict_kg[key] = round(rez_dict_kg[key], 2)
    CSQ.custom_request_c(self.db_kplan, f"""UPDATE mnts_plan SET ( {str_hats} ) = 
         ({CSQ.questions_for_mask(list_hats)}) WHERE Дата = '{month}' and poki == {self.place.poki}""",
                         list_of_lists_c=[[_ for _ in rez_dict_kg.values()]])
    CQT.msgbox(f'Успешно')


def clear_plan(self):
    self.ui.lbl_current_moth_pl.setText("")
    Month_plan.clear()


def load_plan(self, file, month):
    def fix_file_nmin_to_nsm(file):
        fixed_file = dict()
        for k, v in file.items():
            tmp_item = dict()
            tmp_groups = dict()
            for group_k, group_v in v['Группы_работ'].items():
                tmp_params = dict()
                for params, vals in group_v.items():
                    if '_н_мин' in params:
                        tmp_params[params.replace('_н_мин', '_н_см')] = round(vals / 480, 2)
                    else:
                        tmp_params[params] = vals
                tmp_groups[group_k] = tmp_params
            tmp_item['Группы_работ'] = tmp_groups
            for field in v.keys():
                if field == 'Группы_работ':
                    continue
                tmp_item[field] = v[field]

            fixed_file[k] = tmp_item
        return fixed_file

    self.ui.lbl_current_moth_pl.setText(month)
    Month_plan().update_data(fix_file_nmin_to_nsm(file), month)

    Month_plan.tabel_workforce_pull_poz_pl = CMS.load_tabel_workforce(self.db_kplan, self.DICT_PROFESSIONS,
                                                                      self.DICT_VID_RABOT)


class Month_plan():
    tabel_workforce_pull_poz_pl = []
    file = None
    month = None

    @classmethod
    def clear(cls):
        cls.file = None
        cls.month = None
        cls.tabel_workforce_pull_poz_pl = []

    def __init__(self):
        self.file = Month_plan.file
        self.month = Month_plan.month
        self.tabel_workforce_pull_poz_pl = Month_plan.tabel_workforce_pull_poz_pl

    def update_data(self, file, month):
        Month_plan.file = file
        Month_plan.month = month

    def set_type(self, pnum: int, type_poz: str):
        Month_plan.file[pnum]['Тип'] = type_poz
