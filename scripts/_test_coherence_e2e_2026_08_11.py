# -*- coding: utf-8 -*-
"""_test_coherence_e2e_2026_08_11.py — P4.3b étape E.

Tests d'intégration bout-en-bout de la cohérence intra-réponse via la voie
COMPLÈTE `neuro_grader.grade_neuro` (extraction NER + scoring V3 + adaptateur
Correction). Vérifie les 3 comportements du design :

  E1. chal_02 (cas 49, FA + « rythme parfaitement régulier ») :
      conflict DEFAULT détecté → avertissement « À vérifier » dans le
      commentaire, note INCHANGÉE (pas de cap DEFAULT en V1).
  E2. HARD synthétique (cas 27, hyperkaliémie) : réponse affirmant à la fois
      hyperkaliémie ET hypokaliémie → cap 25, correspondance incorrecte,
      élément erroné « Contradiction ».
  E3. Contrôle négatif : réponse normale sans contradiction → aucun
      avertissement de cohérence, aucun cap.

Usage : python scripts/_test_coherence_e2e_2026_08_11.py
"""
from __future__ import annotations

import os
import sys

ROOT = r"c:\Users\Administrateur\bmad\ECG lecture"
sys.path.insert(0, os.path.join(ROOT, "ecg-online"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "ecg-online", ".env"))

from app import neuro_grader

OK, KO = "\u2705", "\u274c"
failures = []


def check(label: str, cond: bool, detail: str = ""):
    print(f"{OK if cond else KO} {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        failures.append(label)


def main():
    # ── E1 : chal_02 — DEFAULT actif → warning sans pénalité ────────────
    print("\n=== E1. chal_02 (cas 49) : FA + rythme régulier (DEFAULT) ===")
    txt = ("Fibrillation atriale avec rythme parfaitement régulier à QRS fins, "
           "fréquence 75/min normale.")
    c = neuro_grader.grade_neuro(49, txt)
    assert c is not None, "grade_neuro(49) a renvoyé None"
    d = c.to_dict()
    has_warning = "À vérifier" in (d.get("commentaire") or "")
    check("E1a warning cohérence dans le commentaire", has_warning,
          "(FA ↔ RYTHME_REGULIER)")
    check("E1b note NON plafonnée par le warning DEFAULT", d["score"] > 25,
          f"score={d['score']}")
    no_coh_err = not any("Contradiction" in (e.get("label") or "")
                         for e in d.get("elements_errones", []))
    check("E1c pas d'élément erroné 'Contradiction' (DEFAULT ≠ HARD)", no_coh_err)

    # ── E2 : HARD synthétique — hyperK + hypoK sur le cas 27 ────────────
    print("\n=== E2. cas 27 : hyperkaliémie ET hypokaliémie (HARD) ===")
    txt2 = ("Hyperkaliémie sévère avec ondes T amples et pointues, mais aussi "
            "hypokaliémie avec ondes U visibles.")
    c2 = neuro_grader.grade_neuro(27, txt2)
    assert c2 is not None, "grade_neuro(27) a renvoyé None"
    d2 = c2.to_dict()
    coh_err = [e for e in d2.get("elements_errones", [])
               if "Contradiction" in (e.get("label") or "")]
    check("E2a élément erroné 'Contradiction' présent", bool(coh_err),
          coh_err[0]["label"][:80] + "…" if coh_err else "")
    check("E2b score plafonné à 25 (cap HARD)", d2["score"] <= 25,
          f"score={d2['score']}")
    check("E2c correspondance = incorrecte", d2.get("correspondance") == "incorrecte",
          d2.get("correspondance", ""))

    # ── E3 : contrôle négatif — cas 49 réponse cohérente ────────────────
    print("\n=== E3. cas 49 : réponse cohérente (contrôle négatif) ===")
    txt3 = ("Fibrillation atriale : rythme irrégulièrement irrégulier, "
            "absence d'ondes P, trémulation de la ligne de base.")
    c3 = neuro_grader.grade_neuro(49, txt3)
    assert c3 is not None, "grade_neuro(49) a renvoyé None"
    d3 = c3.to_dict()
    check("E3a aucun warning cohérence", "À vérifier" not in (d3.get("commentaire") or ""))
    no_coh_err3 = not any("Contradiction" in (e.get("label") or "")
                          for e in d3.get("elements_errones", []))
    check("E3b aucun élément erroné 'Contradiction'", no_coh_err3)
    check("E3c score non plafonné", d3["score"] > 25, f"score={d3['score']}")

    print("\n" + "=" * 60)
    if failures:
        print(f"{KO} {len(failures)} échec(s) : {failures}")
        sys.exit(1)
    print(f"{OK} Tous les tests E2E cohérence passent.")


if __name__ == "__main__":
    main()
