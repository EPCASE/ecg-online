import unittest
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import collector


class CollectorMetricsSchemaTest(unittest.TestCase):
    def test_timing_columns_are_append_only_and_unique(self):
        self.assertEqual(len(collector.LOG_COLS), len(set(collector.LOG_COLS)))
        self.assertEqual(collector.LOG_COLS[:8], [
            "horodatage", "session", "cas", "titre", "reponse",
            "score", "correspondance", "backend",
        ])
        for column in (
            "t_reflexion_s", "t_total_s", "t_premiere_saisie_active_s",
            "t_autonome_s", "t_autonome_actif_s", "t_total_actif_s",
            "t_hors_app_s", "mises_arriere_plan", "appareil",
            "brouillon_restaure", "ouvertures_visionneuse", "zooms_visionneuse",
        ):
            self.assertIn(column, collector.LOG_COLS)

    def test_last_column_range_supports_more_than_z(self):
        self.assertEqual(collector._column_label(len(collector.LOG_COLS)), "AI")

    def test_write_row_matches_header_order(self):
        class LogSheet:
            def __init__(self):
                self.row = None

            def append_row(self, row, **_kwargs):
                self.row = row

        class PerCaseSheet:
            def col_values(self, _column):
                return ["cas", "23"]

            def row_values(self, _row):
                return ["23", "Cas 23"]

            def update_cell(self, *_args):
                return None

        log = LogSheet()
        per_case = PerCaseSheet()

        class Spreadsheet:
            def worksheet(self, title):
                return log if title == "reponses" else per_case

        meta = {
            "t_total_actif_s": 42,
            "t_hors_app_s": 7,
            "appareil": "telephone",
            "zooms_visionneuse": 3,
        }
        with mock.patch.object(collector, "_get_spreadsheet", return_value=Spreadsheet()), \
             mock.patch.object(collector, "_ENSURED", True):
            collector._write(23, "Cas 23", "réponse", 80, "ok", "test", "session", meta)

        self.assertEqual(len(log.row), len(collector.LOG_COLS))
        row = dict(zip(collector.LOG_COLS, log.row))
        self.assertEqual(row["t_total_actif_s"], 42)
        self.assertEqual(row["t_hors_app_s"], 7)
        self.assertEqual(row["appareil"], "telephone")
        self.assertEqual(row["zooms_visionneuse"], 3)


if __name__ == "__main__":
    unittest.main()
