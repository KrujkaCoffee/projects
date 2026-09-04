


`
itemSelectionChanged
->kal_plan.select_row
->prepare_local_gant_and_poz_info
->update_local_graf
`

```python
import datetime

from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38.Cust_mes import Type_day_gant, Month_cld_day

DICT_CLD = CSQ.custom_request_c(db,
       f"""SELECT data FROM notes_blob WHERE name = 'kplan_max_mosh';"""
    ,one_column=True,one=True,hat_c=False)
DICT_CLD = {
    datetime.datetime(2027, 7, 28, 0, 0): Month_cld_day(
        is_holyday=0, day_week=3, podrs={'podr': 3, 'пл_оуп': 2036.064, 'cust': 2036.064, 'знпр': 2036.064, 'mk': 2036.064, 'napravl_deyat': 2036.064, 'пл_ко': 170.688, 'пл_топ': 85.344, 'пл_осил': 97.536, 'пл_заг': 42.672, 'пл_мех': 67.056, 'plan': 67.056, 'пл_сб': 304.8, 'пл_отк': 42.672, 'пл_покр': 24.384, 'пл_компл': 73.152, 'пл_рскр': 304.8, 'пл_оснтк': 36.576, 'пл_швк': 36.576, 'пл_сбтк': 304.8, 'пл_чпу': 0, 'пл_сбмл': 304.8, 'пл_нбвк': 30.48, 'пл_свг': 304.8, 'пл_сббси': 304.8, 'пл_упквк': 73.152, 'пл_кмпл': 73.152, 'пл_откк': 42.672, 'пл_форм': 73.152, 'napravlenie': 2036.064}), 
    datetime.datetime(2027, 7, 29, 0, 0): Month_cld_day(
        is_holyday=0, day_week=4, podrs={'podr': 4, 'пл_оуп': 2036.064, 'cust': 2036.064, 'знпр': 2036.064, 'mk': 2036.064, 'napravl_deyat': 2036.064, 'пл_ко': 170.688, 'пл_топ': 85.344, 'пл_осил': 97.536, 'пл_заг': 42.672, 'пл_мех': 67.056, 'plan': 67.056, 'пл_сб': 304.8, 'пл_отк': 42.672, 'пл_покр': 24.384, 'пл_компл': 73.152, 'пл_рскр': 304.8, 'пл_оснтк': 36.576, 'пл_швк': 36.576, 'пл_сбтк': 304.8, 'пл_чпу': 0, 'пл_сбмл': 304.8, 'пл_нбвк': 30.48, 'пл_свг': 304.8, 'пл_сббси': 304.8, 'пл_упквк': 73.152, 'пл_кмпл': 73.152, 'пл_откк': 42.672, 'пл_форм': 73.152, 'napravlenie': 2036.064}), 
    datetime.datetime(2027, 7, 30, 0, 0): Month_cld_day(
        is_holyday=0, day_week=5, podrs={'podr': 5, 'пл_оуп': 2036.064, 'cust': 2036.064, 'знпр': 2036.064, 'mk': 2036.064, 'napravl_deyat': 2036.064, 'пл_ко': 170.688, 'пл_топ': 85.344, 'пл_осил': 97.536, 'пл_заг': 42.672, 'пл_мех': 67.056, 'plan': 67.056, 'пл_сб': 304.8, 'пл_отк': 42.672, 'пл_покр': 24.384, 'пл_компл': 73.152, 'пл_рскр': 304.8, 'пл_оснтк': 36.576, 'пл_швк': 36.576, 'пл_сбтк': 304.8, 'пл_чпу': 0, 'пл_сбмл': 304.8, 'пл_нбвк': 30.48, 'пл_свг': 304.8, 'пл_сббси': 304.8, 'пл_упквк': 73.152, 'пл_кмпл': 73.152, 'пл_откк': 42.672, 'пл_форм': 73.152, 'napravlenie': 2036.064}), 
}


gant_o = CMS.Gant(DICT_CLD,DTCLS.FIELDS_DB_INFO,min_day,max_day)

CMS.Day_gant().custom_weekend = False

poz = CMS.Poz_gant(7122).dict_agregate_etaps = {
    'plan': {
        Type_day_gant(name='plan', text='Пл.', emoj='📅'): (datetime.datetime(2026, 3, 26, 0, 0), datetime.datetime(2026, 3, 27, 0, 0))}, 
    'пл_заг': {
        Type_day_gant(name='fact', text='Ф.', emoj='🏁'): (datetime.datetime(2026, 3, 18, 0, 0), datetime.datetime(2026, 3, 18, 0, 0)), 
        Type_day_gant(name='plan', text='Пл.', emoj='📅'): (datetime.datetime(2026, 3, 23, 0, 0), datetime.datetime(2026, 3, 25, 0, 0))}, 
    'пл_компл': {
        Type_day_gant(name='fact', text='Ф.', emoj='🏁'): (datetime.datetime(2026, 3, 18, 0, 0), datetime.datetime(2026, 6, 24, 0, 0))}, 
    'пл_мех': {
        Type_day_gant(name='plan', text='Пл.', emoj='📅'): (datetime.datetime(2026, 3, 23, 0, 0), datetime.datetime(2026, 3, 25, 0, 0)), 
        Type_day_gant(name='fact', text='Ф.', emoj='🏁'): (datetime.datetime(2026, 6, 9, 0, 0), datetime.datetime(2026, 6, 9, 0, 0))}, 
    'пл_отк': {
        Type_day_gant(name='fact', text='Ф.', emoj='🏁'): (datetime.datetime(2026, 3, 20, 0, 0), datetime.datetime(2026, 6, 25, 0, 0)), 
        Type_day_gant(name='plan', text='Пл.', emoj='📅'): (datetime.datetime(2026, 4, 24, 0, 0), datetime.datetime(2026, 4, 27, 0, 0))}, 
    'пл_покр': {
        Type_day_gant(name='plan', text='Пл.', emoj='📅'): (datetime.datetime(2026, 4, 27, 0, 0), datetime.datetime(2026, 5, 4, 0, 0))}, 
    'пл_сб': {
        Type_day_gant(name='plan', text='Пл.', emoj='📅'): (datetime.datetime(2026, 3, 30, 0, 0), datetime.datetime(2026, 4, 23, 0, 0)), 
        Type_day_gant(name='fact', text='Ф.', emoj='🏁'): (datetime.datetime(2026, 6, 24, 0, 0), datetime.datetime(2026, 6, 26, 0, 0))}, 
    'пл_топ': {
        Type_day_gant(name='plan', text='Пл.', emoj='📅'): (datetime.datetime(2026, 3, 11, 0, 0), datetime.datetime(2026, 3, 20, 0, 0))}
}
CMS.Poz_gant().dict_days = {
    datetime.datetime(2026, 3, 1, 0, 0): Day_gant(poz_id=7122, date=2026-03-01, etaps_count=8), 
    datetime.datetime(2026, 3, 2, 0, 0): Day_gant(poz_id=7122, date=2026-03-02, etaps_count=8), 
    datetime.datetime(2026, 3, 3, 0, 0): Day_gant(poz_id=7122, date=2026-03-03, etaps_count=8), 
    datetime.datetime(2026, 3, 4, 0, 0): Day_gant(poz_id=7122, date=2026-03-04, etaps_count=8), 
    datetime.datetime(2026, 3, 5, 0, 0): Day_gant(poz_id=7122, date=2026-03-05, etaps_count=8), 
    datetime.datetime(2026, 3, 6, 0, 0): Day_gant(poz_id=7122, date=2026-03-06, etaps_count=8), 
    datetime.datetime(2026, 3, 7, 0, 0): Day_gant(poz_id=7122, date=2026-03-07, etaps_count=8), 
    datetime.datetime(2026, 3, 8, 0, 0): Day_gant(poz_id=7122, date=2026-03-08, etaps_count=8), 
datetime.datetime(2026, 3, 9, 0, 0): Day_gant(poz_id=7122, date=2026-03-09, etaps_count=8), 
datetime.datetime(2026, 3, 10, 0, 0): Day_gant(poz_id=7122, date=2026-03-10, etaps_count=8), 
datetime.datetime(2026, 3, 11, 0, 0): Day_gant(poz_id=7122, date=2026-03-11, etaps_count=8), 
datetime.datetime(2026, 3, 12, 0, 0): Day_gant(poz_id=7122, date=2026-03-12, etaps_count=8), 
datetime.datetime(2026, 3, 13, 0, 0): Day_gant(poz_id=7122, date=2026-03-13, etaps_count=8), 
datetime.datetime(2026, 3, 14, 0, 0): Day_gant(poz_id=7122, date=2026-03-14, etaps_count=8), 
datetime.datetime(2026, 3, 15, 0, 0): Day_gant(poz_id=7122, date=2026-03-15, etaps_count=8), 
datetime.datetime(2026, 3, 16, 0, 0): Day_gant(poz_id=7122, date=2026-03-16, etaps_count=8), 
datetime.datetime(2026, 3, 17, 0, 0): Day_gant(poz_id=7122, date=2026-03-17, etaps_count=8), 
datetime.datetime(2026, 3, 18, 0, 0): Day_gant(poz_id=7122, date=2026-03-18, etaps_count=8), 
datetime.datetime(2026, 3, 19, 0, 0): Day_gant(poz_id=7122, date=2026-03-19, etaps_count=8), 
datetime.datetime(2026, 3, 20, 0, 0): Day_gant(poz_id=7122, date=2026-03-20, etaps_count=8), 
datetime.datetime(2026, 3, 21, 0, 0): Day_gant(poz_id=7122, date=2026-03-21, etaps_count=8), 
datetime.datetime(2026, 3, 22, 0, 0): Day_gant(poz_id=7122, date=2026-03-22, etaps_count=8), 
datetime.datetime(2026, 3, 23, 0, 0): Day_gant(poz_id=7122, date=2026-03-23, etaps_count=8), 
datetime.datetime(2026, 3, 24, 0, 0): Day_gant(poz_id=7122, date=2026-03-24, etaps_count=8), 
datetime.datetime(2026, 3, 25, 0, 0): Day_gant(poz_id=7122, date=2026-03-25, etaps_count=8), datetime.datetime(2026, 3, 26, 0, 0): Day_gant(poz_id=7122, date=2026-03-26, etaps_count=8), datetime.datetime(2026, 3, 27, 0, 0): Day_gant(poz_id=7122, date=2026-03-27, etaps_count=8), datetime.datetime(2026, 3, 28, 0, 0): Day_gant(poz_id=7122, date=2026-03-28, etaps_count=8), datetime.datetime(2026, 3, 29, 0, 0): Day_gant(poz_id=7122, date=2026-03-29, etaps_count=8), datetime.datetime(2026, 3, 30, 0, 0): Day_gant(poz_id=7122, date=2026-03-30, etaps_count=8), datetime.datetime(2026, 3, 31, 0, 0): Day_gant(poz_id=7122, date=2026-03-31, etaps_count=8), datetime.datetime(2026, 4, 1, 0, 0): Day_gant(poz_id=7122, date=2026-04-01, etaps_count=8), datetime.datetime(2026, 4, 2, 0, 0): Day_gant(poz_id=7122, date=2026-04-02, etaps_count=8), datetime.datetime(2026, 4, 3, 0, 0): Day_gant(poz_id=7122, date=2026-04-03, etaps_count=8), datetime.datetime(2026, 4, 4, 0, 0): Day_gant(poz_id=7122, date=2026-04-04, etaps_count=8), datetime.datetime(2026, 4, 5, 0, 0): Day_gant(poz_id=7122, date=2026-04-05, etaps_count=8), datetime.datetime(2026, 4, 6, 0, 0): Day_gant(poz_id=7122, date=2026-04-06, etaps_count=8), datetime.datetime(2026, 4, 7, 0, 0): Day_gant(poz_id=7122, date=2026-04-07, etaps_count=8), datetime.datetime(2026, 4, 8, 0, 0): Day_gant(poz_id=7122, date=2026-04-08, etaps_count=8), datetime.datetime(2026, 4, 9, 0, 0): Day_gant(poz_id=7122, date=2026-04-09, etaps_count=8), datetime.datetime(2026, 4, 10, 0, 0): Day_gant(poz_id=7122, date=2026-04-10, etaps_count=8), datetime.datetime(2026, 4, 11, 0, 0): Day_gant(poz_id=7122, date=2026-04-11, etaps_count=8), datetime.datetime(2026, 4, 12, 0, 0): Day_gant(poz_id=7122, date=2026-04-12, etaps_count=8), datetime.datetime(2026, 4, 13, 0, 0): Day_gant(poz_id=7122, date=2026-04-13, etaps_count=8), datetime.datetime(2026, 4, 14, 0, 0): Day_gant(poz_id=7122, date=2026-04-14, etaps_count=8), datetime.datetime(2026, 4, 15, 0, 0): Day_gant(poz_id=7122, date=2026-04-15, etaps_count=8), datetime.datetime(2026, 4, 16, 0, 0): Day_gant(poz_id=7122, date=2026-04-16, etaps_count=8), datetime.datetime(2026, 4, 17, 0, 0): Day_gant(poz_id=7122, date=2026-04-17, etaps_count=8), datetime.datetime(2026, 4, 18, 0, 0): Day_gant(poz_id=7122, date=2026-04-18, etaps_count=8), datetime.datetime(2026, 4, 19, 0, 0): Day_gant(poz_id=7122, date=2026-04-19, etaps_count=8), datetime.datetime(2026, 4, 20, 0, 0): Day_gant(poz_id=7122, date=2026-04-20, etaps_count=8), datetime.datetime(2026, 4, 21, 0, 0): Day_gant(poz_id=7122, date=2026-04-21, etaps_count=8), datetime.datetime(2026, 4, 22, 0, 0): Day_gant(poz_id=7122, date=2026-04-22, etaps_count=8), datetime.datetime(2026, 4, 23, 0, 0): Day_gant(poz_id=7122, date=2026-04-23, etaps_count=8), datetime.datetime(2026, 4, 24, 0, 0): Day_gant(poz_id=7122, date=2026-04-24, etaps_count=8), datetime.datetime(2026, 4, 25, 0, 0): Day_gant(poz_id=7122, date=2026-04-25, etaps_count=8), datetime.datetime(2026, 4, 26, 0, 0): Day_gant(poz_id=7122, date=2026-04-26, etaps_count=8), datetime.datetime(2026, 4, 27, 0, 0): Day_gant(poz_id=7122, date=2026-04-27, etaps_count=8), datetime.datetime(2026, 4, 28, 0, 0): Day_gant(poz_id=7122, date=2026-04-28, etaps_count=8), datetime.datetime(2026, 4, 29, 0, 0): Day_gant(poz_id=7122, date=2026-04-29, etaps_count=8), datetime.datetime(2026, 4, 30, 0, 0): Day_gant(poz_id=7122, date=2026-04-30, etaps_count=8), datetime.datetime(2026, 5, 1, 0, 0): Day_gant(poz_id=7122, date=2026-05-01, etaps_count=8), datetime.datetime(2026, 5, 2, 0, 0): Day_gant(poz_id=7122, date=2026-05-02, etaps_count=8), datetime.datetime(2026, 5, 3, 0, 0): Day_gant(poz_id=7122, date=2026-05-03, etaps_count=8), datetime.datetime(2026, 5, 4, 0, 0): Day_gant(poz_id=7122, date=2026-05-04, etaps_count=8), datetime.datetime(2026, 5, 5, 0, 0): Day_gant(poz_id=7122, date=2026-05-05, etaps_count=8), datetime.datetime(2026, 5, 6, 0, 0): Day_gant(poz_id=7122, date=2026-05-06, etaps_count=8), datetime.datetime(2026, 5, 7, 0, 0): Day_gant(poz_id=7122, date=2026-05-07, etaps_count=8), datetime.datetime(2026, 5, 8, 0, 0): Day_gant(poz_id=7122, date=2026-05-08, etaps_count=8), datetime.datetime(2026, 5, 9, 0, 0): Day_gant(poz_id=7122, date=2026-05-09, etaps_count=8), datetime.datetime(2026, 5, 10, 0, 0): Day_gant(poz_id=7122, date=2026-05-10, etaps_count=8), datetime.datetime(2026, 5, 11, 0, 0): Day_gant(poz_id=7122, date=2026-05-11, etaps_count=8), datetime.datetime(2026, 5, 12, 0, 0): Day_gant(poz_id=7122, date=2026-05-12, etaps_count=8), datetime.datetime(2026, 5, 13, 0, 0): Day_gant(poz_id=7122, date=2026-05-13, etaps_count=8), datetime.datetime(2026, 5, 14, 0, 0): Day_gant(poz_id=7122, date=2026-05-14, etaps_count=8), datetime.datetime(2026, 5, 15, 0, 0): Day_gant(poz_id=7122, date=2026-05-15, etaps_count=8), datetime.datetime(2026, 5, 16, 0, 0): Day_gant(poz_id=7122, date=2026-05-16, etaps_count=8), datetime.datetime(2026, 5, 17, 0, 0): Day_gant(poz_id=7122, date=2026-05-17, etaps_count=8), datetime.datetime(2026, 5, 18, 0, 0): Day_gant(poz_id=7122, date=2026-05-18, etaps_count=8), datetime.datetime(2026, 5, 19, 0, 0): Day_gant(poz_id=7122, date=2026-05-19, etaps_count=8), datetime.datetime(2026, 5, 20, 0, 0): Day_gant(poz_id=7122, date=2026-05-20, etaps_count=8), datetime.datetime(2026, 5, 21, 0, 0): Day_gant(poz_id=7122, date=2026-05-21, etaps_count=8), datetime.datetime(2026, 5, 22, 0, 0): Day_gant(poz_id=7122, date=2026-05-22, etaps_count=8), datetime.datetime(2026, 5, 23, 0, 0): Day_gant(poz_id=7122, date=2026-05-23, etaps_count=8), datetime.datetime(2026, 5, 24, 0, 0): Day_gant(poz_id=7122, date=2026-05-24, etaps_count=8), datetime.datetime(2026, 5, 25, 0, 0): Day_gant(poz_id=7122, date=2026-05-25, etaps_count=8), datetime.datetime(2026, 5, 26, 0, 0): Day_gant(poz_id=7122, date=2026-05-26, etaps_count=8), datetime.datetime(2026, 5, 27, 0, 0): Day_gant(poz_id=7122, date=2026-05-27, etaps_count=8), datetime.datetime(2026, 5, 28, 0, 0): Day_gant(poz_id=7122, date=2026-05-28, etaps_count=8), datetime.datetime(2026, 5, 29, 0, 0): Day_gant(poz_id=7122, date=2026-05-29, etaps_count=8), datetime.datetime(2026, 5, 30, 0, 0): Day_gant(poz_id=7122, date=2026-05-30, etaps_count=8), datetime.datetime(2026, 5, 31, 0, 0): Day_gant(poz_id=7122, date=2026-05-31, etaps_count=8), datetime.datetime(2026, 6, 1, 0, 0): Day_gant(poz_id=7122, date=2026-06-01, etaps_count=8), datetime.datetime(2026, 6, 2, 0, 0): Day_gant(poz_id=7122, date=2026-06-02, etaps_count=8), datetime.datetime(2026, 6, 3, 0, 0): Day_gant(poz_id=7122, date=2026-06-03, etaps_count=8), datetime.datetime(2026, 6, 4, 0, 0): Day_gant(poz_id=7122, date=2026-06-04, etaps_count=8), datetime.datetime(2026, 6, 5, 0, 0): Day_gant(poz_id=7122, date=2026-06-05, etaps_count=8), datetime.datetime(2026, 6, 6, 0, 0): Day_gant(poz_id=7122, date=2026-06-06, etaps_count=8), datetime.datetime(2026, 6, 7, 0, 0): Day_gant(poz_id=7122, date=2026-06-07, etaps_count=8), datetime.datetime(2026, 6, 8, 0, 0): Day_gant(poz_id=7122, date=2026-06-08, etaps_count=8), datetime.datetime(2026, 6, 9, 0, 0): Day_gant(poz_id=7122, date=2026-06-09, etaps_count=8), datetime.datetime(2026, 6, 10, 0, 0): Day_gant(poz_id=7122, date=2026-06-10, etaps_count=8), datetime.datetime(2026, 6, 11, 0, 0): Day_gant(poz_id=7122, date=2026-06-11, etaps_count=8), datetime.datetime(2026, 6, 12, 0, 0): Day_gant(poz_id=7122, date=2026-06-12, etaps_count=8), datetime.datetime(2026, 6, 13, 0, 0): Day_gant(poz_id=7122, date=2026-06-13, etaps_count=8), datetime.datetime(2026, 6, 14, 0, 0): Day_gant(poz_id=7122, date=2026-06-14, etaps_count=8), datetime.datetime(2026, 6, 15, 0, 0): Day_gant(poz_id=7122, date=2026-06-15, etaps_count=8), datetime.datetime(2026, 6, 16, 0, 0): Day_gant(poz_id=7122, date=2026-06-16, etaps_count=8), datetime.datetime(2026, 6, 17, 0, 0): Day_gant(poz_id=7122, date=2026-06-17, etaps_count=8), datetime.datetime(2026, 6, 18, 0, 0): Day_gant(poz_id=7122, date=2026-06-18, etaps_count=8), datetime.datetime(2026, 6, 19, 0, 0): Day_gant(poz_id=7122, date=2026-06-19, etaps_count=8), datetime.datetime(2026, 6, 20, 0, 0): Day_gant(poz_id=7122, date=2026-06-20, etaps_count=8), datetime.datetime(2026, 6, 21, 0, 0): Day_gant(poz_id=7122, date=2026-06-21, etaps_count=8), datetime.datetime(2026, 6, 22, 0, 0): Day_gant(poz_id=7122, date=2026-06-22, etaps_count=8), datetime.datetime(2026, 6, 23, 0, 0): Day_gant(poz_id=7122, date=2026-06-23, etaps_count=8), datetime.datetime(2026, 6, 24, 0, 0): Day_gant(poz_id=7122, date=2026-06-24, etaps_count=8), datetime.datetime(2026, 6, 25, 0, 0): Day_gant(poz_id=7122, date=2026-06-25, etaps_count=8), datetime.datetime(2026, 6, 26, 0, 0): Day_gant(poz_id=7122, date=2026-06-26, etaps_count=8), datetime.datetime(2026, 6, 27, 0, 0): Day_gant(poz_id=7122, date=2026-06-27, etaps_count=8), datetime.datetime(2026, 6, 28, 0, 0): Day_gant(poz_id=7122, date=2026-06-28, etaps_count=8), datetime.datetime(2026, 6, 29, 0, 0): Day_gant(poz_id=7122, date=2026-06-29, etaps_count=8), datetime.datetime(2026, 6, 30, 0, 0): Day_gant(poz_id=7122, date=2026-06-30, etaps_count=8)}
```