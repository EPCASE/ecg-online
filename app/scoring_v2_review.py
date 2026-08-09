"""
scoring_v2_review.py — I/O de l'annotation solo + second avis IA (P1.3 simplifié).
========================================================================
Cf. audit_doc/roadmap_scientifique_2026.md §P1.3 — adapté en pratique pour
tenir sans mobiliser deux experts humains :

    1. UN relecteur humain (expert_1) annote/corrige les critères du cas ;
    2. à la demande, un second avis GPT (ai_review) est généré : il compare
       le texte de référence (interpretation_ref) aux critères du relecteur
       et signale des désaccords/oublis potentiels (mêmes champs que la
       comparaison inter-experts) ;
    3. le relecteur consulte cet avis et corrige directement ses propres
       critères s'il est convaincu — pas d'étape d'adjudication séparée ni
       de second relecteur humain bloquant.

Ce module réplique le pattern déjà validé pour le golden d'extraction
(cf. app/extraction_golden.py, page /annotation) mais appliqué au golden
CONCEPTUEL de scoring (critères structurés scoring_v2, pas concepts extraits
d'une réponse libre). Entrée : data/scoring_pilot_v2.json (10 cas, P1.2,
evidence_source="single_expert" — le premier jet solo devient ici le
pré-remplissage de "expert_1", à confirmer/corriger).

Sortie persistée : data/scoring_v2_review.json — structure :

    {
      "version": 1,
      "updated": "...",
      "cases": {
        "<case_id>": {
          "expert_1": {"annotateur": "...", "annotated_at": "...",
                       "criteria": [ {..critère scoring_v2..}, ... ]},
          "ai_review": {
            "generated_at": "...", "model": "...",
            "alertes": [ {criterion_id, type_probleme, commentaire}, ... ],
            "synthese": "..."
          } | null
        }
      }
    }

⚠️ IMPORTANT — TRAÇABILITÉ P1.3 → P4 : le champ `minimum_specificity` que
l'on annote ici (exact_only/child_ok/parent_ok/any_related, par critère)
N'EST PAS ENCORE branché au moteur de scoring en production. À ce jour
(2026-08), `rag_pipeline/scoring_v3.py` applique une règle GLOBALE et
uniforme, câblée en dur pour TOUS les concepts (enfant trouvé → 1.0 toujours,
parent direct → 2/3, parent éloigné → 1/3 ; cf. règles 1b/1c de ce fichier).
`minimum_specificity` est la couche de correction PAR CRITÈRE conçue pour
remplacer cette règle globale — la brancher est un prérequis de P4 (refonte
scoring). Tant que ce n'est pas fait, annoter ce champ prépare le travail
mais n'a AUCUN effet sur la note réelle des étudiants.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

from . import cases_repo

logger = logging.getLogger(__name__)

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
        ai = entry.get("ai_review")
        suggestions = entry.get("ai_suggested_criteria")
        n_alertes = len((ai or {}).get("alertes", []) or [])
        n_suggestions = len((suggestions or {}).get("criteria", []) or [])
        if e1 and ai:
            status = "reviewed"
        elif e1:
            status = "annotated"
        else:
            status = "pending"
        out.append({
            "case_id": case_id,
            "label": cas_labels.get(case_id, ""),
            "n_criteria_pilot": len(pilot["cases"].get(case_id, []) or []),
            "expert_1_done": bool(e1),
            "ai_review_done": bool(ai),
            "n_alertes": n_alertes,
            "n_suggestions": n_suggestions,
            "status": status,
        })
    return out


def get_case(case_id: str) -> Optional[dict]:
    pilot = _load_pilot()
    if case_id not in pilot.get("cases", {}):
        return None
    review = load()
    entry = review["cases"].get(case_id, {})
    # Contexte ECG (image, titre, patient, contexte clinique, interprétation de
    # référence) indispensable pour annoter en connaissance de cause — sans
    # ça le relecteur juge des critères à l'aveugle, sans voir le tracé.
    ecg = {}
    try:
        ecg = cases_repo.get_case(int(case_id)) or {}
    except (TypeError, ValueError):
        ecg = {}
    return {
        "case_id": case_id,
        "pilot_criteria": pilot["cases"][case_id],
        "expert_1": entry.get("expert_1"),
        "expert_2": entry.get("expert_2"),
        "adjudication": entry.get("adjudication"),
        "ai_review": entry.get("ai_review"),
        "ai_suggested_criteria": entry.get("ai_suggested_criteria"),
        "ecg": {
            "titre": ecg.get("titre", ""),
            "patient": ecg.get("patient", ""),
            "contexte": ecg.get("contexte", ""),
            "images": ecg.get("images", []),
            "interpretation_ref": ecg.get("interpretation_ref", ""),
        },
    }


def _criteria_for_slot(case_id: str, slot: str, review: dict, pilot: dict) -> List[dict]:
    """Pré-remplissage : si le slot n'a jamais été enregistré, on part du
    pilote solo (P1.2) comme base de travail — le relecteur doit ensuite le
    confirmer ou le corriger."""
    entry = review["cases"].get(case_id, {})
    existing = entry.get(slot)
    if existing and isinstance(existing.get("criteria"), list):
        return existing["criteria"]
    return [dict(c) for c in pilot["cases"].get(case_id, [])]


def save_expert_annotation(case_id: str, slot: str, criteria: List[dict],
                            annotateur: str = "") -> dict:
    if slot != "expert_1":
        raise ValueError("slot invalide (seul 'expert_1' est utilisé désormais)")
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


def generate_ai_review(case_id: str) -> dict:
    """Génère (ou régénère) un second avis GPT sur l'annotation de expert_1,
    en s'appuyant sur l'interprétation de référence du cas ECG (le texte
    d'expert qui sert de base à la construction des critères). Remplace
    l'ancienne étape de double annotation humaine + adjudication : ici, un
    seul relecteur humain reste responsable de la version finale, l'IA ne
    fait que signaler des points à vérifier."""
    from . import gpt_annotator

    pilot = _load_pilot()
    if case_id not in pilot.get("cases", {}):
        raise KeyError(f"case {case_id} introuvable dans le pilote")
    data = load()
    entry = data["cases"].get(case_id, {})
    e1 = entry.get("expert_1")
    if not e1 or not isinstance(e1.get("criteria"), list):
        raise ValueError("l'annotation du relecteur (expert_1) doit être enregistrée avant de demander un second avis IA")

    ecg = {}
    try:
        ecg = cases_repo.get_case(int(case_id)) or {}
    except (TypeError, ValueError):
        ecg = {}
    interpretation_ref = ecg.get("interpretation_ref", "")

    result = gpt_annotator.review_scoring_criteria(
        interpretation_ref, e1["criteria"])
    if result is None:
        raise RuntimeError(
            "second avis IA indisponible (clé OPENAI_API_KEY absente ou erreur modèle)")

    entry = data["cases"].setdefault(case_id, {})
    entry["ai_review"] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": gpt_annotator.DEFAULT_MODEL,
        "alertes": result.get("alertes", []),
        "synthese": result.get("synthese", ""),
    }
    _atomic_write(data)
    return entry


def generate_ai_suggested_criteria(case_id: str) -> dict:
    """Génère (ou régénère) une liste de critères CANDIDATS pour un cas, à
    partir du seul texte d'interprétation de référence — indépendamment de
    toute annotation existante (contrairement à generate_ai_review qui relit
    des critères déjà écrits). Sert de premier jet quand le pilote solo P1.2
    est absent/incomplet, ou pour repérer des concepts descriptifs oubliés
    (cf. demande : « je n'ai pas la liste des concepts que je peux choisir,
    fait une passe IA pour que je n'aie qu'à relire et valider »). Stocké à
    part (`ai_suggested_criteria`), n'écrase jamais expert_1."""
    from . import gpt_annotator

    pilot = _load_pilot()
    if case_id not in pilot.get("cases", {}):
        raise KeyError(f"case {case_id} introuvable dans le pilote")

    ecg = {}
    try:
        ecg = cases_repo.get_case(int(case_id)) or {}
    except (TypeError, ValueError):
        ecg = {}
    interpretation_ref = ecg.get("interpretation_ref", "")

    data = load()
    entry = data["cases"].setdefault(case_id, {})
    # Fallback sur le premier jet solo (P1.2) si le relecteur n'a pas encore
    # enregistré expert_1 dans ce fichier — sinon existing=[] et l'IA ne
    # verrait AUCUN critère déjà posé, d'où des doublons/reformulations
    # proposés comme s'ils étaient neufs (cf. bug remonté sur le cas 24 :
    # "BAV 2 Mobitz 1" déjà dans le pilote, reproposé sous un autre nom).
    existing = _criteria_for_slot(case_id, "expert_1", data, pilot)

    suggested = gpt_annotator.suggest_scoring_criteria(
        interpretation_ref, case_id=case_id, existing_criteria=existing)
    if suggested is None:
        raise RuntimeError(
            "génération de critères IA indisponible (clé OPENAI_API_KEY absente ou erreur modèle)")

    entry["ai_suggested_criteria"] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": gpt_annotator.DEFAULT_MODEL,
        "criteria": suggested,
    }
    _atomic_write(data)
    return entry
