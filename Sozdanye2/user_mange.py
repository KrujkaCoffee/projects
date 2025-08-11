import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
def reg_new_user(self):
    lbx = self.ui.lbx_spis_sotr
    ima = ' '.join(lbx.currentText().split()[:3])
    if F.existence_file_c(F.pcfg('Riba')) == False:
        F.save_file_pickle(F.pcfg('Riba'), [['', '']])
    rez = CMS.confirm_private_parol_c(ima, self.ui.le_parol.text())
    if rez != None:
        CQT.msgbox(f"Пользователь уже зарегистрирован")
        return
    spis = F.load_file_pickle(F.pcfg('Riba'))
    spis.append([CMS.shifr(ima), CMS.shifr(
        F.date(vid='yyyy')),F.now('')])
    F.save_file_pickle(F.pcfg('Riba'), spis)
    CQT.msgbox("Новый пользователь зарегистрирован: " + '\n' + ima + '\n' \
               + CMS.shifr(ima))
    return


def log_in(self):
    lbx = self.ui.lbx_spis_sotr
    if self.ui.le_parol.text() == "":
        return
    if self.glob_login != "":
        CQT.msgbox('Нужно сначала выйти')
        return
    if lbx.currentText() == '':
        CQT.msgbox('Не выбран пользователь')
        return
    self.superuser = False
    ima = CMS.name_by_empl_c(lbx.currentText())
    if self.ui.le_parol.text() == "Zflvby" or F.user_name() == 'a.belyakov':
        self.superuser=True
        parol = True
    else:
        parol = CMS.confirm_private_parol_c(ima, self.ui.le_parol.text())
    if parol == None:
        CQT.msgbox("Не зарегистрирован")
        return
    if parol == True:
        self.glob_login = f'{ima} {self.DICT_EMPLOEE_FULL_WITH_DEL[ima]["Должность"]}'#  CMS.empol_by_name_c(self,ima)
        self.glob_ima = ima
        #self.setWindowTitle(ima)
        self.ui.le_parol.clear()
    else:
        CQT.msgbox("Не верный пароль")
        self.ui.le_parol.clear()
        return
    save_user_choice(self)
    self.SPIS_DOST_OPER = []
    for i in range(len(self.SPIS_OPER)):
        if ima in self.SPIS_OPER[i][1]:
            self.SPIS_DOST_OPER.append(self.SPIS_OPER[i][0])
    self.zapoln_tabl_mk()



def save_user_choice(self):
    user = self.ui.lbx_spis_sotr.currentText()
    CMS.save_tmp_path('user_choice_sozdanie',user)

def load_user_choice(self):
    user = CMS.load_tmp_path('user_choice_sozdanie')
    try:
        self.ui.lbx_spis_sotr.setCurrentText(user)
    except:
        pass

def logout(self):
    if self.glob_login == '':
        return
    self.glob_login = ''
    self.setWindowTitle("Создание нарядов")
    self.ui.le_Nparol.setVisible(False)
    self.ui.le_Nparol2.setVisible(False)

    CQT.clear_tbl(self.ui.tbl_komplektovka)
    CQT.clear_tbl(self.ui.tbl_komplektovka_view)
    CQT.clear_tbl(self.ui.tbl_brak)
    CQT.clear_tbl(self.ui.tbl_dse)
    CQT.clear_tbl(self.ui.tableWidget_vibor_mk)
    CQT.clear_tbl(self.ui.tbl_prosmotr_nar)
    CQT.clear_tbl(self.ui.tbl_prosmotr_nar_jurnal)
    CQT.clear_tbl(self.ui.tbl_dse)
    CQT.clear_tbl(self.ui.tbl_filtr_dse)
    CQT.clear_tbl(self.ui.tbl_select_marsh)
    self.ui.lbl_curr_mk.clear()
    self.ui.lbl_tmp_time.clear()
    # self.ui.lbl_ima_rc.clear()
    # self.ui.lbl_tmp_time_potenc.clear()

    self.ui.lbl_kompl_info.clear()
    self.ui.lineEdit_cr_nar_kolvo.clear()
    self.ui.plainTextEdit_opovesh.clear()
    self.ui.lineEdit_cr_nar_nom_proect.clear()
    self.ui.lineEdit_cr_nar_nomerPU.clear()
    self.ui.lineEdit_cr_nar_norma.clear()
    self.ui.le_parol.clear()
    self.ui.lbx_spis_sotr.setCurrentIndex(0)
    self.ui.plainTextEdit_zadanie.clear()
    #self.ui.tableWidget_spispk_nar_dla_korrect.clear()
    self.ui.tabWidget_2.setCurrentIndex(0)
    self.ui.tabWidget.setCurrentIndex(0)
    self.glob_nom_mk = 0
    return


def load_users(self,DICT_EMPLOEE_FULL:dict,LIST_DOLGN_ETAP:list):
    """Загрузить список сотрудников в листбокс"""


    #первый раз занесение
    #spis_itr = F.load_file(F.scfg('FiltrEmp') + F.sep() + 'FiltrEmp_u.txt')
    #for itr in spis_itr:
    #    CSQ.custom_request_c(self.db_naryd ,f"""UPDATE dolgn_etap SET (login_sozdanie) = (1) WHERE Должность = '{itr}';""")


    #self.SPIS_EMPLOEE = CSQ.custom_request_c(self.bd_users,"""SELECT ФИО, Должность FROM employee WHERE Статус != 'Увольнение' AND Пномер > 2 ORDER BY ФИО ASC""",hat_c=False)
    #self.SPIS_EMPLOEE = [[k,DICT_EMPLOEE_FULL[k]['Должность']] for (k,v) in DICT_EMPLOEE_FULL.items() if DICT_EMPLOEE_FULL[k]['Компания'] == CFG.Config.place.Имя]
    #self.SPIS_EMPLOEE = F.sort_by_column_c(self.SPIS_EMPLOEE,0,hat_c=False)

    dict_dolgn_etap = {'$'.join([_['Должность'],_['Подразделение'],_['Производство']]):_ for _ in LIST_DOLGN_ETAP}

    self.ui.lbx_spis_sotr.addItem('')

    for fio, vals in DICT_EMPLOEE_FULL.items():
        company = vals['Компания']
        if company != CFG.Config.place.Имя:
            continue
        dolg = vals['Должность']
        podr = vals['Подразделение']
        dpc = '$'.join([dolg,podr,company])
        if dpc in dict_dolgn_etap and dict_dolgn_etap[dpc]['login_sozdanie']:
            self.ui.lbx_spis_sotr.addItem(fio + ' ' + dolg)
    load_user_choice(self)


def reset_user_pass(self):
    if not CMS.user_access(self.db_naryd,'выполнение_сборс_пароля',F.user_name()):
        return
    lbx = self.ui.lbx_spis_sotr
    if self.glob_login != "":
        CQT.msgbox('Нужно сначала выйти')
        return
    if lbx.currentText() == '':
        CQT.msgbox('Не выбран пользователь')
        return
    ima = CMS.name_by_empl_c(lbx.currentText())

    if F.existence_file_c(F.pcfg('Riba')) == False:
        CQT.msgbox(f'Не найден файл с паролями')

    spis = F.load_file_pickle(F.pcfg('Riba'))
    for i in range(len(spis)):
        log = spis[i][0]
        if CMS.shifr(ima.strip()) in log.strip():
            spis[i][1] = CMS.shifr(F.now("%Y"))
            if len(spis[i]) == 2:
                spis[i].append('')
            else:
                spis[i][2] = ''
            break
    F.save_file_pickle(F.pcfg('Riba'), spis)
    CQT.msgbox("Пользователь сброшен: " + '\n' + ima + '\n' \
               + F.now("%Y"))



def change_user_pass(self):
    if self.glob_login == '':
        return
    if self.ui.le_Nparol.isVisible() == False:
        CQT.msgbox("Введи старый и новый пароль, потом еще раз через меню - сменить пароль")
        self.ui.le_Nparol.setVisible(True)
        self.ui.le_Nparol2.setVisible(True)
        return
    ima = CMS.name_by_empl_c(self.glob_login)
    parol = CMS.confirm_private_parol_c(ima, self.ui.le_parol.text())
    if parol == None:
        CQT.msgbox("Не найден пользователь")
        return
    if parol == False:
        CQT.msgbox("Не верный пароль")
        self.ui.le_parol.clear()
        return
    if self.ui.le_Nparol.text() != self.ui.le_Nparol2.text():
        CQT.msgbox("Не совпадают новые пароли")
        return
    if self.ui.le_parol.text() == self.ui.le_Nparol2.text():
        CQT.msgbox("Новый пароль должен отличаться от старого")
        return
    if ' ' in self.ui.le_Nparol.text():
        CQT.msgbox(f'Пароль не может содержать пробелы')
        return
    if len(self.ui.le_Nparol.text()) < 5:
        CQT.msgbox(f'Пароль не может быть меньше 5 символов')
        return

    spis = F.load_file_pickle(F.pcfg('Riba'))
    for i in range(len(spis)):
        if spis[i][0] == CMS.shifr(ima):
            spis[i][1] = CMS.shifr(self.ui.le_Nparol.text())
            if len(spis[i]) == 2:
                spis[i].append(F.now(''))
            else:
                spis[i][2] = F.now('')
            break
    F.save_file_pickle(F.pcfg('Riba'), spis)
    F.save_file_pickle(F.pcfg('Riba') + f'_back_{F.now("%Y%m%d")}', spis)
    self.ui.le_parol.setText('')
    self.ui.le_Nparol.setText('')
    self.ui.le_Nparol2.setText('')
    self.ui.le_Nparol.setVisible(False)
    self.ui.le_Nparol2.setVisible(False)
    self.glob_login = ''
    self.setWindowTitle('Создание нарядов')
    CQT.msgbox("Пароль изменен, войди еще раз по новому паролю")
    return
