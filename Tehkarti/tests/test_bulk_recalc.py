"""Checks for bulk time calculation without the Windows/PyQt application runtime."""

import importlib.util
import math
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


def load_bulk_operations():
    qt = types.ModuleType('PyQt5')
    qt.QtCore = types.ModuleType('PyQt5.QtCore')
    qt.QtWidgets = types.ModuleType('PyQt5.QtWidgets')
    qt.QtWidgets.QDialog = object

    functions = types.ModuleType('project_cust_38.Cust_Functions')
    def valm(value):
        raw = str(value).replace(',', '.')
        if not raw.strip():
            return 0
        return float(raw) if '.' in raw or 'e' in raw.lower() else int(raw)

    functions.valm = valm
    functions.is_numeric = lambda value: is_numeric(value)
    config = types.ModuleType('project_cust_38.Cust_config')
    config.Config = types.SimpleNamespace(place=types.SimpleNamespace(limit_time_on_naryad=100))
    operations = types.ModuleType('project_cust_38.operacii')
    operations.Data_oper_norm = types.SimpleNamespace(DICT_OPERS_CALC={})
    qt_helpers = types.ModuleType('project_cust_38.Cust_Qt')
    package = types.ModuleType('project_cust_38')
    package.Cust_Functions = functions
    package.Cust_config = config
    package.operacii = operations
    package.Cust_Qt = qt_helpers
    imports = {
        'PyQt5': qt,
        'PyQt5.QtCore': qt.QtCore,
        'PyQt5.QtWidgets': qt.QtWidgets,
        'project_cust_38': package,
        'project_cust_38.Cust_Functions': functions,
        'project_cust_38.Cust_config': config,
        'project_cust_38.operacii': operations,
        'project_cust_38.Cust_Qt': qt_helpers,
    }
    spec = importlib.util.spec_from_file_location(
        'tehkart_bulk_under_test', Path(__file__).parents[1] / 'bulk_operations.py')
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {**imports, spec.name: module}):
        spec.loader.exec_module(module)
    return module


def is_numeric(value):
    try:
        return math.isfinite(float(str(value).replace(',', '.')))
    except ValueError:
        return False


class Item:
    def __init__(self, name, level, time='', setup='', children=()):
        self.columns = {0: name, 2: '005', 6: setup, 7: time, 10: '', 20: level}
        self.children = list(children)
        for child in self.children:
            child.parent_item = self

    def text(self, column):
        return self.columns.get(column, '')

    def parent(self):
        return self.parent_item

    def childCount(self):
        return len(self.children)

    def child(self, index):
        return self.children[index]


class FormulaRegistry:
    def __init__(self, approved=(), strict=False):
        self.approved = set(approved)
        self.strict = strict

    def check_approved(self, *, operation, pereh=''):
        return pereh in self.approved

    def check_strict_calc(self, *, operation):
        return self.strict


class BulkRecalcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bulk = load_bulk_operations()

    def calculate(self, op, params, op_result, transition_results=None, *, approved=(), strict=False,
                  with_materials=False, material_result=None):
        window = types.SimpleNamespace(
            DICT_OPERS={'Резка': {'Tpz': '2'}},
            xl_formulas=FormulaRegistry(approved, strict))
        self.bulk.operacii.vremya_tsht = mock.Mock(return_value=op_result)
        self.bulk.operacii.materiali = mock.Mock(return_value=material_result)
        transition_results = transition_results or {}
        self.bulk.operacii.vremya_tsht_perehodi = mock.Mock(
            side_effect=lambda _, name, per, parent: transition_results[name])
        with mock.patch.object(self.bulk, 'params_for_calc', side_effect=lambda _, item: params.get(item)):
            result = self.bulk.recalc_one(window, op, with_materials)
        return result

    def test_informative_transition_and_operation_priority(self):
        info = Item('Проверить маркировку', '2')
        calc = Item('Отрезать', '2', time='3')
        op = Item('Резка', '1', time='1', setup='1', children=[info, calc])
        (changes, report) = self.calculate(
            op, {op: [['Количество'], ['12']], calc: [['Длина'], ['7']]}, 4,
            {'Отрезать': 2}, approved={'Отрезать'})
        self.assertEqual(changes, [(calc, 7, '2'), (op, 7, '4'), (op, 6, '2')])
        self.assertIn('информативных переходов: 1', report)
        self.assertEqual(info.text(7), '')
        self.bulk.operacii.vremya_tsht.assert_called_once_with('Резка', {'Количество': '12'})
        self.bulk.operacii.vremya_tsht_perehodi.assert_called_once_with(
            'Резка', 'Отрезать', {'Длина': '7'}, {'Количество': '12'})

    def test_zero_operation_uses_transitions_and_clears_zero_times(self):
        calculated = Item('Отрезать', '2', time='5')
        zero = Item('Замерить', '2', time='8')
        manual = Item('Установить', '2', time='1,5')
        info = Item('Пояснение', '2')
        op = Item('Резка', '1', time='9', setup='2', children=[calculated, zero, manual, info])
        (changes, _) = self.calculate(
            op, {calculated: [['Длина'], ['7']], zero: [['Ширина'], ['2']]}, 0,
            {'Отрезать': 2.5, 'Замерить': 0, 'Установить': 0})
        self.assertEqual(changes, [(calculated, 7, '2.5'), (zero, 7, ''),
                                   (manual, 7, ''), (op, 7, '2.5')])

    def test_none_keeps_existing_time_and_default_setup(self):
        transition = Item('Отрезать', '2', time='1.25')
        op = Item('Резка', '1', time='8', setup='0', children=[transition])
        (changes, report) = self.calculate(
            op, {transition: [['Длина'], ['7']]}, None, {'Отрезать': None})
        self.assertEqual(changes, [(op, 6, '2')])
        self.assertIn('нет результата формулы операции', report)
        self.assertIn('переходов без результата формулы: 1', report)

    def test_tuple_overrides_default_setup(self):
        op = Item('Резка', '1', time='1', setup='2')
        (changes, _) = self.calculate(op, {}, (5, 3))
        self.assertEqual(changes, [(op, 7, '5'), (op, 6, '3')])

    def test_zero_strict_operation_is_rejected(self):
        op = Item('Резка', '1', time='1', setup='2', children=[Item('Пояснение', '2')])
        with self.assertRaisesRegex(ValueError, 'обязательным расчётом'):
            self.calculate(op, {}, 0, strict=True)

    def test_manual_operation_is_untouched(self):
        op = Item('Резка', '1', time='=5', setup='2', children=[Item('Отрезать', '2')])
        changes, report = self.calculate(op, {}, 10)
        self.assertIsNone(changes)
        self.assertIn('ручная норма', report)
        self.bulk.operacii.vremya_tsht.assert_not_called()

    def test_materials_follow_checkbox(self):
        op = Item('Резка', '1', time='1', setup='2')
        op.columns[10] = '001$Лист$кг$1'
        params = {op: [['Количество'], ['12']]}
        calculated = '001$Лист$кг$2{002$Круг$кг$3'
        changes, _ = self.calculate(op, params, 1, with_materials=True, material_result=calculated)
        self.assertEqual(changes, [(op, 10, calculated)])
        self.bulk.operacii.materiali.assert_called_once()
        changes, _ = self.calculate(op, params, 1, with_materials=False, material_result=calculated)
        self.assertIsNone(changes)
        self.bulk.operacii.materiali.assert_not_called()


if __name__ == '__main__':
    unittest.main()
