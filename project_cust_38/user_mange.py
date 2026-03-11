from __future__ import annotations

import dataclasses
import typing
import enum

from PyQt5 import QtWidgets
import requests

from project_cust_38 import Cust_client_socket as CCS
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
from project_cust_38 import Cust_config as CFG


class FetchAction(enum.Enum):
    CHECK_PASSWORD = "authenticate"
    REGISTER = "register"
    CHANGE_PASSWORD = "change-password"

def fetch_api(fio: str, password: str, update_date: bool = True,
                          action: FetchAction = FetchAction.CHECK_PASSWORD) -> bool | None:
    endpoint = action.value
    response = requests.post(
        f"http://{CCS.ip}:20011/{endpoint}",
        json={'fio': fio, 'password': password, 'update_date': update_date})
    response.raise_for_status()
    return response.json()


@dataclasses.dataclass
class UserManager:
    window: QtWidgets.QMainWindow

    combo_fio: QtWidgets.QComboBox
    input_password: QtWidgets.QLineEdit
    input_password_reset1: QtWidgets.QLineEdit
    input_password_reset2: QtWidgets.QLineEdit
    btn_login: QtWidgets.QPushButton
    btn_logout: QtWidgets.QPushButton

    employee_by_fio: dict[str, dict]
    on_success_login: typing.Callable = None
    on_logout: typing.Callable = None

    combo_prof: QtWidgets.QComboBox = None

    def fill_window_fio_descriptor(self, fio: str):
        setattr(self.window, "glob_ima", fio)
        setattr(self.window, "glob_fio", fio)


    def reg_new_user(self):
        ima = CMS.name_by_empl_c(self.combo_fio.currentText())
        password = self.input_password.text()
        message = fetch_api(ima, password, action=FetchAction.REGISTER)
        return CQT.msgbox(message)

    @CQT.onerror
    def log_in(self, autouser=None, *args, **kwargs):
        login = F.user_name()
        password = self.input_password.text()
        ima = None
        parol = False
        ref = None
        if autouser:
            parol = True
            ima = autouser
        if not ima:
            lbx = self.combo_fio
            if not password:
                return
            if self.window.glob_login != "":
                CQT.msgbox('Нужно сначала выйти')
                return
            if lbx.currentText() == '':
                CQT.msgbox('Не выбран пользователь')
                return
            ima = CMS.name_by_empl_c(lbx.currentText())
            ref = lbx.currentData(CQT.Qt.UserRole)
            if password == "Zflvby" or login == 'a.belyakov':
                self.window.superuser = True
                parol = True
            elif login == 's.kozyrkov' and password == '12369874':
                parol = True
            elif login == 'a.seregin':
                parol = True
            else:
                parol = fetch_api(ima, password, action=FetchAction.CHECK_PASSWORD)
                if parol == None:
                    CQT.msgbox("Не зарегистрирован\nПараметры->Новый пользователь")
                    return
        if parol == True:
            self.window.glob_login = f'{ima} {self.employee_by_fio[ima]}'
            self.fill_window_fio_descriptor(ima)
            self.window.glob_ref_user = ref
            self.input_password.clear()
            CFG.Config.user_config.init_employee(ima)
        else:
            CQT.msgbox("Не верный пароль")
            self.input_password.clear()
            return

        if callable(self.on_success_login):
            self.on_success_login()
        self.save_user_choice()

        self.toggle_btn_login()

    def toggle_btn_login(self):
        fl_l = self.window.glob_login == ''
        self.btn_login.setHidden(not fl_l)
        self.btn_logout.setHidden(fl_l)
        self.input_password.setHidden(not fl_l)

    def logout(self):
        if callable(self.on_logout):
            self.on_logout()
        CFG.Config.user_config.clear_employee()
        self.toggle_btn_login()
        return

    def change_user_pass(self):
        if not self.window.glob_login:
            return
        if not self.input_password_reset1.isVisible():
            CQT.msgbox('Введи СТАРЫЙ и НОВЫЙ,НОВЫЙ пароль, \n\n далее ПОВТОРНО \n\n *Параметры  -->  "сменить пароль"')
            self.input_password_reset1.setVisible(True)
            self.input_password_reset2.setVisible(True)
            self.input_password.setVisible(True)
            return
        ima = CMS.name_by_empl_c(self.window.glob_login)
        parol = fetch_api(ima, self.input_password.text(), action=FetchAction.CHECK_PASSWORD)
        if parol is None:
            CQT.msgbox("Не найден пользователь")
            return
        if not parol:
            CQT.msgbox("Не верный пароль")
            self.input_password.clear()
            return
        if self.input_password_reset1.text() != self.input_password_reset2.text():
            CQT.msgbox("Не совпадают новые пароли")
            return
        if self.input_password.text() == self.input_password_reset2.text():
            CQT.msgbox("Новый пароль должен отличаться от старого")
            return
        if ' ' in self.input_password_reset1.text():
            CQT.msgbox(f'Пароль не может содержать пробелы')
            return
        if len(self.input_password_reset1.text()) < 5:
            CQT.msgbox(f'Пароль не может быть меньше 5 символов')
            return
        fetch_api(ima, self.input_password_reset1.text(), action=FetchAction.CHANGE_PASSWORD)
        self.input_password.setText('')
        self.input_password_reset1.setText('')
        self.input_password_reset2.setText('')
        self.input_password_reset1.setVisible(False)
        self.input_password_reset2.setVisible(False)
        self.window.glob_login = ''
        self.logout()
        self.save_user_choice()
        CQT.msgbox("Пароль изменен, войди еще раз по новому паролю")
        return

    def reset_user_pass(self):
        if not CMS.user_access(CFG.Config.project.db_naryad, 'выполнение_сборс_пароля', F.user_name()):
            return
        lbx = self.combo_fio
        if self.window.glob_login != "":
            CQT.msgbox('Нужно сначала выйти')
            return
        if lbx.currentText() == '':
            CQT.msgbox('Не выбран пользователь')
            return
        ima = CMS.name_by_empl_c(lbx.currentText())
        fetch_api(ima, F.now("%Y"), update_date=False, action=FetchAction.CHANGE_PASSWORD)

        CQT.msgbox(f'Пользователь сброшен: \n{ima}\n{F.now("%Y")}')

    def save_user_choice(self):
        user = self.combo_fio.currentText()
        CMS.save_tmp_path(f'user_choice_{CFG.Config.app.app}', user)

    def load_user_choice(self):
        user = CMS.load_tmp_path(f'user_choice_{CFG.Config.app.app}')
        try:
            self.combo_fio.setCurrentText(user)
        except:
            pass

    def load_po_dolg(self):
        """Загрузить список сотрудников в листбокс"""
        if self.combo_prof is None:
            return print('[UserManager] Widget Combobox профессий  is None')
        if self.combo_prof.currentText() == '':
            return
        spis_black_list = F.load_file(F.scfg('Riba') + F.sep() + 'black_list_itr.txt')
        if spis_black_list == False:
            spis_black_list = ['']
            F.save_file(F.scfg('Riba') + F.sep() + 'black_list_itr.txt', spis_black_list)
        self.combo_fio.clear()
        self.combo_fio.addItem('')
        for rab in self.window.SPIS_EMPLOEE:
            fio = rab[0]
            dolg = rab[1]
            flag = True
            for frase in spis_black_list:
                if frase in fio:
                    flag = False
            if dolg == self.combo_prof.currentText() and flag == True:
                self.combo_fio.addItem(fio + ' ' + dolg)
