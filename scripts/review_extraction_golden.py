#!/usr/bin/env python
"""
review_extraction_golden.py — Contrôle qualité GPT-5.6 de l'annotation finale.
================================================================================
Cf. GOLDEN_EXTRACTION.md §5ter.

Relit chaque item déjà annoté par l'expert humain (`annotation_expert` /
`annotation_expert_2`) et demande à GPT-5.6 de repérer des erreurs/oublis/
doutes potentiels — PAS une nouvelle extraction indépendante (ça c'est le
rôle de `gpt_annotator.annotate`, utilisé en amont pour le pré-remplissage),
mais une relecture critique de la décision humaine déjà prise.

⚠️ Ceci est un outil d'AIDE à la relecture, pas un arbitre : les alertes sont
à trier par l'expert, pas appliquées automatiquement.

Usage :
    python scripts/review_extraction_golden.py
    python scripts/review_extraction_golden.py --item 12-01
    python scripts/review_extraction_golden.py --only-flagged   # n'affiche que les items avec alertes
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path
from typing import Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from app import extraction_golden, gpt_annotator  # noqa: E402


def review_all(item_filter: Optional[str] = None, only_flagged: bool = False) -> dict:
    data = extraction_golden.load()
    items = data.get("items", {})
    report = {}
    n_reviewed = 0
    n_with_alerts = 0

    for item_id, item in sorted(items.items()):
        if item_filter and item_id != item_filter:
            continue

        slots = [("annotation_expert", item.get("annotation_expert"))]
        if item.get("double_annotation"):
            slots.append(("annotation_expert_2", item.get("annotation_expert_2")))

        item_reports = {}
        for slot_name, ann in slots:
            if not ann or not ann.get("concepts"):
                continue
            n_reviewed += 1
            result = gpt_annotator.review_annotation(
                item.get("reponse_texte", ""), ann["concepts"])
            if result is None:
                print(f"⚠️  {item_id} [{slot_name}] : relecture indisponible.", file=sys.stderr)
                continue
            alertes = result.get("alertes", [])
            if alertes:
                n_with_alerts += 1
            item_reports[slot_name] = result

            if not only_flagged or alertes:
                print(f"\n{'─'*70}\n📋 {item_id} [{slot_name}] (cas {item.get('cas')})")
                print(f"   Texte : {item.get('reponse_texte', '')[:150]}…")
                print(f"   Synthèse : {result.get('synthese', '')}")
                if alertes:
                    for a in alertes:
                        icon = {"omission": "➕", "douteux": "❓",
                                "statut_a_verifier": "🔄", "ok_mais_limite": "🟡"}.get(
                            a["type_probleme"], "•")
                        print(f"   {icon} [{a['type_probleme']}] {a['concept']} — {a['commentaire']}")
                else:
                    print("   ✅ Aucune alerte.")

        if item_reports:
            report[item_id] = item_reports

    print(f"\n{'='*70}")
    print(f"✅ {n_reviewed} annotation(s) relue(s), {n_with_alerts} avec au moins une alerte.")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", type=str, default=None,
                     help="Ne relire qu'un item précis (ex. 12-01).")
    ap.add_argument("--only-flagged", action="store_true",
                     help="N'affiche que les items avec au moins une alerte.")
    ap.add_argument("--json", type=Path, default=None,
                     help="Écrit le rapport complet en JSON à ce chemin.")
    args = ap.parse_args()

    if not gpt_annotator.available():
        print("❌ OPENAI_API_KEY non configurée — impossible de lancer la relecture.",
              file=sys.stderr)
        sys.exit(1)

    report = review_all(item_filter=args.item, only_flagged=args.only_flagged)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Rapport complet écrit dans {args.json}")


if __name__ == "__main__":
    main()
