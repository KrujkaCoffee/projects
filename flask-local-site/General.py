import sys
from pathlib import Path

# Получаем абсолютный путь к родительскому каталогу текущего файла
parent_dir = str(Path(__file__).parent.parent)  # Дважды parent для поднятия на уровень выше

# Добавляем родительский каталог в sys.path
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


import os
import socket
from flask import Flask, render_template, url_for, request, redirect
import project_cust_38.Cust_SQLite as CSQ
import graf_pad_mosh as GRAF
from jinja2 import Environment, BaseLoader
from threading import Thread
from flask import Response, json, jsonify, send_file
import datetime

import project_cust_38.Cust_Functions as F
from report_parser import start_daemon_thread, get_pictures_type, check_report, DEPATMENTS, excel_maker
import settings
from remark_journal import Remark


def generate_html(my_list):
    rtemplate = Environment(loader=BaseLoader()).from_string(my_list)

    return rtemplate

# https://fontawesome.ru/all-icons/

if F.existence_file_c('templates') is False:
    F.create_dir_c('templates')

if F.existence_file_c('static/css') is False:
    F.create_dir_c('static/css')

if F.existence_file_c('static/images') is False:
    F.create_dir_c('static/images')

list_projects = [{"way":"КЛ","nn":'0193-21'},{"way":"КТ","nn":'0134-721'},
                 {"way":"КЛ","nn":'3193-21'},{"way":"КТ","nn":'3134-721'}]
list_ways = sorted(list({x['way'] for x in list_projects}))

#Z:\MES_setup\vbs\Setup.vbs
INSTRUMENTS_MENU = [{'Наименование': 'Десктопное приложение МЕС',
                     'Описание': 'Такая версия позволяет получить доступ к более богатому набору функций, '
                                 'которые часто отсутствуют в мобильных приложениях.', 'Ссылка': r'http://192.168.50.44:20011/hs/mes/open_local_path_dir/MES_setup/Setup.lnk'},
    {'Наименование': 'Выработка цеха', 'Описание': 'Выработка сборочного цеха', 'Ссылка': 'http://stat.powerz.ru/'},
    {'Наименование': 'Веб приложение МЕС', 'Описание': 'Модули обсчета и пр.', 'Ссылка': 'http://mesinfo.powerz.ru:20013/'},
]

zag_pr = ['Заготовительное производство', ["""Выполняет раскрой изделий чёрных и нержавеющих заготовок из 
листового металлопроката- способом лазерной резки металла. Имеем гильотину для резки металла. Имеет возможность 
оказывать услуги гибочных работ по металлу, а также пробивные работы листового металлопроката. """]]
meh_pr = ['Участок механической обработки', ["""Имеет возможность обрабатывать изделия из
 нержавеющих, черных сталей, титана. Используем токарные станки, сверлильно-расточные аппараты, фрезерные станки. 
"""]]
sb_pr = ['Слесарно-каркасный сборочно-сварочный цех ', ["""Выполняет вальцовку деталей, нарезание резьбы в отверстиях,
 разметку, рубку, рихтовку, сверление, полировку и сборку металлоконструкций. Производит сварочные работы : 
 газовая сварка и резка металла, различные режимы полуавтоматической сварки, различные режимы аргонодуговой 
 сварки вольфрамовым электродами, включая пульсирующий режим, точечная сварка"""]]
mal_pr = ['Цех покрытий и финишной обработки', ["""Производит работы по пескоструйной обработке металла, покрасочные
 работы. Выполняется покраска серийной продукции и мелких партий 
 металлоконструкций. Покрасочное производство ориентировано на большое количество различных мелких деталей, 
 работы по металлу выполняются с помощью ручных распылителей с электростатических эффектом. Применяется для 
 быстрой окраски больших плоских поверхностей"""]]

divisions = [['Отдел комплектации', ["""Контролирует условия хранения оборудования, упаковывание продукции и 
комплектующих изделий, правильность их консервации и обеспечение сохранности. Организует ведение учёта наличия и 
движения оборудования и комплектующих изделий, ответственные при передаче продукции на склад. """, ]],
             ['Технологический отдел производства', ["""Разрабатывает технологические нормативы, инструкции, 
             схемы сборки, маршрутные карты, карты технического уровня и качества продукции и другую 
             технологическую документацию, вносит изменения в техническую документацию в связи с корректировкой 
             технологических процессов и режимов производства""", ]],
             ['Планово-диспетчерский отдел', ["""Контроль выполнения графика выпуска продукции цехом и прохождения 
             ДСЕ в цикле производства, ведение производственного плана на предприятие и предоставление отчётности по
              эффективности его выполнения. """, ]],
             ['Производственные цеха', ["""Основное производственное подразделение предприятия, участвует в общем
              процессе производства, выполняют определенные функции по изготовлению продукции по маршрутной карте 
              проекта. """, ]],
             ['Отдел механика', ["""Основная задача отдела является организация бесперебойной и технически правильной 
             эксплуатации и надежной работы тепло-энергического оборудования, содержание его в работоспособном 
             состоянии и на требуемом уровне точности""", ]],
             ['Главный сварщик', ["""Руководит технологической подготовкой выполнения сварочных работ, обеспечивает 
             изготовление и выпуск высококачественной продукции, совершенствование конструкций изделий, их 
             технологичность, экологичность, высокую производительность труда.""", ]], ]

leaderships = [['Антон Беляков', 'Обращаться по вопросам организации системы управления производства '],            #8
               ['', ''],                                                                                            #9
               ['', ''],                                                                                            #10
               ['Максим Моренко', 'Обращаться по вопросам сроков изготовления продукции, планов работ'],            #12
               ['Виктор Егоров', 'Обращаться по вопросам ремонта и технического обслуживания оборудования'],        #13
               ['Александр Серегин', 'Обращаться по вопросам выполнения производственных заданий и планов'],]      #14

dict_info_ind = {'title': 'Производство Powerz', """o_nas""": ["""Энергия сильных людей - энергия лучших идей
""", ''],
                 'opportunity': [[zag_pr[0], zag_pr[1]],
                                 [meh_pr[0], meh_pr[1]],
                                 [sb_pr[0], sb_pr[1]],
                                 [mal_pr[0], mal_pr[1]], ],
                 'documents': {'title': """ Целью 
                 политики в области качества является разработка, 
                 выпуск и реализация конкурентоспособной продукции в установленные сроки, в заданных объемах, с уровнем 
                 качества, удовлетворяющим требованиям и ожиданиям наших потребителей и других заинтересованных сторон,
                  обеспечение устойчивого экономического положения организации, здоровья и безопасности персонала""",
                               "body": [
                                        """В своей работе мы руководствуемся –  законодательством РФ, а также 
                 собственной совестью. Неотъемлемой частью нашей работы является качество и сроки продукции.""","""Важно 
                 следовать документам, стандартам предприятия. """,]},
                 'fun_msg': ["""Пылесос был изобретен случайно. Один инженер заметил, что его новейший отпугиватель 
                 котов еще и неплохо втягивает пыль.""", 'Народное'],
                 'media': ['Медиа', 'о нас','https://novgorod-tv.ru/news/novgorodskaya-kompaniya-pauerz-prodolzhaet-narashhivat-zarubezhnye-rynki-sbyta-nevziraya-na-sankczii/',
                           "https://novgorod-tv.ru/novosti/58018-novgorodskoe-predpriyatie-kelast-planiruet-zapustit-novyj-tsekh.html"]}

dict_info_elem = {'title': 'План работ'}
r"""Sub ads()
          Set wb = Application.ActiveWorkbook
          Call FF.vigruzit_v_txt("C:\Python\Flusk_test2\templates\", "table.txt", "Çàäà÷è (4).xlsx", "Ëèñò1", 1, 10, "|")
End Sub
"""
def load_pr_proj():
    return  F.open_file_c(r'O:\Журналы и графики\Ведомости для передачи\table_pr_proj.txt',False,"|")

def clear_py(py):
    old_fr = r"Отдел технолога\В работе\Заказы для собственных нужд"
    py = py.replace(old_fr, '')
    py = py.replace('\\', '')
    return  py


def calc_changes_plans():

    path = r'O:\Журналы и графики\Ведомости для передачи\Даты плана'
    list_files = F.list_of_files_c(path)[0][2]
    list_dates_files = [['dates']]
    for file in list_files:
        list_dates_files.append([F.throw_out_extention_c(file)])
        pass
    list_dates_files = F.sort_by_column_c(list_dates_files, 'dates', date_time=True, date_format="%d.%m.%Y")
    dict_projects = dict()

    for name in list_dates_files:
        # print(f'{name[0]}.txt')
        list_proj = F.open_file_c(path + F.sep() + f'{name[0]}.txt', separ="|")
        list_proj = F.list_of_lists_to_list_of_dicts(list_proj)
        for row in list_proj:
            if 'Дата_н' not in row:
                break
            np = row['№ проекта']
            py = row['номер ПУ']
            nppy = np + "$" + py
            if nppy not in dict_projects:
                dict_projects[nppy] = {'Вид': row['Вид'], 'На дату': dict()}
            if name[0] not in dict_projects[nppy]['На дату']:
                dict_projects[nppy]['На дату'][name[0]] = dict()
                dict_projects[nppy]['На дату'][name[0]]['Дата_н'] = row['Дата_н']
                dict_projects[nppy]['На дату'][name[0]]['Дата_к'] = row['Дата_к']
    return dict_projects


def load_projects(poki=None):
    # dict_mk = CSQ.custom_request_c(
    #     r"SRV:Naryad.db\\Naryad.db",
    #     f"""SELECT Пномер, Номенклатура, Номер_заказа || "$" || Номер_проекта FROM mk WHERE Статус != 'НаУдаление'""",
    #     rez_dict=True)
    def check_late_dates(tbl):
        nk_end = F.num_col_by_name_in_hat_c(tbl,'Текущая плановая дата зав. упаковки')
        for i in range(len(tbl)):
            for j in range(len(tbl[i])):
                if F.is_date(tbl[i][j],"%Y-%m-%d"):
                    tbl[i][j] = F.datetostr(F.strtodate(tbl[i][j],"%Y-%m-%d"),"%d.%m.%Y")
            if F.is_date(tbl[i][nk_end],"%d.%m.%Y"):
                if F.strtodate(tbl[i][nk_end],"%d.%m.%Y") < F.now(""):
                    tbl[i][nk_end] = "'" + tbl[i][nk_end]
        return tbl

    def add_line(tbl,row):
        napr = row['alias']
        def first_date(list_dates):
            min_date = None
            for item in list_dates:
                tmp_date = item.split("/")[0]
                if F.is_date(tmp_date,"%Y-%m-%d"):
                    if min_date == None or F.strtodate(tmp_date,"%Y-%m-%d") < F.strtodate(min_date,"%Y-%m-%d"):
                        min_date = tmp_date
            if min_date != None:
                min_date = F.add_days(F.strtodate(min_date,"%Y-%m-%d"),datetime.timedelta(days=-25),True)
                min_date = F.datetostr(min_date,"%d.%m.%Y")
            else:
                min_date = ''
            return min_date

        list_etaps_dates = [row['Резка'],
                            row['Мех_обработка'],
                            row['Сборка+сварка'],
                            row['Упаковка'],]
        poz_name = row['Позиция']
        count = str(row['Количество'])
        if row['Кд'] != '' or row['Статус']=='Резерв':
            min_date = ''
        else:
            min_date = first_date(list_etaps_dates)
            if min_date != '':
                days_delta = (F.strtodate(min_date,"%d.%m.%Y") - F.now('')).days
                if days_delta <0:
                    min_date = f"'{min_date}"
                if 5> days_delta >0:
                    min_date = f"`{min_date}"
        py = clear_py(row['Номер заявки'])
        prpy = row['Номер проекта'] + "$" + row['Номер заявки']
        primech = row['Примечание_сб']
        prognoz_date = row['Прогноз_дата_зав_сб']

        date_sb = row['Сборка+сварка'].split('/')[1]
        date_upak = row['Упаковка'].split('/')[1]
        date_rezka_start = row['Резка'].split('/')[0]
        if prognoz_date != '' and F.is_date(prognoz_date,"%Y-%m-%d") and F.is_date(date_upak,"%Y-%m-%d") and F.is_date(date_sb,"%Y-%m-%d"):
            delta = F.delta_days(F.strtodate(date_sb),F.strtodate(date_upak),True)
            date_sb = F.datetostr(F.strtodate(prognoz_date),"%d.%m.%Y")
            date_upak = F.datetostr(F.add_days(F.strtodate(date_upak) , delta,True),"%d.%m.%Y")

        # mk_list = []
        mk_is = '' if row['Маршрутки'] == 0 else 'Да'
        # for item in dict_mk:
        #     # if item['Номер_заказа || "$" || Номер_проекта'] == row['Номер заявки'] + '$' + row['Номер проекта']:
        #     if item['Пномер'] == row['Маршрутки']:
        #         mk_list.append(item['Номенклатура'].replace(';','; '))
        #         break
        # if len(mk_list) > 0:
        #     mk_is = 'Да'

        date_contract = row['Дата_отгрузки_ПУ']
        date_add_kpl = row['Дата_внесения']

        otkl_dog = 0
        if date_contract != '' and row['Упаковка'].split('/')[1] != '':
            otkl_dog = (F.strtodate(row['Упаковка'].split('/')[1],) - F.strtodate(date_contract,)).days
        otkl_dog = str(otkl_dog)
        pdo_prim = row['Примечание_ПДО']
        pdo_zayav = row["ПДО_Заявки_на_закуп"]
        tbl.append([napr,                                  #0      'Направление'
                    row['Псевдоним'],                      #1      'Псевдоним'
                    row['Номер проекта'],                  #2      Номер проекта
                    py,                                    #3      Номер заявки
                    poz_name,                             #4       Поз.
                    count,                                #5       Кол-во
                    str(row['Нормо-час сб']),              #6      Нормо-час сб
                    row['Статус'],                        #7       'Статус'
                    date_add_kpl,                             #8      Дата внесения в МЕС
                    min_date,                               #9       Требуемая дата КД
                    row['Кд'],                           #10      Ф.Дата получения КД
                    mk_is,#first_date,                    #11      Тех. МК
                    date_rezka_start,                      #12     Плановая дата начала загот. участка
                    date_sb,                              #13      Текущая плановая дата зав. сборки
                    date_upak,                            #14      Текущая плановая дата зав. упаковки
                    date_contract,                        #15      Дата по договору
                    prognoz_date,                         #16      Прогноз дата зав.сб.
                    otkl_dog,                             #17      Откл. от дог.
                    primech,                              #18      Примечание сб. участок
                    pdo_prim,                             #19      ПДО Примечание
                    pdo_zayav])                            #20     ПДО Заявки на закуп

    postfix = ''
    postfix_2 = ''
    if not poki == None:
        postfix = f"AND plan.poki = {poki}"
        postfix_2 = f"and poki = {poki}"

    #list_table = F.open_file_c(r'O:\Журналы и графики\Ведомости для передачи\Sroki_etapov.txt', False, "|")
    #list_table = F.list_to_dict(list_table)
    custom_request_c = f"""SELECT 
            пл_оуп.№проекта AS "Номер проекта", 
            пл_оуп.№ERP AS "Номер заявки", 
            plan.Позиция AS "Позиция", 
            plan.Примечание as 'Примечание_ПДО',
            пл_осил.Примечание as "ПДО_Заявки_на_закуп",
            plan.Дата_внесения as "Дата_внесения",
            пл_оуп.Количество AS "Количество", 
            napravlenie.name AS "Направление", 
            napravlenie.alias AS "alias", 
            status_poz.Имя AS "Статус", 
            plan.Фдата_получения_КД AS "Кд", 
            пл_сб.Нчас_сб AS "Нормо-час сб", 
            plan.МК AS "Маршрутки", 
            пл_заг.ПДата_нач_заг || "/" || пл_заг.ПДата_зав_заг AS "Резка", 
            пл_мех.Пдата_нач_мехобр  || "/" || пл_мех.Пдата_зав_мехобр AS "Мех_обработка", 
            пл_сб.Пдата_нач_сб  || "/" || пл_сб.Пдата_зав_сб  AS "Сборка+сварка", 
            "/" AS "Зачистка", 
            пл_покр.Пдата_нач_покр    || "/" || пл_покр.Пдата_зав_покр  AS "Покрытие", 
            пл_компл.ПДата_нач_комплект_упаковки   || "/" || пл_компл.ПДата_зав_комплект_упаковки  AS "Упаковка", 
            plan.Пдата_нач_вспом   || "/" || plan.Пдата_зав_вспом  AS "Всп", 
            "`" AS "Сумм_н`Сумм_к",
             пл_оуп.Дата_отгрузки_ПУ AS "Дата_отгрузки_ПУ",
             пл_сб.Примечание_сб,
             пл_сб.Прогноз_дата_зав_сб,
             napravl_deyat.Псевдоним 
             FROM plan 
            LEFT JOIN napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности  
            LEFT JOIN napravlenie ON napravlenie.Пномер = napravl_deyat.Направление
            LEFT JOIN status_poz ON status_poz.Пномер = plan.Статус 
            LEFT JOIN пл_осил ON пл_осил.НомПл = plan.Пномер 
            LEFT JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер 
            LEFT JOIN пл_мех ON пл_мех.НомПл = plan.Пномер 
            LEFT JOIN пл_сб ON пл_сб.НомПл = plan.Пномер 
            LEFT JOIN пл_компл ON пл_компл.НомПл = plan.Пномер 
            LEFT JOIN пл_заг ON пл_заг.НомПл = plan.Пномер 
            LEFT JOIN пл_покр ON пл_покр.НомПл = plan.Пномер 
            WHERE status_poz.Имя NOT IN ("Завершена","На удаление") {postfix}; 
            """
    list_table = CSQ.custom_request_c(r"SRV:DB_kplan.db\\DB_kplan.db",custom_request_c,rez_dict=True)

    #====================================changes


    dict_first_day_py = dict() #calc_changes_plans()

    # ================================

    hat_c = ['Направление',                                  #0
             'Псевдоним',                                    #1
             'Номер проекта',                                #2
             'Номер заявки',                                 #3
             'Поз.',                                        #4
             'Кол-во',                                      #5
             'Нормо-час сб',                                 #6
             'Статус',                                      #7
             'Дата внесения в МЕС',                          #8
             'Требуемая дата КД',                           #9
             'Ф.Дата получения КД',                         #10
             'Тех. МК',                                     #11
             'Плановая дата начала загот. участка',          #12
             'Текущая плановая дата зав. сборки',           #13
             'Текущая плановая дата зав. упаковки',         #14
             'Дата по договору',                            #15
             'Прогноз дата зав.сб.',                        #16
             'Откл. от дог.',                               #17
             'Примечание сб. участок',                      #18
             'ПДО Примечание',                              #19
             'ПДО Заявки на закуп']                         #20

    custom_request_c = f'''SELECT * FROM napravlenie WHERE val > 0 {postfix_2}'''
    list_d_napr = CSQ.custom_request_c(r"SRV:DB_kplan.db\\DB_kplan.db", custom_request_c, rez_dict=True)

    dict_napr = {_['alias']:[hat_c].copy() for _ in list_d_napr}

    for i in range(len(list_table)):
        add_line(dict_napr[list_table[i]['alias']], list_table[i])
    for name, napr in dict_napr.items():
        tbl_ = F.sort_by_column_c(napr,'Текущая плановая дата зав. сборки', date_time=True,date_format="%d.%m.%Y")
        tbl_ = check_late_dates(tbl_)
        dict_napr[name]=tbl_
    return dict_napr

def load_change_projects(poki):

    list_table_etap = F.open_file_c(r'O:\Журналы и графики\Ведомости для передачи\Sroki_etapov.txt', False, "|")
    list_table_smena = F.open_file_c(r'O:\Журналы и графики\Ведомости для передачи\Изменение сроков сб.txt', False, "|")
    rez = [["Дата записи","Номер проекта","Номер заявки","Было","Стало","Разница,дней","Примечание",'Вид']]
    for i in range(len(list_table_smena)-1,0,-1):
        item = list_table_smena[i]
        np = item[1]
        py = item[2]

        for etap_row in list_table_etap:
            if etap_row[0] == np and etap_row[1] == py and etap_row[3] in ['к производству','подготовка','резерв','завершен']:
                if item[5] != '-'and item[5] != 'новый':
                    item[2] = clear_py(item[2])
                    item.append(etap_row[2])
                    d1 = F.strtodate(item[3],"%d.%m.%Y")
                    d2 = F.strtodate(item[4], "%d.%m.%Y")
                    item[5] = (d2-d1).days
                    rez.append(item)
                break


    return rez


app = Flask(__name__)


@app.route("/")
@app.route("/index")
def root():
    print(url_for('root'))
    return render_template('index.html', title=dict_info_ind['title'], o_nas=dict_info_ind['o_nas'],
                           opportunity=dict_info_ind['opportunity'], documents=dict_info_ind['documents'],
                           fun_msg=dict_info_ind['fun_msg'], divisions=divisions, media=dict_info_ind['media'],
                           leaderships=leaderships)


@app.route("/elements")
def elements():
    # table_pr_proj = load_pr_proj()
    return render_template(
        'elements.html',
        title=dict_info_elem['title'],
        leaderships=leaderships,
        divisions=divisions,
        list_ways=list_ways,
        INSTRUMENTS_MENU=INSTRUMENTS_MENU
    )

@app.route("/projects")
def projects():
    print(url_for('projects'))




    custom_request_c = f'''SELECT * FROM napravl_deyat'''
    list_d_napr = CSQ.custom_request_c(r"SRV:DB_kplan.db\\DB_kplan.db", custom_request_c, rez_dict=True)
    dict_napr_d = dict()
    for item in list_d_napr:
        clr = f"rgb({item['Цвет'].replace(';',', ')})"
        dict_napr_d[item['Псевдоним']] = clr

    dict_companies = F.deploy_dict_c(CSQ.custom_request_c(r'SRV:Naryad.db\\Naryad.db' ,f'''SELECT Код,
       Имя,
       Примечание,
       Организация_Key,
       poki,
       letter,
       doc_prefix,
       ИспПроверкуВнесенияТрудозатрат,
       ИспПроверкуТехартыВнесениеВидаИВесаТО,
       РодительВидаРабот,
       ИспользоватьФильтрМКПоплану,
       prefix_projects_localnet_path,
       projects_localnet_path,
       УИД_ЕРП_договора_виртуального_поставщика,
       УИД_ЕРП_Отдел_снабжения,
       evaluation_department_podrazdel_for_reports,
       view_on_site
  FROM places
  WHERE view_on_site = 1
''',rez_dict=True), 'poki')
    grafics_pad_mosh = []
    comp_projects = []
    for poki, company in dict_companies.items():
        graf_pad_mosh = GRAF.graf_html(poki)
        graf = generate_html(graf_pad_mosh)
        grafics_pad_mosh.append( {'name': company['Имя'],
            'graf': graf})

        projects = load_projects(poki)
        comp_projects.append(projects)
        #changes = load_change_projects(poki)

    dict_colors_states =F.deploy_dict_c(CSQ.custom_request_c(r"SRV:DB_kplan.db\\DB_kplan.db",f"""SELECT Имя, color FROM status_poz""",rez_dict=True),'Имя')
    for k in dict_colors_states:
        dict_colors_states[k] = f' rgb({dict_colors_states[k].split(";")[0]}, {dict_colors_states[k].split(";")[1]}, {dict_colors_states[k].split(";")[2]})'
    return render_template('projects.html', title=dict_info_elem['title'],
                           comp_projects=comp_projects,
                           changes=[],
                           date_now = F.now("%H:%M %d.%m.%Y"),grafics_pad_mosh = grafics_pad_mosh,dict_colors_states =dict_colors_states,dict_napr_d = dict_napr_d)


@app.route("/projects/<way>", methods = ["POST","GET"])
def way(way):
    print(url_for('way', way =way))
    if request.method == 'POST':
        print(request.form)
    return render_template("way.html", title = way, list_projects = [_ for _ in list_projects if _['way'] == way])


@app.route("/projects/<way>/<proj>")
def info(way,proj):
    print(url_for('info', way = way, proj = proj))
    return f'Проект инфо {way}, {proj}'


@app.route("/reporting")
def reporting():
    print(url_for('reporting'))
    print(get_pictures_type(is_html=False))
    return render_template('reporting.html', title='Отчетность', report_cards=get_pictures_type(is_html=False))

@app.route("/report/<int:page_id>")
def report_page(page_id):
    pictures_di = get_pictures_type(is_html=True)
    return render_template(f'temp_html/{pictures_di[page_id]}')


@app.route('/download/projects/xlsx/')
def download_list_projects():
    from project_writer import ProjectWriter
    projects = load_projects()
    pw_obj = ProjectWriter(data=projects)
    filename = pw_obj.build()
    if not filename or not os.path.exists(filename):
        print('[/download/projects/xlsx/]Некорректный путь файла')
        return redirect(url_for('projects'))
    return send_file(filename, download_name='projects.xlsx')

@app.route("/remark_journal", methods = ["POST","GET"])
def remark_journal():
    print(url_for('remark_journal'))
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        stop_date = request.form.get('stop_date')
        check_start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        check_stop = datetime.datetime.strptime(stop_date, '%Y-%m-%d')
        if check_start > check_stop:
            return render_template('remark_journal.html', title='Журнал замечаний', is_error=True)
        if not stop_date or not start_date:
            return render_template('remark_journal.html', title='Журнал замечаний', is_error=True)
        rmk = Remark(start=start_date, stop=stop_date)
        div_labels, div_values = rmk.get_result_labels_values()
        vp_labels, vp_values = rmk.get_result_labels_values(is_kod_vp=True)
        kod_labels, kod_values = rmk.get_result_labels_values(is_kod_zamech=True)
        full_remarks = rmk.get_result_labels_values(is_full=True)
        return render_template('remark_journal.html', title='Журнал замечаний', div_labels=div_labels, div_values=div_values, vp_labels=vp_labels, vp_values=vp_values, kod_labels=kod_labels, kod_values=kod_values, full_remark=full_remarks)
    else:
        return render_template('remark_journal.html', title='Журнал замечаний')

@app.route('/table_reports', methods = ["POST","GET"])
def table_reports():
    print(url_for('table_reports'))
    header = 'Табличные отчеты'
    all_reports = [
        'Исполнение плана месяца'
    ]  # list(settings.dict_sort_c_report_c.keys())
    # all_depatments ={}# {name:key for key, name  in DEPATMENTS}
    # depatments_li = list(all_depatments.keys())
    dir_z = r'Z:\Data\viewer'
    dict_files = {_.replace('isp_month_','').replace('.pickle','') :[dir_z + F.sep() + _, dir_z + F.sep() + 'tbl_color_' +_, ] for _ in F.list_of_files_c(dir_z)[0][2] if ('isp_month' in _ and '.pickle' in _ and 'tbl_color' not in _)}
    all_month = list(dict_files.keys())
    if request.method == 'POST':
        report = request.form.get('reports')
        selected_month = request.form.get('sel_month')


        if not selected_month or selected_month == '' or not report or report == '':  # not stop_date or not start_date or not
            return render_template('tables_.html', title=header, is_error=True, all_reports=all_reports,all_month=all_month)
        file = dict_files[selected_month][0]
        _, filename = os.path.split(file)
        filename = filename.replace('.pickle', '.xlsx')
        file_data = F.load_file_pickle(file)
        for i in range(len(file_data)):
            for k,v in file_data[i].items():
                file_data[i][k] = str(v)

        table = F.list_of_dicts_to_list_of_lists(file_data)
        tbl_color = F.load_file_pickle(dict_files[selected_month][1])
        return render_template('tables_.html', all_reports=all_reports, table=table, all_month=all_month,tbl_color=tbl_color, filename=filename)
    else:
        return render_template('tables_.html', title=header, all_reports=all_reports, all_month=all_month)


@app.route('/download_report', methods = ["POST"])
def download_report():
    filename = request.form.get('filename')
    return send_file(
        os.path.normpath(f'Z:/Data/viewer/{filename}'),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")



if __name__ == "__main__":
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    if app.config['TEMPLATES_AUTO_RELOAD']:
        p = Thread(target=start_daemon_thread, args=(settings.TIME_CHECK_HTML,), daemon=True)
        p.start()
    if socket.gethostname() == "POW-ING23":
        app.run(debug=True, host='192.168.47.61', port=20000)  # g.sviridov
    else:
        if socket.gethostname() == "POW18-15":
            app.run(debug=False, host='192.168.18.91', port=20001)#a.belyakov
        else:
            # app.run(debug=False, host='192.168.47.123', port=20000)
            # app.run(debug=False,host='192.168.50.230',port=20000)
            app.run(debug=False, host='0.0.0.0', port=20000)  # SRVmes 'http://mesinfo.powerz.ru:20000/'
            print('mesinfo.powerz.ru')

