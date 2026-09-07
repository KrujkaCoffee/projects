from __future__ import annotations


import plotly.graph_objects as go
from plotly.subplots import make_subplots
import project_cust_38.Cust_Functions as F
from typing import TYPE_CHECKING
import project_cust_38.Cust_Qt as CQT
from project_cust_38.Cust_mes import tmp_dir
try:
    from PyQt5 import QtCore
    from PyQt5 import QtWebEngineWidgets
    from PyQt5.QtWidgets import QVBoxLayout, QApplication
except:
    print(f'PyQt5 не подгружен QtWebEngineWidgets')
    pass
if TYPE_CHECKING:
    from MKart import mywindow


def generate(self:mywindow,selected_napr):
    def naming_data(data_file):
        dict_types_graf_num_list_napr = {'full': 1, 'skd': 3, 'std': 4, 'autsors': 5, 'rezerv': 6, 'default_mosh': 2,'rezerv_d': 7}
        dict_data = F.list_of_lists_to_list_of_dicts(data_file)
        rez = {k:dict(map(lambda x: (x[0], F.valm(x[1])) , dict_data[v-1].items())) for k,v in dict_types_graf_num_list_napr.items()}
        return rez
    # =================add_ui============================
    list_napr = []
    parent_for_grafic = self.ui.la_parent_for_grafic
    summ_all_vals_data_napr = dict()

    dict_color_by_type = {
        'Поз. с КД':'#00B0F0',
        'Поз. с ТД':'#00B050',
        'Аутсорс':'#cccc00',
        'Резерв':"#ff2b2b",
        'Долгосрочный':'#553535'
    }
    if selected_napr is None:

        summ_mosh = 0
        summ_mosh_plan = 0

        for napr, percent, name_for_file in [[_['name'], _['val'], _['name_for_file_graf_pad_mosh']] for _ in
                                             self.Data_plan.DICT_NAPRAVLENIE.values() if _['poki'] == self.place.poki]:
            data_file = F.open_file_c(fr"Z:\Data\gr_pad_mosh_{name_for_file}.txt", separ="|")
            if data_file == ['']:
                continue

            naming_data_vals = naming_data(data_file)
            for vid, dat in naming_data_vals.items():

                if vid not in summ_all_vals_data_napr:
                    summ_all_vals_data_napr[vid] = dict()
                for day, val in dat.items():
                    if day not in summ_all_vals_data_napr[vid]:
                        summ_all_vals_data_napr[vid][day] = 0
                    summ_all_vals_data_napr[vid][day] += val

            napr_summ_mosch = sum([F.valm(_) for _ in naming_data_vals['full'].values()]) / len(
                naming_data_vals['full'])
            napr_summ_mosch_plan = sum([F.valm(_) for _ in naming_data_vals['default_mosh'].values()]) / len(
                naming_data_vals['default_mosh'])
            summ_mosh += napr_summ_mosch
            summ_mosh_plan += napr_summ_mosch_plan

        color16 = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME['']['color_16']
        color = [[f'СУММ ', color16, f'Макс. мощность {round(summ_mosh)} час.', '#00B0F0',
                  'с КД', '#00B050', 'с ТД', '#cccc00', 'аутсорс', "#ff2b2b", "резерв"],]
        data_color = [f'CУММ ', color16, f'Доля 100%']
    else:
        napr_name = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME[selected_napr]['name_for_file_graf_pad_mosh']
        alias = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME[selected_napr]['alias']
        percent = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME[selected_napr]['val']
        list_napr = F.open_file_c(fr"Z:\Data\gr_pad_mosh_{napr_name}.txt", separ="|")
        summ_all_vals_data_napr  = naming_data(list_napr)
        color16 = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME[selected_napr]['color_16']
        color = [[f'{selected_napr} ', color16, f'Макс. мощность {round(F.valm(list_napr[2][0]))} час.', '#00B0F0',
                  'с КД', '#00B050', 'с ТД', '#cccc00', 'аутсорс', "#ff2b2b", "резерв"],]
        data_color = [f'{alias} ', color16, f'Доля {percent}%']
    koef = 1
    data = summ_all_vals_data_napr
    def gen_set(name_key):
        return [list(data[name_key].keys()),[round(v * koef) for v in data[name_key].values()]]
    rez = gen_set('full')
    rez_skd =  gen_set('skd')
    rez_std =  gen_set('std')
    rez_autsors =  gen_set('autsors')
    rez_rezerv =  gen_set('rezerv')
    rez_rezerv_d =  gen_set('rezerv_d')
    rez_default_mosh =  gen_set('default_mosh')
    # koef = 21*102.5/1000#21 day, 102.5 kg on post, 1000 v tonn
    customdata = []
    for dt, val in data['full'].items():
        customdata.append([round(val+data['rezerv'][dt])])

    fig = make_subplots(1, 1, y_title="Загрузка, Нормо-час", subplot_titles=" ", vertical_spacing=0.07)

    data_inf = data_color

    scatt_std = go.Scatter(x=rez_std[0], y=rez_std[1],
                           name='Поз. с ТД', line=dict(color=dict_color_by_type['Поз. с ТД']), fill='tozeroy', opacity=0.65,
                           legendgroup='Поз. с ТД', legendgrouptitle={"text": 'Поз. с ТД'})
    scatt_skd = go.Scatter(x=rez_skd[0], y=rez_skd[1],
                           name='Поз. с КД', line=dict(color=dict_color_by_type['Поз. с КД']), fill='tonexty', opacity=0.65,
                           legendgroup='Поз. с КД', legendgrouptitle={"text": 'Поз. с КД'})
    scatt_autsors = go.Scatter(x=rez_autsors[0],
                               y=rez_autsors[1],
                               name='Аутсорс', line=dict(color=dict_color_by_type['Аутсорс']),
                               fill='tozeroy', opacity=0.65, legendgroup='Аутсорс',
                               legendgrouptitle={"text": 'Аутсорс'})
    scatt_rezerv = go.Scatter(x=rez_rezerv[0],
                              y=rez_rezerv[1],
                              name='Резерв',
                              line=dict(color=dict_color_by_type['Резерв']),
                              fill='tozeroy', stackgroup='one', opacity=0.65, legendgroup='Резерв',
                              legendgrouptitle={"text": 'Резерв'})
    scatt_rezerv_d = go.Scatter(x=rez_rezerv_d[0],
                                y=[_ * -1 for _ in rez_rezerv_d[1]],
                                name='Долгосрочный',
                                line=dict(color=dict_color_by_type['Долгосрочный']),
                                fill='tonexty', stackgroup='two', opacity=0.65, legendgroup='Долгосрочный',
                                legendgrouptitle={"text": 'Долгосрочный'})
    scatt_default_line = go.Scatter(x=rez_default_mosh[0],
                                    y=rez_default_mosh[1],
                                    name='Макс мощность', line=dict(color='#e13d3d'), opacity=0.65, legendgroup='Макс мощность',
                                    legendgrouptitle={"text": 'Макс мощность'})
    scatt = go.Scatter(x=rez[0], y=rez[1],
                       name=data_inf[0], line=dict(color=data_inf[1]), stackgroup='one', opacity=0.65,
                       customdata = customdata,
                       hovertemplate=
                       'Дата: %{x}<br>' +
                       'Загрузка: %{customdata[0]} н-час.' +
                       '<extra></extra>',
                       legendgroup='Направления', legendgrouptitle={"text": 'Направления'})
    num_trace = 1
    fig.add_trace(scatt_rezerv_d, num_trace, 1)
    fig.add_trace(scatt_rezerv, num_trace, 1)
    fig.add_trace(scatt, num_trace, 1)
    fig.add_trace(scatt_skd, num_trace, 1)
    fig.add_trace(scatt_std, num_trace, 1)
    fig.add_trace(scatt_autsors, num_trace, 1)
    fig.add_trace(scatt_default_line, num_trace, 1)

    fig.add_annotation(text=f'{data_inf[0]} {data_inf[2]}',
                       xref="paper", yref="paper",
                       x=0.97, y=1.23 - 0.2252 * num_trace, showarrow=False,
                       font=dict(
                           family="sans serif",
                           size=18,
                           color=data_inf[1])
                       )
    fig.add_vline(x=F.now("%d.%m.%Y"), line_width=2, line_dash="dash", line_color="green", opacity=0.65)

    fig.update_xaxes(tickangle=45, tickfont=dict(family='Rockwell', color='black', size=12))


    fig.update_xaxes(tickangle=45, tickfont=dict(family='Rockwell', color='black', size=14))
    fig.update_layout(legend=dict(traceorder='reversed'))
    if self.Data_plan.BROWSER_GR_PAD_MOSH is None:
        self.Data_plan.BROWSER_GR_PAD_MOSH = QtWebEngineWidgets.QWebEngineView(self)
        parent_for_grafic.addWidget(self.Data_plan.BROWSER_GR_PAD_MOSH)
    CQT.output_gant(self, fig, self.Data_plan.BROWSER_GR_PAD_MOSH, selected_napr, tmp_dir())
