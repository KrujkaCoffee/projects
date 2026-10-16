from __future__ import annotations
from functools import wraps
import json

if __name__ == "__main__":
    import sys
    import os
    os.environ['MODIFIED_CFG'] = '{"BD_users": "SRV:BD_users.db"}'


import copy
from functools import partial
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_tree_widget  as CTREE
from project_cust_38.sub_mes.product_structure_constructor.dataClasses import data_app as DTCLS
from project_cust_38.sub_mes.product_structure_constructor.dataClasses import ReferenceStore as STORE_C
import project_cust_38.sub_mes.product_structure_constructor.constructor_ui as constructor_ui
import project_cust_38.sub_mes.product_structure_constructor.sub_classes as CLSS

if DTCLS.CONFIG.user_config.is_developer:
    if CQT.convert_UI_into_PY_c(str(F.Cust_path(constructor_ui)) + F.sep()):
        import importlib
        importlib.reload(constructor_ui)

import project_cust_38.sub_mes.product_structure_constructor.connects as _con

CFGo = CFG.Config

from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    pass

STORE = STORE_C()
STORE.load_data_reference()



def marks_dirty(arg=None):
        """
        Универсальный декоратор.

        @marks_dirty
        def f(...): ...            # arg = сама функция -> ставим dirty
        @marks_dirty(True)
        def f(...): ...            # явно ставим dirty
        @marks_dirty(False)
        def f(...): ...            # снимаем dirty (после сохранения)
        """
        # случай @marks_dirty без скобок
        if callable(arg):
            func = arg
            return _wrap(func, dirty=True)

        # случай @marks_dirty(True/False)
        dirty = bool(arg) if arg is not None else True

        def deco(func):
            return _wrap(func, dirty=dirty)

        return deco

def _wrap(func, dirty: bool):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is False:
                return result
            DTCLS.opened_file_path.set_dirty(dirty)
            return result

        return wrapper

class StartMode():
    def __init__(self,name:str,text:str,fl_editable:bool):
        self.name = name
        self.text = text
        self.fl_editable=fl_editable

    @property
    def editable(self):
        return self.fl_editable

class StartModes():
    editabele:StartMode = StartMode('editabele','Редактирование',True)
    readonly:StartMode = StartMode('readonly','Просмотр',False)
class CentralWindow(CQT.QtWidgets.QMainWindow):


    #=============signal====================
    to_mk_ready: CQT.QtCore.pyqtSignal = CQT.QtCore.pyqtSignal(CQT.QtWidgets.QMainWindow,list)
    #def on_data_from_child(sub_app,data, *args):
    #    print('Получены данные')
    #sub_window = CentralWindow(None)
    #sub_window.to_mk_ready.connect(on_data_from_child)
    #sub_window.showMaximized()
    #def bnt_close(self):
    #    self.to_mk_ready.emit(self ,self.data_for_mk)
    #=========================================

    def __init__(self,app_self=None,mode:StartMode=StartModes.readonly):
        """
        BD_users -> app_config -> new_sub_app				new_sub_app.py	0
        :param app_self:
        """

        super(CentralWindow, self).__init__()
        self.VER:str= '0.1'
        self.ui = constructor_ui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_self = app_self
        DTCLS.app_self = app_self
        DTCLS.sub_self = self
        self.DTCLS = DTCLS
        DTCLS.mode = mode
        if DTCLS.app_self:
             self.setStyleSheet(DTCLS.app_self.styleSheet())
        else:
             self._load_free_css()

        self.data_for_mk:list[dict]|None = None


        self.setAttribute(CQT.Qt.WA_DeleteOnClose)
        CQT.connect_to_resize(self, CMS.tmp_dir())

        CQT.load_icons(self, 26, dir=str(F.Cust_path(constructor_ui)) + F.sep() + 'icons' + F.sep())
        self.setWindowModality(CQT.Qt.ApplicationModal)
        self.apply_subj()

        _con.load_connects(self)
        self.fill_docs()

    def _____________service_______________(self):pass

    def some_action(self):
        self.data_ready.emit({"result": 42})
    def keyReleaseEvent(self, e):
        key = e.key()
        mod = e.modifiers()
        _con.key_release_event(self, key, mod)

    def eventFilter(self, obj, event):
        # noinspection PyUnresolvedReferences
        if isinstance(obj, CQT.QtWidgets.QDockWidget) and event.type() == CQT.QtCore.QEvent.MouseButtonDblClick:
            # noinspection PyUnresolvedReferences
            if event.button() == CQT.QtCore.Qt.LeftButton:
                obj.setFloating(True)
                screen = CQT.QtWidgets.QApplication.primaryScreen()
                rect = screen.availableGeometry()
                if obj.geometry() == rect:
                    # Уже развернут — вернуть нормальный размер
                    # self.ui.dockNavigator.showNormal()
                    obj.showMaximized()
                else:
                    # Растянуть ровно по рабочей области (без панели задач)
                    obj.setGeometry(rect)
                    obj.show()
                return True

        if isinstance(obj, CQT.QtWidgets.QDockWidget) and event.type() == CQT.QtCore.QEvent.Resize:
            if CQT.QtWidgets.QApplication.mouseButtons() == CQT.QtCore.Qt.LeftButton:
                key = f'QDockWidget:{obj.objectName()}'
                target = getattr(self, '_resize_targets', {}).get(key)
                if target is not None:
                    CQT._on_resize_event(self, target)
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        #before_close(self)
        CFG.BaseSubWindow.close_in_event(self)
        event.accept()

    @classmethod
    def start_sub_app(cls,app_self)->'CentralWindow':
        window_manual = CentralWindow(app_self)
        window_manual.showMaximized()
        return window_manual
    
    def _____________sub__________________(self):
        pass

    def init_data(self):


        DTCLS.init_data()
        DTCLS.spec_schema = CLSS.SpecSchema(self.ui.tree_of_product)
        DTCLS.types_nomenclature = CLSS.TypesNomenclature()
        DTCLS.opened_file_path = CLSS.OpenedFile(self.ui.lbl_curr_file)
        DTCLS.orders_docs = CLSS.OrdersDocs()
        CQT.QtCore.QTimer.singleShot(50, lambda: CQT.load_resize_splitters(self, CMS.tmp_dir()))
        pass


    def _load_free_css(self):
        theme_path = F.sep().join([F.path_to_execut_file_c(), 'css'])
        CQT.apply_css_theme(self, theme_path + F.sep()  + 'metallic.qss')

    def apply_subj(self,subject_mode:str=None):
        if subject_mode is None:
            subject_mode_str = ''
        else:
            subject_mode_str = f' - {subject_mode}'
        self.NAME_MODULE_BASE = f'Конструктор структуры изделия v{self.VER}{subject_mode_str}'
        DTCLS.CONFIG.user_config.set_sub_window_title(self)
        # CONNECTS
        _con.prepare_ui(self)
        if self.app_self:
            CFG.BaseSubWindow.window_binding(self, F.name_of_caller_file(), self.app_self)
            print(f'add sub {CFG.Config.window_manager.active} into window_manager')
        else:
            CFG.BaseSubWindow.set_as_root(self)


        self.init_data()
        
        #self.test_fill_tbl()

    def update_table(self):
        if CQT.QtWidgets.QApplication.focusWidget() is self.ui.tbl_cards:
            self.fill_docs()


    def ___________CALCS_____________(self):pass

    @staticmethod
    def _parse_num(s) -> float:
        """'5389,45' / '5 389.45' -> float. Пусто/мусор -> 0.0"""
        if s is None:
            return 0.0
        txt = str(s).strip().replace(" ", "").replace("\u00a0", "")
        if not txt:
            return 0.0
        txt = txt.replace(",", ".")
        try:
            return float(txt)
        except ValueError:
            return 0.0

    @staticmethod
    def _fmt_num(v: float) -> str:
        """float -> '5389,45' (русская локаль, 2 знака)."""
        return f"{v:.2f}".replace(".", ",")

    @staticmethod
    def _fmt_qty(v: float) -> str:
        return str(round(v,2))

    # ---------------- recalc: weights ----------------

    def _recalc_mass_item(self, tree) -> None:
        def rec(item,parent_qty: float = 1.0) -> None:
            d = CLSS.Dse_row(item)
            qty = self._parse_num(d.values.get("qty", ""))
            mass_one = self._parse_num(d.values.get("mass_one", ""))
            div_qty = qty * parent_qty
            d.set("_qty_on_item", self._fmt_qty(div_qty))
            # 1) сначала дети
            for i in range(item.childCount()):
                rec(item.child(i), div_qty)


            if item.childCount() > 0:
                d.set("mass_item", "")
            else:

                d.set("mass_item", self._fmt_qty(div_qty*mass_one))


        for i in range(tree.topLevelItemCount()):
            d = CLSS.Dse_row(tree.topLevelItem(i))
            qty = self._parse_num(d.values.get("qty", ""))
            rec(tree.topLevelItem(i),qty)

    def _recalc_weights(self, tree) -> None:
        """
        Рекурсивный bottom-up за один проход:
            лист:    mass_one  — как введено
                     mass_total = mass_one × qty
            сборка:  mass_one  = Σ(mass_total детей)
                     mass_total = mass_one сборки × qty сборки
        """

        def rec(item) -> None:
            # 1) сначала дети
            for i in range(item.childCount()):
                rec(item.child(i))

            d = CLSS.Dse_row(item)
            qty = self._parse_num(d.values.get("qty", ""))

            if item.childCount() > 0:
                total = 0.0
                for i in range(item.childCount()):
                    cd = CLSS.Dse_row(item.child(i))
                    total += self._parse_num(cd.values.get("mass_total", ""))
                d.set("mass_one", self._fmt_qty(total))
                mass_one = total
            else:
                mass_one = self._parse_num(d.values.get("mass_one", ""))

            d.set("mass_total", self._fmt_qty(mass_one * qty))

        for i in range(tree.topLevelItemCount()):
            rec(tree.topLevelItem(i))
    # ---------------- recalc: mass_one ----------------

    def _recalc_mass_one(self, tree) -> None:
        """
        Снизу вверх: масса1 сборки = сумма масса1 её детей.
        Листья (без детей) не трогаем — читаем как есть.
        """

        def recalc(item) -> float:
            if item.childCount() == 0:
                d = CLSS.Dse_row(item)
                return self._parse_num(d.values.get("mass_one", ""))

            total = 0.0
            for i in range(item.childCount()):
                total += recalc(item.child(i))

            d = CLSS.Dse_row(item)
            d.set("mass_one", self._fmt_qty(total))
            return total

        for i in range(tree.topLevelItemCount()):
            recalc(tree.topLevelItem(i))

    def _recalc_qty_on_struct(self, tree) -> None:
        """
        _qty_on_struct — сумма _qty_on_item всех вхождений с одинаковым
        Обозначением (rollup по всей структуре).
        Пишется в каждую строку группы — чтобы правая панель и dump сразу видели.
        """
        sum_by_desig: dict[str, float] = {}

        def collect(item) -> None:
            d = CLSS.Dse_row(item)
            desig = str(d.values.get("designation", "") or "")
            if desig:
                q = self._parse_num(d.values.get("_qty_on_item", ""))
                sum_by_desig[desig] = sum_by_desig.get(desig, 0.0) + q
            for i in range(item.childCount()):
                collect(item.child(i))

        for i in range(tree.topLevelItemCount()):
            collect(tree.topLevelItem(i))

        def apply(item) -> None:
            d = CLSS.Dse_row(item)
            desig = str(d.values.get("designation", "") or "")
            val = sum_by_desig.get(desig, 0.0) if desig else 0.0
            d.set("_qty_on_struct", self._fmt_qty(val))
            for i in range(item.childCount()):
                apply(item.child(i))

        for i in range(tree.topLevelItemCount()):
            apply(tree.topLevelItem(i))


    def _____________________________(self):pass

    @staticmethod
    def fnc_oform_tree(item: CLSS.CTREE.ExtTreeWidgetItem, lvl, *args):
        val_str_pki = item.get_value_by_field('_pki')
        item.set_value_by_field('ПКИ', '', '')
        if F.is_numeric_positive_integer(val_str_pki):
            if F.boolm(val_str_pki):
                item.set_value_by_field('ПКИ', CLSS.Nomenclature.EMO_PKI, '')

    def recalc_tree(self):
        DTCLS.spec_schema.oform_tree(self.fnc_oform_tree)
        self._recalc_weights(self.ui.tree_of_product)
        self._recalc_mass_item(self.ui.tree_of_product)
        self._recalc_qty_on_struct(self.ui.tree_of_product)
        self.refresh_pos_user_idx()

    def refresh_pos_user_idx(self) -> None:
        """
        Проставить колонку "№ п.п" во всём дереве по позиции в иерархии.
        Схема нумерации: 1, 1.1, 1.1.1, 1.1.2, 1.2, 2, 2.1, ...
        """
        tree = self.ui.tree_of_product
        pos_header = CLSS.SpecSchema.DICT_ALIASES["pos"]
        col = None
        header = tree.headerItem()
        for c in range(tree.columnCount()):
            if header.text(c) == pos_header:
                col = c
                break
        if col is None:
            return

        def walk(parent, prefix: str):
            count = parent.childCount() if parent else tree.topLevelItemCount()
            for i in range(count):
                item = parent.child(i) if parent else tree.topLevelItem(i)
                num = f"{prefix}.{i + 1}" if prefix else str(i + 1)
                item.setText(col, num)
                walk(item, num)

        walk(None, "")

    def fill_docs(self):

        DTCLS.orders_docs.update()
        template = DTCLS.orders_docs.list_orders_docs
        CQT.fill_wtabl(template,self.ui.tbl_cards,styleSheet=CQT.MES_EDIT_CSS ,selectionBehavior=CQT.SelectionBehaviors.SelectRows,
        selectionMode=CQT.SelectionModes.SingleSelection,aliases_header=DTCLS.orders_docs.DICT_ALIASES,
                       floating_btn_mngr=CMS.register_floating_btn_threads(
                           'uuiD_proc',''
                                       'Конструктор структур-процессы',
                                        ['iD_proc','iD_card']))
        t = CQT.TableContext(self.ui.tbl_cards)
        t.hide_if_not_dev(CFG,forced_text=True)
        for text,i in t.nft.items():
            name = t.name_by_idx(i)
            if 'карточк' in text:
                t.set_color_background(233,244,244,col_name=name)
            elif 'процесс' in text:
                t.set_color_background(244,244,233,col_name=name)

        CQT.fill_filtr_c(self,self.ui.tbl_cards_filtr,self.ui.tbl_cards,show_header=False,hidden_scroll=True)


    def test_fill_tbl(self):
        pathf = fr'C:\\Users\\a.belyakov\\Work folders\\Desktop\\временная\\test_struct.pickle'
        self.load_struct_f(pathf)


    def ____________BTNS_________________________________(self):pass

    @marks_dirty
    def _on_tree_drop(sub_self, parent_item, dropped_item,*args):
        """
           Хук успешного drag&drop.
           sub_self    — CentralWindow (проброшен через partial)
           parent_item — родитель после вставки (None если top-level)
           dropped_item — ExtTreeWidgetItem, вставленный элемент
           """
        tree = sub_self.ui.tree_of_product
        #sub_self.recalc_tree(tree)

        # откладываем на следующий тик — иначе Qt перетрёт перерисовку своим drag-render
        CQT.QtCore.QTimer.singleShot(0, lambda: sub_self.recalc_tree())
        CQT.QtCore.QTimer.singleShot(0, tree.viewport().update)

        dse = CLSS.Dse_row(dropped_item)
        print(
            f"[DROP] pos={dse.get('pos')!r} "
            f"desig={dse.get('designation')!r} "
            f"parent={parent_item.text(1) if parent_item else None!r}"
        )

    @marks_dirty
    def duplicate_row(self,*args):
        """Кнопка/шорткат: дублировать выбранную строку."""
        item = DTCLS.spec_schema.duplicate_row_silent()
        if item is None:
            return
        tree = self.ui.tree_of_product
        tree.setCurrentItem(item)
        tree.scrollToItem(item, tree.EnsureVisible)
        self.recalc_tree()
        tree.viewport().update()

    @marks_dirty
    def del_row(self,*args):
        """Кнопка/шорткат: удалить выбранную с подтверждением."""
        tree = self.ui.tree_of_product
        cur = tree.currentItem()
        if cur is None:
            CQT.msgbox("Строка не выбрана.")
            return

        dse = CLSS.Dse_row(cur)
        name = dse.get("designation") or dse.get("name") or "(без имени)"
        child_cnt = cur.childCount()

        msg = f"Удалить строку?\n\n{name}"
        if child_cnt:
            msg += f"\n\nВместе с ней будет удалено вложенных строк: {child_cnt}."

        if not CQT.msgboxgYN(msg):
            return

        if not DTCLS.spec_schema.remove_cur_row_silent():
            return

        self.recalc_tree()
        tree.viewport().update()

    @marks_dirty
    def new_row(self, *args):
        """
        Кнопка/шорткат «Новая ДСЕ».
        - Есть текущая строка → добавляем дочернюю (CHILD).
        - Ничего не выбрано, дерево пустое → создаём корневую (изделие).
        - Ничего не выбрано, дерево непустое → не даём создать второй корень.
        """
        tree = self.ui.tree_of_product

        cur = tree.currentItem()

        if DTCLS.spec_schema.is_new:

            # пустое дерево → создаём корень
            item = DTCLS.spec_schema.add_row_silent(CLSS.AddMode.SIBLING)
            if item is None:
                return False
        else:

            if cur is None:
                # дерево непустое, но не выбрана строка — не плодим корни
                CQT.msgbox("Выберите строку, к которой добавить дочернюю.")
                return False
            else:
                item = DTCLS.spec_schema.add_row_silent(CLSS.AddMode.CHILD)
                if item is None:
                    return False

        tree.setCurrentItem(item)
        tree.scrollToItem(item, tree.EnsureVisible)
        self.recalc_tree()
        tree.viewport().update()
        return True


    def load_struct_f(self,pathf:str|None|CLSS.CardDocs=None,new:bool=False,*args):




        if DTCLS.opened_file_path.is_dirty:
            if CQT.msgboxgYN("Имеются несохраненные изменения.\n\nСохранить?"):
              if not self.save_current_struct_f():
                  return
        if new:
            data = {'sig':DTCLS.spec_schema.signature(),'data':[]}
        else:
            if pathf is None:
                base_path = CMS.load_tmp_path('ps_constructor_tree')
                pathf = CQT.f_dialog_name(self,'Загрузить структуру',base_path,'*.pickle')
                if pathf == '' or pathf == '.':
                    return

            if isinstance(pathf,CLSS.CardDocs):
                data =  pathf.get_structure()
            if isinstance(pathf,str):
                data = F.load_file_pickle(pathf)

        succ, errs=DTCLS.spec_schema.load_tree(data)
        if not succ:
            CQT.msgboxg_get_table_ok_inf(self,'Ошибка загрузки',[errs],use_first_row_as_header=False,
                                         print_hat=False, show_filtr=False, styleSheet=CQT.MES_CSS)
            return
        DTCLS.opened_file_path.set(pathf)

        CQT.load_column_widths(self, self.ui.tree_of_product, CQT.qt_tmp_dir())
        _con.set_tree_readonly(self.ui.tree_of_product, not DTCLS.mode.editable)

        self.recalc_tree()

        DTCLS.spec_schema.expand_all()


    def save_current_struct_f(self,*args):
        if not DTCLS.opened_file_path.is_opened:
            return self.save_struct_f()
        return self.save_struct_f(DTCLS.opened_file_path.pathf)

    @marks_dirty(False)
    def save_struct_f(self,pathf:str|None|CLSS.CardDocs=None,*args)->bool:

        if pathf is None:
            base_path = CMS.load_tmp_path('ps_constructor_tree')
            pathf = CQT.f_dialog_save(self, "Сохранить структуру", base_path, "*.pickle")
            if pathf == '' or pathf == '.':
                return False


        data = DTCLS.spec_schema.save_tree()

        if isinstance(pathf,CLSS.CardDocs):
            comment= ''
            succ, comment_rez = CQT.get_dialog_choose_text(self,'Комментарий',start_text='')
            if succ:
                comment= comment_rez
            return pathf.save_structure(data,CFGo.user_config.User.ID_ФизЛица,comment)


        if isinstance(pathf,str):
            CMS.save_tmp_path('ps_constructor_tree',pathf,True)
            F.save_file_pickle(pathf,data)
            return True

    def oform_tbl_row(self,t:CQT.TableContext):

        def fill_ref_nomen(t:CQT.TableContext,ref,code_erp):
            row_ref_nomen = t.find_row({'_name': '_nomenclature_ref'}, True)
            row_ref_nomen.set_value('Значение', ref)
            row_ref_nomen_code = t.find_row({'_name': 'code_erp'}, True)
            row_ref_nomen_code.set_value('Значение', code_erp)

        def fill_pki(t:CQT.TableContext,pki_val:str|int|bool='',only_data=True):
            if isinstance(pki_val,str):
                if F.is_numeric(pki_val):
                    pki_val = F.boolm(pki_val)
                else:
                    pki_val= False if pki_val == '' else True
            fl_pki = 1 if pki_val  else 0

            row_pki_ui = t.find_row({'_name': 'pki_ui'}, True)
            if only_data:

                row_pki_ui.set_value('Значение', str(fl_pki))
                row_pki = t.find_row({'_name': '_pki'},True)
                row_pki.set_value('Значение', str(fl_pki))
            else:
                switcher_w: CQT.Check_box_switcher | None = row_pki_ui.widget('Значение', type_w=CQT.Check_box_switcher)
                if switcher_w:
                    switcher_w.setChecked(fl_pki)

        def fnc_select_nomenclature(lbl_o:CQT.InteractiveLabelInstance,self_app:CentralWindow,i:int,j:int,addit_data,*args):
            row:CQT.TableRow = addit_data[0]
            t:CQT.TableContext = addit_data[1]

            def fnc_oform_types_nomen(tbl:CQT.QtWidgets.QtableWidget,*args):
                t = CQT.TableContext(tbl)
                t.hide_if_not_dev(CFGo)
                last_ref = DTCLS.types_nomenclature.last_type_nomen
                if last_ref:
                    row = t.find_row({'_ref': last_ref},True)
                    t.set_selected_cell(row,'Наименование')
                pass

            rez = CQT.msgboxg_get_table(self,'Выбор номенклатуры',DTCLS.types_nomenclature.data,styleSheet=CQT.ERP_CSS,
                                  selection_from_tbl=True,selectRows=True,ExtendedSelection=False,func_oform_tbl=fnc_oform_types_nomen)

            if not rez:
                return
            DTCLS.types_nomenclature.last_type_nomen = rez['_ref']
            refs_types_nomen = DTCLS.types_nomenclature.get_set_child_refs(rez['_ref'])


            def fnc_oform_nomen(tbl:CQT.QtWidgets.QtableWidget,*args):
                t = CQT.TableContext(tbl)
                t.hide_if_not_dev(CFGo)
                pass


            rez = CQT.msgboxg_get_table(self, 'Выбор номенклатуры', CLSS.Nomenclature(refs_types_nomen).data,
                                        styleSheet=CQT.ERP_CSS,
                                        selection_from_tbl=True, selectRows=True, ExtendedSelection=False,
                                        func_oform_tbl=fnc_oform_nomen)

            if not rez:
                return
            lbl_o.set_text(rez['Наименование'])
            row.set_value('Значение', rez['Наименование'])
            fill_ref_nomen(t,rez['_ref'],rez['Код'])
            fill_pki(t,rez['ПКИ'],only_data=False)

        def fnc_clear_nomenclature(lbl_o:CQT.InteractiveLabelInstance,self_app:CentralWindow,i:int,j:int,addit_data,*args):
            row:CQT.TableRow = addit_data[0]
            t:CQT.TableContext = addit_data[1]
            lbl_o.set_text('')
            row.set_value('Значение', '')
            fill_ref_nomen(t, '','')
            fill_pki(t,only_data=False)

        def fnc_switch_pki(tbl:CQT.QtWidgets.QtableWidget,val:bool,i,j,*args):
            t = CQT.TableContext(tbl)
            fill_pki(t, str(int(val)),only_data=True)


        t.hide_if_not_dev(CFGo)


        for row in t.rows():
            name_row = row.value('_name')
            val_row = row.value('Значение')
            row.set_font_format(col_name='Параметр', bold=True)
            if name_row in DTCLS.spec_schema.USER_EDITABLE_FIELDS and DTCLS.mode.editable:
                row.set_editable('Значение')
            else:
                row.set_font_format(col_name= 'Значение',italic=True)
                row.set_color_font(*CMS.Colors.dull_black.rgb,col_name='Значение')

            if name_row == 'pki_ui' and DTCLS.mode.editable:
                val_pki = t.find_row({'_name': '_pki'}, True).value('Значение')
                CQT.add_check_box_switcher(t.tbl, row.i, t.nf['Значение'], int(val_pki), fnc_switch_pki)

            if name_row == 'nomenclature' and DTCLS.mode.editable:

                widg = CQT.add_interactive_label(t.tbl, row.i, t.nf['Значение'], val_row,
                                                 parent_self=self,make_label_opacity=True)

                widg.add_button('', 'Выбор',
                                fnc_select_nomenclature,
                                cell_val=(row,t), img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                      'icons', 'select_from']))
                widg.add_button('', 'Очистить',
                                fnc_clear_nomenclature,
                                cell_val=(row,t), img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                      'icons', 'close']))


            if name_row.startswith('_'):
                if CFGo.user_config.is_developer:
                    row.set_color_font(*CMS.Colors.dull_black.rgb)
                else:
                    row.hide()


    def select_tree_row(self, current, prev):
        """Триггер смены текущей строки дерева (мышь или клавиатура)."""
        if current is None:
            # очистка выделения — позже тут будем чистить tbl_row
            return
        dse = CLSS.Dse_row(current)
        CQT.fill_wtabl(dse.template(), self.ui.tbl_row,styleSheet=CQT.MES_EDIT_CSS,auto_type=False)
        t = CQT.TableContext(self.ui.tbl_row)
        self.oform_tbl_row(t)

    @marks_dirty(True)
    def apply_changes_row(self,*args):
        tree = self.ui.tree_of_product
        current = tree.currentItem()
        if current is None:
            return
        data = CQT.list_from_wtabl_c(self.ui.tbl_row,rez_dict=True)
        dse = CLSS.Dse_row(current)
        changed = dse.apply_template(data)
        if changed:
            self.recalc_tree()
            tree.viewport().update()
            CQT.msgbox('Изменения применены',time_life=0.4)
            return True
        return False

    def btn_save_card_struct(self):
        t = CQT.TableContext(self.ui.tbl_cards)
        row = t.current_row()
        if row.no_selection:
            return
        uuid_card = row.value('uuiD_card')
        card_o = DTCLS.orders_docs.get_card(uuid_card)

        if not self.save_struct_f(card_o):
            CQT.msgbox(f'Ошибка сохранения структуры в карточку {card_o}')
        CQT.msgbox(f'Структура сохранена в карточку {card_o}',time_life=0.5)


    def btn_load_card_struct(self):

        def fnc_oform(tbl:CQT.QtWidgets.QTableWidget,*args):
            t = CQT.TableContext(tbl)
            t.hide_if_not_dev(CFG,forced_text=True)


        t = CQT.TableContext(self.ui.tbl_cards)
        row = t.current_row()
        if row.no_selection:
            return
        uuid_card = row.value('uuiD_card')
        card_o = DTCLS.orders_docs.get_card(uuid_card)

        tmplate,aliases = card_o.get_template_versions()
        if not tmplate:
            if not CQT.msgboxgYN(f'В карточке {card_o} не найдена структура!\nСоздать новую?'):
                return
            else:
                self.load_struct_f(new=True)
            return

        rez = CQT.msgboxg_get_table(self,'Выберите структуру',tmplate,'Выбор',styleSheet=CQT.MES_CSS,
                                    selectRows=True,ExtendedSelection=False,selection_from_tbl=True,
                                    aliases_header=aliases,func_oform_tbl=fnc_oform,
                                    floating_btn_mngr=CMS.register_floating_btn_threads(
                                        'uuid_card','Конструктор - Структура в карточке проекта',
                                        ['id_card','rev_file']
                                    ))
        if not rez:
            return
        id_rev = int(rez['rev_file'])

        card_o.set_current_rev(id_rev)
        self.load_struct_f(card_o)


    def ________________ui_________________(self):pass

    def btn_get_to_mk(self):

        self.data_for_mk = DTCLS.spec_schema.dump_tree()
        self.to_mk_ready.emit(self ,self.data_for_mk)
        self.close()


    def ________________ui_________________(self):pass

    def toggle_dock_floating(self) -> None:
        dock: QtWidgets.QDockWidget = self.ui.dockw_cards

        dock.setFloating(not dock.isFloating())

    def toggle_dock_fullscreen(self) -> None:
        """
        Развернуть плавающий QDockWidget на всю рабочую область экрана.
        Повторный вызов — вернуть к обычному размеру плавающего окна.
        """
        dock: QtWidgets.QDockWidget = self.ui.dockw_cards
        if not dock.isFloating():
            return

        # запоминаем «нормальный» размер — чтобы уметь вернуться
        if not hasattr(dock, "_pre_fs_geometry") or dock._pre_fs_geometry is None:
            dock._pre_fs_geometry = dock.geometry()

        screen = CQT.QApplication.screenAt(dock.geometry().center()) \
                 or CQT.QApplication.primaryScreen()
        rect = screen.availableGeometry()  # без панели задач

        if dock.geometry() == rect:
            # уже развёрнут — восстановить
            if dock._pre_fs_geometry is not None:
                dock.setGeometry(dock._pre_fs_geometry)
                dock._pre_fs_geometry = None
        else:
            dock._pre_fs_geometry = dock.geometry()
            dock.setGeometry(rect)
            dock.show()
            dock.raise_()

if __name__ == "__main__":

    def on_data_from_child(data,*args):
        print('Получены данные')

    from project_cust_38.Cust_application import install_crash_guard, SafeApplication
    app = SafeApplication(sys.argv)
    CQT.QtWinExtras.QtWin.setCurrentProcessExplicitAppUserModelID(
        f'Powerz.BAG.SustControlWork.0.0.0 {F.name_of_caller_file()}')
    app.setWindowIcon(CQT.QtGui.QIcon(os.path.join(F.path_to_caller_file_c(False), "icons", "icon.png")))
    install_crash_guard(app, app_name='',user_name='', log_qt_warnings=False,log_qt_debug_info=False, enable_native_fault_handler=False)
    sub_window = CentralWindow(None,StartModes.editabele)
    sub_window.to_mk_ready.connect(on_data_from_child)
    sub_window.showMaximized()

    sys.exit(app.exec())
