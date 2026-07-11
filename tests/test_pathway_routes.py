"""Smoke tests sans réseau pour les routes et données des parcours."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ECG_COLLECT", "0")
os.environ["CURATION_TOKEN"] = "test-curation-token"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import server as server_module  # noqa: E402
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
        self.assertEqual(len(catalog["pathways"]), 5)

        for entry in catalog["pathways"]:
            response = self.get_response(entry["config_url"])
            self.assertEqual(response.status_code, 200, entry["config_url"])
            self.assertEqual(response.get_json()["id"], entry["id"])

    def test_public_cases_do_not_disclose_reference(self) -> None:
        for case_num in (8, 9, 10, 13, 14, 15, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49):
            response = self.get_response(f"/api/case/{case_num}")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertNotIn("interpretation_ref", payload)
            self.assertNotIn("commentaires", payload)
            self.assertNotIn("qcm", payload)
            self.assertNotIn("referentiel", payload)
            self.assertNotIn("second_trace", payload)
            self.assertEqual(payload["titre"], f"Cas {case_num}")

    def test_case_49_context_stops_before_post_cardioversion_findings(self) -> None:
        response = self.get_response("/api/case/49")
        self.assertEqual(response.status_code, 200)
        context = response.get_json()["contexte"]
        self.assertEqual(context, "Consultation pour palpitations depuis quelques jours.")
        self.assertNotIn("bloc de branche", context.lower())

    def test_full_case_requires_teacher_token(self) -> None:
        response = self.get_response("/api/case/14/full")
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            "/api/case/14/full",
            headers={"X-Curation-Token": "test-curation-token"},
        )
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)
        self.assertIn("interpretation_ref", response.get_json())

    def test_full_case_stays_closed_without_configured_token(self) -> None:
        original = server_module.CURATION_TOKEN
        try:
            server_module.CURATION_TOKEN = ""
            response = self.get_response("/api/case/14/full")
            self.assertEqual(response.status_code, 403)
        finally:
            server_module.CURATION_TOKEN = original

    def test_primary_ecg_assets_exist(self) -> None:
        for case_num in (8, 9, 10, 13, 14, 15, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49):
            case_response = self.get_response(f"/api/case/{case_num}")
            self.assertEqual(case_response.status_code, 200, case_num)
            images = case_response.get_json().get("images", [])
            primary = next((name for name in images if "_p" not in name), None)
            self.assertIsNotNone(primary, case_num)
            response = self.get_response(f"/images/{primary}")
            self.assertEqual(response.status_code, 200, primary)


if __name__ == "__main__":
    unittest.main()
