#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_test_coherence_2026_08_11.py — tests unitaires du module coherence (P4.3b-C).

Couvre les 6 situations du design (§5 étape C) :
  1. HARD actif (excludes, golden UNKNOWN)                → active/error
  2. HARD data_inconsistency (golden accepte les 2 pôles) → data_inconsistency
  3. DEFAULT overridden (golden accepte les 2 pôles)      → overridden
  4. DEFAULT confirmé par golden FORBIDDEN                → active/confirmed
  5. DEFAULT golden UNKNOWN                               → active/warning
  6. allowed_cooccurrences                                → overridden
+ symétrie (ordre A/B indifférent), present-only (l'appelant filtre).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rag_pipeline"))

import coherence  # noqa: E402
from coherence import (  # noqa: E402
    ACTIVE, DATA_INCONSISTENCY, OVERRIDDEN,
    check_response_coherence, build_constraint_registry, golden_status,
)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print(f"  OK  {label}")
    else:
        print(f"  KO  {label} {detail}")
        FAILURES.append(label)


def golden(entries, allowed=None):
    """entries: list of (golden_id, statut) ; construit un case_golden."""
    g = {"mapping": {f"label_{i}": {"golden_id": gid, "statut": st}
                     for i, (gid, st) in enumerate(entries)}}
    if allowed:
        g["allowed_cooccurrences"] = allowed
    return g


def find(contras, a, b):
    key = tuple(sorted((a, b)))
    for c in contras:
        if tuple(sorted((c.concept_a, c.concept_b))) == key:
            return c
    return None


def main():
    reg = build_constraint_registry()
    print(f"Registry : {len(reg)} paires")
    n_hard = sum(1 for c in reg.values() if c.kind == "excludes")
    n_def = sum(1 for c in reg.values() if c.kind == "conflicts_by_default")
    n_fam = sum(1 for c in reg.values() if c.kind == "excludes_families")
    print(f"  excludes={n_hard} conflicts_by_default={n_def} families={n_fam}")
    # après migration : 16 déclarations excludes → paires canoniques dédupliquées
    check("registry contient des HARD et des DEFAULT", n_hard > 0 and n_def > 0)

    # 1. HARD actif — HYPERKALIEMIE/HYPOKALIEMIE, golden vide
    r = check_response_coherence({"HYPERKALIEMIE", "HYPOKALIEMIE"}, {})
    c = find(r, "HYPERKALIEMIE", "HYPOKALIEMIE")
    check("1. HARD actif", c is not None and c.status == ACTIVE and c.severity == "error",
          f"got={c}")

    # 2. HARD data_inconsistency — golden accepte les 2 pôles
    g = golden([("HYPERKALIEMIE", "present"), ("HYPOKALIEMIE", "present")])
    r = check_response_coherence({"HYPERKALIEMIE", "HYPOKALIEMIE"}, g)
    c = find(r, "HYPERKALIEMIE", "HYPOKALIEMIE")
    check("2. HARD data_inconsistency", c is not None and c.status == DATA_INCONSISTENCY,
          f"got={c}")

    # 3. DEFAULT overridden — FA+BAV complet : golden accepte FA (via flutter?) —
    #    utiliser IRREGULIER/RYTHME_REGULIER acceptés tous deux
    g = golden([("IRREGULIER", "present"), ("RYTHME_REGULIER", "present")])
    r = check_response_coherence({"IRREGULIER", "RYTHME_REGULIER"}, g)
    c = find(r, "IRREGULIER", "RYTHME_REGULIER")
    check("3. DEFAULT overridden (golden_accepts_both)",
          c is not None and c.status == OVERRIDDEN and c.detail == "golden_accepts_both",
          f"got={c}")

    # 4. DEFAULT confirmé par FORBIDDEN
    g = golden([("RYTHME_REGULIER", "absent")])
    r = check_response_coherence({"IRREGULIER", "RYTHME_REGULIER"}, g)
    c = find(r, "IRREGULIER", "RYTHME_REGULIER")
    check("4. DEFAULT confirmé par golden FORBIDDEN",
          c is not None and c.status == ACTIVE and c.detail == "confirmed_by_golden_forbidden",
          f"got={c}")

    # 5. DEFAULT golden UNKNOWN → warning actif, detail vide
    r = check_response_coherence({"BLOC_DE_BRANCHE", "QRS_FINS"}, {})
    c = find(r, "BLOC_DE_BRANCHE", "QRS_FINS")
    check("5. DEFAULT UNKNOWN → warning actif",
          c is not None and c.status == ACTIVE and c.severity == "warning" and c.detail == "",
          f"got={c}")

    # 6. allowed_cooccurrences
    g = golden([], allowed=[["QRS_FINS", "BLOC_DE_BRANCHE"]])
    r = check_response_coherence({"BLOC_DE_BRANCHE", "QRS_FINS"}, g)
    c = find(r, "BLOC_DE_BRANCHE", "QRS_FINS")
    check("6. allowed_cooccurrence → overridden",
          c is not None and c.status == OVERRIDDEN and c.detail == "allowed_cooccurrence",
          f"got={c}")

    # 7. Symétrie : la contrainte se déclenche quel que soit le déclarant
    #    (BRADYCARDIE déclare TACHYCARDIE et réciproquement — mais une seule
    #    paire canonique dans le registry)
    r = check_response_coherence({"TACHYCARDIE", "BRADYCARDIE"}, {})
    pairs = [tuple(sorted((c.concept_a, c.concept_b))) for c in r]
    check("7. symétrie + dédup (1 seule contradiction pour la paire)",
          pairs.count(("BRADYCARDIE", "TACHYCARDIE")) == 1, f"got={pairs}")

    # 8. Pas de conflit sans relation
    r = check_response_coherence({"FIBRILLATION_ATRIALE", "QRS_FINS"}, {})
    check("8. paire sans relation → aucune contradiction", len(r) == 0, f"got={r}")

    # 9. golden_status
    g = golden([("FIBRILLATION_ATRIALE", "present"), ("RYTHME_SINUSAL", "absent")])
    check("9. golden_status", golden_status("FIBRILLATION_ATRIALE", g) == "ACCEPTED"
          and golden_status("RYTHME_SINUSAL", g) == "FORBIDDEN"
          and golden_status("BAV_COMPLET", g) == "UNKNOWN")

    # 10. chal_02 : FA + rythme régulier, golden UNKNOWN sur les deux →
    #     DEFAULT warning ? Vérifier qu'une relation existe (FA n'a pas de
    #     conflicts déclaré vers RYTHME_REGULIER — mais IRREGULIER oui).
    #     La réponse chal_02 extrait FIBRILLATION_ATRIALE + RYTHME_REGULIER :
    #     pas de paire déclarée → PAS de contradiction (attendu : l'ontologie
    #     ne déclare pas FA↔régulier ; le conflit passe par IRREGULIER).
    r = check_response_coherence({"FIBRILLATION_ATRIALE", "RYTHME_REGULIER"}, {})
    print(f"  (info) chal_02 FA+RYTHME_REGULIER : {len(r)} contradiction(s) "
          f"— relation FA<->REGULIER non déclarée dans l'ontologie à ce stade")

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} échec(s) : {FAILURES}")
        sys.exit(1)
    print("✅ Tous les tests coherence passent.")


if __name__ == "__main__":
    main()
