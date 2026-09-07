import os
from difflib import get_close_matches
from urllib.parse import quote, unquote

import requests
import xml.etree.ElementTree as ET
import project_cust_38.Cust_Functions as F
import pickle


import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import operacii

import os
import shutil

import patoolib  # pip install patool
from PyQt5.QtWidgets import QApplication, QFormLayout, QDialog, QLabel, QVBoxLayout, QPushButton, QLineEdit
from PyQt5 import QtCore


import requests
import re

from requests_toolbelt.multipart import decoder
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS



tmp_dir = 'temp_dir'  # временная папка для сохранения файлов
min_similarity = 0.82   # минимальная похожесть при подборе материала если меньше то он не будет подобран
search_erp_for_it = ['Материал']  # если есть это поле то ищем код ERP


docs_mes_params_convert = {
    'материал': 'Материал(1-черн,2-нерж):int',
    'толщина': 'Толщина,мм:int',
    'периметр': 'Периметр, мм:int',
    'площадь_поверхности,м2': 'Площадь поверхности,м2:int',
    'диаметр':  'Диаметр,мм:int',
    'диаметр_отверстий': 'Диаметр отверстий:str',
    'число_гибов': 'Число гибов:int',
    'длина': 'Длина,мм:int',    
    'длина_швов':  'Длина швов(мм):int',
    'Длина_заготовки_детали,мм': 'длина заготовки детали, мм:int',
    'ширина': 'Ширина,мм:int',
    'ширина_фланцев': 'Ширина фланцев:int',
    'количество': 'Кол-во штук:int',
    'количество_деталей': 'Количество деталей:int',
    'количество_сварных_узлов': 'Количество сварных узлов:int',
    'количество_точек_крепления': 'Количество точек крепления:int',
    'кол-во_штук': 'Кол-во штук:int',
    'масса':  'Масса,кг:int',
    'глубина_сверления': 'Глубина сверления:str',
    'колво_входящих_дсе':  'Кол-во входящих ДСЕ:int',
    'число_мест_защ': 'число мест защ.:int',
    'сложность(1-да,0-нет)': 'Сложность(1-да,0-нет):str',
    'вид_изделия': 'Вид изделия:str',
    'оборудование': 'Оборудование:str',
    'виды_швов': 'Виды швов:str',
    'число_шпилек/створок': 'Число шпилек/створок:int',
    'пол_закрыт(1-да,0-нет)': 'Пол закрыт(1-да,0-нет):int',
    'вид_дсе': 'Вид ДСЕ:str',
    'число_резов': 'Число резов:int',
    'модуль_зуба': 'Модуль зуба:str',
    'высота_профиля': 'Выс.профиля:int',
    'вид_конструкции': 'Вид конструкции:int',
    'условия(1-удобные,2-неудобные)': 'Условия(1-удобные 2-неудобные):int',
    'длинна_стыков':  'Длинна стыков(мм):int',
    'длинна_обечайки' : 'Длинна обечайки(мм):int',
    'длинна_реза': 'Длинна реза,мм:int',
    'коэфф_сложности': 'Коэфф сложности:int',
    'коэфф_сложности_значения': 'Коэфф сложности значения:int',
    'изделие': 'Изделие:int',
    'число_сегментов': 'Число сегментов:int',
    'вид_поверхности': 'Вид поверхности:str',
    'коэфф_сборки': 'Коэфф сборки:int',
    'коэффициент_сложности': 'Коэфф сложности значения:int',
    'кол-во_отверстий': 'Кол-во_отверстий',
    'тип_отверстий(глухое-1,нет-0)': 'Тип отв.(глухое(1)нет(0)):str',
    'зачистка_в_труднодоступных_местах(1-да,2-нет)': 'Зачистка в труднодоступных местах(1-да 2-нет):int',
    'зачистка_заподлицо(1-да,2-нет)': 'Зачистка заподлицо(1-да 2-нет):int',
    'маршрут': 'Маршрут:str',
    'фаска_паз(1-фаска,2-паз)': '1-фаска, 2-паз:int',
    'вид_транспорта': 'Вид транспорта:str',
    'длинномерность': 'Длинномерность:int',
    'угол_поворота(0-90град,1-180град)': 'угол поворота(0-90град,1-180град):int',
    'давление': 'Давление:int',
    'плоскость_поворота(0-горзонт,1-веритикаль)': 'плоскость поворота(0-горзонт,1-веритикаль):int',
    'толщина_металла':  'Толщина металла(мм):int',
    'число_сегментов':  'Число сегментов:int',
    'ширина_фланцев':  'Ширина фланцев:int',
    'площадь_поверхности': 'Площадь поверхности,м2:int',
    'длина_швов': 'Длина швов,мм:int;',
    'тип_сортамента':  'Tип_сортамента',
    'вид_сварки(20-п,21-а)': 'Вид сварки(20-П,21-А)',
    'тип_поверхности(1плоская)': 'Тип поверхности(1плоская 2 криволинейная):int',
}

not_corrosion = ["08Х18Н10Т", "12Х18Н9Т", "08Х18Н10", "12Х18Н10Т", "04Х18Н10", "08Х17", "08Х13", "20Х13", "30Х13", "40Х13", "15Х25Т", "15Х28", "20Х25Н20С2", "12Х17", "08Х17Т", "08Х17А", "08Х17Т-Ш", "08Х17А-Ш", "08Х17Т-ВД", "08Х17А-ВД", "08Х17М2", "08Х17М3", "08Х17М3-Ш", "08Х17М3-ВД", "08Х17Т-У", "08Х17А-У", "08Х17М2-У", "08Х17М3-У", "08Х17М3-У-Ш", "08Х17М3-У-ВД", "08Х17М2-У-Ш", "08Х17М2-У-Ш", "08Х17М3-У-SH", "08Х17М3-У-SH", "08Х17М3-У-VD", 'X2CrNi12', 'X2CrNi19-11', 'X2CrNiMo17-12-2', 'X2CrNiMoN17-12-2', 'X2CrTiN18', 'X3CrNiCuNbN20-8', 'X3CrNiMoNbN20-8', 'X3CrNiMoNbN20-8']
not_corrosion = [i.lower() for i in not_corrosion]


def clean_dir(zip_name=None, unzip_dir=None):
    if unzip_dir and os.path.exists(unzip_dir):
        shutil.rmtree(unzip_dir)
    if zip_name and os.path.exists(zip_name):
        os.remove(zip_name)


def befor_preparation_params(operation_name):
    if operation_name in ['Упаковывание']:
        return "Масса_изделия,кг;Направление,кг"


def material_preparater(arr, operation_name):
    headers = arr[0]
    values = arr[1]
    for index, val in enumerate(headers):
        if val == 'Материал(1-черн,2-нерж):int':
            if operation_name in ['Сборка под сварку']:  # список где заменяем из за того что при подстановке данных техкарты работают по 2 системам ввода даннх из базы и из файла и ключи-названия разные
                arr[0][index] = 'Материал'
            # print(values[index])
            cur_val = arr[1][index]
            if cur_val.lower() in not_corrosion:
                arr[1][index] = '2'
            else:
                arr[1][index] = '1'
    return arr


def conditions_preparater(arr, operation_name):
    headers = arr[0]
    for index, val in enumerate(headers):
        if val == 'Условия(1-удобные 2-неудобные):int':
            if operation_name in ['Сборка под сварку']:  # список где заменяем из за того что при подстановке данных техкарты работают по 2 системам ввода даннх из базы и из файла и ключи-названия разные
                arr[0][index] = 'Условия'
    return arr

def lenth_preparater(arr, operation_name):
    headers = arr[0]
    for index, val in enumerate(headers):
        if val == 'Длинна стыков(мм):int':
            if operation_name in ['Сборка под сварку']:  # список где заменяем из за того что при подстановке данных техкарты работают по 2 системам ввода даннх из базы и из файла и ключи-названия разные
                arr[0][index] = 'Длина (метр) стыков'
    return arr




def thickness_preparater(arr, operation_name):
    headers = arr[0]
    for index, val in enumerate(headers):
        if val == 'Толщина металла(мм):int':
            if operation_name in ['Сборка под сварку']:  # список где заменяем из за того что при подстановке данных техкарты работают по 2 системам ввода даннх из базы и из файла и ключи-названия разные
                arr[0][index] = 'Толщина металла'
    return arr


    
def val_replacer(arr, replacer):
    new_arr = [[0 for _ in range(len(arr[0]))],[0 for _ in range(len(arr[1]))]]
    for cur_index, new_index in enumerate(replacer):
        new_arr[0][new_index] = arr[0][cur_index]
        new_arr[1][new_index] = arr[1][cur_index]
    return new_arr



def shell_length_preparater(arr, operation_name):
    headers = arr[0]
    for index, val in enumerate(headers):
        if val == 'Длинна обечайки(мм):int':
            if operation_name in ['Сборка под сварку']:  # список где заменяем из за того что при подстановке данных техкарты работают по 2 системам ввода даннх из базы и из файла и ключи-названия разные
                arr[0][index] = 'Длина обечайки'
    return arr

def k_complexity_preparater(arr, operation_name):
    headers = arr[0]
    for index, val in enumerate(headers):
        if val == 'Коэфф сложности:int':
            if operation_name in ['Сборка под сварку']:  # список где заменяем из за того что при подстановке данных техкарты работают по 2 системам ввода даннх из базы и из файла и ключи-названия разные
                arr[0][index] = 'Коэфф сложности'
    return arr


def k_assemblies_preparater(arr, operation_name):
    headers = arr[0]
    for index, val in enumerate(headers):
        if val == 'Коэфф сборки:int':
            if operation_name in ['Сборка под сварку']:  # список где заменяем из за того что при подстановке данных техкарты работают по 2 системам ввода даннх из базы и из файла и ключи-названия разные
                arr[0][index] = 'Коэфф сборки'
    return arr


def convert_docs_to_mes(params):
    new_details = {}
    fake_new_details = {}
    for d_name, d_dict in params.items():
        inner_di = {}
        for k, v in d_dict.items():
            res = docs_mes_params_convert.get(k.lower())
            if res:
                inner_di[res] = v
            else:
                fake_new_details[k] = v
        new_details[d_name] = inner_di
    return new_details, fake_new_details
    


def split_to_params(sub_res):
    params = {}
    fake_params = {}
    for project_param, value in sub_res.items():
        if '__' in project_param:
            project_param = project_param.replace('$', '')
            params[project_param] = value
        else:
            fake_params[project_param] = value
    return params, fake_params


def split_to_details(sub_res):
    # это не результирующая сборка а просто разбиение по деталям
    details = {}
    for project_param, value in sub_res.items():
        project_name, param = project_param.split('__')
        project_name = project_name.replace('_', '.')
        if not details.get(project_name):
            inner_di = {}
            inner_di[param] = value
            details[project_name] = inner_di
        else:
            details[project_name][param] = value

    return details


def get_erp_code(self, material):
    material = material.lower()
    if not getattr(self, 'NOMENGLATURA', None):
        sub_res = CSQ.custom_request_c(F.bdcfg('nomenklatura_erp'),"""SELECT * FROM nomen""",hat_c=False,rez_dict=True)
        self.NOMENGLATURA = F.deploy_dict_c(sub_res, 'Наименование')
        self.nomenglatura = {k.lower().strip():v for k, v in self.NOMENGLATURA.items() if isinstance(k, str)}

    nomenglatura_lower = self.nomenglatura
    nomenglatura_li = list(nomenglatura_lower.keys())
    
    material = get_close_matches(material, nomenglatura_li, cutoff=min_similarity, n=1)
    if material:
        return nomenglatura_lower.get(material[0])['Код'], nomenglatura_lower.get(material[0])
    else:
        return None, None

def check_code_erp(self, param_name):
    finded_code, _ = get_erp_code(self, param_name)
    if finded_code:
        return finded_code
    else:
        is_first = True
        while True:
            dlg = FindErpCode(param_name, is_first)
            dlg.exec()
            is_first = False
            param_name = dlg.get_code()
            if param_name:
                return param_name
                        


class FindErpCode(QDialog):
    def __init__(self, material_for_find, is_first=True, parent=None):
        super().__init__(parent)
        self.setBaseSize(500, 400)
        self.material_for_find = material_for_find if material_for_find else ''
        lt = QVBoxLayout()
        if is_first:
            msg = f'Нет кода ERP для материала "{self.material_for_find}"\nНеобходим поиск'
        else:
            msg = f'код не найден {self.material_for_find}\nеще раз'
        lt.addWidget(QLabel(msg))
        self.line = QLineEdit()
        lt.addWidget(self.line)
        self.find_btn = QPushButton('Искать')
        self.find_btn.clicked.connect(self.find_code)
        lt.addWidget(self.find_btn)

        self.setLayout(lt)
        self.res_code = None

    def find_code(self):
        res_code, _ = get_erp_code(self, self.line.text().strip())
        if res_code and len(res_code) > 2:
            self.res_code = res_code
            self.accept()
        else:
            self.reject()

    def get_code(self):
        return self.res_code


class CheckDialog(QDialog):
    def __init__(self, times, parent=None, is_get_params=False, is_fake_params=False, is_first_elem=False):
        super().__init__(parent)
        form_lt1 = QFormLayout()
        self.setBaseSize(500, 400)
        self.times = times
        if not times:
            no_params_lbl = QLabel('в проекте нет файлов с расширением grb и/или xml')
            lt = QVBoxLayout()
            lt.addWidget(no_params_lbl)

            self.setLayout(lt)
        else:
            if is_get_params:
                self.setWindowTitle("Полученные параметры")
                form_lt1.addRow('Параметр', QLabel('Значение'))
            elif is_fake_params:
                self.setWindowTitle("Неиспользуемые или неправильно переданные параметры")
                form_lt1.addRow('Операция', QLabel('Значение'))
            else:
                self.setWindowTitle("Время получено для операций")
                form_lt1.addRow('Операция', QLabel('Расчетное время\nзатраченное на операцию'))
            
            
            
            for operation, time in times.items():
                if is_first_elem:
                    lbl = QLabel(f'{time[0]}')
                    lbl.setStyleSheet("color: green;" if time[0] else "color: red;")
                    form_lt1.addRow(f'{time[3]}', lbl)
                else:
                    lbl = QLabel(f'{time}')
                    lbl.setStyleSheet("color: green;" if time else "color: red;")
                    form_lt1.addRow(operation, lbl)
            self.setLayout(form_lt1)


def load_project_files(project_number):
    clean_dir(None, tmp_dir)
    status = None
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    url = f'http://srv-docs.powerz.ru:42334/GetFilesFromCards.svc/GetFilesFromCards2?project_number={project_number}'  # рабочий
    # url = f'http://srv-docs-dev.powerz.ru:41324/GetFilesFromCards.svc/GetFilesFromCards2?project_number={project_number}'  # тестовый
    testEnrollResponse = requests.get(url)
    print(f'testEnrollResponse.content {len(testEnrollResponse.content)}  {testEnrollResponse.text}')
    if testEnrollResponse.status_code != 200 or len(testEnrollResponse.content) == 2:
        CQT.msgbox(f'Не корректно указан номер изделия-{project_number}\n в DOCs нет такого номера')
        return
    print(testEnrollResponse)
    try:
        multipart_data = decoder.MultipartDecoder.from_response(testEnrollResponse)
    except decoder.NonMultipartContentTypeException:
        CQT.msgbox(f'ошибка получения от Docs- не предоставлены файлы')
        return
    
    for part in multipart_data.parts:
        for i in part.headers.values():
            pattern = re.compile(r'filename\*=.*')
            res = re.findall(pattern, str(i))
            if res:
                res = res[0]
                res = res[22:-1]
                status = True
                with open(os.path.join(tmp_dir, res), 'wb') as file:
                    file.write(part.content)
    return status


class GetParams:
    def __init__(self, output_self):
        self.tmp_dir = tmp_dir
        self.data_file = 'SearchFilterText'
        self.output_self = output_self

    def get_files(self):
        grb = []
        xml = []
        for _, _, files in os.walk(tmp_dir):
            for file in files:
                if file.endswith('.grb'):
                    grb.append(file)
                elif file.endswith('.xml'):
                    self.output_self.xml_file = os.path.join(tmp_dir, file)
                    xml.append(file)
        return grb, xml

    # def get_detail_name(self, val):
    #     detail_name = f'{unquote(val)}'
    #     pattern = re.compile(r'\S*\.\d*')
    #     res = re.search(pattern, detail_name).group(0)

    #     return res


    def get_GRB(self, filname):
        
        soruce_file = os.path.join(tmp_dir, filname)
        zip_file = os.path.join(tmp_dir, f'{filname[:-3]}zip')
        unzip_dir = os.path.join(tmp_dir, f'{filname[:-3]}_unzip_dir')
        clean_dir(zip_file, unzip_dir)
        shutil.copy(soruce_file, zip_file)
        patoolib.extract_archive(zip_file, outdir=unzip_dir, verbosity=0)
        res = None
        try:
            res = self.get_grb_params(unzip_dir)
        except Exception:
            print('неудачная обработка файла')
        finally:
            # clean_dir(zip_file, unzip_dir) нельзя т.к. еще нужен будет xml
            return res

    # def preparate_grb_params(self, params):


    
    def get_grb_params(self, unzip_dir, detail_name):
        result = {}
        with open(os.path.join(unzip_dir, self.data_file) , 'r', encoding='utf-16') as file:
            res = file.read()
        res = res.replace('\n', '').replace('\t', '')
        res = res.split(';')

        # $КИС_900_01_03_001__Масса;17.454817
        inner_di = {}
        for i in res:
            if '__' in i:
                sub_product = i.split('__')
                product_name = sub_product[0].replace('$', '').replace('_', '.')
                param = sub_product[1]
                value = res.index(i+1)
                if len(product_name) > 2:
                    param = f'{param}__{sub_product[2]}'
                inner_di[param] = value
        if inner_di != {}:
            result[product_name] = inner_di
            return result

    
    
    def get_Xml_by_elements(self, filename):
        tree = ET.parse(os.path.join(tmp_dir, filename))
        root = tree.getroot()
        di = {}
        elements = [full_child for full_child in root.iter('Element')]
        
        for full_child in elements:
            parametrs = {param.attrib.get('Name'): f'{param.attrib.get("Value")}' for param in full_child.iter('Parameter') if param.attrib.get('Value') and param.attrib.get('Name')}
            detail_name, is_main =  (parametrs.get('Обозначение'), True) if parametrs.get('Обозначение') else (parametrs.get('Обозначение полное'), False)
            if is_main:
                parametrs['Главное изделие'] = True
            di[detail_name] = parametrs    
        return di
    

    def get_Xml(self, filename):
        tree = ET.parse(os.path.join(tmp_dir, filename))
        root = tree.getroot()
        di = {}
        for child in root.iter('Parameter'):
            value = child.attrib.get('Value')
            if value:
                key = child.attrib.get('Name')
                if key == 'Сводное наименование':
                    key = 'Основное изделие'
                di[key] = value
        
        return di
    
    def compare_params(self, xml_params, grb_params):
        result_products = {}
        for product_name, product_di in xml_params.items():
            grb_dict = grb_params.get(product_name)
            if grb_dict:
                product_di.update(grb_dict)
            result_products[product_name] = product_di
        return result_products

    

    def run(self):
        res = {}
        grb_li, xml_li = self.get_files()
        for xml in xml_li:  # обязательно первой т.к. здесь берутся все параметры чтобы их перезаписать с grb
            input_xml = self.get_Xml_by_elements(xml)
            if input_xml:
                res.update(input_xml)
            else:
                print(f'неудачная обработка xml {xml}')
                return None

        for grb in grb_li:
            input_grb = self.get_GRB(grb)
            if input_grb:
                res = self.compare_params(input_xml, input_grb)
            else:
                print(f'неудачная обработка grb {grb}')

        if res == {}:
            return None
        else:
            return res  


class PiclerUpdater:
    def __init__(self, f_name, new_params, output_self) -> None:
        self.f_name = os.path.join(F.scfg('pickle'), f'ТДТК.{f_name}_{f_name}.pickle') # Рабочий
        self.new_params = new_params
        self.full_updated_di = {}
        self.output_self = output_self
        self.detail_name = f_name


    def load_pickle(self):
        try:
            with open(self.f_name, 'rb') as file:
                self.res = pickle.load(file)
            return True
        except FileNotFoundError:
            print('файл не найден')
            return None
        

    def get_time(self):
        vrema = 0
        operation_time = {}
        start_with = 11
        res = self.res[start_with:]
        current_operation_di = None

        all_operations_in_pickle = []
        for index, i in enumerate(res):
            operation_di = {}
            column = i.split('|')
            if len(column) < 3:
                continue
            operation_params = column[-7]
            operation_name = column[0]

            if not getattr(self, 'SPIS_OP', None):
                sub_res = CSQ.custom_request_c('SRV:Naryad.db','''SELECT * FROM operacii''',hat_c=False,rez_dict=True)
                self.FULL_OPPEATIONS = F.deploy_dict_c(sub_res, 'name')


            if operation_name not in list(self.FULL_OPPEATIONS.keys()):
                continue
            
            for find_operation, operation in self.FULL_OPPEATIONS.items():
                if find_operation == operation_name:
                    current_operation_di = operation.get('Vars')
                    break
                    

            if not current_operation_di:
                res = befor_preparation_params(operation_name)
                if res:
                    current_operation_di = res
                else:
                    continue

            current_operation_di = current_operation_di.split(';')
            pickled_params = self.get_pickled_params(operation_params, current_operation_di)
            new_params = self.get_new_params(current_operation_di)

            arr_tmp, updated_di = self.match_pickle_params(pickled_params, new_params, current_operation_di)
            
            
            operation_di['updated_di'] = updated_di
            # обработчики для отдельных видов переменных
            arr_tmp = material_preparater(arr_tmp, operation_name)  
            arr_tmp = conditions_preparater(arr_tmp, operation_name) 
            arr_tmp = lenth_preparater(arr_tmp, operation_name) 
            arr_tmp = thickness_preparater(arr_tmp, operation_name) 
            arr_tmp = shell_length_preparater(arr_tmp, operation_name) 
            arr_tmp = k_complexity_preparater(arr_tmp, operation_name) 
            arr_tmp = k_assemblies_preparater(arr_tmp, operation_name)
            # arr_tmp = header_preparater(arr_tmp, operation_name)
            
            send_di = {arr_tmp[0][i].split(':')[0]:arr_tmp[1][i] for i in range(len(arr_tmp[0]))}
            # if operation_name == 'Перемещение':
            #     ...
            try:
                vrema = operacii.vremya_tsht(operation_name, arr_tmp)
                print(f'{operation_name} получилось: время {vrema}')
                if not vrema:
                    vrema = 0
                pz = 0
                if isinstance(vrema, tuple):
                    vrema, pz = vrema
                    operation_di['t_sht'] = vrema
                    operation_di['ttpz'] = pz
                time = (vrema, '$'.join(arr_tmp[1]), send_di, operation_name)
            except:
                time = (0, '$'.join(arr_tmp[1]), send_di, operation_name)
         
            self.set_detail_operation(self.detail_name, operation_name, time, pz, column)
            operation_time[index+start_with] = time #[operation_name] = time
            all_operations_in_pickle.append(operation_di)
        return operation_time
    
    def get_new_params(self, current_operation_di):
        di = {}
        for k in current_operation_di:
            finded_v = self.new_params.get(k)
            if finded_v:
                di[k] = finded_v
        return di


    def get_pickled_params(self, operation_params, current_operation_di):
        di = {}
        values = operation_params.split('$')
        for i, k in enumerate(current_operation_di):
            try:
                di[k] = values[i]
            except IndexError:
                print(values)
                print(di)
        return di



    def add_material_from_grb(self, material_one_operation, operation):
        material = None
        mass = None
        for param_name, param_val in self.new_params.items():
            if 'материал' in param_name:
                material += param_val + " "

            # if '__' in param_val.lower():
            #     par_name, param_operation = param_val.split('__')
            #     if param_operation.lower() == operation.lower():
            #         material = par_name
            #         mass = True
        if mass:
            for param_name, param_val in self.new_params.items():
                if 'масса' in param_name.lower():
                    mass = float(param_val)

        if mass and material:
            material_one_operation.append(self.get_material_per_operation(mass, material))
        return material_one_operation
    
    def get_material_per_operation(self, mass, material):
        material_di = {}
        erp_code, material_data = get_erp_code(self, material)
        material_di['Мат_код'] = erp_code
        material_di['Мат_наименование'] = material
        material_di['Мат_ед_изм'] = material_data['ЕдиницаИзмерения']
        material_di['Мат_норма'] = mass * 1.3
        material_di['Мат_норма_ед'] = 1
        material_di['Мат_параметрика'] = {}
        material_di['Материалы_Статья_калькуляции'] = 'Сырье'
        material_di['Способы_получения_материала'] = 'Обеспечивать'
        return material_di
    
    def set_detail_operation(self, detail, operation, time, pz, column):
        if not self.output_self.result_json[detail].get('Операции'):
            self.output_self.result_json[detail]['Операции'] = []

        if not getattr(self, 'WORK_CENTERS', None):
            SPIS_OP = CSQ.custom_request_c(F.bdcfg('BD_users'),"""SELECT prof.этап, rc.Имя, rc.Код, prof.код, prof.имя, prof.вид_работ, rc.empl_Подразделение, rc.Наим_ЕРП FROM professions prof join rab_mesta rab_m on prof.код=rab_m.Код_профессии join rab_c rc on rc.Код=rab_m.Код_РЦ """,hat_c=False,rez_dict=True)
            # SPIS_OP = CSQ.custom_request_c(F.bdcfg('BD_users'),"""SELECT * FROM professions prof join rab_mesta rab_m on prof.код=rab_m.Код_профессии join rab_c rc on rc.Код=rab_m.Код_РЦ """,hat_c=False,rez_dict=True)
            
            self.WORK_CENTERS = F.deploy_dict_c(SPIS_OP, 'Код') 

            
            test = F.deploy_dict_c(SPIS_OP, 'Код') 
        
        rc = self.FULL_OPPEATIONS[operation]['rc']  # в комплектовочной неправильно подставляетс рабочий центр 020100 а должен быть 020101
        sub_rc = self.WORK_CENTERS.get(rc)


        
        material_one_operation = [] if not column[10] else self.get_material_one_operation(column[10])
        material_one_operation = self.add_material_from_grb(material_one_operation, operation)
    
        one_operation = {
            "Опер_РЦ_наименование": operation,
            "Опер_РЦ_наименовние": operation,  # т.к. без этого поля с ошибкой не проходит т.к. оно обязательно
            "Опер_профессия_наименование": self.WORK_CENTERS[rc]['имя'] if sub_rc else ' ',
            "Опер_наименование_подразделения": self.WORK_CENTERS[rc]['Наим_ЕРП'] if sub_rc else ' ',
            "Опер_вспомогательная": 1 if self.FULL_OPPEATIONS[operation]['Вспомогат']==1  else 0,
            "Опер_наименовние": operation,
            "Этап": self.FULL_OPPEATIONS[operation]['etap'], 
            "Опер_Тпз": pz if pz!=0 else self.FULL_OPPEATIONS[operation]['Tpz'],
            "Опер_Тшт_ед": time[0],
            'Материалы': material_one_operation,
        }
        
        self.output_self.result_json[detail]['Операции'].append(one_operation)

    
    
    def get_one_material(self, str_val):
        res = str_val.split("$")
        material_di = {}
        material_di['Мат_код'] = res[0] if len(res[0])>2 else check_code_erp(self, res[1])
        material_di['Мат_наименование'] = res[1]
        material_di['Мат_ед_изм'] = res[2]
        material_di['Мат_норма'] = res[3]
        material_di['Мат_норма_ед'] = 1
        material_di['Мат_параметрика'] = {}
        material_di['Материалы_Статья_калькуляции'] = 'Сырье'
        material_di['Способы_получения_материала'] = 'Обеспечивать'

        return material_di



    def get_material_one_operation(self, str_val):
        li_materials = str_val.split('{')
        res = []
        for material in li_materials:
            res.append(self.get_one_material(material))         
        return res


        

    def preparate_pickle(self, operation_time):
        save_operations = []
        for index, operation in enumerate(self.res):
            if '|' in operation:
                operation = operation.split('|')
                if operation[0] in operation_time.keys():
                    time = operation_time[index]
                    operation[7] = f'{time[0]}'
                    operation[14] = time[1]
                    operation[16] = time[2] if time[2] else ''

                operation = '|'.join(operation)     
            save_operations.append(operation) 

        return save_operations

    def save_pickle(self, sub_res):
        with open(self.f_name, 'wb') as file:
            pickle.dump(sub_res, file)



    def run(self):
        res = self.load_pickle()
        if res:
            time = self.get_time()
            sub_res = self.preparate_pickle(time)
            self.save_pickle(sub_res)
            return time
        return None
        
    


    def match_pickle_params(self, old, new, operation_params_order):
        # подставлять новые параметры если новых нет то оставлять старые
        for k in old.keys():
            new_val = new.get(k)
            if new_val:
                old[k] = new_val

        params = []
        for param_name in operation_params_order:
            val = old.get(param_name)
            if val:
                params.append(f'{val}')
            else:
                params.append('+')

        res = []
        res.append(operation_params_order)
        res.append(params)
        return res, old






def json_generation(self):
    self.xml_file = None

    def generate2(self, path='', name=''):

        def apply_kotlovoy_method(self):
            recompile_results = []
            index = 0
            for detail_name, params in self.result_json.items():
                if params == {}:
                    continue
                index +=1

                inner_detail_di = {}
                inner_detail_di['Номерпп'] = index
                inner_detail_di['Наименование'] = params.get('Наименование')
                inner_detail_di['Номенклатурный_номер'] = detail_name
                if params.get('Код ERP'):
                    inner_detail_di['Код_ERP'] = params.get('Код ERP') 
                else:
                    erpcode, _ = get_erp_code(self.additional_params.get('Материал'), self.additional_params.get('Материал2'), self.additional_params.get('Материал3'))
                    inner_detail_di['Код_ERP'] = erpcode
                    
                inner_detail_di['Количество'] = 1
                inner_detail_di['Количество_ед'] = 1
                inner_detail_di['Уровень'] = 1 if params.get('Главное изделие') else 0
                inner_detail_di['Операции'] = params.get('Операции') if params.get('Операции') else []
                inner_detail_di['Параметрика'] = {}
                inner_detail_di['Документы'] = []
                inner_detail_di['ПКИ'] = '0'
                inner_detail_di['Мат_кд'] = '0//'
                inner_detail_di['Ссылка'] = params.get('Ссылка на объект DOCs')
                inner_detail_di['Прим'] = ''
                inner_detail_di['Способы_получения_материала'] = "Произвести по основной спецификации"
                inner_detail_di['dreva_kod'] = 1
                
                recompile_results.append(inner_detail_di)

            return recompile_results
         
        put = F.put_po_umolch()
        if F.existence_file_c(CMS.tmp_dir() + F.sep() + 'json_dir_cache.txt'):
            sod_f = F.load_file(CMS.tmp_dir() + F.sep() + 'json_dir_cache.txt')
            if sod_f != []:
                put = sod_f
        dir = CQT.getDirectory(self, put)
        if dir == ['.'] or dir == '.':
            return
        F.save_file(CMS.tmp_dir() + F.sep() + 'json_dir_cache.txt', dir)


        res = apply_kotlovoy_method(self)
        path = dir + F.sep() + "К_" + name

        F.write_json_c(res, path, False)
        CQT.msgbox(f'Готово')
        F.open_dir_c(dir)

    if not self.xml_file:
        xml_name = 'test'
    else:
        _, xml_name = os.path.splitext(self.xml_file)

    generate2(self, path='temp_dir', name=f'{xml_name}_VO_{F.now("%Y%m%d-%H%M%S")}.json')



def clean_project_name(project_name):
    project_name = project_name.split('.')
    project_name = '_'.join(project_name)    
    return project_name


def get_params(self, project_name):
    self.ui.btn_ok.setDisabled(True)
    timer_dlg = TimerDialog(self)
    timer_dlg.show()
    if not load_project_files(project_name.strip()):
        return None
    m = GetParams(self)
    params = m.run()


    if params:
        self.ui.btn_ok.setDisabled(True)
        self.ui.le_nnom_izd.setReadOnly(True)
        self.ui.set_var_btn.setDisabled(False)
    else:
        dlg = CheckDialog(params)
        dlg.exec()
        return
        
    

    dlg = CheckDialog(params, is_get_params=True)
    dlg.exec()
    # params, self.additional_params = split_to_params(params)
    # project_details = split_to_details(params)
    # self.project_details,  fake_new_details = convert_docs_to_mes(project_details)
    self.project_details = params
    # if fake_new_details:
    #     dlg = CheckDialog(fake_new_details, is_fake_params=True)
    #     dlg.exec()
        


def set_params(self, project_name):
    not_found_files = ''

    self.result_json = {}
    is_next = False
    for detail_name, detail_params in self.project_details.items():
        self.result_json[detail_name] = detail_params
        po = PiclerUpdater(detail_name, detail_params, self)
        res = po.run()
            
        if not res:
            not_found_files += project_name + '\n '
        else:
            dlg = CheckDialog(res, is_first_elem=True)
            dlg.exec()
            is_next = True
    if not_found_files != '':
        CQT.msgbox(f"не найдены picke {not_found_files}")
        if not is_next:
            return None
        
    self.ui.get_json_cotl.setEnabled(True)
    self.ui.set_var_btn.setDisabled(True)



def reset_params(self):
    self.ui.btn_ok.setEnabled(True)
    self.ui.le_nnom_izd.setReadOnly(False)
    self.ui.set_var_btn.setDisabled(True)
    self.ui.get_json_cotl.setDisabled(True)



class TimerDialog(QDialog):
    def __init__(self,input_self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Ожидание загрузки')
        self.timer = QtCore.QTimer()
        lt = QVBoxLayout()
        lt.addWidget(QLabel('Загрузка из Docs ожидание 3 сек'))
        self.setLayout(lt)
        QtCore.QTimer.singleShot(3*1000, lambda: input_self.ui.btn_ok.setEnabled(True))

