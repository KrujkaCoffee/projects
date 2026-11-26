"""Check report cards through real builders without application or database imports."""

import ast
import io
import json
import math
import os
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from components.silencer_calculation_core import calc_new_data, default_input_data

try:
    import flet as ft
    from reportlab.pdfgen import canvas
except ImportError:
    ft = None
    canvas = None


COMPONENTS = Path(__file__).resolve().parents[1] / "components"
PRE_VALVE = "ak_produvka_davlenie_v_nachale_truby_mpa_davlenie_do_klapana_mpa"
INLET = "davlenie_na_vhode_v_shg_ri_abs_mpa"


def load_report_definitions(filename, namespace):
    path = COMPONENTS / filename
    source = ast.parse(path.read_text(encoding="utf-8"))
    definitions = [
        node for node in source.body
        if isinstance(node, (ast.FunctionDef, ast.Assign, ast.AnnAssign))
    ]
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *definitions,
    ], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


@unittest.skipIf(ft is None or canvas is None, "Report checks require Flet and reportlab")
class SilencerReportCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = load_report_definitions("silencer_chart_report.py", {"ft": ft})
        cls.pdf = load_report_definitions("silencer_report_pdf.py", {
            "math": math, "os": os, "re": re, "date": date,
            "F": SimpleNamespace(clear_row_for_file_name_c=str, now=lambda fmt: "test"),
        })
        fixture_path = Path(__file__).parent / "fixtures" / "silencer_tz_case.json"
        cls.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cls.inputs = default_input_data()
        cls.inputs.update(cls.fixture["input_overrides"])
        cls.calculated, errors, success = calc_new_data(cls.inputs)
        if not success:
            raise AssertionError(errors)
        cls.inputs[PRE_VALVE] = 13.5

    def web_cards(self, inputs):
        rendered, raw = {}, {}
        build_card = self.web["build_card_component"]

        def collect_card(title, rows, **kwargs):
            card = build_card(title, rows, **kwargs)
            for row in rows:
                if row[0]:
                    raw[row[0]] = (row[1], row[2])
            for row in card.content.controls[1:]:
                name, value, unit = row.controls
                # Пустые строки выравнивают высоту карточек, это не параметры.
                if name.value:
                    rendered[name.value] = (value.value, unit.value)
            return card

        with patch.dict(self.web, {"build_card_component": collect_card}):
            self.web["build_silencer_report"](
                input_values=inputs, calculated=self.calculated, on_back=lambda event: None,
            )
        return rendered, raw

    def pdf_cards(self, inputs):
        rendered, raw = {}, {}
        draw_table = self.pdf["draw_column_table"]
        draw_cell = self.pdf["draw_cell"]

        def collect_table(c, x, y, w, rows, **kwargs):
            cells = []

            def collect_cell(c, x, y, w, h, text="", **cell_kwargs):
                cells.append(text)
                return draw_cell(c, x, y, w, h, text, **cell_kwargs)

            with patch.dict(self.pdf, {"draw_cell": collect_cell}):
                height = draw_table(c, x, y, w, rows, **kwargs)
            self.assertEqual(len(cells), 1 + len(rows) * 3)  # Title, then label/value/unit.
            for index, row in enumerate(rows):
                name, value, unit = cells[1 + index * 3:4 + index * 3]
                rendered[name] = (value, unit)
                raw[row[0]] = (row[1], row[2])
            return height

        real_canvas = canvas.Canvas
        stream = io.BytesIO()
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(self.pdf, {"draw_column_table": collect_table}), patch.object(
                canvas, "Canvas", side_effect=lambda path, **kwargs: real_canvas(stream, **kwargs),
            ):
                self.pdf["build_silencer_report_pdf"](
                    report_name="card-test", input_values=inputs,
                    calculated=self.calculated, save_dir=directory,
                )
        self.assertTrue(stream.getvalue().startswith(b"%PDF-"))
        return rendered, raw

    def test_distinct_pressures_medium_and_diameter_match_in_web_and_pdf(self):
        web, _ = self.web_cards(self.inputs)
        pdf, _ = self.pdf_cards(self.inputs)
        self.assertEqual(web, pdf)
        for name, expected in (
            ("Среда", ("Пар", "")),
            ("Давление до клапана", ("13,5", "МПа")),
            ("Давление на входе (абс.)", ("0,15", "МПа")),
            ("Заданный внутренний диаметр корпуса", ("0,945", "м")),
        ):
            with self.subTest(name=name):
                self.assertEqual(web[name], expected)
        self.assertNotIn("Наличие кассет", web)

    def test_inlet_keeps_three_decimal_places_without_padding_trailing_zero(self):
        for value, expected in ((0.155, "0,155"), (0.15, "0,15")):
            inputs = dict(self.inputs, **{INLET: value})
            for builder in (self.web_cards, self.pdf_cards):
                with self.subTest(builder=builder.__name__, value=value):
                    rendered, _ = builder(inputs)
                    self.assertEqual(rendered["Давление на входе (абс.)"], (expected, "МПа"))

    def test_missing_pre_valve_pressure_never_falls_back_to_inlet(self):
        for missing in (None, "", "absent"):
            inputs = dict(self.inputs)
            if missing == "absent":
                inputs.pop(PRE_VALVE)
            else:
                inputs[PRE_VALVE] = missing
            for builder in (self.web_cards, self.pdf_cards):
                with self.subTest(builder=builder.__name__, missing=missing):
                    rendered, raw = builder(inputs)
                    self.assertIn(rendered["Давление до клапана"][0], ("—", "-"))
                    self.assertIsNone(raw["Давление до клапана"][0])
                    self.assertEqual(rendered["Давление на входе (абс.)"], ("0,15", "МПа"))

    def test_reactive_cards_use_actual_fixture_calculation_values(self):
        expected = self.fixture["expected"]
        checks = (
            ("Массовый расход", "massovyj_rashod_kg_s_out", "mass_flow_kg_s", "5,56", "кг/с"),
            ("Удельный объём при pатм", "udelnyj_obem_m3_kg_out", "specific_volume_m3_kg", "2,702", "м³/кг"),
            ("Диаметр в расчёте силы", "diametr_shg_m_out", "diameter_m", "0,945", "м"),
            ("Скорость на выходе ШГ", "skorost_na_vyhode_shg_m_s", "exit_speed_m_s", "21,4", "м/с"),
            ("Реактивная сила", "r_reaktivnye_sily_n", "reactive_force_n", "119,1", "Н"),
        )
        for builder in (self.web_cards, self.pdf_cards):
            rendered, raw = builder(self.inputs)
            for label, key, fixture_key, text, unit in checks:
                with self.subTest(builder=builder.__name__, label=label):
                    self.assertAlmostEqual(self.calculated[key], expected[fixture_key], delta=1e-9)
                    self.assertEqual(raw[label], (self.calculated[key], unit))
                    self.assertEqual(rendered[label], (text, unit))


if __name__ == "__main__":
    unittest.main()
