"""
extraction_golden.py — I/O du golden d'extraction (data/extraction_golden.json).
=================================================================================
Cf. GOLDEN_EXTRACTION.md pour la méthodologie complète.

Ce module NE construit PAS l'échantillon (voir
scripts/build_extraction_golden_sample.py) — il fournit uniquement les
primitives de lecture/écriture consommées par la page d'annotation
(`/annotation`) et par le script de calcul de métriques.

Format persistant : cf. GOLDEN_EXTRACTION.md §3.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

from . import cases_repo

EXTRACTION_GOLDEN_PATH = os.path.join(cases_repo.DATA_DIR, "extraction_golden.json")
REVIEW_PATH = os.path.join(cases_repo.DATA_DIR, "extraction_golden_review.json")


def _empty() -> dict:
    return {
        "version": 1,
        "created": None,
        "updated": None,
        "seed": None,
        "n_total": 0,
        "n_double_annotation": 0,
        "items": {},
    }


def load() -> dict:
    if not os.path.exists(EXTRACTION_GOLDEN_PATH):
        return _empty()
    try:
        with open(EXTRACTION_GOLDEN_PATH, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("items", {})
        return data
    except (json.JSONDecodeError, OSError):
        return _empty()


def _atomic_write(data: dict) -> None:
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(EXTRACTION_GOLDEN_PATH), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(EXTRACTION_GOLDEN_PATH), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, EXTRACTION_GOLDEN_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def save(data: dict) -> None:
    _atomic_write(data)


def load_review() -> Dict[str, dict]:
    """Charge le rapport de relecture qualité GPT-5.6 (cf. GOLDEN_EXTRACTION.md
    §5ter, scripts/review_extraction_golden.py). {item_id: {slot: {alertes, synthese}}}.
    Dict vide si le rapport n'a pas encore été généré (dégradation propre)."""
    if not os.path.exists(REVIEW_PATH):
        return {}
    try:
        with open(REVIEW_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def overview() -> List[dict]:
    """Résumé léger de chaque item, pour la vue d'ensemble de la page d'annotation."""
    data = load()
    review = load_review()
    out = []
    for item_id, item in sorted(data["items"].items()):
        annotated = item.get("annotation_expert") is not None
        annotated_2 = item.get("annotation_expert_2") is not None
        double = bool(item.get("double_annotation"))
        status = "pending"
        if annotated and (not double or annotated_2):
            status = "done"
        elif annotated:
            status = "partial"  # double annotation, un seul relecteur a fini

        # Nombre d'alertes de relecture GPT-5.6 (tous slots confondus), pour le
        # badge ⚠️ de la liste — cf. GOLDEN_EXTRACTION.md §5ter.
        item_review = review.get(item_id, {})
        n_alertes = sum(len(r.get("alertes", []) or []) for r in item_review.values())

        out.append({
            "item_id": item_id,
            "cas": item.get("cas"),
            "double_annotation": double,
            "n_concepts_pipeline": len(item.get("pipeline_extraction", []) or []),
            "n_concepts_gpt56": len(item.get("gpt56_extraction", []) or []),
            "status": status,
            "n_alertes_review": n_alertes,
            "preview": (item.get("reponse_texte", "") or "")[:120],
        })
    return out


def get_item(item_id: str) -> Optional[dict]:
    data = load()
    item = data["items"].get(item_id)
    if item is None:
        return None
    review = load_review().get(item_id)
    if review:
        item = dict(item)
        item["review"] = review
    return item


def save_annotation(item_id: str, concepts: List[dict], annotateur: str = "",
                     slot: str = "annotation_expert") -> dict:
    """Enregistre l'annotation experte d'un item.

    `slot` vaut "annotation_expert" (relecteur 1) ou "annotation_expert_2"
    (relecteur 2, uniquement pour les items en double annotation)."""
    if slot not in ("annotation_expert", "annotation_expert_2"):
        raise ValueError("slot invalide")
    data = load()
    item = data["items"].get(item_id)
    if item is None:
        raise KeyError(f"item {item_id} introuvable")
    if slot == "annotation_expert_2" and not item.get("double_annotation"):
        raise ValueError(f"item {item_id} n'est pas en double annotation")
    item[slot] = {
        "annotateur": annotateur or "",
        "annotated_at": datetime.now().isoformat(timespec="seconds"),
        "concepts": concepts,
    }
    _atomic_write(data)
    return item
