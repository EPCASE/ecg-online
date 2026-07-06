"""
scoring_config.py — Curation « validant / complémentaire » des concepts de correction.
======================================================================================
Objectif : rendre la notation moins sévère. Pour chaque cas, l'enseignant choisit
parmi les `points_cles` (concepts de correction) ceux qui sont :

  • VALIDANT      → comptent DANS LA NOTE (en général 1 ou 2 par cas : le
                    diagnostic principal et l'anomalie-clé).
  • COMPLÉMENTAIRE → enrichissent la DESCRIPTION / le feedback mais ne pèsent
                    PAS sur la note (l'étudiant n'est pas pénalisé s'il les omet).

Persistance : data/scoring_config.json
  {
    "version": 1,
    "updated": "2026-07-05T18:00:00",
    "cases": {
      "1": {
        "roles": { "<label exact du point_cle>": "validant" | "complementaire" },
        "extra_validants": [ "<concept ajouté à la main>", ... ],
        "removed": [ "<label de point_cle à ne PAS utiliser du tout>", ... ]
      }
    }
  }

Le fichier ne stocke QUE les choix (par label) ; les concepts eux-mêmes restent
dans cases_reference.json. À la lecture, on re-joint les deux → robuste aux
retouches de la référence. Un cas sans config prend un défaut raisonnable :
rang A ⇒ validant, rang B/C ⇒ complémentaire.

Les diagnostics/concepts « supprimés » (`removed`) sont totalement exclus : ils
ne comptent ni dans la note ni dans la description, et ne sont pas montrés à
l'étudiant comme « à compléter ». On peut les restaurer à tout moment.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

from . import cases_repo

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(cases_repo.DATA_DIR, "scoring_config.json")

VALIDANT = "validant"
COMPLEMENTAIRE = "complementaire"
REMOVED = "removed"


# ─────────────────────────── I/O bas niveau ───────────────────────────
def _empty() -> dict:
    return {"version": 1, "updated": None, "cases": {}}


def _load() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return _empty()
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("version", 1)
        data.setdefault("cases", {})
        return data
    except (json.JSONDecodeError, OSError):
        return _empty()


def _atomic_write(data: dict) -> None:
    """Écriture atomique (tmp + replace) pour ne jamais corrompre le fichier."""
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CONFIG_PATH), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ─────────────────────────── Défaut & fusion ───────────────────────────
def _default_role(rang: str) -> str:
    return VALIDANT if str(rang).upper() == "A" else COMPLEMENTAIRE


def curated_points(num, include_removed: bool = False) -> List[dict]:
    """Concepts d'un cas, chacun enrichi de son `role` (validant/complémentaire).

    Fusionne `points_cles` (de la référence) avec les choix enregistrés.
    Un point non configuré prend le rôle par défaut (A ⇒ validant).
    Les `extra_validants` (concepts ajoutés à la main) sont ajoutés en fin.

    `include_removed` : si True, les concepts supprimés sont renvoyés avec
    `role="removed"` (pour l'éditeur de curation) ; sinon ils sont omis (pour
    la correction).
    """
    ref = cases_repo.get_reference(num) or {}
    points = ref.get("points_cles", []) or []
    case_cfg = _load().get("cases", {}).get(str(num), {})
    roles: Dict[str, str] = case_cfg.get("roles", {}) or {}
    removed = set(case_cfg.get("removed", []) or [])

    out: List[dict] = []
    for p in points:
        label = (p.get("label") or "").strip()
        if not label:
            continue
        is_removed = label in removed
        if is_removed and not include_removed:
            continue
        rang = p.get("rang", "?")
        role = REMOVED if is_removed else (roles.get(label) or _default_role(rang))
        out.append({
            "label": label,
            "rang": rang,
            "role": role,
            "source": "points_cles",
            "configured": label in roles or is_removed,
        })
    for lbl in case_cfg.get("extra_validants", []) or []:
        lbl = (lbl or "").strip()
        if lbl:
            out.append({
                "label": lbl, "rang": "A", "role": VALIDANT,
                "source": "custom", "configured": True,
            })
    return out


def split_for_grader(num) -> dict:
    """Renvoie {validants:[{label,rang}], complementaires:[{label,rang}]}
    pour injection dans le prompt de correction. Les concepts supprimés
    (`removed`) sont exclus."""
    validants, complementaires = [], []
    for c in curated_points(num):   # include_removed=False → removed exclus
        item = {"label": c["label"], "rang": c["rang"]}
        (validants if c["role"] == VALIDANT else complementaires).append(item)
    return {"validants": validants, "complementaires": complementaires}


# ─────────────────────────── API haut niveau ───────────────────────────
def get_case_config(num) -> Optional[dict]:
    """Config brute enregistrée pour un cas (ou None si aucune)."""
    return _load().get("cases", {}).get(str(num))


def save_case_config(num, roles: Dict[str, str],
                     extra_validants: Optional[List[str]] = None,
                     removed: Optional[List[str]] = None) -> dict:
    """Enregistre les rôles choisis pour un cas. `roles` = {label: role}.
    `removed` = labels de points_cles à exclure totalement.
    Ignore les rôles invalides. Renvoie la config du cas après écriture."""
    clean_roles = {
        str(k): (VALIDANT if str(v) == VALIDANT else COMPLEMENTAIRE)
        for k, v in (roles or {}).items() if str(k).strip()
    }
    clean_extra = [s.strip() for s in (extra_validants or []) if s and s.strip()]
    clean_removed = sorted({s.strip() for s in (removed or []) if s and s.strip()})
    # Un concept supprimé ne doit pas garder de rôle actif (cohérence).
    for lbl in clean_removed:
        clean_roles.pop(lbl, None)

    data = _load()
    data.setdefault("cases", {})[str(num)] = {
        "roles": clean_roles,
        "extra_validants": clean_extra,
        "removed": clean_removed,
    }
    _atomic_write(data)
    return data["cases"][str(num)]


def reset_case_config(num) -> None:
    """Supprime la config d'un cas (retour aux défauts)."""
    data = _load()
    data.get("cases", {}).pop(str(num), None)
    _atomic_write(data)


def overview() -> List[dict]:
    """Index de tous les cas + résumé de leur curation (pour la page d'édition)."""
    out = []
    for c in cases_repo.all_cases():
        num = c.get("num")
        pts = curated_points(num)   # sans les supprimés
        nb_val = sum(1 for p in pts if p["role"] == VALIDANT)
        cfg = get_case_config(num) or {}
        out.append({
            "num": num,
            "titre": c.get("titre"),
            "famille": c.get("famille"),
            "nb_concepts": len(pts),
            "nb_validants": nb_val,
            "nb_removed": len(cfg.get("removed", []) or []),
            "configured": get_case_config(num) is not None,
        })
    return sorted(out, key=lambda d: d["num"])
