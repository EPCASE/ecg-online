# -*- coding: utf-8 -*-
"""
run_challenge_set_2026_08_10.py — Exécute le challenge set P3.3
(`data/challenge_set_v1.json`) contre le pipeline de scoring réel
(`golden_config.golden_for_scorer` + `candidate_report.generate_candidate_report`)
et produit un rapport documentant, pour chaque item adversarial :
  - le score obtenu,
  - les concepts extraits (avec statut/method),
  - si le "risque_cible" documenté dans l'item semble se matérialiser ou non.

Ce script NE CORRIGE RIEN — c'est un outil de diagnostic/non-régression
(P3.3 de la roadmap), à relancer à chaque évolution du moteur de scoring
pour repérer si de nouveaux comportements adversariaux apparaissent ou si
d'anciens régressent.

Usage :
    python scripts/run_challenge_set_2026_08_10.py
    python scripts/run_challenge_set_2026_08_10.py --id chal_01_redundant_alternative_credit
    python scripts/run_challenge_set_2026_08_10.py --json rapport_challenge.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = r"c:\Users\Administrateur\bmad\ECG lecture"
sys.path.insert(0, os.path.join(ROOT, "ecg-online"))
sys.path.insert(0, os.path.join(ROOT, "rag_pipeline"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "ecg-online", ".env"))

from app import golden_config
from candidate_report import generate_candidate_report

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
CHALLENGE_PATH = os.path.join(DATA_DIR, "challenge_set_v1.json")


def run_item(item: dict) -> dict:
    case_id = item["case_id"]
    texte = item["texte_etudiant"]

    contract = golden_config.golden_for_scorer(case_id)
    validants = contract.get("validants", [])
    descripteurs = contract.get("descripteurs", [])
    all_pts = validants + descripteurs
    golden_ids = [p["concept_id"] for p in all_pts]
    golden_names = [p["concept_name"] for p in all_pts]
    golden_roles = ["validant"] * len(validants) + ["descripteur"] * len(descripteurs)

    report = generate_candidate_report(
        texte,
        golden_names=golden_names,
        golden_ids=golden_ids,
        golden_roles=golden_roles,
        diagnostic_principal=contract.get("diagnostic_principal", ""),
        with_feedback=False,
    )

    concepts = [
        {
            "terme_brut": c.terme_brut,
            "ontology_id": c.ontology_id,
            "statut": c.statut,
            "method": c.method,
        }
        for c in report.concepts_extraits
    ]

    return {
        "id": item["id"],
        "pattern": item["pattern"],
        "case_id": case_id,
        "texte_etudiant": texte,
        "risque_cible": item["risque_cible"],
        "verification_attendue": item.get("verification_attendue", []),
        "score_final_pct": report.score_final_pct,
        "concepts_extraits": concepts,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="N'exécuter qu'un seul item par son id")
    parser.add_argument("--json", help="Écrire le rapport complet en JSON dans ce fichier")
    args = parser.parse_args()

    with open(CHALLENGE_PATH, encoding="utf-8") as f:
        challenge = json.load(f)

    items = challenge["items"]
    if args.id:
        items = [it for it in items if it["id"] == args.id]
        if not items:
            print(f"⚠️  Aucun item avec id={args.id!r} trouvé.")
            return

    results = []
    for item in items:
        print(f"\n{'='*80}\n{item['id']}  (cas {item['case_id']}, pattern: {item['pattern']})")
        print(f"Texte: {item['texte_etudiant']!r}")
        try:
            res = run_item(item)
        except Exception as exc:  # noqa: BLE001
            print(f"❌ ERREUR lors de l'exécution: {exc}")
            results.append({"id": item["id"], "error": str(exc)})
            continue
        print(f"Score: {res['score_final_pct']}%")
        for c in res["concepts_extraits"]:
            print(f"   {c['terme_brut']!r} -> {c['ontology_id']} [{c['statut']}] ({c['method']})")
        print(f"Risque documenté: {res['risque_cible']}")
        results.append(res)

    print(f"\n{'='*80}\nTotal: {len(results)} item(s) exécuté(s).")

    if args.json:
        out_path = args.json
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"results": results}, f, ensure_ascii=False, indent=2)
        print(f"Rapport JSON écrit dans {out_path}")


if __name__ == "__main__":
    main()
