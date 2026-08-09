#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_synonym_removals_to_owl_2026_08_09.py — Reproduit dans le .owl les
retraits de synonymes des catégories A/B/C (fix_synonym_collisions_preexisting_
2026_08_09.py) : retire les skos:altLabel correspondants des classes OWL
existantes. La fusion catégorie D est déjà réglée (VOLTAGE_DU_QRS_NORMAL était
et reste le concept canonique, aucune classe OWL à toucher pour ça).

Opère sur BrYOzRZIu7jQTwmfcGsi35_patched_2026-08-09.owl (déjà généré avec les
10 nouveaux concepts par generate_owl_relecture75.py) — modifie ce même fichier
en place (avec backup .bak avant écriture).
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\Administrateur\bmad\ECG lecture")
OWL_PATH = ROOT / "BrYOzRZIu7jQTwmfcGsi35_patched_2026-08-09.owl"
ID_TO_IRI_PATH = ROOT / "data" / "id_to_iri.json"

# (concept_id, synonyme_a_retirer_lower) — categories A + B + C
REMOVALS = [
    ("MORPHOLOGIE_ONDE_P_SINUSALE", "activité atriale sinusale"),
    ("ARYTHMIE_VENTRICULAIRE", "arythmie ventriculaire polymorphe"),
    ("BLOC_DE_BRANCHE_DROIT", "aspect de bloc de branche droite"),
    ("BLOC_DE_BRANCHE_DROIT_COMPLET", "aspect de bloc de branche droite"),
    ("BLOC_DE_BRANCHE_GAUCHE", "aspect de bloc de branche gauche"),
    ("TACHYCARDIE_ATRIALE_FOCALE", "at"),
    ("BLOC_DE_BRANCHE_DROIT_COMPLET", "bloc de branche droite"),
    ("ONDE_P_NORMALE", "morphologie normale des ondes p"),
    ("ONDE_P_NORMALE", "ondes p de morphologie normale"),
    ("SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST", "onde de pardee"),
    ("ONDE_P_PRESENTE", "onde p avant chaque complexe qrs"),
    ("DYSFONCTION_SINUSALE", "perte de l'automatisme sinusal"),
    ("COURANT_DE_LESION_SOUS_ENDOCARDIQUE", "sous-décalage en miroir"),
    ("FLUTTER_ATRIAL_ATYPIQUE", "ta"),
    ("TROUBLES_DE_CONDUCTION_ET_DE_L_AUTOMATICITE", "trouble de conduction atrioventriculaire"),
    ("TROUBLES_DE_CONDUCTION_ET_DE_L_AUTOMATICITE", "trouble de conduction auriculo-ventriculaire"),
    ("ECHAPPEMENT", "échappement jonctionnel"),
    ("RYTHME_D_ECHAPPEMENT_JONCTIONNEL", "rija"),
    ("ASPECT_DE_BRUGADA", "brs"),
    ("REPOLARISATION_PRECOCE", "ers"),
]


def main():
    id_to_iri = json.load(open(ID_TO_IRI_PATH, encoding="utf-8"))
    owl = OWL_PATH.read_text(encoding="utf-8")

    by_concept = {}
    for cid, syn in REMOVALS:
        by_concept.setdefault(cid, set()).add(syn)

    total_removed = 0
    for cid, syns_lower in by_concept.items():
        iri = id_to_iri.get(cid)
        if not iri:
            print(f"[!] {cid} : pas d'IRI connu, ignoré")
            continue
        pat = re.compile(
            rf'(<owl:Class rdf:about="http://webprotege\.stanford\.edu/{re.escape(iri)}">)(.*?)(</owl:Class>)',
            re.DOTALL)
        m = pat.search(owl)
        if not m:
            print(f"[!] {cid} [{iri}] : classe introuvable dans le .owl")
            continue
        open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)

        def strip_line(match):
            nonlocal total_removed
            text = html.unescape(match.group(1)).strip()
            if text.lower() in syns_lower:
                total_removed += 1
                print(f"  - {cid} : retire altLabel {text!r}")
                return ""
            return match.group(0)

        new_body = re.sub(r'[ \t]*<skos:altLabel[^>]*>([^<]+)</skos:altLabel>\s*\n?',
                           strip_line, body)
        if new_body != body:
            owl = owl[:m.start()] + open_tag + new_body + close_tag + owl[m.end():]

    print(f"\nTotal altLabel retirés : {total_removed}")

    backup = OWL_PATH.with_suffix(".owl.bak")
    shutil.copy(OWL_PATH, backup)
    OWL_PATH.write_text(owl, encoding="utf-8")
    print(f"[OK] écrit : {OWL_PATH} (backup: {backup.name})")


if __name__ == "__main__":
    main()
