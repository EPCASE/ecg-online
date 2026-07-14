"""Unit tests for the private deterministic Edu-ECG scorer."""
from __future__ import annotations

import unittest

from app.edu_ecg_scoring import evaluate, is_complete


def activity(kind, response, scoring=None):
    return {
        "id": f"TEST_{kind}",
        "activity_type": kind,
        "response": response,
        "scoring": scoring or {},
    }


class EduEcgScoringTest(unittest.TestCase):
    def test_closed_answers_are_deterministic(self) -> None:
        self.assertTrue(evaluate(activity("single_choice", {"correct_option_id": "b"}), {"choice": "b"})["correct"])
        self.assertTrue(evaluate(activity("multiple_choice", {"correct_option_ids": ["a", "c"]}), {"choices": ["c", "a"]})["correct"])
        self.assertTrue(evaluate(activity("card_sorting", {"cards": [{"id": "v1", "category": "horizontal"}]}), {"assignments": {"v1": "horizontal"}})["correct"])
        self.assertTrue(evaluate(activity("ordering_cards", {"correct_order": ["a", "b"]}), {"order": ["a", "b"]})["correct"])
        self.assertTrue(evaluate(activity("matching_pairs", {"correct_pairs": [["P", "oreillettes"]]}), {"pairs": {"P": "oreillettes"}})["correct"])
        self.assertTrue(evaluate(activity("image_hotspot_labeling", {"correct_labels": {"p": "P"}}), {"labels": {"p": "P"}})["correct"])

    def test_free_answer_is_recorded_but_not_scored(self) -> None:
        result = evaluate(
            activity("short_answer", {"expected_concepts": ["temps", "amplitude"]}),
            {"text": "temps et amplitude"},
        )
        self.assertFalse(result["evaluated"])
        self.assertIsNone(result["percent"])

    def test_critical_errors_require_an_explicit_mapping(self) -> None:
        unmapped = evaluate(
            activity("single_choice", {"correct_option_id": "safe"}, {"non_compensable_errors": ["unsafe"]}),
            {"choice": "other"},
        )
        self.assertEqual(unmapped["criticalErrors"], [])
        mapped = evaluate(
            activity("single_choice", {"correct_option_id": "safe"}, {"critical_error_options": {"other": "unsafe"}}),
            {"choice": "other"},
        )
        self.assertEqual(mapped["criticalErrors"], ["unsafe"])

    def test_integrated_answer_must_be_complete(self) -> None:
        item = activity("integrated_assessment", {
            "tasks": [
                {"id": "quality", "type": "single_choice", "options": ["oui", "non"], "correct_option_id": "oui"},
                {"id": "cause", "type": "single_choice", "options": ["a", "b"], "correct_option_id": "a"},
            ],
        })
        self.assertFalse(is_complete(item, {"tasks": {"quality": {"choice": "oui"}}}))
        answer = {"tasks": {"quality": {"choice": "oui"}, "cause": {"choice": "a"}}}
        self.assertTrue(is_complete(item, answer))
        self.assertTrue(evaluate(item, answer)["correct"])


if __name__ == "__main__":
    unittest.main()
