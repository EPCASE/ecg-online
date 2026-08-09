#!/usr/bin/env python3
"""
generate_ai_review_all_cases.py — Génère un second avis IA (ai_review) pour
TOUS les cas du pilote scoring_v2 (75 cas après bootstrap), en se basant sur
les critères du PILOTE (pas sur un expert_1 fictif — cf. leçon apprise le
2026-08-08 : ne jamais écrire un expert_1 avec annotateur vide, ça masque le
pilote et se fait passer pour une validation humaine réelle, cf. le bug du
cas 24).

Contrairement à `scoring_v2_review.generate_ai_review()` (qui exige un
expert_1 déjà enregistré), ce script appelle directement
`gpt_annotator.review_scoring_criteria()` sur les critères du pilote, et
stocke le résultat dans `ai_review` SANS jamais toucher à `expert_1`.
Objectif : donner au relecteur un avis IA en même temps que la
pré-annotation, pour qu'il puisse relire/valider plus vite (cf. demande
utilisateur : « avis IA pour l'ensemble des cas avec preannotation »).

Usage : python scripts/generate_ai_review_all_cases.py [--only 3,24,48]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import cases_repo, gpt_annotator, scoring_v2_review as r  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default="", help="Liste de case_id séparés par des virgules (sinon tous)")
    args = ap.parse_args()

    pilot = r._load_pilot()
    data = r.load()

    case_ids = sorted(pilot["cases"].keys(), key=int)
    if args.only:
        wanted = set(args.only.split(","))
        case_ids = [c for c in case_ids if c in wanted]

    ok, errors, skipped = 0, 0, 0
    for case_id in case_ids:
        criteria = pilot["cases"].get(case_id, [])
        if not criteria:
            skipped += 1
            continue
        try:
            ecg = cases_repo.get_case(int(case_id)) or {}
        except (TypeError, ValueError):
            ecg = {}
        interpretation_ref = ecg.get("interpretation_ref", "")
        if not interpretation_ref:
            print(f"[case {case_id}] pas d'interpretation_ref — skip")
            skipped += 1
            continue

        try:
            result = gpt_annotator.review_scoring_criteria(interpretation_ref, criteria)
        except Exception as exc:  # noqa: BLE001
            print(f"[case {case_id}] ERREUR : {exc}")
            errors += 1
            continue
        if result is None:
            print(f"[case {case_id}] IA indisponible (pas de clé/erreur modèle)")
            errors += 1
            continue

        entry = data["cases"].setdefault(case_id, {})
        entry["ai_review"] = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": gpt_annotator.DEFAULT_MODEL,
            "alertes": result.get("alertes", []),
            "synthese": result.get("synthese", ""),
            "based_on": "pilot_v2",  # traçabilité : pas basé sur un expert_1 validé
        }
        n_alertes = len(result.get("alertes", []))
        print(f"[case {case_id}] OK — {n_alertes} alerte(s)")
        ok += 1

    r.save(data)
    print(f"\nTotal : {ok} avis générés, {errors} erreurs, {skipped} cas ignorés (sans texte/critères).")


if __name__ == "__main__":
    main()
