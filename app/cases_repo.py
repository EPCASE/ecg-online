"""
cases_repo.py — Accès à la banque de cas (data/cases.json).
Chargement paresseux + cache, filtrage par famille, expurgation de la réponse
de référence pour l'API publique (on ne divulgue pas l'interprétation avant
que l'étudiant ait répondu).
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(_HERE, "..", "data"))
CASES_PATH = os.path.join(DATA_DIR, "cases.json")
REFERENCE_PATH = os.path.join(DATA_DIR, "cases_reference.json")
IMAGES_DIR = os.path.join(DATA_DIR, "ecg_images")

# Champs jamais renvoyés par l'API tant que l'étudiant n'a pas répondu.
_HIDDEN_FIELDS = {"interpretation_ref", "commentaires", "qcm"}


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_references() -> dict:
    """Corrigés-types + fiches de secours (filet si l'IA dérape). Optionnel."""
    if not os.path.exists(REFERENCE_PATH):
        return {}
    with open(REFERENCE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {str(r["num"]): r for r in data.get("references", [])}


def get_reference(num) -> Optional[dict]:
    """Renvoie {reponse_attendue, points_cles, fiche_secours} pour un cas, ou None."""
    return _load_references().get(str(num))


def all_cases() -> List[dict]:
    return _load_raw().get("cases", [])


def get_case(num: int) -> Optional[dict]:
    for c in all_cases():
        if str(c.get("num")) == str(num):
            return c
    return None


def families() -> List[dict]:
    """Compte des cas par famille, pour les filtres du front."""
    counts: dict = {}
    for c in all_cases():
        fam = c.get("famille", "autre")
        counts[fam] = counts.get(fam, 0) + 1
    return sorted(
        ({"famille": k, "count": v} for k, v in counts.items()),
        key=lambda d: (-d["count"], d["famille"]),
    )


def public_case(case: dict) -> dict:
    """Version « énoncé » d'un cas : contexte + images, SANS la correction."""
    return {k: v for k, v in case.items() if k not in _HIDDEN_FIELDS}


def public_index() -> List[dict]:
    """Liste légère pour le sélecteur (num, titre, famille, nb images)."""
    out = []
    for c in all_cases():
        out.append({
            "num": c.get("num"),
            "titre": c.get("titre"),
            "famille": c.get("famille"),
            "images": c.get("images", []),
            "has_qcm": bool((c.get("qcm") or {}).get("options")),
        })
    return sorted(out, key=lambda d: d["num"])


# ─────────────────────────── QCM ───────────────────────────
def parse_reponses(raw) -> List[str]:
    """Normalise le champ `reponses` (formats mixtes : 'A', 'A, E', 'A-D-E', '').
    Renvoie la liste triée des lettres attendues, ex. ['A', 'D', 'E']."""
    if not raw:
        return []
    letters = re.findall(r"[A-Ea-e]", str(raw))
    return sorted({l.upper() for l in letters})


def get_qcm_public(num) -> Optional[dict]:
    """QCM d'un cas SANS la solution (question + options + lettres disponibles).
    Renvoie None si le cas n'a pas de QCM exploitable."""
    case = get_case(num)
    if not case:
        return None
    qcm = case.get("qcm") or {}
    options = qcm.get("options") or []
    if not options:
        return None
    # Lettre en tête de chaque option ("A. ...") sinon A, B, C… par position.
    letters = []
    for i, opt in enumerate(options):
        m = re.match(r"\s*([A-Ea-e])\s*[.)-]", str(opt))
        letters.append(m.group(1).upper() if m else chr(65 + i))
    return {
        "num": num,
        "question": qcm.get("question", ""),
        "options": options,
        "letters": letters,
        "multiple": len(parse_reponses(qcm.get("reponses"))) > 1,
    }


def check_qcm(num, selected: List[str]) -> Optional[dict]:
    """Corrige une soumission QCM. `selected` = lettres cochées par l'étudiant.
    Renvoie {correct, expected, selected, per_option, score} ou None si pas de QCM."""
    case = get_case(num)
    if not case:
        return None
    qcm = case.get("qcm") or {}
    if not (qcm.get("options")):
        return None
    expected = parse_reponses(qcm.get("reponses"))
    chosen = sorted({str(s).upper() for s in (selected or []) if str(s).strip()})

    pub = get_qcm_public(num) or {}
    letters = pub.get("letters", [])
    per_option = []
    for let in letters:
        is_expected = let in expected
        is_chosen = let in chosen
        per_option.append({
            "letter": let,
            "expected": is_expected,
            "chosen": is_chosen,
            # état pédagogique par option
            "status": (
                "correct" if is_expected and is_chosen else
                "missed" if is_expected and not is_chosen else
                "wrong" if not is_expected and is_chosen else
                "neutral"
            ),
        })
    correct = (chosen == expected)
    # Score partiel : (bonnes cochées - mauvaises cochées) / nb attendues, borné 0-100
    n_expected = len(expected) or 1
    good = len([l for l in chosen if l in expected])
    bad = len([l for l in chosen if l not in expected])
    score = int(max(0, min(100, round((good - bad) / n_expected * 100))))
    if correct:
        score = 100
    return {
        "num": num,
        "correct": correct,
        "expected": expected,
        "selected": chosen,
        "per_option": per_option,
        "score": score,
    }
