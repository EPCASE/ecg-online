"""
golden_config.py — Le « pont sémantique » : barème (labels libres) → concepts ontologiques.
============================================================================================
Deuxième couche de curation, PAR-DESSUS `scoring_config.py`.

  • `scoring_config.json` répond à : « ce point-clé est-il VALIDANT ou COMPLÉMENTAIRE ? »
    (le RÔLE — déjà construit, déjà validé en live).
  • `cases_golden.json` (ce module) répond à : « à quel CONCEPT de l'ontologie
    ce point-clé correspond-il ? » (le mapping sémantique — l'étape 1).

En joignant les deux, on obtient le contrat que le **scorer ontologique V3**
attend :  validant/complémentaire  ×  concept_id  →  {validants:[IDs], descripteurs:[IDs]}.

    role (scoring_config)          concept_id (golden_config)          scorer onto
    ─────────────────────          ─────────────────────────          ───────────
    validant            ┐                                          ┌  validant onto
    complementaire      ├──── jointure par `label` exact ────┤  descripteur onto
    removed  (exclu)    ┘                                          └  (exclu)

Le fichier `cases_golden.json` est produit une première fois par le script
`scripts/map_bareme_to_ontology.py` (GPT-5.5), puis corrigé À LA MAIN dans
l'UI `/curation` (picker de concepts). Ce module est la source de vérité pour
les éditions humaines.

Persistance : data/cases_golden.json
  {
    "version": 1,
    "updated": "...",
    "model": "gpt-5.5",
    "cases": {
      "1": {
        "diagnostic_principal": "Inversion des électrodes des deux bras",
        "mapping": {
          "<label exact du point_cle>": {
            "golden_id": "INVERSION_ELECTRODES_BRAS",
            "concept_name": "Inversion des électrodes des bras",  // cache d'affichage
            "confiance": 0.94,
            "valide_par": "gpt" | "humain" | "manuel",
            "justification": "..."
          }
        }
      }
    }
  }

Le mapping ne stocke QUE le lien label→concept. Le rôle reste dans
`scoring_config.json` (robuste : retoucher l'un n'écrase pas l'autre).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional

from . import cases_repo
from . import scoring_config

GOLDEN_PATH = os.path.join(cases_repo.DATA_DIR, "cases_golden.json")

# L'ontologie est VENDORÉE dans rag_pipeline/data/ (déployée sur Scalingo).
# On la cherche d'abord via un chemin PORTABLE (relatif à ce fichier) pour que
# ça marche identiquement en local (Windows) et en production (Linux/Scalingo).
# Les chemins Windows absolus ne sont conservés qu'en ultime repli (dev only).
_APP_DIR = os.path.dirname(os.path.abspath(__file__))   # .../ecg-online/app
_ROOT_DIR = os.path.dirname(_APP_DIR)                    # .../ecg-online
ONTO_CANDIDATES = [
    os.path.join(_ROOT_DIR, "rag_pipeline", "data", "ontology_v2.json"),  # vendorée (prod + local)
    os.path.join(cases_repo.DATA_DIR, "ontology_v2.json"),
    r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\RAG ontologique\data\ontology_v2.json",
]

VALIDE_PAR_GPT = "gpt"
VALIDE_PAR_HUMAIN = "humain"
VALIDE_PAR_MANUEL = "manuel"

# Polarité du concept, alignée sur le `statut` du NER ontologique.
#   present : le concept EST présent sur le tracé (« il y a une FA »).
#   absent  : le concept est ACTIVEMENT nié (« pas de FA », « éliminer une FA »).
# Défaut = present (rétrocompatible avec les mappings déjà écrits).
STATUT_PRESENT = "present"
STATUT_ABSENT = "absent"
_STATUTS = (STATUT_PRESENT, STATUT_ABSENT)


def _norm_statut(s) -> str:
    s = str(s or "").strip().lower()
    return STATUT_ABSENT if s == STATUT_ABSENT else STATUT_PRESENT


# ─────────────────────────── Ontologie (lecture) ───────────────────────────
def canon(s) -> str:
    """Normalisation robuste : minuscules, sans accents, alphanumérique compacté."""
    s = unicodedata.normalize("NFKD", str(s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


@lru_cache(maxsize=1)
def _onto_concepts() -> dict:
    """Dict {concept_id: {concept_name, categorie, type, poids, synonymes, ...}}."""
    for p in ONTO_CANDIDATES:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("concepts", data)
    return {}


def onto_available() -> bool:
    return bool(_onto_concepts())


def resolve_concept(cid: Optional[str]) -> Optional[dict]:
    """Infos d'affichage d'un concept, ou None si l'ID n'existe pas dans l'onto."""
    if not cid:
        return None
    c = _onto_concepts().get(cid)
    if not c:
        return None
    return {
        "id": cid,
        "name": c.get("concept_name", ""),
        "name_en": c.get("concept_name_en", ""),
        "categorie": c.get("categorie", ""),
        "type": c.get("type", ""),
        "poids": c.get("poids"),
    }


@lru_cache(maxsize=1)
def _search_rows() -> List[dict]:
    """Pré-calcul de l'index de recherche (nom + synonymes normalisés)."""
    rows = []
    for cid, c in _onto_concepts().items():
        names = [c.get("concept_name", ""), c.get("concept_name_en", "")]
        names += c.get("synonymes", []) or []
        keys = [canon(n) for n in names if n]
        rows.append({
            "id": cid,
            "name": c.get("concept_name", ""),
            "categorie": c.get("categorie", ""),
            "type": c.get("type", ""),
            "keys": [k for k in keys if k],
        })
    return rows


def search_concepts(q: str, limit: int = 20) -> List[dict]:
    """Recherche floue d'un concept par nom/synonyme, pour le picker de l'UI.
    Score : exact 100 · préfixe 80 · inclusion 65 · tous les tokens 55 · overlap partiel."""
    ck = canon(q)
    if not ck:
        return []
    toks = set(ck.split())
    scored = []
    for r in _search_rows():
        best = 0
        for k in r["keys"]:
            if k == ck:
                best = max(best, 100)
            elif k.startswith(ck):
                best = max(best, 80)
            elif ck in k:
                best = max(best, 65)
            else:
                kt = set(k.split())
                if toks and toks <= kt:
                    best = max(best, 55)
                else:
                    ov = toks & kt
                    if ov:
                        best = max(best, 25 + len(ov) * 6)
        if best > 0:
            scored.append((best, r))
    scored.sort(key=lambda x: (-x[0], len(x[1]["name"])))
    return [{
        "id": r["id"], "name": r["name"],
        "categorie": r["categorie"], "type": r["type"], "score": s,
    } for s, r in scored[:limit]]


# ─────────────────────────── I/O mapping (label→concept) ───────────────────────────
def _empty() -> dict:
    return {"version": 1, "updated": None, "model": None, "cases": {}}


def _load() -> dict:
    if not os.path.exists(GOLDEN_PATH):
        return _empty()
    try:
        with open(GOLDEN_PATH, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("version", 1)
        data.setdefault("cases", {})
        return data
    except (json.JSONDecodeError, OSError):
        return _empty()


def _atomic_write(data: dict) -> None:
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(GOLDEN_PATH), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(GOLDEN_PATH), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, GOLDEN_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def get_case_mapping(num) -> Dict[str, dict]:
    """{label_exact: {golden_id, concept_name, confiance, valide_par, justification}}."""
    case = _load().get("cases", {}).get(str(num), {}) or {}
    return case.get("mapping", {}) or {}


def get_case_diag(num) -> str:
    case = _load().get("cases", {}).get(str(num), {}) or {}
    return case.get("diagnostic_principal", "") or ""


# ─────────────────────────── Jointure rôle × concept ───────────────────────────
def attach_mapping(num, concepts: List[dict]) -> List[dict]:
    """Enrichit chaque concept curé (issu de scoring_config.curated_points) de son
    mapping ontologique, pour l'UI de curation. Mutation en place + renvoi."""
    mp = get_case_mapping(num)
    for c in concepts:
        m = mp.get(c["label"]) or {}
        cid = m.get("golden_id")
        info = resolve_concept(cid) if cid else None
        c["golden_id"] = cid or None
        c["golden_name"] = (info or {}).get("name") or m.get("concept_name")
        c["golden_categorie"] = (info or {}).get("categorie")
        c["golden_conf"] = m.get("confiance")
        c["golden_by"] = m.get("valide_par")
        c["golden_statut"] = _norm_statut(m.get("statut"))
        # concept réellement présent dans l'ontologie (garde contre les ID périmés)
        c["golden_valid"] = bool(cid and info)
    return concepts


def golden_for_scorer(num) -> dict:
    """Contrat final pour le scorer ontologique V3 : joint le RÔLE (scoring_config)
    et le CONCEPT (golden_config), en excluant les concepts supprimés (removed).

    Chaque entrée porte un `statut` (present/absent) aligné sur le NER onto :
      • present : le concept doit être AFFIRMÉ par l'étudiant (cas nominal).
      • absent  : le concept doit être ÉCARTÉ / nié (« éliminer une FA ») — c'est
        un critère de non-régression, scoré à part par le pipeline onto.

    Renvoie :
      {num, diagnostic_principal,
       validants:   [{concept_id, concept_name, label, rang, statut}],  # font la note
       descripteurs:[{concept_id, concept_name, label, rang, statut}],  # bonus / description
       exclusions:  [{concept_id, concept_name, label, rang, role}],    # statut=absent (vue dédiée)
       unresolved:  [{label, rang, role}]}                              # pas encore mappés
    """
    pts = scoring_config.curated_points(num)  # removed déjà exclus
    mp = get_case_mapping(num)
    validants, descripteurs, exclusions, unresolved = [], [], [], []
    for p in pts:
        m = mp.get(p["label"]) or {}
        info = resolve_concept(m.get("golden_id"))
        if not info:
            unresolved.append({"label": p["label"], "rang": p["rang"], "role": p["role"]})
            continue
        statut = _norm_statut(m.get("statut"))
        entry = {
            "concept_id": info["id"], "concept_name": info["name"],
            "label": p["label"], "rang": p["rang"], "statut": statut,
        }
        (validants if p["role"] == scoring_config.VALIDANT else descripteurs).append(entry)
        if statut == STATUT_ABSENT:
            exclusions.append({**entry, "role": p["role"]})
    diag = get_case_diag(num) or (validants[0]["label"] if validants else "")
    return {
        "num": num, "diagnostic_principal": diag,
        "validants": validants, "descripteurs": descripteurs,
        "exclusions": exclusions, "unresolved": unresolved,
    }


def save_case_mapping(num, mapping_in: Dict[str, object],
                      diagnostic_principal: Optional[str] = None) -> dict:
    """Enregistre le mapping validé pour un cas. `mapping_in` = {label: golden_id}
    ou {label: {golden_id, valide_par, confiance, justification}}.

    - Un `golden_id` vide/None ⇒ le label redevient NON mappé (entrée retirée).
    - Un `golden_id` absent de l'ontologie ⇒ ignoré (garde-fou).
    - L'UI envoie le mapping COMPLET du cas ⇒ on remplace le bloc en entier.
    """
    onto = _onto_concepts()
    clean: Dict[str, dict] = {}
    for label, val in (mapping_in or {}).items():
        label = str(label).strip()
        if not label:
            continue
        if isinstance(val, dict):
            cid = str(val.get("golden_id") or "").strip()
            by = val.get("valide_par") or VALIDE_PAR_HUMAIN
            conf = val.get("confiance")
            note = val.get("justification") or val.get("note")
            statut = _norm_statut(val.get("statut"))
        else:
            cid = str(val or "").strip()
            by, conf, note = VALIDE_PAR_HUMAIN, 1.0, None
            statut = STATUT_PRESENT
        if not cid or cid not in onto:
            continue  # non mappé (ou ID invalide) → on n'écrit rien
        entry = {
            "golden_id": cid,
            "concept_name": onto[cid].get("concept_name", ""),
            "valide_par": by,
            "statut": statut,
        }
        if conf is not None:
            entry["confiance"] = conf
        if note:
            entry["justification"] = note
        clean[label] = entry

    data = _load()
    case = data.setdefault("cases", {}).setdefault(str(num), {})
    case["mapping"] = clean
    if diagnostic_principal is not None:
        case["diagnostic_principal"] = str(diagnostic_principal).strip()
    _atomic_write(data)
    return case


# ─────────────────────────── Vue d'ensemble (sidebar) ───────────────────────────
def overview_status() -> Dict[int, dict]:
    """Par cas : {nb_points, nb_mapped, nb_human} pour la progression du mapping."""
    cases = _load().get("cases", {})
    out: Dict[int, dict] = {}
    for c in cases_repo.all_cases():
        num = c.get("num")
        if num is None:
            continue
        pts = scoring_config.curated_points(num)  # removed exclus
        mp = (cases.get(str(num), {}) or {}).get("mapping", {}) or {}
        nb_mapped = sum(1 for p in pts if resolve_concept((mp.get(p["label"]) or {}).get("golden_id")))
        nb_human = sum(1 for p in pts
                       if (mp.get(p["label"]) or {}).get("valide_par") in (VALIDE_PAR_HUMAIN, VALIDE_PAR_MANUEL))
        out[num] = {"nb_points": len(pts), "nb_mapped": nb_mapped, "nb_human": nb_human}
    return out
