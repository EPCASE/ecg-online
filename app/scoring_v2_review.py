"""
scoring_v2_review.py — I/O de la double annotation indépendante (P1.3).
========================================================================
Cf. audit_doc/roadmap_scientifique_2026.md §P1.3 :

    Pour chaque cas :
    1. expert 1 annote indépendamment ;
    2. expert 2 annote indépendamment ;
    3. les désaccords sont enregistrés ;
    4. une adjudication est réalisée ;
    5. la version consensuelle est produite ;
    6. les annotations initiales restent conservées.

Ce module réplique le pattern déjà validé pour le golden d'extraction
(cf. app/extraction_golden.py, page /annotation) mais appliqué au golden
CONCEPTUEL de scoring (critères structurés scoring_v2, pas concepts extraits
d'une réponse libre). Entrée : data/scoring_pilot_v2.json (10 cas, P1.2,
evidence_source="single_expert" — le premier jet solo devient ici le
pré-remplissage de "expert_1", à confirmer/corriger indépendamment).

Sortie persistée : data/scoring_v2_review.json — structure :

    {
      "version": 1,
      "updated": "...",
      "cases": {
        "<case_id>": {
          "expert_1": {"annotateur": "...", "annotated_at": "...",
                       "criteria": [ {..critère scoring_v2..}, ... ]},
          "expert_2": {"annotateur": "...", "annotated_at": "...",
                       "criteria": [...]} | null,
          "adjudication": {
            "adjudicateur": "...", "adjudicated_at": "...",
            "criteria": [...],     # version consensuelle finale
            "disagreements": [     # traçabilité scientifique (roadmap: "les
                                    # désaccords constituent eux-mêmes un
                                    # résultat scientifique")
              {"criterion_id": "...", "field": "...",
               "expert_1_value": ..., "expert_2_value": ...,
               "resolution": "...", "note": "..."}
            ]
          } | null
        }
      }
    }

Les annotations initiales (expert_1/expert_2) ne sont JAMAIS écrasées par
l'adjudication (exigence explicite du roadmap, point 6) : elles restent
lisibles séparément à tout moment pour l'audit scientifique.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

from . import cases_repo

REVIEW_PATH = os.path.join(cases_repo.DATA_DIR, "scoring_v2_review.json")
PILOT_PATH = os.path.join(cases_repo.DATA_DIR, "scoring_pilot_v2.json")

CRITERION_FIELDS_COMPARED = [
    # Champs comparés pour détecter un désaccord entre expert_1/expert_2 sur
    # un même criterion_id (les champs purement narratifs comme "comment"
    # ne comptent pas comme désaccord bloquant).
    "concept_id", "label", "role", "expected_status", "importance",
    "error_severity", "alternative_group", "group_logic", "group_min_n",
    "sufficient_alone", "minimum_specificity",
]


def _empty() -> dict:
    return {"version": 1, "updated": None, "cases": {}}


def _load_pilot() -> dict:
    if not os.path.exists(PILOT_PATH):
        return {"_meta": {}, "cases": {}}
    with open(PILOT_PATH, encoding="utf-8") as f:
        return json.load(f)


def load() -> dict:
    if not os.path.exists(REVIEW_PATH):
        return _empty()
    try:
        with open(REVIEW_PATH, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("cases", {})
        return data
    except (json.JSONDecodeError, OSError):
        return _empty()


def _atomic_write(data: dict) -> None:
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(REVIEW_PATH), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(REVIEW_PATH), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, REVIEW_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def save(data: dict) -> None:
    _atomic_write(data)


def overview() -> List[dict]:
    """Résumé par cas pilote, pour la vue d'ensemble de la page d'annotation."""
    pilot = _load_pilot()
    review = load()
    meta = pilot.get("_meta", {})
    cas_labels = meta.get("cas_couverts", {})
    out = []
    for case_id in pilot.get("cases", {}).keys():
        entry = review["cases"].get(case_id, {})
        e1 = entry.get("expert_1")
        e2 = entry.get("expert_2")
        adj = entry.get("adjudication")
        n_disagreements = len((adj or {}).get("disagreements", []) or [])
        if adj:
            status = "adjudicated"
        elif e1 and e2:
            status = "ready_for_adjudication"
        elif e1 or e2:
            status = "partial"
        else:
            status = "pending"
        out.append({
            "case_id": case_id,
            "label": cas_labels.get(case_id, ""),
            "n_criteria_pilot": len(pilot["cases"].get(case_id, []) or []),
            "expert_1_done": bool(e1),
            "expert_2_done": bool(e2),
            "n_disagreements": n_disagreements,
            "status": status,
        })
    return out


def get_case(case_id: str) -> Optional[dict]:
    pilot = _load_pilot()
    if case_id not in pilot.get("cases", {}):
        return None
    review = load()
    entry = review["cases"].get(case_id, {})
    return {
        "case_id": case_id,
        "pilot_criteria": pilot["cases"][case_id],
        "expert_1": entry.get("expert_1"),
        "expert_2": entry.get("expert_2"),
        "adjudication": entry.get("adjudication"),
    }


def _criteria_for_slot(case_id: str, slot: str, review: dict, pilot: dict) -> List[dict]:
    """Pré-remplissage : si le slot n'a jamais été enregistré, on part du
    pilote solo (P1.2) comme base de travail — l'expert doit ensuite le
    confirmer ou le corriger indépendamment (pas de recopie automatique de
    expert_1 vers expert_2, chacun repart du même pilote neutre)."""
    entry = review["cases"].get(case_id, {})
    existing = entry.get(slot)
    if existing and isinstance(existing.get("criteria"), list):
        return existing["criteria"]
    return [dict(c) for c in pilot["cases"].get(case_id, [])]


def save_expert_annotation(case_id: str, slot: str, criteria: List[dict],
                            annotateur: str = "") -> dict:
    if slot not in ("expert_1", "expert_2"):
        raise ValueError("slot invalide (attendu expert_1 ou expert_2)")
    pilot = _load_pilot()
    if case_id not in pilot.get("cases", {}):
        raise KeyError(f"case {case_id} introuvable dans le pilote")
    data = load()
    entry = data["cases"].setdefault(case_id, {})
    entry[slot] = {
        "annotateur": annotateur or "",
        "annotated_at": datetime.now().isoformat(timespec="seconds"),
        "criteria": criteria,
    }
    _atomic_write(data)
    return entry


def compute_disagreements(case_id: str) -> List[dict]:
    """Compare expert_1/expert_2 critère par critère (par criterion_id) et
    liste les champs divergents — base de travail affichée à l'adjudicateur."""
    data = load()
    entry = data["cases"].get(case_id, {})
    e1 = (entry.get("expert_1") or {}).get("criteria", [])
    e2 = (entry.get("expert_2") or {}).get("criteria", [])
    by_id_1 = {c.get("criterion_id"): c for c in e1}
    by_id_2 = {c.get("criterion_id"): c for c in e2}
    all_ids = sorted(set(by_id_1) | set(by_id_2))
    disagreements = []
    for cid in all_ids:
        c1 = by_id_1.get(cid)
        c2 = by_id_2.get(cid)
        if c1 is None or c2 is None:
            disagreements.append({
                "criterion_id": cid, "field": "_presence",
                "expert_1_value": bool(c1), "expert_2_value": bool(c2),
                "note": "Critère absent chez un des deux experts.",
            })
            continue
        for field in CRITERION_FIELDS_COMPARED:
            if c1.get(field) != c2.get(field):
                disagreements.append({
                    "criterion_id": cid, "field": field,
                    "expert_1_value": c1.get(field), "expert_2_value": c2.get(field),
                    "note": "",
                })
    return disagreements


def save_adjudication(case_id: str, criteria: List[dict],
                       disagreements: List[dict], adjudicateur: str = "") -> dict:
    """Enregistre la version consensuelle finale + la trace des désaccords
    résolus. N'écrase jamais expert_1/expert_2 (conservés tels quels)."""
    data = load()
    entry = data["cases"].get(case_id)
    if entry is None or not entry.get("expert_1") or not entry.get("expert_2"):
        raise ValueError(
            f"case {case_id} : adjudication impossible sans les deux annotations expertes")
    entry["adjudication"] = {
        "adjudicateur": adjudicateur or "",
        "adjudicated_at": datetime.now().isoformat(timespec="seconds"),
        "criteria": criteria,
        "disagreements": disagreements,
    }
    _atomic_write(data)
    return entry
