from __future__ import annotations

import math
import re
import traceback
import os
from pathlib import Path

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ

from dataclasses import dataclass

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TehKart import mywindow2
import project_cust_38.Cust_Qt as CQT
from project_cust_38 import Cust_xl_formul as CXLF
from project_cust_38 import Cust_config as CFG

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QWidget, QTableWidget, QVBoxLayout

if __name__ == '__main__':
    exit()


class DataPreparater:
    # упрощеный обработчик для полей без пред установленных значений
    def __init__(self, arr_tmp) -> None:
        self.arr_tmp = arr_tmp
        self.SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    def get_arr(self, val):
        for key in self.SLOV_ZAMEN.keys():
            self.arr_tmp[-1][F.num_col_by_name_in_hat_c(self.arr_tmp, val)] = self.arr_tmp[-1][
                F.num_col_by_name_in_hat_c(self.arr_tmp, val)].replace(key, self.SLOV_ZAMEN[key])
        return self.arr_tmp[-1][F.num_col_by_name_in_hat_c(self.arr_tmp, val)].split(";")


class GetFromDataclass():
    # обработчик для предустановленных значений
    def __init__(self, ima_operacii, arr_tmp) -> None:
        self.arr_tmp = arr_tmp
        self.ima_operacii = ima_operacii

    def get(self, name):
        if self.arr_tmp[1][F.num_col_by_name_in_hat_c(self.arr_tmp, name)] == '+':
            return 0
        if name in Data_oper_norm.DICT_OPERS_CALC[self.ima_operacii]:
            if Data_oper_norm.DICT_OPERS_CALC[self.ima_operacii][name]['type'] == 'int':
                print(f"{name} - {Data_oper_norm.DICT_OPERS_CALC[self.ima_operacii][name]['type']}")
                return int(F.valm(self.arr_tmp[1][F.num_col_by_name_in_hat_c(self.arr_tmp, name)]))
            if Data_oper_norm.DICT_OPERS_CALC[self.ima_operacii][name]['type'] == 'float':
                print(f"{name} - {Data_oper_norm.DICT_OPERS_CALC[self.ima_operacii][name]['type']}")
                return F.valm(self.arr_tmp[1][F.num_col_by_name_in_hat_c(self.arr_tmp, name)])
            if Data_oper_norm.DICT_OPERS_CALC[self.ima_operacii][name]['type'] == 'str':
                print(f"{name} - {Data_oper_norm.DICT_OPERS_CALC[self.ima_operacii][name]['type']}")
                return str(self.arr_tmp[1][F.num_col_by_name_in_hat_c(self.arr_tmp, name)])
        else:
            CQT.msgbox(f'{name} не найден в БД')
            return False

class ConfigMeta(type):
    def __new__(cls, *args, **kwargs):
        """Инициализация конфигураций"""
        new_cls = super().__new__(cls, *args, **kwargs)
        from project_cust_38 import Cust_config as CFG
        org_name = CFG.Config.user_config.Organization['Значение']
        if org_name:
            db_naryad = CFG.Config.project.db_naryad
            response = CSQ.custom_request_c(db_naryad, f'SELECT poki FROM places WHERE Имя = {org_name!r}', rez_dict=True, one=True)
            if 'poki' in response:
                return cls.init_config(new_cls, str(response.get('poki')))

    @staticmethod
    def init_config(new_cls, poki):
        cash = Path(F.scfg('cash'))
        new_cls.CASH = str(cash)
        new_cls.CASH_WITH_POKI = str(cash / poki)
        return new_cls


class OperationConfig(metaclass=ConfigMeta):
    CASH: str # Z:\Data\TehKart\Data\bin
    CASH_WITH_POKI: str # Z:\Data\TehKart\Data\bin\1

    @classmethod
    def operation_table_path(cls, operation: str, pereh: str = ''):
        return str(Path(cls.CASH_WITH_POKI) / 'tables' / operation / pereh)


def vremya_tsht_perehodi(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    try:
        if type(arr_tmp) == dict:
            arr_tmp = F.list_of_dicts_to_list_of_lists([arr_tmp])
        if type(arr_tmp_parent) == dict:
            arr_tmp_parent = F.list_of_dicts_to_list_of_lists([arr_tmp_parent])[1]
        vrema = 0
        for i in range(len(arr_tmp[0])):
            have_data_type = arr_tmp[0][i].split(":")
            if len(have_data_type) > 1 and have_data_type[1] in ('int', 'str', 'float'):
                arr_tmp[0][i] = arr_tmp[0][i].split(":")[0]
        obj = CXLF.XlFormula()
        is_xl = obj.check_per(ima_operacii, ima_perehoda, approved=True)
        op_obj = Operations(arr_tmp)
        if not arr_tmp[1]: return 0
        params = op_obj.convert_params()
        if obj.check_approved(operation=ima_operacii, pereh=ima_perehoda) and not is_xl:
            CQT.msgbox(f'Не возможно расчитать переход: {ima_perehoda}\n из-за недоступности сервера')
            return
        for param in params:
            if is_xl:
                head = arr_tmp[0] if len(arr_tmp) > 0 else []
                vrema += obj.client.srv_pereh_calc(oper_name=ima_operacii, pereh_name=ima_perehoda, params=[head, param])
                continue
            if CFG.Config.place.poki == 1:
                return
            if ima_operacii == 'Фрезерная':
                if ima_perehoda == 'Фрезеровать плоскость с точностью _,глубиной _, длиной _':
                    vrema = frezerovnie_ploskosti(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Фрезеровать уступ глубиной  _, длиной  _, шириной  _ и фрезой диаметром  _':
                    vrema = frezerovnie_ustupa(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Установить деталь _ переустановить деталь _ снять деталь':
                    vrema = vspomogatelnoe(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Фрезеровать шпоночный паз на глубину  _, длиной  _':
                    vrema = frezerovnie_shponki(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
            if ima_operacii == 'Токарная':
                if ima_perehoda == 'Торцевать':
                    vrema = butting(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Нарезать внутреннюю резьбу':
                    vrema = toch_vnutr_rezb(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Нарезать наружную резьбу':
                    vrema = toch_nar_rezb(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Нарезать трапецеидальную резьбу':
                    vrema = trapezoidal_carving(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Центрование торцов':
                    vrema = centering_ends(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Обработать фаски галтели':
                    vrema = toch_fask(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Наружная черновая обработка':
                    vrema = external_roughing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Наружная чистовая обработка':
                    vrema = external_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Наружная получистовая обработка':
                    vrema = external_sub_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Внутреняя черновая обработка':
                    vrema = internal_roughing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Внутреняя чистовая обработка':
                    vrema = internal_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Внутреняя получистовая обработка':
                    vrema = internal_sub_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Отрезать':
                    vrema = toch_otrez(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Прорезать наружный паз':
                    vrema = toch_nar_paz(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Сверлить отверстие':
                    vrema = toch_sverl_otv(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Точить внутреннюю поверхность':
                    vrema = toch_vnutr_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Точить наружную поверхность':
                    vrema = toch_nar_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Установить_переустановить_снять деталь':
                    vrema = toch_ust_pereust_sn_det(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
            if ima_operacii == 'Токарно-карусельная':
                if ima_perehoda == 'Точить вертикальную поверхность':
                    vrema = tochkar_vert_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Точить горизонтальную поверхность':
                    vrema = tochkar_gor_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
                if ima_perehoda == 'Установить_переустановить_снять деталь':
                    vrema = tochkar_ust_pereust_sn_det(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
        return round(vrema, 3)

    except ArithmeticError as e:
        description = {
            ZeroDivisionError: 'Деление на ноль',
            OverflowError: 'Значение выходит за рамки допустимого',
            FloatingPointError: 'Некорректная работа с дробью'
        }
        msg = (
            f'Произошла ошибка во время операции: {ima_operacii}\n'
            f'С именем перехода: {ima_perehoda}\n'
            f'Предположительно: {description[e.__class__]}'
        )
        CQT.msgbox(msg)
        return
    except TypeError as e:
        reg = re.compile(r"\[F\.num_col_by_name_in_hat_c\(.*,(.*)\)\]")
        trace = traceback.format_tb(e.__traceback__)[0]
        args = reg.findall(trace)
        if args and isinstance(args[0], str):
            msg = (
                f'Произошла ошибка во время операции: {ima_operacii}\n'
                f'С именем перехода: {ima_perehoda}\n'
                f'Не найдено: {args[0]}'
            )
            CQT.msgbox(msg)
            return
        else:
            raise e
    return round(vrema, 3)


def tochkar_ust_pereust_sn_det(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Способ установки')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Способ установки')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Масса')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Необходимость применения приспособления')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Необходимость применения приспособления')].replace(key,
                                                                                                    SLOV_ZAMEN[key])

    arr_spos_ust = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Способ установки')].split(";")
    mass = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса')]
    arr_prisp = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Необходимость применения приспособления')].split(";")
    ima_table_v = 'table1.txt'
    summa_vremeni = 0
    if len(arr_spos_ust) == len(arr_prisp):
        for i in range(len(arr_spos_ust)):
            spos_ust = F.valm(arr_spos_ust[i])
            prisp = F.valm(arr_prisp[i])
            if spos_ust == 1:
                tvy = table(put + os.sep + ima_table_v, mass)
            else:
                tvy = 19.3
            tp = 0
            if prisp == 1:
                tp = 176
            tsht = tvy + tp
            summa_vremeni += tsht
    else:
        return 0
    return summa_vremeni


def tochkar_gor_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)
    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина прохода инструмента')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина прохода инструмента')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Начальная_толщина')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Начальная_толщина')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Конечная_толщина')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Конечная_толщина')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид_обработки')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид_обработки')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_обработки')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_обработки')].replace(key, SLOV_ZAMEN[key])

    arr_dl_proh_inst = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина прохода инструмента')].split(";")
    arr_tol_nach = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Начальная_толщина')].split(";")
    arr_tol_kon = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Конечная_толщина')].split(";")
    mat = F.valm(arr_tmp_parent[1])
    oborud = F.valm(arr_tmp_parent[0])
    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид_обработки')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_обработки')].split(";")

    summa_vremeni = 0
    if len(arr_dl_proh_inst) == len(arr_tol_nach):
        for i in range(len(arr_dl_proh_inst)):
            l = F.valm(arr_dl_proh_inst[i])
            H = F.valm(arr_tol_nach[i])
            h = F.valm(arr_tol_kon[i])
            D = F.valm(arr_diam[i])
            s = 0.18 if oborud == 2 else 0.2
            ima_table_v = 'table1.txt' if oborud == 2 else 'table2.txt'
            v = table(put + os.sep + ima_table_v, str(mat), D)
            q = table(put + os.sep + 'table3.txt', str(mat), str(oborud))
            n = F.round_up(F.valm(arr_sort_c[i]) + (H - h) / (2 * q))
            tsht = l * n / (s * v)
            summa_vremeni += tsht
    else:
        return 0
    return summa_vremeni


def tochkar_vert_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина прохода инструмента')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина прохода инструмента')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нач')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нач')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_кон')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_кон')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид_обработки')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид_обработки')].replace(key, SLOV_ZAMEN[key])
    arr_dl_proh_inst = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина прохода инструмента')].split(";")
    arr_diam_nach = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нач')].split(";")
    arr_diam_kon = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_кон')].split(";")
    mat = F.valm(arr_tmp_parent[1])
    oborud = F.valm(arr_tmp_parent[0])
    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид_обработки')].split(";")
    summa_vremeni = 0
    if len(arr_dl_proh_inst) == len(arr_diam_nach):
        for i in range(len(arr_dl_proh_inst)):
            l = F.valm(arr_dl_proh_inst[i])
            D = F.valm(arr_diam_nach[i])
            d = F.valm(arr_diam_kon[i])
            s = 0.18 if oborud == 2 else 0.2
            ima_table_v = 'table1.txt' if oborud == 2 else 'table2.txt'
            v = table(put + os.sep + ima_table_v, str(mat), D)
            q = table(put + os.sep + 'table3.txt', str(mat), str(oborud))
            n = F.round_up(F.valm(arr_sort_c[i]) + (D - d) / (2 * q))
            tsht = l * n / (s * v)
            summa_vremeni += tsht
    else:
        return 0
    return summa_vremeni


def find_time_carving(input_di, need_step, diametr, lenth, len_li: list):
    # обработчик для словарей резьб
    len_pluce = 5
    for step, step_li in input_di.items():
        if step == need_step:
            for params_tup, time_li in step_li.items():
                if params_tup[0] <= diametr <= params_tup[1]:
                    current_hundred = len_li[-1] // 100
                    len_li.extend([val * 100 for val in range(current_hundred + 1, current_hundred + len_pluce + 1, 1)])
                    new_li = {len_li[index]: val for index, val in enumerate(time_li)}
                    res = new_li.get(lenth)
                    if res:
                        return res
                    else:
                        if lenth % 100 == 0 and len(params_tup) > 2:
                            find_len = list(new_li.keys())
                            hundred = lenth - find_len[-1]
                            hundred = hundred // 100
                            summ = hundred * params_tup[2]
                            find_val = list(new_li.values())
                            return find_val[-1] + summ

                        else:
                            return 0
    return 0


def toch_vnutr_rezb(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид нарезаемой резьбы')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид нарезаемой резьбы')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв.')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв.')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина резьбы')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина резьбы')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Точность резьбы')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Точность резьбы')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэфф_мат')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Коэфф_мат')].replace(key, SLOV_ZAMEN[key])
        # arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp,'Шаг_резьбы')] = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp,'Шаг_резьбы')].replace(key, SLOV_ZAMEN[key])

    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид нарезаемой резьбы')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв.')].split(";")
    arr_dlina = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина резьбы')].split(";")
    arr_tochnost = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Точность резьбы')].split(";")
    arr_koef = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэфф_мат')].split(";")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_sort_c):
        for i in range(len(arr_sort_c)):
            vid = F.valm(arr_sort_c[i])
            if vid == 1:
                putf = put + F.sep() + 'table1.txt'
            elif vid == 2:
                putf = put + F.sep() + 'table2.txt'
            elif vid == 3:
                putf = put + F.sep() + 'table3.txt'
            elif vid == 4:
                putf = put + F.sep() + 'table4.txt'

            diam = F.valm(arr_diam[i])
            dlina = F.valm(arr_dlina[i])
            tochnost = F.valm(arr_tochnost[i])
            koef = F.valm(arr_koef[i])

            vremya_shtuchnoe = table(putf, diam, dlina)
            summa_vremeni += vremya_shtuchnoe * tochnost * koef

    else:
        return 0
    return summa_vremeni


def trapezoidal_carving(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # наружной трапециедальной  резьбы
    # Вид нарезаемой резьбы:int;Диаметр_отв.:int;Длина резьбы:int;Шаг_резьбы:int

    dp = DataPreparater(arr_tmp)
    arr_vid = dp.get_arr("Вид нарезаемой резьбы")
    arr_step = dp.get_arr("Шаг_резьбы")
    arr_diam = dp.get_arr("Диаметр_отв.")
    arr_dlina = dp.get_arr("Длина резьбы")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_vid):
        for i in range(len(arr_vid)):

            diam = F.valm(arr_diam[i])
            dlina = F.valm(arr_dlina[i])
            step = F.valm(arr_step[i])
            vid = F.valm(arr_vid[i])

            if vid == 1:  # наружной трапециедальной  резьбы  в упор
                upd_len = [100, 150, 200, 250, 300, 400, 500]
                summa_vremeni += find_time_carving(input_di=Data_oper_norm.TRAP_STOP, need_step=step, diametr=diam,
                                                   lenth=dlina, len_li=upd_len)
            elif vid == 2:  # наружной трапециедальной  резьбы напроход
                len_li = [100, 125, 150, 175, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
                summa_vremeni += find_time_carving(Data_oper_norm.TRAP_TROUGH, need_step=step, diametr=diam,
                                                   lenth=dlina, len_li=len_li)
            elif vid == 3:  # наружной трапециедальной  резьбы напроход
                len_li = [100, 125, 150, 175, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
                time = find_time_carving(Data_oper_norm.TRAP_TROUGH, need_step=step, diametr=diam, lenth=dlina,
                                         len_li=len_li)
                summa_vremeni += time * 1.3
    else:
        return 0
    return summa_vremeni


def centering_ends(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # центрование торцов
    # Диаметр торца:int;Количество торцов:int

    dp = DataPreparater(arr_tmp)
    arr_diam = dp.get_arr("Диаметр торца")
    arr_quantity = dp.get_arr("Количество торцов")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_quantity):
        for i in range(len(arr_diam)):
            diam = F.valm(arr_diam[i])
            quantity = F.valm(arr_quantity[i])

            time_one_detail = 1.1 if diam < 30 else 1.2 if diam < 50 else 1.3 if diam < 80 else 1.6 if diam < 120 else 1.8 if diam < 180 else 2.4 if diam < 260 else 3.5
            summa_vremeni += time_one_detail * quantity
    else:
        return 0
    return summa_vremeni


# def external_sub_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
#     # получистовая обработка ШАБЛОН!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#     # Начальный диаметр заготовки:int;Конечный диаметр:int;

#     dp = DataPreparater(arr_tmp)
#     arr_start_diam = dp.get_arr("Начальный диаметр заготовки")
#     arr_end_diam = dp.get_arr("Конечный диаметр")

#     summa_vremeni = 0
#     if len(arr_start_diam) == len(arr_end_diam):
#         for i in range(len(arr_start_diam)):

# am<50 else 1.3 if diam<80 else 1.6 if diam<120 else 1.8 if diam<180 else 2.4 if diam<260 else 3.5
#            summa_vremeni += time_one_detail* quantity
#     else:
#         return 0
#     return summa_vremeni


def get_di_for_internal_turning(steel, lenth, end_diam, sub_finishing=None, finishing=None, roughing=None):
    if roughing:
        if steel == 1:
            lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400]
            di = {
                30: {"25": 0.46, "50": 0.54, "75": 0.64, "100": 0.74},
                50: {"25": 0.56, "50": 0.7, "75": 0.85, "100": 1, "125": 1.4, "150": 1.55},
                75: {"25": 0.68, "50": 0.89, "75": 1.1, "100": 1.35, "125": 1.85, "150": 2.1, "200": 2.45, "250": 2.95},
                100: {"25": 0.73, "50": 1, "75": 1.3, "100": 1.6, "125": 2.15, "150": 2.45, "200": 2.9, "250": 3.5,
                      "300": 4.1},
                125: {"25": 0.84, "50": 1.2, "75": 1.65, "100": 2.1, "125": 2.75, "150": 3.2, "200": 3.8, "250": 4.7,
                      "300": 5.5, "350": 6.5, "400": 7.5},
                150: {"25": 0.88, "50": 1.3, "75": 1.75, "100": 2.25, "125": 2.95, "150": 3.5, "200": 4.2, "250": 5,
                      "300": 6, "350": 7, "400": 8},
                200: {"25": 1.05, "50": 1.6, "75": 2.25, "100": 2.95, "125": 3.35, "150": 4.6, "200": 5.5, "250": 7,
                      "300": 8.5, "350": 9.5, "400": 11},
                250: {"25": 1.1, "50": 1.8, "75": 2.5, "100": 3.3, "125": 4.3, "150": 5, "200": 6, "250": 8, "300": 9.5,
                      "350": 11, "400": 12.5},
                300: {"25": 1.25, "50": 2.1, "75": 3.05, "100": 4.1, "125": 5, "150": 6, "200": 7.5, "250": 9.5,
                      "300": 11.5, "350": 13.5, "400": 15.5},
                350: {"25": 1.45, "50": 2.5, "75": 3.65, "100": 4.9, "125": 6, "150": 7.5, "200": 9, "250": 12,
                      "300": 14, "350": 16.5, "400": 19},
                400: {"25": 1.55, "50": 2.75, "75": 4.05, "100": 5.5, "125": 6.5, "150": 8.5, "200": 10.5, "250": 13,
                      "300": 16, "350": 18.5, "400": 21},
            }
        else:
            lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 400]
            di = {
                50: {"25": 0.6, "50": 0.83, "75": 1.03, "100": 1.25},
                75: {"25": 0.73, "50": 0.98, "75": 1.25, "100": 1.55, "125": 2.1},
                100: {"25": 0.8, "50": 1.15, "75": 1.5, "100": 1.85, "125": 2.45, "150": 2.75},
                125: {"25": 1.05, "50": 1.5, "75": 1.95, "100": 2.45, "125": 3.2, "150": 3.8, "200": 4.6},
                150: {"25": 1.15, "50": 1.75, "75": 2.4, "100": 2.95, "125": 4.1, "150": 4.7, "200": 5.5},
                200: {"25": 1.25, "50": 2.05, "75": 2.85, "100": 3.55, "125": 4.8, "150": 5.5, "200": 6.5, "250": 8.5,
                      "300": 10, "350": 12},
                225: {"25": 1.45, "50": 2.4, "75": 3.35, "100": 4.25, "125": 5.5, "150": 6.5, "200": 8, "250": 10,
                      "300": 12, "350": 15},
                250: {"25": 1.65, "50": 2.85, "75": 4.05, "100": 5.5, "125": 7, "150": 8, "200": 10, "250": 12.5,
                      "300": 15, "350": 18.5},
            }
    if sub_finishing:
        if steel == 1:
            lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400]
            di = {
                30: {"25": 0.63, "50": 0.67, "75": 0.71, "100": 0.76},
                50: {"25": 0.71, "50": 0.78, "75": 0.85, "100": 0.93, "125": 1.3, "150": 1.4},
                75: {"25": 0.79, "50": 0.89, "75": 1, "100": 1.1, "125": 1.6, "150": 1.75, "200": 1.9, "250": 2.15},
                100: {"25": 0.82, "50": 0.96, "75": 1.1, "100": 1.25, "125": 1.8, "150": 1.95, "200": 2.2, "250": 2.5,
                      "300": 2.8},
                125: {"25": 1.25, "50": 1.4, "75": 1.6, "100": 1.8, "125": 2.3, "150": 2.5, "200": 2.75, "250": 3.15,
                      "300": 3.55, "350": 3.95, "400": 4.3},
                150: {"25": 1.3, "50": 1.5, "75": 1.7, "100": 2, "125": 2.5, "150": 2.8, "200": 3.15, "250": 3.65,
                      "300": 4.15, "350": 4.65, "400": 5},
                200: {"25": 1.35, "50": 1.6, "75": 1.9, "100": 2.2, "125": 2.8, "150": 3.15, "200": 3.6, "250": 4.2,
                      "300": 4.85, "350": 5.5, "400": 6},
                250: {"25": 1.4, "50": 1.7, "75": 2.1, "100": 2.5, "125": 3.15, "150": 3.6, "200": 4.15, "250": 4.9,
                      "300": 5.5, "350": 6.5, "400": 7},
                300: {"25": 1.45, "50": 1.9, "75": 2.35, "100": 2.85, "125": 3.6, "150": 4.15, "200": 4.85, "250": 6,
                      "300": 7, "350": 7.5, "400": 8.5},
                350: {"25": 1.5, "50": 1.95, "75": 2.45, "100": 2.95, "125": 3.75, "150": 4.3, "200": 5, "250": 6,
                      "300": 7, "350": 8, "400": 9},
                400: {"25": 1.55, "50": 2.1, "75": 2.7, "100": 3.35, "125": 4.2, "150": 4.9, "200": 5.5, "250": 7,
                      "300": 8.5, "350": 9.5, "400": 11},
            }
        else:
            lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 400]
            di = {
                50: {"25": 0.69, "50": 0.8, "75": 0.92},
                75: {"25": 0.73, "50": 0.92, "75": 1.05, "100": 1.25},
                100: {"25": 0.85, "50": 1.05, "75": 1.3, "100": 1.55, "125": 2.15},
                125: {"25": 0.89, "50": 1.2, "75": 1.45, "100": 1.8, "125": 2.45, "150": 2.75},
                150: {"25": 1.4, "50": 1.65, "75": 2, "100": 2.4, "125": 3.05, "150": 3.4},
                200: {"25": 1.45, "50": 1.8, "75": 2.25, "100": 2.7, "125": 3.45, "150": 3.9, "200": 4.6},
                225: {"25": 1.55, "50": 2, "75": 2.55, "100": 3.1, "125": 4, "150": 4.55, "200": 5.5, "250": 6.5,
                      "300": 7.5, "400": 8.5},
                250: {"25": 1.7, "50": 2.25, "75": 2.95, "100": 3.65, "125": 4.7, "150": 5.5, "200": 6.5, "250": 8,
                      "300": 9.5, "400": 10},
            }
    if finishing:
        if steel == 1:
            lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400]
            di = {
                30: {"25": 0.88, "50": 0.94, "75": 1, "100": 1.1},
                50: {"25": 0.94, "50": 1, "75": 1.1, "100": 1.2, "125": 1.75, "150": 1.85},
                75: {"25": 1.05, "50": 1.15, "75": 1.25, "100": 1.4, "125": 2, "150": 2.15, "200": 2.35, "250": 2.65},
                100: {"25": 1.05, "50": 1.2, "75": 1.35, "100": 1.55, "125": 2.2, "150": 2.35, "200": 2.6, "250": 2.95,
                      "300": 3.3},
                125: {"25": 1.55, "50": 1.75, "75": 1.95, "100": 2.15, "125": 2.9, "150": 3.15, "200": 3.45, "250": 3.9,
                      "300": 4.35, "350": 4.75},
                150: {"25": 1.6, "50": 1.85, "75": 2.1, "100": 2.35, "125": 3.2, "150": 3.45, "200": 3.85, "250": 4.4,
                      "300": 4.95, "350": 5.5, "400": 6},
                200: {"25": 1.65, "50": 1.95, "75": 2.3, "100": 2.65, "125": 3.5, "150": 3.85, "200": 4.35, "250": 5,
                      "300": 5.5, "350": 6.5, "400": 7},
                250: {"25": 1.75, "50": 2.1, "75": 2.2, "100": 2.95, "125": 3.9, "150": 4.35, "200": 5, "250": 6,
                      "300": 6.5, "350": 7.5, "400": 8.5},
                300: {"25": 1.85, "50": 2.25, "75": 2.8, "100": 3.35, "125": 4.45, "150": 4.95, "200": 6, "250": 7,
                      "300": 8, "350": 9, "400": 10},
                350: {"25": 1.95, "50": 2.5, "75": 3.15, "100": 3.85, "125": 4.8, "150": 5.5, "200": 6.5, "250": 8,
                      "300": 9.5, "350": 10.5, "400": 12},
                400: {"25": 2, "50": 2.55, "75": 3.3, "100": 4, "125": 5, "150": 6, "200": 7, "250": 8.5, "300": 10,
                      "350": 11.5, "400": 13},
                500: {"25": 2.1, "50": 2.8, "75": 3.65, "100": 4.55, "125": 6, "150": 7, "200": 8, "250": 10,
                      "300": 11.5, "350": 13.5, "": 15},
            }
        else:
            lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 400]
            di = {
                50: {"25": 0.91, "50": 1, "75": 1.1},
                75: {"25": 1, "50": 1.15, "75": 1.3, "100": 1.5},
                100: {"25": 1.15, "50": 1.35, "75": 1.6, "100": 1.85, "125": 2.6},
                125: {"25": 1.2, "50": 1.5, "75": 1.85, "100": 2.2, "125": 3, "150": 3.35, "200": 3.85},
                150: {"25": 1.8, "50": 2.15, "75": 2.6, "100": 3, "125": 4, "150": 4.45, "200": 5},
                200: {"25": 1.9, "50": 2.3, "75": 2.85, "100": 3.4, "125": 4.5, "150": 5, "200": 5.5, "250": 7,
                      "300": 8},
                225: {"25": 2.05, "50": 2.55, "75": 3.1, "100": 3.9, "125": 5, "150": 6, "200": 7, "250": 8, "300": 9.5,
                      "400": 11},
                250: {"25": 2.2, "50": 2.85, "75": 3.75, "100": 4.6, "125": 6, "150": 7, "200": 8, "250": 10,
                      "300": 11.5, "400": 13.5},
            }

    find_diam = 0
    for i in di.keys():
        if i >= end_diam:
            find_diam = i
            break
    if find_diam == 0:
        return 0

    sub_detail = di.get(find_diam)
    if not sub_detail:
        return 0

    find_lenth = 0
    for i in lenth_li:
        if i >= lenth:
            find_lenth = i
            break
    time_val = sub_detail.get(f"{find_lenth}")

    if time_val:
        return time_val
    else:
        return 0


def internal_roughing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # внутреняя черновая обработка
    # Вид стали:int;Начальный диаметр заготовки:int;Конечный диаметр:int;Длина прохода инструмента:int;

    dp = DataPreparater(arr_tmp)
    arr_steel_type = dp.get_arr("Вид стали")
    arr_start_diam = dp.get_arr("Начальный диаметр заготовки")
    arr_end_diam = dp.get_arr("Конечный диаметр")
    arr_lenth = dp.get_arr("Длина прохода инструмента")

    summa_vremeni = 0
    if len(arr_start_diam) == len(arr_end_diam):
        for i in range(len(arr_start_diam)):
            start_diam = F.valm(arr_start_diam[i])
            end_diam = F.valm(arr_end_diam[i])
            lenth = F.valm(arr_lenth[i])
            steel = F.valm(arr_steel_type[i])  # 1 черн 2 нерж

            T1 = get_di_for_internal_turning(steel=steel, lenth=lenth, end_diam=end_diam, roughing=True)
            step_quantity = abs(start_diam - end_diam) / 8
            tn = T1 * step_quantity

            Kd = 1.2 if start_diam / end_diam <= 0.7 else 1
            summa_vremeni += tn * Kd
    else:
        return 0
    return summa_vremeni


def internal_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # внутреняя чистовая обработка
    # Вид стали:int;Начальный диаметр заготовки:int;Конечный диаметр:int;Длина прохода инструмента:int;

    dp = DataPreparater(arr_tmp)
    arr_steel_type = dp.get_arr("Вид стали")
    arr_start_diam = dp.get_arr("Начальный диаметр заготовки")
    arr_end_diam = dp.get_arr("Конечный диаметр")
    arr_lenth = dp.get_arr("Длина прохода инструмента")

    summa_vremeni = 0
    if len(arr_start_diam) == len(arr_end_diam):
        for i in range(len(arr_start_diam)):
            start_diam = F.valm(arr_start_diam[i])
            end_diam = F.valm(arr_end_diam[i])
            lenth = F.valm(arr_lenth[i])
            steel = F.valm(arr_steel_type[i])  # 1 черн 2 нерж

            T1 = get_di_for_internal_turning(steel=steel, lenth=lenth, end_diam=end_diam, roughing=True)
            T2 = get_di_for_internal_turning(steel=steel, lenth=lenth, end_diam=end_diam, sub_finishing=True)
            T3 = get_di_for_internal_turning(steel=steel, lenth=lenth, end_diam=end_diam, finishing=True)
            step_quantity = abs(start_diam - end_diam) / 8
            tn = T1 * step_quantity + T2 + T3

            Kd = 1.2 if start_diam / end_diam <= 0.7 else 1
            summa_vremeni += tn * Kd
    else:
        return 0
    return summa_vremeni


def internal_sub_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # внутреняя получистовая обработка
    # Вид стали:int;Начальный диаметр заготовки:int;Конечный диаметр:int;Длина прохода инструмента:int;

    dp = DataPreparater(arr_tmp)
    arr_steel_type = dp.get_arr("Вид стали")
    arr_start_diam = dp.get_arr("Начальный диаметр заготовки")
    arr_end_diam = dp.get_arr("Конечный диаметр")
    arr_lenth = dp.get_arr("Длина прохода инструмента")

    summa_vremeni = 0
    if len(arr_start_diam) == len(arr_end_diam):
        for i in range(len(arr_start_diam)):
            start_diam = F.valm(arr_start_diam[i])
            end_diam = F.valm(arr_end_diam[i])
            lenth = F.valm(arr_lenth[i])
            steel = F.valm(arr_steel_type[i])  # 1 черн 2 нерж

            T1 = get_di_for_internal_turning(steel=steel, lenth=lenth, end_diam=end_diam, roughing=True)
            T2 = get_di_for_internal_turning(steel=steel, lenth=lenth, end_diam=end_diam, sub_finishing=True)
            step_quantity = abs(start_diam - end_diam) / 8
            tn = T1 * step_quantity + T2

            Kd = 1.2 if start_diam / end_diam <= 0.7 else 1
            summa_vremeni += tn * Kd
    else:
        return 0
    return summa_vremeni


def get_di_for_turning(steel, Kld, end_diam, lenth, sub_finishing=None, finishing=None, roughing=None):
    di = {}
    if sub_finishing:
        if steel == 1:
            if Kld <= 3:
                lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 700, 800, 900, 1000,
                            1100]
                di = {
                    20: {"25": 0.62, "50": 0.66, "75": 0.71},
                    30: {"25": 0.64, "50": 0.69, "75": 0.75, "100": 0.8},
                    50: {"25": 0.75, "50": 0.84, "75": 0.96, "100": 1.1, "125": 1.5, "150": 1.65},
                    75: {"25": 0.82, "50": 0.95, "75": 1.1, "100": 1.25, "125": 1.8, "150": 1.95, "200": 2.15,
                         "250": 2.45},
                    100: {"25": 0.86, "50": 1, "75": 1.2, "100": 1.4, "125": 1.95, "150": 2.15, "200": 2.45,
                          "250": 2.85, "300": 3.25},
                    125: {"25": 1.25, "50": 1.45, "75": 1.7, "100": 1.95, "125": 2.5, "150": 2.75, "200": 3.15,
                          "250": 3.65, "300": 4.1, "350": 4.6, "400": 5},
                    150: {"25": 1.35, "50": 1.6, "75": 1.9, "100": 2.2, "125": 2.8, "150": 3.1, "200": 3.6, "250": 4.2,
                          "300": 4.8, "350": 5.5, "400": 6, "450": 6.5},
                    200: {"25": 1.4, "50": 1.7, "75": 2, "100": 2.5, "125": 3.2, "150": 3.55, "200": 4.15, "250": 4.9,
                          "300": 5.5, "350": 6.5, "400": 7, "450": 8, "500": 8.5, "550": 10, "600": 10.5},
                    250: {"25": 1.5, "50": 1.85, "75": 2.35, "100": 2.8, "125": 3.6, "150": 4.1, "200": 4.85,
                          "250": 5.5, "300": 6.5, "350": 7.5, "400": 8.5, "450": 9.5, "500": 10.5, "550": 12, "600": 13,
                          "700": 14, "800": 16},
                    300: {"25": 1.6, "50": 2.1, "75": 2.7, "100": 3.3, "125": 4.25, "150": 4.85, "200": 6, "250": 7,
                          "300": 8, "350": 9.5, "400": 10.5, "450": 12, "500": 13, "550": 14.5, "600": 16, "700": 17.5,
                          "800": 20, "900": 22.5},
                    350: {"25": 1.7, "50": 2.35, "75": 3.1, "100": 3.9, "125": 4.9, "150": 5.5, "200": 7, "250": 8.5,
                          "300": 10, "350": 11.5, "400": 13, "450": 14.5, "500": 16, "550": 18, "600": 19.5, "700": 22,
                          "800": 25, "900": 28, "1000": 31, "1100": 34},
                    400: {"25": 1.9, "50": 2.65, "75": 3.6, "100": 4.6, "125": 6, "150": 7, "200": 8, "250": 10,
                          "300": 12, "350": 14, "400": 16, "450": 18, "500": 20, "550": 21.5, "600": 24, "700": 27,
                          "800": 30.6, "900": 34.5, "1000": 38.5, "1100": 42.5},
                }
            elif 3 < Kld <= 10:
                lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 700, 800, 900, 1000,
                            1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000]
                di = {
                    20: {"25": 0.64, "50": 0.68, "75": 0.73, "100": 0.79, "125": 1.05, "150": 1.1, "200": 1.2},
                    30: {"25": 0.66, "50": 0.72, "75": 0.8, "100": 0.88, "125": 1.2, "150": 1.25, "200": 1.4,
                         "250": 1.55, "300": 1.7},
                    50: {"25": 0.77, "50": 0.88, "75": 1, "100": 1.15, "125": 1.65, "150": 1.75, "200": 2, "250": 2.25,
                         "300": 2.55, "350": 2.85, "400": 3.15, "450": 3.4, "500": 3.7},
                    75: {"25": 0.88, "50": 1.05, "75": 1.3, "100": 1.5, "125": 2.1, "150": 2.35, "200": 2.7,
                         "250": 3.15, "300": 3.6, "350": 4, "400": 4.5, "450": 5, "500": 5.5, "550": 6, "600": 6.5,
                         "700": 7},
                    100: {"25": 0.93, "50": 1.15, "75": 1.45, "100": 1.75, "125": 2.4, "150": 2.7, "200": 3.1,
                          "250": 3.7, "300": 4.1, "350": 4.85, "400": 5.5, "450": 6, "500": 6.5, "550": 7, "600": 8,
                          "700": 8.5, "800": 10, "900": 11, "1000": 12},
                    125: {"25": 1.4, "50": 1.65, "75": 2, "100": 2.4, "125": 3, "150": 3.4, "200": 3.95, "250": 4.5,
                          "300": 5.5, "350": 6, "400": 7, "450": 7.5, "500": 8, "550": 9, "600": 10, "700": 11,
                          "800": 12.5, "900": 14, "1000": 15.5, "1100": 17.5, "1200": 19},
                    150: {"25": 1.45, "50": 1.8, "75": 2.25, "100": 2.7, "125": 3.5, "150": 3.9, "200": 4.6, "250": 5.5,
                          "300": 6.5, "350": 7.5, "400": 8, "450": 9, "500": 10, "550": 11, "600": 12, "700": 13.5,
                          "800": 15, "900": 17, "1000": 19, "1100": 21.5, "1200": 23.5, "1300": 25, "1400": 27,
                          "1500": 28.5},
                    200: {"25": 1.55, "50": 2, "75": 2.55, "100": 3.1, "125": 4, "150": 4.55, "200": 5.5, "250": 6.5,
                          "300": 7.5, "350": 9, "400": 10, "450": 11, "500": 12, "550": 13.5, "600": 14.5, "700": 16.5,
                          "800": 18.5, "900": 21, "1000": 23, "1100": 26.5, "1200": 28.5, "1300": 30, "1400": 33,
                          "1500": 35.5, "1600": 37.5, "1700": 40, "1800": 42, "1900": 44.5, "2000": 46.5},
                    250: {"25": 1.7, "50": 2.25, "75": 3, "100": 3.7, "125": 4.75, "150": 5.5, "200": 6.5, "250": 8,
                          "300": 9.5, "350": 11, "400": 12.5, "450": 13.5, "500": 15, "550": 17, "600": 18.5,
                          "700": 20.5, "800": 23.5, "900": 26, "1000": 29, "1100": 33, "1200": 36, "1300": 38.5,
                          "1400": 41.5, "1500": 44.5, "1600": 47.5, "1700": 50, "1800": 53, "1900": 56, "2000": 59},
                }
        else:
            lenth_li = [25, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600]
            di = {
                20: {"25": 0.67, "50": 0.74, "75": 0.83},
                30: {"25": 0.73, "50": 0.82, "75": 0.93},
                50: {"25": 0.76, "50": 0.87, "75": 1},
                75: {"25": 0.85, "50": 1, "75": 1.2, "100": 1.4},
                100: {"25": 0.9, "50": 1.1, "75": 1.35, "100": 1.6, "125": 2.2, "150": 2.45},
                125: {"25": 1.35, "50": 1.55, "75": 1.9, "100": 2.2, "125": 2.8, "150": 3.1},
                150: {"25": 1.1, "50": 1.7, "75": 2.1, "100": 2.45, "125": 3.15, "150": 3.55, "200": 4.1},
                175: {"25": 1.45, "50": 1.75, "75": 2.2, "100": 2.6, "125": 3.35, "150": 3.8, "200": 4.4, "250": 5,
                      "300": 6},
                200: {"25": 1.45, "50": 1.8, "75": 2.25, "100": 2.7, "125": 3.45, "150": 3.9, "200": 4.55, "250": 5.5,
                      "300": 6.5},
                225: {"25": 1.5, "50": 1.85, "75": 2.3, "100": 2.8, "125": 3.6, "150": 4.05, "200": 4.75, "250": 6,
                      "300": 7, "400": 8},
                250: {"25": 1.55, "50": 1.95, "75": 2.5, "100": 3, "125": 3.9, "150": 4.4, "200": 5, "250": 6.5,
                      "300": 7.5, "400": 9},
                300: {"25": 1.6, "50": 2.15, "75": 2.85, "": 3.5, "125": 4.5, "150": 5, "200": 6, "250": 7.5, "300": 9,
                      "400": 11, "500": 13.5, "600": 16.5},
                350: {"25": 1.7, "50": 2.3, "75": 3, "100": 3.8, "125": 4.85, "150": 5.5, "200": 6.5, "250": 8,
                      "300": 9.5, "400": 12, "500": 15, "600": 18.5},
                400: {"25": 1.8, "50": 2.5, "75": 3.4, "100": 4.25, "125": 5.5, "150": 6.5, "200": 7.5, "250": 9.5,
                      "300": 11, "400": 14, "500": 17.5, "600": 21.5},
                450: {"25": 2, "50": 2.8, "75": 3.8, "100": 5, "125": 6, "150": 7.5, "200": 8.5, "250": 11, "300": 12.5,
                      "400": 16, "500": 19.5, "600": 24},
                500: {"25": 2.2, "50": 3.1, "75": 4, "100": 5.5, "125": 7, "150": 8, "200": 9.5, "250": 12, "300": 13.5,
                      "400": 17.5, "500": 22, "600": 27},
            }

    if finishing:
        if steel == 1:
            if Kld <= 3:
                lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800]
                di = {
                    20: {"25": 0.86, "50": 0.91},
                    30: {"25": 0.92, "50": 0.99, "75": 1.05, "100": 1.1},
                    50: {"25": 0.93, "50": 1, "75": 1.2, "100": 1.5, "125": 1.75, "150": 1.85},
                    75: {"25": 1.05, "50": 1.15, "75": 1.25, "100": 1.35, "125": 1.95, "150": 2.05, "200": 2.25,
                         "250": 2.65},
                    100: {"25": 1.05, "50": 1.2, "75": 1.3, "100": 1.45, "125": 2.1, "150": 2.25, "200": 2.45,
                          "250": 2.7, "300": 2.85},
                    125: {"25": 1.55, "50": 1.7, "75": 1.85, "100": 2, "125": 2.85, "150": 3, "200": 3.3, "250": 3.65,
                          "300": 4, "350": 4.4, "400": 5},
                    150: {"25": 1.55, "50": 1.75, "75": 1.95, "100": 2.2, "125": 3, "150": 3.25, "200": 3.55, "250": 4,
                          "300": 4.4, "350": 4.9, "400": 5.5, "450": 6},
                    200: {"25": 1.6, "50": 1.85, "75": 2.1, "100": 2.5, "125": 3.3, "150": 3.55, "200": 3.95,
                          "250": 4.5, "300": 5, "350": 5.5, "400": 6, "450": 6.5, "500": 7.5, "550": 8},
                    250: {"25": 1.65, "50": 1.95, "75": 2.3, "100": 2.7, "125": 3.6, "150": 4, "200": 4.5, "250": 5,
                          "300": 6, "350": 6.5, "400": 7.5, "450": 8, "500": 8.5, "550": 9.5, "600": 10.5, "650": 11,
                          "700": 12, "750": 12.5},
                    300: {"25": 1.7, "50": 2.1, "75": 2.5, "100": 3, "125": 4, "150": 4.45, "200": 5, "250": 6,
                          "300": 7, "350": 7.5, "400": 8.5, "450": 9.5, "500": 10.5, "550": 11.5, "600": 12.5,
                          "650": 13, "700": 14, "750": 15, "800": 16},
                    350: {"25": 1.8, "50": 2.3, "75": 2.8, "100": 3.4, "125": 4.5, "150": 5, "200": 6, "250": 7,
                          "300": 8, "350": 9, "400": 10.5, "450": 11.5, "500": 12.5, "550": 14, "600": 15, "650": 16,
                          "700": 17, "750": 18.5, "800": 19.5},
                    400: {"25": 1.9, "50": 2.5, "75": 3.1, "100": 3.8, "125": 5, "150": 6, "200": 7, "250": 8,
                          "300": 9.5, "350": 11, "400": 12, "450": 13.5, "500": 15, "550": 16.5, "600": 18, "650": 19.5,
                          "700": 20.5, "750": 22, "800": 23.5},
                }
            elif 3 < Kld <= 10:
                lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800,
                            850, 900, 950, 1000, 1100, 1200, 1300, 1400, 1500]
                di = {
                    20: {"25": 0.85, "50": 0.9, "75": 0.95, "100": 1, "125": 1.4, "150": 1.45, "200": 1.5},
                    30: {"25": 0.92, "50": 0.97, "75": 1.05, "100": 1.1, "125": 1.6, "150": 1.65, "200": 1.75,
                         "250": 1.9, "300": 2.05},
                    50: {"25": 0.94, "50": 1, "75": 1.1, "100": 1.5, "125": 1.7, "150": 1.8, "200": 1.9, "250": 2.1,
                         "300": 2.25, "350": 2.45, "400": 2.6, "450": 2.8, "500": 2.95},
                    75: {"25": 1.05, "50": 1.15, "75": 1.25, "100": 1.4, "125": 2.05, "150": 2.15, "200": 2.35,
                         "250": 2.65, "300": 2.9, "350": 3.15, "400": 3.45, "450": 3.7, "500": 4, "550": 4.5,
                         "600": 4.8, "650": 5, "700": 5.2, "750": 5.5},
                    100: {"25": 1.1, "50": 1.2, "75": 1.35, "100": 1.55, "125": 1.85, "150": 2.2, "200": 2.6,
                          "250": 2.95, "300": 3.3, "350": 3.65, "400": 4, "450": 4.3, "500": 4.7, "550": 5, "600": 5.5,
                          "650": 6, "700": 6.2, "750": 6.5, "800": 7, "850": 7.5, "900": 8, "950": 8.2, "1000": 8.5},
                    125: {"25": 1.6, "50": 1.75, "75": 2, "100": 2.2, "125": 2.95, "150": 3.15, "200": 3.5, "250": 3.9,
                          "300": 4.35, "350": 4.75, "400": 5, "450": 5.5, "500": 6, "550": 6.5, "600": 7, "650": 7.5,
                          "700": 8, "750": 8.5, "800": 9, "850": 9.5, "900": 10, "950": 10.5, "1000": 11, "1100": 12.5,
                          "1200": 13.5, "1300": 14},
                    150: {"25": 1.65, "50": 1.85, "75": 2.1, "100": 2.4, "125": 3.2, "150": 3.45, "200": 3.85,
                          "250": 4.4, "300": 4.95, "350": 5.5, "400": 6, "450": 6.5, "500": 7, "550": 8, "600": 8.5,
                          "650": 9, "700": 9.5, "750": 10, "800": 10.5, "850": 11, "900": 11.5, "950": 12, "1000": 13,
                          "1100": 14.5, "1200": 16, "1300": 17, "1400": 18, "1500": 19},
                    200: {"25": 1.7, "50": 1.95, "75": 2.3, "100": 2.65, "125": 3.55, "150": 3.85, "200": 4.35,
                          "250": 5, "300": 5.5, "350": 6.5, "400": 7, "450": 8, "500": 8.5, "550": 9.5, "600": 1,
                          "650": 11, "700": 11.5, "750": 12, "800": 13, "850": 13.5, "900": 14, "950": 15, "1000": 15.5,
                          "1100": 17.5, "1200": 19, "1300": 20.5, "1400": 22, "1500": 23},
                    250: {"25": 1.8, "50": 2.1, "75": 2.55, "100": 2.95, "125": 3.95, "150": 4.35, "200": 5, "250": 6,
                          "300": 6.5, "350": 7.5, "400": 8.5, "450": 9.5, "500": 10.5, "550": 11.5, "600": 12.5,
                          "650": 13, "700": 14, "750": 15, "800": 15.5, "850": 16.5, "900": 17.5, "950": 18.5,
                          "1000": 19, "1100": 21.5, "1200": 23.5, "1300": 25, "1400": 26.5, "1500": 28.5},
                }

        else:
            lenth_li = [25, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600]
            di = {
                20: {"25": 0.87, "50": 0.91, "75": 0.98},
                30: {"25": 0.92, "50": 1, "75": 1.15},
                50: {"25": 1, "50": 1.1, "75": 1.2, "100": 1.45, "125": 2},
                75: {"25": 1.15, "50": 1.35, "75": 1.55, "100": 1.8, "125": 2.55, "150": 2.9},
                100: {"25": 1.2, "50": 1.45, "75": 1.8, "100": 2.1, "125": 2.9, "150": 3.25, "200": 4.15},
                125: {"25": 1.75, "50": 2.05, "75": 2.45, "100": 2.85, "125": 3.75, "150": 4.15, "200": 4.75,
                      "250": 5.5},
                150: {"25": 1.85, "50": 2.2, "75": 2.7, "100": 3.2, "125": 4.15, "150": 4.7, "200": 5.5, "250": 6.5,
                      "300": 7.5},
                175: {"25": 1.95, "50": 2.4, "75": 3, "100": 3.65, "125": 4.75, "150": 5.5, "200": 6.5, "250": 7.5,
                      "300": 8.5},
                200: {"25": 2, "50": 2.5, "75": 3.2, "100": 3.9, "125": 5, "150": 5.5, "200": 6.5, "250": 8, "300": 9.5,
                      "400": 11.5},
                225: {"25": 2.05, "50": 2.7, "75": 3.45, "100": 4.2, "125": 5.5, "150": 6, "200": 7.5, "250": 9,
                      "300": 10.5, "400": 12.5, "500": 15.5},
                250: {"25": 2.1, "50": 2.8, "75": 3.6, "100": 4.4, "125": 5.5, "150": 6.5, "200": 7.5, "250": 9.5,
                      "300": 11, "400": 13.5, "500": 16.5, "600": 20.5},
                300: {"25": 2.25, "50": 3, "75": 4, "100": 5, "125": 6.5, "150": 7.5, "200": 9, "250": 11, "300": 12.5,
                      "400": 15.5, "500": 19.5, "600": 24},
                350: {"25": 2.45, "50": 3.45, "75": 4.7, "100": 6, "125": 7.5, "150": 9, "200": 10.5, "250": 13,
                      "300": 15.5, "400": 19, "500": 21, "600": 29},
                400: {"25": 2.6, "50": 3.65, "75": 5, "100": 6.5, "125": 8, "150": 9.5, "200": 11.5, "250": 14,
                      "300": 17, "400": 21, "500": 26.5, "600": 32},
                500: {"25": 2.8, "50": 4.1, "75": 5.5, "100": 7.5, "125": 9.5, "150": 11.5, "200": 13.5, "250": 16.5,
                      "300": 20, "400": 24, "500": 31, "600": 38},
            }

    if roughing:
        if steel == 1:
            if Kld <= 3:
                lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800]
                di = {
                    20: {"25": 0.42, "50": 0.46, "75": 0.5},
                    30: {"25": 0.47, "50": 0.47, "75": 0.53, "100": 0.58},
                    50: {"25": 0.51, "50": 0.58, "75": 0.67, "100": 0.76, "125": 1.05, "150": 1.15},
                    75: {"25": 0.6, "50": 0.7, "75": 0.85, "100": 1, "125": 1.4, "150": 1.6, "200": 1.8, "250": 2},
                    100: {"25": 0.65, "50": 0.8, "75": 1, "100": 1.2, "125": 1.6, "150": 1.8, "200": 2.1, "250": 2.5,
                          "300": 2.8},
                    125: {"25": 0.85, "50": 1, "75": 1.2, "100": 1.5, "125": 2.1, "150": 2.35, "200": 2.7, "250": 3.1,
                          "300": 3.6, "350": 4, "400": 4.5},
                    150: {"25": 0.9, "50": 1.1, "75": 1.35, "100": 1.7, "125": 2.4, "150": 2.7, "200": 3.1, "250": 3.6,
                          "300": 4.2, "350": 4.7, "400": 5.5, "450": 6},
                    200: {"25": 1, "50": 1.3, "75": 1.6, "100": 2, "125": 2.8, "150": 3.2, "200": 3.7, "250": 4.45,
                          "300": 5, "350": 6, "400": 6.5, "450": 7.5, "500": 8, "550": 9, "600": 10},
                    250: {"25": 1, "50": 1.5, "75": 1.8, "100": 2.4, "125": 3.25, "150": 3.7, "200": 4.4, "250": 5.5,
                          "300": 6, "350": 7.5, "400": 8, "450": 9, "500": 10, "550": 11, "600": 12, "650": 13,
                          "700": 14, "750": 14.5},
                    300: {"25": 1.1, "50": 1.6, "75": 2.1, "100": 2.7, "125": 3.7, "150": 4.25, "200": 5, "250": 6,
                          "300": 7.5, "350": 8.5, "400": 9.5, "450": 10.5, "500": 11.5, "550": 13, "600": 14, "650": 15,
                          "700": 16.5, "750": 17.5, "800": 18.5},
                    350: {"25": 1.2, "50": 1.9, "75": 2.4, "100": 3.3, "125": 4.3, "150": 5, "200": 6, "250": 7.5,
                          "300": 9, "350": 10, "400": 11.5, "450": 13, "500": 14.5, "550": 16, "600": 17.5, "650": 18.5,
                          "700": 20, "750": 21.5, "800": 22.5},
                    400: {"25": 1.4, "50": 2.2, "75": 2.9, "100": 4, "125": 4.3, "150": 6, "200": 7.5, "250": 9,
                          "300": 11, "350": 12.5, "400": 14.5, "450": 16, "500": 18, "550": 20, "600": 21.5,
                          "650": 23.5, "700": 25, "750": 26.5, "800": 28.5},
                }

            elif 3 < Kld <= 10:
                lenth_li = [25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800,
                            850, 900, 950, 1000, 1100, 1200, 1300, 1400, 1500]
                di = {
                    20: {"25": 0.44, "50": 0.48, "75": 0.53, "100": 0.6, "125": 0.86, "150": 0.91, "200": 1},
                    30: {"25": 0.5, "50": 0.57, "75": 0.63, "100": 0.73, "125": 1.05, "150": 1.1, "200": 1.2,
                         "250": 1.35, "300": 1.55},
                    50: {"25": 0.52, "50": 0.62, "75": 0.7, "100": 0.82, "125": 1.15, "150": 1.25, "200": 1.4,
                         "250": 1.6, "300": 1.8, "350": 2, "400": 2.2, "450": 2.4, "500": 2.6},
                    75: {"25": 0.62, "50": 0.76, "75": 0.88, "100": 1.05, "125": 1.5, "150": 1.65, "200": 1.85,
                         "250": 2.15, "300": 2.45, "350": 2.75, "400": 3.05, "450": 3.35, "500": 3.65, "550": 4.1,
                         "600": 4.4, "650": 4.7, "700": 5, "750": 5.5},
                    100: {"25": 0.65, "50": 0.83, "75": 0.98, "100": 1.2, "125": 1.65, "150": 1.85, "200": 2.15,
                          "250": 2.5, "300": 2.9, "350": 3.3, "400": 3.65, "450": 4.05, "500": 4.4, "550": 4.95,
                          "600": 5.5, "650": 5.8, "700": 6, "750": 6.5, "800": 6.8, "850": 7, "900": 7.5, "950": 8,
                          "1000": 8.5},
                    125: {"25": 0.85, "50": 1.05, "75": 1.25, "100": 1.55, "125": 2.25, "150": 2.45, "200": 2.85,
                          "250": 3.3, "300": 3.8, "350": 4.25, "400": 4.75, "450": 5, "500": 5.5, "550": 6.5, "600": 7,
                          "650": 7.5, "700": 8, "750": 8.5, "800": 9, "850": 9.5, "900": 9.5, "950": 10, "1000": 10.5,
                          "1100": 13.5, "1200": 15, "1300": 16},
                    150: {"25": 0.9, "50": 1.2, "75": 1.4, "100": 1.8, "125": 2.5, "150": 2.8, "200": 3.25, "250": 3.85,
                          "300": 4.45, "350": 5, "400": 5.5, "450": 6.5, "500": 7, "550": 7.5, "600": 8.5, "650": 9,
                          "700": 9.5, "750": 10, "800": 10.5, "850": 11, "900": 12, "950": 12.5, "1000": 13,
                          "1100": 16.5, "1200": 15, "1300": 16},
                    200: {"25": 0.98, "50": 1.35, "75": 1.65, "100": 2.15, "125": 3, "150": 3.4, "200": 4, "250": 4.8,
                          "300": 5.5, "350": 6.5, "400": 7, "450": 8, "500": 8.5, "550": 10, "600": 10.5, "650": 11.5,
                          "700": 12, "750": 13, "800": 14, "850": 14.5, "900": 15.5, "950": 16, "1000": 17,
                          "1100": 20.5, "1200": 12.5, "1300": 13.5, "1400": 14.5, "1500": 15.5},
                    250: {"25": 1.25, "50": 1.7, "75": 2.2, "100": 2.75, "125": 3.7, "150": 4.25, "200": 5, "250": 6,
                          "300": 7, "350": 8.5, "400": 9.5, "450": 10.5, "500": 11.5, "550": 13, "600": 14, "650": 15,
                          "700": 16, "750": 17, "800": 18, "850": 19, "900": 20.5, "950": 21.5, "1000": 22.5,
                          "1100": 25, "1200": 18, "1300": 19, "1400": 20.5, "1500": 22},
                }
        else:
            lenth_li = [25, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600]
            di = {
                20: {"25": 0.5, "50": 0.6, "75": 0.7},
                30: {"25": 0.6, "50": 0.8, "75": 0.9, "100": 1.1},
                50: {"25": 0.6, "50": 0.8, "75": 1, "100": 1.1, "150": 1.4},
                75: {"25": 0.7, "50": 0.9, "75": 1.2, "100": 1.4, "150": 2.6, "200": 2.5, "250": 3},
                100: {"25": 0.8, "50": 1.1, "75": 1.3, "100": 1.7, "150": 2.4, "200": 2.9, "250": 3.5, "300": 4.1},
                125: {"25": 1, "50": 1.4, "75": 1.8, "100": 2.2, "150": 3.2, "200": 4, "250": 4.8, "300": 5.5},
                150: {"25": 1.1, "50": 1.5, "75": 2, "100": 2.5, "150": 3.6, "200": 4.6, "250": 5.5, "300": 6.5,
                      "400": 8},
                200: {"25": 1.2, "50": 1.8, "75": 2.4, "100": 3, "150": 4.3, "200": 5.5, "250": 6.5, "300": 8,
                      "400": 9.5, "500": 12, "600": 14.5},
                250: {"25": 1.3, "50": 2, "75": 2.8, "100": 3.5, "150": 5, "200": 6.5, "250": 8, "300": 9.5, "400": 12,
                      "500": 15, "600": 18},
                300: {"25": 1.5, "50": 2.4, "75": 3.3, "100": 4.3, "150": 6, "200": 8, "250": 10, "300": 12,
                      "400": 14.5, "500": 18.5, "600": 22.5},
                350: {"25": 1.7, "50": 2.8, "75": 4.1, "100": 5, "150": 7.5, "200": 10, "250": 12, "300": 14.5,
                      "400": 18.5, "500": 23, "600": 28},
                400: {"25": 1.8, "50": 3, "75": 4.4, "100": 5.5, "150": 8, "200": 9.5, "250": 13.5, "300": 16,
                      "400": 20, "500": 25, "600": 30.5},
                450: {"25": 2.2, "50": 3.15, "75": 4.65, "100": 6, "150": 9, "200": 12, "250": 15, "300": 18,
                      "400": 22.5, "500": 28.5, "600": 35},
                500: {"25": 2.3, "50": 3.35, "75": 4.95, "100": 6.5, "150": 9.5, "200": 12.5, "250": 16, "300": 19,
                      "400": 24, "500": 30.5, "600": 37, },
            }
    find_diam = 0
    for i in di.keys():
        if i >= end_diam:
            find_diam = i
            break
    if find_diam == 0:
        return 0

    sub_detail = di.get(find_diam)
    if not sub_detail:
        return 0

    find_lenth = 0
    for i in lenth_li:
        if i >= lenth:
            find_lenth = i
            break
    time_val = sub_detail.get(f"{find_lenth}")

    if time_val:
        return time_val
    else:
        return 0


def external_sub_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # получистовая обработка
    # Вид стали:int;Начальный диаметр заготовки:int;Конечный диаметр:int;Длина прохода инструмента:int;

    dp = DataPreparater(arr_tmp)
    arr_steel_type = dp.get_arr("Вид стали")
    arr_start_diam = dp.get_arr("Начальный диаметр заготовки")
    arr_end_diam = dp.get_arr("Конечный диаметр")
    arr_lenth = dp.get_arr("Длина прохода инструмента")

    summa_vremeni = 0
    if len(arr_start_diam) == len(arr_end_diam):
        for i in range(len(arr_start_diam)):
            start_diam = F.valm(arr_start_diam[i])
            end_diam = F.valm(arr_end_diam[i])
            lenth = F.valm(arr_lenth[i])
            steel = F.valm(arr_steel_type[i])  # 1 черн 2 нерж

            Kld = lenth / start_diam
            T1 = get_di_for_turning(steel, Kld, end_diam, lenth, roughing=True)
            T2 = get_di_for_turning(steel, Kld, end_diam, lenth, sub_finishing=True)
            step_quantity = (start_diam - end_diam) / 8
            tn = T1 * step_quantity + T2

            Kd = 0.85 if end_diam / start_diam <= 0.7 else 1
            summa_vremeni += tn * Kd
    else:
        return 0
    return summa_vremeni


def external_finishing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # чистовая обработка
    # Вид стали:int;Начальный диаметр заготовки:int;Конечный диаметр:int;Длина прохода инструмента:int;

    dp = DataPreparater(arr_tmp)
    arr_steel_type = dp.get_arr("Вид стали")
    arr_start_diam = dp.get_arr("Начальный диаметр заготовки")
    arr_end_diam = dp.get_arr("Конечный диаметр")
    arr_lenth = dp.get_arr("Длина прохода инструмента")

    summa_vremeni = 0
    if len(arr_start_diam) == len(arr_end_diam):
        for i in range(len(arr_start_diam)):
            start_diam = F.valm(arr_start_diam[i])
            end_diam = F.valm(arr_end_diam[i])
            lenth = F.valm(arr_lenth[i])
            steel = F.valm(arr_steel_type[i])  # 1 черн 2 нерж

            Kld = lenth / start_diam
            T1 = get_di_for_turning(steel, Kld, end_diam, lenth, roughing=True)
            T2 = get_di_for_turning(steel, Kld, end_diam, lenth, sub_finishing=True)
            T3 = get_di_for_turning(steel, Kld, end_diam, lenth, finishing=True)
            step_quantity = (start_diam - end_diam) / 8
            tn = T1 * step_quantity + T2 + T3

            Kd = 0.85 if end_diam / start_diam <= 0.7 else 1
            summa_vremeni += tn * Kd
    else:
        return 0
    return summa_vremeni


def external_roughing(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # черновая обработка
    # Вид стали:int;Начальный диаметр заготовки:int;Конечный диаметр:int;Длина прохода инструмента:int;

    dp = DataPreparater(arr_tmp)
    arr_steel_type = dp.get_arr("Вид стали")
    arr_start_diam = dp.get_arr("Начальный диаметр заготовки")
    arr_end_diam = dp.get_arr("Конечный диаметр")
    arr_lenth = dp.get_arr("Длина прохода инструмента")

    summa_vremeni = 0
    if len(arr_start_diam) == len(arr_end_diam):
        for i in range(len(arr_start_diam)):
            start_diam = F.valm(arr_start_diam[i])
            end_diam = F.valm(arr_end_diam[i])
            lenth = F.valm(arr_lenth[i])
            steel = F.valm(arr_steel_type[i])  # 1 черн 2 нерж

            Kld = lenth / start_diam
            T1 = get_di_for_turning(steel, Kld, end_diam, lenth, roughing=True)
            step_quantity = (start_diam - end_diam) / 8
            tn = T1 * step_quantity

            Kd = 0.85 if end_diam / start_diam <= 0.7 else 1
            summa_vremeni += tn * Kd
    else:
        return 0
    return summa_vremeni


def butting(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    # Количество торцов:int;Внешний диаметр обрабатываемой поверхности(мм):int;Внутренний диаметр(мм):int;Материал(0 черн, 1 нерж):int;Марка сплава(ВК8-1,Т5К10-2,Т15К6-3):int;
    dp = DataPreparater(arr_tmp)
    alloy_arr = dp.get_arr("Марка сплава(ВК8-1,Т5К10-2,Т15К6-3)")
    material_arr = dp.get_arr("Материал(0 черн, 1 нерж)")
    count_arr = dp.get_arr("Количество торцов")
    external_diametr_arr = dp.get_arr("Внешний диаметр обрабатываемой поверхности(мм)")
    internal_diametr_arr = dp.get_arr("Внутренний диаметр(мм)")

    summ = 0
    if len(count_arr) == len(external_diametr_arr):
        for index, _ in enumerate(count_arr):
            current_diametr = float(external_diametr_arr[index])
            cur_internal_diametr = float(internal_diametr_arr[index])
            cur_alloy = int(alloy_arr[index])
            cur_butt = int(count_arr[index])
            k_alloy = 1 if cur_alloy == 1 else 0.75 if cur_alloy == 2 else 0.55

            i = (current_diametr - cur_internal_diametr) / 8
            if material_arr[index] == '0':
                K_ext_diametr = 0.77 if current_diametr < 10 else 0.82 if current_diametr < 20 else 0.83 if current_diametr < 30 else 0.97 if current_diametr < 40 else 1.25 if current_diametr < 60 else 1.5 if current_diametr < 80 else 1.9 if current_diametr < 90 else 2.15
                summ += K_ext_diametr * i * k_alloy * cur_butt
            else:
                K_ext_diametr = 0.51 if current_diametr < 15 else 0.93 if current_diametr < 30 else 1.2 if current_diametr < 40 else 2.1 if current_diametr < 60 else 2.85 if current_diametr < 80 else 2.95 if current_diametr < 90 else 3.45
                summ += K_ext_diametr * i * k_alloy * cur_butt
    return summ


def toch_nar_rezb(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    rez = toch_vnutr_rezb(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent)
    return rez


def toch_fask(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Количество')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Количество')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэфф_мат')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Коэфф_мат')].replace(key, SLOV_ZAMEN[key])

    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр')].split(";")
    arr_kolich = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Количество')].split(";")
    arr_koef = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэфф_мат')].split(";")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_sort_c):
        for i in range(len(arr_sort_c)):
            vid = F.valm(arr_sort_c[i])
            diam = F.valm(arr_diam[i])
            if vid == 0:
                vremya_shtuchnoe = 0.4 if diam <= 50 else 0.45 if diam <= 100 else 0.55 if diam <= 200 else 0.6 if diam <= 300 else 0.7
            elif vid == 1:
                vremya_shtuchnoe = 0 if diam <= 50 else 1.1 if diam <= 100 else 1.4 if diam <= 200 else 1.5 if diam <= 300 else 1.6
            elif vid == 2:
                vremya_shtuchnoe = 1.1 if diam <= 30 else 1.2 if diam <= 50 else 1.3 if diam <= 80 else 1.6 if diam <= 120 else 1.8 if diam <= 180 else 2.4 if diam <= 260 else 3.5

            kolich = F.valm(arr_kolich[i])
            koef = F.valm(arr_koef[i])
            summa_vremeni += vremya_shtuchnoe * kolich * koef
    else:
        return 0
    return summa_vremeni


def toch_otrez(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нар')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нар')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_внут')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_внут')].replace(key, SLOV_ZAMEN[key])

    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нар')].split(";")
    arr_diam_vnut = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_внут')].split(";")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_sort_c):
        for i in range(len(arr_sort_c)):
            vid = F.valm(arr_sort_c[i])
            diam = F.valm(arr_diam[i])
            diam_vnut = F.valm(arr_diam_vnut[i])

            if vid == 0:
                if diam_vnut == 0:
                    putf = put + F.sep() + 'table1.txt'
                    vremya_shtuchnoe = table(putf, diam)
                else:
                    putf = put + F.sep() + 'table2.txt'
                    vremya_shtuchnoe = table(putf, diam, (diam - diam_vnut) / 2)
            else:
                if diam_vnut == 0:
                    putf = put + F.sep() + 'table3.txt'
                    vremya_shtuchnoe = table(putf, diam)
                else:
                    putf = put + F.sep() + 'table4.txt'
                    vremya_shtuchnoe = table(putf, diam, (diam - diam_vnut) / 2)

            summa_vremeni += vremya_shtuchnoe
    else:
        return 0
    return summa_vremeni


def toch_nar_paz(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нар')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нар')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина паза')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина паза')].replace(key, SLOV_ZAMEN[key])

    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нар')].split(";")
    arr_glub = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина паза')].split(";")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_sort_c):
        for i in range(len(arr_sort_c)):
            vid = F.valm(arr_sort_c[i])
            diam = F.valm(arr_diam[i])
            glub = F.valm(arr_glub[i])
            if vid == 1:
                putf = put + F.sep() + 'table1.txt'
            else:
                putf = put + F.sep() + 'table2.txt'

            vremya_shtuchnoe = table(putf, diam, glub)

            summa_vremeni += vremya_shtuchnoe
    else:
        return 0
    return summa_vremeni


def toch_sverl_otv(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_дет')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_дет')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина_отв')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина_отв')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глухое')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Глухое')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].replace(key, SLOV_ZAMEN[key])

    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_дет')].split(";")
    arr_dlina = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина_отв')].split(";")
    arr_gluh = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глухое')].split(";")
    arr_mat = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].split(";")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_sort_c):
        for i in range(len(arr_sort_c)):
            vid = F.valm(arr_sort_c[i])
            diam = F.valm(arr_diam[i])
            dlina = F.valm(arr_dlina[i])
            gluh = F.valm(arr_gluh[i])
            mat = F.valm(arr_mat[i])
            if gluh == 1:
                gluh = 1.1
            else:
                gluh = 1

            if mat == 0:
                mat = 1
            else:
                mat = 1.5

            if vid == 2:
                putf = put + F.sep() + 'table2.txt'
            elif vid == 3:
                putf = put + F.sep() + 'table3.txt'
            elif vid == 4:
                putf = put + F.sep() + 'table4.txt'
            else:
                putf = put + F.sep() + 'table1.txt'

            vremya_shtuchnoe = table(putf, diam, dlina)

            summa_vremeni += vremya_shtuchnoe * gluh * mat
    else:
        return 0
    return summa_vremeni


def toch_vnutr_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв_нач')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв_нач')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв_кон')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв_кон')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].replace(key, SLOV_ZAMEN[key])

    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв_нач')].split(";")
    arr_diam_kon = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_отв_кон')].split(";")
    arr_dl = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина')].split(";")
    arr_mat = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].split(";")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_sort_c):
        for i in range(len(arr_sort_c)):
            vid = F.valm(arr_sort_c[i])
            diam = F.valm(arr_diam[i])
            diam_kon = F.valm(arr_diam_kon[i])
            dl = F.valm(arr_dl[i])
            mat = F.valm(arr_mat[i])
            koef_d = 1
            if diam_kon / diam >= 0.7:
                koef_d = 1.2

            n_proh = (diam_kon - diam) // 8
            vremya_shtuchnoe = 0
            if mat == 0:
                if vid == 2:
                    putf = put + F.sep() + 'table1.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
                    putf = put + F.sep() + 'table2.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                elif vid == 3:
                    putf = put + F.sep() + 'table1.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
                    putf = put + F.sep() + 'table2.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                    putf = put + F.sep() + 'table3.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                else:
                    putf = put + F.sep() + 'table1.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
            else:
                if vid == 2:
                    putf = put + F.sep() + 'table4.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
                    putf = put + F.sep() + 'table5.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                elif vid == 3:
                    putf = put + F.sep() + 'table4.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
                    putf = put + F.sep() + 'table5.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                    putf = put + F.sep() + 'table6.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                else:
                    putf = put + F.sep() + 'table4.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh

            summa_vremeni += vremya_shtuchnoe * koef_d
    else:
        return 0
    return summa_vremeni


def toch_nar_pov(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нач')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нач')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_кон')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_кон')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].replace(key, SLOV_ZAMEN[key])

    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].split(";")
    arr_diam = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_нач')].split(";")
    arr_diam_kon = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр_кон')].split(";")
    arr_dl = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина')].split(";")
    arr_mat = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].split(";")

    summa_vremeni = 0
    if len(arr_diam) == len(arr_sort_c):
        for i in range(len(arr_sort_c)):
            vid = F.valm(arr_sort_c[i])
            diam = F.valm(arr_diam[i])
            diam_kon = F.valm(arr_diam_kon[i])
            dl = F.valm(arr_dl[i])
            mat = F.valm(arr_mat[i])
            koef_d = 1
            if diam_kon / diam <= 0.7:
                koef_d = 0.85

            n_proh = F.round_up((diam - diam_kon) / 8)
            kld = dl / diam

            vremya_shtuchnoe = 0
            if mat == 0:
                if vid == 2:
                    if kld <= 3:
                        putf = put + os.sep + 'table1.txt'
                    else:
                        putf = put + os.sep + 'table2.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh

                    if kld <= 3:
                        putf = put + os.sep + 'table3.txt'
                    else:
                        putf = put + os.sep + 'table4.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)

                elif vid == 3:

                    if kld <= 3:
                        putf = put + os.sep + 'table1.txt'
                    else:
                        putf = put + os.sep + 'table2.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh

                    if kld <= 3:
                        putf = put + os.sep + 'table3.txt'
                    else:
                        putf = put + os.sep + 'table4.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)

                    if kld <= 3:
                        putf = put + os.sep + 'table5.txt'
                    else:
                        putf = put + os.sep + 'table6.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)

                else:
                    if kld <= 3:
                        putf = put + os.sep + 'table1.txt'
                    else:
                        putf = put + os.sep + 'table2.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
            else:
                if vid == 2:
                    putf = put + os.sep + 'table7.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
                    putf = put + os.sep + 'table8.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                elif vid == 3:
                    putf = put + os.sep + 'table7.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh
                    putf = put + os.sep + 'table8.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                    putf = put + os.sep + 'table9.txt'
                    vremya_shtuchnoe += table(putf, diam, dl)
                else:
                    putf = put + os.sep + 'table7.txt'
                    vremya_shtuchnoe = table(putf, diam, dl) * n_proh

            summa_vremeni += vremya_shtuchnoe * koef_d
    else:
        return 0
    return summa_vremeni


def toch_ust_pereust_sn_det(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Масса')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число_переустановок')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Число_переустановок')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Тип')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Тип')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число_деталей_в_партии')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Число_деталей_в_партии')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')] = arr_tmp[-1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].replace(key, SLOV_ZAMEN[key])

    arr_mass = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса')].split(";")
    arr_pereust = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число_переустановок')].split(";")
    arr_tip = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Тип')].split(";")
    arr_n = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число_деталей_в_партии')].split(";")
    arr_sort_c = arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид')].split(";")

    summa_vremeni = 0
    if len(arr_mass) == len(arr_tip):
        for i in range(len(arr_mass)):
            mass = F.valm(arr_mass[i])
            pereust = F.valm(arr_pereust[i])
            tip = F.valm(arr_tip[i])
            n = F.valm(arr_n[i])
            vid = F.valm(arr_sort_c[i])

            tpz = 14
            if tip == 1:
                tpz = 22
            elif tip == 2:
                tpz = 35

            tvy = 0.78 if mass <= 0.3 else 1.1 if mass <= 1 else 1.35 if mass <= 3 else 1.65 if mass <= 5 else 1.9 if mass <= 10 else 2.5 if mass <= 20 else 5 if mass <= 30 else 6.5 if mass <= 50 else 8.5 if mass <= 100 else 9.8

            kkon = 1
            if vid == 1:
                kkon = 1.2

            summa_vremeni += tvy * (
                        1 + pereust) * kkon  # + tpz/n --  это должно быть в результируюей операции токарная а не здесь

    else:
        return 0
    return summa_vremeni


def frezerovnie_shponki(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    material = arr_tmp_parent[0]
    koef_mater = 1 if material == '1' else 1.2

    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])

    arr_glubin_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')].split(";")
    arr_dlina_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')].split(";")
    summa_vremeni = 0

    if len(arr_glubin_frezer) == len(arr_dlina_frezer):
        putf = put + F.sep() + 'table1.txt'

        for i in range(len(arr_glubin_frezer)):
            glubin_frezer = F.valm(arr_glubin_frezer[i])
            dlina_frezer = F.valm(arr_dlina_frezer[i])
            vremya_shtuchnoe = table(putf, glubin_frezer, dlina_frezer)
            summa_vremeni += vremya_shtuchnoe
    else:
        return 0
    return summa_vremeni * 1.13 * koef_mater


def vspomogatelnoe(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)
    putf = put + F.sep() + 'table1.txt'
    massa = F.valm(arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса,кг')])
    kol_vo_povorotov = F.valm(arr_tmp[-1][F.num_col_by_name_in_hat_c(arr_tmp, 'Количество поворотов,шт')])
    tabl_parametr = table(putf, massa)
    Nvr = tabl_parametr * (1 + 0.8 * kol_vo_povorotov)
    return Nvr


def frezerovnie_ustupa(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    material = arr_tmp_parent[0]
    koef_mater = 1 if material == '1' else 1.2

    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина фрезерования , мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина фрезерования , мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Фреза диаметром, мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Фреза диаметром, мм')].replace(key, SLOV_ZAMEN[key])

    arr_glubin_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')].split(";")
    arr_dlina_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')].split(";")
    arr_shirina_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина фрезерования , мм')].split(";")
    arr_diametr_frez = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Фреза диаметром, мм')].split(";")
    summa_vremeni = 0

    if len(arr_glubin_frezer) == len(arr_dlina_frezer) == len(arr_shirina_frezer) == len(arr_diametr_frez):
        putf_chern = put + F.sep() + 'table1.txt'

        for i in range(len(arr_glubin_frezer)):
            glubin_frezer = F.valm(arr_glubin_frezer[i])
            dlina_frezer = F.valm(arr_dlina_frezer[i])
            shirina_frezer = F.valm(arr_shirina_frezer[i])
            diametr_frez = F.valm(arr_diametr_frez[i])
            shirina_hoda = 0

            if glubin_frezer <= 0.3 * diametr_frez:
                shirina_hoda = diametr_frez
            elif glubin_frezer <= 0.5 * diametr_frez:
                shirina_hoda = 0.7 * diametr_frez
            elif glubin_frezer <= 0.7 * diametr_frez:
                shirina_hoda = 0.5 * diametr_frez
            elif glubin_frezer <= diametr_frez:
                shirina_hoda = 0.3 * diametr_frez
            elif glubin_frezer <= 2 * diametr_frez:
                shirina_hoda = 0.1 * diametr_frez

            dlina_hoda = dlina_frezer * (1 + shirina_frezer // shirina_hoda) + diametr_frez
            vremya_za_hod_chern = table(putf_chern, dlina_hoda)
            vremya_za_hod = vremya_za_hod_chern

            if (dlina_hoda > 950):
                vremya_za_hod += (math.ceil((dlina_hoda - 950) / 100) + 1) * 2.15

            chislo_hodov = math.ceil(glubin_frezer / 30 + 1)
            vremya_shtuchnoe = vremya_za_hod * chislo_hodov

            summa_vremeni += vremya_shtuchnoe
    else:
        return 0
    summa_vremeni *= 1.25 * koef_mater
    return summa_vremeni


# def frezerovnie_ustupa(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
#     SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
#     material = arr_tmp_parent[0]
#     koef_mater = 1 if material == '1' else 1.2

#     for key in SLOV_ZAMEN.keys():
#         arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Глубина фрезерования, мм')] = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Глубина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])
#         arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Длина фрезерования, мм')] = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Длина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])
#         arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Ширина фрезерования , мм')] = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Ширина фрезерования , мм')].replace(key, SLOV_ZAMEN[key])
#         arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Фреза диаметром, мм')] = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Фреза диаметром, мм')].replace(key, SLOV_ZAMEN[key])

#     arr_glubin_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Глубина фрезерования, мм')].split(";")
#     arr_dlina_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Длина фрезерования, мм')].split(";")
#     arr_shirina_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Ширина фрезерования , мм')].split(";")
#     arr_diametr_frez = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp,'Фреза диаметром, мм')].split(";")
#     summa_vremeni = 0

#     if len(arr_glubin_frezer) == len(arr_dlina_frezer) == len(arr_shirina_frezer) == len(arr_diametr_frez):
#         putf_chern = F.scfg(
#             'cash') + F.sep() + "tables" + F.sep() + ima_operacii + F.sep() + ima_perehoda + F.sep() + 'table1.txt'

#         for i in range(len(arr_glubin_frezer)):
#             glubin_frezer = F.valm(arr_glubin_frezer[i])
#             dlina_frezer = F.valm(arr_dlina_frezer[i])
#             shirina_frezer = F.valm(arr_shirina_frezer[i])
#             diametr_frez = F.valm(arr_diametr_frez[i])
#             shirina_hoda = 0

#             if glubin_frezer <= 0.3 * diametr_frez:
#                 shirina_hoda = diametr_frez
#             elif glubin_frezer <= 0.5 * diametr_frez:
#                 shirina_hoda = 0.7 * diametr_frez
#             elif glubin_frezer <= 0.7 * diametr_frez:
#                 shirina_hoda = 0.5 * diametr_frez
#             elif glubin_frezer <= diametr_frez:
#                 shirina_hoda = 0.3 * diametr_frez
#             elif glubin_frezer <= 2 * diametr_frez:
#                 shirina_hoda = 0.1 * diametr_frez

#             i = glubin_frezer//30 + 1
#             L = (dlina_frezer * shirina_frezer / shirina_hoda) + diametr_frez
#             T = table(putf_chern, L)
#             tnsh = T * i
#             Kts = 1.25
#             vremya_shtuchnoe = tnsh * koef_mater * Kts

#             summa_vremeni += vremya_shtuchnoe

#     else:
#         return 0
#     # summa_vremeni *= 1.25 * koef_mater
#     return summa_vremeni

def frezerovnie_ploskosti(ima_operacii, ima_perehoda, arr_tmp, arr_tmp_parent):
    put = OperationConfig.operation_table_path(ima_operacii, ima_perehoda)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    material = arr_tmp_parent[0]
    koef_mater = 1 if material == '1' else 1.2

    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Точность')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Точность')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')].replace(key, SLOV_ZAMEN[key])

    arr_tochnost = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Точность')].split(";")
    arr_glubin_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина фрезерования, мм')].split(";")
    arr_dlina_frezer = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина фрезерования, мм')].split(";")
    summa_vremeni = 0

    if len(arr_glubin_frezer) == len(arr_dlina_frezer):
        putf_chern = put + F.sep() + 'table1.txt'
        putf_poluchist = put + F.sep() + 'table2.txt'

        for i in range(len(arr_glubin_frezer)):
            glubin_frezer = F.valm(arr_glubin_frezer[i])
            dlina_frezer = F.valm(arr_dlina_frezer[i])

            vremya_za_hod_chern = table(putf_chern, dlina_frezer)
            chislo_hodov = 1 + glubin_frezer // 5
            vremya_za_hod = vremya_za_hod_chern

            if (dlina_frezer > 950):
                vremya_za_hod += (1 + (dlina_frezer - 950) // 100) * 0.9

            vremya_shtuchnoe = vremya_za_hod * chislo_hodov

            if (arr_tochnost[i] == '2'):
                vremya_za_hod_poluchist = table(putf_poluchist, dlina_frezer)
                if (dlina_frezer > 950):
                    vremya_za_hod_poluchist += (1 + (dlina_frezer - 950) // 100) * 0.77
                vremya_shtuchnoe += vremya_za_hod_poluchist

            summa_vremeni += vremya_shtuchnoe
    else:
        return 0
    summa_vremeni *= 1.2 * koef_mater
    return summa_vremeni

class Operations:
    def __init__(self, params) -> None:
        self.params = params

    def convert_params(self):
        count = len(self.params[1][0].split(';'))
        converted_params = []

        for num in range(count):
            row = [elem.split(';')[num] for elem in self.params[1]]
            converted_params.append(row)
        return converted_params

def vremya_tsht(ima_operacii, arr_tmp):
    try:
        if type(arr_tmp) == dict:
            arr_tmp = F.list_of_dicts_to_list_of_lists([arr_tmp])
        vrema = 0
        for i in range(len(arr_tmp[0])):
            arr_tmp[0][i] = arr_tmp[0][i].split(":")[0]
        op_obj = Operations(arr_tmp)
        if not arr_tmp[1]: return 0
        params = op_obj.convert_params()
        result = 0
        obj = CXLF.XlFormula()
        is_xl = obj.check_op(ima_operacii, True)
        is_approved = obj.check_approved(operation=ima_operacii)
        if is_approved and not is_xl:
            CQT.msgbox(f'Не возможно расчитать операцию: {ima_operacii}\n из-за недоступности сервера')
            return
        for elem in params:
            arr_tmp = [arr_tmp[0], elem]
            if is_xl:
                vrema = obj.client.srv_operation_calc(ima_operacii, '', arr_tmp)
                if not isinstance(vrema, (float, int, tuple)):
                    CQT.msgbox('Допущена ошибка при расчете')
                if isinstance(vrema, tuple) and len(vrema) == 2:
                    sht, pz = vrema
                    result = (result[0] + sht, pz) if isinstance(result, tuple) else (sht, pz)
                else:
                    result += vrema
                continue
            if CFG.Config.place.poki == 1:
                return
            if ima_operacii == 'Упаковывание':
                vrema = upacovivanie(ima_operacii, arr_tmp)
            if ima_operacii == 'Электроэрозионная':
                vrema = el_erozion(ima_operacii, arr_tmp)
            # if ima_operacii == 'Вальцовка':               # 24.07.25 Переход на excel
            #     vrema = valcovka(ima_operacii, arr_tmp)
            if ima_operacii == 'Гибка':
                vrema = gibka(ima_operacii, arr_tmp)
            # if ima_operacii == 'Сборка общая':
            #     vrema = sbor_obsh(ima_operacii, arr_tmp)
            if ima_operacii == 'Слесарная(зачистка швов)':
                vrema = sles_zach_shvov(ima_operacii, arr_tmp)
            if ima_operacii == 'Сборка под сварку':
                vrema = sb_pod_sv(ima_operacii, arr_tmp)
            # if ima_operacii == 'Гравировальная':          # 24.07.25 Переход на excel
            #     vrema = gravir(ima_operacii, arr_tmp)
            # if ima_operacii == 'Слесарная(снять заусенцы)':
            #     vrema = sles_zausenci(ima_operacii, arr_tmp)
            if ima_operacii == 'Отрезка(гильотина)':
                vrema = gilotina(ima_operacii, arr_tmp)
            if ima_operacii == 'Окрашивание':
                vrema = okras(ima_operacii, arr_tmp)
            if ima_operacii == 'Отрезка(лентопил)':
                vrema = otrez_lentopil(ima_operacii, arr_tmp)
            if ima_operacii == 'Сварка':
                vrema = svarka(ima_operacii, arr_tmp)
            if ima_operacii == 'Сборка линз':
                vrema = sborka_linz(ima_operacii, arr_tmp)
            if ima_operacii == 'Укладка набивки':
                vrema = ukladka_nabivki(ima_operacii, arr_tmp)
            if ima_operacii == 'Формовка линз':
                vrema = formovka_linz(ima_operacii, arr_tmp)
            if ima_operacii == 'Отрезка слесарная':
                vrema = otrez_sles(ima_operacii, arr_tmp)
            if ima_operacii == 'Дробеструйная':
                vrema = drobestrui(ima_operacii, arr_tmp)
            # if ima_operacii == 'Слесарная(правка в плоскости)':
            #     vrema = sles_prav(ima_operacii, arr_tmp)
            if ima_operacii == 'Сверлильная':
                vrema = sverlil(ima_operacii, arr_tmp)
            if ima_operacii == 'Слесарная(сверление)':
                vrema = sles_sverl(ima_operacii, arr_tmp)
            if ima_operacii == 'Штамповочная(перфорация)':
                vrema = shtamp_perf(ima_operacii, arr_tmp)
            if ima_operacii == 'Слесарная(нарезка резьбы)':
                vrema = sles_rezba(ima_operacii, arr_tmp)
            if ima_operacii == 'Слесарная(разделка кромок)':
                vrema = sles_razd_krom(ima_operacii, arr_tmp)
            if ima_operacii == 'Слесарная(разметка)':
                vrema = sles_razmetka(ima_operacii, arr_tmp)
            if ima_operacii == 'Кантование':
                vrema = kantovanie(ima_operacii, arr_tmp)
            if ima_operacii == 'Резка(ЧПУ)':
                vrema = lazer(ima_operacii, arr_tmp)
            if ima_operacii == 'Резка плазма':
                vrema = rezka_plazma(ima_operacii, arr_tmp)
            if ima_operacii == 'Вальцовка линз':
                vrema = valtcovka_linz(ima_operacii, arr_tmp)
            if ima_operacii == 'Комплектовочная':
                vrema = komplektov(ima_operacii, arr_tmp)
            if ima_operacii == 'Перемещение':
                vrema = peremeschenie(ima_operacii, arr_tmp)
            if ima_operacii == 'Контроль(формы и расположения поверхностей)':
                vrema = kontrol_form_i_raspoloj_poverhn(ima_operacii, arr_tmp)
            if ima_operacii == 'Контроль(механическая обработка)':
                vrema = kontrol_mech_obrabot(ima_operacii, arr_tmp)
            if ima_operacii == 'Контрольная(цветная дефектоскопия)':
                vrema = kontrol_tcvet_defekt(ima_operacii, arr_tmp)
            if ima_operacii == 'Рейкодолбежная':
                vrema = reykodolbejnaya(ima_operacii, arr_tmp)
            if ima_operacii == 'Слесарная(зачистка поверхности)':
                vrema = surface_cleaning(arr_tmp)
            if ima_operacii == 'Слесарная(снятие фасок)':
                vrema = chamfering(arr_tmp)
            if isinstance(vrema, tuple) and len(vrema) == 2:
                sht, pz = vrema
                result = (result[0] + sht, pz) if isinstance(result, tuple) else (sht, pz)
            else:
                result += vrema

    except ArithmeticError as e:
        description = {
            ZeroDivisionError: 'Деление на ноль',
            OverflowError: 'Значение выходит за рамки допустимого',
            FloatingPointError: 'Некорректная работа с дробью'
        }
        msg = (
            f'Произошла ошибка во время операции: {ima_operacii}\n'
            f'Предположительно: {description[e.__class__]}'
        )
        CQT.msgbox(msg)
        raise e
    except TypeError as e:
        reg = re.compile(r"\[F\.num_col_by_name_in_hat_c\(.*,(.*)\)\]")
        trace = traceback.format_tb(e.__traceback__)[0]
        args = reg.findall(trace)
        if args and isinstance(args[0], str):
            msg = (
                f'Произошла ошибка во время операции: {ima_operacii}\n'
                f'Не найдено: {args[0]}'
            )
            CQT.msgbox(msg)
            return
        else:
            raise e
    if result == None:
        return
    if type(result) == tuple:
        return round(result[0], 2), round(result[1], 3)  # sht, pz
    return round(result, 2)


def materiali(self, ima_operacii, arr_tmp):
    mat = ""
    for i in range(len(arr_tmp[0])):
        arr_tmp[0][i] = arr_tmp[0][i].split(":")[0]
    if ima_operacii == 'Упаковывание':
        mat = komp_upacovivanie(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Вальцовка':
        mat = komp_valcovka(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Отрезка(лентопил)':
        mat = komp_otrezka_lentopil(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Отрезка(гильотина)':
        mat = komp_gilotina(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Токарная':
        mat = komp_tokarnaya(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Сборка под сварку':
        mat = komp_sb_pod_sv(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Фрезерная':
        mat = komp_frezernaya(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Слесарная(нарезка резьбы)':
        mat = komp_sles_rezba(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Резка(ЧПУ)':
        mat = komp_lazernaya_rezka(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Резка плазма':
        mat = komp_rezka_plazma(ima_operacii, arr_tmp)
    if ima_operacii == 'Вальцовка линз':
        mat = komp_valtcovka_linz(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Гибка':
        mat = komp_gibka(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Гравировальная':
        mat = komp_gravirov(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Комплектовочная':
        mat = komp_komplektov(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Отрезка слесарная':
        mat = komp_otrezka_slesar(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Перемещение':
        mat = komp_peremeschenie(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Рейкодолбежная':
        mat = komp_reykodolbejnaya(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Сборка линз':
        mat = komp_sborka_linz(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Сборка общая':
        mat = komp_sborka_obschaya(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Сварка':
        mat = komp_svarka(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Сверлильная':
        mat = komp_sverlilnaya(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Слесарная(зачистка швов)':
        mat = komp_slesarnaya_zach_shvov(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Слесарная(правка в плоскости)':
        mat = komp_slesarnya_pravka_v_plos(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Слесарная(сверление)':
        mat = komp_slesarnaya_sverlen(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Слесарная(снять заусенцы)':
        mat = komp_slesarnaya_snyatie_zausentcev(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Укладка набивки':
        mat = komp_ukladka_nabivki(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Формовка линз':
        mat = komp_formovka_linz(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Штамповочная(перфорация)':
        mat = komp_shtampovochnaya(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Слесарная(разделка кромок)':
        mat = komp_slesarnaya_razdelka_kromok(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Кантование':
        mat = komp_kantovanie(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Контроль(формы и расположения поверхностей)':
        mat = komp_kontrol_form_i_raspoloj_poverhn(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Контроль(механическая обработка)':
        mat = komp_kontrol_mech_obrabot(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Контрольная(цветная дефектоскопия)':
        mat = komp_kontrol_tcvet_defekt(self, ima_operacii, arr_tmp)
    if ima_operacii == 'Дробеструйная':
        mat = komp_drobestryi(self, ima_operacii, arr_tmp)

    tmp = []
    for i in range(len(mat)):
        tmp.append('$'.join(mat[i]))
    return '{'.join(tmp)


def list_mat_for_complex(self, ima_operacii, tag=0, uslovie='', conn=''):
    kod_oper = self.DICT_KOD_OPER[ima_operacii]
    if uslovie != '':
        query = f"""SELECT complex_filtr.kod, nomen.Наименование, nomen.ЕдиницаИзмерения,  complex_filtr.expenditure_per_smena FROM complex_filtr 
            INNER JOIN nomen ON nomen.Код == complex_filtr.kod 
                        WHERE complex_filtr.kod_oper == '{kod_oper}' AND complex_filtr.tag == {tag} AND 
            complex_filtr.commentss LIKE '%{uslovie}%' AND complex_filtr.filtr == 0"""
    else:
        query = f"""SELECT complex_filtr.kod, nomen.Наименование, nomen.ЕдиницаИзмерения,  complex_filtr.expenditure_per_smena FROM complex_filtr 
                    INNER JOIN nomen ON nomen.Код == complex_filtr.kod 
                                WHERE complex_filtr.kod_oper == '{kod_oper}' AND complex_filtr.tag == {tag}
                        AND complex_filtr.filtr == 0"""
    list = CSQ.custom_request_c(self.db_mater, query, hat_c=False, conn=conn)
    return list


def komp_upacovivanie(self, ima_operacii, arr_tmp):
    try:
        dict_tmp = F.list_of_lists_to_list_of_dicts(arr_tmp)[0]
    except:
        CQT.msgbox(f'Ошибка входных данных')
        return 0
    spis = list_mat_for_complex(self, ima_operacii, tag=int(dict_tmp['Изделие']))
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) * F.valm(dict_tmp['Масса_изделия,кг']) / 1000, 8))
    return spis


def komp_drobestryi(self, ima_operacii, arr_tmp):
    ploshad = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Площадь поверхности,м2')])  # Материал:str (1 - 12)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) * ploshad, 8))
    return spis


def komp_kontrol_tcvet_defekt(self, ima_operacii, arr_tmp):
    vrema = kontrol_tcvet_defekt(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_kontrol_mech_obrabot(self, ima_operacii, arr_tmp):
    vrema = kontrol_mech_obrabot(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_kontrol_form_i_raspoloj_poverhn(self, ima_operacii, arr_tmp):
    vrema = kontrol_form_i_raspoloj_poverhn(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_kantovanie(self, ima_operacii, arr_tmp):
    vrema = kantovanie(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_slesarnaya_razdelka_kromok(self, ima_operacii, arr_tmp):
    vrema = sles_razd_krom(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_shtampovochnaya(self, ima_operacii, arr_tmp):
    vrema = shtamp_perf(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_formovka_linz(self, ima_operacii, arr_tmp):
    vrema = formovka_linz(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_ukladka_nabivki(self, ima_operacii, arr_tmp):
    vrema = ukladka_nabivki(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_slesarnaya_snyatie_zausentcev(self, ima_operacii, arr_tmp):
    vrema = sles_zausenci(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_slesarnaya_sverlen(self, ima_operacii, arr_tmp):
    vrema = sles_sverl(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_slesarnya_pravka_v_plos(self, ima_operacii, arr_tmp):
    vrema = sles_prav(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_slesarnaya_zach_shvov(self, ima_operacii, arr_tmp):
    vrema = sles_zach_shvov(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_sverlilnaya(self, ima_operacii, arr_tmp):
    vrema = sverlil(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def int_to_str(len_s: int, number: int):
    str_num = str(number)
    if number < 10:
        return '0' * (len_s - 1) + str_num
    if number < 100:
        return '0' * (len_s - 2) + str_num
    return str_num


def komp_svarka(self, ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    spis_prov = None
    vrema = svarka(ima_operacii, arr_tmp)
    # Материал:str (1 - 12)

    conn, cur = CSQ.connect_bd(self.db_mater)
    try:
        SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

        for key in SLOV_ZAMEN.keys():
            arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')] = arr_tmp[1][
                F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')].replace(key, SLOV_ZAMEN[key])
            arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')] = arr_tmp[1][
                F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].replace(key, SLOV_ZAMEN[key])
            arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')] = arr_tmp[1][
                F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].replace(key, SLOV_ZAMEN[key])
            arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')] = arr_tmp[1][
                F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].replace(key, SLOV_ZAMEN[key])
            arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')] = arr_tmp[1][
                F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')].replace(key, SLOV_ZAMEN[key])

        koef_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')].split(
            ";")  # Коэффициент сложности:str
        vid_shva_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].split(";")  # Виды швов:str
        dl_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].split(";")  # Длина швов,мм:str
        tolsh_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].split(";")  # толщина
        mat_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].split(";")
        arr_vid_svarki = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')].split(";")

        DICT_KOD_VALS_SVARKA = Data_oper_norm.DICT_KOD_VALS_SVARKA

        for key in DICT_KOD_VALS_SVARKA['Виды швов'].keys():
            for i, vid in enumerate(vid_shva_arr):
                if key == vid:
                    vid_shva_arr[i] = DICT_KOD_VALS_SVARKA['Виды швов'][key]

        dict_prov = dict()

        spis_extra = []

        for i in range(len(koef_arr)):
            nr_prov = 0

            vid_shva = vid_shva_arr[0] if len(vid_shva_arr) <= 1 else vid_shva_arr[i]

            tolsh = F.valm(tolsh_arr[0]) if len(tolsh_arr) <= 1 else F.valm(tolsh_arr[i])
            mat = mat_arr[0] if len(mat_arr) <= 1 else mat_arr[i]
            plotn = F.valm(table(put + F.sep() + 'table7.txt', mat))
            koef_sl = koef_arr[0] if len(koef_arr) <= 1 else koef_arr[i]
            dlina = F.valm(dl_arr[i])
            kod_prov = list_mat_for_complex(self, ima_operacii, int(mat), int_to_str(2, tolsh), conn=conn)
            vid_svarki = arr_vid_svarki[0] if len(arr_vid_svarki) <= 1 else arr_vid_svarki[i]
            if kod_prov == []:
                continue
            else:
                kod_prov = kod_prov[-1][0]

            query = f"""SELECT Наименование, ЕдиницаИзмерения FROM nomen WHERE Код == '{kod_prov}' """
            naim_prov, edizm_prov = CSQ.custom_request_c(self.db_mater, query, conn=conn)[-1]

            putf = put + F.sep() + 'table2.txt'
            koef_sl_rez = F.valm(table(putf, koef_sl))  # оставить

            putf = put + F.sep() + 'table4.txt'
            pl_pop_sech = F.valm(table(putf, vid_shva)) * tolsh

            nr_prov += koef_sl_rez * pl_pop_sech * plotn * dlina / 1000000
            if kod_prov in dict_prov:
                dict_prov[kod_prov][-1] += nr_prov
            else:
                dict_prov[kod_prov] = [kod_prov, naim_prov, edizm_prov, nr_prov]

            if int(vid_svarki) == 20:
                spis = list_mat_for_complex(self, ima_operacii, 20, conn=conn)  # полуавтомат
            if int(vid_svarki) == 21:
                spis = list_mat_for_complex(self, ima_operacii, 21, str(mat), conn=conn)  # аргон
                spis2 = list_mat_for_complex(self, ima_operacii, 21, '-', conn=conn)  # аргон
                for item_extra in spis2:
                    spis_extra.append(item_extra)
            for item_extra in spis:
                spis_extra.append(item_extra)

        spis_prov = [v for k, v in dict_prov.items()]
        for i in range(len(spis_prov)):
            spis_prov[i][-1] = str(round(spis_prov[i][-1], 8))

        for i in range(len(spis_extra)):
            spis_prov.append([spis_extra[i][0], spis_extra[i][1], spis_extra[i][2],
                              str(round(F.valm(spis_extra[i][-1]) / 480 * vrema, 8))])

    except:
        pass
    finally:
        CSQ.close_bd(conn)
        return spis_prov


def komp_sborka_obschaya(self, ima_operacii, arr_tmp):
    vrema = sbor_obsh(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_sborka_linz(self, ima_operacii, arr_tmp):
    vrema = sborka_linz(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_reykodolbejnaya(self, ima_operacii, arr_tmp):
    vrema = reykodolbejnaya(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_peremeschenie(self, ima_operacii, arr_tmp):
    vrema = peremeschenie(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_otrezka_slesar(self, ima_operacii, arr_tmp):
    vrema = otrez_sles(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_kontrol(ima_operacii, arr_tmp):
    pass


def komp_komplektov(self, ima_operacii, arr_tmp):
    vrema = komplektov(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_gravirov(self, ima_operacii, arr_tmp):
    vrema = gravir(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_tokarnaya(self, ima_operacii, arr_tmp):
    vrema = tokarnaya(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_lazernaya_rezka(self, ima_operacii, arr_tmp):
    vrema = lazer(ima_operacii, arr_tmp)
    obor = 0
    spis = list_mat_for_complex(self, ima_operacii, tag=obor)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_rezka_plazma(self, ima_operacii, arr_tmp):
    vrema = rezka_plazma(ima_operacii, arr_tmp)
    obor = 1
    spis = list_mat_for_complex(self, ima_operacii, tag=obor)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_valtcovka_linz(self, ima_operacii, arr_tmp):
    vrema = valtcovka_linz(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_gibka(self, ima_operacii, arr_tmp):
    vrema = gibka(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_sles_rezba(self, ima_operacii, arr_tmp):
    vrema = sles_rezba(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_frezernaya(self, ima_operacii, arr_tmp):
    vrema = F.valm(arr_tmp[1][0])
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_sb_pod_sv(self, ima_operacii, arr_tmp):
    vrema = sb_pod_sv(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_gilotina(self, ima_operacii, arr_tmp):
    vrema = gilotina(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_otrezka_lentopil(self, ima_operacii, arr_tmp):
    vrema = otrez_lentopil(ima_operacii, arr_tmp)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(F.valm(spis[i][-1]) / 480 * vrema, 8))
    return spis


def komp_valcovka(self, ima_operacii, arr_tmp):
    vrema = valcovka(ima_operacii, arr_tmp)
    # putf = F.scfg('cash') + F.sep() + "tables" + F.sep() + "kmp" + F.sep() + ima_operacii + F.sep() + 'table1.txt'
    # spis = table_kmp(putf)
    spis = list_mat_for_complex(self, ima_operacii)
    for i in range(len(spis)):
        spis[i][-1] = str(round(spis[i][-1] / 480 * vrema, 8))
    return spis


def kontrol_mech_obrabot(ima_operacii, arr_tmp):
    vrem = F.valm(arr_tmp[1][0]) * 0.1
    return vrem


def kontrol_tcvet_defekt(ima_operacii, arr_tmp):
    dlina_shvov = int(F.round_up(arr_tmp[1][0]))
    vid_DSE = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид ДСЕ')])
    koef_DSE = 1 if vid_DSE == '1' else 1.3 if vid_DSE == '2' else 1.5
    vremya_tcvet_defect = koef_DSE * (8 * dlina_shvov / 1000 + 3 * dlina_shvov / 1000)
    return vremya_tcvet_defect


def kontrol_form_i_raspoloj_poverhn(ima_operacii, arr_tmp):
    vid_DSE = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид ДСЕ')])
    dlina_shvov = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')]))
    koef_DSE = 1 if vid_DSE == '1' else 1.3 if vid_DSE == '2' else 1.5

    vremya_obschee = koef_DSE * (8 * dlina_shvov / 1000 + 3 * dlina_shvov / 1000)
    return vremya_obschee


def reykodolbejnaya(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    modul = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Модуль зуба')])
    dlina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])

    putf = put + F.sep() + 'table1.txt'
    N_vr = modul * dlina / 1000
    return N_vr


def peremeschenie(ima_operacii, arr_tmp):
    # Маршрут:str;Вид транспорта:str;Масса,кг:int;Длинномерность:int;Количество точек крепления:int;
    put = OperationConfig.operation_table_path(ima_operacii)

    gfd = GetFromDataclass(ima_operacii, arr_tmp)
    way = gfd.get('Маршрут')
    tr = gfd.get('Вид транспорта')
    mass = gfd.get('Масса,кг')
    hook_quantity = gfd.get('Количество точек крепления')
    long_length = gfd.get('Длинномерность')

    if tr == '3':
        time_one_detail = 4.88 if hook_quantity == 1 else 5.02
        K_long_length, workers_quantity = (1.3, 2) if long_length == 1 else (1, 1)
        res = time_one_detail * K_long_length
        tpz_procent = 18
        tpz = res * tpz_procent / 100
        res = tpz + res
        res = workers_quantity * res
        return res

    putf = put + F.sep() + 'table1.txt'
    if tr == '1':
        koef_kol = 300 // mass
    elif tr == '2':
        koef_kol = 2100 // mass
    N_vr = table(putf, way, tr) / koef_kol
    return N_vr


def komplektov(ima_operacii, arr_tmp):
    massa = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса,кг')])
    if massa <= 0.3:
        Nvr = 2 / 60
    else:
        if massa > 25:
            Nvr = 9 / 60
        else:
            Nvr = 5 / 60
    return Nvr


def lazer(ima_operacii, arr_tmp):
    # Материал(1-черн,2-нерж):int;Толщина,мм:int;Периметр, мм:int;время_из_металликс:int;использовать_металликс:int;лазер_1плазма_2:int;число_резов:int;количество_сегментов:int
    put = OperationConfig.operation_table_path(ima_operacii)

    mat = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    s = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])
    lenth_slice = float(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Периметр, мм')])
    is_mettalics = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'использовать_металликс')])
    mettalics_time = float(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'время_из_металликс')])
    lazer = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'лазер_1плазма_2')])
    Vrez = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'число_резов')])
    segment = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'количество_сегментов')])

    if is_mettalics == 1:
        return mettalics_time * 2 * segment

    if lazer == 1:
        putf = put + F.sep() + 'сталь_нерж.txt'
    else:
        putf = put + F.sep() + 'плазма_черн_нерж.txt'

    if mat == '2':
        nvr = table(putf, '2', s)
    else:
        nvr = table(putf, '1', s)

    N_v = (lenth_slice / 1000 * nvr + Vrez / 60) * segment * 2
    return N_v


def rezka_plazma(ima_operacii, arr_tmp):
    # Материал(1-черн,2-нерж):int;Толщина,мм:int;Периметр, мм:int;время_из_металликс:int;использовать_металликс:int
    put = OperationConfig.operation_table_path(ima_operacii)

    mat = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    s = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])
    lenth_slice = float(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Периметр, мм')])
    is_mettalics = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'использовать_металликс')])
    mettalics_time = float(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'время_из_металликс')])

    if is_mettalics == 1:
        return mettalics_time * 2

    putf = put + F.sep() + 'плазма_черн_нерж.txt'

    if mat == '2':
        nvr = table(putf, '2', s)
    else:
        nvr = table(putf, '1', s)

    N_v = (nvr * lenth_slice / 1000) * 2
    return N_v


def lazer_old(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][5] = arr_tmp[1][5].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][6] = arr_tmp[1][6].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][7] = arr_tmp[1][7].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][8] = arr_tmp[1][8].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][9] = arr_tmp[1][9].replace(key, SLOV_ZAMEN[key])

    no_arr = arr_tmp[1][5].split(";")  # число отверстий
    do_arr = arr_tmp[1][6].split(";")  # Диаметр отверстий
    np_arr = arr_tmp[1][7].split(";")  # Число пазов
    lp_arr = arr_tmp[1][8].split(";")  # Длина паза
    bp_arr = arr_tmp[1][9].split(";")  # Ширина поаза

    if len(no_arr) != len(do_arr) or len(np_arr) != len(lp_arr) or len(np_arr) != len(bp_arr):
        # CQT.msgbox('Число переменных не корректно')
        return 0

    mat = str(arr_tmp[1][0])
    s = F.valm(arr_tmp[1][1])
    d = F.valm(arr_tmp[1][2])
    l = F.valm(arr_tmp[1][3])
    b = F.valm(arr_tmp[1][4])

    nsec = int(arr_tmp[1][10])
    obor = str(arr_tmp[1][11])

    if obor == '0':  # laser
        putf = put + F.sep() + 'tabl1.txt'
    else:
        putf = put + F.sep() + 'tabl2.txt'
    skorost = table(putf, mat, s)

    if d == 0:
        perimetr_konura = (l + b) * 2
        shir = b
    else:
        perimetr_konura = d * 3.141592
        shir = 50
        for i in range(len(no_arr)):
            if F.valm(no_arr[i]) == 1:
                shir = (d - do_arr[i]) / 2

    perim_otv = 0
    for i in range(len(no_arr)):
        perim_otv = perim_otv + F.valm(no_arr[i]) * F.valm(do_arr[i]) * 3.141592

    perim_paz = 0
    for i in range(len(np_arr)):
        perim_paz = perim_paz + F.valm(np_arr[i]) * (F.valm(lp_arr[i]) + F.valm(bp_arr[i])) * 2

    kontur = ((perimetr_konura + perim_otv + perim_paz) / nsec + (2 * nsec * shir)) / 1000
    return round(kontur * skorost, 3)


def kantovanie(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    massa = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса,кг')]))
    ugol = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'угол поворота(0-90град,1-180град)')]))
    ploskost = int(
        F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'плоскость поворота(0-горзонт,1-веритикаль)')]))
    tpz = 3

    if ploskost == 0:
        putf = put + F.sep() + 'table1.txt'
    else:
        putf = put + F.sep() + 'table2.txt'
    Nvr = table(putf, ugol, massa)

    return Nvr


def sles_razd_krom(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].replace(key, SLOV_ZAMEN[key])
    material_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')].split(";")
    vid_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].split(";")
    dlina_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].split(";")
    tolsh_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].split(";")

    putf = put + F.sep() + 'table1.txt'

    summ_vr = 0

    for i in range(len(vid_arr)):
        km = 1 if str(material_arr[i]) == '1' else 1.5
        vid = str(vid_arr[i])
        dlina = F.valm(dlina_arr[i])
        tolsh = F.valm(tolsh_arr[i])
        Nvr = table(putf, tolsh, vid)
        N_v = Nvr * dlina * km
        summ_vr += N_v

    return summ_vr


def tokarnaya(ima_operacii, arr_tmp):
    return 0.01


def frezernaya(ima_operacii, arr_tmp):
    return 0.01


def sles_rezba(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    hat_c = arr_tmp[0].copy()
    for key in SLOV_ZAMEN.keys():
        for head in hat_c:
            nk_head = F.num_col_by_name_in_hat_c(arr_tmp, head)
            arr_tmp[1][nk_head] = arr_tmp[1][nk_head].replace(key, SLOV_ZAMEN[key])
    count_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во отв')].split(";")
    mat_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')].split(";")
    gluh_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Тип отв.(глухое(1)нет(0))')].split(";")
    diam_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр отверстий')].split(";")
    glub_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина сверления')].split(";")

    if len(count_arr) != len(gluh_arr):
        return 0

    summ_vr = 0

    putf = put + F.sep() + 'table1.txt'


    for i in range(len(count_arr)):

        material = str(mat_arr[i])
        gluh = str(gluh_arr[i])
        diam = F.valm(diam_arr[i])
        glub = F.valm(glub_arr[i])

        km = 1 if material == '1' else 1.5
        kg = 1.2 if gluh == '1' else 1
        n = float(count_arr[i])
        Nvr = table(putf, diam, glub)
        N_v = Nvr * n * km * kg
        summ_vr += N_v

    return summ_vr


def shtamp_perf(ima_operacii, arr_tmp):
    dlina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'длина заготовки детали, мм')])
    n = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'кол-во деталей')])
    N_vr = dlina / 1000 * 11.2 * n
    return N_vr


def sles_sverl(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    material = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    diametr = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр,мм')])
    tolshina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])
    n = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во отв.')])

    putf = put + F.sep() + 'table1.txt'
    Nvr = table(putf, diametr, tolshina)
    km = 1 if material == '1' else 1.5
    N_vr = Nvr * km * n
    return N_vr


def sverlil(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    material = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во отв')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во отв')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Тип отв.(глухое(1)нет(0))')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Тип отв.(глухое(1)нет(0))')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр отверстий')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр отверстий')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина сверления')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина сверления')].replace(key, SLOV_ZAMEN[key])
    n_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во отв')].split(";")
    gluh_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Тип отв.(глухое(1)нет(0))')].split(";")
    diam_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр отверстий')].split(";")
    glub_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Глубина сверления')].split(";")

    if len(n_arr) != len(gluh_arr):
        return 0

    summ_vr = 0

    putf = put + F.sep() + 'table1.txt'

    km = 1 if material == '1' else 1.5

    for i in range(len(n_arr)):
        n = F.valm(n_arr[i])
        gluh = str(gluh_arr[i])
        diam = F.valm(diam_arr[i])
        glub = F.valm(glub_arr[i])

        kg = 1.1 if gluh == '1' else 1

        Nvr = table(putf, diam, glub)
        N_v = Nvr * n * km * kg
        summ_vr += N_v

    return summ_vr


def sles_prav(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    dlina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])
    shir = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина,мм')])
    tolsh = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])
    plosh = dlina * shir * 0.000001
    plosh = round(plosh, 2)

    putf = put + F.sep() + 'table1.txt'
    Nvr = table(putf, plosh, tolsh)
    return Nvr


def drobestrui(ima_operacii, arr_tmp):
    protected_surface = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Пол закрыт(1-да,0-нет)')])
    plosh = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Площадь поверхности,м2')])
    chislo_mest = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'число мест защ.')])
    slogn_izd = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Сложность(1-да,0-нет)')])
    quantity = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')]))  # добавлено

    Nvr = 18 if protected_surface == '1' else 15

    tpz = 1.5
    koef = 1.4 if slogn_izd == '1' else 1

    if chislo_mest == 0:
        N_v = Nvr * plosh * koef * quantity
    else:
        N_v = Nvr * plosh * koef + (tpz * chislo_mest) * quantity

    return N_v


def otrez_sles(ima_operacii, arr_tmp):
    vid = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид ДСЕ')])
    diametr = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр,мм')])
    tolsh = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])
    vis_prof = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Выс.профиля')])
    kol_vo_rez = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число резов')]))
    material = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])

    Km = 1.5 if material == '2' else 1
    Nvr = 0
    if vid == '1':
        arr = [1.5, 1.6, 1.7, 1.75, 1.8]
        k_d = 0
        if diametr >= 0 and diametr <= 5:
            k_d = 0
        if diametr > 5 and diametr <= 10:
            k_d = 1
        if diametr > 10 and diametr <= 15:
            k_d = 2
        if diametr > 15 and diametr <= 20:
            k_d = 3
        if diametr > 20 and diametr <= 25000:
            k_d = 4
        Nvr = arr[k_d]
    if vid == '2':
        arr = [1.8, 1.9, 2.05, 2.15, 2.25, 2.3, 2.35, 2.4]
        k_d = 0
        if vis_prof >= 0 and vis_prof <= 20:
            k_d = 1 if tolsh == 4 else 0
        if vis_prof > 20 and vis_prof <= 25:
            k_d = 3 if tolsh == 4 else 2
        if vis_prof > 25 and vis_prof <= 28:
            k_d = 4
        if vis_prof > 28 and vis_prof <= 32:
            k_d = 6 if tolsh == 4 else 5
        if vis_prof > 32 and vis_prof <= 333:
            k_d = 7
        Nvr = arr[k_d]
    if vid == '3':
        arr = [1.5, 1.55, 1.6, 1.65, 1.7]
        k_d = 0
        if diametr >= 0 and diametr <= 8:
            k_d = 0
        if diametr > 8 and diametr <= 10:
            k_d = 1
        if diametr > 10 and diametr <= 12:
            k_d = 2
        if diametr > 12 and diametr <= 14:
            k_d = 3
        if diametr > 14 and diametr <= 25000:
            k_d = 4
        Nvr = arr[k_d]
    if vid == '4':
        arr = [1.9, 2.05, 2.3, 2.75, 3.25, 3.7, 4.2, 4.45, 4.7, 5.2]
        k_d = 0
        if vis_prof >= 0 and vis_prof <= 10:
            k_d = 0
        if vis_prof > 10 and vis_prof <= 15:
            k_d = 1
        if vis_prof > 15 and vis_prof <= 20:
            k_d = 2
        if vis_prof > 20 and vis_prof <= 25:
            k_d = 3
        if vis_prof > 25 and vis_prof <= 30:
            k_d = 4
        if vis_prof > 30 and vis_prof <= 35:
            k_d = 5
        if vis_prof > 35 and vis_prof <= 40:
            k_d = 6
        if vis_prof > 40 and vis_prof <= 42:
            k_d = 7
        if vis_prof > 42 and vis_prof <= 45:
            k_d = 8
        if vis_prof > 45 and vis_prof <= 5000:
            k_d = 9
        Nvr = arr[k_d]
    if vid == '5':
        arr = [0.85, 1.1, 1.65, 2.2, 2.75, 3.3, 3.85, 4.4, 5.5]
        k_d = 0
        if tolsh >= 0 and tolsh <= 1.5:
            k_d = 0
        if tolsh > 1.5 and tolsh <= 2:
            k_d = 1
        if tolsh > 2 and tolsh <= 3:
            k_d = 2
        if tolsh > 3 and tolsh <= 4:
            k_d = 3
        if tolsh > 4 and tolsh <= 5:
            k_d = 4
        if tolsh > 5 and tolsh <= 6:
            k_d = 5
        if tolsh > 6 and tolsh <= 7:
            k_d = 6
        if tolsh > 7 and tolsh <= 8:
            k_d = 7
        if tolsh > 8 and tolsh <= 8888:
            k_d = 8
        Nvr = arr[k_d] / 1000
        Km = kol_vo_rez
    N_v = Nvr * Km * kol_vo_rez

    return N_v


def formovka_linz(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    dlina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])
    krug_linz = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид изделия')])
    quantity = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')]))  # добавлено

    putf = put + F.sep() + 'tabl1.txt'
    Nvr = table(putf, dlina)
    koef = 0.4 if krug_linz == '1' else 1
    N_v = Nvr * dlina / 1000 * koef * quantity
    return N_v


def ukladka_nabivki(ima_operacii, arr_tmp):
    plosh = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Площадь поверхности,м2')])
    vid_pov = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид поверхности')])
    gabarit = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])
    quantity = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')]))  # добавлено

    if vid_pov == '1':
        if gabarit < 500:
            Ttr = 24
        elif gabarit < 800:
            Ttr = 18
        else:
            Ttr = 15
    else:
        Ttr = 18

    N_v = Ttr * plosh * quantity

    return N_v


def sborka_linz(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    material = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    chislo_uzlov = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')]))
    mass = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса,кг')])
    km = 1.2 if material == '2' else 1

    putf = put + F.sep() + 'table1.txt'
    Nvr = table(putf, mass, chislo_uzlov)
    N_v = Nvr * km
    return N_v


def svarka(ima_operacii, arr_tmp):
    # Z:\Data\TehKart\Data\bin\tables\Сварка
    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    put = OperationConfig.operation_table_path(ima_operacii)

    if len(arr_tmp[0]) == 0:
        return None
    material = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')])

    DICT_MAT = {"1": 1,
                "2": 1.15,
                "3": 1.00,
                "4": 1.00,
                "5": 1.15,
                "6": 1.15,
                "7": 1.15,
                "8": 1.15,
                "9": 0,
                "10": 0,
                "11": 0,
                "12": 0
                }

    DICT_POL_SHVA = {'1': 1, '2': 1.18, '3': 1.32, '4': 1.5, '5': 1.15, '6': 1.4}
    DICT_OBMAZ = {'С': {'1': 0.35, '2': 0.38, '3': 0.38, '4': 0.41, '5': 0.57, '6': 0.62},
                  'Н': {'1': 0.35, '2': 0.38, '3': 0.38, '4': 0.41, '5': 0.57, '6': 0.62},
                  'Т': {'1': 0.43, '2': 0.46, '3': 0.46, '4': 0.51, '5': 0.63, '6': 0.65},
                  'У': {'1': 0.43, '2': 0.46, '3': 0.46, '4': 0.51, '5': 0.63, '6': 0.65},
                  }

    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].replace(key, SLOV_ZAMEN[key])

    if F.num_col_by_name_in_hat_c(arr_tmp, 'Положение шва') == None:
        tmp = ';'.join(['1' for _ in arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].split(";")])
        arr_tmp[0].append('Положение шва')
        arr_tmp[1].append(tmp)
    arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')] = arr_tmp[1][
        F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].upper()
    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Положение шва')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Положение шва')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].replace(key, SLOV_ZAMEN[key])

    vid_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].split(";")
    dlina_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].split(";")
    tolsh_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].split(";")
    arr_slognost = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')].split(";")
    arr_pol_shva = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Положение шва')].split(";")
    arr_quantity = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')].split(";")
    arr_vid_svarki = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')].split(";")
    arr_material = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')].split(";")

    DICT_KOD_VALS_SVARKA = Data_oper_norm.DICT_KOD_VALS_SVARKA

    for key in DICT_KOD_VALS_SVARKA['Виды швов'].keys():
        for i, vid in enumerate(vid_arr):
            if key == vid:
                vid_arr[i] = DICT_KOD_VALS_SVARKA['Виды швов'][key]

    if len(dlina_arr) != len(vid_arr):
        return 0
    if len(dlina_arr) != len(tolsh_arr):
        return 0

    summ_vr = 0

    # km = 1 if material == '1' else 1.5
    for i in range(len(vid_arr)):

        vid = vid_arr[0] if len(vid_arr) <= 1 else vid_arr[i]
        dlina = F.valm(dlina_arr[i])
        tolsh = F.valm(tolsh_arr[i])
        slognost = arr_slognost[0] if len(arr_slognost) <= 1 else arr_slognost[i]
        pol_shva = arr_pol_shva[0] if len(arr_pol_shva) <= 1 else arr_pol_shva[i]
        quantity = arr_quantity[0] if len(arr_quantity) <= 1 else arr_quantity[i]
        vid_svarki = arr_vid_svarki[0] if len(arr_vid_svarki) <= 1 else arr_vid_svarki[i]
        material = arr_material[0] if len(arr_material) <= 1 else arr_material[i]

        km = DICT_MAT[material]
        kysl = 1
        if slognost == '1':
            kysl = 1.03
        if slognost == '2':
            kysl = 1.1
        if slognost == '3':
            kysl = 1.05

        kpol = DICT_POL_SHVA[pol_shva]

        tvsp = DICT_OBMAZ[vid[0]][pol_shva]
        if vid_svarki == '20':
            putf = put + F.sep() + 'table1.txt'
        else:
            if material == 9:
                km = 1
                kysl = 1
                tvsp = 0
                putf = put + F.sep() + 'table10.txt'
            else:
                putf = put + F.sep() + 'table11.txt'

        Nvr = table(putf, tolsh, vid)

        N_v = Nvr * dlina / 1000 * km * kysl * kpol + tvsp
        summ_vr += N_v

    return round(summ_vr, 2), 3


def svarka_old(ima_operacii, arr_tmp):  # 05.03.2024
    put = OperationConfig.operation_table_path(ima_operacii)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN
    material = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал')])
    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')].replace(key, SLOV_ZAMEN[key])

    vid_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Виды швов')].split(";")
    dlina_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')].split(";")
    tolsh_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')].split(";")
    arr_slognost = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Коэффициент сложности')].split(";")
    quantity = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')].split(";")
    quantity = int(quantity[0])

    if ';' in arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')]:
        vid_svarki = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')].split(";")[
            0]  # Вид сварки(20-П,21-А)
    else:
        vid_svarki = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид сварки(20-П,21-А)')]
    if len(dlina_arr) != len(vid_arr):
        return 0
    if len(dlina_arr) != len(tolsh_arr):
        return 0

    summ_vr = 0
    putf = put + F.sep() + 'table6.txt'
    km = table(putf, material)

    # km = 1 if material == '1' else 1.5
    for i in range(len(vid_arr)):
        dlina = F.valm(dlina_arr[i])
        vid = vid_arr[i]
        tolsh = F.valm(tolsh_arr[i])

        slognost = arr_slognost[i]
        ks = 1
        if slognost == '1':
            ks = 1.05
        if slognost == '2':
            ks = 1.1

        if material == '9':
            putf = put + F.sep() + 'table10.txt'
            km = 1
        else:
            putf = put + F.sep() + 'table1.txt'

        Nvr = table(putf, tolsh, vid)

        N_v = Nvr * dlina / 1000 * km * ks
        summ_vr += N_v

    return summ_vr


def sles_razmetka(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    SLOV_ZAMEN = Data_oper_norm.SLOV_ZAMEN

    for key in SLOV_ZAMEN.keys():
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид ДСЕ')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Вид ДСЕ')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина элемента')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Длина элемента')].replace(key, SLOV_ZAMEN[key])
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Сложность')] = arr_tmp[1][
            F.num_col_by_name_in_hat_c(arr_tmp, 'Сложность')].replace(key, SLOV_ZAMEN[key])

    vid_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид ДСЕ')].split(";")
    dlina_arr = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина элемента')].split(";")
    arr_slognost = arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Сложность')].split(";")

    if len(dlina_arr) != len(vid_arr):
        return 0
    if len(dlina_arr) != len(arr_slognost):
        return 0
    summ_vr = 0

    for i in range(len(vid_arr)):
        dlina = F.valm(dlina_arr[i])
        vid = vid_arr[i]
        slognost = arr_slognost[i]
        putf = put + F.sep() + 'table2.txt'
        ks = table(putf, slognost)
        putf = put + F.sep() + 'table1.txt'
        nvr = table(putf, vid)

        N_v = (nvr * dlina / 1000) * ks
        summ_vr += N_v

    return round(summ_vr, 2)


def otrez_lentopil(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    material = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-ЧНЛ,2-ЧВЛ,3-нерж)')])
    diametr = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр,мм')])
    vid = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид изделия')])

    putf = put + F.sep() + 'table1.txt'
    tst = table(putf, diametr, material)
    koef_trub = 0.4 if vid == '1' else 1

    N_v = tst * koef_trub + 1

    return N_v


def surface_cleaning(arr_tmp):
    '''зачистка поверхности'''
    long = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])
    width = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина,мм')])
    quantity = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Количество')])
    pressure = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Давление')])
    surface = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Тип поверхности(1плоская 2 криволинейная)')])

    К_endurance = 0.9 if pressure < 590 else 1 if pressure <= 740 else 1.2  # к прочности
    К_detail = 1.3 if quantity < 3 else 1.1 if quantity < 6 else 1 if quantity < 11 else 0.95 if quantity < 16 else 0.9 if quantity < 25 else 0.85  # Кп
    К_surface = 0.0124 if surface else 0.0148
    T_unit = К_surface * К_endurance * width ** 0.37 * long ** 0.65
    N_v = T_unit * К_detail * 1.3

    return N_v


def chamfering(arr_tmp):
    '''снятие фаски'''
    type_of_removal = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, '1-фаска, 2-паз')])
    long = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])

    T_vsp = 12.35 if type_of_removal == 2 else 14.53
    t_remove = 0.011 if type_of_removal == 2 else 0.019
    T_unit = T_vsp + t_remove * long
    N_v = T_unit * 1.3

    return N_v


def okras(ima_operacii, arr_tmp):
    # добавить в базу
    # Вид изделия:str;Оборудование:str;Длина,мм:int;Ширина,мм:int;Сложность:str;Площадь поверхности,м2:int;Число шпилек/створок:int;Количество деталей:int;Шильда(1-есть):str
    put = OperationConfig.operation_table_path(ima_operacii)

    vid_izd = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид изделия')])
    tip_oborud = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Оборудование')])
    dlina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])
    shirina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина,мм')])
    slognost = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Сложность')])
    ploshad = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Площадь поверхности,м2')])
    ch_st_shp = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число шпилек/створок')]))
    nameplate = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Шильда(1-есть)')])
    n = int(F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Количество деталей')]))
    mass = int(F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса,кг')]))

    gabarit = dlina if dlina > shirina else shirina

    if tip_oborud == '1':
        putf = put + F.sep() + 'tabl1.txt'
    else:
        putf = put + F.sep() + 'tabl2.txt'

    nvr = table(putf, gabarit, slognost)

    if slognost == '1':
        Tpol = 0.596 * pow(0.29, 0.29) if ploshad <= 0.1 else 1.443 * pow(0.82, 0.82) if ploshad <= 10 else 1.3 * pow(
            0.82, 0.82)
    elif slognost == '2':
        Tpol = 0.745 * pow(0.29, 0.29) if ploshad <= 0.1 else 2.02 * pow(0.82, 0.82) if ploshad <= 10 else 1.818 * pow(
            0.82, 0.82)
    elif slognost == '3':
        Tpol = 0.85 * pow(0.29, 0.29) if ploshad <= 0.1 else 2.881 * pow(0.82, 0.82) if ploshad <= 10 else 2.593 * pow(
            0.82, 0.82)

    if vid_izd == '1':
        N_v = (ploshad * nvr + ch_st_shp * 6.5 + Tpol) * n
    elif vid_izd == '2':
        N_v = (ploshad * nvr + ch_st_shp * 0.4 + Tpol) * n
    else:
        N_v = (ploshad * nvr + Tpol) * n

    tkontr = 0.08
    Nside = 1 if vid_izd == '0' else 2
    Ndot = 2 if gabarit < 1600 else 3
    tcantin = 0 if mass < 50 else 8 if mass <= 500 else 15 if mass <= 1000 else 32
    toverturn = 0.06 if gabarit <= 630 else 0.7 if gabarit <= 1600 else 0
    tunfolding = 0.06 if gabarit <= 630 else 0.2 if gabarit <= 1600 else 0.5
    tmark = 0.22
    tnameplate = 1.7 if nameplate == '1' else 0
    tkomp = 0.05 if gabarit <= 630 else 0.15 if gabarit <= 1600 else 0
    ttrafic = 1.52

    tvs = tkontr * Nside * Ndot + tcantin + toverturn + tunfolding + tmark + tnameplate + tkomp + ttrafic
    Ttr = tvs * n

    return N_v + Ttr


def gilotina(ima_operacii, arr_tmp):
    rezi = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число резов')]))
    rezi = 4 if rezi > 4 else rezi
    if rezi == 1:
        N_v = 3.3
    elif rezi == 2:
        N_v = 4.6
    elif rezi == 3:
        N_v = 5.3
    elif rezi == 4:
        N_v = 6
    return N_v


def sles_zausenci(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    material = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    partia = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'кол-во штук')]))
    plosh = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Площадь поверхности,м2')])
    perimetr = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Периметр,мм')])

    putf = put + F.sep() + 'tabl1.txt'
    koef = table(putf, partia)

    if material == 1:
        N_v = 12.65 * plosh * koef * partia
    else:
        N_v = 0.64 * perimetr / 1000 * koef * partia

    return N_v


def gravir(ima_operacii, arr_tmp):
    dlina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])
    shir = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина,мм')])
    shirm = shir / 1000
    dlinam = dlina / 1000
    plosh = dlinam * shirm
    N_v = 0.17 + 113 * plosh
    return N_v


@dataclass
class Data_oper_norm():
    TRAP_STOP = {
        # резьба трапецевидная в упор {шаг (мин_предел, макс предел, шаг_добавления_больше_макс_диапазона) [диапазон коэф]}
        2: {
            (0, 21): [2.5, 3.8, 5, 6],
            (22, 30): [3, 4.6, 6, 7.5],
        },
        3: {
            (0, 35): [2, 2.9, 3.8, 4.7],
            (36, 45): [2.4, 3.6, 4.7, 6, 7],
        },
        4: {
            (0, 21): [16, 23, 29, 35],
            (22, 70, 18): [22, 32, 41, 50, 60, 73, 91],
        },
        5: {
            (0, 50, 12): [16.5, 23, 29, 35, 42, 51, 63],
            (51, 90, 19): [23, 33, 42, 52, 62, 76, 95],
            (91, 120, 24): [29, 38, 54, 66, 79, 97, 121],
        },
        6: {
            (0, 35, 8.5): [14, 18.5, 23, 27, 32, 39, 48],
            (36, 60, 11): [16, 22, 27, 33, 39, 47, 58],
            (61, 140, 18): [24, 33, 42, 51, 61, 74, 92],
        },
        8: {
            (0, 35, 8.5): [16.5, 20, 26, 30, 35, 42, 50],
            (36, 55, 11.5): [19, 25, 31, 37, 43, 52, 63],
            (56, 70, 14): [23, 31, 38, 45, 53, 64, 78],
        },
        10: {
            (0, 37, 9): [21, 27, 32, 36, 42, 49, 58],
            (38, 50, 11.5): [23.5, 31, 36.5, 42, 49, 58, 69],
            (50, 70, 13.5): [26, 34, 41, 48, 56, 66, 79],
            (71, 90, 15): [28, 37, 45, 52, 61, 73, 88],
        },
        12: {
            (0, 50, 8.5): [22.5, 28, 32, 36, 42, 49, 58],
            (51, 75, 11): [24, 31, 37, 42, 50, 58, 69],
            (76, 95, 14.5): [29, 37, 44, 51, 61, 72, 86],
            (95, 120, 17.5): [35, 45, 53, 62, 72, 85, 103],
        },
    }

    TRAP_TROUGH = {  # резьба трапецевидная напроход {шаг (мин_предел, макс предел) [диапазон коэф]}
        2: {
            (0, 20): [2, 2.2, 2.4, 2.5, 2.6, 2.8, 3.2],
            (21, 27): [2.1, 2.4, 2.6, 2.7, 2.9, 3.1, 3.6, 3.9],
            (28, 30): [2.3, 2.6, 2.8, 2.95, 3.1, 3.4, 4, 4.5, 5],
        },
        3: {
            (0, 30): [3.6, 4, 4.3, 4.45, 4.6, 5, 5.5, 6, 6.5, 9, 9.5, 10],
            (31, 45): [3.8, 4.3, 4.7, 4.85, 5, 5.5, 6, 6.5, 7.5, 10, 11, 11.5, 12.5],
            (45, 59): [4, 4.5, 5, 5.3, 5.5, 6, 6.5, 7.5, 8.5, 11.5, 12.5, 13.5, 14.5],
            (60, 80): [4.5, 5, 5.5, 6, 6.5, 7, 8, 9, 10.5, 13.5, 15, 16, 17.5, 19],
        },
        4: {
            (0, 16): [3.3, 3.6, 3.9, 4, 4.1, 4.2, 4.4],
            (17, 64): [3.4, 3.7, 4, 4.1, 4.2, 4.4, 4.7, 5],
            (65, 74): [4.5, 5, 5.5, 5.8, 6, 6.5, 7, 7.5, 9, 11.5, 3, 14, 15, 16],
            (75, 80): [4.9, 5.5, 6, 6.3, 6.5, 7.5, 8.5, 9.5, 11, 14.5, 16, 17.5, 19, 20],
        },
        5: {
            (0, 22): [3.8, 3.9, 4, 4.4, 4.8, 5, 5.5, 6, 6.5],
            (23, 45): [4, 4.2, 4.5, 4.8, 5, 5.5, 6, 6.5, 6, 9.5],
            (45, 95): [5.5, 5.7, 6, 6.5, 7, 8, 9, 10, 11.5, 15, 16.5, 18, 19.5, 21],
            (95, 130): [6, 6.5, 7, 7.5, 8, 9, 10.5, 12, 13.5, 18, 19.5, 21.5, 23.5, 25],
        },
        6: {
            (0, 35): [4.5, 4.8, 5, 5.2, 5.5, 6, 6.5, 7, 7.5, 10.5, 11, 12],
            (35, 80): [4.7, 5, 5.5, 5.8, 6, 6.5, 7, 7.5, 8.5, 11.5, 12.5, 13, 14],
            (81, 130): [8, 8.5, 9.5, 10, 11, 12, 14, 15.5, 18, 23, 25.5, 28, 30.5, 33],
            (131, 160): [8.5, 9.5, 11, 11.5, 12.5, 14, 16, 18.5, 21.5, 27, 30, 33.5, 36.5, 39.5],
        },
        8: {
            (0, 22): [5, 5.2, 5.5, 5.8, 6, 6.5, 7, 7.5, 8],
            (23, 35): [5, 5.2, 5.5, 6, 6.5, 6.5, 7, 7.5, 8.5, 11.5],
            (36, 55): [5.5, 6, 6.5, 6.8, 7, 7.5, 8.5, 9, 10, 13.5, 14.5, 15.5, 16, 17],
            (56, 70): [6.5, 7, 8, 8.3, 8.5, 9, 10, 11, 12, 16.5, 18, 19, 20, 21],
        },
        10: {
            (0, 37): [6, 6.5, 7, 7.3, 7.5, 8, 8.5, 9, 10, 14, 14.5, 15.5],
            (38, 48): [6.5, 7, 7.5, 7.7, 8, 8.5, 9, 10, 10.5, 15, 16, 17, 17.5, 18.5],
            (48, 70): [8, 8.5, 9, 9.5, 10, 11, 12, 13, 14.5, 19, 20.5, 22, 23.5, 24.5],
            (71, 90): [8.5, 9.5, 10, 10.5, 11, 12.5, 13, 14.5, 16.5, 21.5, 23, 25, 26.5, 28.5],
        },
        12: {
            (0, 46): [7.5, 8, 8.5, 9, 9.5, 10, 11, 11.5, 13, 17, 18, 19.5, 20.5, 21.5],
            (47, 70): [8.5, 9.5, 10, 10.5, 10.5, 11.5, 12.5, 13.5, 15, 18.5, 20, 21, 22.5, 23.5],
            (71, 90): [9, 10, 11, 11.3, 11.5, 12.5, 14, 15, 16.5, 22, 24, 25.5, 27, 29],
            (91, 120): [11, 12, 13, 13.5, 14, 15, 17, 18.5, 20.5, 27, 29.5, 31.5, 33.5, 36],
        }, }

    DICT_VID_TIME_UPACOVIVANIE = {1: 0.49, 2: 0, 3: 0.65, 4: 0.49}

    DICT_KOD_VALS_SVARKA = {"Виды швов": {'1': 'С1',
                                          '2': 'С2',
                                          '3': 'С6',
                                          '4': 'С7',
                                          '5': 'С8',
                                          '6': 'С11',
                                          '7': 'С12',
                                          '8': 'С15',
                                          '9': 'С17',
                                          '10': 'С25',
                                          '11': 'У1',
                                          '12': 'У2',
                                          '13': 'У4',
                                          '14': 'У5',
                                          '15': 'У8',
                                          '16': 'У9',
                                          '17': 'У10',
                                          '18': 'Т1',
                                          '19': 'Т3',
                                          '20': 'Т6',
                                          '21': 'Т7',
                                          '22': 'Т8',
                                          '23': 'Н1',
                                          '24': 'Н2',
                                          '25': 'Н4',
                                          }
                            }

    SLOV_ZAMEN = {',': '.', ' ': ';', '/': ';', '$': ';', 'c': 'с', 'C': 'С', 'T': 'Т', 'у': 'У', 'y': 'У', 'Y': 'У'}
    SET_BLOCK_LINE = {' ', '/', ';', '$'}
    DICT_OPERS_CALC = {
        # 'Упаковывание': { #
        #     "Масса_изделия,кг": {"type": "float", "comment": 'кг', "vals": {}},
        #     "Направление,кг": {"type": "float", "comment": '', "vals": {
        #         1: {'val': 'КЛ', 'prim': ''},
        #         2: {'val': 'КТ', 'prim': ''},
        #         3: {'val': 'ШГ', 'prim': ''},
        #         4: {'val': 'ПР', 'prim': ''},
        #     }},
        # },
        'Упаковывание': {
            'Площадь поддона': {"type": "float", "comment": 'кв.метры', "vals": {}},
            'Диаметр,мм': {"type": "float", "comment": 'мм', "vals": {}},
            'Количество': {"type": "float", "comment": '', "vals": {}},
            "Масса_изделия,кг": {"type": "float", "comment": 'кг', "vals": {}},
            "Изделие": {"type": "float", "comment": '', "vals": {
                1: {'val': 'КЛ', 'prim': ''},
                2: {'val': 'КТ', 'prim': ''},
                3: {'val': 'ШГ', 'prim': ''},
                4: {'val': 'ПР', 'prim': ''},
            }},
        },
        'Перемещение': {
            "Вид транспорта": {"type": "str", "comment": '', "vals": {
                1: {'val': 'Погрузчик', 'prim': '', 'show': ["Вид транспорта", 'Маршрут', 'Масса,кг']},
                2: {'val': 'Автомобиль', 'prim': '', 'show': ["Вид транспорта", 'Маршрут', 'Масса,кг']},
                3: {'val': 'Электромостовой кран', 'prim': '',
                    'show': ["Вид транспорта", 'Количество точек крепления', 'Длинномерность']},
            }},
            "Масса,кг": {"type": "float", "comment": 'кг', "vals": {}},
            "Маршрут": {"type": "str", "comment": '', "vals": {
                1: {'val': 'Заготовительный - сборочный', 'prim': ''},
                2: {'val': 'сборочный - малярный', 'prim': ''},
                3: {'val': 'сборочный - улица', 'prim': ''},
                4: {'val': 'малярный - улица', 'prim': ''},
            }},
            'Количество точек крепления': {"type": "int", "comment": '', "vals": {
                1: {'val': '2', 'prim': '2 крюка'},
                2: {'val': '4', 'prim': '4 крюка'},
            }},
            "Длинномерность":
                {"type": "int", "comment": '', "vals": {
                    1: {'val': 'Да',
                        'prim': 'Груз является длинномерным если его длинна и/или диаметр больше 3 метров'},
                    2: {'val': 'Нет',
                        'prim': 'Груз НЕ является длинномерным если его длинна и/или диаметр МЕНЬШЕ 3 метров'},
                }}},

        'Сборка под сварку': {
            "Вид конструкции": {"type": "str", "comment": '', "vals": {
                1: {'val': 'сборка металлоконструкций под сварку из листового металла', 'prim': '', 'show': [
                    'Условия', 'Материал', 'Вид конструкции', 'Масса,кг', 'Кол-во входящих ДСЕ', 'Длина стыков,мм',
                    'Толщина металла', 'Сопряжения узлов', 'Коэфф сложности', 'Изделие', 'Количество сварных узлов']},
                2: {'val': 'сборка металлоконструкций под сварку из профильного и листового металла', 'prim': '',
                    'show': [
                        'Условия', 'Материал', 'Вид конструкции', 'Масса,кг', 'Кол-во входящих ДСЕ', 'Длина стыков,мм',
                        'Толщина металла', 'Сопряжения узлов', 'Коэфф сложности', 'Изделие',
                        'Количество сварных узлов']},
                3: {'val': 'сборка металлоконструкций под сварку из профильного металла', 'prim': '', 'show': [
                    'Условия', 'Материал', 'Вид конструкции', 'Масса,кг', 'Кол-во входящих ДСЕ', 'Сопряжения узлов',
                    'Коэфф сложности', 'Изделие', 'Количество сварных узлов']},
                4: {'val': 'сборка плоских колец (фланцев) из сегментов (секторов)', 'prim': '', 'show': [
                    'Условия', 'Материал', 'Вид конструкции', 'Кол-во входящих ДСЕ', 'Толщина', 'Диаметр,мм',
                    'Число сегментов', 'Длина стыков,мм', 'Ширина фланцев,мм', 'Толщина металла']},
                5: {'val': 'сборка продольных стыков цилиндрических обечаек под сварку', 'prim': '', 'show': [
                    'Условия', 'Материал', 'Вид конструкции', 'Кол-во входящих ДСЕ', 'Толщина', 'Диаметр,мм',
                    'Длина обечайки', 'Коэфф сборки', 'Изделие', 'Толщина металла']},
                6: {'val': 'сборка продольных стыков конических обечаек под сварку', 'prim': '', 'show': [
                    'Условия', 'Материал', 'Вид конструкции', 'Кол-во входящих ДСЕ', 'Толщина', 'Диаметр,мм',
                    'Длина обечайки', 'Коэфф сборки', 'Изделие', 'Толщина металла']}}},
            "Масса,кг":
                {"type": "float", "comment": '', "vals": {}},
            "Кол-во входящих ДСЕ": {"type": "int", "comment": '', "vals": {}},
            "Материал": {"type": "int", "comment": '',
                         "vals": {1: {'val': 'Черный', 'prim': ''}, 2: {'val': 'Нерж', 'prim': ''}}},

            "Длина стыков,мм": {"type": "float", "comment": '', "vals": {}},
            "Толщина металла": {"type": "int", "comment": '', "vals": {}},
            "Сопряжения узлов": {"type": "float", "comment": '', "vals": {
                1: {'val': 'Простое',
                    'prim': 'Детали узлов расположены НЕ более чем в 3-х основных плоскостях под прямыми углами и имеют прямолинейные сопряжения'},
                2: {'val': 'Сложное',
                    'prim': 'Детали узлов расположены БОЛЕЕ чем в 3-х основных плоскостях и имеют криволинейные сопряжения'}}},
            "Изделие": {"type": "int", "comment": '', "vals": {
                1: {'val': 'КЛ', 'prim': ''},
                2: {'val': 'КТ', 'prim': ''},
                3: {'val': 'ШГ', 'prim': ''},
                4: {'val': 'ЛК', 'prim': ''},
                5: {'val': 'ГГ', 'prim': ''},
                6: {'val': 'ПН', 'prim': ''},
                7: {'val': 'ПР', 'prim': ''}}},
            "Коэфф сложности": {"type": "int", "comment": '', "vals": {1: {'val': 'Крупные ДСЕ',
                                                                           'prim': 'установка деталей  БОЛШЕ 15 кг и  длине сопряжения БОЛЬШЕ 1,6 метров'},
                                                                       2: {'val': 'Мелкие ДСЕ',
                                                                           'prim': 'установка мелких деталей ДО 15 кг и  длине сопряжения ДО 1,6 метров'}},
                                'Коэфф сложности значения': {
                                    1: {1: 2, 2: 3.7, 3: 2.5, 4: 2.7, 5: 2.7, 6: 2.7, 7: 2.7},
                                    2: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1},
                                    'СБОРКА ПРОДОЛЬНЫХ СТЫКОВ': {1: 1, 2: 1, 3: 3.6, 4: 1.35, 5: 1, 6: 1, 7: 1},
                                }
                                },
            "Количество сварных узлов": {"type": "int", "comment": '', "vals": {
                1: {'val': 'При наличии их в узле МЕНЕЕ 25 проц.',
                    'prim': 'Сварные узлы, входящие в собираемую конструкцию, следует считать как отдельную деталь.'},
                2: {'val': 'При наличии их в узле БОЛЕЕ 25 проц.',
                    'prim': 'Сварные узлы, входящие в собираемую конструкцию, следует считать как отдельную деталь.'}
            }},
            "Условия": {"type": "int", "comment": '', "vals": {1: {'val': 'Удобные', 'prim': ''},
                                                               2: {'val': 'Неудобные',
                                                                   'prim': 'наличие различных перегородок/передвижения на коленях/применения лестниц'}}},
            "Диаметр,мм": {"type": "float", "comment": '', "vals": {}},
            "Число сегментов": {"type": "int", "comment": '', "vals": {}},
            "Ширина фланцев,мм": {"type": "float", "comment": '', "vals": {}},
            "Длина обечайки": {"type": "float", "comment": '', "vals": {}},
            "Коэфф сборки": {"type": "int", "comment": '', "vals": {
                1: {'val': '1 часть', 'prim': 'При сборке обечаек из одной части'},
                2: {'val': '2 частей', 'prim': ' При сборке обечаек из двух частей'}
            }},
        },
        "Сварка": {"Материал":
                       {"type": "str", "comment": '', "vals": {
                           1: {'val': 'Черн', 'prim': 'Черная сталь'},
                           2: {'val': 'Нерж', 'prim': 'Нержавеющая сталь'},
                           3: {'val': '12ХМ, 15ХМ', 'prim': ''},
                           4: {'val': '12Х1МФ', 'prim': ''},
                           5: {'val': '10X17Н13М2Т', 'prim': ''},
                           6: {'val': '06ХН28МДТ', 'prim': ''},
                           7: {'val': '20X23Н18', 'prim': ''},
                           8: {'val': 'переходная', 'prim': 'низколегированная +нержавейка'},
                           9: {'val': 'титан(аргон)', 'prim': 'аргон'},
                           10: {'val': 'углеродистая сталь(аргон)', 'prim': 'аргон'},
                           11: {'val': 'легированная сталь(аргон)', 'prim': 'аргон'},
                           12: {'val': '20X23Н18(аргон)', 'prim': 'аргон'},
                       }
                        }
            , "Виды швов":
                       {"type": "str", "comment": '', "vals": {
                           1: {'val': 'С1', 'prim': 'стыковых соединений'},
                           2: {'val': 'С2', 'prim': 'стыковых соединений'},
                           3: {'val': 'С6', 'prim': 'стыковых соединений'},
                           4: {'val': 'С7', 'prim': 'стыковых соединений'},
                           5: {'val': 'С8', 'prim': 'стыковых соединений'},
                           6: {'val': 'С11', 'prim': 'стыковых соединений'},
                           7: {'val': 'С12', 'prim': 'стыковых соединений'},
                           8: {'val': 'С15', 'prim': 'стыковых соединений'},
                           9: {'val': 'С17', 'prim': 'стыковых соединений'},
                           10: {'val': 'С25', 'prim': 'стыковых соединений'},
                           11: {'val': 'У1', 'prim': 'угловых соединений'},
                           12: {'val': 'У2', 'prim': 'угловых соединений'},
                           13: {'val': 'У4', 'prim': 'угловых соединений'},
                           14: {'val': 'У5', 'prim': 'угловых соединений'},
                           15: {'val': 'У8', 'prim': 'угловых соединений'},
                           16: {'val': 'У9', 'prim': 'угловых соединений'},
                           17: {'val': 'У10', 'prim': 'угловых соединений'},
                           18: {'val': 'Т1', 'prim': 'тавровых соединений'},
                           19: {'val': 'Т3', 'prim': 'тавровых соединений'},
                           20: {'val': 'Т6', 'prim': 'тавровых соединений'},
                           21: {'val': 'Т7', 'prim': 'тавровых соединений'},
                           22: {'val': 'Т8', 'prim': 'тавровых соединений'},
                           23: {'val': 'Н1', 'prim': 'нахлёсточных соединений'},
                           24: {'val': 'Н2', 'prim': 'нахлёсточных соединений'},
                           25: {'val': 'Н4', 'prim': 'нахлёсточных соединений'}}
                        }
            , "Длина швов,мм":
                       {"type": "float", "comment": '', "vals": {}}
            , "Толщина,мм":
                       {"type": "float", "comment": '', "vals": {}}
            , "Коэффициент сложности":
                       {"type": "str", "comment": '',
                        "vals": {0: {'val': 'Стац.раб.место', 'prim': ' стационарное рабочее место в цехе'},
                                 1: {'val': 'не на столе', 'prim': 'сварка производится не на сварочном столе'},
                                 2: {'val': 'лежа', 'prim': 'лежа (на  спине, боку, груди)'},
                                 3: {'val': 'высота', 'prim': 'работа в ограниченном пространстве или на высоте'}, }}
            , "Вид сварки(20-П,21-А)":
                       {"type": "str", "comment": '', "vals": {20: {'val': 'Полуавтоамат', 'prim': 'Полуавтоамат'},
                                                               21: {'val': 'Аргон', 'prim': 'Аргон'}, }}
            , "Кол-во входящих ДСЕ":
                       {"type": "int", "comment": '', "vals": {}}
            , "Положение шва":
                       {"type": "int", "comment": '', "vals": {
                           1: {'val': 'нижнее', 'prim': 'нижнее в пространстве'},
                           2: {'val': 'вертикальное', 'prim': 'вертикальное в пространстве'},
                           3: {'val': 'горизонтальное', 'prim': 'горизонтальное в пространстве'},
                           4: {'val': 'потолочное', 'prim': 'потолочное в пространстве'},
                           5: {'val': 'наклонное нижнее', 'prim': 'наклонное нижнее'},
                           6: {'val': 'наклонное потолочное', 'prim': 'наклонное потолочное'}, }}
                   }
    }


@CQT.onerror
def sb_pod_sv(ima_operacii, arr_tmp):
    def acc_type(ima_operacii, name):
        if arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, name)] == '+':
            return 0
        if name in Data_oper_norm.DICT_OPERS_CALC[ima_operacii]:
            if Data_oper_norm.DICT_OPERS_CALC[ima_operacii][name]['type'] == 'int':
                print(f"{name} - {Data_oper_norm.DICT_OPERS_CALC[ima_operacii][name]['type']}")
                return int(F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, name)]))
            if Data_oper_norm.DICT_OPERS_CALC[ima_operacii][name]['type'] == 'float':
                print(f"{name} - {Data_oper_norm.DICT_OPERS_CALC[ima_operacii][name]['type']}")
                return F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, name)])
            if Data_oper_norm.DICT_OPERS_CALC[ima_operacii][name]['type'] == 'str':
                print(f"{name} - {Data_oper_norm.DICT_OPERS_CALC[ima_operacii][name]['type']}")
                return str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, name)])
        else:
            CQT.msgbox(f'{name} не найден в БД')
            return False

    mass = acc_type(ima_operacii, 'Масса,кг')
    kol_vo = acc_type(ima_operacii, 'Кол-во входящих ДСЕ')
    vid_konstr = acc_type(ima_operacii, 'Вид конструкции')
    material = acc_type(ima_operacii, 'Материал')
    uslovia = acc_type(ima_operacii, 'Условия')
    dl_stik = acc_type(ima_operacii, 'Длина стыков,мм')
    tolshina_met = acc_type(ima_operacii, 'Толщина металла')
    sopr_uzl = acc_type(ima_operacii, 'Сопряжения узлов')
    kol_sv_uzl = acc_type(ima_operacii, 'Количество сварных узлов')
    slogn_sobs = acc_type(ima_operacii, 'Коэфф сложности')
    vid_izd = acc_type(ima_operacii, 'Изделие')
    diametr = acc_type(ima_operacii, 'Диаметр,мм')
    kol_vo_segm = acc_type(ima_operacii, 'Число сегментов')
    shir_fl = acc_type(ima_operacii, 'Ширина фланцев,мм')
    dl_obech = acc_type(ima_operacii, 'Длина обечайки')
    koef_sborki = acc_type(ima_operacii, 'Коэфф сборки')
    dl_obech = dl_obech / 1000  # мм ->м
    dl_stik = dl_stik / 1000  # мм -> м
    diametr = diametr / 1000  # мм -> м
    shir_fl = shir_fl / 1000  # мм -> м
    # Масса,кг:int;Кол-во входящих ДСЕ:int;Вид конструкции:int;Материал(1-черн,2-нерж):int;Условия(1-удобные 2-неудобные):int;Длина стыков,мм:int;Толщина металла(мм):int;Сопряжения узлов:int;Количество сварных узлов:int;Коэфф сложности:int;Коэфф сложности значения:int;Изделие:int;Диаметр,мм:int;Число сегментов:int;Ширина фланцев,мм:int;Длинна обечайки(мм):int;Коэфф сборки:int;Длина швов(мм):int

    Kusl = 1.1 if uslovia == 2 else 1  # коэффициент, учитывающий условия выполнения работы
    Km = 2 if material == 2 else 1  # коэффициент, учитывающий вид стали
    Tpz = 0.03 if kol_vo <= 15 else 0.04 if kol_vo <= 50 else 0.05  # Подготовительно-заключительное время
    koef_met = 1 if tolshina_met <= 12 else 1.15 if tolshina_met <= 20 else 3  # Коэфициент металла
    koef_sbor = 1.3 if sopr_uzl == 2 else 1  # Коэфициент сборки
    koef_uzl = 1.15 if kol_sv_uzl == 2 else 1  # Количество сварных узлов

    if vid_konstr == '1':  # СБОРКА МЕТАЛЛОКОНСТРУКЦИЙ ПОД СВАРКУ ИЗ ЛИСТОВОГО МЕТАЛЛА
        koef_slognost = \
        Data_oper_norm.DICT_OPERS_CALC[ima_operacii]['Коэфф сложности']['Коэфф сложности значения'][slogn_sobs][vid_izd]
        Tsht = 0.0158 * mass ** 0.26 * kol_vo ** 0.71 * dl_stik ** 0.18 * koef_met * koef_sbor * koef_slognost * koef_uzl * 60

    elif vid_konstr == '2':  # сборка металлоконструкций под сварку из профильного и листового металла
        koef_slognost = \
            Data_oper_norm.DICT_OPERS_CALC[ima_operacii]['Коэфф сложности']['Коэфф сложности значения'][slogn_sobs][
                vid_izd]
        Tsht = 0.0195 * mass ** 0.26 * kol_vo ** 0.71 * dl_stik ** 0.18 * koef_met * koef_sbor * koef_slognost * koef_uzl * 60


    elif vid_konstr == '3':  # сборка металлоконструкций под сварку из профильного металла
        koef_slognost = \
            Data_oper_norm.DICT_OPERS_CALC[ima_operacii]['Коэфф сложности']['Коэфф сложности значения'][slogn_sobs][
                vid_izd]
        Tsht = 0.038 * mass ** 0.26 * kol_vo ** 0.71 * koef_sbor * koef_slognost * koef_uzl * 60

    elif vid_konstr == '4':  # сборка плоских колец (фланцев) из сегментов (секторов)
        koef_stika = 1.2 if dl_stik > 0.2 else 1
        koef_shir = 1.2 if shir_fl > 0.2 else 1
        koef_slognost = 1  # есть таблица №11 но там все 1

        Tsht = 2.212 * tolshina_met ** 0.25 * diametr ** 0.23 * kol_vo_segm ** 0.68 * koef_stika * koef_shir * koef_slognost * koef_met

    elif vid_konstr == '5':  # сборка продольных стыков цилиндрических обечаек под сварку
        koef_sbor = 1.8 if koef_sborki == 2 else 1
        koef_slognost = Data_oper_norm.DICT_OPERS_CALC[ima_operacii]['Коэфф сложности']['Коэфф сложности значения'][
            'СБОРКА ПРОДОЛЬНЫХ СТЫКОВ'][vid_izd]
        Tsht = 0.166 * tolshina_met ** 0.63 * diametr ** 0.37 * dl_obech ** 0.5 * koef_sbor * koef_slognost * koef_met

    elif vid_konstr == '6':  # сборка продольных стыков конических обечаек под сварку
        koef_sbor = 1.8 if koef_sborki == 2 else 1

        koef_slognost = Data_oper_norm.DICT_OPERS_CALC[ima_operacii]['Коэфф сложности']['Коэфф сложности значения'][
            'СБОРКА ПРОДОЛЬНЫХ СТЫКОВ'][vid_izd]
        Tsht = 0.254 * tolshina_met ** 0.60 * diametr ** 0.37 * dl_obech ** 0.5 * koef_sbor * koef_slognost * koef_met

    N_v = Tsht * Kusl * Km * (1 + Tpz / 100) * 1.3
    slogn_tpz = 0.03
    if kol_vo >= 15:
        slogn_tpz = 0.04
    if kol_vo > 50:
        slogn_tpz = 0.05
    return round(N_v), round(N_v * slogn_tpz, 3)


def sles_zach_shvov(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    tip = str(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Вид ДСЕ')])
    gabarit = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина,мм')])
    d_shvov = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина швов,мм')])
    material = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    tolsh = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])

    clean_spray = F.valm(
        arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Зачистка в труднодоступных местах(1-да 2-нет)')])
    clean_influx = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Зачистка заподлицо(1-да 2-нет)')])

    km = 1 if material == 1 else 1.85

    putf = put + F.sep() + 'table2.txt'
    kt = 1 if tolsh < 10 else 1.1 if tolsh < 16 else 1.2 if tolsh < 25 else 1.3

    putf = put + F.sep() + 'table1.txt'

    nvr = table(putf, tip, gabarit)
    K_spray = 2.1 if clean_spray == 1 else 1
    K_influx = 5.8 if clean_influx == 1 else 1

    T_thing = nvr * d_shvov / 1000 * km * kt * K_spray * K_influx
    N_v = T_thing * 1.3

    return N_v


def sbor_obsh(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    material = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    chislo_det = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во входящих ДСЕ')]))
    massa = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса,кг')])

    koef = 1 if material == 1 else 1.2

    putf = put + F.sep() + 'tabl1.txt'
    nvr = table(putf, massa, chislo_det)
    # N_v = nvr * koef * chislo_det
    return nvr


def gibka(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii)

    material = int(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Материал(1-черн,2-нерж)')])
    chislo_gibov = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число гибов')]))
    dlina_det = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длина, мм')])
    shirina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Ширина,мм')])
    chislo_partii = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Кол-во штук')]))
    massa = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Масса,кг')])

    putf = put + F.sep() + 'tabl1.txt'
    nvr = table(putf, chislo_gibov, dlina_det)
    putf = put + F.sep() + 'tabl2.txt'
    kp = table(putf, chislo_partii)
    putf = put + F.sep() + 'tabl3.txt'
    km = table(putf, massa)
    koef = 0
    if material == 1:
        N_v = nvr * chislo_partii * kp * km
    else:
        summ = (dlina_det + shirina) * 2
        N_v = (nvr + summ / 1000 * 0.64) * kp * km * chislo_partii
    return N_v


def upacovivanie(ima_operacii, arr_tmp):
    """
    'площадь поддона': {"type": "float", "comment": 'кв.метры', "vals": {}},
    'диаметр,мм': {"type": "float", "comment": 'мм', "vals": {}},
    'количество': {"type": "float", "comment": '', "vals": {}},
    "Изделие": {"type": "float", "comment": '', "vals": {
        1: {'val': 'КЛ', 'prim': ''},
        2: {'val': 'КТ', 'prim': ''},
        3: {'val': 'ШГ', 'prim': ''},
        5: {'val': 'ГГ', 'prim': ''},
    }},
    """
    idx_S = F.num_col_by_name_in_hat_c(arr_tmp, 'Площадь поддона')
    idx_D = F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр,мм')
    idx_N = F.num_col_by_name_in_hat_c(arr_tmp, 'Количество')
    idx_mat_name = F.num_col_by_name_in_hat_c(arr_tmp, 'Изделие')
    mat_name = arr_tmp[1][idx_mat_name]
    if mat_name == '3': # ШГ
        t_p = 10.03  # Время, происходящее на поддоне, мин/ кв.м
        t_d = 0.06  # Время работы с ШГ, мин/ мм упаковка
        const = 49.8  # Постоянные операции, мин
        S = float(arr_tmp[-1][idx_S])  # Площадь поддона, кв.метры
        D = float(arr_tmp[-1][idx_D])  # Диаметр  ШГ, мм
        N = float(arr_tmp[-1][idx_N])  # Количество ШГ  на поддоне
        return t_p * S + t_d * D * N + const, 5
    if mat_name == '1': # КК
        t_p = 7.53  # Время  , происходящее на поддоне, мин/ кв.м
        t_d = 0.02  # Время  работы с ШГ, мин/ мм упаковка
        const = 115.7  # Постоянные операции, мин
        S = float(arr_tmp[-1][idx_S])  # Площадь поддона, кв.метры
        D = float(arr_tmp[-1][idx_D])  # Диаметр  ШГ, мм
        return t_p * S + t_d * D + const, 5
    if mat_name == '4': # ГГ
        t_co_gg = 85.0  # Время комплектовки ГГ, мин/шт
        t_co_so = 85.0  # Время комплектовкиСОПЛА, мин/шт
        const = 96.0  # Постоянные операции, мин
        N = float(arr_tmp[-1][idx_N])  # Количество ШГ  на поддоне
        return (t_co_gg + t_co_so) * N + const, 5
    if mat_name == '2': # КТ
        t_p = 10.03  # Время, происходящее на поддоне, мин/ кв.м
        const = 49.8  # Постоянные операции, мин
        S = float(arr_tmp[-1][idx_S])  # Площадь поддона, кв.метры
        return t_p * S + const, 5


def el_erozion(ima_operacii, arr_tmp):
    tolsch = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])
    dlina = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Длинна реза,мм')])
    N_v = round(F.valm(tolsch) * F.valm(dlina / 70), 2)
    return N_v


def valcovka(ima_operacii, arr_tmp):
    put = OperationConfig.operation_table_path(ima_operacii, ima_operacii)

    tolsch = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Толщина,мм')])
    diametr = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр,мм')])

    putp = put + '.txt'
    N_v = table(putp, tolsch, diametr)
    return N_v


def valtcovka_linz(ima_operacii, arr_tmp):
    diametr_linz = int(F.round_up(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Диаметр линзы,мм')]))
    segmenti = F.valm(arr_tmp[1][F.num_col_by_name_in_hat_c(arr_tmp, 'Число сегментов')])  # добавлено
    Nvr = 25 if diametr_linz <= 1000 else 21 if diametr_linz <= 1500 else 16 if diametr_linz <= 2000 else 12
    return Nvr * segmenti

def normilize_path(path: str) -> str:
    pattern = r'\\([^\\]+ / \d+)\\'
    match = re.search(pattern, path)
    if match:
        result = match.group(1)
        op_code = result.split(' / ')
        if len(op_code) == 2:
            return path.replace(result, op_code[0])
    return path

def table(putf, vert, gor=None, rez_valm=True):
    putf = normilize_path(putf)
    if F.existence_file_c(putf) == False:
        return 0
    spis = F.open_file_c(putf, separ='|', utf8=True)
    row = False
    if type(vert) == type(2) or type(vert) == type(2.2):
        for i in range(1, len(spis)):
            if vert <= F.valm(spis[i][0]):
                row = i
                break
    else:
        for i in range(1, len(spis)):
            if vert.upper() == spis[i][0].upper():
                row = i
                break
    if row == False:
        return 0
    if gor == None:
        if rez_valm:
            return F.valm(spis[row][1])
        else:
            return spis[row][1]
    kol = False
    if type(gor) == type(2) or type(gor) == type(2.2):
        for i in range(1, len(spis[0])):
            if gor <= int(spis[0][i]):
                kol = i
                break
    else:
        for i in range(1, len(spis[0])):
            if gor.upper() == spis[0][i].upper():
                kol = i
                break
    if kol == False:
        return 0
    if rez_valm:
        return F.valm(spis[row][kol])
    else:
        return spis[row][kol]


def table_kmp(putf):
    if F.existence_file_c(putf) == False:
        return []
    spis = F.open_file_c(putf, separ='|', utf8=True)
    return spis


class Window(QWidget, Data_oper_norm):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 QTableView")
        self.setGeometry(500, 400, 500, 300)
        self.Tables()
        self.show()

    def Tables(self):
        self.tableWidget = QTableWidget()

        fill_tbl(self, self.tableWidget, 'Сборка под сварку')
        oform_operation(self, self.tableWidget, 'Сборка под сварку')
        self.vBox = QVBoxLayout()
        self.vBox.addWidget(self.tableWidget)
        self.setLayout(self.vBox)


def fill_tbl(self, tbl, name_oper):
    obj = Data_oper_norm()
    dct = obj.DICT_OPERS_CALC
    list = [[], []]
    if name_oper in dct:
        for key in dct[name_oper].keys():
            list[0].append(key)
            list[1].append('')
        CQT.fill_wtabl(list, tbl)
    return


def oform_operation(self: mywindow2, tbl: QTableWidget, oper_name: str):
    def apply_combo_values(self: mywindow2, tbl: QTableWidget):
        for row in range(tbl.rowCount()):
            for j in range(tbl.columnCount()):
                if tbl.cellWidget(row, j) == None:
                    continue
                name = tbl.horizontalHeaderItem(j).text()
                val = tbl.item(row, j).text()
                if name in Data_oper_norm.DICT_OPERS_CALC[oper_name]:
                    for key in Data_oper_norm.DICT_OPERS_CALC[oper_name][name]["vals"]:
                        if str(key) == val:
                            text = Data_oper_norm.DICT_OPERS_CALC[oper_name][name]["vals"][key]['val']
                            for i in range(tbl.cellWidget(row, j).count()):
                                if text == tbl.cellWidget(row, j).itemText(i):
                                    tbl.blockSignals(True)
                                    tbl.cellWidget(row, j).setCurrentIndex(i)
                                    hide_fields(self, tbl, oper_name, name, key)
                                    tbl.blockSignals(False)
                                    break
                            break


    def hide_fields(self: mywindow2, tbl: QTableWidget, oper_name, name_field, key):
        list_show = ''
        if 'show' in Data_oper_norm.DICT_OPERS_CALC[oper_name][name_field]['vals'][key]:
            list_show = Data_oper_norm.DICT_OPERS_CALC[oper_name][name_field]['vals'][key]['show']
        if list_show == '':
            return

        def set_cell_enable(i, j, val=True):
            if val:
                CQT.set_cell_editable(tbl, i, j, True)
                CQT.set_color_wtab_c(tbl, i, j, 255, 255, 255)
                if tbl.item(i, j).text() == '+':
                    tbl.item(i, j).setText('-')
            else:
                CQT.set_cell_editable(tbl, i, j, False)
                CQT.set_color_wtab_c(tbl, i, j, 215, 215, 215)
                tbl.item(i, j).setText('+')

        if list_show == []:
            for r in range(tbl.rowCount()):
                for j in range(tbl.columnCount()):
                    set_cell_enable(r, j)
                return
        for r in range(tbl.rowCount()):
            for j in range(tbl.columnCount()):
                name = tbl.horizontalHeaderItem(j).text()
                if name in list_show:
                    set_cell_enable(r, j)
                else:
                    set_cell_enable(r, j, False)

    def select_val(self: mywindow2, text, row, col, *args):
        val = '-'
        oper_name, name_field, tbl = args[0]
        for key in Data_oper_norm.DICT_OPERS_CALC[oper_name][name_field]['vals'].keys():
            if Data_oper_norm.DICT_OPERS_CALC[oper_name][name_field]['vals'][key]['val'] == text:
                val = key
                break
        tbl.item(row, col).setText(str(val))

        hide_fields(self, tbl, oper_name, name_field, key)
        self.ui2.lbl_prim.setText(Data_oper_norm.DICT_OPERS_CALC[oper_name][name_field]['comment'])

    if oper_name not in Data_oper_norm.DICT_OPERS_CALC:
        return
    for param in Data_oper_norm.DICT_OPERS_CALC[oper_name]:
        nk_mat = CQT.num_col_by_name_c(tbl, param)
        if nk_mat != None:
            dict_vals = dict()
            for key in Data_oper_norm.DICT_OPERS_CALC[oper_name][param]["vals"]:
                dict_vals[Data_oper_norm.DICT_OPERS_CALC[oper_name][param]["vals"][key]['val']] = \
                Data_oper_norm.DICT_OPERS_CALC[oper_name][param]["vals"][key]['prim']

            if len(dict_vals):
                if not self.pself.chbox_edit_combos:
                    for i in range(tbl.rowCount()):
                        CQT.add_combobox(self, tbl, i, nk_mat, dict_vals, True, select_val,
                                         name_flag=[oper_name, param, tbl])
            apply_combo_values(self, tbl)


def oform_pereh(self: mywindow2, tbl: QTableWidget, pereh_name: str, struct: dict):
    def apply_combo_values(self: mywindow2, tbl: QTableWidget):
        for row in range(tbl.rowCount()):
            for j in range(tbl.columnCount()):
                if tbl.cellWidget(row, j) == None:
                    continue
                name = tbl.horizontalHeaderItem(j).text()
                val = tbl.item(row, j).text()
                if name in struct:
                    for key in struct[name]["vals"]:
                        if str(key) == val:
                            text = struct[name]["vals"][key]['val']
                            for i in range(tbl.cellWidget(row, j).count()):
                                if text == tbl.cellWidget(row, j).itemText(i):
                                    tbl.blockSignals(True)
                                    tbl.cellWidget(row, j).setCurrentIndex(i)
                                    tbl.blockSignals(False)
                                    break
                            break

    def select_val(self: mywindow2, text, row, col, *args):
        val = '-'
        oper_name, name_field, tbl = args[0]
        for key in struct[name_field]['vals'].keys():
            if struct[name_field]['vals'][key]['val'] == text:
                val = key
                break
        tbl.item(row, col).setText(str(val))

        # self.ui2.lbl_prim.setText(struct[name_field]['comment'])

    for param in struct:
        nk_mat = CQT.num_col_by_name_c(tbl, param)
        if nk_mat != None:
            dict_vals = dict()
            for key in struct[param]["vals"]:
                dict_vals[struct[param]["vals"][key]['val']] = \
                struct[param]["vals"][key]['prim']

            if len(dict_vals):
                if not self.pself.chbox_edit_combos:
                    for i in range(tbl.rowCount()):
                        CQT.add_combobox(self, tbl, i, nk_mat, dict_vals, True, select_val,
                                         name_flag=[pereh_name, param, tbl])
            apply_combo_values(self, tbl)


# App = QApplication(sys.argv)
# window = Window()
# sys.exit(App.exec())
@CQT.onerror
def del_welds(self: mywindow2, *args):
    CQT.clear_tbl(self.ui2.tab_vib)

def check_line(self, dict_line):
    oper_name = self.ui2.lineEdit.text()
    put = OperationConfig.operation_table_path(oper_name)
    for key in dict_line.keys():
        val = dict_line[key]
        if val.strip() == '':
            CQT.msgbox(f'В {key} не заполнено')
            return False
        for item in Data_oper_norm.SET_BLOCK_LINE:
            if item in val.strip():
                CQT.msgbox(f'В {key} содержится недопустимы символ "{item}"')
                return False
    if oper_name == 'Сварка':
        if dict_line['Вид сварки(20-П,21-А)'] == '20':
            putf = put + F.sep() + 'table1.txt'
            if dict_line['Материал'] in ('9', '10', '11', '12'):
                CQT.msgbox(f'Не верно выбрана комбинация материал-вид сварки')
                return False
        else:
            if dict_line['Материал'] not in ('9', '10', '11', '12'):
                CQT.msgbox(f'Не верно выбрана комбинация материал-вид сварки')
                return False
            if dict_line['Материал'] == '9':
                putf = put + F.sep() + 'table10.txt'
            else:
                putf = put + F.sep() + 'table11.txt'

        tolsh = dict_line['Толщина,мм']
        vid = Data_oper_norm.DICT_KOD_VALS_SVARKA['Виды швов'][dict_line['Виды швов']]
        Nvr = table(putf, tolsh, vid)
        if Nvr <= 0.001:
            CQT.msgbox(f'Не верная комбинация {vid} толщина {tolsh}')
            return False
    return True


def check_column(self, dict_line):
    oper_name = self.ui2.lineEdit.text()
    put = OperationConfig.operation_table_path(oper_name)
    type_weld = dict_line['Вид сварки(20-П,21-А)']
    material = dict_line['Материал']
    thick = dict_line['Толщина,мм']
    type_seams = dict_line['Виды швов']
    set_color_columns = {}
    if type_weld and material:
        if dict_line['Вид сварки(20-П,21-А)'] == '20':

            putf = put + F.sep() + 'table1.txt'
            if dict_line['Материал'] in ('9', '10', '11', '12'):
                CQT.msgbox(f'Не верно выбрана комбинация материал-вид сварки')
                set_color_columns['Материал'] = 1
                set_color_columns['Вид сварки(20-П,21-А)'] = 1
                return set_color_columns
            else:
                set_color_columns['Материал'] = 0
                set_color_columns['Вид сварки(20-П,21-А)'] = 0
        else:
            if dict_line['Материал'] not in ('9', '10', '11', '12'):
                CQT.msgbox(f'Не верно выбрана комбинация материал-вид сварки')
                set_color_columns['Материал'] = 1
                set_color_columns['Вид сварки(20-П,21-А)'] = 1
                return set_color_columns
            else:
                set_color_columns['Материал'] = 0
                set_color_columns['Вид сварки(20-П,21-А)'] = 0
            if dict_line['Материал'] == '9':
                putf = put + F.sep() + 'table10.txt'
            else:
                putf = put + F.sep() + 'table11.txt'
    if thick and type_seams and material and type_weld:
        tolsh = dict_line['Толщина,мм']
        vid = Data_oper_norm.DICT_KOD_VALS_SVARKA['Виды швов'][dict_line['Виды швов']]
        Nvr = table(putf, tolsh, vid)
        if Nvr <= 0.001:
            CQT.msgbox(f'Не верная комбинация {vid} толщина {tolsh}')
            set_color_columns['Толщина,мм'] = 1
            set_color_columns['Виды швов'] = 1
        else:
            set_color_columns['Толщина,мм'] = 0
            set_color_columns['Виды швов'] = 0
    return set_color_columns


@CQT.onerror
def add_weld(self: mywindow2, *args):
    """
    Разработка -> Редактор операций(диалоговое окно)
    Добавляет строку для заполнения в таблице tab_vib
    """
    # if not CQT.msgboxgYN(f'Вы уверены что хотите создать дополнительную строку в операции {self.ui2.combo2.currentText()}?'):
    #     return
    list_line = CQT.list_from_wtabl_c(self.ui2.tab_vib, '', True, False, False, False)[0]
    last_row = self.ui2.tab_vib.rowCount()
    tbl = self.ui2.tab_vib
    tbl.blockSignals(True)

    tbl.insertRow(last_row)
    for idx, _ in enumerate(list_line):
        widget = QtWidgets.QTableWidgetItem()
        widget.setText('')
        self.ui2.tab_vib.setItem(last_row, idx, widget)
    current = self.pself.ui.tree.currentItem()
    parent = self.pself.ui.tree.currentItem().parent()
    index_of_top_lvl = self.pself.ui.tree.indexOfTopLevelItem(parent)
    if index_of_top_lvl != -1:
        oper_name = self.ui2.lineEdit.text()
        pereh_name = ''
    else:
        oper_name = parent.text(0)
        pereh_name = self.ui2.lineEdit.text()
    name = oper_name if pereh_name == '' else pereh_name
    if self.pself.xl_formulas.check_per(oper_name, pereh_name, True):
        struct = self.pself.xl_formulas.convert_old_struct(oper_name, pereh_name)
        oform_pereh(self, tbl, name, struct)
    else:
        oform_operation(self, tbl, name)
    tbl.setRowHeight(last_row, 40)
    tbl.blockSignals(False)


@CQT.onerror
def del_one_weld(self: mywindow2, *args):
    """
    Разработка -> Редактор операций(диалоговое окно)
    Удаляет строку в таблице tab_vib
    """
    tbl = self.ui2.tab_vib
    current_row = tbl.currentRow()
    if current_row == -1:
        CQT.msgbox('Выделите строку для удаления')
        return
    if CQT.msgboxgYN('Вы действительно хотите удалить шов?'):
        tbl.removeRow(tbl.currentRow())
    tbl.clearFocus()

def validate_welds(self: mywindow2, row: int) -> None:
    tbl = self.ui2.tab_vib
    dict_line = CQT.list_from_wtabl_c(
        tbl, '', True, False, True, False
    )[row]
    keys = list(dict_line.keys())
    self.ui2.tab_vib.blockSignals(True)
    col_colors = check_column(self, dict_line)
    for column, is_err in col_colors.items():
        if is_err:
            r, g, b = 255, 36, 0
        else:
            r, g, b = 255, 255, 255
        idx_column = keys.index(column)
        item = tbl.cellWidget(row, idx_column)
        if isinstance(item, QtWidgets.QComboBox):
            pal = item.palette()
            pal.setColor(QtGui.QPalette.Button, QtGui.QColor(r, g, b))
            item.setPalette(pal)
        else:
            CQT.set_color_wtab_c(tbl, row, idx_column, r, g, b)
    self.ui2.tab_vib.blockSignals(False)


def table_sum_cell_changed(self: mywindow2, row, col):
    if self.ui2.combo2.currentText() == 'Сварка':
        validate_welds(self, row)
     
