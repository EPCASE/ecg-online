# -*- coding: utf-8 -*-
"""
p42_add_golden_variants_2026_08_12.py — P4.2, arbitrage expert « a » (2026-08-12).

Ajoute au golden des cas « ECG normal » les variantes physiologiques que
l'expert crédite mais que le barème ne mentionnait pas — et qui, via
excludes_families (ECG_NORMAL ⟂ famille ARYTHMIE / ANOMALIE_DES_ONDES_T),
annulaient tout le score des copies les décrivant (S113, S018, S104 cas 3 ;
S003, S129 cas 8) :

  cas 3 → ARYTHMIE_SINUSALE   (arythmie sinusale physiologique respiratoire)
  cas 8 → ONDE_T_NEGATIVE     (T négatives V1-V3, variante normale acceptée)

Rang C ⇒ rôle complémentaire par défaut (poids faible : ne pénalise presque
pas les étudiants qui ne la mentionnent pas), statut present. Une fois dans le
golden, le « golden override » de scoring_v3._check_excludes (variante 2)
neutralise l'exclusion — c'est le mécanisme générique voulu.

Édite : data/cases_reference.json (points_cles) + data/cases_golden.json
(mapping). Sauvegardes .bak_p42_variants avant écriture. Idempotent.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
REF = os.path.join(DATA, "cases_reference.json")
GOLDEN = os.path.join(DATA, "cases_golden.json")

ADDITIONS = {
    "3": {
        "label": "Arythmie sinusale physiologique respiratoire (variante normale, acceptée)",
        "rang": "C",
        "golden_id": "ARYTHMIE_SINUSALE",
    },
    "8": {
        "label": "Ondes T négatives en V1-V3 (variante normale, acceptée)",
        "rang": "C",
        "golden_id": "ONDE_T_NEGATIVE",
    },
}


def main() -> int:
    sys.path.insert(0, ROOT)
    from app import golden_config  # noqa: E402

    onto = golden_config._onto_concepts()
    for add in ADDITIONS.values():
        if add["golden_id"] not in onto:
            print(f"[erreur] concept absent de l'ontologie : {add['golden_id']}")
            return 1

    for p in (REF, GOLDEN):
        bak = p + ".bak_p42_variants"
        if not os.path.exists(bak):
            shutil.copy2(p, bak)
            print(f"[backup] {bak}")

    # 1) points_cles dans cases_reference.json
    with open(REF, encoding="utf-8") as f:
        ref = json.load(f)
    refs = ref.get("references", ref)  # liste de {num, points_cles, ...}
    by_num = {str(c.get("num")): c for c in refs} if isinstance(refs, list) else refs
    changed_ref = False
    for num, add in ADDITIONS.items():
        case = by_num.get(num)
        if case is None:
            print(f"[erreur] cas {num} introuvable dans cases_reference.json")
            return 1
        pts = case.setdefault("points_cles", [])
        if any((p.get("label") or "") == add["label"] for p in pts):
            print(f"[skip] cas {num} : point déjà présent")
        else:
            pts.append({"label": add["label"], "rang": add["rang"]})
            changed_ref = True
            print(f"[ref] cas {num} : + point_cle rang {add['rang']} : {add['label']}")
    if changed_ref:
        with open(REF, "w", encoding="utf-8") as f:
            json.dump(ref, f, ensure_ascii=False, indent=2)

    # 2) mapping dans cases_golden.json
    with open(GOLDEN, encoding="utf-8") as f:
        gold = json.load(f)
    changed_gold = False
    for num, add in ADDITIONS.items():
        mp = gold.setdefault("cases", {}).setdefault(num, {}).setdefault("mapping", {})
        if add["label"] in mp:
            print(f"[skip] cas {num} : mapping déjà présent")
            continue
        mp[add["label"]] = {
            "golden_id": add["golden_id"],
            "concept_name": onto[add["golden_id"]].get("concept_name", ""),
            "statut": "present",
            "confiance": 1.0,
            "valide_par": "humain",
            "justification": "P4.2 calibration 2026-08-12 — variante physiologique créditée "
                             "par l'expert ; ajoutée au golden pour activer le golden override "
                             "des exclusions (scoring_v3, variante 2).",
        }
        changed_gold = True
        print(f"[golden] cas {num} : {add['golden_id']} mappé")
    if changed_gold:
        with open(GOLDEN, "w", encoding="utf-8") as f:
            json.dump(gold, f, ensure_ascii=False, indent=2)

    # 3) vérification via l'API du scorer
    golden_config._load.cache_clear() if hasattr(golden_config._load, "cache_clear") else None
    for num in ADDITIONS:
        g = golden_config.golden_for_scorer(int(num))
        ids = [e["concept_id"] for e in g["validants"] + g["descripteurs"]]
        ok = ADDITIONS[num]["golden_id"] in ids
        print(f"[verif] cas {num} : {ADDITIONS[num]['golden_id']} dans golden_for_scorer → {ok}")
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
