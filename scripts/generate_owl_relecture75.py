#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_owl_relecture75.py — Reproduit dans le .owl (pour réimport WebProtégé)
les 10 concepts créés en JSON le 2026-08-09 lors de la relecture complète des 75 cas,
+ met à jour data/id_to_iri.json avec leurs nouveaux IRIs mintés.

Ne modifie JAMAIS le .owl source en place : produit une COPIE datée
(BrYOzRZIu7jQTwmfcGsi35_patched_2026-08-09.owl) à réimporter dans WebProtégé Stanford.

Usage:
    python generate_owl_relecture75.py --dry-run   # aperçu, n'écrit rien
    python generate_owl_relecture75.py             # écrit le .owl patché + id_to_iri.json
"""
from __future__ import annotations
import argparse
import html
import json
import random
import re
import string
from pathlib import Path

ROOT = Path(r"C:\Users\Administrateur\bmad\ECG lecture")
OWL_SRC = ROOT / "BrYOzRZIu7jQTwmfcGsi35.owl"
OWL_OUT = ROOT / "BrYOzRZIu7jQTwmfcGsi35_patched_2026-08-09.owl"
ID_TO_IRI_PATH = ROOT / "data" / "id_to_iri.json"
ONTOLOGY_PATH = ROOT / "data" / "ontology_v2.json"

BASE = "http://webprotege.stanford.edu/"

PROP_REQUIRES = "R7w5XngTituGN8Nt6R834WB"
PROP_SUPPORTS = "RC1nx89OA7XMKZ0L1UMLNYg"
PROP_HAS_QUALIFIERS = "RCYrSiiYt2sTA1qKFTVbXbA"
PROP_EXCLUDES = "Rgkbf3QYLEo9sJtKMJFyFW"
PROP_WEIGHT = "R91SX26q028zwTknzSKDZUj"
PROP_ORIGIN_STRUCTURE = "R8EpeA2cxOPJQ7nwwuht2D2"
ANNOTATION_MAYHAVETERR = "RvQtNXH9Cp7Ss5k9ocYaZD"

WEIGHT_IRI = {5: "RBcPkxOyTreNPKJHa25qM1B",  # Urgent
              4: "RBT3FHCwtm7DKaJJI4e8AtK",  # majeur
              3: "R8SOLkvCn36dXJqU0nxc4L4",  # moyen
              2: "RDS61oKTxprp8xENlr88zdn"}  # descriptif

# concept_id -> parent concept_id (déjà existant dans l'OWL, pour subClassOf)
PARENT_OF = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": "TACHYCARDIE_VENTRICULAIRE",
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": "TACHYCARDIE_VENTRICULAIRE",
    "ANGOR_DE_PRINZMETAL": "ANOMALIES_DU_SEGMENT_ST",
    "EXTENSION_VENTRICULE_DROIT": "VENTRICULE_DROIT",
    "MALADIE_RYTHMIQUE_OREILLETTE": "DYSFONCTION_SINUSALE",
    "S1Q3": "ANOMALIES_DU_SEGMENT_ST",
    "ONDE_P_RETROGRADE": "ONDE_P",
    "BLOC_DE_BRANCHE_ALTERNANT": "BLOC_DE_BRANCHE",
    "FLUTTER_ATRIAL": "TACHYCARDIE_ATRIALE",
    "SYNCOPE": None,  # top-level, contexte clinique
}

# concept_id -> poids (repris du JSON, cf. dump précédent)
POIDS = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": 4,
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": 5,
    "ANGOR_DE_PRINZMETAL": 5,
    "EXTENSION_VENTRICULE_DROIT": 3,
    "MALADIE_RYTHMIQUE_OREILLETTE": 4,
    "S1Q3": 3,
    "ONDE_P_RETROGRADE": 2,
    "BLOC_DE_BRANCHE_ALTERNANT": 4,
    "FLUTTER_ATRIAL": 4,
    "SYNCOPE": None,  # contexte clinique : pas de restriction de poids OWL
}

LABELS_FR = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": "Tachycardie ventriculaire non soutenue",
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": "Tachycardie ventriculaire soutenue",
    "ANGOR_DE_PRINZMETAL": "Angor de Prinzmetal",
    "EXTENSION_VENTRICULE_DROIT": "Extension au ventricule droit",
    "MALADIE_RYTHMIQUE_OREILLETTE": "Maladie rythmique de l'oreillette",
    "S1Q3": "Aspect S1Q3 (McGinn-White)",
    "ONDE_P_RETROGRADE": "Onde P rétrograde",
    "BLOC_DE_BRANCHE_ALTERNANT": "Bloc de branche alternant",
    "FLUTTER_ATRIAL": "Flutter atrial",
    "SYNCOPE": "Syncope",
}
LABELS_EN = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": "Non-sustained ventricular tachycardia",
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": "Sustained ventricular tachycardia",
    "ANGOR_DE_PRINZMETAL": "Prinzmetal's angina",
    "EXTENSION_VENTRICULE_DROIT": "Right ventricular extension",
    "MALADIE_RYTHMIQUE_OREILLETTE": "Sick sinus syndrome (tachy-brady)",
    "S1Q3": "S1Q3 pattern",
    "ONDE_P_RETROGRADE": "Retrograde P wave",
    "BLOC_DE_BRANCHE_ALTERNANT": "Alternating bundle branch block",
    "FLUTTER_ATRIAL": "Atrial flutter",
    "SYNCOPE": "Syncope",
}

# requires (déjà finalisés après dédup synonymes) — concept_id -> [concept_id requis]
REQUIRES = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": ["QRS_LARGE", "TACHYCARDIE", "NON_SOUTENU"],
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": ["QRS_LARGE", "TACHYCARDIE", "SOUTENU"],
    "ANGOR_DE_PRINZMETAL": ["COURANT_DE_LESION_SOUS_EPICARDIQUE"],
    "MALADIE_RYTHMIQUE_OREILLETTE": ["FIBRILLATION_ATRIALE", "DYSFONCTION_SINUSALE"],
}
SUPPORTS = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": ["COMPLEXE_DE_FUSION", "CAPTURE_SUPRAVENTRICULAIRE",
                                                "DISSOCIATION_ATRIO_VENTRICULAIRE"],
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": ["COMPLEXE_DE_FUSION", "CAPTURE_SUPRAVENTRICULAIRE",
                                           "DISSOCIATION_ATRIO_VENTRICULAIRE"],
    "MALADIE_RYTHMIQUE_OREILLETTE": ["BRADYCARDIE_SINUSALE"],
}
HAS_QUALIFIERS = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": ["MONOMORPHE"],
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": ["MONOMORPHE"],
    "S1Q3": ["ONDE_T_NEGATIVE"],
}
EXCLUDES = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": ["TACHYCARDIE_VENTRICULAIRE_SOUTENUE"],
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": ["TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE"],
}
ORIGIN_STRUCTURE = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": ["VENTRICULE"],
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": ["VENTRICULE"],
}
MAYHAVETERRITORY = {"TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE", "TACHYCARDIE_VENTRICULAIRE_SOUTENUE"}

# synonymes FINAUX (après dédup du 2026-08-09) — repris du JSON après fix
SYNONYMES = {
    "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE": ["TVNS", "TV non soutenue", "salve de TV non soutenue",
                                                "tachycardie ventriculaire non soutenue",
                                                "réduction spontanée < 30 secondes"],
    "TACHYCARDIE_VENTRICULAIRE_SOUTENUE": ["TV soutenue", "tachycardie ventriculaire soutenue",
                                            "TV prolongée", "TV > 30 secondes"],
    "ANGOR_DE_PRINZMETAL": ["Prinzmetal", "angor de Prinzmetal", "angor vasospastique",
                            "spasme coronaire", "spasme coronaire droit", "spasme coronarien",
                            "sus-décalage transitoire régressif sous trinitrine",
                            "vasospasme coronaire"],
    "EXTENSION_VENTRICULE_DROIT": ["extension au ventricule droit",
                                   "atteinte du ventricule droit associée",
                                   "sus-décalage V3R-V4R"],
    "MALADIE_RYTHMIQUE_OREILLETTE": ["maladie de l'oreillette", "syndrome bradycardie-tachycardie",
                                     "syndrome tachycardie-bradycardie", "maladie rythmique auriculaire",
                                     "alternance tachyarythmie atriale et dysfonction sinusale"],
    "S1Q3": ["S1Q3", "S1q3", "S1Q3T3", "S1q3T3", "aspect de McGinn-White",
             "onde S en DI et onde Q en DIII"],
    "ONDE_P_RETROGRADE": ["onde P rétrograde", "activité atriale rétrograde",
                          "onde P négative en inférieur", "ondes P' rétrogrades",
                          "conduction atriale rétrograde"],
    "BLOC_DE_BRANCHE_ALTERNANT": ["bloc de branche alternant", "alternance bloc de branche droit/gauche",
                                  "alternance BBD/BBG"],
    "FLUTTER_ATRIAL": ["flutter atrial", "flutter auriculaire", "flutter"],
    "SYNCOPE": ["syncope", "malaise avec perte de connaissance", "perte de connaissance brève",
                "contexte de syncopes"],
}

NEW_CONCEPTS = list(LABELS_FR.keys())


def mint_iri(existing: set) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        cand = "R" + "".join(random.choice(alphabet) for _ in range(21))
        if cand not in existing:
            existing.add(cand)
            return cand


def build_class_block(cid: str, iri: str, id_to_iri: dict) -> str:
    lines = [f'    <owl:Class rdf:about="{BASE}{iri}">']

    parent = PARENT_OF.get(cid)
    if parent:
        p_iri = id_to_iri[parent]
        lines.append(f'        <rdfs:subClassOf rdf:resource="{BASE}{p_iri}"/>')

    def restriction(prop_iri: str, target_cid: str):
        t_iri = id_to_iri[target_cid]
        lines.append("        <rdfs:subClassOf>")
        lines.append("            <owl:Restriction>")
        lines.append(f'                <owl:onProperty rdf:resource="{BASE}{prop_iri}"/>')
        lines.append(f'                <owl:someValuesFrom rdf:resource="{BASE}{t_iri}"/>')
        lines.append("            </owl:Restriction>")
        lines.append("        </rdfs:subClassOf>")

    for t in REQUIRES.get(cid, []):
        restriction(PROP_REQUIRES, t)
    for t in SUPPORTS.get(cid, []):
        restriction(PROP_SUPPORTS, t)
    for t in HAS_QUALIFIERS.get(cid, []):
        restriction(PROP_HAS_QUALIFIERS, t)
    for t in EXCLUDES.get(cid, []):
        restriction(PROP_EXCLUDES, t)
    for t in ORIGIN_STRUCTURE.get(cid, []):
        restriction(PROP_ORIGIN_STRUCTURE, t)

    poids = POIDS.get(cid)
    if poids is not None:
        w_iri = WEIGHT_IRI[poids]
        lines.append("        <rdfs:subClassOf>")
        lines.append("            <owl:Restriction>")
        lines.append(f'                <owl:onProperty rdf:resource="{BASE}{PROP_WEIGHT}"/>')
        lines.append(f'                <owl:someValuesFrom rdf:resource="{BASE}{w_iri}"/>')
        lines.append("            </owl:Restriction>")
        lines.append("        </rdfs:subClassOf>")

    if cid in MAYHAVETERRITORY:
        lines.append(f'        <webprotege:{ANNOTATION_MAYHAVETERR} '
                      f'rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true'
                      f'</webprotege:{ANNOTATION_MAYHAVETERR}>')

    lines.append(f'        <rdfs:label xml:lang="fr">{html.escape(LABELS_FR[cid])}</rdfs:label>')
    lines.append(f'        <rdfs:label xml:lang="en">{html.escape(LABELS_EN[cid])}</rdfs:label>')
    for syn in SYNONYMES.get(cid, []):
        lines.append(f"        <skos:altLabel>{html.escape(syn)}</skos:altLabel>")

    lines.append("    </owl:Class>")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    owl = OWL_SRC.read_text(encoding="utf-8")
    id_to_iri = json.load(open(ID_TO_IRI_PATH, encoding="utf-8"))

    # IRIs déjà utilisés dans le .owl (pour ne jamais collisionner en mintant les nouveaux)
    existing_iris = set(re.findall(r'http://webprotege\.stanford\.edu/([A-Za-z0-9]+)', owl))
    existing_iris |= set(id_to_iri.values())

    minted = {}
    for cid in NEW_CONCEPTS:
        if cid in id_to_iri:
            print(f"[SKIP] {cid} a déjà un IRI ({id_to_iri[cid]}) — non re-mintè.")
            minted[cid] = id_to_iri[cid]
            continue
        minted[cid] = mint_iri(existing_iris)

    print("IRIs mintés :")
    for cid, iri in minted.items():
        print(f"  {cid} -> {iri}")

    id_to_iri_new = dict(id_to_iri)
    id_to_iri_new.update(minted)

    blocks = [build_class_block(cid, minted[cid], id_to_iri_new) for cid in NEW_CONCEPTS]
    insertion = "\n\n" + "\n\n".join(blocks) + "\n"

    idx = owl.rfind("</rdf:RDF>")
    if idx == -1:
        raise RuntimeError("Balise </rdf:RDF> introuvable dans le .owl source.")
    new_owl = owl[:idx] + insertion + owl[idx:]

    print(f"\n{len(blocks)} classes OWL générées, insérées avant </rdf:RDF>.")

    if args.dry_run:
        print("[DRY-RUN] Aucun fichier écrit.")
        print("\n--- Aperçu du premier bloc ---")
        print(blocks[0])
        return

    OWL_OUT.write_text(new_owl, encoding="utf-8")
    print(f"[OK] écrit : {OWL_OUT}")

    json.dump(id_to_iri_new, open(ID_TO_IRI_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, sort_keys=True)
    print(f"[OK] mis à jour : {ID_TO_IRI_PATH}")


if __name__ == "__main__":
    main()
