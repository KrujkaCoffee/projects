"""Exercise real Flet controls without importing application/database startup code."""

import ast
import inspect
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

try:
    import flet as ft
except ImportError:
    ft = None


def load_table_definitions():
    path = Path(__file__).resolve().parents[1] / "components" / "common_funcs.py"
    source = ast.parse(path.read_text(encoding="utf-8"))
    names = {
        "Field_params", "Cell_description", "_Cell_data", "Row_data",
        "Table_data", "InvalidUniqueError", "Table_view",
        "create_value_cell", "datatable_to_dicts",
    }
    definitions = [
        node for node in source.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names
    ]
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *definitions,
    ], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"ft": ft, "inspect": inspect, "Decimal": Decimal}
    exec(compile(module, str(path), "exec"), namespace)
    return SimpleNamespace(**namespace)


@unittest.skipIf(ft is None, "Flet is not installed; these checks use real controls")
class TableDropdownFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definitions = load_table_definitions()

    def make_view(self, *, navigation, lazy=False, options=None, data_type=int, callback=None):
        definitions = self.definitions
        options = [1, 2, 3] if options is None else options
        table = definitions.Table_data()
        table.append_column_desc("name", "Имя", unique=True, hidden=True)
        table.append_column_desc("val", "Значение", editable=True)
        row = definitions.Row_data()
        row.append("choice", definitions.Cell_description())
        cell = row.append(options[0], definitions.Cell_description(options, data_type=data_type))
        table.add_row(row)
        view = definitions.Table_view(
            table, fnc_onchange=callback,
            keyboard_navigation=navigation, lazy_groups=lazy,
        )
        if lazy:
            # The same deferred row builder is called when a lazy group opens.
            view.rows = [view._build_data_row(row)]
        control = view.rows[0].cells[1].content.content
        return table, view, cell, control

    def test_regular_and_lazy_rows_use_m2_only_when_navigation_is_enabled(self):
        for navigation in (False, True):
            for lazy in (False, True):
                with self.subTest(navigation=navigation, lazy=lazy):
                    callback = lambda event: None
                    table, view, cell, control = self.make_view(
                        navigation=navigation, lazy=lazy, callback=callback,
                    )
                    expected_control = ft.DropdownM2 if navigation else ft.Dropdown
                    expected_option = ft.dropdownm2.Option if navigation else ft.dropdown.Option
                    self.assertIs(type(control), expected_control)
                    self.assertTrue(all(type(option) is expected_option for option in control.options))
                    self.assertEqual([option.key for option in control.options], ["1", "2", "3"])
                    self.assertEqual(control.value, "1")
                    self.assertIs(control.data["cell"], cell)
                    self.assertIs(cell.control_ref.current, control)
                    self.assertIs(cell.container_ref.current, view.rows[0].cells[1].content)
                    self.assertIs(control.on_change if navigation else control.on_select, callback)

    def test_m2_selection_preserves_numeric_and_text_value_contracts(self):
        for options, data_type, selected in (
            ([1, 2, 3], int, "2"),
            (["Пар", "Воздух"], str, "Воздух"),
        ):
            with self.subTest(data_type=data_type):
                calls = []

                def changed(event):
                    cell = event.control.data["cell"]
                    cell.val = cell.description.cast_type(event.data)
                    calls.append(event.data)

                table, view, cell, control = self.make_view(
                    navigation=True, options=options, data_type=data_type, callback=changed,
                )
                control.value = selected
                control.on_change(SimpleNamespace(control=control, data=selected))
                self.assertEqual(calls, [selected])
                self.assertEqual(cell.val, data_type(selected))
                self.assertIs(type(cell.val), data_type)
                cell.val = options[0]
                self.assertTrue(table.sync_ui_to_data("val"))
                self.assertEqual(cell.val, data_type(selected))
                self.assertIs(type(cell.val), data_type)

    def test_extraction_preserves_selected_strings_and_none_for_both_controls(self):
        for navigation in (False, True):
            with self.subTest(navigation=navigation):
                _, view, _, control = self.make_view(
                    navigation=navigation, options=["Пар", "Воздух"], data_type=str,
                )
                for selected in ("Пар", "Воздух", None):
                    control.value = selected
                    data = self.definitions.datatable_to_dicts(view)
                    self.assertEqual(data, [{"Имя": "choice", "Значение": selected}])

    def test_m2_uses_native_focus_state_with_a_distinct_filled_background(self):
        table, _, cell, control = self.make_view(navigation=True)
        self.assertEqual(control.focused_bgcolor, ft.Colors.PRIMARY_CONTAINER)
        self.assertEqual(control.bgcolor, ft.Colors.SECONDARY_CONTAINER)
        self.assertNotEqual(control.focused_bgcolor, control.bgcolor)
        self.assertIs(control.filled, True)
        self.assertEqual(control.on_focus, cell.on_focus)
        self.assertEqual(control.on_blur, cell.on_blur)
        control.on_focus(SimpleNamespace(control=control))
        self.assertIs(table.current_row.current_cell, cell)
        self.assertTrue(cell._has_focus)
        control.on_blur(SimpleNamespace(control=control))
        self.assertFalse(cell._has_focus)
        self.assertEqual(control.value, "1")


if __name__ == "__main__":
    unittest.main()
