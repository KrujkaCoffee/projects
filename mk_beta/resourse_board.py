
from __future__ import annotations

import copy

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QStyle
import subprocess
from form_res import Ui_WindowRes
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Functions as F
from copy import deepcopy
import project_cust_38.operacii as operacii
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_odata_erp as CODAT
import project_cust_38.Cust_config as USRCNF
from typing import TYPE_CHECKING
import project_cust_38.Cust_resource_creator as CRES
from project_cust_38.Cust_mes import TkpSchema
from project_cust_38.Cust_emoji import EmojiMain as CEmoji
if TYPE_CHECKING:
    from MKart import mywindow


class Resourse_mk():
    def __init__(self, res: list, db_resxml: str, db_kplan: str, bd_naryad: str, db_users: str,
                 tkp_current_schema, parent_self, name_res_for_ERP: str = '', nom_mk=None, num_kpl=None,
                 primech: str | None = None):

        self.parent_self = parent_self
        self.db_kplan = db_kplan
        self.bd_naryad = bd_naryad
        self.db_resxml = db_resxml
        self.db_users = db_users

        self.tkp_current_schema: TkpSchema = tkp_current_schema
        self.name_res_for_ERP = name_res_for_ERP
        self.poz = None
        self.вид_по_напр = None
        self.res = res
        self.res_kotel = None
        self.num_kpl = None
        self.s_num_tkp = None
        self.primech = primech
        self.izd = None
        if nom_mk:
            # self.res = load_res(nummk_or_reslist, db_resxml=db_resxml)
            num_kpl = CSQ.custom_request_c(self.bd_naryad, f'''SELECT НомКплан FROM mk
                WHERE Пномер == {int(nom_mk)}
                            ''', one_column=True, one=True, hat_c=False)
            if num_kpl == None or nom_mk == False:
                CQT.msgbox(f'Ошибка получения НомКплан по МК {nom_mk}')
                raise ValueError(f"Ошибка получения НомКплан по МК {nom_mk}")
            num_kpl = num_kpl #12.11.25
            self.num_kpl = num_kpl
            self.poz = CMS.Pozition(num_kpl, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self.parent_self)
            self.poz.load_kpl_table('пл_топ')
            self.poz.load_kpl_table('пл_оуп')
            self.izd = self.poz.dict_tables['пл_оуп']['Номенклатура_ЕРП']
            self.is_tkp = False
            self.вид_по_напр = self.poz.dict_tables['пл_топ']['Вид']
        else:
            if self.tkp_current_schema.is_tkp and not self.tkp_current_schema.is_parametric:  # 09.04.25
                # if 'type_tkp' in tkp_current_schema:
                #     if tkp_current_schema['type_tkp'] in (3, 4):
                self.is_tkp = True
                self.s_num_tkp = tkp_current_schema['s_nom']
            if 'вид_по_напр' in tkp_current_schema:
                self.вид_по_напр = tkp_current_schema['вид_по_напр']
            self.num_kpl = num_kpl

        self.nn = self.res[0]['Номенклатурный_номер']
        self.naim = self.res[0]['Наименование']
        self.list_res_for_erp = None
        self.obj_res_for_erp = None

    @CQT.onerror
    def __make_erp_etaps_message_tbl(self, edit_etap_data_for_dialog: list[dict], res: list[dict],
                                     dict_etaps: list | dict):  # 11.04.25
        """
        Принимает: 1.edit_etap_data_for_dialog=[
            {'Этап': ..., 'ПномерДсе': Индекс ДСЕ в структуре ресурсной, 'ПномерОперации': Индекс операции в структуре ресурсной},
        ]
        2. объект ресурсной list[dict]
        3. Словарь/список этапов ERP
        Действие: Создает таблицу для редактирования конфликтных этапов
        Возвращает: объект ресурсной с правками или None в случае отмены
        """

        def oform(tbl):
            nk_etap = CQT.num_col_by_name_c(tbl, 'Этап')
            nk_dse = CQT.num_col_by_name_c(tbl, 'ПномерДсе')
            nk_oper = CQT.num_col_by_name_c(tbl, 'ПномерОперации')
            tbl.hideColumn(nk_dse) or tbl.hideColumn(nk_oper)
            tbl.verticalHeader().setHidden(True)
            for i in range(tbl.rowCount()): # 17.12.25 по задаче 100064340
                stages = list(sorted(dict_etaps))
                tbl.item(i, nk_etap).setText(stages[0])
                text_setter = lambda tbl, text, row, col: tbl.item(row, col).setText(text)
                CQT.add_combobox(self=tbl, table=tbl, i=i, j=nk_etap, list=list(dict_etaps), first_void=False,
                                 conn_func=text_setter)

        resp = CQT.msgboxg_get_table(
            self.parent_self.myparent,
            'Не найден подходящий этап для 1С',
            edit_etap_data_for_dialog,
            'Продолжить выгрузку', 'Прервать',
            func_oform_tbl=oform,
            func_validate=lambda data: data,
            show_filtr=False, use_first_row_as_header=True, print_hat=True,
            WindowTitle="Выбор этапов для операций"
        )
        if not resp: return
        CMS.dict_rc(self, USRCNF.Config.project.db_users) # 27.02.2026
        department_by_stage_name = {item['etaps_name']: item['Наим_ЕРП'] for _, item in self.DICT_RC.items()}
        for item in resp:
            dse_pk = int(item['ПномерДсе'])
            oper_pk = int(item['ПномерОперации'])
            stage = item['Этап']
            department = department_by_stage_name.get(stage)
            res[dse_pk]['Операции'][oper_pk]['Этап'] = stage
            res[dse_pk]['Операции'][oper_pk]['Опер_наименование_подразделения'] = department
        return res

    @CQT.onerror
    def add_erp_etaps_in_res(self, res: list[dict], DICT_OP: dict, DICT_RC: dict, dict_etaps: dict):  # 11.04.25
        """
        Принимает:
        1. res - Объект ресурсной
        2. Словарь операций (где ключ=код операции)
        3. Словарь рабочих центров (где ключ код рц)
        3. Словарь/список этапов ERP
        Действие: Обновляет/создает ключ Этап для каждой операции
            Если этап не найден вызывает таблицу с конфликтными строками для корректировки
        Возвращает: объект ресурсной с правками или None в случае отмены в таблице корректировки
        """
        cp_rez = copy.deepcopy(res)
        edit_etap_data_for_dialog = []
        for dse_pk, dse in enumerate(res):
            for oper_pk, oper in enumerate(dse['Операции']):
                rc_cod = oper['Опер_РЦ_код']
                oper_kod = oper['Опер_код']
                etap = DICT_RC[rc_cod]['etaps_name']
                if etap not in dict_etaps:
                    etap = 'Сборка+сварка'
                    tmp = {
                        'ПномерДсе': dse_pk,
                        'ПномерОперации': oper_pk,
                        'Наименование': dse['Наименование'],
                        'Номенклатурный_номер': dse['Номенклатурный_номер'],
                        'Этап': etap,
                        'ДСЕ': dse['Номенклатурный_номер'],
                        "Операция": DICT_OP[oper_kod]['name'],
                        'Материалы': []
                    }
                    if oper['Материалы']:
                        for mat in oper['Материалы']:
                            tmp['Материалы'].append({
                                "Мат_код": mat['Мат_код'],
                                "Мат_наименование": mat['Мат_наименование'],
                            })
                    edit_etap_data_for_dialog.append(tmp)  # 15.04.25
                cp_rez[dse_pk]['Операции'][oper_pk]['Этап'] = etap
        if edit_etap_data_for_dialog:
            return self.__make_erp_etaps_message_tbl(edit_etap_data_for_dialog, cp_rez,
                                                     dict_etaps)  # 02.06.2025 (Проект: "разработка, внедрение MES" 8386266)
        return cp_rez

    @CQT.onerror
    def generate_list_res_for_erp(self, DICT_PROF_CODE, DICT_NOMEN, DICT_OP, DICT_RC):
        list_err = []
        test = []
        mainSelf = self.parent_self.myparent
        DICT_VID_RAB_BY_REF = F.list_of_lists_to_dict_of_dicts(
            F.dict_of_dicts_to_list_of_lists(mainSelf.DICT_VID_RABOT), 'ref_Key_erp')
        rez = self.res_kotel
        rez_new = [copy.deepcopy(rez[0])]
        count_po_mk = 1
        rez_new[0]['Операции'] = []
        rez_new[0]['Параметрика'] = {}
        rez_new[0]['Документы'] = []
        rez_new[0]['ПКИ'] = '0'
        dict_rc_vid = dict()

        dict_etaps = {name: {'Опер_наименование_подразделения': None,
                             "Материалы": dict(),
                             "Трудозатраты": dict(),

                             } for name, val in mainSelf.Data_plan.DICT_ETAPS_NAME.items() if val['ДляЕРП']}

        rez = self.add_erp_etaps_in_res(rez, DICT_OP, DICT_RC, dict_etaps)
        if rez is None:
            return None, None
        for dse in rez:
            if dse['ПКИ'] == '1':
                if 'Способы_получения_материала' not in dse:
                    dse['Способы_получения_материала'] = 'Обеспечивать'
                dse['Количество_ед'] = dse['кол_во_инф']['кол_во_1_изд_по_структуре']
                # rez_new.append(dse)

            if 'Способы_получения_материала' not in dse:
                dse['Способы_получения_материала'] = 'Произвести по основной спецификации'
            for oper in dse['Операции']:
                if oper['Опер_вспомогательная'] == 1:
                    continue
                rc_cod = oper['Опер_РЦ_код']
                rc_name = oper['Опер_РЦ_наименование']
                prof_cod = oper['Опер_профессия_код']
                prof_name = oper['Опер_профессия_наименование']
                podr_name = oper['Опер_наименование_подразделения']
                oper_kod = oper['Опер_код']
                if prof_cod != '' and prof_cod not in DICT_PROF_CODE:
                    CQT.msgbox(
                        f"профессия {oper['Опер_профессия_код']} из {oper['Опер_наименование']} {dse['Номенклатурный_номер']} не найдена в справочнике")
                    return None, None
                if oper_kod != '' and oper_kod not in DICT_OP:
                    CQT.msgbox(
                        f"операция {oper['Опер_код']} {oper['Опер_наименование']} из {dse['Номенклатурный_номер']} не найдена в справочнике")
                    return None, None
                etap = oper['Этап']  # 11.04.25
                # etap = DICT_RC[rc_cod]['etaps_name'] #11.04.25
                # if etap not in dict_etaps:
                #     if oper['Материалы']:
                #         for mat in oper['Материалы']:
                #             list_err.append([f"Мат. {mat['Мат_наименование']} попал в Сборка+сварка, т.к. этап {etap} для НЕ предусмотрен в ЕРП"])
                #     etap = 'Сборка+сварка'

                if dict_etaps[etap]['Опер_наименование_подразделения'] == None:
                    dict_etaps[etap]['Опер_наименование_подразделения'] = podr_name
                # if dict_etaps[etap]['Опер_наименование_подразделения'] != podr_name:
                #    CQT.msgbox(f"""При компоновке по котловому методу возникла ошибка, для этапа {etap}
                #     `{dict_etaps[etap]['Опер_наименование_подразделения']}` указано несогласующиеся подразделения
                #     `{podr_name}` из {oper['Опер_наименование']} {dse['Номенклатурный_номер']}""")
                #    return None, None

                vid_rab = mainSelf.DICT_PROF_CODE[prof_cod]['вид_работ']
                guid_vid_rab = mainSelf.DICT_VID_RABOT[vid_rab]['ref_Key_erp']
                if guid_vid_rab != None:
                    if guid_vid_rab not in dict_etaps[etap]['Трудозатраты']:
                        dict_etaps[etap]['Трудозатраты'][guid_vid_rab] = 0
                    dict_etaps[etap]['Трудозатраты'][guid_vid_rab] += (
                                oper['Опер_Тпз'] + oper['Опер_Тшт'] / count_po_mk)
                    test.append([dse['Номенклатурный_номер'], oper['Опер_РЦ_наименование'], etap,
                                 (oper['Опер_Тпз'] + oper['Опер_Тшт'] / count_po_mk),
                                 dict_etaps[etap]['Трудозатраты'][guid_vid_rab]])
                for mat in oper['Материалы']:
                    Мат_код = mat['Мат_код']
                    if Мат_код not in DICT_NOMEN:
                        CQT.msgbox(f'Материал {mat["Мат_код"]} не найден в номенклатуре')
                        return None, None
                    if DICT_NOMEN[Мат_код]['На_удаление']:
                        CQT.msgbox(
                            f'Материал \n\nКод: `{Мат_код}` \nНаименование: `{DICT_NOMEN[Мат_код]["Наименование"]}`'
                            f' \n\nотмечен в 1С `На_удаление`\n\nИспользование не возможно.')
                        return None, None

                    if 'Способы_получения_материала' not in mat:
                        mat['Способы_получения_материала'] = 'Обеспечивать'

                    if 'Материалы_Статья_калькуляции' not in mat:
                        Материалы_Статья_калькуляции = 'Сырье'
                        if DICT_NOMEN[Мат_код][
                            'Вид'] == 'Упаковочные материалы для складского хоз-ва 10.09':
                            Материалы_Статья_калькуляции = 'Упаковка'
                        mat['Материалы_Статья_калькуляции'] = Материалы_Статья_калькуляции

                    Мат_наименование = mat['Мат_наименование']
                    Мат_ед_изм = mat['Мат_ед_изм']
                    Мат_норма = mat['Мат_норма']
                    Мат_норма_ед = mat['Мат_норма_ед']
                    Мат_параметрика = mat['Мат_параметрика']
                    Материалы_Статья_калькуляции = mat['Материалы_Статья_калькуляции']
                    Способы_получения_материала = mat['Способы_получения_материала']

                    if Мат_код not in dict_etaps[etap]["Материалы"]:
                        dict_etaps[etap]["Материалы"][Мат_код] = {
                            'Мат_код': Мат_код,
                            'Мат_наименование': Мат_наименование,
                            'Мат_ед_изм': Мат_ед_изм,
                            'Мат_норма': 0,
                            'Мат_параметрика': Мат_параметрика,
                            'Материалы_Статья_калькуляции': Материалы_Статья_калькуляции,
                            'Способы_получения_материала': Способы_получения_материала,
                        }
                    if Мат_норма == 0:
                        if CQT.msgboxgYN(f"""При компоновке материалов обнаружено для {Мат_наименование} Мат_норма == 0 
                      {oper['Опер_наименование']} {dse['Номенклатурный_номер']}""", 'Прервать            ',
                                         'Продолжить'):
                            return None, None

                    dict_etaps[etap]["Материалы"][Мат_код]['Мат_норма'] += Мат_норма / count_po_mk
                for osn in oper['Оснастка']:
                    if not osn['load_to_erp']:
                        continue
                    Мат_код = osn['Код']
                    Мат_наименование = osn['Наименование']
                    Мат_ед_изм = osn['mesure']
                    Мат_норма = 1

                    if Мат_код not in dict_etaps[etap]["Материалы"]:
                        dict_etaps[etap]["Материалы"][Мат_код] = {
                            'Мат_код': Мат_код,
                            'Мат_наименование': Мат_наименование,
                            'Мат_ед_изм': Мат_ед_изм,
                            'Мат_норма': 0,
                            'Мат_параметрика': {},
                            'Материалы_Статья_калькуляции':  'Материалы основные',
                            'Способы_получения_материала': 'Обеспечивать',
                        }

                    dict_etaps[etap]["Материалы"][Мат_код]['Мат_норма'] += Мат_норма / count_po_mk

        list_etaps = []
        for k, v in dict_etaps.items():
            if len(v['Материалы']) or len(v['Трудозатраты']):
                new_mats = dict()
                mats = v['Материалы']
                for key, mat in mats.items():
                    if mat['Мат_норма']:
                        new_mats[key] = mat
                    else:
                        CQT.msgbox(
                            f'В `{v["Опер_наименование_подразделения"]}` пропущен материал \n`{mat["Мат_наименование"]}`\nт.к. кол-во = 0')
                new_trs = dict()
                trs = v['Трудозатраты']
                for key, tr in trs.items():
                    if tr:
                        new_trs[key] = tr
                    else:
                        CQT.msgbox(
                            f'В `{v["Опер_наименование_подразделения"]}` пропущен вид работ \n`{DICT_VID_RAB_BY_REF[key]["Список"]}`\nт.к. кол-во = 0')
                new_v = {'Опер_наименование_подразделения': v['Опер_наименование_подразделения'],
                         'Материалы': new_mats,
                         'Трудозатраты': new_trs}
                list_etaps.append({'Этап': k, "Данные": new_v})

        self.list_res_for_erp = list_etaps

        return list_etaps, list_err
        CQT.msgboxg_get_table_ok_inf(self.parent_self, 'test', [[_[0], _[1], _[2], str(_[3]), _[4]] for _ in test],
                                     use_first_row_as_header=False)

    @CQT.onerror
    def generate_ResourceSpecification(self, hat: CRES.ResourceHeader, DICT_PROF_CODE, DICT_NOMEN, DICT_OP,
                                       DICT_RC) -> CRES.ResourceSpecification:

        # Итог
        spec = CRES.ResourceSpecification(hat)

        test = []
        mainSelf = self.parent_self.myparent
        DICT_VID_RAB_BY_REF = F.list_of_lists_to_dict_of_dicts(
            F.dict_of_dicts_to_list_of_lists(mainSelf.DICT_VID_RABOT), 'ref_Key_erp')
        rez = self.res_kotel

        count_po_mk = 1

        dict_rc_vid = dict()

        dict_etaps = {name: {'Опер_наименование_подразделения': None,
                             "Материалы": dict(),
                             "Трудозатраты": dict(),
                             } for name, val in mainSelf.Data_plan.DICT_ETAPS_NAME.items() if val['ДляЕРП']}

        rez = self.add_erp_etaps_in_res(rez, DICT_OP, DICT_RC, dict_etaps)
        if rez is None:
            return None
        for dse in rez:
            if dse['ПКИ'] == '1':
                if 'Способы_получения_материала' not in dse:
                    dse['Способы_получения_материала'] = 'Обеспечивать'
                dse['Количество_ед'] = dse['кол_во_инф']['кол_во_1_изд_по_структуре']

            if 'Способы_получения_материала' not in dse:
                dse['Способы_получения_материала'] = 'Произвести по основной спецификации'
            for oper in dse['Операции']:
                if oper['Опер_вспомогательная'] == 1:
                    continue
                rc_cod = oper['Опер_РЦ_код']
                rc_name = oper['Опер_РЦ_наименование']
                prof_cod = oper['Опер_профессия_код']
                prof_name = oper['Опер_профессия_наименование']
                podr_name = oper['Опер_наименование_подразделения']
                oper_kod = oper['Опер_код']
                if prof_cod != '' and prof_cod not in DICT_PROF_CODE:
                    CQT.msgbox(
                        f"профессия {oper['Опер_профессия_код']} из {oper['Опер_наименование']} {dse['Номенклатурный_номер']} не найдена в справочнике")
                    return None, None
                if oper_kod != '' and oper_kod not in DICT_OP:
                    CQT.msgbox(
                        f"операция {oper['Опер_код']} {oper['Опер_наименование']} из {dse['Номенклатурный_номер']} не найдена в справочнике")
                    return None
                etap = oper['Этап']  # 11.04.25

                if dict_etaps[etap]['Опер_наименование_подразделения'] == None:
                    dict_etaps[etap]['Опер_наименование_подразделения'] = podr_name
                if dict_etaps[etap]['Опер_наименование_подразделения'] == None:
                    dict_etaps[etap]['Опер_наименование_подразделения'] = DICT_RC[rc_cod]['Наим_ЕРП']
                if dict_etaps[etap]['Опер_наименование_подразделения'] == None:
                    CQT.msgbox(f'В БД МЕС для РЦ {rc_cod} не указан Наим_ЕРП')
                    return

                vid_rab = mainSelf.DICT_PROF_CODE[prof_cod]['вид_работ']
                guid_vid_rab = mainSelf.DICT_VID_RABOT[vid_rab]['ref_Key_erp']
                if guid_vid_rab != None:
                    if guid_vid_rab not in dict_etaps[etap]['Трудозатраты']:
                        dict_etaps[etap]['Трудозатраты'][guid_vid_rab] = 0
                    dict_etaps[etap]['Трудозатраты'][guid_vid_rab] += (
                            oper['Опер_Тпз'] + oper['Опер_Тшт'] / count_po_mk)
                    test.append([dse['Номенклатурный_номер'], oper['Опер_РЦ_наименование'], etap,
                                 (oper['Опер_Тпз'] + oper['Опер_Тшт'] / count_po_mk),
                                 dict_etaps[etap]['Трудозатраты'][guid_vid_rab]])
                for mat in oper['Материалы']:
                    Мат_код = mat['Мат_код']
                    if Мат_код not in DICT_NOMEN:
                        CQT.msgbox(f'Материал {mat["Мат_код"]} не найден в номенклатуре')
                        return None
                    if DICT_NOMEN[Мат_код]['На_удаление']:
                        CQT.msgbox(
                            f'Материал \n\nКод: `{Мат_код}` \nНаименование: `{DICT_NOMEN[Мат_код]["Наименование"]}`'
                            f' \n\nотмечен в 1С `На_удаление`\n\nИспользование не возможно.')
                        return None

                    if 'Способы_получения_материала' not in mat:
                        mat['Способы_получения_материала'] = 'Обеспечивать'

                    if 'Материалы_Статья_калькуляции' not in mat:
                        Материалы_Статья_калькуляции = 'Сырье'
                        if DICT_NOMEN[Мат_код][
                            'Вид'] == 'Упаковочные материалы для складского хоз-ва 10.09':
                            Материалы_Статья_калькуляции = 'Упаковка'
                        mat['Материалы_Статья_калькуляции'] = Материалы_Статья_калькуляции

                    Мат_наименование = mat['Мат_наименование']
                    Мат_ед_изм = mat['Мат_ед_изм']
                    Мат_норма = mat['Мат_норма']
                    Мат_норма_ед = mat['Мат_норма_ед']
                    Мат_параметрика = mat['Мат_параметрика']
                    Материалы_Статья_калькуляции = mat['Материалы_Статья_калькуляции']
                    Способы_получения_материала = mat['Способы_получения_материала']

                    if Мат_код not in dict_etaps[etap]["Материалы"]:
                        dict_etaps[etap]["Материалы"][Мат_код] = {
                            'Мат_код': Мат_код,
                            'Мат_наименование': Мат_наименование,
                            'Мат_ед_изм': Мат_ед_изм,
                            'Мат_норма': 0,
                            'Мат_параметрика': Мат_параметрика,
                            'Материалы_Статья_калькуляции': Материалы_Статья_калькуляции,
                            'Способы_получения_материала': Способы_получения_материала,
                        }
                    if Мат_норма == 0:
                        if CQT.msgboxgYN(f"""При компоновке материалов обнаружено для {Мат_наименование} Мат_норма == 0 
                      {oper['Опер_наименование']} {dse['Номенклатурный_номер']}""", 'Прервать            ',
                                         'Продолжить'):
                            return None
                    dict_etaps[etap]["Материалы"][Мат_код]['Мат_норма'] += Мат_норма / count_po_mk

                for osn in oper['Оснастка']:
                    if not osn['load_to_erp']:
                        continue
                    Мат_код = osn['Код']
                    Мат_наименование = osn['Наименование']
                    Мат_ед_изм = osn['mesure']
                    Мат_норма = 1

                    if Мат_код not in dict_etaps[etap]["Материалы"]:
                        dict_etaps[etap]["Материалы"][Мат_код] = {
                            'Мат_код': Мат_код,
                            'Мат_наименование': Мат_наименование,
                            'Мат_ед_изм': Мат_ед_изм,
                            'Мат_норма': 0,
                            'Мат_параметрика': {},
                            'Материалы_Статья_калькуляции':  'Материалы основные',
                            'Способы_получения_материала': 'Обеспечивать',
                        }
                    dict_etaps[etap]["Материалы"][Мат_код]['Мат_норма'] += Мат_норма / count_po_mk
        list_etaps = []
        for k, v in dict_etaps.items():
            if len(v['Материалы']) or len(v['Трудозатраты']):
                # Этап
                Подразделение = CRES.SubdivisionsData.find_by_name(v['Опер_наименование_подразделения'])
                stage_data = CRES.StageData(
                    Подразделение=Подразделение
                )
                for mat in v['Материалы'].values():
                    if mat['Мат_норма']:
                        stage_data.add_material(CRES.Material(
                            mat['Мат_код'],
                            mat['Мат_норма'],
                            CRES.ArticulationArticlesData.find_by_name(mat['Материалы_Статья_калькуляции']),
                            CRES.MethodOfObtainingMaterialspecificationsData.find_by_name(
                                mat['Способы_получения_материала'])
                        ))
                    else:
                        CQT.msgbox(
                            f'В `{v["Опер_наименование_подразделения"]}` пропущен материал \n`{mat["Мат_наименование"]}`\nт.к. кол-во = 0')

                trs = v['Трудозатраты']
                for key, tr in trs.items():
                    if tr:
                        stage_data.add_labor(CRES.LaborCost(
                            CRES.TypeOfWorkData.find_by_ref(key),
                            tr)
                        )

                    else:
                        CQT.msgbox(
                            f'В `{v["Опер_наименование_подразделения"]}` пропущен вид работ \n`{DICT_VID_RAB_BY_REF[key]["Список"]}`\nт.к. кол-во = 0')

                spec.add_stage(CRES.Stage(k, stage_data))

        self.obj_res_for_erp = spec
        return spec
        CQT.msgboxg_get_table_ok_inf(self.parent_self, 'test', [[_[0], _[1], _[2], str(_[3]), _[4]] for _ in test],
                                     use_first_row_as_header=False)

    @staticmethod
    def __clear_zero_time_opers(res):
        list_msg = []
        for i, dse in enumerate(res):
            tmp_opers = []
            for j, oper in enumerate(dse['Операции']):
                if oper['Опер_Тшт_ед'] == 0 and len(oper['Материалы']) == 0:
                    list_msg.append({'Операция': oper['Опер_наименование'],
                                     'ДСЕ': f"{dse['Наименование']} {dse['Номенклатурный_номер']} ",
                                     'val': f"не учтена т.к. норма времени = 0"
                                     })
                    continue
                tmp_opers.append(oper)
            if len(tmp_opers) != dse['Операции']:
                res[i]['Операции'] = tmp_opers
        return res, list_msg

    @staticmethod
    def __add_code_erp(DICT_DSE, res):
        # dict_dse = CMS.load_dict_dse(self.db_dse)
        for i, dse in enumerate(res):
            if 'Код_ERP' not in dse and 'Код ERP' not in dse:
                kod_erp = ''
                if dse['Номенклатурный_номер'] in DICT_DSE:
                    kod_erp = DICT_DSE[dse['Номенклатурный_номер']]['Код_ЕРП']
                res[i]['Код_ERP'] = kod_erp
                res[i]['Код ERP'] = kod_erp
        return res

    @staticmethod
    def apply_kotlovoy_method(DICT_PROF_CODE, DICT_NOMEN, rez, self=None):
        rez_new = [copy.deepcopy(rez[0])]
        count_po_mk = rez_new[0]['Количество']
        rez_new[0]['Операции'] = []
        rez_new[0]['Параметрика'] = {}
        rez_new[0]['Документы'] = []
        rez_new[0]['ПКИ'] = '0'
        dict_rc_vid = dict()
        dev_analisis = []
        for dse in rez:
            if dse['ПКИ'] == '1':
                if 'Способы_получения_материала' not in dse:
                    dse['Способы_получения_материала'] = 'Обеспечивать'
                if not len(dse['Операции']):
                    CQT.msgbox(f'Для ДСЕ {dse["Номенклатурный_номер"]} {dse["Наименование"]} не найдены операции\n'
                               f'Учтена в ресурсной не будет.')
                    continue
                fl_naid = False
                for oper in dse['Операции']:
                    for mat in oper['Материалы']:
                        if dse['Код_ERP'] == mat['Мат_код']:
                            dse['Операции'][0]['Опер_вспомогательная'] = 0
                            mat['Способы_получения_материала'] = dse['Способы_получения_материала']
                            fl_naid = True
                        if fl_naid:
                            break
                    if fl_naid:
                        break

                SET_SHT_EDIZM = {'Штука',
                                 'Шт',
                                 'штУДАЛИТЬ',
                                 'шт.штУДАЛИТЬ',
                                 'штука',
                                 'штштУДАЛИТЬ',
                                 'шт',
                                 }
                ЕдиницаИзмерения = ""
                if dse['Код_ERP'] in self.myparent.DICT_NOMEN:
                    dict_Материалы = self.myparent.DICT_NOMEN[dse['Код_ERP']]
                    ЕдиницаИзмерения = dict_Материалы['ЕдиницаИзмерения']
                koef = dse['Количество'] / dse['Количество_ед']
                if ЕдиницаИзмерения in SET_SHT_EDIZM:
                    mat_val_ed = dse['Количество']
                else:
                    mat_val_ed = 0
                    if '/' in dse['Мат_кд']:
                        mat_val_ed = F.valm(dse['Мат_кд'].split('/')[0])

                if not fl_naid and mat_val_ed:
                    dse['Операции'][0]['Опер_вспомогательная'] = 0
                    dse['Операции'][0]['Материалы'] = [{
                        'Мат_код': dse['Код_ERP'],
                        'Мат_наименование': dse['Наименование'],
                        'Мат_ед_изм': '',
                        'Мат_норма': mat_val_ed,
                        'Мат_норма_ед': mat_val_ed / koef,
                        'Мат_параметрика': '',

                        'Способы_получения_материала': dse['Способы_получения_материала'],
                    }]

                # rez_new.append(dse)

            if 'Способы_получения_материала' not in dse:
                dse['Способы_получения_материала'] = 'Произвести по основной спецификации'

            for oper in dse['Операции']:
                if oper['Опер_вспомогательная'] == 1:
                    continue
                rc_cod = oper['Опер_РЦ_код']
                if 'Опер_РЦ_наименовние' in oper and 'Опер_РЦ_наименование' not in oper:
                    oper['Опер_РЦ_наименование'] = oper['Опер_РЦ_наименовние']
                    oper['Опер_наименование'] = oper['Опер_наименовние']
                rc_name = oper['Опер_РЦ_наименование']
                prof_cod = oper['Опер_профессия_код']
                prof_name = oper['Опер_профессия_наименование']
                podr_name = oper['Опер_наименование_подразделения']
                if prof_cod not in DICT_PROF_CODE:
                    CQT.msgbox(
                        f"профессия {oper['Опер_профессия_код']} из {oper['Опер_наименование']} {dse['Номенклатурный_номер']} не найдена в справочнике")
                    return

                prof_s_rc = prof_cod + "$" + rc_cod
                if prof_s_rc not in dict_rc_vid:
                    pnum = len(rez_new[0]['Операции'])
                    dict_rc_vid[prof_s_rc] = pnum
                    rez_new[0]['Операции'].append(
                        {
                            'Опер_РЦ_наименование': rc_name,
                            'Опер_РЦ_код': rc_cod,
                            'Опер_профессия_наименование': prof_name,
                            'Опер_профессия_код': prof_cod,
                            'Опер_наименование_подразделения': podr_name,
                            'Опер_вспомогательная': 0,
                            'Опер_наименование': str(pnum),
                            'Опер_код': oper['Опер_код'],
                            'Этап': oper['Этап'],
                            'Опер_Тпз': 0,
                            'Опер_Тшт_ед': 0,
                            'Опер_Тшт': 0,
                            'Материалы': [],
                            'Оснастка': [],
                        }
                    )

                dev_analisis.append({
                    'Этап': oper['Этап'],
                    'Номенклатурный_номер': dse['Номенклатурный_номер'],
                    'Опер_номер': oper['Опер_номер'],
                    'Опер_наименование': oper['Опер_наименование'],
                    'Опер_профессия_код': oper['Опер_профессия_код'],
                    'count_po_mk': count_po_mk,
                    'Опер_Тшт': oper['Опер_Тшт'],
                    'Опер_Тпз': oper['Опер_Тпз']
                })
                rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Опер_Тпз'] += oper['Опер_Тпз']
                rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Опер_Тшт_ед'] += oper['Опер_Тшт_ед'] / count_po_mk
                rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Опер_Тшт'] += oper['Опер_Тшт'] / count_po_mk
                for mat in oper['Материалы']:
                    mat_kod = mat['Мат_код']
                    if mat_kod not in DICT_NOMEN:
                        CQT.msgbox(
                            f"Номенклатура `{mat['Мат_наименование']}` (код:`{mat_kod}`, ПКИ:`{dse['ПКИ']}`) из операции `{oper['Опер_номер']}` `{oper['Опер_наименование']}` "
                            f"ДСЕ:`{dse['Номенклатурный_номер']}` не найдена в справочнике номенклатуры МЕС")
                        return

                    mat_nr = mat['Мат_норма']
                    mat_nr_ed = mat['Мат_норма_ед']
                    fl_kod = False
                    for i, item in enumerate(rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Материалы']):
                        if item['Мат_код'] == mat_kod:
                            fl_kod = True
                            rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Материалы'][i][
                                'Мат_норма_ед'] += mat_nr_ed / count_po_mk
                            rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Материалы'][i][
                                'Мат_норма'] += mat_nr / count_po_mk
                            break

                    if fl_kod == False:
                        mat['Мат_норма_ед'] = mat['Мат_норма_ед'] / count_po_mk
                        mat['Мат_норма'] = mat['Мат_норма'] / count_po_mk

                        if 'Способы_получения_материала' not in mat:
                            mat['Способы_получения_материала'] = 'Обеспечивать'

                        if 'Материалы_Статья_калькуляции' not in mat:
                            Материалы_Статья_калькуляции = 'Сырье'
                            if DICT_NOMEN[mat_kod]['Вид'] == 'Упаковочные материалы для складского хоз-ва 10.09':
                                Материалы_Статья_калькуляции = 'Упаковка'
                            mat['Материалы_Статья_калькуляции'] = Материалы_Статья_калькуляции

                        rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Материалы'].append(mat)

                list_codes_erp = [_ for _ in oper['Опер_оснастка'] if _.startswith('00-')]
                list_codes = [f'"{_}"' for _ in list_codes_erp]
                if list_codes:
                    text = f"""
                                        ВЫБРАТЬ
                                            Номенклатура.Код КАК Код,
                                            Номенклатура.Наименование КАК Наименование,
                                            Номенклатура.ЕдиницаИзмерения КАК ЕдиницаИзмерения,
                                            Номенклатура.Описание КАК Описание
                                        ИЗ
                                            Справочник.Номенклатура КАК Номенклатура
                                        ГДЕ
                                            Номенклатура.Код В ({', '.join(list_codes)})
                                            И Номенклатура.ЭтоГруппа = ЛОЖЬ
                                            И Номенклатура.ПометкаУдаления = ЛОЖЬ

                                        УПОРЯДОЧИТЬ ПО
                                            Код УБЫВ
                                    """
                    code, data = APIERP.get_wet_request(text=text)
                    not_founded_cods = []
                    if code != 200:
                        CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
                        return
                    if data['data']:
                        founded_cods = F.deploy_dict_c(data['data'], 'Код')
                        for osn in list_codes_erp:
                            cod = osn
                            name = f'{CEmoji.СтатусыПроизводства.error}Не найден в {USRCNF.Config.user_config.ERP_base_name["Значение"]}, не будет выгружен'
                            mesure = 'Шт.'
                            load = False
                            if osn in founded_cods:
                                cod = osn
                                name = founded_cods[osn]['Наименование']
                                mesure = founded_cods[osn]['ЕдиницаИзмерения']
                                load = True
                            rez_new[0]['Операции'][dict_rc_vid[prof_s_rc]]['Оснастка'].append({'Код':cod, 'Наименование':name, 'mesure':mesure, 'load_to_erp':load})
        return rez_new
        CQT.msgboxg_get_table_ok_inf(self, 'Check', dev_analisis, load_summ=True)

    def generate_table_form(self, DICT_DSE, DICT_PROF_CODE, DICT_NOMEN, silent_mode=False):
        """    стадия МК(ресурсной план)
    этап по имени операции (operacii)
    вид работ по профессии (professions)

    стадия выгрузки трудов (факт)
    этап по должности исполнителя (dolgn_etap)
    вид работ по должности исполнителя (professions)"""
        res = copy.deepcopy(self.res)

        res, msg = self.__clear_zero_time_opers(res)
        res = self.__add_code_erp(DICT_DSE, res)
        res = self.apply_kotlovoy_method(DICT_PROF_CODE, DICT_NOMEN, res, self.parent_self)
        if res == None:
            return
        self.res_kotel = res
        if msg and not silent_mode:
            CQT.msgboxg_get_table(self.parent_self, 'Внимание', msg, 'OK', disable_btn1=True)
        rez_list = []

        def add_row(rez_list, lvl, Тип, Наименование, Номер, Вид_работ='', Количество=1, Ед_изм='', Этап='',
                    Подразделение=''):
            tnp_dict = {'lvl': f'{"    " * lvl}{lvl}',
                        'Тип': f'{"    " * lvl}{Тип}',
                        'Наименование': Наименование,
                        'Номер': Номер,
                        'Вид работ': Вид_работ,
                        'Количество': Количество,
                        'Ед изм': Ед_изм,
                        'Этап': Этап,
                        'Подразделение': Подразделение
                        }
            rez_list.append(tnp_dict)
            return rez_list

        test = []
        for dse in res:
            rez_list = add_row(rez_list, 1, 'ДСЕ', dse['Наименование'], dse['Номенклатурный_номер'],
                               Количество=dse['Количество_ед'], Ед_изм='Штука')
            for rc in dse['Операции']:
                vid_rab = DICT_PROF_CODE[rc['Опер_профессия_код']]['вид_работ']

                etap = self.parent_self.myparent.DICT_RC[rc['Опер_РЦ_код']]['etaps_name']
                if 'Опер_РЦ_наименование' not in rc:
                    CQT.msgbox(
                        f"Опер_РЦ_наименование (Рабочий центр) отсутствет в ДСЕ {dse['Наименование']} {dse['Номенклатурный_номер']}")
                    return
                Примечание = ''
                if rc['Опер_РЦ_код'] in self.parent_self.myparent.DICT_RC:
                    Опер_РЦ_наименование = self.parent_self.myparent.DICT_RC[rc['Опер_РЦ_код']]['Имя']
                    Примечание = " (" + self.parent_self.myparent.DICT_RC[rc['Опер_РЦ_код']]['Примечание'] + ')'
                rez_list = add_row(rez_list, 2, 'РЦ', Опер_РЦ_наименование + Примечание, rc['Опер_РЦ_код'],
                                   vid_rab, round(rc['Опер_Тпз'] + rc['Опер_Тшт'], 3), 'мин', etap,
                                   rc['Опер_наименование_подразделения'])
                test.append([dse['Номенклатурный_номер'], rc['Опер_РЦ_наименование'], etap,
                             str(rc['Опер_Тпз'] + rc['Опер_Тшт'])])
                for mat in rc['Материалы']:
                    Мат_наименование = self.parent_self.myparent.DICT_NOMEN[mat['Мат_код']]['Наименование']
                    Мат_ед_изм = self.parent_self.myparent.DICT_NOMEN[mat['Мат_код']]['ЕдиницаИзмерения']
                    rez_list = add_row(rez_list, 3, 'Мат.', Мат_наименование, mat['Мат_код'],
                                       vid_rab, round(mat['Мат_норма'], 3), Мат_ед_изм, etap,
                                       rc['Опер_наименование_подразделения'])



                for osn in rc['Оснастка']:
                    rez_list = add_row(rez_list, 3, 'Осн.', osn['Наименование'], osn['Код'],
                                       vid_rab, 1,  osn['mesure'], etap,
                                       rc['Опер_наименование_подразделения'])
        return rez_list
        CQT.msgboxg_get_table_ok_inf(self.parent_self, 'test', [[_[0], _[1], _[2], str(_[3])] for _ in test],
                                     use_first_row_as_header=False)


class mywindow_res(QtWidgets.QDialog):  # диалоговое окно
    def __init__(self, parent,name_res_for_ERP=None,possible_upload_ERP=False,nom_mk=None,save_as_predv_res=False,num_kpl=None,primech:str|None=None):
        self.myparent:mywindow = parent
        super(mywindow_res, self).__init__()
        self.ui3 = Ui_WindowRes()
        self.ui3.setupUi(self)
        self.setStyleSheet(parent.styleSheet())
        #self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle("Заголовок")
        self.err = False
        self.db_resxml = USRCNF.Config.project.db_resxml
        self.db_kplan = USRCNF.Config.project.db_kplan
        self.db_dse = USRCNF.Config.project.db_dse
        self.ui3.mouseReleaseEvent=lambda event,my_variable:self.clck_form(event,my_variable)
        self.ui3.btn_send_toERP.clicked.connect(self.send_to_ERP)
        self.ui3.btn_compare_res.clicked.connect(self.show_hide_list_old_res)
        self.ui3.btn_show_options_upload_erp.clicked.connect(self.show_options_upload)
        self.ui3.btn_show_options_upload_erp.setEnabled(possible_upload_ERP)
        self.ui3.tbl_list_res.doubleClicked.connect(self.select_res_compare)
        self.showMaximized()
        self.dragPos = QtCore.QPoint()
        CQT.load_css(self)
        CQT.load_icons(self,24)
        self.generate_and_fill_tbl_res(self.myparent.res, name_res_for_ERP, nom_mk=nom_mk, num_kpl=num_kpl, primech=primech)
        if self.err:
            return
        self.ui3.fr_list_res.setHidden(True)
        self.save_as_predv_res= save_as_predv_res
        self.load_list_old_res()
        self.ui3.fr_res2.setHidden(True)
        self.ui3.fr_options_upload.setHidden(True)
        self.fact_load_res = False
        if not USRCNF.Config.user_config.is_developer:
            self.check_box_tkp()

    def check_box_tkp(self):
        list_points = [
            {'Пункт': '1. Обрезь отсутствует в РС', 'Чек': ''},
            {'Пункт': '2. Привод, находящийся в проработке, отсутствует в РС', 'Чек': ''},
            {'Пункт': '3. Проверить, соответствует ли масса чертежу ВО', 'Чек': ''},
            {'Пункт': '4. Проверить наполняемость структуры изделия сравнивая с ВО', 'Чек': ''},

        ]
        def add_check(tbl:QtWidgets.QTableWidget):
            for i in range(tbl.rowCount()):
                CQT.add_check_box(tbl,i,1)
            tbl.setColumnWidth(0,600)
        CQT.msgboxg_get_table_ok_inf(self,'Чек-лист',list_points,selectRows=True,func_oform_tbl=add_check)





    def full_screen(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonDblClick:
            self.full_screen()


    def keyReleaseEvent(self, e):
        if self.ui3.tbl_res_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui3.tbl_res_filtr, self.ui3.tbl_res)
                CMS.fill_summ_tbl(self, self.ui3.tbl_res_summ, self.ui3.tbl_res, {'Количество'}, round_summ_digit=3)
        if self.ui3.tbl_list_res_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui3.tbl_list_res_filtr, self.ui3.tbl_list_res)
        if self.ui3.tbl_res_filtr_2.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self, self.ui3.tbl_res_filtr_2, self.ui3.tbl_res_2)
                CMS.fill_summ_tbl(self, self.ui3.tbl_res_summ_2, self.ui3.tbl_res_2, {'КолРес_1','КолРес_2','Дельта','Дельта%'}, round_summ_digit=2,average=True)

        if e.key() == 67 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())
        if e.key() == QtCore.Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()


    def generate_and_fill_tbl_res(self, res, name_res_for_ERP="", nom_mk=None, num_kpl=None, primech: str | None=None):
        # if 'tkp_current_schema' in self.myparent.__dict__: #09.04.25
        tkp_current_schema = self.myparent.tkp_current_schema

        proj_name = self.myparent.dict_cur_poz_cr_mk['Проект']
        if proj_name and len(proj_name) == 5 and '.ВО' in proj_name:
            schema = self.myparent.tkp_current_schema
            if 'file_name' in schema:
                name_res_for_ERP = schema['file_name']
                napr_deyat_is_kt = None

                if F.valm(schema['вид_по_напр']) in self.myparent.Data_plan.DICT_VID_PO_NAPR:
                    napr_deyat_is_kt = self.myparent.Data_plan.DICT_VID_PO_NAPR[int(schema['вид_по_напр'])]['napravl_deyat.Псевдоним'] == 'КТ'
                if schema['name_tkp'] is not None and (schema['name_tkp'].lower() == 'Компенсатор тканевый'.lower() or napr_deyat_is_kt):
                    try:
                        pref, snom, *nomen  =  schema['nnom_tkp'].split('_')
                        nomen = '_'.join(nomen)
                        name_res_for_ERP = f'{pref}_{snom}_Металлическая арматура для компенсатора {nomen}'
                    except:
                        pass
            else:
                name_res_for_ERP = (f"{F.clear_row_for_file_name_c(self.myparent.tkp_current_schema['nnom_tkp'])}"
                                    f"_{F.clear_row_for_file_name_c(self.myparent.tkp_current_schema['name_tkp'])}")

        res_obj = Resourse_mk(res,self.myparent.db_resxml,self.myparent.db_kplan,self.myparent.bd_naryad,
                                  self.myparent.db_users,tkp_current_schema,self,name_res_for_ERP,nom_mk=nom_mk,num_kpl=num_kpl,primech=primech)

        list_data = res_obj.generate_table_form(self.myparent.DICT_DSE_save_mk,self.myparent.DICT_PROF_CODE,self.myparent.DICT_NOMEN, silent_mode=True)
        if list_data == None:
            self.close()
            self.err=True
            return
        CQT.fill_wtabl(list_data,self.ui3.tbl_res,auto_type=False,height_row=24,ogr_maxshir_kol=600)
        CMS.fill_filtr_c(self,self.ui3.tbl_res_filtr,self.ui3.tbl_res,hidden_scroll=True)
        CMS.update_width_filtr(self.ui3.tbl_res,self.ui3.tbl_res_filtr)
        CMS.fill_summ_tbl(self,self.ui3.tbl_res_summ,self.ui3.tbl_res,{'Количество'},round_summ_digit=3)
        for i in range(self.ui3.tbl_res.rowCount()):
            if '1' in self.ui3.tbl_res.item(i,0).text():
                for j in range(self.ui3.tbl_res.columnCount()):
                    CQT.set_color_wtab_c(self.ui3.tbl_res,i,j,255, 204, 102)
            if '2' in self.ui3.tbl_res.item(i,0).text():
                for j in range(self.ui3.tbl_res.columnCount()):
                    CQT.set_color_wtab_c(self.ui3.tbl_res,i,j,102, 153, 255)
            if '3' in self.ui3.tbl_res.item(i,0).text():
                if 'Мат.' in self.ui3.tbl_res.item(i,1).text():
                    for j in range(self.ui3.tbl_res.columnCount()):
                        CQT.set_color_wtab_c(self.ui3.tbl_res,i,j,153, 204, 153)
                if 'Осн.' in self.ui3.tbl_res.item(i,1).text():
                    for j in range(self.ui3.tbl_res.columnCount()):
                        CQT.set_color_wtab_c(self.ui3.tbl_res,i,j,*F.hex_to_rgb('#CC99CC'))
                        pass
        self.res_data = list_data
        self.ui3.le_res_first.setText(res_obj.nn)
        self.res_obj = res_obj
    def compare_res(self,list_data_l,res_r):

        def dict_form_list_data_res(res):
            dict_data = dict()
            for item in res:
                key = '$'.join([item['Этап'], item['Подразделение'], item['Номер']])
                val = F.valm(item['Количество'])
                if key not in dict_data:
                    dict_data[key] = {'data':item,'val':0}
                dict_data[key]['val'] += val
            return dict_data

        def compare_lr(dict_data_l,dict_delta_r):
            dict_delta_rez = dict()
            for item_l, vals_l in dict_data_l.items():
                delta = vals_l['val']
                l_val = 0
                if item_l in dict_delta_r:
                    delta = vals_l['val'] - dict_delta_r[item_l]['val']
                    l_val= dict_delta_r[item_l]['val']
                if delta > 0:
                    dict_delta_rez[item_l] = {'item':vals_l['data'],'delta': delta,'l_val':l_val,'r_val':vals_l['val']}
            return dict_delta_rez

        tkp_current_schema = self.myparent.tkp_current_schema #09.04.25
        # if 'tkp_current_schema' in self.myparent.__dict__:
        #     tkp_current_schema = self.myparent.tkp_current_schema

        res_obj_r = Resourse_mk(res_r, self.myparent.db_resxml,self.myparent.db_kplan,self.myparent.bd_naryad,
                                    self.myparent.db_users,tkp_current_schema,self)
        list_data_r = res_obj_r.generate_table_form(self.myparent.DICT_DSE_save_mk, self.myparent.DICT_PROF_CODE, self.myparent.DICT_NOMEN)

        if list_data_r == None:
            return
        dict_data_l = dict_form_list_data_res(list_data_l)
        dict_data_r = dict_form_list_data_res(list_data_r)

        dict_delta_l = compare_lr(dict_data_l,dict_data_r)
        dict_delta_r = compare_lr(dict_data_r,dict_data_l)

        delta_rez = []
        def add_delta_to_rez(list_rez,dict_delta,name_l,name_r):
            for item, val in dict_delta.items():

                tmp_item:dict
                tmp_item = copy.deepcopy(val['item'])
                tmp_item.pop('Количество', None)
                tmp_item.pop('lvl', None)
                name_kol_l = 'КолРес_' + name_l
                name_kol_r = 'КолРес_' + name_r
                tmp_item[name_kol_l] = round(val['r_val'],3)
                tmp_item[name_kol_r] = round(val['l_val'],3)
                tmp_item['Дельта'] = round(val['delta'],3)
                list_rez.append(tmp_item)
            return list_rez

        delta_rez = add_delta_to_rez(delta_rez,dict_delta_l,'1','2')
        delta_rez = add_delta_to_rez(delta_rez, dict_delta_r, '2','1')

        for item in delta_rez:
            item['Дельта'] = item.pop("Дельта")
            delta_p = 100
            if item['Дельта'] == 0:
                delta_p = 0
            else:
                if item['КолРес_1'] > 0:
                    delta_p = round(item['Дельта']/item['КолРес_1']*100,2)
            item['Дельта%'] = delta_p

        delta_rez = F.sort_by_column_c(delta_rez,'Дельта%',revers=True)
        CQT.fill_wtabl(delta_rez,self.ui3.tbl_res_2,auto_type=False,height_row=24,ogr_maxshir_kol=500)
        CMS.fill_filtr_c(self,self.ui3.tbl_res_filtr_2,self.ui3.tbl_res_2,hidden_scroll=True)
        CMS.update_width_filtr(self.ui3.tbl_res_2,self.ui3.tbl_res_filtr_2)
        CMS.fill_summ_tbl(self, self.ui3.tbl_res_summ_2, self.ui3.tbl_res_2, {'КолРес_1','КолРес_2','Дельта','Дельта%'}, round_summ_digit=2,average=True)




    @CQT.onerror
    def load_list_old_res(self,*args):
        list_mk_res = CSQ.custom_request_c(self.myparent.db_resxml,f"""SELECT Номер_мк FROM res""",hat_c=False,one_column=True)
        list_mk = CSQ.custom_request_c(self.myparent.bd_naryad, f"""
            SELECT 'МК' as 'Тип', mk.Пномер, mk.Номенклатура as Имя 
            FROM mk 
            INNER JOIN plan ON plan.Пномер = mk.НомКплан
            WHERE mk.Пномер in ({CSQ.prepare_list_to_tuple(list_mk_res)})
                AND plan.poki = {USRCNF.Config.place.poki}
""", rez_dict=True, attach_dbs=USRCNF.Config.project.db_kplan) # 05.08.25
        list_tkp =  CSQ.custom_request_c(self.myparent.db_resxml,f"""SELECT 'ТКП' as 'Тип', Пномер as Пномер,  Имя as Имя FROM predv_res;""",rez_dict=True)

        for row in list_mk:
            list_tkp.append(row)

        CQT.fill_wtabl(list_tkp,self.ui3.tbl_list_res,auto_type=False,height_row=24)
        CMS.fill_filtr_c(self,self.ui3.tbl_list_res_filtr,self.ui3.tbl_list_res,hidden_scroll=True)
        CMS.update_width_filtr(self.ui3.tbl_list_res,self.ui3.tbl_list_res_filtr)

    @CQT.onerror
    def show_hide_list_old_res(self, *args):
        if self.ui3.fr_list_res.isHidden():
            self.ui3.fr_list_res.setHidden(False)
            self.ui3.fr_options_upload.setHidden(True)
        else:
            self.ui3.fr_list_res.setHidden(True)
    @CQT.onerror
    def select_res_compare(self, *args):
        row = CQT.get_dict_line_form_tbl(self.ui3.tbl_list_res)
        if row == {}:
            return

        res_old = None
        s_num = int(row['Пномер'])
        if row['Тип'] == 'МК':
            res_old = CMS.load_res(s_num,'','',self=self.myparent)

        if row['Тип'] == 'ТКП':
            #data = CSQ.custom_request_c(self.myparent.db_resxml, f"""SELECT * FROM predv_res WHERE Пномер = {row['Пномер']};""",
            #                                        rez_dict=True)
            res_old = CMS.load_res(s_num,'','',self=self.myparent, tkp=True)

        self.show_hide_list_old_res()
        self.ui3.le_res_second.setText(row['Имя'])
        self.compare_res(self.res_data,res_old)

        self.ui3.fr_res2.setHidden(False)
        self.ui3.fr_options_upload.setHidden(True)

    @CQT.onerror
    def show_options_upload(self, *args):
        LIST_VIDS_NOMEN = ()
        if USRCNF.Config.place.poki == 0:
            LIST_VIDS_NOMEN  = ("Металлическая арматура", "Фильтры рукавные", "ФР.2403088", "Аппараты обдувки",
                            "Газоходы", "Горелки", "Испытательный цех", "Клапаны", "Линзовые компенсаторы",
                            "Металлоизделия", "Прочая продукция Пауэрза", "Рукава фильтровальные",
                            "Системы газоочистки и компоненты", "Системы сухого золоудаления и ком-ты",
                            "Шумоглушители")
        if USRCNF.Config.place.poki == 1:
            LIST_VIDS_NOMEN = (
            "Компенсатор тканевый",
            "БСИ_Изоляция рукавов",
            "БСИ_КЗХ",
            "БСИ_КИП",
            "БСИ_Оборудование",
            "БСИ_Палеты",
            "БСИ_Рукава",
            "КЗХ Стандарт",
            "Готовая набивка (Подушки)",
            "Гибкие вставки",
            "Лента для гибких вставок",
            "Рукава фильтровальные",
            "Поддоны обычные",
            "Ящики (на обычных поддонах)",
            "Изделия, формы деревянные",
            "Обрешетка деревянная",
            "Оснастка для литья",
            "Поддоны усиленные",
            "Упаковка КЛ",
            "Упаковка не стандарт",
            "Ящики не стандарт",
            "Крышки для ящиков",
            "Стенки боковые",
            "Стенки торцевые",
           "Прочая продукция Келаста",
           "Арматура литейная",
            )

        self.ui3.fr_res2.setHidden(True)
        self.ui3.fr_options_upload.setHidden(False)
        self.ui3.fr_list_res.setHidden(True)
        start_date =F.now()
        if not self.res_obj.is_tkp and F.is_date(self.res_obj.poz.max_date,"%d.%m.%Y"):
            start_date = F.datetostr(F.strtodate(self.res_obj.poz.max_date,"%d.%m.%Y" ))
        date_end = F.date_add_days(start_date,28)

        name_res = self.res_obj.name_res_for_ERP
        if USRCNF.Config.user_config.is_developer:
            name_res = self.res_obj.name_res_for_ERP + "_test"
        headers = [['Параметр',"Значение",'Действие','Создать'],
                   ['Наименование ресурсной',name_res,'',''],
                   ['Код ресурсной', '', '', ''],
                   ['НачалоДействия ресурсной',F.now(),'',''],
                   ['КонецДействия ресурсной', date_end,'',''],
                   ['ОсновноеИзделиеНоменклатура','','',''],
                   ['ОсновноеИзделиеАртикул', '', '', ''],
                   ['ОсновноеИзделиеКод','','',''],
                   ['ГруппаКод','','',''],
                   ['Связать с КПЛ','','',''],
                   ]

        def coord(row_name=None, col_name=None):
            row = None
            col = None
            if row_name:
                for i in range(len(headers)):
                    if headers[i][0] == row_name:
                        row = i-1
                        break
            if col_name:
                for j in range(len(headers[0])):
                    if headers[0][j] == col_name:
                        col = j
                        break
            return row,col

        CQT.fill_wtabl(headers ,self.ui3.tbl_options_for_erp,{"Значение"},800,height_row=24,auto_type=False,min_width_col=200,styleSheet=CQT.ERP_CSS)

        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеНоменклатура',"Значение") ,False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('Код ресурсной', "Значение"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул',"Значение"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеКод',"Значение"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул',"Создать"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ГруппаКод',"Создать"), False)
        CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ГруппаКод',"Значение"), False)

        def edit_art():
            row = self.ui3.tbl_options_for_erp.currentRow()
            col = self.ui3.tbl_options_for_erp.currentColumn()
            if (row, col) == coord('ОсновноеИзделиеАртикул','Создать'):
                art = self.ui3.tbl_options_for_erp.item(*(row, col)).text()
                if art.strip() == '':
                    text_art = ''
                else:
                    text_art = 'Металлическая арматура для компенсатора ' + art
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеНоменклатура','Создать')).setText(text_art)

            if (row, col) == coord('Наименование ресурсной','Значение'):
                self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText('')

        self.ui3.tbl_options_for_erp.cellChanged.connect(edit_art)
        str_НомерВидаНоменДляСозданияРесЕРП = self.myparent.Data_plan.DICT_VID_PO_NAPR[self.res_obj.вид_по_напр]['НомерВидаНоменДляСозданияРесЕРП']

        dict_ordered_type_refs = None

        if str_НомерВидаНоменДляСозданияРесЕРП == None or str_НомерВидаНоменДляСозданияРесЕРП == '':
            list_tmp = copy.deepcopy(LIST_VIDS_NOMEN)
            list_vids = ', '.join(['"' + _ + '"' for _ in list_tmp])
            main_sql_param = f"ВидыНоменклатуры.Наименование В ({list_vids})"
        else:
            # list_tmp = copy.deepcopy([self.myparent.Data_plan.DICT_VID_NOMEN_NUM[int(_)]['name'] for _ in str_НомерВидаНоменДляСозданияРесЕРП.split(';')])
            list_tmp = copy.deepcopy([self.myparent.Data_plan.DICT_VID_NOMEN_NUM[int(_)]['Ref_Key'] for _ in str_НомерВидаНоменДляСозданияРесЕРП.split(';')])
            dict_ordered_type_refs = { # 22.10.25 по задаче 100061761
                f'&ВидНоменклатуры_{index}':ref for index, ref in enumerate(list_tmp)
                if F.is_unique_identifier(ref)
            }
            sql_vars = ", ".join(list(dict_ordered_type_refs.keys()))
            main_sql_param = f"Номенклатура.ВидНоменклатуры В ({sql_vars})"

        affix = ''

        msg_about_nomen = f''
        if not self.res_obj.is_tkp and not self.res_obj.num_kpl == 3345:
            name_izd = self.res_obj.izd
            if name_izd:
                name_izd = name_izd.replace('"', '\""') #12.08.25
                affix = f' И Номенклатура.Наименование = "{name_izd}"'
                msg_about_nomen = f'- Наличие номенклатуры в ЕРП\n      `{name_izd}`\n'

        text = f"""ВЫБРАТЬ 
            ВидыНоменклатуры.Наименование КАК Вид,
            Номенклатура.Наименование КАК Наименование,
            Номенклатура.Код КАК Код,
            Номенклатура.Артикул КАК Артикул
        ИЗ
            Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
                ЛЕВОЕ СОЕДИНЕНИЕ Справочник.Номенклатура КАК Номенклатура
                ПО (Номенклатура.ВидНоменклатуры = ВидыНоменклатуры.Ссылка)
        ГДЕ
            {main_sql_param}
            И Номенклатура.ПометкаУдаления = ЛОЖЬ {affix}"""
        refs = None # 22.10.25 по задаче 100061761
        if dict_ordered_type_refs:
            refs = APIERP.Refs_wet(text_req=text)
            for nick, ref in dict_ordered_type_refs.items():
                ref_obj = APIERP.Ref_wet(nick[1:], 'Справочники.ВидыНоменклатуры', ref)
                refs.add_ref(ref_obj)
        code, data  = APIERP.get_wet_request(text=text, refs=refs)
        list_nomen = []
        if code != 200:
            CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
            self.close()
            return

        if not len(data['data']):
            CQT.msgbox(f'Номенклатура не найдена!\n Необходимо проверить:\n'
                       f'- Текущую базу ЕРП в настройках МЕС\n'
                       f'- Номенклатуру, указанную в МЕС в КПЛ\n'
                       f'{msg_about_nomen}'
                       
                       f'- НомерВидаНоменДляСозданияРесЕРП\n      на {self.res_obj.вид_по_напр} вид\n'
                       )
            self.close()
            return
        @CQT.onerror
        def check_exist_res(self, row, col):

            def check_is_block_state_res(new_name) -> (bool, list):
                text = f"""ВЫБРАТЬ 
                    РесурсныеСпецификации.Код КАК Код,
                	РесурсныеСпецификации.Статус КАК Статус
                ИЗ
                    Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                ГДЕ
                    РесурсныеСпецификации.Наименование = "{new_name}"
                    И РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
                    И РесурсныеСпецификации.ЭтоГруппа = ЛОЖЬ"""
                code, data = APIERP.get_wet_request(text=text)
                if code != 200:
                    CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
                    return True, []
                if len(data['data']):
                    list_blocked_res = []
                    for res in data['data']:
                        if res['Статус'] == 'Действует':
                            res['Решение'] = 'Выбрать другое `Наименование ресурсной`'
                            list_blocked_res.append(res)
                    if list_blocked_res:
                        CQT.msgboxg_get_table_ok_inf(self, 'Ресурсные с таким именем, имеют статус `Действует`и заблокированы от затирания и удаления',
                                                     list_blocked_res, show_filtr=False)
                        return True, []
                return False, data

            def check_is_used_in_ZP(new_name):
                text = f"""ВЫБРАТЬ
                                    
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Код КАК СпецификацияКод,
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Наименование КАК СпецификацияНаименование,
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Статус КАК СпецификацияСтатус,
                                    ЗаказНаПроизводство2_2Продукция.Ссылка.Статус КАК ЗаказНаПроизводствоСтатус,
                                    ЗаказНаПроизводство2_2Продукция.Ссылка КАК ЗаказНаПроизводство
                                    ИЗ
                                    Документ.ЗаказНаПроизводство2_2.Продукция КАК ЗаказНаПроизводство2_2Продукция
                                    ГДЕ
                                    ЗаказНаПроизводство2_2Продукция.Спецификация.Наименование = "{new_name}" 
                                    И ЗаказНаПроизводство2_2Продукция.Спецификация.ПометкаУдаления = ЛОЖЬ 
                                    И ЗаказНаПроизводство2_2Продукция.Ссылка.ПометкаУдаления = ЛОЖЬ"""
                code, data = APIERP.get_wet_request(text=text)
                if code != 200:
                    CQT.msgbox(f'Запрос get_wet_request номенклатуры в 1С ошибка {code}')
                    return True
                return data['data']

            new_name = self.ui3.tbl_options_for_erp.item(0 ,1).text().replace('"', '\""') #12.08.25
            self.ui3.tbl_options_for_erp.item(1, 1).setText('')


            is_block_state, data_list_found_res = check_is_block_state_res(new_name)
            if is_block_state:
                self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной', 'Создать')).setText("")
                return

            is_used_in_ZP = check_is_used_in_ZP(new_name)
            if is_used_in_ZP:
                CQT.msgboxg_get_table_ok_inf(self, 'Ресурсная с таким именем уже используется в ЗП',
                                             is_used_in_ZP, show_filtr=False)
                return

            if len(data_list_found_res['data']):
                if len(data_list_found_res['data']) > 1:
                    self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной', 'Создать')).setText(
                        'Создать новую')
                else:
                    res_code = data_list_found_res['data'][0]['Код']
                    if CQT.msgboxgYN(f"Ресурсная\n{res_code}\n{new_name}\nуже существует",'Создать новую',"Перезаполнить"):
                        self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText('Создать новую')
                    else:
                        self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText(f"Перезаполнить")
                        self.ui3.tbl_options_for_erp.item(1, 1).setText(res_code)
            else:
                self.ui3.tbl_options_for_erp.item(*coord('Наименование ресурсной','Создать')).setText("Свободно")


        @CQT.onerror
        def select_nomen(self, row, col, *args):
            if args:
                rez = args[0]
            else:
                rez = CQT.msgboxg_get_table(self,'Выбор номенклатуры',list_nomen,selectRows=True,ExtendedSelection=False,selection_from_tbl=True)
            if  rez:
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеНоменклатура','Значение')).setText(rez['Наименование'])
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеАртикул','Значение')).setText(rez['Артикул'])
                self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеКод','Значение')).setText(rez['Код'])

        @CQT.onerror
        def create_nomen(self, row, col):
            new_art = self.ui3.tbl_options_for_erp.item(5,3).text()
            new_nomen = self.ui3.tbl_options_for_erp.item(4,3).text()

            if new_art == '':
                CQT.msgbox(f'Артикул не введен')
                return
            msg_yn = f'''Будет создана новая номенклатура:\n
            Наименование: `{new_nomen}`
            Артикул: `{new_art}`'''
            if not CQT.msgboxgYN(msg_yn):
                return

            dict_nomen = {'Наименование':new_nomen,
                          'НаименованиеПолное': new_nomen,
                            'Артикул':new_art,
                          'ТипНоменклатуры': 'Товар',
                          'ВариантОформленияПродажи': 'РеализацияТоваровУслуг',
                          'ГруппаДоступа': 'Продукция Пауэрз для Эластика',
                          'ЕдиницаИзмерения': 'Штука',
                          'ЕдиницаДляОтчетов': 'Штука',
                          'ИспользованиеХарактеристик': 'НеИспользовать',
                          'ВидНоменклатуры': 'Металлоизделия',
                          'СтавкаНДС': '20%',
                          'ГруппаАналитическогоУчета': 'Металлоизделия',
                          'ГруппаФинансовогоУчета': 'Продукция собственного производства (Пауэрз)',

                          }
            code, data  =APIERP.make_nomen(dict_nomen)
            if code != 200:
                CQT.msgbox(f'Запрос создания номенклатуры в 1С ошибка код {code}\n{data["Ошибки"]}')
                return
            new_cod = data["Код"]
            self.ui3.tbl_options_for_erp.item(4, 1).setText(new_nomen)
            self.ui3.tbl_options_for_erp.item(5, 1).setText(new_art)
            self.ui3.tbl_options_for_erp.item(6, 1).setText(new_cod)

            CQT.msgbox('Успешно',time_life=0.5)

        @CQT.onerror
        def clear_group(lblself:CQT.InteractiveLabelInstance,self, row, col):
            self.ui3.tbl_options_for_erp.item(*coord('ГруппаКод', "Значение")).setText('')
            lblself.set_text('')

        @CQT.onerror
        def select_group( lblself:CQT.InteractiveLabelInstance,self, row, col):
            text = f"""ВЫБРАТЬ
                РесурсныеСпецификации.Ссылка КАК Ссылка,
                РесурсныеСпецификации.Родитель КАК Родитель,
                РесурсныеСпецификации.Код КАК Код
            ИЗ
                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
            ГДЕ
                РесурсныеСпецификации.ЭтоГруппа = ИСТИНА
                И РесурсныеСпецификации.Ссылка В ИЕРАРХИИ
                        (ВЫБРАТЬ ПЕРВЫЕ 1
                            РесурсныеСпецификации.Ссылка КАК Ссылка
                        ИЗ
                            Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                        ГДЕ
                            РесурсныеСпецификации.ЭтоГруппа = ИСТИНА
                            И РесурсныеСпецификации.Код = "{USRCNF.Config.place.КодГруппыРесурсных}")
            УПОРЯДОЧИТЬ ПО
                Родитель"""
            key, data_rez = APIERP.get_wet_request(text=text)
            if key != 200:
                raise ConnectionError(f'Ошибка получения данных РесурсныеСпецификации из ERP')

            if not data_rez['data']:
                raise ValueError(f'Не найдено РесурсныеСпецификации из ERP')

            list_groups = data_rez['data']
            rez = CQT.msgboxg_get_table(self, 'Выбор группы', list_groups, selectRows=True,
                                        ExtendedSelection=False, selection_from_tbl=True)
            if not rez:
                return
            self.ui3.tbl_options_for_erp.item(*coord('ГруппаКод', "Значение")).setText(rez['Код'])
            lblself.set_text(rez['Код'])


        list_nomen = data['data']
        CQT.add_btn(self.ui3.tbl_options_for_erp, *coord('Наименование ресурсной','Действие'),
                    'Чек наличие', conn_func_checked_row_col=check_exist_res,
                    self=self)

        widget = CQT.add_interactive_label(
            self.ui3.tbl_options_for_erp,
            *coord('ГруппаКод', 'Значение'),
            text=self.ui3.tbl_options_for_erp.item(*coord('ГруппаКод', "Значение")).text(),
            txt_cut=14,
            btn_width=25,
            parent_self=self,
        )
        widget.add_button(txt_button='...',
                          on_clicked= select_group,
                          tooltip='Подбор группы ресурсной')

        widget.add_button(txt_button='X',
                          on_clicked=clear_group,
                          tooltip='Очистить')

        #CQT.add_btn(self.ui3.tbl_options_for_erp, *coord('ГруппаКод', 'Действие'),
        #            'Подбор группы ресурсной', conn_func_checked_row_col=select_group, self=self)
        CQT.add_check_box(self.ui3.tbl_options_for_erp, *coord('Связать с КПЛ', "Значение"),val=False,enabled=not self.res_obj.is_tkp)

        if len(list_nomen) == 1:
            select_nomen(self,1,1,list_nomen[0])
        else:
            CQT.add_btn(self.ui3.tbl_options_for_erp,*coord('ОсновноеИзделиеНоменклатура','Действие'),
                    'Подбор номенклатуры',conn_func_checked_row_col=select_nomen, self=self)
        if self.myparent.Data_plan.DICT_VID_PO_NAPR[self.res_obj.вид_по_напр]['ВозможностьСозданияНоменМеталоармДляСозданияРесЕРП']:
            self.ui3.tbl_options_for_erp.item(*coord('ОсновноеИзделиеАртикул', "Создать")).setText('Ввод наименования ...')
            CQT.set_cell_editable(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул', "Создать"), True)
            CQT.add_btn(self.ui3.tbl_options_for_erp, *coord('ОсновноеИзделиеАртикул', 'Действие'),
                        'Создать номенклатуру ->', conn_func_checked_row_col=create_nomen, self=self)

    @CQT.onerror
    def send_to_ERP(self, *args):
        def check():
            tbl = self.ui3.tbl_options_for_erp
            if tbl.item(0 ,3).text() == "":
                CQT.blink_obj_c(self,2,tbl.cellWidget(0,2),f'Не проверено наличие ресурсной')
                return False
            if tbl.item(4 ,1).text() == "":
                CQT.blink_obj_c(self,2,tbl.cellWidget(4,2),f'Не указан ОсновноеИзделиеНоменклатура')
                return False
            if tbl.item(5 ,1).text() == "":
                if not CQT.msgboxgYN_delay('Не задан артикул основного изделия. Продолжить создание ресурсной БЕЗ артикула основного изделия?'):
                    CQT.blink_obj_c(self,2,tbl.cellWidget(4,2),f'Не указан ОсновноеИзделиеАртикул')
                    return False
            if tbl.item(6 ,1).text() == "":
                CQT.blink_obj_c(self,2,tbl.cellWidget(4,2),f'Не указан ОсновноеИзделиеКод')
                return False
            if tbl.item(0 ,1).text() == "":
                CQT.migat(self,tbl,0,1 ,2,f'Не указан Наименование ресурсной')
                return False
            if not F.is_date(tbl.item(2 ,1).text()):
                CQT.migat(self,tbl,2,1 ,2,f'Не указан НачалоДействия ресурсной\nформат: "%Y-%m-%d %H:%M:%S"')
                return False
            if not F.is_date(tbl.item(3 ,1).text()):
                CQT.migat(self,tbl,3,1 ,2,f'Не указан КонецДействия ресурсной\nформат: "%Y-%m-%d %H:%M:%S"')
                return False
            if F.strtodate(tbl.item(2 ,1).text()) >= F.strtodate(tbl.item(3 ,1).text()):
                CQT.migat(self, tbl, 3, 1, 2, f'ДатаНачала >= ДатаОкончания')
                return False
            if tbl.item(7 ,1).text() == "" and not USRCNF.Config.place.poki==0 :
                CQT.blink_obj_c(self,2,tbl.cellWidget(7,1),f'Не указан ГруппаКод')
                return False

            return True

        def generate(code_old_res=None):

            hat = {_['Параметр']: _['Значение'] for _ in
                   CQT.list_from_wtabl_c(self.ui3.tbl_options_for_erp, rez_dict=True)}
            hat['РежимЗамены'] = self.ui3.tbl_options_for_erp.item(0 ,3).text()
            hat['ТекущийПользователь'] = F.user_full_namre()
            hat['НачалоДействия'] = F.datetostr(F.strtodate(hat['НачалоДействия ресурсной']),"%d.%m.%Y")
            hat['КонецДействия'] = F.datetostr(F.strtodate(hat['КонецДействия ресурсной']), "%d.%m.%Y")
            hat['Сохранять'] = True
            hat['ИмяБазы'] = USRCNF.Config.user_config.ERP_base_name['Значение']
            hat['КластерСерверов'] = self.myparent.Data_plan.DICT_BASES_ERP[hat['ИмяБазы']]['КластерСерверов']
            hat['Описание'] = ''
            hat['ПодразделениеДиспетчер'] = "Планово-диспетчерский отдел Производства (Пауэрз)"
            if self.res_obj.primech:
                hat['Описание'] = self.res_obj.primech
            if code_old_res:
                hat['Код'] = code_old_res

            data, err = self.res_obj.generate_list_res_for_erp(DICT_PROF_CODE=self.myparent.DICT_PROF_CODE,
                                                          DICT_NOMEN= self.myparent.DICT_NOMEN,
                                                          DICT_OP=self.myparent.DICT_OP,
                                                          DICT_RC = self.myparent.DICT_RC)

            if err:
                err.insert(0,['Ошибки'])
                if not CQT.msgboxg_get_table(self,'Ошибки компоновки',err,
                                             'Продолжить выгрузку','Прервать',
                                             show_filtr=False,use_first_row_as_header=True,print_hat=True,yesNoMode=True):
                    return

            if data == None:
                return
            a = [[_['Этап'], _['Данные']['Трудозатраты']] for _ in data]
            return {'hat': hat, 'data': data}

        def generate_obj(code_old_res=None):
            pref_hat = {_['Параметр']: _['Значение'] for _ in
                   CQT.list_from_wtabl_c(self.ui3.tbl_options_for_erp, rez_dict=True)}
            ОсновноеИзделиеКод = CRES.MainProduct.find_by_name(
                pref_hat['ОсновноеИзделиеНоменклатура'])

            СпособРаспределенияЗатратНаВыходныеИзделия = CRES.TheMethodOfAllocatingTheCostOfTheOutputProductsData._hnt_по_долям_стоимости_0
            РодительКод = CRES.GroupResData.find_by_code(pref_hat['ГруппаКод'], CRES.GroupRes())
            if USRCNF.Config.place.poki == 0:
                #ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_автоматически_по_приоритету_0
                ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_планово_диспетчерский_отдел_производства_пауэрз_производственные_подразделения_пауэрз_00_000049
            if USRCNF.Config.place.poki== 1:
                ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_планово_диспетчерский_отдел_производства_келаст_производственные_подразделения_келаст_00_000112
                #ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_вручную_1
            if USRCNF.Config.place.poki== 2:
                ПодразделениеДиспетчер = CRES.SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
                #ВариантПодбораВДокументы = CRES.VariationsrespecificationdocumentsData._hnt_вручную_1
            # Шапка
            hat = CRES.ResourceHeader(
                ОсновноеИзделиеКод=ОсновноеИзделиеКод,
                КоличествоУпаковок=1,
                Наименование=pref_hat['Наименование ресурсной'],
                ТекущийПользователь=CRES.CurrentUser(F.user_full_namre()),
                ДатаНачала=F.dateStrToStr(pref_hat['НачалоДействия ресурсной']),
                ДатаОкончания=F.dateStrToStr(pref_hat['КонецДействия ресурсной']),
                ПодразделениеДиспетчер=ПодразделениеДиспетчер,
                РодительКод=РодительКод,
                #ВариантПодбораВДокументы=ВариантПодбораВДокументы,
                Описание=self.res_obj.primech,
                СпособРаспределенияЗатратНаВыходныеИзделия=СпособРаспределенияЗатратНаВыходныеИзделия,
                Код=code_old_res
            )


            #data, err = self.res_obj.generate_list_res_for_erp(DICT_PROF_CODE=self.myparent.DICT_PROF_CODE,
            #                                              DICT_NOMEN= self.myparent.DICT_NOMEN,
            #                                              DICT_OP=self.myparent.DICT_OP,
            #                                              DICT_RC = self.myparent.DICT_RC)
            err = []
            data = self.res_obj.generate_ResourceSpecification(hat=hat, DICT_PROF_CODE=self.myparent.DICT_PROF_CODE,
                                                               DICT_NOMEN=self.myparent.DICT_NOMEN,
                                                               DICT_OP=self.myparent.DICT_OP,
                                                               DICT_RC=self.myparent.DICT_RC)
            if err:
                err.insert(0,['Ошибки'])
                if not CQT.msgboxg_get_table(self,'Ошибки компоновки',err,
                                             'Продолжить выгрузку','Прервать',
                                             show_filtr=False,use_first_row_as_header=True,print_hat=True,yesNoMode=True):
                    return
            if data == None:
                return

            return data #{'hat': hat, 'data': data}

        @CQT.onerror
        def send(data):
            code, answ = APIERP.post_res_json(data,self.myparent.ERP_base_name)
            if code == 200:
                return answ
            else:
                CQT.msgbox(f'Ошибка создания ресурсной. Код {code}\n{answ["Ошибки"]}')
            return False

        @CQT.onerror
        def delete_res(name):
            data = {"data": {'Наименование':name}}
            code, answ = APIERP.delete_res_json(data, self.myparent.ERP_base_name)
            if code == 200:
                if not USRCNF.Config.user_config.is_developer:
                    CMS.send_info_mk_b24_by_action(f'{F.user_full_namre()}\nУдалены, не использующиеся в ЗП, ресурсные:\n{answ["Код"]}', 'готовность РС')
                CQT.msgbox(f'Удалены ресурсные. \n{answ["Код"]}')
                return True
            else:
                CQT.msgbox(f'Ошибка удаления ресурсной. Код {code}\n{answ["Ошибки"]}')
            return False

        @CQT.onerror
        def clear_res(code):
            data = {"data": {'Код': code}}
            code_resp, answ = APIERP.clear_res_json(data, self.myparent.ERP_base_name)
            if code_resp == 200:
                if not USRCNF.Config.user_config.is_developer:
                    CMS.send_info_mk_b24_by_action(f'{F.user_full_namre()}\nОчищена и перезаполнена, не использующаяся в ЗП, ресурсная:\n{answ["Код"]}',
                                               'готовность РС')
                CQT.msgbox(f'Очищена ресурсная. \n{code}')
                return True
            else:
                CQT.msgbox(f'Ошибка очистки ресурсной. Код ошибки {code_resp}\n{answ["Ошибки"]}')
            return False


        @CQT.onerror
        def open_link(lnk,*args):
            c1_lint_wet = args[3]
            c1_link = c1_lint_wet.replace('e1cib','')
            prefix = fr'"%programfiles%\1cv8\common\1cestart.exe" '
            line = prefix + fr'/url "e1c://server/srv-1c:3541/ERP_MES1#e1cib{c1_link}"'
            try:
                subprocess.call(line, shell=True)
            except:
                F.copy_bufer(c1_lint_wet)
                CQT.msgbox(f'Скопировано в буфер\n{c1_lint_wet}')

        wo_erp = False
        if 'shift' in CQT.get_key_modifiers(self):
            wo_erp=True

        if not check():
            return

        mode = self.ui3.tbl_options_for_erp.item(0 ,3).text()
        code_old_res = None
        if mode != "":
            if mode == 'Перезаполнить':
                code_old_res = self.ui3.tbl_options_for_erp.item(1 ,1).text()

        #data_to_ERP = generate(code_old_res)

        data_to_ERP = generate_obj(code_old_res)
        if data_to_ERP == None:
            return
        code = 'None'
        data_answ = {'Ссылка':'None'}
        if not wo_erp:
            if mode != "":
                if mode == 'Создать новую':
                    if not delete_res(self.ui3.tbl_options_for_erp.item(0 ,1).text()):
                        return
                elif mode == 'Перезаполнить':
                    code_old_res = self.ui3.tbl_options_for_erp.item(1 ,1).text()
                    if not clear_res(code_old_res):
                        return
            data_answ = data_to_ERP.send()
            #data_answ = send(data_to_ERP)
            if not data_answ:
                return
            code = data_answ['Код']

        name_res = self.ui3.tbl_options_for_erp.item(0, 1).text()
        if code:
            link = data_answ['Ссылка']
            #CQT.msgbox(f'Успешно создана Код "{code}"',time_life=3)
            self.ui3.tbl_options_for_erp.item(0, 3).setText('')
            self.ui3.tbl_options_for_erp.item(1, 1).setText(str(code))
            connection_kpl_state = f'Ресурсная НЕ записана в КПЛ'
            if self.res_obj.is_tkp and self.save_as_predv_res: #08.04.25
                self.write_data_res_analogue(self.res_obj.res,name_res,self.res_obj.num_kpl,self.res_obj.s_num_tkp)
                if self.res_obj.num_kpl and self.res_obj.s_num_tkp and self.res_obj.num_kpl != 3345:
                    self.write_name_analogue_into_kplan(name_res, self.res_obj.num_kpl)
                    connection_kpl_state = f'Записана `Предв_спецификация_ЕРП` в КПЛ №{self.res_obj.num_kpl}'
            if self.ui3.tbl_options_for_erp.cellWidget(8,1).isChecked():
                self.write_name_main_res_into_kplan(name_res, self.res_obj.num_kpl,code)
                connection_kpl_state = f'Записана `Спецификация_код_ЕРП` в КПЛ №{self.res_obj.num_kpl}'
            # if self.save_as_predv_res and self.res_obj.is_tkp and self.res_obj.num_kpl and self.res_obj.s_num_tkp and self.res_obj.num_kpl != 3345:
            CQT.msgboxg_get_table_ok_inf(self, 'Результат', [{'Поле': 'Ссылка', 'Значение': '|'.join([link,'Открыть в 1С'])},
                                                             {'Поле': 'Код', 'Значение': code},
                                                             {'Поле': 'ИмяРесурсной', 'Значение': name_res},
                                                             {'Поле': 'Связь с КПЛ', 'Значение': connection_kpl_state},
                                                             ],load_links=True,styleSheet=CQT.ERP_CSS)
            if not USRCNF.Config.user_config.is_developer: #26.08.25
                self.close()

    @CQT.onerror #08.04.25
    def write_data_res_analogue(self, rez,name_res,num_kpl,s_num_tkp=None,*args):
        res_pickle = F.to_binary_pickle(rez)
        predv_sp = CSQ.custom_request_c(self.db_resxml, f"""SELECT Имя FROM predv_res WHERE Имя = ?;""",
                                        list_of_lists_c=(name_res,))
        if predv_sp == False or predv_sp == None:
            CQT.msgbox(f'Ошибка SELECT Имя FROM predv_res')
            return
        if len(predv_sp) == 1:
            CSQ.custom_request_c(self.db_resxml, f"""INSERT INTO predv_res(Имя,data) VALUES (?,?);""",
                                 list_of_lists_c=[[name_res, res_pickle]])
        else:
            CSQ.custom_request_c(self.db_resxml, f"""UPDATE predv_res SET data = ? WHERE Имя = ?;""",
                                 list_of_lists_c=[[res_pickle, name_res]])
        CSQ.custom_request_c(self.db_dse, f"""UPDATE tkp SET (name_res,date_res) = (?,?) WHERE s_nom = ?""",
                             list_of_lists_c=[[name_res, F.now(), s_num_tkp]])

    @CQT.onerror
    def write_name_analogue_into_kplan(self, name_res,num_kpl, *args):
        res = CSQ.custom_request_c(self.db_kplan,
                             f"""UPDATE пл_топ SET Предв_спецификация_ЕРП = "{name_res}" WHERE НомПл = {num_kpl};""")#self.dict_cur_poz_cr_mk['Пномер']
    @CQT.onerror
    def write_name_main_res_into_kplan(self, name_res,num_kpl,code, *args):
        res = CSQ.custom_request_c(self.db_kplan,
                             f"""UPDATE пл_топ SET (Спецификация_ЕРП, Спецификация_код_ЕРП) 
                                = ("{name_res}", "{code}") WHERE НомПл = {num_kpl};""")



