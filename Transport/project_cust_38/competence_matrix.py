from __future__ import annotations
from typing import TYPE_CHECKING
import copy

from project_cust_38 import b24_html_content_deployer
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_b24 as CB24
try:
    from dataClass import data_app as DTCLS
except:
    pass

if TYPE_CHECKING:
    from Sozdanie import mywindow
    

class Tbl_comp():
    def __init__(self,tbl:CQT.QtWidgets.QTableWidget):
        self.tbl = tbl

    def oform(self,data_comp,aliases,editable_mode:bool=False):
        tbl = self.tbl
        editable_columns = {}
        if editable_mode:
            editable_columns = [str(_) for _ in  DTCLS.obj_Competencies.DICT_COMPETENCE_SHABL.keys()]
        with (CQT.table_updating(tbl)):
            CQT.fill_wtabl(data_comp, tbl, set_editeble_col_nomera=editable_columns,
                           sortingEnabled=True,
                           selectionMode='SingleSelection',
                           selectionBehavior='SelectItems',
                           list_column_widths=CMS.load_column_widths(DTCLS.app_self, tbl),
                           height_row=64, aliases_header=aliases
                           )
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,'ID_ФизЛица'),True)
            for i in range(tbl.rowCount()):

                fl_even = False
                if i % 2 == 0:
                    fl_even = True

                for j in range(tbl.columnCount()):
                    header_name = tbl.horizontalHeaderItem(j).text()
                    if header_name in DTCLS.obj_Competencies.LIST_NAMES_COMP or header_name == DTCLS.obj_Competencies.RESULT_NAME:
                        val = tbl.item(i, j).text()
                        if F.is_numeric(val):
                            clr = CMS.Color_tbl(F.valm(val) * 25,dark_mode=True)
                            CQT.set_font_color_wtab_c(tbl, i, j, clr.r, clr.g, clr.b)
                        CQT.font_cell_size_format(tbl, i, j, 16)
                        if header_name in DTCLS.obj_Competencies.LIST_NAMES_COMP:
                            CQT.set_color_wtab_c(tbl, i, j, 242, 242, 242)

                    else:
                        CQT.set_color_wtab_c(tbl, i, j, 225, 225, 225)
                        CQT.font_cell_size_format(tbl, i, j, 12)


                    if fl_even:
                        CQT.add_color_wtab_c(tbl, i, j, 11, 0, 11)


class Competence():
    def __init__(self, data:dict):
        self.params_s_num:int|None = None
        self.params_snum_matrix:int|None = None
        self.params_name_competence:str|None = None
        self.params_nenable:bool|None = None
        self.matrix_s_num:int|None = None
        self.name_matrix:str|None = None
        self.Подразделения_id:int|None = None
        self.Подразделения_Наименование:str|None = None
        self.Подразделения_Подразделение_Key:str|None = None
        self.Подразделения_Организация_poki:int|None = None
        self.Подразделения_for_deletion:int|None = None
        self.user:User|None = None
        self.val:int|None = None

        for key in data.keys():
            exec(f'self.{key.replace(".", "_")} = data[key]')
            #print(f'self.{key.replace(".", "_")} = {data[key]}')
    def __str__(self):
        return f"""Competence: {self.params_name_competence} - {self.val}"""

class User():
    SET_MASTERS_DUTY = {'Старший мастер цеха'}
    ACCORDANCE_SCHEDULE = {'Сменный график №2 15.30-00.00 вечер/утро':{
        'Сменный график №2 15.30-00.00 вечер/утро',
        '0,4/16 часов в неделю/3 час.12 мин в день',
    'Пятидневка (8.00-16.30)'},
        'Сменный график №1 7.00-15.30 утро/вечер':{'Пятидневка (8.00-16.30)'}
    }
    def __init__(self,competencies:Competencies,row_data_dict:dict,data_users:list[dict]):

        self._data_users:list[dict] = data_users
        self.base_competencies:Competencies = competencies
        data_competence = copy.deepcopy(self.base_competencies.COMPETENCE_SHABL)
        comp_vals: list[dict] = self.base_competencies._comp_vals
        self.Пномер: int | None = None
        self.ФИО: str | None = None
        self.Должность: str | None = None
        self.Статус: str | None = None
        self.Подразделение: str | None = None
        self.Режим: str | None = None
        self.Компания: str | None = None
        self.ID_ФизЛица: str | None = None
        self.ВидЗанятости: str | None = None
        self.ДатаИзмененияДолжности: str | None = None
        self.login: str | None = None
        self.computer_name: str | None = None
        self.gender: str | None = None
        self.Пномер: str | None = None
        self.ФИО: str | None = None
        self.Должность: str | None = None
        self.Статус: str | None = None
        self.Подразделение: str | None = None
        self.Режим: str | None = None
        self.Компания: str | None = None
        self.ID_ФизЛица: str | None = None
        self.ВидЗанятости: str | None = None
        self.ДатаИзмененияДолжности: str | None = None
        self.login: str | None = None
        self.computer_name: str | None = None
        self.gender: str | None = None
        self.surname: str | None = None
        self.initials: str | None = None
        self.short_name: str | None = None

        for key in row_data_dict.keys():
            exec(f'self.{key.replace(".", "_")} = row_data_dict[key]')
            #print(f'self.{key.replace(".", "_")}:str|None = None')
        if self.ФИО:
            surname, name, second_name = self.ФИО.split()
            self.surname = surname
            self.initials = f'{name[0]}.{second_name[0]}.'
            self.short_name = f'{self.surname} {self.initials}'


        self.Режим = self.get_work_shift(self.Режим)
        self.Ответственный: str | None = self.calc_master()
        self.list_competencies: list[Competence] = []
        self.dict_competencies: dict[int,Competence] = dict()
        for item in data_competence:
            competence = Competence(item)
            self.list_competencies.append(competence)
            self.dict_competencies[competence.params_s_num] = competence


        for comp in self.list_competencies:
            comp.user = self
            comp.val = 0
            for item in comp_vals:
                if item['id_user'] == self.ID_ФизЛица and comp.params_s_num == item['id_comp']:
                    comp.val = item['value']
                    break

    def is_master(self)->bool:
        if self.Должность in self.SET_MASTERS_DUTY:
            return True
        return False
    def get_usr_by_id(self,id):
        for row in self._data_users:
            if row['ID_ФизЛица'] == id:
                return User(self.base_competencies,row,self._data_users)

    def get_vals(self,start_date,end_date):
        users_map = CSQ.custom_request_c(CFG.Config.project.db_users, f"""SELECT id_user FROM competence_vals
                LEFT JOIN ФизическоеЛица ON ФизическоеЛица.id == 
                WHERE "")""")


    def __str__(self):
        return f"""User: {self.ФИО} ({self.Должность}) - {self.calc_average()}"""

    @staticmethod
    def get_work_shift(schedule:str)->str|None:
        list_sch = schedule.split()
        if len(list_sch)>2:
            return ' '.join(list_sch[:3])


    def calc_master(self):
        list_masters = [_ for _ in self._data_users if
                   _['Подразделение'] == self.Подразделение
                   and _['Компания'] == self.Компания
                   and _['Должность'] in self.SET_MASTERS_DUTY
                   ]

        if len(list_masters) == 1:
            return list_masters[0]['ID_ФизЛица']

        for master in list_masters:
            if self.get_work_shift(master['Режим']) == self.Режим:
                return master['ID_ФизЛица']

    def set_new_val(self,new_val:int,name_comp:str):
        for comp in self.list_competencies:
            if comp.params_name_competence == name_comp:
                comp.val = new_val


    def gen_description_dict(self):
        master_name = ''
        master = self.get_usr_by_id(self.Ответственный)
        if master is not  None:
            master_name = f'{master.ФИО}\n{master.Должность}'
        return {
            'ФИО':F.split_text_optimal(self.ФИО),
            'ID_ФизЛица':self.ID_ФизЛица,
            'Должность':F.split_text_optimal(self.Должность),
            'Ответственный':master_name,
        }

    def calc_average(self):
        if not  len(self.list_competencies):
            return 0
        summ_val = sum([_.val for _ in self.list_competencies])
        return round(summ_val/len(self.list_competencies),2)
class Depatment():
    def __init__(self,depatment_ref:str):
        self.id: int | None = None
        self.Наименование: str | None = None
        self.Подразделение_Key: str | None = None
        self.Организация_poki: int | None = None
        self.for_deletion: int | None = None
        self.Организация_Key: str | None = None
        self.Организация_Имя: str | None = None
        self.matrix_s_num: int | None = None
        self.matrix_id_landing_b24:int | None = None
        self.matrix_id_landing_table_block_b24:int | None = None
        self.name_matrix: str | None = None
        data = CSQ.custom_request_c(CFG.Config.project.db_users, f"""SELECT 
                        Подразделения.id,
                        Подразделения.Наименование,
                        Подразделения.Подразделение_Key,
                        Подразделения.Организация_poki,
                        Подразделения.for_deletion,
                        places.Организация_Key,
                        places.Имя as Организация_Имя,
                        competence_matrix.s_num as matrix_s_num,
                        competence_matrix.name_matrix as name_matrix,
                        competence_matrix.id_landing_b24 AS matrix_id_landing_b24, 
                        competence_matrix.id_landing_table_block_b24 AS matrix_id_landing_table_block_b24
                        FROM Подразделения INNER JOIN places 
                        ON places.poki == Подразделения.Организация_poki,
                        competence_matrix 
                        ON competence_matrix.id_depatment_mes == Подразделения.id
                        
                         WHERE Подразделения.Подразделение_Key == "{depatment_ref}" 
                         and Подразделения.for_deletion = 0 """, rez_dict=True,one=True,
                                    attach_dbs=CFG.Config.project.db_naryad)
        for key in data.keys():
            exec(f'self.{key.replace(".", "_")} = data[key]')
            #print(f'self.{key.replace(".", "_")}:str|None = None')

    def __str__(self):
        return f"""Depatment: {self.Наименование} ({self.Организация_Имя})"""
class Competencies():
    ADDIT_INFO = f'''
    	Критерии оценки навыков работников с бальными оценками
        0	- работник не имеет навыка на данной операции				
        1	- работник начал осваивать операцию, владеет теорией				
        2	- работник способен рабовать самостоятельно, но нуждается в постоянном наблюдении				
        3	- работник самостоятельно выполняет операцию, работает в нужном качестве и количестве, без помощи наставника				
        4	- работник прошел полную подготовку, способен обучать других				
        '''
    RESULT_NAME = 'Итоговый\nбалл'
    def __init__(self,depatment_ref:str,tbl:Tbl_comp,tblf:CQT.QtWidgets.QTableWidget,editable_mode=False):
        if not F.is_unique_identifier(depatment_ref):
            raise TypeError(f'Competence depatment_ref not F.is_unique_identifier')
        self._tbl:Tbl_comp = tbl
        self._tblf:CQT.QtWidgets.QTableWidget = tblf
        self.editable_mode:bool = editable_mode
        self.depatment:Depatment = Depatment(depatment_ref)

        self.COMPETENCE_SHABL = CSQ.custom_request_c(CFG.Config.project.db_users, f"""SELECT 
        competence_params.s_num AS params_s_num, 
        competence_params.snum_matrix AS params_snum_matrix, 
        competence_params.name_competence AS params_name_competence, 
        competence_params.enable AS params_nenable, 
        competence_matrix.s_num AS matrix_s_num, 
        competence_matrix.id_depatment_mes AS matrix_id_depatment_mes, 
        competence_matrix.name_matrix AS name_matrix, 
        Подразделения.id AS Подразделения_id, 
        Подразделения.Наименование AS Подразделения_Наименование, 
        Подразделения.Подразделение_Key AS Подразделения_Подразделение_Key, 
        Подразделения.Организация_poki AS Подразделения_Организация_poki, 
        Подразделения.for_deletion AS Подразделения_for_deletion 
        FROM competence_params INNER JOIN 
        competence_matrix ON competence_matrix.s_num = competence_params.snum_matrix, 
        Подразделения ON  Подразделения.id = competence_matrix.id_depatment_mes 
         WHERE Подразделения.Подразделение_Key == "{self.depatment.Подразделение_Key}" AND 
        competence_params.enable = 1 """, rez_dict=True)

        self.LIST_NAMES_COMP = [v['params_name_competence'] for v in self.COMPETENCE_SHABL]
        self.DICT_COMPETENCE_SHABL:dict[int,Competence] = {v['params_s_num']: Competence(v)  for v in self.COMPETENCE_SHABL}
        

        data_users = CSQ.custom_request_c(CFG.Config.project.db_users,f"""SELECT * 
        FROM employee 
         WHERE Статус IN ('Работа',
            'Отсутствие по невыясненным причинам',
            'Болезнь',
            'Отпуск основной',
            'Командировка',
            'Отпуск по уходу за ребенком'
         )
          and Компания == "{self.depatment.Организация_Имя}"
            and Подразделение == "{self.depatment.Наименование}"
            """,rez_dict=True)
        self.list_users:list[User] = []
        self._comp_vals:list[dict] = self.load_vals_from_db()
        for item in data_users:

            user = User(self,item,data_users)
            if user.is_master():
                continue
            self.list_users.append(user)

        pass
    def __str__(self):
        return f"""Competencies: {self.depatment}({len(self.list_users)} users)"""

    def load_vals_from_db(self)->list[dict]: #26.12.25
        query = """
            SELECT *
            FROM (
              SELECT
                cv.*,
                ROW_NUMBER() OVER (
                  PARTITION BY id_comp, id_user
                  ORDER BY created_at DESC, s_num DESC
                ) AS rn
              FROM competence_vals AS cv
            )
            WHERE rn = 1;
        """
        return CSQ.custom_request_c(CFG.Config.project.db_users, query,rez_dict=True)

    def pull_vals_into_db(self)->tuple[bool,list,list]:
        def find_data(old_vals,id_user,id_comp):
            for row in old_vals:
                if row['id_user'] == id_user and row['id_comp'] == id_comp:
                    return row['value']

        def pull(list_add):
            vals_add = [[_['id_comp'], _['id_user'], _['value']] for _ in list_add]
            resp = CSQ.custom_request_c(CFG.Config.project.db_users,
                                        f"""INSERT OR REPLACE INTO competence_vals
                                                (id_comp, id_user, value)
                                        VALUES (?, ?, ?);""", list_of_lists_c=vals_add)

        fl_suc = False
        list_changes = []
        list_add = []
        old_vals: list[dict] = self.load_vals_from_db()
        for usr in self.list_users:
            id_user = usr.ID_ФизЛица
            name_user = f'{usr.short_name}\n({usr.Должность})'
            for comp in usr.list_competencies:
                id_comp = comp.params_s_num
                params_name_competence = comp.params_name_competence
                val = comp.val
                old_val = find_data(old_vals,id_user,id_comp)
                tmp_struct =  {
                            'id_comp':id_comp,
                            'params_name_competence':params_name_competence,
                            'id_user':id_user,
                            'name_user':name_user,
                            'value':val,
                            'old_val':old_val,
                        }

                if old_val is None:
                    if val > 0:
                        list_add.append(tmp_struct)
                else:
                    if old_val != val:
                        list_changes.append(tmp_struct)

        if list_changes:
            pull(list_changes)
            fl_suc = True
        if list_add:
            pull(list_add)
            fl_suc = True


        return fl_suc , list_changes, list_add

    def calc_output_export(self):
        data = self.calc_output(names_comp = True)
        return {
            'poki':self.depatment.Организация_poki,
                'company':self.depatment.Организация_Имя,
                'name_matrix':self.depatment.name_matrix,
                'depatment':self.depatment.Наименование,
            'tbl':data,'info':self.ADDIT_INFO}

    def calc_output(self,names_comp = False)->list[dict]:
        result = []
        for usr in self.list_users:
            tmp_row = usr.gen_description_dict()
            for s_num, comp in usr.dict_competencies.items():
                if names_comp:
                    tmp_row[comp.params_name_competence] = comp.val
                else:
                    tmp_row[comp.params_s_num] = comp.val
            tmp_row[self.RESULT_NAME] = usr.calc_average()
            result.append(tmp_row)
        result = F.sort_by_column_c(result,'Ответственный')
        return result

    def get_aliases_comps(self)->dict[int,str]:
        return {k:v.params_name_competence for k,v in self.DICT_COMPETENCE_SHABL.items()}


    def recalc_average(self,user_id:str):
        usr = self.get_usr(user_id)
        if usr is None:
            return
        usr.calc_average()
        self.refill()


    def refill(self):
        data_comp = self.calc_output()
        aliases = self.get_aliases_comps()
        self._tbl.oform(data_comp,aliases,editable_mode=self.editable_mode)
        CMS.fill_filtr_c(DTCLS.app_self, self._tblf, self._tbl.tbl)
 
        
    def get_usr(self,id:str)->User:
        for usr in self.list_users:
            if usr.ID_ФизЛица == id:
                return usr
@CQT.onerror
def fill_cmb_to_select_dep(cmb:CQT.QtWidgets.QComboBox,poki:int,selected_dep_name:str=None):
    depatments = CSQ.custom_request_c(CFG.Config.project.db_users, f"""
        SELECT * FROM Подразделения INNER JOIN competence_matrix 
         ON competence_matrix.id_depatment_mes = Подразделения.id 
         WHERE 
         Организация_poki == {poki}
            """, rez_dict=True)
    
    if not cmb.count():
        cmb.blockSignals(True)
        for dep in depatments:
            cmb.addItem(dep['Наименование'])
            cmb.setItemData(cmb.count() - 1, dep['Подразделение_Key'], CQT.Qt.UserRole)
            if selected_dep_name:
                if dep['Наименование'] == selected_dep_name:
                    cmb.setCurrentText(dep['Наименование'])
        cmb.blockSignals(False)

@CQT.onerror
def select_depatment_comp(self:mywindow,*args):
    load_tbl(self)


@CQT.onerror
def load_tbl(self:mywindow):
    ref_user = self.glob_ref_user
    if ref_user is None:
        tab = self.ui.tabWidget
        tab.blockSignals(True)
        tab.setCurrentIndex(CQT.number_table_by_name_c(tab,'Создание наряда'))
        tab.blockSignals(False)
        CQT.msgbox(f'Необходимо войти в программу')
        return

    empl_obj = CMS.Emploee_usr(ref_user, CFG.Config.project.db_users)
    DTCLS.empl_obj = empl_obj
    cmb = self.ui.cmb_select_depatment_comp
    poki = self.DICT_PLACES[empl_obj.Компания]['poki']
    fill_cmb_to_select_dep(cmb, poki, empl_obj.Подразделение)
    
    depatment = cmb.currentData(CQT.Qt.UserRole)

    tbl = Tbl_comp(self.ui.tbl_competence_users)
    comps = Competencies(depatment,tbl,DTCLS.app_self.ui.tbl_competence_users_filtr,editable_mode=True)
    DTCLS.obj_Competencies = comps
    comps.refill()

@CQT.onerror
def save_old_val(item:CQT.QtWidgets.QTableWidgetItem):
    DTCLS._old_val_cell =  item.text() if item else None

@CQT.onerror
def tbl_current_elem_itemActivated(self,item):
    if CQT.is_table_updating(item.tableWidget()):
        return
    save_old_val(item)
@CQT.onerror
def tbl_current_elem_cellEntered(self, i,j):
    if CQT.is_table_updating(self.ui.tbl_competence_users):
        return
    item: CQT.QtWidgets.QTableWidgetItem = self.ui.tbl_competence_users.item(i, j)
    save_old_val(item)
@CQT.onerror
def tbl_current_elem_itemChanged(self:mywindow, item):
    tbl = self.ui.tbl_competence_users
    if CQT.is_table_updating(tbl):
        return
    if item is None:
        return
    i, j = item.row(), item.column()
    new_value = int(item.text())
    name_field = tbl.horizontalHeaderItem(j).text()
    
    def check(name, val):
        if name in  DTCLS.obj_Competencies.LIST_NAMES_COMP:
            if F.is_numeric(val):
                val = F.valm(val)
                if val>=0 and val<=4:
                    return True
        return False

    if not check(name_field,new_value):
        with CQT.table_updating(tbl):
            item.setText(DTCLS._old_val_cell)
            return
    row = CQT.get_dict_line_form_tbl(tbl,i)
    
    DTCLS.obj_Competencies.get_usr(row['ID_ФизЛица']).set_new_val(new_value,name_field)
    DTCLS.obj_Competencies.recalc_average(row['ID_ФизЛица'])
    DTCLS._old_val_cell = None

@CQT.onerror
def reset_changes_competence(self:mywindow):
    load_tbl(self)

@CQT.onerror
def apply_changes_competence(self:mywindow):
    if not CQT.msgboxgYN(f'''Все изменения будут записаны в БД''',
                         "Продолжить","Отмена"):
        return
    obj_Comp = DTCLS.obj_Competencies
    suc, list_changes, list_adds = obj_Comp.pull_vals_into_db()
    if not suc:
        CQT.msgbox(f'Измененинй нет')
        return
    name_matrix = obj_Comp.depatment.name_matrix

    for item in list_adds:
        item['old_val'] = '-'
    list_changes = list_changes + list_adds
    list_for_b24_msg = [{'ФИОД':f"{_['name_user'][:23]}...",
                         'Имя': f'{_['params_name_competence'].replace('\n',' ')[:8]}...\n',
                         'Было': f'{_['old_val']}\n',
                         'Стало':f'{_['value']}\n',
                         } for _ in list_changes]#дата,вид изменения, фио у кого изменили и кто изменил


    CMS.send_tbl_b24_by_action(f'{name_matrix}\n{F.now("%d.%m.%Y %H:%M")} {DTCLS.empl_obj.ФИО}',
                               'Матрицы компетенций',
                               list_for_b24_msg)

    from project_cust_38 import b24_html_content_deployer
    import importlib
    importlib.reload(b24_html_content_deployer)
    data_export = obj_Comp.calc_output_export()

    cfg = b24_html_content_deployer.GeneratorConfig()
    # задаток на будущее, если появится необходимость подсвечивать оценки или задавать жестко цвета
    # cfg.score_highlight.enabled = True
    # cfg.score_highlight = b24_html_content_deployer.default_score_colors()
    renderer = b24_html_content_deployer.BitrixLandingMatrixRenderer(cfg)
    html = renderer.render(data_export)
    b24_html_deployer = CB24.HtmlContentDeployer()
    is_done = b24_html_deployer.pick_html_into_landing_block(
        html=html,
        matrix_id_landing_b24=obj_Comp.depatment.matrix_id_landing_b24,
        matrix_id_landing_table_block_b24=obj_Comp.depatment.matrix_id_landing_table_block_b24
    )
    if is_done:
        return CQT.msgbox('Матрица успешно опубликована в базе знаний компетенций')
    else:
        return CQT.msgbox('Не удалось опубликовать матрицу')

@CQT.onerror
def create_comp(self:mywindow):
    name_comp = self.ui.le_name_comp.text().strip()

    if CMS.user_access(CFG.Config.project.db_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    depart_name = DTCLS.obj_Competencies.depatment.Наименование
    matrix_id = DTCLS.obj_Competencies.depatment.matrix_s_num

    if len(name_comp) < 5:
        CQT.msgbox(f' компетенция\n"{name_comp}"\nкороткое название')
        return
    name_comp = F.split_text_optimal(name_comp,round(len(name_comp)/30))
    found = CSQ.custom_request_c(CFG.Config.project.db_users,f"""SELECT * FROM competence_params
     WHERE snum_matrix == {matrix_id} and name_competence == "{name_comp}";""",rez_dict=True)
    if found:
        CQT.msgbox(f'Компетенция\n"{name_comp}"\nуже существует')
        return

    if not CQT.msgboxgYN(f'''Будет создана новая компетенция\n"{name_comp}"\nдля {depart_name}''',
                         "Продолжить","Отмена"):
        return

    CSQ.custom_request_c(CFG.Config.project.db_users,f"""INSERT INTO competence_params
                              (snum_matrix, name_competence)
                              VALUES (?, ?);""",list_of_lists_c=[[matrix_id,name_comp]])
    self.ui.le_name_comp.setText('')
    reset_changes_competence(self)
    CQT.msgbox(f'Компетенция\n"{name_comp}"\nуспешно создана')

def show_info_comp(self:mywindow):
    CQT.msgbox(DTCLS.obj_Competencies.ADDIT_INFO)