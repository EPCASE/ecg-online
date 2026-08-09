#!/usr/bin/env python3
"""
bootstrap_pilot_v2_all_cases.py — Étend le pilote scoring_v2 (data/scoring_pilot_v2.json)
des 10 cas P1.2 initiaux à L'ENSEMBLE des 75 cas de la banque, en réutilisant
EXACTEMENT la même logique que scripts/merge_bareme_into_pilot_v2.py (même
construction de critère, même tag evidence_source="bareme_v1_migre"), mais
pour les cas qui n'existent PAS ENCORE dans le pilote (au lieu de compléter
des cas déjà présents).

Objectif (cf. session du 2026-08-08, demande : « avis IA pour l'ensemble des
cas avec pré-annotation ») : donner un point de départ structuré (scoring_v2)
pour les 65 cas restants, dérivé du barème de PRODUCTION déjà validé
(scoring_config.json + cases_golden.json), pour que le relecteur n'ait plus
qu'à RELIRE/CORRIGER au lieu de partir de zéro.

Ne touche jamais data/scoring_v2_review.json (annotations humaines).

Usage :
    python scripts/bootstrap_pilot_v2_all_cases.py            # dry-run
    python scripts/bootstrap_pilot_v2_all_cases.py --write    # applique
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import cases_repo  # noqa: E402
from scripts.merge_bareme_into_pilot_v2 import (  # noqa: E402
    resolve_label, build_new_criterion,
)

DATA_DIR = cases_repo.DATA_DIR
PILOT_PATH = os.path.join(DATA_DIR, "scoring_pilot_v2.json")
BAREME_PATH = os.path.join(DATA_DIR, "scoring_config.json")
GOLDEN_PATH = os.path.join(DATA_DIR, "cases_golden.json")


def build_case_criteria(case_id: str, bareme_case: dict, golden_case: dict) -> tuple[list[dict], int]:
    mapping = golden_case.get("mapping", {})
    roles = bareme_case.get("roles", {})
    extra_validants = bareme_case.get("extra_validants", []) or []
    removed = set(bareme_case.get("removed") or [])

    criteria: list[dict] = []
    existing_concept_ids: set[str] = set()
    used_slugs: set[str] = set()

    labels_to_process = [(lbl, role) for lbl, role in roles.items()] + \
        [(lbl, "validant") for lbl in extra_validants]

    n_unresolved = 0
    for label, role_v1 in labels_to_process:
        if label in removed:
            continue
        resolved = resolve_label(case_id, label, mapping)
        if not resolved:
            n_unresolved += 1
            continue
        if resolved["concept_id"] in existing_concept_ids:
            continue
        new_c = build_new_criterion(case_id, label, role_v1, resolved, used_slugs)
        criteria.append(new_c)
        existing_concept_ids.add(resolved["concept_id"])
    return criteria, n_unresolved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Écrit le fichier (sinon dry-run)")
    args = ap.parse_args()

    pilot = json.load(open(PILOT_PATH, encoding="utf-8"))
    bareme = json.load(open(BAREME_PATH, encoding="utf-8"))
    golden = json.load(open(GOLDEN_PATH, encoding="utf-8"))

    existing_cases = set(pilot["cases"].keys())
    all_bareme_cases = set(bareme.get("cases", {}).keys())
    missing = sorted(all_bareme_cases - existing_cases, key=int)

    print(f"Cas déjà dans le pilote : {len(existing_cases)}")
    print(f"Cas du barème total    : {len(all_bareme_cases)}")
    print(f"Cas à ajouter          : {len(missing)}")

    total_added_cases = 0
    total_criteria = 0
    total_unresolved = 0
    empty_cases = []

    for case_id in missing:
        bareme_case = bareme["cases"].get(case_id)
        golden_case = golden.get("cases", {}).get(case_id)
        if not bareme_case or not golden_case:
            print(f"[case {case_id}] pas de barème/golden — ignoré")
            continue
        criteria, n_unresolved = build_case_criteria(case_id, bareme_case, golden_case)
        total_unresolved += n_unresolved
        if not criteria:
            empty_cases.append(case_id)
            print(f"[case {case_id}] ⚠️ AUCUN critère résolu (0 ajouté)")
            continue
        pilot["cases"][case_id] = criteria
        total_added_cases += 1
        total_criteria += len(criteria)
        print(f"[case {case_id}] +{len(criteria)} critères ({n_unresolved} non résolus)")

    print(f"\nTotal : {total_added_cases} nouveaux cas, {total_criteria} critères, "
          f"{total_unresolved} labels non résolus (skip), {len(empty_cases)} cas vides : {empty_cases}")

    if args.write:
        pilot.setdefault("_meta", {})["bootstrap_all_cases"] = (
            "Étendu à l'ensemble des 75 cas depuis scoring_config.json + "
            "cases_golden.json le 2026-08-08 (scripts/bootstrap_pilot_v2_all_cases.py) "
            "— critères evidence_source='bareme_v1_migre' à re-valider par le relecteur."
        )
        with open(PILOT_PATH, "w", encoding="utf-8") as f:
            json.dump(pilot, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Écrit dans {PILOT_PATH}")
    else:
        print("\n(dry-run — relancer avec --write pour appliquer)")


if __name__ == "__main__":
    main()
