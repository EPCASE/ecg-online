#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_synonym_collisions_preexisting_2026_08_09.py — Traite les 20 collisions
de synonymes pré-existantes identifiées lors de la relecture ontologie du
2026-08-09 (validées par l'expert) :

  CATÉGORIE A (règle "spécifique > générique") — 14 synonymes retirés du
  concept le plus générique, gardés sur le plus spécifique.
  CATÉGORIE B (erreur clinique) — RIJA retiré de RYTHME_D_ECHAPPEMENT_JONCTIONNEL
  (RIJA = rythme *accéléré*, pas un rythme d'échappement).
  CATÉGORIE C (arbitrage clinique) — BRS/ERS gardés sur le SYNDROME (diagnostic
  génétique), retirés du simple signe ECG (ASPECT_DE_BRUGADA / REPOLARISATION_PRECOCE).
  CATÉGORIE D (fusion de concepts quasi-doublons) — VOLTAGE_DU_QRS_NORMAL fusionné
  dans VOLTAGE_NORMAL_DU_QRS (qui porte l'inférence ECG_NORMAL, Partie B — concept
  canonique conservé), puis VOLTAGE_DU_QRS_NORMAL supprimé.

Applique aux 3 copies runtime de ontology_v2.json + migre les références
VOLTAGE_DU_QRS_NORMAL -> VOLTAGE_NORMAL_DU_QRS dans scoring_pilot_v2.json et
scoring_v2_review.json (data cases). Idempotent, avec backups horodatés.
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

# --- CATEGORIE A : (synonyme_lower, concept_id_a_garder, [concept_id_a_retirer, ...]) ---
CATEGORY_A = [
    ("activité atriale sinusale", "RYTHME_SINUSAL", ["MORPHOLOGIE_ONDE_P_SINUSALE"]),
    ("arythmie ventriculaire polymorphe", "TACHYCARDIE_VENTRICULAIRE_POLYMORPHE", ["ARYTHMIE_VENTRICULAIRE"]),
    ("aspect de bloc de branche droite", "ASPECT_DE_RETARD_DROIT",
     ["BLOC_DE_BRANCHE_DROIT", "BLOC_DE_BRANCHE_DROIT_COMPLET"]),
    ("aspect de bloc de branche gauche", "ASPECT_DE_RETARD_GAUCHE", ["BLOC_DE_BRANCHE_GAUCHE"]),
    ("at", "TACHYCARDIE_ATRIALE", ["TACHYCARDIE_ATRIALE_FOCALE"]),
    ("bloc de branche droite", "BLOC_DE_BRANCHE_DROIT", ["BLOC_DE_BRANCHE_DROIT_COMPLET"]),
    ("morphologie normale des ondes p", "MORPHOLOGIE_ONDE_P_SINUSALE", ["ONDE_P_NORMALE"]),
    ("ondes p de morphologie normale", "MORPHOLOGIE_ONDE_P_SINUSALE", ["ONDE_P_NORMALE"]),
    ("onde de pardee", "COURANT_DE_LESION_SOUS_EPICARDIQUE",
     ["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST"]),
    ("onde p avant chaque complexe qrs", "1_1", ["ONDE_P_PRESENTE"]),
    ("perte de l'automatisme sinusal", "PARALYSIE_SINUSALE", ["DYSFONCTION_SINUSALE"]),
    ("sous-décalage en miroir", "MIROIR", ["COURANT_DE_LESION_SOUS_ENDOCARDIQUE"]),
    ("ta", "TACHYCARDIE_ATRIALE", ["FLUTTER_ATRIAL_ATYPIQUE"]),
    ("trouble de conduction atrioventriculaire", "BLOC_AURICULO_VENTRICULAIRE",
     ["TROUBLES_DE_CONDUCTION_ET_DE_L_AUTOMATICITE"]),
    ("trouble de conduction auriculo-ventriculaire", "BLOC_AURICULO_VENTRICULAIRE",
     ["TROUBLES_DE_CONDUCTION_ET_DE_L_AUTOMATICITE"]),
    ("échappement jonctionnel", "RYTHME_D_ECHAPPEMENT_JONCTIONNEL", ["ECHAPPEMENT"]),
]

# --- CATEGORIE B : erreur clinique (même format que A) ---
CATEGORY_B = [
    ("rija", "RYTHME_JONCTIONELLE_ACCELERE", ["RYTHME_D_ECHAPPEMENT_JONCTIONNEL"]),
]

# --- CATEGORIE C : arbitrage clinique (garder sur le SYNDROME, retirer du signe ECG) ---
CATEGORY_C = [
    ("brs", "SYNDROME_DE_BRUGADA", ["ASPECT_DE_BRUGADA"]),
    ("ers", "SYNDROME_DE_REPOLARISATION_PRECOCE", ["REPOLARISATION_PRECOCE"]),
]

# --- CATEGORIE D : fusion VOLTAGE_DU_QRS_NORMAL -> VOLTAGE_NORMAL_DU_QRS ---
MERGE_SRC = "VOLTAGE_DU_QRS_NORMAL"
MERGE_DST = "VOLTAGE_NORMAL_DU_QRS"


def remove_synonym(concept: dict, syn_lower: str) -> int:
    syns = concept.get("synonymes") or []
    before = len(syns)
    concept["synonymes"] = [s for s in syns if s.strip().lower() != syn_lower]
    if not concept["synonymes"]:
        del concept["synonymes"]
        return before
    return before - len(concept["synonymes"])


def apply_categories_abc(concepts: dict, log: list):
    for syn, keep_cid, remove_from in CATEGORY_A + CATEGORY_B + CATEGORY_C:
        for cid in remove_from:
            c = concepts.get(cid)
            if not c:
                log.append(f"  [!] {cid} absent (synonyme {syn!r} ignoré)")
                continue
            removed = remove_synonym(c, syn)
            if removed:
                log.append(f"  - {cid} : retire {removed}x {syn!r} (garde sur {keep_cid})")


def merge_voltage_concepts(concepts: dict, log: list):
    src = concepts.get(MERGE_SRC)
    dst = concepts.get(MERGE_DST)
    if not src or not dst:
        log.append(f"  [!] fusion ignorée : {MERGE_SRC} ou {MERGE_DST} absent")
        return

    # union des synonymes (dédup insensible à la casse)
    dst_syns = dst.get("synonymes") or []
    have = {s.strip().lower() for s in dst_syns}
    added = 0
    for s in src.get("synonymes") or []:
        if s.strip().lower() not in have:
            dst_syns.append(s)
            have.add(s.strip().lower())
            added += 1
    dst["synonymes"] = dst_syns

    # union des excludes
    dst_exc = set(dst.get("excludes") or [])
    src_exc = set(src.get("excludes") or [])
    if src_exc - dst_exc:
        dst["excludes"] = sorted(dst_exc | src_exc)

    # union origin_structure
    if src.get("origin_structure"):
        dst_os = list(dst.get("origin_structure") or [])
        for x in src["origin_structure"]:
            if x not in dst_os:
                dst_os.append(x)
        dst["origin_structure"] = dst_os

    # conserve concept_name_en si absent
    if src.get("concept_name_en") and not dst.get("concept_name_en"):
        dst["concept_name_en"] = src["concept_name_en"]

    # trace de la fusion
    dst.setdefault("comment", "")
    fusion_note = (f"Fusionné avec {MERGE_SRC} le 2026-08-09 (doublon quasi-identique, "
                   f"même parent VOLTAGE_DU_QRS) — {MERGE_DST} conservé car porteur de "
                   f"l'inférence ECG_NORMAL (QRS_NORMAL.requires).")
    dst["comment"] = (dst["comment"] + " " + fusion_note).strip() if dst["comment"] else fusion_note

    log.append(f"  + fusion {MERGE_SRC} -> {MERGE_DST} : +{added} synonyme(s), "
               f"excludes={dst.get('excludes')}")

    # supprime le concept source
    del concepts[MERGE_SRC]
    log.append(f"  - concept supprimé : {MERGE_SRC}")

    # recâble VOLTAGE_DU_QRS.children (retire MERGE_SRC)
    parent = concepts.get("VOLTAGE_DU_QRS")
    if parent and MERGE_SRC in (parent.get("children") or []):
        parent["children"] = [c for c in parent["children"] if c != MERGE_SRC]
        log.append(f"  - VOLTAGE_DU_QRS.children : retiré {MERGE_SRC}")

    # cherche et corrige toute autre référence résiduelle à MERGE_SRC dans tous les concepts
    for cid, concept in concepts.items():
        for field in ("parents", "children", "requires", "supports", "excludes",
                      "has_qualifiers", "has_qualifier_families"):
            vals = concept.get(field)
            if vals and MERGE_SRC in vals:
                concept[field] = [MERGE_DST if v == MERGE_SRC else v for v in vals]
                log.append(f"  - {cid}.{field} : {MERGE_SRC} -> {MERGE_DST}")


def process_ontology(path: Path):
    if not path.exists():
        print(f"[SKIP] absent : {path}")
        return
    data = json.load(open(path, encoding="utf-8"))
    concepts = data["concepts"]
    log: list = []
    apply_categories_abc(concepts, log)
    merge_voltage_concepts(concepts, log)

    backup = path.with_suffix(f".json.bak_syncollisions_{STAMP}")
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
            if o.get("concept_id") == MERGE_SRC:
                o["concept_id"] = MERGE_DST
                n += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    if n:
        backup = path.with_suffix(f".json.bak_syncollisions_{STAMP}")
        shutil.copy(path, backup)
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[OK] {label} : {n} référence(s) {MERGE_SRC} -> {MERGE_DST} migrée(s) (backup: {backup.name})")
    else:
        print(f"[=] {label} : aucune référence à migrer")


if __name__ == "__main__":
    for p in ONTO_PATHS:
        process_ontology(p)
    migrate_case_references(PILOT_PATH, "scoring_pilot_v2.json")
    migrate_case_references(REVIEW_PATH, "scoring_v2_review.json")
