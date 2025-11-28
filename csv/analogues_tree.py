from __future__ import annotations
import base64
import pprint
from collections import defaultdict
import copy

import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from project_cust_38.Cust_config import Config

from PyQt5 import QtGui, QtCore, QtWidgets
import project_cust_38.xml_v_drevo as XML
from typing import TYPE_CHECKING
import project_cust_38.Cust_odata_erp as ODAT
import tkp

if TYPE_CHECKING:
    from csv_tkp import mywindow


@CQT.onerror
def apply_tooltip_tree_edit_tbl(self: mywindow, *args, **kwargs):
    dict_tool_fields = {'Коэфф_длины_швов': 'Отношение длин швов целевой к аналогу (Lц/Lа)',
                        'Уд_количество_аналог': 'Отношение длины и ширины целевой к аналогу (Lц/Lа)*(Вц/Bа)'
                        }
    tbl = self.ui.tbl_red_tree
    tbl.setToolTip('')
    cur_text = tbl.horizontalHeaderItem(tbl.currentColumn()).text()
    if cur_text in dict_tool_fields:
        tbl.setToolTip(dict_tool_fields[cur_text])
    weight = tbl.item(
        tbl.currentRow(),
        CQT.num_col_by_name_c(tbl, 'Масса/М1,М2,М3')
    ).text()
    desc = tbl.item(
        tbl.currentRow(),
        CQT.num_col_by_name_c(tbl, 'Обозначение')
    ).text()
    self.calculation.view_calculation(f'{desc}:{weight}')


@CQT.onerror
def load_nomen_wo_prices(self: mywindow, *args):
    def check_poz(self, snum, list_err):
        strukt = CSQ.custom_request_c(self.Data_mes.db_dse,
                                      f'SELECT pickle_file, name_tkp, nnom_izd, dir_rkd,вид_по_напр  FROM tkp WHERE s_nom = {snum}',
                                      rez_dict=True, one=True)
        if strukt == None or strukt == False:
            CQT.msgbox(f'Ошибка загрузки с БД Порядковый номер {snum}')
            return
        pickle_file = F.from_binary_pickle(strukt['pickle_file'])['Структура']
        for item in pickle_file:
            if item['Код ERP'] != '':
                if item['Код ERP'] not in self.Data_mes.dict_nomenklat_by_kod:
                    list_err.append({'Код ERP': item['Код ERP'],
                                     'Номенклатура': 'Не найден в БД обратиться в ТО'})
                    continue
                price = self.Data_mes.dict_nomenklat_by_kod[item['Код ERP']]['Закупочная_цена']
                if price == None or F.valm(price) == 0:
                    list_err.append({'Код ERP': item['Код ERP'],
                                     'Номенклатура': self.Data_mes.dict_nomenklat_by_kod[item['Код ERP']][
                                         'Наименование']
                                     })
        return list_err

    list_err = []
    tbl = self.ui.tbl_list_tkp
    if 'shift' in CQT.get_key_modifiers(self):
        row = CQT.get_dict_line_form_tbl(tbl)
        type = row['Тип ТКП']
        snum = int(row['Порядковый номер'])
        # if type != 'Аналог':
        #     CQT.msgbox(f'Тип ТКП не корректный')
        #     return
        list_err = check_poz(self, snum, list_err)
        if len(list_err) == 0:
            CSQ.custom_request_c(self.Data_mes.db_dse,
                                 f"""UPDATE tkp SET (check_prices) = (1) WHERE s_nom = {int(row['Порядковый номер'])}""")
            CQT.set_val_tbl_by_name(tbl, tbl.currentRow(), 'Проверка цены', 'OK')
        else:
            CSQ.custom_request_c(self.Data_mes.db_dse,
                                 f"""UPDATE tkp SET (check_prices) = (2) WHERE s_nom = {int(row['Порядковый номер'])}""")
            CQT.set_val_tbl_by_name(tbl, tbl.currentRow(), 'Проверка цены', 'NOK')
        tbl.setFocus()

        CQT.select_cell(tbl, tbl.currentRow(), 5)

    else:

        set_state = {CQT.get_dict_line_form_tbl(tbl, i)['Проверка цены'] for i in range(tbl.rowCount()) if
                     tbl.isRowHidden(i) == False}
        if len(set_state) > 1 or 'NOK' not in set_state:
            CQT.msgbox(f'Не все строки имеют статус "Проверка цены" NOK')
            return
        for i in range(tbl.rowCount()):
            if tbl.isRowHidden(i):
                continue
            row = CQT.get_dict_line_form_tbl(tbl, i)
            type = row['Тип ТКП']
            snum = int(row['Порядковый номер'])
            if type != 'Аналог':
                CQT.msgbox(f'Тип ТКП не корректный')
                return
            list_err = check_poz(self, snum, list_err)

    if len(list_err) == 0:
        return
    F.save_file(CMS.tmp_dir() + F.sep() + 'tmp_prices_info.txt', F.list_of_dicts_to_list_of_lists(list_err), sep='\t')
    F.run_file_os_c(CMS.tmp_dir() + F.sep() + 'tmp_prices_info.txt')


@CQT.onerror
def check_prices(self: mywindow, *args):
    if not CMS.user_access(self.Data_mes.db_naryad, 'csv_check_prices', F.user_full_namre()):
        return
    tbl = self.ui.tbl_list_tkp
    row = CQT.get_dict_line_form_tbl(tbl)
    if not CQT.msgboxgYN(f'Отметить проверку цен в ТКП № {row["Порядковый номер"]}?'):
        return
    if row['Проверка цены'] == "NOK" or row['Проверка цены'] == "":
        CQT.set_val_tbl_by_name(tbl, column_name='Проверка цены', val='OK')
        CSQ.custom_request_c(self.Data_mes.db_dse,
                             f"""UPDATE tkp SET check_prices == 1 WHERE s_nom ={row['Порядковый номер']}""")
        msg = f"{F.user_full_namre()} снял в ТКП № {row['Порядковый номер']} отметку о проверке цен"
        CMS.send_info_mk_b24_by_action(msg, 'Разработка ТКП по ВО')
        # msg_to_b24(
        #     f"{F.user_full_namre()} снял в ТКП № {row['Порядковый номер']} отметку о проверке цен")
    else:
        CQT.set_val_tbl_by_name(tbl, column_name='Проверка цены', val='NOK')
        CSQ.custom_request_c(self.Data_mes.db_dse,
                             f"""UPDATE tkp SET check_prices == 2 WHERE s_nom ={row['Порядковый номер']}""")
        msg = f"{F.user_full_namre()} проверил в ТКП № {row['Порядковый номер']} цены"
        CMS.send_info_mk_b24_by_action(msg, 'Разработка ТКП по ВО')
        # msg_to_b24(
        #     f"{F.user_full_namre()} проверил в ТКП № {row['Порядковый номер']} цены")



@CQT.onerror
def recalc_weight(self, *args):
    tbl = self.ui.tbl_red_tree
    list_rows = CQT.list_from_wtabl_c(tbl, rez_dict=True)

    def calc_count(self, num_row):
        def check_cell(data):
            if data == '':
                return False
            if not F.is_numeric(data):
                return False
            return True

        # tbl = self.ui.tbl_red_tree
        # current_row = CQT.get_dict_line_form_tbl(tbl, num_row)
        current_row = list_rows[num_row]
        if not check_cell(current_row['Количество']) or not check_cell(current_row['Уровень']):
            return
        count = F.valm(current_row['Количество'])
        ur = int(current_row['Уровень'])
        for i in range(num_row - 1, -1, -1):
            # row = CQT.get_dict_line_form_tbl(tbl, i)
            row = list_rows[i]
            if not check_cell(row['Количество']) or not check_cell(row['Уровень']):
                return
            if int(row['Уровень']) == 0:
                break
            if int(row['Уровень']) == ur - 1:
                count *= int(row['Количество'])
                ur -= 1
        return count

    rez = 0
    rez_wo_pki = 0
    self.ui.lbl_summ_weight.setText('')
    self.ui.lbl_summ_weight_wo_pki.setText('')
    key_count_na_izd = 'Количество на изделие'
    nf_count_by_izd = CQT.num_col_by_name_c(tbl, key_count_na_izd)
    if tbl.rowCount() == 0:
        return
    tbl.blockSignals(True)
    for i in range(tbl.rowCount()):
        # row = CQT.get_dict_line_form_tbl(tbl, i)
        row = list_rows[i]
        split_weight = row['Масса/М1,М2,М3'].split('/')
        if len(split_weight) <= 1 or split_weight[1] == '':
            continue
        str_weight = row['Масса/М1,М2,М3'].split('/')[0]
        pki = row['ПКИ']
        count = calc_count(self, i)
        # tbl.item(i, nf_count_by_izd).setText('-')
        if count == None:
            tbl.blockSignals(False)
            return 0, 0
        else:
            if row[key_count_na_izd] != str(count):
                tbl.item(i, nf_count_by_izd).setText(str(count))
        # if count != int(row['Количество на изделие']):
        #    CQT.msgbox(f'Ошибка расчетка количества на изделие')
        #    return
        rez += F.valm(str_weight) * count
        if pki == '0':
            rez_wo_pki += F.valm(str_weight) * count
    if rez > 0:
        self.ui.lbl_summ_weight.setText(str(round(rez, 2)))
    if rez_wo_pki > 0:
        self.ui.lbl_summ_weight_wo_pki.setText(str(round(rez_wo_pki, 2)))
    tbl.blockSignals(False)
    if tbl.currentRow() != -1:
        weight = tbl.item(
            tbl.currentRow(),
            CQT.num_col_by_name_c(tbl, 'Масса/М1,М2,М3')
        ).text()
        desc = tbl.item(
            tbl.currentRow(),
            CQT.num_col_by_name_c(tbl, 'Обозначение')
        ).text()
        self.calculation.save_calculation(f'{desc}:{weight}')
    return round(rez, 2), round(rez_wo_pki, 2)


@CQT.onerror
def save_red_tree(self: mywindow):
    # 24.11.25 (Чат доработка МЕС: Арсенов) Актуализация номенклатуры перед валидацией
    self.Data_mes.reload_nomen(Config.project.db_nomen)
    def generate_rez_dict(self: mywindow):
        struct = CQT.list_from_wtabl_c(self.ui.tbl_red_tree, rez_dict=True)
        for item in struct:
            item['Наименование'] = item['Наименование'].strip()
            item['Обозначение'] = item['Обозначение'].strip()
            item['Наименование_аналог'] = item['Наименование_аналог'].strip()
            item['Обозначение_аналог'] = item['Обозначение_аналог'].strip()
            if item['Масса/М1,М2,М3'] == '//':
                item['Масса/М1,М2,М3'] = ''

        dict_rez = {'Структура': struct, 'Параметры': dict()}
        return dict_rez

    def check_tbl(self: mywindow):

        def check_analogue_property(item: dict, list_of_errs: list[str]):
            if 'Не найден в БД' in item['Наименование_аналог']:
                list_of_errs.append(
                    f"В {item['Наименование']} {item['Обозначение']} не найден аналог в номенклатуре ДСЕ")
            if F.is_numeric(item['Коэфф_длины_швов'] + item['Уд_количество_аналог']) == False:
                list_of_errs.append(
                    f"В {item['Наименование']} {item['Обозначение']} Коэфф_длины_швов/Уд_количество_аналог не число")
            if item['Коэфф_длины_швов'] == '' and item['Уд_количество_аналог'] == '':
                list_of_errs.append(
                    f"В {item['Наименование']} {item['Обозначение']} Коэфф_длины_швов/Уд_количество_аналог не заполнен")
            if item['Коэфф_длины_швов'] != '' and item['Уд_количество_аналог'] != '':
                list_of_errs.append(
                    f"В {item['Наименование']} {item['Обозначение']} Коэфф_длины_швов/Уд_количество_аналог к заполнению только один параметр")

        list_of_dicts = CQT.list_from_wtabl_c(self.ui.tbl_red_tree, rez_dict=True)
        list_of_errs = []
        count_konts = 0
        is_simple = self.ui.tbl_red_tree.property('is_simple')
        if self.ui.cmb_vid_napr.currentText() == '':
            list_of_errs.append(f"Не выбран вид изделия")
        for i in range(len(list_of_dicts)):
            item = list_of_dicts[i]
            weight = item['Масса/М1,М2,М3'].split("/")
            if len(weight) <= 1 or weight[1] == '':
                wei_col = CQT.num_col_by_name_c(self.ui.tbl_red_tree, 'Масса/М1,М2,М3')
                item['Масса/М1,М2,М3'] = '//'
                self.ui.tbl_red_tree.item(i, wei_col).setText('//')
            if not is_simple:
                check_analogue_property(item, list_of_errs)
            if item['Обозначение'] == '':
                list_of_errs.append(f'Пустое обозначение в строке {i}')
            if ' не найден' in item['Масса/М1,М2,М3']:
                list_of_errs.append(f"В {item['Наименование']} {item['Обозначение']} код ЕРП не найден в номенклатуре")
            if F.is_numeric(item['Количество']) == False:
                list_of_errs.append(f"В {item['Наименование']} {item['Обозначение']} количество не число")

            if F.is_numeric(item['Уровень']) == False:
                list_of_errs.append(f"В {item['Наименование']} {item['Обозначение']} Уровень не число")
            else:
                if item['Уровень'] == '0':
                    count_konts += 1
            if i == 0:
                if F.valm(item['Уровень']) > 1:
                    list_of_errs.append(
                        f"В {item['Наименование']} {item['Обозначение']} 0 уровень в иерархии должен быть первым")
            if i > 0 and i < len(list_of_dicts) - 1:
                if F.valm(item['Уровень']) - F.valm(list_of_dicts[i - 1]['Уровень']) > 1:
                    list_of_errs.append(
                        f"В {item['Наименование']} {item['Обозначение']} Уровень не может быть оторван от иерархии")

            if item['ПКИ'] == '1' and item['Код ERP'] == '':
                list_of_errs.append(f"В {item['Наименование']} {item['Обозначение']} не указан Код ЕРП")
            if item['Масса/М1,М2,М3'] != '':
                if item['Масса/М1,М2,М3'].split("/")[1] != '':
                    if item['Код ERP'] == '':
                        list_of_errs.append(f"В {item['Наименование']} {item['Обозначение']} не указан Код ЕРП")

            if item['Код ERP'] != '':
                if item['Код ERP'] in self.Data_mes.dict_nomenklat_by_kod:
                    if self.Data_mes.dict_nomenklat_by_kod[item['Код ERP']]['На_удаление'] == 1:
                        list_of_errs.append(
                            f"В {item['Наименование']} {item['Обозначение']} материал помечен на удаление")
                else:
                    list_of_errs.append(f"В {item['Наименование']} {item['Обозначение']} материал отсутствует в БД")
        if count_konts > 1 or count_konts == 0:
            list_of_errs.append(
                f"В структуре должен быть один корневой узел")
        if len(list_of_errs) > 0:
            CQT.msgbox(pprint.pformat(list_of_errs))
            return False
        if not tkp.check_name_tkp(self.ui.le_name_tkp_2.text().strip(), self.ui.le_nnom_izd_2.text().strip(),
                                  self.ui.le_path_vo_2.text()):
            return
        return True

    def save_into_db(self: mywindow):

        rez_dict = generate_rez_dict(self)
        if rez_dict == None:
            return
        byte_dict = F.to_binary_pickle(rez_dict)
        now = F.now()
        weight, weight_wo_pki = recalc_weight(self)
        res_pnom_last = CSQ.last_row_db_c(self.Data_mes.db_dse, 'tkp', 's_nom', ['s_nom'])
        if res_pnom_last == False:
            CQT.msgbox(f'ОШибка обращения к БД')
            return

        nom_tkp = "ТКПА_" + str(int(res_pnom_last[0]) + 1) + '_' + self.ui.le_nnom_izd_2.text()
        vid_napr = self.Data_mes.dict_vid_napr[self.ui.cmb_vid_napr.currentText()]['Пномер']
        type_tkp = 4 if self.ui.tbl_red_tree.property('is_simple') else 3

        list_vals = [
            now,
            F.user_full_namre(),
            type_tkp,
            self.ui.le_name_tkp_2.text(),
            self.ui.le_nnom_izd_2.text(),
            nom_tkp,
            byte_dict,
            self.ui.le_path_vo_2.text(),
            'В работе',
            '',
            '',
            '',
            vid_napr,
            weight]
        CSQ.custom_request_c(self.Data_mes.db_dse, f"""INSERT INTO tkp (date_create, 
            user_create, 
            type_tkp, 
            name_tkp, 
            nnom_izd, 
            nnom_tkp, 
            pickle_file, 
            dir_rkd, 
            status, 
            resp_technolog, 
            date_res,
            name_res,
            вид_по_напр,
            weight_wh_pki)
                                      VALUES ({('?,' * len(list_vals))[:-1]});""", list_of_lists_c=[list_vals])
        p_nom = CSQ.custom_request_c(self.Data_mes.db_dse, f"""SELECT s_nom FROM tkp WHERE date_create = '{now}'""",
                                     hat_c=False, one_column=True)
        if p_nom == None or p_nom == False:
            CQT.msgbox(f'Добавление в БД произошло с ошибкой.')
            return
        msg = f"{F.user_full_namre()} создал структуру Аналог № {p_nom} на {self.ui.le_name_tkp_2.text().replace('%', 'проц.')} {self.ui.le_nnom_izd_2.text().replace('%', 'проц.')}"
        CMS.send_info_mk_b24_by_action(msg, 'Разработка ТКП по ВО')
        # msg_to_b24(
        #     f"{F.user_full_namre()} создал структуру Аналог № {p_nom} на {self.ui.le_name_tkp_2.text().replace('%', 'проц.')} {self.ui.le_nnom_izd_2.text().replace('%', 'проц.')}")
        CQT.msgbox(f'Успешно')

    def update_into_db(self: mywindow):
        if self.glob_edit_red_tree_snum == '':
            CQT.msgbox(f'Ошибка, self.glob_edit_red_tree_snum')
            return
        rez_dict = generate_rez_dict(self)
        if rez_dict == None:
            return
        byte_dict = F.to_binary_pickle(rez_dict)
        list_vals = [byte_dict, self.glob_edit_red_tree_snum]
        CSQ.custom_request_c(self.Data_mes.db_dse, f"""UPDATE tkp SET(
            pickle_file 
            ) = (?) WHERE s_nom = ?;""", list_of_lists_c=[list_vals])

        CQT.msgbox(f'Успешно')

    if 'shift' in CQT.get_key_modifiers(self):
        update_into_db(self)
        return
    self.ui.tbl_red_tree.blockSignals(True)
    if not check_tbl(self):
        return

    save_into_db(self)
    self.ui.tbl_red_tree.blockSignals(False)


@CQT.onerror
def get_into_red(self: mywindow):
    tbl = self.ui.tbl_list_tkp
    nf_type = CQT.num_col_by_name_c(tbl, 'Тип ТКП')
    nf_snum = CQT.num_col_by_name_c(tbl, 'Порядковый номер')
    row = tbl.currentRow()
    if row == -1:
        return
    type = tbl.item(row, nf_type).text()
    snum = int(tbl.item(row, nf_snum).text())
    # if type != 'Аналог':
    #     CQT.msgbox(f'Тип ТКП не корректный')
    #     return
    strukt = CSQ.custom_request_c(self.Data_mes.db_dse,
                                  f'SELECT pickle_file, name_tkp, nnom_izd, dir_rkd,вид_по_напр  FROM tkp WHERE s_nom = {snum}',
                                  rez_dict=True, one=True)
    if strukt == None or strukt == False:
        CQT.msgbox(f'Ошибка загрузки с БД')
        return
    pickle_file = F.from_binary_pickle(strukt['pickle_file'])['Структура']
    for item in pickle_file:
        if item['Наименование_аналог'] == 'Не найден в БД':
            if item['Обозначение'] in self.Data_mes.dict_dse:
                item['Наименование_аналог'] = item['Наименование']
                item['Обозначение_аналог'] = item['Обозначение']
                CQT.msgbox(f'{item["Обозначение"]} поправлен')
    pickle_file = F.list_of_dicts_to_list_of_lists(pickle_file)
    if pickle_file:
        hat_c_loaded = set(pickle_file[0])
        tbl = self.ui.tbl_red_tree
        hat_c_main = {tbl.horizontalHeaderItem(col).text() for col in range(tbl.columnCount())}
        dif = hat_c_main.difference(hat_c_loaded)
        if dif:
            spis = [
                [hat, *elem] for hat in dif
                for elem in pickle_file
            ]
        else:
            spis = pickle_file
    fill_tbl_strukt(self, spis)
    fill_tab_to_level(self.ui.tbl_red_tree)

    self.ui.cmb_vid_napr.setCurrentText(self.Data_mes.DICT_VID_PO_NAPR[strukt['вид_по_напр']]['Имя'])
    self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget, 'Структура'))
    self.glob_edit_red_tree_snum = snum
    self.ui.le_name_tkp_2.setText(strukt['name_tkp'])
    self.ui.le_nnom_izd_2.setText(strukt['nnom_izd'])
    self.ui.le_path_vo_2.setText(strukt['dir_rkd'])
    recalc_weight(self)

def fix_struct(struct):
    for item in struct:
        if isinstance(item, list):
            return
        if 'Обозначение' not in item or 'Обозначение_аналог' not in item:
            continue
        if item['Обозначение'] == '':
            item['Обозначение'] = item['Обозначение_аналог']
def fix_columns(tabl_cr_stukt):
    required_columns = ['b', 'Наименование', 'Обозначение', 'Количество', 'Масса/М1,М2,М3','Количество на изделие', 'Примечание', 'ПКИ', 'Код ERP',
                  'Наименование_аналог', 'Обозначение_аналог', 'Уд_количество_аналог', 'Коэфф_длины_швов', 'Кол. по заявке', 'Уровень']
    for col in range(tabl_cr_stukt.columnCount()):
        text = tabl_cr_stukt.horizontalHeaderItem(col).text()
        width = tabl_cr_stukt.columnWidth(col)
        if text in required_columns and width < 20:
            tabl_cr_stukt.setColumnWidth(col, 20)

@CQT.onerror
def fill_tbl_strukt(self, data):
    fix_struct(data)
    horizontal_scroll = self.ui.tbl_red_tree.horizontalScrollBar().value()
    scroll_vertical = self.ui.tbl_red_tree.verticalScrollBar().value()
    hidden_column = CQT.num_col_by_name_c(self.ui.tbl_red_tree, 'Ед.изм.')
    CQT.fill_wtabl(data, self.ui.tbl_red_tree, self.edit_cr_mk, 200, height_row=24, auto_type=False,
                   list_column_widths=CMS.load_column_widths(self,self.ui.tbl_red_tree))
    self.ui.tbl_red_tree.horizontalHeader().hideSection(hidden_column)
    # CMS.load_column_widths(self, self.ui.tbl_red_tree)
    CQT.set_color_sort_cell_table_c(self.ui.tbl_red_tree)
    hide_columns_for_simple_mode(self, self.ui.tbl_red_tree)
    self.ui.tbl_red_tree.verticalScrollBar().setValue(scroll_vertical)
    self.ui.tbl_red_tree.horizontalScrollBar().setValue(horizontal_scroll)
    fix_columns(self.ui.tbl_red_tree)




@CQT.onerror
def set_udk(self: mywindow):
    if self.ui.lbl_udk_rez.text() == '0':
        return
    current_row = self.ui.tbl_red_tree.currentRow()
    if current_row == -1:
        CQT.msgbox(f'Не выбрана строка')
        return
    if self.ui.chk_change_mass.checkState() == 1:
        CQT.msgbox(f'Не выбран режим простановки масс')
        return
    tbl = self.ui.tbl_red_tree
    nf_udk = CQT.num_col_by_name_c(self.ui.tbl_red_tree, 'Уд_количество_аналог')
    if nf_udk == None:
        CQT.msgbox(f'Таблица не прогружена')
    delta = F.valm(self.ui.lbl_udk_rez.text())
    # self.ui.tbl_red_tree.item(row,nf_udk).setText(self.ui.lbl_udk_rez.text())
    row = CQT.get_dict_line_form_tbl(tbl)
    if row['ПКИ'] == '0':
        if self.ui.chk_change_mass.checkState() == 2:
            if row['Масса/М1,М2,М3'] != '':
                line_mass = row['Масса/М1,М2,М3'].split("/")
                val = line_mass[0]
                new_val = str(round(F.valm(val) * delta, 2))
                if len(line_mass) > 2:
                    CQT.set_val_tbl_by_name(tbl, tbl.currentRow(), 'Масса/М1,М2,М3',
                                            '/'.join([new_val, line_mass[1], line_mass[2]]))
        if row['Уд_количество_аналог'] != '':
            new_val = str(round(F.valm(row['Уд_количество_аналог']) * delta, 2))
            CQT.set_val_tbl_by_name(tbl, current_row, 'Уд_количество_аналог', new_val)
        if row['Коэфф_длины_швов'] != '':
            new_val = str(round(F.valm(row['Коэфф_длины_швов']) * delta, 2))
            CQT.set_val_tbl_by_name(tbl, current_row, 'Коэфф_длины_швов', new_val)
    else:
        CQT.msgbox(f'ПКИ не зависят от коэфф.')
    recalc_weight(self)


@CQT.onerror
def click_row_mat(self: mywindow):
    tbl = self.ui.tbl_anal_mat
    row = CQT.get_dict_line_form_tbl(tbl)
    art = row['Код'].replace('\n', '').replace("\t", "")
    self.ui.le_art_after.setText(art)

    if self.ui.fr_dse_erp_view.isHidden():
        return
    val_chk_nomen_desc = self.ui.chk_nomen_desc.isChecked()
    val_chk_nomen_unit = self.ui.chk_nomen_unit.isChecked()
    val_chk_nomen_maker = self.ui.chk_nomen_maker.isChecked()
    val_chk_nomen_describe = self.ui.chk_nomen_describe.isChecked()
    val_chk_nomen_add_r = self.ui.chk_nomen_add_r.isChecked()

    options = {
        'load_nomen_desc': val_chk_nomen_desc,
        'load_nomen_describe': val_chk_nomen_describe,
        'load_nomen_add_r': val_chk_nomen_add_r,
        'load_nomen_maker': val_chk_nomen_maker,
        'load_nomen_unit': val_chk_nomen_unit,
    }
    headers = {
         '':'load_nomen_desc',
         'Описание:':'load_nomen_describe',
         'Дополнительные реквизиты:':'load_nomen_add_r',
         'Сведения о производителе:':'load_nomen_maker',
         'Единицы измерения и условия хранения:':'load_nomen_unit',
    }
    requisites = {
        'load_nomen_desc': ['Description',
                   'НаименованиеПолное', 'Артикул', 'Code',],
        'load_nomen_describe': ['ФайлКартинки_Key', 'Описание', 'ФайлОписанияДляСайта_Key',
                   'ВестиУчетСертификатовНоменклатуры'],
        'load_nomen_add_r': ['ДополнительныеРеквизиты'],
        'load_nomen_maker': ['ПроизводительИмпортерКонтрагент_Key', 'Производитель_Key', 'Марка_Key', 'СтранаПроисхождения_Key',],
        'load_nomen_unit': ['ИспользоватьУпаковки', 'ЕдиницаИзмерения_Key', 'ЕдиницаДляОтчетов_Key',
                    'ВесЗнаменатель','ВесЧислитель','ВесЕдиницаИзмерения_Key',
                    'ОбъемЗнаменатель','ОбъемЧислитель', 'ОбъемЕдиницаИзмерения_Key',
                    'ДлинаЗнаменатель', 'ДлинаЧислитель', 'ДлинаЕдиницаИзмерения_Key',
                    'ПлощадьЗнаменатель', 'ПлощадьЧислитель', 'ПлощадьЕдиницаИзмерения_Key',
                    'СкладскаяГруппа_Key', 'ВесИспользовать', 'ОбъемИспользовать', 'ДлинаИспользовать', 'ПлощадьИспользовать'],
    }



    DICT_REPLACE_NAMES = {
        'Description':"Рабочее наименование:",
        'НаименованиеПолное': "Наименование для печати:",
        'Артикул': "Артикул:",
        'Code': "Код:",

        'Описание:':'Описание:',
        'ФайлКартинки_Key': "Изображение",
        'Описание': "Текстовое описание",
        'ФайлОписанияДляСайта_Key': 'Файл описания для сайта',
        "ВестиУчетСертификатовНоменклатуры": "Учет сертификатов номенклатуры",

        'Дополнительные реквизиты:':'Дополнительные реквизиты:',


    }
    DICT_REPLACE_NAMES_add_1 = {

        'Сведения о производителе:': 'Сведения о производителе:',
        'ПроизводительИмпортерКонтрагент_Key': 'Производитель, импортер (контрагент)',
        'Производитель_Key': 'Производитель (бренд)',
        'Марка_Key': 'Марка (бренд)',
        'СтранаПроисхождения_Key': 'Страна происхождения',

        'Единицы измерения и условия хранения:': 'Единицы измерения и условия хранения:',
        'ИспользоватьУпаковки': 'Упаковки',#Булево
        'ЕдиницаИзмерения_Key': 'Единица хранения',#СправочникСсылка.УпаковкиЕдиницыИзмерения
        'ЕдиницаДляОтчетов_Key': 'Единица для отчетов',#СправочникСсылка.УпаковкиЕдиницыИзмерения
        'Вес': 'Вес',#расчетный
        'Объем': 'Объем',#расчетный
        'Длина': 'Длина',#расчетный
        'Площадь': 'Площадь',#расчетный
        'СкладскаяГруппа_Key': 'Складская группа',#СправочникСсылка.СкладскиеГруппыНоменклатуры

    }

    #Номенклатура - модуль менеджера - 1359

    fields = []
    for k,v in requisites.items():
        if k in options:
            if options[k]:
                fields.append(', '.join(v))
    fields = ', '.join(fields)
    if fields == '':
        return


    m = ODAT.OrdersComposit('ERP')

    code, resp_general = m.get_response(doc_name='Catalog_Номенклатура',
                  wet_filtr=f"""?$filter= Ref_Key eq guid'{row['Ref_Key']}'&$select= 
                  Ref_Key, {fields} 
                    """,with_cod=True)

    #resp_general = m.get_response(doc_name='Catalog_Номенклатура',
    #               wet_filtr=f"""?$filter= Code eq '00-00007669'&$select= *""",
    #               )



    if code != 200:
        CQT.msgbox(f'Ошибка загрузки данных из ЕРП')
        return

    resp_general = resp_general[0]

    def is_key_description_load(key_desc:str):
        for k,v in DICT_REPLACE_NAMES.items():
            if v == key_desc:
                for kr, vr in requisites.items():
                    if k in vr:
                        if options[kr]:
                            return True
                        else:
                            return False
        return False

    DICT_DESCRIPTIONS = {
        'Производитель, импортер (контрагент)': 'Catalog_Контрагенты',
        'Производитель (бренд)': 'Catalog_Производители',
        'Марка (бренд)': 'Catalog_Марки',
        'Страна происхождения': 'Catalog_СтраныМира',
        'Единица хранения': 'Catalog_УпаковкиЕдиницыИзмерения',
        'Единица для отчетов': 'Catalog_УпаковкиЕдиницыИзмерения',
        'Складская группа': 'Catalog_СкладскиеГруппыНоменклатуры',

    }
    if options['load_nomen_unit']:
        if resp_general['ВесИспользовать']:
            DICT_DESCRIPTIONS['ВесЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'
        if resp_general['ОбъемИспользовать']:
            DICT_DESCRIPTIONS['ОбъемЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'
        if resp_general['ДлинаИспользовать']:
            DICT_DESCRIPTIONS['ДлинаЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'
        if resp_general['ПлощадьИспользовать']:
            DICT_DESCRIPTIONS['ПлощадьЕдиницаИзмерения_Key'] = 'Catalog_УпаковкиЕдиницыИзмерения'


    if options['load_nomen_add_r']:
        for dop in resp_general['ДополнительныеРеквизиты']:
            dop_name = m.get_response(doc_name='ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения',
                           wet_filtr=f"""?$filter= Ref_Key eq guid'{dop['Свойство_Key']}'&$select= Description""")
            dop_val = m.get_response(doc_name='Catalog_ЗначенияСвойствОбъектов',
                                  wet_filtr=f"""?$filter= Ref_Key eq guid'{dop['Значение']}'&$select= Description""")
            if dop_name and dop_val:
                dop_name = dop_name[0]['Description']
                dop_val = dop_val[0]['Description']
                DICT_REPLACE_NAMES[dop_name] = dop_name
                resp_general[dop_name] = dop_val

    for k,v in DICT_REPLACE_NAMES_add_1.items():
        DICT_REPLACE_NAMES[k] = v

    ref_key_nomen = resp_general['Ref_Key']
    for name , psd in DICT_REPLACE_NAMES.items():
        if name in resp_general and name != psd:
            resp_general[psd] = resp_general[name]
            resp_general.pop(name,None)

    def get_file(row_add_file:dict):
        типХраненияФайла = row_add_file['ТипХраненияФайла']
        if типХраненияФайла == 'ВТомахНаДиске':
            том_Key = row_add_file['Том_Key']
            img_data = m.get_response(doc_name='Catalog_ТомаХраненияФайлов',
                                      wet_filtr=f"""?$filter= Ref_Key eq guid'{том_Key}'&$select= ПолныйПутьWindows""")
            ПолныйПутьWindows = img_data[0]['ПолныйПутьWindows'] + row_add_file['ПутьКФайлу']

            code, dict_file = APIERP.get_file(ПолныйПутьWindows)
            if code != 200:
                return

            file_data = dict_file[0][ПолныйПутьWindows]
        else:
            ПолныйПутьWindows =  row_add_file['Том_Key']
            img_b64 = row_add_file['ТекстХранилище_Base64Data']
            file_data = base64.decodebytes(str.encode(img_b64))

        ext = F.keep_extention_c(ПолныйПутьWindows)
        tmp_win_dir = F.save_tmp_win_dir_file(file_data, extention=ext)
        return tmp_win_dir
    if options['load_nomen_describe']:
        img = '<не указано>'
        if resp_general['Изображение'] != ODAT.EMPTY_KEY:
            #TODO
            img_data = m.get_response(doc_name='Catalog_НоменклатураПрисоединенныеФайлы',
                      wet_filtr=f"""?$filter= Ref_Key eq guid'{resp_general['Изображение']}'&$select= ТипХраненияФайла,Том_Key,ПутьКФайлу""")#resp['Изображение']
            img = get_file(img_data[0])
        resp_general['Изображение'] = img

        files = []
        add_files =  m.get_response(doc_name='Catalog_НоменклатураПрисоединенныеФайлы',
                      wet_filtr=f"""?$filter=ВладелецФайла_Key eq guid'{ref_key_nomen}'&$select=ТипХраненияФайла,Том_Key,ПутьКФайлу""")
        for row in add_files:
            files.append(get_file(row))
        resp_general["Файлы"] = ';'.join(files) #f'Файлы ({len(files)})'

        file = '<не указано>'
        if resp_general['Файл описания для сайта'] != ODAT.EMPTY_KEY:

            file_data = m.get_response(doc_name='Catalog_НоменклатураПрисоединенныеФайлы',
                      wet_filtr=f"""?$filter= Ref_Key eq guid'{resp_general['Файл описания для сайта']}'&$select= ТипХраненияФайла,Том_Key,ПутьКФайлу""")
            file = get_file(file_data[0])
        resp_general['Файл описания для сайта'] = file


    for k,v in DICT_DESCRIPTIONS.items():
        if not is_key_description_load(k):
            continue
        default_val = '<не указано>'
        if resp_general[k] != ODAT.EMPTY_KEY:

            resp_data = m.get_response(doc_name=v,
                      wet_filtr=f"""?$filter= Ref_Key eq guid'{resp_general[k]}'&$select= Description""")
            default_val = resp_data[0]['Description']
        resp_general[k] = default_val
    if options['load_nomen_unit']:
        #============calc weight, val, lenght, area===============

        resp_general['Вес'] = '<не указано>'
        resp_general['Объем'] = '<не указано>'
        resp_general['Длина'] = '<не указано>'
        resp_general['Площадь'] = '<не указано>'

        ЕдиницаИзмерения = resp_general['Единица хранения']

        if resp_general['ВесИспользовать']:
            ВесЗнаменатель = resp_general['ВесЗнаменатель']
            ВесЧислитель = resp_general['ВесЧислитель']
            ВесЕдиницаИзмерения = resp_general['ВесЕдиницаИзмерения_Key']
            resp_general['Вес'] = f'{ВесЗнаменатель} {ЕдиницаИзмерения} весит {ВесЧислитель} {ВесЕдиницаИзмерения}'

        if resp_general['ОбъемИспользовать']:
            ОбъемЗнаменатель = resp_general['ОбъемЗнаменатель']
            ОбъемЧислитель = resp_general['ОбъемЧислитель']
            ОбъемЕдиницаИзмерения = resp_general['ОбъемЕдиницаИзмерения_Key']
            resp_general['Объем'] = f'{ОбъемЗнаменатель} {ЕдиницаИзмерения} весит {ОбъемЧислитель} {ОбъемЕдиницаИзмерения}'
        if resp_general['ДлинаИспользовать']:
            ДлинаЗнаменатель = resp_general['ДлинаЗнаменатель']
            ДлинаЧислитель = resp_general['ДлинаЧислитель']
            ДлинаЕдиницаИзмерения = resp_general['ДлинаЕдиницаИзмерения_Key']
            resp_general['Длина'] = f'{ДлинаЗнаменатель} {ЕдиницаИзмерения} весит {ДлинаЧислитель} {ДлинаЕдиницаИзмерения}'
        if resp_general['ПлощадьИспользовать']:
            ПлощадьЗнаменатель = resp_general['ПлощадьЗнаменатель']
            ПлощадьЧислитель = resp_general['ПлощадьЧислитель']
            ПлощадьЕдиницаИзмерения = resp_general['ПлощадьЕдиницаИзмерения_Key']
            resp_general['Площадь'] = f'{ПлощадьЗнаменатель} {ЕдиницаИзмерения} весит {ПлощадьЧислитель} {ПлощадьЕдиницаИзмерения}'


        #======================================

    tbl_dse_erp_view = self.ui.tbl_dse_erp_view
    tbl_dse_erp_view.setStyleSheet(CQT.ERP_CSS)
    filter_resp = []
    for k, v in DICT_REPLACE_NAMES.items():
        if v in resp_general:
            filter_resp.append({'Параметр': v, 'Значение': resp_general[v]} )
        else:
            if v in headers and options[headers[v]]:
                filter_resp.append({'Параметр': f'-        {v}', 'Значение': ''})
    #main_data = F.sort_by_column_c(filter_resp, 'Параметр')
    CQT.fill_wtabl(filter_resp,tbl_dse_erp_view, height_row=24,ogr_maxshir_kol=500,selectionBehavior='SelectRows',count_rows_cell_max=-1,load_links=True)



@CQT.onerror
def click_row_strukt(self: mywindow):
    tbl = self.ui.tbl_red_tree
    row = CQT.get_dict_line_form_tbl(tbl)
    art = row['Код ERP']
    self.ui.le_art_before.setText(art)


@CQT.onerror
def kmass_apply(self: mywindow):
    def check():

        if before == '':
            CQT.blink_obj_c(self, 2, self.ui.le_kmass_before, 'Не указана масса аналога')
            return False
        if not F.is_numeric(before):
            CQT.blink_obj_c(self, 2, self.ui.le_kmass_before, 'Масса аналога не число')
            return False
        if F.valm(before) == 0:
            CQT.blink_obj_c(self, 2, self.ui.le_kmass_before, 'Масса аналога не может быть 0')
            return False
        if after == '':
            CQT.blink_obj_c(self, 2, self.ui.le_kmass_after, 'Не указана масса ткп')
            return False
        if not F.is_numeric(after):
            CQT.blink_obj_c(self, 2, self.ui.le_kmass_after, 'Масса ткп не число')
            return False

        return True

    after = self.ui.le_kmass_after.text()
    before = self.ui.le_kmass_before.text()
    if not check():
        return
    if self.ui.chk_change_mass.checkState() == 1:
        CQT.msgbox(f'Не выбран режим простановки масс')
        return
    delta = round(F.valm(after) / F.valm(before), 3)
    if self.ui.chk_change_mass.checkState() == 2:
        if not CQT.msgboxgYN(
                f'Обновить ВСЕ массы и коэффициенты норм, с учетом коэфф масс = {delta}?'):
            return
    else:
        if not CQT.msgboxgYN(
                f'Обновить только коэффициенты норм, с учетом коэфф масс = {delta}?'):
            return

    tbl = self.ui.tbl_red_tree
    for i in range(tbl.rowCount()):
        row = CQT.get_dict_line_form_tbl(tbl, i)
        if row['ПКИ'] == '0':
            if self.ui.chk_change_mass.checkState() == 2:
                if row['Масса/М1,М2,М3'] != '':
                    line_mass = row['Масса/М1,М2,М3'].split("/")
                    val = line_mass[0]
                    new_val = str(round(F.valm(val) * delta, 2))
                    if len(line_mass) > 2:
                        CQT.set_val_tbl_by_name(tbl, i, 'Масса/М1,М2,М3',
                                                '/'.join([new_val, line_mass[1], line_mass[2]]))
            if row['Уд_количество_аналог'] != '':
                new_val = str(round(F.valm(row['Уд_количество_аналог']) * delta, 2))
                CQT.set_val_tbl_by_name(tbl, i, 'Уд_количество_аналог', new_val)
            if row['Коэфф_длины_швов'] != '':
                new_val = str(round(F.valm(row['Коэфф_длины_швов']) * delta, 2))
                CQT.set_val_tbl_by_name(tbl, i, 'Коэфф_длины_швов', new_val)
    recalc_weight(self)


@CQT.onerror
def replace_arts(self: mywindow):
    def check():
        if self.ui.le_art_after.text().strip() == '':
            CQT.blink_obj_c(self, 2, self.ui.le_art_after, 'Не указан артикул(Код)')
            return False
        if self.ui.le_art_after.text() not in self.Data_mes.dict_nomenklat_by_kod:
            CQT.blink_obj_c(self, 2, self.ui.le_art_after, 'Артикул(Код) не найден в БД')
            return False
        # if self.ui.le_art_before.text().strip() == '': #04.09.25
        #     CQT.blink_obj_c(self, 2, self.ui.le_art_before, 'Не указан артикул(Код)')
        #     return False
        return True

    if not check():
        return
    if not CQT.msgboxgYN(
            f'Заменить ВСЕ материалы с Артикулом {self.ui.le_art_before.text()}  на Артикул {self.ui.le_art_after.text()}?'):
        return
    mat = self.Data_mes.dict_nomenklat_by_kod[self.ui.le_art_after.text()]
    sort = mat['Наименование']
    tbl = self.ui.tbl_red_tree
    is_empty = self.ui.le_art_before.text().strip() == ''
    selected_rows = {item.row() for item in tbl.selectedItems()}
    if is_empty:
        for row in selected_rows:
            list_mat_before = row['Масса/М1,М2,М3'].split('/')

            CQT.set_val_tbl_by_name(tbl, row, 'Масса/М1,М2,М3', '/'.join([list_mat_before[0], sort]))
            CQT.set_val_tbl_by_name(tbl, row, 'Код ERP', self.ui.le_art_after.text())
    else:
        for i in range(tbl.rowCount()):
            row = CQT.get_dict_line_form_tbl(tbl, i)
            if row['Код ERP'] == self.ui.le_art_before.text():
                list_mat_before = row['Масса/М1,М2,М3'].split('/')

                CQT.set_val_tbl_by_name(tbl, i, 'Масса/М1,М2,М3', '/'.join([list_mat_before[0], sort]))
                CQT.set_val_tbl_by_name(tbl, i, 'Код ERP', self.ui.le_art_after.text())
    recalc_weight(self)


class CalculationAnalog:
    fields = (
        'le_udk_len_a',
        'le_udk_wid_a',
        'le_udk_diam_a_nar',
        'le_udk_diam_a_vn',
    )
    del_fields = (
        'le_udk_len',
        'le_udk_wid',
        'le_udk_diam_nar',
        'le_udk_diam_vn',
    )

    def __init__(self, obj, default_values=None):
        self.calculation = defaultdict(dict)
        if default_values:
            self.calculation.update(default_values)
        self.obj = obj.ui
        self.selected = []

    def save_calculation(self, row):
        for field in self.fields:
            text = getattr(self.obj, field).text()
            self.calculation[row][field] = text

    def view_calculation(self, row):
        data = self.calculation.get(row)
        for field in self.fields:
            text = ''
            attr = getattr(self.obj, field)
            if data:
                text = data[field]
            attr.setText(text)

    def item_selection(self):
        self.selected = [item.topRow() for item in self.obj.tbl_red_tree.selectedRanges()]
        # self.selected = self.obj.tbl_red_tree.selectedRanges()
        for field in self.del_fields:
            attr = getattr(self.obj, field)
            attr.setText('')


@CQT.onerror
def calc_udk(self: mywindow):
    try:
        len_dse = F.valm(self.ui.le_udk_len.text())
        len_dse_a = F.valm(self.ui.le_udk_len_a.text())
        width_dse = F.valm(self.ui.le_udk_wid.text())
        width_dse_a = F.valm(self.ui.le_udk_wid_a.text())
        koef = len_dse / len_dse_a * width_dse / width_dse_a
        self.ui.lbl_udk_rez.setText(str(round(koef, 2)))
    except:
        self.ui.lbl_udk_rez.setText('0')
    recalc_weight(self)


@CQT.onerror
def art_repl(self: mywindow):
    pass


@CQT.onerror
def calc_udk_d(self: mywindow):
    try:
        diam_dse_nar = F.valm(self.ui.le_udk_diam_nar.text())
        diam_dse_vn = F.valm(self.ui.le_udk_diam_vn.text())
        diam_dse_a_nar = F.valm(self.ui.le_udk_diam_a_nar.text())
        diam_dse_a_vn = F.valm(self.ui.le_udk_diam_a_vn.text())
        pl = diam_dse_nar ** 2 * 3.14 / 4 - diam_dse_vn ** 2 * 3.14 / 4
        pl_a = diam_dse_a_nar ** 2 * 3.14 / 4 - diam_dse_a_vn ** 2 * 3.14 / 4
        koef = pl / pl_a
        self.ui.lbl_udk_rez.setText(str(round(koef, 2)))
    except:
        self.ui.lbl_udk_rez.setText('0')
    recalc_weight(self)

def clear_add_info(self: mywindow):
    self.ui.le_add_naim.clear()
    self.ui.le_add_nn.clear()
    self.ui.chk_pki.setCheckState(1)


@CQT.onerror
def add_row(self: mywindow):
    cur_row = self.ui.tbl_anal_dse.currentRow()
    if cur_row == -1:
        CQT.msgbox(f'Не выбран ДСЕ')
        return
    tabl_cr_stukt = self.ui.tbl_red_tree
    if tabl_cr_stukt.currentRow() == -1:
        q_strok = 0
        q_column = 1
    else:
        q_strok = tabl_cr_stukt.currentRow() + 1
        q_column = tabl_cr_stukt.currentColumn()

    if self.ui.chk_pki.checkState() == 1:
        CQT.msgbox(f'Не вырбан статус ПКИ')
        return
    if self.ui.le_add_nn.text().strip() == '' and self.ui.chk_pki.checkState() == 0:  # dse
        CQT.msgbox(f'Не указано Обозначение(НН)')
        return

    if self.ui.le_add_naim.text().strip() == '':
        CQT.msgbox(f'Не указано Наименование')
        return

    pki_name = 'Да'
    pki_val = '1'
    if self.ui.chk_pki.checkState() == 2:  # pki
        self.ui.le_add_nn.setText(F.shifr(self.ui.le_add_naim.text().strip())[:13])
    if self.ui.chk_pki.checkState() == 0:
        pki_name = 'Нет'
        pki_val = '0'

    if not CQT.msgboxgYN(f'Добавить строку {self.ui.le_add_naim.text()} {self.ui.le_add_nn.text()} ПКИ  = {pki_name}'):
        return

    spisok = CQT.list_from_wtabl_c(tabl_cr_stukt, "", True)
    if len(spisok) == 0:
        spisok = [self.hat_c]

    idx_lvl = F.num_col_by_name_in_hat_c(spisok, 'Уровень')
    level = spisok[q_strok][idx_lvl]
    tmp_row = ['' for _ in spisok[0]]
    tmp_row[F.num_col_by_name_in_hat_c(spisok, 'Наименование')] = self.ui.le_add_naim.text()
    tmp_row[F.num_col_by_name_in_hat_c(spisok, 'Обозначение')] = self.ui.le_add_nn.text()
    tmp_row[F.num_col_by_name_in_hat_c(spisok, 'Количество')] = '1'
    tmp_row[F.num_col_by_name_in_hat_c(spisok, 'ID')] = str(F.get_time_shtamp_c())[:14]
    tmp_row[F.num_col_by_name_in_hat_c(spisok, 'ПКИ')] = pki_val
    tmp_row[idx_lvl] = level
    spisok.insert(q_strok + 1, tmp_row)
    fill_tbl_strukt(self, spisok)

    tabl_cr_stukt.setCurrentCell(q_strok, q_column)
    apply_dse(self, False)
    clear_add_info(self)
    recalc_weight(self)


@CQT.onerror
def red_tree_del_knot(self: mywindow):
    tabl_cr_stukt = self.ui.tbl_red_tree
    if tabl_cr_stukt.currentRow() == -1:
        CQT.msgbox('Не выбрана позиция в МК')
        return

    q_strok = tabl_cr_stukt.currentRow()
    q_column = tabl_cr_stukt.currentColumn()
    lvl_col = CQT.num_col_by_name_c(tabl_cr_stukt, 'Уровень')
    lvl = tabl_cr_stukt.item(q_strok, CQT.num_col_by_name_c(tabl_cr_stukt, 'Уровень')).text()
    if lvl == '':
        CQT.msgbox(f'Уровень строки не укзаан')
        return
    if not F.is_numeric(lvl):
        CQT.msgbox(f'Уровень указан не корректно')
        return

    spisok = CQT.list_from_wtabl_c(tabl_cr_stukt, "", True)
    spisok_tmp = spisok.copy()
    k = 0
    spisok.pop(q_strok + 1)
    k += 1
    ur = int(lvl)
    for i in range(q_strok + 2, len(spisok_tmp)):
        if spisok_tmp[i][lvl_col] == '':
            CQT.msgbox(f'Уровень строки {i} не укзазан')
            return
        if int(spisok_tmp[i][lvl_col]) > ur:
            spisok.pop(i - k)
            k += 1
        else:
            break
    tabl_cr_stukt.blockSignals(True)
    change = CQT.list_from_wtabl_c(self.ui.tbl_red_tree, "", True, rez_dict=True)
    fill_tbl_strukt(self, spisok)

    if len(spisok) > 1:
        tabl_cr_stukt.setCurrentCell(q_strok, q_column)
        fill_tab_to_level(self.ui.tbl_red_tree)
        accumulate_tree_mass(self)
        fill_tab_to_level(tabl_cr_stukt)
    tabl_cr_stukt.setCurrentCell(-1, 0)
    recalc_weight(self)
    tabl_cr_stukt.blockSignals(False)


@CQT.onerror
def red_tree_save(self: mywindow):
    path = CMS.load_tmp_path('btn_save_analog')

    dir = CQT.f_dialog_save(self, 'Сохранить структуру', path, '*.pickle')
    if dir == '.':
        return
    CMS.save_tmp_path('btn_save_analog', dir, True)
    spis = CQT.list_from_wtabl_c(self.ui.tbl_red_tree, hat_c=True, rez_dict=True, only_visible=False)
    data = {'ver': 2, 'list_table': spis, 'heads': {
        'path_vo': self.ui.le_path_vo_2.text(),
        'name_tkp': self.ui.le_name_tkp_2.text(),
        'nn_izd': self.ui.le_nnom_izd_2.text(),
        'vid_napr': self.ui.cmb_vid_napr.currentText(),
        'calculation': self.calculation.calculation
    }}
    F.save_file_pickle(dir, data)


@CQT.onerror
def red_tree_load(self: mywindow):
    path = CMS.load_tmp_path('btn_save_analog')
    dir = CQT.f_dialog_name(self, 'Загрузить структуру', path, '*.pickle')
    if dir == '.':
        return
    CMS.save_tmp_path('btn_save_analog', dir, True)
    data = F.load_file_pickle(dir)
    spis = None
    if isinstance(data, list):
        spis = data
        if len(spis[0]) != len(self.hat_c):
            CQT.msgbox(f'Не соответствует структура')
            return
        fl_differ = True
        for i in range(len(self.hat_c)):
            if self.hat_c[i] not in spis[0]:
                fl_differ = False
                break
        if not fl_differ:
            CQT.msgbox(f'Не соответствует структура')
            return
        self.ui.le_path_vo_2.setText('')
        self.ui.le_name_tkp_2.setText('')
        self.ui.le_nnom_izd_2.setText('')
        self.ui.cmb_vid_napr.setCurrentText('')
    if isinstance(data, dict):
        if data.get('Структура'):
            spis = data['Структура']
        else:
            if 'ver' not in data:
                CQT.msgbox(f'Формат файлй не корректный')
                return
            spis = data['list_table']
            self.ui.le_path_vo_2.setText(data['heads']['path_vo'])
            self.ui.le_name_tkp_2.setText(data['heads']['name_tkp'])
            self.ui.le_nnom_izd_2.setText(data['heads']['nn_izd'])
            self.ui.cmb_vid_napr.setCurrentText(data['heads']['vid_napr'])
            calculation = data['heads'].get('calculation', {})
            setattr(self, 'calculation', CalculationAnalog(self, calculation))
    if spis == None:
        return
    if spis:
        hat_c_loaded = set(spis[0].keys())
        tbl = self.ui.tbl_red_tree
        hat_c_main = {tbl.horizontalHeaderItem(col).text() for col in range(tbl.columnCount())}
        dif = hat_c_main.difference(hat_c_loaded)
        if dif:
            spis = [
                {hat: '', **elem} for hat in dif
                for elem in spis
            ]
    spis = check_knot(self, spis)
    fill_tbl_strukt(self, spis)
    fill_tab_to_level(self.ui.tbl_red_tree)
    recalc_weight(self)


@CQT.onerror
def red_tree_move(self: mywindow, operator):
    tabl_cr_stukt = self.ui.tbl_red_tree
    selected_rows = {item.row() for item in tabl_cr_stukt.selectedItems()}
    tabl_cr_stukt.clearSelection()
    tabl_cr_stukt.blockSignals(True)
    nk_lvl = CQT.num_col_by_name_c(tabl_cr_stukt, 'Уровень')
    if not selected_rows:
        CQT.msgbox('Не выбрана позиция')
        return
    for row in sorted(selected_rows):
        if row == 0:
            return
        tabl_cr_stukt.setRowHidden(row, tabl_cr_stukt.isRowHidden(operator(row, 1)))
        for col in range(tabl_cr_stukt.columnCount()):
            cur_item = tabl_cr_stukt.takeItem(row, col)
            swap_item = tabl_cr_stukt.takeItem(operator(row, 1), col)
            if col == nk_lvl:
                cur_item.setText(swap_item.text())
            tabl_cr_stukt.setItem(operator(row, 1), col, cur_item)
            tabl_cr_stukt.setItem(row, col, swap_item)
    accumulate_tree_mass(self)
    fill_tab_to_level(self.ui.tbl_red_tree)
    tabl_cr_stukt.blockSignals(False)
    for row in sorted(selected_rows):
        for col in range(tabl_cr_stukt.columnCount()):
            self.ui.tbl_red_tree.item(operator(row, 1), col).setSelected(True)


@CQT.onerror
def clear_mat(self: mywindow, *args):
    tbl = self.ui.tbl_red_tree
    weight_nk = CQT.num_col_by_name_c(tbl, 'Масса/М1,М2,М3')
    if tbl.currentRow() == -1: return CQT.msgbox('Не выбрана позиция')
    target_item = tbl.item(tbl.currentRow(), weight_nk)
    weight_m1_m2 = target_item and tbl.item(tbl.currentRow(), weight_nk).text()
    unpack_weight = weight_m1_m2.split('/')
    new_text = unpack_weight[0] if len(unpack_weight) >= 1 else 0
    target_item.setText(new_text)


@CQT.onerror
def add_row_branch(self: mywindow, *args):
    tbl = self.ui.tbl_red_tree
    lvl_nk = CQT.num_col_by_name_c(tbl, 'Уровень')
    if tbl.currentRow() == -1: return CQT.msgbox('Не выбрана родительская позиция')
    target_item = tbl.item(tbl.currentRow(), lvl_nk)
    level = target_item and tbl.item(tbl.currentRow(), lvl_nk).text()
    if not F.is_numeric(level): return
    data = CQT.list_from_wtabl_c(tbl, rez_dict=True)
    new_data = [''] * tbl.columnCount()
    new_data[lvl_nk] = int(level) + 1
    data[tbl.currentRow() + 1] = new_data
    fill_tbl_strukt(self, data)

def rollback(self: mywindow, tbl):
    # CQT.RollBackUserChangesDelegator.
    ...

def add_stack_row(self, tbl):
    ...

@CQT.onerror
def mat_apply(self: mywindow, val: str, name: str, kod: str):
    tbl = self.ui.tbl_red_tree
    selected_row = tbl.currentRow()
    if selected_row == -1:
        CQT.msgbox(f'Не выбрана строка в структуре')
        return
    nn = CQT.valt(tbl, 'Обозначение', selected_row)
    nf_mat = CQT.num_col_by_name_c(tbl, 'Масса/М1,М2,М3')
    nf_kod = CQT.num_col_by_name_c(tbl, 'Код ERP')

    if kod == '':
        kod = tbl.item(selected_row, nf_kod).text()
        if kod not in self.Data_mes.dict_nomenklat_by_kod:
            CQT.msgbox(f'Код {kod} отсутствует в номенклатуре, нужно выбрать материал заново')
            return
        name = self.Data_mes.dict_nomenklat_by_kod[kod]['Наименование']

    else:
        if not CQT.msgboxgYN(f'Заменить {tbl.item(selected_row, nf_mat).text()} на {val + "/" + name}'):
            return
    if CQT.msgboxgYN(f'Применить ко всем строкам с обозначением: {nn!r}'):
        sync_row_materials(self, nn, val, name, kod)
    tbl.item(selected_row, nf_mat).setText(val + "/" + name)
    tbl.item(selected_row, nf_kod).setText(kod)
    accumulate_tree_mass(self)
    fill_tab_to_level(tbl)
    recalc_weight(self)
    CQT.msgbox(f'Успешно')
    CQT.select_cell(tbl, selected_row, nf_mat)

@CQT.onerror #08.09.25
def mat_apply_2(self: mywindow, replace_weight: bool = False, replace_material: bool = False):
    tbl_struct = self.ui.tbl_red_tree
    tbl_mats = self.ui.tbl_anal_mat
    # колонки материалов
    nf_naim = CQT.num_col_by_name_c(tbl_mats, 'Наименование')
    nf_kod = CQT.num_col_by_name_c(tbl_mats, 'Код')

    # колонки структуры
    st_nn_column = CQT.num_col_by_name_c(tbl_struct, 'Обозначение')
    st_mat_column = CQT.num_col_by_name_c(tbl_struct, 'Масса/М1,М2,М3')
    st_code_column = CQT.num_col_by_name_c(tbl_struct, 'Код ERP')

    current_row_materials = tbl_mats.currentRow()

    selected_rows = {item.row() for item in tbl_struct.selectedItems()}
    if len(selected_rows) == 0: # Если строка в изменяемой структуре не выбрана
        return CQT.msgbox(f'Не выбрана строка в структуре')
    changes = []
    if replace_weight:
        val = self.ui.le_norma.text()
        changes.append(val)
        if not F.is_numeric(val): # Если масса из lineedit не число
            return CQT.msgbox(f'Норма не число')
    if replace_material:
        name_mat = tbl_mats.item(current_row_materials, nf_naim).text()
        changes.append(name_mat)
        if current_row_materials == -1:
            return CQT.msgbox(f'Не выбран материал')

    new_val = '/'.join(changes)
    if not CQT.msgboxgYN(f'Применить значение {new_val!r}\n к всем выделенным строкам'):
        return
    for current_row_struct in selected_rows:
        st_nn_value = tbl_struct.item(current_row_struct, st_nn_column).text()
        st_code_value = tbl_struct.item(current_row_struct, st_code_column).text()
        st_mass_value = tbl_struct.item(current_row_struct, st_mat_column).text()

        if replace_material:
            name_mat = tbl_mats.item(current_row_materials, nf_naim).text()
            kod_mat = tbl_mats.item(current_row_materials, nf_kod).text()
        else:
            name_mat = ''
            if st_code_value:
                name_mat = self.Data_mes.dict_nomenklat_by_kod[st_code_value]['Наименование']
            kod_mat = st_code_value

        if not replace_weight:
            split_mass = st_mass_value.split('/')
            val = '0'
            if len(split_mass) > 0:
                val = st_mass_value.split('/')[0]
        if self.ui.chk_mat_for_all.isChecked():
            sync_row_materials(self, st_nn_value, val, name_mat, kod_mat)
        tbl_struct.item(current_row_struct, st_mat_column).setText(val + "/" + name_mat)
        tbl_struct.item(current_row_struct, st_code_column).setText(kod_mat)
        accumulate_tree_mass(self)
        fill_tab_to_level(tbl_struct)
    recalc_weight(self)
    for row in selected_rows:
        for col in range(tbl_struct.columnCount()):
            tbl_struct.item(row, col).setSelected(True)
    CQT.msgbox(f'Успешно')

def sync_row_materials(self: mywindow, target_nn: str, val: str, name: str, kod: str):
    tbl = self.ui.tbl_red_tree
    # if target_nn in self.Data_mes.dict_dse:
    lst_dse = CQT.list_from_wtabl_c(tbl, rez_dict=True)
    cp_lst = copy.deepcopy(lst_dse)
    for idx, dse in enumerate(cp_lst):
        if 'Обозначение' in dse and dse['Обозначение'] == target_nn:
            lst_dse[idx]['Масса/М1,М2,М3'] = '/'.join((val, name))
            lst_dse[idx]['Код ERP'] = kod
    fill_tbl_strukt(self, lst_dse)


@CQT.onerror
def apply_dse(self: mywindow, check=True):
    cur_row = self.ui.tbl_anal_dse.currentRow()
    if cur_row == -1:
        CQT.msgbox(f'Не выбран ДСЕ')
        return
    nf_dse_name_db = CQT.num_col_by_name_c(self.ui.tbl_anal_dse, 'Наименование')
    nf_dse_nn_db = CQT.num_col_by_name_c(self.ui.tbl_anal_dse, 'Номенклатурный_номер')
    nf_dse_path_db = CQT.num_col_by_name_c(self.ui.tbl_anal_dse, 'Путь_docs')
    nf_note_db = CQT.num_col_by_name_c(self.ui.tbl_anal_dse, 'Примечание')
    naim_db = self.ui.tbl_anal_dse.item(cur_row, nf_dse_name_db).text()
    nn_db = self.ui.tbl_anal_dse.item(cur_row, nf_dse_nn_db).text()
    dse_path_db = self.ui.tbl_anal_dse.item(cur_row, nf_dse_path_db).text()
    note_db = self.ui.tbl_anal_dse.item(cur_row, nf_note_db).text()
    note_db = note_db.split("(ОГК: ")[-1].split(")")[0]
    tbl = self.ui.tbl_red_tree
    selected_row = tbl.currentRow()
    if selected_row == -1:
        CQT.msgbox(f'Не выбрана строка в структуре')
        return
    nf_dse_name = CQT.num_col_by_name_c(tbl, 'Наименование_аналог')
    nf_dse_nn = CQT.num_col_by_name_c(tbl, 'Обозначение_аналог')
    nf_dse_path = CQT.num_col_by_name_c(tbl, 'Ссылка')
    nf_note = CQT.num_col_by_name_c(tbl, 'Примечание')
    if check:
        if not CQT.msgboxgYN(f'Установить {naim_db} {nn_db} в качестве налога для'
                             f' {tbl.item(selected_row, nf_dse_name).text()} {tbl.item(selected_row, nf_dse_nn).text()}?'):
            return
    tbl.item(selected_row, nf_dse_name).setText(naim_db)
    tbl.item(selected_row, nf_dse_nn).setText(nn_db)
    tbl.item(selected_row, nf_dse_path).setText(dse_path_db)
    if note_db: # 11.09.25
        tbl.item(selected_row, nf_note).setText(note_db)
    recalc_weight(self)
    CQT.msgbox(f'Успешно')


@CQT.onerror
def mat_apply_wout_mat(self: mywindow):
    val = self.ui.le_norma.text()
    if not F.is_numeric(val):
        CQT.msgbox(f'Норма не число')
        return
    mat_apply(self, str(round(F.valm(val), 2)).replace(",", '.'), "", '')
    recalc_weight(self)


@CQT.onerror
def mat_apply_mat(self: mywindow):
    val = self.ui.le_norma.text()
    if not F.is_numeric(val):
        CQT.msgbox(f'Норма не число')
        return
    cur_row = self.ui.tbl_anal_mat.currentRow()
    if cur_row == -1:
        CQT.msgbox(f'Не выбран материал')
        return
    nf_naim = CQT.num_col_by_name_c(self.ui.tbl_anal_mat, 'Наименование')
    nf_kod = CQT.num_col_by_name_c(self.ui.tbl_anal_mat, 'Код')
    name_mat = self.ui.tbl_anal_mat.item(cur_row, nf_naim).text()
    kod_mat = self.ui.tbl_anal_mat.item(cur_row, nf_kod).text()
    mat_apply(self, str(round(F.valm(val), 2)).replace(",", '.'), name_mat, kod_mat)
    recalc_weight(self)


@CQT.onerror
def change_mat(self: mywindow):
    cur_row = self.ui.tbl_anal_mat.currentRow()
    cur_row_anal = self.ui.tbl_red_tree.currentRow()
    if cur_row == -1:
        CQT.msgbox(f'Не выбран материал')
        return
    if cur_row_anal == -1:
        return
    nf_naim = CQT.num_col_by_name_c(self.ui.tbl_anal_mat, 'Наименование')
    nf_kod = CQT.num_col_by_name_c(self.ui.tbl_anal_mat, 'Код')
    if None in (nf_naim, nf_kod):
        return
    col_mass_anal = CQT.num_col_by_name_c(self.ui.tbl_red_tree, 'Масса/М1,М2,М3')
    name_mat = self.ui.tbl_anal_mat.item(cur_row, nf_naim).text()
    kod_mat = self.ui.tbl_anal_mat.item(cur_row, nf_kod).text()
    mass_mat = self.ui.tbl_red_tree.item(cur_row_anal, col_mass_anal).text()
    val = round(F.valm(mass_mat.split("/")[0]), 3)
    mat_apply(self, str(round(F.valm(val), 2)).replace(",", '.'), name_mat, kod_mat)
    recalc_weight(self)


@CQT.onerror
def load_mats(self: mywindow):
    CQT.fill_wtabl(self.Data_mes.list_nomenklat, self.ui.tbl_anal_mat, set_editeble_col_nomera={})
    self.ui.tbl_anal_mat.hideColumn(CQT.num_col_by_name_c(self.ui.tbl_anal_mat, 'Ref_Key'))
    CMS.fill_filtr_c(self, self.ui.tbl_anal_mat_filtr, self.ui.tbl_anal_mat, hidden_scroll=True)
    CMS.update_width_filtr(self.ui.tbl_anal_mat, self.ui.tbl_anal_mat_filtr)
    self.ui.tbl_anal_dse.setSelectionBehavior(1)
    self.ui.tbl_anal_dse.setSelectionMode(1)
    self.ui.tbl_anal_dse.setSortingEnabled(True)
    self.ui.tbl_anal_mat.setToolTip('Нажмите F5 чтобы обновить')


@CQT.onerror
def load_vids(self: mywindow):
    self.ui.cmb_vid_napr.clear()
    i = 0
    start_cmb_value = 'Для начала работы выберите вид'
    self.ui.cmb_vid_napr.addItem(start_cmb_value)
    for _ in self.Data_mes.dict_vid_napr.keys():
        self.ui.cmb_vid_napr.addItem(_)
        self.ui.cmb_vid_napr.setItemData(i, self.Data_mes.dict_vid_napr[_]['Примечание'], QtCore.Qt.ToolTipRole)
        i += 1
    self.ui.cmb_vid_napr.setCurrentText(start_cmb_value)


@CQT.onerror
def load_dse(self: mywindow):
    CQT.fill_wtabl(self.Data_mes.list_dse, self.ui.tbl_anal_dse, set_editeble_col_nomera={})
    CMS.fill_filtr_c(self, self.ui.tbl_anal_dse_filtr, self.ui.tbl_anal_dse, hidden_scroll=True)
    CMS.update_width_filtr(self.ui.tbl_anal_dse, self.ui.tbl_anal_dse_filtr)
    self.ui.tbl_anal_mat.setSelectionBehavior(1)
    self.ui.tbl_anal_mat.setSelectionMode(1)
    self.ui.tbl_anal_mat.setSortingEnabled(True)


@CQT.onerror
def prepare_tbl_red_stukt(self: mywindow):
    tabl_cr_stukt = self.ui.tbl_red_tree
    tabl_cr_stukt.clearContents()
    tabl_cr_stukt.setRowCount(0)
    self.hat_c = ['b', 'Наименование', 'Обозначение', 'Количество', 'Ед.изм.', 'Масса/М1,М2,М3', 'Ссылка',
                  'ID', 'Количество на изделие', 'Примечание', 'ПКИ', 'Сумм.Количество', 'Код ERP',
                  'Наименование_аналог', 'Обозначение_аналог', 'Уд_количество_аналог', 'Коэфф_длины_швов', '_5', '_6'
        , 'dreva_kod', 'Кол. по заявке', 'Уровень']
    tabl_cr_stukt.setColumnCount(len(self.hat_c))

    tabl_cr_stukt.setHorizontalHeaderLabels(self.hat_c)
    # tabl_cr_stukt.resizeColumnsToContents()
    for column_name in ('_5', '_6', 'dreva_kod', 'ID'):
        try:
            tabl_cr_stukt.setColumnHidden(CQT.num_col_by_name_c(tabl_cr_stukt, column_name), True)
        except Exception as e:
            ...
    # tabl_cr_stukt.setColumnHidden(7, True)
    # tabl_cr_stukt.setColumnHidden(10, True)
    CQT.set_color_sort_cell_table_c(tabl_cr_stukt)
    tabl_cr_stukt.horizontalHeader().setStretchLastSection(True)
    tabl_cr_stukt.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
    delegator = CQT.RollBackUserChangesDelegator(tabl_cr_stukt, self)
    tabl_cr_stukt.setItemDelegate(delegator)
    # self.edit_cr_mk = {2, 5, 8, 14,15, 19, 20}
    self.edit_cr_mk = {3, 6, 9, 10, 15, 16, 20, 21}
    self.calculation = CalculationAnalog(self)
    # recalc_weight(self)


"""def get_convert_di(li):
    levels = []
    for i in li:
        levels.append(int(i['Уровень']))
    min_val = min(levels)
    di = {}
    for i in range(10):
        di[min_val] = i
        min_val +=1
    return di"""


def get_convert_di(li):
    levels = []
    for i in li:
        levels.append(int(i['Уровень']))
    min_val = min(levels)
    di = {}
    for i in range(10):
        di[min_val] = i
        min_val += 1

    for i in li:
        i['Уровень'] = di[int(i['Уровень'])]
    return li

@CQT.onerror
def fill_tab_to_level(table: QtWidgets.QTableWidget):
    table.blockSignals(True)

    def btn_action(row, col):
        table.blockSignals(True)  # блок событий на время нажатия кнопки иначе recalc
        btn = table.cellWidget(row, 0)
        level_col = CQT.num_col_by_name_c(table, 'Уровень')
        previous = int(table.item(row, level_col).text())
        if btn.text() == '-':
            for row_idx in range(row + 1, table.rowCount()):
                current_level = int(table.item(row_idx, level_col).text())
                if previous >= current_level: break
                table.setRowHidden(row_idx, True)
            btn.setText('+')
        else:
            for row_idx in range(row + 1, table.rowCount()):
                current_level = int(table.item(row, level_col).text())
                if previous > current_level: break
                table.setRowHidden(row_idx, False)
            btn.setText('-')
        QtWidgets.QApplication.processEvents()
        table.blockSignals(False)  # блок событий на время нажатия кнопки иначе recalc

    data = CQT.list_from_wtabl_c(table, rez_dict=True)
    tree_obj = TreeKnotList(data)

    for row_idx, obj in enumerate(tree_obj):
        lvl_nk = CQT.num_col_by_name_c(table, 'Наименование')
        row_item = table.item(row_idx, lvl_nk)
        level = obj.level
        tabs = '      ' * level
        row_item.setText(tabs + row_item.text().strip())
        gray_value = 130 + ((level + 1) * 25)
        if obj.is_root:
            btn_text = '+' if obj.child and table.isRowHidden(row_idx + 1) else '-'
            font = QtGui.QFont()
            font.setBold(True)
            font.setPixelSize(16)
            CQT.add_btn(table, row_idx, 0, btn_text, conn_func_checked_row_col=btn_action)
            table.cellWidget(row_idx, 0).setFont(font)
            CQT.set_color_row_wtab_c(table, row_idx, gray_value, gray_value, gray_value)
        else:
            CQT.set_color_row_wtab_c(table, row_idx, 255, 255, 255)
    table.blockSignals(False)

@CQT.onerror
def accumulate_tree_mass(self: mywindow, previous: int = 0, row: int = None, col: int = None):
    data = CQT.list_from_wtabl_c(self.ui.tbl_red_tree, "", True, rez_dict=True)
    tree_knot_object = TreeKnotList(data)
    data = tree_knot_object.calc_knot()
    fill_tbl_strukt(self, data)
    # CMS.load_column_widths(self, self.ui.tbl_red_tree)
    return data


def change_lvl(self: mywindow, operator) -> None:
    tabl_cr_strukt = self.ui.tbl_red_tree

    row = tabl_cr_strukt.currentRow()
    if row == -1:
        CQT.msgbox('Чтобы изменить уровень, нужно выделить строчку')
        return
    num_col_lvl = CQT.num_col_by_name_c(tabl_cr_strukt, 'Уровень')
    selected_rows = [item.topRow() for item in tabl_cr_strukt.selectedRanges()]
    for row in sorted(selected_rows):
        current_level = tabl_cr_strukt.item(row, num_col_lvl).text()
        if current_level == '0':
            CQT.msgbox('Нельзя менять главный корень')
            return
        tabl_cr_strukt.selectRow(row)
        current_item = tabl_cr_strukt.item(row, num_col_lvl)
        current_item.setText(str(operator(int(current_level), 1)))


class TreeKnotBranch:
    def __init__(self, parent, **kwargs):
        self.item = kwargs
        self.parent: 'TreeKnotBranch' = parent
        self.child: 'TreeKnotBranch' = None
        self.summ = self.count * self.mass

    @property
    def level(self):
        level = self.item.get('Уровень')
        if F.is_numeric(level):
            return int(level)
        return self.parent.level if self.parent else 0

    @property
    def count(self):
        count = self.item.get('Количество')
        if count and F.is_numeric(count):
            return F.valm(count)
        CQT.msgbox('Количество не число')
        return 1

    @property
    def mass(self):
        text = self.item.get('Масса/М1,М2,М3', '')
        lst = text.split('/')
        if len(lst[0]) >= 1 and F.is_numeric(lst[0]):
            return F.valm(lst[0]) #09.09.25
        return float()

    @property
    def root_summ(self):
        summ = float()
        cur_child = self.child
        while cur_child and cur_child.level > self.level:
            if not cur_child.is_root:
                summ += cur_child.summ
            cur_child = cur_child.child
        return summ

    @property
    def is_root(self):
        return self.child and self.child.level > self.level

    def calc_children(self):
        child = self.child
        child_lvl = child.level
        sum = 0
        if self.level == 0:
            print()
        while child:
            if child.level == child_lvl:
                mass = child.mass
                if not child.is_root:
                    mass *= child.count
                sum += mass
            child = child.child
            if not child or self.level >= child.level: break
        return sum


class TreeKnotList:
    __lst = []

    def __init__(self, data):
        self.__lst = []
        prev = None
        for item in data:
            inst = TreeKnotBranch(parent=prev, **item)
            if prev:
                prev.child = inst
            prev = inst
            self.__lst.append(inst)

    def __getitem__(self, item):
        return self.__lst[item]

    def __len__(self):
        return len(self.__lst)

    def __iter__(self):
        return iter(self.__lst)

    def calc_knot(self):
        for branch in self.__lst:
            summ = branch.mass
            if branch and branch.is_root:
                summ = branch.root_summ
            cp_item = branch.item.copy()
            mass_m1_m2 = cp_item.get('Масса/М1,М2,М3')
            mass = mass_m1_m2.split('/')
            if len(mass) > 1:
                mass[0] = str(summ)
            else:
                mass = [str(summ)]
            branch.item['Масса/М1,М2,М3'] = '/'.join(mass)
        return self.calc_roots()

    def to_list(self):
        return [b.item for b in self]

    def calc_roots(self):
        cp_lst = self.to_list()
        for idx, item in reversed(list(enumerate(self.__lst))):
            if item.is_root:
                key_mass = 'Масса/М1,М2,М3'
                mass_m1_m2 = item.item.get(key_mass, '').split('/')
                if len(mass_m1_m2) > 1:
                    mass_m1_m2[0] = str(item.calc_children() * item.count)
                else:
                    mass_m1_m2 = [str(item.calc_children() * item.count)]
                cp_lst[idx][key_mass] = '/'.join(mass_m1_m2)
        return cp_lst


def check_tree_on_type_tkp(window: mywindow):
    tbl: QtWidgets.QTableWidget = window.ui.tbl_red_tree
    tab_widget: QtWidgets.QTabWidget = window.ui.tabWidget
    cmb: QtWidgets.QComboBox = window.ui.cmb_vid_napr
    previous = cmb.property('previous')
    current = cmb.currentText()
    disable_interface = current.strip() in ('', 'Для начала работы выберите вид')
    window.ui.fr_left.setDisabled(disable_interface)
    if tab_widget.tabText(tab_widget.currentIndex()) == 'Структура':
        if previous is not None and previous != current and tbl.rowCount() > 1:
            if CQT.msgboxgYN('Вы уверены что хотите сменить направление?\nВ случае согласия таблица аналога будет очищена'):
                tbl.setRowCount(0)
            else:
                cmb.setCurrentText(previous)
    cmb.setProperty('previous', current)

def check_knot(self, struct):
    spisok = copy.deepcopy(struct)
    for i in range(len(spisok)):
        spisok[i]['ID'] = spisok[i]['ID'].split('_')[0] + f'_{str(i)}'
        nn_analogue = spisok[i]['Обозначение_аналог'].strip()
        if nn_analogue and nn_analogue in self.Data_mes.dict_dse:
            nn = self.Data_mes.dict_dse.get(nn_analogue) or {}
            spisok[i]['Наименование_аналог'] = nn.get('Наименование', '')
        else:
            spisok[i]['Наименование_аналог'] = spisok[i]['Наименование'].strip()
            spisok[i]['Обозначение_аналог'] = spisok[i]['Обозначение'].strip()

        norma = 0
        if '/' in spisok[i]['Масса/М1,М2,М3']:
            if F.is_numeric(spisok[i]['Масса/М1,М2,М3'].split("/")[0]):
                norma = str(round(F.valm(spisok[i]['Масса/М1,М2,М3'].split("/")[0]), 3))

        spisok[i]['Код ERP'] = spisok[i]['Код ERP'].strip()
        if spisok[i]['Код ERP'] != "":
            name_mat = f"Материал {spisok[i]['Код ERP']} не найден"
            if spisok[i]['Код ERP'] in self.Data_mes.dict_nomenklat_by_kod:
                name_mat = self.Data_mes.dict_nomenklat_by_kod[spisok[i]['Код ERP']]['Наименование']
            else:
                print(f"Материал {spisok[i]['Код ERP']} не найден")
            spisok[i]['Масса/М1,М2,М3'] = '/'.join([str(norma), name_mat])

        if spisok[i]['Обозначение_аналог'].strip() not in self.Data_mes.dict_dse:
            spisok[i]['Обозначение_аналог'] = 'Не найден в БД'
            spisok[i]['Наименование_аналог'] = 'Не найден в БД'
    return spisok

@CQT.onerror
def get_knot(self: mywindow):
    def add_level_for_expansion_tree(added: list, base_lvl: int, lvl_column: int):
        lst_to_add = added.copy()
        root_lvl = lst_to_add[1][lvl_column]
        counter = 0
        for element in lst_to_add[1:]:
            current_lvl = element[lvl_column]
            if root_lvl < current_lvl:
                counter += 1
            if root_lvl > current_lvl:
                counter -= 1
            root_lvl = current_lvl
            element[lvl_column] = int(base_lvl) + counter
        return lst_to_add

    tabl_cr_stukt = self.ui.tbl_red_tree
    tree = self.ui.tree_base_tree

    if tree.currentIndex().row() == -1 or tabl_cr_stukt.rowCount() > 1 and tabl_cr_stukt.currentRow() == -1:
        CQT.msgbox('Не выбран узел')
        return
    item = tree.currentItem()
    if item == None:
        return
    nk = CQT.num_col_by_name_c(tree, 'ID')
    current_ID = item.text(nk)
    sp_tree = CQT.list_from_tree_c(tree, hat_c=True)
    flag_naid = -1
    for i in range(len(sp_tree)):
        if sp_tree[i][nk] == current_ID:
            flag_naid = i
            break
    if flag_naid == -1:
        CQT.msgbox("Не найден выбранный узел")
        return

    q_strok = tabl_cr_stukt.currentRow() + 1
    q_column = tabl_cr_stukt.currentColumn()
    spisok = CQT.list_from_wtabl_c(tabl_cr_stukt, "", True, rez_dict=True)

    nk_level_c = F.num_col_by_name_in_hat_c(sp_tree, 'Уровень')

    dict_zamen = {'Ссылка на объект DOCs': 'Ссылка', 'Покупное изделие': 'ПКИ', 'Обозначение': 'Обозначение2',
                  'Обозначение полное': 'Обозначение'}

    for i in range(len(sp_tree[0])):
        for key in dict_zamen.keys():
            if sp_tree[0][i] == key:
                sp_tree[0][i] = dict_zamen[key]
    current_row_anal = tabl_cr_stukt.currentRow()
    if current_row_anal != -1 and accumulate_tree_mass(self) is None:
        CQT.msgbox('Перед добавлением новых элементов исправьте структуру добавленных уровней')
        return

    col_lvl_anal = CQT.num_col_by_name_c(tabl_cr_stukt, 'Уровень')
    base_lvl = 0

    list_to_add = [sp_tree[0]]
    ur = int(sp_tree[flag_naid][nk_level_c])
    list_to_add.append(sp_tree[flag_naid])

    for i in range(flag_naid + 1, len(sp_tree)):
        if int(sp_tree[i][nk_level_c]) <= ur:
            break
        list_to_add.append(sp_tree[i])
    if current_row_anal != -1:
        base_lvl = int(tabl_cr_stukt.item(current_row_anal, col_lvl_anal).text())
        list_to_add = add_level_for_expansion_tree(list_to_add, base_lvl, nk_level_c)
    dict_to_add = F.list_to_dict(list_to_add)

    for item in dict_to_add[::-1]:
        tmp_dict = dict()
        for key in self.hat_c:
            if key in item:
                tmp_dict[key] = item[key]
            else:
                tmp_dict[key] = ''
        if tmp_dict['Масса/М1,М2,М3'].split('/')[1] == '':
            koeff = '1'
            if F.is_numeric(item.get('Коэфф_длины_швов')):
                koeff = item.get('Коэфф_длины_швов')
            tmp_dict['Коэфф_длины_швов'] = koeff
            tmp_dict['Уд_количество_аналог'] = ''
        else:
            koeff = '1'
            if F.is_numeric(item.get('Уд_количество_аналог')):
                koeff = item.get('Уд_количество_аналог')
            tmp_dict['Уд_количество_аналог'] = koeff
            tmp_dict['Коэфф_длины_швов'] = ''
        spisok.insert(q_strok, tmp_dict)

    spisok = get_convert_di(spisok)
    spisok = check_knot(self, spisok)
    spisok = [{'b': '', **elem} for elem in spisok]
    fill_tbl_strukt(self, spisok)
    accumulate_tree_mass(self)
    fill_tab_to_level(tabl_cr_stukt)
    recalc_weight(self)

def hide_columns_for_simple_mode(self, tabl_cr_stukt):
    current_type = self.ui.cmb_vid_napr.currentText()
    if current_type == '':
        CQT.blink_obj_c(self, 2, self.ui.cmb_vid_napr, 'Сначала необходимо выбрать тип')
        return
    is_simple = CMS.check_possibility_statistic_calc_tkp(current_type)
    exclude_columns = (
        'Наименование_аналог',
        'Обозначение_аналог',
        'Уд_количество_аналог',
        'Коэфф_длины_швов'
    )
    for col in exclude_columns:
        num = CQT.num_col_by_name_c(tabl_cr_stukt, col)
        if num is not None:
            tabl_cr_stukt.setColumnHidden(num, bool(is_simple)) # 04.09.25 Критическая ошибка
    tabl_cr_stukt.setProperty('is_simple', is_simple)


@CQT.onerror
def load_xml(self: mywindow):
    self.TIP_NEGRUZ_DSE = ('Сборочный чертёж', 'Изделие проекта', 'Монтажный чертёж', 'Материал', 'Материалы')

    path = CMS.load_tmp_path('btn_load_xml')

    file_select = CQT.f_dialog_name(self, 'Выбор xml', path, '*.xml')
    if file_select == '.':
        return
    CMS.save_tmp_path('btn_load_xml', file_select, True)
    xml = XML.spisok_iz_xml(file_select)
    spis_xml = CMS.podgotovka_xml(self, xml, show_negruz=True)
    if spis_xml == None:
        CQT.msgbox('Файл не корректный')
        return
    err_flag = False
    msg_text = ''
    for i in range(len(spis_xml)):
        if 'Тип' not in spis_xml[i]['data']:
            err_flag = True
            msg_text = f'Отсутствует поле Тип'
        if spis_xml[i]['data']['Наименование'] == "" and spis_xml[i]['data']['Обозначение полное'] == "":
            err_flag = True
            msg_text = f'Наименование  и  Обозначение полное ПУСТО'
        if spis_xml[i]['data']['Количество'] == "" or spis_xml[i]['data']['Количество на изделие'] == "":
            msg_text = f'Количество  и  Количество на изделие ПУСТО'
            err_flag = True
    if err_flag == True:
        CQT.msgbox(f'Файл XML имеет ошибки \n{msg_text}\n работать с ним нельзя!')
        return

    list_user = CMS.load_tree(self, spis_xml, self.ui.tree_base_tree)

    CMS.zapoln_tree_spiskom(self, spis_xml, list_user, self.ui.tree_base_tree)
    for _ in range(0, 8):
        self.ui.tree_base_tree.resizeColumnToContents(_)
    recalc_weight(self)