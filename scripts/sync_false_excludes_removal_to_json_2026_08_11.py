#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_false_excludes_removal_to_json_2026_08_11.py — P4.3a-bis étape 1 (suite).

Reproduit dans les 3 copies runtime de ontology_v2.json les 12 retraits de
relations `excludes` déjà appliqués au .owl source par
remove_false_excludes_from_owl_2026_08_11.py (arbitrage expert,
docs/P4.3a_audit_excludes_2026_08_11.md section SUPPRIMER).

NB : le rebuild complet (rebuild_ontology_from_owl.py) est impossible ici —
onto_overlay.json n'existe qu'en version archivée du 2026-07-06, antérieure
à toutes les corrections du 08-09. On suit donc le workflow établi le 08-09 :
patch ciblé synchronisé OWL <-> JSON.

Usage :
    python scripts/sync_false_excludes_removal_to_json_2026_08_11.py --dry-run
    python scripts/sync_false_excludes_removal_to_json_2026_08_11.py
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

PAIRS = [
    ("PRESENCE_DE_QRS", "ABSENCE_DE_QRS"),
    ("SEQUELLE_DE_NECROSE", "ABSENCE_D_ONDE_Q_PATHOLOGIQUE"),
    ("BLOC_DE_BRANCHE", "BLOC_FASCICULAIRE"),
    ("QRS_NORMAL", "FAISCEAU_ACCESSOIRE_A_CONDUCTION_ANTEROGRADE"),
    ("QRS_NORMAL", "PREEXCITATION_VENTRICULAIRE_PAR_FIBRE_DE_MAHAIM"),
    ("ABSENCE_D_ONDE_Q_PATHOLOGIQUE", "MORPHOLOGIE_ANORMALE_DU_QRS"),
    ("VOLTAGE_DU_QRS_NORMAL", "TROUBLE_DE_CONDUCTION_INTRAVENTRICULAIRE"),
    ("FLUTTER_ATRIAL_ATYPIQUE", "TOIT_D_USINE"),
    ("TACHYCARDIE_VENTRICULAIRE_POLYMORPHE", "ORGANISEE"),
    ("ARYTHMIE_SINUSALE", "ONDE_P_ANORMALE"),
    ("TROUBLE_DE_REPOLARISATION", "ONDE_U_NORMALE"),
    ("TROUBLE_DE_REPOLARISATION", "ST_NORMAL"),
]


def patch(path: Path, dry: bool) -> None:
    data = json.load(open(path, encoding="utf-8"))
    concepts = data.get("concepts", data)
    removed = 0
    for src, dst in PAIRS:
        c = concepts.get(src)
        if not c:
            print(f"  [!] {src} absent de {path.name}")
            continue
        ex = c.get("excludes") or []
        if dst in ex:
            ex.remove(dst)
            c["excludes"] = ex
            removed += 1
        else:
            print(f"  [!] {src} -> {dst} déjà absent ({path})")
    total = sum(len(c.get("excludes") or []) for c in concepts.values())
    print(f"  {path} : {removed}/12 retirés, excludes restants = {total}")
    if dry:
        return
    if removed:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, f"{path}.bak_{ts}")
        json.dump(data, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for p in COPIES:
        patch(p, args.dry_run)
    print("[DRY-RUN] rien écrit." if args.dry_run else "✅ 3 copies patchées (backups créés).")


if __name__ == "__main__":
    main()
