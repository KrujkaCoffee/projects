import unittest

from components.excel_compat import excel_round, excel_rounddown, excel_roundup


class ExcelCompatibilityTests(unittest.TestCase):
    def test_round_uses_excel_half_away_from_zero(self):
        self.assertEqual(excel_round(2.5), 3.0)
        self.assertEqual(excel_round(-2.5), -3.0)
        self.assertEqual(excel_round(1.25, 1), 1.3)
        self.assertEqual(excel_round(-1.25, 1), -1.3)

    def test_roundup_is_away_from_zero(self):
        self.assertEqual(excel_roundup(1.21, 1), 1.3)
        self.assertEqual(excel_roundup(-1.21, 1), -1.3)

    def test_rounddown_is_toward_zero(self):
        self.assertEqual(excel_rounddown(1.29, 1), 1.2)
        self.assertEqual(excel_rounddown(-1.29, 1), -1.2)


if __name__ == "__main__":
    unittest.main()
