# -*- coding: utf-8 -*-
"""Hotfix ontologie 2026-10-26 — polarité des concepts négatifs.

Bug : ABSENCE_D_ISCHEMIE a pour parent ISCHEMIQUE. ECG_NORMAL exclut la famille
ischémique → « pas de signe d'ischémie » (résolu en ABSENCE_D_ISCHEMIE, statut
present) est traité comme une ischémie affirmée → ECG_NORMAL excluded → 0/100
(cas 3 et 8 : 9 faux zéros depuis le 13/08, 3 dans l'échantillon aveugle).

Principe : un concept « Absence de X » n'est PAS un sous-type de X. Il le
contredit (`excludes`), mais ne doit pas hériter de sa hiérarchie, sinon toute
exclusion de famille le prend pour un membre positif de la famille.

Patch (idempotent) sur les deux copies de l'ontologie :
  - ABSENCE_D_ISCHEMIE : parents ISCHEMIQUE → DESCRIPTION_ECG ; ISCHEMIQUE.children -= ABSENCE_D_ISCHEMIE
  - ABSENCE_D_ONDE_P   : parents ONDE_P      → DESCRIPTION_ECG ; ONDE_P.children -= ...
  - ABSENCE_DE_QRS     : parents QRS         → DESCRIPTION_ECG ; QRS.children -= ...
  (les excludes existants sont conservés ; aucun ajout.)

Usage : python scripts/hotfix_negative_polarity_2026_10_26.py [--dry-run]
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve()
ECG_ONLINE = HERE.parents[1]
PARENT = ECG_ONLINE.parent
TARGETS = [
    ECG_ONLINE / "rag_pipeline" / "data" / "ontology_v2.json",   # vendorée (prod)
    PARENT / "rag_pipeline" / "data" / "ontology_v2.json",       # source
]
NEUTRAL_PARENT = "DESCRIPTION_ECG"
MOVES = {
    "ABSENCE_D_ISCHEMIE": "ISCHEMIQUE",
    "ABSENCE_D_ONDE_P": "ONDE_P",
    "ABSENCE_DE_QRS": "QRS",
}


def patch(path: Path, dry: bool) -> None:
    if not path.exists():
        print(f"-- absent : {path}")
        return
    o = json.loads(path.read_text(encoding="utf-8"))
    concepts = o["concepts"]
    changed = []
    for cid, old_parent in MOVES.items():
        c = concepts.get(cid)
        if not c:
            print(f"   {cid}: absent de {path.name}")
            continue
        parents = list(c.get("parents") or [])
        if old_parent in parents:
            parents = [p for p in parents if p != old_parent]
            if NEUTRAL_PARENT not in parents:
                parents.append(NEUTRAL_PARENT)
            c["parents"] = parents
            changed.append(f"{cid}.parents: -{old_parent} +{NEUTRAL_PARENT}")
        par = concepts.get(old_parent) or {}
        kids = list(par.get("children") or [])
        if cid in kids:
            par["children"] = [k for k in kids if k != cid]
            changed.append(f"{old_parent}.children: -{cid}")
        neu = concepts.get(NEUTRAL_PARENT)
        if neu is not None:
            nk = list(neu.get("children") or [])
            if cid not in nk:
                neu["children"] = nk + [cid]
                changed.append(f"{NEUTRAL_PARENT}.children: +{cid}")
    print(f"== {path}")
    for line in changed:
        print("   ", line)
    if not changed:
        print("    (déjà patché)")
        return
    if dry:
        return
    meta = o.setdefault("metadata", {})
    meta["last_patch"] = {
        "date": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "source": HERE.name,
        "negative_polarity_fix": sorted(MOVES),
    }
    bak = path.with_suffix(f".json.bak_{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(path, bak)
    path.write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    écrit ; sauvegarde {bak.name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dry = "--dry-run" in sys.argv
    for t in TARGETS:
        patch(t, dry)
