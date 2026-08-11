#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""add_fa_regulier_conflict_2026_08_11.py — P4.3b.

Ajoute la relation `FIBRILLATION_ATRIALE conflit_par_defaut RYTHME_REGULIER`
(validée par l'expert : exemple canonique de conflit par défaut ; l'exception
FA + BAV complet avec échappement régulier est gérée par l'override golden).

OWL d'abord (restriction avec la propriété conflitParDefaut_edu_ecg créée par
migrate_conflicts_owl_2026_08_11.py), puis sync des 3 copies JSON.

Usage :
    python scripts/add_fa_regulier_conflict_2026_08_11.py --dry-run
    python scripts/add_fa_regulier_conflict_2026_08_11.py
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Administrateur\bmad\ECG lecture")
OWL_PATH = ROOT / "BrYOzRZIu7jQTwmfcGsi35.owl"
IRI_PATH = ROOT / "data" / "id_to_iri.json"
PREFIX = "http://webprotege.stanford.edu/"
CONFLICT_PROP = PREFIX + "conflitParDefaut_edu_ecg"

SRC, DST = "FIBRILLATION_ATRIALE", "RYTHME_REGULIER"

COPIES = [
    ROOT / "data" / "ontology_v2.json",
    ROOT / "ecg-online" / "rag_pipeline" / "data" / "ontology_v2.json",
    ROOT / "rag_pipeline" / "data" / "ontology_v2.json",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ---- OWL ----
    iri_map = json.load(open(IRI_PATH, encoding="utf-8"))
    iri_map = {k: (v if str(v).startswith("http") else PREFIX + str(v))
               for k, v in iri_map.items()}
    iri_src, iri_dst = iri_map[SRC], iri_map[DST]
    owl = OWL_PATH.read_text(encoding="utf-8")
    m = re.search(r'(<owl:Class rdf:about="' + re.escape(iri_src) + r'">)(.*?)(</owl:Class>)',
                  owl, re.S)
    if not m:
        print(f"⛔ classe {SRC} introuvable"); return
    if CONFLICT_PROP in m.group(2) and iri_dst in m.group(2):
        print("= OWL : relation déjà présente")
    else:
        block = (f"\n        <rdfs:subClassOf>\n"
                 f"            <owl:Restriction>\n"
                 f"                <owl:onProperty rdf:resource=\"{CONFLICT_PROP}\"/>\n"
                 f"                <owl:someValuesFrom rdf:resource=\"{iri_dst}\"/>\n"
                 f"            </owl:Restriction>\n"
                 f"        </rdfs:subClassOf>\n")
        new = m.group(1) + block + m.group(2).lstrip("\n") + m.group(3)
        owl_new = owl.replace(m.group(0), new, 1)
        print(f"+ OWL : {SRC} -conflit_par_defaut-> {DST}")
        if not args.dry_run:
            shutil.copy2(OWL_PATH, OWL_PATH.with_suffix(f".owl.bak_{ts}"))
            OWL_PATH.write_text(owl_new, encoding="utf-8")

    # ---- JSON (3 copies) ----
    for p in COPIES:
        data = json.load(open(p, encoding="utf-8"))
        c = data["concepts"][SRC]
        cbd = c.setdefault("conflicts_by_default", [])
        if DST in cbd:
            print(f"= {p.name} ({p.parent.parent.parent.name}) : déjà présent")
            continue
        cbd.append(DST)
        print(f"+ JSON {p.parent.parent.parent.name} : {SRC}.conflicts_by_default += {DST}")
        if not args.dry_run:
            shutil.copy2(p, f"{p}.bak_{ts}")
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("[DRY-RUN] rien écrit." if args.dry_run else "✅ OWL + 3 JSON mis à jour.")


if __name__ == "__main__":
    main()
