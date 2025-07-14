import plotly.express as px
import pandas as pd
import project_cust_38.Cust_Functions as F

import random

def random_colour():
    # Generating a random number in between 0 and 2^24
    color = random.randrange(0, 2 ** 24)
    # Converting that number from base-10
    # (decimal) to base-16 (hexadecimal)
    return  hex(color)


def fiig(plan):
    df = pd.DataFrame(plan)
    fig = px.timeline(df, x_start="Начало", x_end="Завершение", y="РЦ", color='РЦ', facet_row_spacing=0.6,
                      facet_col_spacing=0.6, opacity=0.9, hover_data=['Проект', 'МК', 'Наменование', 'Номер', 'Минут'],
                      title='график проектов')
    for i, d in enumerate(fig.data):
        d.width = df[df['РЦ'] == d.name]['Вес']

    """    
    fig.add_hrect( y0="Проект C", y1="Проект C",
                  annotation_text="аываыв", annotation_position = 'inside top left',
                  fillcolor="green", opacity=0.25, line_width=0,               annotation_font_size=20,
                  annotation_font_color="blue")
    fig.add_vline(x="2009-02-06", line_width=3, line_dash="dash", line_color="green", opacity=0.06)
"""

    # fig.add_hline(y="  ")
    # fig.add_hline(y=" ")
    return fig


# fig.add_vrect(x0=0.9, x1=2)
# fig.show()

def fig_porc_projects(plan):
    df = pd.DataFrame(plan)
    fig = px.timeline(df, x_start="Начало", x_end="Завершение", y="Проект", color='РЦ', facet_row_spacing=0.2,
                      facet_col_spacing=0.1, opacity=0.5, hover_data=plan[0].keys(), title=f'Диаграмма проектов')
    # for i, d in enumerate(fig.data):
    #    d.width = df[df['РЦ'] == d.name]['РЦ']

    """    
    fig.add_hrect( y0="Проект C", y1="Проект C",
                  annotation_text="аываыв", annotation_position = 'inside top left',
                  fillcolor="green", opacity=0.25, line_width=0,               annotation_font_size=20,
                  annotation_font_color="blue")
    fig.add_vline(x="2009-02-06", line_width=3, line_dash="dash", line_color="green", opacity=0.06)
"""

    # fig.add_hline(y="  ")
    # fig.add_hline(y=" ")
    return fig


# fig.add_vrect(x0=0.9, x1=2)
# fig.show()

def fig_podetalno_naproject_rc(plan, proj):
    df = pd.DataFrame([_ for _ in plan if proj in _['Проект']])

    fig = px.timeline(df, x_start="Начало", x_end="Завершение", y="Номер", color='РЦ', facet_row_spacing=0.2,
                      facet_col_spacing=0.1, opacity=0.5, hover_data=plan[0].keys(), title=f'Диаграмма по {proj}')
    # for i, d in enumerate(fig.data):
    #    d.width = df[df['РЦ'] == d.name]['РЦ']

    """    
    fig.add_hrect( y0="Проект C", y1="Проект C",
                  annotation_text="аываыв", annotation_position = 'inside top left',
                  fillcolor="green", opacity=0.25, line_width=0,               annotation_font_size=20,
                  annotation_font_color="blue")
    fig.add_vline(x="2009-02-06", line_width=3, line_dash="dash", line_color="green", opacity=0.06)
"""

    # fig.add_hline(y="  ")
    # fig.add_hline(y=" ")
    return fig

def fig_podetalno_narc_projects(plan,vert_filtr, vert_znach,color_separ,tochnost):

    nach_konec = ["Начало", 'Конец']
    if tochnost == 'Помаршрутно':
        nach_konec = ['Начало мк', 'Завершение мк']
        set_mk = set()
        plan_tmp =[plan[0]]
        nk_mk = F.num_col_by_name_in_hat_c(plan,'МК')
        for item in plan[1:]:
            if item[nk_mk] not in set_mk:
                plan_tmp.append(item)
                set_mk.add(item[nk_mk])
        plan = plan_tmp
    plan = F.list_to_dict(plan)
    if vert_znach != '':
        filtr = [_ for _ in plan if vert_znach in _[vert_filtr]]
        df = pd.DataFrame(filtr)
    else:
        df = pd.DataFrame(plan)
    fig = px.timeline(df, x_start=nach_konec[0], x_end=nach_konec[1], y=vert_filtr, color=color_separ, facet_row_spacing=0.2,
                      facet_col_spacing=0.2, opacity=0.5, hover_data=plan[0].keys(),
                      title=f'Диаграмма {vert_filtr}-{color_separ} по {vert_znach}')
    #for i, d in enumerate(fig.data):
    #    d.width = df[df['Проект'] == d.name]['Пост']/10 + 0.1


    """    
    fig.add_hrect( y0="Проект C", y1="Проект C",
                  annotation_text="аываыв", annotation_position = 'inside top left',
                  fillcolor="green", opacity=0.25, line_width=0,               annotation_font_size=20,
                  annotation_font_color="blue")
    fig.add_vline(x="2009-02-06", line_width=3, line_dash="dash", line_color="green", opacity=0.06)
"""

    # fig.add_hline(y="  ")
    # fig.add_hline(y=" ")
    return fig

