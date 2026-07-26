import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS


def create_db(self):
    frase_tmp = """CREATE TABLE IF NOT EXISTS zamech(
           Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
           Проект_пу TEXT DEFAULT "",
           Отдел TEX DEFAULT "",
           Вопрос TEXT DEFAULT "",
           Дата_вопроса TEXT DEFAULT "",
           Код_проблемы TEXT DEFAULT "",
           Ответственный TEXT DEFAULT "",
           Дней_на_решение INTEGER DEFAULT (1),
           Дата_решения TEXT DEFAULT "",
           Примечание TEXT DEFAULT "");
        """
    CSQ.create_db_sql_c(self.db_selector,frase_tmp)

    frase_tmp = """CREATE TABLE IF NOT EXISTS projects(
           Пномер INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ON CONFLICT ROLLBACK,
           Проект_пу TEXT DEFAULT "",
           Примечание TEXT DEFAULT "");
        """
    CSQ.create_db_sql_c(self.db_selector,frase_tmp)

def load_table_db(self):
    self.selector_department = ("Производство",
"ПДО",
"Конструкторский отдел",
"Отдел Снабжения",
"Склад",
"Отдел главного технолога",
"Менеджеры проектов"
                              )
#self.DICT_EMPLOEE_RC

    if F.existence_file_c(self.db_selector) == False:
        create_db(self)

    if 'zamech' not in CSQ.get_list_of_tables_c(self.db_selector):
        create_db(self)
    if 'projects' not in CSQ.get_list_of_tables_c(self.db_selector):
        create_db(self)
    update_list_zamech(self)
    update_list_projects(self)

def edit_primech(self,row,column):
    if CQT.is_table_updating(self.ui.tbl_selector_proj_view):
        return
    current_primech = self.ui.tbl_selector_proj_view.item(row, CQT.num_col_by_name_c(self.ui.tbl_selector_proj_view,
                                                                                  'Примечание')).text()
    np = self.ui.tbl_selector_proj_view.item(row, CQT.num_col_by_name_c(self.ui.tbl_selector_proj_view,
                                                                      '№ проекта$№ в ERP:')).text()
    custom_request_c = f'''SELECT Примечание FROM projects WHERE Проект_пу = "{np}"'''
    rez = CSQ.custom_request_c(self.db_selector, custom_request_c, one=True,hat_c=True)
    if len(rez)>1:

        custom_request_c = f'''UPDATE projects
            SET (Примечание)
           = ("{current_primech}")
            WHERE Проект_пу == "{np}" ;'''
        CSQ.custom_request_c(self.db_selector, custom_request_c)
    else:
        custom_request_c = f'''INSERT INTO projects
                                      (Проект_пу, 
                   Примечание)
                                      VALUES (?, ?);'''
        CSQ.custom_request_c(self.db_selector, custom_request_c, list_of_lists_c=[[np,current_primech]])


def edit_zamech_from_view(self, row, column):
    nom_zam = self.ui.tbl_selector_proj_view_zamech.item(row, CQT.num_col_by_name_c(self.ui.tbl_selector_proj_view_zamech,
                                                                      'Пномер')).text()

    nk_zam = CQT.num_col_by_name_c(self.ui.tbl_selector, 'Пномер')
    list_zam = CQT.list_from_wtabl_c(self.ui.tbl_selector,hat_c=True)
    for i in range(len(list_zam)):
        if list_zam[i][nk_zam] == nom_zam:
            select_zamech(self,i-1,nk_zam)
    self.ui.tbl_selector.setCurrentCell(i-1,nk_zam)
    self.ui.tabWidget_5.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_5, 'Замечания'))

def add_new_zamech(self, row, column):
    if column == CQT.num_col_by_name_c(self.ui.tbl_selector_proj_view,
                                                                      'Примечание'):
        return
    np = self.ui.tbl_selector_proj_view.item(row, CQT.num_col_by_name_c(self.ui.tbl_selector_proj_view,
                                                                      '№ проекта$№ в ERP:')).text()
    self.ui.tabWidget_5.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_5, 'Замечания'))
    nk_np_py = CQT.num_col_by_name_c(self.ui.tbl_selector_add,'Проект_пу')
    self.ui.tbl_selector_add.cellWidget(0,nk_np_py).setCurrentText(np)
    self.ui.tbl_selector_add.item(0,nk_np_py).setText(np)

def select_zamech(self,row,column):
    row+=1
    list = CQT.list_from_wtabl_c(self.ui.tbl_selector,hat_c=True)
    rez = [list[0],list[row]]
    set_red = {
               F.num_col_by_name_in_hat_c(rez, 'Примечание')}
    CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_selector_edit, separ='', isp_hat_c=True, set_editeble_col_nomera=set_red)
    nk_data_resh = F.num_col_by_name_in_hat_c(rez,'Дата_решения')
    if rez[-1][nk_data_resh] == '':
        CQT.add_btn(self.ui.tbl_selector_edit,0,CQT.num_col_by_name_c(self.ui.tbl_selector_edit,'Дата_решения'),'РЕШЕНО',True,btn_resheno,self)

def selector_proj_view_itemSelection(self):
    row = self.ui.tbl_selector_proj_view.currentRow()
    np = self.ui.tbl_selector_proj_view.item(row,CQT.num_col_by_name_c(self.ui.tbl_selector_proj_view,'№ проекта$№ в ERP:')).text()
    list_zamech = CSQ.custom_request_c(self.db_selector, f'''SELECT * FROM zamech WHERE Проект_пу = "{np}"''', hat_c=True)
    CQT.fill_wtabl_old_c(self, list_zamech, self.ui.tbl_selector_proj_view_zamech, separ='', isp_hat_c=True)
    CMS.fill_filtr_c(self, self.ui.tbl_selector_proj_view_zamech_filtr, self.ui.tbl_selector_proj_view_zamech)

def update_list_projects(self):
    dict_primech = CSQ.custom_request_c(self.db_selector,f'''SELECT * FROM projects''',rez_dict=True)
    dict_primech = F.deploy_dict_c(dict_primech,'Проект_пу')
    rez_list = []
    for key in self.DICT_PROJECTS:
        tmp = list(self.DICT_PROJECTS[key].keys())
        tmp.append('Примечание')
        rez_list.append(tmp)
        break
    for key in self.DICT_PROJECTS:
        tmp = list(self.DICT_PROJECTS[key].values())
        if key in dict_primech:
            tmp.append(dict_primech[key]['Примечание'])
        else:
            tmp.append('')
        rez_list.append(tmp)
        #rez_list.append(list(self.DICT_PROJECTS[key].values()))
    set_red = {
               F.num_col_by_name_in_hat_c(rez_list, 'Примечание')}
    CQT.fill_wtabl_old_c(self, rez_list, self.ui.tbl_selector_proj_view, separ='', isp_hat_c=True, set_editeble_col_nomera=set_red,max_vis_row=25)
    CMS.fill_filtr_c(self, self.ui.tbl_selector_proj_view_filtr, self.ui.tbl_selector_proj_view)
    CMS.load_column_widths(self,self.ui.tbl_selector_proj_view)

def update_list_zamech(self):
    list = CSQ.custom_request_c(self.db_selector, '''SELECT * FROM zamech''', hat_c=True)
    CQT.fill_wtabl_old_c(self, list, self.ui.tbl_selector, separ='', isp_hat_c=True,max_vis_row=25)
    CMS.fill_filtr_c(self, self.ui.tbl_selector_filtr, self.ui.tbl_selector)
    nk_data_vopr = F.num_col_by_name_in_hat_c(list,'Дата_вопроса')
    nk_data_resh = F.num_col_by_name_in_hat_c(list, 'Дата_решения')
    nk_dney = F.num_col_by_name_in_hat_c(list, 'Дней_на_решение')
    for i, item in enumerate (list[1:]):
        data_vopr = F.strtodate(item[nk_data_vopr])
        dney = item[nk_dney]
        plan_data = F.date_add_days(data_vopr,dney,format_out='')
        if item[nk_data_resh] != "":
            data_resh = F.strtodate(item[nk_data_resh])
            if plan_data < data_resh:
                CQT.set_color_wtab_c(self.ui.tbl_selector,i, nk_data_resh , 250,200,200)
        else:
            if F.now('') > plan_data:
                CQT.set_color_wtab_c(self.ui.tbl_selector,i, nk_dney, 250, 200, 200)


def btn_resheno(self, row, col):
    self.ui.tbl_selector_edit.item(row,col).setText(F.now("%Y-%m-%d"))
    self.ui.tbl_selector_edit.cellWidget(row,col).setText(self.ui.tbl_selector_edit.item(row,col).text())

def select_responsible(self, text, row, col):
    current_user = text
    self.ui.tbl_selector_add.item(row,col).setText(text)

def select_project(self, text, row, col):
    current_project = text
    self.ui.tbl_selector_add.item(row,col).setText(text)
    #print(current_project)

def select_dept(self, text, row, col):
    current_dept = text
    self.ui.tbl_selector_add.item(row, col).setText(text)
    #print(current_dept)

def select_kod(self, text, row, col):
    current_kod = text
    self.ui.tbl_selector_add.item(row, col).setText(text)
    #print(current_kod)

def add_zamech(self):
    if CQT.msgboxgYN(f'Создать новую запись?') == False:
        return
    if check_row_before_add(self):
        list = CQT.list_from_wtabl_c(self.ui.tbl_selector_add, hat_c=True)
        list = F.delete_column(list,names_del=['Пномер'])
        custom_request_c = f'''INSERT INTO zamech
                              (Проект_пу, Отдел,
           Вопрос,
           Дата_вопроса,
           Код_проблемы,
           Ответственный,
            Дней_на_решение,
           Дата_решения,
           Примечание)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);'''
        CSQ.custom_request_c(self.db_selector,custom_request_c,list_of_lists_c=[list[-1]])
        update_list_zamech(self)


def edit_zamech(self):
    if CQT.msgboxgYN(f'Выполнить корректровку?') == False:
        return
    list = CQT.list_from_wtabl_c(self.ui.tbl_selector_edit, hat_c=True)
    dict_list = F.list_to_dict(list)[0]
    custom_request_c = f'''UPDATE zamech
    SET (Дата_решения, Примечание)
   = ("{dict_list['Дата_решения']}", "{dict_list['Примечание']}")
    WHERE Пномер == {int(dict_list['Пномер'])} ;'''
    CSQ.custom_request_c(self.db_selector,custom_request_c)
    update_list_zamech(self)


def check_row_before_add(self):
    list = CQT.list_from_wtabl_c(self.ui.tbl_selector_add,hat_c=True)
    dict_list = F.list_to_dict(list)[0]
    if dict_list['Дней_на_решение'] == "":
        CQT.msgbox(f'Дней_на_решение не может быть пусто')
        return False
    if F.is_numeric(dict_list['Дней_на_решение']) == False:
        CQT.msgbox(f'Дней_на_решение не может быть текст')
        return False
    if dict_list['Проект_пу'] == "":
        CQT.msgbox(f'Проект_пу не может быть пусто')
        return False
    if dict_list['Отдел'] == "":
        CQT.msgbox(f'Отдел не может быть пусто')
        return False
    if dict_list['Вопрос'] == "":
        CQT.msgbox(f'Вопрос не может быть пусто')
        return False
    if dict_list['Код_проблемы'] == "":
        CQT.msgbox(f'Код_проблемы не может быть пусто')
        return False
    if dict_list['Ответственный'] == "":
        CQT.msgbox(f'Ответственный не может быть пусто')
        return False
    return True

def load_dicts_for_selector(self):
    self.SET_selector_STATUS_PROJ = ("Формируется", "К производству", "Закрыт", "ТКП", "Приостановлено", "Удалить")
    self.SET_selector_PODRAZD = ("ОУП", "ОГК", "Снабжение", "ОГТ", "Склад", "ПДО", "Производство")
    self.DICT_selector_OSHIBKI = {1: 'сроки процедуры', 2: 'порядок процедуры', 3: 'пересортица', 4: 'ошибка в документации',
                       5: 'ошибка в эл.файлах', 6: 'ошибка в спецификациях', 7: 'ошибка в нормативах',
                       8: 'нетехнологичность', }

def load_table_add(self):
    list = CSQ.list_of_columns_c(self.db_selector,'zamech')

    tmp = [list,['' for _ in list]]

    list_projects = self.DICT_PROJECTS.keys()


    nk_data_vopr = F.num_col_by_name_in_hat_c(tmp,'Дата_вопроса')
    tmp[-1][nk_data_vopr] = F.now("%Y-%m-%d")

    set_red = {F.num_col_by_name_in_hat_c(tmp,'Вопрос'),
               F.num_col_by_name_in_hat_c(tmp, 'Дней_на_решение'),
               F.num_col_by_name_in_hat_c(tmp,'Примечание')}


    CQT.fill_wtabl_old_c(self, tmp, self.ui.tbl_selector_add, separ='', isp_hat_c=True,set_editeble_col_nomera=set_red)
    users = sorted([_ for _ in  self.DICT_EMPLOEE.keys()])
    self.ui.tbl_selector_add.setColumnHidden(CQT.num_col_by_name_c(self.ui.tbl_selector_add,'Пномер'),True)
    self.ui.tbl_selector_add.setColumnHidden(CQT.num_col_by_name_c(self.ui.tbl_selector_add, 'Дата_решения'), True)

    CQT.add_combobox(self,self.ui.tbl_selector_add,0,CQT.num_col_by_name_c(self.ui.tbl_selector_add,'Ответственный'),
                     users,True,select_responsible)
    CQT.add_combobox(self, self.ui.tbl_selector_add, 0, CQT.num_col_by_name_c(self.ui.tbl_selector_add, 'Проект_пу'),
                     list_projects, True, select_project)

    CQT.add_combobox(self, self.ui.tbl_selector_add, 0, CQT.num_col_by_name_c(self.ui.tbl_selector_add, 'Отдел'),
                     self.SET_selector_PODRAZD, True, select_dept)

    CQT.add_combobox(self, self.ui.tbl_selector_add, 0, CQT.num_col_by_name_c(self.ui.tbl_selector_add, 'Код_проблемы'),
                     self.DICT_selector_OSHIBKI.values(), True, select_kod)

    self.ui.tbl_selector_add.resizeColumnsToContents()

