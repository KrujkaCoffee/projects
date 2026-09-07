from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_SQLite as CSQ
import kpl_vipoln as KPLVIP

fio = 'Общий специалист снабжения'


def start_naryad(nom_nar: int):
    now = F.now()
    employee = CMS.dict_emploee_full(F.scfg('BD_users'))
    journal_object = CMS.Jurnal_nar(F.scfg('Naryad'), nom_nar=nom_nar, user=fio)
    rez = journal_object.add_new_row(DICT_EMPL_FULL=employee, lbl_abstract_text=fio, date_time=now, state='Начат')
    if rez:
        print(f'Наряд №{nom_nar} успешно начат')

def stop_naryad(nom_nar: int):
    now = F.now()
    employee = CMS.dict_emploee_full(F.scfg('BD_users'))
    journal_object = CMS.Jurnal_nar(F.scfg('Naryad'), nom_nar=nom_nar, user=fio)
    rez = journal_object.add_new_row(DICT_EMPL_FULL=employee, lbl_abstract_text=fio, date_time=now, state='Завершен')
    if rez:
        print(f'Наряд №{nom_nar} успешно завершен')


def otk(self, nom_mk: int, nom_nar: int):
    nar_obj = CMS.Naryads(nom_nar, F.scfg('BD_users'))
    journal_object = CMS.Jurnal_nar(F.scfg('Naryad'), nom_nar=nom_nar, user=fio)
    nar_obj.get_mk()
    nom_kpl = nar_obj.mk.НомКплан
    type_mk = nar_obj.mk.Тип
    if type_mk == 1:  # Тип Плановая
        msg = KPLVIP.check_otk_after_proizv(self, nom_mk, kod_oper={'7135', '6011',
                                                                    '0136'})  # Пассивирование Окрашивание Дробеструйная
        if not msg:
            custom_request_c = f'''UPDATE пл_отк  SET (Контр_покрытие_ФИО, Контр_покрытие_дата) = (?,?) 
                    WHERE НомПл == ?;'''
            param = [journal_object.user, F.now(), nom_kpl]
            CSQ.custom_request_c(self.db_kplan, custom_request_c, list_of_lists_c=param)
            # try:
            #     obj = B24.B24('chat21323')
            #     msg_rows = f'По {nar_obj.mk.Номер_заказа} {nar_obj.mk.Номер_проекта} MK №{nar_obj.mk.Пномер} контроль\n ' \
            #                f'после Пассивирование/Окрашивание/Дробеструйная успешно пройден {jur_obj.user} по наряду {nom_nar}'
            #     obj.msg(msg_rows)
            # except:
            #     pass
    mk = CMS.Marshrut_cards(nom_mk, self.db_naryd, self.db_resxml)
    mk.apply_count_from_nar(int(nom_nar))
    if nar_obj.count_users() == 2:
        if nar_obj.Фвремя != '' and nar_obj.Фвремя2 != '':
            custom_request_c = f'UPDATE naryad SET Подтвержд_вып = 1, Подтвержд_вып_дата = "{F.now()}", Подтвержд_вып_фио = "{self.glob_fio}" WHERE Пномер == {nom_nar}'
            CSQ.custom_request_c(self.db_naryd, custom_request_c)
    else:
        custom_request_c = f'UPDATE naryad SET Подтвержд_вып = 1, Подтвержд_вып_дата = "{F.now()}", Подтвержд_вып_фио = "{self.glob_fio}" WHERE Пномер == {nom_nar}'
        CSQ.custom_request_c(self.db_naryd, custom_request_c)

