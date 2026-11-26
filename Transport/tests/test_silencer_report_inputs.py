"""Check report snapshots without importing application or database startup code."""

import ast
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from components.silencer_calculation_core import INPUT_PARAM_NAMES, calc_new_data, default_input_data


def load_definitions(filename, names, namespace=None):
    path = Path(__file__).resolve().parents[1] / "components" / filename
    source = ast.parse(path.read_text(encoding="utf-8"))
    definitions = [
        node for node in ast.walk(source)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names
    ]
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *definitions,
    ], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {} if namespace is None else namespace
    exec(compile(module, str(path), "exec"), namespace)
    return SimpleNamespace(**namespace)


class SilencerReportInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = load_definitions("common_funcs.py", {
            "Field_params", "Cell_description", "_Cell_data", "Row_data",
            "Table_data", "InvalidUniqueError",
        })

    def setUp(self):
        self.old_inputs = default_input_data()
        self.current_inputs = dict(self.old_inputs, sreda="Воздух", davlenie_na_vhode_v_shg_ri_abs_mpa=0.15)
        self.table = self.models.Table_data()
        self.table.append_column_desc("name", unique=True)
        self.table.append_column_desc("val", editable=True)
        self.cells = {}
        for name, value in self.current_inputs.items():
            row = self.models.Row_data()
            row.append(name, self.models.Cell_description())
            cell = row.append(value, self.models.Cell_description(data_type=type(value)))
            cell.control_ref = SimpleNamespace(current=SimpleNamespace(value=str(value)))
            self.table.add_row(row)
            self.cells[name] = cell
        self.pressure = self.cells["davlenie_na_vhode_v_shg_ri_abs_mpa"]
        self.old_calculated, _, _ = calc_new_data(self.old_inputs)
        self.state = SimpleNamespace(
            input_tbl_editbl=self.table, last_input_vals=self.old_inputs,
            last_calculated=self.old_calculated, last_calc_errors=["previous"],
            last_metrics_ms={}, output_tbl=SimpleNamespace(table_view=object()),
        )
        self.data = SimpleNamespace(Data_module=SimpleNamespace(
            cust_data=self.state, status_bar=Mock(),
        ))
        self.page = SimpleNamespace(data=self.data, on_keyboard_event=None, update=Mock())
        self.refs = SimpleNamespace(
            input_table=SimpleNamespace(current=SimpleNamespace(table_data=self.table)),
            output_table=SimpleNamespace(),
            output_column=SimpleNamespace(current=SimpleNamespace(controls=[], update=Mock())),
            desktop_column=SimpleNamespace(current=SimpleNamespace(controls=[], update=Mock())),
            calculation_name=SimpleNamespace(current=SimpleNamespace(value="")),
        )
        self.common = SimpleNamespace(
            Table_data=self.models.Table_data,
            datatable_to_dicts=Mock(return_value=[]), message_dialog=Mock(),
        )
        self.backend = load_definitions("calc_silencer_back.py", {
            "get_vals_from_input_data_tbl", "prepare_calc_new_data",
        }, {"CMF": self.common, "INPUT_PARAM_NAMES": INPUT_PARAM_NAMES,
            "time": time, "calc_new_data": calc_new_data})
        self.backend.generate_rez_tbl = Mock(return_value=True)
        self.backend.get_name_new_calc = Mock(return_value="report")
        self.backend.get_vals_from_input_data_tbl = Mock(wraps=self.backend.get_vals_from_input_data_tbl)
        self.backend.calc_new_data = Mock(wraps=calc_new_data)
        self.build_report = Mock(return_value=object())
        self.callbacks = load_definitions("calc_silencer.py", {
            "fnc_onchange_tbl_input", "add_rez_table", "show_chart_report",
        }, {
            "Data": self.data, "refs": self.refs, "CMF": self.common,
            "calc_silencer_back": self.backend, "build_silencer_report": self.build_report,
            "_schedule_draft_save": Mock(), "set_header_elems_visible": Mock(),
            "fnc_cell_click": Mock(),
            "_refStatusBar": SimpleNamespace(current=SimpleNamespace(update=Mock())),
            "ft": SimpleNamespace(Icons=SimpleNamespace(ERROR="error"),
                MainAxisAlignment=SimpleNamespace(START="start"),
                CrossAxisAlignment=SimpleNamespace(STRETCH="stretch")),
        })
        self.event = SimpleNamespace(page=self.page)

    def test_snapshot_preserves_medium_and_decimal_pressure(self):
        self.pressure.control_ref.current.value = "0,15"
        snapshot = self.backend.get_vals_from_input_data_tbl(self.refs.input_table.current)
        self.assertEqual(snapshot["sreda"], "Воздух")
        self.assertEqual(snapshot["davlenie_na_vhode_v_shg_ri_abs_mpa"], 0.15)

    def test_snapshot_rejects_invalid_ui_and_explicit_false_sync(self):
        self.pressure.control_ref.current.value = "invalid"
        with self.assertRaises(ValueError):
            self.backend.get_vals_from_input_data_tbl(self.refs.input_table.current)
        self.assertEqual(self.pressure.val, 0.15)
        with patch.object(self.table, "sync_ui_to_data", return_value=False):
            with self.assertRaises(ValueError):
                self.backend.get_vals_from_input_data_tbl(self.refs.input_table.current)

    def test_edit_invalidates_both_snapshots_even_if_value_cannot_be_parsed(self):
        for value in ("0,15", "invalid"):
            with self.subTest(value=value):
                self.state.last_input_vals = self.old_inputs
                self.state.last_calculated = self.old_calculated
                self.state.last_calc_errors = ["previous"]
                event = SimpleNamespace(page=self.page, data=value,
                    control=SimpleNamespace(data={"cell": self.pressure}))
                if value == "invalid":
                    with self.assertRaises(ValueError):
                        self.callbacks.fnc_onchange_tbl_input(event)
                else:
                    self.callbacks.fnc_onchange_tbl_input(event)
                self.assertIsNone(self.state.last_input_vals)
                self.assertIsNone(self.state.last_calculated)
                self.assertEqual(self.state.last_calc_errors, [])

    def test_failed_snapshot_after_new_result_does_not_keep_old_inputs(self):
        self.pressure.control_ref.current.value = "invalid"
        self.callbacks.add_rez_table(self.event)
        self.assertIsNone(self.state.last_input_vals)
        self.backend.get_name_new_calc.assert_called_once_with({})

    def test_report_rebuilds_both_halves_if_either_snapshot_is_missing(self):
        expected, errors, success = calc_new_data(self.current_inputs)
        self.assertTrue(success, errors)
        for inputs, calculated in (
            (self.old_inputs, None), (None, self.old_calculated), (None, None),
        ):
            with self.subTest(inputs_missing=inputs is None, result_missing=calculated is None):
                self.state.last_input_vals = inputs
                self.state.last_calculated = calculated
                self.callbacks.show_chart_report(self.event)
                report = self.build_report.call_args.kwargs
                self.assertEqual(report["input_values"], self.current_inputs)
                self.assertEqual(report["calculated"], expected)
                self.assertIs(self.state.last_input_vals, report["input_values"])
                self.assertIs(self.state.last_calculated, report["calculated"])
                self.assertEqual(self.state.last_calc_errors, [])

    def test_report_uses_the_captured_inputs_even_if_ui_changes_after_capture(self):
        snapshot = self.backend.get_vals_from_input_data_tbl(self.refs.input_table.current)
        self.cells["sreda"].control_ref.current.value = "Пар"
        self.backend.get_vals_from_input_data_tbl = Mock(return_value=snapshot)
        self.state.last_input_vals = None
        self.state.last_calculated = None
        self.callbacks.show_chart_report(self.event)
        report = self.build_report.call_args.kwargs
        expected, _, _ = calc_new_data(snapshot)
        self.assertEqual(report["input_values"], snapshot)
        self.assertEqual(report["calculated"], expected)

    def test_cached_report_reuses_the_matching_pair(self):
        self.callbacks.show_chart_report(self.event)
        report = self.build_report.call_args.kwargs
        self.assertIs(report["input_values"], self.old_inputs)
        self.assertIs(report["calculated"], self.old_calculated)
        self.backend.get_vals_from_input_data_tbl.assert_not_called()
        self.backend.calc_new_data.assert_not_called()

    def test_report_does_not_build_on_failed_snapshot_or_leave_cached_halves(self):
        self.pressure.control_ref.current.value = "invalid"
        self.state.last_calculated = None
        self.callbacks.show_chart_report(self.event)
        self.build_report.assert_not_called()
        self.backend.calc_new_data.assert_not_called()
        self.common.message_dialog.assert_called_once()
        self.assertIsNone(self.state.last_input_vals)
        self.assertIsNone(self.state.last_calculated)
        self.assertEqual(self.state.last_calc_errors, [])


if __name__ == "__main__":
    unittest.main()
