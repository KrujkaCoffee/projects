from PyQt5 import QtWidgets

from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_config as CFG


def dict_from_combo_table(tbl: QtWidgets.QTableWidget) -> list[dict]:
    result = []
    headers = [
        tbl.horizontalHeaderItem(col).text()
        for col in range(tbl.columnCount())
    ]
    for row in range(tbl.rowCount()):
        tmp = {}
        for col, head in enumerate(headers):
            cell = tbl.cellWidget(row, col)
            if isinstance(cell, QtWidgets.QComboBox):
                text = cell.currentText()
            else:
                text = tbl.item(row, col).text()
            tmp[head] = text
        result.append(tmp)
    return result

def create_order(self, *args):
    if not CMS.user_access(self.db_naryad, 'аутсорс_создание_заявки', F.user_full_namre()): #todo вкл
        return
    tbl_order = self.ui.tbl_new_order
    tbl_naryads = self.ui.tbl_list_chosed_naryads
    order = dict_from_combo_table(tbl_order)
    naryads = CQT.list_from_wtabl_c(tbl_naryads, hat_c=False, rez_dict=True)

    order_params = self.DICT_PARAMS_BY_OBJECT.get('Заявка')
    nar_params = self.DICT_PARAMS_BY_OBJECT.get('Наряд')
    if self.check_nar_reg_for_order([nar['Номер_наряда'] for nar in naryads]):
        app = insert_application(order=order.pop(0), naryads=naryads, order_params=order_params, nar_params=nar_params)
        if app:
            naryads = ','.join(str(naryad['Номер_наряда']) for naryad in naryads)
            user = F.user_full_namre()
            query = f"""SELECT 
                naryad.Пномер as Номер_Наряда,
                mk.Пномер as МК, 
                пл_оуп.НомПл as "Номер КПЛ", 
                знпр.№ERP, 
                знпр.№проекта
                 FROM naryad
                        JOIN mk ON mk.Пномер = naryad.Номер_мк
                        join пл_оуп ON пл_оуп.НомПл = mk.НомКплан
                        JOIN знпр ON пл_оуп.Пномер_ЗП = знпр.s_num
                        where naryad.Пномер IN ({naryads})
                    """
            credentials = CSQ.custom_request_c(CFG.Config.project.db_naryad, query, rez_dict=True,
                                               attach_dbs=self.db_kplan)
            msg = f"{user} Создал(а) заявку на аутсорсинг по нарядам:\n"
            for nar_credentials in credentials:
                msg += "\n".join(
                    f"\t\t{key}: {val}" for key, val in nar_credentials.items()
                )
                msg += '\n' + ('===' * 16) + '\n'
            from project_cust_38 import Cust_mes as CMS
            CMS.send_info_mk_b24_by_action(msg, 'Аутсорсинг')
            print()
            CQT.msgbox('Заявка успешно создана!')
            self.ui.tabWidget.setCurrentIndex(0)