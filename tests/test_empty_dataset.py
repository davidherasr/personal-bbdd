import unittest
from pathlib import Path

import pandas as pd

from scouting_hub.config import SCHEMAS


class EmptyDatasetTests(unittest.TestCase):
    def test_all_dataset_csvs_are_header_only(self):
        root = Path(__file__).resolve().parents[1]
        for table, columns in SCHEMAS.items():
            df = pd.read_csv(root / "data" / f"{table}.csv", dtype=str)
            self.assertEqual(list(df.columns), columns)
            self.assertEqual(len(df), 0)


if __name__ == "__main__":
    unittest.main()
