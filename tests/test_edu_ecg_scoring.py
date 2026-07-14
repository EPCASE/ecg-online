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

    def test_reserved_or_underspecified_activity_accepts_qualitative_response(self) -> None:
        reserved_order = activity("ordering_cards", {"mode": "order_images"})
        self.assertFalse(is_complete(reserved_order, {"text": ""}))
        self.assertTrue(is_complete(reserved_order, {"text": "V1 puis V2"}))
        self.assertFalse(evaluate(reserved_order, {"text": "V1 puis V2"})["evaluated"])

        reserved_test = activity("integrated_assessment", {
            "tasks": [
                {"id": "pairs", "type": "matching_pairs"},
                {"id": "waves", "type": "image_hotspot_labeling"},
            ],
        })
        answer = {"tasks": {"pairs": {"text": "association"}, "waves": {"text": "P QRS T"}}}
        self.assertTrue(is_complete(reserved_test, answer))
        self.assertFalse(evaluate(reserved_test, answer)["evaluated"])

    def test_repeated_choice_requires_one_answer_per_case(self) -> None:
        item = activity("single_choice", {"cases": 3, "options": ["positive", "négative", "équiphasique"]})
        self.assertFalse(is_complete(item, {"choices": ["positive", "négative"]}))
        answer = {"choices": ["positive", "négative", "équiphasique"]}
        self.assertTrue(is_complete(item, answer))
        self.assertFalse(evaluate(item, answer)["evaluated"])


if __name__ == "__main__":
    unittest.main()
