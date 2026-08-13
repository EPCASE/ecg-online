# -*- coding: utf-8 -*-
"""
p42_audit_zeros_2026_08_12.py — P4.2 : audit des zéros aberrants
(machine=0 / expert>=80, diag principal vu par l'expert).

Pour chaque copie : golden attendu (validants) vs concepts extraits par le
pipeline, pour comprendre pourquoi le match a échoué.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = r"c:\Users\Administrateur\bmad\ECG lecture"
sys.path.insert(0, os.path.join(ROOT, "ecg-online"))
sys.path.insert(0, os.path.join(ROOT, "rag_pipeline"))
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "ecg-online", ".env"))

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

from app import golden_config


def main() -> int:
    with open(os.path.join(DATA, "p42_calibration_report.json"), encoding="utf-8") as f:
        pairs = json.load(f)["pairs"]
    with open(os.path.join(DATA, "p42_corpus_rescored.json"), encoding="utf-8") as f:
        corpus = {it["key"]: it for it in json.load(f)["items"]}
    with open(os.path.join(DATA, "p42_annotation_key.json"), encoding="utf-8") as f:
        key = {e["sample_id"]: e for e in json.load(f)["entries"]}

    aberrants = [p for p in pairs
                 if p["machine"] <= 10 and p["expert"] >= 80 and p["q_diag"] == "1"]
    print(f"=== {len(aberrants)} zeros aberrants (machine<=10, expert>=80, diag vu) ===\n")

    from collections import Counter
    cas_count = Counter(p["cas"] for p in aberrants)
    print("Par cas :", dict(sorted(cas_count.items())), "\n")

    for p in sorted(aberrants, key=lambda x: (x["cas"], x["sample_id"])):
        it = corpus[key[p["sample_id"]]["key"]]
        g = golden_config.golden_for_scorer(p["cas"])
        validants = [(v["concept_id"], v["concept_name"], v.get("statut", "present"))
                     for v in (g.get("validants") or [])]
        concepts = it.get("concepts") or []
        print(f"--- {p['sample_id']} cas {p['cas']} machine={p['machine']:.0f} expert={p['expert']:.0f}")
        print(f"    TEXTE     : {it['texte'][:150]!r}")
        print(f"    VALIDANTS : {validants}")
        print(f"    EXTRAITS  : {[(c.get('concept_id'), c.get('rang'), c.get('statut'), c.get('match_type')) for c in concepts]}")
        print(f"    correspondance={it.get('correspondance')} type_erreur={it.get('type_erreur')}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
