#!/usr/bin/env python3
"""
generate_v1_v2_diff_report.py — Rapport de différences entre le golden V1
(cases_golden.json + scoring_config.json, EN PRODUCTION) et le golden
conceptuel V2 (scoring_v2_review.json, PAS branché au moteur), pour les 75
cas — livrable P1.4 (audit_doc/roadmap_scientifique_2026.md §P1.4).

Objectif : documenter, cas par cas, ce qui change de rôle/statut entre les
deux schémas, pour qu'un futur branchement du V2 (P4) ne soit jamais une
surprise silencieuse. Ne modifie aucun fichier — génère un rapport markdown.

Usage :
    python scripts/generate_v1_v2_diff_report.py > docs/P1.4_diff_v1_v2_report.md
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def v1_concepts_for_case(golden_case, bareme_case):
    """Retourne {concept_id: role_v1} pour un cas donné, en V1."""
    mapping = golden_case.get("mapping", {})
    roles = bareme_case.get("roles", {})
    extra_validants = bareme_case.get("extra_validants", []) or []
    removed = set(bareme_case.get("removed") or [])
    out = {}
    for label, role in roles.items():
        if label in removed:
            continue
        info = mapping.get(label)
        if info and info.get("golden_id"):
            out[info["golden_id"]] = role
    for label in extra_validants:
        if label in removed:
            continue
        info = mapping.get(label)
        if info and info.get("golden_id"):
            out[info["golden_id"]] = "validant"
    return out


def v2_concepts_for_case(review_case):
    """Retourne {concept_id: (role_v2, expected_status, evidence_source)}."""
    crits = review_case.get("expert_1", {}).get("criteria", [])
    out = {}
    for cr in crits:
        out[cr["concept_id"]] = (cr["role"], cr["expected_status"], cr.get("evidence_source"))
    return out


ROLE_MAP_V1_TO_V2 = {"validant": "required", "complementaire": "optional"}


def main():
    golden = load("cases_golden.json")["cases"]
    bareme = load("scoring_config.json")["cases"]
    review = load("scoring_v2_review.json")["cases"]

    all_cases = sorted(set(golden) | set(review), key=int)

    print("# Rapport de différences V1 (production) vs V2 (pilote, non branché)")
    print()
    print("Généré automatiquement par `scripts/generate_v1_v2_diff_report.py`")
    print(f"(75 cas). Golden V1 = `cases_golden.json` + `scoring_config.json` ")
    print("(EN PRODUCTION). Golden V2 = `scoring_v2_review.json` (annotation ")
    print("`expert_1`, PAS branché au moteur de scoring, cf. `app/scoring_v2_review.py`).")
    print()
    print("Légende des écarts :")
    print("- 🆕 **only_v2** : concept présent en V2 mais absent du mapping V1")
    print("  (ajouté pendant la relecture, ex: nouveaux concepts ontologiques).")
    print("- ❌ **only_v1** : concept présent en V1 mais absent des critères V2")
    print("  (pas encore repris dans l'annotation experte, ou volontairement omis).")
    print("- 🔁 **role_diff** : rôle V1 (validant/complementaire) ne correspond pas")
    print("  à la conversion attendue en V2 (required/optional) — À VÉRIFIER, ")
    print("  car ça peut signifier soit une correction experte volontaire (bien),")
    print("  soit un oubli de migration (à corriger).")
    print()

    total_only_v2 = total_only_v1 = total_role_diff = 0
    cases_with_diffs = []

    for cid in all_cases:
        gcase = golden.get(cid, {})
        bcase = bareme.get(cid, {})
        rcase = review.get(cid, {})
        v1 = v1_concepts_for_case(gcase, bcase)
        v2 = v2_concepts_for_case(rcase)

        only_v2 = sorted(set(v2) - set(v1))
        only_v1 = sorted(set(v1) - set(v2))
        role_diffs = []
        for cid_concept in sorted(set(v1) & set(v2)):
            role_v1 = v1[cid_concept]
            role_v2, expected_status, source = v2[cid_concept]
            expected_v2 = ROLE_MAP_V1_TO_V2.get(role_v1)
            # exclusion en V2 n'a pas d'équivalent direct en V1 (status=absent
            # dans golden -> déjà transformé en exclusion par la migration)
            if expected_status == "absent":
                expected_v2 = "exclusion"
            if role_v2 != expected_v2:
                role_diffs.append((cid_concept, role_v1, role_v2, expected_status, source))

        if not only_v2 and not only_v1 and not role_diffs:
            continue

        cases_with_diffs.append(cid)
        total_only_v2 += len(only_v2)
        total_only_v1 += len(only_v1)
        total_role_diff += len(role_diffs)

        print(f"## Cas {cid}")
        print()
        if only_v2:
            print(f"🆕 **only_v2** ({len(only_v2)}) : {', '.join(only_v2)}")
            print()
        if only_v1:
            print(f"❌ **only_v1** ({len(only_v1)}) : {', '.join(only_v1)}")
            print()
        if role_diffs:
            print(f"🔁 **role_diff** ({len(role_diffs)}) :")
            print()
            print("| concept_id | role V1 | role V2 | expected_status V2 | evidence_source |")
            print("|---|---|---|---|---|")
            for cid_c, rv1, rv2, es, src in role_diffs:
                print(f"| {cid_c} | {rv1} | {rv2} | {es} | {src} |")
            print()

    print("---")
    print()
    print("## Synthèse globale")
    print()
    print(f"- Cas avec au moins un écart : **{len(cases_with_diffs)} / {len(all_cases)}**")
    print(f"- Total concepts only_v2 (nouveaux en V2) : **{total_only_v2}**")
    print(f"- Total concepts only_v1 (non repris en V2) : **{total_only_v1}**")
    print(f"- Total écarts de rôle (role_diff) : **{total_role_diff}**")
    print()
    print("**Lecture** : `only_v1` est le point le plus sensible pour une future ")
    print("migration P4 — un concept validant/complémentaire de production non ")
    print("repris en V2 signifierait une perte silencieuse de critère si on ")
    print("basculait le moteur sur V2 sans vérifier. `role_diff` peut être une ")
    print("correction experte légitime (à documenter) ou un oubli de migration.")


if __name__ == "__main__":
    main()
