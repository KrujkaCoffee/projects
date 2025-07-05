from __future__ import annotations

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import pprint
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from TehKart import mywindow

def check_plan_responce_sort_c_weight(self:mywindow):
    def check_respons_techn(self:mywindow):
        query = f"""SELECT plan.Пномер, пл_оуп.№проекта, пл_оуп.№ERP, plan.Позиция, plan.Дата_внесения, пл_топ.Вид, пл_топ.Отв_технолог, пл_топ.Уд_вес_ВО, пл_топ.Нчас_ТД, 
        пл_топ.Число_ДСЕ FROM пл_топ INNER join plan ON plan.Пномер = пл_топ.НомПл , пл_оуп ON пл_оуп.НомПл = пл_топ.НомПл 
        WHERE DATE(plan.Дата_внесения) >= DATE("2023-08-01") and plan.Статус IN (1,2,3,7) and plan.poki = {self.place.poki}"""
        responce = CSQ.custom_request_c(self.db_kplan,query,rez_dict=True)
        pull = []
        for item in responce:
            if item['Отв_технолог'] == '':
                pull.append(item)
        if len(pull) > 0:
            CQT.msgbox(f'не внесены "Отв_технолог"  в план МЕС   для:\n\n{pprint.pformat(pull)}')
            return False
        return True
    def check_respons_sort_c_weight(self:mywindow,name):
        query = f"""SELECT plan.Пномер, пл_оуп.№проекта, пл_оуп.№ERP, plan.Позиция, plan.Дата_внесения, пл_топ.Вид, пл_топ.Отв_технолог, пл_топ.Уд_вес_ВО, пл_топ.Нчас_ТД, 
        пл_топ.Число_ДСЕ FROM пл_топ INNER join plan ON plan.Пномер = пл_топ.НомПл , пл_оуп ON пл_оуп.НомПл = пл_топ.НомПл 
        WHERE DATE(plan.Дата_внесения) >= DATE("2023-08-01") and пл_топ.Отв_технолог = '{name}' and plan.Статус IN (1,2,3,7) and plan.poki = {self.place.poki}"""
        responce = CSQ.custom_request_c(self.db_kplan,query,rez_dict=True)
        pull = []
        for item in responce:
            if item['Вид'] == 1 or item['Уд_вес_ВО'] == 0:
                pull.append(item)
        if len(pull) > 0:
            CQT.msgbox(f'не внесены   "Вид",  "Уд_вес_ВО" в план МЕС    для:\n\n{pprint.pformat(pull)}')
            return False
        return True

    LIST_CHECK_TECHN = ['Цеховой технолог','Инженер-технолог']
    LIST_CHECK_GL_TECHN = ['Главный технолог', 'Ведущий инженер-технолог']
    LIST_CHECK_GL_TECHN_EXCLUDE_FIO = ['Степанова Алёна Сергеевна']
    name = F.user_full_namre()
    if name not in self.DICT_EMPLOEE_FULL:
        return True
    position = self.DICT_EMPLOEE_FULL[name]['Должность']

    if position in LIST_CHECK_GL_TECHN and name not in LIST_CHECK_GL_TECHN_EXCLUDE_FIO:
        if not check_respons_techn(self):
            return False
    if position in LIST_CHECK_TECHN:
        if not check_respons_sort_c_weight(self,name):
            return False
    return True

