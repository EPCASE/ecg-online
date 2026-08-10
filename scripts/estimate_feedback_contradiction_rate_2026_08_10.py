# -*- coding: utf-8 -*-
"""
estimate_feedback_contradiction_rate_2026_08_10.py — Estime, sur un
échantillon plus large que le test ponctuel du cas 41, le taux réel
d'auto-contradiction en PREMIÈRE génération du texte de feedback
pédagogique (avant intervention du garde-fou LLM post-hoc), pour les
concepts validants crédités via match_type != "exact" (qualifier/requires/
support), qui sont la source du risque identifié le 2026-08-10.

Approche :
- Parcourt les items du challenge set (`data/challenge_set_v1.json`) qui
  ciblent des concepts crédités indirectement.
- Pour chaque item, exécute N générations indépendantes du feedback.
- Utilise un détecteur DÉTERMINISTE (regex) de contradiction explicite
  dans le texte final ET intercepte le log du juge LLM pour savoir si une
  correction a été déclenchée en cours de route (proxy du taux avant
  garde-fou).

Ce script ne modifie aucune donnée — c'est un outil de mesure, à archiver
comme preuve pour la décision P4 sur la nécessité d'un garde-fou
déterministe.

Usage :
    python scripts/estimate_feedback_contradiction_rate_2026_08_10.py --n 3
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys

ROOT = r"c:\Users\Administrateur\bmad\ECG lecture"
sys.path.insert(0, os.path.join(ROOT, "ecg-online"))
sys.path.insert(0, os.path.join(ROOT, "rag_pipeline"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "ecg-online", ".env"))

from app import golden_config
from candidate_report import generate_candidate_report
import pedagogical_feedback as pf

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
CHALLENGE_PATH = os.path.join(DATA_DIR, "challenge_set_v1.json")

# Items dont la réponse est censée déclencher au moins un match_type
# indirect (qualifier/requires/support) sur un concept validant — ce sont
# les candidats les plus à risque pour l'auto-contradiction du texte.
TARGET_ITEM_IDS = [
    "chal_01_redundant_alternative_credit",
    "chal_07_diagnostic_juste_sans_justification",
    "chal_09_concept_enfant_plus_specifique",
]

# Détection déterministe (regex) d'une contradiction explicite dans le
# texte FINAL livré (après garde-fou éventuel) : co-occurrence de
# "mentionné/identifié ... explicitement" et "sans le nommer/identifier
# explicitement" dans un texte court suggère une contradiction résiduelle.
_POS_RE = re.compile(r"(mentionn|identifi|not(?:é|e))[a-zé]*\s+(explicitement|clairement)", re.IGNORECASE)
_NEG_RE = re.compile(r"sans\s+(?:le|la|l['’])\s*(?:nommer|identifier|mentionner)\s+explicitement", re.IGNORECASE)


class _JudgeCallCounter(logging.Handler):
    """Compte les warnings 'Affirmation(s) clinique(s) non fondée(s)' émis
    par pedagogical_feedback pendant une génération, pour savoir si le
    garde-fou a dû intervenir."""

    def __init__(self):
        super().__init__()
        self.triggered = False

    def emit(self, record):
        msg = record.getMessage()
        if "Affirmation(s) clinique(s) non fondée(s)" in msg:
            self.triggered = True


def detect_residual_contradiction(text: str) -> bool:
    return bool(_POS_RE.search(text) and _NEG_RE.search(text))


def run_one(item: dict) -> dict:
    case_id = item["case_id"]
    texte = item["texte_etudiant"]
    contract = golden_config.golden_for_scorer(case_id)
    validants = contract.get("validants", [])
    descripteurs = contract.get("descripteurs", [])
    all_pts = validants + descripteurs

    report = generate_candidate_report(
        texte,
        golden_names=[p["concept_name"] for p in all_pts],
        golden_ids=[p["concept_id"] for p in all_pts],
        golden_roles=["validant"] * len(validants) + ["descripteur"] * len(descripteurs),
        diagnostic_principal=contract.get("diagnostic_principal", ""),
        with_feedback=False,
    )

    handler = _JudgeCallCounter()
    logger = logging.getLogger("pedagogical_feedback")
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    try:
        fb = pf.generate_pedagogical_feedback(report)
    finally:
        logger.removeHandler(handler)

    return {
        "match_types": [vd.match_type for vd in report.validant_details],
        "judge_triggered": handler.triggered,
        "residual_contradiction_in_final_text": detect_residual_contradiction(fb.texte),
        "texte": fb.texte,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=3, help="Nombre de générations par item")
    args = parser.parse_args()

    with open(CHALLENGE_PATH, encoding="utf-8") as f:
        challenge = json.load(f)
    items = {it["id"]: it for it in challenge["items"]}

    total_runs = 0
    total_judge_triggered = 0
    total_residual = 0
    per_item_summary = []

    for item_id in TARGET_ITEM_IDS:
        item = items[item_id]
        judge_count = 0
        residual_count = 0
        for i in range(args.n):
            print(f"\n--- {item_id} run {i+1}/{args.n} ---")
            res = run_one(item)
            total_runs += 1
            print("match_types:", res["match_types"])
            print("judge_triggered:", res["judge_triggered"])
            print("residual_contradiction_in_final_text:", res["residual_contradiction_in_final_text"])
            if res["judge_triggered"]:
                judge_count += 1
                total_judge_triggered += 1
            if res["residual_contradiction_in_final_text"]:
                residual_count += 1
                total_residual += 1
                print("⚠️  CONTRADICTION RÉSIDUELLE DANS LE TEXTE FINAL :")
                print(res["texte"])
        per_item_summary.append((item_id, judge_count, residual_count, args.n))

    print(f"\n{'='*80}\nRÉSUMÉ ({total_runs} générations au total sur {len(TARGET_ITEM_IDS)} items)")
    for item_id, judge_count, residual_count, n in per_item_summary:
        print(f"  {item_id}: garde-fou déclenché {judge_count}/{n} — contradiction résiduelle finale {residual_count}/{n}")
    print(f"\nTaux global de déclenchement du garde-fou : {total_judge_triggered}/{total_runs} "
          f"({100*total_judge_triggered/total_runs:.0f}%)")
    print(f"Taux global de contradiction résiduelle dans le texte FINAL livré à l'étudiant : "
          f"{total_residual}/{total_runs} ({100*total_residual/total_runs:.0f}%)")


if __name__ == "__main__":
    main()
