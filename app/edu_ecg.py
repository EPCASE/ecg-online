"""Guarded, schema-aware delivery of the experimental Edu-ECG course."""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from flask import abort, jsonify, request, send_from_directory

from . import edu_ecg_scoring


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "edu_ecg"
ASSET_DIR = DATA_DIR / "assets"
COURSE_PATH = DATA_DIR / "course.json"
AVAILABILITY_PATH = DATA_DIR / "availability.json"
MODULE_DIR = DATA_DIR / "modules"

SUPPORTED_ACTIVITY_TYPES = {
    "single_choice",
    "multiple_choice",
    "short_answer",
    "card_sorting",
    "ordering_cards",
    "matching_pairs",
    "image_comparison",
    "image_hotspot_labeling",
    "sequence_checklist",
    "integrated_assessment",
    "micro_lesson",
}
CONTENT_STATUSES = {
    "draft", "medical_review", "pedagogical_review", "approved", "retired"
}
PHASES = {
    "prime", "probe", "point", "attach", "strengthen", "test", "review",
    "optional_extension",
}
MODULE_ID = re.compile(r"^M[0-7]$")
ACTIVITY_ID = re.compile(r"^M[0-7](?:\.[0-9]+)?_[A-Z_]+_[0-9]+$")


class EduEcgContentError(RuntimeError):
    """Raised when the packaged course violates its JSON contracts."""


def feature_enabled() -> bool:
    return os.environ.get("EDU_ECG_INTRO_COURSE", "0").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise EduEcgContentError(f"Impossible de charger {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EduEcgContentError(f"{path.name} doit contenir un objet JSON.")
    return payload


def _require(payload: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(field for field in fields if field not in payload)
    if missing:
        raise EduEcgContentError(f"{label}: champs requis absents: {', '.join(missing)}")


def _validate_activity(activity: dict[str, Any], module_id: str, seen: set[str]) -> None:
    _require(
        activity,
        {"id", "module_id", "competency_ids", "phase", "activity_type", "title",
         "prompt", "content_status"},
        f"activité de {module_id}",
    )
    activity_id = str(activity["id"])
    if not ACTIVITY_ID.fullmatch(activity_id):
        raise EduEcgContentError(f"Identifiant d'activité invalide: {activity_id}")
    if activity_id in seen:
        raise EduEcgContentError(f"Identifiant d'activité dupliqué: {activity_id}")
    seen.add(activity_id)
    if activity.get("module_id") != module_id:
        raise EduEcgContentError(f"{activity_id}: module_id incohérent")
    if activity.get("activity_type") not in SUPPORTED_ACTIVITY_TYPES:
        raise EduEcgContentError(f"{activity_id}: activity_type non pris en charge")
    if activity.get("phase") not in PHASES:
        raise EduEcgContentError(f"{activity_id}: phase invalide")
    if activity.get("content_status") not in CONTENT_STATUSES:
        raise EduEcgContentError(f"{activity_id}: content_status invalide")
    competencies = activity.get("competency_ids")
    if not isinstance(competencies, list) or not competencies:
        raise EduEcgContentError(f"{activity_id}: competency_ids doit être une liste non vide")
    hints = activity.get("hints", [])
    if not isinstance(hints, list) or len(hints) > 3:
        raise EduEcgContentError(f"{activity_id}: hints invalide")
    if activity.get("phase") == "test" and hints:
        raise EduEcgContentError(f"{activity_id}: un test autonome ne peut pas contenir d'indice")
    asset_policy = activity.get("asset_policy") or {}
    if asset_policy.get("reserved_for_test") and activity.get("phase") not in {"test", "review"}:
        raise EduEcgContentError(f"{activity_id}: un asset réservé doit appartenir à une phase test ou review")
    if activity.get("phase") == "test":
        attempt_policy = activity.get("attempt_policy") or {}
        if attempt_policy.get("allow_revision_after_hint"):
            raise EduEcgContentError(f"{activity_id}: un test autonome ne permet pas de révision après indice")
    for asset in activity.get("assets", []):
        asset_path = Path(str(asset))
        if asset_path.is_absolute() or ".." in asset_path.parts:
            raise EduEcgContentError(f"{activity_id}: chemin d'asset non sûr: {asset}")


def _module_filename(reference: str) -> str:
    name = Path(str(reference)).name
    if not re.fullmatch(r"module_[0-7]{2}\.json", name):
        raise EduEcgContentError(f"Référence de module invalide: {reference}")
    return name


@lru_cache(maxsize=1)
def validate_content() -> dict[str, Any]:
    """Validate every course/module document before any route can expose it.

    The repository deliberately avoids a new runtime dependency. The checked
    invariants mirror the packaged JSON schemas and add the pedagogical test/hint
    guard that JSON Schema alone does not express.
    """
    course = _read_json(COURSE_PATH)
    _require(course, {"id", "version", "title", "modules"}, "course")
    if not isinstance(course.get("modules"), list) or not course["modules"]:
        raise EduEcgContentError("course.modules doit être une liste non vide")
    availability = _read_json(AVAILABILITY_PATH)
    available_modules = availability.get("modules", {})
    if not isinstance(available_modules, dict):
        raise EduEcgContentError("availability.modules doit être un objet")

    modules: dict[str, dict[str, Any]] = {}
    activity_ids: set[str] = set()
    for reference in course["modules"]:
        module = _read_json(MODULE_DIR / _module_filename(str(reference)))
        _require(module, {"id", "version", "title", "terminal_objective", "competencies",
                          "activities"}, "module")
        module_id = str(module["id"])
        if not MODULE_ID.fullmatch(module_id):
            raise EduEcgContentError(f"Identifiant de module invalide: {module_id}")
        if module_id in modules:
            raise EduEcgContentError(f"Module dupliqué: {module_id}")
        if not isinstance(module.get("activities"), list):
            raise EduEcgContentError(f"{module_id}: activities doit être une liste")
        for activity in module["activities"]:
            if not isinstance(activity, dict):
                raise EduEcgContentError(f"{module_id}: activité non objet")
            _validate_activity(activity, module_id, activity_ids)
        modules[module_id] = module

    for module_id, entry in available_modules.items():
        if module_id not in modules or not isinstance(entry, dict):
            raise EduEcgContentError(f"Disponibilité inconnue: {module_id}")
        allowed = entry.get("activity_ids")
        module_activity_ids = {item["id"] for item in modules[module_id]["activities"]}
        if allowed != "all" and (
            not isinstance(allowed, list) or not set(allowed).issubset(module_activity_ids)
        ):
            raise EduEcgContentError(f"{module_id}: activity_ids de disponibilité invalides")

    return {"course": course, "modules": modules, "availability": availability}


def _guard() -> None:
    if not feature_enabled():
        abort(404)


def course_payload() -> dict[str, Any]:
    validated = validate_content()
    availability = validated["availability"]["modules"]
    summaries = []
    for module_id, entry in availability.items():
        module = validated["modules"][module_id]
        allowed = entry.get("activity_ids")
        count = len(module["activities"]) if allowed == "all" else len(allowed)
        summaries.append({
            "id": module_id,
            "title": module["title"],
            "terminal_objective": module["terminal_objective"],
            "estimated_duration_minutes": module.get("estimated_duration_minutes"),
            "implementation_status": entry.get("status", "prototype"),
            "activity_count": count,
        })
    return {**validated["course"], "available_modules": summaries}


_PRIVATE_RESPONSE_FIELDS = {
    "accepted_answers", "answer", "category", "correct", "correct_labels",
    "correct_option_id", "correct_option_ids", "correct_options", "correct_order",
    "correct_pairs", "expected_concepts",
}
_PUBLIC_SCORING_FIELDS = {
    "all_axes_required", "all_cards_required", "all_critical_items_required",
    "all_pairs_required", "all_targets_required", "concepts_required",
    "decision_points", "domains", "exact_order_required", "minimum_percent",
    "points", "reason_points",
}


def _public_response(value: Any) -> Any:
    """Recursively remove answer keys from content sent before submission."""
    if isinstance(value, list):
        return [_public_response(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        key: _public_response(item)
        for key, item in value.items()
        if key not in _PRIVATE_RESPONSE_FIELDS
    }


def _public_activity(activity: dict[str, Any]) -> dict[str, Any]:
    public = deepcopy(activity)
    public["response"] = _public_response(public.get("response") or {})
    public["scoring"] = {
        key: value
        for key, value in (public.get("scoring") or {}).items()
        if key in _PUBLIC_SCORING_FIELDS
    }
    # Feedback is returned only after a submission. For a micro-lesson the
    # explanation is the lesson itself and therefore remains public.
    if public.get("activity_type") != "micro_lesson":
        public.pop("explanation", None)
    public.pop("review", None)
    return public


def _available_activity(module_id: str, activity_id: str) -> dict[str, Any]:
    validated = validate_content()
    availability = validated["availability"]["modules"].get(module_id)
    if not availability:
        abort(404)
    allowed = availability.get("activity_ids")
    if allowed != "all" and activity_id not in allowed:
        abort(404)
    activity = next(
        (item for item in validated["modules"][module_id]["activities"] if item["id"] == activity_id),
        None,
    )
    if activity is None:
        abort(404)
    return activity


def module_payload(module_id: str) -> dict[str, Any]:
    validated = validate_content()
    availability = validated["availability"]["modules"].get(module_id)
    if not availability:
        abort(404)
    module = deepcopy(validated["modules"][module_id])
    allowed = availability.get("activity_ids")
    if allowed != "all":
        allowed_ids = set(allowed)
        module["activities"] = [
            item for item in module["activities"] if item["id"] in allowed_ids
        ]
    module["activities"] = [_public_activity(item) for item in module["activities"]]
    module["implementation_status"] = availability.get("status", "prototype")
    return module


def register_routes(app, frontend_dir: str) -> None:
    """Register all Edu-ECG routes behind the disabled-by-default feature flag."""
    # Build/startup validation: invalid course data prevents a silently broken deploy.
    validation = validate_content()
    app.config["EDU_ECG_CONTENT_VERSION"] = validation["course"]["version"]

    @app.get("/edu-ecg")
    def edu_ecg_page():
        _guard()
        return send_from_directory(frontend_dir, "edu-ecg.html")

    @app.get("/api/edu-ecg/course")
    def edu_ecg_course():
        _guard()
        return jsonify(course_payload())

    @app.get("/api/edu-ecg/modules/<module_id>")
    def edu_ecg_module(module_id: str):
        _guard()
        if not MODULE_ID.fullmatch(module_id):
            abort(404)
        return jsonify(module_payload(module_id))

    @app.post("/api/edu-ecg/modules/<module_id>/activities/<activity_id>/evaluate")
    def edu_ecg_evaluate(module_id: str, activity_id: str):
        _guard()
        if not MODULE_ID.fullmatch(module_id) or not ACTIVITY_ID.fullmatch(activity_id):
            abort(404)
        activity = _available_activity(module_id, activity_id)
        payload = request.get_json(silent=True) or {}
        answer = payload.get("answer")
        if not isinstance(answer, dict) or not edu_ecg_scoring.is_complete(activity, answer):
            abort(400, description="Réponse incomplète ou invalide.")
        result = edu_ecg_scoring.evaluate(activity, answer)
        return jsonify({
            "result": result,
            "explanation": deepcopy(activity.get("explanation") or {}),
        })

    @app.get("/api/edu-ecg/assets/<path:filename>")
    def edu_ecg_asset(filename: str):
        _guard()
        return send_from_directory(ASSET_DIR, filename)
