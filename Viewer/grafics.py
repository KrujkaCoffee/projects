# Import Data https://habr.com/ru/post/468295/
import copy

import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


def load_elements(self,spis,vid):
    try:
        self.figure.clear()
    except:
        pass
    self.figure = plt.figure(dpi= 80)
    self.canvas = FigureCanvas(self.figure)
    self.toolbar = NavigationToolbar(self.canvas, self)
    if vid == 'Понедельный график выработки и отгрузок':
        create_fig(self.figure.add_subplot(111),spis)
    if vid == 'План-фактный анализ по месяцам':
        create_fig_plan_fact(self.figure.add_subplot(111),spis,self)
    self.figure.subplots_adjust(0.03, 0.11, 0.98, 0.94)
    self.canvas.draw()
''
def create_fig_plan_fact(plt,spis,self):
    """b: blue
g: green
r: red
c: cyan
m: magenta
y: yellow
k: black
w: white"""
    spis_new = copy.deepcopy(spis)
    for i in range(1,len(spis_new)):
        spis_new[i][6] =spis_new[i][6] /10
    #df = pd.read_csv('https://github.com/selva86/datasets/raw/master/AirPassengers.csv')
    df = pd.DataFrame.from_records(spis_new[1:],columns=spis_new[0])
    # Get the Peaks and Troughs

    df.date = df['Месяц'].values
    df.value = df['План, н-см.'].values
    df.otgr = df['Отгрузка, кг.'].values
    df.fact = df['Факт, н-см.'].values
    df.vneplan = df['Внеплан, н-см.'].values
    df.summ_fact = df['Сумм. Факт, н-см.'].values
    df.summ_sv = df['Сумм св_швов, м.'].values
    df.f_1 = df['Брак производственный'].values
    df.f_2 = df['Ошибка нормирования и технологии'].values
    df.f_3 = df['Доработка КД'].values
    df.f_4 = df['Обучение'].values
    df.f_5 = df['Работы на внешней площадке'].values
    df.f_6 = df['Ошибка планирования нарядов(не использовать)'].values#'Ошибка планирования нарядов(не использовать)'
    df.f_7 = df['Отсутствие заказа на производство(не использовать)'].values
    df.f_8 = df['Исправление чужого брака'].values
    df.f_9 = df['Цеховая оснастка(для нужд цеха)'].values
    df.f_10 = df['Простой'].values

    doublediff = np.sign(np.diff(df.fact))
    peak_locations = np.where(doublediff == 1)[0] + 1

    doublediff2 = np.sign(np.diff(-1*df.fact))
    trough_locations = np.where(doublediff2 == 1)[0] + 1

    doublediff_2 = df.otgr
    peak_locations_2 = np.where(doublediff_2)[0]

    doublediff2_2 = df.otgr
    trough_locations_2 = np.where(doublediff2_2)[0]

    doublediff3 = df.fact
    trough_locations_3 = np.where(doublediff3)[0]

    doublediff5 = df.vneplan
    trough_locations_5 = np.where(doublediff5)[0]

    trough_locations_6 = np.where(df.summ_fact)[0]

    trough_locations_svar = np.where(df.summ_sv)[0]

    trough_locations_f_1 = np.where(df.f_1)[0]
    trough_locations_f_2 = np.where(df.f_2)[0]
    trough_locations_f_3 = np.where(df.f_3)[0]
    trough_locations_f_4 = np.where(df.f_4)[0]
    trough_locations_f_5 = np.where(df.f_5)[0]
    trough_locations_f_6 = np.where(df.f_6)[0]
    trough_locations_f_7 = np.where(df.f_7)[0]
    trough_locations_f_8 = np.where(df.f_8)[0]
    trough_locations_f_9 = np.where(df.f_9)[0]
    trough_locations_f_10 = np.where(df.f_10)[0]



    # Draw Plot
    #plt.figure(figsize=(16,10), dpi= 80)
    #plt = Figure(figsize=(16,10), dpi= 80)
    plt.plot('Месяц', 'План, н-см.', data=df, color='tab:blue', label='План, н-см.',linewidth = 5)
    plt.plot('Месяц', 'Отгрузка, кг.', data=df, color='y', label='Отгрузка, кг.',linewidth = 5)
    plt.plot('Месяц', 'Факт, н-см.', data=df, color='g', label='Факт, н-см.', linewidth=5)
    plt.plot('Месяц', 'Внеплан, н-см.', data=df, color='r', label='Внеплан, н-см.', linewidth=5)
    plt.plot('Месяц', 'Сумм. Факт, н-см.', data=df, color='#C65911', label='Сумм. Факт, н-см.', linewidth=5)
    plt.plot('Месяц', 'Брак производственный', data=df, color='#C15911', label='Брак производственный', linewidth=3, linestyle = "--")
    plt.plot('Месяц', 'Ошибка нормирования и технологии', data=df, color='#B3F410', label='Ошибка нормирования и технологии', linewidth=3,
             linestyle="--")
    plt.plot('Месяц', 'Доработка КД', data=df, color='#5D14F0', label='Доработка КД', linewidth=3,
             linestyle="--")
    plt.plot('Месяц', 'Обучение', data=df, color='#BC4890', label='Обучение', linewidth=3,
             linestyle="--")
    plt.plot('Месяц', 'Работы на внешней площадке', data=df, color='#0DD6F7', label='Работы на внешней площадке', linewidth=3,
             linestyle="--")
    plt.plot('Месяц', 'Ошибка планирования нарядов(не использовать)', data=df, color='#D7F90B', label='Ошибка планирования нарядов(не использовать)', linewidth=3,
             linestyle="-.")
    plt.plot('Месяц', 'Отсутствие заказа на производство(не использовать)', data=df, color='#7BA85C', label='Отсутствие заказа на производство(не использовать)', linewidth=3,
             linestyle="-.")
    plt.plot('Месяц', 'Исправление чужого брака', data=df, color='r', label='Исправление чужого брака', linewidth=3,
             linestyle=":")
    plt.plot('Месяц', 'Цеховая оснастка(для нужд цеха)', data=df, color='#A06468', label='Цеховая оснастка(для нужд цеха)', linewidth=3,
             linestyle=":")
    plt.plot('Месяц', 'Простой', data=df, color='#689B9C', label='Аварийные работы', linewidth=3,
             linestyle=":")
    plt.plot('Месяц', 'Сумм св_швов, м.', data=df, color='y', label='Сумм св_швов, м.', linewidth=5,
             linestyle=":")

    #plt.scatter(df.date[peak_locations], df.value[peak_locations], marker=mpl.markers.CARETUPBASE, color='tab:green', s=200, label='Рост Факт, н-см.')
    #plt.scatter(df.date[trough_locations], df.value[trough_locations], marker=mpl.markers.CARETDOWNBASE, color='tab:red', s=200, label='Падение Факт, н-см.')
    #plt.scatter(df.date[peak_locations_2], df.otgr[peak_locations_2], marker=".", color='tab:green', s=300, label='Отгрузка, кг.')
    #plt.scatter(df.date[trough_locations_3], df.fact[trough_locations_3], marker=".", color='tab:green', s=300,
    #            label='Факт, н-см.')
    #plt.scatter(df.date[trough_locations_5], df.vneplan[trough_locations_5], marker=".", color='tab:green', s=300,
    #            label='Внеплан, н-см.')
    #plt.scatter(df.date[trough_locations_6], df.summ_fact[trough_locations_6], marker=".", color='#C65911', s=300,
    #            label='Сумм. Факт, н-см.')

    # Annotate
    for t in trough_locations:
        plt.text(df.date[t], df.value[t] * 1.03, df.value[t], horizontalalignment='center', color='darkred', size=15)
    for p in peak_locations:
        plt.text(df.date[p], df.value[p] * 1.03, df.value[p], horizontalalignment='center', color='darkgreen', size = 15)

    for t, p in zip(trough_locations_2,peak_locations_2):
        plt.text(df.date[p], df.otgr[p]*1.03, (df.otgr[p]* 100).astype(np.int64), horizontalalignment='center', color='darkgreen', size = 15)
        plt.text(df.date[t], df.otgr[t]*1.03, (df.otgr[t]* 100).astype(np.int64), horizontalalignment='center', color='darkred', size = 15)

    for p in trough_locations_3:
        plt.text(df.date[p], df.fact[p] * 1.03, df.fact[p], horizontalalignment='center', color='darkgreen', size=15)

    for p in trough_locations_5:
        plt.text(df.date[p], df.vneplan[p] * 1.03, df.vneplan[p], horizontalalignment='center', color='darkgreen', size=15)

    for p in trough_locations_6:
        plt.text(df.date[p], df.summ_fact[p] * 1.03, df.summ_fact[p], horizontalalignment='center', color='darkgreen', size=15)

    for p in trough_locations_f_1:
        plt.text(df.date[p], df.f_1[p] * 1.03, df.f_1[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_2:
        plt.text(df.date[p], df.f_2[p] * 1.03, df.f_2[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_3:
        plt.text(df.date[p], df.f_3[p] * 1.03, df.f_3[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_4:
        plt.text(df.date[p], df.f_4[p] * 1.03, df.f_4[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_5:
        plt.text(df.date[p], df.f_5[p] * 1.03, df.f_5[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_6:
        plt.text(df.date[p], df.f_6[p] * 1.03, df.f_6[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_7:
        plt.text(df.date[p], df.f_7[p] * 1.03, df.f_7[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_8:
        plt.text(df.date[p], df.f_8[p] * 1.03, df.f_8[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_9:
        plt.text(df.date[p], df.f_9[p] * 1.03, df.f_9[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_f_10:
        plt.text(df.date[p], df.f_10[p] * 1.03, df.f_10[p], horizontalalignment='center', color='darkgreen', size=15)
    for p in trough_locations_svar:
        plt.text(df.date[p], df.summ_sv[p] * 1.03, (df.summ_sv[p]* 10).astype(np.int64), horizontalalignment='center', color='darkgreen', size=15)

    # Decoration
    plt.set_title(f"План-фактный анализ по месяцам {self.ui.cmb_podrazdelenie.currentText()}")
    for label in plt.get_xticklabels(which='major'):
        label.set(rotation=90, horizontalalignment='right')

    plt.legend(loc='upper left')
    plt.grid(axis='y', alpha=.3)
    #plt.show()
    return plt



def create_fig(plt,spis):
    """b: blue
g: green
r: red
c: cyan
m: magenta
y: yellow
k: black
w: white"""
    #df = pd.read_csv('https://github.com/selva86/datasets/raw/master/AirPassengers.csv')
    df = pd.DataFrame.from_records(spis[1:],columns=spis[0])
    # Get the Peaks and Troughs
    data = df['Выработка, н-см.'].values
    df.date = df['Дата конца'].values
    df.value = df['Выработка, н-см.'].values
    df.otgr = df['Заверш. вес, кг.'].values
    df.post = df['Постов'].values
    df.proizv = df["Произв-ть,н-см./см."].values

    doublediff = np.sign(np.diff(df.value))
    peak_locations = np.where(doublediff == 1)[0] + 1

    doublediff2 = np.sign(np.diff(-1*df.value))
    trough_locations = np.where(doublediff2 == 1)[0] + 1


    doublediff_2 = df.otgr
    peak_locations_2 = np.where(doublediff_2)[0]

    doublediff2_2 = df.otgr
    trough_locations_2 = np.where(doublediff2_2)[0]

    doublediff3 = df.post
    trough_locations_3 = np.where(doublediff3)[0]

    diff_proizv = df.proizv
    locations_proizv = np.where(diff_proizv)[0]

    # Draw Plot
    #plt.figure(figsize=(16,10), dpi= 80)
    #plt = Figure(figsize=(16,10), dpi= 80)
    plt.plot('Дата конца', 'Выработка, н-см.', data=df, color='tab:blue', label='Выработка, н-см.',linewidth = 5)
    plt.plot('Дата конца', 'Заверш. вес, кг.', data=df, color='y', label='Заверш. вес, кг.',linewidth = 5)
    plt.plot('Дата конца', 'Постов', data=df, color='g', label='Постов', linewidth=5)
    plt.plot('Дата конца', "Произв-ть,н-см./см.", data=df, color='r', label="Произв-ть,н-см./см.", linewidth=5)

    plt.scatter(df.date[peak_locations], df.value[peak_locations], marker=mpl.markers.CARETUPBASE, color='tab:green', s=200, label='Рост выработка')
    plt.scatter(df.date[trough_locations], df.value[trough_locations], marker=mpl.markers.CARETDOWNBASE, color='tab:red', s=200, label='Падение выработка')
    plt.scatter(df.date[peak_locations_2], df.otgr[peak_locations_2], marker=".", color='tab:green', s=300, label='Заверш. вес')
    plt.scatter(df.date[trough_locations_3], df.post[trough_locations_3], marker=".", color='tab:green', s=300,
                label='Постов')
    plt.scatter(df.date[locations_proizv], df.proizv[locations_proizv], marker=".", color='tab:green', s=200,
                label="Произв-ть,кг/см.")

    # Annotate
    for t in trough_locations:
        plt.text(df.date[t], df.value[t] * 1.03+15, df.value[t], horizontalalignment='center', verticalalignment ='top', color='darkred', size=10)
    for p in peak_locations:
        plt.text(df.date[p], df.value[p] * 1.03+15, df.value[p], horizontalalignment='center', verticalalignment ='top', color='darkgreen', size = 10)


    for t, p in zip(trough_locations_2,peak_locations_2):
        plt.text(df.date[p], df.otgr[p]*1.03+15, (df.otgr[p]*100).astype(np.int64), horizontalalignment='center', verticalalignment ='top', color='darkgreen', size = 10)
        plt.text(df.date[t], df.otgr[t]*1.03+15, (df.otgr[t]*100).astype(np.int64), horizontalalignment='center', verticalalignment ='top', color='darkred', size = 10)

    for p in trough_locations_3:
        plt.text(df.date[p], df.post[p] * 1.03+15, df.post[p]/10, horizontalalignment='center', verticalalignment ='top', color='darkgreen', size=10)

    for p in locations_proizv:
        plt.text(df.date[p], df.proizv[p] * 1.03+15, (df.proizv[p]/100).astype(np.float64) , horizontalalignment='center', verticalalignment ='top', color='darkgreen', size=10)

    # Decoration
    plt.set_title("Понедельный график выработки по нарядам и отгрузок чистый металл")
    for label in plt.get_xticklabels(which='major'):
        label.set(rotation=90, horizontalalignment='right')
    #plt.ylim(50,750)
    #xtick_location = df.index.tolist()[::6]
    #xtick_labels = df.date.tolist()[::6]
    #plt.xticks(ticks=xtick_location, labels=xtick_labels, rotation=90, fontsize=12, alpha=.7)
    #plt.title("Peak and Troughs of Air Passengers value (1949 - 1969)", fontsize=22)
    #plt.yticks(fontsize=12, alpha=.7)

    # Lighten borders
    #plt.gca().spines["top"].set_alpha(.0)
    #plt.gca().spines["bottom"].set_alpha(.3)
    #plt.gca().spines["right"].set_alpha(.0)
    #plt.gca().spines["left"].set_alpha(.3)
    plt.legend(loc='upper left')
    plt.grid(axis='y', alpha=.3)
    #plt.show()
    return plt
