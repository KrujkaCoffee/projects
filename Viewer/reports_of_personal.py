from __future__ import annotations

import copy
import datetime

import dataClass

if __name__ == "__main__":
    quit()
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_emoji as CEMOJ

from dataclasses import dataclass
try:
    from dataClass import data_app as DTCLS
except:
    pass

from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from Viewer import mywindow

class Base_get_data():
    def parse_data(self,data:dict):
        for key in data.keys():
            fix_key = key.replace(".", "_")
            if fix_key not in self.__dict__:
                print(f'arg {fix_key} missed in {self.__class__.__name__}')
            exec(f'self.{key.replace(".", "_")} = data[key]')

class Report_date():
    DB_MASK = "%Y-%m-%d"
    def __init__(self, date: str | None | Report_date=None):

        self.date:None|datetime.date = None
        if isinstance(date, Report_date):
            self.date = date.date
            return
        if isinstance(date,datetime.datetime):
            self.date = date
        if isinstance(date,datetime.date):
            self.date = datetime.datetime.combine(date,datetime.time.min)
        if date and F.is_date(date,self.DB_MASK):
            self.date = F.strtodate(date, self.DB_MASK)

    @staticmethod
    def into_ru_notation(date:str|datetime.datetime|datetime.date):
        return F.dateStrToStr(date,format_out="%d.%m.%Y")
    def to_db(self)->str:
        return str(self)
    def ru_notation(self):
        if self.date is None:
            return ''
        return F.datetostr(self.date, "%d.%m.%Y")

    def __str__(self):
        if self.date is None:
            return ''
        return F.datetostr(self.date,self.DB_MASK)




class Rule(Base_get_data):
    def __init__(self,data=None):
        self.name = None
        self.id = None
        self.ref_user = None
        self.doc_types:list[Doc_type] = []
        self.period:Period|None|int = None
        self.count_by_period:int|None = None
        self.start_date: Report_date | None = Report_date()
        self.description:str = ''
        self.ref_creator:str = ''
        self.id_chat_24:str = ''
        if data:
            self.parse_data(data)
        if self.period:
            self.period = Periods.get_period(self.period)
        if self.start_date and not isinstance(self.start_date, Report_date):
            self.start_date = Report_date(self.start_date)
        self.state:Status|None = None
        self.is_early:bool = self.start_date.date > F.now('')

    def __str__(self):
        return f'{self.name} ({self.count_by_period} в {self.period.date_time_liter}) с {self.start_date}'

    def __eq__(self, other):
        return str(self) == str(other)

    def __gt__(self, other):
        return str(self)>str(other)


    def calc_status(self):
        self.state = Statuses.in_period

        count_passed = 0
        count_approved = 0
        start_date_period, end_date_period = F.start_end_dates_c(vid=self.period.date_time_liter,format_out='')
        for doc in DTCLS.module_repots_of_personal.current_user_events.list_events:
            if doc.rule != self:
                continue
            if doc.date.date >= start_date_period and doc.date.date <= end_date_period:
                count_passed += 1
                if doc.date_approval.date:
                    count_approved += 1
        if count_approved == self.count_by_period:
            self.state = Statuses.approved
            return
        if count_passed == self.count_by_period:
            self.state = Statuses.passed
            return


    @staticmethod
    def load(ref_user:str)->list[Rule]:
        return DTCLS.module_repots_of_personal.user_report_rules.find(ref_user)

    def creator_fio(self):
        return DTCLS.app_self.DICT_EMPLOEE_FULL_WITH_DEL_BY_REF[self.ref_creator]['ФИО']

    def title_rule(self,short=False,types=True)->str:
        types_str = ''
        if types:
            types_str = f', {";".join([_h.name for _h in self.doc_types])}'
        if short:
            return f'{self.name}{types_str}'
        msg = f'{self.name}: {self.count_by_period} раз в {self.period.name}{types_str}'
        return msg

    def str_doc_types(self):
        return Rules.SEP.join([str(_.id) for _ in self.doc_types])

    def str_period(self):
        if self.period is None:
            return  ''
        return str(self.period.id)

    def get_template(self):
        name = self.name
        id = self.id
        ref_user = self.ref_user
        doc_types = self.doc_types
        period: Period | None | int = self.period
        count_by_period: int | None = self.count_by_period
        start_date: Report_date | None = self.start_date
        description: str  = self.description
        chat:str = self.id_chat_24


        tmp =   [
            {'Параметр':'Название', 'Значение':name, 'Name':'name'},
            {'Параметр':'УИД', 'Значение':id, 'Name':'id'},
            {'Параметр':'Пользователь', 'Значение':ref_user, 'Name':'ref_user'},
            {'Параметр':'Типы документов', 'Значение':self.str_doc_types(), 'Name':'doc_types'},
            {'Параметр':'Период', 'Значение':self.str_period(), 'Name':'period'},
            {'Параметр':'Кол-во за период', 'Значение':count_by_period, 'Name':'count_by_period'},
            {'Параметр':'Дата начала', 'Значение': start_date, 'Name':'start_date'},
            {'Параметр':'Описание', 'Значение': description, 'Name':'description'},
            {'Параметр':'Вывод в Б24 чат №', 'Значение': chat, 'Name':'id_chat_24'},
        ]
        return tmp
class Rules():
    SEP = '; '
    def __init__(self):
        self.rules:list[Rule]|None = None
        self._dict_user_count:dict = dict()
        self._dict_doctypes:dict = dict()

    def get_id_doc_type(self,id_rule:int,id_type:int)->int|None:
        for item in self._dict_doctypes:
            if item['rule_id'] == id_rule and item['doc_type_id'] == id_type:
                return item['id']

    def generate_diagramm(self, events: Events, list_rules: list[Rule]) -> list[dict]:
        sc = Schedule()
        for rule in list_rules:
            sc.add_rule(rule)
        for event in events.list_events:
            sc.apply_event(event)
        sc.recalc_states()
        sc.filtred()
        sc.sorted()
        return sc.get_template()

    def get_rule_id_by_doc_type(self, id_doc_type: int) -> int | None:
        for item in self._dict_doctypes:
            if item['id'] == id_doc_type:
                return item['rule_id']

    def edit_rule(self, edited_rule: dict) -> Rule | None:

        def err_clear(id_rule, num_add):
            CSQ.custom_request_c(CFG.Config.project.db_users, f"""DELETE FROM user_report_rules WHERE 
                            rule_id = {id_rule} AND doc_type_id IN ({CSQ.prepare_list_to_tuple(num_add)}) 
                            ;"""
                                 )
            CQT.msgbox(f'Ошибка создания правила')

        id_rule = int(edited_rule['id'])
        edit_data = [

            edited_rule['name'],
            edited_rule['period'],
            edited_rule['count_by_period'],
            edited_rule['start_date'],
            edited_rule['description'],
            edited_rule['id_chat_24'],
        ]

        returning = CSQ.custom_request_c(CFG.Config.project.db_users,
                                         f"""UPDATE user_report_rules SET (

                                  name,
                                  period,
                                  count_by_period,
                                  start_date,
                                  description,
                                  id_chat_24
                              )
                        =  ({CSQ.questions_for_mask(edit_data)}) WHERE id = {id_rule};
                """, list_of_lists_c=edit_data)

        old_rule = DTCLS.module_repots_of_personal.user_report_rules.get_rule(id_rule)

        old_doc_types = old_rule.doc_types
        new_doc_types = [int(_) for _ in edited_rule['doc_types'].split(Rules.SEP)]
        old_set_num = set([_.id for _ in old_doc_types])
        new_set_num = set(new_doc_types)
        num_del = list(old_set_num - new_set_num)
        num_add = list(new_set_num - old_set_num)

        if num_add:
            insert_data = [[id_rule, int(_)] for _ in num_add]
            id_added_doc_types = CSQ.custom_request_c(CFG.Config.project.db_users, f"""INSERT INTO user_report_rule_doc_types (

                                                   rule_id,
                                                   doc_type_id
                                               )
                                               VALUES ({CSQ.questions_for_mask(insert_data[0])}
                                               );
            """, list_of_lists_c=insert_data)
            if not id_added_doc_types:
                err_clear(id_rule, num_add)
                return

        if num_del:
            res = CSQ.custom_request_c(CFG.Config.project.db_users, f"""DELETE FROM user_report_rule_doc_types 
                    WHERE rule_id = {id_rule} AND doc_type_id IN ({CSQ.prepare_list_to_tuple(num_del)}) ;
            """)
            if not res:
                err_clear(id_rule, num_add)
                return

        self.load_rules()
        CQT.msgbox(f'Успешно изменено правило')
        return self.get_rule(id_rule)

    def new_rule(self, new_rule: dict) -> Rule | None:

        insert_data = [

            new_rule['ref_user'],
            new_rule['name'],
            new_rule['period'],
            new_rule['count_by_period'],
            new_rule['start_date'],
            new_rule['description'],
            DTCLS.module_repots_of_personal.creator_user.ID_ФизЛица,
            new_rule['id_chat_24'],
        ]

        returning = CSQ.custom_request_c(CFG.Config.project.db_users,
                                         f"""INSERT INTO user_report_rules (

                                  ref_user,
                                  name,
                                  period,
                                  count_by_period,
                                  start_date,
                                  description,
                                  ref_creator,
                                  id_chat_24
                              )
                        VALUES ({CSQ.questions_for_mask(insert_data)}) RETURNING id ;
                """, list_of_lists_c=insert_data)

        new_doc_type_data = F.list_of_lists_to_list_of_dicts(returning)[0]
        new_id = new_doc_type_data['id']

        insert_data = [[new_id, int(_)] for _ in new_rule['doc_types'].split(Rules.SEP)]
        id_added_doc_types = CSQ.custom_request_c(CFG.Config.project.db_users, f"""INSERT INTO user_report_rule_doc_types (

                                               rule_id,
                                               doc_type_id
                                           )
                                           VALUES ({CSQ.questions_for_mask(insert_data[0])}
                                           );
        """, list_of_lists_c=insert_data)
        if not id_added_doc_types:
            CSQ.custom_request_c(CFG.Config.project.db_users, f"""DELETE FROM user_report_rules WHERE id = {new_id};"""
                                 )
            CQT.msgbox(f'Ошибка создания правила')
            return
        self.load_rules()
        CQT.msgbox(f'Успешно создано правило')
        return self.get_rule(new_id)

    def _load_dict_doctypes(self):
        doc_types_rules_data = CSQ.custom_request_c(CFG.Config.project.db_users,
                                                    f"""SELECT id,
                                                           rule_id,
                                                           doc_type_id
                                                      FROM user_report_rule_doc_types;""", rez_dict=True)
        self._dict_doctypes = doc_types_rules_data

    def load_rules(self):
        list_rules = CSQ.custom_request_c(CFG.Config.project.db_users,
                                          f"""SELECT id,
               ref_user,
               name,
               period,
               count_by_period,
               start_date,
               description,
               ref_creator,
               id_chat_24
          FROM user_report_rules;
        """, rez_dict=True)
        rules = [Rule(_) for _ in list_rules]

        self._load_dict_doctypes()

        _dict_user_count = dict()
        for rule in rules:
            if rule.ref_user not in _dict_user_count:
                _dict_user_count[rule.ref_user] = 0
            _dict_user_count[rule.ref_user] += 1

            for doc_type in self._dict_doctypes:
                if rule.id == doc_type['rule_id']:
                    rule.doc_types.append(Doc_types.get_doc_type(doc_type['doc_type_id']))
        self.rules = rules
        self._dict_user_count = _dict_user_count
        DTCLS.module_repots_of_personal.user_report_rules = self

    def user_count_rules(self, id: str) -> int:
        if id in self._dict_user_count:
            return self._dict_user_count[id]
        return 0

    def get_rule(self, id: int) -> Rule:
        for rule in self.rules:
            if rule.id == id:
                return rule

    def find(self, ref_user: str, creator_ref: str | None = None,
             date_end: datetime.date | None = None) -> list[Rule]:
        res = []
        if self.rules is None:
            return res
        for rule in self.rules:
            fl_add = True
            if rule.ref_user != ref_user:
                fl_add = False

            if fl_add and creator_ref:
                if rule.ref_creator != creator_ref:
                    fl_add = False
            if fl_add and date_end:
                if rule.start_date.date > date_end:
                    fl_add = False

            if fl_add:
                res.append(rule)
        return res


class Schedule():
    def __init__(self):
        self.elems:list[Schedule_elem]=[]
        self._set_for_recalc_states:set[Schedule_elem] = set()
    def recalc_states(self):
        for elem in self._set_for_recalc_states:
            elem.calc_status()
        self._set_for_recalc_states = set()
    def get_template(self):
        return [_.gen_template() for _ in self.elems]

    def add_rule(self,rule:Rule):
        period = rule.period
        period_liter = period.date_time_liter
        start_date = rule.start_date.date
        start_date_period = F.start_end_dates_c(start_date, '', vid=period_liter, format_out='')[0]
        end_date_period = F.start_end_dates_c(F.now("%Y-%m-%d"), "%Y-%m-%d", vid=period_liter, format_out='')[0]

        start_tmp = copy.deepcopy(start_date_period)
        while start_tmp <= end_date_period:
            end_tmp = F.date_add_period(start_tmp, '', period_liter, '')
            end_date = F.date_add_days(end_tmp, -1, '', '')
            sc_elem = Schedule_elem(rule,
                                    start_tmp,
                                    end_date
                                    )
            self.elems.append(sc_elem)
            start_tmp = end_tmp

    def apply_event(self,event:Event):
        rule = event.rule
        id = rule.id
        date_obj = event.date
        for item in self.elems:
            if item.rule_id == id:
                if item.start_time_frame <= date_obj.date and item.end_time_frame >= date_obj.date:
                    item.docs.append(Schedule_doc(event))
                self._set_for_recalc_states.add(item)



    def filtred(self):
        DTM = DTCLS.module_repots_of_personal
        rezult_filtered = []

        def date_between_settings(date) -> bool:
            if date >= DTM.date_start_report and date <= DTM.date_end_report:
                return True
            return False

        def settings_between_date(elem_date_start,elem_date_end) -> bool:
            if elem_date_start <= DTM.date_start_report and elem_date_start >= DTM.date_end_report:
                return True
            return False

        for item in self.elems:
            if (date_between_settings(item.start_time_frame) or date_between_settings(item.end_time_frame)
                    or settings_between_date(item.start_time_frame,item.end_time_frame)):
                rezult_filtered.append(item)
        self.elems = rezult_filtered



    def sort_by_attr(
            self,
            attr_name: str,
            reverse: bool = False,
            date_time: bool = False,
            date_format: str = "%Y-%m-%d %H:%M:%S",
            type_compare: str | None = None
    ):
        if not self.elems:
            return

        def key_func(elem: Schedule_elem):
            val = getattr(elem, attr_name, None)

            if val is None or val == "":
                if type_compare == "numeric":
                    return 0
                if type_compare == "str":
                    return ""
                return val

            if date_time:
                if F.is_date(val, date_format):
                    return F.strtodate(val, date_format)
                return F.strtodate("20.11.2001", "%d.%m.%Y")

            if type_compare == "numeric":
                return val

            if type_compare == "str":
                return str(val)

            return val

        self.elems.sort(key=key_func, reverse=reverse)

    def sorted(self):
        self.sort_by_attr('rule')
        self.sort_by_attr('period_priority')
        self.sort_by_attr('end_time_frame', date_time=True, date_format="%d.%m.%Y")

class Schedule_doc():
    def __init__(self,event:Event):
        self.event = event
        self.date = event.date.ru_notation()
        self.doc = event.link
        self.message = event.message
        self.approval = event.date_approval.ru_notation()
        self.msg_approval = event.msg_approval
        self.event_id = event.id

    def get_template(self):
        return {
            'Дата':   self.date,
            'Документ':  self.doc,
            'Примечание': self.message,
            'Утвержден':  self.approval,
            'Замечание':  self.msg_approval,
            'event_id':  self.event_id
        }

class Schedule_elem():
    def __init__(self,rule:Rule,
                 start_time_frame,
                 end_time_frame,

                 ):
        self.rule:Rule = rule
        self.start_time_frame:str = start_time_frame
        self.end_time_frame:str = end_time_frame
        self.rule_id:int = rule.id
        self.ref_creator:str = rule.ref_creator
        self.period_priority:int = rule.period.priority
        self.docs:list[Schedule_doc] = []
        self.state:Status |None   = None
        self.calc_status()
    def __str__(self):
        return f'С {self.start_time_frame} по {self.end_time_frame} {self.rule.name}'

    def calc_status(self):
        if F.now('') < self.start_time_frame:
            self.state = Statuses.early
        if F.now('') > self.start_time_frame and F.now('') <= self.end_time_frame:
            self.state = Statuses.in_period
        if F.now('') > self.end_time_frame:
            self.state = Statuses.expired
        if self.docs:
            count_passed = False
            count_approved = False
            for doc in self.docs:
                if doc.event.date.date:
                    count_passed += 1
                if doc.event.date_approval.date:
                    count_approved += 1
            if count_approved == self.rule.count_by_period:
                self.state = Statuses.approved
                return
            if count_passed == self.rule.count_by_period:
                self.state = Statuses.passed
                return




    def gen_template(self):
        docs = ''
        if self.docs:
            docs = [_.get_template() for _ in self.docs]
        return {
            'Срок с': Report_date.into_ru_notation(self.start_time_frame),
            'Срок по': Report_date.into_ru_notation(self.end_time_frame),
            'rule_id': self.rule_id,
            'ref_creator': self.ref_creator,
            'Правило': self.rule.title_rule(False, False),
            'period_priority': self.period_priority,
            'Статус': self.state.to_str(),
            'state': self.state.name,
            'Документы': docs
        }

class Doc_type(Base_get_data):
    def __init__(self,data):
        self.id:None|int = None
        self.name:None|str = None
        self.file_extension:None|str = None
        self.parse_data(data)
    @staticmethod
    def get_template():
        attrs =  [
            {'Параметр':'Название', 'Значение':'', 'Name':'name'},
            {'Параметр':'Расширения', 'Значение':'', 'Name':'file_extension'}]
        return attrs

    def title(self)->str:
        return f'{self.name}({self.file_extension})'

class Doc_types():
    list_types: list[Doc_type] | None =  [Doc_type(_) for _ in DTCLS.module_repots_of_personal.user_report_doc_types]

    @classmethod
    def get_list_types(cls):
        cls.list_types: list[Doc_type] | None = [Doc_type(_) for _ in DTCLS.module_repots_of_personal.user_report_doc_types]

    @classmethod
    def get_doc_type(cls, id: int):
        if not isinstance(id, int):
            raise TypeError
        for item in cls.list_types:
            if id == item.id:
                return item
    @classmethod
    def add_new(cls,name_doc_type,file_extension):
        insert_data = [name_doc_type, file_extension]

        returning = CSQ.custom_request_c(CFG.Config.project.db_users,
                                                 f"""INSERT INTO user_report_doc_types (name,
                                      file_extension)
                                  VALUES ({CSQ.questions_for_mask(insert_data)}) RETURNING id ;
                """, list_of_lists_c=insert_data)
        new_doc_type_data = F.list_of_lists_to_list_of_dicts(returning)[0]
        DTCLS.module_repots_of_personal.user_report_doc_types =  dataClass.load_user_report_doc_types()
        Doc_types.get_list_types()
        obj = Doc_types.get_doc_type(new_doc_type_data['id'])
        return obj

class Period(Base_get_data):
    def __init__(self,data:dict):
        self.name:str|None = None
        self.id:int|None  = None
        self.date_time_liter:str|None  = None
        self.priority:int|None  = None
        self.parse_data(data)

class Periods():
    list_periods:list[Period]|None = [Period(_) for _ in DTCLS.module_repots_of_personal.user_report_periods]
    @classmethod
    def get_period(cls,id:int):
        if not isinstance(id,int):
            raise TypeError
        for item in cls.list_periods:
            if id == item.id:
                return item

class Event(Base_get_data):
    def __init__(self,data:dict|None=None):
        self.id:int|None = None
        self.rule_doc_id:int|None = None
        self.link:str|None = None
        self.client_link:str|None = None
        self.message:str|None = None
        self._date: Report_date | str | None = None
        self.user:CMS.Emploee_usr|None = None
        self.rule:Rule|None = None
        self._date_approval:Report_date|None = None
        self.msg_approval:str|None = None

        if data:
            self.parse_data(data)

        if data:
            self.get_rule()
            self.get_user()

    def __str__(self):
        appr = f''
        if self.date_approval:
            appr = f' утв.:{self.date_approval.ru_notation()}'
        return f'{self.date.ru_notation()} по {self.rule.name} ({self.message}){appr}'

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self,val):
        self._date = Report_date(val)


    @property
    def date_approval(self):
        return self._date_approval

    @date_approval.setter
    def date_approval(self,val):
        self._date_approval = Report_date(val)



    @staticmethod
    def get_template():
        attrs = [
            {'Параметр': 'Tип', 'Значение': '', 'Name': 'doc_type'},
            {'Параметр': 'Файл', 'Значение': '', 'Name': 'link'},
            {'Параметр': 'Описание', 'Значение': '', 'Name': 'message'}]
        return attrs

    def get_template_b24(self):
        return [
            {'Параметр':'Правило','Значение':self.rule.name},
            {'Параметр':'Дата','Значение':self.date.ru_notation()},
            {'Параметр':'Примечание','Значение':self.message},
                ]

    def set_approved(self,msg:str):
        self.date_approval = F.now('')
        self.msg_approval = msg
        self.save()

    def get_rule(self):
        id_rule = DTCLS.module_repots_of_personal.user_report_rules.get_rule_id_by_doc_type(self.rule_doc_id)
        rule =  DTCLS.module_repots_of_personal.user_report_rules.get_rule(id_rule)
        self.rule = rule
        return rule

    def get_user(self):
        if not hasattr(self,'rule'):
            self.get_rule()
        user = CMS.Emploee_usr(self.rule.ref_user,CFG.Config.project.db_users)
        self.user = user
        return user


    def gen_path(self,ext) -> str:
        if not self.date:
            raise ValueError(f'{self.date} is not date')
        path = f'{F.sep().join([Events.DIR_REPOZ_FILES,self.user.ФИО,self.rule.name,self.date.to_db()])}{ext}'
        return path

    def save(self):
        if self.id is None:
            list_ins = [self.rule_doc_id,self.link,self.message,self.date.to_db(),self.date_approval.to_db(),self.msg_approval]
            rez = CSQ.custom_request_c(CFG.Config.project.db_users,f""" INSERT INTO user_report_events
                              (rule_doc_id, link, message,date,date_approval,msg_approval)
                              VALUES ({CSQ.questions_for_mask(list_ins)}) RETURNING id ; """,
                                       list_of_lists_c=list_ins,rez_dict=True)
            self.id = rez[0]['id']
        else:
            list_upd = [self.rule_doc_id, self.link, self.message,self.date.to_db(),self.date_approval.to_db(),self.msg_approval.strip()]
            rez = CSQ.custom_request_c(CFG.Config.project.db_users, f""" UPDATE user_report_events
                SET  (
                rule_doc_id,
                link,
                message,
                date,
                date_approval,
                msg_approval 
                )
                    = ({CSQ.questions_for_mask(list_upd)}) WHERE id = {self.id}; """, list_of_lists_c=[list_upd])

    def send_into_b24(self,id_chat_24:str,edit=False):
        msg = f'Добавлен документ'
        if edit:
            msg = f'Изменен документ'
        CMS.send_tbl_b24_by_action(
            f'{msg} по \n{self.rule.name}\n{F.now("%d.%m.%Y %H:%M")} {DTCLS.module_repots_of_personal.current_user.ФИО}',
            'Отчетность пользователей',
            self.get_template_b24(),chat_id=id_chat_24)
class Regime():
    def __init__(self,name,description,icon,tooltip):
        self.name = name
        self.description = description
        self.icon = icon
        self.tooltip = tooltip
@dataclass
class Regimes():
    settings:Regime = Regime('settings','Настройки',CEMOJ.EmojiMain.ОборудованиеИнструменты.tool.symbol,'Создание и изменение правил сдачи отчетности')
    report:Regime = Regime('report','Отчет',CEMOJ.EmojiMain.ДокументыДанные.analysis.symbol,'Генерация план-отчета сдачи отчетности по сотруднику')
    events:Regime = Regime('events','Документы',CEMOJ.EmojiMain.ДокументыДанные.document.symbol,'Просмотр и добавление отчетности по сотруднику' )

class Status():
    def __init__(self,
                name:str,
                descr:str,
                emo:str,
                in_period:bool,
                expired:bool,
                passed:bool,
                approved:bool
    ):
        self.name:str = name
        self.descr:str = descr
        self.emo:str = emo
        self.in_period:bool = in_period
        self.expired:bool = expired
        self.passed:bool = passed
        self.approved:bool = approved

    def __str__(self):
        return f'{self.name}({self.descr})'
    def to_str(self):
        return f'{self.emo} {self.descr}'

@dataclass
class Statuses():
    early:Status = Status('early','',CEMOJ.EmojiMain.СтатусыПроизводства.selected.symbol,False,False,False,False)
    in_period:Status = Status('in_period','К сдаче',CEMOJ.EmojiMain.СтатусыПроизводства.uncertain.symbol,True,False,False,False)
    expired:Status = Status('expired','Просрочен',CEMOJ.EmojiMain.СтатусыПроизводства.stopped.symbol,False,True,False,False)
    passed:Status = Status('passed','Сдан',CEMOJ.EmojiMain.СтатусыПроизводства.idle.symbol,True,False,True,False)
    approved:Status = Status('approved','Утвержден',CEMOJ.EmojiMain.СтатусыПроизводства.normal.symbol,True,False,True,True)



class Events():
    list_events:list[Event]|None = None
    #DIR_REPOZ_FILES = fr'O:\ОБЩАЯ\Отдел персонала\ПАУЭРЗ\Отчетность персонала'
    DIR_REPOZ_FILES = fr'O:\ОБЩАЯ\Обмен\Отчетность персонала'

    def __init__(self):
        if not F.existence_file_c(self.DIR_REPOZ_FILES):
            CQT.msgbox(f'Нет доступа к Директории с файлами. Обратитесь к администратору')
            raise PermissionError
        DTCLS.module_repots_of_personal.current_user_events = self

    def load_event(self,id:int)->Event:
        event = CSQ.custom_request_c(CFG.Config.project.db_users, f"""SELECT 
                            user_report_events.id,
                           user_report_events.rule_doc_id,
                           user_report_events.link,
                           user_report_events.message,
                           user_report_events.date,
                           user_report_events.date_approval,
                           user_report_events.msg_approval 
                           FROM user_report_events
                            INNER JOIN user_report_rule_doc_types ON user_report_rule_doc_types.id = user_report_events.rule_doc_id
                        INNER JOIN user_report_rules ON user_report_rules.id = user_report_rule_doc_types.rule_id
                       WHERE user_report_events.id = {id};
                """, rez_dict=True,one=True)

        return Event(event)
    def load_events(self,ref_user:str):
        events = CSQ.custom_request_c(CFG.Config.project.db_users, f"""SELECT 
                    user_report_events.id,
                   user_report_events.rule_doc_id,
                   user_report_events.link,
                   user_report_events.message,
                   user_report_events.date,
                   user_report_events.date_approval,
                   user_report_events.msg_approval 
                   FROM user_report_events
                    INNER JOIN user_report_rule_doc_types ON user_report_rule_doc_types.id = user_report_events.rule_doc_id
                INNER JOIN user_report_rules ON user_report_rules.id = user_report_rule_doc_types.rule_id
               WHERE user_report_rules.ref_user = "{ref_user}";
        """, rez_dict=True)

        self.list_events = [Event(_) for _ in events]


    def gen_template(self)->list[dict]:
        if self.list_events is None:
            return  []
        return [ {
            'id':_.id,
            'Дата':_.date,
            'Название': _.rule.name,
            'link':_.link,
            'Файл':'',
            'Примечание':_.message,
            'Утвержден':_.date_approval,
            'Замечание':_.msg_approval,

        } for _ in self.list_events]

    def _copy_file(self,event:Event)->str|None:
        link = event.client_link
        if not F.existence_file_c(link):
            CQT.msgbox(f'Файл {link} не обнаружен')
            raise FileNotFoundError
        ext = F.keep_extention_c(link)
        new_path = event.gen_path(ext)
        if not F.copy_file_c(link,new_path):
            CQT.msgbox(f'Error copy files')
            return
        return new_path


    def add_new_event(self,rule_doc_id,link,message)->Event|None:
        event = Event()
        event.client_link = link
        event.rule_doc_id = rule_doc_id
        event.message = message
        event.date_approval = ''

        event.get_rule()
        event.get_user()
        event.date = F.now('%Y-%m-%d')
        new_path = self._copy_file(event)
        if new_path is None:
            return
        event.link = new_path

        event.save()
        self.list_events.append(event)
        return event



def ______________INIT___________________():
    pass

def init_rules():
    Rules().load_rules()

def init_dates_reports(date_start:datetime.datetime,date_end:datetime.datetime):
    DTCLS.module_repots_of_personal.date_start_report = date_start
    DTCLS.module_repots_of_personal.date_end_report = date_end

def ______________INPUT___________________():
    pass

def ______________MUTUAL___________________():
    pass

def fill_cmb_users_with_rules(cmb:CQT.QtWidgets.QComboBox):
    list_users_refs = [_.ref_user for _ in  DTCLS.module_repots_of_personal.user_report_rules.rules]
    list_names = [f"{DTCLS.app_self.DICT_EMPLOEE_FULL_WITH_DEL_BY_REF[_]['ФИО']}({DTCLS.app_self.DICT_EMPLOEE_FULL_WITH_DEL_BY_REF[_]['Должность']})"
                  for _ in list_users_refs]
    CQT.fill_list_combobx(DTCLS.app_self,cmb,list_names,list_data=list_users_refs,first_void=True)

def clck_user():
    tbl = DTCLS.app_self.ui.tbl_report_c
    row = CQT.get_dict_line_form_tbl(tbl)
    if not row:
        return
    if DTCLS.module_repots_of_personal.regime == Regimes.settings:
        tbl_details = DTCLS.app_self.ui.tbl_report_add
        tbl_details_f = DTCLS.app_self.ui.tbl_report_add_filtr
        events = Events()
        events.load_events(row['ID_ФизЛица'])
        fill_details_by_user(row['ID_ФизЛица'],tbl_details,tbl_details_f)


def dbl_clck_user():
    tbl = DTCLS.app_self.ui.tbl_report_c
    row = CQT.get_dict_line_form_tbl(tbl)

    if not row:
        return
    if DTCLS.module_repots_of_personal.regime == Regimes.events:
        tbl_details = DTCLS.app_self.ui.tbl_report_add
        tbl_details_f = DTCLS.app_self.ui.tbl_report_add_filtr
        t = CQT.TableContext(tbl_details_f)
        t.get_row(0).set_value('Название',row['Название'])
        CQT.apply_filtr_c(DTCLS.app_self,tbl_details_f,tbl_details)

def ______________SETTINGS___________________():
    pass


def load_pers_rules():
    DTCLS.module_repots_of_personal.regime = Regimes.settings
    ui = DTCLS.app_self.ui
    ui.bnt_glsv_append.setHidden(True)
    ui.bnt_glsv_add_rule.setHidden(False)
    ui.bnt_glsv_edit_rule.setHidden(False)
    DTCLS.module_repots_of_personal.creator_user = CMS.Emploee_usr(F.user_full_namre(),CFG.Config.project.db_users)
    tbl = DTCLS.app_self.ui.tbl_report_c
    list_empl = [ {
        'ФИО':k,
       'Должность':_['Должность'],
       'Подразделение':_['Подразделение'],
        'ID_ФизЛица':_['ID_ФизЛица'],
                   } for k, _ in DTCLS.app_self.DICT_EMPLOEE_FULL.items()
                  if _['Компания'] == CFG.Config.place.Имя]
    obj_rules =  Rules()
    obj_rules.load_rules()

    for usr in list_empl:
        msg  = calc_msg_rules(usr['ID_ФизЛица'])

        usr['Правила'] = msg

    CQT.fill_wtabl(list_empl,tbl,selectionMode='SingleSelection',selectionBehavior='SelectRows')
    nf = CQT.nums_col_by_name_dict(tbl)
    tbl.setColumnHidden(nf['ID_ФизЛица'],True)
    CMS.fill_filtr_c(DTCLS.app_self,DTCLS.app_self.ui.tbl_report_c_filtr,tbl)


def clck_tbl_report_add():
    if DTCLS.module_repots_of_personal.regime == Regimes.settings:
        ui = DTCLS.app_self.ui
        tbl = ui.tbl_report_add
        row = CQT.get_dict_line_form_tbl(tbl)
        ref_creator = row['ref_creator']
        if ref_creator == DTCLS.module_repots_of_personal.creator_user.ID_ФизЛица:
            ui.bnt_glsv_edit_rule.setEnabled(True)
        else:
            ui.bnt_glsv_edit_rule.setEnabled(False)


def fill_details_by_user(uid:str,tbl_details,tbl_details_f):

    tbl_report_add_summ =  DTCLS.app_self.ui.tbl_report_add_summ

    tbl_report_add_summ.setHidden(True)

    rules = DTCLS.module_repots_of_personal.user_report_rules.find(uid)
    CQT.clear_tbl(tbl_details)
    for rule in rules:
        rule.calc_status()
    templ = [{
        'id':_.id,
        'early':_.is_early,
        'Название':_.name,
        'ref_creator':_.ref_creator,
        'Создатель':_.creator_fio(),
        'Период':_.period.name,
        'Частота':_.count_by_period,
        'Дата начала':_.start_date.ru_notation(),
        'Статус': _.state.to_str(),
        'Описание':_.description,
        'Документы':[{
                        'Расширение':_d.file_extension,
                        'Название': _d.name,
                       } for _d in _.doc_types],

              } for _ in rules]
    if not templ:
        return
    CQT.fill_wtabl(templ,tbl_details,ogr_maxshir_kol=500,styleSheet=CQT.MES_CSS)
    t = CQT.TableContext(tbl_details)
    for row in t.rows():
        if F.is_bool(row.value('early')):
            CQT.set_font_color_wtab_c(t.tbl,row.i,row.nf['Дата начала'],122,55,55)

    if tbl_details.rowCount():
        tbl_details.hideColumn(t.nf['id'])
        tbl_details.hideColumn(t.nf['ref_creator'])
        tbl_details.hideColumn(t.nf['early'])
    CMS.fill_filtr_c(DTCLS.app_self, tbl_details_f, tbl_details)

@CQT.onerror
def bnt_glsv_edit_rule(*args):
    edit_rule()
@CQT.onerror
def bnt_glsv_add_rule(*args):
    add_rule()


def ______________EVENTS___________________():
    pass

def fill_events_by_user(uid:str):
    tbl =  DTCLS.app_self.ui.tbl_report_add
    tbl_f =  DTCLS.app_self.ui.tbl_report_add_filtr

    tbl_rules =  DTCLS.app_self.ui.tbl_report_c
    tbl_rules_f =  DTCLS.app_self.ui.tbl_report_c_filtr

    tbl_report_add_summ =  DTCLS.app_self.ui.tbl_report_add_summ
    tbl_report_add_summ.setHidden(True)
    events = Events()
    events.load_events(uid)
    templ = events.gen_template()

    CQT.fill_wtabl(templ,tbl,ogr_maxshir_kol=500,styleSheet=CQT.MES_CSS)

    t = CQT.TableContext(tbl)

    def fnc_show_file(lbl, app_self, i, j):
        row = t.current_row()
        link = row.value('link')
        run_doc(link)

    if tbl.rowCount():
        dev = CFG.Config.user_config.is_developer
        if not dev:
            tbl_rules.hideColumn(t.nf['id'])
            tbl_rules.hideColumn(t.nf['link'])

    for row in t.rows():
        if row.value('link'):
            row.set_value('Файл',CEMOJ.EmojiMain.ДокументыДанные.document.symbol)
            widg = CQT.add_interactive_label(tbl, row.i, t.nf['Файл'], row.value('Файл'), parent_self=DTCLS.app_self,grab_style_from_cell=True)
            widg.add_button(CEMOJ.EmojiMain.ПоказателиМетрики.eye.symbol, 'Открыть',
                            fnc_show_file,
                            cell_val=None, )
    CMS.fill_filtr_c(DTCLS.app_self, tbl_f, tbl)

def load_pers_events():
    DTM = DTCLS.module_repots_of_personal
    DTM.regime = Regimes.events
    DTCLS.module_repots_of_personal.creator_user = CMS.Emploee_usr(F.user_full_namre(), CFG.Config.project.db_users)
    DTCLS.app_self.ui.bnt_glsv_append.setHidden(False)
    DTCLS.app_self.ui.bnt_glsv_add_rule.setHidden(True)
    DTCLS.app_self.ui.bnt_glsv_edit_rule.setHidden(True)
    apply_current_user()
    recalc_and_fill_tbls()
def recalc_and_fill_tbls():
    DTM = DTCLS.module_repots_of_personal
    tbl_details = DTCLS.app_self.ui.tbl_report_c
    tbl_details_f = DTCLS.app_self.ui.tbl_report_c_filtr
    fill_events_by_user(DTM.current_user.ID_ФизЛица)
    fill_details_by_user(DTM.current_user.ID_ФизЛица,tbl_details,tbl_details_f)


@CQT.onerror
def bnt_glsv_append(*args):
    add_event()

def ______________REPORT___________________():
    pass

def load_pers_report():
    DTM = DTCLS.module_repots_of_personal
    DTM.regime = Regimes.report
    DTCLS.module_repots_of_personal.creator_user = CMS.Emploee_usr(F.user_full_namre(),CFG.Config.project.db_users)
    ui = DTCLS.app_self.ui
    tbl = ui.tbl_report_c
    tblf = ui.tbl_report_c_filtr
    ui.bnt_glsv_append.setHidden(True)
    ui.bnt_glsv_add_rule.setHidden(True)
    ui.bnt_glsv_edit_rule.setHidden(True)
    ui.fr_addition_tbl.setHidden(True)
    start_te = ui.le_start_of_period.text()
    end_te = ui.le_end_of_period.text()
    apply_current_user()
    events = Events()
    events.load_events(DTM.current_user.ID_ФизЛица)

    rules = DTM.user_report_rules
    list_rules = rules.find(DTM.current_user.ID_ФизЛица,date_end=DTM.date_end_report)

    diagramm = rules.generate_diagramm(events,list_rules)
    with CQT.table_updating(tbl):
        CQT.fill_wtabl(diagramm,tbl,styleSheet=CQT.MES_EDIT_CSS)
        t_main = CQT.TableContext(tbl)
        def fnc_show_file(lbl,app_self,i,j,tbl):
            t = CQT.TableContext(tbl)
            row = t.get_row(i)
            link = row.value('Документ')
            run_doc(link)
        def fnc_approve(lbl:CQT.InteractiveLabelInstance,app_self,i,j,tbl:CQT.QtWidgets.QTableWidget):
            t = CQT.TableContext(tbl)
            row = t.get_row(i)
            id = int(row.value('event_id'))
            event = Events().load_event(id)
            msg = row.value('Замечание').strip()
            event.set_approved(msg)
            row.set_editable('Замечание',False)
            row.set_value('Утвержден',event.date_approval.ru_notation())
            lbl.remove()

        for row_main in t_main.rows():
            tbl_sub = row_main.get_sub_table('Документы')
            if tbl_sub:
                t = CQT.TableContext(tbl_sub)
                for row in t.rows():
                    if row.value('Документ'):
                        row.item('Документ').background().color().red()
                        row.item('Утвержден').background().color().rgba()
                        widg = CQT.add_interactive_label(tbl_sub, row.i, t.nf['Документ'], CEMOJ.EmojiMain.ДокументыДанные.document.symbol,
                                                         parent_self=DTCLS.app_self,grab_style_from_cell=True)
                        widg.add_button(CEMOJ.EmojiMain.ПоказателиМетрики.eye.symbol, 'Открыть',
                                        fnc_show_file,
                                        cell_val=tbl_sub, )
                        if row_main.value('ref_creator') == DTM.creator_user.ID_ФизЛица:

                            if not row.value('Утвержден'):
                                widg = CQT.add_interactive_label(tbl_sub, row.i, t.nf['Утвержден'],
                                                                 '',
                                                                 parent_self=DTCLS.app_self,grab_style_from_cell=True)
                                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.success_tin.symbol, 'Утвердить',
                                                fnc_approve,
                                                cell_val=tbl_sub)
                                row.set_editable('Замечание',True)
                    t.hide('event_id')

    if diagramm:
        t_main.hide('rule_id')
        t_main.hide('period_priority')
        t_main.hide('ref_creator')
        t_main.hide('state')

    CMS.fill_filtr_c(DTCLS.app_self,tblf,tbl)


def __END_INPUT___________________():
    pass

def run_doc(link:str):
    ext = F.keep_extention_c(link)
    file_data = F.file_into_blob(link)
    tmp_win_dir = F.save_tmp_win_dir_file(file_data, extention=ext)
    F.run_file_c(tmp_win_dir)

def apply_current_user():
    uid_user = DTCLS.app_self.ui.cmb_addit_sort_c_report.currentData(CQT.Qt.UserRole)
    if uid_user is None:
        CQT.blink_obj_c(DTCLS.app_self,1,DTCLS.app_self.ui.cmb_addit_sort_c_report,f'Не выбран пользователь',)
        return
    DTCLS.module_repots_of_personal.current_user = CMS.Emploee_usr(uid_user,CFG.Config.project.db_users)

def add_rule():
    tbl = DTCLS.app_self.ui.tbl_report_c
    row = CQT.get_dict_line_form_tbl(tbl)

    if not row:
        return
    handling_rule(row['ID_ФизЛица'])
def handling_rule(user_id:str,id_rule:int|None =None):
    tbl = DTCLS.app_self.ui.tbl_report_c
    show_form(user_id,id_rule)
    msg  = calc_msg_rules(user_id)
    CQT.TableContext(tbl).set_value(tbl.currentRow(), 'Правила', msg)

def calc_msg_rules(user_id):
    rules = DTCLS.module_repots_of_personal.user_report_rules.find(user_id)
    if not rules:
        msg = ''
    else:
        count_rules = len(rules)
        msg  = f'{count_rules}шт - ({"); (".join([_.title_rule() for _ in rules])})'
    return msg



def edit_rule():
    tbl = DTCLS.app_self.ui.tbl_report_c
    tbl_sub = DTCLS.app_self.ui.tbl_report_add
    row = CQT.get_dict_line_form_tbl(tbl)

    if not row:
        return

    row_sub = CQT.get_dict_line_form_tbl(tbl_sub)
    if not row_sub:
        id_rule = select_rule(row['ID_ФизЛица'])
    else:
        id_rule = int(row_sub['id'])

    if id_rule is None:
        return
    rule = DTCLS.module_repots_of_personal.user_report_rules.get_rule(id_rule)
    if rule.ref_creator != DTCLS.module_repots_of_personal.creator_user.ID_ФизЛица:
        CQT.msgbox(f'Нет доступа')
        return
    handling_rule(row['ID_ФизЛица'], id_rule)


def add_event():
    tbl_sub = DTCLS.app_self.ui.tbl_report_c
    row_sub = CQT.get_dict_line_form_tbl(tbl_sub)
    if not row_sub:
        CQT.msgbox(f'Не выбрано правило')
        return
    else:
        id_rule = int(row_sub['id'])
    if id_rule is None:
        return

    rule = DTCLS.module_repots_of_personal.user_report_rules.get_rule(id_rule)

    dict_event = event_handler(rule)
    if not dict_event:
        return

    rule_doc_id = DTCLS.module_repots_of_personal.user_report_rules.get_id_doc_type(rule.id,int(dict_event['doc_type']))
    if rule_doc_id is None:
        CQT.msgbox(f'Ошибка обработки данных (rule_doc_id is None)')
        return

    event = DTCLS.module_repots_of_personal.current_user_events.add_new_event(rule_doc_id,
                           dict_event['link'],
                           dict_event['message'])
    if event is None:
        return
    if event.rule.id_chat_24:
        event.send_into_b24(f'chat{event.rule.id_chat_24}')
    recalc_and_fill_tbls()


def event_handler(rule)->dict|None:
    def fnc_oform(tbl: CQT.QtWidgets.QTableWidget):
        t = CQT.TableContext(tbl)

        def fnc_cmb_select(val:Doc_type,i,j):
            row_link = t.find_row({'Name':'link'},first=True)
            row_link.set_value('Значение','')
            lbl = CQT.InteractiveLabelInstance.get_interactive_label_from_cell(t.tbl,row_link.i,t.nf['Значение'])
            lbl.setText('')
            if val is None:
                return
            tbl.item(i,j).setText(str(val.id))


        for row in t.rows():
            if row.value('Name') == 'doc_type':
                CQT.add_combobox('',tbl,row.i,t.nf['Значение'],[_.title() for _ in rule.doc_types],
                                 True,fnc_cmb_select,list_data=[_ for _ in rule.doc_types],
                                 return_data=True)
            if row.value('Name') == 'message':
                row.set_editable('Значение')
                row.set_height(200)
            if row.value('Name') == 'link':
                def fnc_select_file_link(lbl:CQT.InteractiveLabelInstance,app_self,i,j,cell_val):
                    row = t.find_row({'Name':'doc_type'})
                    if not row:
                        return
                    row = row[0]
                    id_type = row.value('Значение')
                    if id_type == '':
                        CQT.msgbox(f'Не выбран Тип')
                        return
                    doc_type_obj = Doc_types().get_doc_type(int(id_type))
                    list_ext = doc_type_obj.file_extension.split(Rules.SEP)

                    patf = CQT.f_dialog_name(DTCLS.app_self,'Выбор документа',putt= F.put_po_umolch(),
                                             filtr= '*.' + ';*.'.join(list_ext))
                    if patf == '.':
                        return

                    row_link = t.get_row(i)
                    row_link.set_value('Значение',patf)
                    lbl.set_text(patf)

                widg = CQT.add_interactive_label(tbl, row.i, t.nf['Значение'], row.value('Значение'),
                                                 parent_self=DTCLS.app_self)
                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбрать',
                                fnc_select_file_link,
                                cell_val=tbl, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                      'icons', 'btn_select']))


        tbl.setColumnWidth(t.nf['Значение'],299)
        dev = False
        if CFG.Config.user_config.is_developer:
            dev = True
        if not dev:
            t.tbl.setColumnHidden(t.nf['Name'],True)


    def fnc_check_btn(btn, dialog, tbl: CQT.QtWidgets.QTableWidget):
        if btn.text() == 'Ввод':
            t = CQT.TableContext(tbl)
            for row in t.rows():
                if row.value('Name') == 'doc_type':
                    if row.value('Значение') == '':
                        CQT.msgbox(f"Не выбран Tип")
                        return
                if row.value('Name') == 'link':
                    if row.value('Значение') == '':
                        CQT.msgbox(f"Не выбран Файл")
                        return
                if row.value('Name') == 'message':
                    if row.value('Значение').strip() == '':
                        CQT.msgbox(f"Нет Описания")
                        return

            dialog.accept()
        else:
            dialog.reject()
            return

    def fnc_get_data(data):
        data = {_['Name']: _['Значение'] for _ in data}
        data['message'] = data['message'].strip()
        return data

    templ = Event.get_template()
    rez = CQT.msgboxg_get_table(DTCLS.app_self, 'Добавление события', templ, func_oform_tbl=fnc_oform,
                          not_standart_close=True, func_btn0=fnc_check_btn,func_validate=fnc_get_data)
    if not rez:
        return
    return rez




def select_rule(user_id:str)->int|None:
    rules = DTCLS.module_repots_of_personal.user_report_rules.find(user_id,DTCLS.module_repots_of_personal.creator_user.ID_ФизЛица)
    if not rules:
        return
    id_rule = None
    if len(rules)>1:
        templ = [{'id':_.id, 'Правило': _.title_rule()} for _ in rules]
        result = CQT.msgboxg_get_table(DTCLS.app_self,'Выбор правила',templ,'Выбор',styleSheet=CQT.MES_CSS,
                              selectRows=True,selection_from_tbl=True,SelectionMode='SingleSelection')
        if not result:
            return

        result = result[0]
        id_rule = int(result['id'])
    else:
        id_rule = rules[0].id
    return id_rule



def show_form(user_id:str,id_rule:int|None =None):
    fl_new = False
    if id_rule is None:
        fl_new = True
    user = DTCLS.app_self.DICT_EMPLOEE_FULL_WITH_DEL_BY_REF[user_id]
    if fl_new:
        msg = f'Новое правило'
        rule = Rule()
        rule.ref_user = user_id

    else:
        rule = DTCLS.module_repots_of_personal.user_report_rules.get_rule(id_rule)
        msg = f'Правка правила'

    template = rule.get_template()

    def fnc_check(btn, dialog, tbl:CQT.QtWidgets.QTableWidget):
        if btn.text() == 'Завершить':
            for row in CQT.TableContext(tbl).rows():
                val = row.value('Значение').strip()
                if row.value('Параметр') in ('Название','Пользователь','Типы документов','Период'):
                    if val == '':
                        CQT.msgbox(f'В строке {row.i+1} не указано значение' )
                        return
                    if Rules.SEP in val:
                        CQT.msgbox(f'Недопустимый символ "{Rules.SEP}" в строке {row.i+1}')
                if row.value('Параметр') == 'Кол-во за период':
                    if val == '' or val == 0:
                        CQT.msgbox(f'В строке {row.i + 1} не указано значение')
                        return
                    if not F.is_numeric(val):
                        CQT.msgbox(f'В строке {row.i + 1} не число')
                        return
                if row.value('Name') == 'id_chat_24':
                    if val != '' and not F.is_numeric(val):
                        CQT.msgbox(f'В строке {row.i + 1} не число')
                        return
            dialog.accept()
        else:
            dialog.reject()
            return
    def fnc_oform(tbl:CQT.QtWidgets.QTableWidget):
        def fnc_select_period(period:Period, r,c):
            if period is None:
                val = ''
            else:
                val = str(period.id)
            tbl.item(r,c).setText(val)

        nf_val = 1
        for i  in range(tbl.rowCount()):
            row:dict = CQT.get_dict_line_form_tbl(tbl,i)
            if row['Name'] in  ('name','count_by_period'):
                CQT.set_cell_editable(tbl,i,nf_val,True)
            if row['Name'] == 'period':
                list_periods = Periods().list_periods
                id_period = tbl.item(i,nf_val).text()
                if id_period:
                    id_period = Periods().get_period(int(id_period))
                    if id_period is not None:
                        id_period = id_period.name
                else:
                    id_period = None
                CQT.add_combobox('',tbl,i,nf_val,[_.name for _ in list_periods],
                                 list_data=list_periods,return_data=True,conn_func=fnc_select_period,current_text=id_period)

            if row['Name'] == 'doc_types':

                @CQT.onerror
                def item_txt_into_lbl(tbl,i,j,lbl):
                    str_ids = tbl.item(i, j).text()
                    ids = str_ids.split(Rules.SEP)
                    new_tupes_names = Rules.SEP.join([Doc_types.get_doc_type(int(_)).name for _ in ids if F.is_numeric(_)])
                    lbl.set_text(new_tupes_names, True)

                def fnc_select_doc_types(lbl,app_self,i,j):
                    def fnc_oform_doc_type(tbl:CQT.QtWidgets.QTableWidget):
                        nf = CQT.nums_col_by_name_dict(tbl)
                        dev = False
                        if CFG.Config.user_config.is_developer:
                            dev = True
                        if not dev:
                            pass


                    list_doc_types = dataClass.load_user_report_doc_types()
                    doc = CQT.msgboxg_get_table(DTCLS.app_self, msg, list_doc_types, 'Выбор',
                                          WindowTitle=f'Тип документа', func_oform_tbl=fnc_oform_doc_type,
                                          show_filtr=False,selectRows=True,selection_from_tbl=True,
                                                aliases_header={'id':'N','name':'Названеие','file_extension':'Расширение'}
                                          )
                    if not doc:
                        return

                    types_doc =[_['id'] for _ in doc]
                    old_txt = tbl.item(i, j).text()
                    new_txt = []
                    if old_txt:
                        new_txt = old_txt.split(Rules.SEP)
                    for typed_doc in types_doc:
                        if typed_doc not in new_txt:
                            new_txt.append(typed_doc)
                    tbl.item(i,j).setText(Rules.SEP.join(new_txt))
                    item_txt_into_lbl(tbl,i,j,lbl)

                def fnc_create_doc_types(lbl,app_self,i,j):
                    def fnc_oform_create_doc_type(tbl:CQT.QtWidgets.QTableWidget):
                        def fnc_select_file_extension(lbl:CQT.InteractiveLabelInstance,app_self,i,j):
                            def fnc_oform_select_file_extension(tbl):
                                pass

                            list_file_extension = ['*','doc','docx','pdf','xlsx','xls','txt','rar','zip']
                            file_extension = CQT.msgboxg_get_table(DTCLS.app_self, msg,
                                                                   [{'Расширение':_} for _ in list_file_extension] ,
                                                                   'Выбор',
                                                        WindowTitle=f'Тип документа(или несколько)',
                                                                   func_oform_tbl=fnc_oform_select_file_extension,
                                                        show_filtr=False,SelectionMode='MultiSelection'
                                                        )
                            if not file_extension:
                                return

                            file_extensions = Rules.SEP.join([_['Расширение'] for _ in file_extension])
                            tbl.item(i, j).setText(file_extensions)
                            lbl.set_text(file_extensions,True)

                        def fnc_clear_file_extension(lbl,app_self,i,j):
                            types_doc = tbl.item(i,j).text().split(Rules.SEP)
                            if len(types_doc):
                                tbl.item(i, j).setText(Rules.SEP.join(types_doc[:-1]))
                            lbl.set_text(tbl.item(i, j).text(), True)

                        nf_val = 1
                        for i in range(tbl.rowCount()):
                            row = CQT.get_dict_line_form_tbl(tbl, i)
                            if row['Name'] in ('name'):
                                CQT.set_cell_editable(tbl, i, nf_val, True)
                            if row['Name'] == 'file_extension':
                                widg = CQT.add_interactive_label(tbl, i, nf_val, tbl.item(i, nf_val).text(),
                                                                 parent_self=DTCLS.app_self)
                                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбрать',
                                                fnc_select_file_extension,
                                                cell_val=None, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                                      'icons', 'btn_select']))

                                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol, 'Очистить',
                                                fnc_clear_file_extension,
                                                cell_val=None)

                            nf = CQT.nums_col_by_name_dict(tbl)
                            dev = False
                            if CFG.Config.user_config.is_developer:
                                dev = True
                            if not dev:
                                tbl.setColumnHidden(nf['Name'], True)
                            pass

                    def fnc_check_new_doc_type(btn, dialog, tbl:CQT.QtWidgets.QTableWidget):
                        if btn.text() == 'Создать':
                            t = CQT.TableContext(tbl)
                            ext_row = t.find_row({'Name':'file_extension'})[0]
                            if ext_row.value('Значение') == "":
                                CQT.msgbox(f'Не выбрано расширение, создание не возможно')
                                return
                            name_row = t.find_row({'Name':'name'})[0]
                            if Rules.SEP in name_row.value('Значение'):
                                CQT.msgbox(f'Недопустимый символ "{Rules.SEP}" в названии, создание не возможно')
                                return
                            dialog.accept()
                        else:
                            dialog.reject()

                    def fnc_get_data(data):
                        data = {_['Name']:_['Значение'] for _ in data}
                        return data
                    doc = CQT.msgboxg_get_table(DTCLS.app_self, msg, Doc_type.get_template(), 'Создать',
                                                WindowTitle=f'Тип документа', func_oform_tbl=fnc_oform_create_doc_type,
                                                show_filtr=False,func_validate=fnc_get_data, not_standart_close=True,func_btn0=fnc_check_new_doc_type
                                                )
                    if not doc:
                        return
                    name_doc_type = doc['name']
                    file_extension = doc['file_extension']
                    new_doc = Doc_types.add_new(name_doc_type,file_extension)
                    id = new_doc.id
                    old_txt = tbl.item(i,j).text()
                    if old_txt:
                        new_txt = old_txt.split(Rules.SEP)
                    else:
                        new_txt = []
                    new_txt.append(str(id))
                    tbl.item(i, j).setText(Rules.SEP.join(new_txt))
                    item_txt_into_lbl(tbl,i,j,lbl)

                def fnc_clear_doc_types(lbl,app_self,i,j):
                    types_doc = tbl.item(i,j).text().split(Rules.SEP)
                    if len(types_doc):
                        tbl.item(i, j).setText(Rules.SEP.join(types_doc[:-1]))
                    item_txt_into_lbl(tbl,i,j,lbl)

                text = tbl.item(i, nf_val).text()
                new_tupes_names = ''
                if text:
                    new_tupes_names = Rules.SEP.join(
                        [Doc_types.get_doc_type(int(_)).name for _ in tbl.item(i, nf_val).text().split(Rules.SEP)])
                widg = CQT.add_interactive_label(tbl, i, nf_val, new_tupes_names, parent_self=DTCLS.app_self)
                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбрать тип',
                                fnc_select_doc_types,
                                cell_val=None,img_path=  F.sep().join([F.path_to_execut_file_c(),
                                                                              'icons','btn_select']) )
                widg.add_button(CEMOJ.EmojiMain.ДокументыДанные.archive.symbol, 'Создать тип',
                                fnc_create_doc_types,
                                cell_val=None,img_path=  F.sep().join([F.path_to_execut_file_c(),
                                                                              'icons','btn_create_doc']))
                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol, 'Очистить',
                                fnc_clear_doc_types,
                                cell_val=None)

            if row['Name'] == 'start_date':

                def fnc_select_start_date(lbl,app_self,i,j):
                    data_date = CQT.get_data_dialog_choose(DTCLS.app_self,'Выбрать дату начала',start_date=F.now(''),
                                                      format_dates="%Y-%m-%d",info_point_size=14)
                    if not data_date:
                        return
                    date = data_date[1]['date_from']
                    tbl.item(i, j).setText(date)
                    lbl.set_text(Report_date.into_ru_notation(date), True)
                text = ''
                if tbl.item(i, nf_val).text():
                    text = Report_date.into_ru_notation(tbl.item(i, nf_val).text())
                widg = CQT.add_interactive_label(tbl, i, nf_val, text, parent_self=DTCLS.app_self)
                widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.ellipsis.symbol, 'Выбрать дату',
                                fnc_select_start_date,
                                cell_val=None, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                      'icons', 'btn_select']))

            if row['Name'] == 'description':
                tbl.setRowHeight(i,200)
                CQT.set_cell_editable(tbl,i,nf_val,True)
            if row['Name'] == 'id_chat_24':
                CQT.set_cell_editable(tbl, i, nf_val, True)

        nf = CQT.nums_col_by_name_dict(tbl)
        dev = False
        if CFG.Config.user_config.is_developer:
            dev = True
        if not dev:
            tbl.setColumnHidden(nf['Name'], True)
            rows = CQT.TableContext(tbl).find_row({'Параметр': ('Пользователь','УИД')})
            for row_obj in rows:
                row_obj.hide()

        pass
    def fnc_get_data(data):
        data = {_['Name']: _['Значение'] for _ in data}
        data['description'] = data['description'].strip()
        data['id_chat_24'] = data['id_chat_24'].strip()
        return data
    rezult = CQT.msgboxg_get_table(DTCLS.app_self,msg,template,'Завершить',
                          WindowTitle=f'Правило для {user["ФИО"]}',func_oform_tbl=fnc_oform,show_filtr=False,
                                   not_standart_close=True,func_btn0=fnc_check,func_validate=fnc_get_data)
    if not rezult:
        return



    if fl_new:
        rule = Rules().new_rule(rezult)
    else:
        rule = DTCLS.module_repots_of_personal.user_report_rules.edit_rule(rezult)
    return




def fill_cmb_to_select_regime():

    cmb = DTCLS.app_self.ui.cmb_podrazdelenie
    cmb.clear()
    all_regimes = F.get_all_attrs_with_properties(Regimes)
    list_descr =    [
                           f'{v.icon} {v.description}' for v in all_regimes.values()
                           ]
    list_names =    [
                          v.name for v in all_regimes.values()
                           ]

    list_tooltips =    [
                          v.tooltip for v in all_regimes.values()
                           ]

    CQT.fill_list_combobx(DTCLS.app_self,cmb,
                          list_descr,
                          first_void=True,list_data=list_names,list_tooltip=list_tooltips)



