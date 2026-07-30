import unittest

import pandas as pd

from scouting_hub.config import SCHEMAS
from scouting_hub.scoring import heritage_metrics


class HeritageScoringTests(unittest.TestCase):
    def _obs(self, rating="7.0", minutes="90", mvp="No", comp="30", match="m1"):
        row = {col: "" for col in SCHEMAS["observations"]}
        row.update({
            "match_id": match,
            "global_rating": rating,
            "minutes_observed": minutes,
            "mvp": mvp,
            "competition_value": comp,
        })
        return row

    def test_mvp_and_competition_raise_score_without_explosion(self):
        player = pd.Series({"age": "22"})
        normal = heritage_metrics(player, pd.DataFrame([self._obs()]))
        stronger = heritage_metrics(player, pd.DataFrame([self._obs(mvp="Sí", comp="45")]))
        self.assertGreater(stronger["heritage_score"], normal["heritage_score"])
        self.assertLessEqual(stronger["heritage_score"], 100)

    def test_more_evidence_improves_stability_component(self):
        player = pd.Series({"age": "24"})
        one = heritage_metrics(player, pd.DataFrame([self._obs(rating="8.0")]))
        three = heritage_metrics(player, pd.DataFrame([
            self._obs(rating="8.0", match="m1"),
            self._obs(rating="8.0", match="m2"),
            self._obs(rating="8.0", match="m3"),
        ]))
        self.assertGreater(three["heritage_score"], one["heritage_score"])
        self.assertEqual(three["matches_seen"], 3)


if __name__ == "__main__":
    unittest.main()
