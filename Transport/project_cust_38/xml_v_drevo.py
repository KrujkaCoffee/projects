import copy
import pprint

import lxml2dict as L
from lxml import etree
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT

def spisok_iz_xml(putt=None,str_f = None):
    
    SET_NECESSARY_FIELDS = {
    'Обозначение полное',
      'Наименование',
       'Тип',
    }
    
    def count_val(val_str:str):
        try:
            return int(val_str)
        except:
            CQT.msgbox(
                f"Ошибка в \nНаименование: {tmp[i]['data']['Наименование']}\n"
                f"Обозначение полное: {tmp[i]['data']['Обозначение полное']}\n количество не может быть дробным\nКоличество: `{tmp[i]['data']['Количество']}`")
            return
        
    def check_row(row):
        for field in SET_NECESSARY_FIELDS:
            if field not in row:
                CQT.msgbox(
                    f"Ошибка в \n{row}\n"
                    f"отсутствует обязательное поле\n `{field}`")
                return False
        return True
    
    if putt:
        rr = etree.parse(putt).getroot()
    else:
        rr = etree.fromstring(str_f)
    tree = L.convert(rr)

    tmp = list_tree(tree)
    s = []
    msg_err = []
    if tmp == None:
        return
    for i in range(len(tmp)):
        if tmp[i] == None:
            return
        tmp[i]['data']['ID'] += "_" + str(i)
        tmp[i]['ID'] += "_" + str(i)

        if i > 0 and tmp[i]['data']['Обозначение полное'] != 'D' and i< len(tmp)-1:
            ur = tmp[i]['level_c']
            
            summ_count = count_val(tmp[i]['data']['Количество']) 
            if summ_count == None:
                return 
            
            for j in range(i+1,len(tmp)):
                if tmp[j]['level_c'] != ur:
                    break
                if not check_row(tmp[i]['data']):
                    return 
                if tmp[i]['data']['Обозначение полное'] == tmp[j]['data']['Обозначение полное'] and\
                        tmp[i]['data']['Наименование'] == tmp[j]['data']['Наименование'] and\
                        tmp[i]['data']['Тип'] == tmp[j]['data']['Тип']:
                    
                    curr_count = count_val(tmp[i]['data']['Количество'])
                    if curr_count == None:
                        return
                    
                    summ_count += curr_count
                    msg_err.append(f"Объединено {tmp[i]['data']['Обозначение полное']} {tmp[i]['data']['Наименование']}"
                                   f" {int(tmp[j]['data']['Количество'])} шт. + {int(tmp[i]['data']['Количество'])} шт."
                               f"на уровне {ur}")
                    tmp[j]['data']['Обозначение полное'] = 'D'
            tmp[i]['data']['Количество'] = summ_count

    ur = 0
    flag = False
    for i in range(len(tmp)):
        if flag == True and tmp[i]['level_c'] <= ur:
            flag = False
        if flag == False:
            if tmp[i]['data']['Обозначение полное'] == 'D':
                flag = True
                ur = tmp[i]['level_c']
            else:
                s.append(tmp[i])
    if len(msg_err) > 0:
        CQT.msgbox(pprint.pformat(msg_err))
    return s
#doc = etree.parse('P:\\Python\\Mkarti\\КТ.1408182.11 (меньше метизов).xml')

def base_sp_names(tree):
    s = []
    sp = tree['Root']['Elements']['Element']['Parameters']['Parameter']
    for i in range(0, len(sp)):
        s.append(sp[i]['@Name'])
    return s

def base_ob(tree,name):
    sp = tree['Root']['Elements']['Element']['Parameters']['Parameter']
    for i in range(0, len(sp)):
        if sp[i]['@Name'] == name:
            otv = sp[i]['@Value']
            return otv
    return None



def sp_imen_child_poputi(putt):
    s=[]
    for i in range(0, len(putt['Children']['Element'])):
        s.append(putt['Children']['Element'][i]['@ObjectId'])
    return s

def spis_child(tree,obj):
    s = []
    if obj == '':
        if type(tree['Root']['Elements']['Element']) == type([]):
            for i in range(0, len(tree['Root']['Elements']['Element'])):
                s.append(tree['Root']['Elements']['Element'][i]['@ObjectId'])
        else:
            s.append(tree['Root']['Elements']['Element']['@ObjectId'])
        return s
    if obj == spis_child(tree,"")[0]:
        return sp_imen_child_poputi(tree['Root']['Elements']['Element'])

    putt = tree['Root']['Elements']['Element']
    putt = naity_put_obj(putt,obj)
    if putt == None:
        return None
    return sp_imen_child_poputi(putt)

def naity_put_obj(putt,obj):
    if putt.get('Children') != None:
        for i in range(0, len(putt['Children']['Element'])):
            #s.append(putt['Children']['Element'][i]['@ObjectId'])
            if putt['Children']['Element'][i]['@ObjectId'] == obj:
                return putt['Children']['Element'][i]
            else:
                naity_put_obj(putt['Children']['Element'][i], obj)
    return None

def znach_param(putt,param):
    for i in range(0, len(putt)):
        if putt[i]['@Name'] == param:
            return putt[i]['@Value']

def oform_strok(putt, ur,type_item=''):
    dict_obj = dict()
    for item in (putt['Parameters']['Parameter']):
        dict_obj[item['@Name']] = item['@Value']
    if type_item:
        dict_obj['Тип'] = type_item
    dict_obj['ID'] = putt['@ObjectId']

    return {'ID':putt['@ObjectId'], 'data':dict_obj, "level_c":ur}

    p1 = znach_param(putt['Parameters']['Parameter'], 'Наименование')
    p2 = znach_param(putt['Parameters']['Parameter'], 'Обозначение полное')
    p3 = znach_param(putt['Parameters']['Parameter'], 'Количество')
    p4 = znach_param(putt['Parameters']['Parameter'], 'Материал')
    p5 = znach_param(putt['Parameters']['Parameter'], 'Материал2')
    p6 = znach_param(putt['Parameters']['Parameter'], 'Материал3')
    p7 = znach_param(putt['Parameters']['Parameter'], 'Количество на изделие')
    p8 = znach_param(putt['Parameters']['Parameter'], 'Масса')
    p9 = znach_param(putt['Parameters']['Parameter'], 'Покупное изделие')
    p10 = znach_param(putt['Parameters']['Parameter'], 'Единица измерения')
    p11 = znach_param(putt['Parameters']['Parameter'], 'Ссылка на объект DOCs')
    p12 = znach_param(putt['Parameters']['Parameter'], 'Примечание')
    p13 = znach_param(putt['Parameters']['Parameter'], 'Классификатор изделия')
    p14 = znach_param(putt['Parameters']['Parameter'], 'Код ERP')

    p15 = znach_param(putt['Parameters']['Parameter'], 'Position')
    p16 = znach_param(putt['Parameters']['Parameter'], 'IncludeInDoc')
    p17 = znach_param(putt['Parameters']['Parameter'], 'IncludeInAssembly')
    p18 = znach_param(putt['Parameters']['Parameter'], 'Сводное наименование')
    p19 = znach_param(putt['Parameters']['Parameter'], 'Раздел')
    p20 = znach_param(putt['Parameters']['Parameter'], 'Обозначение')
    p21 = znach_param(putt['Parameters']['Parameter'], 'Изделие')
    p22 = znach_param(putt['Parameters']['Parameter'], 'Код документа')
    p23 = znach_param(putt['Parameters']['Parameter'], 'Тип')

    if dict_obj['Покупное изделие'] == '1':
        if dict_obj['Обозначение полное'].strip() == '':
            dict_obj['Обозначение полное'] = F.shifr(dict_obj['Наименование'])[:13]
    else:
        if dict_obj['Обозначение полное'].strip() == '':
            CQT.msgbox(f"Ошибка {dict_obj['Наименование']} {dict_obj['Обозначение полное']} не имеет Обозначение/не покупная")
            return
    if dict_obj['Классификатор изделия'] == None:
        dict_obj['Классификатор изделия'] = ''
    if dict_obj['Код ERP'] == None:
        dict_obj['Код ERP'] = ''

    mat = "/".join((str(dict_obj['Масса']).replace(',','.'), F.clear_row_for_file_name_c(str(dict_obj['Материал'])),
                    F.clear_row_for_file_name_c(str(dict_obj['Материал2'])),
            F.clear_row_for_file_name_c(str(dict_obj['Материал3']))))


    return [F.clear_row_for_file_name_c(dict_obj['Наименование']),
            F.clear_row_for_file_name_c(dict_obj['Обозначение полное']),
            dict_obj['Количество'],
            dict_obj['Единица измерения'],
            mat, dict_obj['Ссылка на объект DOCs'], dict_obj['ID'],
            dict_obj['Количество на изделие'], dict_obj['Примечание'], dict_obj['Покупное изделие'],
            dict_obj['Классификатор изделия'], dict_obj['Код ERP'],
            dict_obj['Position'], dict_obj['IncludeInDoc'], dict_obj['IncludeInAssembly'], dict_obj['Сводное наименование'],
                            dict_obj['Раздел'], dict_obj['Тип'], dict_obj['Изделие'], dict_obj['Код документа'], ur]

def naidi_child(putt,s,ur):
    if putt.get('Children') != None and  '@ObjectId' not in putt['Children']['Element']:
        ur+=1
        for i in range(0, len(putt['Children']['Element'])):
            s.append(oform_strok(putt['Children']['Element'][i],ur))
            s = naidi_child(putt['Children']['Element'][i], s, ur)
    if putt.get('Children') != None and  '@ObjectId' in putt['Children']['Element']:
        ur+=1
        s.append(oform_strok(putt['Children']['Element'],ur))
        s = naidi_child(putt['Children']['Element'], s, ur)
    return s

def naidi_child_cad(item,s,ur):
    ur += 1
    if type(item) != list:
        item = [item]
    for i in range(0, len(item)):
        
        if type(item[i]['Items']['Element']) != list:
            elem = [item[i]['Items']['Element']]
        else:
            elem = item[i]['Items']['Element']
        type_item = item[i]['@Name']
        for el in elem:
            s.append(oform_strok(el, ur,type_item))
            if 'Groups' in el:
                s = naidi_child_cad(el['Groups']['Groups'], s, ur)
    return s


def tree_from_docs(tree):
    ur = 0
    s = []
    try:
        if type(tree['Root']['Elements']['Element']) == type([]):
            for i in range(0, len(tree['Root']['Elements']['Element'])):
                s.append(oform_strok(tree['Root']['Elements']['Element'][i], ur))
                s = naidi_child(tree['Root']['Elements']['Element'][i], s, ur)
        else:
            s.append(oform_strok(tree['Root']['Elements']['Element'], ur))
            s = naidi_child(tree['Root']['Elements']['Element'], s, ur)
        return s
    except:
        CQT.msgbox('Структура не корректная')
        return
    
def tree_from_cad(tree):
    ur = -1
    s = []
    try:
        s = naidi_child_cad(tree['Root']['Groups']['Groups'], s, ur)
        return s
    except:
        CQT.msgbox('Структура не корректная')
        return
    
def list_tree(tree):
    if 'Root' not in tree:
        CQT.msgbox(f'В структре отсутсвет корневой уровень, структура не корректна')
        return 
    if 'Elements' in tree['Root']:
        return tree_from_docs(tree)
    if 'Groups' in tree['Root']:
        return tree_from_cad(tree)
    
#puttt = 'O:\\Производство Powerz\\Диспетчерское бюро\\xml\\КТ.1210127.28 ИЗД 01_11_2021 011144.xml'

#s = spisok_iz_xml(puttt)
#a=a
#s = list_tree(tree)
#for i in s:
#    pr = ''
#    for j in range(0,6):
#        pr +=  i[j] +"|"
#    print("    " * i[20]+ pr + ' - ' + str(i[20]))


