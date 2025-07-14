import plotly.graph_objects as go
from plotly.subplots import make_subplots
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ

def graf_html(poki):
    custom_request_c = f'''SELECT * FROM napravlenie WHERE val > 0 and poki = {poki}'''
    list_d_napr = CSQ.custom_request_c(r"SRV:DB_kplan.db\\DB_kplan.db",custom_request_c,rez_dict=True)



    def naming_data(data_file):
        dict_types_graf_num_list_napr = {'full': 1, 'skd': 3, 'std': 4, 'autsors': 5, 'rezerv': 6, 'default_mosh': 2,'rezerv_d': 7}
        dict_data = F.list_of_lists_to_list_of_dicts(data_file)
        rez = {k:dict(map(lambda x: (x[0], F.valm(x[1])) , dict_data[v-1].items())) for k,v in dict_types_graf_num_list_napr.items()}
        return rez

    summ_mosh = 0
    summ_mosh_plan = 0


    summ_list_napr = dict()

    for napr in list_d_napr:
        data_file = F.open_file_c(fr"Z:\Data\gr_pad_mosh_{napr['name_for_file_graf_pad_mosh']}.txt", separ="|")
        if data_file == ['']:
            continue
        napr['list_napr'] = naming_data(data_file)
        for vid, dat in napr['list_napr'].items():
            if vid not in summ_list_napr:
                summ_list_napr[vid] = dict()
            for day, val in dat.items():
                if day not in summ_list_napr[vid]:
                    summ_list_napr[vid][day] = 0
                summ_list_napr[vid][day] += val

        napr['summ_mosch'] = sum([F.valm(_) for _ in  napr['list_napr']['full'].values()])/len(napr['list_napr']['full'])
        napr['summ_mosch_plan'] = sum([F.valm(_) for _ in napr['list_napr']['default_mosh'].values()]) / len(
            napr['list_napr']['default_mosh'])
        summ_mosh += napr['summ_mosch']
        summ_mosh_plan += napr['summ_mosch_plan']

    dict_color_by_type = {
        'Поз. с КД':'#00B0F0',
        'Поз. с ТД':'#00B050',
        'Аутсорс':'#cccc00',
        'Резерв':"#ff2b2b",
        'Долгосрочный':'#553535'
    }


    for napr in list_d_napr:
        mosch = round(napr['summ_mosch'] / summ_mosh * 100,1)
        mosch_plan = round(napr['summ_mosch_plan'] / summ_mosh_plan * 100,1)
        napr['data_color'] = [f'{napr["alias"]} ', napr["color_16"], f'Доля {mosch}/{mosch_plan}%']




    list_d_napr.append(
        {'name': 'СУММ', 'val': 100, 'Пномер': 99, 'Цвет': '180;180;180', 'koef_vneplana': 1.0, 'koef_pogr_norm': 1.0,
         'name_for_file_graf_pad_mosh': 'summ', 'color_16': '#cc8100', 'list_napr': summ_list_napr})
    list_d_napr[-1]['data_color'] = [f'{list_d_napr[-1]["name"]} ', list_d_napr[-1]["color_16"],
                                     f'{100}%']

  #  min_column_count = calc_shortest_line(list_d_napr)
    #
  #  dict_rez = {k:[[] for _ in range((len(list_d_napr)+2))] for k in dict_types_graf_num_list_napr.keys()}
  #
  #  #koef = 21*102.5/1000#21 day, 102.5 kg on post, 1000 v tonn
  #  koef  =1
  #
  #
  #  for i in range(min_column_count):
  #      for key in dict_rez.keys():
  #          summ = 0
  #          dict_rez[key][0].append(hat[i])
  #          num = dict_types_graf_num_list_napr[key]
  #          for j, napr in enumerate(list_d_napr):
  #              dict_rez[key][j+1].append(round(F.valm(list_d_napr[j]['list_napr'][num][i]) * koef))
  #              summ += F.valm(list_d_napr[j]['list_napr'][1][i])
  #          dict_rez[key][-1].append(round(summ) * koef)


    fig = make_subplots(5, 1, y_title="Загрузка, Нормо-час",subplot_titles = " ",vertical_spacing = 0.07)




    for i, napr in enumerate(list_d_napr):
        data_inf= napr['data_color']



        scatt_std = go.Scatter(x=list(napr['list_napr']['std'].keys()), y=list(napr['list_napr']['std'].values()),
                               name='', line=dict(color=dict_color_by_type['Поз. с ТД']),fill='tozeroy',opacity=0.65,   legendgroup='Поз. с ТД',  legendgrouptitle ={"text":'Поз. с ТД'})
        scatt_skd = go.Scatter(x=list(napr['list_napr']['skd'].keys()), y=list(napr['list_napr']['skd'].values()),
                               name='', line=dict(color=dict_color_by_type['Поз. с КД']),fill='tonexty',opacity=0.65,   legendgroup='Поз. с КД',  legendgrouptitle ={"text":'Поз. с КД'})
        scatt_autsors = go.Scatter(x=list(napr['list_napr']['autsors'].keys()), y=list(napr['list_napr']['autsors'].values()),
                                   name='', line=dict(color=dict_color_by_type['Аутсорс']),
                                                                            fill='tozeroy',opacity=0.65,   legendgroup='Аутсорс',  legendgrouptitle ={"text":'Аутсорс'})
        scatt_rezerv = go.Scatter(x=list(napr['list_napr']['rezerv'].keys()), y=list(napr['list_napr']['rezerv'].values()),
                                  name='',
                                   line=dict(color=dict_color_by_type['Резерв']),
                                                            fill='tozeroy',stackgroup='one' ,opacity=0.65,   legendgroup='Резерв',  legendgrouptitle ={"text":'Резерв'})
        scatt_rezerv_d = go.Scatter(x=list(napr['list_napr']['rezerv_d'].keys()), y=[_*-1 for _ in napr['list_napr']['rezerv_d'].values()],
                                  name='',
                                   line=dict(color=dict_color_by_type['Долгосрочный']),
                                                            fill='tonexty',stackgroup='two' ,opacity=0.65,   legendgroup='Долгосрочный',  legendgrouptitle ={"text":'Долгосрочный'})
        scatt_default_line = go.Scatter(x=list(napr['list_napr']['default_mosh'].keys()), y=list(napr['list_napr']['default_mosh'].values()),
                                        name ='',  line = dict(color='#e13d3d'),opacity=0.65,   legendgroup='Макс мощность',  legendgrouptitle ={"text":'Макс мощность'})
        scatt = go.Scatter(x=list(napr['list_napr']['full'].keys()), y=list(napr['list_napr']['full'].values()),
                           name=data_inf[0], line=dict(color=data_inf[1]), stackgroup='one', opacity=0.65,
                           legendgroup='Направления', legendgrouptitle={"text": 'Направления'})
        num_trace = i+1
        fig.add_trace(scatt_rezerv_d, num_trace, 1)
        fig.add_trace(scatt_rezerv, num_trace, 1)
        fig.add_trace(scatt, num_trace, 1)
        fig.add_trace(scatt_skd, num_trace, 1)
        fig.add_trace(scatt_std, num_trace, 1)
        fig.add_trace(scatt_autsors, num_trace, 1)
        fig.add_trace(scatt_default_line, num_trace, 1)

        fig.add_annotation(text=f'{data_inf[0]} {data_inf[2]}' ,
                        xref="paper", yref="paper",
                        x=0.97, y=1.23 - 0.2252*num_trace, showarrow=False,
                        font=dict(
                            family="sans serif",
                            size=18,
                            color=data_inf[1])
                           )
    fig.add_vline(x=F.now("%d.%m.%Y"), line_width=2, line_dash="dash", line_color="green", opacity=0.65)

    fig.update_xaxes(tickangle=45, tickfont=dict(family='Rockwell', color='black', size=12))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),legend=dict(traceorder='grouped+reversed',tracegroupgap=20), height=int(350*len(list_d_napr)))

    with open('templates\\graf_pad_mosh.html', 'w+', encoding='utf-8') as f:
        f.write(fig.to_html(full_html=False))
    return fig.to_html(full_html=False)

#graf_html()
