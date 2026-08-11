#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reclass_microvoltage_conflict_2026_08_11.py — P4.3b étape F (suite audit).

Reclasse `MICROVOLTAGE ↔ VOLTAGE_DU_QRS_NORMAL` de excludes (HARD) vers
conflicts_by_default (DEFAULT). Décision expert (option a) suite à F4 du
garde-fou CI : le cas 75 (amylose) est un contre-exemple clinique réel —
microvoltage FRONTAL + voltage précordial conservé coexistent légitimement
(territoires différents → la paire ne satisfait pas le critère HARD « même
objet, même instant, même portée »). L'override golden gère le cas 75
automatiquement.

OWL d'abord (retrait des restrictions `exclut` dans les 2 sens + ajout
`conflitParDefaut_edu_ecg` dans le sens canonique), puis sync des 3 JSON.

Usage :
    python scripts/reclass_microvoltage_conflict_2026_08_11.py --dry-run
    python scripts/reclass_microvoltage_conflict_2026_08_11.py
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
EXCLUT_PROP = PREFIX + "Rgkbf3QYLEo9sJtKMJFyFW"
CONFLICT_PROP = PREFIX + "conflitParDefaut_edu_ecg"

A, B = "MICROVOLTAGE", "VOLTAGE_DU_QRS_NORMAL"

COPIES = [
    ROOT / "data" / "ontology_v2.json",
    ROOT / "ecg-online" / "rag_pipeline" / "data" / "ontology_v2.json",
    ROOT / "rag_pipeline" / "data" / "ontology_v2.json",
]


def _remove_restriction(owl: str, iri_src: str, prop: str, iri_dst: str) -> tuple[str, bool]:
    """Retire, dans la classe iri_src, la restriction (prop, someValuesFrom=iri_dst)."""
    m = re.search(r'<owl:Class rdf:about="' + re.escape(iri_src) + r'">.*?</owl:Class>',
                  owl, re.S)
    if not m:
        return owl, False
    block = m.group(0)
    pat = re.compile(
        r'\s*<rdfs:subClassOf>\s*<owl:Restriction>\s*'
        r'<owl:onProperty rdf:resource="' + re.escape(prop) + r'"/>\s*'
        r'<owl:someValuesFrom rdf:resource="' + re.escape(iri_dst) + r'"/>\s*'
        r'</owl:Restriction>\s*</rdfs:subClassOf>', re.S)
    new_block, n = pat.subn("", block, count=1)
    if n == 0:
        return owl, False
    return owl.replace(block, new_block, 1), True


def _add_restriction(owl: str, iri_src: str, prop: str, iri_dst: str) -> tuple[str, bool]:
    m = re.search(r'(<owl:Class rdf:about="' + re.escape(iri_src) + r'">)(.*?)(</owl:Class>)',
                  owl, re.S)
    if not m:
        return owl, False
    if prop in m.group(2) and iri_dst in m.group(2):
        return owl, False  # déjà présent
    block = (f"\n        <rdfs:subClassOf>\n"
             f"            <owl:Restriction>\n"
             f"                <owl:onProperty rdf:resource=\"{prop}\"/>\n"
             f"                <owl:someValuesFrom rdf:resource=\"{iri_dst}\"/>\n"
             f"            </owl:Restriction>\n"
             f"        </rdfs:subClassOf>\n")
    new = m.group(1) + block + m.group(2).lstrip("\n") + m.group(3)
    return owl.replace(m.group(0), new, 1), True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ---- OWL ----
    iri_map = json.load(open(IRI_PATH, encoding="utf-8"))
    iri_map = {k: (v if str(v).startswith("http") else PREFIX + str(v))
               for k, v in iri_map.items()}
    ia, ib = iri_map[A], iri_map[B]
    owl = OWL_PATH.read_text(encoding="utf-8")
    changed = False
    for src, dst, na, nb in ((ia, ib, A, B), (ib, ia, B, A)):
        owl, ok = _remove_restriction(owl, src, EXCLUT_PROP, dst)
        print(f"{'-' if ok else '='} OWL : {na} -exclut-> {nb}"
              f" {'retiré' if ok else '(absent)'}")
        changed = changed or ok
    owl, ok = _add_restriction(owl, ia, CONFLICT_PROP, ib)
    print(f"{'+' if ok else '='} OWL : {A} -conflit_par_defaut-> {B}"
          f" {'ajouté' if ok else '(déjà présent)'}")
    changed = changed or ok
    if changed and not args.dry_run:
        shutil.copy2(OWL_PATH, OWL_PATH.with_suffix(f".owl.bak_{ts}"))
        OWL_PATH.write_text(owl, encoding="utf-8")

    # ---- JSON (3 copies) ----
    for p in COPIES:
        data = json.load(open(p, encoding="utf-8"))
        concepts = data["concepts"]
        mod = False
        for src, dst in ((A, B), (B, A)):
            exc = concepts.get(src, {}).get("excludes", [])
            if dst in exc:
                exc.remove(dst)
                mod = True
                print(f"- JSON {p.parent.parent.parent.name} : {src}.excludes -= {dst}")
        cbd = concepts[A].setdefault("conflicts_by_default", [])
        if B not in cbd:
            cbd.append(B)
            mod = True
            print(f"+ JSON {p.parent.parent.parent.name} : {A}.conflicts_by_default += {B}")
        if not mod:
            print(f"= {p.name} ({p.parent.parent.parent.name}) : rien à faire")
        elif not args.dry_run:
            shutil.copy2(p, f"{p}.bak_{ts}")
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("[DRY-RUN] rien écrit." if args.dry_run else "✅ OWL + 3 JSON mis à jour.")


if __name__ == "__main__":
    main()
