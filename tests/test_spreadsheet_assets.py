import csv
import subprocess
import unittest
import zipfile
from pathlib import Path


class SpreadsheetAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(['python3', 'spreadsheet_model/build_workbook.py'], check=True)

    def test_required_spreadsheet_files_exist(self) -> None:
        base = Path('spreadsheet_model')
        required = [
            '00_parameters.csv',
            '01_goods.csv',
            '02_worlds.csv',
            '03_profiles.csv',
            '04_events_table.csv',
            'SPREADSHEET_GUIDE.md',
            'build_workbook.py',
            'hyperion_spreadsheet_model.xlsx',
        ]
        for filename in required:
            self.assertTrue((base / filename).exists(), filename)

    def test_goods_rows_have_expected_columns(self) -> None:
        path = Path('spreadsheet_model/01_goods.csv')
        with path.open(newline='', encoding='utf-8') as fh:
            rows = list(csv.DictReader(fh))
        self.assertGreaterEqual(len(rows), 8)
        self.assertIn('good', rows[0])
        self.assertIn('base_price', rows[0])
        self.assertIn('volatility', rows[0])
        self.assertIn('strategic', rows[0])

    def test_push_fix_script_exists(self) -> None:
        path = Path('scripts/fix_push_binary_issue.sh')
        self.assertTrue(path.exists())

    def test_single_workbook_contains_multiple_sheets(self) -> None:
        path = Path('spreadsheet_model/hyperion_spreadsheet_model.xlsx')
        with zipfile.ZipFile(path, 'r') as zf:
            names = set(zf.namelist())
        self.assertIn('xl/workbook.xml', names)
        self.assertIn('xl/worksheets/sheet1.xml', names)
        self.assertIn('xl/worksheets/sheet6.xml', names)


if __name__ == '__main__':
    unittest.main()
