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
    # =================add_ui============================
    self.parent_for_grafic = self.ui.la_parent_for_grafic

    napr_name = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME[selected_napr]['name_for_file_graf_pad_mosh']

    list_napr = F.open_file_c(fr"Z:\Data\gr_pad_mosh_{napr_name}.txt", separ="|")

    color16 = self.Data_plan.DICT_NAPRAVLENIE_BY_NAME[selected_napr]['color_16']

    color = [[f'{selected_napr} ', color16, f'Макс. мощность {round(F.valm(list_napr[2][0]))} час.', '#00B0F0',
              'с КД', '#00B050', 'с ТД', '#cccc00', 'аутсорс', "#ff2b2b", "резерв"],]

    rez = [[],[]]
    rez_skd = [[],[]]
    rez_std = [[],[]]
    rez_autsors = [[],[]]
    rez_rezerv = [[],[]]
    rez_default_mosh = [[],[]]
    # koef = 21*102.5/1000#21 day, 102.5 kg on post, 1000 v tonn
    koef = 1

    for i in range(len(list_napr[0])):
        rez[0].append(list_napr[0][i])
        rez[1].append(round(F.valm(list_napr[1][i]) * koef))

        rez_skd[0].append(list_napr[0][i])
        rez_skd[1].append(round(F.valm(list_napr[3][i]) * koef))

        rez_std[0].append(list_napr[0][i])
        rez_std[1].append(round(F.valm(list_napr[4][i]) * koef))


        rez_autsors[0].append(list_napr[0][i])
        rez_autsors[1].append(round(F.valm(list_napr[5][i]) * koef))


        rez_rezerv[0].append(list_napr[0][i])
        rez_rezerv[1].append(round(F.valm(list_napr[6][i]) * koef))

        rez_default_mosh[0].append(list_napr[0][i])
        rez_default_mosh[1].append(round(F.valm(list_napr[2][i]) * koef))

    fig = make_subplots(1, 1, y_title="Загрузка, Нормо-час", subplot_titles=" ",
                        horizontal_spacing= 0, vertical_spacing=0)
    i = 1
    scatt_std = go.Scatter(x=rez_std[0], y=rez_std[i], name=color[0][6], line=dict(color=color[0][5]),
                           fill='tozeroy', opacity=0.65)
    scatt_skd = go.Scatter(x=rez_skd[0], y=rez_skd[i], name=color[0][4], line=dict(color=color[0][3]),
                           fill='tonexty', opacity=0.65)
    scatt_autsors = go.Scatter(x=rez_autsors[0], y=rez_autsors[i], name=color[0][8],
                               line=dict(color=color[0][7]),
                               fill='tozeroy', opacity=0.65)
    scatt_rezerv = go.Scatter(x=rez_rezerv[0], y=rez_rezerv[i], name=color[0][10],
                              line=dict(color=color[0][9]),
                              fill='tozeroy', stackgroup='one', opacity=0.65)
    scatt = go.Scatter(x=rez[0], y=rez[i], name=color[0][0], line=dict(color=color[0][1]), stackgroup='one',
                       opacity=0.65)
    scatt_default_line = go.Scatter(x=rez[0], y=rez_default_mosh[i], name=color[0][2],
                                    line=dict(color='#e13d3d'), opacity=0.65)

    fig.add_trace(scatt_rezerv, 1, 1)
    fig.add_trace(scatt, 1, 1)
    fig.add_trace(scatt_skd, 1, 1)
    fig.add_trace(scatt_std, 1, 1)

    fig.add_trace(scatt_autsors, 1, 1)
    fig.add_trace(scatt_default_line, 1, 1)

    fig.add_annotation(text=color[0][0],
                       xref="paper", yref="paper",
                       x=0.97, y=1.23 - 0.2252 * i, showarrow=False,
                       font=dict(
                           family="sans serif",
                           size=18,
                           color=color[0][1])
                       )

    fig.update_xaxes(tickangle=45, tickfont=dict(family='Rockwell', color='black', size=14))
    fig.update_layout(legend=dict(traceorder='reversed'), height=int(520))

    try:
        self.parent_for_grafic.removeWidget(self.browser)
    except:
        pass
    self.browser = QtWebEngineWidgets.QWebEngineView(self)
    self.parent_for_grafic.addWidget(self.browser)


    CQT.output_gant(self, fig, self.browser, selected_napr, tmp_dir())
