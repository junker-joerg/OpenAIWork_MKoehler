import csv
import json
import unittest
from pathlib import Path


class SpreadsheetAssetsTests(unittest.TestCase):
    def test_required_spreadsheet_files_exist(self) -> None:
        base = Path('spreadsheet_model')
        required = [
            '00_parameters.csv',
            '01_goods.csv',
            '02_worlds.csv',
            '03_profiles.csv',
            '04_events_table.csv',
            'SPREADSHEET_GUIDE.md',
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

    def test_simulation_metadata_is_valid(self) -> None:
        with Path('hyperion_simulation_config.json').open(encoding='utf-8') as fh:
            metadata = json.load(fh)
        self.assertEqual(metadata['years'], 30)
        self.assertEqual(metadata['run_seeds'], [7, 8, 9, 10, 11])
        self.assertEqual(metadata['model_data'], 'spreadsheet_model')


if __name__ == '__main__':
    unittest.main()
