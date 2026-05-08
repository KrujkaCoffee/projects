from __future__ import annotations

import copy
import datetime
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
from data_class import Data_plan as DTCLS
import project_cust_38.border_painter as BORDERP
from functools import partial
if TYPE_CHECKING:
    from MKart import mywindow
from PyQt5 import QtWidgets, QtCore

def _____________________gant_manage_________________________():pass
def hover_tbl_pl_gaf(self, event):
    tbl = self.ui.tbl_pl_gaf
    hover_tbl_gant(self,tbl,event)

def hover_tbl_preview(self, event):
    tbl = self.ui.tbl_preview
    hover_tbl_gant(self,tbl,event)

def hover_tbl_gant(self, tbl:CQT.QtWidgets.QTableWidget, event):
    i, j = CQT.get_hover_row_col(self, tbl, event)
    if i == None or j == None:
        return
    if tbl.item(i, j) == None:
        return
    g_handler = KPL.Gant_handler(local_mode=tbl is self.ui.tbl_preview, by_hover=event)
    if g_handler.gant is None:
        return
    if g_handler is None:
        return
    val = g_handler.selected_cell
    fl_clear = False
    mouse_move_mode = False
    if val is None or not val:
        fl_clear = True
    if DTCLS.MOUSE_MOVING_BLOCK_GANT:
        mouse_move_mode =True
    load_info_select_block(self,g_handler,fl_clear,mouse_move_mode)
@CQT.onerror
def load_info_select_block(self:mywindow,g_handler:KPL.Gant_handler,clear=False,mouse_move_mode=False):
    def set_border_block(border_o:BORDERP.BorderPainter,
                         g_handler:KPL.Gant_handler,
                         clr_ins:CMS.Color,
                         clr_out:CMS.Color):
        delta_clmn_idx_left = 0
        delta_clmn_idx_right = 0
        if mouse_move_mode:
            start_clmn_idx = g_handler.t.nf[DTCLS.MOUSE_MOVING_BLOCK_GANT.cld_day]
            delta_clmn_idx = g_handler.t.nf[g_handler.cld_day] - start_clmn_idx
            if DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.block:
                delta_clmn_idx_left = delta_clmn_idx_right = delta_clmn_idx
            elif  DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.left_edge:
                delta_clmn_idx_left  = delta_clmn_idx
            elif  DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.right_edje:
                delta_clmn_idx_right = delta_clmn_idx

        border_o.set_colors(clr_out.rgb,clr_ins.rgb)
        border_o.enabled = True
        left_block_idx = g_handler.left_block_idx or 0
        united_left_block_idx= left_block_idx+delta_clmn_idx_left
        right_block_idx = g_handler.right_block_idx or 0
        united_right_block_idx = right_block_idx+delta_clmn_idx_right
        if united_left_block_idx < g_handler.left_idx_net:
            united_left_block_idx = g_handler.left_idx_net
        if united_right_block_idx > g_handler.right_idx_net:
            united_right_block_idx = g_handler.right_idx_net
        g_handler.t.tbl.columnCount()
        border_o.update_border(g_handler.t.tbl,
                   (g_handler.current_row.i,united_left_block_idx),
                (g_handler.current_row.i,united_right_block_idx),repaint_by_row=mouse_move_mode)


    def format_date(val: str) -> str:
        if not val:
            return ''
        date = F.dateStrToStr(val,format_out="%d.%m.%Y",onerror= None)
        if date:
            return date
        return val  # если формат не распознан

    if clear:
        CQT.statusbar_text(self, '')
        g_handler.t.tbl.setToolTip('')
        if not mouse_move_mode:
            g_handler.t.set_cursor(CQT.Cursors.simple.get())

    if mouse_move_mode:
        if DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.block:
            g_handler.t.set_cursor(CQT.Cursors.closedhand.get())
        else:
            g_handler.t.set_cursor(CQT.Cursors.sizehorcursor.get())

    if g_handler.local_mode:
        border_o = DTCLS.tbl_gant_local_border
    else:
        border_o = DTCLS.tbl_gant_context_border
    if g_handler.cld_day is None:
        return

        #====border_load========
    if g_handler.block_selected or mouse_move_mode:
        if not mouse_move_mode and g_handler.local_mode:
            if g_handler.selected_cell and g_handler.selected_cell.for_tbl():
                g_handler.t.set_cursor(CQT.Cursors.double_and_context.get())
            else:
                g_handler.t.set_cursor(CQT.Cursors.right_click.get())

        clr_ins = g_handler.tbl_db.color.align_colors(level_percent=-12, saturation_percent=40, copy=True)
        clr_out = g_handler.tbl_db.color.align_colors(level_percent=-12, saturation_percent=30, copy=True)
        set_border_block(border_o, g_handler, clr_ins, clr_out)
    else:
        border_o.clear_borders(g_handler.t.tbl)
    # ==========
    if clear:
        return

    blocks = []
    hours = g_handler.block_count_hours
    lines = [f"Этап: {g_handler.tbl_db.alias}"]
    start = format_date(g_handler.min_date_block)
    end = format_date(g_handler.max_date_block)
    if start or end:
        lines.append(f"Период: {start} — {end}")
    lines.append(f"Время: {round(hours, 2)} ч.")
    blocks.append("\n".join(lines))

    info = "\n\n".join(blocks)
    g_handler.t.tbl.setToolTip(info)
    power = ''
    power_etap = g_handler.get_power_hour_current_etap
    try:
        power = f'Макс. мощность по {g_handler.tbl_db.alias} : {round(power_etap,2)} н-час.'
    except:
        pass
    CQT.statusbar_text(self,
                       f'{self.glob_kpl_summ_selct_tbl}    |    {info}    |    {power}' )
def mouse_moving_stop():
    g_handler = KPL.Gant_handler()
    g_handler_move = DTCLS.MOUSE_MOVING_BLOCK_GANT
    origin_left_idx = g_handler_move.left_block_idx
    origin_right_idx = g_handler_move.right_block_idx
    start_clmn_idx = g_handler.t.nf[g_handler_move.cld_day]
    delta_clmn_idx = g_handler.t.tbl.currentColumn() - start_clmn_idx
    if DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.block:
        g_handler_move.set_new_date(True, F.date_add_days(g_handler_move.min_date_block, delta_clmn_idx, '', ''))
        g_handler_move.set_new_date(False, F.date_add_days(g_handler_move.max_date_block, delta_clmn_idx, '', ''))
    elif DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.left_edge:
        g_handler_move.set_new_date(True, F.date_add_days(g_handler_move.min_date_block, delta_clmn_idx, '', ''))
    elif DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.right_edje:
        g_handler_move.set_new_date(False, F.date_add_days(g_handler_move.max_date_block, delta_clmn_idx, '', ''))

    if g_handler.link_blocks_moving:
        for row in g_handler.t.rows():
            tmp_g_hndlr = KPL.Gant_handler(forced_row=row)
            if tmp_g_hndlr.current_row.i ==  g_handler_move.current_row.i:
                continue
            if not tmp_g_hndlr.is_block_replaced_dates:
                if (DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.block or
                    DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.right_edje): # сдвигаем правее на +
                    if tmp_g_hndlr.left_block_idx > origin_right_idx or tmp_g_hndlr.left_block_idx == origin_left_idx:# правее исходного края
                        tmp_g_hndlr.set_new_date(True,
                                                    F.date_add_days(tmp_g_hndlr.min_date_block, delta_clmn_idx, '',
                                                                    ''))
                        tmp_g_hndlr.set_new_date(False,
                                                    F.date_add_days(tmp_g_hndlr.max_date_block, delta_clmn_idx, '',
                                                                    ''))
                if (DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.block or
                    DTCLS.MOUSE_MOVING_BLOCK_GANT._mouse_moving_block_gant_mode == Mouse_moving_block_gant_modes.left_edge):
                    if tmp_g_hndlr.right_block_idx < origin_left_idx or tmp_g_hndlr.left_block_idx == origin_left_idx:
                        tmp_g_hndlr.set_new_date(True,
                                                 F.date_add_days(tmp_g_hndlr.min_date_block, delta_clmn_idx, '',
                                                                 ''))
                        tmp_g_hndlr.set_new_date(False,
                                                 F.date_add_days(tmp_g_hndlr.max_date_block, delta_clmn_idx, '',
                                                                 ''))


    DTCLS.MOUSE_MOVING_BLOCK_GANT = None
    KPL.update_local_graf(True,g_handler.poz_gant.poz_id,True)
def fill_select_poz_kpl(self,forced_kpl_id:int|None=None):
    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields
    tbl = self.ui.tbl_kal_pl
    t = CQT.TableContext(tbl)
    CQT.clear_tbl(self.ui.tbl_addit_info_poz_gant)

    if forced_kpl_id is None:
        row = t.current_row()
        if row.no_selection:
            return
    else:
        row = t.find_row({'plan.Пномер':forced_kpl_id},True)
        if row is None:
            return

    row_fix = row.get_list_dict_vals(aliases=False)
    set_not_loaded = set([_ for _ in DICT_FIELDS.values() if not _.is_loaded or _.is_hidden])

    templ = []
    for it in row_fix:
        name_field = it['Параметр']
        val_field = it['Значение']
        field_o = DICT_FIELDS[name_field]
        if not val_field or val_field == '0' or val_field == '0.0':
            continue
        if field_o in set_not_loaded:
            continue
        templ.append({
            '_name':field_o.name_mes,
            'Параметр':field_o.name_alias,
            'Значение':val_field,
            'Описание':field_o.description
        })
    row_fix = templ

    CQT.fill_wtabl(row_fix,self.ui.tbl_addit_info_poz_gant,height_row=42,styleSheet=CQT.MES_CSS)


    t = CQT.TableContext(self.ui.tbl_addit_info_poz_gant)
    t.hide_if_not_dev(CFG)
    for row in t.rows():
        name = row.value('_name')
        field_o = DICT_FIELDS[name]
        clr = field_o.table_color
        clrs = clr.align_colors(level_percent=-30, saturation_percent=-20,copy=True)
        row.set_color_font(*clrs.rgb)
        row.set_font_format(bold=True,col_name= 'Параметр')
        row.set_font_format(bold=True,col_name= 'Значение')


@CQT.onerror
def move_manage(self,direction:int):
    g_handler = KPL.Gant_handler()
    if g_handler.poz_gant is None:
        CQT.msgbox(f'Не выбран этап в ганте')
        return


    fl_update_gant = False
    fl_update_gant_tmp ,errors = move(g_handler, direction, self.ui.le_edit_local_gant_nach.text(),
                                      start=True)
    if errors:
        CQT.msgbox('\n'.join(list[errors]))
        return
    if fl_update_gant_tmp:
        fl_update_gant = True

    fl_update_gant_tmp, errors = move(g_handler, direction, self.ui.le_edit_local_gant_kon.text(),
                                      start=False)
    if errors:
        CQT.msgbox('\n'.join(list[errors]))
        return
    if fl_update_gant_tmp:
        fl_update_gant = True

    if fl_update_gant:
        KPL.update_local_graf(True, g_handler.poz_gant.poz_id)
        if not self.is_main_mode():
            VPL.load_tbl_gant(self)  # объемный загрузка


@CQT.onerror
def move_left(self):
    move_manage(self,-1)
@CQT.onerror
def move_right(self):
    move_manage(self, 1)

@CQT.onerror
def move( g_handler: KPL.Gant_handler, direction: int = 1, count_str: str = '',
          start: bool = True) -> tuple[bool,set[str]]:
    def parse_date(date_txt: str) -> datetime.datetime | None:
        return F.dateStrToStr(date_txt, format_out='', onerror=None)

    errors = set()
    count_str = count_str.strip()
    if count_str in ('', '0'):
        return False, errors
    describe = 'Начало' if start else 'Конец'

    old_date = g_handler.min_date_block if start else g_handler.max_date_block




    new_date: datetime.datetime | None = None
    delta_days:int|None = None
    if not F.is_numeric(count_str):
        dt_date = parse_date(count_str)
        if dt_date is None:
            CQT.msgbox(f'В поле периода {describe} не число и не дата')
            return False, errors
        delta_days = abs((old_date - dt_date).days)
    else:
        delta_days = F.valm(count_str)

    if delta_days is None:
        err = f'Ошибка расчетов даты'
        CQT.msgbox(err)
        errors.add(err)
        return False , errors

    selectd_rows = g_handler.list_selected_rows
    if len(selectd_rows) == 1:
        if g_handler.type_day == CMS.Types_day_gant.fact:
            err = 'Перемещение невозможно для факта'
            CQT.msgbox(err)
            errors.add(err)
            return False, errors
        if g_handler.is_block_replaced_dates:
            err = 'Перемещение невозможно для нерасчетных блоков'
            CQT.msgbox(err)
            errors.add(err)
            return False, errors

    fl_update_gant = False
    for row in g_handler.list_selected_rows:
        tmp_g_handler = KPL.Gant_handler(forced_row=row)
        if tmp_g_handler.type_day == CMS.Types_day_gant.fact:
            continue
        if tmp_g_handler.is_block_replaced_dates:
            continue
        old_date = tmp_g_handler.min_date_block if start else tmp_g_handler.max_date_block

        new_date = F.date_add_days(old_date, delta_days * direction, '', '')
        if tmp_g_handler.set_new_date(start, new_date):
            fl_update_gant = True


    return fl_update_gant, errors

@CQT.onerror
def tbl_preview_on_header_click(self,ind):
    tbl = self.ui.tbl_preview
    t = CQT.TableContext(tbl)
    data = t.name_by_idx(ind)
    if isinstance(data,CMS.Month_cld_day):
        text = F.datetostr(data.dt_datetime,"%d.%m.%Y" )
        F.copy_bufer(text)
        CQT.msgbox(f'Скопировано в буфер: {text}',time_life=1)
def clear_edit_local_gant(lbl:CQT.QtWidgets.QLabel):
    lbl.setText('')
    lbl.setFocus()
def clear_edit_local_gant_nach(self:mywindow):
   clear_edit_local_gant(self.ui.le_edit_local_gant_nach)

def clear_edit_local_gant_kon(self:mywindow):
   clear_edit_local_gant(self.ui.le_edit_local_gant_kon)

def pickup_dates(lbl_start:CQT.QtWidgets.QLabel,lbl_end:CQT.QtWidgets.QLabel,columns:list):
    def fill_date(lbl, clmn:CMS.Month_cld_day):
        if not isinstance(clmn,CMS.Month_cld_day):
            return
        lbl.setText(F.datetostr(clmn.dt_datetime,"%d.%m.%Y"))

    fill_date(lbl_start, columns[0])
    fill_date(lbl_end, columns[-1])

def pickup_date(lbl:CQT.QtWidgets.QLabel,clmn):
    def fill_date(lbl, clmn:CMS.Month_cld_day):
        if not isinstance(clmn,CMS.Month_cld_day):
            return
        lbl.setText(F.datetostr(clmn.dt_datetime,"%d.%m.%Y"))

    fill_date(lbl,clmn)

def pickup_date_nach(self:mywindow):
    tbl = DTCLS.app_self.ui.tbl_preview
    t = CQT.TableContext(tbl)
    columns = t.get_selected_columns()
    if len(columns) == 1:
        pickup_date(self.ui.le_edit_local_gant_nach,columns[0])
    else:
        pickup_dates(
            self.ui.le_edit_local_gant_nach,
            self.ui.le_edit_local_gant_kon,
            columns
        )
def pickup_date_kon(self:mywindow):
    tbl = DTCLS.app_self.ui.tbl_preview
    t = CQT.TableContext(tbl)
    columns = t.get_selected_columns()
    if len(columns) == 1:
        pickup_date(self.ui.le_edit_local_gant_kon,columns[0])
    else:
        pickup_dates(
            self.ui.le_edit_local_gant_nach,
            self.ui.le_edit_local_gant_kon,
            columns
        )
@CQT.onerror
def set_start_end_dates_clnd(self:mywindow):
    succ, dates = CQT.get_data_dialog_choose(self,'Выбрать дату начала работы с позицией',
                                       range_dates=False)
    if not succ:
        return
    start_date = dates["date_from"]
    self.ui.le_start_set_dates_etaps.setText(F.datetostr(start_date,"%d.%m.%Y"))


class Mouse_moving_block_gant_modes:
    block='block'#перетягивание блока
    left_edge ='left_edge '#движения левой границе
    right_edje ="rigth edge"# движений правой границей

@CQT.onerror
def fnc_context_menu_gant(app_self, object_tbl, row, col, builder):

    g_handler = KPL.Gant_handler()
    if not g_handler.block_selected:
        return
    clmn_o: CMS.Month_cld_day = g_handler.t.current_column_name()
    if not isinstance(clmn_o, CMS.Month_cld_day):
        return

    def fnc_hand_move_r(g_handler,*args):# KPL.clck_tbl_preview
        DTCLS.MOUSE_MOVING_BLOCK_GANT = g_handler
        g_handler._mouse_moving_block_gant_mode = Mouse_moving_block_gant_modes.right_edje
    def fnc_hand_move_l(g_handler,*args):# KPL.clck_tbl_preview
        DTCLS.MOUSE_MOVING_BLOCK_GANT = g_handler
        g_handler._mouse_moving_block_gant_mode = Mouse_moving_block_gant_modes.left_edge
    def fnc_hand_move(g_handler,*args):# KPL.clck_tbl_preview
        DTCLS.MOUSE_MOVING_BLOCK_GANT = g_handler
        g_handler._mouse_moving_block_gant_mode = Mouse_moving_block_gant_modes.block

    if not g_handler.is_block_replaced_dates:
        builder.add_submenu(f"{CEMOJ.EmojiMain.ДокументыДанные.shuffle.symbol} Перемещение")
        builder.add_menu(f'{CEMOJ.EmojiMain.ДокументыДанные.revers.symbol}\t Блок',
                         partial( fnc_hand_move,g_handler))
        builder.add_menu(f'{CEMOJ.EmojiMain.ДокументыДанные.move_left_border.symbol}\t Л. Границу',
                         partial( fnc_hand_move_l,g_handler))
        builder.add_menu(f'{CEMOJ.EmojiMain.ДокументыДанные.move_right_border.symbol}\t П. Границу',
                         partial( fnc_hand_move_r,g_handler))
        builder.end_submenu()
    builder.add_submenu(f"{CEMOJ.EmojiMain.ОборудованиеИнструменты.tool.symbol} В разработке")

def recalc_gant_forced(*args):
    KPL.update_local_graf(pnom=DTCLS.current_id_poz_kpl,update=True,fill_gant=True)


def _________refactored__________():pass#^^^^^^^^^^^^^^^^^

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
                                                             'StandardODATA.Document_ЗаказНаВнутреннееПотребление',
                                                             'StandardODATA.Document_ЗаказДавальца2_5'
                                                             ):
                    CQT.msgbox(f"Основание для {self.place.doc_prefix}:\n{data_py['ДокументОснование_Type']}.\n Нужен Заказа клиента/Заказ на сборку")
                    return
                client_order = data_py['ДокументОснование']
                data_co = None
                if data_py['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказДавальца2_5':
                    data_co = m.get_response(doc_name=f"Document_ЗаказДавальца2_5(guid'{data_py['ДокументОснование']}')",
                                             wet_filtr=f"?$select= Number,Date,Статус,"
                                                       f"Комментарий,Продукция/LineNumber,"
                                                       f"Продукция/Номенклатура_Key,Продукция/Количество,"
                                                       f"Продукция/ДатаОтгрузки,"
                                                       f"Сделка_Key ")

                    data_co['Документ'] = f"ЗаказДавальца {data_co['Number']}"
                    data_co['Товары'] = data_co['Продукция']
                    data_co.pop('Продукция',None)

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



                if data_co is None:
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
def btn_tree_pl_wrap_all(*args):
    self = DTCLS.app_self
    tree = self.ui.tree_fields
    tree.collapseAll()

@CQT.onerror
def btn_tree_pl_unwrap_all(*args):
    self = DTCLS.app_self
    tree = self.ui.tree_fields
    tree.expandAll()

@CQT.onerror
def load_fields_for_tree(self:mywindow):
    tree = self.ui.tree_fields
    tbl = self.ui.tbl_kal_pl

    if tbl.currentRow() ==-1:
        CQT.msgbox(f'Не выбрана позиция')
        return
    t = CQT.TableContext(tbl)
    row = t.current_row()
    if row.value('plan.Статус') == 'Группа':
        return
    id_kpl = row.value('plan.Пномер')

    data_from_db = KPL.load_db(self,id_kpl) or {}

    set_existance = set()

    color1 = '254;254;254'
    color2 = '234;234;234'

    tree_o = CMS.Tree_unique()
    f_field = tree_o.add_field('Поле')
    f_tbl = tree_o.add_field('_tbl')
    f_name = tree_o.add_field('_name_mes',primary = True)
    f_val = tree_o.add_field('Значение',bold_font=False,color_font='10;10;10')
    f_loaded = tree_o.add_field('Табличное',bold_font=False,color_font='10;10;10')
    f_note = tree_o.add_field('Примечание',bold_font=False)

    for tbl in DTCLS.FIELDS_DB_INFO.tables_db.tabels:

        if not any(f.is_loaded for f in tbl.set_fields):
            continue

        clr = copy.deepcopy(tbl.color)
        clr.align_colors(level_percent=-20,saturation_percent=-20)
        color_font_str = clr.get_str(';')

        if tbl.alias not in set_existance:
            set_existance.add(tbl.alias)

            row = tree_o.add_row(0,tbl.descr,color_font_str,bold_font=True)
            row.add_val(f_tbl,tbl.alias)
            row.add_val(f_name,tbl.name)
            row.add_val(f_field,tbl.alias)
            row.add_val(f_val,'')
            row.add_val(f_note,tbl.descr)

        for field in tbl.set_fields:
            if not field.is_loaded:
                continue
            if field.sys_hide:
                continue
            name_mes =  field.name_mes
            val = str(data_from_db.get(name_mes, ''))

            row = tree_o.add_row(1,'', color_font_str,bold_font=False,color_background=color1,color_background_odd=color2)
            row.add_val(f_tbl,tbl.alias)
            row.add_val(f_name,name_mes)
            row.add_val(f_field,field.name_alias)
            row.add_val(f_val,val)
            row.add_val(f_loaded, CEMOJ.EmojiMain.ПоказателиМетрики.eye.symbol if field.tbl_idx is not None else '' )
            row.add_val(f_note,field.description)


    tree_o.fill_tree(tree)
    CQT.load_column_widths(DTCLS.app_self, tree_o.tree_q)
    if not CFG.Config.user_config.is_developer:
        for f in tree_o.fields:
            if f.name.startswith('_'):
                tree_o.hide(f)

    #CQT.fill_wtree_unique(tree,list_data_tree, False)

@CQT.onerror
def tree_fields_dbl_clck(self:mywindow,*args):
    tree = self.ui.tree_fields

    row = CQT.get_tree_current_row_dict(tree)
    dict_fields = DTCLS.FIELDS_DB_INFO.dict_fields
    name_mes = row['_name_mes']
    if name_mes not in dict_fields:
        CQT.msgbox(f'Поле не найдено')
        return
    column = dict_fields[name_mes].tbl_idx
    if column is None:
        return
    tbl = self.ui.tbl_kal_pl
    row_tbl = tbl.currentRow()
    if row_tbl <= 0:
        return
    tbl.blockSignals(True)
    CQT.select_cell(tbl,row_tbl,column)
    tbl.blockSignals(False)
    pass


@CQT.onerror
def set_start_end_dates(self:mywindow):
    tbl = DTCLS.app_self.ui.tbl_preview
    t = CQT.TableContext(tbl)
    columns = t.get_selected_columns()
    pickup_date(
            self.ui.le_start_set_dates_etaps,
            columns[0]
        )

@CQT.onerror
def clear_dates_etaps_le(self:mywindow):
    self.ui.le_start_set_dates_etaps.setText('')

@CQT.onerror
def set_dates_etaps(self:mywindow):
    def prepare_dates()->datetime.datetime|None:
        start_str = self.ui.le_start_set_dates_etaps.text()


        # start_str = "2024-06-25"
        # end_str = "2024-07-25"
        def check_dates(str_date) -> datetime.datetime | None:
            dt_date = F.dateStrToStr(str_date, format_out='', onerror=None)
            if isinstance(dt_date, datetime.datetime):
                return dt_date
            return

        start_date = check_dates(start_str)

        if start_date is None:
            CQT.msgbox(f'Дата введена не корректно')
            return None


        return start_date

    g_handler = KPL.Gant_handler()
    if g_handler.poz_gant is None :
        t_plan = CQT.TableContext(self.ui.tbl_kal_pl)
        row = t_plan.current_row()
        if row.no_selection:
            CQT.msgbox(f'Не выбрана позиция(гант)')
            return
        poz_id = int(row.value('plan.Пномер'))
    else:
        poz_id = g_handler.poz_gant.poz_id


    start_date_dt  = prepare_dates()
    if start_date_dt is None:return
    gant = CMS.Gant(DTCLS.DICT_CLD,DTCLS.FIELDS_DB_INFO)
    gant.load([poz_id])
    if not gant.recalc([poz_id],start_date_dt):
        if gant.err_recalc:
            str_err = "\n".join(gant.err_recalc)
        else:
            str_err = f'Не выполнено'
        CQT.msgbox(str_err)
        return
    KPL.update_local_graf( False, poz_id,fill_gant=True)
    clear_dates_etaps_le(self)
    CQT.msgbox(f'Успешно')

    return




@CQT.onerror
def apply_field_filter_hat_name(tbl_filtr):
    tbl_filtr.setVerticalHeaderLabels(['план_факт_подр'])
    tbl_filtr.setRowHeight(0, 25)



