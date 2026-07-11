"""Smoke tests sans réseau pour les routes et données des parcours."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ECG_COLLECT", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.server import create_app  # noqa: E402


class PathwayRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def get_response(self, path: str):
        response = self.client.get(path)
        self.addCleanup(response.close)
        return response

    def test_catalog_and_pages_are_served(self) -> None:
        response = self.get_response("/static/pathways.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Carte de compétences", response.get_data(as_text=True))

        response = self.get_response("/static/pathway.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Tous les parcours", response.get_data(as_text=True))

        response = self.get_response("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/static/pathways.html", response.get_data(as_text=True))

    def test_all_catalog_configs_are_available(self) -> None:
        catalog_response = self.get_response("/static/pathways.json")
        self.assertEqual(catalog_response.status_code, 200)
        catalog = catalog_response.get_json()
        self.assertEqual(catalog["default_id"], "bav-foundations")
        self.assertEqual(len(catalog["pathways"]), 3)

        for entry in catalog["pathways"]:
            response = self.get_response(entry["config_url"])
            self.assertEqual(response.status_code, 200, entry["config_url"])
            self.assertEqual(response.get_json()["id"], entry["id"])

    def test_public_cases_do_not_disclose_reference(self) -> None:
        for case_num in (37, 38, 39, 40, 41, 42, 43, 44):
            response = self.get_response(f"/api/case/{case_num}")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertNotIn("interpretation_ref", payload)
            self.assertNotIn("qcm", payload)
            self.assertEqual(payload["titre"], f"Cas {case_num}")

    def test_primary_ecg_assets_exist(self) -> None:
        for case_num in (37, 38, 39, 40, 41, 42, 43, 44):
            response = self.get_response(f"/images/cas_{case_num}.png")
            self.assertEqual(response.status_code, 200, case_num)


if __name__ == "__main__":
    unittest.main()
