from __future__ import annotations

import copy
import datetime
from builtins import bool

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite  as CSQ
import kal_plan as KPL
import gui_kal_plan as GKPL
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_emoji as CEMOJ
from data_class import Data_plan as DTCLS
from functools import partial
from typing import TYPE_CHECKING
import plotly.graph_objects as go
if TYPE_CHECKING:
    from MKart import mywindow




def generate_diagram(selected_napr):
    # =================add_ui============================
    self = DTCLS.app_self
    parent_for_grafic = self.ui.fr_diagram_summ

    napr_name = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME[selected_napr]['name_for_file_graf_pad_mosh']

    g_hande = KPL.Gant_handler(False)

    pass

    """try:
        self.parent_for_grafic.removeWidget(self.browser)
    except:
        pass
    self.browser = QtWebEngineWidgets.QWebEngineView(self)
    self.parent_for_grafic.addWidget(self.browser)

    CQT.output_gant(self, fig, self.browser, selected_napr, tmp_dir())"""


@CQT.onerror
def pl_mode_upd(*args):
    tabw = DTCLS.app_self.ui.tab_pl_graf_context
    tab_name = tabw.currentWidget().objectName()
    if tab_name == 'tab_pl_graf':
        load_tbl_gant(DTCLS.app_self, False, True)
    if tab_name == 'tab_summ_diagram':
        load_svod(DTCLS.app_self)
    if tab_name == 'tab_workload':
        KPL.update_graf_site_and_get_local(DTCLS.app_self)


@CQT.onerror
@F.time_of_exec_cls_func_args_c
def load_tbl_gant(self:mywindow,warn_msg:bool = True,restore_selected_cell:bool=False)->bool:
    dirty_list_kpls = []
    t_kpl = CQT.TableContext(DTCLS.app_self.ui.tbl_kal_pl)

    set_napr_deyt = set()
    for row in t_kpl.rows():
        if not row.is_hidden():
            dirty_list_kpls.append(int(row.value('plan.Пномер')))
            napr_d = row.value('plan.Направление_деятельности')
            if napr_d:
                set_napr_deyt.add(napr_d)
    dict_napr_d = DTCLS.DICT_NAPR_DEYAT_NAME
    dict_napr = DTCLS.DICT_NAPRAVLENIE

    if warn_msg:
        set_napr = set([dict_napr[dict_napr_d[_]['Направление']]['alias'] for _ in set_napr_deyt])
        if len(set_napr)>1:
            if not CQT.msgboxgYN(f'Будет загружен план для направлений:\n{", ".join(list(set_napr))}'):
                return False

    self.ui.fr_main_mode.setVisible(False)  # для заполнения
    list_kpls = [_ for _ in dirty_list_kpls if _ > 0]
    if not list_kpls:
        return False

    min_day = self.ui.de_vol_pl.dateTime().toPyDateTime()
    max_day = self.ui.de_vol_pl_end.dateTime().toPyDateTime()
    gant_o = CMS.Gant(DTCLS.DICT_CLD, DTCLS.FIELDS_DB_INFO, min_day, max_day)
    gant_o.load(list_kpls,forced_recalc= 'shift' in CQT.get_key_modifiers(DTCLS.app_self) )
    DTCLS.current_vol_gant = gant_o
    gant_o.oforml_table(DTCLS.app_self,DTCLS.app_self.ui.tbl_pl_gaf,DTCLS.app_self.ui.tbl_pl_gaf_filtr,
                        restore_selected_cell=restore_selected_cell)


    return True



@CQT.onerror
def show_svod_tbl(*args):
    load_svod(DTCLS.app_self,True)


@CQT.onerror
def click_tab_pl_graf_context(*args):
    tabw = DTCLS.app_self.ui.tab_pl_graf_context
    tab_name = tabw.currentWidget().objectName()
    if tab_name=='tab_summ_diagram':
        if not DTCLS.app_self.ui.lout_diagram_summ.property('_loaded'):
            load_svod(DTCLS.app_self)
    if tab_name=='tab_workload':
        KPL.update_graf_site_and_get_local(DTCLS.app_self)


@CQT.onerror
def load_svod(self:mywindow,as_table:bool=False):


    g_handle = KPL.Gant_handler(False)
    if g_handle is None:
        CQT.msgbox(f'Не выбрана строка в таблице')
        return

    gant = DTCLS.current_vol_gant
    CLD_DAYS = {k:v for k,v in DTCLS.DICT_CLD.items() if gant.min_day<= k <= gant.max_day }


    list_id_pozitions = CSQ.custom_request_c(DTCLS.db_kplan,f"""SELECT Пномер FROM plan WHERE 
          Статус IN ({', '.join([str(i) for i, _ in self.Data_plan.DICT_STATUS_POZ.items() if _['for_reports']])}) 
           and poki == {DTCLS.PLACE.poki}""",hat_c=False,one_column=True)

    agr = CMS.Gant_agregator()
    data = agr.load(gant.min_day,gant.max_day,list_id_pozitions)
    set_dt = set()
    shabl_podrs = {k:0 for k in CLD_DAYS[gant.min_day].dict_podrs.keys()}
    tbl_top = DTCLS.FIELDS_DB_INFO.tables_db.get_table('пл_топ')
    for it in data:
        it['day_dt'] = F.strtodate(it['day_dt'],"%Y-%m-%d %H:%M:%S")
        set_dt.add(it['day_dt'])
        it['holyday'] = CLD_DAYS[it['day_dt']].is_holyday
        it['weekend'] = CLD_DAYS[it['day_dt']].day_week == 7
        name_podr = DTCLS.DICT_PODR_BY_ID[it['etap_podrazdel']]['Имя']
        tbl_o = DTCLS.FIELDS_DB_INFO.tables_db.get_table(name_podr)
        it['max_time'] = CLD_DAYS[it['day_dt']].dict_podrs[name_podr]
        it['etap_podrazdel'] = tbl_o.alias
        it['etap_podrazdel_order'] = tbl_o.order
        it['filler'] = False
        #[_ for _ in data if F.datetostr(_['day_dt'],"%d.%m.%Y") == '09.03.2026' ]
    #[_ for _ in data if _['id_poz'] == 7086 and _['etap_podrazdel'] == 'пл_сб']
    #sum([_['val_minutes']/60 for _ in data if _['id_poz'] == 7086 and _['etap_podrazdel'] == 'пл_сб'])
    #[_ for _ in data if F.datetostr(_['day_dt'],"%d.%m.%Y") == '07.04.2026' and _['etap_podrazdel'] == 'пл_сб']
    #sum([_['val_minutes']/60 for _ in data if F.datetostr(_['day_dt'],"%d.%m.%Y") == '07.04.2026' and _['etap_podrazdel'] == 'пл_сб'])


    if as_table:
        def fnc_oform_filter(tbl:CQT.QtWidgets.QTableWidget,tblf:CQT.QtWidgets.QTableWidget):
            CMS.fill_filtr_c(DTCLS.app_self,tblf,tbl, combo_dict={'Этап':None})
            pass
        CQT.msgboxg_get_table_ok_inf(self,'Таблица сводного плана',[{
                                                                'Дата':F.datetostr(_['day_dt'],"%d.%m.%Y"),
                                                                'Этап':_['etap_podrazdel'],
                                                                'КПЛ':_['id_poz'],
                                                                'Статус':_['state'],
                                                                'Напр.д.':_['napr_d'],
                                                                'Позиция':_['poz'],
                                                                'Колич.':_['count'],
                                                                'Проект':_['np'],
                                                                'ЗП':_['zp'],
                                                                'Время,час.':round(_['val_minutes']/60 ,2),
                                                                'Предел,час.':round(_['max_time'] ,2),
                                                                     } for _ in data],
                                                    styleSheet=CQT.MES_CSS,load_summ=True,func_oform_filtr=fnc_oform_filter)
        return

    for dt, dt_data in CLD_DAYS.items():
        if dt not in set_dt:
            data.append({'day_dt':dt,'holyday':dt_data.is_holyday,'weekend':dt_data.day_week==7,'max_time':0,
                         'etap_podrazdel':tbl_top.alias,'etap_podrazdel_order':tbl_top.order,'val_minutes':0,
                         'filler' :True})

    def create_heatmap_figure(data: list[dict]):

        # --- 1. сортировки ---
        stages = sorted(
            {(row['etap_podrazdel_order'], row['etap_podrazdel']) for row in data},
            key=lambda x: x[0]
        )
        stages = [_[-1] for _ in stages]

        dates = sorted({row['day_dt'] for row in data})
        dates_str = [F.datetostr(d, "%d.%m.%Y") for d in dates]

        stage_index = {s: i for i, s in enumerate(stages)}
        date_index = {d: i for i, d in enumerate(dates)}

        # --- 2. АГРЕГАЦИЯ (ВАЖНО) ---
        agg = {}

        for row in data:
            key = (row['etap_podrazdel'], row['day_dt'])

            plan = (row['val_minutes'] or 0) / 60
            cap = row['max_time'] or 0

            if key not in agg:
                agg[key] = {
                    "plan": 0.0,
                    "cap": cap
                }

            agg[key]["plan"] += plan
            agg[key]["cap"] = max(agg[key]["cap"], cap)
            agg[key]["filler"] = row['filler']

        # --- 3. матрицы ---
        z = [[None for _ in dates] for _ in stages]
        text = [["" for _ in dates] for _ in stages]
        tool_text = [["" for _ in dates] for _ in stages]

        # --- 4. заполняем из agg ---
        for (stage, day), val in agg.items():

            i = stage_index[stage]
            j = date_index[day]

            plan = val["plan"]
            cap = val["cap"]

            load = None
            if not val["filler"]:
                load = plan / cap if cap > 0 else 2

            z[i][j] = load

            if cap > 0:
                percent = int(load * 100)
                text[i][j] = f"{plan:.0f}<br>из<br>{cap:.0f}<br>{percent}%"
                tool_text[i][j] = f"{plan:.2f} час. из {cap:.2f} ({percent}%)"
            else:
                tool_text[i][j] = f"{plan:.2f} час. из 0"
                if not val["filler"]:
                    text[i][j] = f"{plan:.0f}<br>из<br>{cap:.0f}<br>{200}%"
        # --- 5. heatmap ---
        fig = go.Figure()

        fig.add_trace(go.Heatmap(
            z=z,
            x=list(range(len(dates))),
            y=stages,
            zmin=0,
            zmax=2,
            text=text,
            name='Загрузка',
            texttemplate="%{text}",
            textfont=dict(size=8),
            colorscale=[
                [0.0, "rgb(71,135,223)"],  # мягкий синий
                [0.5, "rgb(102,183,61)"],  # приглушённый зелёный (как в Excel)
                [1.0, "rgb(248,105,107)"]  # мягкий красный
            ],
            colorbar=dict(
                title='Загрузка, %',
                tickvals=[0, 1, 2],
                ticktext=['0%', '100%', '200%']
            ),
            hovertemplate=(
                "Этап: %{y}<br>"
                "Дата: %{x}<br>"
                "%{customdata}<extra></extra>"
            ),
            customdata=[
                [
                    tool_text[i][j]
                    for j in range(len(dates))
                ]
                for i in range(len(stages))
            ],
            hoverongaps=False
        ))

        # --- 6. оси ---
        fig.update_layout(
            margin=dict(l=80, r=40, t=40, b=80),
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(len(dates))),
                ticktext=dates_str,
                tickangle=-45
            ),
            yaxis=dict(automargin=True)
        )

        # --- 7. выходные ---
        holiday_map = {}
        weekend_map = {}
        for row in data:
            d = row['day_dt']
            if d not in holiday_map:
                holiday_map[d] = row['holyday']
            if d not in weekend_map:
                weekend_map[d] = row['weekend']

        shapes = []

        for j, d in enumerate(dates):
            if holiday_map.get(d) == 1:
                shapes.append(dict(
                    type="rect",
                    xref="x",
                    yref="paper",
                    x0=j - 0.5,
                    x1=j + 0.5,
                    y0=0,
                    y1=1,
                    fillcolor="rgba(120,120,120,0.15)",
                    line=dict(width=0),
                    layer="above"
                ))
            if weekend_map.get(d) == 1:
                shapes.append(dict(
                    type="line",
                    xref="x",
                    yref="paper",
                    x0=j - 0.5,
                    x1=j - 0.5,
                    y0=0,
                    y1=1,
                    line=dict(color="rgba(0,0,0,0.45)", width=2),
                    layer="above"
                ))

        for j in range(len(dates) + 1):
            shapes.append(dict(
                type="line",
                xref="x",
                yref="paper",
                x0=j - 0.5,
                x1=j - 0.5,
                y0=0,
                y1=1,
                line=dict(color="rgba(0,0,0,0.25)", width=1),
                layer="above"
            ))

        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(showgrid=False)
        fig.update_layout(shapes=shapes)

        return fig
    fig = create_heatmap_figure(data)

    parent_for_grafic = DTCLS.app_self.ui.lout_diagram_summ

    if self.Data_plan.BROWSER_DIAGRAM_SUMM is None:
        self.Data_plan.BROWSER_DIAGRAM_SUMM = CQT.QtWebEngineWidgets.QWebEngineView(self)
        parent_for_grafic.addWidget(self.Data_plan.BROWSER_DIAGRAM_SUMM)

    parent_for_grafic.setProperty("_loaded","true")
    CQT.output_gant(self, fig, self.Data_plan.BROWSER_DIAGRAM_SUMM, 'svod_gr', CMS.tmp_dir())
@CQT.onerror
def dbl_clk_select_etap(self:mywindow):

    if KPL.is_local_gant_hidden(self):
        return
    g_handle = KPL.Gant_handler(False)
    if g_handle.current_row is None :
        return

    t = CQT.TableContext(self.ui.tbl_preview)
    if g_handle.cld_day not in t.nf:
        return
    for row in t.rows():
        if row.value('_tbl_name') == g_handle.tbl_db.name and row.value('_type_day') == g_handle.type_day.name:
            t.tbl.setProperty(f'_selected_column', t.nf[g_handle.cld_day])
            t.tbl.setProperty(f'_selected_row', row.i)
            t.restore_selected_cell()
            break

def _________________refactored___________________():pass#^^^^^^^^^^^^^^^^^^^^^^^^^^^














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


