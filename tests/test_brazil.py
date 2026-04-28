import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aneel_power_watch.brazil import ibge_prefix_to_region, ibge_prefix_to_uf, states_records


class BrazilMappingTest(unittest.TestCase):
    def test_maps_ibge_prefix_to_uf(self):
        self.assertEqual(ibge_prefix_to_uf("35"), "SP")
        self.assertEqual(ibge_prefix_to_uf(33), "RJ")
        self.assertEqual(ibge_prefix_to_uf("53"), "DF")

    def test_maps_ibge_prefix_to_region(self):
        self.assertEqual(ibge_prefix_to_region("15"), "Norte")
        self.assertEqual(ibge_prefix_to_region("29"), "Nordeste")
        self.assertEqual(ibge_prefix_to_region("43"), "Sul")

    def test_all_states_have_coordinates(self):
        records = states_records()
        self.assertEqual(len(records), 27)
        self.assertTrue(all(record["lat"] and record["lon"] for record in records))


if __name__ == "__main__":
    unittest.main()
