import plotly.express as px
import pandas as pd


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

def fig_podetalno_narc_projects(plan, rc):
    filtr = [_ for _ in plan if rc in _['РЦ']]
    df = pd.DataFrame(filtr)

    fig = px.timeline(df, x_start="Начало", x_end="Завершение", y="Номер", color='Проект', facet_row_spacing=0.2,
                      facet_col_spacing=0.1, opacity=0.5, hover_data=plan[0].keys(), title=f'Диаграмма по {rc}')
    for i, d in enumerate(fig.data):
        d.width = df[df['Проект'] == d.name]['Пост']/10 + 0.1


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
