"""Regression cases for the bulk calculation path without a Windows Qt runtime."""

import importlib.util
import math
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


def load_module():
    qt = types.ModuleType('PyQt5')
    qt.QtCore = types.ModuleType('PyQt5.QtCore')
    qt.QtCore.Qt = types.SimpleNamespace(Checked=2)
    qt.QtWidgets = types.ModuleType('PyQt5.QtWidgets')
    qt.QtWidgets.QDialog = object
    funcs = types.ModuleType('project_cust_38.Cust_Functions')
    def valm(value):
        raw = str(value).strip().replace(',', '.')
        if not raw:
            return 0
        return float(raw) if '.' in raw or 'e' in raw.lower() else int(raw)
    funcs.valm = valm
    funcs.is_numeric = lambda value: is_numeric(value)
    funcs.scfg = lambda key: '10'
    funcs.existence_file_c = lambda path: True
    funcs.open_file_c = lambda *args: []
    config = types.ModuleType('project_cust_38.Cust_config')
    config.Config = types.SimpleNamespace(place=types.SimpleNamespace(limit_time_on_naryad=1000))
    opers = types.ModuleType('project_cust_38.operacii')
    opers.Data_oper_norm = types.SimpleNamespace(DICT_OPERS_CALC={})
    package = types.ModuleType('project_cust_38')
    package.Cust_Functions = funcs
    package.Cust_config = config
    package.operacii = opers
    imports = {'PyQt5': qt, 'PyQt5.QtCore': qt.QtCore, 'PyQt5.QtWidgets': qt.QtWidgets,
               'project_cust_38': package, 'project_cust_38.Cust_Functions': funcs,
               'project_cust_38.Cust_config': config, 'project_cust_38.operacii': opers}
    spec = importlib.util.spec_from_file_location('tehkart_bulk_under_test',
                                                 Path(__file__).parents[1] / 'tk_bulk.py')
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {**imports, spec.name: module}):
        spec.loader.exec_module(module)
    return module


def is_numeric(value):
    try:
        return math.isfinite(float(str(value).replace(',', '.')))
    except (TypeError, ValueError):
        return False


class Item:
    __hash__ = None

    def __init__(self, name, level, time='', setup='', raw='', old_dict='', children=()):
        self.cols = {0: name, 2: '005', 6: setup, 7: time, 10: '', 14: raw, 16: old_dict, 20: level}
        self.children = list(children)
        for child in self.children:
            child.parent_item = self

    def text(self, column):
        return self.cols.get(column, '')

    def setText(self, column, value):
        self.cols[column] = value

    def parent(self):
        return self.parent_item

    def childCount(self):
        return len(self.children)

    def child(self, index):
        return self.children[index]


class Registry:
    def __init__(self, approved=(), available=True, op_names=(), per_names=(), strict=False):
        self.approved = set(approved)
        self.available = available
        self.op_names = list(op_names)
        self.per_names = list(per_names)
        self.strict = strict

    def check_approved(self, *, operation, pereh=''):
        return (operation, pereh) in self.approved

    def check_op(self, operation, approved=False):
        return self.available and (operation, '') in self.approved

    def check_per(self, operation, pereh, approved=False):
        return self.available and (operation, pereh) in self.approved

    def get_op_params(self, operation):
        return self.op_names

    def get_per_params(self, operation, pereh):
        return self.per_names

    def get_pereh_txt_path(self, operation):
        return f'/mock/{operation}.txt'

    def check_strict_calc(self, *, operation):
        return self.strict


class BulkRecalcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bulk = load_module()

    def setUp(self):
        self.bulk.operacii.Data_oper_norm.DICT_OPERS_CALC = {}
        self.bulk.operacii.vremya_tsht = mock.Mock(return_value=0)
        self.bulk.operacii.vremya_tsht_perehodi = mock.Mock(return_value=0)
        self.bulk.operacii.materiali = mock.Mock(return_value=None)

    def window(self, name, vars='', tpz='2', poki=0, registry=None):
        return types.SimpleNamespace(place=types.SimpleNamespace(poki=poki),
                                     DICT_OPERS={name: {'Vars': vars, 'Tpz': tpz}},
                                     spis_op=[[name, 100, tpz, vars]],
                                     xl_formulas=registry or Registry())

    def test_z_notebook_without_parameter_column_is_informative(self):
        name = 'Комплектовочная'
        info = Item('Комплектовать ДСЕ на участке сборки', '2', time='—')
        op = Item(name, '1', time='0.2', setup='2', raw='2', children=[info])
        window = self.window(name, 'Масса,кг:int')
        with mock.patch.object(self.bulk.F, 'open_file_c', return_value=[[info.text(0), '239']]):
            self.assertIsNone(self.bulk.params_for_calc(window, info))
            self.bulk.operacii.vremya_tsht.return_value = 0.3
            changes, report = self.bulk.recalc_one(window, op, False)
        self.assertEqual(changes, [(op, 7, '0.3')])
        self.assertEqual(info.text(7), '—')
        self.assertIn('информативных переходов: 1', report)
        self.bulk.operacii.vremya_tsht_perehodi.assert_not_called()

    def test_excel_operation_uses_annotations_and_returns_setup(self):
        name = 'Упаковывание'
        names = ['Площадь поддона', 'Диаметр,мм', 'Количество', 'Масса_изделия,кг', 'Изделие']
        op = Item(name, '1', time='10', setup='14', raw='3$580$2$42$1')
        registry = Registry(approved={(name, '')}, op_names=names)
        window = self.window(name, 'устаревшее поле:int', tpz='14', registry=registry)
        self.bulk.operacii.vremya_tsht.return_value = (115.7, 5)
        changes, _ = self.bulk.recalc_one(window, op, False)
        self.assertEqual(changes, [(op, 7, '115.7'), (op, 6, '5')])
        self.bulk.operacii.vremya_tsht.assert_called_once_with(name, [names, ['3', '580', '2', '42', '1']])

    def test_excel_transition_uses_server_metadata_and_parent_values(self):
        name = 'Сверлильная'
        per_name = 'Сверлить отверстие по КД'
        transition = Item(per_name, '2', time='0', raw='8')
        op = Item(name, '1', time='0', setup='2', children=[transition])
        registry = Registry(approved={(name, per_name)}, per_names=['Диаметр отверстий'])
        window = self.window(name, registry=registry)
        self.bulk.operacii.vremya_tsht_perehodi.return_value = 0.75
        changes, _ = self.bulk.recalc_one(window, op, False)
        self.assertEqual(changes, [(transition, 7, '0.75'), (op, 7, '0.8')])
        self.bulk.operacii.vremya_tsht_perehodi.assert_called_once_with(
            name, per_name, [['Диаметр отверстий'], ['8']], [''])

    def test_code_transition_uses_notebook_third_column(self):
        name = 'Токарная'
        per_name = 'Торцевать'
        transition = Item(per_name, '2', time='0', raw='40')
        op = Item(name, '1', time='0', setup='2', children=[transition])
        window = self.window(name)
        self.bulk.operacii.vremya_tsht_perehodi.return_value = 1.25
        with mock.patch.object(self.bulk.F, 'open_file_c', return_value=[[per_name, '239', 'Длина элемента:int']]):
            changes, _ = self.bulk.recalc_one(window, op, False)
        self.assertEqual(changes, [(transition, 7, '1.25'), (op, 7, '1.2')])
        self.bulk.operacii.vremya_tsht_perehodi.assert_called_once_with(
            name, per_name, [['Длина элемента'], ['40']], [''])

    def test_template_with_stale_saved_dict_keeps_its_norm(self):
        name = 'Шаблон'
        op = Item(name, '1', time='6', setup='2', raw='12', old_dict="{'Количество': '12'}",
                  children=[Item('Пояснение', '2', time='Без нормы')])
        window = self.window(name, poki=1)
        changes, report = self.bulk.recalc_one(window, op, False)
        self.assertIsNone(changes)
        self.assertIn('нет параметров для автоматического расчёта', report)
        self.bulk.operacii.vremya_tsht.assert_not_called()

    def test_numeric_transition_and_informative_text(self):
        name = 'Комплектовочная'
        info = Item('Указать комплектность', '2', time='Без нормы')
        numeric = Item('Упаковать', '2', time='1,5')
        op = Item(name, '1', time='0', setup='2', raw='2', children=[info, numeric])
        window = self.window(name, 'Масса,кг:int')
        changes, report = self.bulk.recalc_one(window, op, False)
        self.assertEqual(changes, [(op, 7, '1.5')])
        self.assertIn('информативных переходов: 1', report)

    def test_unavailable_approved_excel_reports_error_without_fallback(self):
        name = 'Упаковывание'
        op = Item(name, '1', time='10', setup='14', raw='2')
        window = self.window(name, 'количество:int', registry=Registry(approved={(name, '')}, available=False))
        with self.assertRaisesRegex(ValueError, 'недоступна утверждённая формула'):
            self.bulk.recalc_one(window, op, False)
        self.bulk.operacii.vremya_tsht.assert_not_called()

    def test_unavailable_approved_transition_does_not_use_saved_time(self):
        name = 'Сверлильная'
        per_name = 'Сверлить отверстие по КД'
        per = Item(per_name, '2', time='8', raw='12')
        op = Item(name, '1', time='6', setup='2', children=[per])
        window = self.window(name, registry=Registry(approved={(name, per_name)}, available=False))
        with self.assertRaisesRegex(ValueError, 'недоступна утверждённая формула перехода'):
            self.bulk.recalc_one(window, op, False)
        self.bulk.operacii.vremya_tsht_perehodi.assert_not_called()

    def test_transition_not_allowed_by_editor_keeps_manual_numeric_time(self):
        name = 'Сверлильная'
        per = Item('Сверлить отверстие по КД', '2', time='1.5', raw='12')
        op = Item(name, '1', time='0', setup='2', children=[per])
        window = self.window(name)
        with mock.patch.object(self.bulk.F, 'existence_file_c', return_value=False):
            changes, _ = self.bulk.recalc_one(window, op, False)
        self.assertEqual(changes, [(op, 7, '1.5')])
        self.bulk.operacii.vremya_tsht_perehodi.assert_not_called()

    def test_multirow_values_pass_to_formula_in_editor_format(self):
        name = 'Сверлильная'
        op = Item(name, '1', time='0', setup='2', raw='2;3$5;6')
        window = self.window(name, 'Кол-во отв:str;Диаметр отверстий:str')
        self.bulk.operacii.vremya_tsht.return_value = 4
        changes, _ = self.bulk.recalc_one(window, op, False)
        self.assertEqual(changes, [(op, 7, '4')])
        self.bulk.operacii.vremya_tsht.assert_called_once_with(
            name, [['Кол-во отв', 'Диаметр отверстий'], ['2;3', '5;6']])

    def test_materials_receive_editor_inputs_and_do_not_block_time(self):
        name = 'Комплектовочная'
        per_name = 'Сосчитать'
        transition = Item(per_name, '2', time='0', raw='2')
        op = Item(name, '1', time='0', setup='2', raw='12', children=[transition])
        window = self.window(name, 'Масса,кг:int')
        self.bulk.operacii.vremya_tsht_perehodi.return_value = 2
        self.bulk.operacii.materiali.side_effect = ['001$Материал$кг$2', RuntimeError('нет справочника')]
        with mock.patch.object(self.bulk.F, 'open_file_c', return_value=[[per_name, '200', 'Количество:int']]):
            changes, report = self.bulk.recalc_one(window, op, True)
        self.assertIn((op, 7, '2.0'), changes)
        self.assertIn((op, 10, '001$Материал$кг$2'), changes)
        self.assertIn('материалы после перехода: нет справочника', report)
        self.assertEqual(self.bulk.operacii.materiali.call_args_list[-1].args,
                         (window, name, ['', ['2.0']]))

    def test_grouped_parameters_update_unhashable_tree_item_once(self):
        op = Item('Комплектовочная', '1', raw='2$3')
        uses = [self.bulk.ParamUse(op, ['Количество', 'Масса'], ['2', '3'], i,
                                   '005 — Комплектовочная', '2$3', 'int') for i in range(2)]
        groups = [self.bulk.ParamGroup(name, [use]) for name, use in zip(['Количество', 'Масса'], uses)]
        cell = lambda value: types.SimpleNamespace(checkState=lambda: 2, text=lambda: value)
        values = [['', '', '12'], ['', '', '25']]
        fake = types.SimpleNamespace(groups=groups, table=types.SimpleNamespace(
            item=lambda row, col: cell(values[row][col])), accept=mock.Mock(), changed_count=0)
        self.bulk.BulkParametersDialog.apply_values(fake)
        self.assertEqual(op.text(14), '12$25')
        self.assertEqual(fake.changed_count, 1)
        fake.accept.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
