"""Deterministic scoring primitives for Edu-ECG activities.

The module contains no medical content. It only evaluates explicit keys present
in the private course JSON. Missing keys always produce a non-evaluated result.
"""
from __future__ import annotations

from typing import Any


def _result(
    activity: dict[str, Any],
    evaluated: bool,
    earned: float | None = None,
    possible: float | None = None,
    detail: str | None = None,
    critical_errors: list[str] | None = None,
) -> dict[str, Any]:
    percent = None
    if evaluated and possible:
        percent = round(((earned or 0) / possible) * 100)
    return {
        "activityId": activity.get("id"),
        "evaluated": evaluated,
        "correct": bool(possible and earned == possible) if evaluated else None,
        "earned": earned if evaluated else None,
        "possible": possible if evaluated else None,
        "percent": percent,
        "detail": detail or (
            "Évaluation déterministe."
            if evaluated
            else "Contenu à valider : aucun corrigé explicite n’est fourni."
        ),
        "criticalErrors": critical_errors or [],
    }


def _equal_sets(left: Any, right: Any) -> bool:
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    return sorted({str(item) for item in left}) == sorted({str(item) for item in right})


def _choice_key(activity: dict[str, Any]) -> str | None:
    response = activity.get("response") or {}
    scoring = activity.get("scoring") or {}
    for key in ("correct_option_id", "correct"):
        if response.get(key) is not None:
            return str(response[key])
    for key in ("correct_option_id", "correct"):
        if scoring.get(key) is not None:
            return str(scoring[key])
    return None


def _choice(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    key = _choice_key(activity)
    if key is None:
        return _result(activity, False)
    selected = str(answer.get("choice", ""))
    scoring = activity.get("scoring") or {}
    possible = float(scoring.get("points") or scoring.get("decision_points") or 1)
    correct = selected == key
    critical: list[str] = []
    option_map = scoring.get("critical_error_options") or {}
    if isinstance(option_map, dict) and option_map.get(selected):
        critical.append(str(option_map[selected]))
    elif not correct and scoring.get("critical_error"):
        critical.append(str(scoring["critical_error"]))
    return _result(activity, True, possible if correct else 0, possible, critical_errors=critical)


def _multiple(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    response = activity.get("response") or {}
    scoring = activity.get("scoring") or {}
    key = (
        response.get("correct_option_ids")
        or response.get("correct_options")
        or scoring.get("correct_option_ids")
        or scoring.get("correct_options")
    )
    if not isinstance(key, list):
        return _result(activity, False)
    possible = float(scoring.get("points") or 1)
    correct = _equal_sets(answer.get("choices"), key)
    critical = [str(scoring["critical_error"])] if not correct and scoring.get("critical_error") else []
    return _result(activity, True, possible if correct else 0, possible, critical_errors=critical)


def _cards(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    response = activity.get("response") or {}
    scoring = activity.get("scoring") or {}
    cards = response.get("cards") or []
    if not cards or any(not isinstance(card, dict) or card.get("category") is None for card in cards):
        return _result(activity, False)
    assignments = answer.get("assignments") or {}
    earned = sum(assignments.get(card.get("id")) == card.get("category") for card in cards)
    critical_cards = set(scoring.get("critical_cards") or [])
    critical = [
        f"critical_card:{card['id']}"
        for card in cards
        if card.get("id") in critical_cards and assignments.get(card.get("id")) != card.get("category")
    ]
    return _result(activity, True, earned, len(cards), critical_errors=critical)


def _order(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    response = activity.get("response") or {}
    scoring = activity.get("scoring") or {}
    key = response.get("correct_order")
    if not isinstance(key, list) or not key:
        return _result(activity, False)
    order = answer.get("order") or []
    earned = sum(str(order[index]) == str(item) for index, item in enumerate(key) if index < len(order))
    critical = [str(scoring["critical_error"])] if earned != len(key) and scoring.get("critical_error") else []
    return _result(activity, True, earned, len(key), critical_errors=critical)


def _pairs(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    response = activity.get("response") or {}
    scoring = activity.get("scoring") or {}
    correct_pairs = response.get("correct_pairs")
    if not isinstance(correct_pairs, list) or not correct_pairs:
        return _result(activity, False)
    pairs = answer.get("pairs") or {}
    earned = sum(pairs.get(left) == right for left, right in correct_pairs)
    critical: list[str] = []
    critical_pair = scoring.get("critical_pair")
    if isinstance(critical_pair, list) and len(critical_pair) == 2:
        left, right = critical_pair
        if pairs.get(left) != right:
            critical.append(f"critical_pair:{left}")
    return _result(activity, True, earned, len(correct_pairs), critical_errors=critical)


def _hotspots(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    response = activity.get("response") or {}
    scoring = activity.get("scoring") or {}
    key = response.get("correct_labels")
    if not isinstance(key, dict):
        targets = response.get("targets") or []
        if targets and all(
            isinstance(target, dict) and (target.get("correct_label") or target.get("answer"))
            for target in targets
        ):
            key = {
                str(target["id"]): target.get("correct_label") or target.get("answer")
                for target in targets
            }
    if not isinstance(key, dict) or not key:
        return _result(activity, False)
    labels = answer.get("labels") or {}
    earned = sum(labels.get(item_id) == label for item_id, label in key.items())
    critical = [str(scoring["critical_error"])] if earned != len(key) and scoring.get("critical_error") else []
    return _result(activity, True, earned, len(key), critical_errors=critical)


def _checklist(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    response = activity.get("response") or {}
    if response.get("free_checklist"):
        return _result(activity, False)
    expected = response.get("correct_order") or response.get("checklist")
    if not isinstance(expected, list) or not expected:
        return _result(activity, False)
    checked = answer.get("checked") or []
    earned = sum(item in checked for item in expected)
    return _result(activity, True, earned, len(expected))


def _task_activity(parent: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"{parent.get('id')}:{task.get('id', 'task')}",
        "activity_type": task.get("type"),
        "response": task,
        "scoring": task.get("scoring") or {},
    }


def _integrated(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    tasks = (activity.get("response") or {}).get("tasks")
    if not isinstance(tasks, list) or not tasks or any(not isinstance(task, dict) for task in tasks):
        return _result(activity, False)
    answers = answer.get("tasks") or {}
    evaluations = [evaluate(_task_activity(activity, task), answers.get(task.get("id"), {})) for task in tasks]
    if any(not item["evaluated"] for item in evaluations):
        return _result(activity, False)
    earned = sum(item["earned"] for item in evaluations)
    possible = sum(item["possible"] for item in evaluations)
    critical = [error for item in evaluations for error in item["criticalErrors"]]
    return _result(activity, True, earned, possible, critical_errors=critical)


def evaluate(activity: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    """Evaluate an answer exclusively from explicit private JSON keys."""
    kind = activity.get("activity_type")
    if kind == "single_choice":
        return _choice(activity, answer)
    if kind == "multiple_choice":
        return _multiple(activity, answer)
    if kind == "short_answer":
        return _result(activity, False, detail="Réponse enregistrée sans notation automatique.")
    if kind == "card_sorting":
        return _cards(activity, answer)
    if kind == "ordering_cards":
        return _order(activity, answer)
    if kind == "matching_pairs":
        return _pairs(activity, answer)
    if kind == "image_comparison":
        response_type = (activity.get("response") or {}).get("type")
        if response_type == "multiple_choice":
            return _multiple(activity, answer)
        if response_type == "short_answer":
            return _result(activity, False, detail="Réponse enregistrée sans notation automatique.")
        return _choice(activity, answer)
    if kind == "image_hotspot_labeling":
        return _hotspots(activity, answer)
    if kind == "sequence_checklist":
        return _checklist(activity, answer)
    if kind == "integrated_assessment":
        return _integrated(activity, answer)
    if kind == "micro_lesson":
        return _result(activity, False, detail="Micro-leçon consultée : aucune note attribuée.")
    raise ValueError(f"Type d’activité non pris en charge: {kind}")


def is_complete(activity: dict[str, Any], answer: dict[str, Any]) -> bool:
    """Return whether the submitted shape constitutes a complete UI response."""
    response = activity.get("response") or {}
    kind = activity.get("activity_type")
    effective_kind = response.get("type", "single_choice") if kind == "image_comparison" else kind
    if effective_kind == "single_choice":
        return bool(answer.get("choice"))
    if effective_kind == "multiple_choice":
        return bool(answer.get("choices"))
    if effective_kind == "short_answer":
        return bool(str(answer.get("text", "")).strip())
    if kind == "card_sorting":
        assignments = answer.get("assignments") or {}
        return bool(response.get("cards")) and all(assignments.get(card.get("id")) for card in response["cards"])
    if kind == "ordering_cards":
        return bool(answer.get("order"))
    if kind == "matching_pairs":
        pairs = answer.get("pairs") or {}
        return bool(response.get("left_items")) and all(pairs.get(item) for item in response["left_items"])
    if kind == "image_hotspot_labeling":
        return bool(answer.get("labels"))
    if kind == "sequence_checklist":
        if response.get("free_checklist"):
            return bool(str(answer.get("text", "")).strip())
        return bool(answer.get("checked"))
    if kind == "integrated_assessment":
        tasks = response.get("tasks")
        if not isinstance(tasks, list) or not tasks or any(not isinstance(task, dict) for task in tasks):
            return bool(str(answer.get("text", "")).strip())
        answers = answer.get("tasks") or {}
        return all(is_complete(_task_activity(activity, task), answers.get(task.get("id"), {})) for task in tasks)
    if kind == "micro_lesson":
        return bool(answer.get("continued"))
    return False
