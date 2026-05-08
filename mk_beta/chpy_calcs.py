# -*- coding: utf-8 -*-
import copy
import pprint
import os

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS

@CQT.onerror
def check_full_raskroy(self):
    list_auts = []
    csv_lsit = generate_precsv_tree(self, write=False)
    if csv_lsit == None:
        return
    if len(csv_lsit) == 0:
        return list_auts
    dict_for_check_from_csv = {F.throw_out_extention_c(_[1]):0 for _ in csv_lsit}
    list_unnecessary_dse_aut = []

    dir_xml = self.glob_pre_csv_file_path
    fiels_in_dir = F.list_of_files_c(dir_xml)[0]
    list_files = []
    for file_name in fiels_in_dir[2]:
        if len(file_name) > 8 and file_name[-8:] == '_AUT.txt':
            list_files.append(fiels_in_dir[0] + F.sep() + file_name)
    for file_path_name in list_files:
        aut = aut_rasclad_into_dict(self, file_path_name)
        if len(aut) == 0:
            continue
        for dse in aut['num']:
            name_dse = F.throw_out_extention_c(aut['num'][dse]['Part file name'])
            if name_dse not in dict_for_check_from_csv:
                list_unnecessary_dse_aut.append(aut['num'][dse]['Part file name'])
            else:
                dict_for_check_from_csv[name_dse]+=1
            list_auts.append(aut)

    if [_ for _ in dict_for_check_from_csv.keys() if dict_for_check_from_csv[_] == 0] != []:
        CQT.msgbox(f'Не найдены раскрои под резку {pprint.pformat(dict_for_check_from_csv)}')
        return
    if list_unnecessary_dse_aut != []:
        CQT.msgbox(f'В раскрои заложены лишние детали {pprint.pformat(list_unnecessary_dse_aut)}')
        return
    return list_auts

@CQT.onerror
def aut_rasclad_into_dict(self, path: str) -> dict:
    try:
        file = F.open_file_c(path, )
        file = [_.replace('\t', '').strip() for _ in file]
        rez_dict = {'hat': dict(),
                    'num': dict(),
                    'rem': dict()
                    }

        file_list = []

        for line in file:

            if ':' not in line:
                continue
            line_list = line.split(':', 1)
            var = line_list[0].strip()
            val = line_list[1].strip()
            if F.is_numeric(val):
                val = F.valm(val)
            if F.is_date(val, '%H:%M:%S'):
                val = F.strtodate(val, '%H:%M:%S')
            file_list.append([var, val])

        count_dse = 0
        count_rem = 0
        start_dse = 0
        start_rem = 0
        stop_dse = len(file_list) - 1

        for i, line in enumerate(file_list):
            var = line[0]
            if var == 'Num':
                if start_dse == 0:
                    start_dse = i
                count_dse += 1
            if var == 'ID':
                if stop_dse == len(file_list) - 1:
                    stop_dse = i - 1
                    start_rem = i
                count_rem += 1

        for dse_pnom in range(count_dse):
            name_dse = file_list[start_dse + dse_pnom][1]
            rez_dict['num'][name_dse] = dict()
            for i in range(start_dse, stop_dse, count_dse):
                rez_dict['num'][name_dse][file_list[i + dse_pnom][0]] = file_list[i + dse_pnom][1]

        for rem_pnom in range(count_rem):
            name_rem = file_list[start_rem + rem_pnom][1]
            rez_dict['rem'][name_rem] = dict()
            for i in range(start_rem, len(file_list), count_rem):
                rez_dict['rem'][name_rem][file_list[i + rem_pnom][0]] = file_list[i + rem_pnom][1]

        fl_status = 'hat'
        for line in file_list:
            var = line[0]
            val = line[1]
            if var == 'Num':
                break
            rez_dict[fl_status][var] = val

        # calc time================
        for dse in rez_dict['num']:
            hours = rez_dict['num'][dse]['P_TOTAL_CUT_MACHINE_TIME'].hour
            minutes = rez_dict['num'][dse]['P_TOTAL_CUT_MACHINE_TIME'].minute
            secs = rez_dict['num'][dse]['P_TOTAL_CUT_MACHINE_TIME'].second
            count_dse = rez_dict['num'][dse]['Qty']
            rez_dict['num'][dse]['TOTAL_CUT_MACHINE_TIME_MINUTES'] = round((hours * 60 + minutes + secs / 60), 1)

        # calc weith dse with remnant================
        nedel_othod = rez_dict['hat']['Total parts weight (KG)'] * 1.26 - rez_dict['hat']['Total parts weight (KG)']
        for dse in rez_dict['num']:
            dolya_dse = rez_dict['num'][dse]['Weight']  / rez_dict['hat']['Total parts weight (KG)']
            udel_weight_rem = dolya_dse * nedel_othod
            weight_with_rem = rez_dict['num'][dse]['Weight'] + udel_weight_rem
            rez_dict['num'][dse]['weight_with_rem'] = round(weight_with_rem,4)


        #for remnant in rez_dict['rem']:
        #    weight = rez_dict['rem'][remnant]['X'] * rez_dict['rem'][remnant]['Y'] * \
        #             rez_dict['rem'][remnant]['Thickness'] * 7.8 / 1000000
        #    rez_dict['rem'][remnant]['Weight'] = weight

        return rez_dict
    except:
        return dict()


@CQT.onerror
def generate_precsv_tree(self,p=None,write = True, *args,**kwargs):
    def segm_count(item:dict) -> int:
        prim = item['Примечание']
        kolvo_seg = 1
        err_arr = []
        flag_naid = False
        for slovo in set_segment:
            if slovo.lower() in prim.lower():
                flag_naid = True
                break
        if flag_naid == True:
            list_words = prim.split(' ')
            flag_naid_int = False
            for word in list_words:
                if F.is_numeric(word):
                    kolvo_seg = int(word)
                    flag_naid_int = True
                    break
            if flag_naid_int == False:
                err_arr.append(f'Число сегментов не распознано на {item["Обозначение полное"] + "_" + item["Наименование"]} принят 1')
            else:
                kolvo_seg = int(kolvo_seg)
        return kolvo_seg

    if 'xml_name' not in self.__dict__ or self.xml_name == None:
        CQT.msgbox(f'не загружена структура')
        return
    path_dir_xml = CMS.load_tmp_path("tmp_putt")

    dict_tree =F.list_of_lists_to_list_of_dicts(CQT.list_from_tree_c(self.ui.tree_base_tree,True))
    set_segment = {"част", "сегм", "сект"}
    list_csv = dict()
    list_err = []
    for item in dict_tree:
        cleaned_code_erp = item['Код ERP'].strip()
        if cleaned_code_erp == '':
            continue
        if cleaned_code_erp not in self.DICT_NOMEN:
            list_err.append(f"Ошибка. {item['Обозначение полное']} код {item['Код ERP']} отсутствует в номенклатуре")
            continue

        if self.DICT_NOMEN[cleaned_code_erp]['П5'] != '1':
            if 'лист' in  self.DICT_NOMEN[cleaned_code_erp]['Наименование'].lower():
                list_err.append(f'{item["Обозначение полное"]}, код:{cleaned_code_erp} -в номенклатуре МЕС материал не имеет параметр (П5 = 1) обратиться к Администратору материалов.')
            continue

        kod_mat = str(self.DICT_NOMEN[cleaned_code_erp]['П6'])
        tolsh = str(self.DICT_NOMEN[cleaned_code_erp]['П1'])
        if kod_mat == '':
            list_err.append(f'Не найден матерал для резки (П5, П6, П1) на'
                           f' {item["Обозначение полное"]}')


        name_file_obozn = item["Обозначение полное"] + '.dxf'
        name_file_nn_obozn = item["Обозначение полное"]+ " " + item["Наименование"] + '.dxf'
        full_path_name = path_dir_xml+ os.sep + name_file_obozn
        full_path_name_nn =path_dir_xml+ os.sep + name_file_nn_obozn
        if F.existence_file_c(full_path_name_nn):
            if name_file_nn_obozn not in list_csv:
                list_csv[name_file_nn_obozn] = {
                    'full_path_name_nn':full_path_name_nn,
                    'name_file_nn_obozn':name_file_nn_obozn,
                    'Количество':int(item["Количество на изделие"])*segm_count(item),
                    'kod_mat':kod_mat,
                    'tolsh':tolsh,
                    'xml_name':self.xml_name}
            #else:
            #    list_csv[name_file_nn_obozn]['Количество'] += int(item["Количество на изделие"])*segm_count(item)
            continue
        if F.existence_file_c(full_path_name):
            if name_file_obozn not in list_csv:
                list_csv[name_file_obozn] = {
                    'full_path_name_nn':full_path_name,
                     'name_file_nn_obozn':name_file_obozn,
                     'Количество':int(item["Количество на изделие"]) * segm_count(item),
                     'kod_mat':kod_mat,
                     'tolsh':tolsh,
                     'xml_name':self.xml_name}
            #else:
            #    list_csv[name_file_obozn]['Количество'] += int(item["Количество на изделие"]) * segm_count(item)
            continue
        list_err.append(f'Ошибка. отсутствуют файлы {full_path_name}')

    list_csv = F.list_of_dicts_to_list_of_lists(list(list_csv.values()))[1:]
    if len(list_err) > 0:
        list_err.insert(0,f'Список ошибок')
        CQT.msgboxg_get_table_ok_inf(self,'Обнаружены ошибки',list_err)
        return
    if not list_csv:
        CQT.msgbox(f'Список под выгрузку пуст.')
        return
    #if len(list_csv) == 0:
    #    CQT.msgbox(f'Выгрузка пустая.')
    #    return
    self.glob_pre_csv_file_path = path_dir_xml
    if write:
        F.write_file_c(self.glob_pre_csv_file_path+ F.sep() + self.xml_name + '.csv', list_csv, separ=';')
        F.open_dir_c(path_dir_xml)
    else:
        return list_csv




"""
Machine: CUMAQ_HANDYCUT_PL--- название станка
		Order: AutoNest 2.DSP --- 	название задания		            
		Subnest name: AutoNest 2---13--- номер программы
		Order date: Thursday, December 28, 2023, 12:56:38 ---дата создания программы		  
		Sheets Qnt:	1 --- количиство повторений программы
		
Material: 09Г2С ---- материал листа или отхода		
Thickness: 6 --- толщина листа или отхода
Remnant Material:09Г2С    
Thickness:6.00         
Inventory ID: 0- по умолчанию это номер целого листа, если программа из отхода, то тут будет номер присвоенный из родителя

Size (мм): 3000 x 1500  --- габариты листа / отхода  
Subnest num: 13 --- номер программы в задании
Time per nest: 00:45:08 -- время резки с перемещением головы на данную программу     
	Efficiency: 58.42 % --- процент заполненности листа деталями
Num of parts: 34 --- общее количество деталей в программе					 
	Total parts weight (KG): 72.365 --- общий вес деталей с припуском 
Sheet weight (KG): 211.95 -- вес листа/отхода			 
	Skeleton weight (KG): 139.585 вес скелета 
Sheet Area  : 4.5 -- площадь листа  			     
	Left over: 41.579 -- не знаю
OLD_ID:  -- не знаю

Parts in Subnest: детали входящие в программу

	Num: 8 --- присвоенный номер к детали в Металиксе                                                 
	Part file name:КЛ.2108001.17.11.001 Сектор фланца.dft --- шифр детали
	Project:КЛ.2108001.17 25_12_2023 040817 --- к какому проекту относится деталь
	Weight:2.128 --- масса детали с припуском
	Size X:742.5 --- габариты детали по Х  
	Size Y:194.8 --- габариты детали по У    
	Work Order:- --- не знаю          
	Qty :34 количество этих деталей в программе       
	Gross:2.128 --- масса детали с припуском         
	P_TOTAL_CUT_MACHINE_TIME:00:01:17  --- время резки одной детали               
	File patch:O:\Производство Powerz\Отдел технолога\В работе\2021\2108001\КЛ\КЛ.2108001.17.11.001 Сектор фланца.dft --- путь к файлу

Remnant Table: --таблица остатка

	ID:71707 ---номер отхода который создаётся, присваивается Металиксом
	Type:Shaped Remnant---Тип: Фасонный остаток
	Remnant Material:09Г2С --- материал остатка  
	Thickness:6.00 --- толщина остатка         
	X:1500.00 --- габарит остатка по Х
	Y:1483.08 --- габарит остатка по У
сдесть отход будет лестницей,подсчёт массы по этим габаритам не подходит
"""
