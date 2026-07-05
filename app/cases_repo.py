"""
cases_repo.py — Accès à la banque de cas (data/cases.json).
Chargement paresseux + cache, filtrage par famille, expurgation de la réponse
de référence pour l'API publique (on ne divulgue pas l'interprétation avant
que l'étudiant ait répondu).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(_HERE, "..", "data"))
CASES_PATH = os.path.join(DATA_DIR, "cases.json")
IMAGES_DIR = os.path.join(DATA_DIR, "ecg_images")

# Champs jamais renvoyés par l'API tant que l'étudiant n'a pas répondu.
_HIDDEN_FIELDS = {"interpretation_ref", "commentaires", "qcm"}


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


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
        })
    return sorted(out, key=lambda d: d["num"])
