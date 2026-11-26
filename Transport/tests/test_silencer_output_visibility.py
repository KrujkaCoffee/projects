"""Output visibility through real models, without application or database imports."""

import ast
import copy
import itertools
import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from components import silencer_calculation_core as core
from components.tech_report_excel import sort_key_params
from test_table_dropdown_focus import ft, load_table_definitions


TARGET = "Исходный уровень звуковой мощности на входе в глушитель"
RETAINED = "Дроссельный блок"  # GROUPS=False must not hide other saved groups.


def load_backend(models):
    path = Path(__file__).resolve().parents[1] / "components" / "calc_silencer_back.py"
    source = ast.parse(path.read_text(encoding="utf-8"))
    names = {
        "is_empty", "make_res_tbl", "_json_safe", "table_data_to_payload",
        "table_data_from_payload", "_filter_hidden_output_groups",
        "build_history_blob", "decode_history_blob", "load_from_db_history_calc",
    }
    definitions = []
    for node in source.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            definitions.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in {
                "TBL_OUTPUT", "GROUPS", "OUTPUT_PARAMS", "HIDDEN_OUTPUT_GROUPS", "_HISTORY_SCHEMA_VERSION",
            } for target in node.targets
        ):
            definitions.append(node)
        elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
              and isinstance(node.value.func, ast.Attribute)
              and isinstance(node.value.func.value, ast.Name)
              and node.value.func.value.id == "TBL_OUTPUT"):
            definitions.append(node)
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *definitions,
    ], type_ignores=[])
    ast.fix_missing_locations(module)
    counter = itertools.count()
    namespace = {
        "CMF": models, "Table_data": models.Table_data, "calculation_core": core,
        "copy": copy, "math": math, "json": json, "sort_key_params": sort_key_params,
        "F": SimpleNamespace(get_time_shtamp_c=lambda: str(next(counter)),
            is_numeric=lambda value: isinstance(value, (int, float))),
        "CSQ": SimpleNamespace(custom_request_c=Mock()),
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


@unittest.skipIf(ft is None, "Visibility checks use real Flet controls")
class SilencerOutputVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = load_table_definitions()
        cls.models.Table_view.__init__.__globals__["Cust_emoji"] = SimpleNamespace(
            EmojiMain=SimpleNamespace(Документы=SimpleNamespace(plus="➕", minus="➖")),
        )
        cls.calculated, errors, success = core.calc_new_data(core.default_input_data())
        if not success:
            raise AssertionError(errors)
        cls.hidden_keys = {
            key for key, meta in core.OUTPUT_PARAMS.items() if meta.get("group_name") == TARGET
        }

    def setUp(self):
        self.namespace = load_backend(self.models)
        self.backend = SimpleNamespace(**self.namespace)
        self.query = self.backend.CSQ.custom_request_c
        self.data = SimpleNamespace(Data_user=SimpleNamespace(db_flet=object(), login="test"))
        self.input_table = self.models.Table_data()

    def saved_output(self, include_hidden=True):
        table = copy.deepcopy(self.backend.TBL_OUTPUT)
        table.add_table_name("saved", "Расчетные данные:")

        def add_value(group, key, value):
            row = self.models.Row_data()
            row.group_name = group
            for item in (key, key, value, "", "saved comment"):
                row.append(item, self.models.Cell_description(data_type=type(item)))
            table.add_row(row)

        if include_hidden:
            table.add_group("hidden", TARGET)
            for key in sorted(self.hidden_keys):
                add_value(TARGET, key, self.calculated[key])
        table.add_group("retained", RETAINED)
        for key, value in (("text", "Пар"), ("integer", 3), ("float", 0.15), ("boolean", True)):
            add_value(RETAINED, key, value)
        return table

    def assert_visible_model(self, table):
        self.assertFalse(any(row.group_name == TARGET for row in table.rows))
        self.assertTrue(any(row.group_name == RETAINED for row in table.rows))
        unique_values = {row.get_cell_unique().val for row in table.rows}
        self.assertEqual(table._set_unique_vals, unique_values)
        for row in table.rows:
            self.assertIs(row.parent_table_data, table)
            self.assertIs(row.fields, table.list_fields)
            self.assertIs(table.get_row_by_unique_name(row.get_cell_unique().val), row)
            for index, cell in enumerate(row.cells):
                self.assertIs(cell.parent_row, row)
                self.assertIs(cell.params_field, table.list_fields[index])
        for key, expected_type in (("text", str), ("integer", int), ("float", float), ("boolean", bool)):
            self.assertIs(type(table.get_row_by_unique_name(key).dict_cells()["val"].val), expected_type)

    def test_new_result_has_no_group_but_all_nine_formulas_remain(self):
        self.assertEqual(core.HIDDEN_OUTPUT_GROUPS, frozenset({TARGET}))
        self.assertFalse(core.GROUPS[TARGET])
        self.assertEqual(len(self.hidden_keys), 9)
        self.assertTrue(all(math.isfinite(self.calculated[key]) for key in self.hidden_keys))
        table = self.backend.make_res_tbl(self.calculated)
        self.assertFalse(any(row.group_name == TARGET for row in table.rows))
        self.assertNotIn(TARGET, table.table_view._group_order)
        self.assertTrue(self.hidden_keys.isdisjoint(table.to_dict_by_unique()))

    def test_old_json_hides_header_and_rows_even_when_all_groups_expand(self):
        original = self.saved_output()
        before = self.backend.table_data_to_payload(original)
        blob = self.backend.build_history_blob(self.input_table, original)
        self.assertEqual(json.loads(blob)["schema_version"], 2)
        self.query.return_value = blob
        _, visible = self.backend.load_from_db_history_calc(self.data, 7)
        expected = copy.deepcopy(before)
        expected["rows"] = [row for row in expected["rows"] if row["group_name"] != TARGET]
        self.assertEqual(self.backend.table_data_to_payload(visible), expected)
        self.assert_visible_model(visible)
        self.assertFalse(core.GROUPS[RETAINED])
        self.assertEqual(self.backend.table_data_to_payload(original), before)
        _, decoded = self.backend.decode_history_blob(blob)
        self.assertEqual(sum(row.group_name == TARGET for row in decoded.rows), 10)
        self.assertEqual(self.backend.table_data_to_payload(decoded), before)
        self.query.assert_called_once()
        self.assertTrue(self.query.call_args.args[1].startswith("SELECT "))

        view = self.models.Table_view(visible, lazy_groups=True, single_group_expand=False)
        view.toggle_group_ui()
        self.assertEqual(view._expanded_groups, {RETAINED})
        self.assertNotIn(TARGET, view._group_order)
        self.assertNotIn(TARGET, view._ui_data_rows_cache)
        rows = self.models.datatable_to_dicts(view)
        self.assertTrue(self.hidden_keys.isdisjoint(row.get("Имя") for row in rows))
        self.assertNotIn(TARGET, str(rows))

    def test_legacy_decoder_result_uses_same_filter_without_mutating_source(self):
        original = self.saved_output()
        before = self.backend.table_data_to_payload(original)
        self.query.return_value = b"legacy"
        decoded = Mock(return_value=(self.input_table, original))
        with patch.dict(self.namespace, {"decode_history_blob": decoded}):
            inputs, visible = self.backend.load_from_db_history_calc(self.data, 8)
        decoded.assert_called_once_with(b"legacy")
        self.assertIs(inputs, self.input_table)
        self.assertIsNot(visible, original)
        self.assert_visible_model(visible)
        self.assertEqual(self.backend.table_data_to_payload(original), before)
        self.assertEqual(sum(row.group_name == TARGET for row in original.rows), 10)

    def test_snapshot_without_hidden_group_is_reused_and_loads_unchanged(self):
        original = self.saved_output(include_hidden=False)
        before = self.backend.table_data_to_payload(original)
        self.assertIs(self.backend._filter_hidden_output_groups(original), original)
        self.query.return_value = self.backend.build_history_blob(self.input_table, original)
        _, visible = self.backend.load_from_db_history_calc(self.data, 9)
        self.assertEqual(self.backend.table_data_to_payload(visible), before)
        self.assert_visible_model(visible)


if __name__ == "__main__":
    unittest.main()
