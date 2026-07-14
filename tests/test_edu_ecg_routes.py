"""Feature-flag and packaged-content tests for the Edu-ECG introduction."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ECG_COLLECT", "0")
os.environ.setdefault("CURATION_TOKEN", "test-curation-token")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.edu_ecg import SUPPORTED_ACTIVITY_TYPES, validate_content  # noqa: E402
from app.server import create_app  # noqa: E402


class EduEcgRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_flag = os.environ.get("EDU_ECG_INTRO_COURSE")
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        if self.previous_flag is None:
            os.environ.pop("EDU_ECG_INTRO_COURSE", None)
        else:
            os.environ["EDU_ECG_INTRO_COURSE"] = self.previous_flag

    def get_response(self, path: str):
        response = self.client.get(path)
        self.addCleanup(response.close)
        return response

    def test_feature_is_disabled_by_default(self) -> None:
        os.environ.pop("EDU_ECG_INTRO_COURSE", None)
        self.assertEqual(self.get_response("/edu-ecg").status_code, 404)
        self.assertEqual(self.get_response("/api/edu-ecg/course").status_code, 404)

    def test_enabled_course_serves_module_zero_and_only_m2_2_m2_3(self) -> None:
        os.environ["EDU_ECG_INTRO_COURSE"] = "1"
        page = self.get_response("/edu-ecg")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Edu-ECG", page.get_data(as_text=True))

        course = self.get_response("/api/edu-ecg/course").get_json()
        self.assertEqual([item["id"] for item in course["available_modules"]], ["M0", "M2"])
        self.assertEqual(course["available_modules"][0]["activity_count"], 5)

        module2 = self.get_response("/api/edu-ecg/modules/M2").get_json()
        self.assertEqual(
            [item["id"] for item in module2["activities"]],
            ["M2_PROBE_03", "M2_PROBE_04"],
        )

    def test_only_approved_packaged_assets_are_served(self) -> None:
        os.environ["EDU_ECG_INTRO_COURSE"] = "true"
        approved = self.get_response("/api/edu-ecg/assets/approved/plans_frontal_horizontal.png")
        self.assertEqual(approved.status_code, 200)
        missing = self.get_response("/api/edu-ecg/assets/placeholders/m0_clean_ecg.png")
        self.assertEqual(missing.status_code, 404)

    def test_all_documents_validate_and_all_activity_types_are_known(self) -> None:
        content = validate_content()
        seen_types = {
            activity["activity_type"]
            for module in content["modules"].values()
            for activity in module["activities"]
        }
        self.assertTrue(seen_types.issubset(SUPPORTED_ACTIVITY_TYPES))
        self.assertEqual(len(content["modules"]), 8)


if __name__ == "__main__":
    unittest.main()
