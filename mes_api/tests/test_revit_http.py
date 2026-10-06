"""HTTP contract tests; ERP dependencies are replaced, FastAPI/Pydantic are real."""
import copy
import importlib.util
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_revit_router import _load_router_with_stubs


@unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"),
                     "Install FastAPI and httpx to run HTTP contract tests")
class RevitHttpTests(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        self.router = _load_router_with_stubs(real_http=True)
        app = FastAPI()
        app.include_router(self.router.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.router.COE = SimpleNamespace(OrdersComposit=lambda base: SimpleNamespace(
            get_response=lambda *args, **kwargs: (200, [])))
        self.article = "11111111-1111-1111-1111-111111111111"
        self.article_b = "33333333-3333-3333-3333-333333333333"
        self.payload = {
            "action": "upload_resource_map", "contract_version": 2,
            "title": "Ресурсная тест", "creator": "Иван Иванов",
            "start_date": "2026-09-27", "end_date": "2026-09-28",
            "cost_article_ref": self.article,
            "output_product": {"code": "OUT", "name": "Изделие", "unit": "шт"},
            "schedule": {"name": "Спецификация", "field_mapping_exact": True},
            "rows": [
                {"row": 1, "source_row": 7, "erp_code": "", "quantity": "1",
                 "match_state": "matched", "element_ids": [10]},
                {"row": 2, "source_row": 8, "erp_code": "A", "quantity": "2,5 м",
                 "match_state": "matched", "element_ids": [20]},
            ],
        }
        self.fetch = self._patch("_fetch_nomenclature", return_value={
            "out": {"Code": "OUT"}, "a": {"Code": "A"}})
        self._patch("_load_cost_articles", return_value=[{
            "Ref_Key": self.article, "Description": "Сырье"},
            {"Ref_Key": self.article_b, "Description": "Упаковка"}])
        self.upload = self._patch("upload_resource", return_value={"e1c_link": "e1c://created"})

    def _patch(self, name, **kwargs):
        patcher = patch.object(self.router, name, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def post(self, action, payload=None):
        return self.client.post("/api/v1/revit/resource/" + action + "/",
                                json=self.payload if payload is None else payload)

    def test_validate_then_cached_create_skip_identical_rows(self):
        self.payload["skip_unmapped_rows"] = True
        checked = self.post("validate")
        self.assertEqual(checked.status_code, 200, checked.text)
        self.assertEqual(checked.json()["skipped_source_rows"], [7])
        created = self.post("create")
        self.assertEqual(created.status_code, 200, created.text)
        self.fetch.assert_called_once()
        rows = self.upload.call_args.args[1]
        self.assertEqual([(row.source_row, row.erp_code, row.quantity) for row in rows], [(8, "A", 2.5)])
        self.assertEqual(created.json()["export_summary"], {
            "exported_rows": 1, "skipped_rows": 1, "skipped_source_rows": [7]})

    def test_distinct_row_articles_survive_direct_and_cached_create(self):
        self.payload.pop("cost_article_ref")
        self.payload["rows"][0]["erp_code"] = "A"
        self.payload["rows"][0]["cost_article_ref"] = self.article
        self.payload["rows"][1]["cost_article_ref"] = self.article_b
        for validate_first in (False, True):
            with self.subTest(validate_first=validate_first):
                self.fetch.reset_mock()
                if validate_first:
                    checked = self.post("validate")
                    self.assertEqual(checked.status_code, 200, checked.text)
                    self.assertTrue(checked.json()["row_cost_articles_supported"])
                created = self.post("create")
                self.assertEqual(created.status_code, 200, created.text)
                self.fetch.assert_called_once()
                rows = self.upload.call_args.args[1]
                self.assertEqual([(row.source_row, row.cost_article_ref) for row in rows],
                                 [(7, self.article), (8, self.article_b)])

    def test_row_article_overrides_common_article_and_errors_point_to_source_row(self):
        self.payload["skip_unmapped_rows"] = True
        self.payload["rows"][1]["cost_article_ref"] = self.article_b
        self.payload["cost_article_ref"] = "unused-invalid-header"
        self.assertEqual(self.post("validate").status_code, 200)
        self.payload["cost_article_ref"] = self.article
        for invalid in ("", "bad-uuid", "22222222-2222-2222-2222-222222222222"):
            with self.subTest(invalid=invalid):
                self.payload["rows"][1]["cost_article_ref"] = invalid
                response = self.post("create")
                self.assertEqual(response.status_code, 400)
                errors = response.json()["table_errors"]
                self.assertEqual([(row["row"], row["source_row"]) for row in errors], [(2, 8)])
                self.assertIn("Статья калькуляции", errors[0]["msg"])
        self.upload.assert_not_called()

    def test_row_article_change_invalidates_validation_cache(self):
        self.payload["skip_unmapped_rows"] = True
        self.payload["rows"][1]["cost_article_ref"] = self.article
        self.assertEqual(self.post("validate").status_code, 200)
        self.payload["rows"][1]["cost_article_ref"] = "22222222-2222-2222-2222-222222222222"
        response = self.post("create")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["table_errors"][0]["source_row"], 8)
        self.upload.assert_not_called()

    def test_skipped_unmapped_row_does_not_require_an_article(self):
        self.payload["skip_unmapped_rows"] = True
        self.payload["rows"][0]["cost_article_ref"] = "bad-uuid"
        self.payload["rows"][1]["cost_article_ref"] = self.article_b
        response = self.post("create")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([row.cost_article_ref for row in self.upload.call_args.args[1]], [self.article_b])

    def test_articles_endpoint_promotes_server_default_without_changing_cached_order(self):
        with patch.dict(self.router.os.environ, {"REVIT_COST_ARTICLE_DEFAULT_REF": self.article_b}):
            response = self.post("cost_articles", {"action": "get_cost_articles"})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([row["Ref_Key"] for row in response.json()], [self.article_b, self.article])
        with patch.dict(self.router.os.environ, {"REVIT_COST_ARTICLE_DEFAULT_REF": ""}):
            response = self.post("cost_articles", {})
            self.assertEqual([row["Ref_Key"] for row in response.json()], [self.article, self.article_b])

    def test_direct_create_applies_same_skip_rule(self):
        self.payload["skip_unmapped_rows"] = True
        self.payload["rows"][0]["erp_code"] = "-"
        created = self.post("create")
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual([row.erp_code for row in self.upload.call_args.args[1]], ["A"])

    def test_default_is_strict_and_no_materials_means_no_create(self):
        response = self.post("create")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["table_errors"][0]["source_row"], 7)
        self.payload["skip_unmapped_rows"] = True
        self.payload["rows"][1]["erp_code"] = ""
        response = self.post("create")
        self.assertEqual(response.status_code, 400)
        self.assertIn("rows", response.json()["field_errors"])
        self.upload.assert_not_called()

    def test_unknown_and_malformed_filled_codes_are_never_silently_skipped(self):
        self.payload["skip_unmapped_rows"] = True
        for code in ("UNKNOWN", 'bad"code'):
            with self.subTest(code=code):
                self.payload["rows"][1]["erp_code"] = code
                response = self.post("create")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["table_errors"][0]["source_row"], 8)
        self.upload.assert_not_called()

    def test_skipping_does_not_bypass_mapping_or_quantity_checks(self):
        self.payload["skip_unmapped_rows"] = True
        self.payload["rows"][1]["match_state"] = "ambiguous"
        self.payload["rows"][1]["element_ids"] = []
        self.payload["rows"][1]["quantity"] = "-2"
        response = self.post("create")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.json()["table_errors"]), 3)
        self.upload.assert_not_called()

    def test_confirmation_and_article_are_part_of_validation_fingerprint(self):
        self.payload["skip_unmapped_rows"] = True
        self.assertEqual(self.post("validate").status_code, 200)
        changed = copy.deepcopy(self.payload)
        changed["skip_unmapped_rows"] = False
        self.assertEqual(self.post("create", changed).status_code, 400)
        changed = copy.deepcopy(self.payload)
        changed["cost_article_ref"] = "22222222-2222-2222-2222-222222222222"
        response = self.post("create", changed)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cost_article_ref", response.json()["field_errors"])
        self.upload.assert_not_called()

    def test_skip_flag_requires_a_boolean(self):
        self.payload["skip_unmapped_rows"] = "false"
        self.assertEqual(self.post("create").status_code, 422)
        self.upload.assert_not_called()

    def test_legacy_client_can_omit_new_fields(self):
        self.payload.pop("cost_article_ref")
        self.payload.pop("schedule")
        self.payload["contract_version"] = 1
        self.payload["rows"] = [{"ErpCode": "A", "Quantity": "2"}]
        response = self.post("create")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(self.upload.call_args.args[0].cost_article_ref)
        self.assertFalse(self.upload.call_args.args[0].skip_unmapped_rows)

    def test_source_defaults_to_main_and_trailing_slash_does_not_redirect(self):
        self.router._reference_cache.set("types_raw", [])
        with patch.object(self.router, "_filter_kinds_for_source", return_value=[]) as filtering:
            for url, body, source in (
                ("/api/v1/revit/types", {}, "main"),
                ("/api/v1/revit/types/", {"source": "revit_mapping"}, "revit_mapping"),
            ):
                response = self.client.post(url, json=body, follow_redirects=False)
                self.assertEqual(response.status_code, 200)
                filtering.assert_called_with([], source)


if __name__ == "__main__":
    unittest.main()
