import unittest
import pandas as pd
from scouting_hub.config import SCHEMAS
from scouting_hub.scoring import heritage_metrics

class ExcelIntegrationTests(unittest.TestCase):
    def _row(self, match, rating, minutes=90, mvp="No", comp=35):
        row = {col: "" for col in SCHEMAS["observations"]}
        row.update({"match_id": match, "global_rating": str(rating), "minutes_observed": str(minutes), "mvp": mvp, "competition_value": str(comp)})
        return row

    def test_dim_jugadores_metrics(self):
        observations = pd.DataFrame([
            self._row("m1", 8, 90, "Sí", 40),
            self._row("m2", 6, 60, "No", 40),
        ])
        result = heritage_metrics(pd.Series({"age": "22"}), observations)
        self.assertEqual(result["matches_seen"], 2)
        self.assertEqual(result["total_minutes"], 150)
        self.assertEqual(result["rating_sum"], 14)
        self.assertEqual(result["average_rating"], 7)
        self.assertEqual(result["mvp_count"], 1)
        self.assertEqual(result["avg_minutes"], 75)
        self.assertGreater(result["legacy_raw"], 0)
        self.assertTrue(0 <= result["heritage_score"] <= 100)

if __name__ == "__main__":
    unittest.main()
