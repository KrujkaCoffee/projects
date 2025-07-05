from __future__ import annotations

import datetime
import pprint

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Cust_Functions as F
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from TehKart import mywindow

#set_words = F.open_file_c('russian.txt',True)
#F.save_file_pickle('summary.pickle',set(set_words))



DICT_II_FIELDS = {'Номер_ко' :'Номер п/п',
'Номер_проекта' :'Номер проекта',
'ДСЕ' :'Номер документа',
'Наименование_документа' :'Наименование документа',
'Содержимое' :'Содержание изменения',
'Номер_извещения':'Номер Извещения',
'Дата_ко' :'Дата Извещения',
'Разработчик_ко' :'Разработчик КД',
'Причина' :'Причина изменения',
'Примечание':'Обоснование изменения'
}

DICT_KRO_FIELDS = {'Номер_ко' :'№',
#'КРО №' :'Номер проекта',
#'ДСЕ' :'Номер документа',
#'Наименование_документа' :'Наименование документа',
#'Содержимое' :'Содержание изменения',
'Наименование_документа' :'КРО №',
'Дата_ко' :'Дата утверждения КРО',
'Разработчик_ко' :'Автор',
'Причина' :'Примечание',
}
DICT_II_FIELDS3 = {'№':'Номер_ко',
#'КРО №' :'Номер проекта',
#'ДСЕ' :'Номер документа',
#'Наименование_документа' :'Наименование документа',
#'Содержимое' :'Содержание изменения',
'КРО №':'Наименование_документа' ,
'Дата утверждения КРО':'Дата_ко' ,
'Автор':'Разработчик_ко' ,
'Примечание':'Причина' ,
}

def apply_row(self:mywindow):
    def check_permission(korr_res):
        if korr_res != '':
            if not CMS.user_access(self.db_naryad,'тк_ии_корр_рес',F.user_name()):
                return False
        return True

    def check_fill(val:str):
        if val == '':
            return True
        list_words = val.split(' ')
        for word in list_words:
            if word.lower() not in self.SET_RUS_WORDS:
                CQT.msgbox(f'{word} не слово')
                return False
        return True

    row = self.ui.tbl_ii.currentRow()
    if row == -1:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_ii,'Пномер')
    nom = int(self.ui.tbl_ii.item(row,nk_pnom).text())
    zadel = self.ui.le_zadel.text().strip()
    sz_proizv = self.ui.le_sz_proizv.text().strip()
    korr_tk = self.ui.le_korr_tk.text().strip()
    korr_mk = self.ui.le_korr_mk.text().strip()
    korr_res = self.ui.le_korr_res.text().strip()
    korr_raskr = self.ui.le_korr_raskr.text().strip()
    dop_mk = self.ui.le_dop_mk_nom.text().strip()
    podtv = self.ui.le_podtv.text().strip()
    now = F.now()
    user = F.user_full_namre()

    if not check_permission(korr_res):
        return

    dict_vals = {"Задел":zadel,
"Задел_дата":now,
"Задел_ФИО":user,
"СЗ_производство":sz_proizv,
"СЗ_производство_дата":now,
"СЗ_производство_ФИО":user,
"Корр_ТК":korr_tk,
"Корр_ТК_дата":now,
"Корр_ТК_ФИО":user,
"Корр_МК":korr_mk,
"Корр_МК_дата":now,
"Корр_МК_ФИО":user,
"Корр_ресурсная":korr_res,
"Корр_ресурсная_дата":now,
"Корр_ресурсная_ФИО":user,
"Корр_раскрой":korr_raskr,
"Корр_раскрой_дата":now,
"Корр_раскрой_ФИО":user,
"Доп_МК_номер":dop_mk,
"Доп_МК_номер_дата":now,
"Доп_МК_номер_ФИО":user,
"Подтверждение_проводки":podtv,
"Подтверждение_проводки_дата":now,
"Подтверждение_проводки_ФИО":user,
}
    for key in dict_vals:
        if '_дата' in key or '_ФИО' in key:
            pass
        else:
            if not check_fill(dict_vals[key]):
                CQT.msgbox(f'Не корректные данные {key}')
                return
            if key == 'Подтверждение_проводки' and dict_vals[key] != '':
                flag='True'
                for key in dict_vals:
                    if '_дата' in key or '_ФИО' in key:
                        pass
                    else:
                        nk_ = CQT.num_col_by_name_c(self.ui.tbl_ii,key)
                        if nk_ == None or self.ui.tbl_ii.item(row,nk_).text() == '':
                            flag = key
                            break
                if flag != 'True':
                    CQT.msgbox(f'Подтвердить проводку невозможно без отметки {flag}')
                    return
    tmp = []
    for key in dict_vals:
        if '_дата' in key or '_ФИО' in key:
            pass
        else:
            if dict_vals[key] != '':
                tmp.append({key: dict_vals[key],f'{key}_дата': dict_vals[f'{key}_дата'], f'{key}_ФИО': dict_vals[f'{key}_ФИО'],'Пномер':nom})
    if len(tmp) == 0:
        return
    if CQT.msgboxgYN(f'Будут внесены данные: {pprint.pformat(tmp)}'):
        for key in dict_vals:
            if '_дата' in key or '_ФИО' in key:
                pass
            else:
                if dict_vals[key] != '':
                    list_of_lists_c = [[dict_vals[key], dict_vals[f'{key}_дата'],
                                dict_vals[f'{key}_ФИО'], nom]]
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE izv_izm_rkd SET ({key}, {key}_дата, {key}_ФИО) = (?,?,?) WHERE Пномер = ?""",list_of_lists_c=list_of_lists_c)
        fill_table(self,False)
        CQT.msgbox(f'Успешно')

def load_ii():
    ko_ii = (r'O:\Журналы и графики\Журнал конструкторских замечаний\ОБЩИЙ Журнал конструкторских изменений  2023.xlsx',
                  r'O:\Журналы и графики\Журнал конструкторских замечаний\ОБЩИЙ Журнал конструкторских изменений 2024.xlsx')
    def change_fields(list_napr:list,name:str):
        FIELDS = [
                'Направление',
                'Номер_проекта',
                'Номер_ко',
                'ДСЕ',
                'Наименование_документа',
                'Содержимое',
                'Номер_извещения',
                'Дата_ко',
                'Разработчик_ко',
                'Причина',
                'Примечание',
                'Дата_получения_ии',
                'Год'
                ]

        for j in range(len(list_napr[0])):
            for key in DICT_KRO_FIELDS:
                if list_napr[0][j] == DICT_KRO_FIELDS[key]:
                    list_napr[0][j] = key
                    break
        list_napr = F.list_of_lists_to_list_of_dicts(list_napr)
        if list_napr == []:
            return []
        rez = []
        for i in range(len(list_napr)):
            if list_napr[i]['Наименование_документа'] == None:
                continue
            list_napr[i]['Дата_получения_ии'] = F.now('%Y-%m-%d')
            list_napr[i]['Направление'] = name
            if F.is_date(list_napr[i]['Дата_ко'],"%d.%m.%Y"):
                year = F.strtodate(list_napr[i]['Дата_ко'],"%d.%m.%Y").year
            else:
                try:
                    year = list_napr[i]['Дата запуска КРО'].year
                except:
                    year = 2000
            list_napr[i]['Год'] = year
            if year <2024:
                continue
        #for field in FIELDS:
        #    if field not in list_napr[0]:
        #        CQT.msgbox(f'Не найдено поле {field} в журнале изменений {name}')
        #        return []

            item = list_napr[i]
            tmp = dict()
            for field in FIELDS:
                if field in item:
                    if item[field] == None:
                        tmp[field] = ''
                    else:
                        tmp[field] = item[field]
                else:
                    tmp[field] = ''
            rez.append(tmp)
        return  rez

    def change_fields_ii(list_napr:list,name:str,year:int):

        for j in range(len(list_napr[0])):
            if list_napr[0][j] == None:
                continue
            for key in DICT_II_FIELDS:
                if list_napr[0][j] == DICT_II_FIELDS[key]:
                    list_napr[0][j] = key
                    break
        list_napr = F.list_of_lists_to_list_of_dicts(list_napr)
        for i in range(len(list_napr)):
            list_napr[i]['Дата_получения_ии'] = F.now('%Y-%m-%d')
            list_napr[i]['Направление'] = name
            list_napr[i]['Год'] = year
            if isinstance(list_napr[i]['Дата_ко'], datetime.datetime):
                list_napr[i]['Дата_ко'] = F.datetostr(list_napr[i]['Дата_ко'])
        if list_napr == []:
            return []
        #for field in FIELDS:
        #    if field not in list_napr[0]:
        #        CQT.msgbox(f'Не найдено поле {field} в журнале изменений {name}')
        #        return []
        rez = []
        for item in list_napr:
            if item['Номер_ко'] == 'Образец':
                continue
            rez.append(item)
        return  rez


    names = ['КЛ','КТ','ШГ','АО','ТППР','ЛК']
    rez = []
    napr = CEX.read_file(r'O:\Журналы и графики\КРО\Журнал учета КРО форма ПЗ-СТО-12 Ф-04.xlsx', 'Лист1', r1=299)
    napr_fix = change_fields(napr, '-')
    for item in napr_fix:
        rez.append(item)


    for jur in ko_ii:
        year =  int(F.throw_out_extention_c(jur).split(' ')[-1])

        for name in names:
            napr = CEX.read_file(jur,name,r1=2,c2=10)
            napr_fix = change_fields_ii(napr,name,year)
            for item in napr_fix:
                rez.append(item)
    return rez

if __name__ == "__main__":
    pass
    #load_ii()
def update_db(self):
    list_ii = load_ii()
    list_db = CSQ.custom_request_c(self.db_dse, f"""SELECT * FROM izv_izm_rkd""",rez_dict=True)
    diff = []
    for item in list_ii:
        fl_naid = False
        for item_db in list_db:
            if item == None or 'Наименование_документа' not in item:
                continue
            if item['Наименование_документа'] == item_db['Наименование_документа'] and \
                str(item['Номер_ко']) == str(item_db['Номер_ко']) and \
                item['Год'] == item_db['Год']:
                fl_naid = True
                break
        if not fl_naid:
            diff.append(item)
    if len(diff) == 0:
        return
    diff_list= F.list_of_dicts_to_list_of_lists(diff)
    CSQ.custom_request_c(self.db_dse,f"""INSERT INTO izv_izm_rkd (Направление, Номер_проекта, Номер_ко, ДСЕ, 
    Наименование_документа,Содержимое,Номер_извещения,Дата_ко,Разработчик_ко,Причина,Примечание,Дата_получения_ии,Год)
                              VALUES ({','.join(['?' for _ in diff_list[0]])})""",list_of_lists_c=diff_list[1:])


def fill_table(self:mywindow,update = True):
    if update:
        update_db(self)
    list_ii = CSQ.custom_request_c(self.db_dse,f"""SELECT * FROM izv_izm_rkd""")
    CQT.fill_wtabl(list_ii,self.ui.tbl_ii,ogr_maxshir_kol=600,min_width_col=15,height_row=20)
    CMS.fill_filtr_c(self,self.ui.tbl_ii_filtr,self.ui.tbl_ii)
    CMS.update_width_filtr(self.ui.tbl_ii,self.ui.tbl_ii_filtr)

def check_neobr_ii(self:mywindow):
    rez = CSQ.custom_request_c(self.db_dse,f"""SELECT Пномер, Подтверждение_проводки_ФИО FROM izv_izm_rkd WHERE Подтверждение_проводки_ФИО == ''""")
    if rez == False:
        return True
    if rez == None:
        return True
    if len(rez)>1:
        return len(rez)
    return True
