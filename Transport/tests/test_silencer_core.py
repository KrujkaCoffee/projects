import json
import math
import time
import unittest
from pathlib import Path

from components.calc_silencer_functions_M5_M400 import (
    calc_gazovaya_postoyannaya_m2_s2_k,
    calc_kriticheskaya_skorost_skr_m_s,
)
from components.excel_compat import excel_round
from components.silencer_calculation_core import (
    GROUPS,
    OUTPUT_PARAMS,
    calc_new_data,
    default_input_data,
    normalize_input_data,
)
from components.tech_report_excel import sort_key_params


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "silencer_tz_case.json"
SOURCE_DEFAULT_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "silencer_source_default_10_stages.json"
)

FINAL_SPECTRUM_KEYS = [
    "ak_srednegeometricheskaya_chastota_gc_31_5_19",
    "ak_srednegeometricheskaya_chastota_gc_63_9",
    "ak_srednegeometricheskaya_chastota_gc_125_9",
    "ak_srednegeometricheskaya_chastota_gc_250_9",
    "ak_srednegeometricheskaya_chastota_gc_500_9",
    "ak_srednegeometricheskaya_chastota_gc_1000_9",
    "ak_srednegeometricheskaya_chastota_gc_2000_9",
    "ak_srednegeometricheskaya_chastota_gc_4000_9",
    "ak_srednegeometricheskaya_chastota_gc_8000_9",
]

VISIBLE_FINAL_SPECTRUM_KEYS = [
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_31_5_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_63_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_125_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_250_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_500_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_1000_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_2000_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_4000_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_8000_5",
]


class SilencerCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.source_default_fixture = json.loads(
            SOURCE_DEFAULT_FIXTURE_PATH.read_text(encoding="utf-8")
        )

    def test_tz_visible_inputs_match_recalculated_xlsm(self):
        """Проверяет пять видимых входов ТЗ, не неизвестные входы снимка."""
        input_data = default_input_data()
        input_data.update(self.fixture["input_overrides"])

        calculated, errors, success = calc_new_data(input_data)

        self.assertTrue(success, errors)
        self.assertEqual(errors, [])
        actual_spectrum = [calculated[key] for key in FINAL_SPECTRUM_KEYS]
        for actual, expected in zip(actual_spectrum, self.fixture["expected"]["spectrum_db"]):
            self.assertAlmostEqual(actual, expected, delta=5e-6)

        actual_a = calculated["ak_uroven_zvuka_dba_3"]
        self.assertAlmostEqual(
            actual_a,
            self.fixture["expected"]["a_weighted_db"],
            delta=5e-6,
        )
        self.assertEqual(
            excel_round(actual_a),
            self.fixture["expected"]["a_weighted_rounded_db"],
        )
        for actual, expected in zip(
            [calculated[key] for key in VISIBLE_FINAL_SPECTRUM_KEYS],
            self.fixture["expected"]["spectrum_db"],
        ):
            self.assertAlmostEqual(actual, expected, delta=5e-6)
        self.assertEqual(
            calculated["ak_polosa_a_5"],
            self.fixture["expected"]["a_weighted_rounded_db"],
        )

    def test_source_default_ten_stage_case_matches_recalculated_xlsm(self):
        """Guards the pressure-gradient branch that is not used by the TZ case."""

        fixture = self.source_default_fixture
        input_data = default_input_data()
        input_data.update(fixture["input_overrides"])

        calculated, errors, success = calc_new_data(input_data)

        self.assertTrue(success, errors)
        self.assertAlmostEqual(
            calculated["perepad_davlenij_n1"],
            fixture["expected"]["first_stage_pressure_ratio"],
            delta=1e-12,
        )
        actual_spectrum = [calculated[key] for key in FINAL_SPECTRUM_KEYS]
        for actual, expected in zip(actual_spectrum, fixture["expected"]["spectrum_db"]):
            self.assertAlmostEqual(actual, expected, delta=1e-4)
        self.assertAlmostEqual(
            calculated["ak_uroven_zvuka_dba_3"],
            fixture["expected"]["a_weighted_db"],
            delta=1e-4,
        )

    def test_all_allowed_stage_counts_produce_finite_final_spectrum(self):
        for stage_count in range(1, 11):
            with self.subTest(stage_count=stage_count):
                input_data = default_input_data()
                input_data["kolichestvo_stupenej_drosselirovaniya_sht"] = stage_count
                calculated, errors, success = calc_new_data(input_data)
                self.assertTrue(success, errors)
                self.assertTrue(
                    all(math.isfinite(calculated[key]) for key in FINAL_SPECTRUM_KEYS)
                )
                self.assertTrue(math.isfinite(calculated["ak_uroven_zvuka_dba_3"]))

    def test_reactive_force_formula_inputs_are_exposed_and_reproducible(self):
        input_data = default_input_data()
        input_data.update(self.fixture["input_overrides"])
        calculated, errors, success = calc_new_data(input_data)
        expected = self.fixture["expected"]

        self.assertTrue(success, errors)
        for key, fixture_key in (
            ("massovyj_rashod_kg_s_out", "mass_flow_kg_s"),
            ("udelnyj_obem_m3_kg_out", "specific_volume_m3_kg"),
            ("diametr_shg_m_out", "diameter_m"),
            ("skorost_na_vyhode_shg_m_s", "exit_speed_m_s"),
            ("r_reaktivnye_sily_n", "reactive_force_n"),
        ):
            self.assertAlmostEqual(calculated[key], expected[fixture_key], delta=1e-9)

        area = math.pi * calculated["diametr_shg_m_out"] ** 2 / 4
        speed = calculated["massovyj_rashod_kg_s_out"] * calculated["udelnyj_obem_m3_kg_out"] / area
        force = speed ** 2 * area / calculated["udelnyj_obem_m3_kg_out"]
        self.assertAlmostEqual(speed, calculated["skorost_na_vyhode_shg_m_s"], delta=1e-12)
        self.assertAlmostEqual(force, calculated["r_reaktivnye_sily_n"], delta=1e-12)

    def test_workbook_circular_cassette_defaults_are_preserved(self):
        values = default_input_data()
        self.assertEqual(values["kolichestvo_kasset"], 1)
        self.assertEqual(values["r1_vnutrennij_radius_1_kassety_mm"], 0.0)
        self.assertEqual(values["t1_tolschina_1_kassety_mm"], 0.0)
        self.assertEqual(values["r2_rasstoyanie_m_u_1_i_2_kassetoj_mm"], 1000.0)
        self.assertEqual(values["t2_tolschina_2_kassety_mm"], 50.0)

    def test_optional_blank_numeric_is_zero_and_comma_decimal_is_supported(self):
        values = default_input_data()
        values.update(
            r3_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm="",
            temperatura_sredy_s="320,5",
            nazvanie_proekta="",
        )
        normalized, errors = normalize_input_data(values)
        self.assertEqual(errors, [])
        self.assertEqual(
            normalized["r3_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm"],
            0.0,
        )
        self.assertEqual(normalized["temperatura_sredy_s"], 320.5)
        self.assertEqual(normalized["nazvanie_proekta"], "")

    def test_required_blank_numeric_is_rejected_instead_of_hidden_as_zero(self):
        values = default_input_data()
        values["rashod"] = ""
        normalized, errors = normalize_input_data(values)
        self.assertNotIn("rashod", normalized)
        self.assertTrue(any(error["header"] == "Расход" for error in errors))

    def test_out_of_range_and_unknown_choice_are_rejected(self):
        values = default_input_data()
        values["davlenie_na_vhode_v_shg_ri_abs_mpa"] = 10.01
        values["sreda"] = "Неизвестная среда"
        _, errors = normalize_input_data(values)
        headers = {error["header"] for error in errors}
        self.assertIn("Давление на входе в ШГ рi (абс.), МПа", headers)
        self.assertIn("Среда", headers)

    def test_gas_constants_and_workbook_kelvin_shift(self):
        expected = {
            "Пар": 461.5,
            "Природный газ": 508.0,
            "Воздух": 287.0,
            "Углекислый газ (СО2)": 188.9,
            "Азот (N2)": 296.8,
            "Кислород (O2)": 259.7,
            "Аргон (Ar)": 208.0,
        }
        for gas, constant in expected.items():
            self.assertEqual(calc_gazovaya_postoyannaya_m2_s2_k({"sreda": gas}), constant)

            input_data = default_input_data()
            input_data["sreda"] = gas
            calculated, errors, success = calc_new_data(input_data)
            self.assertTrue(success, errors)
            self.assertTrue(math.isfinite(calculated["ak_polosa_a_5"]))

        params = {
            "gazovaya_postoyannaya_m2_s2_k": 461.5,
            "temperatura_sredy_s": 320,
            "koeffcient_adiabaty": 1.3,
        }
        expected_speed = math.sqrt(2 * 461.5 * (320 + 273) * (1.3 / 2.3))
        self.assertAlmostEqual(calc_kriticheskaya_skorost_skr_m_s(params), expected_speed)

    def test_output_defaults_and_units_match_tz(self):
        self.assertFalse(GROUPS["Исходный уровень звуковой мощности на входе в глушитель"])
        group = "Уровень звукового давления на расстоянии 1 м. от ШГ, дБ"
        group_items = {
            key: meta for key, meta in OUTPUT_PARAMS.items() if meta.get("group_name") == group
        }
        self.assertTrue(group_items)
        for meta in group_items.values():
            expected_unit = "дБА" if meta.get("header") == "Полоса А" else "дБ"
            self.assertEqual(meta.get("dimension"), expected_unit)

        a_key = next(key for key, meta in group_items.items() if meta.get("header") == "Полоса А")
        frequency_key = next(key for key, meta in group_items.items() if "31,5" in meta.get("header", ""))
        self.assertGreater(
            sort_key_params(a_key, OUTPUT_PARAMS),
            sort_key_params(frequency_key, OUTPUT_PARAMS),
        )

    def test_formula_engine_is_well_below_ten_second_target(self):
        input_data = default_input_data()
        input_data.update(self.fixture["input_overrides"])
        started = time.perf_counter()
        _, errors, success = calc_new_data(input_data)
        elapsed = time.perf_counter() - started
        self.assertTrue(success, errors)
        self.assertLess(elapsed, 5.0)


if __name__ == "__main__":
    unittest.main()
