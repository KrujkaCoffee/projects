from __future__ import annotations


import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vipoln import mywindow



@CQT.onerror
def check_otk_after_proizv(self:mywindow,nom_mk:int,rc_proizv:str ='',kod_oper:set =''):
    list_nar = CSQ.custom_request_c(self.db_naryd,f"""SELECT * FROM naryad WHERE naryad.Номер_мк == {nom_mk};""",rez_dict=True)

    res = CMS.load_res(nom_mk)

    def get_list_opers_proizv_otk(self,res,rc_proizv):
        rez = []
        for dse in res:
            kolvo = dse['Количество']
            if len(dse['Операции']) <=1:
                continue
            for i,oper in enumerate(dse['Операции']):
                if i == 0:
                    continue
                pev_oper = dse["Операции"][i-1]
                tmp_dict = {'dse_id':dse['Номерпп'],
                                'dse_name': f"{dse['Наименование']} {dse['Номенклатурный_номер']}" ,
                                'count_dse':kolvo,
                                'close_dse':0,
                                'nom_op':oper['Опер_номер'],
                                'name_op': oper['Опер_наименование']
                                }
                if kod_oper:
                    if oper['Опер_РЦ_код'][:3] == '060' and pev_oper['Опер_код'] in kod_oper:
                        rez.append(tmp_dict)
                else:
                    if oper['Опер_РЦ_код'][:3] == '060' and pev_oper['Опер_РЦ_код'][:4] == rc_proizv:
                        rez.append(tmp_dict)
        return rez

    list_opers_otk = get_list_opers_proizv_otk(self,res,rc_proizv)
    for item in list_nar:
        nar = CMS.Naryads(item)
        for elem in nar.params:
            for i, line in enumerate(list_opers_otk):
                if elem['ДСЕ_ID'] == line['dse_id'] and elem['Операции_номер'] == line['nom_op']:
                    list_opers_otk[i]['close_dse'] += elem['Опер_колво']

    list_untapped_opers =[]
    for item in list_opers_otk:
        if item['count_dse'] > item['close_dse']:
            list_untapped_opers.append(f"{item['dse_name']} {item['count_dse']-item['close_dse']} из шт."
                                       f" {item['count_dse']}, операция {item['nom_op']} {item['name_op']}")
    if len(list_untapped_opers)>0:
        return '\n'.join([_ for _ in list_untapped_opers])
    return False



