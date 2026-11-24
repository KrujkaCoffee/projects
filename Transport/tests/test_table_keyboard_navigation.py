"""Navigation regression checks without importing Flet or the database layer."""

import ast
import asyncio
import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace


def load_navigation_definitions():
    path = Path(__file__).resolve().parents[1] / "components" / "common_funcs.py"
    source = ast.parse(path.read_text(encoding="utf-8"))
    names = {
        "Field_params", "Cell_description", "_Cell_data",
        "Row_data", "Table_data", "InvalidUniqueError",
    }
    definitions = [
        node for node in source.body
        if isinstance(node, ast.ClassDef) and node.name in names
    ]
    view = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "Table_view")
    definitions.append(next(node for node in view.body if getattr(node, "name", None) == "on_key"))
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *definitions,
    ], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"inspect": inspect}
    exec(compile(module, str(path), "exec"), namespace)
    return SimpleNamespace(**namespace)


class SyncFocusControl:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls
        self.visible = True
        self.disabled = False

    def focus(self):
        self.calls.append(self.name)


class AsyncFocusControl(SyncFocusControl):
    async def focus(self):
        await asyncio.sleep(0)
        self.calls.append(self.name)


class TableKeyboardNavigationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.definitions = load_navigation_definitions()

    def make_table(self, control_type=AsyncFocusControl):
        definitions = self.definitions
        table = definitions.Table_data()
        table.append_column_desc("name", unique=True, hidden=True)
        table.append_column_desc("val", editable=True)
        calls = []

        def add_row(name, *, merge=False, visible=True, disabled=False, control_visible=True):
            row = definitions.Row_data(merge=merge)
            row.append(name, definitions.Cell_description())
            cell = row.append("unchanged", definitions.Cell_description())
            control = control_type(name, calls)
            control.disabled = disabled
            control.visible = control_visible
            cell.control_ref = SimpleNamespace(current=control)
            row.control_ref = SimpleNamespace(current=SimpleNamespace(visible=visible))
            table.add_row(row)
            return row

        view = SimpleNamespace(table_data=table, keyboard_navigation=True)
        return table, view, calls, add_row

    async def press(self, view, key, **modifiers):
        result = self.definitions.on_key(view, SimpleNamespace(key=key, **modifiers))
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def select(row):
        row.dict_cells()["val"].on_focus(None)

    async def test_repeated_navigation_awaits_async_focus_and_supports_sync_focus(self):
        for control_type in (AsyncFocusControl, SyncFocusControl):
            with self.subTest(control_type=control_type.__name__):
                table, view, calls, add = self.make_table(control_type)
                first, second, third = [add(name) for name in ("first", "second", "third")]
                self.select(first)
                for key in ("Arrow Down", "Arrow Down", "Arrow Up"):
                    await self.press(view, key)
                self.assertEqual(calls, ["second", "third", "second"])
                self.assertIs(table.current_row, second)
                self.assertIs(second.current_cell, second.dict_cells()["val"])
                self.assertTrue(all(row.dict_cells()["val"].val == "unchanged" for row in table.rows))

    async def test_arrows_skip_group_hidden_and_disabled_rows_in_both_directions(self):
        table, view, calls, add = self.make_table()
        first = add("first")
        add("group", merge=True)
        add("hidden_row", visible=False)
        add("disabled_control", disabled=True)
        add("hidden_control", control_visible=False)
        last = add("last")
        self.select(first)
        await self.press(view, "Arrow Down")
        self.assertIs(table.current_row, last)
        await self.press(view, "Arrow Up")
        self.assertIs(table.current_row, first)
        self.assertEqual(calls, ["last", "first"])

    async def test_initial_focus_uses_first_available_editable_cell(self):
        for key in ("Arrow Down", "Arrow Up"):
            with self.subTest(key=key):
                table, view, calls, add = self.make_table()
                add("group", merge=True)
                add("hidden", visible=False)
                add("disabled", disabled=True)
                first = add("first")
                await self.press(view, key)
                self.assertEqual(calls, ["first"])
                self.assertIs(table.current_row, first)
                self.assertEqual(first.current_cell.params_field.name, "val")

    async def test_boundaries_do_not_wrap_or_repeat_focus(self):
        table, view, calls, add = self.make_table()
        first, last = add("first"), add("last")
        self.select(first)
        await self.press(view, "Arrow Up")
        self.assertIs(table.current_row, first)
        self.select(last)
        await self.press(view, "Arrow Down")
        self.assertIs(table.current_row, last)
        self.assertEqual(calls, [])

    async def test_tab_and_other_keys_are_left_to_native_handling(self):
        table, view, calls, add = self.make_table()
        first = add("first")
        add("second")
        self.select(first)
        for key, shift in (("Tab", False), ("Tab", True), ("Arrow Left", False), ("Arrow Right", False), ("Enter", False)):
            await self.press(view, key, shift=shift)
        self.assertEqual(calls, [])
        self.assertIs(table.current_row, first)

    async def test_disabled_navigation_does_not_move_focus(self):
        table, view, calls, add = self.make_table()
        first = add("first")
        add("second")
        self.select(first)
        view.keyboard_navigation = False
        for key in ("Arrow Down", "Arrow Up", "Tab"):
            await self.press(view, key)
        self.assertEqual(calls, [])
        self.assertIs(table.current_row, first)

    async def test_no_available_cells_is_a_noop(self):
        table, view, calls, add = self.make_table()
        for key in ("Arrow Down", "Arrow Up"):
            await self.press(view, key)
        add("group", merge=True)
        add("hidden", visible=False)
        add("disabled", disabled=True)
        for key in ("Arrow Down", "Arrow Up"):
            await self.press(view, key)
        self.assertEqual(calls, [])
        self.assertIsNone(table.current_row)


if __name__ == "__main__":
    unittest.main()
