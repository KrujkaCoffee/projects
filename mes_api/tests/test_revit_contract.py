import unittest
from unittest.mock import patch

from mes_api.revit_contract import (
    TtlCache,
    build_codes_query,
    build_search_query,
    chunked,
    local_resource_errors,
    normalize_nomenclature_items,
    normalize_code,
    normalize_resource_row,
    normalize_search_query,
    normalize_search_window,
    parse_positive_quantity,
    quote_1c_string,
    quote_odata_string,
    unique_codes,
)


class QueryHelpersTests(unittest.TestCase):
    def test_quotes_1c_and_odata_literals(self):
        self.assertEqual(quote_1c_string('A"B\nC'), '"A""B C"')
        self.assertEqual(quote_odata_string("A'B"), "'A''B'")

    def test_codes_are_deduplicated_and_chunked(self):
        self.assertEqual(unique_codes([" 00-1 ", "00-1", "00-2", None]), ["00-1", "00-2"])
        self.assertEqual([len(part) for part in chunked([str(x) for x in range(401)])], [200, 200, 1])

    def test_invalid_code_characters_are_rejected(self):
        self.assertEqual(normalize_code("00-00179666"), "00-00179666")
        self.assertEqual(normalize_code('00-1" OR 1=1'), "")

    def test_empty_codes_do_not_create_invalid_in_clause(self):
        self.assertIsNone(build_codes_query([]))
        self.assertIsNone(build_codes_query(['00-1" OR 1=1']))

    def test_search_query_has_all_terms_and_fields(self):
        query = build_search_query("труба 108", 500)
        self.assertIn("ВЫБРАТЬ ПЕРВЫЕ 500", query)
        self.assertIn('Номенклатура.Код ПОДОБНО "%труба%"', query)
        self.assertIn('Номенклатура.Артикул ПОДОБНО "%108%"', query)
        self.assertIn("\n            И (", query)
        quoted = build_search_query('x" ИЛИ ИСТИНА', 10)
        self.assertIn('"%x""%"', quoted)

    def test_search_input_and_window_are_bounded(self):
        self.assertEqual(normalize_search_query("  труба   108 "), "труба 108")
        with self.assertRaises(ValueError):
            normalize_search_query("x")
        with self.assertRaises(ValueError):
            normalize_search_query("%%")
        self.assertEqual(normalize_search_window(9999, -10), (500, 0))
        self.assertEqual(normalize_search_window(200, 9999), (200, 1500))
        self.assertEqual(normalize_search_window("bad", "bad"), (200, 0))


class NomenclatureNormalizationTests(unittest.TestCase):
    def test_normalizes_deduplicates_and_ranks_results(self):
        rows = [
            {"Code": "10", "Name": "Труба 10", "Article": "A-10"},
            {"Код": "20", "Наименование": "Труба 20", "НаименованиеПолное": "Труба полная"},
            {"Code": "10", "Name": "Труба 10"},
        ]
        result = normalize_nomenclature_items(rows, "20")
        self.assertEqual([item["Code"] for item in result], ["20", "10"])
        self.assertEqual(result[0]["Extra"], "Труба полная")
        self.assertEqual(result[1]["Extra"], "A-10")


class ResourceContractTests(unittest.TestCase):
    def test_parses_revit_formatted_positive_quantity(self):
        self.assertEqual(parse_positive_quantity("1 234,50 м"), 1234.5)
        self.assertEqual(parse_positive_quantity(3), 3.0)
        self.assertIsNone(parse_positive_quantity("0,00"))
        self.assertIsNone(parse_positive_quantity("DN20"))
        self.assertIsNone(parse_positive_quantity("1 x 2"))

    def test_v2_fields_take_precedence_and_element_ids_are_unique(self):
        row = normalize_resource_row(
            {
                "row": 2,
                "source_row": 17,
                "erp_code": "00-2",
                "ErpCode": "legacy",
                "quantity": "2,5 м",
                "Quantity": "9",
                "element_ids": [101, "101", 102, "bad"],
                "match_state": "matched",
            },
            1,
        )
        self.assertEqual(row.erp_code, "00-2")
        self.assertEqual(row.quantity, 2.5)
        self.assertEqual(row.element_ids, (101, 102))
        self.assertEqual(row.source_row, 17)

    def test_dynamic_values_precede_legacy_fields(self):
        row = normalize_resource_row(
            {
                "values": {
                    "Код 1C-ERP": "00-2",
                    "Количество": "3,25 м",
                    "Единица измерения": "м",
                },
                "ErpCode": "legacy",
                "Quantity": "9",
                "Unit": "шт",
            },
            1,
        )
        self.assertEqual(row.erp_code, "00-2")
        self.assertEqual(row.quantity, 3.25)
        self.assertEqual(row.unit, "м")

    def test_flagged_column_is_used_for_custom_header(self):
        columns = [
            {"order": 0, "is_erp_code": True},
            {"order": 1, "is_quantity": True},
            {"order": 2, "is_unit": True},
        ]
        row = normalize_resource_row(
            {"cells": ["00-3", "7,5", "кг"]},
            1,
            columns,
        )
        self.assertEqual((row.erp_code, row.quantity, row.unit), ("00-3", 7.5, "кг"))

    def test_legacy_row_remains_supported(self):
        row = normalize_resource_row({"ErpCode": "00-1", "Quantity": "4"}, 3)
        fields, errors = local_resource_errors([row], contract_version=1)
        self.assertEqual(fields, {})
        self.assertEqual(errors, [])

    def test_v2_reports_source_row_and_ambiguous_association(self):
        row = normalize_resource_row(
            {
                "row": 1,
                "source_row": 74,
                "erp_code": "00-1",
                "quantity": "1",
                "match_state": "no_exact_match",
                "element_ids": [],
            },
            1,
        )
        _, errors = local_resource_errors([row], contract_version=2)
        self.assertEqual({error["source_row"] for error in errors}, {74})
        self.assertTrue(any("однозначной связи" in error["msg"] for error in errors))
        self.assertTrue(any("ElementId" in error["msg"] for error in errors))

    def test_duplicate_element_id_is_rejected(self):
        first = normalize_resource_row(
            {"row": 1, "source_row": 7, "erp_code": "A", "quantity": "1", "match_state": "matched", "element_ids": [10]},
            1,
        )
        second = normalize_resource_row(
            {"row": 2, "source_row": 8, "erp_code": "B", "quantity": "1", "match_state": "matched", "element_ids": [10]},
            2,
        )
        _, errors = local_resource_errors([first, second], contract_version=2)
        self.assertTrue(any("разные ERP-коды" in error["msg"] for error in errors))

    def test_visually_identical_rows_with_same_code_are_allowed(self):
        first = normalize_resource_row(
            {"row": 1, "source_row": 7, "erp_code": "A", "quantity": "1", "match_state": "matched", "element_ids": [10, 11]},
            1,
        )
        second = normalize_resource_row(
            {"row": 2, "source_row": 8, "erp_code": "A", "quantity": "1", "match_state": "matched", "element_ids": [10, 11]},
            2,
        )
        _, errors = local_resource_errors([first, second], contract_version=2)
        self.assertEqual(errors, [])


class TtlCacheTests(unittest.TestCase):
    def test_cache_expires_and_pop_consumes_value(self):
        cache = TtlCache(ttl_seconds=10, max_items=2)
        with patch("mes_api.revit_contract.time.monotonic", return_value=100):
            cache.set("a", 1)
            self.assertEqual(cache.get("a"), 1)
            self.assertEqual(cache.pop("a"), 1)
            self.assertIsNone(cache.get("a"))
            cache.set("b", 2)
        with patch("mes_api.revit_contract.time.monotonic", return_value=111):
            self.assertIsNone(cache.get("b"))


if __name__ == "__main__":
    unittest.main()
