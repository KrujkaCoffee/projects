from __future__ import annotations

import copy
import datetime

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite  as CSQ
import kal_plan as KPL
import gui_kal_plan as GKPL
import project_cust_38.Cust_mes as CMS

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow





def hover_tbl_pl_gaf_svod(self, event):
    tbl = self.ui.tbl_pl_gaf_svod
    row, column = CQT.get_hover_row_col(self, tbl, event)
    if row == None or column == None:
        return
    val = tbl.item(row, column).text()
    if val != '':
        set_tooltip_val(self, tbl, row+1, column)
    else:
        set_tooltip_val(self, tbl, row+1, column, True)


@CQT.onerror
@F.time_of_exec_cls_func_args_c
def load_tbl_gant(self:mywindow):
    def load_tabels(self:mywindow) -> dict:
        tbls = []
        tbl = self.ui.tbl_kal_pl
        nk_pnom = CQT.num_col_by_name_c(tbl,'plan.Пномер')
        nk_local_graf = CQT.num_col_by_name_c(tbl, 'plan.local_graf')
        for i in range(tbl.rowCount()):
            if not tbl.isRowHidden(i):
                tbls.append(tbl.item(i,nk_pnom).text())
        query = CSQ.custom_request_c(self.db_kplan,f"""SELECT plan.Пномер, plan.Позиция, plan.local_graf, plan.Приоритет, plan.fact_jurnal_blolb_data,  
        пл_оуп.№проекта, пл_оуп.№ERP, napravl_deyat.Псевдоним as Направление_деят, 
            napravlenie.name as Направление  FROM plan INNER JOIN
        пл_оуп ON пл_оуп.НомПл = plan.Пномер,
        napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности, 
            napravlenie ON napravlenie.Пномер = napravl_deyat.Направление 
         WHERE plan.Пномер in ({','.join(tbls)}) and plan.poki = {self.place.poki} ORDER BY plan.Приоритет DESC""",rez_dict=True)
        if query == False or len(query) == 0:
            return False
        for item in query:
            if item['local_graf'] == '':
                datat_bin = CMS.update_local_graf(self, True, int(item['Пномер']), False )
                print(f"Создан локальный график на {item['Пномер']}")
                #tbl.item(i, nk_local_graf).setText(str(datat_bin))
        return query

    def generate_full_table(self,query:dict):
        list_errs = []
        set_dates = set()
        dict_dates_vals = dict()
        for item in query:
            if item['local_graf'] == None or F.from_binary_pickle(item['local_graf']) == None:
                print()
                print(f'Пномер {item["Пномер"]}, №проекта {item["№проекта"]} - Не сформирован локальный график')
                datat_bin = CMS.update_local_graf(self, True, int(item['Пномер']), False)
                if datat_bin == None:
                    msg = f"Ошибка генерации графика {str(item['Пномер'])}"
                    print(msg)
                    list_errs.append({'Ошибка':msg})
                    continue
                print(f"Line {int(item['Пномер'])} update")
                item['local_graf'] = datat_bin
                print(f"Создан локальный график на {item['Пномер']}")
            tbl_gant = F.from_binary_pickle(item['local_graf'])
            try:
                for date in tbl_gant[0]['data'].keys():
                    set_dates.add(date)
                    dict_dates_vals[date] = {'Выходные':tbl_gant[0]['data'][date]['Выходные'],'День недели':tbl_gant[0]['data'][date]['День недели']}
            except:
                CQT.msgbox(f"Ошибка генерации {str(item['Пномер'])}")
        list_dates = list(set_dates)
        list_dates = sorted(list_dates)
        dict_form = []
        for item in query:
            tbl_gant = F.from_binary_pickle(item['local_graf'])
            free_shablon = dict()
            for key in tbl_gant[0]['data'].keys():
                free_shablon = tbl_gant[0]['data'][key]['podr']
                break
            for key in free_shablon.keys():
                free_shablon[key] = ''

            dict_tmp_table = dict()
            for date in list_dates:
                if date not in tbl_gant[0]['data'].keys():
                    dict_tmp_table[date] = {'Выходные':dict_dates_vals[date]['Выходные'],
                                            'День недели':dict_dates_vals[date]['День недели'],
                                            'podr':free_shablon}
                else:
                    dict_tmp_table[date] = tbl_gant[0]['data'][date]
            tmp_list = []
            #query[i]['local_graf'] = dict_tmp_table
            dict_replace_by_days = {}
            if item['fact_jurnal_blolb_data']:
                fact_jurnal_blolb_data = F.from_binary_pickle(item['fact_jurnal_blolb_data'])
                if fact_jurnal_blolb_data is not None:
                    dict_replace_by_days = fact_jurnal_blolb_data

            dict_form.append({'pnom':item['Пномер'],
                              'proj':f"{item['№проекта']} {item['№ERP']}",
                              'poz':item['Позиция'],
                              'napr_deya':item['Направление_деят'] ,
                              'napr': item['Направление'],
                              'data':dict_tmp_table,
                                'dict_replace_by_days':dict_replace_by_days })
        if list_errs:
            CQT.msgboxg_get_table_ok_inf(self,f'Ошибки генерации таблицы',list_errs)
            return
        return dict_form

    #list_of_tbls = load_tabels(self) 04.02.2026 убрано при переработке под локальный

    tbl = self.ui.tbl_kal_pl
    kpl_nums = []
    t = CQT.TableContext(tbl)
    for row in t.rows():
        if not tbl.isRowHidden(row.i):
            kpl_nums.append(row.value('plan.Пномер'))
    list_of_tbls = CMS.load_dict_poz_from_sql(kpl_nums)

    count = len(list_of_tbls)
    i = 1
    for item in list_of_tbls:
        if item['local_graf'] == '':
            print(f'{i} from {count} update_local_graf')
            datat_bin = CMS.update_local_graf(None, True, int(item['Пномер']), False)
            print(f"    Создан локальный график на {item['Пномер']}")
            item['local_graf'] = datat_bin

    if not list_of_tbls:
        CQT.msgbox(f'Ошибка')
        return

    dict_form = generate_full_table(self,list_of_tbls)
    if dict_form is None:
        return
    self.current_kpl_table = 'tbl_pl_gaf'
    CMS.fill_gant_table(self, self.ui.tbl_pl_gaf, self.ui.tbl_pl_gaf_filtr, dict_form)



def show_svod(self):
    #if self.ui.fr_pl_gaf.isHidden():
    #    self.ui.fr_pl_gaf.setHidden(False)
    #    self.ui.fr_svod.setHidden(True)
    #else:
    #    self.ui.fr_pl_gaf.setHidden(True)
    #    self.ui.fr_svod.setHidden(False)
    self.ui.fr_svod.setHidden(False)
    self.ui.tbl_pl_gaf_svod.setHidden(False)
    load_svod(self)




def set_tooltip_val(self,tbls='',r='',c='',clear=False):
    if tbls == "":
        tbls = self.ui.tbl_pl_gaf_svod
    if clear:
        CQT.statusbar_text(self, '')
        tbls.setToolTip('')
        return
    CQT.summ_selct_tbl(self,tbls)
    max_mosh, podr, date_tmp = get_max_mosh_frow_tbl(self,r,c)
    info = f'Максимальная мощность {podr} на {date_tmp} : {max_mosh} н-ч.'
    tbls.setToolTip(info)
    CQT.statusbar_text(self,
                       f'{self.glob_kpl_summ_selct_tbl} |  {info}')

def get_max_mosh_frow_tbl(self,i='',j=''):
    tbls = self.ui.tbl_pl_gaf_svod
    if i == '':
        i = tbls.currentRow()+1
    if j == '':
        j = tbls.currentColumn()
    if i == -1 or j == -1:
        return None,None,None
    rez_list = CQT.list_from_wtabl_c(tbls, hat_c=True)

    date_tmp = ".".join(rez_list[0][j].split('\n')[:-1])
    podr = rez_list[i][0].replace('факт_', '').replace('план_', '')
    max_mosh = 0
    try:
        max_mosh = round(self.KPLAN_max_mosh[F.strtodate(date_tmp, f"%d.%m.%y")][podr] * self.selected_napr_koef)
    except:
        pass
    return max_mosh, podr, date_tmp




def oform_tbl_svod(self:mywindow,rez_list:list =''):
    tbls = self.ui.tbl_pl_gaf_svod

    if rez_list == '':
        rez_list = CQT.list_from_wtabl_c(tbls,hat_c=True)
    tbl = self.ui.tbl_pl_gaf
    for j in range(1, self.count_tbl_field):#HORIZONTAL HEADER TABLE FIELDS
        CQT.set_color_text_header_wtab_horisontal_c(tbls, j, 11, 11, 11, self.val_masht * 0.9, False)
        for i in range(1,len(rez_list)):
            CQT.font_cell_size_format(tbls, i - 1, j, self.val_masht)
    for j in range(self.count_tbl_field, len(rez_list[0])):#HORIZONTAL HEADER GANT FIELDS
        if self.dict_tbls_kpl_info['tbl_pl_gaf'][1][j] == 1:
            CQT.set_color_text_header_wtab_horisontal_c(tbls, j, 180, 11, 11, self.val_masht*0.8, True)
        else:
            CQT.set_color_text_header_wtab_horisontal_c(tbls, j, 11, 11, 11, self.val_masht*0.7, False)
            #CQT.set_color_text_header_wtab_horisontal_c(tbls, j, 11, 11, 11, self.val_masht * 0.8, False)
        for i in range(1,len(rez_list)):
            CQT.font_cell_size_format(tbls, i - 1, j, self.val_masht*0.8)
            if rez_list[i][j] > 0:
                max_mosh, podr, date_tmp =  get_max_mosh_frow_tbl(self,i,j)
                if rez_list[i][j]>max_mosh:
                    CQT.set_font_color_wtab_c(tbls, i - 1, j, 244, 244, 244)
                    CQT.font_cell_size_format(tbls,i - 1, j, 0, True)
                    CQT.set_color_wtab_c(tbls, i - 1, j, 233, 33, 33)
                    #CQT.set_color_text_header_wtab_horisontal_c(tbls, j, 250, 3, 3, self.val_masht * 0.8, True)
                else:
                    podr = rez_list[i][0].replace('факт_', '').replace('план_', '')
                    r = 233
                    g = 233
                    b = 233
                    if podr in self.Data_plan.DICT_PODR:
                        r, g, b = self.Data_plan.DICT_PODR[podr]['Цвет'].split(";")
                    CQT.set_color_wtab_c(tbls, i - 1, j, int(r), int(g), int(b))
            else:
                CQT.set_font_color_wtab_c(tbls, i - 1, j, 233, 233, 233)

    for i in range(1, len(rez_list)):
        podr = rez_list[i][0].replace('факт_', '').replace('план_', '')
        r = 233
        g = 233
        b = 233
        if podr in self.Data_plan.DICT_PODR:
            r, g, b = self.Data_plan.DICT_PODR[podr]['Цвет'].split(";")
        CQT.set_color_text_header_wtab_vertical_c(tbls, i - 1, r, g, b, self.val_masht * 0.8, True)


    CMS.update_width_filtr(tbl, tbls)

    #fields_hide = ['Этап', 'Пномер', "Проект", "Поз.", "Напр.",'Напр_д.']
    #for field in fields_hide:
    #    try:
    #        tbls.setColumnHidden(CQT.num_col_by_name_c(tbls, field), True)
    #    except:
    #        pass


@CQT.onerror
def dbl_clk_select_etap(self):
    self.current_kpl_table = 'tbl_pl_gaf'
    def get_down_to_local():
        try:
            cell = self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][r + 1][c]
            if cell == '':
                return
            name_kol = cell[0]['Имя_нз'][0]
        except:
            return
        # date = F.strtodate(".".join(tbl.horizontalHeaderItem(c).text().split('\n')[:-1]), f"%d.%m.%y")
        date = tbl.horizontalHeaderItem(c).text()

        table_new = CQT.list_from_wtabl_c(self.ui.tbl_kal_pl, '', True)
        new_hat_c = ['' for _ in table_new[0]]
        nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_kal_pl, 'plan.Пномер')
        new_hat_c[nk_pnom] = pnom
        CMS.fill_filtr_c(self, tbl_filtr, self.ui.tbl_kal_pl, [new_hat_c])
        CMS.update_width_filtr(self.ui.tbl_kal_pl, tbl_filtr)
        CMS.apply_filtr_c(self, tbl_filtr, self.ui.tbl_kal_pl)
        not_hidden_row = 0
        for i in range(self.ui.tbl_kal_pl.rowCount()):
            if not self.ui.tbl_kal_pl.isRowHidden(i):
                not_hidden_row = i
                break
        # self.ui.tbl_kal_pl.setCurrentCell(not_hidden_row,CQT.num_col_by_name_c(self.ui.tbl_kal_pl,name_kol))
        KPL.btn_pl_mode(self)
        CQT.select_cell(self.ui.tbl_kal_pl, not_hidden_row, CQT.num_col_by_name_c(self.ui.tbl_kal_pl, name_kol))
        # tbl.clearSelection()

        list_local_gant = CQT.list_from_wtabl_c(self.ui.tbl_preview, '', True)
        nk_etap = CQT.num_col_by_name_c(self.ui.tbl_preview, 'Этап')
        for i in range(len(list_local_gant)):
            if list_local_gant[i][nk_etap] == etap:
                for j in range(len(list_local_gant[0])):
                    if list_local_gant[0][j] == date:
                        CQT.select_cell(self.ui.tbl_preview, i - 1, j)
                        return

    list_for_copy_filtr = ['Этап'
,'Пномер'
,'Проект'
,'Поз.'
,'Напр.']
    tbl = self.ui.tbl_pl_gaf
    tbl_filtr = self.ui.tbl_filtr_kal_pl
    r = tbl.currentRow()
    c = tbl.currentColumn()
    pnom = tbl.item(r,CQT.num_col_by_name_c(tbl,'Пномер')).text()
    etap = tbl.item(r,CQT.num_col_by_name_c(tbl,'Этап')).text()

    if self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][0][c] in list_for_copy_filtr:
        self.ui.tbl_pl_gaf_filtr.item(0,c).setText(self.ui.tbl_pl_gaf.item(r,c).text())
        return
    get_down_to_local()



def dbl_clk_svod_select_etap(self):
    tbls = self.ui.tbl_pl_gaf_svod
    tbl_filtr = self.ui.tbl_pl_gaf_filtr
    r = tbls.currentRow()
    c = tbls.currentColumn()
    etap = tbls.item(r,0).text()
    date = F.strtodate(".".join(tbls.horizontalHeaderItem(c).text().split('\n')[:-1]), f"%d.%m.%y")
    self.ui.fr_svod.setHidden(True)
    self.ui.fr_pl_gaf.setHidden(False)
    table_new = CQT.list_from_wtabl_c(self.ui.tbl_pl_gaf,'',True)
    new_hat_c = ['' for _ in table_new[0]]
    nk_etap = CQT.num_col_by_name_c(self.ui.tbl_pl_gaf,'Этап')
    new_hat_c[nk_etap] = etap
    CMS.fill_filtr_c(self,tbl_filtr,self.ui.tbl_pl_gaf,[new_hat_c])
    GKPL.apply_field_filter_hat_name(tbl_filtr)

    for j in range(1, len(self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][0])):
        if self.dict_tbls_kpl_info[KPL.calc_current_ifo_tbl_name(self)][1][j] == 1:
            CQT.set_color_text_header_wtab_horisontal_c(tbl_filtr, j, 200, 11, 11, self.val_masht * 0.5, False)
        else:
            CQT.set_color_text_header_wtab_horisontal_c(tbl_filtr, j, 11, 11, 11, self.val_masht * 0.5, False)
    CMS.update_width_filtr(self.ui.tbl_pl_gaf, tbl_filtr)
    CMS.apply_filtr_c(self,self.ui.tbl_pl_gaf_filtr,self.ui.tbl_pl_gaf)
    not_hidden_row = 0
    for i in range(self.ui.tbl_pl_gaf.rowCount()):
        if not self.ui.tbl_pl_gaf.isRowHidden(i):
            not_hidden_row= i
            break
    #self.ui.tbl_pl_gaf.setCurrentCell(not_hidden_row,CQT.num_col_by_name_c(self.ui.tbl_pl_gaf,tbls.horizontalHeaderItem(c).text()))
    CQT.select_cell(self.ui.tbl_pl_gaf,not_hidden_row,CQT.num_col_by_name_c(self.ui.tbl_pl_gaf,tbls.horizontalHeaderItem(c).text()))
    #tbls.clearSelection()
def get_max_mosh_from_db(self):
    list_tables = CSQ.get_list_of_tables_c(self.db_kplan)
    dict_days = dict()
    for tbl_name in list_tables:
        if F.is_date(tbl_name,'m_cld_%Y_%m_%d'):
            dict_month = CSQ.custom_request_c(self.db_kplan,f"""SELECT * FROM {tbl_name}""")
            for i in range(3,len(dict_month[0])):
                if F.is_date(dict_month[0][i],'d_%Y_%m_%d'):
                    dict_day = dict()
                    for j in range(3,len(dict_month)):
                        dict_day[dict_month[j][1]] = dict_month[j][i]
                    dict_days[F.strtodate(dict_month[0][i],'d_%Y_%m_%d')] = dict_day
    self.KPLAN_max_mosh = dict_days

@CQT.onerror
def load_svod(self:mywindow):

    self.current_kpl_table = 'tbl_pl_gaf_svod'
    tbl = self.ui.tbl_pl_gaf
    tbls =  self.ui.tbl_pl_gaf_svod

    rez_list = [self.dict_tbls_kpl['tbl_pl_gaf'][0]]
    dict_info = {(_[0],_[1]):_ for _ in self.dict_tbls_kpl_info['tbl_pl_gaf'][3:]}
    dict_etapov = dict()
    dict_type_row = dict()

    t = CQT.TableContext(tbl)
    for row in t.rows():
        if not row.is_hidden():
            kpl = int(row.value('Пномер'))
            etap = row.value('Этап')
            data_list = dict_info[(etap,kpl)]
            fl_replaced_vals = bool([_ for  i, _ in  enumerate(data_list) if isinstance(_,list)
                                     and [x for x in _ if x['_type_replace_by_days']]])
            dict_type_row[(etap,kpl)]= fl_replaced_vals
            if etap not in dict_etapov:
                dict_etapov[etap] = []
            dict_etapov[etap].append(data_list)

    templt_podr = []
    for name, item in self.Data_plan.DICT_PODR.items():
        templt_podr.append([f'план_{name}',item['Порядок']])
        templt_podr.append([f'факт_{name}',item['Порядок']])

    templt_podr = sorted(templt_podr,key=lambda x: x[0])
    templt_podr = sorted(templt_podr,key=lambda x: x[1])


    for etap,__ in templt_podr:
        if etap not in dict_etapov:
            continue
        tmp_row = copy.deepcopy(["" for _ in self.list_for_hat])
        tmp_row[0] = etap
        dict_rows = dict_etapov[etap]

        for j in range(self.count_tbl_field,len(self.dict_tbls_kpl_info['tbl_pl_gaf'][0])):
            summ_chas = 0
            for row in dict_rows:
                if row[j] != '':
                    k = (row[0], row[1])
                    replaced_vals_type_row = dict_type_row[k]
                    summ_vol = 0
                    if replaced_vals_type_row:
                        if len(row[j])>1:
                            summ_vol+= row[j][-1]['По дню']
                    else:
                        for oper in row[j]:
                            if oper['_type_replace_by_days']:
                                continue
                            vol = oper['Время_час']
                            summ_vol+=vol
                    summ_chas += summ_vol
            tmp_row.append(round(summ_chas))
        rez_list.append(tmp_row)
    self.dict_tbls_kpl_info[self.current_kpl_table] = rez_list
    CQT.fill_wtabl(rez_list, tbls, min_width_col= int( 4 * 0.8),
                   height_row=self.val_masht * 2, colorful_edit=False, auto_type=False, head_column=0,
                   set_editeble_col_nomera={}, hide_head_column=False)

    oform_tbl_svod(self,rez_list)
    with CQT.table_updating(tbls):
        CQT._load_tbl(tbl,tbls,True,len(dict_etapov))
    self.ui.splitter_svod.setSizes([499, 0])
def save_diapazon_month(self: mywindow):
    str_d = F.datetostr(self.ui.de_vol_pl.date().toPyDate()) + ';' + F.datetostr(self.ui.de_vol_pl_end.date().toPyDate())
    CMS.save_tmp_path('pl_diapazon_month',str_d)

def load_diapazon_month(self: mywindow):
    try:
        list_str_d =  CMS.load_tmp_path('pl_diapazon_month').split(';')
        self.ui.de_vol_pl.setDate(F.strtodate(list_str_d[0]))
        self.ui.de_vol_pl_end.setDate(F.strtodate(list_str_d[1]))
    except:
        pass


