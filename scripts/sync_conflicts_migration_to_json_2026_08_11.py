#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_conflicts_migration_to_json_2026_08_11.py — P4.3b étape B (volet JSON).

Reproduit dans les 3 copies runtime de ontology_v2.json la migration déjà
appliquée à l'OWL (migrate_conflicts_owl_2026_08_11.py) :
  1. Déplace 24 relations DEFAULT de `excludes` vers `conflicts_by_default`
     (nouveau champ) — inclut les 2 paires TV soutenue/non-soutenue absentes
     de l'OWL (concepts de la couche JSON) ;
  2. Ajoute les 3 réciproques HARD manquantes dans `excludes`.

Usage :
    python scripts/sync_conflicts_migration_to_json_2026_08_11.py --dry-run
    python scripts/sync_conflicts_migration_to_json_2026_08_11.py
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

COPIES = [
    Path(r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json"),
    Path(r"C:\Users\Administrateur\bmad\ECG lecture\ecg-online\rag_pipeline\data\ontology_v2.json"),
    Path(r"C:\Users\Administrateur\bmad\ECG lecture\rag_pipeline\data\ontology_v2.json"),
]

DEFAULT_PAIRS = [
    ("BRADYCARDIE", "TACHYCARDIE"),
    ("TACHYCARDIE", "BRADYCARDIE"),
    ("IRREGULIER", "RYTHME_REGULIER"),
    ("BLOC_DE_BRANCHE", "QRS_FINS"),
    ("BLOC_DE_BRANCHE_DROIT", "BLOC_DE_BRANCHE_GAUCHE"),
    ("BLOC_DE_BRANCHE_GAUCHE", "BLOC_DE_BRANCHE_DROIT"),
    ("BLOC_FASCICULAIRE", "AXE_NORMAL_DU_QRS"),
    ("BLOC_FASCICULAIRE_ANTERIEUR_GAUCHE", "BLOC_FASCICULAIRE_POSTERIEUR_GAUCHE"),
    ("BLOC_FASCICULAIRE_POSTERIEUR_GAUCHE", "BLOC_FASCICULAIRE_ANTERIEUR_GAUCHE"),
    ("BAV_COMPLET", "PR_NORMAL"),
    ("PR_ALLONGE", "PR_NORMAL"),
    ("QRS_NORMAL", "ONDE_EPSILON"),
    ("QRS_NORMAL", "TROUBLE_DE_CONDUCTION_INTRAVENTRICULAIRE"),
    ("TROUBLE_DE_CONDUCTION_INTRAVENTRICULAIRE", "QRS_NORMAL"),
    ("VOLTAGE_DU_QRS_NORMAL", "HYPERTROPHIE_VENTRICULAIRE_GAUCHE"),
    ("DESORGANISEE", "ORGANISEE"),
    ("TACHYCARDIE_ATRIALE", "DESORGANISEE"),
    ("TACHYCARDIE_ATRIALE_FOCALE", "DESORGANISEE"),
    ("FLUTTER_ATRIAL_ATYPIQUE", "FIBRILLATION_ATRIALE"),
    ("FLUTTER_ATRIAL_ATYPIQUE", "FLUTTER_DROIT_TYPIQUE"),
    ("TACHYCARDIE_VENTRICULAIRE_BIDIRECTIONNELLE", "MONOMORPHE"),
    ("TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE", "TACHYCARDIE_VENTRICULAIRE_SOUTENUE"),
    ("TACHYCARDIE_VENTRICULAIRE_SOUTENUE", "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE"),
    ("ABSENCE_D_ONDE_P", "ONDE_P_NORMALE"),
]

HARD_RECIPROCALS = [
    ("HYPONATREMIE", "HYPERNATREMIE"),
    ("MICROVOLTAGE", "VOLTAGE_DU_QRS_NORMAL"),
    ("ONDE_DELTA", "SYNDROME_DE_LOWN_GANONG_ET_LEVINE"),
]


def patch(path: Path, dry: bool) -> None:
    data = json.load(open(path, encoding="utf-8"))
    concepts = data.get("concepts", data)
    moved, added = 0, 0
    for src, dst in DEFAULT_PAIRS:
        c = concepts.get(src)
        if not c:
            print(f"  [!] {src} absent"); continue
        ex = c.get("excludes") or []
        if dst in ex:
            ex.remove(dst)
            c["excludes"] = ex
            cbd = c.setdefault("conflicts_by_default", [])
            if dst not in cbd:
                cbd.append(dst)
            moved += 1
        else:
            print(f"  [!] {src}->{dst} pas dans excludes")
    for src, dst in HARD_RECIPROCALS:
        c = concepts.get(src)
        if not c:
            print(f"  [!] {src} absent"); continue
        ex = c.setdefault("excludes", [])
        if dst not in ex:
            ex.append(dst)
            added += 1
    n_ex = sum(len(c.get("excludes") or []) for c in concepts.values())
    n_cbd = sum(len(c.get("conflicts_by_default") or []) for c in concepts.values())
    print(f"  {path.name} ({path.parent.parent.parent.name}): moved={moved}/24 added={added}/3 | excludes={n_ex} conflicts_by_default={n_cbd}")
    if dry or (moved == 0 and added == 0):
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, f"{path}.bak_{ts}")
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for p in COPIES:
        patch(p, args.dry_run)
    print("[DRY-RUN] rien écrit." if args.dry_run else "✅ 3 copies patchées.")


if __name__ == "__main__":
    main()
