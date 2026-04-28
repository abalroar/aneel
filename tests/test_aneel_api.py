import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from aneel_power_watch.aneel_api import add_total_time, enrich_states


class AneelApiHelpersTest(unittest.TestCase):
    def test_enrich_states_adds_region(self):
        df = pd.DataFrame([{"uf_code": "35", "ocorrencias": 10}])
        enriched = enrich_states(df)
        self.assertEqual(enriched.loc[0, "uf"], "SP")
        self.assertEqual(enriched.loc[0, "region"], "Sudeste")

    def test_add_total_time_sums_components(self):
        df = pd.DataFrame(
            [
                {
                    "preparo_medio_min": "10",
                    "deslocamento_medio_min": "20.5",
                    "execucao_medio_min": "30",
                }
            ]
        )
        result = add_total_time(df)
        self.assertAlmostEqual(result.loc[0, "tempo_total_medio_min"], 60.5)


if __name__ == "__main__":
    unittest.main()
