from __future__ import annotations

import unittest

from scouting_hub.config import FORMATION_CUSTOM, FORMATION_SLOT_POSITIONS, FORMATION_TEMPLATES


class FormationTests(unittest.TestCase):
    def test_catalog_has_many_formations(self) -> None:
        self.assertGreaterEqual(len(FORMATION_TEMPLATES), 15)
        self.assertEqual(FORMATION_CUSTOM, "Personalizada")

    def test_every_preset_has_eleven_unique_slots(self) -> None:
        for name, slots in FORMATION_TEMPLATES.items():
            with self.subTest(formation=name):
                self.assertEqual(len(slots), 11)
                keys = [slot[0] for slot in slots]
                self.assertEqual(len(keys), len(set(keys)))
                for key, label, x, y in slots:
                    self.assertTrue(label)
                    self.assertGreaterEqual(x, 0)
                    self.assertLessEqual(x, 100)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(y, 100)
                    self.assertIn(key, FORMATION_SLOT_POSITIONS)


if __name__ == "__main__":
    unittest.main()
