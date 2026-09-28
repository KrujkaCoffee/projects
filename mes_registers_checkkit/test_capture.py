"""Offline tests of the live adapter, using the actual native register and SQL."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS

from cases import base
from capture_live import assess_capture, capture_matrix, capture_one, month_bounds
from engine import (Api, Gateway, Sources, create_fixture, open_connections,
                    test_models)


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Sources()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="capture_check_")
        self.directory = Path(self.temp.name)
        self.case = base()
        self.paths = create_fixture(self.case, self.directory)
        self.connections = open_connections(self.paths)
        self.gateway = Gateway(self.sources, self.connections)
        original_query = self.gateway.custom_request_c
        def query(db, sql, **kwargs):
            if 'FROM "Должности"' in sql:
                return [{"Ref_Key": k, "Наименование": v} for k, v in self.case["dimensions"]["positions"].items()]
            if 'FROM "Подразделения"' in sql:
                return [{"Подразделение_Key": k, "Наименование": v} for k, v in self.case["dimensions"]["departments"].items()]
            return original_query(db, sql, **kwargs)
        self.csq = NS(custom_request_c=query)
        self.catalog = self.sources.native.get_mes_registers(models_module=test_models(),
                    executor=self.sources.native.SqliteExecutor(self.paths))
        self.vir = ModuleType("capture_test_vir")
        self.vir.__file__ = str(self.sources.root / "Cust_virbotka.py")
        self.vir.CSQ = self.csq
        self.vir.CMS = NS(dict_emploee_full=lambda db: copy.deepcopy(self.case["employee_current"]))
        self.vir.APIERP = Api(self.case["erp"], {})
        self.vir.USRCNF = NS(Config=NS(place=NS(Имя="Завод А", poki=0,
                                  КодыНарядов=NS(НеподтвержденныйВнеплан=1))))

    def tearDown(self):
        for conn in self.connections.values(): conn.close()
        self.temp.cleanup()

    def capture(self, **changes):
        args = dict(vir=self.vir, registers=self.catalog, db="Naryad", db_users="BD_users",
                    db_kplan="DB_kplan", podrazdelenie="Цех 1", organization="Завод А",
                    organization_refs=["o1"], nach=self.case["request"]["nach"],
                    konec=self.case["request"]["konec"], as_of=self.case["request"]["as_of"],
                    out_file=self.directory/"capture.json", sources=self.sources)
        args.update(changes)
        return capture_one(**args)

    def test_stable_match_and_replay(self):
        output = self.capture()
        self.assertEqual(output["comparison"]["verdict"], "MATCH")
        saved = json.loads((self.directory/"capture.json").read_text())
        self.assertEqual(assess_capture(saved), output["comparison"])
        self.assertEqual([r["side"] for r in saved["runs"]], ["old", "new", "old", "new"])

    def test_stable_difference(self):
        self.case["erp"]["data"] = self.case["erp"]["data"][:1]
        self.assertEqual(self.capture()["comparison"]["verdict"], "DIFFERENT")

    def test_fallback_not_approved(self):
        self.case["erp"]["status"] = 500
        self.assertEqual(self.capture()["comparison"]["verdict"], "INCONCLUSIVE")

    def test_missing_mapping_blocked(self):
        self.case["dimensions"]["positions"].pop("j1")
        self.assertEqual(self.capture()["comparison"]["verdict"], "BLOCKED")

    def test_live_erp_changed(self):
        responses = [copy.deepcopy(self.case["erp"]["data"]), self.case["erp"]["data"][:1]]
        self.vir.APIERP = NS(get_wet_request=lambda **kwargs: (200, {"data": responses.pop(0)}))
        self.assertEqual(self.capture()["comparison"]["verdict"], "UNSTABLE")

    def test_current_employee_dictionary_changed(self):
        dictionaries = [self.case["employee_current"], self.case["employee_current"], {}, {}]
        self.vir.CMS = NS(dict_emploee_full=lambda db: copy.deepcopy(dictionaries.pop(0)))
        self.assertEqual(self.capture()["comparison"]["verdict"], "UNSTABLE")

    def test_repair_blocked_and_database_unchanged(self):
        # Mutation is restricted to fixture setup, before the four read-only runs.
        import sqlite3
        with sqlite3.connect(self.paths["Naryad"]) as conn:
            conn.execute('UPDATE jurnal SET "Подытог_нормы"=NULL WHERE "Пномер"=1')
        before = self.paths["Naryad"].read_bytes()
        self.assertEqual(self.capture()["comparison"]["verdict"], "BLOCKED")
        self.assertEqual(self.paths["Naryad"].read_bytes(), before)

    def test_matrix_preserves_blocked_month(self):
        result = capture_matrix(vir=self.vir, registers=self.catalog,
            db="Naryad", db_users="BD_users", db_kplan="DB_kplan", podrazdeleniya=["Цех 1"],
            organization="Завод А", organization_refs=["o1"], months=["2026-01", "2026-02"],
            out_dir=self.directory/"matrix", as_of=self.case["request"]["as_of"])
        self.assertEqual([r["verdict"] for r in result["cases"]], ["MATCH", "BLOCKED"])
        self.assertFalse(result["all_cases_matched"])
        self.assertTrue((self.directory/"matrix"/"index.json").is_file())

    def test_calendar_boundaries(self):
        self.assertEqual(month_bounds("2024-02"), ("2024-02-01 05:00:00", "2024-03-01 04:59:59"))
        self.assertEqual(month_bounds("2025-12"), ("2025-12-01 05:00:00", "2026-01-01 04:59:59"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
