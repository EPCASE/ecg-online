#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""revert_voltage_merge_keep_owl_concept_2026_08_09.py — Inverse la fusion du
2026-08-09 : au lieu de garder VOLTAGE_NORMAL_DU_QRS (JSON-only, absent du .owl),
on garde VOLTAGE_DU_QRS_NORMAL comme concept CANONIQUE, car il existe réellement
comme classe dans le .owl (BrYOzRZIu7jQTwmfcGsi35.owl) — ce qui évite l'écart
.owl/JSON documenté au §8 du CHANGELOG_ONTOLOGIE.md.

Actions :
  1. Recrée VOLTAGE_DU_QRS_NORMAL (type=finding, tel qu'il existait avant la
     fusion) avec l'UNION des synonymes/excludes actuellement portés par
     VOLTAGE_NORMAL_DU_QRS (qui avait reçu les ajouts).
  2. Supprime VOLTAGE_NORMAL_DU_QRS.
  3. Recâble toute référence résiduelle (VOLTAGE_DU_QRS.children,
     QRS_NORMAL.requires, etc.) vers VOLTAGE_DU_QRS_NORMAL.
  4. Migre le concept_id dans scoring_pilot_v2.json / scoring_v2_review.json.

Applique aux 3 copies runtime, idempotent, avec backups horodatés.
"""
import json
import shutil
import time
from pathlib import Path

ONTO_PATHS = [
    Path(r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json"),
    Path(r"C:\Users\Administrateur\bmad\ECG lecture\ecg-online\rag_pipeline\data\ontology_v2.json"),
    Path(r"C:\Users\Administrateur\bmad\ECG lecture\rag_pipeline\data\ontology_v2.json"),
]
PILOT_PATH = Path(r"C:\Users\Administrateur\bmad\ECG lecture\ecg-online\data\scoring_pilot_v2.json")
REVIEW_PATH = Path(r"C:\Users\Administrateur\bmad\ECG lecture\ecg-online\data\scoring_v2_review.json")

STAMP = time.strftime("%Y%m%d_%H%M%S")

CANON = "VOLTAGE_DU_QRS_NORMAL"   # concept gardé (existe en OWL)
DROP = "VOLTAGE_NORMAL_DU_QRS"    # concept retiré (JSON-only)

# Définition originale de VOLTAGE_DU_QRS_NORMAL avant la fusion du 2026-08-09
# (récupérée du backup data/ontology_v2.json.bak_syncollisions_20260809_172351)
ORIGINAL_CANON = {
    "concept_name": "Voltage du QRS normal",
    "concept_name_en": "QRS voltage",
    "categorie": "DESCRIPTION_ECG",
    "poids": 2,
    "type": "finding",
    "excludes": ["MICROVOLTAGE", "TROUBLE_DE_CONDUCTION_INTRAVENTRICULAIRE",
                 "HYPERTROPHIE_VENTRICULAIRE_GAUCHE"],
    "synonymes": [
        "Amplitude normale du QRS", "normovolté",
        "complexes QRS dépassant 5 mm en périphérique",
        "complexes QRS dépassant 10 mm en précordial",
        "QRS > 5 mm en dérivation périphérique",
        "QRS > 10 mm en dérivation précordiale",
        "amplitudes normales des complexes QRS",
        "voltage QRS précordial conservé",
        "voltage plus important dans les dérivations précordiales",
        "QRS > 10 mm en précordial",
    ],
    "parents": ["VOLTAGE_DU_QRS"],
    "origin_structure": ["VENTRICULE"],
    "hide": 1,
}


def process_ontology(path: Path):
    if not path.exists():
        print(f"[SKIP] absent : {path}")
        return
    data = json.load(open(path, encoding="utf-8"))
    concepts = data["concepts"]
    log = []

    drop_concept = concepts.get(DROP)
    if drop_concept is None and CANON in concepts:
        print(f"[=] {path} : déjà dans l'état cible (rien à faire)")
        return

    # 1) Reconstruit CANON = original + union des synonymes/excludes actuellement sur DROP
    canon = json.loads(json.dumps(ORIGINAL_CANON))  # copie profonde
    if drop_concept:
        have = {s.strip().lower() for s in canon["synonymes"]}
        for s in drop_concept.get("synonymes") or []:
            if s.strip().lower() not in have:
                canon["synonymes"].append(s)
                have.add(s.strip().lower())
        canon_exc = set(canon["excludes"])
        canon_exc |= set(drop_concept.get("excludes") or [])
        canon["excludes"] = sorted(canon_exc)
        # conserve un comment de traçabilité si le concept fusionné en avait un
        if drop_concept.get("comment"):
            canon["comment"] = ("Ex-VOLTAGE_NORMAL_DU_QRS (fusion inversée le 2026-08-09 : "
                                 "VOLTAGE_DU_QRS_NORMAL restauré comme concept canonique car "
                                 "seul à exister réellement dans le .owl).")

    concepts[CANON] = canon
    log.append(f"  + {CANON} recréé (type=finding, hide=1) avec union synonymes/excludes")

    if DROP in concepts:
        del concepts[DROP]
        log.append(f"  - concept supprimé : {DROP}")

    # 2) recâble toute référence residuelle DROP -> CANON
    for cid, concept in concepts.items():
        for field in ("parents", "children", "requires", "supports", "excludes",
                      "has_qualifiers", "has_qualifier_families"):
            vals = concept.get(field)
            if vals and DROP in vals:
                concept[field] = [CANON if v == DROP else v for v in vals]
                # dédoublonne si CANON était déjà présent
                seen = set()
                dedup = []
                for v in concept[field]:
                    if v not in seen:
                        dedup.append(v)
                        seen.add(v)
                concept[field] = dedup
                log.append(f"  - {cid}.{field} : {DROP} -> {CANON}")

    # 3) s'assure que VOLTAGE_DU_QRS.children contient CANON (pas DROP)
    parent = concepts.get("VOLTAGE_DU_QRS")
    if parent is not None:
        children = parent.get("children") or []
        if CANON not in children:
            children.append(CANON)
            parent["children"] = children
            log.append(f"  - VOLTAGE_DU_QRS.children : ajouté {CANON}")

    backup = path.with_suffix(f".json.bak_revertvoltage_{STAMP}")
    shutil.copy(path, backup)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\n=== {path} ===")
    for line in log:
        print(line)
    print(f"[OK] écrit (backup: {backup.name})")


def migrate_case_references(path: Path, label: str):
    if not path.exists():
        print(f"[SKIP] absent : {path}")
        return
    data = json.load(open(path, encoding="utf-8"))
    n = 0

    def walk(o):
        nonlocal n
        if isinstance(o, dict):
            if o.get("concept_id") == DROP:
                o["concept_id"] = CANON
                n += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    if n:
        backup = path.with_suffix(f".json.bak_revertvoltage_{STAMP}")
        shutil.copy(path, backup)
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[OK] {label} : {n} référence(s) {DROP} -> {CANON} migrée(s) (backup: {backup.name})")
    else:
        print(f"[=] {label} : aucune référence à migrer")


if __name__ == "__main__":
    for p in ONTO_PATHS:
        process_ontology(p)
    migrate_case_references(PILOT_PATH, "scoring_pilot_v2.json")
    migrate_case_references(REVIEW_PATH, "scoring_v2_review.json")
