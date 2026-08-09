#!/usr/bin/env python3
"""
add_missing_concepts_relecture75.py — Ajoute les concepts manquants repérés lors
de la relecture des 75 cas (2026-08-09, cf. _tempreponserelecture75.md) :

  - TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE (TVNS) et
    TACHYCARDIE_VENTRICULAIRE_SOUTENUE (TV soutenue) : enfants de
    TACHYCARDIE_VENTRICULAIRE, pour distinguer explicitement les 2 formes
    (cas 35 : "créer TVNS et TV dans l'ontologie").
  - ANGOR_DE_PRINZMETAL : absent de l'ontologie (cas 70, critère qui utilisait
    l'ID libre "Prinzmetal" au lieu d'un concept réel).
  - EXTENSION_VENTRICULE_DROIT : absent (cas 60, critère qui utilisait un ID
    inventé). Modélisé comme finding lié à VENTRICULE_DROIT (territoire IDM).

Applique le même patch sur les 3 copies vendues de l'ontologie.

Usage : python scripts/add_missing_concepts_relecture75.py [--write]
"""
from __future__ import annotations

import argparse
import json
import os

ONTO_PATHS = [
    r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\ECG lecture\ecg-online\rag_pipeline\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\ECG lecture\rag_pipeline\data\ontology_v2.json",
]

NEW_CONCEPTS = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": {
        "concept_name": "Tachycardie ventriculaire non soutenue",
        "concept_name_en": "Non-sustained ventricular tachycardia",
        "categorie": "DIAGNOSTIC_URGENT",
        "poids": 4,
        "type": "pattern",
        "requires": ["QRS_LARGE", "TACHYCARDIE", "NON_SOUTENU"],
        "supports": ["COMPLEXE_DE_FUSION", "CAPTURE_SUPRAVENTRICULAIRE", "DISSOCIATION_ATRIO_VENTRICULAIRE"],
        "has_qualifiers": ["MONOMORPHE"],
        "excludes": ["TACHYCARDIE_VENTRICULAIRE_SOUTENUE"],
        "synonymes": ["TVNS", "TV non soutenue", "salve de TV non soutenue",
                      "tachycardie ventriculaire non soutenue", "réduction spontanée < 30 secondes"],
        "parents": ["TACHYCARDIE_VENTRICULAIRE"],
        "origin_structure": ["VENTRICULE"],
        "mayhaveterritory": True,
    },
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": {
        "concept_name": "Tachycardie ventriculaire soutenue",
        "concept_name_en": "Sustained ventricular tachycardia",
        "categorie": "DIAGNOSTIC_URGENT",
        "poids": 5,
        "type": "pattern",
        "requires": ["QRS_LARGE", "TACHYCARDIE", "SOUTENU"],
        "supports": ["COMPLEXE_DE_FUSION", "CAPTURE_SUPRAVENTRICULAIRE", "DISSOCIATION_ATRIO_VENTRICULAIRE"],
        "has_qualifiers": ["MONOMORPHE"],
        "excludes": ["TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE"],
        "synonymes": ["TV soutenue", "tachycardie ventriculaire soutenue", "TV prolongée",
                      "TV > 30 secondes"],
        "parents": ["TACHYCARDIE_VENTRICULAIRE"],
        "origin_structure": ["VENTRICULE"],
        "mayhaveterritory": True,
    },
    "ANGOR_DE_PRINZMETAL": {
        "concept_name": "Angor de Prinzmetal",
        "concept_name_en": "Prinzmetal's angina",
        "categorie": "DIAGNOSTIC_MAJEUR",
        "poids": 5,
        "type": "pattern",
        "requires": ["COURANT_DE_LESION_SOUS_EPICARDIQUE"],
        "synonymes": ["Prinzmetal", "angor de Prinzmetal", "angor vasospastique",
                      "spasme coronaire", "spasme coronaire droit", "spasme coronarien",
                      "sus-décalage transitoire régressif sous trinitrine",
                      "vasospasme coronaire"],
        "parents": ["ANOMALIES_DU_SEGMENT_ST"],
        "comment": "Sus-décalage ST transitoire et régressif (spontanément ou sous "
                   "trinitrine), lié à un spasme coronaire — distinct du SCA ST+ par "
                   "constitution de plaque (cf. relecture 2026-08-09, cas 70).",
    },
    "EXTENSION_VENTRICULE_DROIT": {
        "concept_name": "Extension au ventricule droit",
        "concept_name_en": "Right ventricular extension",
        "categorie": "DIAGNOSTIC_MOYEN",
        "poids": 3,
        "type": "finding",
        "parents": ["VENTRICULE_DROIT"],
        "synonymes": ["extension au ventricule droit", "atteinte du ventricule droit associée",
                      "infarctus inférieur avec extension au ventricule droit",
                      "sus-décalage V3R-V4R"],
        "comment": "Cf. relecture 2026-08-09, cas 60 : extension VD sur SCA ST+ inférieur, "
                   "sus-décalage significatif en V3R-V4R.",
    },
    "MALADIE_RYTHMIQUE_OREILLETTE": {
        "concept_name": "Maladie rythmique de l'oreillette",
        "concept_name_en": "Sick sinus syndrome (tachy-brady)",
        "categorie": "DIAGNOSTIC_MAJEUR",
        "poids": 4,
        "type": "pattern",
        "requires": ["FIBRILLATION_ATRIALE", "DYSFONCTION_SINUSALE"],
        "supports": ["BRADYCARDIE_SINUSALE"],
        "synonymes": ["maladie de l'oreillette", "syndrome bradycardie-tachycardie",
                      "syndrome tachycardie-bradycardie", "maladie rythmique auriculaire",
                      "alternance tachyarythmie atriale et dysfonction sinusale"],
        "parents": ["DYSFONCTION_SINUSALE"],
        "comment": "Alternance d'épisodes de tachyarythmie atriale (le plus souvent FA) et "
                   "de dysfonction sinusale/bradycardie sinusale — cf. relecture 2026-08-09, "
                   "cas 31.",
    },
    "S1Q3": {
        "concept_name": "Aspect S1Q3 (McGinn-White)",
        "concept_name_en": "S1Q3 pattern",
        "categorie": "DIAGNOSTIC_MOYEN",
        "poids": 3,
        "type": "pattern",
        "has_qualifiers": ["ONDE_T_NEGATIVE"],
        "synonymes": ["S1Q3", "S1q3", "S1Q3T3", "S1q3T3", "aspect de McGinn-White",
                      "onde S en DI et onde Q en DIII"],
        "parents": ["ANOMALIES_DU_SEGMENT_ST"],
        "comment": "Signe évocateur (non spécifique) de cœur pulmonaire aigu/embolie "
                   "pulmonaire — cf. relecture 2026-08-09, cas 53/54.",
    },
    "ONDE_P_RETROGRADE": {
        "concept_name": "Onde P rétrograde",
        "concept_name_en": "Retrograde P wave",
        "categorie": "DESCRIPTION_ECG",
        "poids": 2,
        "type": "finding",
        "synonymes": ["onde P rétrograde", "activité atriale rétrograde",
                      "onde P négative en inférieur", "ondes P' rétrogrades",
                      "conduction atriale rétrograde"],
        "parents": ["ONDE_P"],
        "comment": "Activité atriale rétrograde (négative en inférieur, positive en "
                   "V1/aVR), typique d'une dépolarisation atriale de bas en haut (rythme "
                   "jonctionnel, TV avec conduction rétrograde…) — cf. relecture "
                   "2026-08-09, cas 44/60.",
    },
    "BLOC_DE_BRANCHE_ALTERNANT": {
        "concept_name": "Bloc de branche alternant",
        "concept_name_en": "Alternating bundle branch block",
        "categorie": "DIAGNOSTIC_MAJEUR",
        "poids": 4,
        "type": "pattern",
        "requires": ["BLOC_DE_BRANCHE"],
        "synonymes": ["bloc de branche alternant", "alternance bloc de branche droit/gauche",
                      "alternance BBD/BBG"],
        "parents": ["BLOC_DE_BRANCHE"],
        "comment": "Alternance d'un bloc de branche droit et d'un bloc de branche gauche "
                   "sur des tracés successifs — signe de maladie bi/trifasciculaire "
                   "sévère, à haut risque de BAV complet. Cf. relecture 2026-08-09, cas 14.",
    },
    "FLUTTER_ATRIAL": {
        "concept_name": "Flutter atrial",
        "concept_name_en": "Atrial flutter",
        "categorie": "DIAGNOSTIC_MAJEUR",
        "poids": 4,
        "type": "pattern",
        "requires": ["TACHYCARDIE_ATRIALE"],
        "synonymes": ["flutter atrial", "flutter auriculaire", "flutter"],
        "parents": ["TACHYCARDIE_ATRIALE"],
        "children": ["FLUTTER_ATRIAL_ANTIHORAIRE", "FLUTTER_ATRIAL_ATYPIQUE",
                     "FLUTTER_ATRIAL_HORAIRE", "FLUTTER_DROIT_TYPIQUE"],
        "comment": "Concept générique regroupant les sous-types de flutter déjà modélisés "
                   "(horaire/antihoraire/atypique/droit typique) — utile pour une "
                   "exclusion large sans devoir choisir un sous-type précis. Cf. relecture "
                   "2026-08-09, cas 65.",
    },
    "SYNCOPE": {
        "concept_name": "Syncope",
        "concept_name_en": "Syncope",
        "categorie": "CONTEXTE_CLINIQUE",
        "poids": 2,
        "type": "context",
        "synonymes": ["syncope", "malaise avec perte de connaissance",
                      "perte de connaissance brève", "contexte de syncopes"],
        "comment": "Contexte clinique (pas un signe ECG) — motif de réalisation de "
                   "l'ECG, pertinent pour évaluer le risque de trouble conductif "
                   "paroxystique (BAV complet infra-hissien…). Cf. relecture "
                   "2026-08-09, cas 11.",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    for path in ONTO_PATHS:
        if not os.path.exists(path):
            print(f"SKIP (introuvable) : {path}")
            continue
        with open(path, encoding="utf-8") as f:
            onto = json.load(f)
        concepts = onto["concepts"]
        added = []
        for cid, payload in NEW_CONCEPTS.items():
            if cid in concepts:
                print(f"[{os.path.basename(path)}] {cid} déjà présent — skip")
                continue
            concepts[cid] = payload
            added.append(cid)
            # Ajoute cid aux 'children' du parent s'il existe
            for parent in payload.get("parents", []):
                if parent in concepts:
                    ch = concepts[parent].setdefault("children", [])
                    if ch is None:
                        concepts[parent]["children"] = ch = []
                    if cid not in ch:
                        ch.append(cid)
        print(f"[{os.path.basename(path)}] ajoutés : {added}")
        if args.write and added:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(onto, f, ensure_ascii=False, indent=2)
            print(f"  -> écrit dans {path}")

    if not args.write:
        print("\n(dry-run — relancer avec --write pour appliquer)")


if __name__ == "__main__":
    main()
