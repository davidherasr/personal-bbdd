import unittest

import pandas as pd

from scouting_hub.config import SCHEMAS
from scouting_hub.scoring import adjusted_decision_score, scoring_breakdown


class ScoringTests(unittest.TestCase):
    def test_low_confidence_shrinks_toward_neutral(self):
        self.assertLess(abs(adjusted_decision_score(90, 10) - 50), abs(90 - 50))
        self.assertLess(abs(adjusted_decision_score(20, 10) - 50), abs(20 - 50))

    def test_zero_rating_is_not_treated_as_real_score(self):
        player = pd.Series({"primary_position": "MC", "primary_role": "Mediocentro organizador", "potential_rating": "5", "position_need": "5"})
        obs = pd.DataFrame([{col: "" for col in SCHEMAS["observations"]}])
        obs.loc[0, ["minutes_observed", "technical_rating", "tactical_rating", "global_rating"]] = ["90", "8", "8", "0"]
        score = scoring_breakdown(player, obs, pd.DataFrame(columns=SCHEMAS["role_assessments"]))
        self.assertGreater(score["level"], 70)


if __name__ == "__main__":
    unittest.main()
