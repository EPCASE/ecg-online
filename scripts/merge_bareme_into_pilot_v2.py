#!/usr/bin/env python3
"""
merge_bareme_into_pilot_v2.py — Complète le pilote P1.2 (scoring_pilot_v2.json)
avec les points-clés du barème EXISTANT (scoring_config.json + cases_golden.json),
déjà validé en production, plutôt que de laisser le premier jet P1.2 (rédigé
indépendamment, 2-3 critères/cas) omettre des points-clés pourtant déjà connus.

Contexte (cf. /scoring-review, session du 2026-08-08) : sur le cas 24 (BAV
Mobitz I), le pilote P1.2 n'avait que 3 critères alors que le barème existant
en avait 7 — bloc incomplet droit/hémibloc antérieur gauche (BLOC_BIFASCICULAIRE),
rythme irrégulier (IRREGULIER), rythme sinusal (RYTHME_SINUSAL) et le label
générique BAV manquaient totalement. Constat systématique sur les 10 cas
pilotes (pilot=2-3 critères vs bareme=5-10 points-clés partout).

Stratégie :
  - Pour chaque cas du pilote, parcourir `scoring_config.json.cases[cid].roles`
    (label → "validant"/"complementaire") + `extra_validants` (traités validant).
  - Résoudre chaque label vers son concept ontologique via
    `cases_golden.json.cases[cid].mapping[label]` (golden_id, statut, concept_name).
    Si absent du mapping → on tente `golden_config.search_concepts` en dernier
    recours, puis on SKIP en le loggant si toujours introuvable (pas d'invention).
  - Si un concept_id est DÉJÀ présent dans le pilote (par concept_id, pas par
    label — les libellés diffèrent souvent), on NE DUPLIQUE PAS : on log un skip.
  - Sinon on ajoute un nouveau critère scoring_v2 complet :
      role: "required" si validant, "optional" si complementaire
      expected_status: statut du mapping ("present"/"absent")
      importance: "major" si validant, "minor" si complementaire
      error_severity: "major" si validant, "none" si complementaire
        (reste prudent — un relecteur humain doit re-valider ces valeurs
         par défaut, cf. evidence_source="bareme_v1_migre" pour tracer l'origine)
      sufficient_alone: false (jamais présumé — à valider par le relecteur)
      minimum_specificity: "exact_only" par défaut
      evidence_source: "bareme_v1_migre" (PAS "single_expert" ni "gpt_assisted_reviewed" :
        origine distincte et traçable — vient du barème de PRODUCTION historique,
        pas d'une annotation P1.2/P1.3 ni d'un premier jet IA)

Le rôle "exclusion" du barème v1 n'existe pas explicitement (roles ne connaît
que validant/complementaire) : un label au statut "absent" dans cases_golden
devient role="exclusion" (peu importe validant/complementaire d'origine, car
sémantiquement une exclusion n'est jamais "required" au sens scoring_v2).

Usage :
    python scripts/merge_bareme_into_pilot_v2.py            # dry-run (affiche le diff)
    python scripts/merge_bareme_into_pilot_v2.py --write    # applique et écrit le fichier

Ne touche JAMAIS à data/scoring_v2_review.json (annotations humaines P1.3
déjà enregistrées) — uniquement au pilote P1.2 brut, qui sert de PRÉ-REMPLISSAGE
pour les cas jamais encore sauvegardés par un relecteur (cf. app/scoring_v2_review.py
`_criteria_for_slot`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import golden_config  # noqa: E402
from app import cases_repo  # noqa: E402

DATA_DIR = cases_repo.DATA_DIR
PILOT_PATH = os.path.join(DATA_DIR, "scoring_pilot_v2.json")
BAREME_PATH = os.path.join(DATA_DIR, "scoring_config.json")
GOLDEN_PATH = os.path.join(DATA_DIR, "cases_golden.json")


def _slug(concept_id: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", concept_id.lower()).strip("_")


def resolve_label(cid: str, label: str, mapping: dict) -> dict | None:
    """Renvoie {concept_id, concept_name, statut} ou None si introuvable."""
    m = mapping.get(label)
    if m and m.get("golden_id"):
        return {
            "concept_id": m["golden_id"],
            "concept_name": m.get("concept_name", ""),
            "statut": m.get("statut", "present"),
        }
    # Dernier recours : fuzzy search direct sur le label (rare — le mapping
    # golden_config a normalement déjà résolu tous les labels du barème).
    matches = golden_config.search_concepts(label, limit=1)
    if matches and matches[0]["score"] >= 70:
        return {
            "concept_id": matches[0]["id"],
            "concept_name": matches[0]["name"],
            "statut": "present",
        }
    return None


def build_new_criterion(case_id: str, label: str, role_v1: str, resolved: dict,
                        used_slugs: set) -> dict:
    concept_id = resolved["concept_id"]
    statut = resolved["statut"]
    is_exclusion = statut == "absent"
    slug = _slug(concept_id)
    base_slug = slug
    n = 2
    while f"case_{case_id}_{slug}" in used_slugs:
        slug = f"{base_slug}_{n}"
        n += 1
    criterion_id = f"case_{case_id}_{slug}"
    used_slugs.add(criterion_id)

    if is_exclusion:
        role = "exclusion"
        importance = "intermediate"
        error_severity = "major"
    elif role_v1 == "validant":
        role = "required"
        importance = "major"
        error_severity = "major"
    else:
        role = "optional"
        importance = "minor"
        error_severity = "minor"

    return {
        "criterion_id": criterion_id,
        "concept_id": concept_id,
        "label": label,
        "role": role,
        "expected_status": statut,
        "importance": importance,
        "error_severity": error_severity,
        "alternative_group": None,
        "group_logic": "ALL",
        "group_min_n": None,
        "sufficient_alone": False,
        "minimum_specificity": "exact_only",
        "expert_confidence": "medium",
        "evidence_source": "bareme_v1_migre",
        "comment": f"Migré depuis le barème existant (scoring_config.json, rôle "
                   f"d'origine={role_v1}) — à RE-VALIDER par le relecteur (role/importance/"
                   f"error_severity/sufficient_alone posés par défaut, pas encore expertisés "
                   f"pour ce schéma V2).",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Écrit le fichier (sinon dry-run)")
    args = ap.parse_args()

    pilot = json.load(open(PILOT_PATH, encoding="utf-8"))
    bareme = json.load(open(BAREME_PATH, encoding="utf-8"))
    golden = json.load(open(GOLDEN_PATH, encoding="utf-8"))

    total_added = 0
    total_skipped_existing = 0
    total_skipped_unresolved = 0

    for case_id, criteria in pilot["cases"].items():
        bareme_case = bareme.get("cases", {}).get(case_id)
        golden_case = golden.get("cases", {}).get(case_id)
        if not bareme_case or not golden_case:
            print(f"[case {case_id}] pas de barème/golden existant — ignoré")
            continue
        mapping = golden_case.get("mapping", {})
        roles = bareme_case.get("roles", {})
        extra_validants = bareme_case.get("extra_validants", []) or []
        removed = set(bareme_case.get("removed") or [])

        existing_concept_ids = {c["concept_id"] for c in criteria}
        used_slugs = {c["criterion_id"] for c in criteria}

        labels_to_process = [(lbl, role) for lbl, role in roles.items()] + \
                            [(lbl, "validant") for lbl in extra_validants]

        for label, role_v1 in labels_to_process:
            if label in removed:
                continue
            resolved = resolve_label(case_id, label, mapping)
            if not resolved:
                print(f"[case {case_id}] ⚠️ non résolu, ignoré : « {label} »")
                total_skipped_unresolved += 1
                continue
            if resolved["concept_id"] in existing_concept_ids:
                total_skipped_existing += 1
                continue
            new_c = build_new_criterion(case_id, label, role_v1, resolved, used_slugs)
            criteria.append(new_c)
            existing_concept_ids.add(resolved["concept_id"])
            total_added += 1
            print(f"[case {case_id}] + {new_c['concept_id']} ({new_c['role']}) — « {label} »")

    print(f"\nTotal : +{total_added} critères ajoutés, "
          f"{total_skipped_existing} déjà présents (skip), "
          f"{total_skipped_unresolved} non résolus (skip).")

    if args.write:
        pilot.setdefault("_meta", {})["migration_bareme_v1"] = (
            "Complété depuis scoring_config.json + cases_golden.json le "
            "2026-08-08 (scripts/merge_bareme_into_pilot_v2.py) — critères "
            "evidence_source='bareme_v1_migre' à re-valider par le relecteur."
        )
        with open(PILOT_PATH, "w", encoding="utf-8") as f:
            json.dump(pilot, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Écrit dans {PILOT_PATH}")
    else:
        print("\n(dry-run — relancer avec --write pour appliquer)")


if __name__ == "__main__":
    main()
