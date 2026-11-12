from project_cust_38 import Cust_Qt as CQT
from dataClass import data_app as DTCLS
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS


def filling_factory_sets()->list[dict]:
    class SimpClsRow_factory_sets(F._SimpMeta):
        id_dse: int
        name_dse: str
        id_oper: str
        oper_name: str
        to_select_fsets: int
        select_all: str

    def oform_tbl_select_sets(tbl :CQT.QTableWidget ,*args):


        def toggle_all_not_checked(row: CQT.TableRow, block: bool = True):
            for clmn, j in row.nf.items():
                if not F.is_numeric(clmn):
                    continue
                widget: CQT.QtWidgets.QCheckBox | None = row.widget(clmn, CQT.QtWidgets.QCheckBox)
                if widget is None:
                    continue
                if not widget.isChecked():
                    widget.setEnabled(not block)

        def fnc_select_all(t:CQT.TableContext,i:int,clmn_name:str,*args):
            def is_exist_selected(row:CQT.TableRow)->bool:
                for clmn_name in t.nf.keys():
                    if not F.is_numeric(clmn):
                        continue
                    chk_widget = row.widget(clmn_name, CQT.QtWidgets.QCheckBox)
                    if chk_widget is None:
                        continue
                    if chk_widget.isChecked():
                        return True
                return False

            def set_unselect():
                for clmn_name in t.nf.keys():
                    if not F.is_numeric(clmn):
                        continue
                    chk_widget:CQT.QtWidgets.QCheckBox = row.widget(clmn_name, CQT.QtWidgets.QCheckBox)
                    if chk_widget is None:
                        continue
                    if chk_widget.isChecked():
                        chk_widget.blockSignals(True)
                        chk_widget.setChecked(False)
                        chk_widget.blockSignals(False)
                return False

            def select_in_order(to_select_fsets:int):
                selected_fsets = 0
                for clmn_name in t.nf.keys():
                    if selected_fsets == to_select_fsets:
                        return

                    if not F.is_numeric(clmn):
                        continue
                    chk_widget:CQT.QtWidgets.QCheckBox = row.widget(clmn_name, CQT.QtWidgets.QCheckBox)
                    if chk_widget is None:
                        continue

                    chk_widget.blockSignals(True)
                    chk_widget.setChecked(True)
                    selected_fsets+=1
                    chk_widget.blockSignals(False)

            if 'shift' in CQT.get_key_modifiers(DTCLS.app_self):
                rows = [_ for _ in t.rows()]
            else:
                rows = [t.get_row(i)]
            if not rows:
                return
            fl_select_toglle = is_exist_selected(rows[0])
            for row in rows:

                to_select_fsets = int(row.value('to_select_fsets'))
                set_unselect()
                if fl_select_toglle:
                    toggle_all_not_checked(row, False)
                else:
                    select_in_order(to_select_fsets)
                    toggle_all_not_checked(row)

        def func_checked_row_col(t :CQT.TableContext ,val :bool ,i ,j):


            def calc_checked_count()->int:
                cnt_checked = 0
                for clmn, j in t.nf.items():
                    if not F.is_numeric(clmn):
                        continue
                    naryad = row.value(clmn)
                    if not naryad:
                        widget: CQT.QtWidgets.QCheckBox | None = row.widget(clmn, CQT.QtWidgets.QCheckBox)
                        if widget.isChecked():
                            cnt_checked += 1

                return cnt_checked

            # проверки
            # подсчет кол-ва по полю to_select_fsets
            # подсчет комплектов
            # подсчет незаполненных
            # 1. блокировка тех что не выброано - если кол-во уже исчерпано
            # 2. разблокировка тех что не выброано - если кол-во не исчерпано
            row = t.get_row(i)
            to_select_fsets = int(row.value('to_select_fsets'))

            cnt_checked = calc_checked_count()
            toggle_all_not_checked(row ,cnt_checked >= to_select_fsets)



        t = CQT.TableContext(tbl)

        t.add_column_events('select_all', on_double_click=fnc_select_all)

        for row in t.rows():
            id_dse = int(row.value('id_dse'))
            id_oper = row.value('id_oper')


            count_filled_fsets = len(DTCLS.current_factory_sets.get_factory_sets_by_dse_oper(id_dse, id_oper))


            to_select_fsets = int(row.value('to_select_fsets'))
            factory_sets_count = 0 if not to_select_fsets else to_select_fsets
            fl_full_set = False
            if factory_sets_count + count_filled_fsets == DTCLS.current_factory_sets.res.count:
                fl_full_set = True

            row.set_font_format(size=16, bold=True,col_name='select_all')

            for clmn, j in t.nf.items():
                if not F.is_numeric(clmn):
                    continue

                naryad = row.value(clmn)
                if naryad == '':
                    CQT.add_check_box(t.tbl ,row.i ,j ,val=fl_full_set ,conn_func_checked_row_col=func_checked_row_col,
                                      self_obj=t ,enabled=not fl_full_set)

        pass

    def fnc_check_select(btn: CQT.QtWidgets.QPushButton, dialog: CQT.Dialog_tbl, tbl: CQT.QtWidgets.QTableWidget):

        if dialog.is_btn_yes_role(btn):
            t = CQT.TableContext(tbl)
            for row in t.rows():

                to_select_fsets = int(row.value('to_select_fsets'))
                if not to_select_fsets:
                    continue
                selected_fsets = 0
                for clmn, j in t.nf.items():
                    if not F.is_numeric(clmn):
                        continue
                    check_box = row.widget(clmn, CQT.QtWidgets.QCheckBox)
                    if check_box is None:
                        continue
                    if check_box.isChecked():
                        selected_fsets += 1

                if selected_fsets != to_select_fsets:
                    CQT.msgbox(f'Не все ДСЕ распределены по комплектам.')
                    return

            dialog.accept()
        else:
            dialog.reject()

    def fnc_adjust_result(t:CQT.TableContext,*args):
        #factory_sets.add_new(param.ДСЕ_ID,param.Операции_номер,it.Пномер,id_factory_set)
        result = []
        for row in t.rows():

            to_select_fsets = int(row.value('to_select_fsets'))
            if not to_select_fsets:
                continue
            dse_id = int(row.value('id_dse'))
            oper_id = row.value('id_oper')

            for clmn, j in t.nf.items():
                if not F.is_numeric(clmn):
                    continue
                check_box = row.widget(clmn, CQT.QtWidgets.QCheckBox)
                if check_box is None:
                    continue
                if check_box.isChecked():
                    id_factory_set = int(clmn)
                    result.append({'dse_id': dse_id, 'oper_id': oper_id, 'id_factory': id_factory_set})
        return result

    def fnc_adjust_result_raw(data_o:list[SimpClsRow_factory_sets],*args):
        #factory_sets.add_new(param.ДСЕ_ID,param.Операции_номер,it.Пномер,id_factory_set)
        result = []
        for row in data_o:
            selected_fsets = 0
            to_select_fsets = int(row.to_select_fsets)
            if not to_select_fsets:
                continue
            dse_id = row.id_dse
            oper_id = row.id_oper
            for clmn, val in row.__dict__.items():
                if not F.is_numeric(clmn):
                    continue
                id_factory_set = int(clmn)
                result.append({'dse_id': dse_id, 'oper_id': oper_id, 'id_factory': id_factory_set})
                selected_fsets += 1
                if selected_fsets == to_select_fsets:
                    break
        return result

    factory_sets = CMS.FactorySets(DTCLS.app_self.glob_nom_mk)
    DTCLS.current_factory_sets = factory_sets
    data , dict_aliases = factory_sets.template_select()
    data_o = [SimpClsRow_factory_sets._from_dict(_) for _ in data]
    data = []
    t_mk = CQT.TableContext(DTCLS.app_self.ui.tbl_dse)
    dict_checked = dict()
    for row in t_mk.rows():
        if row.value('Чек'):
            count = int(row.value('В работу,шт.'))
            id_dse = int(row.value('ID'))
            id_oper = row.value('Ном_оп')
            dict_checked[(id_dse, id_oper)] = count

    fl_selection_required = False

    for row in data_o:
        id_dse = row.id_dse
        id_oper = row.id_oper
        key_row = (id_dse, id_oper)

        count_filled_fsets = len(DTCLS.current_factory_sets.get_factory_sets_by_dse_oper(id_dse, id_oper))

        dse_per_izd = DTCLS.current_factory_sets.dse_per_izd(id_dse)

        to_select_fsets = 0

        if key_row in dict_checked:
            to_select_dse = dict_checked[key_row]
            to_select_fsets = to_select_dse // dse_per_izd

        row.to_select_fsets = to_select_fsets

        factory_sets_count = 0 if not to_select_fsets else to_select_fsets

        fl_full_set = False
        if factory_sets_count + count_filled_fsets >= DTCLS.current_factory_sets.res.count:
            fl_full_set = True


        if not fl_full_set and factory_sets_count:
            fl_selection_required = True

        if factory_sets_count:
            data.append(row)



    if not fl_selection_required:
        selected_sets = fnc_adjust_result_raw(data)
    else:
        selected_sets = CQT.msgboxg_get_table(DTCLS.app_self ,'Выбор заводских комплектов' ,[_.to_dict() for _ in data] ,aliases_header=dict_aliases,
                              styleSheet=CQT.MES_CSS ,func_oform_tbl=oform_tbl_select_sets,
                              func_btn0=fnc_check_select,not_standart_close=True,func_validate_t=fnc_adjust_result)

        pass


    if not selected_sets:
        DTCLS.app_self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(DTCLS.app_self.ui.tabWidget_2, 'ДСЕ'))

    return selected_sets
