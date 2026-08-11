# -*- coding: utf-8 -*-
"""_test_safety_score_2026_08_11.py — P4.1 : tests unitaires safety_score.

Usage : python scripts/_test_safety_score_2026_08_11.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rag_pipeline"))

from safety_score import (SafetyEvent, compute_safety_score, combine_scores,
                          STATUS_ACTIVE, STATUS_OVERRIDDEN, STATUS_WAIVED,
                          STATUS_DATA_INCONSISTENCY)

OK, KO = "\u2705", "\u274c"
fails = []


def check(label, cond, detail=""):
    print(f"{OK if cond else KO} {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(label)


def ev(kind="golden_exclusion_A", concepts=("X",), status=STATUS_ACTIVE,
       penalty=75, source="golden_exclusion", severity="error"):
    return SafetyEvent(kind=kind, severity=severity, concept_ids=concepts,
                       source=source, status=status, penalty=penalty)


# 1. Aucun événement → 100
check("T1 vide → 100", compute_safety_score([]) == 100)

# 2. Rang A actif → 25
check("T2 rang A → 25", compute_safety_score([ev()]) == 25)

# 3. Rang B actif → 70
check("T3 rang B → 70", compute_safety_score([ev(kind="golden_exclusion_B", penalty=30)]) == 70)

# 4. DÉDUPLICATION : même erreur détectée 2 fois (exclusion + HARD, mêmes
#    concepts) → pénalité MAX une seule fois, pas -150.
events = [ev(concepts=("FA", "RS"), penalty=75),
          ev(kind="hard_contradiction", source="symbolic",
             concepts=("RS", "FA"), penalty=75)]  # ordre inversé → même frozenset
check("T4 dédup même paire (ordre inversé) → 25", compute_safety_score(events) == 25,
      f"got {compute_safety_score(events)}")

# 5. Deux erreurs DISTINCTES → pénalités cumulées (75+30 → 0 min 0).
events = [ev(concepts=("A",), penalty=75), ev(concepts=("B",), penalty=30)]
check("T5 deux erreurs distinctes → max(0,100-105)=0", compute_safety_score(events) == 0)

# 6. overridden / waived / data_inconsistency → aucun poids.
events = [ev(status=STATUS_OVERRIDDEN), ev(status=STATUS_WAIVED),
          ev(status=STATUS_DATA_INCONSISTENCY)]
check("T6 non-actifs → 100", compute_safety_score(events) == 100)

# 7. DEFAULT actif pénalité 0 → 100 (observable sans effet).
events = [ev(kind="default_conflict", severity="warning", penalty=0,
             source="symbolic")]
check("T7 DEFAULT actif (penalty 0) → 100", compute_safety_score(events) == 100)

# 8. Dédup garde la pénalité la plus sévère (30 vs 75 même paire → 75).
events = [ev(concepts=("A", "B"), penalty=30), ev(concepts=("A", "B"), penalty=75)]
check("T8 dédup garde max → 25", compute_safety_score(events) == 25)

# 9. Combinaison produit.
check("T9 combine(100,100)=100", combine_scores(100, 100) == 100)
check("T10 combine(100,25)=25 (≡ ancien cap A)", combine_scores(100, 25) == 25)
check("T11 combine(50,25)=13 (gradué, plus sévère que cap)", combine_scores(50, 25) == 13)
check("T12 combine(80,70)=56", combine_scores(80, 70) == 56)
check("T13 combine(0,100)=0", combine_scores(0, 100) == 0)

# 14. Sérialisation (traçabilité API).
d = ev(concepts=("A", "B")).to_dict()
check("T14 to_dict concept_ids liste JSON-safe", d["concept_ids"] == ["A", "B"]
      and d["arbitration"] is None)

print("=" * 50)
if fails:
    print(f"{KO} {len(fails)} échec(s) : {fails}")
    sys.exit(1)
print(f"{OK} Tous les tests safety_score passent.")
